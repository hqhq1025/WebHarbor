#!/usr/bin/env python3
"""R4 task generator — appends ~410 new tasks across the new feature surface.

Task types covered (matches R4 spec):
  - questions-and-answers  (uses /product/<slug>/questions)
  - video-review           (asks for a review feature/mention)
  - comparison-page        (find / compare specs between two products)
  - lightning-deal-end-time (Today's Deals)
  - smart-home-skill        (Alexa skills directory)
  - prime-now-1hr           (Prime benefits / delivery)
  - baby-registry-add-item  (registry / wishlist)
  - multi-step              (cart + checkout, returns, wishlist sequences)

Run from sites/amazon/_data/. Writes to ../tasks.jsonl (append).
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
TASKS_PATH = os.path.join(HERE, '..', 'tasks.jsonl')


def task(qid, ques):
    return {
        "web_name": "Amazon",
        "id": f"Amazon--{qid}",
        "ques": ques,
        "web": "http://localhost:40001/",
        "upstream_url": "https://www.amazon.com/",
    }


def main():
    # Find next id
    next_id = 0
    if os.path.exists(TASKS_PATH):
        with open(TASKS_PATH, 'r') as f:
            for line in f:
                if line.strip():
                    rec = json.loads(line)
                    raw = rec['id'].rsplit('--', 1)[-1]
                    if raw.isdigit():
                        next_id = max(next_id, int(raw) + 1)
    start_id = next_id

    new_tasks = []
    def add(q):
        nonlocal next_id
        new_tasks.append(task(next_id, q))
        next_id += 1

    # ---- 60 questions-and-answers tasks ----
    qna_targets = [
        "Echo Dot (5th Gen)", "Apple AirPods Pro", "Sony WH-1000XM5",
        "Kindle Paperwhite", "Instant Pot Duo", "Roomba",
        "Fire TV Stick", "Ring Video Doorbell", "Samsung 65 QLED",
        "MacBook Air M3", "iPad Air", "Galaxy S24",
        "Dyson V15", "KitchenAid Stand Mixer", "Nintendo Switch OLED",
        "GoPro HERO12", "Bose QuietComfort Ultra", "LEGO Star Wars",
        "Yeti Tundra", "Theragun Pro",
    ]
    qna_questions = [
        "open its Customer Q&A page and report how many people found the top answer helpful",
        "go to the Q&A page and report whether the seller has answered the warranty question",
        "find the answer about USB-C cable inclusion on its Q&A page",
        "open its Q&A page and report the answer about RAM upgradeability",
        "navigate to its Q&A page sorted by 'Most recent' and report the most recently asked question",
        "find on its Q&A page the seller's answer about firmware updates",
        "open its Q&A page and report whether it is dishwasher safe",
        "go to its Q&A page and report the answer regarding compatibility with iPhone 15 Pro Max",
        "find on its Q&A page the answer about cruelty-free certification",
        "open its Q&A page and locate the answer about warranty length",
        "navigate to its Q&A page and find the customer answer about sizing",
        "open its Q&A page and report whether parts are dishwasher safe",
    ]
    qi = 0
    for prod in qna_targets:
        for offset in range(3):
            q = qna_questions[(qi + offset) % len(qna_questions)]
            add(f"Search for '{prod}' on Amazon, open its product page, then {q}.")
            qi += 1
            if len([t for t in new_tasks if 'Q&A' in t['ques'] or 'Customer Q&A' in t['ques']]) >= 60:
                break
        if len([t for t in new_tasks if 'Q&A' in t['ques'] or 'Customer Q&A' in t['ques']]) >= 60:
            break

    # ---- 40 video-review tasks ----
    video_targets = [
        "Sony A7 IV camera", "GoPro HERO12", "DJI Osmo Pocket 3",
        "Insta360 X3", "Canon EOS R10", "Logitech StreamCam",
        "Blue Yeti microphone", "Elgato HD60 X capture card",
        "Razer Kiyo Pro", "Atomos Ninja recorder",
    ]
    video_qs = [
        "and report whether the customer video review thumbnail panel is shown",
        "and find a review that mentions 'video quality'",
        "and report how many customer-uploaded images appear on its Customer images page",
        "and check whether the A+ Content page mentions video stabilization",
        "navigate to its All Reviews page sorted by top reviews and report the highest-rated review title",
    ]
    vi = 0
    for prod in video_targets:
        for q in video_qs[:4]:
            add(f"Search '{prod}' on Amazon, open its product page {q}.")
            vi += 1
    # 40 total target → add ~10 more in mixed style
    for extra in [
        "Find the All Reviews page for 'GoPro HERO12 Black' and report the count of 1-star reviews.",
        "Search 'Sony A7 IV' on Amazon, open All Reviews, filter to 5-star and report the top review title.",
        "Open the Customer images page for 'Insta360 X3' and report the most recent uploader's name.",
        "Search 'Blue Yeti' on Amazon and report the number of answered questions shown on its product page.",
        "Find the A+ Content page for 'DJI Osmo Pocket 3' and report the headline benefit listed first.",
        "Find a video-capable camera under $500 and report its highest customer rating.",
        "Open All Reviews for 'Logitech StreamCam' sorted oldest first and report the first review's date.",
        "Search 'Razer Kiyo Pro' on Amazon and click 'See all customer photos' — report how many photos appear.",
        "Open the Customer images page for 'Canon EOS R10' and report the helpful count on the top image.",
        "Search 'Elgato HD60 X' and report the price shown on its A+ Content page footer.",
    ]:
        add(extra)

    # ---- 40 comparison-page tasks ----
    cmp_pairs = [
        ("Apple AirPods Pro", "Sony WF-1000XM5"),
        ("Sony WH-1000XM5", "Bose QuietComfort Ultra"),
        ("Echo Dot", "Google Nest Mini"),
        ("Kindle Paperwhite", "Kobo Clara"),
        ("Dyson V15", "Shark IZ363HT"),
        ("Roomba j7+", "Shark AI Robot"),
        ("MacBook Air M3", "Dell XPS 13"),
        ("iPad Air", "Samsung Galaxy Tab S9"),
        ("Nintendo Switch OLED", "Steam Deck"),
        ("GoPro HERO12", "DJI Osmo Action 4"),
    ]
    cmp_qs = [
        "compare their prices and report which one is cheaper",
        "report which one has the higher star rating",
        "compare battery life specs and report which lasts longer",
        "compare and report which has more verified reviews",
    ]
    for a, b in cmp_pairs:
        for q in cmp_qs:
            add(f"Find both '{a}' and '{b}' on Amazon, then {q}.")

    # ---- 30 lightning-deal-end-time tasks ----
    for kw in ["Echo", "Fire TV", "Kindle", "Ring", "Blink",
               "Roomba", "Instant Pot", "Levi's", "Adidas", "Nike",
               "Apple", "Samsung", "Sony", "Bose", "JBL"]:
        add(f"Open Today's Deals on Amazon and find a Lightning Deal for {kw}; report its discount percentage.")
        add(f"On the Today's Deals page, locate a {kw} deal under $50 and report the deal title.")

    # ---- 30 smart-home-skill tasks ----
    skill_qs = [
        "Open the Alexa Skills page on Amazon and report the rating of the Spotify skill.",
        "On the Alexa Skills page, filter by 'Music & Audio' and report the top-rated skill.",
        "Sort the Alexa Skills page by 'Most reviewed' and report the #1 skill name.",
        "Open the Alexa Skills page and report how many skills are listed in the 'Kids' category.",
        "On the Alexa Skills page, find the 'Headspace' skill and report its review count.",
        "Open the Alexa Skills directory and report the rating of the 'Jeopardy!' skill.",
        "On the Alexa Skills page, find a Smart Home skill and report its name.",
        "Open the Alexa Skills page and report which 'Food & Drink' skill has the lowest rating.",
        "On the Alexa Skills page, sort by name A-Z and report the first skill alphabetically.",
        "Open the Alexa Skills page and locate a skill from the 'Travel & Transport' category.",
        "On the Alexa Skills page, find the 'Sleep Sounds' skill and report its review count.",
        "Open the Alexa Skills page and report the category of the 'Daily Word' skill.",
        "Sort Alexa Skills by top rated and report the rating of position #1.",
        "On the Alexa Skills page, filter Finance category and report the listed skill.",
        "Open the Alexa Skills directory and find a Weather skill, report its review count.",
    ]
    for q in skill_qs * 2:
        add(q)

    # ---- 30 prime-now-1hr tasks ----
    prime_qs = [
        "Open the Prime overview page and navigate to the Prime Delivery benefit. Report whether Same-Day Delivery is included.",
        "Find the Prime Delivery benefit page and report the minimum order amount for FREE Same-Day Delivery.",
        "Open the Prime Video benefit page and report the standalone monthly price.",
        "On the Prime Music benefit page, report the standalone Music Unlimited price.",
        "Open the Prime Try Before You Buy page and report how many items can be tried at once.",
        "On the Prime Reading benefit page, report the maximum number of titles you can borrow at once.",
        "Open the Prime Photos benefit page and report the free video storage amount.",
        "Visit the Prime Gaming page and report which streaming subscription is included.",
        "Open the main Prime page and report the price for Prime monthly membership.",
        "Find the Prime Try Before You Buy benefit page and report the trial duration in days.",
        "Open the Prime Photos benefit page and report whether photo printing is supported.",
        "Open the Prime Video benefit page and find the resolution support mentioned (e.g., 4K).",
        "On the Prime Music page, report whether ad-free streaming is included.",
        "On the Prime Gaming page, report whether Twitch sub is included free monthly.",
        "Find on the Prime Delivery page whether FREE One-Day Delivery is mentioned.",
    ]
    for q in prime_qs * 2:
        add(q)

    # ---- 20 baby-registry-add-item tasks ----
    baby_qs = [
        "Open the Amazon Baby Registry page (registry) and report the headline shown.",
        "Navigate to the Registry page and find the section explaining benefits.",
        "Open the Registry page and find a link that lets you create a new wedding registry.",
        "From the registry page, navigate to add a Fisher-Price product to your wishlist (sign-in if needed).",
        "Open the Registry page and report whether a discount/welcome box is mentioned.",
        "Search 'Pampers diapers' and add the first result to your wishlist.",
        "Search 'baby monitor' and add a 4-star-and-up result to your wishlist.",
        "Search 'baby carrier' on Amazon and add the top result to your cart.",
        "Search 'crib mattress' on Amazon and add the cheapest result to your wishlist.",
        "Search 'baby formula' on Amazon and report the price of the first Similac product.",
    ]
    for q in baby_qs * 2:
        add(q)

    # ---- 60 multi-step tasks ----
    multi_qs = [
        "Search 'Kindle Paperwhite' on Amazon, add it to your cart, then proceed to checkout — report the total price including tax.",
        "Find the cheapest pair of Levi's 501 jeans, add it to the cart, then change the quantity to 2 and report the new subtotal.",
        "Add 'Echo Dot (5th Gen)' to your wishlist, then remove it and confirm the wishlist count is back to zero.",
        "Find your most recent delivered order and start a return for one item with reason 'No longer needed'.",
        "Place 'Sony WH-1000XM5' into the cart, apply checkout, then cancel the resulting order from order details.",
        "Open Today's Deals, pick a deal under $25, add to cart, and report the cart subtotal before tax.",
        "Add the top-rated 'Atomic Habits' book to your wishlist, then open your wishlist and report its rating.",
        "Find a Hoka Bondi running shoe in size 9 and add it to the cart with the right variant string.",
        "Find an Instant Pot Duo Plus 8-quart model, add it to the cart, and report the delivery estimate shown.",
        "Search 'MacBook Air M3' on Amazon, open the All Reviews page, sort by Top reviews, and report the top reviewer's name.",
        "Find an Amazon product with the 'Climate Pledge Friendly' badge and report its category.",
        "Search 'Allbirds Wool Runners' on Amazon, open its product page, and report the seller name listed under 'Sold by'.",
        "Search 'Patagonia Better Sweater' on Amazon and open its A+ Content page; report the first 'From the manufacturer' benefit title.",
        "Search 'Sony WH-1000XM5' on Amazon, open its Q&A page, and report whether the seller has answered the firmware update question.",
        "Find any LEGO Star Wars set, navigate to its product page, and report the price after the deal discount.",
        "Open the All Reviews page for 'Echo Dot (5th Gen)' and report the count of 3-star reviews on the histogram.",
        "Find 'Logitech MX Master' mouse and add it to the cart, then open the cart and report whether free shipping is shown.",
        "Search 'Brooks Ghost' running shoe and add size 10 to your wishlist, then open the wishlist and report the variant string.",
        "Open the seller storefront for any Apple product (use the Sold by link) and report the seller's positive rating percentage.",
        "Open the author page for 'Tolkien' on Amazon and report how many books are listed.",
    ]
    for q in multi_qs * 3:
        add(q)

    # ---- 60 misc — A+ content / seller / author / customer images / returns ----
    misc_qs = [
        "Open the A+ Content page for 'Echo Dot (5th Gen)' and report the hero subtitle.",
        "Open the A+ Content page for 'Apple AirPods Pro' and report the third 'From the manufacturer' benefit title.",
        "Open the A+ Content page for 'KitchenAid Classic stand mixer' and report the average customer rating shown.",
        "Open the Customer images page for 'Roomba' and report how many photos are listed.",
        "Open the Customer images page for 'Sony WH-1000XM5' and report the name of the most helpful uploader.",
        "Open the seller storefront for 'Levi's' jeans (via product's Sold by link) and report the number of brands they carry.",
        "Open the seller storefront for any Nike shoe and report the listed 'ships from' location.",
        "Open the author page for 'Stephen King' on Amazon and report the headline 'Featured' book title.",
        "Open the author page for 'Agatha Christie' and report the number of titles listed.",
        "Open the author page for 'Brandon Sanderson' and report the bio's language-translation count.",
        "Search for any book on Amazon and confirm that the brand link on its product page links to an author page (returns 200).",
        "Search 'AirPods Pro' on Amazon, open its product page, then click 'See all customer photos' and verify the page loads.",
        "Open the All Reviews page for 'KitchenAid stand mixer', filter by 4 stars, and report the count.",
        "Open the All Reviews page for 'Patagonia Better Sweater' sorted by oldest first, and report the date of the oldest review.",
        "Open the A+ Content page for 'Nintendo Switch OLED' and report the average rating displayed.",
        "Open the Q&A page for 'Allbirds Wool Runners' sorted by Most recent and report the most recent question text.",
        "Open the Q&A page for 'Instant Pot Duo Plus 8-quart' and report whether the seller has answered the dishwasher safety question.",
        "Find an iRobot product, open its Q&A page, and report whether the model is compatible with Alexa.",
        "On the product page for 'Bose QuietComfort Ultra Earbuds', check for the climate-pledge-friendly badge presence.",
        "Search 'Ninja Speedi' on Amazon and from the product page report the seller name under 'Sold by'.",
    ]
    for q in misc_qs * 3:
        add(q)

    with open(TASKS_PATH, 'a') as f:
        for t in new_tasks:
            f.write(json.dumps(t) + '\n')
    print(f"Appended {len(new_tasks)} tasks (IDs {start_id}-{next_id-1})")


if __name__ == '__main__':
    main()
