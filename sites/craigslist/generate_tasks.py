"""Generate ≥1500 WebVoyager-format tasks for the Craigslist mirror.

Run: python3 generate_tasks.py > tasks.jsonl

Uses the live SQLite DB to derive concrete listing titles/ids, then crosses
that catalog with ~30 task templates to produce a diverse benchmark set.
"""
import json
import os
import random
import re
import sys

# Load app context to query the DB
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from app import app, Listing, Category, ForumThread  # noqa: E402

PORT = 40015
WEB = f"http://localhost:{PORT}/"
UPSTREAM = "https://craigslist.org/"
WEB_NAME = "Craigslist"

AREAS = ["san francisco", "east bay", "south bay", "peninsula", "north bay", "santa cruz"]
AREA_SLUGS = {
    "san francisco": "sfc", "east bay": "eby", "south bay": "sby",
    "peninsula": "pen", "north bay": "nby", "santa cruz": "scz",
}

HELP_TOPICS = [
    ("posting", "creating a posting"),
    ("editing", "editing or updating a posting"),
    ("reposting", "reposting an expired ad"),
    ("deleting", "deleting your posting"),
    ("replying", "replying to a posting"),
    ("flags", "flagging a posting"),
    ("blocked", "why was my posting blocked"),
    ("safety", "personal safety while meeting"),
    ("payment", "accepted payment methods"),
    ("fees", "posting fees by category"),
    ("account", "managing your craigslist account"),
    ("search", "advanced search tips"),
    ("forum", "using the discussion forums"),
    ("tos", "terms of use overview"),
    ("privacy", "privacy and what we collect"),
    ("discrimination", "discrimination and fair housing"),
]

FORUM_BOARDS = [
    ("apple", "apple"), ("diy", "do it yourself"), ("garden", "gardening"),
    ("pets", "pets"), ("philosophy", "philosophy"), ("politics", "politics"),
    ("sf-haiku", "sf haiku"), ("feedback", "site feedback"),
    ("housing-help", "housing help"), ("moving", "moving to sf"),
    ("rideshare", "rideshare"), ("linux", "linux"),
]


def emit(tasks, q):
    tasks.append({
        "web_name": WEB_NAME,
        "id": f"{WEB_NAME}--{len(tasks)}",
        "ques": q,
        "web": WEB,
        "upstream_url": UPSTREAM,
    })


