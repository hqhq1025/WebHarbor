"""Generate R5 task additions for tasks.jsonl.

Appends ~700 new tasks covering the R5 task types:
  - indoor-walking-route
  - EV-route-charging-stop
  - transit-realtime-delay
  - accessibility-route-preferred
  - place-share-via-QR
  - group-meetup-coordinate
  - location-history-export
  - multi-step
  - indoor sub-zone discovery (floor selector, food court, restroom)
  - ambient filter (noise / crowd / mask)
  - parking lot capacity / EV connector

Deterministic — same input file produces the same output every time.
Append-only, idempotent: re-running detects existing R5-* ids and skips.
"""
import json
from pathlib import Path

BASE = Path(__file__).parent
TASKS_FILE = BASE / "tasks.jsonl"
WEB_URL = "http://localhost:40008/"
UPSTREAM = "https://www.google.com/maps/"

ANCHOR_CITIES = [
    "New York", "Los Angeles", "Chicago", "San Francisco", "Seattle",
    "Boston", "Washington DC", "Miami", "Philadelphia", "Atlanta",
    "Houston", "Dallas", "Phoenix", "Denver", "Portland",
    "Las Vegas", "Minneapolis", "Detroit", "Baltimore", "San Diego",
    "Austin", "Charlotte", "Indianapolis", "Columbus", "Nashville",
    "Pittsburgh", "Cleveland", "Cincinnati", "Milwaukee", "Kansas City",
]

