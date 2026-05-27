"""Generate R4 / R5 / R6 backfill task entries for tasks.jsonl.

Append-only and idempotent: re-running detects existing task_type prefixes
r4-* / r5-* / r6-* (this generator's namespace) and skips.  No effect on
R7 / R8 / R9 / R10 tasks already in the file.
"""
import hashlib
import json
from pathlib import Path

BASE = Path(__file__).parent
TASKS_FILE = BASE / "tasks.jsonl"
WEB_URL = "http://localhost:40008/"
UPSTREAM = "https://www.google.com/maps/"

# ---- Static anchors (a subset that we know exists in seed DB)
TRANSIT_LINES = [
    ("mta-1-train",       "1 Train",          "New York"),
    ("mta-l-train",       "L Train",          "New York"),
    ("mta-m15-bus",       "M15 Bus",          "New York"),
    ("cta-blue-line",     "CTA Blue Line",    "Chicago"),
    ("cta-brown-line",    "CTA Brown Line",   "Chicago"),
    ("cta-green-line",    "CTA Green Line",   "Chicago"),
    ("bart-blue-line",    "BART Blue Line",   "San Francisco"),
    ("bart-orange-line",  "BART Orange Line", "San Francisco"),
]

R5_EV_SLUGS = [
    "r5-new-york-ev-charging-40", "r5-los-angeles-ev-charging-40",
    "r5-chicago-il-ev-charging-40", "r5-san-francisco-ev-charging-40",
    "r5-seattle-ev-charging-40", "r5-boston-ev-charging-40",
    "r5-miami-fl-ev-charging-40", "r5-philadelphia-ev-charging-40",
    "r5-atlanta-ga-ev-charging-40", "r5-houston-tx-ev-charging-40",
    "r5-dallas-tx-ev-charging-40", "r5-phoenix-ev-charging-40",
    "r5-denver-ev-charging-40", "r5-portland-ev-charging-40",
    "r5-las-vegas-ev-charging-40", "r5-amsterdam-ev-charging-40",
    "r5-berlin-ev-charging-40", "r5-edinburgh-ev-charging-40",
    "r5-london-ev-charging-40", "r5-paris-ev-charging-40",
]
R5_GAS_SLUGS = [
    "r5-las-vegas-gas-stations-63", "r5-london-gas-stations-44",
    "r5-rome-gas-stations-44", "r5-madrid-gas-stations-63",
    "r5-athens-gas-stations-62", "r5-new-york-gas-stations-44",
    "r5-los-angeles-gas-stations-44", "r5-chicago-il-gas-stations-44",
    "r5-san-francisco-gas-stations-44", "r5-seattle-gas-stations-44",
    "r5-boston-gas-stations-44", "r5-miami-fl-gas-stations-44",
    "r5-atlanta-ga-gas-stations-44", "r5-houston-tx-gas-stations-44",
    "r5-dallas-tx-gas-stations-44", "r5-denver-gas-stations-44",
    "r5-portland-gas-stations-44", "r5-philadelphia-gas-stations-44",
    "r5-phoenix-gas-stations-44", "r5-amsterdam-gas-stations-44",
]
R5_PARK_SLUGS = [
    "r5-new-york-parking-33", "r5-san-francisco-parking-32",
    "r5-seattle-parking-33", "r5-paris-parking-33",
    "r5-barcelona-parking-52", "r5-los-angeles-parking-33",
    "r5-chicago-il-parking-33", "r5-boston-parking-33",
    "r5-miami-fl-parking-33", "r5-atlanta-ga-parking-33",
    "r5-houston-tx-parking-33", "r5-dallas-tx-parking-33",
    "r5-phoenix-parking-33", "r5-denver-parking-33",
    "r5-portland-parking-33", "r5-philadelphia-parking-33",
    "r5-las-vegas-parking-33", "r5-london-parking-33",
    "r5-amsterdam-parking-33", "r5-berlin-parking-33",
]