def main():
    rnd = random.Random(20260527)
    tasks = []

    with app.app_context():
        # Pull catalog
        cats = Category.query.order_by(Category.display_order).all()
        cat_by_slug = {c.slug: c for c in cats}
        # Listings per category, area
        all_listings = Listing.query.filter_by(status="active").all()
        by_cat = {}
        by_area = {}
        for L in all_listings:
            by_cat.setdefault(L.category_slug, []).append(L)
            by_area.setdefault(L.area, []).append(L)
        threads = ForumThread.query.all()

        # ---- 1. Browse category, filter by area, find under-X-dollars listing
        # Generate per-(cat × area × price-cap) combinations
        cat_areas = [
            ("furniture", "east bay", [50, 75, 100, 125, 150, 200, 300, 500]),
            ("furniture", "san francisco", [100, 150, 200, 300, 500]),
            ("furniture", "south bay", [100, 150, 200, 300, 500]),
            ("furniture", "peninsula", [100, 200, 300, 500]),
            ("electronics", "east bay", [50, 100, 150, 200, 300]),
            ("electronics", "san francisco", [100, 150, 200, 300]),
            ("electronics", "south bay", [100, 200, 300, 500]),
            ("electronics", "peninsula", [100, 200, 300]),
            ("bikes", "east bay", [200, 300, 400, 500, 700]),
            ("bikes", "san francisco", [300, 500, 700]),
            ("bikes", "south bay", [300, 500, 700]),
            ("bikes", "peninsula", [300, 500]),
            ("cars_trucks", "east bay", [5000, 7000, 10000, 15000]),
            ("cars_trucks", "south bay", [5000, 7000, 10000, 15000]),
            ("cars_trucks", "peninsula", [6000, 10000, 15000]),
            ("cars_trucks", "north bay", [6000, 10000, 15000]),
            ("apartments", "east bay", [1900, 2200, 2400, 2700, 3000]),
            ("apartments", "san francisco", [2500, 3000, 3500, 4000]),
            ("apartments", "south bay", [2200, 2500, 2800]),
            ("apartments", "peninsula", [2200, 2500, 2800]),
            ("apartments", "north bay", [2000, 2400, 2800]),
            ("rooms_shares", "east bay", [1000, 1200, 1500]),
            ("rooms_shares", "san francisco", [1300, 1500, 1700]),
            ("appliances", "east bay", [200, 300, 500]),
            ("musical", "east bay", [300, 500]),
            ("sporting", "east bay", [100, 300]),
            ("tools", "east bay", [100, 300]),
        ]
        for cat_slug, area, prices in cat_areas:
            cat = cat_by_slug.get(cat_slug)
            if not cat:
                continue
            label = cat.name
            for p in prices:
                emit(tasks, f"Browse {label} listings in the {area}, filter to ones priced under ${p:,}, and open the most expensive remaining result.")
                emit(tasks, f"Search {label} in the {area} under ${p:,} sorted by price ascending and open the third listing.")
                emit(tasks, f"In the {label} category restricted to {area}, find a posting under ${p:,} that includes at least one photo, then open its detail page.")

        # ---- 2. Detail page lookup tasks — pick concrete titles from DB
        # Sample listings with details to ask about
        feat_listings = [L for L in all_listings if L.details() and L.image]
        rnd.shuffle(feat_listings)
        for L in feat_listings[:120]:
            d = L.details()
            keys = [k for k in d.keys() if k not in ("images", "map_x", "map_y", "map_lat", "map_lng", "posted_by", "cross_streets")]
            if not keys:
                continue
            k = keys[0]
            cat_name = L.category.name if L.category else L.category_slug
            short = re.sub(r"\s+", " ", L.title).strip()
            short = short[:80]
            emit(tasks, f"Open the {cat_name} listing titled '{short}' and report what value the detail table shows for {k.replace('_', ' ')}.")
            if len(keys) > 1:
                k2 = keys[1]
                emit(tasks, f"Find the {cat_name} posting titled '{short}' in {L.area} and read its detail table — what does it say for {k2.replace('_', ' ')}?")

        # ---- 3. Save listing tasks (require login as benchmark user)
        save_targets = [L for L in all_listings if L.image][:60]
        for L in save_targets:
            short = re.sub(r"\s+", " ", L.title).strip()[:80]
            emit(tasks, f"Log in as alice.j@test.com with password TestPass123!, search for '{short}', open it, and save the listing to your favorites.")

        # Random user assignment
        users = ["alice.j@test.com", "ben.k@test.com", "carla.m@test.com", "david.p@test.com"]
        for L in feat_listings[40:90]:
            u = rnd.choice(users)
            short = re.sub(r"\s+", " ", L.title).strip()[:80]
            emit(tasks, f"Log in as {u} (password TestPass123!), open the posting '{short}' and add it to your favorites.")

        # ---- 4. Reply to listing
        for L in feat_listings[90:140]:
            short = re.sub(r"\s+", " ", L.title).strip()[:80]
            emit(tasks, f"Find the posting '{short}' and send the seller a reply asking whether the item is still available.")

        for L in feat_listings[140:180]:
            short = re.sub(r"\s+", " ", L.title).strip()[:80]
            emit(tasks, f"Open '{short}', then use the reply form to ask the seller for weekend pickup availability.")

        # ---- 5. Contact (different form than reply)
        for L in feat_listings[180:220]:
            short = re.sub(r"\s+", " ", L.title).strip()[:80]
            emit(tasks, f"Locate '{short}' and use the contact form (not the reply button) to leave a callback phone number with your message.")

        # ---- 6. Report listing for abuse
        report_reasons = ["spam", "miscategorized", "scam", "prohibited", "discriminatory", "offensive"]
        for i, L in enumerate(feat_listings[220:260]):
            short = re.sub(r"\s+", " ", L.title).strip()[:80]
            reason = report_reasons[i % len(report_reasons)]
            emit(tasks, f"Open '{short}' and file an abuse report with reason: {reason}.")

        # ---- 7. Flag listing
        for L in feat_listings[260:290]:
            short = re.sub(r"\s+", " ", L.title).strip()[:80]
            emit(tasks, f"Find '{short}' and use the flag button to flag it as prohibited.")

        # ---- 8. Hide listing
        for L in feat_listings[290:310]:
            short = re.sub(r"\s+", " ", L.title).strip()[:80]
            emit(tasks, f"From the search results, hide the posting '{short}' so it stops appearing in your future searches.")

        # ---- 9. Saved searches
        saved_searches = [
            ("east bay furniture under 100", "furniture", "east bay", 100),
            ("apartments in mission with laundry", "apartments", "san francisco", None),
            ("bikes in oakland under 400", "bikes", "east bay", 400),
            ("south bay cars under 8000", "cars_trucks", "south bay", 8000),
            ("electronics monitors", "electronics", None, 300),
            ("free moving boxes", "free", "east bay", 0),
            ("rooms in rockridge", "rooms_shares", "east bay", 1400),
            ("studio apartments berkeley", "apartments", "east bay", 2300),
            ("software jobs san francisco", "software", "san francisco", None),
            ("healthcare positions north bay", "healthcare", "north bay", None),
            ("musical instruments under 500", "musical", None, 500),
            ("sporting goods east bay", "sporting", "east bay", None),
            ("appliances east bay under 400", "appliances", "east bay", 400),
            ("lessons math tutoring", "lessons", None, None),
            ("plant swap events", "events", None, None),
            ("volunteer bike repair", "volunteers", "east bay", None),
            ("art photographer artists", "artists", None, None),
            ("ceramics workshop classes", "classes", None, None),
            ("running group community", "groups", None, None),
            ("lost cat dolores park", "lost_found", "san francisco", None),
        ]
        for name, cat, area, maxp in saved_searches:
            emit(tasks, f"Log in as alice.j@test.com (TestPass123!), run a search for '{name}', and save it with a name of your choice.")
            emit(tasks, f"Log in as ben.k@test.com (TestPass123!) and save a new search named '{name}'.")

        # ---- 10. Post a new listing
        post_titles = [
            ("furniture", "Vintage teak coffee table", 95, "east bay", "oakland"),
            ("furniture", "Pair of bookcases, walnut", 220, "san francisco", "mission district"),
            ("electronics", "Pixel 7 with case and charger", 240, "south bay", "san jose"),
            ("electronics", "27 inch USB-C monitor", 175, "east bay", "berkeley"),
            ("bikes", "Specialized hybrid bike, medium", 460, "north bay", "san rafael"),
            ("bikes", "Kids bike with training wheels", 85, "peninsula", "redwood city"),
            ("cars_trucks", "2010 Honda Fit, runs great", 5400, "east bay", "alameda"),
            ("apartments", "Bright two bedroom in noe valley", 3950, "san francisco", "noe valley"),
            ("free", "Free wooden pallets", 0, "east bay", "richmond"),
            ("free", "Free houseplants, moving", 0, "south bay", "sunnyvale"),
            ("musical", "Yamaha digital piano", 380, "peninsula", "burlingame"),
            ("sporting", "Hardly used tent, 2 person", 80, "santa cruz", "santa cruz"),
            ("tools", "Cordless drill set, three batteries", 60, "east bay", "hayward"),
            ("software", "Junior backend engineer, hybrid", None, "san francisco", "soma"),
            ("healthcare", "Pediatric speech therapist contract", None, "south bay", "santa clara"),
            ("food_bev_hosp", "Weekend brunch server", None, "san francisco", "marina"),
            ("lessons", "Beginner guitar lessons", 40, "east bay", "berkeley"),
            ("computer_services", "Laptop screen repair", 90, "south bay", "santa clara"),
            ("events", "Saturday community plant swap", 0, "san francisco", "mission district"),
            ("volunteers", "Volunteer for tool library shift", 0, "east bay", "oakland"),
        ]
        for cat, title, price, area, nh in post_titles:
            cat_name = cat_by_slug[cat].name if cat in cat_by_slug else cat
            price_part = f"price ${price:,}" if (price is not None and price > 0) else ("free" if price == 0 else "no price")
            emit(tasks, f"Log in as alice.j@test.com (TestPass123!) and post a new {cat_name} ad titled '{title}' in {nh}, {area}, with {price_part}.")
            emit(tasks, f"Log in as ben.k@test.com (TestPass123!) and create a posting in the {cat_name} category titled '{title}'.")

        # ---- 11. Edit / repost / extend (need a user's own post)
        # Use Alice/Ben — they will post first via the test users; the task assumes they did one
        # Adapt to existing seed pattern: tasks reference 'one of your active postings'
        # NOTE: Benchmark users have no pre-seeded posts. Tasks ask agent to post one first.
        edit_targets = post_titles[:8]
        for cat, title, price, area, nh in edit_targets:
            emit(tasks, f"Log in as alice.j@test.com, create a posting titled '{title}', then open its manage page and edit the description to add 'pickup only in {nh}'.")
            emit(tasks, f"Log in as carla.m@test.com, post a {cat_by_slug[cat].name if cat in cat_by_slug else cat} ad titled '{title}', then repost it from the manage page.")
            emit(tasks, f"Log in as david.p@test.com, create a posting titled '{title}', then extend it by 7 days from the manage page.")

        # ---- 12. Subcategory / group hub browsing
        for group_slug, group_label in [
            ("for-sale", "for sale"), ("housing", "housing"), ("jobs", "jobs"),
            ("services", "services"), ("community", "community"),
        ]:
            emit(tasks, f"Open the {group_label} group hub and count how many categories it lists.")
            emit(tasks, f"From the homepage, navigate to the {group_label} section and identify which category has the most active postings.")
            emit(tasks, f"Open the {group_label} group page and click into the most populated category.")

        # ---- 13. Area hub tasks
        for area, slug in AREA_SLUGS.items():
            emit(tasks, f"Open the {area} area hub from the homepage and identify three neighborhoods listed.")
            emit(tasks, f"Browse the {area} area hub, then click into the most recent featured posting.")
            emit(tasks, f"From the {area} hub, find a category that has fewer than ten active postings and report which one.")
            emit(tasks, f"Visit the {area} subhub and open the apartments category restricted to that area.")

        # ---- 14. Neighborhood hubs
        nbhoods = {
            "sfc": ["mission district", "soma", "richmond district", "sunset", "nob hill", "north beach", "marina", "haight", "castro"],
            "eby": ["oakland", "berkeley", "alameda", "emeryville", "fremont", "rockridge", "west oakland"],
            "sby": ["san jose", "sunnyvale", "santa clara", "mountain view", "cupertino"],
            "pen": ["palo alto", "menlo park", "redwood city", "san mateo", "burlingame"],
            "nby": ["san rafael", "santa rosa", "napa", "vallejo", "mill valley"],
            "scz": ["santa cruz", "aptos", "capitola", "watsonville"],
        }
        for slug, items in nbhoods.items():
            area_name = [a for a, s in AREA_SLUGS.items() if s == slug][0]
            for nh in items:
                emit(tasks, f"Open the {nh} neighborhood hub under {area_name} and list the first three postings shown.")
                emit(tasks, f"Browse {area_name} -> {nh} and find a posting whose price is below $200, then open it.")

        # ---- 15. Help / safety / scams / legal
        for slug, title in HELP_TOPICS:
            emit(tasks, f"Open the help topic '{title}' from the craigslist about page and report the first sentence of the body.")
            emit(tasks, f"Find the help page for '{title}' and summarize its main point in one sentence.")
        emit(tasks, "Open the personal safety tips page and report the recommended meeting location for a high-value item exchange.")
        emit(tasks, "Read the avoiding scams page and identify which scam pattern involves an overpayment.")
        emit(tasks, "Open the legal page and find the statute named in connection with the personals category removal.")
        emit(tasks, "Open the terms of use page and report what governing law section is named.")
        emit(tasks, "Find the privacy policy page and identify how long relay messages are retained.")
        emit(tasks, "Open the system status page and report which service is currently in 'degraded' state.")
        emit(tasks, "Open the help topic 'posting fees by category' and report the SF Bay Area jobs posting fee.")
        emit(tasks, "Read the safety tip about disclosing your home address and quote the recommendation.")
        emit(tasks, "Read the help topic on reposting and report the cooldown period.")
        emit(tasks, "Find the help topic about replying and report how long the relay address hides both inboxes.")
        emit(tasks, "Find the help topic on flagging and report whether false flags are rate-limited.")
        emit(tasks, "Open the terms of use page and report what happens to a posting's copyright when you submit it.")
        emit(tasks, "Open the privacy policy and report whether craigslist sells your data to advertisers.")

        # ---- 16. Forum browsing
        for slug, name in FORUM_BOARDS:
            emit(tasks, f"Open the {name} discussion forum and report how many threads it currently lists.")
            emit(tasks, f"Visit the {name} forum and open the most recently updated thread.")
            emit(tasks, f"From the discussion forums index, click into {name} and report the title of the pinned thread (or note that there is none).")
        for t in threads[:20]:
            short = t.title[:90]
            emit(tasks, f"Open the discussion-forums '{t.board_slug}' board and read the thread titled '{short}'. Report how many replies it has.")
            emit(tasks, f"Find the forum thread '{short}' and quote the first reply.")

        # ---- 17. Post a forum thread / reply
        for slug, name in FORUM_BOARDS[:8]:
            emit(tasks, f"Log in as alice.j@test.com and post a new thread in the {name} forum with title 'looking for advice on {name}' and a short body.")
            emit(tasks, f"Log in as ben.k@test.com and reply to the most recently updated thread in the {name} forum with a one-sentence reply.")

        # ---- 18. Account: change password
        for u in users:
            emit(tasks, f"Log in as {u} (current password TestPass123!) and change the password to NewPass2026! via the change-password page.")
            emit(tasks, f"Log in as {u}, open the account settings, and update the phone number to (415) 555-0199.")
            emit(tasks, f"Log in as {u} and update the listed area in your account profile to a different region.")

        # ---- 19. Saved-search delete
        emit(tasks, "Log in as alice.j@test.com and delete the saved search named 'East Bay furniture under 100'.")
        emit(tasks, "Log in as alice.j@test.com and delete the saved search named 'Studios with laundry'.")
        emit(tasks, "Log in as alice.j@test.com, then create a new saved search for east bay bikes under 500 and delete one of your existing saved searches.")
        emit(tasks, "Log in as alice.j@test.com and rename the workflow so only the 'Studios with laundry' saved search remains.")

        # ---- 20. Messages
        emit(tasks, "Log in as alice.j@test.com and report the subject of the most recent inbound message in your inbox.")
        emit(tasks, "Log in as ben.k@test.com and quote the latest unread message body.")
        emit(tasks, "Log in as carla.m@test.com and report how many messages relate to the Toyota Prius posting.")
        emit(tasks, "Log in as david.p@test.com and find an inbound inquiry about the Palo Alto downtown 1BR listing, then reply.")
        emit(tasks, "Log in as alice.j@test.com and delete the most recent message about the Berkeley studio.")

        # ---- 21. Multi-step comparison tasks
        for L1, L2 in [(feat_listings[i], feat_listings[i+1]) for i in range(0, 40, 2)]:
            t1 = re.sub(r"\s+", " ", L1.title).strip()[:60]
            t2 = re.sub(r"\s+", " ", L2.title).strip()[:60]
            emit(tasks, f"Compare the two postings '{t1}' and '{t2}'. Report which has the lower price.")
            emit(tasks, f"Open both '{t1}' and '{t2}' and report which one is in a more northerly Bay Area region.")

        # ---- 22. Sort tasks
        for cat_slug in ["furniture", "electronics", "bikes", "apartments", "cars_trucks", "lessons"]:
            cat = cat_by_slug.get(cat_slug)
            if not cat:
                continue
            emit(tasks, f"Browse the {cat.name} category, sort by price ascending, and report the title and price of the very first result.")
            emit(tasks, f"In the {cat.name} category, sort by price descending and open the second most expensive listing.")
            emit(tasks, f"Sort {cat.name} by oldest first and report when the oldest active posting was created.")
            emit(tasks, f"In {cat.name}, switch to gallery view and identify a listing with at least three photos.")
            emit(tasks, f"Browse {cat.name} in list view, then switch to map view and find a posting close to the bay water.")

        # ---- 23. Has-image filter
        for cat_slug in ["furniture", "cars_trucks", "apartments", "bikes"]:
            cat = cat_by_slug.get(cat_slug)
            if not cat:
                continue
            for area in ["east bay", "san francisco", "south bay"]:
                emit(tasks, f"Search the {cat.name} category in {area} with the 'has image' filter on and report how many listings remain.")

        # ---- 24. Specific named lookups
        named_lookups = [
            ("Ergonomic task chair", "what color is the chair?"),
            ("Marin commuter bike", "what type of brakes does the bike have?"),
            ("2006 Honda Accord EX sedan", "what is the listed mileage?"),
            ("2014 Honda Odyssey EX-L", "how many seats does the minivan have?"),
            ("Sunny studio near Berkeley BART", "what is the pet policy?"),
            ("Dell 27 inch USB-C monitor", "what resolution does the monitor have?"),
            ("Walnut writing desk with two drawers", "what is the depth?"),
            ("Backend engineer for civic data startup", "what is the compensation range?"),
            ("Speech language pathologist school year role", "what is the hourly compensation range?"),
            ("Line cook for modern Asian bistro", "what shift hours are listed?"),
            ("Saturday neighborhood plant swap", "what should you bring?"),
            ("Volunteer bike repair clinic helpers", "what skills are listed?"),
            ("Seeking photographer for small zine project", "what is the budget?"),
            ("LG washer and gas dryer pair", "what type of dryer is it?"),
            ("Free moving boxes and packing paper", "how many boxes are listed?"),
            ("Room in sunny Oakland craftsman", "what is the bathroom situation?"),
            ("Standing desk frame, white", "what is the load rating?"),
            ("Trek hybrid bike, large frame", "what gearing does it have?"),
            ("Mid-century walnut sideboard", "what material is it made of?"),
            ("IKEA Hemnes 6-drawer dresser", "what color is the dresser?"),
            ("Leather recliner armchair", "what color is the recliner?"),
            ("Gray sectional sofa with chaise", "is the home pet-free?"),
            ("Solid oak farmhouse dining table", "how many people does it seat?"),
            ("Pair of mid-century nightstands", "what wood are they made of?"),
            ("Crate and Barrel Lounge II loveseat", "what color is the slipcover?"),
            ("Reclaimed wood console table", "what length is it?"),
            ("LG 55 inch 4K OLED TV", "what is the model number?"),
        ]
        for title, q in named_lookups:
            emit(tasks, f"Find the posting titled '{title}' and answer: {q}")

        # ---- 25. Search using complex query
        complex_queries = [
            ("studio apartment with in-unit laundry under 2300 in east bay", "apartments", "east bay", 2300),
            ("commuter bike with hydraulic disc brakes east bay under 600", "bikes", "east bay", 600),
            ("honda accord under 7000 in south bay", "cars_trucks", "south bay", 7000),
            ("office chair adjustable arms east bay", "furniture", "east bay", None),
            ("dishwasher front-load east bay", "appliances", "east bay", None),
            ("USB-C monitor 27 inch", "electronics", None, None),
            ("plant swap saturday", "events", None, None),
            ("speech language pathologist contract", "healthcare", None, None),
            ("calculus tutoring online", "lessons", None, None),
            ("photographer zine project artists", "artists", None, None),
            ("bike repair volunteer saturday", "volunteers", "east bay", None),
            ("ceramics handbuilding workshop", "classes", None, None),
            ("book club mission", "groups", None, None),
            ("lost cat dolores park", "lost_found", None, None),
            ("free moving boxes east bay", "free", "east bay", None),
            ("piano digital under 500", "musical", None, 500),
            ("tent two person", "sporting", None, None),
            ("cordless drill set", "tools", None, None),
            ("standing desk frame", "furniture", None, None),
            ("commuter folding bike caltrain", "bikes", "south bay", None),
            ("oakland craftsman room rockridge", "rooms_shares", "east bay", None),
            ("sublet near berkeley campus", "sublets", "east bay", None),
            ("parking space mission district", "parking", "san francisco", None),
            ("office commercial space soma", "office_commercial", "san francisco", None),
        ]
        for q, cat, area, maxp in complex_queries:
            emit(tasks, f"Search craigslist for '{q}' and open the most relevant result.")
            emit(tasks, f"Run an advanced search with query '{q}' and report the price of the top result.")

        # ---- 26. Photo gallery navigation
        photo_listings = [L for L in all_listings if L.image][:30]
        for L in photo_listings:
            short = re.sub(r"\s+", " ", L.title).strip()[:80]
            emit(tasks, f"Open '{short}' and step through every photo in the gallery, reporting how many photos it has.")

        # ---- 27. Map view tasks
        for area in AREAS:
            sample = by_area.get(area, [])[:5]
            for L in sample[:3]:
                short = re.sub(r"\s+", " ", L.title).strip()[:80]
                emit(tasks, f"Open '{short}' and report whether its map pin is closer to the bay water or inland.")

        # ---- 28. Unsave / unhide
        emit(tasks, "Log in as alice.j@test.com, open favorites, and unsave the Berkeley BART studio listing.")
        emit(tasks, "Log in as alice.j@test.com, save a furniture listing of your choice, then immediately unsave it.")
        emit(tasks, "Log in as ben.k@test.com, hide the LG OLED TV listing, then visit the search page with hidden items shown and unhide it.")

        # ---- 29. Contact craigslist support
        for topic in ["billing", "bug", "abuse", "legal", "press"]:
            emit(tasks, f"Open the contact craigslist page and submit a {topic} inquiry with a one-sentence message.")

        # ---- 30. Account deletion
        emit(tasks, "Log in as david.p@test.com (TestPass123!), open account settings, and initiate account deletion. Stop before final confirmation.")
        emit(tasks, "Find the account deletion flow under account settings and report what confirmation word is required.")

        # ---- 31. Register a new account
        register_emails = [
            ("evan.m@test.com", "evan", "Evan Mitchell", "south bay"),
            ("fiona.l@test.com", "fiona", "Fiona Lee", "north bay"),
            ("greg.s@test.com", "greg", "Greg Singh", "peninsula"),
            ("hannah.t@test.com", "hannah", "Hannah Tran", "santa cruz"),
            ("ivan.b@test.com", "ivan", "Ivan Bauer", "east bay"),
        ]
        for email, username, name, area in register_emails:
            emit(tasks, f"Register a new account with email {email}, username {username}, name {name}, and area {area}. Use password TestPass123!.")

        # ---- 32. Login error path
        emit(tasks, "Try to log in as alice.j@test.com with the wrong password 'wrong123'. Report the error message shown.")
        emit(tasks, "Try to log in with an unrecognized email someoneunknown@test.com. Report whether the system distinguishes wrong-email from wrong-password in the error.")

        # ---- 33. Sort / view combos
        for view in ["list", "thumb", "gallery", "map"]:
            for cat_slug in ["furniture", "apartments", "cars_trucks"]:
                cat = cat_by_slug.get(cat_slug)
                if cat:
                    emit(tasks, f"Browse {cat.name} in {view} view and identify a listing that catches your attention based on price/photo. Open it.")

        # ---- 34. Best-of / featured
        emit(tasks, "Open the best of craigslist page and report the title of the first featured listing.")
        emit(tasks, "Navigate from the homepage to the best-of-craigslist archive and open any one posting.")
        emit(tasks, "On the homepage, identify the featured posting that has the most views and open it.")

        # ---- 35. Apps page
        emit(tasks, "Open the craigslist apps page and report the current iOS app version.")
        emit(tasks, "Find the apps page and report the minimum android version required.")

        # ---- 36. System status with action
        emit(tasks, "Open system status, identify any service marked degraded, and read its note. Report the affected service.")

        # ---- 37. Cross-account: reply then save
        for L in feat_listings[300:340]:
            short = re.sub(r"\s+", " ", L.title).strip()[:60]
            emit(tasks, f"Log in as alice.j@test.com, search for '{short}', save it to favorites, then send the seller a reply via the relay.")

        # ---- 38. Pagination / volume counts
        for cat in cats[:15]:
            n = len(by_cat.get(cat.slug, []))
            emit(tasks, f"Visit the {cat.name} category and confirm at least {max(1, n - 3)} active postings are shown in the count line.")

        # ---- 39. Multi-step post workflow (use multi-step wizard)
        for cat_slug, title, price, area, nh in post_titles[:10]:
            emit(tasks, f"Use the multi-step posting wizard: choose the {cat_by_slug[cat_slug].name} category, pick {area}, then publish a posting titled '{title}'.")

        # ---- 40. Photo count
        for L in photo_listings:
            short = re.sub(r"\s+", " ", L.title).strip()[:80]
            emit(tasks, f"Open '{short}' and count how many distinct images appear in the photo strip beneath the main image.")

        # ---- 41. Forum: read replies and report author
        for t in threads[:15]:
            short = t.title[:90]
            emit(tasks, f"Open forum thread '{short}' and report the name of the user who posted the first reply.")

        # ---- 42. Aliases / shortcuts
        emit(tasks, "Navigate to /myaccount/posts (your account postings) and report whether you have any active postings.")
        emit(tasks, "Visit /myaccount/favorites and confirm the page redirects to /saved.")

        # ---- 43. Search with date / sort by oldest
        for area in AREAS:
            emit(tasks, f"In the {area} area, sort all active listings by oldest first and report the title of the oldest posting.")

        # ---- 44. Group-hub then drill-down
        for grp in ["housing", "jobs", "services", "community", "for-sale"]:
            emit(tasks, f"Visit the {grp} group hub, pick the category with the most postings, and open the cheapest one.")
            emit(tasks, f"From the {grp} hub, identify a featured listing with a photo and open its detail page.")

        # ---- 45. Save then comparison
        emit(tasks, "Log in as alice.j@test.com, save three different bike listings under $500, then visit favorites and compare their gear setups to decide which has the most reliable braking.")
        emit(tasks, "Log in as ben.k@test.com, save two studio apartments in east bay under $2300, then compare their laundry options on favorites page.")

        # ---- 46. Hide listing chain
        emit(tasks, "From the furniture search results in east bay, hide three different chair listings and then verify they no longer appear in the default view.")

        # ---- 47. Browser flow: search, paginate by sort, save
        emit(tasks, "Search 'commuter bike' across all of SF bay area, sort by price ascending, open the cheapest, and report its frame size.")

        # ---- 48. Saved-search creation with explicit price range
        emit(tasks, "Log in as carla.m@test.com, search apartments in east bay between $2000 and $2400 with the 'has image' filter on, and save the search.")

        # ---- 49. Site footer / help routes
        emit(tasks, "From the listing detail page, find the link to abuse reporting and follow it to the report form.")
        emit(tasks, "From the homepage left sidebar, find a link that leads into the help/FAQ area and follow it.")

        # ---- 50. Photo wall (best-of) verification
        emit(tasks, "Open the best of craigslist archive and verify it shows at least one furniture listing among the first dozen entries.")

        # Now ensure we hit ≥1500
        # If short, add per-listing 'open and read body' tasks
        i = 0
        catalog = list(all_listings)
        while len(tasks) < 1600:
            L = catalog[i % len(catalog)]
            short = re.sub(r"\s+", " ", L.title).strip()[:80]
            emit(tasks, f"Open the posting titled '{short}' located in {L.neighborhood}, {L.area}, and report the first sentence of the posting body.")
            i += 1

    # write
    for t in tasks:
        print(json.dumps(t, ensure_ascii=False))


if __name__ == "__main__":
    main()
