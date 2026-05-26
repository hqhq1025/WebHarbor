"""Generate R6 task additions for tasks.jsonl.

Adds ~1000 cross-page tasks that chain ≥2 sub-pages of a single place
(search → place → /menu → /photos → /reviews → /accessibility → /booking →
/directions → /share → /your-places/saved) plus multi-step plan-a-day-trip
tasks with directions between every stop, plus probes for the R6 edge
banners (permanently closed, temporarily closed, no service after hours,
indoor-floor-unmapped, no-route-found alternatives, accessibility warning).

Deterministic: same source file produces the same output every time.
Append-only, idempotent — re-running detects R6-* task_type values
already in tasks.jsonl and exits cleanly.
"""
import json
from pathlib import Path

BASE = Path(__file__).parent
TASKS_FILE = BASE / "tasks.jsonl"
WEB_URL = "http://localhost:40008/"
UPSTREAM = "https://www.google.com/maps/"

# 30 anchor cities — same set as R5 so question phrasings stay coherent
# across rounds.
ANCHOR_CITIES = [
    "New York", "Los Angeles", "Chicago", "San Francisco", "Seattle",
    "Boston", "Washington DC", "Miami", "Philadelphia", "Atlanta",
    "Houston", "Dallas", "Phoenix", "Denver", "Portland",
    "Las Vegas", "Minneapolis", "Detroit", "Baltimore", "San Diego",
    "Austin", "Charlotte", "Indianapolis", "Columbus", "Nashville",
    "Pittsburgh", "Cleveland", "Cincinnati", "Milwaukee", "Kansas City",
]

# Real-world Wikipedia anchors used elsewhere in the seed so cross-page
# tasks land on rows with rich content (menu, reviews, photos).
LANDMARKS = [
    "Empire State Building", "Central Park", "Times Square", "Brooklyn Bridge",
    "Statue of Liberty", "Madison Square Garden", "Bryant Park",
    "Golden Gate Bridge", "Alcatraz Island", "Lombard Street",
    "Fisherman's Wharf", "Pier 39", "Pike Place Market", "Space Needle",
    "Chihuly Garden", "Willis Tower", "Millennium Park",
    "Art Institute of Chicago", "Navy Pier", "Magnificent Mile",
    "Santa Monica Pier", "Griffith Observatory", "Hollywood Sign",
    "Venice Beach", "Universal Studios Hollywood",
    "Eiffel Tower", "Louvre", "Arc de Triomphe", "Notre Dame",
    "Colosseum", "Vatican City", "Trevi Fountain",
    "Tokyo Tower", "Tokyo Skytree", "Sensoji",
    "Bellagio Hotel", "Venetian Resort",
    "Freedom Trail", "Fenway Park", "Museum of Fine Arts",
]

