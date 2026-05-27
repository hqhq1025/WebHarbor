#!/usr/bin/env python3
"""Generate WebVoyager-style natural-language tasks for R3-R10 deepening.

R3 = Subscribe & Save / auto-delivery
R4 = Gift Center / Registry (wedding, baby, birthday)
R5 = Amazon Fresh / Whole Foods (delivery windows, curbside pickup)
R6 = Product Q&A (ask, answer, vote, helpful)
R7 = Kindle / Prime Video / Audible / Music Unlimited / Redeem codes
R8 = Seller profiles / Brand stores / Seller rating leaderboard
R9 = Vine / Early Reviewer / Promo codes
R10 = Cross-flow polish (multi-round multi-step natural tasks)

Each round targets >=200 tasks.  Task IDs follow:
    Amazon--rN_<theme>_<NNN>
where NNN is zero-padded within the (round, theme) bucket.

Tasks are appended to sites/amazon/tasks.jsonl.
ALL tasks must be GUI-style WebVoyager natural language — never
"Navigate to /subscribe-save/plan/...", never "parse the JSON".
"""

import json
import os
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TASKS_PATH = os.path.join(BASE, 'tasks.jsonl')
WEB = "http://localhost:40001/"
UPSTREAM = "https://www.amazon.com/"

BUCKETS: list[tuple[int, str, list[str]]] = []  # (round, theme, [ques])


def add(round_no: int, theme: str, items: list[str]) -> None:
    BUCKETS.append((round_no, theme, items))


# ============================================================
# R3 - Subscribe & Save / auto-delivery
# ============================================================

R3_PLANS = [
    "Tide Pods laundry detergent",
    "Pampers Swaddlers diapers",
    "Folgers Classic Roast ground coffee",
    "Charmin Ultra Soft toilet paper",
    "Bounty paper towels",
    "Dove body wash",
    "Purina Pro Plan dry dog food",
    "Cheerios cereal",
    "Bumble Bee tuna",
    "Tropicana orange juice (no-pulp)",
    "Kirkland AAA batteries",
    "Quaker oatmeal",
]

add(3, "ss_setup", [
    f"Subscribe & Save: enroll '{p}' to deliver every 2 months and report the new monthly cost shown after the 5% discount."
    for p in R3_PLANS
] + [
    "Open Subscribe & Save, find the active plan for 'Original Ember Pillow Queen' under alice.j@test.com, and tell me its current delivery frequency.",
    "Sign in as alice.j@test.com, open Subscribe & Save manage page, and report how many active plans she currently has.",
    "Sign in as bob.c@test.com, open Subscribe & Save, and tell me which two products he is subscribed to and at what frequency each.",
    "Sign in as carol.d@test.com, open Subscribe & Save manage, and list all three of her active subscriptions with their next-delivery dates.",
    "Sign in as david.k@test.com, open Subscribe & Save, and tell me the longest delivery frequency (in months) he has on any active plan.",
    "Open Subscribe & Save and report the percentage discount applied at the 5+ active-plan tier shown on the tier banner.",
    "Open Subscribe & Save manage and report what the page calls the savings tier between 1 and 4 active plans.",
    "Sign in as alice.j@test.com, then on Subscribe & Save, identify which of her plans has the largest quantity per delivery and report the quantity.",
    "Sign in as carol.d@test.com, open Subscribe & Save, and tell me which of her plans has the lowest single-shipment cost.",
    "Add 'AI Robot Vacuum RVEmber' to a new 3-month Subscribe & Save plan for alice.j@test.com and report the next scheduled delivery date.",
    "Sign in as bob.c@test.com, change the 'Advanced Night Repair Serum' Subscribe & Save frequency from 6-month to 3-month, and report the updated next-delivery date.",
    "Sign in as alice.j@test.com, change the frequency on her 'AI Robot Vacuum RVEmber' plan from 1-month to 3-month, and confirm the new frequency shown on the manage page.",
    "Sign in as david.k@test.com, change his 'Premier Space Saving' set plan to 2-month frequency, then report the new total of his upcoming month's deliveries.",
    "Sign in as carol.d@test.com, switch her 'Niacinamide 10% + Zinc' plan to 1-month and tell me how many bottles she will receive each month.",
    "Sign in as bob.c@test.com, change his 'Smart Oven Air Fryer Pro' plan to 6-month delivery and confirm the new next-shipment date.",
    "Sign in as alice.j@test.com, switch all three of her active 1-month plans to 2-month and tell me how many shipments are still scheduled this calendar quarter.",
])

add(3, "ss_cancel", [
    "Sign in as alice.j@test.com, open Subscribe & Save manage, cancel the 'FreeSip Ember' bottle plan, and report how many active plans she has left.",
    "Sign in as bob.c@test.com, cancel his 'Smart Oven Air Fryer Pro' Subscribe & Save plan and confirm only one active plan remains.",
    "Sign in as carol.d@test.com, cancel the 'Wood Sage & Sea Salt' cologne subscription and report whether her tier banner discount drops.",
    "Sign in as david.k@test.com, cancel his 'Magnifica Foxglove' espresso subscription and report the number of remaining active plans.",
    "Sign in as alice.j@test.com, cancel the 'Resurrection Aromatique Hand Wash' plan and then report the new monthly subtotal across her remaining S&S plans.",
    "Sign in as bob.c@test.com, cancel BOTH of his Subscribe & Save plans and report the empty-state message that appears on Subscribe & Save manage.",
])

add(3, "ss_schedule", [
    "Sign in as alice.j@test.com, open the schedule view of her 'Original Ember Pillow Queen' Subscribe & Save plan, and report the date of the next 'upcoming' delivery (the one after 'next').",
    "Sign in as alice.j@test.com, open the schedule view of her 'AI Robot Vacuum RVEmber' plan, skip the next scheduled delivery, and report the date that is now marked 'next'.",
    "Sign in as bob.c@test.com, open the schedule view of his 'Advanced Night Repair Serum' plan and tell me how many upcoming deliveries are listed.",
    "Sign in as carol.d@test.com, open the schedule view of her 'Classic Foxglove 4.5-Qt Stand Mixer' plan, skip the next delivery, and confirm the cancellation notice on the schedule page.",
    "Sign in as david.k@test.com, open the schedule view of his 'The Dewy Skin Cream' plan and report the spacing in months between consecutive scheduled deliveries.",
    "Sign in as alice.j@test.com, skip TWO consecutive upcoming deliveries on her 'Hairdresser's Invisible Oil' plan and report the new 'next' delivery date.",
])

add(3, "ss_tier", [
    "Open Subscribe & Save manage as alice.j@test.com (she has 5 active plans) and report which tier label (e.g. 'Saver', 'Plus') the banner is showing.",
    "Open Subscribe & Save manage as carol.d@test.com and report the tier discount percentage displayed on her banner.",
    "Sign in as alice.j@test.com, then go to checkout with any cart item; report whether the order summary shows a Subscribe & Save tier line and the discount amount on it.",
    "Sign in as bob.c@test.com (with 2 active plans), open Subscribe & Save manage, and tell me how many more active plans he needs to reach the next discount tier per the tier banner.",
    "Sign in as alice.j@test.com, cancel one plan so she has 4 active, refresh Subscribe & Save manage, and report whether the tier banner percentage changed.",
])

