#!/usr/bin/env python3
"""Seed data generator for Amazon mirror.

Creates realistic products with real scraped Amazon images. Images are picked
from the scraped directories based on size/pattern heuristics.
"""
import os
import re
import json
import random
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
IMG_DIR = os.path.join(BASE_DIR, "static", "images")


def list_sized(subdir, min_size=3000):
    """Return list of (filename, size) for images in a directory."""
    path = os.path.join(IMG_DIR, subdir)
    out = []
    if not os.path.isdir(path):
        return out
    for f in os.listdir(path):
        if f.lower().endswith(('.jpg', '.jpeg', '.png', '.webp')):
            full = os.path.join(path, f)
            try:
                size = os.path.getsize(full)
                if size >= min_size and 'sprite' not in f.lower() and 'shadow' not in f.lower():
                    out.append((f, size, f"/static/images/{subdir}/{f}"))
            except OSError:
                pass
    out.sort(key=lambda x: -x[1])
    return out


def pool(subdirs, min_size=3000):
    """Combined pool of images from multiple directories."""
    result = []
    for sd in subdirs:
        result.extend(list_sized(sd, min_size))
    result.sort(key=lambda x: -x[1])
    return result


CATEGORIES = [
    ('Electronics', 'electronics', '📱'),
    ('Computers', 'computers', '💻'),
    ('Home & Kitchen', 'home', '🏠'),
    ('Fashion', 'fashion', '👕'),
    ('Books', 'books', '📚'),
    ('Beauty', 'beauty', '💄'),
    ('Sports', 'sports', '⚽'),
    ('Toys', 'toys', '🧸'),
    # R7 — Amazon Fresh + Whole Foods + Audible + Kindle storefronts.
    ('Grocery', 'grocery', '🛒'),
    ('Audible', 'audible', '🎧'),
    ('Kindle Store', 'kindle', '📖'),
]