# Each task pattern is parameterised by an anchor city or two.
R5_TASK_PATTERNS = [
    # ---------- indoor-walking-route ----------
    ("Plan an indoor walking route from {a} Airport — Gate A12 Lounge to the Concourse C Food Court.", "indoor-walking-route"),
    ("Show the indoor walking path inside {a} Airport from Terminal 1 Family Restroom to the Gate B7 Charging Cluster.", "indoor-walking-route"),
    ("Plan an indoor walk inside {a} Mall from the Level 1 Food Court to the Rooftop Garden Court.", "indoor-walking-route"),
    ("Walk inside {a} Mall from the Level 2 Fashion Wing to the Lower Level Family Restroom.", "indoor-walking-route"),
    ("Navigate inside {a} Medical Center from the ER Triage Lobby to the Pediatric Wing on floor 3.", "indoor-walking-route"),
    ("Plan an indoor path inside {a} Medical Center from the Cardiology Wing to the Maternity Wing.", "indoor-walking-route"),
    ("Open the floor selector for {a} Mall and switch to Level 2.", "indoor-walking-route"),
    ("Open the floor selector for {a} Airport and show what's on the Mezzanine.", "indoor-walking-route"),
    ("Find the Quiet Meditation Room inside {a} Airport.", "indoor-walking-route"),
    ("Find the Sensory Room at {a} Arena.", "indoor-walking-route"),

    # ---------- EV-route-charging-stop ----------
    ("Plan an EV route from {a} to {b} with at least one fast-charge stop.", "EV-route-charging-stop"),
    ("Show me an EV-friendly drive from {a} to {b}, including charging stops along the way.", "EV-route-charging-stop"),
    ("Find a Tesla Supercharger V4 station near {a}.", "EV-route-charging-stop"),
    ("Find an Electrify America hyperfast charging plaza near {a}.", "EV-route-charging-stop"),
    ("Find a ChargePoint Express 250 station near {a} with both CCS and CHAdeMO connectors.", "EV-route-charging-stop"),
    ("Find an EV charging station near {a} with at least 350 kW peak.", "EV-route-charging-stop"),
    ("Find a Rivian Adventure Network charger near {a}.", "EV-route-charging-stop"),
    ("Show me a Shell Recharge station near {a} that has both gas pumps and EV chargers.", "EV-route-charging-stop"),
    ("Find a BP Pulse station near {a} with 150 kW EV stalls.", "EV-route-charging-stop"),
    ("Find an EV station near {a} with a Tesla connector.", "EV-route-charging-stop"),

    # ---------- transit-realtime-delay ----------
    ("Open the realtime transit delays dashboard and tell me which line is most delayed in {a}.", "transit-realtime-delay"),
    ("Check the realtime delay for the MTA 1 Train.", "transit-realtime-delay"),
    ("Check the realtime delay for the CTA Red Line in {a}.", "transit-realtime-delay"),
    ("Filter the realtime transit board to only {a} and report any line currently delayed.", "transit-realtime-delay"),
    ("How many minutes is the MBTA Red Line delayed right now and what's the reason?", "transit-realtime-delay"),
    ("Show realtime transit delays in {a}.", "transit-realtime-delay"),
    ("Find any transit line currently delayed by more than 5 minutes.", "transit-realtime-delay"),
    ("List all transit lines currently on schedule in {a}.", "transit-realtime-delay"),

    # ---------- accessibility-route-preferred ----------
    ("Plan an accessibility-preferred walking route from the {a} Convention Center to Pike Place Market.", "accessibility-route-preferred"),
    ("Plan a route from {a} to {b} that prefers curb cuts and elevators.", "accessibility-route-preferred"),
    ("Find a hotel near {a} with a wheelchair-accessible entrance.", "accessibility-route-preferred"),
    ("Find a place near {a} with an assistive hearing loop.", "accessibility-route-preferred"),
    ("Find a museum near {a} with a wheelchair-accessible restroom.", "accessibility-route-preferred"),
    ("Find a restaurant near {a} with a braille menu.", "accessibility-route-preferred"),
    ("Find a transit station in {a} with a tactile guide strip.", "accessibility-route-preferred"),
    ("Find a place near {a} with accessibility score above 80.", "accessibility-route-preferred"),
    ("Toggle the high-contrast map style.", "accessibility-route-preferred"),

    # ---------- place-share-via-QR ----------
    ("Open the QR share page for Empire State Building.", "place-share-via-QR"),
    ("Show the QR code to share Central Park.", "place-share-via-QR"),
    ("Get the share URL for Golden Gate Bridge via QR.", "place-share-via-QR"),
    ("Open the QR code for Times Square.", "place-share-via-QR"),
    ("Share Eiffel Tower via QR and get the shareable URL.", "place-share-via-QR"),
    ("Open the QR code for the Louvre.", "place-share-via-QR"),
    ("Open the QR code for the Colosseum.", "place-share-via-QR"),
    ("Open the QR code for Pike Place Market.", "place-share-via-QR"),

    # ---------- group-meetup-coordinate ----------
    ("Coordinate a group meetup with Central Park, Empire State Building, and Brooklyn Bridge.", "group-meetup-coordinate"),
    ("Plan a meetup midpoint between Times Square, Madison Square Garden, and Bryant Park.", "group-meetup-coordinate"),
    ("Find a coffee shop midway between Eiffel Tower and the Louvre.", "group-meetup-coordinate"),
    ("Coordinate a meetup at the midpoint of {a} and {b}.", "group-meetup-coordinate"),
    ("Plan a 3-person meetup at the midpoint of Golden Gate Bridge, Lombard Street, and Fisherman's Wharf.", "group-meetup-coordinate"),
    ("Open the meetup planner and find a midpoint between {a} and {b}.", "group-meetup-coordinate"),

    # ---------- location-history-export ----------
    ("Export your location history as JSON.", "location-history-export"),
    ("Download your Maps timeline data.", "location-history-export"),
    ("Open the location history export page and download the JSON.", "location-history-export"),
    ("How many timeline entries does the current user have to export?", "location-history-export"),
    ("Export the timeline JSON and tell me when the snapshot was made.", "location-history-export"),
    ("Open Your Data > Export and download your visits.", "location-history-export"),

    # ---------- multi-step ----------
    ("Plan a trip from {a} to {b} via EV charging stop, then save the destination to your Favorites list.", "multi-step"),
    ("Find a wheelchair-accessible hotel in {a}, save it, then plan walking directions from your saved hotel to the {b} Museum.", "multi-step"),
    ("Search for a coffee shop with quiet noise level in {a}, save the top result to your Favorites, then export your timeline.", "multi-step"),
    ("Find an EV charging station with at least 250 kW in {a}, then plan a driving route to it from downtown.", "multi-step"),
    ("Open realtime transit delays in {a}, pick a line on schedule, and view its station details.", "multi-step"),
    ("Find a mall with a Level 2 Fashion Wing in {a}, open its floor selector, and share the place via QR.", "multi-step"),

    # ---------- indoor sub-zone discovery ----------
    ("Find an airport food court near {a}.", "indoor-sub-zone"),
    ("Find a mall food court in {a}.", "indoor-sub-zone"),
    ("Find a family restroom in {a} Mall.", "indoor-sub-zone"),
    ("Find a meditation room at {a} Airport.", "indoor-sub-zone"),
    ("Find a quiet floor inside {a} University Library.", "indoor-sub-zone"),
    ("Find a sky lounge bar at the {a} Grand Hotel.", "indoor-sub-zone"),
    ("Find a maternity wing in a hospital in {a}.", "indoor-sub-zone"),
    ("Find an Impressionists wing in a museum in {a}.", "indoor-sub-zone"),
    ("Find a bike & stroller storage area in {a} Central Station.", "indoor-sub-zone"),
    ("Find a sensory room at the {a} Arena.", "indoor-sub-zone"),

    # ---------- ambient filter ----------
    ("Find a quiet restaurant in {a}.", "ambient-filter"),
    ("Find a lively bar in {a}.", "ambient-filter"),
    ("Find a coffee shop in {a} with low crowd level.", "ambient-filter"),
    ("Find a restaurant in {a} where mask is required.", "ambient-filter"),
    ("Find a park in {a} with quiet noise level.", "ambient-filter"),
    ("Find a library in {a} with a quiet noise level and high accessibility score.", "ambient-filter"),
    ("Find a coffee shop in {a} that is quiet and has Wi-Fi.", "ambient-filter"),
    ("Find a hotel in {a} with a quiet spa floor.", "ambient-filter"),
    ("Find a hospital in {a} that requires masks.", "ambient-filter"),
    ("Find a place in {a} with a moderate crowd level.", "ambient-filter"),

    # ---------- parking / EV details ----------
    ("Find a multi-level parking garage in {a} with at least 1000 spaces.", "parking-ev-details"),
    ("Find a parking lot near {a} Convention Center.", "parking-ev-details"),
    ("Find an airport long-term parking lot in {a}.", "parking-ev-details"),
    ("Find a beach day-use parking lot in {a}.", "parking-ev-details"),
    ("Find a park & ride lot near {a}.", "parking-ev-details"),
    ("Find a hospital visitor parking garage in {a}.", "parking-ev-details"),
    ("Find a stadium west lot in {a}.", "parking-ev-details"),
    ("How many spaces does the {a} City Center Multi-Level Garage have?", "parking-ev-details"),
]