# Bulk fill R3 — pump to >=200 using product templates
SS_BULK_PRODUCTS = [
    "Pampers Pure Protection diapers", "Huggies Little Snugglers diapers",
    "Glad ForceFlex trash bags", "Ziploc Slider gallon bags",
    "Brita pitcher replacement filters", "Crest 3D White toothpaste",
    "Colgate Total toothpaste", "Listerine Cool Mint mouthwash",
    "Oral-B Pro electric toothbrush brush heads", "Sensodyne Pronamel toothpaste",
    "Old Spice High Endurance deodorant", "Dove Men+Care body wash",
    "Pantene Pro-V shampoo", "Head & Shoulders shampoo",
    "Aveeno Daily Moisturizing lotion", "CeraVe Moisturizing Cream",
    "Cottonelle Ultra Clean toilet paper", "Scott 1000 toilet paper",
    "Viva Multi-Surface paper towels", "Brawny Tear-A-Square towels",
    "Cascade Platinum dishwasher pacs", "Finish Quantum dishwasher tabs",
    "Dawn Ultra dish soap", "Method Squirt + Mop cleaner",
    "Clorox disinfecting wipes", "Lysol disinfecting spray",
    "Mrs. Meyer's lavender hand soap", "Method foaming hand wash",
    "Iams ProActive Health dry dog food", "Blue Buffalo Life Protection dog food",
    "Purina Fancy Feast wet cat food", "Friskies Pate cat food variety pack",
    "Greenies Original dental dog treats", "Temptations Classic cat treats",
    "Tide Pods Spring Meadow", "Persil ProClean liquid detergent",
    "Gain Original liquid detergent", "Arm & Hammer Clean Burst detergent",
    "Downy Ultra fabric softener", "Bounce Outdoor Fresh dryer sheets",
    "Folgers Black Silk ground coffee", "Maxwell House Original ground coffee",
    "Starbucks Pike Place K-Cups", "Green Mountain Breakfast Blend K-Cups",
    "Coffee Mate French Vanilla creamer", "International Delight Hazelnut creamer",
    "Honey Nut Cheerios cereal", "Frosted Flakes cereal",
    "Kellogg's Special K Red Berries", "Quaker Oat Squares cereal",
    "Nature Valley Crunchy Granola Bars", "KIND Almond Coconut bars",
    "Clif Bar Variety Pack", "RX Bar Chocolate Sea Salt 12-pack",
    "Premier Protein Chocolate shake 12-pack", "Ensure Original Vanilla shake",
    "Gatorade Frost Glacier Freeze 12-pack", "Powerade Mountain Berry 12-pack",
    "Bumble Bee tuna in water 12-pack", "StarKist Chunk Light tuna pouches",
    "Mott's Original apple juice 8-pack", "Tropicana Trop50 orange juice",
    "Stonyfield Organic whole milk yogurt", "Chobani Greek Vanilla yogurt",
    "Yasso frozen Greek yogurt bars", "Halo Top vanilla bean pints",
    "RX Bar nut butter sachets", "Justin's classic almond butter",
    "Kirkland whole almonds", "Planters mixed nuts",
    "Skinnypop popcorn 18-pack", "Lay's Classic potato chips",
    "Stacy's Pita Chips simply naked", "Pirate's Booty puffs",
    "Welch's fruit snacks variety pack", "Annie's organic fruit snacks",
    "Goldfish Cheddar crackers", "Cheez-It Original crackers",
    "Triscuit Original crackers", "Wheat Thins Original crackers",
    "Pirouline chocolate hazelnut wafers", "Walkers shortbread fingers",
]

ss_bulk_qs = []
freqs = ['1 month', '2 months', '3 months', '4 months', '6 months']
for i, p in enumerate(SS_BULK_PRODUCTS):
    freq = freqs[i % len(freqs)]
    ss_bulk_qs.append(
        f"Subscribe & Save: set up '{p}' to deliver every {freq} with quantity 1, then report the next scheduled delivery date shown."
    )
    ss_bulk_qs.append(
        f"Sign in as alice.j@test.com, then on Subscribe & Save manage, add '{p}' to her plans at {freq} frequency, and tell me how many active plans she now has."
    )
add(3, "ss_enroll", ss_bulk_qs)

# ============================================================
# R4 - Gift Center / Registry
# ============================================================
add(4, "reg_browse", [
    "Open the Gift Center, find the registry titled 'Alice & Jordan Wedding Registry', and report its public code (e.g. 'WED-AJ-2026').",
    "Open the Gift Center and report how many public registries are currently listed on the landing page.",
    "Open the Gift Center, scroll to baby registries, and tell me how many baby registries are listed.",
    "Open the Gift Center, find 'Mia turns 5 - Princess Party' registry, and report the event date.",
    "Open the Gift Center, find 'Baby Chen on the Way', and tell me the shipping city in the public address.",
    "Open the Gift Center, find 'David & Priya's Baby Registry', and report its event date.",
    "Open the Gift Center, find the registry titled 'Arjun turns 8 - Robotics Theme', and report its public code.",
    "Open the Gift Center, find 'Carol & Daniel - Vow Renewal', and tell me the event date.",
    "Open the Gift Center, count how many wedding registries are listed and report the count.",
    "Open the Gift Center, count how many birthday registries are listed and report the count.",
    "Open the Gift Center landing and tell me the description shown on 'Alice & Jordan Wedding Registry'.",
    "Open the registry with public code WED-AJ-2026 and report the name of the very first must-have item listed.",
    "Open the registry with public code BABY-BC-2026 and tell me how many items are still un-purchased (qty_wanted > qty_purchased).",
    "Open the registry with public code BIRTH-MD-2026 and report the most expensive must-have item.",
    "Open the registry with public code BIRTH-AK-2026, find any laptop or computer in the items list, and report its full title.",
    "Open the registry with public code WED-CD-2026 and report how many items are marked 'must-have'.",
    "Open the registry with public code BABY-DK-2026 and report the total number of items listed.",
    "Open the public registry view for BIRTH-AK-2026 and tell me how many items have priority 'low'.",
    "Open the public registry view for WED-AJ-2026 and report the count of items with priority 'nice-to-have'.",
    "Open the public registry view for BABY-BC-2026 and report the first listed iPhone variant (color and storage).",
    "Open the Gift Center landing and tell me which of the six listed registries has the earliest event date.",
    "Open the Gift Center landing and tell me which registry has the latest event date.",
])

add(4, "reg_mine", [
    "Sign in as alice.j@test.com, open 'Your registries', and report how many registries she owns plus how many she collaborates on.",
    "Sign in as bob.c@test.com, open 'Your registries', and report the title of the baby registry he owns.",
    "Sign in as carol.d@test.com, open 'Your registries', and tell me both registry titles she owns and their event types.",
    "Sign in as david.k@test.com, open 'Your registries', and tell me both registry titles he owns and their event types.",
    "Sign in as alice.j@test.com, open 'Your registries', then click into her wedding registry and report how many collaborators are listed.",
    "Sign in as bob.c@test.com, open his baby registry, and report the shipping address city + state shown.",
    "Sign in as carol.d@test.com, open her birthday registry for Mia, and report the description.",
    "Sign in as david.k@test.com, open his baby registry, and report the event date and the count of must-have items.",
])

add(4, "reg_add_item", [
    "Sign in as alice.j@test.com, open her wedding registry, add 'Cosori Pro II 5.8-Qt Air Fryer' as a must-have with quantity 2, and confirm it appears at the top of the must-have list.",
    "Sign in as bob.c@test.com, add 'Crocs Classic Clog Adult' to his baby registry as nice-to-have quantity 1, and confirm it shows in the list.",
    "Sign in as carol.d@test.com, add 'Hot Wheels 50-Car Pack of 1:64 Scale Vehicles' to her birthday registry as must-have quantity 3, and confirm it shows.",
    "Sign in as david.k@test.com, add 'Echo Dot (5th Gen)' to his baby registry as nice-to-have quantity 2, and confirm the new item appears.",
    "Sign in as alice.j@test.com, add 'Apple AirPods Pro (2nd Generation) Wireless Earbuds' to her wedding registry as nice-to-have quantity 1, and confirm.",
    "Sign in as carol.d@test.com, add 'Keurig K-Elite Single Serve Coffee Maker' to her vow-renewal wedding registry as must-have quantity 1, and confirm the addition.",
    "Sign in as david.k@test.com, add 'Apple iPad Air (M2) 128GB (Space Gray)' to his Arjun-robotics birthday registry as must-have quantity 1, and confirm.",
    "Sign in as bob.c@test.com, add 'Instant Pot Duo 7-in-1 Electric Pressure Cooker' to his baby registry as must-have quantity 1, and confirm.",
])

