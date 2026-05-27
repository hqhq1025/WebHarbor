"""
Apple GUI deepen — 25+ new HTML surfaces backfilling apple.com pages that the
mirror was missing.  Pure render_template; zero new API/JSON/GraphQL routes,
zero DB writes — instance_seed/*.db md5 unchanged.

Data here is pulled from apple.com (Oct 2025–May 2026 snapshot) for shape;
product names match the existing seeded Product table where possible.
"""
from flask import render_template, request, redirect, url_for, flash, abort
from flask_wtf.csrf import generate_csrf


# ---------------------------------------------------------------------------
# iPhone configurator data — /shop/buy-iphone/<model>
# ---------------------------------------------------------------------------
IPHONE_BUY = {
    "iphone-17-pro-max": {
        "name": "iPhone 17 Pro Max",
        "subtitle": "The ultimate iPhone.",
        "base_price": 1199.00,
        "image": "/static/images/iphone-17-pro-max.jpg",
        "colors": [
            {"name": "Natural Titanium", "hex": "#9c9389"},
            {"name": "Blue Titanium",    "hex": "#3c4858"},
            {"name": "White Titanium",   "hex": "#f0eee9"},
            {"name": "Black Titanium",   "hex": "#393937"},
        ],
        "storage": [
            {"size": "256GB", "delta":   0.00},
            {"size": "512GB", "delta": 200.00},
            {"size": "1TB",   "delta": 400.00},
            {"size": "2TB",   "delta": 800.00},
        ],
        "carrier": [
            {"id": "verizon",      "label": "Verizon"},
            {"id": "att",          "label": "AT&T"},
            {"id": "tmobile",      "label": "T-Mobile"},
            {"id": "connect_later","label": "Connect later"},
        ],
        "payment": [
            {"id": "monthly", "label": "Pay monthly with Apple Card Monthly Installments at 0% APR",
             "months": 24},
            {"id": "full",    "label": "Buy now and pay the full price."},
        ],
        "applecare": [
            {"id": "applecare_plus",       "label": "AppleCare+",                 "monthly":  9.99, "two_year": 199.00},
            {"id": "applecare_plus_theft", "label": "AppleCare+ with Theft & Loss","monthly": 13.49, "two_year": 269.00},
            {"id": "none",                 "label": "No AppleCare+ coverage",     "monthly":  0.00, "two_year":   0.00},
        ],
        "chip": "A19 Pro",
        "camera": "48MP Fusion + 48MP Ultra Wide + 48MP Telephoto (8x optical)",
        "display": "6.9\" Super Retina XDR with ProMotion, Always-On",
        "battery": "Up to 35 hours video playback",
    },
    "iphone-17-pro": {
        "name": "iPhone 17 Pro",
        "subtitle": "The ultimate iPhone.",
        "base_price": 999.00,
        "image": "/static/images/iphone-17-pro.jpg",
        "colors": [
            {"name": "Natural Titanium", "hex": "#9c9389"},
            {"name": "Blue Titanium",    "hex": "#3c4858"},
            {"name": "White Titanium",   "hex": "#f0eee9"},
            {"name": "Black Titanium",   "hex": "#393937"},
        ],
        "storage": [
            {"size": "128GB", "delta":   0.00},
            {"size": "256GB", "delta": 100.00},
            {"size": "512GB", "delta": 300.00},
            {"size": "1TB",   "delta": 500.00},
        ],
        "carrier": [
            {"id": "verizon",      "label": "Verizon"},
            {"id": "att",          "label": "AT&T"},
            {"id": "tmobile",      "label": "T-Mobile"},
            {"id": "connect_later","label": "Connect later"},
        ],
        "payment": [
            {"id": "monthly", "label": "Pay monthly with Apple Card Monthly Installments at 0% APR", "months": 24},
            {"id": "full",    "label": "Buy now and pay the full price."},
        ],
        "applecare": [
            {"id": "applecare_plus",       "label": "AppleCare+",                  "monthly":  9.99, "two_year": 199.00},
            {"id": "applecare_plus_theft", "label": "AppleCare+ with Theft & Loss","monthly": 13.49, "two_year": 269.00},
            {"id": "none",                 "label": "No AppleCare+ coverage",      "monthly":  0.00, "two_year":   0.00},
        ],
        "chip": "A19 Pro",
        "camera": "48MP Fusion + 48MP Ultra Wide + 48MP Telephoto (5x optical)",
        "display": "6.3\" Super Retina XDR with ProMotion, Always-On",
        "battery": "Up to 28 hours video playback",
    },
    "iphone-air": {
        "name": "iPhone Air",
        "subtitle": "The thinnest iPhone ever.",
        "base_price": 999.00,
        "image": "/static/images/iphone-air.jpg",
        "colors": [
            {"name": "Sky Blue", "hex": "#b2cee0"},
            {"name": "White",    "hex": "#f5f5f0"},
            {"name": "Gold",     "hex": "#e7d2a8"},
            {"name": "Black",    "hex": "#222222"},
        ],
        "storage": [
            {"size": "256GB", "delta":   0.00},
            {"size": "512GB", "delta": 200.00},
            {"size": "1TB",   "delta": 400.00},
        ],
        "carrier": [
            {"id": "verizon",      "label": "Verizon"},
            {"id": "att",          "label": "AT&T"},
            {"id": "tmobile",      "label": "T-Mobile"},
            {"id": "connect_later","label": "Connect later"},
        ],
        "payment": [
            {"id": "monthly", "label": "Pay monthly with Apple Card Monthly Installments at 0% APR", "months": 24},
            {"id": "full",    "label": "Buy now and pay the full price."},
        ],
        "applecare": [
            {"id": "applecare_plus",       "label": "AppleCare+",                  "monthly":  9.99, "two_year": 199.00},
            {"id": "applecare_plus_theft", "label": "AppleCare+ with Theft & Loss","monthly": 13.49, "two_year": 269.00},
            {"id": "none",                 "label": "No AppleCare+ coverage",      "monthly":  0.00, "two_year":   0.00},
        ],
        "chip": "A19 Pro",
        "camera": "48MP Fusion main camera",
        "display": "6.5\" Super Retina XDR with ProMotion, Always-On",
        "battery": "Up to 27 hours video playback",
    },
    "iphone-17": {
        "name": "iPhone 17",
        "subtitle": "Built for Apple Intelligence.",
        "base_price": 799.00,
        "image": "/static/images/iphone-17.jpg",
        "colors": [
            {"name": "Lavender",  "hex": "#c8b8d6"},
            {"name": "Mist Blue", "hex": "#bcd0d8"},
            {"name": "Sage",      "hex": "#bccdb2"},
            {"name": "White",     "hex": "#f5f5f0"},
            {"name": "Black",     "hex": "#222222"},
        ],
        "storage": [
            {"size": "128GB", "delta":   0.00},
            {"size": "256GB", "delta": 100.00},
            {"size": "512GB", "delta": 300.00},
        ],
        "carrier": [
            {"id": "verizon",      "label": "Verizon"},
            {"id": "att",          "label": "AT&T"},
            {"id": "tmobile",      "label": "T-Mobile"},
            {"id": "connect_later","label": "Connect later"},
        ],
        "payment": [
            {"id": "monthly", "label": "Pay monthly with Apple Card Monthly Installments at 0% APR", "months": 24},
            {"id": "full",    "label": "Buy now and pay the full price."},
        ],
        "applecare": [
            {"id": "applecare_plus",       "label": "AppleCare+",                  "monthly":  7.99, "two_year": 169.00},
            {"id": "applecare_plus_theft", "label": "AppleCare+ with Theft & Loss","monthly": 11.49, "two_year": 239.00},
            {"id": "none",                 "label": "No AppleCare+ coverage",      "monthly":  0.00, "two_year":   0.00},
        ],
        "chip": "A19",
        "camera": "48MP Fusion + 12MP Ultra Wide",
        "display": "6.3\" Super Retina XDR with ProMotion",
        "battery": "Up to 30 hours video playback",
    },
    "iphone-16e": {
        "name": "iPhone 16e",
        "subtitle": "The most affordable iPhone with Apple Intelligence.",
        "base_price": 599.00,
        "image": "/static/images/iphone-16e.jpg",
        "colors": [
            {"name": "Black", "hex": "#222222"},
            {"name": "White", "hex": "#f5f5f0"},
        ],
        "storage": [
            {"size": "128GB", "delta":   0.00},
            {"size": "256GB", "delta": 100.00},
            {"size": "512GB", "delta": 300.00},
        ],
        "carrier": [
            {"id": "verizon",      "label": "Verizon"},
            {"id": "att",          "label": "AT&T"},
            {"id": "tmobile",      "label": "T-Mobile"},
            {"id": "connect_later","label": "Connect later"},
        ],
        "payment": [
            {"id": "monthly", "label": "Pay monthly with Apple Card Monthly Installments at 0% APR", "months": 24},
            {"id": "full",    "label": "Buy now and pay the full price."},
        ],
        "applecare": [
            {"id": "applecare_plus",       "label": "AppleCare+",                  "monthly":  4.99, "two_year": 119.00},
            {"id": "applecare_plus_theft", "label": "AppleCare+ with Theft & Loss","monthly":  8.49, "two_year": 189.00},
            {"id": "none",                 "label": "No AppleCare+ coverage",      "monthly":  0.00, "two_year":   0.00},
        ],
        "chip": "A18",
        "camera": "48MP Fusion main camera",
        "display": "6.1\" Super Retina XDR",
        "battery": "Up to 26 hours video playback",
    },
}


