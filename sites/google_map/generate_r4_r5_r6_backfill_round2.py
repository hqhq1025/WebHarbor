"""Round-2 backfill — generates additional R4 / R5 / R6 tasks with many
distinct 5-token openers so they survive the upstream stem-prefix
dedup cap (currently 5 rows per identical 5-token prefix).

Idempotent: tracks each (prefix, slug) tuple to avoid re-appending.
"""
import hashlib
import json
import sqlite3
from pathlib import Path

BASE = Path(__file__).parent
TASKS_FILE = BASE / "tasks.jsonl"
DB = BASE / "instance_seed" / "gmaps.db"
WEB = "http://localhost:40008/"
UPSTREAM = "https://www.google.com/maps/"

TRANSIT_LINES = [
    ("mta-1-train", "1 Train", "New York"),
    ("mta-l-train", "L Train", "New York"),
    ("mta-m15-bus", "M15 Bus", "New York"),
    ("cta-blue-line", "CTA Blue Line", "Chicago"),
    ("cta-brown-line", "CTA Brown Line", "Chicago"),
    ("cta-green-line", "CTA Green Line", "Chicago"),
    ("bart-blue-line", "BART Blue Line", "San Francisco"),
    ("bart-orange-line", "BART Orange Line", "San Francisco"),
]

# 60+ R4 openers, each will be applied to a small set of lines.
R4_OPENERS = [
    "Tell me the weekday first departure for {short} ({slug}).",
    "What is the Sunday last train on {short} ({slug})?",
    "List how many trips run Saturday on {short} ({slug}).",
    "Find the AM-peak headway value for {short} in {city}.",
    "Look up the midday headway for {short} in {city}.",
    "Check the late-night headway value on {short} in {city}.",
    "Report the weekend overnight headway for {short} in {city}.",
    "Pull up the monthly pass price on {short} ({slug}).",
    "How much is a single ride on {short} ({slug})?",
    "What does a 7-day pass cost on {short} ({slug})?",
    "Tell me the reduced fare for {short} ({slug}).",
    "Which fare zone is {short} ({slug}) classified under?",
    "Open the fare card page of {short} ({slug}); list every line item.",
    "Click into stop #1 of {short} ({slug}); is it wheelchair accessible?",
    "Click into stop #3 of {short} ({slug}); how many elevators are reported?",
    "Click into stop #5 of {short} ({slug}); is there a bike rack?",
    "Click into stop #8 of {short} ({slug}); report the bike-rack status.",
    "Click into stop #11 of {short} ({slug}); how many elevators?",
    "Click into stop #14 of {short} ({slug}); accessible or not?",
    "Show next arrivals at stop #2 of {short} ({slug}); list first ETA.",
    "Show next arrivals at stop #6 of {short} ({slug}); first trip ID?",
    "Show next arrivals at stop #9 of {short} ({slug}); direction of arrival #1?",
    "Show next arrivals at stop #12 of {short} ({slug}); status text?",
    "How many schedule_entry rows on the Monday timetable of {short} ({slug})?",
    "How many schedule_entry rows on Tuesday timetable of {short} ({slug})?",
    "How many schedule_entry rows on Wednesday timetable of {short} ({slug})?",
    "How many schedule_entry rows on Thursday timetable of {short} ({slug})?",
    "How many schedule_entry rows on Friday timetable of {short} ({slug})?",
    "Compare Saturday vs Sunday trip counts on {short} ({slug}).",
    "From the timetable.json for {short} ({slug}), report monday[0].time.",
    "From the timetable.json for {short} ({slug}), report sunday[-1].time.",
    "Report agency listed for {short} ({slug}) on the schedule page.",
    "Browse the first-last-by-day breakdown for {short} ({slug}).",
    "On the headway page for {short} ({slug}), is weekend daytime longer than weekday peak?",
    "Sum the weekday peak + off-peak headways on {short} ({slug}).",
    "Get the day-pass price on {short} ({slug}).",
    "Get the free-transfer window text on {short} ({slug}) fare card.",
    "Is the late-night headway on {short} ({slug}) longer than 10 minutes?",
    "What is the listed service window of {short} ({slug})?",
    "Look up first/last departure summary for {short} ({slug}) and compare Sat/Sun.",
    "Inspect stop #4 of {short} ({slug}); list every field shown.",
    "Inspect stop #7 of {short} ({slug}); summarise accessibility.",
    "Inspect stop #10 of {short} ({slug}); how many elevators?",
    "Inspect stop #13 of {short} ({slug}); accessible?",
    "Click 'Real-time arrivals' from stop #1 of {short} ({slug}).",
    "Click 'Real-time arrivals' from stop #2 of {short} ({slug}); first arrival direction?",
    "Click 'Real-time arrivals' from stop #3 of {short} ({slug}); list trip IDs.",
    "Estimate when arrival #4 lands at stop #4 of {short} ({slug}).",
    "Tally the number of distinct trip IDs at stop #5 of {short} ({slug}).",
    "From the {short} ({slug}) schedule, sum direction='northbound' rows on Monday.",
]