add(4, "reg_mark_purchased", [
    "Sign in as alice.j@test.com, open her wedding registry, mark the first 'must-have' item as purchased, and confirm the purchased count went up by 1.",
    "Sign in as bob.c@test.com, open his baby registry, mark 'Apple iPhone 15 Pro (1TB, Blue Titanium)' as purchased, and confirm the change reflects on the public view too.",
    "Sign in as carol.d@test.com, mark 'Le rouge et le noir' as purchased on Mia's birthday registry and confirm the purchased counter increments.",
    "Sign in as david.k@test.com, mark 'Apple MacBook Air 13\" M3 - 64GB RAM, 512GB' on Arjun's birthday registry as purchased and report the new purchased count.",
    "Sign in as alice.j@test.com, mark 'Therabody Theragun Prime Massage Gun' as purchased on her wedding registry and confirm the public view shows it as fulfilled.",
    "Sign in as bob.c@test.com, mark 'Original Two Pillow Queen' as purchased on his baby registry and confirm the qty_purchased counter increments.",
])

add(4, "reg_invite", [
    "Sign in as alice.j@test.com, open her wedding registry, invite bob.c@test.com as a collaborator, and confirm he now appears in the collaborator list.",
    "Sign in as bob.c@test.com, open his baby registry, invite alice.j@test.com as collaborator, and confirm the invitation succeeded.",
    "Sign in as carol.d@test.com, invite david.k@test.com to collaborate on Mia's birthday registry and confirm.",
    "Sign in as david.k@test.com, open his baby registry, invite alice.j@test.com and carol.d@test.com to collaborate, and report the total collaborator count after.",
    "Sign in as alice.j@test.com, open her wedding registry, invite carol.d@test.com as collaborator, then sign out and verify carol can see this registry under 'Your registries'.",
    "Sign in as bob.c@test.com, attempt to add an item to alice.j's wedding registry directly (without invitation), and report the access-denied / permission message shown.",
])

# Bulk R4
gift_themes = [
    ("wedding", "Alice & Jordan", "WED-AJ-2026", "blender / cookware"),
    ("wedding", "Carol & Daniel vow renewal", "WED-CD-2026", "stand mixer"),
    ("baby", "Baby Chen", "BABY-BC-2026", "stroller / car seat"),
    ("baby", "David & Priya", "BABY-DK-2026", "nursery monitor"),
    ("birthday", "Mia 5th birthday", "BIRTH-MD-2026", "Frozen-Elsa toy"),
    ("birthday", "Arjun 8th robotics", "BIRTH-AK-2026", "robotics-themed product"),
]
gift_bulk = []
gift_actions = [
    "open the gift center and find this registry by name, then report the public code",
    "open this registry by public code and report the description shown",
    "open this registry by public code and report the count of nice-to-have items",
    "open this registry and report the most expensive item still un-purchased",
    "open this registry, sort by priority, and tell me the first must-have item",
    "open this registry and tell me how many items have qty_wanted greater than 2",
    "open this registry and report whether 'Apple MacBook Air' or any laptop is in the items list",
    "open this registry and report whether any pressure cooker is listed",
    "open this registry's event date and tell me how many days remain until the event from today",
    "open this registry and report the shipping city + state shown in the public address",
]
for et, name, code, hint in gift_themes:
    for act in gift_actions:
        gift_bulk.append(f"For the {et} registry '{name}' ({code}), {act}.")
add(4, "reg_browse_bulk", gift_bulk)

# more R4 — gift card / wishlist crossover
gift_xover = []
for code in ['WED-AJ-2026', 'BABY-BC-2026', 'BIRTH-MD-2026', 'WED-CD-2026', 'BABY-DK-2026', 'BIRTH-AK-2026']:
    gift_xover.append(
        f"Open the registry by public code {code}, identify one must-have item that is not yet purchased, add it to your own cart, and report the cart subtotal."
    )
    gift_xover.append(
        f"Open the registry by public code {code}, count the items still marked 'must-have' and un-purchased, and report the count along with the first such item's name."
    )
    gift_xover.append(
        f"Open the registry by public code {code} and tell me the percentage of items already purchased (rounded to nearest 10%)."
    )
add(4, "reg_actions", gift_xover)

# Additional R4 bulk — registry-item-detail tasks
r4_items_long = [
    "Apple iPhone 15 Pro (1TB, Blue Titanium) - Unlocked",
    "Apple MacBook Pro 16\" M3 Max - 16GB RAM, 256GB, Silver",
    "Apple iPad Air (M2) 128GB (Space Gray)",
    "Samsung Galaxy Tab S9 Ultra 256GB (Graphite)",
    "Google Pixel 7a (256GB, Obsidian) - Unlocked",
    "Apple MacBook Air 13\" M3 - 64GB RAM, 512GB, Space Gray",
    "Logitech G Pro X Superlight 2 Wireless Mouse",
    "NVIDIA GeForce RTX 4070 Founders Edition",
    "Therabody Theragun Prime Massage Gun",
    "Original Two Pillow Queen", "Inferno",
    "Captains Courageous", "Frozen Elsa Singing Doll Edition X",
    "Z-Man Games Pandemic Board Game",
    "Surface Pro XL (i7, 16GB)",
    "Sklz Pro Mini Basketball Hoop System",
    "HeatGear Compression Shirt Size Studio",
    "Maybe You Should Talk to Someone",
    "Motorola Edge 50 Pro (256GB, Luxe Lavender) - Unlocked",
    "Nothing Phone (2) (1TB, White) - Unlocked",
    "Dell XPS 15 OLED - 64GB RAM, 1TB, Platinum Silver",
    "Roughing It", "Shadow and Bone",
    "Apple iPhone 13 (512GB, Blue Titanium) - Unlocked",
    "Le rouge et le noir", "Fahrenheit 451",
]
r4_codes = ['WED-AJ-2026', 'BABY-BC-2026', 'BIRTH-MD-2026', 'WED-CD-2026', 'BABY-DK-2026', 'BIRTH-AK-2026']
r4_extra = []
for it in r4_items_long:
    for code in r4_codes[:3]:
        r4_extra.append(
            f"Open the registry with public code {code} and search for '{it}'; report whether it appears in the registry's item list (yes/no), and if yes, its qty_wanted and priority."
        )
add(4, "reg_item_lookup", r4_extra)