# ---------------------------------------------------------------------------
# Mac configurator data — /shop/buy-mac/<model>
# ---------------------------------------------------------------------------
MAC_BUY = {
    "macbook-pro-16": {
        "name": "MacBook Pro 16\"",
        "subtitle": "Mind-blowing. Head-turning.",
        "base_price": 2499.00,
        "image": "/static/images/macbook-pro-16.jpg",
        "chip_options": [
            {"label": "Apple M4 Pro with 12-core CPU, 16-core GPU", "delta":   0.00},
            {"label": "Apple M4 Pro with 14-core CPU, 20-core GPU", "delta": 200.00},
            {"label": "Apple M4 Max with 14-core CPU, 32-core GPU", "delta": 500.00},
            {"label": "Apple M4 Max with 16-core CPU, 40-core GPU", "delta": 700.00},
        ],
        "memory": [
            {"label": "24GB unified memory", "delta":   0.00},
            {"label": "48GB unified memory", "delta": 400.00},
            {"label": "64GB unified memory", "delta": 600.00},
            {"label": "128GB unified memory","delta":1200.00},
        ],
        "ssd": [
            {"label":  "512GB SSD", "delta":   0.00},
            {"label":  "1TB SSD",   "delta": 200.00},
            {"label":  "2TB SSD",   "delta": 600.00},
            {"label":  "4TB SSD",   "delta":1200.00},
            {"label":  "8TB SSD",   "delta":2400.00},
        ],
        "keyboard": [
            {"label": "Magic Keyboard with Touch ID — US English",       "delta":  0.00},
            {"label": "Magic Keyboard with Touch ID — US English (Braille)","delta":0.00},
            {"label": "Magic Keyboard with Touch ID — Chinese (Pinyin)","delta":  0.00},
            {"label": "Magic Keyboard with Touch ID — Japanese",       "delta":  0.00},
            {"label": "Magic Keyboard with Touch ID — Spanish",        "delta":  0.00},
        ],
        "colors": [
            {"name": "Space Black", "hex": "#1d1d1f"},
            {"name": "Silver",      "hex": "#e3e3e3"},
        ],
        "display": "16.2\" Liquid Retina XDR with ProMotion",
        "ports": "3× Thunderbolt 5, HDMI, SDXC, MagSafe 3, 3.5mm headphone",
        "battery": "Up to 24 hours",
    },
    "macbook-pro-14": {
        "name": "MacBook Pro 14\"",
        "subtitle": "Mind-blowing. Head-turning.",
        "base_price": 1599.00,
        "image": "/static/images/macbook-pro-14.jpg",
        "chip_options": [
            {"label": "Apple M4 with 10-core CPU, 10-core GPU",    "delta":   0.00},
            {"label": "Apple M4 Pro with 12-core CPU, 16-core GPU","delta": 400.00},
            {"label": "Apple M4 Pro with 14-core CPU, 20-core GPU","delta": 600.00},
            {"label": "Apple M4 Max with 14-core CPU, 32-core GPU","delta": 900.00},
        ],
        "memory": [
            {"label": "16GB unified memory", "delta":   0.00},
            {"label": "24GB unified memory", "delta": 200.00},
            {"label": "48GB unified memory", "delta": 600.00},
            {"label": "64GB unified memory", "delta": 800.00},
        ],
        "ssd": [
            {"label":  "512GB SSD", "delta":   0.00},
            {"label":  "1TB SSD",   "delta": 200.00},
            {"label":  "2TB SSD",   "delta": 600.00},
            {"label":  "4TB SSD",   "delta":1200.00},
        ],
        "keyboard": [
            {"label": "Magic Keyboard with Touch ID — US English",       "delta": 0.00},
            {"label": "Magic Keyboard with Touch ID — Chinese (Pinyin)", "delta": 0.00},
            {"label": "Magic Keyboard with Touch ID — Japanese",         "delta": 0.00},
            {"label": "Magic Keyboard with Touch ID — Spanish",          "delta": 0.00},
        ],
        "colors": [
            {"name": "Space Black", "hex": "#1d1d1f"},
            {"name": "Silver",      "hex": "#e3e3e3"},
        ],
        "display": "14.2\" Liquid Retina XDR with ProMotion",
        "ports": "3× Thunderbolt 4 (M4) or Thunderbolt 5 (M4 Pro/Max), HDMI, SDXC, MagSafe 3",
        "battery": "Up to 24 hours",
    },
    "macbook-air-15": {
        "name": "MacBook Air 15\"",
        "subtitle": "Lean. Mean. M3 machine.",
        "base_price": 1299.00,
        "image": "/static/images/macbook-air-15.jpg",
        "chip_options": [
            {"label": "Apple M3 with 8-core CPU, 10-core GPU", "delta":   0.00},
        ],
        "memory": [
            {"label":  "16GB unified memory", "delta":   0.00},
            {"label":  "24GB unified memory", "delta": 200.00},
        ],
        "ssd": [
            {"label":  "512GB SSD", "delta":   0.00},
            {"label":  "1TB SSD",   "delta": 200.00},
            {"label":  "2TB SSD",   "delta": 600.00},
        ],
        "keyboard": [
            {"label": "Magic Keyboard with Touch ID — US English",       "delta": 0.00},
            {"label": "Magic Keyboard with Touch ID — Chinese (Pinyin)", "delta": 0.00},
            {"label": "Magic Keyboard with Touch ID — Japanese",         "delta": 0.00},
        ],
        "colors": [
            {"name": "Midnight",     "hex": "#191c20"},
            {"name": "Starlight",    "hex": "#f0e3cd"},
            {"name": "Sky Blue",     "hex": "#b2cee0"},
            {"name": "Silver",       "hex": "#e3e3e3"},
        ],
        "display": "15.3\" Liquid Retina",
        "ports": "2× Thunderbolt / USB 4, MagSafe 3, 3.5mm headphone",
        "battery": "Up to 18 hours",
    },
    "macbook-air-13": {
        "name": "MacBook Air 13\"",
        "subtitle": "Lean. Mean. M3 machine.",
        "base_price": 1099.00,
        "image": "/static/images/macbook-air-13.jpg",
        "chip_options": [
            {"label": "Apple M3 with 8-core CPU, 8-core GPU",  "delta":   0.00},
            {"label": "Apple M3 with 8-core CPU, 10-core GPU", "delta": 100.00},
        ],
        "memory": [
            {"label":  "16GB unified memory", "delta":   0.00},
            {"label":  "24GB unified memory", "delta": 200.00},
        ],
        "ssd": [
            {"label":  "256GB SSD", "delta":   0.00},
            {"label":  "512GB SSD", "delta": 200.00},
            {"label":  "1TB SSD",   "delta": 400.00},
            {"label":  "2TB SSD",   "delta": 800.00},
        ],
        "keyboard": [
            {"label": "Magic Keyboard with Touch ID — US English",       "delta": 0.00},
            {"label": "Magic Keyboard with Touch ID — Chinese (Pinyin)", "delta": 0.00},
            {"label": "Magic Keyboard with Touch ID — Japanese",         "delta": 0.00},
        ],
        "colors": [
            {"name": "Midnight",     "hex": "#191c20"},
            {"name": "Starlight",    "hex": "#f0e3cd"},
            {"name": "Sky Blue",     "hex": "#b2cee0"},
            {"name": "Silver",       "hex": "#e3e3e3"},
        ],
        "display": "13.6\" Liquid Retina",
        "ports": "2× Thunderbolt / USB 4, MagSafe 3, 3.5mm headphone",
        "battery": "Up to 18 hours",
    },
    "mac-mini": {
        "name": "Mac mini",
        "subtitle": "Small. Mighty. Mini.",
        "base_price": 599.00,
        "image": "/static/images/mac-mini.jpg",
        "chip_options": [
            {"label": "Apple M4 with 10-core CPU, 10-core GPU",    "delta":   0.00},
            {"label": "Apple M4 Pro with 12-core CPU, 16-core GPU","delta": 600.00},
            {"label": "Apple M4 Pro with 14-core CPU, 20-core GPU","delta": 800.00},
        ],
        "memory": [
            {"label": "16GB unified memory", "delta":   0.00},
            {"label": "24GB unified memory", "delta": 200.00},
            {"label": "32GB unified memory", "delta": 400.00},
            {"label": "64GB unified memory", "delta": 800.00},
        ],
        "ssd": [
            {"label":  "256GB SSD", "delta":   0.00},
            {"label":  "512GB SSD", "delta": 200.00},
            {"label":  "1TB SSD",   "delta": 400.00},
            {"label":  "2TB SSD",   "delta": 800.00},
        ],
        "keyboard": [
            {"label": "No keyboard included",                       "delta": 0.00},
            {"label": "Magic Keyboard — US English",                "delta": 99.00},
            {"label": "Magic Keyboard with Touch ID — US English",  "delta":129.00},
        ],
        "colors": [{"name": "Silver", "hex": "#e3e3e3"}],
        "display": "Sold separately",
        "ports": "Front: 2× USB-C, 3.5mm headphone. Back: 3× Thunderbolt 4, HDMI, Ethernet",
        "battery": "AC powered",
    },
    "imac": {
        "name": "iMac",
        "subtitle": "Wow. From every angle.",
        "base_price": 1299.00,
        "image": "/static/images/imac.jpg",
        "chip_options": [
            {"label": "Apple M4 with 8-core CPU, 8-core GPU",  "delta":   0.00},
            {"label": "Apple M4 with 10-core CPU, 10-core GPU","delta": 200.00},
        ],
        "memory": [
            {"label": "16GB unified memory", "delta":   0.00},
            {"label": "24GB unified memory", "delta": 200.00},
            {"label": "32GB unified memory", "delta": 400.00},
        ],
        "ssd": [
            {"label":  "256GB SSD", "delta":   0.00},
            {"label":  "512GB SSD", "delta": 200.00},
            {"label":  "1TB SSD",   "delta": 400.00},
            {"label":  "2TB SSD",   "delta": 800.00},
        ],
        "keyboard": [
            {"label": "Magic Keyboard — US English",               "delta": 0.00},
            {"label": "Magic Keyboard with Touch ID — US English", "delta":30.00},
            {"label": "Magic Keyboard with Numeric Keypad",        "delta":30.00},
        ],
        "colors": [
            {"name": "Green",  "hex": "#c0d6a8"},
            {"name": "Yellow", "hex": "#f5e08c"},
            {"name": "Orange", "hex": "#f3a07a"},
            {"name": "Pink",   "hex": "#f5b6c1"},
            {"name": "Purple", "hex": "#d2c2ed"},
            {"name": "Blue",   "hex": "#a5c6e8"},
            {"name": "Silver", "hex": "#e3e3e3"},
        ],
        "display": "24\" 4.5K Retina",
        "ports": "2× Thunderbolt / USB 4 (4 ports with 10-core GPU)",
        "battery": "AC powered",
    },
}


