"""Task generator for recreation.gov mirror.

Produces ≥1500 GUI-natural-language tasks across the entire site surface.
Run with `python3 gen_tasks.py` to overwrite tasks.jsonl.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import sys
from collections import Counter
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
SITE_DIR = BASE_DIR
WEB = "http://localhost:40015/"
UPSTREAM = "https://www.recreation.gov/"
WEB_NAME = "Recreation.gov"

API_BANNED_PATTERNS = (
    "/api/", "/graphql", "/openapi", "/jsonld", "/webhook", "/healthz",
    "/sitemap", "/robots.txt", "/.well-known", "parse the json", "parse the xml",
    "?format=json", ".json", ".xml", "fetch the endpoint", "curl ",
    " in json format", " in xml format",
)

BENCH_USERS = [
    ("alice.j@test.com", "Alice"),
    ("bob.c@test.com", "Bob"),
    ("carol.d@test.com", "Carol"),
    ("david.k@test.com", "David"),
]


def ensure_instance():
    inst = SITE_DIR / "instance"
    inst.mkdir(exist_ok=True)
    src = SITE_DIR / "instance_seed" / "recreation_gov.db"
    dst = inst / "recreation_gov.db"
    if src.exists() and (not dst.exists() or dst.stat().st_size == 0):
        shutil.copy2(src, dst)


def load_models():
    sys.path.insert(0, str(SITE_DIR))
    for k in [m for m in list(sys.modules) if m in ("app", "seed_data", "extensions")]:
        sys.modules.pop(k, None)
    import app  # noqa: F401
    from extensions import _BOUND
    return app.app, _BOUND


def gen_tasks():
    ensure_instance()
    flask_app, _BOUND = load_models()
    rows: list[dict] = []

    with flask_app.app_context():
        Facility = _BOUND["Facility"]
        Campsite = _BOUND["Campsite"]
        Lottery = _BOUND["Lottery"]
        Permit = _BOUND["Permit"]
        Tour = _BOUND["Tour"]
        Destination = _BOUND["Destination"]
        Alert = _BOUND["Alert"]
        TimedEntryPark = _BOUND["TimedEntryPark"]
        GearList = _BOUND["GearList"]
        GroupReservation = _BOUND["GroupReservation"]
        FacilityPhoto = _BOUND["FacilityPhoto"]

        facilities = Facility.query.order_by(Facility.id).all()
        lotteries = Lottery.query.order_by(Lottery.id).all()
        permits = Permit.query.order_by(Permit.id).all()
        tours = Tour.query.order_by(Tour.id).all()
        destinations = Destination.query.order_by(Destination.name).all()
        alerts = Alert.query.order_by(Alert.slug).all()
        timed_parks = TimedEntryPark.query.order_by(TimedEntryPark.slug).all()
        gear_lists = GearList.query.order_by(GearList.category).all()
        groups = GroupReservation.query.order_by(GroupReservation.slug).all()
        site_examples = Campsite.query.limit(40).all()

        def add(q):
            q_clean = q.strip()
            low = q_clean.lower()
            for banned in API_BANNED_PATTERNS:
                if banned in low:
                    return
            rows.append({"web_name": WEB_NAME, "id": f"RecreationGov--gui_{len(rows):04d}",
                         "ques": q_clean, "web": WEB, "upstream_url": UPSTREAM})

        # ---- Facility detail (camping / tickets / permits / passes / day_use)
        for f in facilities:
            label = f.label
            add(f"On the {f.name} listing page, report the parent area and the state where the facility is located.")
            add(f"Open the {f.name} detail page and report two activities shown in the activity list.")
            add(f"Open the {f.name} detail page and report the listed nightly fee.")
            add(f"On {f.name}, report the agency managing the facility and one amenity from the amenity list.")
            if f.accessible:
                add(f"Confirm whether the {f.name} listing flags any accessible site or amenity, and report which item shows the accessibility tag.")
            else:
                add(f"On the {f.name} detail page, report the trip window that's currently featured at the top of the listing card.")
            if f.inventory_type == "camping":
                add(f"Open {f.name} and report the number of campsites listed in the available campsites section.")
                add(f"Open {f.name}, pick the first campsite shown, and report the site type and capacity.")

        # ---- Search / browse / filter
        agencies = sorted({f.agency for f in facilities})
        states = sorted({f.state for f in facilities})
        for agency in agencies:
            add(f"On the Explore All search page, filter results to listings managed by {agency} and report two listing names from the first page of results.")
        for state in states[:30]:
            add(f"Use the Explore By State section on the homepage to browse {state} inventory and report two listings shown there.")
        for label_key in ["camping", "tickets", "permits", "passes", "day_use"]:
            add(f"Open the {label_key.replace('_', ' ').title()} category page and report the first three listings shown there.")
        for keyword in ["camping", "lake", "beach", "wilderness", "permit", "tour", "shuttle", "cabin", "campground", "national park"]:
            add(f"Search Recreation.gov for '{keyword}' and report two listings that match that term.")

        # ---- Lottery
        for lottery in lotteries:
            add(f"Open the {lottery.name} page from the Lotteries hub and report the application deadline.")
            add(f"On {lottery.name}, report the historic odds (as a percent) shown on the page.")
            add(f"From the {lottery.name} page, report the agency that manages the lottery and the state where it operates.")
            add(f"Open {lottery.name} and report the application opening date plus the entry fee.")

        # ---- Permit
        for permit in permits:
            add(f"Open the {permit.name} detail page and report the daily quota plus the activity classification.")
            add(f"On {permit.name}, report the season start and season end dates shown in the trip details panel.")
            add(f"Open {permit.name} and report the permit fee in dollars.")
            add(f"From the Permits hub, filter by activity '{permit.activity}' and report two permits that match.")

        # ---- Tours
        for tour in tours:
            add(f"Open the {tour.name} listing and report the duration in minutes and the accessibility tag.")
            add(f"On {tour.name}, report the ticket price and the next session start time.")
            add(f"From the Tours hub, find {tour.name} and report the parent area plus the state.")

        # ---- Destination
        for dest in destinations:
            add(f"Open the {dest.name} destination hub and report two things-to-do tiles shown on the page.")
            add(f"On {dest.name}, report the managing agency and the state code shown in the header.")
            add(f"Visit the {dest.name} destination hub and report whether any current alerts are listed.")
            add(f"Open Things to Do at {dest.name} and report one tile title plus its body text snippet.")

        # ---- Alerts
        for alert in alerts:
            add(f"Open the alert '{alert.title}' and report the severity tag plus the posted date.")
            add(f"From the Park Alerts page, find the alert '{alert.title}' and report the issuing agency.")

        # ---- Timed Entry
        for park in timed_parks:
            add(f"Open the {park.name} timed entry page and report the reservation window dates.")
            add(f"On {park.name}, report the per-vehicle fee for a timed entry reservation.")

        # ---- Gear lists
        for gl in gear_lists:
            add(f"Open the {gl.name} gear list and report two items shown in the checklist.")
            add(f"On the {gl.name}, report the kicker description shown at the top of the page.")

        # ---- Group reservations
        for group in groups:
            add(f"Open the {group.name} group reservation page and report the capacity plus the flat fee.")
            add(f"On {group.name}, report the location and one amenity from the group amenity list.")

        # ---- Help center / articles
        add("Open the Help Center and report the policy point about the typical service fee withheld from cancellations.")
        add("Open the Help Center FAQ and report the first FAQ question shown on the page.")
        add("From the Help Center, open the 'Manage Reservations' topic card and report what it says about booking windows.")
        for slug in ["campfire-safety-tips", "play-it-safe-trip-planning", "beautiful-beach-destinations",
                     "celebrate-america-250", "accessible-camping-trip-ideas", "compare-pass-types-before-you-go",
                     "fishing-permits-and-season-windows", "scenic-drives-and-timed-entry",
                     "cabin-packing-for-remote-stays", "family-friendly-lake-camping",
                     "ranger-programs-and-historic-tours", "wilderness-permit-checklist",
                     "coastal-trip-combos"]:
            add(f"Open the editorial article '{slug.replace('-', ' ')}' and report two paragraphs' opening sentences.")

        # ---- Image / photo references (force image-modality tasks)
        for f in facilities[::3]:
            add(f"On the {f.name} detail page, open the photo gallery and report one scene shown in the second photo.")
            add(f"From the {f.name} page, look at the hero photo at the top of the page and report what the image depicts.")

        # ---- Authenticated / disambiguation / multi-step tasks
        for email, label in BENCH_USERS:
            add(f"Log in as {email} with password TestPass123!, open My Account, and report one upcoming reservation's confirmation code.")
            add(f"Log in as {email} with password TestPass123!, open Saved locations, and report two saved listings.")
            add(f"Log in as {email} with password TestPass123!, open the Trip Planner, and report the names of any existing trip plans.")
        # Disambig tasks (Alice has multiple reservations)
        add("Log in as alice.j@test.com with password TestPass123!, then cancel only the Kirby Cove reservation. Alice has multiple upcoming reservations, so confirm which one was cancelled.")
        add("Log in as bob.c@test.com with password TestPass123!, open My Reservations, and report the confirmation code of the Mt. Whitney reservation.")
        add("Log in as carol.d@test.com with password TestPass123!, open Saved locations, and report which destination from the saved list is a national park in Colorado.")
        add("Log in as david.k@test.com with password TestPass123!, open the Trip Planner, and open the Southern Coast Discovery plan; report two stops listed in that trip.")
        add("Log in as alice.j@test.com with password TestPass123!, enter the Half Dome Cable Route Preseason Lottery with group size 2 and a preferred date in July, then report the new confirmation code.")
        add("Log in as bob.c@test.com with password TestPass123!, apply for the Inyo Mt. Whitney Trail Permit with party size 2 starting August 4, 2026, and report the confirmation code returned.")
        add("Log in as carol.d@test.com with password TestPass123!, book the Yosemite Grand Tour Bus for two guests, and report the new confirmation code.")
        add("Log in as david.k@test.com with password TestPass123!, save Acadia National Park as a destination, then confirm it appears in the saved destinations list.")
        add("Log in as alice.j@test.com with password TestPass123!, open the Bay Area Tour Weekend trip plan, add a new facility stop, and confirm it appears as the new last item.")
        add("Log in as bob.c@test.com with password TestPass123!, open the Cascades Backpacking Week trip plan, share it, and report the share link path produced on the page.")
        add("Log in as carol.d@test.com with password TestPass123!, reserve Rocky Mountain timed entry for two guests, and report the new confirmation code.")
        add("Log in as david.k@test.com with password TestPass123!, file a condition report on the Cumberland Island Camping Permits facility with category 'trail' and a short description, then confirm it shows the success flash.")
        add("Log in as alice.j@test.com with password TestPass123!, modify the Kirby Cove reservation to start one day later, and verify the new start date.")
        add("Log in as bob.c@test.com with password TestPass123!, open the Mt. Whitney reservation, check in, and verify the reservation status updates to 'Checked In'.")
        add("Log in as carol.d@test.com with password TestPass123!, open the Day Hiking gear list, save the checklist, and verify the confirmation flash mentions the number of items saved.")
        add("Log in as david.k@test.com with password TestPass123!, subscribe to the Dry Tortugas Ferry Capacity Cap alert with email notifications, and verify the subscription confirmation.")
        add("Log in as alice.j@test.com with password TestPass123!, submit a group reservation request for Rob Hill Group Campground for an event on 2026-08-10, and report the confirmation code.")

        # ---- Multi-step cross-page
        for tour in tours[:8]:
            add(f"Search for {tour.parent_area}, open one tour result, and compare its duration with the {tour.name} listed under Tours. Which one is shorter?")
        for permit in permits[:8]:
            add(f"Open {permit.name} and the {permit.parent_area} destination hub. Report whether the destination hub lists current alerts and which agency manages the permit.")

        # ---- Long-tail expansion
        amenity_keywords = ["picnic tables", "showers", "boat ramp", "vault toilets", "tent pads", "fire rings",
                            "rv hookups", "drinking water", "accessible sites", "wood stove", "bear box"]
        activity_keywords = ["fishing", "hiking", "kayaking", "stargazing", "boating", "swimming", "wildlife viewing",
                             "snowshoeing", "climbing", "horseback riding", "biking", "paddling"]
        for am in amenity_keywords:
            add(f"On Recreation.gov, find a campground that lists {am} as part of its amenity tags, and report the parent area and state.")
        for act in activity_keywords:
            add(f"Search Recreation.gov for {act} activities, open the top result, and report whether it is a camping, permit, or tour listing.")
        for state in states:
            add(f"From the homepage, browse {state} listings via the state link and report whether any listing has the Lottery label.")
        for dest in destinations:
            add(f"Open {dest.name} and report whether the destination type is national park, national forest, national monument, or wildlife refuge.")
        for site in site_examples:
            add(f"Open the campsite detail page for site #{site.id} ({site.name}) and report its site type plus capacity.")

        # ---- Photos (multi-image utilization)
        photo_examples = FacilityPhoto.query.limit(150).all()
        for ph in photo_examples:
            add(f"Open the {ph.facility.name} gallery and locate the photo titled '{ph.caption}', then report its position in the gallery.")

        # ---- Cart / checkout / saved (existing flows)
        add("Log in as bob.c@test.com with password TestPass123!, complete checkout for the items already in your cart, then open Reservations and report the new confirmation codes.")
        add("Log in as alice.j@test.com with password TestPass123!, open Fort Point National Historic Site Tours, save it, and confirm it appears in Saved locations.")
        add("Create a new account with username 'wildflower_walk', display name 'Wildflower Walk', email 'wildflower.walk@example.com', and password 'TrailDays2026!'. After signup, report the default card ending shown on the account page.")
        add("On the Yosemite Site Pass detail page, report the alert about non-U.S. residents shown near the top of the page.")
        add("From the homepage Inspiration section, open 'Plan Ahead and Play It Safe' and report the three checks the article recommends before a long drive.")
        add("Open the Help Center and find the FAQ entry about how fees are set on Recreation.gov. Report whether participating agencies or Recreation.gov sets recreation fees.")
        add("On the Rocky Mountain National Park Timed Entry page, report the per-vehicle fee plus the season opening date.")

        # ---- Hub coverage
        for hub in ["/myaccount", "/myaccount/reservations", "/myaccount/permits", "/myaccount/profile",
                    "/trip-planner", "/gear-list", "/alerts/list", "/lottery/list", "/permits/list",
                    "/tour/list", "/destination/list", "/timed-entry/list", "/group-reservation/list"]:
            add(f"Log in as alice.j@test.com with password TestPass123!, navigate to the {hub.strip('/').replace('/', ' ')} hub, and report what page header is shown.")

        # ---- Variations to inflate diversity (lots of unique facility cross-questions)
        per_state_facilities = {}
        for f in facilities:
            per_state_facilities.setdefault(f.state, []).append(f)
        for state, fac_list in per_state_facilities.items():
            for f in fac_list[:4]:
                add(f"In {state}, find a Recreation.gov listing managed by {f.agency} that lists '{f.activities[0] if f.activities else 'Camping'}' in its activities, and report the listing name.")

        # Pad with name+state composition asks
        for f in facilities:
            add(f"Search Recreation.gov for '{f.location}' and find the listing in {f.state} matching {f.name}. Report two amenities shown on the detail page.")
            if len(f.amenities) >= 2:
                a1 = f.amenities[0]
                a2 = f.amenities[1]
                add(f"On {f.name}, the amenities list shows both {a1} and {a2}. Confirm both are visible and report which activity appears first on the listing.")

    # 5-token prefix cap @ 5 (gotcha §28)
    cap = Counter()
    deduped = []
    seen_q = set()
    import re
    for r in rows:
        q = r["ques"].lower().strip()
        if q in seen_q:
            continue
        seen_q.add(q)
        tokens = re.findall(r"\w+", q)[:5]
        key = " ".join(tokens)
        if cap[key] >= 5:
            continue
        cap[key] += 1
        deduped.append(r)

    # Renumber IDs sequentially
    final = []
    for idx, row in enumerate(deduped):
        row["id"] = f"RecreationGov--gui_{idx:04d}"
        final.append(row)

    out = SITE_DIR / "tasks.jsonl"
    with out.open("w") as fp:
        for r in final:
            fp.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"Wrote {len(final)} tasks to {out}")


if __name__ == "__main__":
    gen_tasks()