# Pair anchor cities deterministically so {a}/{b} are stable across runs.
def pair_anchors(i):
    a = ANCHOR_CITIES[i % len(ANCHOR_CITIES)]
    b = ANCHOR_CITIES[(i * 7 + 3) % len(ANCHOR_CITIES)]
    if a == b:
        b = ANCHOR_CITIES[(i + 1) % len(ANCHOR_CITIES)]
    return a, b


def main():
    existing = []
    if TASKS_FILE.exists():
        with open(TASKS_FILE, "r") as f:
            existing = [json.loads(l) for l in f if l.strip()]
    max_id = -1
    have_r5 = False
    for t in existing:
        try:
            n = int(t["id"].rsplit("--", 1)[1])
            max_id = max(max_id, n)
        except (ValueError, IndexError, KeyError):
            continue
        if t.get("task_type", "").startswith(("indoor-walking", "EV-route", "transit-realtime",
                                              "accessibility-route", "place-share",
                                              "group-meetup", "location-history",
                                              "multi-step", "indoor-sub", "ambient",
                                              "parking-ev")):
            have_r5 = True

    if have_r5:
        print("R5 tasks already appended — skipping")
        return

    # Generate enough variations so total >= 1500.
    target_new = max(700, 1500 - len(existing))
    new_tasks = []
    i = 0
    pat_idx = 0
    while len(new_tasks) < target_new:
        a, b = pair_anchors(i)
        pattern, task_type = R5_TASK_PATTERNS[pat_idx % len(R5_TASK_PATTERNS)]
        ques = pattern.replace("{a}", a).replace("{b}", b)
        max_id += 1
        new_tasks.append({
            "web_name": "Google Map",
            "id": f"Google Map--{max_id}",
            "ques": ques,
            "web": WEB_URL,
            "upstream_url": UPSTREAM,
            "task_type": task_type,
        })
        i += 1
        pat_idx += 1

    with open(TASKS_FILE, "a") as f:
        for t in new_tasks:
            f.write(json.dumps(t) + "\n")
    print(f"Appended {len(new_tasks)} R5 tasks. Total tasks: {len(existing) + len(new_tasks)}")


if __name__ == "__main__":
    main()