# ---------------------------------------------------------------------------
# iPad configurator data — /shop/buy-ipad/<model>
# ---------------------------------------------------------------------------
IPAD_BUY = {
    "ipad-pro-13": {
        "name": "iPad Pro 13\"",
        "subtitle": "Unbelievably thin. Incredibly powerful.",
        "base_price": 1299.00,
        "image": "/static/images/ipad-pro-13.jpg",
        "colors": [
            {"name": "Space Black", "hex": "#1d1d1f"},
            {"name": "Silver",      "hex": "#e3e3e3"},
        ],
        "storage": [
            {"size":  "256GB", "delta":    0.00},
            {"size":  "512GB", "delta":  200.00},
            {"size":   "1TB",  "delta":  600.00},
            {"size":   "2TB",  "delta": 1000.00},
        ],
        "connectivity": [
            {"id": "wifi",      "label": "Wi-Fi",          "delta":   0.00},
            {"id": "wifi_cell", "label": "Wi-Fi + Cellular","delta": 200.00},
        ],
        "accessories": [
            {"id": "pencil_pro",      "label": "Apple Pencil Pro",       "price": 129.00},
            {"id": "pencil_usbc",     "label": "Apple Pencil (USB-C)",   "price":  79.00},
            {"id": "magic_keyboard",  "label": "Magic Keyboard for iPad Pro 13\"", "price": 349.00},
        ],
        "chip": "Apple M5",
        "display": "13\" Ultra Retina XDR with ProMotion, Tandem OLED",
        "camera": "12MP Wide camera, LiDAR Scanner",
        "battery": "Up to 10 hours",
    },
    "ipad-pro-11": {
        "name": "iPad Pro 11\"",
        "subtitle": "Unbelievably thin. Incredibly powerful.",
        "base_price": 999.00,
        "image": "/static/images/ipad-pro-11.jpg",
        "colors": [
            {"name": "Space Black", "hex": "#1d1d1f"},
            {"name": "Silver",      "hex": "#e3e3e3"},
        ],
        "storage": [
            {"size":  "256GB", "delta":    0.00},
            {"size":  "512GB", "delta":  200.00},
            {"size":   "1TB",  "delta":  600.00},
            {"size":   "2TB",  "delta": 1000.00},
        ],
        "connectivity": [
            {"id": "wifi",      "label": "Wi-Fi",           "delta":   0.00},
            {"id": "wifi_cell", "label": "Wi-Fi + Cellular","delta": 200.00},
        ],
        "accessories": [
            {"id": "pencil_pro",      "label": "Apple Pencil Pro",       "price": 129.00},
            {"id": "pencil_usbc",     "label": "Apple Pencil (USB-C)",   "price":  79.00},
            {"id": "magic_keyboard",  "label": "Magic Keyboard for iPad Pro 11\"", "price": 299.00},
        ],
        "chip": "Apple M5",
        "display": "11\" Ultra Retina XDR with ProMotion, Tandem OLED",
        "camera": "12MP Wide, LiDAR Scanner",
        "battery": "Up to 10 hours",
    },
    "ipad-air": {
        "name": "iPad Air",
        "subtitle": "Crazy fun. Crazy powerful.",
        "base_price": 599.00,
        "image": "/static/images/ipad-air.jpg",
        "colors": [
            {"name": "Space Gray", "hex": "#5c5c5c"},
            {"name": "Blue",       "hex": "#a5c6e8"},
            {"name": "Purple",     "hex": "#d2c2ed"},
            {"name": "Starlight",  "hex": "#f0e3cd"},
        ],
        "storage": [
            {"size":  "128GB", "delta":   0.00},
            {"size":  "256GB", "delta": 100.00},
            {"size":  "512GB", "delta": 300.00},
            {"size":   "1TB",  "delta": 500.00},
        ],
        "connectivity": [
            {"id": "wifi",      "label": "Wi-Fi",           "delta":   0.00},
            {"id": "wifi_cell", "label": "Wi-Fi + Cellular","delta": 150.00},
        ],
        "accessories": [
            {"id": "pencil_pro",      "label": "Apple Pencil Pro",     "price": 129.00},
            {"id": "pencil_usbc",     "label": "Apple Pencil (USB-C)", "price":  79.00},
            {"id": "magic_keyboard",  "label": "Magic Keyboard for iPad Air", "price": 269.00},
        ],
        "chip": "Apple M3",
        "display": "11\" or 13\" Liquid Retina",
        "camera": "12MP Wide",
        "battery": "Up to 10 hours",
    },
    "ipad": {
        "name": "iPad",
        "subtitle": "Lovable. Drawable. Magical.",
        "base_price": 349.00,
        "image": "/static/images/ipad.jpg",
        "colors": [
            {"name": "Silver",    "hex": "#e3e3e3"},
            {"name": "Blue",      "hex": "#a5c6e8"},
            {"name": "Pink",      "hex": "#f5b6c1"},
            {"name": "Yellow",    "hex": "#f5e08c"},
        ],
        "storage": [
            {"size":  "128GB", "delta":   0.00},
            {"size":  "256GB", "delta": 100.00},
            {"size":  "512GB", "delta": 300.00},
        ],
        "connectivity": [
            {"id": "wifi",      "label": "Wi-Fi",           "delta":   0.00},
            {"id": "wifi_cell", "label": "Wi-Fi + Cellular","delta": 150.00},
        ],
        "accessories": [
            {"id": "pencil_usbc",     "label": "Apple Pencil (USB-C)",  "price":  79.00},
            {"id": "pencil_1",        "label": "Apple Pencil (1st gen)","price":  99.00},
            {"id": "magic_keyboard",  "label": "Magic Keyboard Folio",  "price": 249.00},
        ],
        "chip": "A16",
        "display": "10.9\" Liquid Retina",
        "camera": "12MP Wide (landscape Front)",
        "battery": "Up to 10 hours",
    },
}


