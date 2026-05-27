"""Generate WebVoyager-style GUI tasks for the deepened compass mirror.

Pulls real seed data from instance/compass.db so every question has a real
answer in the DB, then writes tasks.jsonl with the original 18 tasks
preserved + ~1500 new GUI-anchored tasks.

Run with:
    python3 generate_tasks.py
"""
import json
import os
import sqlite3
import sys


WEB = "http://localhost:40015/"
UPSTREAM = "https://www.compass.com/"
WEB_NAME = "Compass"


def _id(slug, n):
    return f"Compass--gui_{slug}_{n:03d}"


def task(slug, n, ques):
    return {
        "web_name": WEB_NAME,
        "id": _id(slug, n),
        "ques": ques,
        "web": WEB,
        "upstream_url": UPSTREAM,
    }


def city_state_slug(city, state):
    return f"{city.lower().replace(' ', '-')}-{state.lower()}"


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    db = sqlite3.connect(os.path.join(here, "instance", "compass.db"))
    db.row_factory = sqlite3.Row

    # ─── Preserve original tasks ──────────────────────────────────────────────
    base_path = os.path.join(here, "tasks.jsonl")
    preserved = []
    if os.path.exists(base_path):
        for line in open(base_path):
            line = line.strip()
            if not line:
                continue
            d = json.loads(line)
            if not d.get("id", "").startswith("Compass--gui_"):
                preserved.append(d)

    all_tasks = list(preserved)

    # ─── Reference rows ───────────────────────────────────────────────────────
    listings = db.execute(
        "SELECT id, slug, address, city, state, zip, price, status, beds, "
        "baths_full, baths_half, sqft, year_built, property_type, neighborhood, "
        "is_open_house, open_house_date, is_compass_exclusive, is_luxury, "
        "is_new, has_pool, has_garage, has_doorman, has_waterfront, mls_number, "
        "days_on_compass, hero_image, agent_id "
        "FROM listings ORDER BY id"
    ).fetchall()
    agents = db.execute(
        "SELECT id, slug, name, title, city, state, transactions_count, "
        "sales_volume_usd, years_experience, is_top_agent "
        "FROM agents ORDER BY id"
    ).fetchall()
    cities = db.execute("SELECT * FROM cities ORDER BY slug").fetchall()
    neighborhoods = db.execute("SELECT * FROM neighborhoods ORDER BY slug").fetchall()
    schools = db.execute("SELECT * FROM schools ORDER BY slug").fetchall()
    offices = db.execute("SELECT * FROM offices ORDER BY slug").fetchall()
    teams = db.execute("SELECT * FROM teams ORDER BY slug").fetchall()
    sold = db.execute("SELECT * FROM sold_listings ORDER BY slug").fetchall()
    market = db.execute("SELECT * FROM market_reports ORDER BY city_slug, month").fetchall()
    posts = db.execute("SELECT * FROM blog_posts ORDER BY slug").fetchall()

    cities_with_listings = sorted({(L["city"], L["state"]) for L in listings})

    def head(seq, n=10):
        return list(seq)[:n]

    # ─── 1. Listing detail tasks (photos / floor-plan / video / etc.) ─────────
    fam = "listing_detail"
    sample_listings = head(listings, 80)
    n = 1
    for L in sample_listings:
        addr = L["address"]
        city = L["city"]
        all_tasks.append(task(fam, n, f"Open the listing at {addr} in {city}. Report its asking price and the property type."))
        n += 1
        all_tasks.append(task(fam, n, f"Open the listing page for {addr} in {city}. Report the MLS number shown in the Property details section."))
        n += 1
        all_tasks.append(task(fam, n, f"Open the listing for {addr} in {city}. Report the number of bedrooms and full bathrooms."))
        n += 1
        all_tasks.append(task(fam, n, f"Find {addr} in {city} on Compass. Report the listing agent's name."))
        n += 1
        all_tasks.append(task(fam, n, f"Open the listing at {addr} in {city}. Report the year built and the listed days-on-Compass count."))
        n += 1

    # ─── 2. Listing photo / floor / video / walkscore / etc. (deep dives) ─────
    fam = "listing_deepdive"
    n = 1
    for L in head(sample_listings, 60):
        addr = L["address"]; city = L["city"]; slug = L["slug"]
        all_tasks.append(task(fam, n, f"Open the photos page for the listing at {addr} in {city} and report how many photos are shown in total."))
        n += 1
        all_tasks.append(task(fam, n, f"Open the floor plan page for {addr} in {city} and report the total square footage shown."))
        n += 1
        all_tasks.append(task(fam, n, f"Open the video tour page for {addr} in {city} and report the listing agent shown on the page."))
        n += 1
        all_tasks.append(task(fam, n, f"Open the price history page for {addr} in {city}. Report the date of the most recent 'Listed' event."))
        n += 1
        all_tasks.append(task(fam, n, f"On the listing at {addr} in {city}, open the Walk Score page and report the Walk Score number shown."))
        n += 1
        all_tasks.append(task(fam, n, f"Open the schools page for the listing at {addr} in {city} and report the name of the assigned school (the one marked 'Assigned')."))
        n += 1
        all_tasks.append(task(fam, n, f"Open the neighborhood page for the listing at {addr} in {city} and report the neighborhood name shown."))
        n += 1

    # ─── 3. Price/Bedroom filter tasks ────────────────────────────────────────
    fam = "search_filter"
    n = 1
    pq = [
        ("price_max=1500000", "under $1,500,000"),
        ("price_max=2000000", "under $2,000,000"),
        ("price_max=3000000&beds=3", "under $3M with 3+ bedrooms"),
        ("price_min=5000000", "$5,000,000 and up"),
        ("price_max=1000000&beds=2", "under $1M with 2+ bedrooms"),
        ("price_min=2000000&price_max=4000000", "between $2M and $4M"),
    ]
    for (city, state) in cities_with_listings:
        cs = city_state_slug(city, state)
        for q, label in pq:
            all_tasks.append(task(fam, n, f"On Compass, open the for-sale page for {city}, {state} and apply filters for homes {label}. Report how many listings match."))
            n += 1

    # ─── 4. Property type filter ─────────────────────────────────────────────
    fam = "property_type"
    n = 1
    for (city, state) in cities_with_listings:
        for pt in ["Condo", "Co-op", "Single Family", "Townhouse"]:
            all_tasks.append(task(fam, n, f"Browse {city}, {state} homes for sale and filter to {pt} only. Report how many {pt} listings are shown."))
            n += 1
        all_tasks.append(task(fam, n, f"Browse {city}, {state} for-sale listings and apply the 'New' filter. Report how many new listings are shown."))
        n += 1
        all_tasks.append(task(fam, n, f"Browse {city}, {state} for-sale listings and apply the 'Compass Exclusive' filter. Report how many results are shown."))
        n += 1

    # ─── 5. Sorting tasks ─────────────────────────────────────────────────────
    fam = "sort"
    n = 1
    for (city, state) in cities_with_listings:
        for s_key, label in [
            ("price_asc", "Price low to high"),
            ("price_desc", "Price high to low"),
            ("newest", "Newest"),
            ("sqft_desc", "Largest sq ft first"),
            ("beds_desc", "Most bedrooms first"),
            ("ppsf_asc", "Lowest price per sq ft first"),
        ]:
            all_tasks.append(task(fam, n, f"Browse {city}, {state} for-sale listings and sort by '{label}'. Report the address of the first listing."))
            n += 1

    # ─── 6. Agent profile tasks ───────────────────────────────────────────────
    fam = "agent_profile"
    n = 1
    for A in head(agents, 50):
        all_tasks.append(task(fam, n, f"Open the Compass agent directory and find {A['name']}. Report the agent's number of transactions and total sales volume."))
        n += 1
        all_tasks.append(task(fam, n, f"Open {A['name']}'s Compass agent profile. Report the agent's license number."))
        n += 1
        all_tasks.append(task(fam, n, f"Open the Reviews page for Compass agent {A['name']}. Report the average rating shown."))
        n += 1
        all_tasks.append(task(fam, n, f"Open the Awards page for Compass agent {A['name']} and report the most recent year of any award shown."))
        n += 1
        all_tasks.append(task(fam, n, f"Open the Sold listings page for Compass agent {A['name']}. Report how many closed transactions are listed."))
        n += 1

    # ─── 7. Agent directory filter ────────────────────────────────────────────
    fam = "agent_directory"
    n = 1
    for (city, state) in cities_with_listings:
        all_tasks.append(task(fam, n, f"Open the Compass agent directory and filter to agents in {city}. Report how many agents are listed."))
        n += 1
        all_tasks.append(task(fam, n, f"Open the Compass agent directory, filter to agents in {city}, and report the name of the agent with the highest total sales volume."))
        n += 1
        all_tasks.append(task(fam, n, f"Open the Compass agent directory, filter to agents in {city}, and report the name of the agent with the most years of experience."))
        n += 1

    # ─── 8. Open houses ───────────────────────────────────────────────────────
    fam = "open_houses"
    n = 1
    for (city, state) in cities_with_listings:
        all_tasks.append(task(fam, n, f"Visit the Open Houses page, filter to {city}, and report how many open houses are scheduled."))
        n += 1
        all_tasks.append(task(fam, n, f"Visit the Open Houses page, filter to {city}, and report the address of the first open house listed."))
        n += 1
        all_tasks.append(task(fam, n, f"Visit the Open Houses page, filter to {city}, and report the earliest open-house date shown."))
        n += 1

    # ─── 9. Neighborhoods ─────────────────────────────────────────────────────
    fam = "neighborhood"
    n = 1
    for N in head(neighborhoods, 30):
        nslug = N["slug"]
        cs = city_state_slug(N["city"], N["state"])
        all_tasks.append(task(fam, n, f"Open the {N['name']} neighborhood guide in {N['city']} on Compass. Report the median sale price shown."))
        n += 1
        all_tasks.append(task(fam, n, f"Open the {N['name']} neighborhood guide. Report the Walk Score and Transit Score shown."))
        n += 1
        all_tasks.append(task(fam, n, f"Open the {N['name']} neighborhood guide in {N['city']}. Report the median household income shown."))
        n += 1
        all_tasks.append(task(fam, n, f"Open the {N['name']} neighborhood guide and report the population shown."))
        n += 1

    fam = "neighborhood_index"
    n = 1
    for (city, _state) in cities_with_listings:
        all_tasks.append(task(fam, n, f"Browse Compass neighborhood guides and filter to {city}. Report how many neighborhoods are listed."))
        n += 1

    # ─── 10. Sold homes ───────────────────────────────────────────────────────
    fam = "sold"
    n = 1
    for (city, state) in cities_with_listings:
        cs = city_state_slug(city, state)
        all_tasks.append(task(fam, n, f"Open Compass Recently Sold homes for {city}, {state}. Report how many sold homes are listed."))
        n += 1
        all_tasks.append(task(fam, n, f"Open Compass Recently Sold homes for {city}, {state}. Report the most recent sold date shown."))
        n += 1
        all_tasks.append(task(fam, n, f"On Compass Recently Sold homes for {city}, {state}, report the highest sold price in the list."))
        n += 1

    fam = "sold_detail"
    n = 1
    for S in head(sold, 40):
        all_tasks.append(task(fam, n, f"Open the sold-home detail page for {S['address']} in {S['city']}. Report the sold price and sold date."))
        n += 1
        all_tasks.append(task(fam, n, f"Open the sold-home detail page for {S['address']} in {S['city']}. Report the days-on-market shown."))
        n += 1

    # ─── 11. Market reports ───────────────────────────────────────────────────
    fam = "market_report"
    n = 1
    for (city, state) in cities_with_listings:
        cs = city_state_slug(city, state)
        all_tasks.append(task(fam, n, f"Open the Compass market report for {city}, {state}. Report the latest median sale price shown."))
        n += 1
        all_tasks.append(task(fam, n, f"On the Compass market report for {city}, {state}, report the latest median days-on-market and sale-to-list ratio."))
        n += 1
        all_tasks.append(task(fam, n, f"On the Compass market report for {city}, {state}, report the YoY price-change percentage in the latest month."))
        n += 1
        all_tasks.append(task(fam, n, f"On the Compass market report for {city}, {state}, report the inventory and new-listings counts for the latest month."))
        n += 1

    # ─── 12. Teams & Offices ──────────────────────────────────────────────────
    fam = "teams"
    n = 1
    for T in teams:
        all_tasks.append(task(fam, n, f"Open the Compass Teams directory and find {T['name']}. Report the team's city and total transaction count."))
        n += 1
        all_tasks.append(task(fam, n, f"Open the team page for {T['name']} on Compass. Report how many members are on the team."))
        n += 1
        all_tasks.append(task(fam, n, f"Open the team page for {T['name']} on Compass. Report the team lead's name."))
        n += 1

    fam = "offices"
    n = 1
    for O in offices:
        all_tasks.append(task(fam, n, f"Open the Compass Offices directory. Report the address and phone number for the {O['name']} office."))
        n += 1
        all_tasks.append(task(fam, n, f"Open the office detail page for {O['name']}. Report the office director's name and active agent count."))
        n += 1

    # ─── 13. Buy/Sell hubs ────────────────────────────────────────────────────
    fam = "buy_hub"
    n = 1
    for (city, state) in cities_with_listings:
        cs = city_state_slug(city, state)
        all_tasks.append(task(fam, n, f"Open the Compass buy hub for {city}, {state}. Report the total number of active listings shown."))
        n += 1

    fam = "sell_hub"
    n = 1
    sell_qs = [
        "Open the Compass selling resources page. Report the three resource options shown in the main grid.",
        "On the Compass sell hub, list the three reasons given for selling with Compass.",
        "On the Compass home valuation form (sell evaluation), report the move-timeline options available in the dropdown.",
        "Open the Compass CMA request form. Report the form fields shown.",
        "On the Compass sell hub, identify which resource has a '1-business-day response' tag.",
    ]
    for q in sell_qs:
        all_tasks.append(task(fam, n, q))
        n += 1

    # ─── 14. Blog / editorial ─────────────────────────────────────────────────
    fam = "blog"
    n = 1
    for P in head(posts, 40):
        all_tasks.append(task(fam, n, f"Open the Compass Edit blog post titled '{P['title']}'. Report the author and the read-time in minutes."))
        n += 1
        all_tasks.append(task(fam, n, f"Open the blog post '{P['title']}' on Compass. Report which category the post is filed under."))
        n += 1

    fam = "blog_index"
    n = 1
    blog_cats = ["Market Insights", "Buying", "Selling", "Living", "Luxury",
                 "Architecture & Design"]
    for c in blog_cats:
        all_tasks.append(task(fam, n, f"Open the Compass Edit blog and filter to the '{c}' category. Report how many posts are listed."))
        n += 1
        all_tasks.append(task(fam, n, f"Open the Compass Edit blog and filter to the '{c}' category. Report the title of the most recent post."))
        n += 1

    # ─── 15. Calculators ──────────────────────────────────────────────────────
    fam = "calculator"
    n = 1
    calc_qs = [
        "Open the Compass mortgage calculator. Enter a $850,000 home price with $170,000 down at 6.5% for 30 years and no taxes/insurance/HOA. Report the principal-and-interest monthly payment shown.",
        "Open the Compass mortgage calculator. Enter $1,200,000 home price, $240,000 down, 6.75%, 30 years, $9,600 annual tax, $1,800 annual insurance, $0 HOA. Report the total monthly payment shown.",
        "Open the Compass mortgage calculator with $600,000 home price, $120,000 down, 6.25%, 30 years. Report the monthly principal-and-interest.",
        "Open the Compass affordability calculator with $200,000 income, $800 monthly debts, $50,000 down, and 6.5% rate. Report the maximum home price shown.",
        "Open the Compass affordability calculator with $150,000 income, $500 monthly debts, $30,000 down, and 7% rate. Report the maximum monthly payment.",
        "Open the Compass closing-cost calculator and report the typical closing-cost percentage range shown.",
        "Open the Compass mortgage calculator and report the term-year options shown in the Term dropdown.",
        "Open the Compass mortgage calculator and report the default interest-rate value shown when the page first loads.",
    ]
    for q in calc_qs:
        all_tasks.append(task(fam, n, q))
        n += 1

    # ─── 16. Account flows (logged-in tasks) ─────────────────────────────────
    fam = "account"
    n = 1
    USERS = [
        ("alice.j@test.com",  "Alice Johnson",  "San Francisco"),
        ("bob.smith@test.com", "Bob Smith",     "New York"),
        ("carol.lee@test.com", "Carol Lee",     "Miami"),
        ("david.kim@test.com", "David Kim",     "Austin"),
    ]
    for email, name, city in USERS:
        all_tasks.append(task(fam, n, f"Log in as {email} (password webharbor123). Open the My Notes page and report how many notes are currently saved."))
        n += 1
        all_tasks.append(task(fam, n, f"Log in as {email} (password webharbor123). Open the My Offers page and report how many offers you have submitted."))
        n += 1
        all_tasks.append(task(fam, n, f"Log in as {email} (password webharbor123). Open My Notes and add a new note with the body 'Follow up next week.' Confirm it appears in the list."))
        n += 1
        all_tasks.append(task(fam, n, f"Log in as {email} (password webharbor123). Open the mortgage calculator, run it with home price $900,000, down $180,000, rate 6.5%, 30 years, then click the 'Save this scenario' option with label 'Q3 plan' and submit. Confirm the success message."))
        n += 1
        all_tasks.append(task(fam, n, f"Log in as {email} (password webharbor123). Open Saved Homes and report the number of homes saved."))
        n += 1
        all_tasks.append(task(fam, n, f"Log in as {email} (password webharbor123). Open Saved Searches and report the name of the saved search shown."))
        n += 1
        all_tasks.append(task(fam, n, f"Log in as {email} (password webharbor123). Open the Inquiries page and report how many inquiries you have sent."))
        n += 1
        all_tasks.append(task(fam, n, f"Log in as {email} (password webharbor123). Open Tours and report the date of your earliest tour."))
        n += 1
        all_tasks.append(task(fam, n, f"Log in as {email} (password webharbor123). Open My Collections and report the share token for the first collection."))
        n += 1

    # ─── 17. POST/submit flows that produce a verifiable change ──────────────
    fam = "submit"
    n = 1
    sample_listing_for_post = listings[0]
    addr0 = sample_listing_for_post["address"]
    city0 = sample_listing_for_post["city"]
    submit_qs = [
        f"Subscribe to the Compass newsletter with email 'subscriber.test@example.com' and city of interest 'New York'. Confirm the success message.",
        f"Log in as alice.j@test.com (password webharbor123). Open the listing at {addr0} in {city0} and submit an offer of $1,000,000 with $20,000 earnest money. Confirm the success message and that the offer appears on the My Offers page.",
        f"Log in as bob.smith@test.com (password webharbor123). Open any New York neighborhood guide and subscribe to weekly alerts with your account email. Confirm the success flash message.",
        f"Log in as carol.lee@test.com (password webharbor123). Open the Miami market report and subscribe to receive it monthly using your account email. Confirm the success flash message.",
        f"Log in as david.kim@test.com (password webharbor123). Open a listing in Austin and submit a share with the recipient email 'friend@example.com'. Confirm the success message.",
        f"Open the Compass sell evaluation form. Submit a 1,800 sq ft 3BR/2BA home at 123 Main St, Austin, TX with a 3-6mo timeline. Confirm the estimated value is shown.",
        f"Open the Compass CMA request form. Submit a request for 88 Stadium Drive, Boston, MA, with name 'Test Buyer', email 'test@example.com', and a note 'recently renovated kitchen'. Confirm the success message.",
        f"Log in as alice.j@test.com (password webharbor123). Open the Compass agent reviews page for the lowest-ID agent in San Francisco and submit a 5-star review titled 'Highly recommended' with body 'Professional and patient.' Confirm the review appears on the page.",
        f"Log in as bob.smith@test.com (password webharbor123). Open one of your Collections and invite the email 'co-buyer@example.com'. Confirm the email now appears in the invited list.",
        f"Open the Compass affordability calculator with $250,000 income, $1,000 monthly debts, $80,000 down, 6.5% rate, then check 'Save this result' and submit. Confirm the success message states a max home price.",
    ]
    for q in submit_qs:
        all_tasks.append(task(fam, n, q))
        n += 1

    # ─── 18. Comparison / multi-listing analysis ──────────────────────────────
    fam = "compare"
    n = 1
    for (city, state) in cities_with_listings:
        in_city = [L for L in listings if L["city"] == city and L["status"] == "for-sale"]
        if len(in_city) >= 3:
            top3 = sorted(in_city, key=lambda L: -(L["price"] or 0))[:3]
            adrs = ", ".join(L["address"] for L in top3)
            all_tasks.append(task(fam, n, f"On Compass, compare the three most expensive for-sale listings in {city}, {state} ({adrs}). Report which has the lowest price per square foot."))
            n += 1
            bot3 = sorted(in_city, key=lambda L: (L["price"] or 0))[:3]
            adrs = ", ".join(L["address"] for L in bot3)
            all_tasks.append(task(fam, n, f"On Compass, compare the three cheapest for-sale listings in {city}, {state} ({adrs}). Report which has the most bedrooms."))
            n += 1

    # ─── 19. Misc: search, register, password, navigation ────────────────────
    fam = "misc"
    n = 1
    misc_qs = [
        "Open the Compass homepage. List the six top-nav links shown in the header.",
        "Open the Compass homepage. Report the heading of the first Featured listings section shown.",
        "Open the Compass /about page. Report the page heading.",
        "Open the Compass /help page. Report the page heading.",
        "Open the Compass /careers page. Report the page heading.",
        "Open the Compass /concierge page. Report the page heading.",
        "Open the Compass /private-exclusives page. Report the page heading.",
        "Register a new Compass account with name 'Riley Garcia', email 'riley.garcia+gui@example.com', and password 'newpass123'. Confirm you are taken to your account overview.",
        "Open Compass /register and try submitting with mismatched passwords. Report the error message shown.",
        "Open Compass /login and try logging in with email 'doesnotexist@test.com' and any password. Report the error message shown.",
        "Open the Compass search page with query 'Brooklyn waterfront'. Report how many results are shown.",
        "Open the Compass /luxury page. Report how many listings are shown.",
        "Open the Compass /new-listings page. Report how many listings are shown.",
        "Open the Compass /homes-for-rent page. Report how many cities are listed.",
        "Open the Compass /homes-for-sale page. Report how many cities are listed.",
    ]
    for q in misc_qs:
        all_tasks.append(task(fam, n, q))
        n += 1

    # ─── 20. Photo/Image-anchored tasks ──────────────────────────────────────
    fam = "photos"
    n = 1
    for L in head(sample_listings, 60):
        all_tasks.append(task(fam, n, f"Open the listing at {L['address']} in {L['city']} and click into the full photo gallery. Report the alt-text of photo 2 of the gallery."))
        n += 1

    # ─── Renumber sequentially within each family group prefix ────────────────
    # (Already done by counter per family above.)

    # ─── Write out ────────────────────────────────────────────────────────────
    out_path = base_path
    with open(out_path, "w") as f:
        for t in all_tasks:
            f.write(json.dumps(t) + "\n")
    print(f"Wrote {len(all_tasks)} tasks ({len(preserved)} preserved + {len(all_tasks) - len(preserved)} generated)")


if __name__ == "__main__":
    main()
