#!/usr/bin/env python3
"""Amazon extras seed: synthetic products + wishlist + returns + extra carts.

All functions are idempotent (early-return when target rows already exist) so
the byte-identical /reset invariant holds.
"""
import os
import re
import json
import random
from datetime import datetime, timedelta

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
IMG_DIR = os.path.join(BASE_DIR, "static", "images")
REFERENCE_DATE = datetime(2026, 4, 15)


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
        if f.lower().endswith(('.jpg', '.jpeg', '.png', '.webp')) and \
                'sprite' not in f.lower() and 'shadow' not in f.lower():
            full = os.path.join(path, f)
            try:
                if os.path.getsize(full) >= min_size:
                    out.append(f"/static/images/{subdir}/{f}")
            except OSError:
                pass
    return out


CATEGORY_POOLS = {
    'electronics': ['search_electronics', 'search_camera', 'products_amazon'],
    'computers': ['search_laptop', 'products_amazon', 'products'],
    'home': ['search_home', 'products', 'products_amazon'],
    'fashion': ['search_fashion', 'products', 'products_amazon'],
    'books': ['search_books', 'products', 'products_amazon'],
    'beauty': ['products_amazon', 'products', 'homepage'],
    'sports': ['products_amazon', 'products', 'homepage'],
    'toys': ['products_amazon', 'products', 'homepage'],
}


def _category_pool(cat):
    pool = []
    for d in CATEGORY_POOLS.get(cat, ['products_amazon', 'products']):
        pool.extend(_list_imgs(d))
    # dedupe preserving order
    seen = set()
    unique = []
    for p in pool:
        if p not in seen:
            seen.add(p)
            unique.append(p)
    return unique


def _pick_image(pool, idx):
    if not pool:
        return '/static/images/homepage/placeholder.jpg'
    return pool[idx % len(pool)]


def _pick_gallery(pool, count, start_idx):
    if not pool:
        return []
    n = len(pool)
    return [pool[(start_idx + j * 7) % n] for j in range(count)]


# ----- Product templates (synthetic Amazon-style) -----

# Books: (title, author, genre, pages, price, list_price, rating, reviews, year)
BOOKS = [
    ('The Quiet River', 'Margaret Holloway', 'Literary Fiction', 320, 16.99, 24.00, 4.4, 1820, 2023),
    ('Atomic Patterns', 'Daniel Wexler', 'Self-Help', 256, 14.99, 22.00, 4.6, 4250, 2022),
    ('Lessons from the Forge', 'Sarah Chen', 'Memoir', 288, 17.50, 25.99, 4.5, 1560, 2024),
    ('Beyond the Pale Horizon', 'Marcus Reed', 'Science Fiction', 412, 18.99, 27.00, 4.7, 3210, 2023),
    ('A Brief History of Tomorrow', 'Eleanor Hayworth', 'Nonfiction', 368, 19.99, 28.00, 4.3, 980, 2022),
    ('Whispers in the Walls', 'Vera Nakamura', 'Mystery', 304, 13.99, 19.99, 4.2, 2750, 2024),
    ('The Last Cartographer', 'Henry Whitfield', 'Historical Fiction', 448, 21.50, 29.99, 4.5, 1430, 2023),
    ('Code Without Tears', 'Priya Subramanian', 'Programming', 512, 39.99, 54.99, 4.7, 2980, 2024),
    ('The Mind Garden', 'Olivia Brookes', 'Psychology', 272, 15.99, 22.50, 4.4, 1820, 2023),
    ('Salt and Light', 'Aaron Levinson', 'Cookbook', 320, 28.99, 39.99, 4.8, 3650, 2023),
    ('Quantum Cafe', 'Reginald Park', 'Popular Science', 288, 17.99, 25.00, 4.3, 1240, 2022),
    ('Through Cedar Hollow', 'Beatrice Marsh', 'Literary Fiction', 352, 16.50, 23.00, 4.6, 2110, 2024),
    ('The Investor Almanac 2026', 'Thomas Rourke', 'Business', 416, 24.99, 34.99, 4.4, 1950, 2025),
    ('Origami for Restless Minds', 'Yuki Tanaka', 'Crafts', 192, 18.99, 24.99, 4.5, 870, 2023),
    ('Languages We Never Spoke', 'Camille Dufresne', 'Poetry', 144, 14.99, 18.99, 4.6, 540, 2024),
    ('The Empire of Salt', 'Nikolai Volkov', 'Epic Fantasy', 624, 22.99, 32.00, 4.7, 6810, 2023),
    ('Mountains Made of Glass', 'Iris Lawford', 'Young Adult', 384, 13.99, 19.00, 4.4, 4280, 2024),
    ('The Algorithm of Trust', 'Frances Ojo', 'Tech Nonfiction', 320, 21.99, 29.99, 4.3, 1130, 2023),
    ('Letters from the Lighthouse', 'Adelaide Stone', 'Historical Fiction', 368, 17.99, 24.99, 4.6, 2380, 2022),
    ('Slow Coffee', 'Kenji Murakami', 'Lifestyle', 224, 19.99, 27.99, 4.5, 1410, 2023),
    ('Field Guide to Coastal Birds', 'Ramona Velez', 'Nature', 256, 23.99, 32.99, 4.7, 760, 2023),
    ('How to Build a City', 'Lior Bensimon', 'Urban Planning', 432, 32.99, 44.00, 4.4, 540, 2024),
    ('The Antique Hour', 'Vincent Park', 'Mystery', 320, 15.99, 22.00, 4.3, 1720, 2023),
    ('Mathematics of Joy', 'Helena Sokolov', 'Mathematics', 288, 24.99, 34.00, 4.6, 880, 2024),
    ('The Garden in Winter', 'Esme Tilford', 'Gardening', 240, 22.99, 29.99, 4.5, 1140, 2023),
    ('Silicon Valley Confidential', 'Dale Pemberton', 'Business', 368, 19.99, 27.99, 4.2, 2360, 2024),
    ('Stitches of Memory', 'Constance Pruitt', 'Crafts', 208, 19.99, 26.00, 4.6, 690, 2023),
    ('The Cartoon Universe', 'Felix Brunner', 'Art', 288, 28.99, 39.99, 4.7, 1280, 2023),
    ('Watershed', 'Anya Petrescu', 'Environmental', 352, 21.50, 29.00, 4.4, 1010, 2024),
    ('The Patient Architect', 'Mateus Oliveira', 'Architecture', 384, 34.99, 49.99, 4.8, 760, 2024),
    ('Children of the Reef', 'Talia Reyes', 'Young Adult', 320, 14.50, 19.99, 4.5, 3210, 2023),
    ('A Theory of Almost Everything', 'Stanford Briggs', 'Physics', 432, 22.99, 31.00, 4.3, 1840, 2022),
    ('Bread Daily', 'Margot Vasquez', 'Cookbook', 272, 24.99, 34.00, 4.7, 2810, 2024),
    ('The Witness Window', 'Donovan Frye', 'Thriller', 384, 16.99, 23.99, 4.4, 4520, 2023),
    ('Tides of the North Sea', 'Ingrid Olsen', 'Historical Fiction', 416, 18.99, 26.99, 4.5, 1670, 2024),
    ('The Mindful Manager', 'Akira Yoshimoto', 'Business', 256, 17.99, 24.99, 4.3, 1450, 2023),
    ('Cinder Roads', 'Owen Whitlock', 'Dystopian', 352, 16.50, 22.99, 4.6, 2310, 2024),
    ('Lullabies for Lost Stars', 'Sophia Aaltonen', 'Poetry', 168, 13.99, 18.00, 4.7, 410, 2023),
    ('The Builder of Bridges', 'Jamal Hartwell', 'Biography', 432, 24.99, 34.99, 4.5, 980, 2023),
    ('Microbes and Us', 'Linnea Carlsson', 'Biology', 304, 19.99, 27.50, 4.4, 720, 2024),
    ('Studio Living', 'Penelope Wren', 'Interior Design', 240, 27.99, 36.99, 4.6, 1180, 2023),
    ('Rain in the Hangar', 'Bartholomew Voss', 'Mystery', 336, 15.99, 21.99, 4.3, 1280, 2024),
    ('The Edge of the Map', 'Niamh O\'Leary', 'Adventure', 368, 17.50, 24.00, 4.5, 2050, 2023),
    ('Sleep Smart', 'Dr. Yara Halevi', 'Health', 288, 18.99, 25.99, 4.4, 3210, 2024),
    ('Coastal Watercolors', 'Maxim Bauer', 'Art', 224, 26.99, 36.00, 4.8, 540, 2023),
    ('Decoding the Cell', 'Dr. Felix Adeyemi', 'Biology', 416, 32.99, 44.00, 4.5, 660, 2024),
    ('Letters to a Young Engineer', 'Imelda Santos', 'Engineering', 256, 18.99, 25.99, 4.6, 1110, 2024),
    ('The Glasshouse Affair', 'Wesley Cromwell', 'Historical Mystery', 384, 17.99, 24.99, 4.4, 1870, 2023),
    ('The Whole Vegetable', 'Hana Greenfield', 'Cookbook', 304, 26.99, 36.00, 4.7, 1480, 2023),
    ('Skipping Stones', 'Dolores McAllister', 'Childrens', 96, 9.99, 14.99, 4.8, 2380, 2024),
    ('Tomorrow\'s Atlas', 'Quentin Ashford', 'Geography', 320, 29.99, 39.99, 4.5, 540, 2024),
    ('Concrete Forests', 'Ren Sato', 'Photography', 288, 38.99, 49.99, 4.9, 380, 2023),
    ('The Vanishing Lake', 'Cordelia Vance', 'Environmental Fiction', 352, 16.99, 23.00, 4.4, 1620, 2024),
    ('Hands of the Maker', 'Eitan Bar-Levi', 'Crafts', 240, 22.99, 29.99, 4.6, 720, 2023),
    ('A Brief Theory of Sleep', 'Lydia Brookhart', 'Science', 272, 18.99, 25.99, 4.3, 1340, 2024),
    ('The Lost Diner', 'Robbie Nguyen', 'Memoir', 304, 17.50, 23.99, 4.5, 990, 2023),
    ('Riverbend Years', 'Tabitha Sinclair', 'Family Saga', 528, 19.99, 27.99, 4.6, 2150, 2022),
    ('Welding the Future', 'Carl Ostrowski', 'Engineering', 352, 28.99, 39.00, 4.4, 410, 2024),
    ('The Spice Routes', 'Devika Rao', 'Travel', 336, 24.99, 33.00, 4.7, 870, 2023),
    ('In Search of Quiet', 'Erik Andersson', 'Philosophy', 288, 19.99, 26.99, 4.5, 1240, 2024),
    ('The Sketchbook Project', 'Mae Lin', 'Art Instruction', 240, 24.99, 32.99, 4.7, 1380, 2023),
    ('When the Tide Turns', 'Joaquin Salazar', 'Literary Fiction', 384, 18.50, 25.99, 4.4, 1670, 2024),
    ('Field Notes on Friendship', 'Hilda Bremer', 'Essays', 224, 16.99, 22.99, 4.6, 940, 2023),
    ('The Patent Office', 'Stuart Greaves', 'Historical', 416, 21.99, 28.99, 4.4, 720, 2023),
]