# ---------------------------------------------------------------------------
# Watch configurator data — /shop/buy-watch/<model>
# ---------------------------------------------------------------------------
WATCH_BUY = {
    "ultra-3": {
        "name": "Apple Watch Ultra 3",
        "subtitle": "The most rugged and capable Apple Watch.",
        "base_price": 799.00,
        "image": "/static/images/watch-ultra-3.jpg",
        "case": [
            {"label": "49mm Natural Titanium Case", "delta": 0.00},
            {"label": "49mm Black Titanium Case",   "delta": 0.00},
        ],
        "band": [
            {"label": "Trail Loop — Green/Gray",       "delta": 0.00},
            {"label": "Trail Loop — Blue/Black",       "delta": 0.00},
            {"label": "Ocean Band — Black",            "delta": 0.00},
            {"label": "Ocean Band — White",            "delta": 0.00},
            {"label": "Alpine Loop — Indigo",          "delta": 0.00},
            {"label": "Alpine Loop — Olive",           "delta": 0.00},
            {"label": "Titanium Milanese Loop",        "delta": 99.00},
        ],
        "connectivity": [
            {"id": "gps_cell", "label": "GPS + Cellular (only option for Ultra)", "delta": 0.00},
        ],
        "applecare": [
            {"id": "applecare_plus", "label": "AppleCare+ for Apple Watch Ultra 3", "monthly": 4.99, "two_year": 99.00},
            {"id": "none",           "label": "No AppleCare+",                       "monthly": 0.00, "two_year":  0.00},
        ],
        "chip": "S10",
        "display": "49mm Always-On Retina LTPO3",
        "battery": "Up to 36 hours (72 hours Low Power)",
    },
    "series-11": {
        "name": "Apple Watch Series 11",
        "subtitle": "Apple Watch beat.",
        "base_price": 399.00,
        "image": "/static/images/watch-series-11.jpg",
        "case": [
            {"label": "42mm Aluminum Case — Jet Black", "delta":   0.00},
            {"label": "42mm Aluminum Case — Rose Gold", "delta":   0.00},
            {"label": "42mm Aluminum Case — Silver",    "delta":   0.00},
            {"label": "46mm Aluminum Case — Jet Black", "delta":  30.00},
            {"label": "46mm Aluminum Case — Silver",    "delta":  30.00},
            {"label": "42mm Titanium Case — Natural",   "delta": 350.00},
            {"label": "42mm Titanium Case — Slate",     "delta": 350.00},
            {"label": "46mm Titanium Case — Natural",   "delta": 380.00},
        ],
        "band": [
            {"label": "Sport Band — Black",     "delta": 0.00},
            {"label": "Sport Band — Plum",      "delta": 0.00},
            {"label": "Sport Loop — Pure Gray", "delta": 0.00},
            {"label": "Braided Solo Loop — Lake Green", "delta": 99.00},
            {"label": "Milanese Loop — Silver",         "delta": 99.00},
        ],
        "connectivity": [
            {"id": "gps",      "label": "GPS",            "delta":   0.00},
            {"id": "gps_cell", "label": "GPS + Cellular", "delta": 100.00},
        ],
        "applecare": [
            {"id": "applecare_plus", "label": "AppleCare+ for Apple Watch Series 11", "monthly": 3.99, "two_year": 79.00},
            {"id": "none",           "label": "No AppleCare+",                         "monthly": 0.00, "two_year":  0.00},
        ],
        "chip": "S10",
        "display": "42mm/46mm Always-On Retina LTPO3",
        "battery": "Up to 24 hours (36 hours Low Power)",
    },
    "se-2": {
        "name": "Apple Watch SE",
        "subtitle": "All the essentials. Lots of fun.",
        "base_price": 249.00,
        "image": "/static/images/watch-se-2.jpg",
        "case": [
            {"label": "40mm Aluminum Case — Midnight",  "delta":  0.00},
            {"label": "40mm Aluminum Case — Starlight", "delta":  0.00},
            {"label": "40mm Aluminum Case — Silver",    "delta":  0.00},
            {"label": "44mm Aluminum Case — Midnight",  "delta": 30.00},
            {"label": "44mm Aluminum Case — Starlight", "delta": 30.00},
            {"label": "44mm Aluminum Case — Silver",    "delta": 30.00},
        ],
        "band": [
            {"label": "Sport Band — Midnight",   "delta": 0.00},
            {"label": "Sport Band — Starlight",  "delta": 0.00},
            {"label": "Sport Loop — Storm Blue", "delta": 0.00},
            {"label": "Solo Loop — Black",       "delta": 0.00},
        ],
        "connectivity": [
            {"id": "gps",      "label": "GPS",            "delta":  0.00},
            {"id": "gps_cell", "label": "GPS + Cellular", "delta": 50.00},
        ],
        "applecare": [
            {"id": "applecare_plus", "label": "AppleCare+ for Apple Watch SE", "monthly": 2.99, "two_year": 59.00},
            {"id": "none",           "label": "No AppleCare+",                  "monthly": 0.00, "two_year":  0.00},
        ],
        "chip": "S8",
        "display": "40mm/44mm Retina",
        "battery": "Up to 18 hours",
    },
}


# ---------------------------------------------------------------------------
# Compare tables  (one entry per family)
# ---------------------------------------------------------------------------
COMPARE_IPHONE = [
    {"slug": "iphone-17-pro-max", "name": "iPhone 17 Pro Max", "price": 1199.00, "chip": "A19 Pro",
     "display": "6.9\" Super Retina XDR with ProMotion", "camera": "48MP Fusion + 48MP UW + 48MP Tele 8x",
     "battery": "35 hr video", "storage_top": "2TB", "weight": "227 g", "colors": 4},
    {"slug": "iphone-17-pro", "name": "iPhone 17 Pro", "price": 999.00, "chip": "A19 Pro",
     "display": "6.3\" Super Retina XDR with ProMotion", "camera": "48MP Fusion + 48MP UW + 48MP Tele 5x",
     "battery": "28 hr video", "storage_top": "1TB", "weight": "199 g", "colors": 4},
    {"slug": "iphone-air", "name": "iPhone Air", "price": 999.00, "chip": "A19 Pro",
     "display": "6.5\" Super Retina XDR with ProMotion", "camera": "48MP Fusion main",
     "battery": "27 hr video", "storage_top": "1TB", "weight": "165 g", "colors": 4},
    {"slug": "iphone-17", "name": "iPhone 17", "price": 799.00, "chip": "A19",
     "display": "6.3\" Super Retina XDR with ProMotion", "camera": "48MP Fusion + 12MP UW",
     "battery": "30 hr video", "storage_top": "512GB", "weight": "177 g", "colors": 5},
    {"slug": "iphone-16e", "name": "iPhone 16e", "price": 599.00, "chip": "A18",
     "display": "6.1\" Super Retina XDR", "camera": "48MP Fusion main",
     "battery": "26 hr video", "storage_top": "512GB", "weight": "170 g", "colors": 2},
]

COMPARE_MAC = [
    {"slug": "macbook-pro-16", "name": "MacBook Pro 16\"", "price": 2499.00,
     "chip": "M4 Pro/Max", "memory": "24GB to 128GB", "ssd": "512GB to 8TB",
     "display": "16.2\" Liquid Retina XDR", "battery": "24 hr", "weight": "2.16 kg"},
    {"slug": "macbook-pro-14", "name": "MacBook Pro 14\"", "price": 1599.00,
     "chip": "M4 / M4 Pro / M4 Max", "memory": "16GB to 64GB", "ssd": "512GB to 4TB",
     "display": "14.2\" Liquid Retina XDR", "battery": "24 hr", "weight": "1.55 kg"},
    {"slug": "macbook-air-15", "name": "MacBook Air 15\"", "price": 1299.00,
     "chip": "M3", "memory": "16GB to 24GB", "ssd": "512GB to 2TB",
     "display": "15.3\" Liquid Retina", "battery": "18 hr", "weight": "1.51 kg"},
    {"slug": "macbook-air-13", "name": "MacBook Air 13\"", "price": 1099.00,
     "chip": "M3", "memory": "16GB to 24GB", "ssd": "256GB to 2TB",
     "display": "13.6\" Liquid Retina", "battery": "18 hr", "weight": "1.24 kg"},
    {"slug": "mac-mini", "name": "Mac mini", "price": 599.00,
     "chip": "M4 / M4 Pro", "memory": "16GB to 64GB", "ssd": "256GB to 2TB",
     "display": "sold separately", "battery": "AC powered", "weight": "0.67 kg"},
    {"slug": "imac", "name": "iMac", "price": 1299.00,
     "chip": "M4", "memory": "16GB to 32GB", "ssd": "256GB to 2TB",
     "display": "24\" 4.5K Retina", "battery": "AC powered", "weight": "4.42 kg"},
]