# R6 anchors — real landmark places that already exist in seed
R6_PLACE_SLUGS = [
    "new-york-ny-central-park", "new-york-ny-times-square",
    "new-york-ny-empire-state-building", "new-york-ny-brooklyn-bridge",
    "new-york-ny-statue-of-liberty", "new-york-ny-grand-central-terminal",
    "san-francisco-golden-gate-bridge", "san-francisco-alcatraz-island",
    "san-francisco-lombard-street", "san-francisco-fishermans-wharf",
    "seattle-space-needle", "seattle-pike-place-market",
    "chicago-il-willis-tower", "chicago-il-millennium-park",
    "chicago-il-navy-pier", "los-angeles-hollywood-sign",
    "los-angeles-griffith-observatory", "los-angeles-santa-monica-pier",
    "las-vegas-strip", "washington-dc-lincoln-memorial",
    "boston-fenway-park", "boston-freedom-trail",
    "philadelphia-liberty-bell", "miami-fl-south-beach",
    "denver-red-rocks-amphitheatre", "portland-powells-city-of-books",
    "atlanta-ga-georgia-aquarium", "houston-tx-space-center-houston",
    "dallas-tx-dealey-plaza", "phoenix-camelback-mountain",
]

# Photosphere ids are md5(sphere:slug)[:12] in app.py.
def _sphere_id(place_slug):
    return hashlib.md5(f"sphere:{place_slug}".encode()).hexdigest()[:12]


def gen_r4_tasks():
    """≥200 R4 transit tasks across schedule/stop/arrival/headway/fare."""
    out = []
    for slug, short, city in TRANSIT_LINES:
        # 8 schedule tasks (weekday + each day + first/last + headway + fare)
        out.extend([
            (f"Open the weekday schedule for the {short} ({slug}) in {city} and report the first departure time listed.",
             "r4-transit-schedule"),
            (f"Visit /transit/lines/{slug}/schedule/saturday — report the headway value shown for the Saturday timetable on the {short}.",
             "r4-transit-schedule"),
            (f"Open the Sunday schedule for the {short} and report how many trips are listed in the timetable.",
             "r4-transit-schedule"),
            (f"Find the first/last-train summary for the {short} in {city} (/transit/lines/{slug}/first-last) and report Sunday's last trip time.",
             "r4-transit-first-last"),
            (f"Open the headway analytics page for the {short} ({slug}) and report the weekday late-night headway in minutes.",
             "r4-transit-headway"),
            (f"Check the fare page for the {short} and report the price of a single ride.",
             "r4-transit-fare"),
            (f"Look up the fare card for the {short} ({slug}) and report the monthly pass price.",
             "r4-transit-fare"),
            (f"Open /transit/lines/{slug}/timetable.json and report the total number of weekday schedule_entry rows for the {short}.",
             "r4-transit-timetable-json"),
        ])
        # Stops + arrivals — 14 stops × 2 = 28 tasks per line
        for idx in range(1, 15):
            out.append((
                f"Open stop #{idx} of the {short} (/transit/lines/{slug}/stop/{idx}) and report whether it is wheelchair accessible.",
                "r4-transit-stop"))
            out.append((
                f"Show the next arrivals at stop #{idx} of the {short} in {city} and report the ETA of the first listed arrival.",
                "r4-transit-stop-arrivals"))
    return out


def gen_r5_tasks():
    out = []
    for s in R5_EV_SLUGS:
        out.extend([
            (f"Open /charging/{s} and report the EV network name and price per kWh.",
             "r5-ev-charging-detail"),
            (f"Visit the connector compatibility page for /charging/{s}/connectors and report whether CHAdeMO is supported.",
             "r5-ev-connectors"),
            (f"Open the live availability dashboard at /charging/{s}/availability and report how many stalls are currently 'available'.",
             "r5-ev-availability"),
        ])
    for s in R5_GAS_SLUGS:
        out.extend([
            (f"Open /gas-station/{s} and report the current Regular gasoline price.",
             "r5-gas-station-detail"),
            (f"Visit the gas station detail at /gas-station/{s} and report the current Diesel price along with the number of pumps.",
             "r5-gas-station-detail"),
            (f"Open the 14-day price history page at /gas-station/{s}/price-history and report the Premium price 7 days ago.",
             "r5-gas-station-price-history"),
        ])
    for s in R5_PARK_SLUGS:
        out.extend([
            (f"Open /parking-lot/{s} and report the total parking capacity and current hourly rate.",
             "r5-parking-lot-detail"),
            (f"Open the parking lot detail for /parking-lot/{s} and report the number of EV stalls and the daily max.",
             "r5-parking-lot-detail"),
            (f"Open the live occupancy report at /parking-lot/{s}/realtime and report the 08:00 occupancy percentage.",
             "r5-parking-lot-realtime"),
        ])
    # A handful of cross-vertical comparison tasks
    out.extend([
        (f"Compare two parking lots: /parking-lot/{R5_PARK_SLUGS[0]} and /parking-lot/{R5_PARK_SLUGS[1]} — report which one has the lower hourly rate.",
         "r5-parking-lot-detail"),
        (f"Compare two EV chargers: /charging/{R5_EV_SLUGS[0]} and /charging/{R5_EV_SLUGS[2]} — report which one offers a higher max-power rating.",
         "r5-ev-charging-detail"),
        (f"Compare gas stations /gas-station/{R5_GAS_SLUGS[0]} and /gas-station/{R5_GAS_SLUGS[3]} — report which has the cheaper Regular price.",
         "r5-gas-station-detail"),
    ])
    return out