# Electronics: (name, brand, subcategory, price, list_price, rating, reviews, specs_dict_json_str, tags_csv)
ELECTRONICS = [
    ('Anker PowerCore 20000 USB-C Power Bank', 'Anker', 'Power Banks', 49.99, 69.99, 4.6, 8520, {'Capacity':'20000mAh','Ports':'1 USB-C, 2 USB-A','Output':'20W PD','Weight':'12.1 oz','Color':'Black'}, 'portable,fast-charging,usb-c,travel'),
    ('Anker 737 Power Bank 24000mAh 140W', 'Anker', 'Power Banks', 149.99, 179.99, 4.7, 3210, {'Capacity':'24000mAh','Output':'140W','Ports':'2 USB-C, 1 USB-A','Color':'Black','Display':'Smart digital display'}, 'high-capacity,140w,smart-display,laptop-charging'),
    ('Anker Soundcore Liberty 4 NC Earbuds', 'Anker', 'Headphones', 79.99, 99.99, 4.4, 5680, {'Battery':'Up to 10h','ANC':'Adaptive','Driver':'11mm','Bluetooth':'5.3','Color':'Black'}, 'anc,bluetooth,earbuds,wireless'),
    ('JBL Charge 5 Portable Bluetooth Speaker', 'JBL', 'Speakers', 149.95, 179.95, 4.7, 12300, {'Battery':'20h','Waterproof':'IP67','Bluetooth':'5.1','Weight':'2.1 lb','Color':'Black'}, 'portable,waterproof,ip67,party'),
    ('Bose QuietComfort Ultra Headphones', 'Bose', 'Headphones', 379.00, 429.00, 4.6, 4210, {'Battery':'24h','ANC':'World-class','Driver':'35mm','Bluetooth':'5.3','Color':'Black'}, 'anc,premium,wireless,over-ear'),
    ('Sennheiser HD 660S2 Audiophile Headphones', 'Sennheiser', 'Headphones', 599.95, 699.95, 4.8, 720, {'Impedance':'300 ohm','Driver':'42mm','Weight':'9.2 oz','Connector':'6.3mm,4.4mm','Type':'Open-back'}, 'audiophile,wired,open-back,studio'),
    ('Logitech G Pro X Superlight 2 Wireless Mouse', 'Logitech', 'Computer Accessories', 159.99, 179.99, 4.7, 3820, {'DPI':'32000','Battery':'95h','Weight':'2.12 oz','Connectivity':'Lightspeed','Color':'Black'}, 'gaming,wireless,lightweight,esports'),
    ('Razer DeathAdder V3 Pro Wireless', 'Razer', 'Computer Accessories', 149.99, 159.99, 4.6, 4710, {'DPI':'30000','Battery':'90h','Weight':'2.22 oz','Switches':'Optical Gen-3','Color':'Black'}, 'gaming,wireless,ergonomic'),
    ('Keychron Q1 Pro QMK Wireless Mechanical Keyboard', 'Keychron', 'Computer Accessories', 199.00, 219.00, 4.7, 1820, {'Layout':'75%','Switches':'Gateron Brown','Battery':'1000h','Connectivity':'Bluetooth,Wired','Color':'Carbon Black'}, 'mechanical,qmk,wireless,hot-swap'),
    ('Glorious GMMK 3 Pro 75% Keyboard', 'Glorious', 'Computer Accessories', 169.99, 199.99, 4.5, 980, {'Layout':'75%','Switches':'Fox V2','Connectivity':'Wired','Color':'Onyx'}, 'mechanical,hot-swap,gasket-mount'),
    ('SteelSeries Arctis Nova Pro Wireless Headset', 'SteelSeries', 'Headphones', 329.99, 349.99, 4.5, 2310, {'Battery':'Swappable','ANC':'Yes','Driver':'40mm','Connectivity':'2.4GHz,Bluetooth','Color':'Black'}, 'gaming,wireless,anc,hot-swap-battery'),
    ('Sony WF-1000XM5 Wireless Noise Canceling Earbuds', 'Sony', 'Headphones', 299.99, 329.99, 4.4, 5230, {'Battery':'8h+16h case','ANC':'Industry-leading','Driver':'8.4mm','Bluetooth':'5.3','Color':'Black'}, 'anc,premium,wireless,earbuds'),
    ('Sony LinkBuds S Truly Wireless Earbuds', 'Sony', 'Headphones', 149.99, 199.99, 4.3, 3120, {'Battery':'6h+14h case','ANC':'Yes','Bluetooth':'5.2','Color':'White','Weight':'0.16 oz each'}, 'lightweight,anc,wireless,everyday'),
    ('Bose SoundLink Flex Bluetooth Speaker', 'Bose', 'Speakers', 149.00, 159.00, 4.7, 8910, {'Battery':'12h','Waterproof':'IP67','Weight':'1.3 lb','Bluetooth':'4.2','Color':'Stone Blue'}, 'portable,waterproof,ip67'),
    ('Sonos Era 100 Wireless Speaker', 'Sonos', 'Speakers', 249.00, 279.00, 4.6, 4120, {'Connectivity':'WiFi, Bluetooth, USB-C','Voice':'Sonos Voice, Alexa','Color':'Black','Power':'2x tweeters + 1 mid-woofer'}, 'smart-speaker,wifi,multi-room'),
    ('Sonos Move 2 Portable Smart Speaker', 'Sonos', 'Speakers', 449.00, 499.00, 4.7, 1820, {'Battery':'24h','Waterproof':'IP56','Connectivity':'WiFi, Bluetooth','Weight':'6.6 lb','Color':'Olive'}, 'portable,wifi,bluetooth,outdoor'),
    ('Apple HomePod (2nd Generation)', 'Apple', 'Smart Home', 299.00, 299.00, 4.5, 3650, {'Voice':'Siri','Connectivity':'WiFi, Bluetooth 5.0','Color':'Midnight','Power':'High-excursion woofer + tweeter array'}, 'smart-speaker,siri,homekit'),
    ('Google Nest Hub Max', 'Google', 'Smart Home', 229.00, 249.00, 4.5, 7820, {'Display':'10in HD','Camera':'6.5MP','Voice':'Google Assistant','Connectivity':'WiFi, Bluetooth, Thread','Color':'Charcoal'}, 'smart-display,google-assistant,video-call'),
    ('Ring Video Doorbell Pro 2', 'Ring', 'Smart Home', 229.99, 249.99, 4.5, 12450, {'Resolution':'1536p HD+','Field of View':'150° H, 150° V','Power':'Hardwired','Color':'Satin Nickel'}, 'video-doorbell,hardwired,1536p'),
    ('Ring Indoor Cam (2nd Gen) Plug-In', 'Ring', 'Smart Home', 59.99, 69.99, 4.4, 9810, {'Resolution':'1080p HD','Field of View':'143° H, 80° V','Power':'Plug-in','Color':'White'}, 'indoor-camera,1080p,plug-in'),
    ('Arlo Pro 5S 2K Wireless Security Camera (3-pack)', 'Arlo', 'Smart Home', 549.99, 649.99, 4.6, 1280, {'Resolution':'2K','Battery':'Rechargeable, 6 months','Field of View':'160°','Color':'White'}, 'wireless-camera,2k,outdoor,battery'),
    ('Eufy Security S330 4K Wireless Cam', 'Eufy', 'Smart Home', 179.99, 219.99, 4.5, 2380, {'Resolution':'4K','Battery':'Solar-rechargeable','Storage':'Local + Cloud','Color':'White'}, 'wireless-camera,4k,solar,local-storage'),
    ('Philips Hue White and Color Ambiance Starter Kit', 'Philips Hue', 'Smart Home', 199.99, 229.99, 4.7, 6890, {'Bulbs':'4x A19','Hub':'Included','Connectivity':'Zigbee, Bluetooth','Color':'Multicolor + White'}, 'smart-bulb,zigbee,color,starter-kit'),
    ('LIFX Color A19 Smart Bulb (2-pack)', 'LIFX', 'Smart Home', 79.98, 99.98, 4.4, 2810, {'Bulbs':'2x A19','Connectivity':'WiFi','Color':'16 million','Hub':'Not required'}, 'smart-bulb,wifi,no-hub,color'),
    ('TP-Link Kasa Smart Plug HS103P4 4-pack', 'TP-Link', 'Smart Home', 28.99, 39.99, 4.7, 38120, {'Pack':'4','Connectivity':'WiFi','Voice':'Alexa, Google','Color':'White'}, 'smart-plug,wifi,4-pack,budget'),
    ('Wyze Cam v3 1080p Indoor/Outdoor Camera', 'Wyze', 'Smart Home', 35.98, 45.98, 4.5, 24680, {'Resolution':'1080p HD','Field of View':'130°','Power':'Wired','Color':'White'}, 'budget,indoor-outdoor,1080p,wired'),
    ('Apple AirTag (4-pack)', 'Apple', 'Smart Home', 99.00, 99.00, 4.8, 18920, {'Pack':'4','Battery':'CR2032, 1 year','Connectivity':'Bluetooth, UWB','Color':'White'}, 'tracker,find-my,uwb,4-pack'),
    ('Tile Pro (2024) Bluetooth Tracker', 'Tile', 'Smart Home', 34.99, 39.99, 4.4, 7120, {'Range':'400 ft','Battery':'CR2032, 1 year (replaceable)','Connectivity':'Bluetooth','Color':'Black'}, 'tracker,replaceable-battery,400ft'),
    ('Garmin Forerunner 165 GPS Running Watch', 'Garmin', 'Wearables', 249.99, 279.99, 4.6, 1820, {'Display':'AMOLED','Battery':'Up to 11 days','GPS':'Multi-band','Water Rating':'5 ATM','Color':'Black'}, 'gps-watch,running,amoled,multi-band'),
    ('Garmin Fenix 7 Pro Solar Multisport Watch', 'Garmin', 'Wearables', 799.99, 899.99, 4.7, 980, {'Display':'1.3in MIP + Solar','Battery':'22 days w/ solar','GPS':'Multi-band','Water Rating':'10 ATM','Color':'Slate Gray'}, 'gps-watch,solar,multisport,rugged'),
    ('Fitbit Charge 6 Fitness Tracker', 'Fitbit', 'Wearables', 159.95, 179.95, 4.3, 5820, {'Display':'AMOLED','Battery':'7 days','GPS':'Built-in','Water Rating':'50m','Color':'Obsidian'}, 'fitness-tracker,gps,heart-rate'),
    ('Apple Watch Ultra 2', 'Apple', 'Wearables', 799.00, 799.00, 4.8, 6230, {'Display':'49mm Always-On Retina','Battery':'36h (72h low power)','GPS':'Precision dual-frequency','Water Rating':'100m','Color':'Titanium'}, 'smartwatch,titanium,rugged,multi-band-gps'),
    ('Samsung Galaxy Watch6 Classic 47mm', 'Samsung', 'Wearables', 429.99, 499.99, 4.4, 3120, {'Display':'1.5in Super AMOLED','Battery':'40h','GPS':'Yes','Water Rating':'5 ATM','Color':'Silver'}, 'smartwatch,wear-os,rotating-bezel'),
    ('Polar Vantage V3 Multisport Watch', 'Polar', 'Wearables', 599.95, 649.95, 4.5, 410, {'Display':'AMOLED','Battery':'8 days','GPS':'Dual-band','ECG':'Yes','Color':'Sunrise Apricot'}, 'multisport,gps,ecg,dual-band'),
    ('GoPro HERO12 Black 5.3K Action Camera', 'GoPro', 'Cameras', 349.00, 399.00, 4.6, 4980, {'Resolution':'5.3K60','Stabilization':'HyperSmooth 6.0','Waterproof':'33 ft','Battery':'Enduro','Color':'Black'}, 'action-camera,5k,waterproof,hypersmooth'),
    ('DJI Osmo Pocket 3 Vlog Camera', 'DJI', 'Cameras', 519.00, 549.00, 4.7, 2310, {'Sensor':'1-inch CMOS','Stabilization':'3-axis gimbal','Display':'2-inch rotatable','Video':'4K/120fps','Color':'Black'}, 'vlog,gimbal,4k,1-inch-sensor'),
    ('Sony ZV-1F Vlog Camera', 'Sony', 'Cameras', 499.99, 549.99, 4.5, 1280, {'Sensor':'1-inch','Lens':'20mm F2','Video':'4K30','Display':'Flip-out','Color':'White'}, 'vlog,1-inch,wide-lens,4k'),
    ('Canon EOS R10 Mirrorless Camera Body', 'Canon', 'Cameras', 879.99, 999.99, 4.7, 980, {'Sensor':'APS-C 24.2MP','Video':'4K60','AF':'Dual Pixel CMOS AF II','Mount':'RF','Color':'Black'}, 'mirrorless,aps-c,4k60,beginner-friendly'),
    ('Insta360 X4 8K 360 Camera', 'Insta360', 'Cameras', 499.99, 549.99, 4.6, 1820, {'Resolution':'8K30 360','Battery':'135 min','Waterproof':'33 ft','Display':'2.5in touch','Color':'Black'}, '360,8k,waterproof,immersive'),
    ('Blink Outdoor 4 Wireless Camera (3-pack)', 'Blink', 'Smart Home', 159.99, 219.99, 4.5, 4810, {'Resolution':'1080p HD','Battery':'2 years (2 AA)','Field of View':'143°','Color':'Black'}, 'wireless-camera,battery,2-year,3-pack'),
    ('Roku Streaming Stick 4K', 'Roku', 'Streaming', 39.99, 49.99, 4.7, 28910, {'Resolution':'4K HDR Dolby Vision','Voice Remote':'Yes','WiFi':'Dual-band','Color':'Black'}, 'streaming,4k,hdr,voice-remote'),
    ('Roku Ultra 4K HDR Streaming Player', 'Roku', 'Streaming', 89.99, 99.99, 4.7, 6820, {'Resolution':'4K HDR10+ Dolby Vision','Ethernet':'Yes','WiFi 6':'Yes','Voice Remote Pro':'Included'}, 'streaming,4k,ethernet,wifi6'),
    ('Amazon Fire TV Stick 4K Max (2nd Gen)', 'Amazon', 'Streaming', 49.99, 59.99, 4.7, 41200, {'Resolution':'4K HDR','WiFi 6E':'Yes','Storage':'16GB','Voice Remote':'Alexa Pro'}, 'streaming,4k,wifi6e,alexa'),
    ('Chromecast with Google TV (4K)', 'Google', 'Streaming', 49.99, 59.99, 4.6, 14820, {'Resolution':'4K HDR Dolby Vision','OS':'Google TV','Remote':'Included','Color':'Snow'}, 'streaming,4k,google-tv'),
    ('Apple TV 4K (3rd Generation)', 'Apple', 'Streaming', 129.00, 149.00, 4.8, 5890, {'Resolution':'4K HDR10+ Dolby Vision','Chip':'A15 Bionic','Storage':'64GB','Remote':'Siri'}, 'streaming,4k,a15,siri-remote'),
    ('Beats Studio Pro Wireless Headphones', 'Beats', 'Headphones', 349.99, 399.99, 4.5, 2810, {'Battery':'40h','ANC':'Adaptive','Bluetooth':'5.3','Color':'Deep Brown'}, 'anc,wireless,over-ear,beats'),
    ('Beats Solo 4 Wireless On-Ear Headphones', 'Beats', 'Headphones', 199.99, 229.99, 4.4, 3120, {'Battery':'50h','Bluetooth':'5.3','Weight':'7.6 oz','Color':'Matte Black'}, 'wireless,on-ear,50h-battery'),
    ('Marshall Emberton II Portable Speaker', 'Marshall', 'Speakers', 169.99, 199.99, 4.6, 4520, {'Battery':'30h','Waterproof':'IP67','Bluetooth':'5.1','Color':'Black & Brass'}, 'portable,waterproof,30h,marshall'),
    ('Anker Soundcore Motion+ Hi-Res Speaker', 'Anker', 'Speakers', 99.99, 129.99, 4.6, 8910, {'Battery':'12h','Waterproof':'IPX7','Bluetooth':'5.0','Power':'30W','Color':'Black'}, 'portable,hi-res,ipx7,budget'),
    ('Anker Eufy RoboVac 11S Max Robot Vacuum', 'Anker', 'Smart Home', 159.99, 229.99, 4.4, 24820, {'Suction':'2000Pa','Height':'2.85in','Battery':'100 min','Bin':'0.6L','Color':'Black'}, 'robot-vacuum,thin,quiet,budget'),
]