COMPARE_IPAD = [
    {"slug": "ipad-pro-13", "name": "iPad Pro 13\"", "price": 1299.00, "chip": "Apple M5",
     "display": "13\" Tandem OLED ProMotion", "storage_top": "2TB",
     "weight": "579 g", "battery": "10 hr", "pencil": "Apple Pencil Pro"},
    {"slug": "ipad-pro-11", "name": "iPad Pro 11\"", "price": 999.00, "chip": "Apple M5",
     "display": "11\" Tandem OLED ProMotion", "storage_top": "2TB",
     "weight": "444 g", "battery": "10 hr", "pencil": "Apple Pencil Pro"},
    {"slug": "ipad-air", "name": "iPad Air", "price": 599.00, "chip": "Apple M3",
     "display": "11\" or 13\" Liquid Retina", "storage_top": "1TB",
     "weight": "462 g (11\") / 617 g (13\")", "battery": "10 hr", "pencil": "Apple Pencil Pro"},
    {"slug": "ipad", "name": "iPad", "price": 349.00, "chip": "A16",
     "display": "10.9\" Liquid Retina", "storage_top": "512GB",
     "weight": "477 g", "battery": "10 hr", "pencil": "Apple Pencil (USB-C)"},
    {"slug": "ipad-mini", "name": "iPad mini", "price": 499.00, "chip": "A17 Pro",
     "display": "8.3\" Liquid Retina", "storage_top": "512GB",
     "weight": "293 g", "battery": "10 hr", "pencil": "Apple Pencil Pro"},
]

COMPARE_AIRPODS = [
    {"slug": "airpods-pro-3", "name": "AirPods Pro 3", "price": 249.00,
     "chip": "H3", "anc": "Adaptive Audio + ANC + Conversation Awareness",
     "battery": "8 hr (Pro 3) / 30 hr (case)",
     "hearing_aid": "Yes — clinical-grade", "transparency": "Yes",
     "spatial_audio": "Yes — Personalized Spatial Audio"},
    {"slug": "airpods-4-anc", "name": "AirPods 4 (with ANC)", "price": 179.00,
     "chip": "H2", "anc": "Active Noise Cancellation",
     "battery": "5 hr / 30 hr (case)",
     "hearing_aid": "No", "transparency": "Yes",
     "spatial_audio": "Yes — Personalized Spatial Audio"},
    {"slug": "airpods-4", "name": "AirPods 4", "price": 129.00,
     "chip": "H2", "anc": "—",
     "battery": "5 hr / 30 hr (case)",
     "hearing_aid": "No", "transparency": "—",
     "spatial_audio": "Yes — Personalized Spatial Audio"},
    {"slug": "airpods-max-2", "name": "AirPods Max", "price": 549.00,
     "chip": "H1", "anc": "Active Noise Cancellation",
     "battery": "20 hr",
     "hearing_aid": "No", "transparency": "Yes",
     "spatial_audio": "Yes — Personalized Spatial Audio"},
]


# ---------------------------------------------------------------------------
# Apple Services hubs  — /services/<slug>
# ---------------------------------------------------------------------------
SERVICES = {
    "tv-plus": {
        "name": "Apple TV+",
        "tagline": "All Apple Originals. Always something good.",
        "monthly": 12.99,
        "trial": "7 days free",
        "key_titles": [
            "Severance", "Slow Horses", "Ted Lasso", "The Morning Show",
            "Foundation", "Silo", "For All Mankind", "Pachinko",
        ],
        "feature_bullets": [
            "Stream on any Apple device, Roku, Fire TV, Chromecast, smart TVs, and online.",
            "Stream up to six family members at the same time when shared via Family Sharing.",
            "All Apple Originals in 4K HDR, Dolby Vision and Dolby Atmos where available.",
            "Download to watch offline on iPhone, iPad, and Mac.",
        ],
    },
    "music": {
        "name": "Apple Music",
        "tagline": "Over 100 million songs. Lossless. Spatial.",
        "monthly": 10.99,
        "trial": "1 month free",
        "key_titles": [
            "Apple Music Radio", "Apple Music Classical", "Apple Music Sing",
            "Apple Music Live concerts", "Beats 1 / 2 / 3", "Personalised stations",
        ],
        "feature_bullets": [
            "Lossless and Hi-Res Lossless audio, plus Dolby Atmos.",
            "Real-time and time-synced lyrics for millions of songs.",
            "Apple Music Sing for karaoke on iPhone, iPad, and Apple TV 4K.",
            "Shared playlists with friends and SharePlay over FaceTime.",
        ],
    },
    "arcade": {
        "name": "Apple Arcade",
        "tagline": "Unlimited play, no ads, no in-app purchases.",
        "monthly": 6.99,
        "trial": "1 month free",
        "key_titles": [
            "NBA 2K25 Arcade Edition", "Sonic Dream Team", "TMNT Splintered Fate",
            "Cooking Mama", "Disney Dreamlight Valley Arcade Edition",
            "Stardew Valley+", "Crossy Road+", "Hello Kitty Island Adventure",
        ],
        "feature_bullets": [
            "Over 200 games — no ads, no in-app purchases, ever.",
            "Play on iPhone, iPad, Mac, and Apple TV across one subscription.",
            "Share with up to five family members using Family Sharing.",
            "Game saves sync seamlessly via iCloud.",
        ],
    },
    "news-plus": {
        "name": "Apple News+",
        "tagline": "Hundreds of magazines, top newspapers, and exclusive features.",
        "monthly": 12.99,
        "trial": "1 month free",
        "key_titles": [
            "The Wall Street Journal", "Los Angeles Times", "The Atlantic",
            "Vogue", "TIME", "National Geographic", "GQ", "The New Yorker",
        ],
        "feature_bullets": [
            "Hundreds of top magazines and leading newspapers.",
            "Audio narrated stories from professional voices.",
            "Daily crossword and puzzles, including Quartiles.",
            "Read on iPhone, iPad, and Mac with downloaded offline issues.",
        ],
    },
    "fitness-plus": {
        "name": "Apple Fitness+",
        "tagline": "Workouts and meditations for everyone.",
        "monthly": 9.99,
        "trial": "1 month free",
        "key_titles": [
            "Strength", "HIIT", "Yoga", "Pilates", "Treadmill",
            "Meditation", "Mindful Cooldown", "Time to Walk",
        ],
        "feature_bullets": [
            "Studio-style workouts in 10 categories with new releases every week.",
            "Apple Watch metrics sync live on the screen during every workout.",
            "Custom Plans recommend workouts based on your goals and history.",
            "Share with up to five family members via Family Sharing.",
        ],
    },
    "icloud": {
        "name": "iCloud+",
        "tagline": "More storage. Better privacy. New superpowers.",
        "monthly": 0.99,
        "trial": "Bundled free 5 GB",
        "key_titles": [
            "iCloud Private Relay", "Hide My Email", "Custom Email Domain",
            "HomeKit Secure Video", "iCloud Photos", "iCloud Drive",
        ],
        "feature_bullets": [
            "Plans from 50 GB ($0.99/mo) up to 12 TB ($59.99/mo).",
            "Private Relay routes Safari browsing through two relays.",
            "Hide My Email generates unique addresses that forward to your inbox.",
            "HomeKit Secure Video supports unlimited cameras on the 2 TB+ plans.",
        ],
    },
}

# iCloud+ storage plans — /services/icloud/storage-plans
ICLOUD_PLANS = [
    {"size":  "5GB",  "monthly":  0.00, "note": "Bundled free with every Apple Account."},
    {"size": "50GB",  "monthly":  0.99, "note": "Great for iPhone backup and a few thousand photos."},
    {"size":"200GB",  "monthly":  2.99, "note": "Family Sharing across up to five members."},
    {"size":  "2TB",  "monthly":  9.99, "note": "Family Sharing + HomeKit Secure Video unlimited cameras."},
    {"size":  "6TB",  "monthly": 29.99, "note": "Pro photographers and large families."},
    {"size": "12TB",  "monthly": 59.99, "note": "Maximum tier with unlimited HomeKit cameras."},
]

# Apple One bundle tiers — /services/apple-one
APPLE_ONE_PLANS = [
    {"slug": "individual", "name": "Individual", "monthly": 19.95,
     "members": "1 person",
     "includes": ["iCloud+ (50GB)", "Apple Music", "Apple TV+", "Apple Arcade"]},
    {"slug": "family",     "name": "Family",     "monthly": 25.95,
     "members": "Up to 6 family members",
     "includes": ["iCloud+ (200GB)", "Apple Music", "Apple TV+", "Apple Arcade"]},
    {"slug": "premier",    "name": "Premier",    "monthly": 37.95,
     "members": "Up to 6 family members",
     "includes": ["iCloud+ (2TB)", "Apple Music", "Apple TV+", "Apple Arcade",
                  "Apple News+", "Apple Fitness+"]},
]