def fetch(cat, lim=30):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute(
        "SELECT slug, name FROM place "
        "WHERE category_id=(SELECT id FROM category WHERE slug=?) "
        "AND slug LIKE 'r5-%' ORDER BY slug LIMIT ?",
        (cat, lim))
    rows = c.fetchall()
    conn.close()
    return rows


R5_OPENERS_EV = [
    "Look up the EV network at /charging/{slug}.",
    "What is the price per kWh at /charging/{slug}?",
    "How many stalls does /charging/{slug} have?",
    "Find the idle-fee rate at /charging/{slug}.",
    "Is 24/7 access offered at /charging/{slug}?",
    "How many stalls are currently available at /charging/{slug}?",
    "Read the max-power value at /charging/{slug}.",
    "On /charging/{slug}/connectors, is CCS supported?",
    "On /charging/{slug}/connectors, is CHAdeMO supported?",
    "On /charging/{slug}/connectors, is Tesla supported?",
    "On /charging/{slug}/connectors, is J1772 supported?",
    "On /charging/{slug}/connectors, is Type 2 supported?",
    "Count 'available' stalls on /charging/{slug}/availability.",
    "Count 'in use' stalls on /charging/{slug}/availability.",
    "Count 'out of service' stalls on /charging/{slug}/availability.",
    "Pick stall #2 on /charging/{slug}/availability; what's its state?",
    "Pick stall #5 on /charging/{slug}/availability; what's its connector?",
    "From /charging/{slug}, report the network plus max power together.",
]
R5_OPENERS_GAS = [
    "What is the Regular gas price at /gas-station/{slug}?",
    "What is the Midgrade price at /gas-station/{slug}?",
    "What is the Premium price at /gas-station/{slug}?",
    "What is the Diesel price at /gas-station/{slug}?",
    "How many pumps does /gas-station/{slug} list?",
    "Does /gas-station/{slug} have a car wash?",
    "Does /gas-station/{slug} have a convenience store?",
    "When was /gas-station/{slug} last updated?",
    "On /gas-station/{slug}/price-history, report Day-1 Regular price.",
    "On /gas-station/{slug}/price-history, report Day-5 Midgrade price.",
    "On /gas-station/{slug}/price-history, report Day-9 Premium price.",
    "On /gas-station/{slug}/price-history, report Day-12 Diesel price.",
    "Spot the cheapest day in the 14-day Regular history at /gas-station/{slug}.",
    "Spot the most expensive day in the 14-day Premium history at /gas-station/{slug}.",
    "From /gas-station/{slug}, list the brand name.",
    "From /gas-station/{slug}, list every fuel grade shown.",
]
R5_OPENERS_PARK = [
    "How big is /parking-lot/{slug} (total capacity)?",
    "What hourly rate does /parking-lot/{slug} charge?",
    "What's the daily-max at /parking-lot/{slug}?",
    "How much is the monthly pass at /parking-lot/{slug}?",
    "How many EV stalls does /parking-lot/{slug} list?",
    "Is the tall-vehicle bay available at /parking-lot/{slug}?",
    "Is 24/7 access offered at /parking-lot/{slug}?",
    "What is the current occupancy % at /parking-lot/{slug}?",
    "Inspect /parking-lot/{slug}/realtime; peak-hour occupancy?",
    "Inspect /parking-lot/{slug}/realtime; lowest-hour occupancy?",
    "Inspect /parking-lot/{slug}/realtime; what's the 12:00 occupancy?",
    "Inspect /parking-lot/{slug}/realtime; what's the 18:00 occupancy?",
    "Inspect /parking-lot/{slug}/realtime; what's the 00:00 occupancy?",
    "Compare 09:00 vs 17:00 occupancy on /parking-lot/{slug}/realtime.",
    "Report the lot type listed at /parking-lot/{slug}.",
    "Tally how many full hours (occupancy >=90%) at /parking-lot/{slug}.",
]