# Computers: (name, brand, subcategory, price, list_price, rating, reviews, specs, tags)
COMPUTERS = [
    ('Dell XPS 13 Plus 9320 Laptop (i7, 16GB, 1TB)', 'Dell', 'Laptops', 1499.00, 1799.00, 4.4, 1820, {'CPU':'Intel Core i7-1360P','RAM':'16GB LPDDR5','Storage':'1TB SSD','Display':'13.4in OLED 3.5K','OS':'Windows 11 Home','Weight':'2.73 lb','Color':'Platinum'}, 'ultrabook,oled,16gb,1tb,windows-11-home'),
    ('Dell XPS 15 9530 (i9, 32GB, 1TB, RTX 4060)', 'Dell', 'Laptops', 2599.00, 2999.00, 4.5, 980, {'CPU':'Intel Core i9-13900H','RAM':'32GB DDR5','Storage':'1TB SSD','GPU':'NVIDIA RTX 4060 8GB','Display':'15.6in OLED 3.5K Touch','OS':'Windows 11 Pro','Color':'Platinum Silver'}, 'creator,oled,rtx4060,32gb,windows-11-pro'),
    ('Lenovo ThinkPad X1 Carbon Gen 11 (i7, 16GB, 512GB)', 'Lenovo', 'Laptops', 1849.00, 2299.00, 4.6, 1240, {'CPU':'Intel Core i7-1365U vPro','RAM':'16GB LPDDR5','Storage':'512GB SSD','Display':'14in WUXGA IPS','OS':'Windows 11 Pro','Weight':'2.48 lb','Color':'Deep Black'}, 'business,thinkpad,lightweight,windows-11-pro'),
    ('Lenovo Legion 5i Pro Gaming Laptop (i9, 32GB, RTX 4070)', 'Lenovo', 'Laptops', 1799.99, 2099.99, 4.5, 1860, {'CPU':'Intel Core i9-13900HX','RAM':'32GB DDR5','Storage':'1TB SSD','GPU':'NVIDIA RTX 4070 8GB','Display':'16in WQXGA 240Hz','OS':'Windows 11 Home','Color':'Onyx Gray'}, 'gaming,rtx4070,32gb,240hz'),
    ('ASUS ROG Zephyrus G14 (R9, 32GB, RTX 4070)', 'ASUS', 'Laptops', 1899.00, 2199.00, 4.6, 2410, {'CPU':'AMD Ryzen 9 7940HS','RAM':'32GB DDR5','Storage':'1TB SSD','GPU':'NVIDIA RTX 4070 8GB','Display':'14in QHD+ 165Hz','OS':'Windows 11 Home','Color':'Eclipse Gray'}, 'gaming,compact,rtx4070,ryzen-9'),
    ('ASUS ROG Strix G16 (i9, 16GB, RTX 4060)', 'ASUS', 'Laptops', 1299.99, 1499.99, 4.4, 1620, {'CPU':'Intel Core i9-14900HX','RAM':'16GB DDR5','Storage':'1TB SSD','GPU':'NVIDIA RTX 4060 8GB','Display':'16in WUXGA 165Hz','OS':'Windows 11 Home','Color':'Eclipse Gray'}, 'gaming,rtx4060,16-inch,165hz'),
    ('Apple MacBook Pro 14" M3 Pro (18GB, 512GB)', 'Apple', 'Laptops', 1999.00, 1999.00, 4.8, 3210, {'CPU':'Apple M3 Pro 11-core','RAM':'18GB unified','Storage':'512GB SSD','Display':'14.2in Liquid Retina XDR','OS':'macOS','Weight':'3.5 lb','Color':'Space Black'}, 'macbook,m3-pro,liquid-retina,xdr'),
    ('Apple MacBook Pro 16" M3 Max (36GB, 1TB)', 'Apple', 'Laptops', 3499.00, 3499.00, 4.9, 1820, {'CPU':'Apple M3 Max 14-core','RAM':'36GB unified','Storage':'1TB SSD','Display':'16.2in Liquid Retina XDR','OS':'macOS','Weight':'4.7 lb','Color':'Space Black'}, 'macbook-pro,m3-max,creator,16-inch'),
    ('Microsoft Surface Laptop 5 13.5" (i5, 8GB, 256GB)', 'Microsoft', 'Laptops', 999.99, 1299.99, 4.5, 2480, {'CPU':'Intel Core i5-1235U','RAM':'8GB LPDDR5x','Storage':'256GB SSD','Display':'13.5in PixelSense Touch','OS':'Windows 11 Home','Weight':'2.8 lb','Color':'Platinum'}, 'surface,touchscreen,windows-11-home'),
    ('Microsoft Surface Laptop Studio 2 (i7, 16GB, RTX 4050)', 'Microsoft', 'Laptops', 2399.99, 2499.99, 4.4, 620, {'CPU':'Intel Core i7-13700H','RAM':'16GB','Storage':'512GB SSD','GPU':'NVIDIA RTX 4050','Display':'14.4in 120Hz Touch','OS':'Windows 11 Pro','Color':'Platinum'}, 'creator,convertible,rtx4050,touchscreen'),
    ('HP Spectre x360 14" (i7, 16GB, OLED Touch)', 'HP', 'Laptops', 1599.99, 1799.99, 4.3, 1410, {'CPU':'Intel Core Ultra 7 155H','RAM':'16GB LPDDR5x','Storage':'1TB SSD','Display':'14in OLED 2.8K Touch','OS':'Windows 11 Home','Weight':'3.19 lb','Color':'Nightfall Black'}, '2-in-1,oled,convertible,touchscreen'),
    ('HP OMEN 17 Gaming Laptop (i9, 32GB, RTX 4080)', 'HP', 'Laptops', 2599.99, 2999.99, 4.4, 980, {'CPU':'Intel Core i9-13900HX','RAM':'32GB DDR5','Storage':'2TB SSD','GPU':'NVIDIA RTX 4080 12GB','Display':'17.3in QHD 240Hz','OS':'Windows 11 Home','Color':'Shadow Black'}, 'gaming,17-inch,rtx4080,240hz'),
    ('Acer Swift Go 14 OLED (i7, 16GB, 1TB)', 'Acer', 'Laptops', 899.99, 1099.99, 4.3, 1820, {'CPU':'Intel Core i7-13700H','RAM':'16GB LPDDR5','Storage':'1TB SSD','Display':'14in 2.8K OLED','OS':'Windows 11 Home','Weight':'2.76 lb','Color':'Pure Silver'}, 'budget-ultrabook,oled,16gb'),
    ('Acer Predator Helios 16 (i9, 16GB, RTX 4070)', 'Acer', 'Laptops', 1599.99, 1799.99, 4.5, 1240, {'CPU':'Intel Core i9-13900HX','RAM':'16GB DDR5','Storage':'1TB SSD','GPU':'NVIDIA RTX 4070 8GB','Display':'16in WQXGA 240Hz','OS':'Windows 11 Home','Color':'Abyssal Black'}, 'gaming,rtx4070,16gb,240hz'),
    ('Framework Laptop 13 DIY Edition AMD Ryzen 7', 'Framework', 'Laptops', 1399.00, 1499.00, 4.7, 920, {'CPU':'AMD Ryzen 7 7840U','RAM':'BYO (DDR5)','Storage':'BYO','Display':'13.5in 2256x1504 Matte','OS':'Linux / Windows','Weight':'2.87 lb','Color':'Aluminum'}, 'modular,diy,repairable,ryzen'),
    ('System76 Lemur Pro Linux Laptop (i7, 16GB, 1TB)', 'System76', 'Laptops', 1599.00, 1699.00, 4.6, 280, {'CPU':'Intel Core i7-1355U','RAM':'16GB DDR4','Storage':'1TB NVMe','Display':'14.1in 1080p Matte','OS':'Pop!_OS','Weight':'2.2 lb','Color':'Black'}, 'linux,pop-os,ultrabook,16gb'),
    ('CyberPowerPC Gamer Master Desktop (R7, 16GB, RTX 4060)', 'CyberPowerPC', 'Desktops', 1199.99, 1399.99, 4.4, 3820, {'CPU':'AMD Ryzen 7 5700G','RAM':'16GB DDR4','Storage':'1TB NVMe SSD','GPU':'NVIDIA RTX 4060 8GB','OS':'Windows 11 Home','Color':'Black'}, 'gaming-desktop,rtx4060,ryzen,1tb,windows-11-home'),
    ('Skytech Shadow 3.0 Gaming PC (R5, 16GB, RTX 4060)', 'Skytech', 'Desktops', 1099.99, 1299.99, 4.5, 4280, {'CPU':'AMD Ryzen 5 7600','RAM':'16GB DDR5','Storage':'1TB NVMe SSD','GPU':'NVIDIA RTX 4060 8GB','OS':'Windows 11 Home','Color':'Black'}, 'gaming-desktop,rtx4060,1tb,windows-11-home'),
    ('Alienware Aurora R16 (i7, 32GB, RTX 4070)', 'Alienware', 'Desktops', 2199.99, 2499.99, 4.4, 820, {'CPU':'Intel Core i7-14700F','RAM':'32GB DDR5','Storage':'1TB NVMe SSD','GPU':'NVIDIA RTX 4070 12GB','OS':'Windows 11 Home','Color':'Dark Side of the Moon'}, 'gaming-desktop,alienware,rtx4070,32gb'),
    ('Apple Mac mini M2 (8GB, 256GB)', 'Apple', 'Desktops', 599.00, 599.00, 4.8, 4810, {'CPU':'Apple M2 8-core','RAM':'8GB unified','Storage':'256GB SSD','Ports':'2x USB-C/TB4, HDMI, 2x USB-A, Ethernet','OS':'macOS','Color':'Silver'}, 'mac-mini,m2,compact,desktop'),
    ('Apple Mac Studio M2 Max (32GB, 512GB)', 'Apple', 'Desktops', 1999.00, 1999.00, 4.8, 1240, {'CPU':'Apple M2 Max 12-core','RAM':'32GB unified','Storage':'512GB SSD','Ports':'4x TB4, 2x USB-A, HDMI, 10GbE','OS':'macOS','Color':'Silver'}, 'mac-studio,m2-max,creator,desktop'),
    ('Intel NUC 13 Pro Kit (i7)', 'Intel', 'Desktops', 829.00, 899.00, 4.5, 720, {'CPU':'Intel Core i7-1360P','RAM':'BYO (SODIMM)','Storage':'BYO (M.2)','Form Factor':'Ultra-compact','OS':'BYO','Color':'Black'}, 'mini-pc,nuc,byo,compact'),
    ('Samsung 49" Odyssey OLED G9 Gaming Monitor', 'Samsung', 'Monitors', 1799.99, 2199.99, 4.6, 1280, {'Size':'49in DQHD','Panel':'OLED','Refresh Rate':'240Hz','Response':'0.03ms','HDR':'HDR True Black 400','Color':'Silver'}, 'monitor,oled,49-inch,240hz,ultrawide'),
    ('LG 27GP950-B 4K UltraGear Gaming Monitor', 'LG', 'Monitors', 749.99, 899.99, 4.5, 4820, {'Size':'27in 4K','Panel':'Nano IPS','Refresh Rate':'144Hz (160Hz OC)','Response':'1ms','HDR':'HDR600','Color':'Black'}, 'monitor,4k,144hz,ips'),
    ('Dell UltraSharp U2723QE 27" 4K Monitor', 'Dell', 'Monitors', 599.99, 749.99, 4.6, 3210, {'Size':'27in 4K','Panel':'IPS Black','Refresh Rate':'60Hz','Connectivity':'USB-C 90W, HDMI, DP, RJ45','Color':'Silver'}, 'monitor,4k,usb-c,docking'),
    ('ASUS ProArt PA32UCG-K 32" 4K Mini-LED', 'ASUS', 'Monitors', 4999.00, 5499.00, 4.7, 280, {'Size':'32in 4K','Panel':'Mini-LED','Refresh Rate':'120Hz','HDR':'HDR1400 / DolbyVision','Color Gamut':'97% DCI-P3','Color':'Black'}, 'monitor,4k,mini-led,creator,reference'),
    ('BenQ ScreenBar Halo USB Monitor Light', 'BenQ', 'Monitors', 199.00, 219.00, 4.7, 3820, {'Power':'USB-C','Adjustment':'Auto-dim','Mount':'Clip','Color':'Black'}, 'monitor-light,usb-c,wireless-remote'),
    ('Samsung T7 Shield 2TB Portable SSD', 'Samsung', 'Storage', 159.99, 219.99, 4.8, 12820, {'Capacity':'2TB','Interface':'USB-C 3.2 Gen 2','Speed':'1050 MB/s','Rugged':'IP65, drop-resistant 9.8 ft','Color':'Beige'}, 'portable-ssd,2tb,rugged,usb-c'),
    ('SanDisk Extreme Pro 1TB Portable SSD', 'SanDisk', 'Storage', 109.99, 169.99, 4.7, 28910, {'Capacity':'1TB','Interface':'USB-C 3.2 Gen 2','Speed':'2000 MB/s','Rugged':'IP55','Color':'Black'}, 'portable-ssd,1tb,fast,rugged'),
    ('Samsung 990 Pro 2TB NVMe SSD', 'Samsung', 'Storage', 169.99, 229.99, 4.8, 8920, {'Capacity':'2TB','Interface':'PCIe 4.0 NVMe','Read':'7450 MB/s','Write':'6900 MB/s','Form Factor':'M.2 2280'}, 'nvme,pcie4,2tb,internal'),
    ('WD Black SN850X 4TB NVMe SSD', 'Western Digital', 'Storage', 309.99, 399.99, 4.7, 5210, {'Capacity':'4TB','Interface':'PCIe 4.0 NVMe','Read':'7300 MB/s','Form Factor':'M.2 2280'}, 'nvme,pcie4,4tb,gaming'),
    ('Seagate Expansion 8TB External Hard Drive', 'Seagate', 'Storage', 159.99, 199.99, 4.6, 12480, {'Capacity':'8TB','Interface':'USB 3.0','Form Factor':'3.5in desktop','Power':'External adapter','Color':'Black'}, 'external-hdd,8tb,desktop,usb3'),
    ('Anker 7-in-1 USB-C Hub PowerExpand+', 'Anker', 'Computer Accessories', 39.99, 49.99, 4.6, 38120, {'Ports':'4K HDMI, 100W PD, SD/microSD, 2x USB-A','Compatibility':'MacBook, iPad, Surface','Color':'Gray'}, 'usb-c-hub,4k-hdmi,100w-pd'),
    ('CalDigit TS4 Thunderbolt 4 Dock', 'CalDigit', 'Computer Accessories', 399.99, 449.99, 4.7, 2810, {'Ports':'18 total','Power':'98W charging','Compatibility':'TB4, USB4, USB-C','Color':'Space Gray'}, 'dock,thunderbolt-4,18-port,creator'),
    ('NVIDIA GeForce RTX 4070 Founders Edition', 'NVIDIA', 'Computer Components', 599.99, 599.99, 4.7, 1240, {'GPU':'RTX 4070','Memory':'12GB GDDR6X','Boost Clock':'2.48 GHz','Power':'200W','Connectors':'1x 16-pin'}, 'gpu,rtx4070,12gb,founders'),
    ('AMD Ryzen 7 7800X3D 8-Core CPU', 'AMD', 'Computer Components', 449.99, 499.99, 4.8, 3120, {'Cores':'8','Threads':'16','Base Clock':'4.2 GHz','Boost':'5.0 GHz','TDP':'120W','Socket':'AM5'}, 'cpu,ryzen-7,x3d,gaming'),
    ('Corsair Vengeance 32GB (2x16GB) DDR5-6000', 'Corsair', 'Computer Components', 119.99, 159.99, 4.7, 8820, {'Capacity':'32GB (2x16GB)','Speed':'DDR5-6000','Latency':'CL30','Color':'Black'}, 'ram,ddr5,32gb,desktop'),
    ('Logitech MX Keys S Wireless Keyboard', 'Logitech', 'Computer Accessories', 109.99, 119.99, 4.6, 6820, {'Layout':'Full-size','Backlight':'Smart illumination','Battery':'10 days w/ backlight','Connectivity':'Bluetooth, Logi Bolt','Color':'Graphite'}, 'wireless,backlit,multi-device,office'),
    ('Apple Magic Mouse (2024) USB-C', 'Apple', 'Computer Accessories', 99.00, 99.00, 4.2, 4820, {'Connectivity':'Bluetooth','Charging':'USB-C','Battery':'1 month','Surface':'Multi-Touch','Color':'White'}, 'magic-mouse,usb-c,mac,wireless'),
    ('Apple Magic Keyboard (2024) Touch ID, USB-C', 'Apple', 'Computer Accessories', 129.00, 129.00, 4.6, 3210, {'Layout':'Full-size','Backlight':'No','Battery':'1 month','Touch ID':'Yes','Connectivity':'Bluetooth, USB-C','Color':'White'}, 'magic-keyboard,touch-id,usb-c,mac'),
    ('Razer Blade 16 (2024) (i9, 32GB, RTX 4090)', 'Razer', 'Laptops', 3999.99, 4499.99, 4.5, 410, {'CPU':'Intel Core i9-14900HX','RAM':'32GB DDR5','Storage':'2TB SSD','GPU':'NVIDIA RTX 4090 16GB','Display':'16in QHD+ 240Hz Dual-Mode OLED','OS':'Windows 11 Home','Color':'Black'}, 'gaming,rtx4090,16-inch,dual-mode-oled'),
    ('Lenovo Yoga 9i 14" 2-in-1 (Ultra 7, 16GB)', 'Lenovo', 'Laptops', 1399.99, 1599.99, 4.4, 920, {'CPU':'Intel Core Ultra 7 155H','RAM':'16GB LPDDR5x','Storage':'1TB SSD','Display':'14in 2.8K OLED Touch','OS':'Windows 11 Home','Weight':'3.09 lb','Color':'Cosmic Blue'}, '2-in-1,convertible,oled,touchscreen'),
    ('Logitech Brio 505 1080p Business Webcam', 'Logitech', 'Computer Accessories', 129.99, 149.99, 4.5, 1820, {'Resolution':'1080p','Field of View':'90°','Mount':'Privacy shutter, monitor mount','Cable':'USB-C 5ft','Color':'Graphite'}, 'webcam,1080p,business,privacy-shutter'),
    ('Insta360 Link AI 4K Webcam', 'Insta360', 'Computer Accessories', 299.99, 329.99, 4.4, 980, {'Resolution':'4K','AI Tracking':'Yes','Mount':'Gimbal','Connectivity':'USB-C','Color':'Black'}, 'webcam,4k,ai-tracking,gimbal'),
    ('CORSAIR HS80 RGB WIRELESS Gaming Headset', 'CORSAIR', 'Headphones', 149.99, 179.99, 4.5, 2810, {'Driver':'50mm','Battery':'20h','Connectivity':'2.4GHz Slipstream + USB','Mic':'Broadcast-grade','Color':'Carbon'}, 'gaming,wireless,rgb,broadcast-mic'),
]