# ============================================================
# R5 - Amazon Fresh / Whole Foods
# ============================================================
add(5, "fresh_browse", [
    "Open Amazon Fresh and report the name of the first product shown on the storefront.",
    "Open Amazon Fresh and tell me how many product cards are on the landing storefront.",
    "Open Whole Foods and report the name of the first item shown.",
    "Open Whole Foods storefront and tell me the temperature zone or shelf-life note of the first item displayed.",
    "Open Amazon Fresh, identify the cheapest item shown on the storefront, and report its price.",
    "Open Whole Foods, identify the most expensive item shown on the storefront, and report its price.",
    "Open Amazon Fresh, look for any frozen item, and tell me its name and price.",
    "Open Amazon Fresh, look for any refrigerated (chilled) item, and report its name and shelf-life note.",
    "Open Whole Foods, look for an organic produce item, and report its price per unit.",
    "Open Whole Foods, look for any prepared meal item, and report its name plus temperature zone.",
    "Open Amazon Fresh, sort the listing by shelf life ascending, and tell me which item is at the top.",
    "Open Whole Foods, sort by temperature zone, and tell me which zone has the most items on the page.",
    "Open Amazon Fresh, find the produce section, and report how many items are shown in that section.",
    "Open Whole Foods, find the dairy section, and report the number of items there.",
    "Open Amazon Fresh, find the 'frozen' section, and report the cheapest frozen item shown.",
    "Open Whole Foods, find the meat & seafood section, and report two items and their prices.",
    "Open Amazon Fresh, find the bakery section, and report the most popular item by reviews.",
    "Open Whole Foods, find the prepared meals section, and report the name and price of the highest-priced meal.",
    "Open Amazon Fresh, click any item and report its shelf life or 'best by' indicator on the detail page.",
    "Open Whole Foods, click any chilled (refrigerated) item, and report the temperature zone shown on the detail page.",
])

add(5, "fresh_delivery_window", [
    "Open the Amazon Fresh delivery-window picker and report the earliest available 2-hour window today.",
    "Open the Amazon Fresh delivery-window picker, select a 2-hour window tomorrow morning, and confirm the selection on the next page.",
    "Open the Amazon Fresh delivery-window picker, look for an attended-only (cold-chain) window, and report whether such a window exists today.",
    "Open the Amazon Fresh delivery-window picker, pick the latest window available tomorrow, and report its time range.",
    "Open the Amazon Fresh delivery-window picker and tell me how many distinct delivery windows are offered across the next 3 days.",
    "Open Amazon Fresh, add a frozen item to your cart, then open delivery-window picker; report which windows are filtered out due to the cold-chain requirement.",
    "Open Amazon Fresh, add any refrigerated milk item, then open delivery-window picker; report whether the picker forces attended delivery.",
    "Open the Amazon Fresh delivery-window picker, choose a same-day window, and confirm the confirmation page shows the selected window.",
    "Open the Amazon Fresh delivery-window picker, choose a window 3 days out, and report the price difference vs the same-day window if any.",
    "Open the Amazon Fresh delivery-window picker and tell me what surcharge (if any) applies to the earliest same-day window vs a 2-day-out window.",
])

add(5, "wholefoods_pickup", [
    "Open the Whole Foods curbside pickup page and tell me the first available pickup slot today.",
    "Open the Whole Foods curbside pickup page, pick a 1-hour window tomorrow afternoon, and confirm on the next screen.",
    "Open the Whole Foods curbside pickup page and report the closest store (by name) used for pickup.",
    "Open the Whole Foods curbside pickup page and report the latest pickup window available tomorrow.",
    "Open the Whole Foods curbside pickup page, count distinct windows offered today, and report the count.",
    "Open the Whole Foods curbside pickup page, identify whether there's an attended-only window, and report 'yes' or 'no'.",
    "Open the Whole Foods curbside pickup page, pick a 30-min slot 2 days out, and confirm the confirmation page shows the slot.",
    "Open the Whole Foods curbside pickup, then add a frozen item to your cart, and report whether the pickup page warns about cold-chain handling.",
])

# bulk R5 — categories + products
fresh_cats = [
    "produce", "dairy", "frozen", "bakery", "meat", "seafood",
    "deli", "prepared meals", "snacks", "beverages",
    "pantry staples", "organic produce", "gluten-free", "vegan",
    "household paper", "personal care",
]
fresh_items = [
    "Organic Hass Avocado 4-pack", "Honeycrisp Apples 2lb",
    "Driscoll's Strawberries 16oz", "Whole Foods 365 Whole Milk",
    "Chobani Greek yogurt vanilla", "Eggland's Best large eggs dozen",
    "Frozen blueberries 12oz", "DiGiorno frozen pizza pepperoni",
    "Ezekiel sprouted bread", "Dave's Killer Bread 21 whole grains",
    "Atlantic salmon fillet 1lb", "Boneless skinless chicken breast 2lb",
    "Organic baby spinach 5oz", "Mini sweet peppers 1lb",
    "Beyond Burger plant-based patties", "Impossible ground 'beef' 12oz",
    "365 organic AA brown eggs", "Annie's mac & cheese 6oz",
    "Whole Foods sushi roll combo platter", "Whole Foods rotisserie chicken",
    "Cold Brew coffee 32oz bottle", "Topo Chico mineral water 12-pack",
    "Califia almond milk unsweetened", "Oatly oat milk barista edition",
    "Kerrygold Pure Irish Butter unsalted", "Tillamook sharp cheddar 8oz",
    "Bob's Red Mill rolled oats 32oz", "Quinoa organic 16oz",
    "Annie's organic peanut butter bunny crackers", "Late July sea salt tortilla chips",
    "Boar's Head turkey breast 1/2 lb", "Applegate Farms ham 8oz",
    "Lily's dark chocolate chips", "Vital Farms pasture-raised eggs",
]
fresh_bulk = []
for it in fresh_items:
    fresh_bulk.append(f"Open Amazon Fresh, search '{it}', and report the price per unit shown on the result.")
    fresh_bulk.append(f"Open Whole Foods, search '{it}', and report the temperature zone and shelf-life note on the detail page.")
add(5, "fresh_search", fresh_bulk)

# multi-step R5
fresh_multi = []
for it in fresh_items[:30]:
    fresh_multi.append(
        f"Add '{it}' from Amazon Fresh to your cart, then open the delivery-window picker, pick the earliest same-day window, and report the resulting order subtotal."
    )
    fresh_multi.append(
        f"Add '{it}' from Whole Foods to your cart, then open the curbside pickup picker, pick a slot tomorrow, and confirm the pickup store shown."
    )
add(5, "fresh_multi", fresh_multi)

# Additional R5 — more fresh / whole-foods polish
fresh_more = []
for it in fresh_items[:35]:
    fresh_more.append(
        f"Open Amazon Fresh, find '{it}', and report its temperature zone (frozen / refrigerated / shelf-stable)."
    )
add(5, "fresh_zone", fresh_more)

# ============================================================
# R6 - Product Q&A
# ============================================================
add(6, "qa_browse", [
    "Open the product 'Apple AirPods Pro (2nd Generation) Wireless Earbuds' Q&A tab and report how many questions are listed.",
    "Open the product 'Crocs Classic Clog Adult' Q&A and report the top-voted question.",
    "Open the product 'Echo Dot (5th Gen) Smart Speaker with Alexa' Q&A and report the count of answered vs un-answered questions.",
    "Open the product 'Instant Pot Duo 7-in-1 Electric Pressure Cooker' Q&A and report the highest vote_score across all questions on the page.",
    "Open the product 'Cosori Pro II 5.8-Qt Air Fryer' Q&A and report the most-helpful answer's text.",
    "Open the product 'Keurig K-Elite Single Serve Coffee Maker' Q&A and report the most-voted question's text and its vote count.",
    "Open the product 'Hydro Flask 32 oz Wide Mouth Bottle' Q&A and report whether any question has a vote_score above 50.",
    "Open the product 'Hot Wheels 50-Car Pack' Q&A, sort by 'most recent', and tell me the latest question asked.",
    "Open the product 'Polo Ralph Lauren Classic Fit Polo Mens' Q&A and report the top question.",
    "Open the product 'Levi's Men's 511 Slim Fit Jeans' Q&A and report the second-highest voted question.",
    "Open the product 'Sony WH-1000XM5' Q&A and report whether at least one question is about battery life.",
    "Open the product 'Apple iPad Air (M2) 128GB' Q&A and report the count of questions tagged about screen.",
    "Open the product 'Nike Sportswear Club Fleece Pullover Hoodie' Q&A and report the most recent question and its asker (if shown).",
    "Open the product 'Timberland 6-Inch Premium Waterproof Boot' Q&A, filter to answered-only, and report how many are shown.",
    "Open the product 'Linenspa 2 Inch Gel Memory Foam Topper Queen' Q&A, sort by oldest, and report the very first question text.",
])