def gen_r6_tasks():
    out = []
    for s in R6_PLACE_SLUGS:
        out.extend([
            (f"Open /street-view/{s}/thumbnails and report how many compass headings (thumbnails) are listed for this location.",
             "r6-streetview-thumbnails"),
            (f"Visit the 360° panorama page /street-view/{s}/panorama and report the capture year and the field-of-view value.",
             "r6-streetview-panorama"),
            (f"Open /street-view/{s}/panorama?heading=90 and report the capture vehicle used and the pano ID shown.",
             "r6-streetview-panorama"),
            (f"Open the Street View timeline /street-view/{s}/timeline and report the most recent capture date listed.",
             "r6-streetview-timeline"),
            (f"Open the Street View metadata page /street-view/{s}/meta and report the listed coverage radius.",
             "r6-streetview-meta"),
            (f"Open the Photosphere detail page /photosphere/{_sphere_id(s)} and report the photographer username and view count.",
             "r6-photosphere-detail"),
        ])
    out.extend([
        ("Open the Photosphere index at /photosphere and report how many community-uploaded photospheres are listed in the table.",
         "r6-photosphere-index"),
        ("Visit /photosphere/upload and report the accepted file format and the maximum file size for a new photosphere.",
         "r6-photosphere-upload"),
        ("Open /photosphere and click into the first listed item — report the year of the photosphere and its type (interior/rooftop/etc.).",
         "r6-photosphere-index"),
    ])
    return out


def next_id(tasks_path):
    n = 0
    if not tasks_path.exists():
        return 0
    with tasks_path.open() as f:
        for line in f:
            try:
                d = json.loads(line)
                tid = d.get("id", "")
                if "--" in tid:
                    n = max(n, int(tid.split("--")[1]) + 1)
            except (json.JSONDecodeError, ValueError):
                pass
    return n


def main():
    # Idempotency: skip if any r4-*/r5-*/r6-* task_type already present
    existing = set()
    with TASKS_FILE.open() as f:
        for line in f:
            try:
                tt = json.loads(line).get("task_type", "")
                if tt.startswith(("r4-", "r5-", "r6-")):
                    existing.add(tt)
            except json.JSONDecodeError:
                pass
    if existing:
        print(f"[skip] {len(existing)} r4/r5/r6 task_types already present")
        return

    tasks = gen_r4_tasks() + gen_r5_tasks() + gen_r6_tasks()
    nid = next_id(TASKS_FILE)
    n4 = sum(1 for _, t in tasks if t.startswith("r4-"))
    n5 = sum(1 for _, t in tasks if t.startswith("r5-"))
    n6 = sum(1 for _, t in tasks if t.startswith("r6-"))
    print(f"r4: {n4}, r5: {n5}, r6: {n6}, total to append: {len(tasks)}")
    with TASKS_FILE.open("a") as f:
        for q, tt in tasks:
            row = {
                "web_name": "Google Map",
                "id": f"Google Map--{nid}",
                "ques": q,
                "web": WEB_URL,
                "upstream_url": UPSTREAM,
                "task_type": tt,
            }
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
            nid += 1
    print(f"appended through id Google Map--{nid - 1}")


if __name__ == "__main__":
    main()