# Home & Kitchen
HOME = [
    ('Cuisinart 14-Cup Food Processor DFP-14BCNY', 'Cuisinart', 'Kitchen Appliances', 229.95, 279.95, 4.7, 18920, {'Capacity':'14 cups','Power':'720W','Blades':'Stainless steel S, slicing, shredding','Color':'Brushed Stainless'}, 'food-processor,14-cup,stainless'),
    ('KitchenAid Artisan 5-Quart Tilt-Head Stand Mixer', 'KitchenAid', 'Kitchen Appliances', 449.99, 499.99, 4.8, 38120, {'Capacity':'5 qt','Power':'325W','Attachments':'10+','Color':'Empire Red'}, 'stand-mixer,5-quart,iconic,baking'),
    ('Vitamix A3500 Ascent Series Smart Blender', 'Vitamix', 'Kitchen Appliances', 549.95, 649.95, 4.7, 8910, {'Capacity':'64 oz','Power':'2.2 HP','Programs':'5','Color':'Brushed Stainless'}, 'blender,vitamix,smart,premium'),
    ('Ninja Foodi 10-in-1 XL Pressure Cooker Air Fryer', 'Ninja', 'Kitchen Appliances', 249.99, 299.99, 4.7, 12820, {'Capacity':'8 qt','Functions':'Pressure cook, air crisp, slow cook, sear, more','Color':'Black/Stainless'}, 'pressure-cooker,air-fryer,8qt,multi-cooker'),
    ('Breville Barista Express BES870XL Espresso Machine', 'Breville', 'Kitchen Appliances', 749.95, 849.95, 4.7, 14820, {'Type':'Semi-automatic','Grinder':'Conical burr built-in','Pressure':'15 bar','Color':'Stainless Steel'}, 'espresso,burr-grinder,15-bar,prosumer'),
    ('Nespresso VertuoPlus Coffee and Espresso Machine', 'Nespresso', 'Kitchen Appliances', 159.00, 199.00, 4.6, 24810, {'Type':'Capsule','Tank':'40 oz','Color':'Matte Black','Pods':'Vertuo'}, 'coffee,capsule,nespresso,one-touch'),
    ('Keurig K-Elite Single Serve Coffee Maker', 'Keurig', 'Kitchen Appliances', 169.99, 189.99, 4.6, 78210, {'Sizes':'4/6/8/10/12 oz','Tank':'75 oz','Color':'Brushed Slate','Hot Water':'Yes'}, 'coffee,k-cup,single-serve,popular'),
    ('Bonavita BV1900TS 8-Cup Coffee Brewer', 'Bonavita', 'Kitchen Appliances', 145.00, 175.00, 4.6, 8210, {'Capacity':'8 cups','Certification':'SCA Home Brewer','Color':'Stainless Steel'}, 'coffee,drip,sca-certified,8-cup'),
    ('Instant Pot Vortex Plus 6 Qt 6-in-1 Air Fryer', 'Instant Pot', 'Kitchen Appliances', 99.99, 139.99, 4.7, 38920, {'Capacity':'6 qt','Functions':'Air fry, roast, broil, bake, reheat, dehydrate','Color':'Black'}, 'air-fryer,6qt,multi-function,budget'),
    ('Cosori Pro II 5.8-Qt Air Fryer', 'Cosori', 'Kitchen Appliances', 119.99, 149.99, 4.7, 84210, {'Capacity':'5.8 qt','Functions':'12 presets','Window':'Yes','Color':'Black'}, 'air-fryer,5.8qt,window,bestseller'),
    ('Lodge 12-Inch Cast Iron Skillet', 'Lodge', 'Cookware', 24.90, 39.90, 4.8, 124820, {'Diameter':'12 inch','Material':'Pre-seasoned cast iron','Made In':'USA','Color':'Black'}, 'cast-iron,12-inch,made-in-usa,bestseller'),
    ('Le Creuset Signature 5.5 Qt Round Dutch Oven', 'Le Creuset', 'Cookware', 449.95, 480.00, 4.9, 8210, {'Capacity':'5.5 qt','Material':'Enameled cast iron','Color':'Cerise (Red)','Lifetime Warranty':'Yes'}, 'dutch-oven,5.5-qt,enameled,premium'),
    ('All-Clad D3 Stainless 10-Piece Cookware Set', 'All-Clad', 'Cookware', 699.95, 1099.95, 4.8, 2820, {'Pieces':'10','Material':'Tri-ply stainless steel','Dishwasher Safe':'Yes','Made In':'USA','Color':'Stainless'}, 'cookware-set,stainless,tri-ply,made-in-usa'),
    ('OXO Good Grips 3-Piece Mixing Bowl Set', 'OXO', 'Kitchen Utensils', 39.95, 49.95, 4.8, 28910, {'Pieces':'3 (1.5/3/5 qt)','Material':'Stainless steel with non-slip base','Color':'Silver/White'}, 'mixing-bowl,3-piece,non-slip,prep'),
    ('Shun Classic 8-Inch Chef\'s Knife', 'Shun', 'Knives', 159.95, 199.95, 4.8, 4280, {'Blade':'8 inch VG-MAX','Handle':'Pakkawood','Made In':'Japan'}, 'chefs-knife,vg-max,japan,8-inch'),
    ('Wüsthof Classic 7-Piece Block Set', 'Wüsthof', 'Knives', 599.95, 799.95, 4.8, 2120, {'Pieces':'7','Material':'High-carbon stainless steel','Made In':'Solingen, Germany'}, 'knife-set,wusthof,germany,7-piece'),
    ('Dyson V15 Detect Cordless Vacuum', 'Dyson', 'Floor Care', 749.99, 799.99, 4.6, 8820, {'Battery':'60 min','Suction':'230AW','Bin':'0.2 gal','Color':'Yellow/Iron'}, 'cordless,60-min,laser,premium'),
    ('Shark Stratos Cordless Stick Vacuum IZ862H', 'Shark', 'Floor Care', 449.99, 499.99, 4.5, 4820, {'Battery':'Removable, 40 min','Self-Cleaning Brushroll':'Yes','Color':'Stratos Navy'}, 'cordless,self-cleaning,40-min'),
    ('iRobot Roomba j7+ (7550) Self-Empty Robot Vacuum', 'iRobot', 'Floor Care', 599.99, 799.99, 4.6, 12820, {'Battery':'90 min','Self-Empty':'Yes (60 days)','Mapping':'PrecisionVision','Color':'Graphite'}, 'robot-vacuum,self-empty,j7,obstacle-avoidance'),
    ('Eufy Clean X10 Pro Omni Robot Vacuum and Mop', 'Eufy', 'Floor Care', 799.99, 999.99, 4.5, 1820, {'Battery':'180 min','Self-Empty':'Yes','Self-Wash':'Yes','Mop':'Dual rotating','Color':'White'}, 'robot-vacuum,mop,omni,self-wash'),
    ('Dyson Pure Cool TP07 Air Purifier', 'Dyson', 'Air Quality', 549.99, 649.99, 4.6, 3820, {'Coverage':'600 sqft','HEPA':'H13','Fan':'10-speed','Color':'White/Silver'}, 'air-purifier,hepa,bladeless,smart'),
    ('Coway Airmega AP-1512HH Mighty Air Purifier', 'Coway', 'Air Quality', 229.00, 269.00, 4.7, 38120, {'Coverage':'361 sqft','HEPA':'True','Color':'White'}, 'air-purifier,true-hepa,quiet,bestseller'),
    ('Levoit Core 600S Smart Air Purifier', 'Levoit', 'Air Quality', 299.99, 349.99, 4.7, 24820, {'Coverage':'1588 sqft','HEPA':'H13','Smart':'WiFi/Alexa','Color':'White'}, 'air-purifier,smart,1500-sqft,h13'),
    ('Brita 18-Cup UltraMax Filtered Water Dispenser', 'Brita', 'Water Filtration', 41.99, 49.99, 4.7, 41820, {'Capacity':'18 cups','Filter':'Brita Standard','BPA Free':'Yes','Color':'White'}, 'water-filter,18-cup,family,countertop'),
    ('Berkey Big Berkey Gravity Water Filter', 'Berkey', 'Water Filtration', 367.00, 399.00, 4.7, 2920, {'Capacity':'2.25 gal','Filters':'Black Berkey (2)','Material':'Stainless steel','Color':'Polished'}, 'gravity-filter,off-grid,stainless,bug-out'),
    ('Sealy Posturepedic 12" Queen Mattress', 'Sealy', 'Bedroom', 799.00, 999.00, 4.5, 1820, {'Size':'Queen','Height':'12 inches','Type':'Innerspring','Firmness':'Medium','Color':'White'}, 'mattress,queen,innerspring,medium'),
    ('Tuft & Needle Original 10" Queen Mattress', 'Tuft & Needle', 'Bedroom', 695.00, 895.00, 4.5, 18920, {'Size':'Queen','Height':'10 inches','Type':'Foam','Firmness':'Medium-firm','Color':'White'}, 'mattress,queen,foam,bed-in-a-box'),
    ('Casper Original Hybrid Queen Mattress', 'Casper', 'Bedroom', 1495.00, 1795.00, 4.4, 8210, {'Size':'Queen','Height':'12 inches','Type':'Hybrid','Firmness':'Medium','Color':'White'}, 'mattress,queen,hybrid,bed-in-a-box'),
    ('Linenspa 2 Inch Gel Memory Foam Topper Queen', 'Linenspa', 'Bedroom', 49.99, 79.99, 4.5, 84210, {'Size':'Queen','Thickness':'2 inch','Material':'Gel-infused memory foam','Color':'White'}, 'topper,queen,memory-foam,budget'),
    ('Mellanni Bed Sheet Set Queen Cooling', 'Mellanni', 'Bedroom', 39.97, 59.97, 4.6, 248910, {'Size':'Queen','Material':'Microfiber','Pieces':'4','Color':'Gray'}, 'sheet-set,queen,microfiber,bestseller'),
    ('Brooklinen Luxe Core Sheet Set Queen', 'Brooklinen', 'Bedroom', 169.00, 199.00, 4.5, 12820, {'Size':'Queen','Material':'Long-staple sateen cotton','Thread Count':'480','Color':'Solid White'}, 'sheet-set,queen,cotton,sateen,premium'),
    ('Saatva Down Alternative Pillow Standard', 'Saatva', 'Bedroom', 165.00, 185.00, 4.6, 1820, {'Size':'Standard','Fill':'Down alternative microfiber','Loft':'Medium','Color':'White'}, 'pillow,down-alternative,medium,hypoallergenic'),
    ('Tempur-Pedic TEMPUR-Cloud Pillow Standard', 'Tempur-Pedic', 'Bedroom', 99.00, 119.00, 4.6, 8210, {'Size':'Standard','Fill':'TEMPUR memory foam','Color':'White'}, 'pillow,memory-foam,tempurpedic'),
    ('YnM Weighted Blanket 15 lb 60x80"', 'YnM', 'Bedroom', 49.99, 79.99, 4.5, 38120, {'Weight':'15 lb','Size':'60x80 (Queen)','Filling':'Glass beads + cotton','Color':'Gray'}, 'weighted-blanket,15lb,queen,sleep'),
    ('Buffy Cloud Comforter Queen', 'Buffy', 'Bedroom', 159.00, 179.00, 4.4, 4280, {'Size':'Queen','Fill':'100% recycled microfiber','Cover':'Eucalyptus lyocell','Color':'White'}, 'comforter,queen,eucalyptus,recycled'),
    ('Hatch Restore 2 Smart Sleep Sound Machine', 'Hatch', 'Bedroom', 199.99, 219.99, 4.6, 8820, {'Sounds':'Library','Sunrise Alarm':'Yes','Smart':'WiFi','Color':'Putty'}, 'sleep,sound-machine,sunrise-alarm,smart'),
    ('Frigidaire EFMIS129 Mini Fridge 6-Can', 'Frigidaire', 'Kitchen Appliances', 39.99, 49.99, 4.5, 28910, {'Capacity':'6 cans','Power':'AC + 12V','Color':'White'}, 'mini-fridge,6-can,desktop,12v'),
    ('Cuisinart ICE-21P1 1.5 Qt Frozen Yogurt-Ice Cream Maker', 'Cuisinart', 'Kitchen Appliances', 89.95, 119.95, 4.7, 38920, {'Capacity':'1.5 qt','Time':'~20 min','Color':'White'}, 'ice-cream-maker,1.5qt,cuisinart'),
    ('Anova Precision Cooker Pro Sous Vide', 'Anova', 'Kitchen Appliances', 399.00, 499.00, 4.4, 4820, {'Power':'1200W','Capacity':'Up to 100L','Pump':'Patented','Color':'Black'}, 'sous-vide,1200w,pro,wifi'),
    ('Yeti Tundra 45 Hard Cooler', 'YETI', 'Outdoor Living', 325.00, 350.00, 4.8, 8210, {'Capacity':'26 cans','Ice Retention':'Multi-day','Material':'Rotomolded polyethylene','Color':'White'}, 'cooler,rotomolded,45qt,outdoor'),
    ('RTIC 52 Qt Ultra-Light Cooler', 'RTIC', 'Outdoor Living', 199.99, 269.99, 4.7, 6820, {'Capacity':'52 qt','Ice Retention':'Up to 8 days','Material':'Rotomolded','Color':'Tan'}, 'cooler,52qt,ultra-light,rtic'),
    ('Stanley Quencher H2.0 FlowState 40 oz Tumbler', 'Stanley', 'Outdoor Living', 44.95, 49.95, 4.8, 184210, {'Capacity':'40 oz','Insulation':'Double-wall vacuum','Lid':'FlowState','Color':'Charcoal'}, 'tumbler,40oz,viral,insulated'),
    ('Hydro Flask 32 oz Wide Mouth Bottle', 'Hydro Flask', 'Outdoor Living', 49.95, 54.95, 4.8, 84120, {'Capacity':'32 oz','Insulation':'TempShield','Material':'18/8 stainless','Color':'Pacific'}, 'bottle,32oz,stainless,insulated'),
    ('Solo Stove Bonfire 2.0 with Stand', 'Solo Stove', 'Outdoor Living', 354.99, 399.99, 4.7, 12820, {'Diameter':'19.5 in','Material':'304 stainless','Smokeless':'Yes','Color':'Stainless'}, 'fire-pit,smokeless,19in,outdoor'),
    ('Weber Original Kettle Premium 22" Grill', 'Weber', 'Outdoor Living', 249.00, 279.00, 4.8, 8820, {'Cooking Area':'363 sq in','Type':'Charcoal','Color':'Black','Lifetime':'10-year warranty'}, 'grill,charcoal,22-inch,classic'),
    ('Traeger Pro Series 22 Pellet Grill', 'Traeger', 'Outdoor Living', 549.99, 649.99, 4.5, 3820, {'Cooking Area':'572 sq in','Hopper':'18 lb','Color':'Bronze','WiFi':'No'}, 'pellet-grill,traeger,bronze,beginner'),
    ('Honeywell HCM350W Cool Mist Humidifier', 'Honeywell', 'Air Quality', 89.99, 119.99, 4.4, 24820, {'Coverage':'Medium room','Tank':'1 gal','Runtime':'24h','Color':'White'}, 'humidifier,cool-mist,medium-room,germ-free'),
    ('Levoit OasisMist 1000S Smart Humidifier', 'Levoit', 'Air Quality', 119.99, 149.99, 4.5, 4820, {'Coverage':'452 sqft','Tank':'1.85 gal','Smart':'WiFi/Alexa','Color':'White'}, 'humidifier,smart,wifi,top-fill'),
    ('Vornado 6303DC Energy Smart Whole Room Air Circulator', 'Vornado', 'Heating & Cooling', 119.99, 149.99, 4.7, 8820, {'Coverage':'Whole room','Power':'Variable speed DC motor','Color':'Black'}, 'fan,whole-room,dc-motor,energy-smart'),
    ('Govee LED Strip Lights 50ft RGB Bluetooth', 'Govee', 'Home Decor', 19.99, 29.99, 4.6, 128920, {'Length':'50 ft','Type':'5050 RGB','Control':'App, IR remote, mic','Color':'Multicolor'}, 'led-strip,50ft,rgb,smart-app'),
]