# Product seed definitions — real realistic Amazon product data
PRODUCTS = [
    # --- Electronics ---
    {
        'name': 'Echo Dot (5th Gen) Smart Speaker with Alexa',
        'brand': 'Amazon',
        'category': 'electronics', 'subcategory': 'Smart Home',
        'price': 49.99, 'list_price': 59.99,
        'description': 'Our best sounding Echo Dot yet - Enjoy an improved audio experience with Echo Dot for clearer vocals, deeper bass and vibrant sound in any room. Ready to help - Ask Alexa to play music, answer questions, play the news, check the weather, set alarms, control compatible smart home devices, and more.',
        'features': [
            'BETTER AUDIO EXPERIENCE – with clearer vocals, deeper bass and vibrant sound',
            'YOUR FAVORITE MUSIC AND CONTENT – Stream songs from Amazon Music, Apple Music, Spotify, and more',
            'HELPFUL ROUTINES – Set routines like "Alexa, good morning" for news, weather, and more',
            'VOICE CONTROL YOUR SMART HOME – Compatible with Ring, Philips Hue, and more',
            'DESIGNED TO PROTECT YOUR PRIVACY – built with multiple layers of privacy controls'
        ],
        'specs': {
            'Dimensions': '3.9" x 3.9" x 3.5"',
            'Weight': '10.7 oz',
            'Connectivity': 'Wi-Fi, Bluetooth',
            'Audio': '1.73" front-firing speaker',
            'Microphones': '4 far-field',
            'Color': 'Charcoal'
        },
        'variants': {'color': ['Charcoal', 'Glacier White', 'Deep Sea Blue']},
        'rating': 4.7, 'review_count': 48215,
        'is_featured': True, 'is_deal': True, 'is_bestseller': True,
        'img_source': ['homepage', 'search_electronics']
    },
    {
        'name': 'Apple AirPods Pro (2nd Generation) Wireless Earbuds',
        'brand': 'Apple',
        'category': 'electronics', 'subcategory': 'Headphones',
        'price': 199.00, 'list_price': 249.00,
        'description': 'AirPods Pro feature up to 2x more Active Noise Cancellation, Adaptive Transparency, and Personalized Spatial Audio. With touch control, you can easily adjust volume with a swipe.',
        'features': [
            'Active Noise Cancellation reduces unwanted background noise',
            'Adaptive Transparency lets outside sounds in while reducing loud environmental noise',
            'Personalized Spatial Audio with dynamic head tracking',
            'Touch control lets you swipe to adjust volume',
            'MagSafe Charging Case with U1 chip delivers more charges'
        ],
        'specs': {
            'Battery Life': 'Up to 6 hours listening',
            'Charging': 'MagSafe, Qi, Lightning',
            'Connectivity': 'Bluetooth 5.3',
            'Water Resistance': 'IPX4',
            'Chip': 'H2'
        },
        'variants': {'color': ['White']},
        'rating': 4.6, 'review_count': 62130,
        'is_featured': True, 'is_deal': True,
        'img_source': ['search_headphones', 'search_electronics']
    },
    {
        'name': 'Sony WH-1000XM5 Wireless Noise Canceling Headphones',
        'brand': 'Sony',
        'category': 'electronics', 'subcategory': 'Headphones',
        'price': 328.00, 'list_price': 399.99,
        'description': 'Industry-leading noise canceling with Auto NC Optimizer. Crystal clear hands-free calling. Up to 30-hour battery life with quick charging.',
        'features': [
            'Industry-leading noise cancellation',
            '30 hours of battery life',
            'Crystal clear phone calls with 4 beamforming microphones',
            'Multi-point connection to two devices simultaneously',
            'Adaptive Sound Control'
        ],
        'specs': {
            'Driver': '30mm',
            'Battery': '30 hours',
            'Weight': '250g',
            'Bluetooth': '5.2',
            'Color': 'Black'
        },
        'variants': {'color': ['Black', 'Silver', 'Midnight Blue']},
        'rating': 4.5, 'review_count': 23415,
        'is_featured': True, 'is_bestseller': True,
        'img_source': ['search_headphones']
    },
    {
        'name': 'Fire TV Stick 4K Max streaming device',
        'brand': 'Amazon',
        'category': 'electronics', 'subcategory': 'Streaming',
        'price': 39.99, 'list_price': 59.99,
        'description': 'Next-gen streaming with more power and storage. Stunning 4K Ultra HD, Dolby Vision, HDR10+, Dolby Atmos. Cinematic experiences powered by Wi-Fi 6E.',
        'features': [
            'Next-gen streaming with Wi-Fi 6E support',
            'Stunning 4K Ultra HD picture quality',
            'Dolby Vision, HDR10, HDR10+, HLG, and Dolby Atmos',
            'Alexa Voice Remote with TV controls',
            'Free and live TV - Access over 200,000 free movies and TV episodes'
        ],
        'specs': {
            'Resolution': '4K Ultra HD',
            'HDR': 'Dolby Vision, HDR10, HDR10+, HLG',
            'Audio': 'Dolby Atmos',
            'Wi-Fi': 'Wi-Fi 6E',
            'Storage': '16 GB'
        },
        'variants': {},
        'rating': 4.7, 'review_count': 91232,
        'is_featured': True, 'is_deal': True,
        'img_source': ['homepage', 'search_electronics']
    },
    {
        'name': 'Kindle Paperwhite (16 GB) – Now with a 6.8" display and adjustable warm light',
        'brand': 'Amazon',
        'category': 'electronics', 'subcategory': 'E-readers',
        'price': 149.99, 'list_price': 159.99,
        'description': 'The perfect reading experience with a glare-free 6.8" display and adjustable warm light. Waterproof, so you can read and relax with confidence.',
        'features': [
            '6.8" glare-free display with 300 ppi',
            'Adjustable warm light',
            'Weeks of battery life',
            'Waterproof (IPX8)',
            '16 GB of storage'
        ],
        'specs': {
            'Display': '6.8" glare-free, 300 ppi',
            'Storage': '16 GB',
            'Battery': '10 weeks',
            'Waterproof': 'IPX8',
            'Weight': '205g'
        },
        'variants': {'color': ['Black', 'Denim', 'Agave Green']},
        'rating': 4.6, 'review_count': 34215,
        'is_bestseller': True,
        'img_source': ['homepage']
    },
    {
        'name': 'Samsung 65" Class QN90C Neo QLED 4K Smart TV',
        'brand': 'Samsung',
        'category': 'electronics', 'subcategory': 'TVs',
        'price': 1499.99, 'list_price': 1899.99,
        'description': 'Experience stunning picture quality with Neo QLED technology. Quantum Mini LEDs deliver extraordinary brightness and contrast.',
        'features': [
            'Neo QLED 4K technology',
            'Quantum Mini LEDs',
            'Neural Quantum Processor 4K',
            '120Hz Motion Xcelerator',
            'Dolby Atmos object tracking sound'
        ],
        'specs': {
            'Display': '65" 4K',
            'Refresh Rate': '120Hz',
            'HDR': 'Quantum HDR',
            'Sound': '60W 4.2.2ch',
            'Smart Platform': 'Tizen'
        },
        'variants': {'size': ['55"', '65"', '75"', '85"']},
        'rating': 4.5, 'review_count': 8523,
        'is_deal': True,
        'img_source': ['search_electronics']
    },

    # --- Computers ---
    {
        'name': 'Apple MacBook Air 13.6" Laptop with M2 Chip',
        'brand': 'Apple',
        'category': 'computers', 'subcategory': 'Laptops',
        'price': 999.00, 'list_price': 1199.00,
        'description': 'Strikingly thin and fast so you can work, play, or create anything anywhere. Apple M2 chip. Superfast memory. Next-generation storage.',
        'features': [
            'Apple M2 chip for a giant leap in performance',
            '13.6-inch Liquid Retina display',
            'Up to 18 hours of battery life',
            'Fanless design',
            '1080p FaceTime HD camera'
        ],
        'specs': {
            'Display': '13.6" Liquid Retina',
            'Chip': 'Apple M2',
            'Memory': '8GB unified',
            'Storage': '256GB SSD',
            'Battery': 'Up to 18 hours',
            'Weight': '2.7 lb'
        },
        'variants': {
            'color': ['Midnight', 'Starlight', 'Space Gray', 'Silver'],
            'storage': ['256GB', '512GB', '1TB']
        },
        'rating': 4.8, 'review_count': 15420,
        'is_featured': True, 'is_bestseller': True,
        'img_source': ['search_laptop']
    },
    {
        'name': 'HP 15.6" Laptop with Intel Core i5',
        'brand': 'HP',
        'category': 'computers', 'subcategory': 'Laptops',
        'price': 479.99, 'list_price': 599.99,
        'description': 'A reliable laptop for everyday work and entertainment. Intel Core i5 processor with 8GB RAM and 256GB SSD for responsive performance.',
        'features': [
            'Intel Core i5 processor',
            '15.6" HD display',
            '8GB DDR4 memory',
            '256GB PCIe SSD',
            'Windows 11 Home'
        ],
        'specs': {
            'Display': '15.6" HD',
            'Processor': 'Intel Core i5-1135G7',
            'Memory': '8GB',
            'Storage': '256GB SSD',
            'OS': 'Windows 11'
        },
        'variants': {'color': ['Silver', 'Gray']},
        'rating': 4.3, 'review_count': 5234,
        'is_deal': True,
        'img_source': ['search_laptop']
    },
    {
        'name': 'Logitech MX Master 3S Wireless Mouse',
        'brand': 'Logitech',
        'category': 'computers', 'subcategory': 'Accessories',
        'price': 99.99, 'list_price': 119.99,
        'description': 'Precision, comfort, and speed — for the ones who make things happen. MX Master 3S is a powerful, precise, and ergonomic mouse.',
        'features': [
            '8K DPI Any-Surface Darkfield tracking',
            'Quiet Clicks with 90% reduction in click sound',
            'MagSpeed electromagnetic scroll wheel',
            'Ergonomic sculpted design',
            'Up to 70 days on a single charge'
        ],
        'specs': {
            'Sensor': '8000 DPI Darkfield',
            'Buttons': '7',
            'Battery': 'Up to 70 days',
            'Connectivity': 'Bluetooth, USB-C',
            'Weight': '141g'
        },
        'variants': {'color': ['Graphite', 'Pale Gray', 'Black']},
        'rating': 4.6, 'review_count': 8412,
        'is_featured': True,
        'img_source': ['search_laptop']
    },
    {
        'name': 'SanDisk 1TB Ultra microSDXC UHS-I Memory Card',
        'brand': 'SanDisk',
        'category': 'computers', 'subcategory': 'Storage',
        'price': 89.99, 'list_price': 149.99,
        'description': 'Save time with transfer speeds up to 150 MB/s. Ideal for Android smartphones and tablets.',
        'features': [
            'Up to 150 MB/s transfer speed',
            'A1 rated for faster app performance',
            'Class 10 and U1 for Full HD video',
            'Waterproof, temperature-proof, X-ray proof',
            '10-year limited warranty'
        ],
        'specs': {
            'Capacity': '1TB',
            'Speed Class': 'Class 10 / U1 / A1',
            'Read Speed': '150 MB/s',
            'Interface': 'UHS-I',
            'Form Factor': 'microSDXC'
        },
        'variants': {'size': ['64GB', '128GB', '256GB', '512GB', '1TB']},
        'rating': 4.7, 'review_count': 42135,
        'is_deal': True, 'is_bestseller': True,
        'img_source': ['search_laptop']
    },
    {
        'name': 'Canon EOS Rebel T7 DSLR Camera with 18-55mm Lens',
        'brand': 'Canon',
        'category': 'electronics', 'subcategory': 'Cameras',
        'price': 499.00, 'list_price': 599.00,
        'description': 'Capture memorable moments with brilliant image quality using the Canon EOS Rebel T7 DSLR camera kit.',
        'features': [
            '24.1 Megapixel CMOS (APS-C) sensor',
            'Built-in Wi-Fi and NFC',
            '9-Point AF system',
            'Full HD 1080p video recording',
            'EF-S 18-55mm f/3.5-5.6 IS II lens included'
        ],
        'specs': {
            'Sensor': '24.1 MP CMOS APS-C',
            'Video': 'Full HD 1080p',
            'AF Points': '9',
            'Display': '3.0" LCD',
            'Weight': '475g'
        },
        'variants': {'kit': ['Body Only', '18-55mm Kit', '18-55 + 75-300 Kit']},
        'rating': 4.5, 'review_count': 16320,
        'is_featured': True,
        'img_source': ['search_camera']
    },
    {
        'name': 'GoPro HERO12 Black Action Camera',
        'brand': 'GoPro',
        'category': 'electronics', 'subcategory': 'Cameras',
        'price': 349.00, 'list_price': 399.00,
        'description': 'The most versatile HERO camera ever. Capture stunning 5.3K60 video and 27MP photos.',
        'features': [
            '5.3K60 + 4K120 Video',
            '27MP Photos',
            'HDR Video',
            'Waterproof to 33ft',
            'HyperSmooth 6.0 stabilization'
        ],
        'specs': {
            'Video': '5.3K60, 4K120',
            'Photo': '27MP',
            'Waterproof': '33ft (10m)',
            'Battery': '1720 mAh',
            'Weight': '153g'
        },
        'variants': {},
        'rating': 4.6, 'review_count': 7213,
        'is_deal': True,
        'img_source': ['search_camera']
    },

    # --- Home & Kitchen ---
    {
        'name': 'Instant Pot Duo 7-in-1 Electric Pressure Cooker',
        'brand': 'Instant Pot',
        'category': 'home', 'subcategory': 'Kitchen',
        'price': 89.99, 'list_price': 119.99,
        'description': '7 appliances in one: pressure cooker, slow cooker, rice cooker, steamer, sauté, yogurt maker, and warmer.',
        'features': [
            '7-in-1 functionality',
            '13 Smart Programs',
            '6 quart capacity',
            'Advanced safety features',
            'Stainless steel inner pot'
        ],
        'specs': {
            'Capacity': '6 Quart',
            'Programs': '13',
            'Material': 'Stainless Steel',
            'Power': '1000W',
            'Dishwasher Safe': 'Yes'
        },
        'variants': {'size': ['3 Quart', '6 Quart', '8 Quart']},
        'rating': 4.7, 'review_count': 182304,
        'is_bestseller': True, 'is_deal': True,
        'img_source': ['search_home']
    },
    {
        'name': 'Ninja Foodi 10-in-1 XL Pro Air Fryer Oven',
        'brand': 'Ninja',
        'category': 'home', 'subcategory': 'Kitchen',
        'price': 199.99, 'list_price': 249.99,
        'description': '10 functions: Air Fry, Air Roast, Air Broil, Bake, Roast, Toast, Bagel, Dehydrate, Pizza, and Reheat.',
        'features': [
            '10 versatile cooking functions',
            'XL family-sized capacity',
            'Cooks 2 meals at once',
            'Air fry with up to 75% less fat',
            'Digital display'
        ],
        'specs': {
            'Capacity': '15.7 lb / 12 lb',
            'Functions': '10',
            'Temperature': 'Up to 450°F',
            'Power': '1800W'
        },
        'variants': {'color': ['Stainless Steel', 'Black']},
        'rating': 4.6, 'review_count': 12453,
        'is_featured': True,
        'img_source': ['search_home']
    },
    {
        'name': 'Keurig K-Elite Single Serve K-Cup Pod Coffee Maker',
        'brand': 'Keurig',
        'category': 'home', 'subcategory': 'Kitchen',
        'price': 169.99, 'list_price': 189.99,
        'description': 'Brew a rich and flavorful cup with the Keurig K-Elite single serve coffee maker. Choose from 5 brew sizes.',
        'features': [
            'Strong Brew increases strength and bold taste',
            'Iced setting brews hot over ice',
            '5 cup sizes: 4, 6, 8, 10, 12 oz',
            '75 oz removable reservoir',
            'Hot water on demand'
        ],
        'specs': {
            'Reservoir': '75 oz',
            'Cup Sizes': '5 (4-12 oz)',
            'Material': 'Metal accents',
            'Color': 'Brushed Slate'
        },
        'variants': {'color': ['Brushed Slate', 'Brushed Silver', 'Brushed Gold']},
        'rating': 4.5, 'review_count': 48203,
        'is_deal': True,
        'img_source': ['search_home']
    },
    {
        'name': 'KitchenAid Classic Series 4.5 Quart Stand Mixer',
        'brand': 'KitchenAid',
        'category': 'home', 'subcategory': 'Kitchen',
        'price': 279.99, 'list_price': 329.99,
        'description': 'Tilt-head design for easy access to mix bowls. 10 speeds for nearly any task. Includes flat beater, dough hook, and wire whip.',
        'features': [
            '4.5 quart stainless steel bowl',
            '10 speed slide control',
            'Tilt-head design',
            'Flat beater, dough hook, wire whip included',
            'Compatible with over 10 optional attachments'
        ],
        'specs': {
            'Capacity': '4.5 Quart',
            'Motor': '275W',
            'Speeds': '10',
            'Attachments': '3 included'
        },
        'variants': {'color': ['White', 'Empire Red', 'Onyx Black', 'Aqua Sky']},
        'rating': 4.8, 'review_count': 25430,
        'is_featured': True, 'is_bestseller': True,
        'img_source': ['search_home']
    },
    {
        'name': 'iRobot Roomba i7+ (7550) Robot Vacuum with Auto Dirt Disposal',
        'brand': 'iRobot',
        'category': 'home', 'subcategory': 'Cleaning',
        'price': 599.99, 'list_price': 799.99,
        'description': 'Empties itself for up to 60 days. Learns your home and cleans the way you want.',
        'features': [
            'Automatic dirt disposal for up to 60 days',
            'Smart mapping technology',
            'Clean specific rooms with voice commands',
            '10x the suction power',
            'Compatible with Alexa and Google'
        ],
        'specs': {
            'Suction': '10x Power-Lifting',
            'Navigation': 'vSLAM',
            'Battery Life': '75 minutes',
            'Recharge': 'Auto recharge and resume'
        },
        'variants': {},
        'rating': 4.4, 'review_count': 7843,
        'is_deal': True,
        'img_source': ['search_home']
    },
    {
        'name': 'Dyson V11 Cordless Stick Vacuum Cleaner',
        'brand': 'Dyson',
        'category': 'home', 'subcategory': 'Cleaning',
        'price': 469.99, 'list_price': 599.99,
        'description': 'Intelligently optimizes suction and run time. Up to 60 minutes of fade-free power.',
        'features': [
            'Up to 60 minutes run time',
            'Intelligent suction optimization',
            'LCD screen shows remaining run time',
            'High Torque cleaner head',
            'Whole-machine filtration'
        ],
        'specs': {
            'Run Time': 'Up to 60 min',
            'Bin Capacity': '0.2 gal',
            'Weight': '6.68 lbs',
            'Modes': 'Eco, Auto, Boost'
        },
        'variants': {'color': ['Blue', 'Nickel/Red']},
        'rating': 4.5, 'review_count': 9234,
        'is_featured': True,
        'img_source': ['search_home']
    },

    # --- Fashion ---
    {
        'name': "Levi's Men's 501 Original Fit Jeans",
        'brand': "Levi's",
        'category': 'fashion', 'subcategory': "Men's",
        'price': 49.99, 'list_price': 69.50,
        'description': "The Levi's 501 Original Fit Jean is a cultural icon that has remained unchanged since 1873. Straight leg, button fly, and a timeless fit.",
        'features': [
            'Straight leg, button fly',
            '100% cotton (varies by wash)',
            'Sits at waist',
            'Classic 5-pocket styling',
            'Iconic leather patch'
        ],
        'specs': {
            'Fit': 'Original/Straight',
            'Rise': 'Mid-rise',
            'Material': '100% Cotton',
            'Closure': 'Button fly',
            'Origin': 'Imported'
        },
        'variants': {
            'size': ['30x30', '32x30', '32x32', '34x30', '34x32', '36x32', '38x32'],
            'color': ['Medium Wash', 'Dark Wash', 'Black', 'Light Stonewash']
        },
        'rating': 4.4, 'review_count': 52430,
        'is_bestseller': True,
        'img_source': ['search_fashion']
    },
    {
        'name': 'Hanes Men\'s ComfortSoft T-Shirt (Pack of 4)',
        'brand': 'Hanes',
        'category': 'fashion', 'subcategory': "Men's",
        'price': 19.99, 'list_price': 29.99,
        'description': 'Soft ringspun cotton tees with reinforced neck for extra durability.',
        'features': [
            'Soft ringspun cotton',
            'Reinforced neck for durability',
            'Tag-free label',
            'Pack of 4',
            'Machine washable'
        ],
        'specs': {
            'Material': '100% Cotton',
            'Pack Size': '4',
            'Care': 'Machine wash'
        },
        'variants': {
            'size': ['S', 'M', 'L', 'XL', 'XXL'],
            'color': ['White', 'Black', 'Gray', 'Navy']
        },
        'rating': 4.5, 'review_count': 87234,
        'is_deal': True, 'is_bestseller': True,
        'img_source': ['search_fashion']
    },
    {
        'name': 'Champion Men\'s Powerblend Fleece Pullover Hoodie',
        'brand': 'Champion',
        'category': 'fashion', 'subcategory': "Men's",
        'price': 34.99, 'list_price': 45.00,
        'description': 'Our ultra-soft Powerblend fleece pullover hoodie is built to last with less shrinkage and less pilling.',
        'features': [
            'Powerblend fleece for softness',
            'Less shrinkage, less pilling',
            'Kangaroo pocket',
            'Ribbed cuffs and hem',
            'Embroidered Champion C logo'
        ],
        'specs': {
            'Material': '50% Cotton, 50% Polyester',
            'Fit': 'Regular',
            'Care': 'Machine wash'
        },
        'variants': {
            'size': ['S', 'M', 'L', 'XL', 'XXL'],
            'color': ['Oxford Gray', 'Black', 'Navy', 'Red', 'Maroon']
        },
        'rating': 4.6, 'review_count': 12340,
        'is_featured': True,
        'img_source': ['search_fashion']
    },
    {
        'name': 'Adidas Women\'s Cloudfoam Pure Running Shoe',
        'brand': 'Adidas',
        'category': 'fashion', 'subcategory': "Women's Shoes",
        'price': 64.99, 'list_price': 80.00,
        'description': 'Lightweight knit upper and cushioned Cloudfoam midsole deliver all-day comfort.',
        'features': [
            'Knit upper for lightweight comfort',
            'Cloudfoam midsole',
            'Memory foam sockliner',
            'Rubber outsole for traction',
            'Versatile sneaker design'
        ],
        'specs': {
            'Upper': 'Textile',
            'Sole': 'Rubber',
            'Closure': 'Lace-up',
            'Weight': '7.1 oz'
        },
        'variants': {
            'size': ['5', '6', '7', '8', '9', '10', '11'],
            'color': ['White/Black', 'All Black', 'Pink/White', 'Gray/White']
        },
        'rating': 4.5, 'review_count': 28435,
        'is_featured': True, 'is_bestseller': True,
        'img_source': ['search_fashion']
    },
    {
        'name': 'Nike Men\'s Air Max 270 Running Shoes',
        'brand': 'Nike',
        'category': 'fashion', 'subcategory': "Men's Shoes",
        'price': 129.99, 'list_price': 150.00,
        'description': 'Inspired by Air Max icons, the Air Max 270 delivers unrivaled, all-day comfort with the tallest Air unit yet.',
        'features': [
            'Biggest Air Max heel ever',
            'Lightweight mesh upper',
            'Rubber waffle outsole',
            'Flex grooves for flexibility',
            'Iconic Air Max design'
        ],
        'specs': {
            'Upper': 'Mesh',
            'Midsole': 'Air Max',
            'Outsole': 'Rubber',
            'Drop': '32mm'
        },
        'variants': {
            'size': ['8', '9', '10', '11', '12', '13'],
            'color': ['Black/White', 'White/Red', 'Gray/Blue']
        },
        'rating': 4.6, 'review_count': 18923,
        'is_deal': True,
        'img_source': ['search_fashion']
    },
    {
        'name': 'Fossil Gen 6 Smartwatch',
        'brand': 'Fossil',
        'category': 'fashion', 'subcategory': 'Watches',
        'price': 179.00, 'list_price': 299.00,
        'description': 'Track your health, respond to notifications, and get help from Google Assistant — all from your wrist.',
        'features': [
            'Wear OS by Google',
            'Heart rate and SpO2 tracking',
            'Google Assistant built-in',
            'Fast charging',
            'Interchangeable straps'
        ],
        'specs': {
            'Case': '44mm stainless steel',
            'Battery': '24+ hours',
            'Storage': '8GB',
            'Connectivity': 'Bluetooth, Wi-Fi, GPS'
        },
        'variants': {'color': ['Silver', 'Black', 'Rose Gold', 'Blue']},
        'rating': 4.2, 'review_count': 6543,
        'is_deal': True,
        'img_source': ['search_fashion']
    },

    # --- Books ---
    {
        'name': 'Atomic Habits: An Easy & Proven Way to Build Good Habits',
        'brand': 'Avery',
        'category': 'books', 'subcategory': 'Self Help',
        'price': 14.99, 'list_price': 27.00,
        'description': 'The #1 New York Times bestseller. Over 15 million copies sold. Tiny Changes, Remarkable Results.',
        'features': [
            'Over 15 million copies sold',
            '#1 New York Times bestseller',
            'Practical strategies based on biology and psychology',
            'Inspiring stories from Olympic gold medalists and award-winning artists',
            'Learn how to overcome lack of motivation'
        ],
        'specs': {
            'Author': 'James Clear',
            'Publisher': 'Avery',
            'Pages': '320',
            'Format': 'Hardcover',
            'ISBN': '978-0735211292'
        },
        'variants': {'format': ['Hardcover', 'Paperback', 'Kindle', 'Audiobook']},
        'rating': 4.8, 'review_count': 143521,
        'is_bestseller': True, 'is_featured': True,
        'img_source': ['search_books']
    },
    {
        'name': 'The Psychology of Money',
        'brand': 'Harriman House',
        'category': 'books', 'subcategory': 'Business',
        'price': 12.99, 'list_price': 19.99,
        'description': '19 short stories exploring the strange ways people think about money and teaching you how to make better sense of one of life\'s most important topics.',
        'features': [
            'Timeless lessons on wealth, greed, and happiness',
            '19 short and engaging stories',
            'New York Times Best Seller',
            'Over 3 million copies sold'
        ],
        'specs': {
            'Author': 'Morgan Housel',
            'Publisher': 'Harriman House',
            'Pages': '256',
            'Format': 'Paperback'
        },
        'variants': {'format': ['Paperback', 'Hardcover', 'Kindle', 'Audiobook']},
        'rating': 4.7, 'review_count': 62134,
        'is_bestseller': True,
        'img_source': ['search_books']
    },
    {
        'name': 'Harry Potter and the Sorcerer\'s Stone (Book 1)',
        'brand': 'Scholastic',
        'category': 'books', 'subcategory': 'Fiction',
        'price': 10.99, 'list_price': 14.99,
        'description': 'Turning the envelope over, his hand trembling, Harry saw a purple wax seal bearing a coat of arms; a lion, an eagle, a badger and a snake surrounding a large letter H.',
        'features': [
            'Book 1 of the Harry Potter series',
            'Over 120 million copies sold',
            '#1 bestselling series',
            'Translated into 80+ languages'
        ],
        'specs': {
            'Author': 'J.K. Rowling',
            'Publisher': 'Scholastic',
            'Pages': '309',
            'Format': 'Paperback',
            'Age Range': '8-12 years'
        },
        'variants': {'format': ['Paperback', 'Hardcover', 'Kindle', 'Audiobook']},
        'rating': 4.9, 'review_count': 204321,
        'is_featured': True, 'is_bestseller': True,
        'img_source': ['search_books']
    },
    {
        'name': 'Where the Crawdads Sing',
        'brand': 'G.P. Putnam\'s Sons',
        'category': 'books', 'subcategory': 'Fiction',
        'price': 11.99, 'list_price': 26.00,
        'description': 'For years, rumors of the "Marsh Girl" haunted Barkley Cove, a quiet fishing village. A #1 New York Times bestseller.',
        'features': [
            '#1 New York Times Bestseller',
            'Over 15 million copies sold',
            'Oprah\'s Book Club Pick',
            'Major Motion Picture'
        ],
        'specs': {
            'Author': 'Delia Owens',
            'Publisher': 'G.P. Putnam\'s Sons',
            'Pages': '384',
            'Format': 'Hardcover'
        },
        'variants': {'format': ['Hardcover', 'Paperback', 'Kindle']},
        'rating': 4.8, 'review_count': 98234,
        'is_bestseller': True,
        'img_source': ['search_books']
    },
    {
        'name': 'The 48 Laws of Power',
        'brand': 'Penguin Books',
        'category': 'books', 'subcategory': 'Business',
        'price': 15.99, 'list_price': 25.00,
        'description': 'Amoral, cunning, ruthless, and instructive, this multi-million-copy New York Times bestseller is the definitive manual for anyone interested in gaining, observing, or defending against power.',
        'features': [
            'Multi-million copy bestseller',
            '48 distilled laws based on 3,000 years of history',
            'Used by executives, entrepreneurs, and students'
        ],
        'specs': {
            'Author': 'Robert Greene',
            'Publisher': 'Penguin Books',
            'Pages': '452',
            'Format': 'Paperback'
        },
        'variants': {'format': ['Paperback', 'Hardcover', 'Kindle']},
        'rating': 4.7, 'review_count': 47231,
        'is_bestseller': True,
        'img_source': ['search_books']
    },
    {
        'name': 'Sapiens: A Brief History of Humankind',
        'brand': 'Harper Perennial',
        'category': 'books', 'subcategory': 'History',
        'price': 13.99, 'list_price': 22.99,
        'description': 'From a renowned historian comes a groundbreaking narrative of humanity\'s creation and evolution.',
        'features': [
            'International bestseller',
            'Translated into 60 languages',
            '#1 New York Times bestseller',
            'Bill Gates recommended'
        ],
        'specs': {
            'Author': 'Yuval Noah Harari',
            'Publisher': 'Harper Perennial',
            'Pages': '464',
            'Format': 'Paperback'
        },
        'variants': {'format': ['Paperback', 'Hardcover', 'Kindle', 'Audiobook']},
        'rating': 4.6, 'review_count': 38234,
        'is_featured': True,
        'img_source': ['search_books']
    },

    # --- Beauty ---
    {
        'name': 'CeraVe Moisturizing Cream | Body and Face Moisturizer',
        'brand': 'CeraVe',
        'category': 'beauty', 'subcategory': 'Skincare',
        'price': 16.08, 'list_price': 19.99,
        'description': 'Developed with dermatologists, CeraVe Moisturizing Cream has a unique formula that provides 24-hour hydration.',
        'features': [
            '24-hour hydration',
            'Contains 3 essential ceramides',
            'Hyaluronic acid for skin hydration',
            'Non-comedogenic, fragrance-free',
            'For normal to dry skin'
        ],
        'specs': {
            'Size': '19 oz',
            'Type': 'Cream',
            'Skin Type': 'Normal to Dry',
            'Formulation': 'Fragrance-free, Non-comedogenic'
        },
        'variants': {'size': ['1.89 oz', '8 oz', '16 oz', '19 oz']},
        'rating': 4.7, 'review_count': 95432,
        'is_bestseller': True, 'is_deal': True,
        'img_source': ['homepage']
    },
    {
        'name': 'The Ordinary Niacinamide 10% + Zinc 1% Serum',
        'brand': 'The Ordinary',
        'category': 'beauty', 'subcategory': 'Skincare',
        'price': 7.90, 'list_price': 12.00,
        'description': 'A high-strength vitamin and mineral blemish formula featuring niacinamide and zinc.',
        'features': [
            'Reduces appearance of blemishes',
            'High 10% niacinamide concentration',
            'Balances sebum production',
            'Vegan, cruelty-free',
            'Alcohol-free'
        ],
        'specs': {
            'Size': '30ml',
            'Key Ingredients': 'Niacinamide 10%, Zinc 1%',
            'Type': 'Serum'
        },
        'variants': {'size': ['30ml', '60ml']},
        'rating': 4.4, 'review_count': 73421,
        'is_bestseller': True,
        'img_source': ['homepage']
    },
    {
        'name': 'Maybelline New York Sky High Waterproof Mascara',
        'brand': 'Maybelline',
        'category': 'beauty', 'subcategory': 'Makeup',
        'price': 8.94, 'list_price': 12.99,
        'description': 'Our first-ever mascara with bamboo extract for stretchable length and volume.',
        'features': [
            'Sky high length and volume',
            'Flexible bamboo-extract infused formula',
            'Waterproof, smudge-resistant',
            'Built-in primer',
            'Flex tower brush'
        ],
        'specs': {
            'Type': 'Mascara',
            'Formula': 'Waterproof',
            'Key Ingredient': 'Bamboo Extract'
        },
        'variants': {'color': ['Very Black', 'Blackest Black', 'Brown']},
        'rating': 4.5, 'review_count': 127845,
        'is_bestseller': True,
        'img_source': ['homepage']
    },
    {
        'name': 'Olaplex No. 3 Hair Perfector',
        'brand': 'Olaplex',
        'category': 'beauty', 'subcategory': 'Hair Care',
        'price': 28.00, 'list_price': 30.00,
        'description': 'At-home treatment that reduces breakage and strengthens all hair types.',
        'features': [
            'Reduces breakage',
            'Restores damaged hair',
            'Safe for color-treated hair',
            'Strengthens and rebuilds hair',
            'Use weekly for best results'
        ],
        'specs': {
            'Size': '3.3 oz',
            'Hair Type': 'All',
            'Formulation': 'Paraben-free, sulfate-free'
        },
        'variants': {'size': ['3.3 oz', '8.5 oz']},
        'rating': 4.6, 'review_count': 54321,
        'is_featured': True,
        'img_source': ['homepage']
    },

    # --- Sports ---
    {
        'name': 'YETI Rambler 20 oz Tumbler with MagSlider Lid',
        'brand': 'YETI',
        'category': 'sports', 'subcategory': 'Drinkware',
        'price': 35.00, 'list_price': 40.00,
        'description': 'Insulated stainless steel tumbler keeps drinks cold or hot. Shatter-resistant MagSlider lid.',
        'features': [
            'Double-wall vacuum insulation',
            'DuraCoat color that won\'t crack, peel or fade',
            'No sweat design',
            'Dishwasher safe',
            'MagSlider lid with magnet closure'
        ],
        'specs': {
            'Capacity': '20 oz',
            'Material': '18/8 Stainless Steel',
            'Insulation': 'Double-wall vacuum',
            'Dishwasher Safe': 'Yes'
        },
        'variants': {
            'color': ['Black', 'Navy', 'Sagebrush Green', 'Charcoal', 'Stainless'],
            'size': ['10 oz', '20 oz', '30 oz']
        },
        'rating': 4.8, 'review_count': 62341,
        'is_featured': True, 'is_bestseller': True,
        'img_source': ['homepage']
    },
    {
        'name': 'Stanley Quencher H2.0 FlowState Tumbler 40 oz',
        'brand': 'Stanley',
        'category': 'sports', 'subcategory': 'Drinkware',
        'price': 39.99, 'list_price': 45.00,
        'description': 'Introducing FlowState: an advanced lid construction featuring a rotating cover.',
        'features': [
            '40oz capacity holds enough to stay hydrated all day',
            'FlowState lid with rotating cover',
            'Double-wall vacuum insulated',
            'Car cup holder compatible',
            'Dishwasher safe'
        ],
        'specs': {
            'Capacity': '40 oz',
            'Material': '18/8 Stainless Steel',
            'Base': 'Fits standard car cup holders'
        },
        'variants': {
            'color': ['Rose Quartz', 'Charcoal', 'Polar', 'Cream', 'Lavender'],
            'size': ['20 oz', '30 oz', '40 oz', '64 oz']
        },
        'rating': 4.7, 'review_count': 43215,
        'is_bestseller': True,
        'img_source': ['homepage']
    },
    {
        'name': 'Hydro Flask Standard Mouth Bottle',
        'brand': 'Hydro Flask',
        'category': 'sports', 'subcategory': 'Drinkware',
        'price': 39.95, 'list_price': 44.95,
        'description': 'Stainless steel water bottle. Keeps drinks cold 24 hours, hot up to 12 hours.',
        'features': [
            'TempShield insulation',
            'Cold 24 hours / Hot 12 hours',
            'Pro-grade 18/8 stainless steel',
            'BPA-free and phthalate-free',
            'Color-last powder coat'
        ],
        'specs': {
            'Capacity': '21 oz',
            'Material': '18/8 Stainless Steel',
            'Weight': '14.3 oz',
            'Dimensions': '3" x 9.4"'
        },
        'variants': {
            'color': ['Pacific', 'Pepper', 'Alpine', 'Stone', 'Mint'],
            'size': ['18 oz', '21 oz', '24 oz', '32 oz', '40 oz']
        },
        'rating': 4.7, 'review_count': 28435,
        'is_featured': True,
        'img_source': ['homepage']
    },
    {
        'name': 'Fitbit Charge 6 Fitness Tracker',
        'brand': 'Fitbit',
        'category': 'sports', 'subcategory': 'Fitness',
        'price': 129.95, 'list_price': 159.95,
        'description': 'Advanced health and fitness tracker with built-in GPS, heart rate, and Google apps.',
        'features': [
            'Built-in GPS',
            'Heart rate and SpO2 tracking',
            'ECG and EDA sensors',
            'Google Maps and Google Wallet',
            '7-day battery life'
        ],
        'specs': {
            'Battery': '7 days',
            'Water Resistant': '50m',
            'Display': 'AMOLED',
            'GPS': 'Built-in'
        },
        'variants': {'color': ['Obsidian', 'Porcelain', 'Coral']},
        'rating': 4.3, 'review_count': 12432,
        'is_deal': True,
        'img_source': ['homepage']
    },

    # --- Toys ---
    {
        'name': "Columbia Women's Newton Ridge Plus Waterproof Hiking Boot",
        'brand': 'Columbia',
        'category': 'fashion', 'subcategory': 'Boots',
        'price': 89.95, 'list_price': 109.99,
        'description': "A waterproof women's hiking boot with superior traction and lightweight cushioning. Seam-sealed construction keeps feet dry on any trail. Omni-Grip advanced traction rubber outsole for grip on varied terrain.",
        'features': [
            'Waterproof full grain leather and mesh upper',
            'Seam-sealed waterproof construction',
            'Techlite lightweight midsole for comfort',
            'Omni-Grip non-marking traction rubber outsole',
            'Durable and supportive ankle-high design'
        ],
        'specs': {
            'Material': 'Full grain leather, mesh',
            'Sole': 'Rubber',
            'Closure': 'Lace-up',
            'Water Resistance': 'Waterproof',
            'Heel Height': '1.5 inches'
        },
        'variants': {
            'color': ['Elk/Mountain Red', 'Black/Storm', 'Quarry/Cool Wave'],
            'size': ['5', '5.5', '6', '6.5', '7', '7.5', '8', '8.5', '9', '9.5', '10']
        },
        'rating': 4.5, 'review_count': 32145,
        'feature_tags': ['waterproof', 'hiking', 'women', 'boots', 'outdoor', 'trail'],
        'is_featured': True,
        'img_source': ['homepage']
    },
    {
        'name': "KEEN Women's Targhee III Waterproof Hiking Boot",
        'brand': 'KEEN',
        'category': 'fashion', 'subcategory': 'Boots',
        'price': 134.95, 'list_price': 174.99,
        'description': "A rugged waterproof hiking boot for women. KEEN.DRY waterproof breathable membrane keeps feet dry. All-terrain rubber outsole with 4mm multi-directional lugs for superior grip.",
        'features': [
            'KEEN.DRY waterproof, breathable membrane',
            'Performance leather and mesh upper',
            'EVA midsole for lightweight cushioning',
            'All-terrain rubber outsole',
            'Secure lace-up closure'
        ],
        'specs': {
            'Material': 'Leather, textile',
            'Sole': 'Rubber',
            'Closure': 'Lace-up',
            'Water Resistance': 'Waterproof',
            'Weight': '14.4 oz per boot'
        },
        'variants': {
            'color': ['Magnet/Atlantic Blue', 'Boysenberry/Grape Wine', 'Alcatraz/Blue Turquoise'],
            'size': ['5', '5.5', '6', '6.5', '7', '7.5', '8', '8.5', '9', '9.5', '10', '11']
        },
        'rating': 4.6, 'review_count': 18742,
        'feature_tags': ['waterproof', 'hiking', 'women', 'boots', 'outdoor', 'trail', 'keen'],
        'is_bestseller': True,
        'img_source': ['homepage']
    },
    {
        'name': 'LEGO Classic Large Creative Brick Box 10698',
        'brand': 'LEGO',
        'category': 'toys', 'subcategory': 'Building',
        'price': 44.99, 'list_price': 59.99,
        'description': '790 LEGO pieces in 33 different colors. Inspires open-ended creative building.',
        'features': [
            '790 LEGO pieces',
            '33 different colors',
            'Includes windows, doors, wheels, eyes',
            'Compatible with all LEGO sets',
            'Age 4+'
        ],
        'specs': {
            'Pieces': '790',
            'Age': '4+',
            'Dimensions': "18.9" + '" x 14.4" x 7"'
        },
        'variants': {},
        'rating': 4.8, 'review_count': 62341,
        'is_bestseller': True, 'is_featured': True,
        'img_source': ['homepage']
    },
    {
        'name': 'Melissa & Doug Deluxe Wooden Multi-Activity Table',
        'brand': 'Melissa & Doug',
        'category': 'toys', 'subcategory': 'Activity Tables',
        'price': 99.99, 'list_price': 149.99,
        'description': 'Activity table with 4 sides: wooden puzzle, magnetic game, abacus, and chalkboard.',
        'features': [
            '4 activity sides',
            'Wooden puzzle with farm theme',
            'Chalkboard surface',
            'Magnetic number game',
            'Beaded abacus'
        ],
        'specs': {
            'Material': 'Wood',
            'Age': '3+',
            'Dimensions': '20" x 20" x 20"'
        },
        'variants': {},
        'rating': 4.6, 'review_count': 7834,
        'is_featured': True,
        'img_source': ['homepage']
    },
    {
        'name': 'Best Choice Products 12V Kids Licensed Ride On Car',
        'brand': 'Best Choice Products',
        'category': 'toys', 'subcategory': 'Ride-On Toys',
        'price': 189.99, 'list_price': 259.99,
        'description': 'Give your child the ultimate driving experience with this 12V electric ride on car. Features realistic design, working LED headlights, built-in music, horn, and parental remote control for safety. Supports up to 66 lbs with a top speed of 3.7 mph.',
        'features': [
            'Licensed design with authentic detailing',
            'Parental remote control for safe operation',
            'Built-in music, horn, and LED headlights',
            'Two driving speeds: 2.5 mph and 3.7 mph',
            'Rechargeable 12V battery with charger included',
            'Soft-start technology for smooth acceleration'
        ],
        'specs': {
            'Battery': '12V 7Ah rechargeable',
            'Max Weight': '66 lbs',
            'Speed': 'Up to 3.7 mph',
            'Age Range': '3-8 years',
            'Dimensions': '45.25" x 26.5" x 19.5"',
            'Charge Time': '8-12 hours',
            'Drive': '2 rear-wheel motors'
        },
        'variants': {
            'color': ['Black', 'White', 'Red'],
        },
        'rating': 4.4, 'review_count': 12543,
        'feature_tags': ['ride-on', 'car', 'electric', 'kids', 'remote-control', 'battery-powered'],
        'is_featured': True, 'is_bestseller': True,
        'img_source': ['homepage']
    },
]


