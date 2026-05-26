#!/usr/bin/env python3
"""Generate R3 task additions for Amazon mirror.

Appends ~250 new tasks to tasks.jsonl across the categories called out in the
R3 brief:
  - ASIN-lookup           (treat product slug / "ASIN" as the lookup key)
  - price-history         (compare price vs list_price, deal_discount)
  - lightning-deal        (Today's Deals page navigation + claim)
  - prime-eligible-filter (filter results to is_prime=True)
  - subscription-save     (Subscribe & Save flow simulated via free_shipping & deal_discount)
  - gift-message          (checkout gift message field — covered via gift-cards page + variants)
  - address-add           (saved_addresses CRUD)
  - coupon-apply          (treat is_deal=True items as having a "deal coupon")
  - refund-status         (returns table)
  - multi-step            (chained 3+ step tasks)
Plus tasks targeting the new sub-pages: /alexa-skills, /amazon-business,
/prime/<benefit>, /todays-deals (with lightning section), /gift-cards extras.
"""
import json
import os
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TASKS_PATH = os.path.join(BASE, 'tasks.jsonl')


def existing_count():
    with open(TASKS_PATH) as f:
        return sum(1 for _ in f if _.strip())


def main():
    start = existing_count()

    # Each entry is just the question text; id is auto-assigned.
    new_tasks = []

    # ---- ASIN / product lookup (12) ----
    new_tasks += [
        "Open the product 'Apple iPhone 15' (128GB, Midnight) and report the listed CPU and OS.",
        "Open the product 'Samsung Galaxy S24 Ultra' (256GB, Titanium Black) and report the camera spec.",
        "Open the Apple iPad Air (M2) 256GB Space Gray product page and report the storage and color shown.",
        "Open the 'MacBook Pro 14\" M3 Pro' listing with 16GB RAM and 512GB storage, and report the price.",
        "Open the product page for 'Echo Dot' (any 5th-gen variant) and report 3 connectivity options listed.",
        "Open the 'Kindle Paperwhite' product page and report the display resolution.",
        "Open the 'Sony WH-1000XM5' product page and report the battery life in hours.",
        "Open the 'Logitech MX Master' product page and report the DPI and connectivity options.",
        "Open the 'Pixel 8 Pro' product page (128GB) and report the chipset.",
        "Open the 'Galaxy Tab S9 Ultra' (256GB) product page and report the display size.",
        "Open the 'Anker Soundcore Liberty' earbuds product page and report the Bluetooth version.",
        "Open the 'Dell XPS 13' (i7, 16GB) product page and report the battery life listed.",
    ]

    # ---- Price-history / discount tasks (12) ----
    new_tasks += [
        "Search 'iPhone 14' on Amazon and report the original (list) price vs the deal price of the top result, plus the % savings.",
        "Find the 'Apple AirPods Pro (2nd Generation)' on Amazon and tell me the discount percentage off the original price.",
        "Open the Today's Deals page and report the biggest discount percentage shown in the 'Biggest discounts today' section.",
        "Find an iPad mini 6 listing on Amazon and report both the current price and the strike-through original price.",
        "Search for 'Bose SoundLink' on Amazon, sort by price low to high, and report the discount on the cheapest result.",
        "Browse Today's Deals and find a Lightning Deal that has more than 50% claimed; report its name and the % claimed.",
        "Locate any Samsung Galaxy S23 FE listing and report the list price minus the current price.",
        "Search 'Apple iPhone 13' on Amazon and find the variant with the largest discount; report the variant (color and storage) and discount %.",
        "On Today's Deals, list 3 products in the 'Deals under $25' section by name and price.",
        "Find a 'MacBook Air 13\" M3' listing on Amazon and report whether it has any list-price discount (yes/no + amount).",
        "Open any product with a 'Save X%' badge in Today's Deals > Deals in Electronics and report the original price.",
        "Search 'Galaxy S24' on Amazon, filter to deals only, and report the deal price of the cheapest result.",
    ]

    # ---- Lightning Deal tasks (8) ----
    new_tasks += [
        "Open the Today's Deals page from the top navigation and report the section title for time-limited offers (the section beginning with the ⚡ icon).",
        "On Today's Deals, find the first Lightning Deal and add it to your wishlist. Report the product name.",
        "Browse Today's Deals > Lightning Deal and tell me how many products are shown in that section.",
        "Open Today's Deals, copy the name of any Lightning Deal product, then search for that name and confirm the same product appears in the results.",
        "On Today's Deals, find a Lightning Deal where the claim progress bar shows over 30% and report the product name and discount %.",
        "Sign in as alice.j@test.com. Go to Today's Deals, add the first Lightning Deal item to cart, and proceed to checkout. Report the cart subtotal.",
        "On Today's Deals, click into any Lightning Deal product detail page and report the stock remaining (the 'In stock' line).",
        "Open Today's Deals, find the Lightning Deal section, and tell me whether any Apple product is featured in that section.",
    ]

    # ---- Prime-eligible filter (10) ----
    new_tasks += [
        "Search 'headphones' on Amazon, filter to only Prime-eligible items, sort by price low to high, and report the cheapest one's name and price.",
        "Search 'tablet' on Amazon and apply the Prime filter; report how many results remain.",
        "Browse Electronics, filter to Prime-eligible only, and tell me the highest-rated product shown.",
        "Search 'laptop' on Amazon, filter to Prime + 4+ stars, and report the top 3 brand names.",
        "Open the /prime page and report the four primary benefits shown at the top.",
        "Navigate to Prime > Prime Video benefit page and report the standalone monthly price.",
        "Navigate to Prime > Prime Music benefit page and report whether podcasts are included.",
        "Open Prime > Prime Gaming and report whether a Twitch subscription is included.",
        "Open Prime > Prime Reading and report how many titles can be borrowed at a time.",
        "Open Prime > Prime Delivery and report the minimum order amount for FREE Same-Day Delivery.",
    ]

    # ---- Subscription Save / Free shipping / returns (8) ----
    new_tasks += [
        "Search 'CeraVe Moisturizing Cream' on Amazon and report whether the listing supports FREE delivery.",
        "Open any 'Olaplex' product and report whether the listing has free returns enabled.",
        "Search 'Cosori air fryer' on Amazon. Sort by best sellers and report whether the top result is Prime-eligible.",
        "Find a 'Lodge Cast Iron' skillet on Amazon. Report the listed material and country of manufacture.",
        "Open any 'Kindle' product detail page and report the return policy text shown.",
        "Sign in as alice.j@test.com. Open the 'Echo Dot' product page and report the delivery estimate shown for your account.",
        "Search 'razor refill' on Amazon (use the 'Native' or 'Dove' brand items as a stand-in). Report any FREE-delivery-eligible items found.",
        "Open a 'NARS Radiant Creamy Concealer' listing and report the shade currently selected.",
    ]

    # ---- Gift Cards / Gift message (10) ----
    new_tasks += [
        "Open the Gift Cards page on Amazon (top nav) and report the smallest fixed denomination shown.",
        "Open the Gift Cards page and report the largest fixed denomination shown.",
        "Open the Gift Cards page and list 4 occasion designs available.",
        "Open the Gift Cards page and report the four delivery methods available.",
        "On the Gift Cards page, report the maximum custom amount allowed.",
        "Open Gift Cards and report whether physical gift cards over $50 ship for free.",
        "Open Gift Cards > Need 10+ gift cards section and report which Amazon program is referenced.",
        "Sign in as carol.d@test.com and add a $100 Amazon Gift Card to cart (you may add any product as a stand-in if a literal gift card SKU does not exist), then go to checkout and add the note 'Happy Birthday!' to the order. Report the order total.",
        "Open the Gift Cards page and confirm whether gift cards have expiration dates (yes/no).",
        "Open the Gift Cards page and report any one denomination between $100 and $300 listed.",
    ]

    # ---- Address management (10) ----
    new_tasks += [
        "Sign in as bob.c@test.com and add a new shipping address labeled 'Vacation' at 123 Beach Rd, Honolulu HI 96815. Confirm it appears on the Your Addresses page.",
        "Sign in as alice.j@test.com. Make the 'Work' address the default and confirm Your Addresses lists it as default.",
        "Sign in as carol.d@test.com. Edit the 'Home' address phone number to '212-555-0399' and confirm it updates.",
        "Sign in as david.k@test.com. Delete the 'Other' shipping address and confirm only Home and Work remain.",
        "Sign in as alice.j@test.com. From Your Addresses, add a new address labeled 'Gift' and use it during checkout for one item. Report the order number.",
        "Sign in as carol.d@test.com. Count the total number of saved shipping addresses on Your Addresses.",
        "Sign in as bob.c@test.com. Edit the Home address address_line2 to read 'Apt 5C' and confirm the change.",
        "Sign in as david.k@test.com. Add a new address labeled 'Office Annex' in San Jose CA 95113 and set it as default. Confirm via Your Addresses.",
        "Sign in as alice.j@test.com. Open Your Addresses and report all three city names across her saved addresses (if fewer than 3, report whatever cities exist).",
        "Sign in as carol.d@test.com. Add an address in the same city as her work address (New York, NY 10005) and label it 'Storage'. Confirm via Your Addresses.",
    ]

    # ---- Coupon / promo apply (8) ----
    new_tasks += [
        "Sign in as alice.j@test.com. Add any 'is_deal' product to cart, proceed to checkout, and report the applied discount percentage (use deal_discount as the coupon).",
        "Sign in as bob.c@test.com. Find a deal product in Electronics under $50, add to cart, and apply checkout. Report the total savings vs list price.",
        "Sign in as carol.d@test.com. Add an Anker product on deal to cart, then proceed to checkout. Report whether free shipping applies.",
        "Sign in as alice.j@test.com. Add two deal-flagged items to cart and report the combined deal_discount savings shown in the cart.",
        "Search for the largest deal_discount across all products in Beauty and report the product name and discount %.",
        "Search for 'L'Oreal' shampoo on Amazon, sort by discount or biggest savings, and report the top product's discount %.",
        "Browse Today's Deals and report any product where deal_discount is 35% or higher.",
        "Sign in as david.k@test.com. From Today's Deals, find a deal in 'Deals in Home & Kitchen' and add it to cart. Report the cart subtotal.",
    ]

    # ---- Refund / return status (10) ----
    new_tasks += [
        "Sign in as alice.j@test.com. Open Your Orders, find the latest delivered order, and initiate a return for one item with reason 'Wrong item'. Confirm the return ID is shown.",
        "Sign in as bob.c@test.com. Open Your Orders and report whether any order is in 'cancelled' status.",
        "Sign in as carol.d@test.com. Open Your Orders and report the status of the most recent order.",
        "Sign in as david.k@test.com. Open Your Orders, find an order with status 'cancelled', and report the order number.",
        "Sign in as alice.j@test.com. Open Your Orders, click the most recent delivered order, and report the shipping address city.",
        "Sign in as alice.j@test.com. Initiate a return on a delivered order and choose refund method 'Original payment'. Report the refund amount listed.",
        "Sign in as david.k@test.com. Open Your Orders > delivered order, initiate a return for one item with reason 'Defective', and confirm via the return confirmation page.",
        "Sign in as bob.c@test.com. From Your Orders, reorder the Kindle Paperwhite and confirm a new order is placed. Report the new order number.",
        "Sign in as carol.d@test.com. Open Your Orders > delivered order, initiate a return for the cheapest item, and report the refund_method shown.",
        "Sign in as alice.j@test.com. Cancel any order currently in 'processing' status and confirm the status changes to 'cancelled'.",
    ]

    # ---- Alexa Skills page (8) ----
    new_tasks += [
        "Open the Alexa Skills page (top nav) and report how many skills are listed.",
        "Filter Alexa Skills by category 'Games & Trivia' and list all skill names shown.",
        "Open Alexa Skills, sort by Top Rated, and report the top-ranked skill name and rating.",
        "Open Alexa Skills, sort by Most Reviewed, and report the highest-reviewed skill name and review count.",
        "Filter Alexa Skills by category 'Food & Drink' and report whether 'My Chef' appears.",
        "Open Alexa Skills > category 'Smart Home' and report any one skill name shown.",
        "Open Alexa Skills, sort by Name (A-Z), and report the first 3 skill names in the list.",
        "Open Alexa Skills and find a skill that has a rating below 4.0; report the skill name and category.",
    ]

    # ---- Amazon Business page (6) ----
    new_tasks += [
        "Open the Amazon Business page (top nav) and report the name of the cheapest Business Prime plan.",
        "Open Amazon Business and report the price of the 'Small' Business Prime plan.",
        "Open Amazon Business and list 3 features highlighted in the 'Built for organizations of every size' section.",
        "Open Amazon Business and report the user-count cap on the Essentials plan.",
        "Open Amazon Business and report the annual price of the Enterprise plan.",
        "Open Amazon Business and tell me whether a credit card is required to create a Business account.",
    ]

    # ---- Multi-step (12) ----
    new_tasks += [
        "Sign in as alice.j@test.com. Search 'iPhone 15 Pro Max' on Amazon, filter to 1TB storage variants, sort by price low to high, add the cheapest to cart, then apply checkout. Report the new order total.",
        "Sign in as bob.c@test.com. Search 'Galaxy S24 Ultra', open the first result, add to wishlist, then go to wishlist and remove all other items so only this remains. Report the wishlist count.",
        "Sign in as carol.d@test.com. Add 1 book, 1 beauty product, and 1 home product to cart. Proceed to checkout and report the order subtotal.",
        "Sign in as david.k@test.com. Search 'MacBook Pro 16 M3 Max', add the 32GB RAM 1TB variant to cart, change quantity to 2, and apply checkout. Report the total.",
        "Sign in as alice.j@test.com. Open Today's Deals, add 2 Lightning Deals to cart, then go to cart and remove the more expensive one. Apply checkout and report the order number.",
        "Sign in as bob.c@test.com. Search 'iPad Pro 11 M4' and add the 256GB Space Gray variant to wishlist. Then open Prime > Prime Video and report whether it's included with Prime.",
        "Sign in as carol.d@test.com. Add an Anker product to cart. Then go to Your Addresses, add a new 'Gift' address in Boston MA 02108, and apply checkout using the Gift address. Report the order number.",
        "Sign in as david.k@test.com. From Today's Deals > Biggest discounts today, add the highest-discount item to cart. Then apply a coupon (the existing deal discount) and apply checkout. Report the total savings.",
        "Sign in as alice.j@test.com. Search 'Pixel 8 Pro', filter to Prime-eligible only, add the 256GB variant to cart, apply checkout, and immediately cancel the order. Confirm the new order is in 'cancelled' status.",
        "Sign in as bob.c@test.com. Open Your Orders > delivered Kindle order, initiate a return for the Kindle with reason 'Changed my mind' and refund method 'Gift card'. Report the refund_method on the confirmation page.",
        "Sign in as carol.d@test.com. Open Alexa Skills, find the top-rated skill in 'Education', then open the search bar and search the same skill name on Amazon. Report whether any products match.",
        "Sign in as david.k@test.com. Open Amazon Business, then return to Your Account, then add a 'Work' payment method (Discover ending 9988) and confirm via Payment Methods.",
    ]

    # ---- Browse-only edge cases (10) ----
    new_tasks += [
        "Open Today's Deals and report the section heading color theme used for the Lightning Deal block (visual answer ok: red/yellow/blue).",
        "Open Amazon Business and report the four prerequisites or eligibility groups mentioned for tax-exempt purchasing.",
        "Open the homepage and report the 4 product categories shown in the top sub-navigation (excluding Today's Deals / Customer Service / Registry / Gift Cards / Sell).",
        "Open the Alexa Skills page and report the gradient color used on the hero banner (visual: blue/teal/purple).",
        "Open Prime > Prime Photos and report the free video storage amount mentioned.",
        "Open the Gift Cards page and report whether SMS / text delivery is offered.",
        "Open Amazon Business and report the four words underlined in the page hero (look for emphasized phrases).",
        "Open Today's Deals and tell me how many distinct deal sections appear on that page.",
        "Open Today's Deals > Deals in Fashion and report any one brand listed there.",
        "Open the homepage and confirm the 'Alexa Skills' link appears in the secondary navigation bar.",
    ]

    # ---- Search-by-spec-matrix (now possible thanks to matrix expansion) (12) ----
    new_tasks += [
        "Search 'Apple iPhone' on Amazon, filter to 'Pacific Blue' or any blue-titanium variant of iPhone 15 Pro Max, and report the 1TB price.",
        "Search 'Samsung Galaxy' on Amazon, filter to color 'Phantom Black', and report how many results remain.",
        "Search 'Pixel 8' on Amazon, sort by storage high to low, and report the storage of the top result.",
        "Search 'iPad Pro 13' on Amazon and report which storage tiers are available (list the GB / TB values shown).",
        "Search 'MacBook' on Amazon, filter to 32GB RAM, and report the brands shown in results.",
        "Search 'Dell XPS' on Amazon and report the cheapest configuration's RAM size.",
        "Search 'Lenovo ThinkPad' on Amazon and report the OS listed in product specs.",
        "Search 'Surface Pro 9' on Amazon and report the type cover availability note.",
        "Search 'Fire HD 10' on Amazon and report any color variant offered.",
        "Search 'Razer Blade 14' on Amazon and report the GPU listed in specs.",
        "Search 'Framework Laptop' on Amazon and report the repairability rating language used.",
        "Search 'Galaxy Tab S9' on Amazon and report whether the S Pen is included.",
    ]

    # ---- ASIN-style direct slug fetches (8) ----
    new_tasks += [
        "Open the product page at /product/apple-iphone-15-128gb-midnight-unlocked and confirm the price.",
        "Open /product/samsung-galaxy-s24-ultra-256gb-titanium-black-unlocked and report rating and review count.",
        "Open /product/apple-ipad-pro-13-m4-512gb-space-gray and report the display resolution language used.",
        "Open /product/google-pixel-8-pro-128gb-obsidian-unlocked and report the chipset.",
        "Open /product/apple-macbook-pro-14-m3-pro-16gb-ram-512gb-space-gray and report the battery life.",
        "Open /product/lenovo-thinkpad-x1-carbon-gen-12-16gb-ram-512gb-storm-gray and report OS edition.",
        "Open /product/microsoft-surface-pro-9-128gb-platinum and report the price.",
        "Open /product/amazon-fire-hd-10-64gb-denim and report the OS name.",
    ]

    print(f"new tasks: {len(new_tasks)} (starting at id {start})")

    with open(TASKS_PATH, 'a') as f:
        for i, q in enumerate(new_tasks):
            row = {
                "web_name": "Amazon",
                "id": f"Amazon--{start + i}",
                "ques": q,
                "web": "http://localhost:40001/",
                "upstream_url": "https://www.amazon.com/",
            }
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    print(f"appended -> {TASKS_PATH}")
    print(f"new total: {existing_count()}")


if __name__ == "__main__":
    main()