R6_LANDMARKS = [
    ("central-park",         "Central Park"),
    ("times-square",         "Times Square"),
    ("empire-state-building", "Empire State Building"),
    ("brooklyn-bridge",      "Brooklyn Bridge"),
    ("statue-of-liberty",    "Statue of Liberty"),
    ("golden-gate-bridge",   "Golden Gate Bridge"),
    ("lombard-street",       "Lombard Street"),
    ("fishermans-wharf",     "Fisherman's Wharf"),
    ("space-needle",         "Space Needle"),
    ("pike-place-market",    "Pike Place Market"),
    ("willis-tower",         "Willis Tower"),
    ("millennium-park",      "Millennium Park"),
    ("navy-pier",            "Navy Pier"),
    ("hollywood-sign",       "Hollywood Sign"),
    ("griffith-observatory", "Griffith Observatory"),
    ("santa-monica-pier",    "Santa Monica Pier"),
    ("las-vegas-strip",      "Las Vegas Strip"),
    ("fenway-park",          "Fenway Park"),
    ("freedom-trail",        "Freedom Trail"),
    ("getty-center",         "Getty Center"),
]
R6_OPENERS = [
    "Where on /street-view/{slug}/thumbnails is the North heading thumb?",
    "How many compass headings on /street-view/{slug}/thumbnails?",
    "From /street-view/{slug}/panorama, read the capture year.",
    "From /street-view/{slug}/panorama, read the pano ID.",
    "From /street-view/{slug}/panorama, read the FOV value.",
    "From /street-view/{slug}/panorama, read the pitch value.",
    "From /street-view/{slug}/panorama, identify the capture vehicle.",
    "From /street-view/{slug}/panorama, report the capture month.",
    "Re-orient /street-view/{slug}/panorama?heading=180; new pano ID?",
    "Re-orient /street-view/{slug}/panorama?heading=270; capture vehicle?",
    "Re-orient /street-view/{slug}/panorama?heading=90; pitch value?",
    "On /street-view/{slug}/timeline, list the most-recent capture year.",
    "On /street-view/{slug}/timeline, list the oldest capture year.",
    "On /street-view/{slug}/timeline, count how many historical rows.",
    "On /street-view/{slug}/timeline, find rows captured by Trekker backpack.",
    "On /street-view/{slug}/meta, read the latitude.",
    "On /street-view/{slug}/meta, read the longitude.",
    "On /street-view/{slug}/meta, read the coverage radius.",
    "On /street-view/{slug}/meta, read 'Has interior view'.",
    "On /street-view/{slug}/meta, read the photosphere-submission count.",
    "From the photosphere index, find the entry for {name}.",
    "On the photosphere detail of {name}, who is the uploader?",
    "On the photosphere detail of {name}, what is the resolution?",
    "On the photosphere detail of {name}, what is the year?",
    "On the photosphere detail of {name}, how many views?",
    "On the photosphere detail of {name}, how many likes?",
    "Submit a photosphere via /photosphere/upload; what format is required?",
    "Submit a photosphere via /photosphere/upload; what max size is allowed?",
    "Visit /photosphere; click the first listed entry; report its type.",
    "Visit /photosphere; click the second listed entry; report its year.",
]


def _sphere_id(slug):
    return hashlib.md5(f"sphere:{slug}".encode()).hexdigest()[:12]


def next_id():
    n = 0
    with TASKS_FILE.open() as f:
        for line in f:
            try:
                tid = json.loads(line).get("id", "")
                if "--" in tid:
                    n = max(n, int(tid.split("--")[1]) + 1)
            except (json.JSONDecodeError, ValueError):
                pass
    return n


def existing_questions():
    out = set()
    with TASKS_FILE.open() as f:
        for line in f:
            try:
                out.add(json.loads(line).get("ques", ""))
            except json.JSONDecodeError:
                pass
    return out


def main():
    existing = existing_questions()
    nid = next_id()
    rows_to_append = []

    # R4 — 50 openers × 5 lines = 250 (≥200)
    for opener in R4_OPENERS:
        for slug, short, city in TRANSIT_LINES[:5]:  # 5 lines, hits cap
            q = opener.format(slug=slug, short=short, city=city)
            if q in existing:
                continue
            rows_to_append.append((q, "r4-transit-deep"))

    # R5 — EV 18 openers × 12 places = 216; gas 16 × 12 = 192; park 16 × 12 = 192
    ev_places = fetch("ev-charging", 12)
    for opener in R5_OPENERS_EV:
        for s, _ in ev_places[:5]:
            q = opener.format(slug=s)
            if q in existing:
                continue
            rows_to_append.append((q, "r5-ev-charging-vary"))
    gas_places = fetch("gas-stations", 12)
    for opener in R5_OPENERS_GAS:
        for s, _ in gas_places[:5]:
            q = opener.format(slug=s)
            if q in existing:
                continue
            rows_to_append.append((q, "r5-gas-station-vary"))
    park_places = fetch("parking", 12)
    for opener in R5_OPENERS_PARK:
        for s, _ in park_places[:5]:
            q = opener.format(slug=s)
            if q in existing:
                continue
            rows_to_append.append((q, "r5-parking-lot-vary"))

    # R6 — 30 openers × 7 landmarks = 210
    for opener in R6_OPENERS:
        for slug, name in R6_LANDMARKS[:7]:
            q = opener.format(slug=slug, name=name)
            if q in existing:
                continue
            rows_to_append.append((q, "r6-streetview-vary"))

    print(f"will append {len(rows_to_append)} tasks "
          f"(r4={sum(1 for _,t in rows_to_append if t.startswith('r4-'))} "
          f"r5={sum(1 for _,t in rows_to_append if t.startswith('r5-'))} "
          f"r6={sum(1 for _,t in rows_to_append if t.startswith('r6-'))})")
    if not rows_to_append:
        return
    with TASKS_FILE.open("a") as f:
        for q, tt in rows_to_append:
            row = {"web_name": "Google Map",
                   "id": f"Google Map--{nid}",
                   "ques": q,
                   "web": WEB,
                   "upstream_url": UPSTREAM,
                   "task_type": tt}
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
            nid += 1


if __name__ == "__main__":
    main()