add(6, "qa_ask", [
    "Sign in as alice.j@test.com, open 'Apple AirPods Pro (2nd Generation)' Q&A, ask 'Are these compatible with Android phones?', and confirm the new question appears at top of the un-answered list.",
    "Sign in as bob.c@test.com, open 'Instant Pot Duo 7-in-1' Q&A, ask 'Does this fit a 6-quart liner inside?', and confirm posting succeeded.",
    "Sign in as carol.d@test.com, open 'Cosori Pro II 5.8-Qt Air Fryer' Q&A, ask 'Is the basket dishwasher safe?', and confirm posting.",
    "Sign in as david.k@test.com, open 'Echo Dot (5th Gen)' Q&A, ask 'Can this control Zigbee bulbs without a hub?', and confirm.",
    "Sign in as alice.j@test.com, open 'Hydro Flask 32 oz Wide Mouth' Q&A, ask 'Does it fit a standard car cup holder?', and confirm the new question appears.",
    "Sign in as bob.c@test.com, open 'Hot Wheels 50-Car Pack' Q&A, ask 'Are any cars duplicated in the pack?', and confirm posting.",
    "Sign in as carol.d@test.com, open 'Apple iPad Air (M2) 128GB' Q&A, ask 'Does this support Apple Pencil 2?', and confirm.",
    "Sign in as david.k@test.com, open 'Sony WH-1000XM5' Q&A, ask 'Can I pair this with two devices at once?', and confirm.",
])

add(6, "qa_answer", [
    "Sign in as alice.j@test.com, open any product Q&A with an un-answered question, answer it with 'Yes, this works as expected.', and confirm the answer appears under the question.",
    "Sign in as bob.c@test.com, open 'Instant Pot Duo 7-in-1' Q&A, answer the top un-answered question with 'Yes, it has a 6-quart liner.', and confirm posting.",
    "Sign in as carol.d@test.com, open 'Cosori Pro II 5.8-Qt Air Fryer' Q&A, answer 'Yes, the basket is dishwasher safe.', and confirm posting.",
    "Sign in as david.k@test.com, open 'Echo Dot (5th Gen)' Q&A, answer with 'You need a Zigbee hub.', and confirm.",
    "Sign in as alice.j@test.com, open 'Apple iPad Air (M2) 128GB' Q&A, answer the screen-tag question, and confirm.",
    "Sign in as bob.c@test.com, open 'Crocs Classic Clog Adult' Q&A, answer a sizing question with 'Order 1 size up.', and confirm.",
])

add(6, "qa_vote", [
    "Sign in as alice.j@test.com, open 'Apple AirPods Pro (2nd Generation)' Q&A, upvote the top question, and report the new vote_score.",
    "Sign in as bob.c@test.com, open 'Instant Pot Duo 7-in-1' Q&A, downvote a low-quality question, and confirm the score decreased by 1.",
    "Sign in as carol.d@test.com, open 'Cosori Pro II 5.8-Qt Air Fryer' Q&A, upvote the top answer (not question), and report the helpful counter on it.",
    "Sign in as david.k@test.com, open 'Echo Dot (5th Gen)' Q&A, mark an answer 'helpful', and confirm the helpful counter goes up.",
    "Sign in as alice.j@test.com, open 'Hydro Flask 32 oz Wide Mouth' Q&A, upvote 3 different questions, and report the cumulative net vote increase.",
])

# Bulk Q&A
qa_products = [
    "Apple iPhone 15 Pro (1TB, Blue Titanium) - Unlocked",
    "Apple MacBook Pro 16\" M3 Max", "Apple iPad Air (M2) 128GB",
    "Samsung Galaxy S24 Ultra 256GB", "Sony WH-1000XM5",
    "Echo Dot (5th Gen)", "Kindle Paperwhite",
    "Instant Pot Duo 7-in-1", "Cosori Pro II 5.8-Qt Air Fryer",
    "Keurig K-Elite Single Serve Coffee Maker",
    "Hydro Flask 32 oz Wide Mouth Bottle", "Crocs Classic Clog Adult",
    "Levi's Men's 501 Original Fit Jeans", "Nike Sportswear Club Fleece Pullover Hoodie",
    "Timberland 6-Inch Premium Waterproof Boot", "Polo Ralph Lauren Classic Fit Polo Mens",
    "Hot Wheels 50-Car Pack", "Frozen Elsa Singing Doll Edition X",
    "Sklz Pro Mini Basketball Hoop System", "Logitech G Pro X Superlight 2 Wireless Mouse",
    "NVIDIA GeForce RTX 4070 Founders Edition", "Therabody Theragun Prime Massage Gun",
    "Z-Man Games Pandemic Board Game", "Original Two Pillow Queen",
    "Linenspa 2 Inch Gel Memory Foam Topper Queen",
]
qa_questions_bulk = [
    "report the number of questions listed and the top-voted question's text",
    "sort by 'most recent' and tell me when the latest question was posted",
    "report the count of answered vs un-answered questions",
    "report the highest helpful count on any answer",
    "find a question about size/fit (if any) and report the asker's first sentence",
    "find a question about battery (if any) and report whether it is answered",
    "report whether at least one question has a vote_score above 30",
    "click into the most-voted answer's parent question and report the answer text",
]
qa_bulk = []
for p in qa_products:
    for q in qa_questions_bulk:
        qa_bulk.append(f"Open the Q&A tab on '{p}' and {q}.")
add(6, "qa_browse_bulk", qa_bulk)

# ============================================================
# R7 - Kindle / Prime Video / Audible / Music / Redeem
# ============================================================
add(7, "kindle_browse", [
    "Open the Kindle Store and report the most-recent release title shown.",
    "Open the Kindle Store and tell me how many of the listed books are eligible for Kindle Unlimited.",
    "Open the Kindle Store, filter to genre 'fantasy', and report how many books are listed.",
    "Open the Kindle Store, sort by price ascending, and tell me the cheapest book title.",
    "Open the Kindle Store, sort by page count descending, and report the book with the highest page count.",
    "Open the Kindle Store and report the average price of books shown on the landing page (rounded to two decimals).",
    "Open the Kindle Store and tell me which Brandon Sanderson title is listed.",
    "Open the Kindle Store and report the title of the most expensive book.",
    "Open the Kindle Store, filter to non-fiction, and report 3 titles.",
    "Open the Kindle Store, filter to biography, and tell me which biography has the highest page count.",
    "Open the Kindle Store, find 'Sapiens: A Brief History of Humankind', and report its file size in MB.",
    "Open the Kindle Store, find 'Project Hail Mary', and report its author and price.",
    "Open the Kindle Store, find 'Fourth Wing', and tell me whether it's eligible for Kindle Unlimited.",
    "Open the Kindle Store, find 'Becoming' by Michelle Obama, and report its release date.",
    "Open the Kindle Store, find 'A Little Life', and report the page count and language.",
    "Open the Kindle Store, find 'Iron Flame', and report the file size and release date.",
])

