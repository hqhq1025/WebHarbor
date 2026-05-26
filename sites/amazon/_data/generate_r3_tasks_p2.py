#!/usr/bin/env python3
"""R3 task pass 2 — add another ~120 tasks to bring total to 400+.

Focus: harder filter combinations, more sub-page coverage, returns/refunds
status, multi-user collaborative scenarios.
"""
import json
import os

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TASKS_PATH = os.path.join(BASE, 'tasks.jsonl')


def existing_count():
    with open(TASKS_PATH) as f:
        return sum(1 for _ in f if _.strip())


def main():
    start = existing_count()
    new = []

    # Books expansion tasks (matrix expansion brings ~1500 books) (20)
    new += [
        "Search 'horror' books on Amazon and report the highest-rated title shown.",
        "Search 'Pride and Prejudice' on Amazon and report the publisher listed in specs.",
        "Browse Books > Mystery and report the cheapest paperback's price.",
        "Browse Books > Cookbook and report the most reviewed cookbook.",
        "Browse Books > Programming and report any 3 titles available.",
        "Browse Books > Children and report a title released before 2000.",
        "Browse Books > Science and find a title with edition_count over 500. Report the title.",
        "Browse Books > Self-Help, sort by Customer Review rating, and report the top 3 titles.",
        "Search 'Harry Potter' on Amazon and report whether any Fantasy-genre result appears.",
        "Browse Books > Travel and report the cheapest title's price.",
        "Browse Books > Poetry and report any one title.",
        "Browse Books > Philosophy and report the most expensive title.",
        "Browse Books > Biography and report the most reviewed title.",
        "Browse Books > Romance and report a title with rating 4.7 or higher.",
        "Browse Books > Young Adult and report any title released in the 2020s.",
        "Browse Books > Thriller and report 3 titles sorted by review count desc.",
        "Browse Books > Science Fiction and report a title with edition_count over 200.",
        "Browse Books > Art and report a title with price over $30.",
        "Browse Books > Business and report a title in the $20-30 range.",
        "Browse Books > Psychology and report the cheapest title.",
    ]

    # Cross-page nav tests (15)
    new += [
        "Open the homepage, then navigate to Today's Deals, then to Alexa Skills, then back to homepage. Report the title of the homepage tab.",
        "Open homepage, click Amazon Business, then go to Prime > Prime Delivery. Report the FREE Same-Day minimum order amount.",
        "Open Today's Deals, scroll to Deals in Home & Kitchen, click into any product, and report the product's category slug shown in the breadcrumb (or URL).",
        "Open Alexa Skills, change the category filter to 'Lifestyle', and report the second skill listed.",
        "Open Amazon Business, scroll to the Business Prime plans table, and count the total number of plans shown.",
        "Open Prime > Prime Reading. Note the borrowing limit. Then go to Prime > Prime Photos and report the family-share member count.",
        "Open the Gift Cards page, then Prime > Prime Music. Compare and report which page has a featured 'standalone' price (and what that price is).",
        "Open Today's Deals and report the total number of distinct deal sections (count h2 headings).",
        "Navigate to homepage, then to Books category, then to Books > Cookbook subcategory. Report 3 cookbook titles.",
        "Open Electronics category, filter to Apple brand only, and report how many results remain.",
        "Open Computers category, filter to Lenovo brand, and report the cheapest laptop's name.",
        "Open Books > Fiction, sort by Newest, and report the top title.",
        "Open Beauty > Skincare and report a CeraVe product.",
        "Open Sports > Outdoor and report a Yeti product.",
        "Open Toys > Building Sets and report a LEGO Technic set.",
    ]

    # Refund flow detail (10)
    new += [
        "Sign in as alice.j@test.com. Open Your Orders, click into a delivered order, and report the 'delivery_estimate' string shown.",
        "Sign in as alice.j@test.com. Initiate a return for one item with refund_method 'gift_card' and report the refund amount.",
        "Sign in as bob.c@test.com. After returning the Kindle, open Your Orders and confirm the order still shows as 'delivered'.",
        "Sign in as carol.d@test.com. Open Your Orders and report how many distinct order statuses appear across her orders.",
        "Sign in as david.k@test.com. Open Your Orders, find the order with shipped status, and report the payment_method shown.",
        "Sign in as alice.j@test.com. Initiate a return on the latest delivered order with reason 'Better price available' and confirm the return confirmation page loads.",
        "Sign in as bob.c@test.com. Open Your Orders and report whether his processing order's delivery_estimate is set.",
        "Sign in as carol.d@test.com. Initiate a return on the MacBook order with reason 'Defective' and report the refund_amount.",
        "Sign in as david.k@test.com. Open his cancelled order detail page and report the order_number.",
        "Sign in as alice.j@test.com. Open Your Orders and report the total count of orders associated with her account.",
    ]

    # Payment methods CRUD (10)
    new += [
        "Sign in as alice.j@test.com. Open Payment Methods and report how many cards she has on file.",
        "Sign in as alice.j@test.com. Set the Mastercard ending 8891 as default and confirm via Payment Methods.",
        "Sign in as bob.c@test.com. Add a new Mastercard ending '4400' expiring 12/2029 and confirm via Payment Methods.",
        "Sign in as carol.d@test.com. Remove the Visa ending '9012' and confirm it no longer appears.",
        "Sign in as david.k@test.com. Add a Visa ending '7788' expiring 6/2028 and set it as default. Confirm Payment Methods shows it.",
        "Sign in as alice.j@test.com. Report all four card types/brands available across her saved payment methods.",
        "Sign in as carol.d@test.com. Report the default card type and last4 on her account.",
        "Sign in as david.k@test.com. Edit his account profile phone to '312-555-0500' and confirm Your Account shows the new phone.",
        "Sign in as alice.j@test.com. Change account password from TestPass123! to AnotherPass789! and sign back in to confirm.",
        "Sign in as bob.c@test.com. Edit his account profile name to 'Robert Chen' and confirm via Your Account.",
    ]

    # Wishlist (8)
    new += [
        "Sign in as alice.j@test.com. Open Wishlist and report the total number of items.",
        "Sign in as alice.j@test.com. From Wishlist, sort items by price (if applicable) and report the most expensive item.",
        "Sign in as bob.c@test.com. Add 'Apple iPhone 15 Pro Max' (any variant) to wishlist and confirm via Wishlist page.",
        "Sign in as carol.d@test.com. Add any 'Samsung Galaxy S24 Ultra' variant to wishlist and confirm via Wishlist.",
        "Sign in as alice.j@test.com. From Wishlist, remove the cheapest item and confirm it's no longer listed.",
        "Sign in as alice.j@test.com. From Wishlist, move 2 items to cart and proceed to checkout. Report the cart total.",
        "Sign in as david.k@test.com. Add a 4K monitor to wishlist and confirm via Wishlist page.",
        "Sign in as bob.c@test.com. From Wishlist, find the highest-rated item and report its rating.",
    ]

    # Cart / quantity / variant (10)
    new += [
        "Sign in as alice.j@test.com. Open Cart and report the total quantity across all items.",
        "Sign in as alice.j@test.com. Update the quantity of the Echo Dot in cart to 2 and confirm cart count increases by 1.",
        "Sign in as alice.j@test.com. Remove the Levi's 501 from cart and confirm via Cart page.",
        "Sign in as bob.c@test.com. Add 'Lodge Cast Iron 10-Inch' to cart and confirm via Cart.",
        "Sign in as carol.d@test.com. Add 'Olaplex No.4 Bond Maintenance Shampoo' to cart with quantity 3. Report the subtotal.",
        "Sign in as david.k@test.com. Add a Razer Blade 14 to cart, then proceed to checkout. Report the order_total.",
        "Sign in as alice.j@test.com. Add an iPad Air (M2) 512GB to cart, change quantity to 2, and report subtotal.",
        "Sign in as bob.c@test.com. Add Cosori Air Fryer to cart and apply checkout with FREE No-Rush Shipping. Confirm shipping cost shown.",
        "Sign in as carol.d@test.com. Add 'Sunday Riley Good Genes' to cart, change variant to Volume 0.5oz (if available), and report the new price.",
        "Sign in as david.k@test.com. Add Garmin Edge GPS to cart and apply checkout. Confirm the new order is in 'processing' status.",
    ]

    # Reviews (5)
    new += [
        "Sign in as alice.j@test.com. On the iPhone 15 product page, leave a 5-star review with title 'Great phone' and body 'Battery life amazing.' Confirm the review appears.",
        "Sign in as bob.c@test.com. On the Kindle Paperwhite page, leave a 4-star review and confirm the average rating on the listing updates accordingly.",
        "Sign in as carol.d@test.com. On the MacBook Pro 14 page, leave a 5-star review titled 'Perfect for design work'. Confirm via Reviews list.",
        "Sign in as alice.j@test.com. Delete her review on the Echo Dot product page and confirm via Reviews list.",
        "Browse the iPhone 15 Pro product page and report the top review's rating and title.",
    ]

    # /amazon-business detailed (5)
    new += [
        "Open Amazon Business and report the user-count cap on the Medium Business Prime plan.",
        "Open Amazon Business and report whether 'Bulk ordering' is included as a feature (yes/no).",
        "Open Amazon Business > Business Prime plans table and report the price difference between Small and Medium plans.",
        "Open Amazon Business and report the role-based permissions feature.",
        "Open Amazon Business hero section and report the orange-colored word.",
    ]

    # /alexa-skills detailed (5)
    new += [
        "Open Alexa Skills and report whether 'Spotify' is listed under Music & Audio category.",
        "Open Alexa Skills and report the rating of 'Question of the Day'.",
        "Open Alexa Skills and report 4 categories shown in the filter dropdown.",
        "Open Alexa Skills with category filter 'Travel & Transport' and list all skills shown.",
        "Open Alexa Skills and find a skill with the highest review count above 100,000. Report its name.",
    ]

    # Multi-step + edge (10)
    new += [
        "Sign in as alice.j@test.com. Add a $50 Amazon Gift Card to cart, add a Lightning Deal product to cart, then apply checkout using the Visa 4242. Report the order total.",
        "Sign in as bob.c@test.com. Open his Home address, edit address_line1 to '789 Pine St Suite A', then add an iPad to cart and checkout. Confirm the new address line in the order.",
        "Sign in as carol.d@test.com. Open Prime > Prime Reading, then back to homepage, then search 'Kindle Paperwhite', and add the result to wishlist. Confirm via wishlist.",
        "Sign in as david.k@test.com. Open Today's Deals > Deals in Electronics, add the top result to cart, then go to Wishlist > move 1 wishlist item to cart, then checkout. Report total.",
        "Sign in as alice.j@test.com. From Your Orders, reorder her cheapest delivered order. Report the new order_total.",
        "Sign in as bob.c@test.com. Add a Galaxy Tab A9+ 64GB variant to cart, change variant to 128GB, and report the new price.",
        "Sign in as carol.d@test.com. Search 'Vegan cookbook' on Amazon and add the top result to wishlist. Confirm via Wishlist.",
        "Sign in as david.k@test.com. Add 5 different items to cart spread across 5 different categories, then apply checkout. Report the count of distinct categories represented.",
        "Sign in as alice.j@test.com. Open the Today's Deals page, take the first Lightning Deal product, then on the product detail page check whether Free Returns is enabled.",
        "Sign in as bob.c@test.com. Open Amazon Business, register the account-creation flow (use the existing register button) and confirm whether a credit card is required.",
    ]

    # Browse-only sanity tasks targeting matrix expansion (12)
    new += [
        "Browse Electronics > Smartphones and report how many distinct Apple iPhone models appear in results.",
        "Browse Electronics > Tablets and report how many distinct brands appear.",
        "Browse Computers > Laptops, filter to 16GB RAM, and report the brands shown.",
        "Search 'iPhone 15 Pro Max 1TB' on Amazon and report the highest price shown for that variant.",
        "Search 'Galaxy S24 Ultra 512GB' on Amazon and report any color variants offered.",
        "Search 'iPad Pro 13 M4' on Amazon and report whether the Tandem OLED display is mentioned.",
        "Search 'MacBook Pro 16 M3 Max' on Amazon and report the GPU listed in specs.",
        "Search 'Surface Pro 9' on Amazon and report whether 'Type Cover' is sold separately.",
        "Search 'Fire Max 11' on Amazon and report the display resolution.",
        "Search 'OnePlus 12' on Amazon and report the fast-charging wattage.",
        "Search 'Xiaomi 14 Pro' on Amazon and report the camera partnership brand listed.",
        "Search 'Nothing Phone (2)' on Amazon and report the design feature mentioned.",
    ]

    print(f"adding {len(new)} more tasks starting at id {start}")
    with open(TASKS_PATH, 'a') as f:
        for i, q in enumerate(new):
            row = {
                "web_name": "Amazon",
                "id": f"Amazon--{start + i}",
                "ques": q,
                "web": "http://localhost:40001/",
                "upstream_url": "https://www.amazon.com/",
            }
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"new total: {existing_count()}")


if __name__ == "__main__":
    main()
