"""Generate R9 task additions for tasks.jsonl.

Targets the R9 outdoor verticals + permit/geocache flows:
  - trail-difficulty-filter: /trail/<id>, /trail/<id>/difficulty
  - beach-water-quality-check: /beach/<id>/water-quality
  - lighthouse-tour: /lighthouse/<id>
  - scenic-byway-route: /scenic-byway/<route>
  - national-park-permit-request: /park/<id>/permit-request (POST)
  - geocache-find: /geocache and /geocache/<id>
  - r9-multi-step: chain trail → difficulty → review,
                    geocache index → detail → place,
                    park → permit POST → ack id, etc.

Deterministic, append-only, idempotent.  Re-running detects an R9 prefix
already in tasks.jsonl and exits cleanly.
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
    "Long Beach", "Virginia Beach", "Myrtle Beach", "Daytona Beach",
    "Miami Beach",
]

CITY_SLUGS = [c.lower().replace(" ", "-") + "-ny" if c == "New York"
              else c.lower().replace(" ", "-") for c in ANCHOR_CITIES]

# Trail bases that we know expand_places_r9 emits.  Matching by stem keeps
# tasks resolvable to a real slug (r9-trail-<city>-NNN matches some city).
TRAIL_BASES = [
    "Ridge Loop Trail", "Summit Trail", "Canyon Rim Trail",
    "Waterfall Loop Trail", "Bluff Overlook Trail", "Creekside Trail",
    "Pine Forest Trail", "Granite Dome Trail", "Alpine Meadow Trail",
    "Cascade Falls Trail", "Marsh Boardwalk", "Glacial Cirque Trail",
    "Sunset Ridge Trail", "Aspen Grove Trail", "Eagle Vista Trail",
    "Hidden Valley Trail", "Wildflower Loop", "Riverbend Trail",
    "Skyline Ridge Trail", "Lighthouse Point Trail", "Three Sisters Loop",
]

BEACH_BASES = [
    "Driftwood Cove Beach", "Long Strand Public Beach", "Pelican Point Beach",
    "Crescent Bay Beach", "Surfside Public Beach", "Tidepool Cove",
    "Northshore Beach", "Reef Point Beach", "Saltwater State Beach",
    "Lighthouse Point Beach", "Boardwalk Public Beach", "Sunset Public Beach",
    "Sunrise State Beach", "Marina Beach", "Dunes Public Beach",
]

LIGHTHOUSE_BASES = [
    "Point Lighthouse", "Cape Lighthouse", "Harbor Lighthouse",
    "Old Bay Lighthouse", "Inlet Lighthouse", "North Point Light",
    "South Cape Light", "Twin Light Station", "Outer Banks Light",
    "Whaler's Lighthouse",
]

BYWAY_BASES = [
    "Coastal Heritage Scenic Byway", "Lighthouse Loop Byway",
    "Mountain Crest Byway", "Wine Country Byway", "Big River Byway",
    "Glacier Trail Byway", "Forest Loop Byway", "Pioneer Trail Byway",
    "Painted Cliffs Byway",
]

GEOCACHE_BASES = [
    "Old Oak Cache", "Lighthouse Step Cache", "Hidden Fern Cache",
    "Roadside Marker Cache", "Park Bench Cache", "Trailhead Cache",
    "Hollow Log Cache", "Bridge Pillar Cache", "Cliff Edge Cache",
    "Boulder Top Cache", "Ridge Cairn Cache", "Tide Pool Cache",
]

PARK_BASES = [
    "Riverside Heritage Park", "Pioneer Memorial Park", "Old Quarry State Park",
    "Painted Cliffs State Park", "Big Cedar State Park", "Sequoia Sentinel Park",
    "Wild River State Park", "Twin Lakes State Park", "Coastal Bluffs State Park",
    "Granite Dome Park", "High Desert State Park", "Sandstone Arch State Park",
]

CHAINS = [
    "Blank Street Coffee", "Devocion Coffee Bar", "Joe & The Juice",
    "Pret A Manger", "Sweetgreen Outpost", "Cava Mezze Grill",
    "Five Guys", "Shake Shack Curbside", "MOD Pizza", "Cane's Curbside Window",
]

GEO_SIZES = ["micro", "small", "regular"]
CACHE_TYPES = ["traditional", "multi", "puzzle", "earth"]
WATER_QUALITIES = ["excellent", "good", "fair", "advisory"]
TRAIL_DIFFICULTIES = ["easy", "moderate", "hard"]
BYWAY_THEMES = ["coastal", "mountain", "river", "heritage", "wine", "glacier",
                "forest", "desert"]


def _slug_for(city, base, kind):
    """Build the R9 expansion slug for testing.  We only need a probe — agents
    will follow real slugs from the listing pages."""
    csl = city.lower().replace(" ", "-")
    if csl in ("new-york", "los-angeles"):
        csl += "-" + ("ny" if csl == "new-york" else "ca")
    return f"r9-{kind}-{csl}"


# Each entry: (template, task_type)
R9_TASK_PATTERNS = [
    # ---- Trail difficulty filter ----
    ("Open /trail/{trail_slug} for {l}; report the trail's overall difficulty rating.",
     "r9-trail-difficulty-filter"),
    ("Visit /trail/{trail_slug}/difficulty and list how many trail sections are shown with their per-section difficulty.",
     "r9-trail-difficulty-filter"),
    ("From the homepage search for '{tb}' in {a}; open the first matching trail and capture its length (mi) and elevation gain.",
     "r9-trail-difficulty-filter"),
    ("Open /trail/{trail_slug}?format=json and verify the JSON payload includes difficulty, length_mi, and elevation_gain_ft fields.",
     "r9-trail-difficulty-filter"),
    ("Find a {diff}-rated trail in {a}; open its difficulty breakdown page and report the grade % of its 'Ascent' section.",
     "r9-trail-difficulty-filter"),
    ("Visit /trail/{trail_slug}/difficulty and verify the page links back to the trail's place_detail.",
     "r9-trail-difficulty-filter"),
    ("Open /trail/{trail_slug}, follow the 'Difficulty' link, and confirm the breakdown lists Approach / Ascent / Summit sections.",
     "r9-trail-difficulty-filter"),
    # ---- Beach water-quality check ----
    ("Open /beach/{beach_slug}/water-quality for {l}; report the latest water-quality rating.",
     "r9-beach-water-quality-check"),
    ("Visit /beach/{beach_slug}/water-quality and capture the enterococci MPN/100 mL value.",
     "r9-beach-water-quality-check"),
    ("Open /beach/{beach_slug}/water-quality?format=json and verify the JSON includes 'sampled_at' and 'advisory'.",
     "r9-beach-water-quality-check"),
    ("Find a beach in {a} with an 'advisory' water-quality rating; report its slug.",
     "r9-beach-water-quality-check"),
    ("Locate {bb} in {a}; open its water-quality page and report the agency name.",
     "r9-beach-water-quality-check"),
    ("Open /beach/{beach_slug}/water-quality and verify the advisory flag is consistent with the rating field.",
     "r9-beach-water-quality-check"),
    # ---- Lighthouse tour ----
    ("Open /lighthouse/{light_slug} for {l}; report the tower height in feet.",
     "r9-lighthouse-tour"),
    ("Visit /lighthouse/{light_slug} and capture the construction year listed.",
     "r9-lighthouse-tour"),
    ("Open /lighthouse/{light_slug}?format=json and verify the 'tour_duration' field is one of 30/45/60/90 minutes.",
     "r9-lighthouse-tour"),
    ("Find a lighthouse in {a} taller than 100 ft; report its name and built year.",
     "r9-lighthouse-tour"),
    ("Open the lighthouse page for {lhb} in {a}; verify the tour is open.",
     "r9-lighthouse-tour"),
    ("Visit /lighthouse/{light_slug} and verify the page links back to the place_detail.",
     "r9-lighthouse-tour"),
    # ---- Scenic byway ----
    ("Open /scenic-byway/{byway_slug} for {a}; report the loop length in miles and the number of pullouts.",
     "r9-scenic-byway-route"),
    ("Visit /scenic-byway/{byway_slug} and capture the byway theme.",
     "r9-scenic-byway-route"),
    ("Open /scenic-byway/{byway_slug}?format=json and verify it includes loop_miles, pullouts, and theme.",
     "r9-scenic-byway-route"),
    ("Find a '{theme}'-themed scenic byway in {a}; report its name.",
     "r9-scenic-byway-route"),
    ("Open /scenic_byway/{byway_slug} (alias) and verify it matches the canonical /scenic-byway/ page.",
     "r9-scenic-byway-route"),
    ("Open /scenic-byway/{byway_slug} and verify the page lists 'Audio tour: Yes' in the field list.",
     "r9-scenic-byway-route"),
    # ---- National park permit request ----
    ("GET /park/{park_slug}/permit-request for {a}; report the required form fields.",
     "r9-national-park-permit-request"),
    ("POST /park/{park_slug}/permit-request with purpose='Family picnic', party_size=8, date='2026-06-15'; report the returned ack_id.",
     "r9-national-park-permit-request"),
    ("POST /park/{park_slug}/permit-request twice with identical fields; verify the ack_id is identical (deterministic).",
     "r9-national-park-permit-request"),
    ("POST /park/{park_slug}/permit-request with party_size=400; verify the response caps party_size at 500.",
     "r9-national-park-permit-request"),
    ("POST /park/{park_slug}/permit-request with purpose='Astronomy night', party_size=12, date='2026-07-04'; verify status='queued'.",
     "r9-national-park-permit-request"),
    ("POST /park/{park_slug}/permit-request?format=json with purpose='Group hike', party_size=20, date='2026-08-02'; verify the JSON includes 'ack_id' starting with 'permit-'.",
     "r9-national-park-permit-request"),
    ("Find a park named {pb} in {a}; GET its permit-request page and confirm Method=POST is listed.",
     "r9-national-park-permit-request"),
    # ---- Geocache find ----
    ("Open /geocache?city={city_slug}&limit=10; report how many caches are returned.",
     "r9-geocache-find"),
    ("Open /geocache?size={size}&limit=20 and verify all results have size='{size}'.",
     "r9-geocache-find"),
    ("Open /geocache?city={city_slug}&size={size} and confirm the filter labels appear in the page subtitle.",
     "r9-geocache-find"),
    ("Open /geocache/{cache_slug} and report the difficulty and terrain ratings.",
     "r9-geocache-find"),
    ("Open /geocache/{cache_slug}?format=json and verify cache_type is one of traditional/multi/puzzle/earth.",
     "r9-geocache-find"),
    ("Find a 'puzzle' geocache in {a}; open its detail page and report its found_count.",
     "r9-geocache-find"),
    ("Open /geocache?limit=5 and verify each item has a 'href' that points to /geocache/<slug>.",
     "r9-geocache-find"),
    ("Open /geocache?city={city_slug}&size=micro&limit=3 and confirm the count matches the filter.",
     "r9-geocache-find"),
    # ---- R9 multi-step (cross-page) ----
    ("Open /geocache?city={city_slug}; pick the first cache; open its detail; then write a 5-star review titled 'r9-cache' as bob.c@test.com.",
     "r9-multi-step"),
    ("Open /trail/{trail_slug}, follow the Difficulty link, then return to the place_detail and confirm the rating is unchanged.",
     "r9-multi-step"),
    ("Open /beach/{beach_slug}/water-quality, follow the 'back to place' link, then sub-page /place/<slug>/popular-times and report its busiest day.",
     "r9-multi-step"),
    ("Open /lighthouse/{light_slug}, follow the back link to the place page, then open its accessibility page.",
     "r9-multi-step"),
    ("Open /park/{park_slug}/permit-request, POST a request, then open the park's place_detail and confirm the place still loads.",
     "r9-multi-step"),
    ("Open /scenic-byway/{byway_slug}, follow the back link, then save the place to your 'Want to go' list as alice.j@test.com.",
     "r9-multi-step"),
    ("Open /geocache, pick a cache in {a}, open its detail, then open the parent place and check the place_detail rating.",
     "r9-multi-step"),
    ("Open /trail/{trail_slug}/difficulty?format=json, capture the overall_difficulty, then open /trail/{trail_slug} and confirm the field matches.",
     "r9-multi-step"),
    # ---- API/JSON probes ----
    ("POST /api/v2/places/graphql with `{{ places(filter:{{query:\"trail\"}}, limit:5){{ slug }} }}`; verify all 5 slugs contain 'trail'.",
     "r9-multi-step"),
    ("POST /api/v2/places/graphql for `{{ places(filter:{{category:\"beaches\"}}, limit:3){{ slug name }} }}`; verify all 3 are beaches.",
     "r9-multi-step"),
]


def pair_anchors(i):
    a = ANCHOR_CITIES[i % len(ANCHOR_CITIES)]
    b = ANCHOR_CITIES[(i * 11 + 5) % len(ANCHOR_CITIES)]
    if b == a:
        b = ANCHOR_CITIES[(i + 1) % len(ANCHOR_CITIES)]
    return a, b


def main():
    existing = []
    if TASKS_FILE.exists():
        with open(TASKS_FILE, "r") as f:
            existing = [json.loads(line) for line in f if line.strip()]

    max_id = -1
    have_r9 = False
    R9_PREFIXES = (
        "r9-trail-difficulty-", "r9-beach-water-quality-",
        "r9-lighthouse-", "r9-scenic-byway-",
        "r9-national-park-permit-", "r9-geocache-find",
        "r9-multi-step",
    )
    for t in existing:
        try:
            n = int(t["id"].rsplit("--", 1)[1])
            max_id = max(max_id, n)
        except (ValueError, IndexError, KeyError):
            continue
        if t.get("task_type", "").startswith(R9_PREFIXES):
            have_r9 = True

    if have_r9:
        print("R9 tasks already appended — skipping")
        return

    target_total = 4700
    target_new = max(700, target_total - len(existing))
    new_tasks = []
    i = 0
    pat_idx = 0
    while len(new_tasks) < target_new:
        a, b = pair_anchors(i)
        a_slug = a.lower().replace(" ", "-")
        # Pick a deterministic R9 expansion slug (city,index) probe.  Many
        # cities have these so any valid (kind,city) pair resolves.
        city_slug = CITY_SLUGS[i % len(CITY_SLUGS)]
        idx_pad = f"{i % 200:03d}"
        trail_slug = f"r9-trail-{city_slug}-{idx_pad}"
        beach_slug = f"r9-beach-{city_slug}-{idx_pad}"
        light_slug = f"r9-lighthouse-{city_slug}-{idx_pad}"
        byway_slug = f"r9-byway-{city_slug}-{idx_pad}"
        cache_slug = f"r9-geocache-{city_slug}-{idx_pad}"
        park_slug = f"r9-park-{city_slug}-{idx_pad}"

        tb = TRAIL_BASES[i % len(TRAIL_BASES)]
        bb = BEACH_BASES[i % len(BEACH_BASES)]
        lhb = LIGHTHOUSE_BASES[i % len(LIGHTHOUSE_BASES)]
        bwb = BYWAY_BASES[i % len(BYWAY_BASES)]
        gcb = GEOCACHE_BASES[i % len(GEOCACHE_BASES)]
        pb = PARK_BASES[i % len(PARK_BASES)]
        chain = CHAINS[i % len(CHAINS)]
        diff = TRAIL_DIFFICULTIES[i % len(TRAIL_DIFFICULTIES)]
        wq = WATER_QUALITIES[i % len(WATER_QUALITIES)]
        theme = BYWAY_THEMES[i % len(BYWAY_THEMES)]
        size = GEO_SIZES[i % len(GEO_SIZES)]
        ctype = CACHE_TYPES[i % len(CACHE_TYPES)]
        # Use a stable landmark name for "{l}" — pick by trail base for trail
        # tasks; otherwise fall back to anchor city name.
        l = tb if "trail" in tb.lower() else f"{a} Park"

        pattern, task_type = R9_TASK_PATTERNS[pat_idx % len(R9_TASK_PATTERNS)]
        ques = (pattern
                .replace("{a_slug}", a_slug)
                .replace("{city_slug}", city_slug)
                .replace("{trail_slug}", trail_slug)
                .replace("{beach_slug}", beach_slug)
                .replace("{light_slug}", light_slug)
                .replace("{byway_slug}", byway_slug)
                .replace("{cache_slug}", cache_slug)
                .replace("{park_slug}", park_slug)
                .replace("{tb}", tb)
                .replace("{bb}", bb)
                .replace("{lhb}", lhb)
                .replace("{bwb}", bwb)
                .replace("{gcb}", gcb)
                .replace("{pb}", pb)
                .replace("{chain}", chain)
                .replace("{diff}", diff)
                .replace("{wq}", wq)
                .replace("{theme}", theme)
                .replace("{size}", size)
                .replace("{ctype}", ctype)
                .replace("{a}", a)
                .replace("{b}", b)
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
    print(f"Appended {len(new_tasks)} R9 tasks. Total: {len(existing) + len(new_tasks)}")


if __name__ == "__main__":
    main()
