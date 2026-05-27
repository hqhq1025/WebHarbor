"""Seeders for the deepened compass mirror — runs idempotently after
seed_database / seed_benchmark_users.

Adds: Neighborhoods, Schools (+ assignments per listing), Offices, Teams,
Market Reports, Blog Posts, Price History per listing, Agent Reviews,
Agent Awards, Sold Listings, Notes / Offers / Mortgage scenarios for
benchmark users, newsletter signups.

All randomness is deterministic via the same _h() hash used in seed_data.py
so reseed produces byte-identical DBs.
"""
import hashlib
import json
import re
from datetime import datetime, timedelta


# ─── Helpers (mirror seed_data.py) ────────────────────────────────────────────


def _h(*parts) -> int:
    return int(hashlib.md5("|".join(map(str, parts)).encode()).hexdigest(), 16)


def _slug(s: str) -> str:
    s = re.sub(r"[^A-Za-z0-9]+", "-", (s or "").strip().lower()).strip("-")
    return s or "x"


def _city_slug(name, state):
    return f"{_slug(name)}-{state.lower()}"


REFERENCE_NOW = datetime(2026, 5, 27, 12, 0, 0)


# ─── Neighborhoods ────────────────────────────────────────────────────────────


# Curated neighborhood roster — keyed by (city, state). These are real-world
# Compass.com geographies; we attach them only to cities where listings carry
# matching neighborhood strings, so a listing's "neighborhood" field can be
# clicked through to a full guide.
NEIGHBORHOOD_ROSTER = {
    ("New York", "NY"): [
        ("Chelsea", "Gallery district between the High Line and Hudson Yards, packed with restaurants and design showrooms."),
        ("West Village", "Tree-lined townhouse streets, intimate bistros, and one of Manhattan's most coveted residential pockets."),
        ("Upper East Side", "Pre-war co-ops, Central Park frontage, and the city's densest concentration of museums."),
        ("Brooklyn Heights", "Quiet, leafy, with the city's most famous promenade and a deep stock of historic townhouses."),
        ("Williamsburg", "Industrial-loft conversions, waterfront parks, and one of NYC's most consistently busy nightlife strips."),
        ("Prospect Heights", "Brownstones a short walk from Prospect Park, the Brooklyn Museum, and Vanderbilt Avenue dining."),
        ("Cobble Hill", "Low-rise brownstone blocks, neighborhood bookstores, and a quieter pace just south of downtown Brooklyn."),
    ],
    ("Los Angeles", "CA"): [
        ("Beverly Hills", "Trophy estates, the city's most exclusive shopping, and tree-lined flats north of Sunset."),
        ("Venice", "Walk Streets, canal homes, and an architecturally adventurous beachside community."),
        ("Silver Lake", "Hillside midcentury homes, an active reservoir loop, and a tight indie restaurant scene."),
        ("Brentwood", "Country-club living, refined retail along San Vicente, and easy 405 access."),
        ("Hollywood Hills", "Iconic view homes overlooking the basin, with architectural pedigree from Lautner to Neutra."),
        ("Pacific Palisades", "Family-oriented coastal village with bluff-top homes and easy Pacific Coast Highway access."),
    ],
    ("Miami", "FL"): [
        ("Brickell", "Glass-towered urban core with waterfront condos and the city's deepest restaurant cluster."),
        ("Coconut Grove", "Sailing village south of downtown, with old-growth canopy and historic estates."),
        ("Coral Gables", "Mediterranean Revival mansions, the Venetian Pool, and one of the country's most planned cities."),
        ("Miami Beach", "Art Deco, ocean-block condos, and an unmatched 24/7 culture."),
        ("Edgewater", "Bayfront mid-rises and parks on the doorstep of the Design District."),
        ("Wynwood", "Murals, breweries, and a converted-warehouse residential scene gathering pace."),
    ],
    ("San Francisco", "CA"): [
        ("Pacific Heights", "Hilltop Victorians with iconic Bay views and the city's most expensive single-family stock."),
        ("Noe Valley", "Family-friendly Victorians, brunch on 24th Street, and protection from the fog."),
        ("Russian Hill", "Steep streets, Lombard's switchbacks, and intimate condo buildings with panoramic outlook."),
        ("Marina District", "Flat blocks of stucco homes near Crissy Field and the Bay."),
        ("Mission District", "Latin culture, dense restaurant strip, and a wave of new mid-rises near BART."),
    ],
    ("Boston", "MA"): [
        ("Back Bay", "Brownstones lining Commonwealth Avenue, with Newbury Street shopping and the Public Garden at the foot of the neighborhood."),
        ("Beacon Hill", "Gas-lit cobblestone lanes, Federal-era row houses, and one of the country's oldest residential neighborhoods."),
        ("South End", "Bow-front Victorians, restaurant rows on Tremont, and a deep gallery and design district."),
        ("Cambridge", "Harvard Square, MIT campus, and a continuous belt of bookstores and labs across the river."),
    ],
    ("Austin", "TX"): [
        ("Tarrytown", "Wooded lots near the Colorado River and Mount Bonnell, with mid-century ranches and modern rebuilds."),
        ("Travis Heights", "South Austin hillside with historic bungalows and downtown skyline views."),
        ("Hyde Park", "Walkable craftsman bungalows north of UT, with Quack's and Asti anchoring the cafe scene."),
        ("Westlake Hills", "Hill-country estates, top-rated schools, and a short hop into downtown."),
    ],
    ("Seattle", "WA"): [
        ("Capitol Hill", "Dense restaurant and music scene, Volunteer Park, and a mix of craftsman homes and mid-rise condos."),
        ("Queen Anne", "Hilltop Edwardians, downtown views, and a tight commercial node on Queen Anne Ave."),
        ("Madison Park", "Lakefront single-family homes, swimming beaches, and a beloved village."),
    ],
    ("Denver", "CO"): [
        ("Cherry Creek", "Boutique shopping, modern townhomes, and one of the metro's most-walked retail strips."),
        ("Wash Park", "Bungalow streets surrounding a 165-acre park with a running loop and lake."),
        ("LoHi", "Modern townhomes, brewery row, and skyline-facing rooftops on the north side of the South Platte."),
    ],
    ("Aspen", "CO"): [
        ("Red Mountain", "Aspen's trophy hillside with private-club estates and panoramic ski-area views."),
        ("West End", "Walkable historic neighborhood of Victorians and modern rebuilds, blocks from downtown."),
    ],
    ("Washington", "DC"): [
        ("Georgetown", "Federal row houses, cobblestone lanes, and Potomac frontage."),
        ("Dupont Circle", "Embassy row, sidewalk cafes, and dense mid-rise condos."),
        ("Capitol Hill", "Hill-east row houses with Eastern Market at the heart of the neighborhood."),
    ],
    ("Chicago", "IL"): [
        ("Lincoln Park", "Greystones, a 1,200-acre lakefront park, and DePaul's college-town feel."),
        ("Lakeview", "Wrigleyville's restaurants and bars, with vintage condos in tree-lined side streets."),
        ("Gold Coast", "Historic mansions, Lake Shore Drive frontage, and high-floor luxury towers."),
    ],
}