add(7, "kindle_book_detail", [
    "Open the Kindle book detail page for 'Sapiens: A Brief History of Humankind' and report the ISBN-13.",
    "Open the Kindle book detail page for 'The Midnight Library' and report the page count and price.",
    "Open the Kindle book detail page for 'Atomic Habits' and tell me the genre and Kindle Unlimited eligibility.",
    "Open the Kindle book detail page for 'Educated' and report whether it's eligible for Kindle Unlimited.",
    "Open the Kindle book detail page for 'Where the Crawdads Sing' and report the page count.",
    "Open the Kindle book detail page for 'Klara and the Sun' and report the file size in MB.",
    "Open the Kindle book detail page for 'Lessons in Chemistry' and tell me the release date.",
    "Open the Kindle book detail page for 'Demon Copperhead' and report the price.",
    "Open the Kindle book detail page for 'Babel' and report the genre.",
    "Open the Kindle book detail page for 'Tom Lake' and tell me whether it's KU eligible.",
])

add(7, "prime_video", [
    "Open Prime Video and report the top-rated title by IMDb rating shown on the landing page.",
    "Open Prime Video, filter to 'series', and tell me how many series are listed.",
    "Open Prime Video, filter to 'movie', and report the highest-rated movie.",
    "Open Prime Video, sort by year descending, and report the 3 newest titles.",
    "Open Prime Video, find 'The Boys', and report its number of episodes.",
    "Open Prime Video, find 'Reacher', and report its IMDb rating.",
    "Open Prime Video, find 'The Marvelous Mrs. Maisel', and report its number of episodes and genre.",
    "Open Prime Video, find 'Fallout' (2024), and report whether it's included with Prime.",
    "Open Prime Video, find 'Citadel', and tell me the genre.",
    "Open Prime Video, find 'Mr. & Mrs. Smith' (2024 series), and report the IMDb rating and episode count.",
    "Open Prime Video, find 'The Rings of Power', and report its year and IMDb rating.",
    "Open Prime Video, find 'Knives Out', and report its IMDb rating and runtime in minutes.",
    "Open Prime Video, find 'Saltburn', and tell me whether it's included with Prime.",
    "Open Prime Video, find 'Argylle', and report its runtime in minutes.",
    "Open Prime Video, find 'The Tomorrow War', and report its IMDb rating.",
    "Open Prime Video, find 'Hunters', and report its episode count.",
    "Open Prime Video, sort by IMDb rating descending, and report the 5 highest-rated titles in order.",
    "Open Prime Video, count how many titles have an IMDb rating above 8.0, and report the count.",
])

add(7, "audible_music_redeem", [
    "Open Audible and report the membership monthly price shown on the landing page.",
    "Open Amazon Music Unlimited landing and report the family plan price.",
    "Open Amazon Music Unlimited landing and tell me how many tiers are advertised.",
    "Open Audible and tell me how many credits the standard plan includes per month.",
    "Open Audible landing and report the trial duration mentioned.",
    "Open the Redeem page and redeem the code 'GIFT-DEMO-15' (signed in as demo@amazon.com); confirm $15 has been added to the account balance.",
    "Open the Redeem page and redeem 'PRIMEVIDEO-3MO-CAROL' as carol.d@test.com; confirm Prime Video has been extended.",
    "Open the Redeem page and redeem 'KINDLEUNL-1MO-DAVID' as david.k@test.com; confirm KU has been extended.",
    "Open the Redeem page and attempt to redeem 'GIFT-USED-100'; report the already-redeemed error message.",
    "Open the Redeem page and redeem 'GIFT-ALICE-50' as alice.j@test.com; report the new balance.",
    "Open the Redeem page and redeem 'AUDIBLE-30DAY-FREE' as a new user; confirm Audible trial activation.",
    "Open the Redeem page and redeem 'MUSICUNL-3MO-PROMO' as alice.j@test.com; confirm Music Unlimited activated.",
    "Open the Redeem page and redeem 'PROMO-FRESH-FREESHIP'; confirm the free-shipping benefit applies on next Fresh order.",
    "Open the Redeem page and report the help text shown above the input box (e.g. 'Gift cards, promo codes, Kindle credits...').",
])

# bulk R7 kindle
kindle_titles = [
    "Sapiens: A Brief History of Humankind", "The Midnight Library",
    "Atomic Habits", "The Subtle Art of Not Giving a F*ck",
    "Educated", "It Ends with Us",
    "Where the Crawdads Sing", "Klara and the Sun",
    "Becoming", "The Way of Kings (Stormlight Archive)",
    "Project Hail Mary", "The Atlas Six",
    "Tomorrow, and Tomorrow, and Tomorrow", "Lessons in Chemistry",
    "Demon Copperhead", "Babel", "Iron Flame", "Fourth Wing",
    "The Heaven & Earth Grocery Store", "Tom Lake",
    "The Wager", "Trust", "A Little Life", "Steve Jobs",
    "When Breath Becomes Air", "The Power of Now",
    "Born a Crime", "Talking to Strangers",
]
kindle_qs = [
    "report its ISBN-13",
    "report its price and KU eligibility",
    "report its page count and file size in MB",
    "report its genre and language",
    "report its release date and author",
]
kindle_bulk = []
for t in kindle_titles:
    for qq in kindle_qs:
        kindle_bulk.append(f"Open the Kindle Store, find '{t}', and {qq}.")
add(7, "kindle_bulk", kindle_bulk)

# bulk R7 prime video
pv_titles = [
    "Reacher", "The Boys", "Goliath", "The Marvelous Mrs. Maisel",
    "Mr. & Mrs. Smith", "The Wheel of Time", "Citadel",
    "The Tomorrow War", "Jack Ryan", "The Idea of You",
    "Knives Out", "Argylle", "Coming 2 America",
    "The Rings of Power", "Saltburn", "My Spy: The Eternal City",
    "Bosch: Legacy", "Fallout", "Hunters", "Sound of Metal",
]
pv_qs = [
    "report its IMDb rating",
    "report its year and genre",
    "report its episode count (or '1' if movie)",
    "report whether it's included with Prime",
    "report its runtime in minutes",
]
pv_bulk = []
for t in pv_titles:
    for qq in pv_qs:
        pv_bulk.append(f"Open Prime Video, find '{t}', and {qq}.")
add(7, "pv_bulk", pv_bulk)

# ============================================================
# R8 - Seller / Brand
# ============================================================
sellers_top = [
    ("Fisher-Price", "US"), ("Dell", "US"), ("LEGO", "DK"), ("Ubisoft", "FR"),
    ("Yeti", "US"), ("Oral-B", "US"), ("HP", "US"), ("LG", "KR"),
    ("Roomba", "US"), ("Nikon", "JP"), ("Neutrogena", "US"),
    ("Vitamix", "US"), ("Gillette", "US"), ("Pampers", "US"),
    ("Razer", "SG"), ("Dyson", "GB"), ("Beats", "US"),
    ("Apple", "US"), ("Sony", "JP"), ("Samsung", "KR"),
    ("Bose", "US"), ("Anker", "CN"), ("Logitech", "CH"),
    ("Nike", "US"), ("Adidas", "DE"), ("Under Armour", "US"),
    ("Patagonia", "US"), ("Levi's", "US"),
]
add(8, "seller_browse", [
    "Open Seller Central and tell me the brand at the top of the seller leaderboard.",
    "Open Seller Central and report the count of distinct seller country codes on the landing page.",
    "Open the seller leaderboard sorted by rating, and report the top 3 seller brands.",
    "Open the seller leaderboard and tell me which brand has the highest on-time delivery percentage.",
    "Open the seller leaderboard and report the brand with the lowest cancellation rate.",
    "Open Seller Central and find a seller from Japan (JP); report its brand name and rating.",
    "Open Seller Central and find a seller from Germany (DE); report the brand and joined date.",
    "Open Seller Central and find a seller from Singapore (SG); report the brand and on-time delivery percentage.",
    "Open Seller Central and find a seller from South Korea (KR); report the brand and review count.",
    "Open the brand store for 'LEGO' and report how many products are listed in the storefront.",
    "Open the brand store for 'Dyson' and tell me the count of products plus the highest-priced one.",
    "Open the brand store for 'Apple' and tell me how many distinct products are listed.",
    "Open the brand store for 'Nike' and report the cheapest item shown.",
    "Open the brand store for 'Sony' and report two product names from the storefront.",
    "Open the brand store for 'Bose' and report a noise-cancelling product if any.",
])