# ---------------------------------------------------------------------------
# Patterns
# ---------------------------------------------------------------------------
# Each entry: (template, task_type).  {l}/{l2}/{a}/{b} get substituted.
R6_TASK_PATTERNS = [
    # ---- cross-page: search -> place -> /menu ----
    ("Open {l}, view its menu, and tell me the price of the most expensive entree.", "cross-page-menu"),
    ("Find {l}, open the menu page, and list 3 vegetarian items.", "cross-page-menu"),
    ("Search for {l}, open its booking page, and read the booking confirmation message after submitting a 2-person 7pm reservation.", "cross-page-booking"),
    ("Find {l}, open the booking page, and submit a reservation for 4 people tomorrow at 6:30pm.", "cross-page-booking"),
    # ---- cross-page: place -> /photos ----
    ("Find {l}, open its photo gallery, and tell me how many sections it has.", "cross-page-photos"),
    ("Open {l} and tell me the caption of the first hero photo.", "cross-page-photos"),
    # ---- cross-page: place -> /reviews ----
    ("Open {l}, scroll to the reviews section, and report the top reviewer's rating.", "cross-page-reviews"),
    ("Find {l}, open the place page, and count how many reviews are shown in the default panel.", "cross-page-reviews"),
    ("Search for {l}, open its detail page, and read the 'Reviewers also visited' section — list 3 places shown.", "cross-page-reviews"),
    # ---- cross-page: place -> /accessibility ----
    ("Find {l}, open the accessibility page, and list every wheelchair-related feature shown.", "cross-page-accessibility"),
    ("Open {l}, go to /accessibility, and tell me the accessibility score.", "cross-page-accessibility"),
    # ---- cross-page: place -> /share QR ----
    ("Find {l}, open the QR share page, and copy the shareable URL.", "cross-page-qr"),
    ("Open the QR code for {l} and tell me the share URL.", "cross-page-qr"),
    # ---- cross-page: place -> /directions ----
    ("Search for {l}, open its detail page, then plan walking directions to {l2}.", "cross-page-directions"),
    ("Find {l}, open the place page, and get driving directions from {l2}.", "cross-page-directions"),
    # ---- cross-page: place -> Save to list ----
    ("Find {l}, save it to your Favorites list, then open /your-places/saved to confirm.", "cross-page-save"),
    ("Search for {l}, save it to a new list called 'Trip ideas', then view the list.", "cross-page-save"),
    # ---- cross-page: long chain (search -> place -> menu -> directions -> share) ----
    ("Find {l}, open its menu, then plan directions from {l2}, and finally share the place via QR.", "cross-page-chain"),
    ("Search for {l}, view its photos, then read the first review, then save it to a list.", "cross-page-chain"),
    ("Find {l}, open booking, check the accessibility page, then share the QR code.", "cross-page-chain"),
    ("Open {l}, view the menu, save the place, then plan directions from {l2}.", "cross-page-chain"),
    # ---- multi-step day-trip with directions between stops ----
    ("Plan a day trip in {a} with 5 stops; show directions between each pair of consecutive stops.", "day-trip-5-stops"),
    ("Plan a 5-stop day trip in {a} starting at {l}, visiting another 4 places, with walking directions between each.", "day-trip-5-stops"),
    ("Plan a 5-stop {a} foodie day with brunch, lunch, coffee break, dinner, dessert; show driving directions between each.", "day-trip-5-stops"),
    ("Plan a 5-stop museum day in {a}; show transit directions between each museum.", "day-trip-5-stops"),
    ("Plan a 5-stop accessibility-friendly tour in {a} — show wheelchair-friendly directions between each.", "day-trip-5-stops"),
    # ---- R6 same-chain ----
    ("Find {l}, open it, and tell me which other locations of the same chain appear in 'From the same chain'.", "cross-page-chain-rail"),
    ("Search for {l}, open its detail page, and list 3 other branches from the same chain.", "cross-page-chain-rail"),
    # ---- R6 better-rated-1mi ----
    ("Open {l} and read the 'Better-rated within 1 mi' rail — name 2 alternatives.", "cross-page-better-rated"),
    ("Find {l}, scroll to the 'Better-rated within 1 mi' section, and pick the highest-rated option.", "cross-page-better-rated"),
    # ---- R6 reviewers-also-visited ----
    ("Open {l} and report what 'Reviewers also visited' suggests as the top option.", "cross-page-reviewers-also"),
    # ---- R6 similar-nearby ----
    ("Find {l}, open it, and list 3 'Similar nearby' places shown within 15 mi.", "cross-page-similar-nearby"),
    # ---- R6 breadcrumb / navigation ----
    ("Open {l} and read its breadcrumb trail — what category and city are shown?", "cross-page-breadcrumb"),
    # ---- R6 edge: permanently closed banner ----
    ("Find a place in {a} that is permanently closed and tell me the reason shown on the banner.", "edge-permanently-closed"),
    ("Are there any permanently closed places near {l}? Open one and report the closure reason.", "edge-permanently-closed"),
    # ---- R6 edge: temporarily closed ----
    ("Find a temporarily closed place in {a} and tell me when it reopens.", "edge-temporarily-closed"),
    ("Open a place with a temporary closure banner; report the reopen date.", "edge-temporarily-closed"),
    # ---- R6 edge: directions no-route-found ----
    ("Plan walking directions from {l} to a destination across the ocean; report the no-route-found banner.", "edge-no-route-found"),
    ("Plan transit directions from {a} to {b} (long-haul); see if a no-route-found suggestion appears.", "edge-no-route-found"),
    # ---- R6 edge: transit no service after hours ----
    ("Open the realtime transit dashboard; list any line marked 'no service after hours'.", "edge-transit-no-service"),
    ("Filter realtime transit to {a} and tell me which lines are showing 'no service' tonight.", "edge-transit-no-service"),
    # ---- R6 edge: indoor floor not mapped ----
    ("Find a multi-floor venue in {a} whose floor plan is marked 'not yet mapped' and tell me the venue's name.", "edge-floor-unmapped"),
    ("Open a place's /floors page and report whether the indoor floor plan banner is shown.", "edge-floor-unmapped"),
    # ---- R6 edge: place not accessible warning ----
    ("Find a place in {a} that displays an accessibility warning banner and report what the warning says.", "edge-a11y-warning"),
    ("Open {l}'s detail page and check if there's an accessibility notice — if so, what does it say?", "edge-a11y-warning"),
    # ---- R6 cross-page: account / settings / lists ----
    ("Sign in as alice.j@test.com, open /your-places/saved, then open the first saved place's detail page.", "cross-page-account"),
    ("Sign in as bob.c@test.com, open /lists, pick the 'Hidden Gems' list, then open one of its places.", "cross-page-account"),
    ("Sign in as carol.d@test.com, open /trips, pick 'NYC Fall Visit', then open the first stop's place detail.", "cross-page-account"),
    # ---- R6 cross-page: search -> filter -> place -> directions ----
    ("Search for coffee shops in {a}, filter to quiet noise level, open the top result, then get walking directions from {l}.", "cross-page-filter-flow"),
    ("Search for restaurants in {a} with reservations, open the top match, view the menu, and book a table for 2.", "cross-page-filter-flow"),
    ("Search for hotels in {a} with EV charging, open one, check accessibility features, then save it to a list.", "cross-page-filter-flow"),
    # ---- R6 cross-page: explore -> category -> city ----
    ("Open /explore, click into the Coffee Shops category, drill into {a}, then open the top-rated coffee shop.", "cross-page-explore"),
    ("Open /explore, drill into the Hotels category for {a}, then open the highest-rated hotel.", "cross-page-explore"),
    # ---- R6 cross-page: trip-edit flow ----
    ("Sign in as alice.j@test.com, open /trips, edit 'Chicago Weekend', and add {l} as a new stop.", "cross-page-trip-edit"),
    ("Sign in as bob.c@test.com, open the Tokyo Tech Tour trip, and remove the last stop.", "cross-page-trip-edit"),
    # ---- R6 cross-page: review submission ----
    ("Sign in as david.k@test.com, open {l}, scroll to reviews, and submit a 5-star review titled 'Loved it'.", "cross-page-review-write"),
    # ---- R6 cross-page: photo upload (form view) ----
    ("Open {l}, scroll to the photo gallery, and report whether a contributor-upload control is visible.", "cross-page-photo-form"),
    # ---- R6 cross-page: timeline ----
    ("Sign in as alice.j@test.com, open /timeline, pick the most recent date with entries, and list each visit.", "cross-page-timeline"),
    ("Sign in as bob.c@test.com, open /your-data/export, download the JSON, and tell me how many entries it has.", "cross-page-timeline-export"),
]


