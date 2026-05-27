"""Generate R10 task additions for tasks.jsonl.

Targets the R10 quality-polish themes:
  - 8-step compound journey: search → place → directions → save → review →
    photo → share → timeline.  Each compound task pins 1-3 deterministic
    steps so the agent can be graded on intermediate state.
  - Cross-city / cross-country multi-stop travel itineraries.
  - International landmark / ski / dive / hostel / coliving / accessibility
    / bike-share probes against the new R10 verticals.
  - Expanded transit-line coverage (probe new /transit/lines/<slug> slugs).

Deterministic, append-only, idempotent.  Re-running detects an R10 prefix
already in tasks.jsonl and exits cleanly.
"""
import json
from pathlib import Path

BASE = Path(__file__).parent
TASKS_FILE = BASE / "tasks.jsonl"
WEB_URL = "http://localhost:40008/"
UPSTREAM = "https://www.google.com/maps/"

# Anchor cities used for the {a}/{b} substitution and for the city_slug.
ANCHOR_CITIES = [
    ("New York", "new-york"),
    ("Los Angeles", "los-angeles"),
    ("Chicago", "chicago"),
    ("San Francisco", "san-francisco"),
    ("Seattle", "seattle"),
    ("Boston", "boston"),
    ("Washington DC", "washington"),
    ("Miami", "miami"),
    ("London", "london"),
    ("Paris", "paris"),
    ("Tokyo", "tokyo"),
    ("Singapore", "singapore"),
    ("Hong Kong", "hong-kong"),
    ("Toronto", "toronto"),
    ("Sydney", "sydney"),
    ("Berlin", "berlin"),
    ("Madrid", "madrid"),
    ("Barcelona", "barcelona"),
    ("Rome", "rome"),
    ("Amsterdam", "amsterdam"),
    ("Vienna", "vienna"),
    ("Prague", "prague"),
    ("Istanbul", "istanbul"),
    ("Beijing", "beijing"),
    ("Dubai", "dubai"),
    ("Mumbai", "mumbai"),
    ("Las Vegas", "las-vegas"),
    ("Atlanta", "atlanta"),
    ("Denver", "denver"),
    ("Portland", "portland"),
]

# Slugs follow the seed naming convention r10-<kind>-<city_slug>-<idx>.
# Indices are the template position in the unified expand_places_r10 stream,
# NOT a per-kind 0-based counter.  Real ranges per kind:
#   intl       000-029 (30 templates)
#   ski        030-049 (20 templates)
#   dive       050-069 (20 templates)
#   hostel     070-089 (20 templates)
#   coliving   090-104 (15 templates)
#   accessible 105-119 (15 templates)
#   bikeshare  120-132 (13 templates)
#   chain      133-144 (12 templates)
R10_KIND_RANGES = {
    "intl":       (0, 29),
    "ski":        (30, 49),
    "dive":       (50, 69),
    "hostel":     (70, 89),
    "coliving":   (90, 104),
    "accessible": (105, 119),
    "bikeshare":  (120, 132),
    "chain":      (133, 144),
}
R10_KINDS = list(R10_KIND_RANGES.keys())

# Transit-line slugs added in expand_transit_lines_r10 (a representative
# subset; the agent can discover full set from /transit/lines).
R10_TRANSIT_SLUGS = [
    "mta-2-train", "mta-7-train", "mta-a-train", "mta-m23-sbs",
    "muni-j-church", "muni-k-ingleside", "muni-t-third", "bart-blue-line",
    "mbta-blue-line", "mbta-orange-line", "mbta-green-c", "mbta-green-d",
    "cta-green-line", "cta-brown-line", "cta-orange-line", "cta-pink-line",
    "wmata-blue", "wmata-orange", "wmata-silver",
    "sound-transit-2-line", "sound-transit-t-line", "king-county-rapidride-e",
    "metro-a-line", "metro-e-line", "metro-g-line", "metro-k-line",
    "metrorail-green", "metromover-inner", "metrobus-202",
    "tfl-piccadilly", "tfl-victoria", "tfl-elizabeth", "tfl-bus-25",
    "ratp-metro-1", "ratp-metro-14", "ratp-rer-a",
    "jr-yamanote", "tokyo-metro-marunouchi", "toei-oedo",
    "mrt-north-south", "mrt-circle", "mrt-east-west",
    "mtr-island-line", "mtr-tsuen-wan-line",
    "ttc-line-1", "ttc-line-2", "ttc-streetcar-501",
    "sydney-t1-north-shore", "sydney-metro-north-west", "sydney-light-rail-l1",
]

R10_BUS_SLUG_CITIES = [
    "new-york", "san-francisco", "boston", "chicago", "washington",
    "seattle", "los-angeles", "miami", "london", "paris", "tokyo",
    "singapore", "toronto", "sydney",
]