# Fashion
FASHION = [
    ('Levi\'s Women\'s Wedgie Straight Jeans', "Levi's", 'Womens Jeans', 79.50, 89.50, 4.4, 12820, {'Fit':'Wedgie Straight','Material':'99% Cotton, 1% Elastane','Color':'Dark Indigo','Sizes':'24-34'}, 'jeans,straight,wedgie,denim'),
    ('Levi\'s Men\'s 511 Slim Fit Jeans', "Levi's", 'Mens Jeans', 69.50, 79.50, 4.5, 84210, {'Fit':'Slim','Material':'99% Cotton, 1% Elastane','Color':'Black','Sizes':'28x30 - 40x32'}, 'jeans,slim,511,denim'),
    ('Levi\'s Men\'s 505 Regular Fit Jeans', "Levi's", 'Mens Jeans', 59.50, 69.50, 4.6, 124820, {'Fit':'Regular','Material':'100% Cotton','Color':'Stonewashed','Sizes':'29x30 - 44x32'}, 'jeans,regular,505,denim'),
    ('Wrangler Authentics Men\'s Classic Cargo Pant', 'Wrangler', 'Mens Pants', 28.99, 39.99, 4.5, 38120, {'Material':'100% Cotton','Color':'Khaki','Sizes':'30x30 - 44x32'}, 'cargo,pants,classic,cotton'),
    ('Dickies Men\'s Original 874 Work Pant', 'Dickies', 'Mens Pants', 32.99, 39.99, 4.7, 84210, {'Material':'65% Polyester, 35% Cotton','Color':'Dark Navy','Sizes':'28x30 - 44x32'}, 'workwear,874,classic,dickies'),
    ('Hanes Men\'s ComfortSoft T-Shirt 4-Pack', 'Hanes', 'Mens Shirts', 22.00, 32.00, 4.5, 184820, {'Pack':'4','Material':'100% Cotton','Color':'White','Sizes':'S-3XL'}, 't-shirt,4-pack,cotton,basic'),
    ('Champion Powerblend Fleece Pullover Hoodie', 'Champion', 'Mens Shirts', 45.00, 60.00, 4.7, 38920, {'Material':'50% Cotton, 50% Polyester','Color':'Oxford Gray','Sizes':'S-3XL Big & Tall'}, 'hoodie,fleece,big-and-tall,bestseller'),
    ('Carhartt Men\'s K87 Workwear Pocket T-Shirt', 'Carhartt', 'Mens Shirts', 22.99, 27.99, 4.7, 84120, {'Material':'6.75-oz cotton','Color':'Heather Gray','Sizes':'S-4XL'}, 't-shirt,workwear,pocket,carhartt'),
    ('The North Face Men\'s Borealis Backpack', 'The North Face', 'Bags', 99.00, 119.00, 4.8, 24820, {'Capacity':'28 L','Material':'Recycled polyester','Color':'TNF Black','Laptop Sleeve':'15in'}, 'backpack,28l,laptop,everyday'),
    ('Herschel Little America Backpack', 'Herschel', 'Bags', 109.99, 129.99, 4.7, 12820, {'Capacity':'25 L','Material':'Polyester','Color':'Black','Laptop Sleeve':'15in'}, 'backpack,25l,laptop,classic'),
    ('Patagonia Black Hole 32L Backpack', 'Patagonia', 'Bags', 169.00, 179.00, 4.8, 4280, {'Capacity':'32 L','Material':'Recycled polyester','Color':'Black','Water Resistant':'Yes'}, 'backpack,32l,water-resistant,travel'),
    ('Osprey Farpoint 40 Travel Backpack', 'Osprey', 'Bags', 185.00, 209.00, 4.8, 8820, {'Capacity':'40 L','Material':'Recycled nylon','Color':'Muted Space Blue','Carry-on':'Yes'}, 'travel,backpack,40l,carry-on'),
    ('Patagonia Better Sweater 1/4-Zip Fleece', 'Patagonia', 'Mens Outerwear', 119.00, 139.00, 4.8, 12820, {'Material':'Polyester fleece','Color':'Navy Blue','Sizes':'XS-2XL'}, 'fleece,quarter-zip,patagonia,outdoor'),
    ('Columbia Men\'s Steens Mountain Fleece', 'Columbia', 'Mens Outerwear', 39.99, 60.00, 4.7, 124820, {'Material':'100% Polyester fleece','Color':'Black','Sizes':'S-6XL Big & Tall'}, 'fleece,full-zip,big-and-tall,budget'),
    ('Carhartt Men\'s J140 Sandstone Active Jacket', 'Carhartt', 'Mens Outerwear', 84.99, 99.99, 4.8, 38120, {'Material':'12-oz cotton duck, sherpa lining','Color':'Brown','Sizes':'S-4XL'}, 'jacket,sherpa-lined,carhartt,workwear'),
    ('Patagonia Nano Puff Hoody Mens', 'Patagonia', 'Mens Outerwear', 279.00, 299.00, 4.8, 4820, {'Material':'Recycled polyester shell, 60g PrimaLoft','Color':'Black','Sizes':'XS-2XL'}, 'jacket,puffer,nano-puff,packable'),
    ('Marmot Tungsten 2P Tent Hiking Backpack', 'Marmot', 'Outdoor Gear', 199.99, 249.99, 4.6, 2820, {'Capacity':'2 person','Material':'Polyester','Weight':'5 lb 4 oz','Color':'Blaze/Steel'}, 'tent,2-person,backpacking,3-season'),
    ('Crocs Classic Clog Adult', 'Crocs', 'Footwear', 49.99, 54.99, 4.8, 484210, {'Material':'Croslite','Color':'Black','Sizes':'M4-M14, W6-W16'}, 'clog,classic,iconic,unisex'),
    ('Allbirds Wool Runners Mens', 'Allbirds', 'Footwear', 110.00, 110.00, 4.5, 8820, {'Material':'Merino wool upper','Color':'Natural Gray','Sizes':'8-14'}, 'sneaker,merino-wool,sustainable'),
    ('Nike Pegasus 41 Mens Running Shoe', 'Nike', 'Footwear', 140.00, 140.00, 4.7, 12820, {'Material':'Engineered mesh','Drop':'10mm','Stack':'37mm/27mm','Color':'Black/White','Sizes':'7-15'}, 'running-shoe,nike,daily-trainer,pegasus'),
    ('Asics Gel-Kayano 30 Womens Running Shoe', 'Asics', 'Footwear', 165.00, 165.00, 4.7, 4820, {'Material':'Engineered jacquard mesh','Drop':'10mm','Stack':'40mm/30mm','Color':'Black/Lilac Hint','Sizes':'5-12'}, 'running-shoe,stability,gel-kayano,asics'),
    ('Hoka Bondi 8 Mens Road Running Shoe', 'Hoka', 'Footwear', 165.00, 165.00, 4.7, 8210, {'Material':'Engineered mesh','Drop':'4mm','Stack':'33mm/29mm','Color':'Black','Sizes':'7-15'}, 'running-shoe,cushioned,hoka,max-cushion'),
    ('Brooks Ghost 16 Womens Running Shoe', 'Brooks', 'Footwear', 140.00, 140.00, 4.8, 12820, {'Material':'Engineered air mesh','Drop':'12mm','Stack':'35.5mm/23.5mm','Color':'White/Atomic Pink','Sizes':'5-13'}, 'running-shoe,brooks,daily-trainer,ghost'),
    ('Salomon Speedcross 6 Trail Running Shoe', 'Salomon', 'Footwear', 145.00, 165.00, 4.7, 6820, {'Material':'Anti-debris mesh','Drop':'10mm','Outsole':'Contagrip TA','Color':'Black/Phantom','Sizes':'7-13'}, 'trail-running,salomon,speedcross,grippy'),
    ('Birkenstock Arizona Soft Footbed Sandal', 'Birkenstock', 'Footwear', 110.00, 125.00, 4.8, 24820, {'Material':'Birko-Flor / cork-latex footbed','Color':'Mocha','Sizes':'EU36-EU46'}, 'sandal,birkenstock,arizona,classic'),
    ('Doc Martens 1460 8-Eye Boot', 'Dr. Martens', 'Footwear', 170.00, 180.00, 4.7, 38120, {'Material':'Smooth leather','Color':'Black','Sizes':'M5-M14'}, 'boot,8-eye,docs,classic'),
    ('Timberland 6-Inch Premium Waterproof Boot', 'Timberland', 'Footwear', 198.00, 220.00, 4.7, 48210, {'Material':'Nubuck leather','Waterproof':'Yes','Color':'Wheat','Sizes':'M7-M14'}, 'boot,waterproof,timberland,iconic'),
    ('Calvin Klein Womens Modern Cotton Bralette', 'Calvin Klein', 'Womens Intimates', 25.00, 32.00, 4.6, 84210, {'Material':'Cotton/Modal/Elastane','Color':'Black','Sizes':'XS-XL'}, 'bralette,modern-cotton,calvin-klein,everyday'),
    ('Hanes Women\'s Cotton Hi-Cut Panties 6-Pack', 'Hanes', 'Womens Intimates', 14.00, 18.00, 4.6, 184820, {'Pack':'6','Material':'100% Cotton','Color':'Assorted','Sizes':'5-10'}, 'panties,6-pack,cotton,basics'),
    ('Spanx Faux Leather Leggings', 'Spanx', 'Womens Pants', 98.00, 110.00, 4.6, 12820, {'Material':'Faux leather/polyester','Color':'Black','Sizes':'XS-3X'}, 'leggings,faux-leather,spanx,viral'),
    ('Lululemon Align High-Rise Pant 25"', 'Lululemon', 'Womens Pants', 98.00, 98.00, 4.7, 28210, {'Material':'Nulu','Inseam':'25in','Color':'Black','Sizes':'0-20'}, 'leggings,align,lululemon,yoga'),
    ('Athleta Salutation Stash Pocket II 7/8 Tight', 'Athleta', 'Womens Pants', 89.00, 99.00, 4.6, 8820, {'Material':'Powervita','Pockets':'2 stash','Color':'Black','Sizes':'XXS-3X'}, 'leggings,athleta,pockets,7-8'),
    ('Ray-Ban RB2140 Original Wayfarer Sunglasses', 'Ray-Ban', 'Eyewear', 171.00, 199.00, 4.8, 38120, {'Lens Width':'54mm','Material':'Acetate frame, crystal lens','Color':'Black with G-15 lens'}, 'sunglasses,wayfarer,ray-ban,iconic'),
    ('Oakley Holbrook XL Sunglasses', 'Oakley', 'Eyewear', 173.00, 196.00, 4.8, 8210, {'Lens Width':'59mm','Material':'O Matter frame, Plutonite lens','Color':'Matte Black/Prizm Black'}, 'sunglasses,holbrook,prizm,oakley'),
    ('Warby Parker Percey Eyeglasses', 'Warby Parker', 'Eyewear', 95.00, 95.00, 4.7, 1820, {'Material':'Acetate','Color':'Crystal','Lens Type':'Single-vision Rx','Frame Width':'140mm'}, 'eyeglasses,acetate,warby-parker,prescription'),
    ('Casio G-Shock GA-2100 CasiOak Watch', 'Casio', 'Accessories', 99.00, 110.00, 4.8, 24820, {'Case':'45.4mm carbon-core','Movement':'Quartz','Water Resistance':'200m','Color':'Black'}, 'watch,casio,g-shock,casioak'),
    ('Seiko 5 Sports SRPD55 Automatic Watch', 'Seiko', 'Accessories', 245.00, 295.00, 4.7, 4820, {'Case':'42.5mm stainless','Movement':'Automatic 4R36','Water Resistance':'100m','Color':'Black/Silver'}, 'watch,seiko,automatic,5-sports'),
    ('Fossil Gen 6 Smartwatch', 'Fossil', 'Accessories', 199.00, 295.00, 4.3, 2820, {'Case':'44mm stainless','OS':'Wear OS','Battery':'1 day','Color':'Black'}, 'smartwatch,wear-os,fossil,gen-6'),
    ('Coach Mini Town Bucket Bag', 'Coach', 'Bags', 295.00, 395.00, 4.7, 1820, {'Material':'Polished pebble leather','Color':'Black','Strap':'Adjustable crossbody'}, 'handbag,bucket,coach,leather'),
    ('Kate Spade New York Knott Medium Crossbody', 'Kate Spade', 'Bags', 248.00, 348.00, 4.8, 4820, {'Material':'Leather','Color':'Black','Strap':'Adjustable'}, 'crossbody,kate-spade,leather,medium'),
    ('Adidas Originals Trefoil Tee Mens', 'Adidas', 'Mens Shirts', 30.00, 35.00, 4.6, 84120, {'Material':'100% Cotton','Color':'Black','Sizes':'XS-4XL'}, 't-shirt,adidas,trefoil,classic'),
    ('Nike Sportswear Club Fleece Pullover Hoodie', 'Nike', 'Mens Shirts', 60.00, 65.00, 4.8, 184820, {'Material':'80% Cotton, 20% Polyester','Color':'Black','Sizes':'S-3XL Tall'}, 'hoodie,nike-club,fleece,bestseller'),
    ('Under Armour Tech 2.0 Short Sleeve Tee', 'Under Armour', 'Mens Shirts', 25.00, 30.00, 4.7, 184120, {'Material':'100% Polyester','Color':'Black','Sizes':'S-3XL'}, 'tech-tee,training,quick-dry,under-armour'),
    ('Polo Ralph Lauren Classic Fit Polo Mens', 'Polo Ralph Lauren', 'Mens Shirts', 98.50, 98.50, 4.8, 48210, {'Material':'100% Cotton mesh','Color':'Navy','Sizes':'XS-3XL Big & Tall'}, 'polo,classic-fit,ralph-lauren,iconic'),
]