# bulk R8 sellers
seller_qs = [
    "report its overall seller rating",
    "report its on-time delivery percentage",
    "report its cancellation rate percentage",
    "report its review count",
    "report the country of operation and founded year",
    "report the customer-service rating and average response-time hours",
    "report the fulfillment method (FBA/FBM)",
    "open its brand store and report the count of products listed",
]
seller_bulk = []
for brand, _country in sellers_top:
    for qq in seller_qs:
        seller_bulk.append(f"Open the seller profile for '{brand}' and {qq}.")
add(8, "seller_profile_bulk", seller_bulk)

add(8, "seller_contact", [
    f"Open the seller profile for '{brand}', click 'Contact seller', send a message titled 'Question about warranty', and confirm the form submits."
    for brand, _ in sellers_top[:15]
])

add(8, "seller_rating_breakdown", [
    f"Open the rating breakdown page for '{brand}' and report the 5-star percentage of all reviews."
    for brand, _ in sellers_top[:15]
])

# ============================================================
# R9 - Vine / Early Reviewer / Promo
# ============================================================
vine_items_list = [
    "Apple AirPods Pro (2nd Generation) Wireless Earbuds",
    "Timberland 6-Inch Premium Waterproof Boot",
    "Keurig K-Elite Single Serve Coffee Maker",
    "Cosori Pro II 5.8-Qt Air Fryer",
    "Polo Ralph Lauren Classic Fit Polo Mens",
    "Instant Pot Duo 7-in-1 Electric Pressure Cooker",
    "Levi's Men's 511 Slim Fit Jeans",
    "Nike Sportswear Club Fleece Pullover Hoodie",
    "Levi's Men's 505 Regular Fit Jeans",
    "Crocs Classic Clog Adult",
    "Linenspa 2 Inch Gel Memory Foam Topper Queen",
    "Hot Wheels 50-Car Pack of 1:64 Scale Vehicles",
    "Levi's Men's 501 Original Fit Jeans",
    "Echo Dot (5th Gen) Smart Speaker with Alexa",
    "Hydro Flask 32 oz Wide Mouth Bottle",
]
add(9, "vine_landing", [
    "Open the Vine landing page and report how many items are currently available (un-claimed) for Vine review.",
    "Open the Vine landing page and report the highest-priced un-claimed item available.",
    "Open the Vine landing page, sort by estimated value descending, and report the top 3 items.",
    "Open the Vine landing page, filter to items under $50, and report 5 such items.",
    "Open the Vine landing page and report the eligible-until date on the first listed item.",
    "Open the Vine landing and identify which items have already been claimed; report the count.",
])

vine_member_qs = [
    "open her Vine member profile and report the items_reviewed count",
    "open her Vine member profile and report the helpful_votes count",
    "open her Vine member profile and report her tier (silver/gold/platinum)",
    "open her Vine member profile and report the joined_at year",
]
add(9, "vine_member", [
    f"Sign in as alice.j@test.com, {qq}."
    for qq in vine_member_qs
] + [
    f"Sign in as bob.c@test.com, {qq.replace('her ', 'his ').replace('her,', 'his,').replace('she ', 'he ')}."
    for qq in vine_member_qs
] + [
    f"Sign in as carol.d@test.com, {qq}."
    for qq in vine_member_qs
] + [
    f"Sign in as david.k@test.com, {qq.replace('her ', 'his ').replace('she ', 'he ')}."
    for qq in vine_member_qs
])

add(9, "vine_leaderboard", [
    "Open the Vine top-reviewer leaderboard and report the #1 reviewer by helpful_votes.",
    "Open the Vine leaderboard and report how many gold-tier members are listed.",
    "Open the Vine leaderboard sorted by items_reviewed and report the top 3 reviewers.",
    "Open the Vine leaderboard and report the average items_reviewed across listed members (rounded to integer).",
    "Open the Vine leaderboard, find Bob Chen, and report his rank by helpful_votes.",
    "Open the Vine leaderboard and report how many silver-tier members are listed.",
])

add(9, "vine_claim", [
    f"Sign in as a Vine member, open the Vine landing, claim the item '{it}', and confirm it now shows as 'claimed by you'."
    for it in vine_items_list
])

add(9, "early_reviewer", [
    "Open the Early Reviewer program landing page and report how the program rewards reviewers.",
    "Open the Early Reviewer program landing page and report the typical reward amount per qualifying review.",
    "Open the Early Reviewer program landing page and tell me the eligibility criteria summary.",
    "Open the Early Reviewer program landing page and report how many active items are listed.",
])

promo_codes_list = [
    ('PRIMEDAY26', 15), ('BACK2SCHOOL', 10), ('CYBER26', 20), ('FRESH5', 5),
    ('VINE-WELCOME', 25), ('GIFT-NEW10', 10), ('AUDIBLE-FREE', 100),
    ('KU-30DAY', 100), ('MUSIC-FREE', 100), ('REFURB-15', 15),
]
add(9, "promo_apply", [
    f"Open the Promo Codes page and report what discount the code '{code}' applies (expected: {pct}% off)."
    for code, pct in promo_codes_list
] + [
    f"Add any item to your cart and at checkout, apply promo code '{code}'; confirm the discount line shows ~{pct}% off (or the equivalent benefit)."
    for code, pct in promo_codes_list
] + [
    "Open the Promo Codes landing page and report which 3 codes give 100% off (free trial codes).",
    "Open the Promo Codes landing page and report the code with the highest percent_off value.",
    "Open the Promo Codes landing page and report the expiry date of 'PRIMEDAY26'.",
    "Open the Promo Codes landing page and report the count of distinct codes listed.",
    "At checkout, apply 'PRIMEDAY26' AND 'GIFT-NEW10' together; report whether stacking is allowed and the final discount applied.",
])

# bulk R9 vine
vine_bulk = []
for it in vine_items_list:
    vine_bulk.append(f"Open Vine, find the item '{it}', and report its estimated value and eligible-until date.")
    vine_bulk.append(f"Open Vine, find '{it}', and report whether it has been claimed (yes/no) and by whom if claimed.")
add(9, "vine_item_browse", vine_bulk)

# Additional R9 — vine member detail + early reviewer items + promo edge cases
r9_extra = []
for u in ['alice.j@test.com', 'bob.c@test.com', 'carol.d@test.com', 'david.k@test.com', 'demo@amazon.com']:
    for it in vine_items_list[:6]:
        r9_extra.append(
            f"Sign in as {u}, open Vine, attempt to claim '{it}'; report whether the claim succeeded (yes/no) and the eligible-until date shown."
        )
add(9, "vine_claim_user", r9_extra)

# More R9 — promo + redemption combinations
r9_promo_extra = []
for code, pct in promo_codes_list:
    for u in ['alice.j@test.com', 'bob.c@test.com', 'carol.d@test.com', 'david.k@test.com']:
        r9_promo_extra.append(
            f"Sign in as {u}, add any item to cart, apply promo '{code}' at checkout, and report whether the {pct}%-off discount applies (yes/no) plus the final subtotal."
        )
add(9, "promo_user", r9_promo_extra)

