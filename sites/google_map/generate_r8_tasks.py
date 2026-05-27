"""Generate R8 task additions for tasks.jsonl.

Adds ~700 tasks targeting the R8 themes:
  - keyboard-shortcut: '+' / '-' zoom, '/' search focus, '?' help, 'g h' chord
  - command-palette: Cmd+K / Ctrl+K jump to place / category / list
  - symbol-glossary tooltip: hover gas-pump / parking-P / transit-T / WiFi
  - developer console: /developer/maps-embed-code + iframe / static / JS
  - v2 GraphQL: POST /api/v2/places/graphql with filter+limit
  - webhooks: POST /webhook/place-update event envelope
  - observability: /healthz + /api/uptime + /api/events
  - multi-step: chain keyboard-shortcut → palette → place page → review
  - cross-page: dev-console → graphql → webhook ack

Deterministic, append-only, idempotent.  Re-running detects an R8 prefix
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
    "Tokyo", "Paris", "London", "Rome", "Barcelona",
]

LANDMARKS = [
    "Empire State Building", "Central Park", "Times Square", "Brooklyn Bridge",
    "Statue of Liberty", "Bryant Park",
    "Golden Gate Bridge", "Alcatraz Island", "Lombard Street", "Pier 39",
    "Pike Place Market", "Space Needle", "Chihuly Garden",
    "Willis Tower", "Millennium Park", "Art Institute of Chicago",
    "Navy Pier", "Magnificent Mile",
    "Santa Monica Pier", "Griffith Observatory", "Hollywood Sign",
    "Venice Beach", "Universal Studios Hollywood",
    "Freedom Trail", "Fenway Park", "Bellagio Hotel", "Tokyo Tower",
    "Tokyo Skytree", "Eiffel Tower", "Louvre", "Arc de Triomphe",
    "Colosseum", "Trevi Fountain", "Vatican City", "Sagrada Família",
]

CHAINS = [
    "Tim Hortons", "Gong cha", "Kung Fu Tea", "Boba Guys", "Crumbl Cookies",
    "Wegmans", "Mitsuwa Marketplace", "99 Ranch Market", "Sprouts Farmers Market",
    "DashMart", "Gopuff", "Sonder", "citizenM", "Hoxton", "Ace Hotel",
    "SIXT", "Zipcar", "Tesla Supercharger V4", "Electrify America", "EVgo Fast",
    "F45 Training", "CorePower Yoga", "SoulCycle", "Barry's Bootcamp",
    "WeWork", "Industrious", "Capital One Cafe", "Topgolf",
    "REI Co-op", "Patagonia", "Uniqlo", "Muji", "Daiso",
    "Sephora Studio", "Ulta Beauty", "PetSmart", "Petco",
]

CATEGORIES = [
    "restaurants", "hotels", "museums", "parks", "shopping",
    "coffee-shops", "supermarkets", "pharmacies", "fitness",
    "entertainment", "ev-charging", "car-rental",
    "transit", "religious", "schools", "hospitals", "parking",
]

GLYPHS = ["P", "T", "EV", "GAS", "WC", "H", "$", "i", "WiFi", "BIKE", "ELEV", "DOG"]

LOCALES = [
    "en", "es", "fr", "de", "it", "pt", "nl", "sv", "da", "no",
    "fi", "pl", "cs", "el", "tr", "ru", "ja", "ko", "zh", "hi",
    "th", "vi", "id", "ar", "he",
]

# Each entry: (template, task_type)
R8_TASK_PATTERNS = [
    # ---- Keyboard shortcut: zoom ----
    ("Open the homepage, press '+' three times, and confirm the map zoom level increased.",
     "r8-keyboard-shortcut-zoom"),
    ("Press '-' twice on the homepage and verify the zoom-out button registered the change.",
     "r8-keyboard-shortcut-zoom"),
    ("Press '=' once to reset zoom; verify the map canvas returns to its default zoom for the city of {a}.",
     "r8-keyboard-shortcut-zoom"),
    ("Open {l} and use the '+' key to zoom in on its place card map without clicking the on-screen controls.",
     "r8-keyboard-shortcut-zoom"),
    ("On the explore page, press '+' and '-' in sequence; confirm both Vim-style shortcuts are documented in /help.",
     "r8-keyboard-shortcut-zoom"),
    ("Press 't' on the homepage to toggle the traffic layer and confirm aria-pressed flips on the Traffic button.",
     "r8-keyboard-shortcut-zoom"),
    ("Press 's' on the homepage and verify the map type switches to satellite via the keyboard shortcut.",
     "r8-keyboard-shortcut-zoom"),
    ("Press 'b' on the homepage and verify the bicycling layer toggles via keyboard.",
     "r8-keyboard-shortcut-zoom"),
    # ---- Keyboard shortcut: / focus search ----
    ("Open the homepage and press '/' to focus the search input; type {chain} and submit.",
     "r8-keyboard-shortcut-search-focus"),
    ("Open /explore, press '/' to focus search, search for {cat} in {a}, and report the top hit.",
     "r8-keyboard-shortcut-search-focus"),
    # ---- Command palette (Cmd+K / Ctrl+K) ----
    ("Press Cmd+K (or Ctrl+K) on the homepage to open the command palette; jump to category {cat} and report the result count.",
     "r8-command-palette-jump-place"),
    ("Open the command palette and jump to the place {l}; confirm the place detail loads.",
     "r8-command-palette-jump-place"),
    ("Open the command palette, type '{chain}', and confirm matching places appear under the Places section.",
     "r8-command-palette-jump-place"),
    ("Open the command palette, type the city slug for {a}, and select the City entry; verify /city/{a_slug} loads.",
     "r8-command-palette-jump-place"),
    ("Open the command palette, type 'Developer'; confirm the Developer console page is listed.",
     "r8-command-palette-jump-place"),
    ("Open the command palette and use Arrow-Down to navigate to the 3rd result, then press Enter to open it.",
     "r8-command-palette-jump-place"),
    ("Open /api/command-palette?q={cat} and report how many category results are returned.",
     "r8-command-palette-jump-place"),
    ("Open /api/command-palette?q={chain}&limit=5 and verify each place entry has an href starting with /place/.",
     "r8-command-palette-jump-place"),
    ("Open /api/command-palette and confirm the 'pages' section includes a Developer-console entry.",
     "r8-command-palette-jump-place"),
    # ---- Help modal + chord shortcuts ----
    ("Press '?' on the homepage to open the help modal; report how many keyboard shortcuts are listed.",
     "r8-contextual-help-symbol-glossary"),
    ("Open the help modal and confirm the symbol glossary lists the 'EV', 'GAS', and 'WiFi' glyphs.",
     "r8-contextual-help-symbol-glossary"),
    ("Hover the 'P' symbol in the map legend on the homepage; confirm a tooltip showing 'Parking' appears.",
     "r8-contextual-help-symbol-glossary"),
    ("Hover the '{glyph}' symbol in the map legend; report the tooltip description it surfaces.",
     "r8-contextual-help-symbol-glossary"),
    ("Open /help/symbol-glossary and report the total number of glyphs in the JSON payload.",
     "r8-contextual-help-symbol-glossary"),
    ("Open /help/keyboard-shortcuts and confirm the 'open_help' shortcut maps to the '?' key.",
     "r8-contextual-help-symbol-glossary"),
    ("Press 'g' then 'h' on the homepage; verify the chord-shortcut navigates to /.",
     "r8-contextual-help-symbol-glossary"),
    ("Press 'g' then 'l' on the homepage; verify the chord-shortcut jumps to /lists.",
     "r8-contextual-help-symbol-glossary"),
    ("Press 'g' then 't'; verify the chord-shortcut navigates to /trips (signed in as alice.j@test.com).",
     "r8-contextual-help-symbol-glossary"),
    ("Press 'g' then 'e'; verify the chord-shortcut jumps to /explore.",
     "r8-contextual-help-symbol-glossary"),
    # ---- Developer console ----
    ("Open /developer/maps-embed-code and copy the iframe embed snippet; report the iframe's width attribute.",
     "r8-developer-maps-embed-code"),
    ("Open /developer/maps-embed-code and tell me the api_version listed at the top of the console.",
     "r8-developer-maps-embed-code"),
    ("Open the developer console and verify it links to /healthz, /api/uptime, and /api/events.",
     "r8-developer-maps-embed-code"),
    ("Open /developer/maps-embed-code, navigate to the GraphQL section, and capture the curl example.",
     "r8-developer-maps-embed-code"),
    ("Open the developer console and confirm the static-map snippet uses the /maps/staticmap path with markers parameter.",
     "r8-developer-maps-embed-code"),
    ("Open /developer/maps-embed-code and report the X-Maps-Signature header convention shown in the webhook section.",
     "r8-developer-maps-embed-code"),
    ("Open /developer/maps-embed-code, scroll to the keyboard-shortcuts table, and report how many shortcuts are listed.",
     "r8-developer-maps-embed-code"),
    ("Open /developer/maps-embed-code and confirm the symbol-glossary table includes the 'BIKE' and 'ELEV' rows.",
     "r8-developer-maps-embed-code"),
    # ---- v2 GraphQL endpoint ----
    ("GET /api/v2/places/graphql and verify it returns the schema preview including a 'places(filter,limit)' root field.",
     "r8-api-v2-places-graphql"),
    ("POST /api/v2/places/graphql with the example query for top-rated {cat} in {a_slug}; report the first result's slug.",
     "r8-api-v2-places-graphql"),
    ("POST /api/v2/places/graphql with a query for place(slug: ...) on {l}'s slug; verify the returned name matches.",
     "r8-api-v2-places-graphql"),
    ("POST /api/v2/places/graphql with `{ places(filter:{minRating:4.8}, limit:5){ slug rating } }`; verify all 5 ratings >= 4.8.",
     "r8-api-v2-places-graphql"),
    ("POST /api/v2/places/graphql with a query for `health`; verify the buildSha field starts with 'r8-google-map'.",
     "r8-api-v2-places-graphql"),
    ("POST /api/v2/places/graphql with `{ categories { slug name } }`; report how many categories are returned.",
     "r8-api-v2-places-graphql"),
    ("POST /api/v2/places/graphql with `{ cities(limit:3) { slug displayName } }`; report the 3 cities returned.",
     "r8-api-v2-places-graphql"),
    ("POST /api/v2/places/graphql with a filter on city={a_slug} and category={cat}; confirm the results all share that city+category.",
     "r8-api-v2-places-graphql"),
    ("POST /api/v2/places/graphql with limit=50; confirm the response contains exactly 50 places.",
     "r8-api-v2-places-graphql"),
    ("POST /api/v2/places/graphql with `query:\"{ places(filter:{query:\\\"{chain}\\\"}, limit:3){ slug name } }\"`; verify all 3 names contain '{chain}'.",
     "r8-api-v2-places-graphql"),
    ("Open the GET preview at /api/v2-places-graphql alias and confirm it matches the /api/v2/places/graphql output.",
     "r8-api-v2-places-graphql"),
    # ---- Webhook ----
    ("GET /webhook/place-update and report the auth header convention documented in the spec.",
     "r8-webhook-place-update"),
    ("POST /webhook/place-update with event=place.metadata and place_slug={a_slug}-mall; report the ack_id length.",
     "r8-webhook-place-update"),
    ("POST /webhook/place-update with event=place.delete; verify the response includes the place_exists flag.",
     "r8-webhook-place-update"),
    ("POST /webhook/place-update with an unsupported event 'foo.bar'; verify the response is 400 with allowed-event list.",
     "r8-webhook-place-update"),
    ("POST /webhook/place-update twice with identical payloads; confirm the ack_id is identical (deterministic).",
     "r8-webhook-place-update"),
    ("POST /webhook/place-update with delta={ hours, phone }; verify the delta_fields array contains 'hours' and 'phone' sorted.",
     "r8-webhook-place-update"),
    # ---- Observability ----
    ("GET /healthz and report the build_sha + api_version returned by the health probe.",
     "r8-observability-healthz"),
    ("GET /api/uptime and report the uptime_human field value.",
     "r8-observability-uptime"),
    ("GET /api/uptime and verify the rows.places count is >= 540000.",
     "r8-observability-uptime"),
    ("GET /api/uptime and confirm the regions array lists at least 4 cloud regions.",
     "r8-observability-uptime"),
    ("GET /api/events and report how many events are returned by default.",
     "r8-observability-events"),
    ("GET /api/events?limit=5 and verify the response respects the limit parameter.",
     "r8-observability-events"),
    ("GET /api/events and confirm each event has an id starting with 'evt-' and a place_slug field.",
     "r8-observability-events"),
    # ---- Multi-step / cross-page ----
    ("Press Cmd+K to open the palette, jump to {l}, then write a 5-star review titled 'palette-jump' as bob.c@test.com.",
     "r8-multi-step"),
    ("Open the developer console, copy the GraphQL curl, POST it, then open the first result's place page and capture the og:image meta.",
     "r8-multi-step"),
    ("Open /healthz, confirm status=ok, then open /api/uptime and verify both endpoints report the same build_sha.",
     "r8-multi-step"),
    ("Open /api/events, pick the first event, then open /place/<that-slug> and verify the JSON-LD @type matches the event's category.",
     "r8-multi-step"),
    ("POST /webhook/place-update to acknowledge a place.metadata update for {l}; then open the place page and confirm hours are unchanged (mirror does not mutate).",
     "r8-multi-step"),
    ("Press '?' to open the help modal, click the developer-console link, then navigate to the GraphQL section.",
     "r8-multi-step"),
    ("From /developer/maps-embed-code follow the webhook section; POST a place.upsert envelope; report the queued_at timestamp.",
     "r8-multi-step"),
    ("Switch to the /{loc}/ locale, press Ctrl+K to open the palette, jump to {l}, and confirm the place page retains its primary language metadata.",
     "r8-multi-step"),
    # ---- Telemetry / events probes ----
    ("GET /api/events with no cursor; capture the next_cursor and confirm it is a non-empty string.",
     "r8-telemetry-events"),
    ("GET /api/events and verify each event's `at` timestamp is monotonically increasing from event 1 to event N.",
     "r8-telemetry-events"),
    ("GET /api/uptime twice in a row and confirm the snapshot_at timestamp is identical between calls (deterministic).",
     "r8-telemetry-events"),
    # ---- Cross-page: keyboard + glossary + a11y ----
    ("Open {l}, hover the 'P' glyph in the map legend, and report the tooltip's data-glyph attribute value.",
     "r8-cross-page-glyph-tooltip"),
    ("Open the /ar/ locale homepage and verify the map legend's glyph tooltips still load with English labels (right-to-left does not change them).",
     "r8-cross-page-glyph-tooltip"),
    ("Open /explore, hover the 'WiFi' glyph; verify the tooltip's category is 'amenity'.",
     "r8-cross-page-glyph-tooltip"),
    # ---- Perf via composite paths ----
    ("POST /api/v2/places/graphql for `{ places(filter:{city:\\\"{a_slug}\\\", minRating:4.7}, limit:10){ slug rating } }`; verify all ratings ≥ 4.7.",
     "r8-perf-graphql-rating-index"),
    ("POST /api/v2/places/graphql for `{ places(filter:{category:\\\"{cat}\\\", query:\\\"{chain}\\\"}, limit:5){ name } }`; verify all names contain '{chain}'.",
     "r8-perf-graphql-chain-index"),
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
    have_r8 = False
    R8_PREFIXES = (
        "r8-keyboard-shortcut-", "r8-command-palette-",
        "r8-contextual-help-", "r8-developer-",
        "r8-api-v2-", "r8-webhook-", "r8-observability-",
        "r8-multi-step", "r8-telemetry-", "r8-cross-page-glyph-",
        "r8-perf-graphql-",
    )
    for t in existing:
        try:
            n = int(t["id"].rsplit("--", 1)[1])
            max_id = max(max_id, n)
        except (ValueError, IndexError, KeyError):
            continue
        if t.get("task_type", "").startswith(R8_PREFIXES):
            have_r8 = True

    if have_r8:
        print("R8 tasks already appended — skipping")
        return

    # Generate enough variations so total >= 4000.
    target_total = 4000
    target_new = max(700, target_total - len(existing))
    new_tasks = []
    i = 0
    pat_idx = 0
    while len(new_tasks) < target_new:
        a, b = pair_anchors(i)
        l, l2 = pair_landmarks(i)
        loc = LOCALES[i % len(LOCALES)]
        cat = CATEGORIES[i % len(CATEGORIES)]
        chain = CHAINS[i % len(CHAINS)]
        glyph = GLYPHS[i % len(GLYPHS)]
        a_slug = a.lower().replace(" ", "-")
        pattern, task_type = R8_TASK_PATTERNS[pat_idx % len(R8_TASK_PATTERNS)]
        ques = (pattern
                .replace("{a_slug}", a_slug)
                .replace("{a}", a)
                .replace("{b}", b)
                .replace("{l2}", l2)
                .replace("{loc}", loc)
                .replace("{cat}", cat)
                .replace("{chain}", chain)
                .replace("{glyph}", glyph)
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
    print(f"Appended {len(new_tasks)} R8 tasks. Total: {len(existing) + len(new_tasks)}")


if __name__ == "__main__":
    main()