# Beauty
BEAUTY = [
    ('CeraVe Hydrating Facial Cleanser 12 oz', 'CeraVe', 'Skincare', 17.99, 19.99, 4.8, 184120, {'Size':'12 oz','Skin Type':'Normal to Dry','Ingredients':'Ceramides, Hyaluronic Acid','Fragrance':'Free'}, 'cleanser,hydrating,ceramides,gentle'),
    ('CeraVe Moisturizing Cream 16 oz', 'CeraVe', 'Skincare', 19.99, 22.99, 4.8, 248120, {'Size':'16 oz','Skin Type':'Dry to Very Dry','Texture':'Rich cream','Fragrance':'Free'}, 'moisturizer,16-oz,ceramides,body'),
    ('La Roche-Posay Anthelios Melt-in Milk SPF 60', 'La Roche-Posay', 'Skincare', 35.99, 39.99, 4.7, 28210, {'Size':'5 oz','SPF':'60','Type':'Mineral + chemical','Water Resistant':'80 min'}, 'sunscreen,spf60,broad-spectrum,la-roche-posay'),
    ('EltaMD UV Clear Tinted Sunscreen SPF 46', 'EltaMD', 'Skincare', 41.00, 47.00, 4.7, 28120, {'Size':'1.7 oz','SPF':'46','Tint':'Light','Type':'Mineral with niacinamide'}, 'sunscreen,tinted,spf46,sensitive-skin'),
    ('The Ordinary Niacinamide 10% + Zinc 1%', 'The Ordinary', 'Skincare', 8.50, 10.50, 4.5, 84120, {'Size':'30 mL','Active':'10% Niacinamide','Concern':'Pores, oil'}, 'serum,niacinamide,affordable,pores'),
    ('Paula\'s Choice 2% BHA Liquid Exfoliant', "Paula's Choice", 'Skincare', 35.00, 39.00, 4.7, 38120, {'Size':'4 oz','Active':'2% Salicylic Acid','Concern':'Pores, blackheads'}, 'exfoliant,bha,salicylic-acid,pores'),
    ('Olaplex No. 3 Hair Perfector', 'Olaplex', 'Hair Care', 30.00, 32.00, 4.6, 84120, {'Size':'3.3 oz','Use':'Weekly bond-builder treatment','Hair Type':'All damaged'}, 'hair-treatment,bond-builder,olaplex,weekly'),
    ('Living Proof Perfect Hair Day Dry Shampoo', 'Living Proof', 'Hair Care', 30.00, 32.00, 4.5, 12820, {'Size':'4 oz','Use':'Refresh between washes','Hair Type':'All'}, 'dry-shampoo,living-proof,phd'),
    ('Dyson Supersonic Hair Dryer (Nickel/Copper)', 'Dyson', 'Hair Care', 429.99, 429.99, 4.7, 12820, {'Power':'1600W','Heat Modes':'4','Speed':'3','Color':'Nickel/Copper'}, 'hair-dryer,dyson,supersonic,premium'),
    ('Revlon One-Step Volumizer Hot Air Brush', 'Revlon', 'Hair Care', 47.94, 59.99, 4.5, 484210, {'Power':'1100W','Barrel':'2.4in oval','Color':'Mint','Heat Settings':'3'}, 'hot-air-brush,volumizer,viral,revlon'),
    ('Maybelline Lash Sensational Mascara', 'Maybelline', 'Makeup', 9.99, 10.99, 4.6, 184820, {'Volume':'0.32 fl oz','Color':'Very Black','Brush':'Fanning'}, 'mascara,maybelline,drugstore,bestseller'),
    ('NYX Professional Makeup Butter Gloss', 'NYX', 'Makeup', 5.49, 6.99, 4.7, 84120, {'Volume':'0.27 fl oz','Color':'Crème Brulee','Type':'Sheer'}, 'lip-gloss,nyx,butter-gloss,drugstore'),
    ('e.l.f. Halo Glow Liquid Filter', 'e.l.f.', 'Makeup', 14.00, 14.00, 4.4, 38120, {'Volume':'1.01 fl oz','Shades':'8','Finish':'Glowy'}, 'liquid-filter,glow,elf,viral'),
    ('Charlotte Tilbury Pillow Talk Lipstick', 'Charlotte Tilbury', 'Makeup', 38.00, 38.00, 4.7, 4280, {'Volume':'0.12 oz','Shade':'Original Pillow Talk','Finish':'Matte Revolution'}, 'lipstick,pillow-talk,charlotte-tilbury'),
    ('Fenty Beauty Pro Filt\'r Soft Matte Foundation', 'Fenty Beauty', 'Makeup', 40.00, 40.00, 4.5, 12820, {'Volume':'1.08 fl oz','Shades':'50','Finish':'Soft Matte'}, 'foundation,fenty,soft-matte,inclusive'),
    ('Tatcha The Dewy Skin Cream', 'Tatcha', 'Skincare', 72.00, 72.00, 4.5, 4820, {'Size':'1.7 oz','Texture':'Rich cream','Concern':'Dryness, plumping'}, 'moisturizer,tatcha,luxury,dewy'),
    ('Drunk Elephant T.L.C. Sukari Babyfacial', 'Drunk Elephant', 'Skincare', 80.00, 80.00, 4.4, 4280, {'Size':'1.69 oz','Active':'25% AHA + 2% BHA','Frequency':'Weekly mask'}, 'mask,aha-bha,drunk-elephant,resurfacing'),
    ('Bioderma Sensibio H2O Micellar Water', 'Bioderma', 'Skincare', 16.99, 19.99, 4.7, 84120, {'Size':'8.4 oz','Use':'Cleanser/Makeup remover','Skin Type':'Sensitive'}, 'micellar-water,bioderma,sensitive'),
    ('Aquaphor Healing Ointment 14 oz Jar', 'Aquaphor', 'Skincare', 19.99, 23.99, 4.9, 184120, {'Size':'14 oz','Use':'Dry skin, lips, cuticles','Fragrance':'Free'}, 'ointment,aquaphor,multi-use,bestseller'),
    ('Native Deodorant Coconut & Vanilla', 'Native', 'Personal Care', 13.99, 14.99, 4.6, 184820, {'Size':'2.65 oz','Scent':'Coconut & Vanilla','Aluminum':'Free'}, 'deodorant,aluminum-free,native,coconut'),
    ('Old Spice High Endurance Deodorant 3-pack', 'Old Spice', 'Personal Care', 9.99, 14.99, 4.7, 84210, {'Size':'3 x 3 oz','Scent':'Pure Sport','Protection':'24h'}, 'deodorant,old-spice,3-pack,mens'),
    ('Philips Norelco Series 9000 Shaver', 'Philips Norelco', 'Personal Care', 249.99, 349.99, 4.5, 12820, {'Battery':'60 min','Wet/Dry':'Yes','Heads':'V-Track Precision','Color':'Black'}, 'shaver,philips,9000,wet-dry'),
    ('Braun Series 9 Pro+ Electric Shaver', 'Braun', 'Personal Care', 379.94, 449.94, 4.6, 8820, {'Battery':'60 min','Wet/Dry':'Yes','Heads':'5','Color':'Silver'}, 'shaver,braun,series-9,premium'),
    ('Oral-B iO Series 9 Electric Toothbrush', 'Oral-B', 'Personal Care', 299.99, 349.99, 4.6, 12820, {'Modes':'7','Display':'Interactive','Battery':'2 weeks','Color':'Rose Quartz'}, 'toothbrush,electric,oral-b,smart'),
    ('Philips Sonicare DiamondClean 9700', 'Philips', 'Personal Care', 229.95, 269.95, 4.6, 8820, {'Modes':'5','Battery':'2 weeks','Color':'Pink','App':'Yes'}, 'toothbrush,sonicare,smart,premium'),
    ('Burt\'s Bees 100% Natural Lip Balm 4-Pack', "Burt's Bees", 'Personal Care', 7.99, 10.99, 4.9, 248120, {'Pack':'4','Material':'Beeswax','Color':'Original'}, 'lip-balm,4-pack,burts-bees,natural'),
    ('Vaseline Lip Therapy Original 3-pack', 'Vaseline', 'Personal Care', 6.99, 8.99, 4.8, 84120, {'Pack':'3','Size':'0.25 oz each','Use':'Dry lips'}, 'lip-balm,vaseline,3-pack'),
    ('Trader Joe\'s 24-Hour Skincare Set (Multipack)', 'Generic', 'Skincare', 24.99, 34.99, 4.3, 1820, {'Pack':'5 items','Concern':'Hydration, brightening','Travel Size':'Yes'}, 'skincare-set,travel,multipack'),
    ('Sol de Janeiro Brazilian Bum Bum Cream 240mL', 'Sol de Janeiro', 'Skincare', 50.00, 55.00, 4.8, 18120, {'Size':'240 mL','Use':'Body cream, firming','Scent':'Cheirosa 62'}, 'body-cream,sol-de-janeiro,viral,brazilian'),
    ('Mielle Organics Rosemary Mint Scalp & Hair Oil', 'Mielle Organics', 'Hair Care', 9.99, 11.99, 4.6, 124820, {'Size':'2 oz','Active':'Rosemary, mint, biotin','Hair Type':'Damaged, growth'}, 'hair-oil,rosemary-mint,growth,viral'),
]


# Sports & Outdoors
SPORTS = [
    ('Bowflex SelectTech 552 Adjustable Dumbbells (Pair)', 'Bowflex', 'Strength Training', 549.00, 599.00, 4.8, 38120, {'Weight Range':'5-52.5 lb each','Increments':'2.5/5 lb','Color':'Gray'}, 'dumbbells,adjustable,bowflex,space-saving'),
    ('NordicTrack Commercial 1750 Treadmill', 'NordicTrack', 'Cardio', 1799.00, 1999.00, 4.6, 8210, {'Belt':'60in x 22in','Speed':'0-12 mph','Incline':'-3% to 15%','iFit':'30-day included'}, 'treadmill,1750,ifit,commercial'),
    ('Peloton Bike+ All-Access Membership Required', 'Peloton', 'Cardio', 2495.00, 2495.00, 4.7, 12820, {'Display':'24in HD Touchscreen','Resistance':'Magnetic','Color':'Black'}, 'exercise-bike,peloton,touchscreen'),
    ('Hydrow Wave Smart Rowing Machine', 'Hydrow', 'Cardio', 1495.00, 1795.00, 4.6, 1820, {'Display':'16in HD Touchscreen','Resistance':'Computer-controlled drag','Color':'Black'}, 'rower,hydrow,touchscreen,subscription'),
    ('Concept2 Model D Indoor Rowing Machine', 'Concept2', 'Cardio', 1010.00, 1010.00, 4.9, 12820, {'Display':'PM5','Resistance':'Flywheel','Color':'Black'}, 'rower,concept2,gold-standard,no-subscription'),
    ('TRX All-in-One Suspension Training System', 'TRX', 'Strength Training', 199.95, 219.95, 4.8, 8820, {'Strap Length':'Up to 9 ft','Includes':'Door anchor, getting-started program','Color':'Black/Yellow'}, 'suspension,trainer,trx,bodyweight'),
    ('Rogue Echo Bike V3.0', 'Rogue Fitness', 'Cardio', 745.00, 795.00, 4.9, 4820, {'Resistance':'Air','Display':'LCD console','Color':'Black'}, 'air-bike,rogue,echo,crossfit'),
    ('Rep Fitness AB-3000 FID Adjustable Bench', 'Rep Fitness', 'Strength Training', 379.99, 419.99, 4.8, 2820, {'Capacity':'1000 lb','Positions':'7 back, 4 seat','Color':'Black/Red'}, 'bench,fid,adjustable,rep'),
    ('Yes4All Vinyl Coated Cast Iron Kettlebell 35 lb', 'Yes4All', 'Strength Training', 49.99, 69.99, 4.7, 18120, {'Weight':'35 lb','Material':'Cast iron, vinyl-coated','Color':'Pink'}, 'kettlebell,35lb,cast-iron,budget'),
    ('Manduka PRO Yoga Mat 6mm', 'Manduka', 'Yoga & Pilates', 138.00, 145.00, 4.8, 12820, {'Thickness':'6 mm','Length':'71 inches','Material':'PVC, lifetime guarantee','Color':'Black Sage'}, 'yoga-mat,6mm,manduka,premium'),
    ('Liforme Original Yoga Mat 4.2mm', 'Liforme', 'Yoga & Pilates', 150.00, 165.00, 4.8, 4820, {'Thickness':'4.2 mm','Length':'73 inches','Material':'Natural rubber, eco-polyurethane','Color':'Grey'}, 'yoga-mat,grippy,liforme,alignment'),
    ('Coleman Sundome 4-Person Tent', 'Coleman', 'Camping', 119.99, 149.99, 4.6, 38120, {'Capacity':'4 person','Setup Time':'10 min','Material':'WeatherTec polyester','Color':'Green'}, 'tent,4-person,coleman,family'),
    ('REI Co-op Half Dome SL 2+ Tent', 'REI Co-op', 'Camping', 329.00, 379.00, 4.7, 1820, {'Capacity':'2+ person','Weight':'4 lb 6 oz','Color':'Green/Gray'}, 'tent,backpacking,2-person,3-season'),
    ('Coleman 0F Big Basin Sleeping Bag', 'Coleman', 'Camping', 89.99, 109.99, 4.5, 8820, {'Temp Rating':'0°F','Length':'Up to 6ft 4in','Color':'Black/Red'}, 'sleeping-bag,0f,big-basin,winter'),
    ('Thermarest NeoAir XLite Sleeping Pad', 'Therm-a-Rest', 'Camping', 199.95, 219.95, 4.6, 4820, {'R-Value':'4.5','Weight':'13 oz','Length':'Regular','Color':'Lemon Curry'}, 'sleeping-pad,backpacking,lightweight'),
    ('YETI Rambler 26 oz Stackable Cup w/ Straw Lid', 'YETI', 'Outdoor Hydration', 38.00, 42.00, 4.8, 84120, {'Capacity':'26 oz','Material':'18/8 stainless','Color':'Sea Foam'}, 'cup,26oz,yeti,stackable'),
    ('Owala FreeSip Insulated Stainless Steel 24 oz', 'Owala', 'Outdoor Hydration', 27.95, 32.95, 4.8, 124820, {'Capacity':'24 oz','Lid':'FreeSip','Color':'Shy Marshmallow','Insulation':'24h cold'}, 'water-bottle,freesip,24oz,viral'),
    ('Spalding NBA Street Outdoor Basketball 29.5"', 'Spalding', 'Team Sports', 24.99, 29.99, 4.7, 38120, {'Size':'29.5in official','Material':'Rubber','Color':'Orange'}, 'basketball,outdoor,29.5in,bestseller'),
    ('Wilson NCAA Replica Football Game Ball', 'Wilson', 'Team Sports', 39.95, 49.95, 4.7, 8820, {'Size':'Official','Material':'Composite leather','Color':'Brown'}, 'football,wilson,ncaa,outdoor'),
    ('Franklin Sports MLB Authentic Baseball Glove 12.5"', 'Franklin Sports', 'Team Sports', 69.99, 89.99, 4.6, 8820, {'Size':'12.5in','Hand':'Right-handed thrower','Material':'Premium steerhide','Color':'Tan/Black'}, 'baseball-glove,12.5in,franklin'),
    ('Callaway Big Bertha B21 Driver', 'Callaway', 'Golf', 399.99, 529.99, 4.7, 4820, {'Loft':'9°','Shaft':'Graphite','Hand':'Right-handed','Color':'Black'}, 'driver,callaway,b21,golf'),
    ('Titleist Pro V1 Golf Balls (Dozen)', 'Titleist', 'Golf', 54.99, 54.99, 4.9, 28120, {'Pack':'12','Cover':'Cast urethane','Construction':'3-piece','Color':'White'}, 'golf-balls,pro-v1,titleist,dozen'),
    ('Wilson NBA Authentic Series Basketball 28.5"', 'Wilson', 'Team Sports', 19.99, 29.99, 4.7, 8210, {'Size':'28.5in','Material':'Composite leather','Color':'Brown'}, 'basketball,wilson,28.5in,indoor'),
    ('Schwinn IC4 Indoor Cycling Bike', 'Schwinn', 'Cardio', 999.00, 1199.00, 4.6, 12820, {'Resistance':'100-level magnetic','Display':'Backlit LCD','Color':'Black'}, 'exercise-bike,schwinn,ic4,quiet'),
    ('Garmin Edge 540 GPS Bike Computer', 'Garmin', 'Cycling', 349.99, 399.99, 4.5, 1820, {'Display':'2.6in color','Battery':'42h Power Save','GPS':'Multi-band','Color':'Black'}, 'bike-computer,gps,garmin,multi-band'),
    ('Trek Marlin 7 Gen 3 29" Mountain Bike', 'Trek', 'Cycling', 1099.99, 1199.99, 4.7, 820, {'Wheel Size':'29in','Drivetrain':'1x10 Shimano Deore','Suspension':'RockShox Judy','Color':'Trek Black'}, 'mountain-bike,trek,marlin,29er'),
    ('Speedo Vanquisher 2.0 Goggle', 'Speedo', 'Swim', 18.00, 22.00, 4.8, 38120, {'Style':'Mirrored','Fit':'Adult','Color':'Smoke'}, 'goggles,speedo,vanquisher,training'),
    ('Speedo Endurance+ Polyester Square Leg', 'Speedo', 'Swim', 39.00, 49.00, 4.7, 12820, {'Material':'Polyester','Size':'30','Color':'Black'}, 'swim,endurance,square-leg,training'),
    ('Sklz Pro Mini Basketball Hoop System', 'Sklz', 'Toys', 39.99, 54.99, 4.7, 18120, {'Hoop Size':'9in','Mount':'Door','Ball':'Mini foam included','Color':'Black/Red'}, 'mini-hoop,door-mount,sklz,indoor'),
    ('Therabody Theragun Prime Massage Gun', 'Therabody', 'Recovery', 199.00, 299.00, 4.6, 12820, {'Speeds':'5','Battery':'120 min','Attachments':'4','Color':'Black'}, 'massage-gun,theragun,recovery,prime'),
]