def pair_anchors(i):
    a = ANCHOR_CITIES[i % len(ANCHOR_CITIES)]
    b = ANCHOR_CITIES[(i * 11 + 5) % len(ANCHOR_CITIES)]
    if b == a:
        b = ANCHOR_CITIES[(i + 1) % len(ANCHOR_CITIES)]
    return a, b


def pair_landmarks(i):
    l = LANDMARKS[i % len(LANDMARKS)]
    l2 = LANDMARKS[(i * 13 + 7) % len(LANDMARKS)]
    if l2 == l:
        l2 = LANDMARKS[(i + 1) % len(LANDMARKS)]
    return l, l2


def main():
    existing = []
    if TASKS_FILE.exists():
        with open(TASKS_FILE, "r") as f:
            existing = [json.loads(line) for line in f if line.strip()]

    max_id = -1
    have_r6 = False
    R6_PREFIXES = (
        "cross-page-", "day-trip-", "edge-",
    )
    for t in existing:
        try:
            n = int(t["id"].rsplit("--", 1)[1])
            max_id = max(max_id, n)
        except (ValueError, IndexError, KeyError):
            continue
        if t.get("task_type", "").startswith(R6_PREFIXES):
            have_r6 = True

    if have_r6:
        print("R6 tasks already appended — skipping")
        return

    # Generate enough variations so total >= 2500.
    target_total = 2500
    target_new = max(1000, target_total - len(existing))
    new_tasks = []
    i = 0
    pat_idx = 0
    while len(new_tasks) < target_new:
        a, b = pair_anchors(i)
        l, l2 = pair_landmarks(i)
        pattern, task_type = R6_TASK_PATTERNS[pat_idx % len(R6_TASK_PATTERNS)]
        ques = (pattern
                .replace("{a}", a)
                .replace("{b}", b)
                .replace("{l2}", l2)
                .replace("{l}", l))
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
    print(f"Appended {len(new_tasks)} R6 tasks. Total: {len(existing) + len(new_tasks)}")


if __name__ == "__main__":
    main()