NBHD_HERO_DEFAULT = "/static/images/hero-compass.svg"


def seed_neighborhoods():
    from app import Listing, Neighborhood, db
    if Neighborhood.query.count() > 0:
        return

    # Only attach neighborhoods that match an actual Listing.neighborhood string.
    listing_nbhds = {
        (L.city, L.state, L.neighborhood)
        for L in Listing.query.all() if L.neighborhood
    }

    for (city, state), roster in NEIGHBORHOOD_ROSTER.items():
        for nm, blurb in roster:
            # Allow neighborhoods that don't yet appear in listings — they still
            # render fine as standalone guides. But prefer the ones that do.
            slug = _slug(f"{nm}-{city}-{state}")
            h = _h("nbhd", slug)
            walk = 65 + (h % 35)            # 65-99
            transit = 40 + ((h >> 2) % 60)  # 40-99
            bike = 50 + ((h >> 4) % 50)
            # Median price loosely calibrated to the city.
            base_price = {
                "New York": 1_400_000, "Los Angeles": 1_300_000,
                "Miami": 700_000,      "San Francisco": 1_500_000,
                "Boston": 950_000,     "Austin": 700_000,
                "Seattle": 900_000,    "Denver": 700_000,
                "Aspen": 5_800_000,    "Washington": 950_000,
                "Chicago": 600_000,
            }.get(city, 600_000)
            median = base_price + (h % 600_000)
            median = (median // 5_000) * 5_000
            rent = max(1500, median // 350)
            rent = (rent // 50) * 50
            pop = 8_000 + (h % 90_000)
            age = 28 + (h % 22)
            income = 70_000 + ((h >> 1) % 200_000)
            income = (income // 1000) * 1000
            db.session.add(Neighborhood(
                slug=slug, name=nm, city=city, state=state,
                blurb=blurb,
                walk_score=walk, transit_score=transit, bike_score=bike,
                median_sale_price=median, median_rent=rent,
                population=pop, median_age=age,
                median_household_income=income,
                hero_image=NBHD_HERO_DEFAULT,
                dining_blurb=("Standout dining ranges from neighborhood bistros "
                              "to special-occasion tables, with a strong cafe and "
                              "bakery culture for everyday mornings."),
                parks_blurb=("Green space is woven through the neighborhood, "
                             "with multiple parks and playgrounds within an "
                             "easy walk of most homes."),
                transit_blurb=("Transit access is solid — multiple rail or rapid-bus "
                               "lines connect to the city's core in under 25 minutes."),
            ))
    db.session.commit()


# ─── Schools ──────────────────────────────────────────────────────────────────


SCHOOL_NAME_POOLS = {
    "elementary": ["Jefferson Elementary", "Roosevelt Elementary", "Lincoln Elementary",
                   "Washington Elementary", "Adams Elementary", "Madison Elementary",
                   "Hamilton Elementary", "Franklin Elementary", "Wilson Elementary",
                   "Kennedy Elementary", "Greenfield Elementary", "Riverside Elementary",
                   "Oakwood Elementary", "Maplewood Elementary", "Brookside Elementary"],
    "middle":     ["Jefferson Middle School", "Roosevelt Middle School",
                   "Madison Middle School", "Adams Middle School",
                   "Franklin Middle School", "Hamilton Middle School",
                   "Greenfield Middle School", "Oakwood Middle School"],
    "high":       ["Lincoln High School", "Roosevelt High School",
                   "Jefferson High School", "Madison High School",
                   "Washington High School", "Adams High School",
                   "Franklin High School", "Greenfield High School"],
    "private":    ["St. Catherine's Day School", "Holy Family Academy",
                   "The Compass Academy", "Riverdale Country School",
                   "Oakwood Friends School", "The Hewitt School",
                   "Browning Preparatory", "Holton-Hayes Academy"],
}


def seed_schools():
    from app import City, School, db
    if School.query.count() > 0:
        return

    # 6 schools per listing-bearing city: 3 elem, 1 middle, 1 high, 1 private.
    cities = (City.query.order_by(City.slug).all())
    for ci, c in enumerate(cities):
        plan = [
            ("elementary", "K", "5"),
            ("elementary", "K", "5"),
            ("elementary", "K", "5"),
            ("middle",     "6", "8"),
            ("high",       "9", "12"),
            ("private",    "K", "12"),
        ]
        for j, (pool, lo, hi) in enumerate(plan):
            names = SCHOOL_NAME_POOLS[pool]
            base_name = names[_h("sn", c.slug, j) % len(names)]
            # Always suffix with the city to guarantee global slug uniqueness.
            parts = base_name.split(" ", 1)
            name = f"{parts[0]} {c.name} {parts[1] if len(parts) > 1 else ''}".strip()
            slug = _slug(f"{name}-{c.slug}-{j}")
            h = _h("school", slug)
            rating = 4 + (h % 7)            # 4-10
            if pool == "private":
                rating = 7 + (h % 4)        # 7-10
            students = 200 + (h % 1800)
            ratio_a = 12 + (h % 12)
            ratio_b = 1
            addr = f"{100 + (h % 9900)} {['Oak','Maple','Pine','Elm','Cedar'][h % 5]} {['St','Ave','Rd','Blvd'][(h>>4) % 4]}"
            db.session.add(School(
                slug=slug, name=name, city=c.name, state=c.state,
                school_type="Private" if pool == "private" else "Public",
                grade_low=lo, grade_high=hi, rating=rating,
                students=students,
                student_teacher_ratio=f"{ratio_a}:{ratio_b}",
                address=f"{addr}, {c.name}, {c.state}",
            ))
    db.session.commit()


def seed_listing_schools():
    from app import Listing, ListingSchool, School, db
    if ListingSchool.query.count() > 0:
        return
    # Each listing gets up to 4 nearby schools from its city, with the closest
    # marked as 'assigned'.
    for L in Listing.query.order_by(Listing.id).all():
        nearby = (School.query.filter_by(city=L.city, state=L.state)
                  .order_by(School.slug).all())
        if not nearby:
            continue
        for i, s in enumerate(nearby[:4]):
            h = _h("ls", L.id, s.id)
            dist = round(0.2 + (h % 35) / 10.0, 1)  # 0.2 - 3.6 mi
            db.session.add(ListingSchool(
                listing_id=L.id, school_id=s.id,
                distance_miles=dist,
                is_assigned=(i == 0),
            ))
    db.session.commit()


# ─── Offices ──────────────────────────────────────────────────────────────────


def seed_offices():
    from app import City, Office, Agent, db
    if Office.query.count() > 0:
        return
    cities = City.query.order_by(City.slug).all()
    for ci, c in enumerate(cities):
        h = _h("off", c.slug)
        name = f"Compass {c.name}"
        slug = _slug(f"compass-{c.slug}-office")
        addr = (f"{100 + (h % 999)} {['Park','Madison','Newbury','Main','Ocean'][h % 5]} "
                f"{['Ave','St','Blvd'][(h>>3) % 3]}, {c.name}, {c.state}")
        phone = f"({200 + (h % 700):03d}) 555-{1000 + (h % 9000):04d}"
        director_idx = h % 999
        director = (Agent.query.filter_by(city=c.name).order_by(Agent.id).first())
        director_name = director.name if director else "Compass"
        ac = Agent.query.filter_by(city=c.name).count()
        db.session.add(Office(
            slug=slug, name=name, city=c.name, state=c.state,
            address=addr, phone=phone,
            hours="Mon-Fri 9am-6pm · Sat 10am-4pm",
            director_name=director_name, agent_count=ac,
        ))
    db.session.commit()


# ─── Teams ────────────────────────────────────────────────────────────────────


TEAM_NAMES = [
    "The {last} Group", "{last} & Co. Real Estate", "The {last} Team",
    "{last} Partners", "{last} Residential", "{last} Collective",
]


def seed_teams():
    from app import Agent, Team, TeamMember, db
    if Team.query.count() > 0:
        return
    # 2 teams in each of the top markets; lead is the top-volume agent.
    TEAM_CITIES = [("New York", "NY"), ("Los Angeles", "CA"), ("Miami", "FL"),
                   ("San Francisco", "CA"), ("Boston", "MA"), ("Austin", "TX"),
                   ("Aspen", "CO"), ("Washington", "DC")]
    for ci, (city, state) in enumerate(TEAM_CITIES):
        agents = (Agent.query.filter_by(city=city, state=state)
                  .order_by(Agent.sales_volume_usd.desc()).all())
        if not agents:
            continue
        for ti in range(min(2, len(agents) // 2)):
            lead = agents[ti]
            last = lead.name.split()[-1]
            tn_idx = _h("team", city, ti) % len(TEAM_NAMES)
            tname = TEAM_NAMES[tn_idx].format(last=last)
            tslug = _slug(f"{tname}-{city}-{state}-{ti}")
            members = [lead]
            # Pull 2-3 more agents
            need = 2 + (_h("tn", city, ti) % 2)
            pool = [a for a in agents if a.id != lead.id]
            for j in range(min(need, len(pool))):
                idx = _h("tm", city, ti, j) % len(pool)
                if pool[idx] not in members:
                    members.append(pool[idx])
            vol = sum(m.sales_volume_usd for m in members)
            tx = sum(m.transactions_count for m in members)
            t = Team(
                slug=tslug, name=tname,
                city=city, state=state,
                bio=(f"{tname} brings together {len(members)} agents who close "
                     f"high-touch transactions across {city} — combining a deep "
                     "neighborhood bench with the resources of the Compass network."),
                lead_agent_id=lead.id,
                sales_volume_usd=vol,
                transactions_count=tx,
            )
            db.session.add(t)
            db.session.flush()
            roles = ["Team Lead"] + ["Senior Agent"] * 2 + ["Associate Agent"] * 4
            for k, m in enumerate(members):
                db.session.add(TeamMember(
                    team_id=t.id, agent_id=m.id,
                    role=roles[k] if k < len(roles) else "Associate Agent",
                ))
    db.session.commit()


# ─── Market reports ───────────────────────────────────────────────────────────


def seed_market_reports():
    from app import City, Listing, MarketReport, db
    if MarketReport.query.count() > 0:
        return
    # 12 months of reports per city with listings (Jun-2025 through May-2026).
    months = [(2025, m) for m in range(6, 13)] + [(2026, m) for m in range(1, 6)]
    cities_with_inventory = sorted({(L.city, L.state)
                                    for L in Listing.query.all()
                                    if L.city and L.state})
    for city, state in cities_with_inventory:
        cs = _city_slug(city, state)
        # Baseline by city
        base = {"New York": 1_400_000, "Los Angeles": 1_300_000,
                "Miami": 700_000, "San Francisco": 1_500_000,
                "Boston": 950_000, "Austin": 700_000,
                "Aspen": 5_800_000, "Seattle": 900_000,
                "Denver": 700_000, "Washington": 950_000,
                "Chicago": 600_000}.get(city, 700_000)
        for mi, (y, m) in enumerate(months):
            month_key = f"{y:04d}-{m:02d}"
            h = _h("mr", cs, month_key)
            # Light seasonal modulation
            season = 0.95 + 0.10 * ((m - 1) / 11.0)
            drift = 1.0 + (mi * 0.005)  # slow upward trend
            median = int(base * season * drift)
            median = (median // 5000) * 5000
            ppsf = int(median / (1500 + (h % 600)))
            sold = 50 + (h % 300)
            dom = 14 + (h % 80)
            ratio = round(0.96 + (h % 80) / 1000.0, 3)  # 0.96-1.04
            inv = 200 + (h % 800)
            new_l = 30 + (h % 150)
            yoy = round((((h >> 3) % 200) - 100) / 100.0 * 5.0, 1)  # -5 to +5
            db.session.add(MarketReport(
                city_slug=cs, city=city, state=state,
                month=month_key,
                median_sale_price=median,
                median_price_per_sqft=ppsf,
                homes_sold=sold,
                median_days_on_market=dom,
                sale_to_list_ratio=ratio,
                inventory=inv,
                new_listings=new_l,
                yoy_price_change_pct=yoy,
            ))
    db.session.commit()


# ─── Blog posts ───────────────────────────────────────────────────────────────


BLOG_CATEGORIES = ["Market Insights", "Buying", "Selling", "Living",
                   "Luxury", "Architecture & Design"]

BLOG_TEMPLATES = [
    ("How a {city} Buyer Wins in a Multiple-Offer Market",
     "Buying",
     "Five contingency tweaks, two timing moves, and the cover letter that doesn't sound like ChatGPT."),
    ("{city} Q4 Market Recap: Where Prices Held and Where They Slipped",
     "Market Insights",
     "Median prices, price per square foot, and days-on-market across {city}'s most-tracked neighborhoods."),
    ("The {city} Seller's Pre-Listing Checklist",
     "Selling",
     "What to spend on, what to skip, and the exact week to put your home on the market in {city}."),
    ("Behind the Door: A Modernist Renovation in {city}",
     "Architecture & Design",
     "Photographed and walked through with the architect, with a candid breakdown of the budget."),
    ("Should You Buy a Condo or a Townhouse in {city}?",
     "Buying",
     "Side-by-side on HOA fees, resale, customization rights, and how each holds up in a downturn."),
    ("How {city}'s Luxury Market Moved This Quarter",
     "Luxury",
     "Trophy sales, off-market activity, and the foreign-buyer slice across {city}."),
    ("Renting Then Buying in {city}: When the Math Tips",
     "Living",
     "We crunched 36 months of rent vs. buy across six neighborhoods in {city}."),
    ("A Compass Agent's Guide to {city} Schools",
     "Living",
     "Catchment-aware home shopping and the school-district questions every buyer should ask."),
]


def seed_blog_posts():
    from app import BlogPost, db
    if BlogPost.query.count() > 0:
        return
    # Reuse the major listing-bearing cities
    cities = ["New York", "Los Angeles", "Miami", "San Francisco", "Boston",
              "Austin", "Seattle", "Denver", "Aspen", "Washington", "Chicago"]
    AUTHORS = ["Compass Editorial", "Maria Castillo", "James Lee",
               "Priya Reddy", "Olivia Brennan", "Marcus Holloway"]
    seen_slugs = set()
    counter = 0
    base = datetime(2025, 8, 1, 9, 0, 0)
    for ci, city in enumerate(cities):
        for ti, (title_tpl, cat, excerpt_tpl) in enumerate(BLOG_TEMPLATES):
            title = title_tpl.format(city=city)
            excerpt = excerpt_tpl.format(city=city)
            slug = _slug(title)
            if slug in seen_slugs:
                continue
            seen_slugs.add(slug)
            h = _h("blog", slug)
            author = AUTHORS[h % len(AUTHORS)]
            published = base + timedelta(days=ci * 8 + ti * 3,
                                         hours=h % 12,
                                         minutes=(h >> 4) % 60)
            read = 3 + (h % 9)
            body_paras = [
                (f"{city}'s housing market in 2026 sits at the intersection of two competing "
                 "pressures. On one side, inventory has crept back up after a multi-year squeeze. "
                 "On the other, buyers who waited out higher rates are returning with more "
                 "negotiating tools than at any point in the recent cycle."),
                ("If you're navigating this moment as a buyer, three things matter: how "
                 "you sequence your search, where you draw the line on concessions, and "
                 "the depth of your pre-approval letter."),
                ("And for sellers, the cycle rewards preparation in a way it hasn't in years. "
                 "The homes hitting market with pre-inspections, polished staging, and a "
                 "well-priced first weekend continue to clear at or above asking."),
                ("The Compass team has compiled a free downloadable worksheet to walk you "
                 "through both sides of the trade — get in touch with your local agent for "
                 "a copy tailored to your zip code."),
            ]
            body = "\n\n".join(body_paras)
            db.session.add(BlogPost(
                slug=slug, title=title, category=cat,
                author=author, excerpt=excerpt, body=body,
                hero_image="/static/images/hero-compass.svg",
                published_at=published, read_minutes=read,
            ))
            counter += 1
    db.session.commit()


# ─── Price history ────────────────────────────────────────────────────────────


def seed_price_history():
    from app import Listing, PriceHistory, db
    if PriceHistory.query.count() > 0:
        return
    REF = datetime(2026, 5, 1)
    for L in Listing.query.order_by(Listing.id).all():
        # All listings: at least a "Listed" event.
        h = _h("ph", L.id)
        days_back = 7 + (h % 240)
        listed_date = (REF - timedelta(days=days_back)).date().isoformat()
        listed_price = L.price + (h % 50) * 1000
        # Round
        listed_price = (listed_price // 5000) * 5000
        events = [(listed_date, "Listed", listed_price)]
        # Maybe a price reduction
        if (h >> 2) % 3 == 0 and L.price > 0:
            cut_days = max(7, days_back // 2)
            cut_date = (REF - timedelta(days=cut_days)).date().isoformat()
            cut_price = max(L.price, listed_price - (50 + (h % 200)) * 1000)
            cut_price = (cut_price // 5000) * 5000
            if cut_price < listed_price:
                events.append((cut_date, "Price reduced", cut_price))
        # Sometimes Pending
        if L.is_pending:
            pen_date = (REF - timedelta(days=max(2, days_back // 4))).date().isoformat()
            events.append((pen_date, "Pending", L.price))
        # If the underlying listing has had earlier owner activity, fake a prior Sold
        if (h >> 4) % 4 == 0:
            old_yr = 2018 + (h % 6)
            old_price = max(50_000, L.price - (300 + (h % 800)) * 1000)
            old_price = (old_price // 5000) * 5000
            events.append((f"{old_yr}-{1 + (h % 12):02d}-15", "Sold", old_price))
        for d, et, p in sorted(events, key=lambda x: x[0], reverse=True):
            db.session.add(PriceHistory(
                listing_id=L.id, event_date=d, event_type=et, price=p,
            ))
    db.session.commit()


# ─── Agent reviews + awards ───────────────────────────────────────────────────


REVIEW_TITLES = [
    "Made buying our first home painless",
    "Knew our market block by block",
    "Honest and patient — won't rush you",
    "Sold above asking in 9 days",
    "Walked us through a tough negotiation",
    "Strong negotiator and great communicator",
    "Found us off-market gems",
    "Made selling feel manageable",
    "Truly responsive — answered every text within an hour",
    "Saved us six figures with a smart counteroffer",
]
REVIEW_BODIES = [
    ("We were nervous first-time buyers and felt fully supported through every step. "
     "She walked us through inspection reports, contract contingencies, and even "
     "negotiated a $20K credit for some plumbing work."),
    ("Knows the inventory and pricing better than anyone else we interviewed. "
     "Was upfront when a home was overpriced and saved us from a couple of bad fits."),
    ("Quietly excellent — never pushed us, returned our calls within minutes, "
     "and got us to the closing table on time despite a lender hiccup."),
    ("Listed our home on a Thursday, three offers by Sunday, accepted at 6% over "
     "ask. The pre-listing prep was the difference."),
    ("A calm, steady presence in a multiple-offer situation. We trusted his read "
     "on the seller's motivation and won without overpaying."),
    ("Found a place that wasn't even listed yet. We toured it the day she heard "
     "about it and were in contract by the weekend."),
]
AWARD_NAMES = [
    "Compass Top 250 Agents Nationwide",
    "RealTrends 'America's Best' Honoree",
    "Compass {city} Top Producer",
    "Five-Star Professional — Real Estate",
    "Compass Compass Concierge Champion",
    "Compass Sphere Award",
    "Compass {city} Rising Star",
]


def seed_agent_reviews_and_awards():
    from app import Agent, AgentAward, AgentReview, db
    if AgentReview.query.count() > 0:
        return
    REVIEWER_NAMES = ["Sam Patel", "Erin Wong", "Drew Singh", "Maya O'Connor",
                      "Hugo Martín", "Camille Beaumont", "Wes Chen",
                      "Yara Kassem", "Owen Lindgren", "Tessa Acharya",
                      "Quinn Larsen", "Ines Ferraro", "Bram Velasquez",
                      "Cleo Marchetti"]
    base = datetime(2024, 8, 1, 10, 0, 0)
    agents = Agent.query.order_by(Agent.id).all()
    for a in agents:
        # 3 reviews each
        for k in range(3):
            h = _h("ar", a.id, k)
            t = REVIEW_TITLES[h % len(REVIEW_TITLES)]
            b = REVIEW_BODIES[(h >> 3) % len(REVIEW_BODIES)]
            name = REVIEWER_NAMES[(h >> 5) % len(REVIEWER_NAMES)]
            tx = ["Buyer", "Seller", "Renter"][(h >> 7) % 3]
            rating = 4 + (h % 3 == 0) * 1  # mostly 5
            if (h % 7) == 0:
                rating = 4
            db.session.add(AgentReview(
                agent_id=a.id, user_id=None,
                reviewer_name=name, rating=rating,
                title=t, body=b, transaction_type=tx,
                created_at=base + timedelta(days=a.id * 5 + k * 60,
                                            minutes=h % 60),
            ))
        # 1-2 awards
        n_awards = 1 + (_h("aw", a.id) % 2)
        for k in range(n_awards):
            h = _h("awn", a.id, k)
            tpl = AWARD_NAMES[h % len(AWARD_NAMES)]
            nm = tpl.format(city=a.city)
            year = 2020 + (h % 6)
            db.session.add(AgentAward(agent_id=a.id, year=year, name=nm))
    db.session.commit()


# ─── Sold listings ────────────────────────────────────────────────────────────


def seed_sold_listings():
    from app import Agent, Listing, SoldListing, db
    if SoldListing.query.count() > 0:
        return
    # For each city with listings, synthesize ~6 "recently sold" homes from
    # similar addresses, with deterministic prices based on neighborhood index.
    listings_by_city = {}
    for L in Listing.query.order_by(Listing.id).all():
        listings_by_city.setdefault((L.city, L.state), []).append(L)

    STREET_NAMES = ["Oak", "Maple", "Pine", "Elm", "Cedar", "Birch", "Willow",
                    "Sycamore", "Holly", "Ash"]
    base = datetime(2026, 1, 15)
    sold_total = 0
    for (city, state), Ls in listings_by_city.items():
        # 8 sold per city (when possible)
        n_sold = min(10, max(6, len(Ls) // 4))
        for k in range(n_sold):
            seed_listing = Ls[_h("sold_seed", city, k) % len(Ls)]
            h = _h("sold", city, k)
            num = 100 + (h % 9000)
            sname = STREET_NAMES[h % len(STREET_NAMES)]
            stype = ["Street", "Avenue", "Drive", "Lane"][(h >> 4) % 4]
            address = f"{num} {sname} {stype}"
            beds = seed_listing.beds or 2 + (h % 4)
            baths_full = seed_listing.baths_full or 1 + (h % 3)
            sqft = seed_listing.sqft or 1100 + (h % 1800)
            yb = seed_listing.year_built or 1960 + (h % 60)
            ptype = seed_listing.property_type
            list_p = seed_listing.price + ((h % 200) - 100) * 1000
            list_p = max(150_000, list_p)
            sold_p = list_p + ((h >> 3) % 200 - 100) * 1000
            sold_p = max(140_000, sold_p)
            list_p = (list_p // 5000) * 5000
            sold_p = (sold_p // 5000) * 5000
            sold_d = (base + timedelta(days=(h % 130))).date().isoformat()
            dom = 7 + (h % 80)
            slug = _slug(f"{address}-{city}-{state}-{k}")
            slug = slug[:180]
            hero = seed_listing.hero_image
            agent_id = seed_listing.agent_id
            db.session.add(SoldListing(
                slug=slug, address=address,
                unit="", neighborhood=seed_listing.neighborhood or "",
                city=city, state=state,
                zip=seed_listing.zip,
                beds=beds, baths_full=baths_full, baths_half=0,
                sqft=sqft, year_built=yb, property_type=ptype,
                list_price=list_p, sold_price=sold_p,
                sold_date=sold_d, days_on_market=dom,
                hero_image=hero, agent_id=agent_id,
            ))
            sold_total += 1
    db.session.commit()


# ─── Per-user notes / offers / mortgage scenarios / newsletter ────────────────


def seed_user_extras():
    from app import (AffordabilityResult, Listing, MortgageScenario,
                     NewsletterSignup, Note, Offer, User, db)
    if Note.query.count() > 0:
        return
    base = datetime(2026, 4, 10, 9, 0, 0)
    users = User.query.filter(User.email.like("%@test.com")).order_by(User.id).all()
    for ui, u in enumerate(users):
        # 2 notes per user, one linked to a listing in their city, one general.
        in_city = (Listing.query.filter_by(city=u.city, status="for-sale")
                   .order_by(Listing.id).all())
        if in_city:
            l_for_note = in_city[_h("note_l", u.email) % len(in_city)]
            db.session.add(Note(
                user_id=u.id, listing_id=l_for_note.id,
                body=("Loved the natural light here — kitchen could use updating "
                      "but layout works. Schedule a 2nd visit before deciding."),
                created_at=base + timedelta(days=ui * 2),
            ))
        db.session.add(Note(
            user_id=u.id, listing_id=None,
            body=("Reminder: confirm with lender on the new conforming-loan "
                  "limit before going above $1.5M."),
            created_at=base + timedelta(days=ui * 2, hours=4),
        ))

        # 1 offer per user on a listing in their city
        if in_city:
            o_listing = in_city[_h("offer_l", u.email) % len(in_city)]
            amt = (o_listing.price // 1000) * 1000  # listing price
            db.session.add(Offer(
                user_id=u.id, listing_id=o_listing.id,
                amount=amt, earnest_money=max(5000, amt // 50),
                contingencies="Financing, Inspection",
                close_date="2026-08-15",
                financing="Conventional",
                notes="Pre-approved through First Republic; flexible on close.",
                status="submitted",
                created_at=base + timedelta(days=10 + ui),
            ))

        # 1 mortgage scenario per user
        hp = (u.budget_max or 800_000)
        down = hp // 5
        rate = 6.25
        mp = _mortgage_pi(max(0, hp - down), rate, 30)
        db.session.add(MortgageScenario(
            user_id=u.id, label=f"{u.city} 30-yr at {rate}%",
            home_price=hp, down_payment=down, rate_pct=rate, term_years=30,
            annual_tax=hp // 80, annual_insurance=hp // 800,
            monthly_hoa=300 if u.city in {"New York", "San Francisco"} else 0,
            monthly_payment=mp + hp // 80 // 12 + hp // 800 // 12 +
                            (300 if u.city in {"New York", "San Francisco"} else 0),
            created_at=base + timedelta(days=20 + ui),
        ))

        # 1 affordability result per user
        income = (u.budget_max or 800_000) * 8 // 30  # back into a salary
        income = (income // 5000) * 5000
        debts = 800
        rate2 = 6.5
        max_monthly = int(income * 0.36 / 12) - debts
        max_monthly = max(0, max_monthly)
        principal = max_monthly * ((1 + rate2 / 1200) ** 360 - 1) / (rate2 / 1200 * (1 + rate2 / 1200) ** 360) if max_monthly else 0
        max_home = int(principal + down)
        db.session.add(AffordabilityResult(
            user_id=u.id, annual_income=income, monthly_debts=debts,
            down_payment=down, rate_pct=rate2, max_home_price=max_home,
            created_at=base + timedelta(days=25 + ui),
        ))

        # Newsletter
        db.session.add(NewsletterSignup(
            email=u.email, name=u.name, city_interest=u.city,
            created_at=base + timedelta(days=30 + ui),
        ))
    db.session.commit()


def _mortgage_pi(P, rate_pct, term_years):
    n = term_years * 12
    if n <= 0:
        return 0
    r = (rate_pct or 0) / 100.0 / 12.0
    if r == 0:
        return int(round(P / n)) if n else 0
    pay = P * (r * (1 + r) ** n) / ((1 + r) ** n - 1)
    return int(round(pay))


# ─── Top-level orchestrator ───────────────────────────────────────────────────


def seed_extras_all():
    seed_neighborhoods()
    seed_schools()
    seed_listing_schools()
    seed_offices()
    seed_teams()
    seed_market_reports()
    seed_blog_posts()
    seed_price_history()
    seed_agent_reviews_and_awards()
    seed_sold_listings()
    seed_user_extras()