def pick_image_from_sources(sources, used_set=None, min_size=5000):
    """Pick the best unused image from given source directories."""
    used_set = used_set or set()
    for src in sources:
        imgs = list_sized(src, min_size)
        for name, size, path in imgs:
            if path not in used_set:
                used_set.add(path)
                return path
    # Fallback: any image from source
    for src in sources:
        imgs = list_sized(src, 1000)
        if imgs:
            return imgs[0][2]
    return '/static/images/homepage/placeholder.jpg'


def pick_gallery_from_sources(sources, count, used_set=None, min_size=5000):
    """Pick `count` images from the given source directories."""
    used_set = used_set or set()
    picked = []
    all_imgs = []
    for src in sources:
        all_imgs.extend(list_sized(src, min_size))
    # Remove duplicates by filename prefix (same image at different sizes)
    seen_prefix = set()
    unique = []
    for name, size, path in all_imgs:
        prefix = name.split('.')[0].split('_')[0]
        if prefix not in seen_prefix:
            seen_prefix.add(prefix)
            unique.append((name, size, path))
    random.shuffle(unique)
    for name, size, path in unique:
        if path not in used_set:
            picked.append(path)
            used_set.add(path)
            if len(picked) >= count:
                break
    return picked


def slugify(text):
    s = re.sub(r'[^\w\s-]', '', text.lower())
    s = re.sub(r'[\s_-]+', '-', s).strip('-')
    return s[:100]