# Each entry: (template, task_type).
# Compound 8-step journey templates pin one or two intermediate steps so
# the agent has to actually navigate through.  Cross-city itinerary templates
# call for multi-stop directions.
R10_TASK_PATTERNS = [
    # ---- 8-step compound: search → place → directions → save → review →
    #      photo → share → timeline ----
    ("Search for '{kind_label}' in {a}, open the first matching place, "
     "then GET /directions?from={a}+downtown&to=<slug> and capture the "
     "estimated driving time.",
     "r10-compound-search-directions"),
    ("Search for '{kind_label}' near {a}, open one result, save it to "
     "your 'Want to go' list as alice.j@test.com, and confirm the place "
     "appears under /your-places.",
     "r10-compound-search-save"),
    ("Search for '{kind_label}' in {a}, open the first matching place, "
     "write a 4-star review titled 'r10-compound' as bob.c@test.com, "
     "then verify the review shows on /place/<slug>.",
     "r10-compound-search-review"),
    ("Open /place/{slug}, follow the photo gallery, then visit "
     "/place/{slug}/popular-times and report the busiest day.",
     "r10-compound-place-photo"),
    ("Open /place/{slug}, then open /place/{slug}/qr and capture the "
     "share URL listed on the QR page.",
     "r10-compound-place-share"),
    ("Save /place/{slug} to your 'Favorites' list as carol.k@test.com, "
     "open /timeline, and verify the saved place is reflected in your "
     "timeline.",
     "r10-compound-save-timeline"),
    ("Open /search?q={kind_label}+in+{a}; pick result #1; open "
     "/directions?from={a}+downtown&to=<slug>; save the destination to "
     "your 'Want to go' list as alice.j@test.com.",
     "r10-compound-search-directions-save"),
    ("Search for '{kind_label}' in {a}; open the first place; "
     "POST a 5-star review titled 'r10-test' as bob.c@test.com; "
     "open /place/<slug>/qr and report the share URL.",
     "r10-compound-search-review-share"),
    ("Open /place/{slug}, save it to a list named 'r10-trip-{a_slug}' "
     "as carol.k@test.com, then verify the list shows the saved place.",
     "r10-compound-place-save-list"),
    ("Open /place/{slug}, post a 4-star review as bob.c@test.com, then "
     "open /timeline and confirm the review activity is visible.",
     "r10-compound-review-timeline"),

    # ---- Cross-city / cross-country multi-stop directions ----
    ("Plan a multi-stop drive from {a} → {b} via /directions?from={a}&to={b} "
     "and report the total estimated driving time.",
     "r10-multi-stop-directions"),
    ("Plan a transit route from {a} downtown to {b} airport using "
     "/directions?from={a}+downtown&to={b}+airport&mode=transit and report "
     "the estimated duration.",
     "r10-multi-stop-directions"),
    ("Plan a bicycling route from {a} to {b} via "
     "/directions?from={a}&to={b}&mode=bicycling and report the distance.",
     "r10-multi-stop-directions"),
    ("Plan a walking route from {a} central station to {a} botanic gardens "
     "via /directions?from={a}+central&to={a}+botanic+gardens&mode=walking; "
     "report the walking duration.",
     "r10-multi-stop-directions"),
    ("Open /directions?from={a}&to={b}&mode=driving and capture three "
     "alternative routes; report the shortest by distance.",
     "r10-multi-stop-directions"),

    # ---- International landmark vertical probes ----
    ("Open /place/{intl_slug} for {a}; report the place rating and the "
     "first photo URL listed on the page.",
     "r10-intl-landmark"),
    ("Search for 'Old Town Square Heritage Walk' in {a}; open the first "
     "result and confirm the place_detail loads.",
     "r10-intl-landmark"),
    ("Open /place/{intl_slug}/popular-times and report the busiest hour.",
     "r10-intl-landmark"),
    ("Open /place/{intl_slug} and verify the address field contains "
     "'{a}'.",
     "r10-intl-landmark"),

    # ---- Ski-resort vertical probes ----
    ("Open /place/{ski_slug} for {a}; report the parking_lot_capacity "
     "field if listed on the page.",
     "r10-ski-resort"),
    ("Search for 'Ski Resort' in {a}; open the first match and confirm "
     "the category is attractions.",
     "r10-ski-resort"),
    ("Open /place/{ski_slug} and verify accepts_reservations is true.",
     "r10-ski-resort"),
    ("Find a ski resort in {a}; report its name and price level.",
     "r10-ski-resort"),

    # ---- Dive-site vertical probes ----
    ("Open /place/{dive_slug} for {a}; report the operator phone listed.",
     "r10-dive-site"),
    ("Search for 'dive site' near {a}; open the first result and confirm "
     "the subtitle contains 'dive'.",
     "r10-dive-site"),
    ("Open /place/{dive_slug} and verify the place rating is between "
     "4.3 and 4.9.",
     "r10-dive-site"),

    # ---- Hostel vertical probes ----
    ("Open /place/{hostel_slug} for {a}; report the price_level.",
     "r10-hostel"),
    ("Search for 'hostel' in {a}; open the first match and verify the "
     "category is hotels.",
     "r10-hostel"),
    ("Open /place/{hostel_slug} and verify serves_breakfast is true.",
     "r10-hostel"),

    # ---- Coliving vertical probes ----
    ("Open /place/{coliving_slug} for {a}; verify subcategory contains "
     "'coliving'.",
     "r10-coliving"),
    ("Search for 'co-live' in {a}; open the first match and report its "
     "address.",
     "r10-coliving"),
    ("Open /place/{coliving_slug} and verify accepts_reservations is true.",
     "r10-coliving"),

    # ---- Accessibility vertical probes ----
    ("Open /place/{accessible_slug} for {a}; verify "
     "wheelchair_accessible_entrance is true on the page.",
     "r10-accessibility"),
    ("Search for 'accessible' in {a}; open the first match and confirm "
     "the accessibility score is listed.",
     "r10-accessibility"),
    ("Open /place/{accessible_slug} and verify has_service_animal_welcome "
     "is true.",
     "r10-accessibility"),
    ("Find an 'Accessible Public Library Branch' in {a}; open its page "
     "and report the wheelchair_accessible_restroom flag.",
     "r10-accessibility"),

    # ---- Bike-share vertical probes ----
    ("Open /place/{bike_slug} for {a}; report the price_level and "
     "bicycle_parking field.",
     "r10-bikeshare"),
    ("Search for 'bike-share' in {a}; open the first match and verify "
     "bicycle_parking is true.",
     "r10-bikeshare"),
    ("Open /place/{bike_slug} and verify the category is services.",
     "r10-bikeshare"),

    # ---- New R10 chain probes ----
    ("Search for 'Notes Coffee Co.' in {a}; open the first result and "
     "report its rating.",
     "r10-chain"),
    ("Search for 'Honest Crust Pizza' in {a}; open the first matching "
     "place and verify the chain_brand field.",
     "r10-chain"),
    ("Open /search?q=Origin+Coffee+Roasters+{a_slug}; pick the first "
     "result; verify its category is coffee-shops.",
     "r10-chain"),
    ("Search for 'Dishoom Counter' in {a}; open the first match and "
     "report its address.",
     "r10-chain"),

    # ---- Transit line probes (route 200 check) ----
    ("Open /transit/lines/{transit_slug}; verify the page renders and "
     "report the line's agency.",
     "r10-transit-line"),
    ("Open /transit/lines/{transit_slug} and count the number of stops "
     "listed.",
     "r10-transit-line"),
    ("Open /transit/lines/{transit_slug} and report the operating hours.",
     "r10-transit-line"),
    ("Open /transit/lines/{transit_slug} and report the off-peak "
     "frequency listed.",
     "r10-transit-line"),
    ("Open /transit/lines/r10-bus-{bus_city_slug}-00 and verify the "
     "page renders with the X1 crosstown express label.",
     "r10-transit-line-bus"),
    ("Open /transit/lines/r10-bus-{bus_city_slug}-03 (Airport Express) "
     "and verify the page returns 200 with stops listed.",
     "r10-transit-line-bus"),
    ("Open /transit/lines/r10-bus-{bus_city_slug}-07 (Night Owl) and "
     "verify the operating-hours field contains 'PM' or 'AM'.",
     "r10-transit-line-bus"),
    ("Open /transit/lines and filter by city={a_slug}; verify at least "
     "3 lines are returned.",
     "r10-transit-line-bus"),

    # ---- API/JSON probes for the 8-step compound state ----
    ("POST /api/v2/places/graphql with `{{ places(filter:{{query:\"hostel\"}}, "
     "limit:5){{ slug name }} }}`; verify all 5 names contain 'Hostel'.",
     "r10-api-probe"),
    ("POST /api/v2/places/graphql with `{{ places(filter:{{query:\"co-live\"}}, "
     "limit:5){{ slug name }} }}`; verify all 5 names contain 'Co-Live'.",
     "r10-api-probe"),
    ("POST /api/v2/places/graphql with `{{ places(filter:{{query:\"ski resort\"}}, "
     "limit:5){{ slug name }} }}`; verify all 5 names contain 'Ski'.",
     "r10-api-probe"),
    ("POST /api/v2/places/graphql with `{{ places(filter:{{query:\"dive site\"}}, "
     "limit:5){{ slug name }} }}`; verify all 5 names contain 'Dive'.",
     "r10-api-probe"),
    ("GET /api/places/services?limit=10 and verify the response includes "
     "at least one Co-Live entry.",
     "r10-api-probe"),
    ("GET /api/nearby/{slug}?radius=5 and verify the response lists at "
     "least 3 nearby venues.",
     "r10-api-probe"),
    ("GET /sitemap/city/{a_slug}.xml and verify the sitemap lists at "
     "least 20 place URLs.",
     "r10-api-probe"),
]