# More R9 — vine items deep + early-reviewer + leaderboard polish
r9_padding = []
for it in vine_items_list:
    r9_padding.append(f"Open Vine, find '{it}', click into its detail, and report the listed product brand.")
    r9_padding.append(f"Open Vine, find '{it}', and report whether its eligible-until date has passed today (yes/no).")
r9_padding += [
    "Open the Vine landing page and tell me the count of items priced between $50 and $100.",
    "Open the Vine landing page and tell me the count of items priced above $150.",
    "Open the Early Reviewer landing page and report which 3 categories are typically eligible.",
    "Open the Early Reviewer landing page and report whether self-published books are eligible.",
    "Open the Vine leaderboard and report the rank of the user with the most items_reviewed.",
    "Open the Vine leaderboard and report the median helpful_votes across listed members (rounded to integer).",
    "Open the Promo Codes landing and report which code lasts longest into the future (latest expiry).",
    "Open the Promo Codes landing and report the count of percent-off codes (<100%) vs free-trial codes (100%).",
]
add(9, "vine_polish", r9_padding)

# ============================================================
# R10 - Cross-flow polish / multi-round multi-step
# ============================================================
add(10, "x_subscribe_kindle", [
    f"Sign in as alice.j@test.com, then in two steps: (a) on Subscribe & Save, switch her 'AI Robot Vacuum RVEmber' plan to 3-month frequency, and (b) on the Kindle Store, find '{t}' and report its price."
    for t in kindle_titles[:12]
])

add(10, "x_registry_prime_video", [
    f"For the registry public code {code}, find any un-purchased 'must-have' electronics item, add it to cart, then in a separate tab open Prime Video and find '{pv}' and report its IMDb rating."
    for code, pv in zip(['WED-AJ-2026', 'BABY-BC-2026', 'BIRTH-MD-2026', 'WED-CD-2026', 'BABY-DK-2026', 'BIRTH-AK-2026'] * 4, pv_titles[:24])
])

add(10, "x_fresh_checkout", [
    f"Add '{it}' from Amazon Fresh to your cart, then apply promo code 'FRESH5' at checkout and report the final total."
    for it in fresh_items[:25]
])

add(10, "x_qa_seller", [
    f"Open the Q&A tab on '{p}' and report the top-voted question; then open the seller profile for the brand of that product and report the brand's overall rating."
    for p in qa_products[:20]
])

add(10, "x_vine_audible", [
    f"Sign in as bob.c@test.com (gold-tier Vine), claim '{it}' on Vine, then go to Audible and report the monthly membership price."
    for it in vine_items_list
])

add(10, "x_promo_kindle", [
    f"Sign in as carol.d@test.com, redeem the code 'KU-30DAY' on the Redeem page, then open the Kindle Store and find '{t}' and confirm whether it's KU eligible."
    for t in kindle_titles[:15]
])

add(10, "x_seller_brand_compare", [
    f"Open the brand store for '{b1}' and the seller leaderboard side by side; report which has the higher rating, '{b1}' or '{b2}'."
    for b1, b2 in zip([s[0] for s in sellers_top[:12]], [s[0] for s in sellers_top[12:24]])
])

add(10, "x_multi_step_polish", [
    "Sign in as alice.j@test.com. Open her wedding registry, mark any 1 must-have item as purchased, then open Subscribe & Save manage and report her current S&S tier banner. Finally open Prime Video and report the highest-rated title.",
    "Sign in as bob.c@test.com. Cancel his 'Smart Oven Air Fryer Pro' Subscribe & Save plan, then open his baby registry and add 'Echo Dot (5th Gen)' as nice-to-have. Finally open the Q&A for 'Echo Dot (5th Gen)' and report the top question.",
    "Sign in as carol.d@test.com. Open Mia's birthday registry, add 'Hot Wheels 50-Car Pack' as must-have qty 3, then on Amazon Fresh add 'Organic Hass Avocado 4-pack' to cart and pick the earliest delivery window.",
    "Sign in as david.k@test.com. Switch his 'Magnifica Foxglove' espresso S&S plan to 6-month, then open Audible and report the monthly membership price, then redeem 'AUDIBLE-30DAY-FREE'.",
    "Open the Gift Center, find 'Baby Chen on the Way', add the first un-purchased must-have to your cart, apply promo 'GIFT-NEW10' at checkout, and report the final total.",
    "Open Amazon Fresh, add a frozen pizza and a gallon of milk to your cart, open the delivery-window picker and pick the earliest attended window, then apply 'FRESH5' and report the total.",
    "Open the brand store for 'LEGO', add the top-rated LEGO product to your cart, then go to the Q&A of that product and report the top-voted question.",
    "Open Prime Video, find 'The Boys', then open the Q&A for 'Echo Dot (5th Gen)' and ask a question 'Does this work with The Boys streaming?', and confirm the question posted.",
    "Sign in as alice.j@test.com. Open Subscribe & Save manage and skip the next delivery on her 'Original Ember Pillow Queen' plan. Then open the Vine leaderboard and report her own helpful_votes rank.",
    "Sign in as bob.c@test.com. On his baby registry, invite alice.j@test.com as a collaborator. Then on Kindle Store, find 'Atomic Habits' and report its KU eligibility.",
    "Open the Gift Center, find any registry with 'wedding' event type, open the public view, and report the count of must-have items still un-purchased.",
    "Open Vine, claim the highest-priced un-claimed item, then immediately open the Q&A on that same product and report the top question.",
    "Open the seller profile for 'Apple', then open Prime Video and report the highest-rated 'movie' title that is included with Prime.",
    "Open the Promo Codes landing page, find the code with the longest expiry, then add any Fresh item to your cart and apply that code at checkout.",
    "Open Audible, then in a new tab open Amazon Music Unlimited; report the monthly cost of each (Audible vs Music Unlimited family plan).",
])

# bulk R10 — multi-step combinations
x_bulk = []
for it in fresh_items[:25]:
    for code, _ in promo_codes_list[:6]:
        x_bulk.append(
            f"Add '{it}' from Amazon Fresh to your cart, apply promo code '{code}' at checkout, and report whether the code applies to Fresh items (yes/no) and the final total."
        )
add(10, "x_promo_fresh_bulk", x_bulk[:120])

x_qa_seller_bulk = []
for p in qa_products:
    for brand, _ in sellers_top[:10]:
        x_qa_seller_bulk.append(
            f"Open the Q&A on '{p}' and the seller profile for '{brand}'; report which has more user-generated content (Q&A count vs review count)."
        )
add(10, "x_qa_seller_compare", x_qa_seller_bulk[:80])

# ============================================================
# Emit
# ============================================================

def main():
    # current count
    with open(TASKS_PATH) as f:
        existing = sum(1 for ln in f if ln.strip())
    out_lines = []
    per_round_count: dict[int, int] = {}
    per_round_theme_seq: dict[tuple[int, str], int] = {}
    for round_no, theme, items in BUCKETS:
        per_round_count[round_no] = per_round_count.get(round_no, 0)
        for q in items:
            seq = per_round_theme_seq.get((round_no, theme), 0) + 1
            per_round_theme_seq[(round_no, theme)] = seq
            tid = f"Amazon--r{round_no}_{theme}_{seq:03d}"
            out_lines.append(json.dumps({
                "web_name": "Amazon",
                "id": tid,
                "ques": q,
                "web": WEB,
                "upstream_url": UPSTREAM,
            }))
            per_round_count[round_no] += 1

    # report
    print(f"Existing tasks: {existing}")
    print(f"New tasks: {len(out_lines)}")
    for rno in sorted(per_round_count):
        print(f"  r{rno}: {per_round_count[rno]}")

    with open(TASKS_PATH, 'a') as f:
        for ln in out_lines:
            f.write(ln + "\n")
    print(f"Wrote to {TASKS_PATH}")


if __name__ == "__main__":
    main()
