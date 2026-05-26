"""Generate R7 task additions for tasks.jsonl.

Adds ~900 tasks targeting the R7 themes:
  - SEO: LocalBusiness/Place JSON-LD, OG cover image, /sitemap.xml grouped
    per city, /robots.txt, BreadcrumbList ld+json
  - Locale paths: 25 locales (incl. RTL ar/he) under /<lang>/
  - Accessibility VoiceOver place-card probes
  - Business-claim multi-step flow
  - Performance probes (composite-index-backed sorts / filters)

Deterministic: same source file produces the same output every time.
Append-only, idempotent — re-running detects R7-* task_type values
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
]

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

LOCALES = [
    "en", "es", "fr", "de", "it", "pt", "nl", "sv", "da", "no",
    "fi", "pl", "cs", "el", "tr", "ru", "ja", "ko", "zh", "hi",
    "th", "vi", "id", "ar", "he",
]
RTL_LOCALES = ["ar", "he"]

CHAINS = [
    "Starbucks Reserve", "Blue Bottle Coffee", "Peet's Coffee", "Dunkin'",
    "Whole Foods Market", "Trader Joe's", "Costco Wholesale", "Safeway",
    "CVS Pharmacy", "Walgreens", "Marriott", "Hilton Garden Inn",
    "Holiday Inn Express", "Hyatt Place", "Hampton Inn", "Apple Store",
    "Best Buy", "IKEA", "Target", "Home Depot", "AMC Theatres",
]

CATEGORIES = [
    "restaurants", "hotels", "museums", "parks", "shopping",
    "coffee-shops", "supermarkets", "pharmacies", "fitness",
    "entertainment", "gas-stations", "atms", "ev-charging",
    "car-rental", "veterinarians", "dentists",
]

# Each entry: (template, task_type).  {l}/{l2}/{a}/{b}/{loc}/{cat}/{chain}
R7_TASK_PATTERNS = [
    # ---- SEO: LocalBusiness JSON-LD verification ----
    ("Open {l}'s place page, inspect the LocalBusiness JSON-LD, and report the schema @type field.",
     "seo-localbusiness-jsonld"),
    ("Find {l}, view its place detail, and tell me the ratingValue inside the AggregateRating JSON-LD block.",
     "seo-localbusiness-jsonld"),
    ("Search for {l}, open its detail, and confirm whether the JSON-LD includes a priceRange field.",
     "seo-localbusiness-jsonld"),
    ("Open {l} and tell me whether the structured-data @type is Restaurant, Hotel, or LocalBusiness.",
     "seo-place-schema-jsonld"),
    ("Find {l} and verify the openingHours field inside the JSON-LD on the place page.",
     "seo-place-schema-jsonld"),
    ("Open the place detail for {l}; report the addressLocality and addressCountry from the structured-data block.",
     "seo-place-schema-jsonld"),
    # ---- SEO: Open Graph cover image ----
    ("Open {l}'s detail page and read the og:image meta tag value.",
     "seo-og-cover-image"),
    ("Find {l} and tell me what its og:title and og:description meta tags say.",
     "seo-og-cover-image"),
    ("Search for {l}, open the page, and verify whether twitter:card is set to summary_large_image.",
     "seo-og-cover-image"),
    ("Open {l} and report the canonical og:type — does the page expose 'place', 'website', or something else?",
     "seo-og-cover-image"),
    # ---- SEO: BreadcrumbList JSON-LD ----
    ("Open {l}'s place page, find the BreadcrumbList JSON-LD, and list the position-1, position-2, and position-3 entries.",
     "seo-breadcrumb-jsonld"),
    # ---- /sitemap.xml grouped per city ----
    ("Open /sitemap.xml and tell me how many <sitemap> child entries it contains.",
     "seo-sitemap-grouped-per-city"),
    ("Fetch /sitemap.xml and confirm it splits by city — show 3 city-sitemap URLs.",
     "seo-sitemap-grouped-per-city"),
    ("Open /sitemap/city/{a_slug}.xml and tell me how many place URLs are listed.",
     "seo-sitemap-grouped-per-city"),
    ("Open /sitemap/category/{cat}.xml and report the first 5 place URLs.",
     "seo-sitemap-grouped-per-city"),
    ("Open /sitemap/static.xml and verify the per-locale homepage URLs are listed.",
     "seo-sitemap-grouped-per-city"),
    # ---- robots.txt ----
    ("Fetch /robots.txt and tell me which paths are disallowed for crawlers.",
     "seo-robots-txt"),
    ("Open /robots.txt and verify the Sitemap: directive points to /sitemap.xml.",
     "seo-robots-txt"),
    # ---- Locale paths (25 locales incl. RTL) ----
    ("Open /{loc}/ and tell me which language the homepage tagline is rendered in.",
     "locale-25-with-rtl"),
    ("Switch to the /ar/ locale and confirm the page's <html> has dir=\"rtl\".",
     "locale-25-with-rtl"),
    ("Switch to the /he/ locale and verify the layout flips to right-to-left.",
     "locale-25-with-rtl"),
    ("Open /locales and list 5 locales the site offers, including any RTL ones.",
     "locale-25-with-rtl"),
    ("Open /{loc}/ and check that the <html lang=\"{loc}\"> attribute is set correctly.",
     "locale-25-with-rtl"),
    ("Visit the {loc} locale homepage and confirm the alternate-hreflang link tags include all 25 supported languages.",
     "locale-25-with-rtl"),
    # ---- Accessibility VoiceOver ----
    ("Open {l}, tab through its place card with a screen reader, and tell me which aria-labels are exposed.",
     "accessibility-voiceover-place-card"),
    ("Find {l} and verify whether the rating star row exposes a screen-reader-only label like 'Rated 4.5 out of 5'.",
     "accessibility-voiceover-place-card"),
    ("Open {l} and report whether the breadcrumb nav has an aria-label of 'Breadcrumb'.",
     "accessibility-voiceover-place-card"),
    ("Find {l} and check that each accessibility-warning banner is announced with role=\"alert\".",
     "accessibility-voiceover-place-card"),
    ("Open {l}'s detail page and verify the hero image has descriptive alt text.",
     "accessibility-voiceover-place-card"),
    # ---- Business-claim multi-step ----
    ("Open {l} and start the business-claim flow at /business/claim/<slug>.",
     "business-claim-flow"),
    ("Claim {l}: submit business name, owner, and a contact email; report the confirmation banner shown.",
     "business-claim-flow"),
    ("Find {l}, click 'Claim this business', and tell me how many fields the form requires.",
     "business-claim-flow"),
    ("Open /business/claim/<slug> for {l}, submit with only the business-name field, and capture the validation message.",
     "business-claim-flow"),
    # ---- Multi-step ----
    ("Open {l}, claim the business, then go back to the place page and verify the JSON-LD still loads.",
     "r7-multi-step"),
    ("Switch to the /{loc}/ locale homepage, search for {chain} in {a}, then open the first result and view its menu.",
     "r7-multi-step"),
    ("Open /sitemap/city/{a_slug}.xml, pick the 3rd URL, open that place, and report its category.",
     "r7-multi-step"),
    ("Open the /ar/ locale, navigate to /explore, drill into {cat}, and confirm the RTL direction persists across pages.",
     "r7-multi-step"),
    ("Open /robots.txt, find the sitemap link, fetch it, and pick a city sitemap to follow to a real place page.",
     "r7-multi-step"),
    # ---- Performance (composite-index-backed) ----
    ("Search for top-rated {cat} in {a} and verify the top 10 are sorted by rating desc within a single city.",
     "perf-city-rating-index"),
    ("Open /search?q={chain}+{a} and report the rating spread of the top 5 chain locations.",
     "perf-chain-rating-index"),
    ("Search for {cat} near {a} sorted by distance, and confirm the first 5 results lie within the city box.",
     "perf-category-lat-lng-index"),
    # ---- Cross-page chains involving the new features ----
    ("Open {l}, copy its og:image URL, then open the QR share page and verify the share URL points back to the same place.",
     "cross-page-seo-qr"),
    ("Find {l}, view JSON-LD aggregateRating, then write a 5-star review titled 'SEO-verified' (signed in as david.k@test.com).",
     "cross-page-seo-review"),
    ("Open the /zh/ locale, search for {chain}, open the first hit, and confirm the JSON-LD @type stays English.",
     "cross-page-locale-jsonld"),
    ("Switch to /es/, open {l}, and verify the OG description meta tag remains in English even though the page chrome is localized.",
     "cross-page-locale-og"),
    ("Open /sitemap/category/{cat}.xml, pick a place, and confirm its JSON-LD address.addressCountry matches the city's country field.",
     "cross-page-sitemap-jsonld"),
    # ---- Place schema specific subtypes ----
    ("Open a Restaurant place in {a} and confirm the JSON-LD @type is exactly 'Restaurant'.",
     "seo-place-schema-restaurant"),
    ("Open a Hotel place in {a} and confirm the JSON-LD @type is 'Hotel' with priceRange filled.",
     "seo-place-schema-hotel"),
    ("Open a Pharmacy in {a} and verify the JSON-LD @type is 'Pharmacy'.",
     "seo-place-schema-pharmacy"),
    ("Open a Gas station in {a} and confirm the JSON-LD @type is 'GasStation'.",
     "seo-place-schema-gasstation"),
    ("Open a Museum in {a} and verify the JSON-LD @type is 'Museum' and openingHours is populated.",
     "seo-place-schema-museum"),
    # ---- Sitemap navigation ----
    ("Count how many city-sitemaps the index lists (open /sitemap.xml and tally).",
     "seo-sitemap-tally"),
    ("Open /sitemap/static.xml and verify there's a URL entry for /transit/realtime.",
     "seo-sitemap-static-urls"),
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
    have_r7 = False
    R7_PREFIXES = (
        "seo-", "locale-25-", "accessibility-voiceover-",
        "business-claim-", "r7-multi-step", "perf-city-", "perf-chain-",
        "perf-category-", "cross-page-seo-",
        "cross-page-locale-", "cross-page-sitemap-",
    )
    for t in existing:
        try:
            n = int(t["id"].rsplit("--", 1)[1])
            max_id = max(max_id, n)
        except (ValueError, IndexError, KeyError):
            continue
        if t.get("task_type", "").startswith(R7_PREFIXES):
            have_r7 = True

    if have_r7:
        print("R7 tasks already appended — skipping")
        return

    # Generate enough variations so total >= 3300.
    target_total = 3300
    target_new = max(800, target_total - len(existing))
    new_tasks = []
    i = 0
    pat_idx = 0
    while len(new_tasks) < target_new:
        a, b = pair_anchors(i)
        l, l2 = pair_landmarks(i)
        loc = LOCALES[i % len(LOCALES)]
        cat = CATEGORIES[i % len(CATEGORIES)]
        chain = CHAINS[i % len(CHAINS)]
        a_slug = a.lower().replace(" ", "-")
        pattern, task_type = R7_TASK_PATTERNS[pat_idx % len(R7_TASK_PATTERNS)]
        ques = (pattern
                .replace("{a_slug}", a_slug)
                .replace("{a}", a)
                .replace("{b}", b)
                .replace("{l2}", l2)
                .replace("{loc}", loc)
                .replace("{cat}", cat)
                .replace("{chain}", chain)
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
    print(f"Appended {len(new_tasks)} R7 tasks. Total: {len(existing) + len(new_tasks)}")


if __name__ == "__main__":
    main()