# ---------------------------------------------------------------------------
# Apple for Business industries — /business/<industry>
# ---------------------------------------------------------------------------
BUSINESS_INDUSTRIES = {
    "retail": {
        "name": "Retail",
        "headline": "Apple at Work — Retail.",
        "subheadline": "Empower store associates and reimagine the customer experience.",
        "use_cases": [
            "Mobile checkout with iPad Pro and Tap to Pay on iPhone.",
            "Real-time inventory lookup across stores via Apple Business Manager.",
            "Clienteling apps that put customer history in the associate's hand.",
            "iPad-based digital signage and product demos on the sales floor.",
        ],
        "case_study": "Lululemon equips every store associate with an iPad and an iPhone for endless aisle and queue-busting.",
        "products": ["iPhone 17 Pro", "iPad Pro 11\"", "MacBook Air 13\"", "Apple Watch Series 11"],
    },
    "healthcare": {
        "name": "Healthcare",
        "headline": "Apple at Work — Healthcare.",
        "subheadline": "Bring iPad and iPhone to every clinical workflow.",
        "use_cases": [
            "iPad at the bedside for charting, video visits, and patient education.",
            "Apple Watch ECG and irregular rhythm notifications surface clinical insights.",
            "ResearchKit and CareKit power patient-facing research studies.",
            "Single Sign-On and Shared iPad keep PHI secure across shift changes.",
        ],
        "case_study": "Sutter Health rolled out 8,000 iPads to nurses for instant charting and clinical photography.",
        "products": ["iPad Air", "iPhone 17", "Apple Watch Series 11", "AirPods 4"],
    },
    "education-pro": {
        "name": "Education Enterprise",
        "headline": "Apple at Work — Education.",
        "subheadline": "School-wide deployments through Apple School Manager.",
        "use_cases": [
            "Zero-touch deployment of thousands of iPads with Automated Device Enrollment.",
            "Shared iPad for classrooms with managed Apple IDs for every student.",
            "Apple Classroom for guided lessons; Schoolwork for assignment grading.",
            "Everyone Can Code and Everyone Can Create curriculum at no cost.",
        ],
        "case_study": "Chicago Public Schools deploys MacBook Air for 360,000+ students through Apple School Manager.",
        "products": ["iPad", "MacBook Air 13\"", "Apple Pencil (USB-C)", "Magic Keyboard Folio"],
    },
    "creative": {
        "name": "Creative",
        "headline": "Apple at Work — Creative.",
        "subheadline": "From the indie studio to the global agency, creative work runs on Apple.",
        "use_cases": [
            "Final Cut Pro on MacBook Pro 16\" with M4 Max for 8K ProRes editing.",
            "Logic Pro on Mac Studio for full mixing and mastering sessions.",
            "iPad Pro M5 + Apple Pencil Pro for storyboarding, painting, and motion.",
            "Apple Vision Pro for 3D production review and immersive content.",
        ],
        "case_study": "Industrial Light & Magic standardises on MacBook Pro M4 Max for every visual-effects artist.",
        "products": ["MacBook Pro 16\"", "Mac Studio", "iPad Pro 13\"", "Apple Vision Pro"],
    },
}


# ---------------------------------------------------------------------------
# Education portals — /education/<slug>
# ---------------------------------------------------------------------------
EDUCATION_STUDENTS = {
    "headline": "Save on a Mac or iPad for college.",
    "subheadline": "Special pricing for college students, recently accepted students, and their parents.",
    "savings": [
        {"product": "MacBook Air 13\"", "edu_price": 999.00,  "regular": 1099.00, "save": 100.00},
        {"product": "MacBook Air 15\"", "edu_price": 1199.00, "regular": 1299.00, "save": 100.00},
        {"product": "MacBook Pro 14\"", "edu_price": 1499.00, "regular": 1599.00, "save": 100.00},
        {"product": "MacBook Pro 16\"", "edu_price": 2299.00, "regular": 2499.00, "save": 200.00},
        {"product": "iMac",             "edu_price": 1199.00, "regular": 1299.00, "save": 100.00},
        {"product": "iPad Pro 11\"",    "edu_price":  899.00, "regular":  999.00, "save": 100.00},
        {"product": "iPad Pro 13\"",    "edu_price": 1199.00, "regular": 1299.00, "save": 100.00},
        {"product": "iPad Air",         "edu_price":  549.00, "regular":  599.00, "save":  50.00},
    ],
    "gifts": [
        "Free engraving on iPad, AirPods, AirTag, Apple Pencil, and the Mac.",
        "Discounted AppleCare+ for students.",
        "20% off AppleCare+ at checkout.",
    ],
}

EDUCATION_EDUCATORS = {
    "headline": "Same Education Pricing, designed for the classroom.",
    "subheadline": "Save up to $200 on a Mac and $100 on an iPad. Educators get exclusive bundles.",
    "savings": [
        {"product": "MacBook Pro 14\"", "edu_price": 1499.00, "regular": 1599.00, "save": 100.00},
        {"product": "MacBook Pro 16\"", "edu_price": 2299.00, "regular": 2499.00, "save": 200.00},
        {"product": "MacBook Air 13\"", "edu_price":  999.00, "regular": 1099.00, "save": 100.00},
        {"product": "iPad (10th gen)",  "edu_price":  329.00, "regular":  349.00, "save":  20.00},
        {"product": "iPad Pro 11\"",    "edu_price":  899.00, "regular":  999.00, "save": 100.00},
    ],
    "exclusive": [
        "Free Apple Pencil (USB-C) with iPad Pro.",
        "Free engraving on iPad.",
        "Volume discount with Apple School Manager.",
    ],
}

EDUCATION_EVERYONE_CREATE = {
    "headline": "Everyone Can Create.",
    "subheadline": "A free curriculum that brings creativity to every subject — from K-12 to higher education.",
    "modules": [
        {"name": "Photo",   "lessons": 10, "level": "Grades 5–12",
         "outcome": "Students learn composition, exposure, and editing using the Camera and Photos apps."},
        {"name": "Video",   "lessons": 11, "level": "Grades 6–12",
         "outcome": "Students plan, shoot, and edit short documentaries with iMovie."},
        {"name": "Music",   "lessons":  9, "level": "Grades 4–12",
         "outcome": "Students compose multitrack pieces in GarageBand on iPad."},
        {"name": "Drawing", "lessons":  8, "level": "Grades 3–12",
         "outcome": "Students sketch, ink, and colour with Apple Pencil in Notes and Procreate."},
    ],
    "downloads": [
        {"name": "Teacher Guide (PDF)",   "size_mb": 18},
        {"name": "Student Project Book (PDF)", "size_mb": 24},
        {"name": "Sample Project — Photo (.zip)", "size_mb": 12},
    ],
}

EDUCATION_SWIFT_PLAYGROUNDS = {
    "headline": "Swift Playgrounds Curriculum.",
    "subheadline": "A complete curriculum that teaches coding from scratch through to building real apps.",
    "tracks": [
        {"name": "Develop in Swift — Explorations",
         "audience": "Grades 9–12",
         "duration": "180 hours",
         "outcome": "Foundational Swift concepts and first iPad apps."},
        {"name": "Develop in Swift — Fundamentals",
         "audience": "Grades 9–12",
         "duration": "180 hours",
         "outcome": "Build SwiftUI apps and prep for the App Store."},
        {"name": "Develop in Swift — Data Collections",
         "audience": "Higher Ed / AP CS",
         "duration": "180 hours",
         "outcome": "Tables, JSON, REST, Core Data and shipping a full app."},
        {"name": "Develop in Swift — Tutorials",
         "audience": "Self-paced (all levels)",
         "duration": "30 modules",
         "outcome": "Bite-size tutorials that pair with Swift Playgrounds on iPad."},
    ],
}