# Toys
TOYS = [
    ('LEGO Star Wars Mandalorian Razor Crest 75331', 'LEGO', 'Building Sets', 599.99, 599.99, 4.9, 8820, {'Pieces':'6187','Age':'18+','Theme':'Star Wars'}, 'lego,star-wars,mandalorian,uc'),
    ('LEGO Architecture Eiffel Tower 21019', 'LEGO', 'Building Sets', 41.99, 49.99, 4.8, 28120, {'Pieces':'321','Age':'12+','Height':'12 in','Theme':'Architecture'}, 'lego,architecture,eiffel-tower,display'),
    ('LEGO Classic Large Creative Brick Box 10698', 'LEGO', 'Building Sets', 59.99, 69.99, 4.9, 84120, {'Pieces':'790','Age':'4+','Theme':'Classic'}, 'lego,classic,starter,creative'),
    ('LEGO Technic Lamborghini Sián FKP 37 42115', 'LEGO', 'Building Sets', 449.99, 449.99, 4.8, 4820, {'Pieces':'3696','Age':'18+','Theme':'Technic'}, 'lego,technic,lamborghini,supercar'),
    ('Mega Bloks First Builders Big Building Bag 80-pc', 'Mega Bloks', 'Building Sets', 21.99, 27.99, 4.8, 28120, {'Pieces':'80','Age':'1-5','Material':'Plastic','Color':'Multicolor'}, 'mega-bloks,toddler,big-blocks'),
    ('Magnetic Magna-Tiles Clear Colors 100-Piece', 'Magna-Tiles', 'Building Sets', 124.95, 149.95, 4.9, 18120, {'Pieces':'100','Age':'3+','Material':'BPA-free plastic','Color':'Clear'}, 'magnetic-tiles,magna-tiles,stem'),
    ('Hot Wheels 50-Car Pack of 1:64 Scale Vehicles', 'Hot Wheels', 'Vehicles', 49.99, 64.99, 4.8, 84120, {'Pack':'50','Scale':'1:64','Age':'3+'}, 'hot-wheels,50-pack,1-64'),
    ('Nerf Elite 2.0 Commander RD-6 Blaster', 'Nerf', 'Outdoor Play', 27.99, 39.99, 4.7, 12820, {'Type':'Dart blaster','Capacity':'6 darts','Range':'Up to 90ft','Color':'Gray/Orange'}, 'nerf,blaster,elite,6-dart'),
    ('Crayola 64-count Crayons Box', 'Crayola', 'Arts & Crafts', 4.99, 6.99, 4.9, 84120, {'Pack':'64','Type':'Crayons','Includes':'Built-in sharpener'}, 'crayons,64-count,classroom'),
    ('Play-Doh Modeling Compound 10-pack of 2-oz Cans', 'Play-Doh', 'Arts & Crafts', 9.99, 14.99, 4.8, 124820, {'Pack':'10 cans','Size':'2 oz each','Age':'2+'}, 'play-doh,10-pack,classic'),
    ('Melissa & Doug Wooden Activity Cube', 'Melissa & Doug', 'Educational', 49.99, 59.99, 4.8, 38120, {'Material':'Wood','Activities':'5 sides','Age':'1-3'}, 'wooden-toy,activity-cube,toddler'),
    ('Vtech Pull and Learn Car Carrier', 'VTech', 'Vehicles', 32.99, 39.99, 4.8, 12820, {'Age':'1-4','Vehicles':'4','Color':'Multicolor'}, 'pull-toy,vtech,learning,toddler'),
    ('Fisher-Price Laugh & Learn Smart Stages Puppy', 'Fisher-Price', 'Educational', 25.99, 29.99, 4.8, 84120, {'Age':'6m-3y','Stages':'3','Material':'Plush'}, 'fisher-price,puppy,smart-stages,baby'),
    ('Barbie Dreamhouse Pool Party Doll House', 'Barbie', 'Dolls', 199.99, 249.99, 4.7, 28120, {'Stories':'3','Pieces':'75+','Pool':'Yes','Age':'3+'}, 'barbie,dreamhouse,dollhouse'),
    ('Bluey Family Home Playset', 'Bluey', 'Dolls', 49.99, 59.99, 4.9, 24820, {'Age':'3+','Includes':'House, 4 figures, furniture'}, 'bluey,playset,family-home'),
    ('PJ Masks Romeo\'s Lab Playset', 'PJ Masks', 'Action Figures', 39.99, 49.99, 4.7, 6820, {'Age':'3+','Includes':'Romeo figure + lab'}, 'pj-masks,playset,romeo'),
    ('LOL Surprise OMG Birthday Doll', 'LOL Surprise', 'Dolls', 39.99, 49.99, 4.6, 8820, {'Age':'4+','Doll':'1','Surprises':'25+'}, 'lol-surprise,omg-doll,fashion'),
    ('Funko Pop! Bluey #1453 Vinyl Figure', 'Funko', 'Collectibles', 12.99, 14.99, 4.8, 4820, {'Size':'3.75in','Material':'Vinyl','Series':'Bluey'}, 'funko-pop,bluey,collectible'),
    ('Hatchimals CollEGGtibles 12-Pack Egg Carton', 'Hatchimals', 'Collectibles', 19.99, 24.99, 4.7, 12820, {'Pack':'12','Age':'5+'}, 'hatchimals,collectible,12-pack'),
    ('Squishmallows 16" Cam the Cat Plush', 'Squishmallows', 'Plush', 29.99, 34.99, 4.9, 38120, {'Size':'16in','Character':'Cam the Cat','Material':'Super-soft polyester'}, 'squishmallow,plush,16in,viral'),
    ('Ravensburger Disney Memorable Moments 40320 Puzzle', 'Ravensburger', 'Puzzles', 599.99, 699.99, 4.8, 4820, {'Pieces':'40320','Age':'14+','Size':'265 x 75 in (assembled)'}, 'puzzle,40320,ravensburger,record'),
    ('Ravensburger Cozy Bakery 1000pc Puzzle', 'Ravensburger', 'Puzzles', 22.99, 27.99, 4.9, 28120, {'Pieces':'1000','Age':'12+','Size':'27 x 20 in'}, 'puzzle,1000pc,ravensburger,cozy'),
    ('Catan Studio Catan 5th Edition Board Game', 'Catan Studio', 'Board Games', 49.99, 59.99, 4.8, 38120, {'Players':'3-4','Age':'10+','Playtime':'60-120 min'}, 'board-game,catan,5th-edition,strategy'),
    ('Z-Man Games Pandemic Board Game', 'Z-Man Games', 'Board Games', 44.95, 54.95, 4.8, 28120, {'Players':'2-4','Age':'8+','Playtime':'45 min'}, 'board-game,pandemic,cooperative'),
    ('Hasbro Monopoly Classic Board Game', 'Hasbro', 'Board Games', 19.99, 24.99, 4.8, 84120, {'Players':'2-8','Age':'8+','Playtime':'60-180 min'}, 'board-game,monopoly,classic,family'),
    ('Mattel UNO Card Game', 'Mattel', 'Board Games', 6.99, 9.99, 4.9, 248120, {'Players':'2-10','Age':'7+','Cards':'108'}, 'card-game,uno,classic,family'),
    ('Exploding Kittens Original Card Game', 'Exploding Kittens', 'Board Games', 19.99, 24.99, 4.8, 84120, {'Players':'2-5','Age':'7+','Playtime':'15 min'}, 'card-game,exploding-kittens,party'),
    ('Magic: The Gathering Foundations Starter Collection', 'Wizards of the Coast', 'Board Games', 29.99, 34.99, 4.7, 1820, {'Players':'2+','Age':'13+','Cards':'350+'}, 'tcg,magic,foundations,starter'),
    ('Pokemon TCG Scarlet & Violet 151 Booster Bundle', 'Pokemon', 'Trading Cards', 27.99, 34.99, 4.8, 8820, {'Pack':'6 boosters','Set':'151','Age':'6+'}, 'pokemon,tcg,151,booster'),
    ('Mattel Hot Wheels Track Builder Unlimited Power Boost Box', 'Mattel', 'Vehicles', 39.99, 49.99, 4.7, 12820, {'Pieces':'40+','Vehicles':'2','Age':'5+'}, 'hot-wheels,track-builder,power-boost'),
]


# Map dataset -> (category_slug, subcategory provided in tuple, kind)
# Books tuples: (title, author, genre, pages, price, list_price, rating, reviews, year)
# Other tuples: (name, brand, subcategory, price, list_price, rating, reviews, specs, tags)

def _build_book_product(idx, t, pool, used):
    title, author, genre, pages, price, list_price, rating, reviews, year = t
    img = _pick_image(pool, idx)
    gallery = _pick_gallery(pool, 6, idx + 3)
    description = (
        f"{title} by {author} — a {genre.lower()} read released in {year}. "
        f"{pages} pages. Whether you are a long-time fan of {author} or new to {genre.lower()}, "
        f"this paperback edition is a satisfying addition to your library."
    )
    features = [
        f'Genre: {genre}',
        f'{pages} pages',
        f'Paperback, English',
        f'Published: {year}',
        f'Author: {author}',
    ]
    specs = {
        'Author': author,
        'Genre': genre,
        'Pages': str(pages),
        'Publisher': 'Aurora & Quill Press',
        'Language': 'English',
        'Publication Date': f'{year}-09-14',
        'Format': 'Paperback',
        'ISBN-13': f'979-1-{(idx % 9000) + 1000:04d}-{(idx * 7) % 900 + 100:03d}-{idx % 10}',
    }
    tags = ['book', 'paperback', genre.lower().replace(' ', '-')]
    return dict(
        name=title, brand=author, category='books', subcategory=genre,
        description=description, features=features, specs=specs,
        price=price, list_price=list_price, rating=rating, reviews=reviews,
        image=img, gallery=gallery, variants={'format': ['Paperback', 'Hardcover', 'Kindle']},
        tags=tags, release_date=f'{year}-09-14',
    )


def _build_generic_product(idx, t, category, pool, used):
    name, brand, subcategory, price, list_price, rating, reviews, specs_dict, tags_csv = t
    img = _pick_image(pool, idx)
    gallery = _pick_gallery(pool, 6, idx + 5)
    specs_lines = '\n'.join(f'• {k}: {v}' for k, v in specs_dict.items())
    description = (
        f"{name} by {brand}. {subcategory} that delivers on quality, fit, and value. "
        f"Key specs:\n{specs_lines}"
    )
    features = [f'{k}: {v}' for k, v in list(specs_dict.items())[:6]]
    variants = {}
    if 'Color' in specs_dict:
        variants['color'] = [specs_dict['Color'], 'Alternate']
    if 'Sizes' in specs_dict:
        sizes_value = specs_dict['Sizes']
        variants['size'] = [s.strip() for s in re.split(r'[,/-]', sizes_value)][:6]
    tags = [t.strip() for t in tags_csv.split(',') if t.strip()]
    return dict(
        name=name, brand=brand, category=category, subcategory=subcategory,
        description=description, features=features, specs=specs_dict,
        price=price, list_price=list_price, rating=rating, reviews=reviews,
        image=img, gallery=gallery, variants=variants, tags=tags,
        release_date='',
    )


def seed_extra_products(db, Product):
    """Add ~310 synthetic products. Idempotent: skip if total >= 700."""
    if Product.query.count() >= 700:
        return

    rng = random.Random(99)

    datasets = [
        ('books', BOOKS, _build_book_product),
        ('electronics', ELECTRONICS, _build_generic_product),
        ('computers', COMPUTERS, _build_generic_product),
        ('home', HOME, _build_generic_product),
        ('fashion', FASHION, _build_generic_product),
        ('beauty', BEAUTY, _build_generic_product),
        ('sports', SPORTS, _build_generic_product),
        ('toys', TOYS, _build_generic_product),
    ]

    added = 0
    for category, table, builder in datasets:
        pool = _category_pool(category)
        used = set()
        for idx, t in enumerate(table):
            if builder is _build_book_product:
                product_data = builder(idx, t, pool, used)
            else:
                product_data = builder(idx, t, category, pool, used)
            slug = _slugify(product_data['name'])
            if Product.query.filter_by(slug=slug).first():
                continue
            list_price = product_data['list_price'] or product_data['price']
            deal_discount = 0
            if list_price > product_data['price']:
                deal_discount = int(round((list_price - product_data['price']) / list_price * 100))
            is_deal = deal_discount >= 10
            # Deterministic seasonality flags
            is_featured = (idx % 7 == 0)
            is_bestseller = (product_data['reviews'] >= 10000)
            # Deterministic stock based on idx, rating
            stock = 25 + ((idx * 13 + int(product_data['rating'] * 10)) % 380)
            p = Product(
                name=product_data['name'],
                slug=slug,
                brand=product_data['brand'],
                category_slug=category,
                subcategory=product_data['subcategory'],
                description=product_data['description'],
                features=json.dumps(product_data['features']),
                specs=json.dumps(product_data['specs']),
                price=product_data['price'],
                list_price=list_price,
                image=product_data['image'],
                gallery_images=json.dumps(product_data['gallery']),
                variant_options=json.dumps(product_data['variants']),
                stock=stock,
                rating=product_data['rating'],
                review_count=product_data['reviews'],
                is_featured=is_featured,
                is_deal=is_deal,
                is_bestseller=is_bestseller,
                deal_discount=deal_discount,
                feature_tags=json.dumps(product_data['tags']),
                release_date=product_data['release_date'],
            )
            db.session.add(p)
            added += 1
    db.session.commit()
    return added


# ----- Wishlists / Cart / Returns / Extra orders -----

# Map review-user email → (city, state, zip, line1, phone, card_type, last4, exp_m, exp_y)
REVIEW_USER_PROFILES = {
    'jessica.m@test.com': ('Portland', 'OR', '97205', '742 NW Glisan St', '503-555-0107', 'Visa', '7711', 4, 2027),
    'rahul.p@test.com':   ('Cambridge', 'MA', '02139', '88 Massachusetts Ave', '617-555-0108', 'Mastercard', '4423', 8, 2028),
    'samir.k@test.com':   ('Denver', 'CO', '80202', '1144 15th St', '720-555-0109', 'Visa', '6602', 11, 2026),
    'emily.r@test.com':   ('Nashville', 'TN', '37203', '402 12th Ave S', '615-555-0110', 'Amex', '9034', 1, 2028),
    'marcus.t@test.com':  ('Atlanta', 'GA', '30309', '1100 Peachtree St', '404-555-0111', 'Discover', '5510', 7, 2027),
    'priya.s@test.com':   ('Seattle', 'WA', '98109', '600 Westlake Ave N', '206-555-0112', 'Visa', '8841', 2, 2028),
    'diana.l@test.com':   ('Miami', 'FL', '33131', '900 Brickell Ave', '305-555-0113', 'Mastercard', '3367', 9, 2026),
    'tommy.h@test.com':   ('Phoenix', 'AZ', '85004', '110 N Central Ave', '602-555-0114', 'Visa', '1158', 5, 2027),
    'linda.w@test.com':   ('Minneapolis', 'MN', '55402', '600 Nicollet Mall', '612-555-0115', 'Visa', '2294', 10, 2028),
    'greg.f@test.com':    ('Boston', 'MA', '02110', '200 Atlantic Ave', '617-555-0116', 'Mastercard', '7785', 3, 2027),
    'aisha.n@test.com':   ('Detroit', 'MI', '48226', '1000 Woodward Ave', '313-555-0117', 'Visa', '6041', 12, 2026),
    'kevin.o@test.com':   ('Las Vegas', 'NV', '89109', '3667 S Las Vegas Blvd', '702-555-0118', 'Amex', '4493', 6, 2028),
}


