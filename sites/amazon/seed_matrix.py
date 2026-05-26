#!/usr/bin/env python3
"""R3 matrix expansion seeder for Amazon mirror.

Adds ~1500 additional products via deterministic brand × model × color × storage
matrices for electronics + computers, plus a second pass over Open Library
books (sites/amazon/_data/openlib_books_r3.json) to bring books → 1500+.

Idempotent: every function early-returns when its slot already has rows.
Every value derived from a fixed Random(seed) or computed from idx so
instance_seed/amazon_store.db md5 stays byte-identical across rebuilds.
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
    return s[:120]


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


def _pool(dirs):
    seen, out = set(), []
    for d in dirs:
        for p in _list_imgs(d):
            if p not in seen:
                seen.add(p)
                out.append(p)
    return out


# ---------------------------------------------------------------------------
# 1) Real-brand electronics SKU matrix (smartphones / tablets / laptops)
# ---------------------------------------------------------------------------
#
# Each entry produces brand × model × color × storage SKUs with realistic
# pricing tiers. The result looks like real Amazon listings the agent can
# filter on color="Midnight" or storage="256GB".

# (brand, model_line, subcat, base_price_128gb, list_uplift_pct, tag_csv, base_specs)
PHONE_MODELS = [
    ('Apple', 'iPhone 15',          'Smartphones', 799.00, 0,  'iphone,5g,a16,ios,unlocked',
     {'CPU':'Apple A16 Bionic','Display':'6.1in Super Retina XDR OLED','Camera':'48MP Main + 12MP Ultra','OS':'iOS 17'}),
    ('Apple', 'iPhone 15 Pro',      'Smartphones', 999.00, 0,  'iphone,pro,5g,a17,titanium,unlocked',
     {'CPU':'Apple A17 Pro','Display':'6.1in ProMotion OLED','Camera':'48MP + 12MP + 12MP','OS':'iOS 17','Body':'Titanium'}),
    ('Apple', 'iPhone 15 Pro Max',  'Smartphones', 1199.00, 0, 'iphone,pro,max,5g,a17,titanium,unlocked',
     {'CPU':'Apple A17 Pro','Display':'6.7in ProMotion OLED','Camera':'48MP + 5x Tetraprism + 12MP','OS':'iOS 17','Body':'Titanium'}),
    ('Apple', 'iPhone 14',          'Smartphones', 699.00, 12, 'iphone,5g,a15,ios',
     {'CPU':'Apple A15 Bionic','Display':'6.1in Super Retina XDR OLED','Camera':'12MP Main + 12MP Ultra','OS':'iOS 17'}),
    ('Apple', 'iPhone 13',          'Smartphones', 599.00, 20, 'iphone,5g,a15,ios,budget',
     {'CPU':'Apple A15 Bionic','Display':'6.1in OLED','Camera':'12MP dual','OS':'iOS 17'}),
    ('Apple', 'iPhone 12',          'Smartphones', 499.00, 25, 'iphone,5g,a14,ios,budget',
     {'CPU':'Apple A14 Bionic','Display':'6.1in OLED','Camera':'12MP dual','OS':'iOS 17'}),
    ('Apple', 'iPhone SE (3rd Gen)','Smartphones', 429.00, 18, 'iphone,5g,a15,touch-id,budget',
     {'CPU':'Apple A15 Bionic','Display':'4.7in LCD','Camera':'12MP','OS':'iOS 17','Body':'Aluminum + Glass'}),
    ('Samsung', 'Galaxy S24',       'Smartphones', 799.99, 12, 'galaxy,android,5g,unlocked,snapdragon',
     {'CPU':'Snapdragon 8 Gen 3','Display':'6.2in Dynamic AMOLED 2X 120Hz','Camera':'50MP + 12MP + 10MP','OS':'Android 14'}),
    ('Samsung', 'Galaxy S24 Ultra', 'Smartphones', 1299.99, 10, 'galaxy,ultra,android,5g,snapdragon,s-pen,titanium',
     {'CPU':'Snapdragon 8 Gen 3','Display':'6.8in Dynamic AMOLED 2X 120Hz','Camera':'200MP + 50MP + 12MP + 10MP','OS':'Android 14','S Pen':'Yes','Body':'Titanium'}),
    ('Samsung', 'Galaxy S23 FE',    'Smartphones', 599.99, 22, 'galaxy,fe,android,5g',
     {'CPU':'Exynos 2200','Display':'6.4in AMOLED 120Hz','Camera':'50MP triple','OS':'Android 14'}),
    ('Samsung', 'Galaxy A54 5G',    'Smartphones', 449.99, 25, 'galaxy,a-series,android,5g,budget',
     {'CPU':'Exynos 1380','Display':'6.4in Super AMOLED','Camera':'50MP triple','OS':'Android 14'}),
    ('Samsung', 'Galaxy Z Flip5',   'Smartphones', 999.99, 15, 'galaxy,foldable,android,5g',
     {'CPU':'Snapdragon 8 Gen 2','Display':'6.7in foldable AMOLED','Camera':'12MP + 12MP','OS':'Android 14','Form Factor':'Flip foldable'}),
    ('Samsung', 'Galaxy Z Fold5',   'Smartphones', 1799.99, 12, 'galaxy,foldable,android,5g,s-pen,large',
     {'CPU':'Snapdragon 8 Gen 2','Display':'7.6in foldable AMOLED','Camera':'50MP + 12MP + 10MP','OS':'Android 14','Form Factor':'Book foldable'}),
    ('Google', 'Pixel 8',           'Smartphones', 699.00, 14, 'pixel,android,5g,tensor,unlocked',
     {'CPU':'Google Tensor G3','Display':'6.2in OLED 120Hz','Camera':'50MP + 12MP ultrawide','OS':'Android 14'}),
    ('Google', 'Pixel 8 Pro',       'Smartphones', 999.00, 12, 'pixel,pro,android,5g,tensor,telephoto',
     {'CPU':'Google Tensor G3','Display':'6.7in LTPO OLED 120Hz','Camera':'50MP + 48MP + 48MP','OS':'Android 14'}),
    ('Google', 'Pixel 7a',          'Smartphones', 499.00, 22, 'pixel,a-series,android,5g,budget',
     {'CPU':'Google Tensor G2','Display':'6.1in OLED 90Hz','Camera':'64MP + 13MP','OS':'Android 14'}),
    ('OnePlus', '12',               'Smartphones', 799.99, 12, 'oneplus,android,5g,snapdragon,fast-charge',
     {'CPU':'Snapdragon 8 Gen 3','Display':'6.82in LTPO AMOLED 120Hz','Camera':'50MP + 48MP + 64MP','OS':'OxygenOS 14','Charging':'100W SuperVOOC'}),
    ('Motorola', 'Edge 50 Pro',     'Smartphones', 499.99, 25, 'motorola,android,5g,snapdragon,curved',
     {'CPU':'Snapdragon 7 Gen 3','Display':'6.7in OLED 144Hz','Camera':'50MP + 13MP + 10MP','OS':'Android 14'}),
    ('Xiaomi', '14 Pro',            'Smartphones', 999.99, 14, 'xiaomi,android,5g,leica,snapdragon',
     {'CPU':'Snapdragon 8 Gen 3','Display':'6.73in LTPO AMOLED 120Hz','Camera':'50MP Leica + 50MP + 50MP','OS':'HyperOS'}),
    ('Nothing', 'Phone (2)',        'Smartphones', 599.00, 18, 'nothing,android,5g,transparent,glyph',
     {'CPU':'Snapdragon 8+ Gen 1','Display':'6.7in LTPO OLED 120Hz','Camera':'50MP + 50MP','OS':'Nothing OS','Design':'Glyph Interface'}),
]

# Color palettes — each brand uses its own marketing color names
COLORS = {
    'Apple':    ['Black Titanium', 'White Titanium', 'Blue Titanium', 'Natural Titanium', 'Midnight', 'Starlight', 'Pink', 'Blue', 'Green', 'Purple'],
    'Samsung':  ['Phantom Black', 'Cream', 'Lavender', 'Mint', 'Graphite', 'Titanium Black', 'Titanium Violet', 'Titanium Gray', 'Awesome Iceberg Blue'],
    'Google':   ['Obsidian', 'Hazel', 'Rose', 'Porcelain', 'Bay', 'Coral', 'Snow', 'Charcoal'],
    'OnePlus':  ['Silky Black', 'Flowy Emerald'],
    'Motorola': ['Black Beauty', 'Vegan Leather Caneel Bay', 'Luxe Lavender'],
    'Xiaomi':   ['Black', 'White', 'Jade Green'],
    'Nothing':  ['Black', 'White'],
}

# Storage tiers (GB) and the multiplier vs base 128GB price
STORAGE_TIERS = [
    (128,  1.00),
    (256,  1.13),
    (512,  1.38),
    (1024, 1.63),
]


def _build_phone(brand, model, subcat, base_price, uplift, tag_csv, base_specs,
                 color, storage_gb, storage_mult, idx, pool):
    storage_str = f"{storage_gb}GB" if storage_gb < 1024 else f"{storage_gb // 1024}TB"
    name = f"{brand} {model} ({storage_str}, {color}) - Unlocked"
    price = round(base_price * storage_mult, 2)
    list_price = round(price * (1 + uplift / 100.0), 2) if uplift else price
    rating = round(4.0 + ((idx * 17 + storage_gb // 64) % 90) / 100.0, 1)
    if rating > 4.9:
        rating = 4.9
    reviews = 250 + (idx * 211) % 38500
    specs = dict(base_specs)
    specs['Brand'] = brand
    specs['Model'] = model
    specs['Storage'] = storage_str
    specs['Color'] = color
    specs['Connectivity'] = '5G + Wi-Fi 6'
    features = [
        f'Storage: {storage_str}',
        f'Color: {color}',
        f'Display: {base_specs.get("Display", "")}',
        f'CPU: {base_specs.get("CPU", "")}',
        f'OS: {base_specs.get("OS", "")}',
        f'Connectivity: 5G, Wi-Fi 6, Bluetooth 5.3',
    ]
    tags = [t.strip() for t in tag_csv.split(',') if t.strip()]
    tags.extend([color.lower().split()[0], storage_str.lower(), 'smartphone', f'{storage_gb}gb'])
    img = pool[idx % len(pool)] if pool else '/static/images/homepage/placeholder.jpg'
    gallery = [pool[(idx + j * 7) % len(pool)] for j in range(6)] if pool else []
    description = (
        f"{brand} {model} smartphone — {storage_str} storage, {color}. "
        f"Featuring {base_specs.get('CPU', 'flagship')} performance and "
        f"{base_specs.get('Display', 'a vivid display')}. Unlocked for use "
        f"with any major US carrier."
    )
    is_deal = (idx % 5 == 0) or uplift >= 18
    is_bestseller = (storage_gb in (128, 256) and brand in ('Apple', 'Samsung', 'Google'))
    is_featured = (idx % 23 == 0)
    return dict(
        name=name, brand=brand, category_slug='electronics', subcategory=subcat,
        description=description, features=features, specs=specs,
        price=price, list_price=list_price, image=img, gallery=gallery,
        variants={'color': COLORS.get(brand, [color]), 'storage': [f"{g}GB" if g < 1024 else f"{g//1024}TB" for g, _ in STORAGE_TIERS]},
        stock=20 + (idx * 11 + storage_gb // 64) % 250,
        rating=rating, reviews=reviews,
        is_featured=is_featured, is_bestseller=is_bestseller, is_deal=is_deal,
        tags=tags, release_date='2024-01-01' if brand == 'Apple' else '2024-02-01',
    )


# ---------------------------------------------------------------------------
# 2) Tablet matrix (smaller — ~80 SKUs)
# ---------------------------------------------------------------------------
TABLET_MODELS = [
    ('Apple', 'iPad (10th Gen)',     'Tablets', 449.00, 0,  'ipad,wifi,a14,ios,family',
     {'CPU':'Apple A14 Bionic','Display':'10.9in Liquid Retina','OS':'iPadOS 17','Cellular':'Wi-Fi only'}),
    ('Apple', 'iPad Air (M2)',       'Tablets', 599.00, 0,  'ipad,air,m2,wifi,creative',
     {'CPU':'Apple M2','Display':'11in Liquid Retina','OS':'iPadOS 17','Cellular':'Wi-Fi only'}),
    ('Apple', 'iPad Pro 11" (M4)',   'Tablets', 999.00, 0,  'ipad,pro,m4,wifi,oled,creative',
     {'CPU':'Apple M4','Display':'11in Tandem OLED ProMotion','OS':'iPadOS 17','Cellular':'Wi-Fi only'}),
    ('Apple', 'iPad Pro 13" (M4)',   'Tablets', 1299.00, 0, 'ipad,pro,m4,wifi,oled,large,creative',
     {'CPU':'Apple M4','Display':'13in Tandem OLED ProMotion','OS':'iPadOS 17','Cellular':'Wi-Fi only'}),
    ('Apple', 'iPad mini 6',         'Tablets', 499.00, 10, 'ipad,mini,a15,wifi,portable',
     {'CPU':'Apple A15 Bionic','Display':'8.3in Liquid Retina','OS':'iPadOS 17','Cellular':'Wi-Fi only'}),
    ('Samsung', 'Galaxy Tab S9',     'Tablets', 799.99, 12, 'galaxy,tab,android,amoled,s-pen',
     {'CPU':'Snapdragon 8 Gen 2','Display':'11in AMOLED 120Hz','OS':'Android 14','S Pen':'Included'}),
    ('Samsung', 'Galaxy Tab S9 Ultra','Tablets', 1199.99, 12, 'galaxy,tab,ultra,android,amoled,s-pen,large',
     {'CPU':'Snapdragon 8 Gen 2','Display':'14.6in AMOLED 120Hz','OS':'Android 14','S Pen':'Included'}),
    ('Samsung', 'Galaxy Tab A9+',    'Tablets', 219.99, 20, 'galaxy,tab,a-series,android,budget',
     {'CPU':'Snapdragon 695','Display':'11in LCD 90Hz','OS':'Android 13','S Pen':'Not included'}),
    ('Amazon', 'Fire HD 10',         'Tablets', 149.99, 33, 'fire,tablet,kids,amazon',
     {'CPU':'Octa-core 2.05GHz','Display':'10.1in 1080p Full HD','OS':'Fire OS','Voice':'Alexa'}),
    ('Amazon', 'Fire Max 11',        'Tablets', 229.99, 28, 'fire,tablet,max,productivity',
     {'CPU':'MediaTek MT8188J','Display':'11in 2000x1200','OS':'Fire OS','Stylus':'Optional'}),
    ('Microsoft', 'Surface Pro 9',   'Tablets', 1099.99, 18, 'surface,2-in-1,windows-11,tablet',
     {'CPU':'Intel Core i5-1235U','Display':'13in PixelSense 120Hz','OS':'Windows 11 Home','Type Cover':'Sold separately'}),
    ('Lenovo', 'Tab P12 Pro',        'Tablets', 699.99, 16, 'lenovo,tab,android,oled',
     {'CPU':'Snapdragon 870','Display':'12.6in AMOLED 120Hz','OS':'Android 13','Pen':'Included'}),
]

TABLET_COLORS = {
    'Apple':     ['Space Gray', 'Silver', 'Pink', 'Blue', 'Yellow', 'Starlight'],
    'Samsung':   ['Graphite', 'Beige', 'Cream'],
    'Amazon':    ['Black', 'Denim', 'Lilac', 'Olive'],
    'Microsoft': ['Platinum', 'Graphite', 'Sapphire', 'Forest'],
    'Lenovo':    ['Storm Gray'],
}

TABLET_STORAGE = [
    (64,   1.00),
    (128,  1.10),
    (256,  1.22),
    (512,  1.45),
    (1024, 1.78),
]


def _build_tablet(brand, model, subcat, base_price, uplift, tag_csv, base_specs,
                  color, storage_gb, storage_mult, idx, pool):
    storage_str = f"{storage_gb}GB" if storage_gb < 1024 else f"{storage_gb // 1024}TB"
    name = f"{brand} {model} {storage_str} ({color})"
    price = round(base_price * storage_mult, 2)
    list_price = round(price * (1 + uplift / 100.0), 2) if uplift else price
    rating = round(4.1 + ((idx * 13 + storage_gb // 32) % 80) / 100.0, 1)
    reviews = 180 + (idx * 173) % 22000
    specs = dict(base_specs)
    specs['Brand'] = brand
    specs['Model'] = model
    specs['Storage'] = storage_str
    specs['Color'] = color
    specs['RAM'] = '8GB' if storage_gb >= 256 else '6GB'
    features = [
        f'Storage: {storage_str}',
        f'Color: {color}',
        f'Display: {base_specs.get("Display", "")}',
        f'CPU: {base_specs.get("CPU", "")}',
        f'OS: {base_specs.get("OS", "")}',
        'Wi-Fi 6 + Bluetooth 5.3',
    ]
    tags = [t.strip() for t in tag_csv.split(',') if t.strip()]
    tags.extend([color.lower().split()[0], storage_str.lower(), 'tablet'])
    img = pool[(idx * 3) % len(pool)] if pool else '/static/images/homepage/placeholder.jpg'
    gallery = [pool[(idx + j * 5) % len(pool)] for j in range(6)] if pool else []
    description = (
        f"{brand} {model} tablet in {color} with {storage_str} of storage. "
        f"Powered by {base_specs.get('CPU', 'a modern processor')} and a "
        f"{base_specs.get('Display', 'high-resolution display')}."
    )
    is_deal = (idx % 4 == 0)
    is_bestseller = (storage_gb in (64, 128) and brand in ('Apple', 'Samsung', 'Amazon'))
    return dict(
        name=name, brand=brand, category_slug='electronics', subcategory=subcat,
        description=description, features=features, specs=specs,
        price=price, list_price=list_price, image=img, gallery=gallery,
        variants={'color': TABLET_COLORS.get(brand, [color]),
                  'storage': [f"{g}GB" if g < 1024 else f"{g//1024}TB" for g, _ in TABLET_STORAGE]},
        stock=15 + (idx * 17 + storage_gb // 32) % 250,
        rating=rating, reviews=reviews,
        is_featured=(idx % 19 == 0), is_bestseller=is_bestseller, is_deal=is_deal,
        tags=tags, release_date='2024-03-01',
    )


# ---------------------------------------------------------------------------
# 3) Laptop matrix (config-driven: CPU x RAM x storage)
# ---------------------------------------------------------------------------
LAPTOP_MODELS = [
    # (brand, line, subcat, base_price, list_uplift, tag_csv, base_specs)
    ('Apple', 'MacBook Air 13" M3',  'Laptops', 1099.00, 0,  'macbook,m3,macos,apple',
     {'CPU':'Apple M3','Display':'13.6in Liquid Retina','OS':'macOS','Battery':'18h'}),
    ('Apple', 'MacBook Pro 14" M3 Pro', 'Laptops', 1999.00, 0, 'macbook,pro,m3-pro,macos,creator',
     {'CPU':'Apple M3 Pro','Display':'14.2in Liquid Retina XDR','OS':'macOS','Battery':'17h'}),
    ('Apple', 'MacBook Pro 16" M3 Max', 'Laptops', 3499.00, 0, 'macbook,pro,m3-max,macos,pro,large',
     {'CPU':'Apple M3 Max','Display':'16.2in Liquid Retina XDR','OS':'macOS','Battery':'21h'}),
    ('Dell',  'XPS 13 (i7, 16GB)',   'Laptops', 1299.99, 18, 'xps,13in,i7,windows-11-home,premium',
     {'CPU':'Intel Core i7','Display':'13.4in FHD+ InfinityEdge','OS':'Windows 11 Home','Battery':'12h'}),
    ('Dell',  'XPS 15 OLED',         'Laptops', 1899.99, 16, 'xps,15in,oled,windows-11-home',
     {'CPU':'Intel Core i9','Display':'15.6in 3.5K OLED','OS':'Windows 11 Home','GPU':'NVIDIA RTX 4060'}),
    ('HP',    'Spectre x360 14',     'Laptops', 1449.99, 22, '2-in-1,convertible,oled,windows-11-home',
     {'CPU':'Intel Core Ultra 7','Display':'14in OLED 2.8K','OS':'Windows 11 Home','Form Factor':'2-in-1'}),
    ('HP',    'OMEN 16 Gaming',      'Laptops', 1599.99, 25, 'gaming,rtx,16in,windows-11-home',
     {'CPU':'Intel Core i7-13700HX','Display':'16in QHD 240Hz','OS':'Windows 11 Home','GPU':'NVIDIA RTX 4070'}),
    ('Lenovo','ThinkPad X1 Carbon Gen 12','Laptops', 1899.99, 18, 'thinkpad,business,carbon,windows-11-pro',
     {'CPU':'Intel Core Ultra 7','Display':'14in 2.8K OLED','OS':'Windows 11 Pro','Battery':'15h'}),
    ('Lenovo','Yoga 9i 2-in-1',      'Laptops', 1599.99, 22, '2-in-1,oled,yoga,windows-11-home',
     {'CPU':'Intel Core Ultra 7','Display':'14in 4K OLED','OS':'Windows 11 Home','Form Factor':'2-in-1'}),
    ('Lenovo','Legion Pro 7i',       'Laptops', 2299.99, 20, 'gaming,rtx,legion,windows-11-home',
     {'CPU':'Intel Core i9-14900HX','Display':'16in WQXGA 240Hz','OS':'Windows 11 Home','GPU':'NVIDIA RTX 4080'}),
    ('ASUS',  'ROG Zephyrus G14',    'Laptops', 1799.99, 20, 'gaming,rtx,oled,zephyrus,windows-11-home',
     {'CPU':'AMD Ryzen 9','Display':'14in OLED 120Hz','OS':'Windows 11 Home','GPU':'NVIDIA RTX 4070'}),
    ('ASUS',  'Zenbook 14 OLED',     'Laptops', 1099.99, 22, 'zenbook,oled,ultraportable,windows-11-home',
     {'CPU':'Intel Core Ultra 7','Display':'14in 3K OLED','OS':'Windows 11 Home','Battery':'14h'}),
    ('Microsoft', 'Surface Laptop 5','Laptops', 1299.99, 18, 'surface,laptop,windows-11-home',
     {'CPU':'Intel Core i5','Display':'13.5in PixelSense','OS':'Windows 11 Home','Battery':'18h'}),
    ('Razer', 'Blade 14 (2024)',     'Laptops', 2199.99, 18, 'gaming,rtx,blade,small,windows-11-home',
     {'CPU':'AMD Ryzen 9','Display':'14in QHD+ 240Hz','OS':'Windows 11 Home','GPU':'NVIDIA RTX 4070'}),
    ('Acer',  'Swift Go 14 OLED',    'Laptops', 849.99, 24, 'budget,oled,swift,windows-11-home',
     {'CPU':'Intel Core Ultra 5','Display':'14in 2.8K OLED','OS':'Windows 11 Home','Battery':'12h'}),
    ('Framework', 'Laptop 13 DIY',   'Laptops', 1099.00, 0,  'modular,framework,linux,diy,windows-11-home',
     {'CPU':'Intel Core Ultra 7','Display':'13.5in 2256x1504','OS':'Windows 11 Home','Repairability':'Modular'}),
]

LAPTOP_RAM_TIERS = [(8, 1.00), (16, 1.10), (32, 1.30), (64, 1.65)]
LAPTOP_STORAGE_TIERS = [(256, 1.00), (512, 1.06), (1024, 1.15), (2048, 1.35)]
LAPTOP_COLORS_BY_BRAND = {
    'Apple':     ['Space Gray', 'Silver', 'Midnight', 'Starlight'],
    'Dell':      ['Platinum Silver', 'Graphite Black'],
    'HP':        ['Nightfall Black', 'Natural Silver', 'Pale Rose Gold'],
    'Lenovo':    ['Storm Gray', 'Cosmic Blue', 'Carbon Black'],
    'ASUS':      ['Cool Silver', 'Eclipse Gray'],
    'Microsoft': ['Platinum', 'Graphite', 'Sage', 'Sandstone'],
    'Razer':     ['Black', 'Mercury'],
    'Acer':      ['Steel Gray', 'Silver'],
    'Framework': ['Aluminum'],
}


def _build_laptop(brand, model_line, subcat, base_price, uplift, tag_csv, base_specs,
                  color, ram_gb, ram_mult, storage_gb, storage_mult, idx, pool):
    storage_str = f"{storage_gb}GB" if storage_gb < 1024 else f"{storage_gb // 1024}TB"
    name = f"{brand} {model_line} — {ram_gb}GB RAM, {storage_str}, {color}"
    price = round(base_price * ram_mult * storage_mult, 2)
    list_price = round(price * (1 + uplift / 100.0), 2) if uplift else price
    rating = round(4.0 + ((idx * 19 + ram_gb + storage_gb // 256) % 90) / 100.0, 1)
    reviews = 60 + (idx * 137) % 12500
    specs = dict(base_specs)
    specs['Brand'] = brand
    specs['Model'] = model_line
    specs['RAM'] = f'{ram_gb}GB'
    specs['Storage'] = f'{storage_str} SSD'
    specs['Color'] = color
    features = [
        f'CPU: {base_specs.get("CPU", "")}',
        f'RAM: {ram_gb}GB',
        f'Storage: {storage_str} SSD',
        f'Color: {color}',
        f'Display: {base_specs.get("Display", "")}',
        f'OS: {base_specs.get("OS", "")}',
    ]
    tags = [t.strip() for t in tag_csv.split(',') if t.strip()]
    tags.extend(['laptop', f'{ram_gb}gb', f'{storage_gb}gb' if storage_gb < 1024 else f'{storage_gb//1024}tb',
                 color.lower().split()[0]])
    img = pool[(idx * 5) % len(pool)] if pool else '/static/images/homepage/placeholder.jpg'
    gallery = [pool[(idx + j * 11) % len(pool)] for j in range(6)] if pool else []
    description = (
        f"{brand} {model_line} laptop with {ram_gb}GB RAM and {storage_str} SSD in {color}. "
        f"Powered by {base_specs.get('CPU', 'a modern processor')}. "
        f"{base_specs.get('Display', '')}."
    )
    is_deal = (idx % 4 == 0) or uplift >= 20
    is_bestseller = (ram_gb in (16, 32) and brand in ('Apple', 'Dell', 'Lenovo', 'HP'))
    return dict(
        name=name, brand=brand, category_slug='computers', subcategory=subcat,
        description=description, features=features, specs=specs,
        price=price, list_price=list_price, image=img, gallery=gallery,
        variants={'color': LAPTOP_COLORS_BY_BRAND.get(brand, [color]),
                  'ram': [f'{g}GB' for g, _ in LAPTOP_RAM_TIERS],
                  'storage': [f'{g}GB' if g < 1024 else f'{g//1024}TB' for g, _ in LAPTOP_STORAGE_TIERS]},
        stock=10 + (idx * 23 + ram_gb + storage_gb // 256) % 200,
        rating=rating, reviews=reviews,
        is_featured=(idx % 17 == 0), is_bestseller=is_bestseller, is_deal=is_deal,
        tags=tags, release_date='2024-04-01',
    )


# ---------------------------------------------------------------------------
# Insert helper
# ---------------------------------------------------------------------------

def _insert(db, Product, data):
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


# ---------------------------------------------------------------------------
# Book pass 2 — read openlib_books_r3.json and inject as additional books
# ---------------------------------------------------------------------------

def _book_pool():
    return _pool(['search_books', 'products', 'homepage'])


GENRE_PRICING = {
    'Fiction':         (12.99, 19.99, 35),
    'Science Fiction': (13.99, 21.99, 38),
    'Fantasy':         (13.99, 22.99, 36),
    'Mystery':         (12.99, 18.99, 32),
    'Thriller':        (13.99, 19.99, 32),
    'Romance':         (10.99, 16.99, 30),
    'History':         (16.99, 28.99, 40),
    'Biography':       (15.99, 26.99, 38),
    'Cookbook':        (19.99, 34.99, 42),
    'Self-Help':       (14.99, 24.99, 38),
    'Business':        (19.99, 32.99, 42),
    'Science':         (17.99, 29.99, 40),
    'Children':        (8.99,  15.99, 30),
    'Young Adult':     (11.99, 18.99, 32),
    'Poetry':          (12.99, 19.99, 30),
    'Philosophy':      (15.99, 26.99, 38),
    'Psychology':      (16.99, 26.99, 38),
    'Programming':     (29.99, 54.99, 45),
    'Art':             (24.99, 49.99, 42),
    'Travel':          (14.99, 24.99, 36),
}

PUBLISHERS_R3 = [
    'Mockingbird Press', 'Salt River Books', 'Driftwood Editions', 'Magnolia House',
    'Stargazer Books', 'Indigo Field Press', 'Brass Lantern', 'Maplewood Editions',
    'Compass Rose Books', 'Echo Mountain Press', 'Riverbend Publishing', 'Tideline Books',
]


def _build_book_r3(idx, b, pool):
    title = b['title']
    author = b.get('author') or 'Anonymous'
    genre = b.get('genre') or 'Fiction'
    year = b.get('year') or 2010
    if not isinstance(year, int) or year < 1800 or year > 2025:
        year = 1900 + (idx * 11) % 125
    edition_count = b.get('edition_count') or 30
    low, high, uplift = GENRE_PRICING.get(genre, (12.99, 22.99, 35))
    # Different prime salt so prices don't collide with seed_bulk
    price = round(low + ((idx * 41 + 7) % 1000) / 1000.0 * (high - low), 2)
    list_price = round(price * (1 + uplift / 100.0), 2)
    rating = round(3.6 + ((idx * 23 + edition_count) % 130) / 100.0, 1)
    if rating > 4.9:
        rating = 4.9
    reviews = max(20, min(48210, edition_count * 5 + (idx * 17) % 4500))
    pages = 160 + (idx * 19) % 560
    publisher = PUBLISHERS_R3[idx % len(PUBLISHERS_R3)]
    isbn = f"979-{(idx % 9) + 1}-{(idx * 13) % 9000 + 1000:04d}-{(idx * 7) % 900 + 100:03d}-{idx % 10}"
    img = pool[(idx * 3 + 1) % len(pool)] if pool else '/static/images/homepage/placeholder.jpg'
    gallery = [pool[(idx + j * 7 + 3) % len(pool)] for j in range(6)] if pool else []
    description = (
        f"{title} by {author}. A {genre.lower()} title originally published in {year}, "
        f"with {edition_count}+ editions in print. {pages} pages. "
        f"Published by {publisher}."
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
    is_deal = (idx % 6 == 0)
    is_bestseller = edition_count > 500
    is_featured = (idx % 17 == 0)
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
# Public entry
# ---------------------------------------------------------------------------

def seed_matrix(db, Product):
    """Run all R3 matrix expansions. Idempotent."""
    if Product.query.count() >= 2800:
        return 0
    added = 0

    # ----- Phones: each brand×model emits color × storage combos -----
    phone_pool = _pool(['search_electronics', 'products_amazon', 'products'])
    p_idx = 0
    for brand, model, subcat, base_price, uplift, tags, specs in PHONE_MODELS:
        colors = COLORS.get(brand, ['Black'])
        # Cap at 3 colors per model so we don't explode the catalog
        for color in colors[:3]:
            for sg, sm in STORAGE_TIERS:
                data = _build_phone(brand, model, subcat, base_price, uplift,
                                    tags, specs, color, sg, sm, p_idx, phone_pool)
                if _insert(db, Product, data):
                    added += 1
                p_idx += 1
    db.session.commit()

    # ----- Tablets: color × storage combos (cap colors per model at 2) -----
    tablet_pool = _pool(['search_electronics', 'search_laptop', 'products_amazon'])
    t_idx = 0
    for brand, model, subcat, base_price, uplift, tags, specs in TABLET_MODELS:
        colors = TABLET_COLORS.get(brand, ['Black'])
        for color in colors[:2]:
            for sg, sm in TABLET_STORAGE[:4]:  # skip 1TB tier on most
                data = _build_tablet(brand, model, subcat, base_price, uplift,
                                     tags, specs, color, sg, sm, t_idx, tablet_pool)
                if _insert(db, Product, data):
                    added += 1
                t_idx += 1
    db.session.commit()

    # ----- Laptops: pick representative (color, ram, storage) tuples
    laptop_pool = _pool(['search_laptop', 'products_amazon', 'products'])
    l_idx = 0
    for brand, line, subcat, base_price, uplift, tags, specs in LAPTOP_MODELS:
        colors = LAPTOP_COLORS_BY_BRAND.get(brand, ['Silver'])
        # Each model emits color × ram tier × storage tier matrix; sample 2 colors
        for color in colors[:2]:
            for ram_gb, ram_mult in LAPTOP_RAM_TIERS:
                for storage_gb, storage_mult in LAPTOP_STORAGE_TIERS[:3]:  # 256/512/1TB
                    # Skip nonsensical low-RAM gaming combos
                    if 'gaming' in tags and ram_gb < 16:
                        continue
                    if 'macbook' in tags and ram_gb < 16:
                        continue
                    data = _build_laptop(brand, line, subcat, base_price, uplift,
                                         tags, specs, color, ram_gb, ram_mult,
                                         storage_gb, storage_mult, l_idx, laptop_pool)
                    if _insert(db, Product, data):
                        added += 1
                    l_idx += 1
    db.session.commit()

    # ----- Books R3 pass -----
    r3_path = os.path.join(DATA_DIR, 'openlib_books_r3.json')
    if os.path.exists(r3_path):
        with open(r3_path) as f:
            r3_books = json.load(f)
        book_pool = _book_pool()
        seen_titles = set(p.name.lower() for p in
                          Product.query.filter_by(category_slug='books').all())
        for idx, b in enumerate(r3_books):
            t = (b.get('title') or '').strip()
            if not t or t.lower() in seen_titles:
                continue
            seen_titles.add(t.lower())
            data = _build_book_r3(idx, b, book_pool)
            if _insert(db, Product, data):
                added += 1
        db.session.commit()

    return added