# ---------------------------------------------------------------------------
# Support categories — /support/category/<slug>
# ---------------------------------------------------------------------------
SUPPORT_CATEGORIES = {
    "iphone":   {"name": "iPhone Support",
                 "top_tasks": ["Check iPhone coverage", "Find a lost iPhone", "Get repair pricing",
                               "Restore iPhone backup", "iPhone won't turn on", "iPhone won't charge"],
                 "articles": ["Update to the latest iOS", "Replace your iPhone battery",
                              "Reset Face ID", "Transfer data to a new iPhone",
                              "Set up Apple Cash on iPhone"]},
    "mac":      {"name": "Mac Support",
                 "top_tasks": ["Check Mac coverage", "Mac won't turn on", "Get repair pricing",
                               "Restore from Time Machine", "Reset NVRAM/PRAM", "Sign in to a new Mac"],
                 "articles": ["Update macOS", "Use Migration Assistant",
                              "Recover deleted files", "Reset SMC", "Boot in Recovery mode"]},
    "ipad":     {"name": "iPad Support",
                 "top_tasks": ["Check iPad coverage", "Pair Apple Pencil", "Get repair pricing",
                               "Reset iPad", "iPad won't charge", "Find a lost iPad"],
                 "articles": ["Update to the latest iPadOS", "Pair Magic Keyboard",
                              "Use Stage Manager", "Take a screenshot on iPad",
                              "Set up Universal Control"]},
    "watch":    {"name": "Apple Watch Support",
                 "top_tasks": ["Pair Apple Watch", "Check Apple Watch coverage", "Take an ECG",
                               "Set up Family Setup", "Watch won't pair", "Recover passcode"],
                 "articles": ["Update watchOS", "Customise watch faces",
                              "Set up Fall Detection", "Track sleep on Apple Watch",
                              "Use the AssistiveTouch feature"]},
    "airpods":  {"name": "AirPods Support",
                 "top_tasks": ["Pair AirPods", "Use Hearing Aid features",
                               "Set up Personalised Spatial Audio", "Clean AirPods",
                               "Get a replacement AirPod", "Find lost AirPods"],
                 "articles": ["Reset AirPods", "Use Conversation Awareness",
                              "Turn on Adaptive Audio", "Use Live Listen",
                              "Charge AirPods Pro 3"]},
    "tv-home":  {"name": "TV & Home Support",
                 "top_tasks": ["Set up Apple TV 4K", "Pair Siri Remote",
                               "Set up HomePod", "Stereo pair HomePod mini",
                               "Use Apple TV with Family Sharing", "Restart Apple TV"],
                 "articles": ["Update tvOS", "Set up SharePlay on Apple TV",
                              "Use the Home app", "Add a HomeKit accessory",
                              "Add Apple TV+ to a smart TV"]},
    "services": {"name": "Services & Subscriptions",
                 "top_tasks": ["Cancel a subscription", "Update Apple ID payment method",
                               "Manage Family Sharing", "Recover purchases",
                               "Request a refund", "Redeem a gift card"],
                 "articles": ["See or cancel subscriptions on iPhone",
                              "Move Apple Music library across devices",
                              "Set up a Custom Email Domain on iCloud+",
                              "Restore previous purchases",
                              "Use Apple Cash with friends"]},
    "account":  {"name": "Apple Account",
                 "top_tasks": ["Reset Apple ID password", "Recover Apple ID",
                               "Manage trusted devices", "Turn on two-factor authentication",
                               "Update Apple ID email", "Cancel Apple One"],
                 "articles": ["Set up a recovery key", "Generate an app-specific password",
                              "Manage app subscriptions",
                              "Add a phone number to your Apple ID",
                              "Remove a trusted device"]},
}


# ---------------------------------------------------------------------------
# Genius Bar / store cities  (re-used by booking page)
# ---------------------------------------------------------------------------
GENIUS_BAR_STORES = [
    {"city": "Cupertino",       "store": "Apple Park Visitor Center", "next": "Today, 3:20 PM"},
    {"city": "San Francisco",   "store": "Apple Union Square",         "next": "Today, 5:40 PM"},
    {"city": "New York",        "store": "Apple Fifth Avenue",         "next": "Tomorrow, 10:00 AM"},
    {"city": "New York",        "store": "Apple SoHo",                 "next": "Today, 6:50 PM"},
    {"city": "Chicago",         "store": "Apple Michigan Avenue",      "next": "Tomorrow, 11:20 AM"},
    {"city": "Los Angeles",     "store": "Apple The Grove",            "next": "Tomorrow, 9:30 AM"},
    {"city": "London",          "store": "Apple Regent Street",        "next": "Tomorrow, 12:40 PM"},
    {"city": "Tokyo",           "store": "Apple Marunouchi",           "next": "Tomorrow, 4:50 PM"},
    {"city": "Shanghai",        "store": "Apple Jing’an",         "next": "Tomorrow, 1:10 PM"},
    {"city": "Sydney",          "store": "Apple Sydney",               "next": "Today, 7:00 PM"},
]

GENIUS_BAR_REASONS = [
    "iPhone screen repair",
    "iPhone battery replacement",
    "Mac startup issue",
    "iPad screen damage",
    "Apple Watch band fit",
    "AirPods audio issue",
    "Apple ID help",
    "iCloud restore",
    "Setup and data transfer",
    "Accessibility setup",
]


# ---------------------------------------------------------------------------
# Trade-in quote — /trade-in/<device>/<model>/quote
# ---------------------------------------------------------------------------
TRADEIN_QUOTES = {
    "iphone": {
        "iphone-15-pro-max":   {"name": "iPhone 15 Pro Max", "good": 630, "excellent": 720, "fair": 470},
        "iphone-15-pro":       {"name": "iPhone 15 Pro",     "good": 520, "excellent": 590, "fair": 380},
        "iphone-15-plus":      {"name": "iPhone 15 Plus",    "good": 440, "excellent": 510, "fair": 320},
        "iphone-15":           {"name": "iPhone 15",         "good": 400, "excellent": 460, "fair": 290},
        "iphone-14-pro-max":   {"name": "iPhone 14 Pro Max", "good": 470, "excellent": 540, "fair": 340},
        "iphone-14-pro":       {"name": "iPhone 14 Pro",     "good": 410, "excellent": 470, "fair": 290},
        "iphone-14":           {"name": "iPhone 14",         "good": 290, "excellent": 340, "fair": 200},
        "iphone-13-pro-max":   {"name": "iPhone 13 Pro Max", "good": 350, "excellent": 420, "fair": 240},
        "iphone-13":           {"name": "iPhone 13",         "good": 230, "excellent": 270, "fair": 160},
        "iphone-12":           {"name": "iPhone 12",         "good": 150, "excellent": 180, "fair":  90},
    },
    "ipad": {
        "ipad-pro-13-m4":      {"name": "iPad Pro 13\" (M4)", "good": 720, "excellent": 820, "fair": 530},
        "ipad-pro-12-9-2022":  {"name": "iPad Pro 12.9\" 2022","good": 460,"excellent": 540,"fair": 340},
        "ipad-air-m2":         {"name": "iPad Air (M2)",       "good": 320, "excellent": 380, "fair": 220},
        "ipad-10":             {"name": "iPad (10th gen)",     "good": 170, "excellent": 200, "fair": 110},
        "ipad-mini-7":         {"name": "iPad mini (7th gen)", "good": 260, "excellent": 310, "fair": 190},
    },
    "mac": {
        "macbook-pro-16-m3":   {"name": "MacBook Pro 16\" M3", "good":1180, "excellent":1380, "fair": 830},
        "macbook-pro-14-m3":   {"name": "MacBook Pro 14\" M3", "good": 880, "excellent":1030, "fair": 620},
        "macbook-air-15-m3":   {"name": "MacBook Air 15\" M3", "good": 720, "excellent": 840, "fair": 510},
        "macbook-air-13-m3":   {"name": "MacBook Air 13\" M3", "good": 580, "excellent": 680, "fair": 410},
        "imac-m3":             {"name": "iMac (M3, 2023)",     "good": 690, "excellent": 810, "fair": 480},
        "mac-mini-m2":         {"name": "Mac mini (M2)",       "good": 360, "excellent": 420, "fair": 250},
    },
    "watch": {
        "ultra-2":  {"name": "Apple Watch Ultra 2", "good": 410, "excellent": 480, "fair": 290},
        "series-10":{"name": "Apple Watch Series 10","good": 230, "excellent": 270, "fair": 150},
        "series-9": {"name": "Apple Watch Series 9", "good": 170, "excellent": 200, "fair": 110},
        "se-2":     {"name": "Apple Watch SE (2nd gen)","good": 90,"excellent": 110, "fair":  50},
    },
}


# ---------------------------------------------------------------------------
# Apple Card apply / financing calculator
# ---------------------------------------------------------------------------
APPLE_CARD = {
    "headline": "A new kind of credit card. Created by Apple.",
    "highlights": [
        {"name": "Daily Cash",         "desc": "3% back at Apple, 2% with Apple Pay, 1% elsewhere — every day, with no limits."},
        {"name": "Apple Card Savings", "desc": "4.40% APY high-yield Savings account from Goldman Sachs, with no fees and no minimum balance."},
        {"name": "Monthly Installments","desc": "0% APR financing on eligible Apple products with Apple Card Monthly Installments."},
        {"name": "Privacy & Security", "desc": "A unique card number stored securely in Wallet, locked with Touch ID or Face ID."},
        {"name": "Family Sharing",     "desc": "Add a family member as a Co-Owner or share a card with your Family."},
    ],
    "monthly_installment_eligible": [
        "iPhone (24 mo at 0% APR)",
        "iPad (12 mo at 0% APR)",
        "Apple Watch (12 mo at 0% APR)",
        "Mac (12 mo at 0% APR)",
        "AirPods (12 mo at 0% APR)",
    ],
    "apr_range": "20.74% to 29.74% based on creditworthiness",
}