# Pinned bcrypt('test1234') for byte-identical reset (see harden-env/gotchas.md).
PINNED_PASSWORD_HASH = '$2b$12$Oi0plj9XBSbuCcjmrSVmje2AWKXN99Xpa7J2O6tjYvquZPTqNXN6i'

# Display names + prime flags for the 12 reviewer/customer accounts.
REVIEW_USER_DISPLAY = {
    'jessica.m@test.com': ('Jessica Mills',     True),
    'rahul.p@test.com':   ('Rahul Patel',       True),
    'samir.k@test.com':   ('Samir Krishnan',    False),
    'emily.r@test.com':   ('Emily Rodriguez',   True),
    'marcus.t@test.com':  ('Marcus Thompson',   False),
    'priya.s@test.com':   ('Priya Shankar',     True),
    'diana.l@test.com':   ('Diana Lim',         False),
    'tommy.h@test.com':   ('Tommy Hernandez',   True),
    'linda.w@test.com':   ('Linda Williams',    False),
    'greg.f@test.com':    ('Greg Fisher',       True),
    'aisha.n@test.com':   ('Aisha Nguyen',      False),
    'kevin.o@test.com':   ('Kevin Okafor',      True),
}


def seed_review_users(db, User):
    """Create the 12 reviewer/customer accounts used by extra orders/wishlists.

    Idempotent: skip when jessica already exists. Uses a pinned bcrypt hash
    instead of set_password() so byte-identical reset holds.
    """
    if User.query.filter_by(email='jessica.m@test.com').first():
        return 0
    added = 0
    for email, profile in REVIEW_USER_PROFILES.items():
        city, state, zc, line1, phone, ctype, last4, em, ey = profile
        name, is_prime = REVIEW_USER_DISPLAY[email]
        u = User(
            email=email, name=name, phone=phone,
            address_line1=line1, address_line2='',
            city=city, state=state, zip_code=zc,
            is_prime=is_prime,
        )
        u.password_hash = PINNED_PASSWORD_HASH
        db.session.add(u)
        added += 1
    db.session.commit()
    return added


def seed_extra_orders(db, User, Order, OrderItem, Product, SavedAddress, PaymentMethod):
    """For 12 review users: seed 1 saved address + 1 payment method + 1-2 orders each.

    Idempotent: skip when jessica already has a saved address.
    """
    jessica = User.query.filter_by(email='jessica.m@test.com').first()
    if jessica and SavedAddress.query.filter_by(user_id=jessica.id).first():
        return 0

    rng = random.Random(77)
    base_date = REFERENCE_DATE
    # Cache of selectable products by category (deterministic)
    pool_by_cat = {}
    for cat in ['electronics', 'home', 'books', 'computers', 'fashion', 'beauty', 'sports', 'toys']:
        prods = (Product.query
                 .filter_by(category_slug=cat)
                 .order_by(Product.id)
                 .all())
        pool_by_cat[cat] = prods

    seq = 0
    added_orders = 0
    for email, profile in REVIEW_USER_PROFILES.items():
        user = User.query.filter_by(email=email).first()
        if user is None:
            continue
        city, state, zc, line1, phone, ctype, last4, em, ey = profile
        # SavedAddress
        if not SavedAddress.query.filter_by(user_id=user.id).first():
            db.session.add(SavedAddress(
                user_id=user.id, label='Home', full_name=user.name,
                phone=phone, address_line1=line1, address_line2='',
                city=city, state=state, zip_code=zc, is_default=True,
            ))
        # PaymentMethod
        if not PaymentMethod.query.filter_by(user_id=user.id).first():
            db.session.add(PaymentMethod(
                user_id=user.id, card_type=ctype, last4=last4,
                exp_month=em, exp_year=ey, cardholder_name=user.name, is_default=True,
            ))
        db.session.flush()
        addr = SavedAddress.query.filter_by(user_id=user.id, is_default=True).first()
        pm = PaymentMethod.query.filter_by(user_id=user.id, is_default=True).first()
        # 1-2 orders per user, drawn deterministically from category pools
        cats_for_user = [
            ['electronics', 'home'],
            ['books', 'beauty'],
            ['computers', 'sports'],
            ['fashion', 'toys'],
        ][seq % 4]
        order_count = 1 + (seq % 2)
        for n in range(order_count):
            cat = cats_for_user[n % len(cats_for_user)]
            prods = pool_by_cat.get(cat) or []
            if not prods:
                continue
            prod = prods[(seq * 13 + n * 7) % len(prods)]
            qty = 1 + ((seq + n) % 2)
            subtotal = round(prod.price * qty, 2)
            ship_cost = 0.0 if (user.is_prime or subtotal > 35) else 5.99
            tax = round(subtotal * 0.0825, 2)
            total = round(subtotal + ship_cost + tax, 2)
            days_ago = 5 + (seq * 3 + n * 7) % 30
            status = 'delivered' if days_ago >= 10 else 'shipped'
            order_number = f"112-{4000000 + seq * 31 + n * 7:07d}-{1000000 + (seq * 53 + n * 11):07d}"
            order = Order(
                user_id=user.id, order_number=order_number, status=status,
                subtotal=subtotal, shipping=ship_cost, tax=tax, total=total,
                ship_name=addr.full_name, ship_address=addr.address_line1,
                ship_city=addr.city, ship_state=addr.state, ship_zip=addr.zip_code,
                payment_method=pm.card_type, payment_last4=pm.last4,
                created_at=base_date - timedelta(days=days_ago),
                delivery_estimate=(base_date + timedelta(days=2 + (n % 4))).strftime('%A, %B %d'),
            )
            db.session.add(order)
            db.session.flush()
            db.session.add(OrderItem(
                order_id=order.id, product_id=prod.id,
                product_name=prod.name, product_image=prod.image,
                variant='', quantity=qty, price=prod.price,
            ))
            added_orders += 1
        seq += 1
    db.session.commit()
    return added_orders


def seed_wishlists(db, User, Product, WishlistItem):
    """Seed 35+ wishlist items across many users. Idempotent: skip if any exist."""
    if WishlistItem.query.count() > 0:
        return 0

    # Distribution: alice/bob/carol/david/demo each 3-5, 12 review users 1-2 each
    plan = [
        ('alice.j@test.com', 5, ['electronics', 'computers', 'home', 'books', 'fashion']),
        ('bob.c@test.com',   4, ['electronics', 'sports', 'computers', 'books']),
        ('carol.d@test.com', 5, ['fashion', 'beauty', 'home', 'books', 'electronics']),
        ('david.k@test.com', 4, ['electronics', 'computers', 'sports', 'toys']),
        ('demo@amazon.com',  3, ['books', 'home', 'beauty']),
        ('jessica.m@test.com', 2, ['beauty', 'fashion']),
        ('rahul.p@test.com',   2, ['computers', 'books']),
        ('samir.k@test.com',   2, ['electronics', 'sports']),
        ('emily.r@test.com',   2, ['beauty', 'home']),
        ('marcus.t@test.com',  2, ['sports', 'electronics']),
        ('priya.s@test.com',   2, ['books', 'fashion']),
        ('diana.l@test.com',   1, ['toys']),
        ('tommy.h@test.com',   1, ['sports']),
        ('linda.w@test.com',   1, ['home']),
        ('greg.f@test.com',    1, ['computers']),
        ('aisha.n@test.com',   1, ['beauty']),
        ('kevin.o@test.com',   1, ['electronics']),
    ]

    pool_by_cat = {}
    for cat in set(c for _, _, cats in plan for c in cats):
        pool_by_cat[cat] = (Product.query.filter_by(category_slug=cat)
                            .order_by(Product.id).all())

    added = 0
    seed_offset = 0
    for email, count, cats in plan:
        user = User.query.filter_by(email=email).first()
        if user is None:
            continue
        for n in range(count):
            cat = cats[n % len(cats)]
            prods = pool_by_cat.get(cat) or []
            if not prods:
                continue
            prod = prods[(seed_offset * 17 + n * 5) % len(prods)]
            if WishlistItem.query.filter_by(user_id=user.id, product_id=prod.id).first():
                continue
            days_ago = 3 + (seed_offset * 2 + n) % 60
            db.session.add(WishlistItem(
                user_id=user.id, product_id=prod.id,
                added_at=REFERENCE_DATE - timedelta(days=days_ago),
            ))
            added += 1
        seed_offset += 1
    db.session.commit()
    return added


def seed_extra_carts(db, User, Product, CartItem):
    """Bring total cart items to 15+ across many users. Idempotent: skip if total >= 15."""
    if CartItem.query.count() >= 15:
        return 0

    plan = [
        ('bob.c@test.com', [('books', 'Format: Paperback'), ('electronics', '')]),
        ('carol.d@test.com', [('fashion', 'Size: M, Color: Black'), ('beauty', ''), ('home', '')]),
        ('david.k@test.com', [('computers', ''), ('sports', '')]),
        ('jessica.m@test.com', [('beauty', '')]),
        ('rahul.p@test.com', [('books', 'Format: Paperback')]),
        ('emily.r@test.com', [('home', '')]),
        ('marcus.t@test.com', [('sports', '')]),
        ('priya.s@test.com', [('books', 'Format: Hardcover')]),
    ]

    pool_by_cat = {}
    for _, items in plan:
        for cat, _v in items:
            if cat not in pool_by_cat:
                pool_by_cat[cat] = (Product.query.filter_by(category_slug=cat)
                                    .order_by(Product.id).all())

    added = 0
    offset = 0
    for email, items in plan:
        user = User.query.filter_by(email=email).first()
        if user is None:
            continue
        for n, (cat, variant) in enumerate(items):
            prods = pool_by_cat.get(cat) or []
            if not prods:
                continue
            prod = prods[(offset * 11 + n * 7) % len(prods)]
            if CartItem.query.filter_by(user_id=user.id, product_id=prod.id).first():
                continue
            qty = 1 + ((offset + n) % 2)
            days_ago = 1 + (offset + n) % 14
            db.session.add(CartItem(
                user_id=user.id, product_id=prod.id, quantity=qty,
                variant=variant,
                added_at=REFERENCE_DATE - timedelta(days=days_ago),
            ))
            added += 1
        offset += 1
    db.session.commit()
    return added


RETURN_REASONS = [
    ('defective', "Item arrived damaged or stopped working"),
    ('wrong_item', "Wrong item was shipped"),
    ('doesnt_fit', "Size or fit was wrong"),
    ('changed_mind', "No longer needed"),
    ('not_as_described', "Item not as described"),
    ('better_price', "Found a better price elsewhere"),
]


def seed_returns(db, Order, OrderItem, Return, ReturnItem):
    """Seed 12+ returns from delivered orders. Idempotent: skip if any exist."""
    if Return.query.count() > 0:
        return 0

    delivered = (Order.query.filter_by(status='delivered')
                 .order_by(Order.id).all())
    added = 0
    for idx, order in enumerate(delivered[:14]):
        items = order.items
        if not items:
            continue
        # Pick subset of items to return
        items_to_return = items[: 1 + (idx % len(items))]
        reason_key, reason_text = RETURN_REASONS[idx % len(RETURN_REASONS)]
        refund_method = 'original_payment' if idx % 3 != 2 else 'gift_card'
        refund_amount = round(
            sum(item.price * item.quantity for item in items_to_return), 2
        )
        # Status mix: requested / approved / completed
        status = ['requested', 'approved', 'completed'][idx % 3]
        days_ago = 1 + (idx * 2) % 25
        r = Return(
            order_id=order.id, user_id=order.user_id, status=status,
            refund_method=refund_method, refund_amount=refund_amount,
            created_at=REFERENCE_DATE - timedelta(days=days_ago),
        )
        db.session.add(r)
        db.session.flush()
        for item in items_to_return:
            db.session.add(ReturnItem(
                return_id=r.id, order_item_id=item.id,
                product_name=item.product_name, quantity=item.quantity,
                reason=reason_key,
            ))
        added += 1
    db.session.commit()
    return added


def run_extras(db, User, Product, Category, CartItem, Order, OrderItem,
               WishlistItem, SavedAddress, PaymentMethod, Return, ReturnItem):
    """Top-level entry that runs every extras seeder in order."""
    seed_review_users(db, User)
    seed_extra_products(db, Product)
    # R2: bulk-add ~800 more products via Open Library + brand SKU synthesis.
    # Must run before orders/wishlists/carts so they can reference new products.
    try:
        from seed_bulk import seed_bulk_products
        seed_bulk_products(db, Product)
    except Exception as e:  # surface error, don't mask
        raise RuntimeError(f"seed_bulk_products failed: {e}") from e
    # R3: brand × model × color × storage matrix + Open Library books pass 2.
    # Runs after seed_bulk so it sees the already-inserted products and only
    # adds genuinely new SKUs (idempotent via slug uniqueness).
    try:
        from seed_matrix import seed_matrix
        seed_matrix(db, Product)
    except Exception as e:
        raise RuntimeError(f"seed_matrix failed: {e}") from e
    # R4: polish pass — pushes catalog past 5500 products with brand-fresh
    # SKU suffixes + R4-only templates + an extra Open Library books slice.
    try:
        from seed_polish import seed_polish
        seed_polish(db, Product)
    except Exception as e:
        raise RuntimeError(f"seed_polish failed: {e}") from e
    # R5: push catalog past 8000 with quality fields (climate-pledge,
    # made-in, recyclable-packaging, age-range, one-day-shipping,
    # subscribe-and-save) + ~7% sold-out coverage for OOS tasks.
    try:
        from seed_r5 import seed_r5
        seed_r5(db, Product)
    except Exception as e:
        raise RuntimeError(f"seed_r5 failed: {e}") from e
    # R6: push catalog past 18000 by replaying every prior template pool
    # with R6_SUFFIXES + R6_NEW_TEMPLATES long-tail categories. Adds
    # low-stock (~12%) + notify-when-back (~6%) coverage on top of R5.
    try:
        from seed_r6 import seed_r6
        seed_r6(db, Product)
    except Exception as e:
        raise RuntimeError(f"seed_r6 failed: {e}") from e
    # R7: push catalog past 29500 by adding Amazon Fresh + Whole Foods +
    # Audible + Kindle storefront templates, plus replaying prior pools with
    # R7_SUFFIXES. Adds dietary / narrator / listen-time / KU fields.
    try:
        from seed_r7 import seed_r7
        seed_r7(db, Product)
    except Exception as e:
        raise RuntimeError(f"seed_r7 failed: {e}") from e
    # R8: push catalog past 39500 by adding cross-brand Amazon Fashion
    # (luxury / streetwear / athleisure) + Beauty (clean / luxury /
    # drugstore) templates, plus replaying prior pools with R8_SUFFIXES.
    # Adds fit-type / skin-type / cruelty-free / vegan-formula /
    # business-prime-eligible quality fields.
    try:
        from seed_r8 import seed_r8
        seed_r8(db, Product)
    except Exception as e:
        raise RuntimeError(f"seed_r8 failed: {e}") from e
    seed_extra_orders(db, User, Order, OrderItem, Product, SavedAddress, PaymentMethod)
    seed_wishlists(db, User, Product, WishlistItem)
    seed_extra_carts(db, User, Product, CartItem)
    seed_returns(db, Order, OrderItem, Return, ReturnItem)
    _normalize_seed_db_layout(db)


def _normalize_seed_db_layout(db):
    """Re-emit indexes in alpha order + VACUUM so rebuilds match byte-for-byte.

    Fixes the SQLAlchemy set-iteration non-determinism documented in
    harden-env/gotchas.md item #2. Runs only when this is a fresh seed (no
    sentinel row); safe to call on warm restart.
    """
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
    # VACUUM must be outside a transaction
    raw = db.engine.raw_connection()
    raw.isolation_level = None
    try:
        raw.execute("VACUUM")
    finally:
        raw.close()