def pair_anchors(i):
    a_name, a_slug = ANCHOR_CITIES[i % len(ANCHOR_CITIES)]
    b_name, b_slug = ANCHOR_CITIES[(i * 13 + 7) % len(ANCHOR_CITIES)]
    if b_slug == a_slug:
        b_name, b_slug = ANCHOR_CITIES[(i + 1) % len(ANCHOR_CITIES)]
    return (a_name, a_slug), (b_name, b_slug)


def main():
    existing = []
    if TASKS_FILE.exists():
        with open(TASKS_FILE, "r") as f:
            existing = [json.loads(line) for line in f if line.strip()]

    max_id = -1
    have_r10 = False
    R10_PREFIXES = (
        "r10-compound", "r10-multi-stop", "r10-intl-",
        "r10-ski-", "r10-dive-", "r10-hostel", "r10-coliving",
        "r10-accessibility", "r10-bikeshare", "r10-chain",
        "r10-transit-line", "r10-api-probe",
    )
    for t in existing:
        try:
            n = int(t["id"].rsplit("--", 1)[1])
            max_id = max(max_id, n)
        except (ValueError, IndexError, KeyError):
            continue
        if t.get("task_type", "").startswith(R10_PREFIXES):
            have_r10 = True

    if have_r10:
        print("R10 tasks already appended — skipping")
        return

    # Need at least 5400 total tasks; we currently have ~4712 so target
    # 700+ new.  Pad to 750 to give margin against dedup.
    target_new = 750
    new_tasks = []
    i = 0
    pat_idx = 0
    seen_ques = set()
    while len(new_tasks) < target_new:
        (a, a_slug), (b, b_slug) = pair_anchors(i)
        # Build slugs whose <idx> falls in the real per-kind range.
        def _slug(kind, city, ii):
            lo, hi = R10_KIND_RANGES[kind]
            idx = lo + (ii % (hi - lo + 1))
            return f"r10-{kind}-{city}-{idx:03d}"
        intl_slug       = _slug("intl", a_slug, i)
        ski_slug        = _slug("ski", a_slug, i)
        dive_slug       = _slug("dive", a_slug, i)
        hostel_slug     = _slug("hostel", a_slug, i)
        coliving_slug   = _slug("coliving", a_slug, i)
        accessible_slug = _slug("accessible", a_slug, i)
        bike_slug       = _slug("bikeshare", a_slug, i)
        # Generic slug for compound tasks; rotate across R10 kinds.
        kind = R10_KINDS[i % len(R10_KINDS)]
        slug = _slug(kind, a_slug, i)
        kind_label = {
            "intl":       "heritage landmark",
            "ski":        "ski resort",
            "dive":       "dive site",
            "hostel":     "hostel",
            "coliving":   "co-live",
            "accessible": "accessible facility",
            "bikeshare":  "bike-share",
            "chain":      "coffee shop chain",
        }[kind]
        transit_slug = R10_TRANSIT_SLUGS[i % len(R10_TRANSIT_SLUGS)]
        bus_city_slug = R10_BUS_SLUG_CITIES[i % len(R10_BUS_SLUG_CITIES)]

        pattern, task_type = R10_TASK_PATTERNS[pat_idx % len(R10_TASK_PATTERNS)]
        ques = (pattern
                .replace("{a_slug}", a_slug)
                .replace("{b_slug}", b_slug)
                .replace("{slug}", slug)
                .replace("{intl_slug}", intl_slug)
                .replace("{ski_slug}", ski_slug)
                .replace("{dive_slug}", dive_slug)
                .replace("{hostel_slug}", hostel_slug)
                .replace("{coliving_slug}", coliving_slug)
                .replace("{accessible_slug}", accessible_slug)
                .replace("{bike_slug}", bike_slug)
                .replace("{transit_slug}", transit_slug)
                .replace("{bus_city_slug}", bus_city_slug)
                .replace("{kind_label}", kind_label)
                .replace("{a}", a)
                .replace("{b}", b))

        # Dedup on question text within this batch.
        if ques in seen_ques:
            i += 1
            pat_idx += 1
            continue
        seen_ques.add(ques)

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
    print(f"Appended {len(new_tasks)} R10 tasks. "
          f"Total: {len(existing) + len(new_tasks)}")


if __name__ == "__main__":
    main()