# ---------------------------------------------------------------------------
# All the registrations
# ---------------------------------------------------------------------------
def register_gui_deepen(app, db):
    """Register every new GUI surface on the Flask app."""

    # ------------ Buy iPhone configurator -----------------------------------
    @app.route('/shop/buy-iphone/<model>')
    def gui_buy_iphone(model):
        cfg = IPHONE_BUY.get(model)
        if not cfg:
            abort(404)
        return render_template(
            'buy_iphone.html', model=model, cfg=cfg,
            csrf_token_value=generate_csrf(),
        )

    # ------------ Buy Mac configurator --------------------------------------
    @app.route('/shop/buy-mac/<model>')
    def gui_buy_mac(model):
        cfg = MAC_BUY.get(model)
        if not cfg:
            abort(404)
        return render_template(
            'buy_mac.html', model=model, cfg=cfg,
            csrf_token_value=generate_csrf(),
        )

    # ------------ Buy iPad configurator -------------------------------------
    @app.route('/shop/buy-ipad/<model>')
    def gui_buy_ipad(model):
        cfg = IPAD_BUY.get(model)
        if not cfg:
            abort(404)
        return render_template(
            'buy_ipad.html', model=model, cfg=cfg,
            csrf_token_value=generate_csrf(),
        )

    # ------------ Buy Watch configurator ------------------------------------
    @app.route('/shop/buy-watch/<model>')
    def gui_buy_watch(model):
        cfg = WATCH_BUY.get(model)
        if not cfg:
            abort(404)
        return render_template(
            'buy_watch.html', model=model, cfg=cfg,
            csrf_token_value=generate_csrf(),
        )

    # ------------ Compare pages ---------------------------------------------
    @app.route('/iphone/compare')
    def gui_compare_iphone():
        return render_template('compare_iphone.html', rows=COMPARE_IPHONE)

    @app.route('/mac/compare')
    def gui_compare_mac():
        return render_template('compare_mac.html', rows=COMPARE_MAC)

    @app.route('/ipad/compare')
    def gui_compare_ipad():
        return render_template('compare_ipad.html', rows=COMPARE_IPAD)

    @app.route('/airpods/compare')
    def gui_compare_airpods():
        return render_template('compare_airpods.html', rows=COMPARE_AIRPODS)

    # ------------ Financing calculator --------------------------------------
    @app.route('/financing/calculator', methods=['GET', 'POST'])
    def gui_financing_calculator():
        # Defaults
        product_price = 999.00
        months = 24
        product_label = 'iPhone 17 Pro'
        if request.method == 'POST':
            try:
                product_price = float(request.form.get('price', product_price))
            except (TypeError, ValueError):
                pass
            try:
                months = int(request.form.get('months', months))
                months = max(6, min(months, 36))
            except (TypeError, ValueError):
                pass
            product_label = (request.form.get('product') or product_label).strip()[:80]
        monthly_zero = round(product_price / months, 2)
        # Indicative APR for non-eligible plans
        apr = 0.2074
        r = apr / 12
        monthly_apr = round(product_price * r / (1 - (1 + r) ** (-months)), 2)
        return render_template(
            'financing_calculator.html',
            product_label=product_label, product_price=product_price,
            months=months, monthly_zero=monthly_zero, monthly_apr=monthly_apr,
            apr_pct="20.74",
            preset_products=[
                ("iPhone 17 Pro Max", 1199.00),
                ("iPhone 17 Pro",      999.00),
                ("iPhone Air",         999.00),
                ("iPhone 17",          799.00),
                ("MacBook Pro 16\"",  2499.00),
                ("MacBook Pro 14\"",  1599.00),
                ("MacBook Air 15\"",  1299.00),
                ("MacBook Air 13\"",  1099.00),
                ("iPad Pro 13\"",     1299.00),
                ("iPad Pro 11\"",      999.00),
                ("iPad Air",           599.00),
                ("Apple Watch Ultra 3", 799.00),
                ("Apple Watch Series 11", 399.00),
                ("Apple Watch SE",     249.00),
                ("AirPods Pro 3",      249.00),
                ("AirPods Max",        549.00),
            ],
        )

    # ------------ Business industry hubs ------------------------------------
    @app.route('/business/retail')
    def gui_business_retail():
        return render_template('business_industry.html', slug='retail',
                               cfg=BUSINESS_INDUSTRIES['retail'])

    @app.route('/business/healthcare')
    def gui_business_healthcare():
        return render_template('business_industry.html', slug='healthcare',
                               cfg=BUSINESS_INDUSTRIES['healthcare'])

    @app.route('/business/education-pro')
    def gui_business_education_pro():
        return render_template('business_industry.html', slug='education-pro',
                               cfg=BUSINESS_INDUSTRIES['education-pro'])

    @app.route('/business/creative')
    def gui_business_creative():
        return render_template('business_industry.html', slug='creative',
                               cfg=BUSINESS_INDUSTRIES['creative'])

    # ------------ Education portals -----------------------------------------
    @app.route('/education/students')
    def gui_education_students():
        return render_template('education_students.html', cfg=EDUCATION_STUDENTS)

    @app.route('/education/educators')
    def gui_education_educators():
        return render_template('education_educators.html', cfg=EDUCATION_EDUCATORS)

    @app.route('/education/everyone-can-create')
    def gui_education_everyone_create():
        return render_template('education_everyone_create.html', cfg=EDUCATION_EVERYONE_CREATE)

    @app.route('/education/swift-playgrounds-curriculum')
    def gui_education_swift():
        return render_template('education_swift_playgrounds.html', cfg=EDUCATION_SWIFT_PLAYGROUNDS)

    # ------------ Services hubs ---------------------------------------------
    @app.route('/services/<slug>')
    def gui_services_hub(slug):
        cfg = SERVICES.get(slug)
        if not cfg:
            abort(404)
        # Distinct templates per service for richer GUI variety
        tpl = f'services_{slug.replace("-", "_")}.html'
        return render_template(tpl, slug=slug, cfg=cfg)

    @app.route('/services/icloud/storage-plans')
    def gui_icloud_storage_plans():
        return render_template('icloud_storage_plans.html', plans=ICLOUD_PLANS)

    @app.route('/services/apple-one')
    def gui_apple_one_plans():
        return render_template('apple_one_plans.html', plans=APPLE_ONE_PLANS)

    # ------------ Apple Card apply ------------------------------------------
    @app.route('/apple-card/apply', methods=['GET', 'POST'])
    def gui_apple_card_apply():
        message = None
        if request.method == 'POST':
            name = (request.form.get('name')   or '').strip()
            ssn4 = (request.form.get('ssn4')   or '').strip()
            inc  = (request.form.get('income') or '').strip()
            if not (name and len(ssn4) == 4 and ssn4.isdigit() and inc.isdigit()):
                message = ('error', "Please complete your full name, last 4 of SSN, and annual income.")
            else:
                message = ('success',
                           f"Thanks {name}. Your Apple Card pre-approval request is in review; "
                           f"we'll respond within 60 seconds in the Wallet app.")
        return render_template(
            'apple_card_apply.html', cfg=APPLE_CARD, message=message,
            csrf_token_value=generate_csrf(),
        )

    # ------------ Support categories ----------------------------------------
    @app.route('/support/category/<slug>')
    def gui_support_category(slug):
        cfg = SUPPORT_CATEGORIES.get(slug)
        if not cfg:
            abort(404)
        return render_template('support_category.html', slug=slug, cfg=cfg,
                               all_slugs=sorted(SUPPORT_CATEGORIES.keys()))

    @app.route('/support/contact')
    def gui_support_contact():
        return render_template('support_contact.html', categories=SUPPORT_CATEGORIES)

    @app.route('/support/genius-bar/booking', methods=['GET', 'POST'])
    def gui_genius_bar_booking():
        message = None
        if request.method == 'POST':
            store = (request.form.get('store')  or '').strip()
            reason= (request.form.get('reason') or '').strip()
            slot  = (request.form.get('slot')   or '').strip()
            if not (store and reason and slot):
                message = ('error', "Pick a store, a reason, and a time slot to book.")
            else:
                message = ('success', f"Genius Bar reservation confirmed at {store} on {slot} for: {reason}.")
        return render_template(
            'genius_bar_booking.html', stores=GENIUS_BAR_STORES,
            reasons=GENIUS_BAR_REASONS, message=message,
            csrf_token_value=generate_csrf(),
        )

    # ------------ Trade-in quote (deep) -------------------------------------
    @app.route('/trade-in/<device>/<model>/quote')
    def gui_trade_in_quote(device, model):
        bucket = TRADEIN_QUOTES.get(device)
        if not bucket:
            abort(404)
        q = bucket.get(model)
        if not q:
            abort(404)
        return render_template('trade_in_quote.html',
                               device=device, model=model, quote=q,
                               family=list(bucket.items()))