def run_seed(db, Category, Product, User, Review):
    """Populate the database."""
    random.seed(42)

    # Categories
    for name, slug, icon in CATEGORIES:
        if not Category.query.filter_by(slug=slug).first():
            db.session.add(Category(name=name, slug=slug, icon=icon,
                description=f'Shop the latest in {name}'))
    db.session.commit()

    # Create a demo user
    if not User.query.filter_by(email='demo@amazon.com').first():
        demo = User(email='demo@amazon.com', name='Demo Customer',
            phone='555-0100', address_line1='410 Terry Ave N',
            city='Seattle', state='WA', zip_code='98109')
        # Pinned bcrypt('demo1234') for byte-identical reset (see harden-env/gotchas.md).
        demo.password_hash = '$2b$12$J0Uv8FcB6BYbjUbI.0vy1uWyLVlC8Dazqq0.iQ.xnebVkCz83hS4O'
        db.session.add(demo)
        db.session.commit()

    # Products
    used_images = set()
    for p in PRODUCTS:
        slug = slugify(p['name'])
        if Product.query.filter_by(slug=slug).first():
            continue

        sources = p.get('img_source', ['homepage'])

        main_img = pick_image_from_sources(sources, used_images, min_size=5000)
        gallery = pick_gallery_from_sources(sources, random.randint(8, 15),
                                            used_images, min_size=4000)

        # If gallery is too small, pull more from other source directories
        if len(gallery) < 6:
            fallback = ['homepage', 'bestsellers', 'deals']
            extra = pick_gallery_from_sources(fallback, 6 - len(gallery),
                                              used_images, min_size=4000)
            gallery.extend(extra)

        product = Product(
            name=p['name'],
            slug=slug,
            brand=p.get('brand', ''),
            category_slug=p['category'],
            subcategory=p.get('subcategory', ''),
            description=p.get('description', ''),
            features=json.dumps(p.get('features', [])),
            specs=json.dumps(p.get('specs', {})),
            price=p['price'],
            list_price=p.get('list_price', p['price']),
            image=main_img,
            gallery_images=json.dumps(gallery),
            variant_options=json.dumps(p.get('variants', {})),
            stock=random.randint(20, 500),
            rating=p.get('rating', 4.5),
            review_count=p.get('review_count', 0),
            is_featured=p.get('is_featured', False),
            is_deal=p.get('is_deal', False),
            is_bestseller=p.get('is_bestseller', False),
            feature_tags=json.dumps(p.get('feature_tags', [])),
            deal_discount=0
        )
        if product.list_price and product.list_price > product.price:
            product.deal_discount = int(round(
                (product.list_price - product.price) / product.list_price * 100))
        db.session.add(product)

    db.session.commit()

    # Seed some sample reviews
    demo = User.query.filter_by(email='demo@amazon.com').first()
    if demo:
        sample_reviews = [
            (5, 'Amazing product!', 'I love this. Exceeded my expectations in every way.'),
            (4, 'Great value', 'Solid product for the price. Would recommend.'),
            (5, 'Five stars', 'Exactly as described. Fast shipping.'),
            (4, 'Good quality', 'Well made and works as expected.'),
            (5, 'Perfect', 'Just what I was looking for.'),
        ]
        for product in Product.query.limit(20).all():
            if not Review.query.filter_by(product_id=product.id, user_id=demo.id).first():
                rating, title, body = random.choice(sample_reviews)
                db.session.add(Review(
                    user_id=demo.id, product_id=product.id,
                    rating=rating, title=title, body=body))
    db.session.commit()

    # Add detailed reviews for Ride On Car products
    demo = User.query.filter_by(email='demo@amazon.com').first()
    if demo:
        ride_on_products = Product.query.filter(Product.name.ilike('%ride on car%')).all()
        ride_on_reviews = [
            (5, 'Best Birthday Gift Ever!',
             'We bought this for our 4-year-old son\'s birthday and it was the highlight of the party. '
             'The car looks absolutely amazing with realistic detailing and working LED headlights. '
             'Assembly took about 45 minutes with two people. The parental remote control is a lifesaver '
             'for younger kids who are still learning to steer. Battery lasts about 1-1.5 hours of '
             'continuous driving, which is plenty for an afternoon of fun. The soft-start feature prevents '
             'jerky movements. Highly recommend for any parent looking for an exciting gift.',
             'Jennifer M.'),
            (4, 'Great Ride-On Car - Minor Assembly Issues',
             'Overall this is a fantastic ride on car for the price. My daughter (age 5) loves driving it '
             'around the yard. The two speed settings are perfect - we use the slower speed in the driveway '
             'and the faster speed on flat grass. Sound effects and horn are fun but can be a bit loud. '
             'Only giving 4 stars because the assembly instructions could be clearer - a few steps were '
             'confusing and we had to watch YouTube videos. Once assembled though, the build quality is solid '
             'and the car handles well on various surfaces.',
             'David K.'),
            (5, 'Kids Cannot Get Enough of This Car',
             'This ride on car exceeded all expectations. The realistic design makes my 6-year-old feel like '
             'he\'s driving a real car. The remote control override gives us peace of mind. We\'ve had it for '
             '3 months now with daily use and the battery still holds a good charge. The tires grip well on '
             'both concrete and grass. Worth every penny - all the neighbor kids want one now!',
             'Sarah T.'),
        ]
        for product in ride_on_products:
            for rating, title, body, reviewer in ride_on_reviews:
                existing = Review.query.filter_by(product_id=product.id, title=title).first()
                if not existing:
                    db.session.add(Review(
                        user_id=demo.id, product_id=product.id,
                        rating=rating, title=title, body=body))

    db.session.commit()

    print(f"Seeded {Product.query.count()} products, {Category.query.count()} categories")
