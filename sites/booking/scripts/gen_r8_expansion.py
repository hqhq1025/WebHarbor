#!/usr/bin/env python3
"""R8 expansion generator (booking mirror).

Run once on the build host:

    python3 sites/booking/scripts/gen_r8_expansion.py

Outputs (deterministic, hash-derived; rerunning produces the same bytes):
- scraped_data/expansion_hotels_r8.json
- scraped_data/expansion_tasks_r8.jsonl

R8 focus:
- Push property count from ~22587 -> ~28000+ by adding ~5600 procedural
  short-term-rental cross-listings (apartment / villa / cabin / B&B / guesthouse).
  R8 listings use a distinctive "Host #NNNN" prefix so they don't collide with
  R4 / R5 / R6 / R7 outputs.
- Add 8 new task categories:
  1. keyboard-shortcut-search ('/' focuses search)
  2. command-palette          (Cmd+K opens jump-to palette)
  3. partner-oauth-v3         (/partner/api/v3/oauth/{authorize,token})
  4. webhook-new-booking      (/webhook/new-booking)
  5. amenity-glossary-tooltip (hover icon -> definition)
  6. refer-friend             (/refer-friend invite + reward)
  7. group-trip-budget-split  (/trip/split per-traveller split)
  8. multi-step               (compound flows that chain the above)
"""
import hashlib
import json
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
SCRAPED = BASE / 'scraped_data'
SCRAPED.mkdir(exist_ok=True)


def _hkey(*parts):
    h = hashlib.sha256('|'.join(str(p) for p in parts).encode('utf-8')).digest()
    return int.from_bytes(h[:4], 'big')


CORE = [
    ('nyc', 'New York', 'us'), ('paris', 'Paris', 'fr'),
    ('london', 'London', 'gb'), ('tokyo', 'Tokyo', 'jp'),
    ('dubai', 'Dubai', 'ae'), ('rome', 'Rome', 'it'),
    ('barcelona', 'Barcelona', 'es'), ('bali', 'Bali', 'id'),
    ('amsterdam', 'Amsterdam', 'nl'), ('singapore', 'Singapore', 'sg'),
    ('maldives', 'Maldives', 'mv'), ('bangkok', 'Bangkok', 'th'),
    ('hongkong', 'Hong Kong', 'hk'), ('istanbul', 'Istanbul', 'tr'),
    ('sydney', 'Sydney', 'au'), ('losangeles', 'Los Angeles', 'us'),
    ('berlin', 'Berlin', 'de'), ('prague', 'Prague', 'cz'),
    ('vienna', 'Vienna', 'at'), ('venice', 'Venice', 'it'),
    ('santorini', 'Santorini', 'gr'), ('mexicocity', 'Mexico City', 'mx'),
    ('rio', 'Rio de Janeiro', 'br'), ('jakarta', 'Jakarta', 'id'),
    ('ohio', 'Ohio', 'us'), ('varanasi', 'Varanasi', 'in'),
    ('chennai', 'Chennai', 'in'), ('chicago', 'Chicago', 'us'),
    ('lisbon', 'Lisbon', 'pt'), ('melbourne', 'Melbourne', 'au'),
    ('toronto', 'Toronto', 'ca'), ('shenzhen', 'Shenzhen', 'cn'),
    ('sapporo', 'Sapporo', 'jp'),
]


def _load_cities():
    cities = {}
    for k, disp, cc in CORE:
        cities[k] = {'display': disp, 'country_code': cc}
    exp = SCRAPED / 'expansion_cities.json'
    if exp.exists():
        for row in json.load(open(exp)):
            k, disp, slug, country, cc = row[0], row[1], row[2], row[3], row[4]
            if k not in cities:
                cities[k] = {'display': disp, 'country_code': cc}
    return cities


# R8 hotels — short-term-rental cross-listings. Distinctive prefix
# "Host #NNNN" so they don't collide with R4-R7 outputs.
R8_HOST_FIRSTNAMES = [
    'Alex', 'Bea', 'Cleo', 'Devi', 'Esme', 'Fai', 'Gio', 'Hana',
    'Inez', 'Jules', 'Kira', 'Lior', 'Mei', 'Nico', 'Ola', 'Pia',
    'Quinn', 'Rumi', 'Sami', 'Tia', 'Uma', 'Vik', 'Wren', 'Xan',
    'Yuna', 'Zev',
]
R8_STYLES = [
    'Sunlit', 'Modernist', 'Industrial', 'Bohemian', 'Mid-century',
    'Scandinavian', 'Rustic', 'Art-deco', 'Minimalist', 'Loft-style',
    'Garden-side', 'Top-floor', 'Hidden-courtyard', 'Light-filled',
    'Designer', 'Heritage', 'Riverview', 'Skyline-view', 'Quiet-lane',
    'Penthouse-grade',
]
R8_TYPES = ['Apartment', 'Villa', 'Cabin', 'Guest House', 'Bed and Breakfast']
R8_NEIGHBORHOODS = [
    'Old Town', 'Riverside Walk', 'Studio Quarter', 'Designer Lane',
    'Botanical Strip', 'Heritage Row', 'Market Yard', 'Civic Crescent',
    'Garden Court', 'Theatre Walk', 'Bay Promenade', 'University Mile',
    'Cathedral Reach', 'Plaza Loop', 'Atelier Block', 'Esplanade Court',
    'Cultural Crescent', 'Innovation Lane', 'Boulevard Annex', 'Skyline Reach',
]


def gen_hotels(cities, target_total=5600):
    out = []
    keys = list(cities.keys())
    core_keys = [k for k in [c[0] for c in CORE] if k in cities]
    exp_keys = [k for k in keys if k not in core_keys]
    core_per = max(1, target_total * 60 // 100 // max(1, len(core_keys)))
    exp_per = max(1, target_total * 40 // 100 // max(1, len(exp_keys))) if exp_keys else 0
    seen = set()

    def emit(city_key, n):
        c = cities[city_key]
        cdisp = c['display']
        for i in range(n):
            host = R8_HOST_FIRSTNAMES[_hkey('r8-ho', city_key, i) % len(R8_HOST_FIRSTNAMES)]
            style = R8_STYLES[_hkey('r8-st', city_key, i) % len(R8_STYLES)]
            ptype = R8_TYPES[_hkey('r8-pt', city_key, i) % len(R8_TYPES)]
            nbh = R8_NEIGHBORHOODS[_hkey('r8-nb', city_key, i) % len(R8_NEIGHBORHOODS)]
            # Stars: short-term rentals skew 2-4; very rare 5.
            stars_pool = [2, 2, 3, 3, 3, 3, 4, 4, 4, 5]
            stars = stars_pool[_hkey('r8-rs', city_key, i, host) % len(stars_pool)]
            listing_id = 10000 + (_hkey('r8-lid', city_key, i) % 89999)
            # Composition variant: half use "Host #N", half "{Host}'s {Style}".
            if (_hkey('r8-shape', city_key, i) % 2) == 0:
                name = f"Host #{listing_id}: {style} {ptype} in {nbh}, {cdisp}"
            else:
                name = f"{host}'s {style} {ptype} in {nbh}, {cdisp}"
            key = (name.lower(), city_key)
            if key in seen:
                name = f"{name} (#{i + 1})"
                key = (name.lower(), city_key)
            seen.add(key)
            out.append({
                'name': name,
                'type': ptype,
                'neighborhood': nbh,
                'city_key': city_key,
                'stars': stars,
            })

    for k in core_keys:
        emit(k, core_per)
    for k in exp_keys:
        emit(k, exp_per)
    return out


TASK_CITIES_BIG = [
    'paris', 'london', 'nyc', 'tokyo', 'rome', 'barcelona', 'dubai',
    'singapore', 'bali', 'sydney', 'amsterdam', 'bangkok', 'maldives',
    'istanbul', 'losangeles', 'berlin', 'prague', 'vienna', 'venice',
    'santorini', 'mexicocity', 'rio', 'jakarta', 'chicago', 'lisbon',
    'melbourne', 'toronto', 'hongkong', 'sapporo', 'shenzhen',
    'chennai', 'varanasi', 'ohio',
]


# 8 new R8 task categories. Each template references a real feature that
# this round added (routes / templates / JS hooks).
R8_TASK_TEMPLATES = [
    # 1. keyboard-shortcut-search ('/' focuses search)
    ("On the {city} city page, press the '/' key; report which input element receives focus.",
     'keyboard-shortcut-search'),
    ("From any Booking page in {city}, press '/' and start typing 'pool'; report the placeholder text shown in the focused search box.",
     'keyboard-shortcut-search'),
    ("Open the homepage, press '/', and verify focus jumps to the destination search input; report the input's id attribute.",
     'keyboard-shortcut-search'),
    ("On a {city} property detail page, press '/' to focus search; report whether the page header search bar receives focus or a sticky in-page bar does.",
     'keyboard-shortcut-search'),
    ("From the search results page for {city}, press the '/' key and report whether the existing query text is preserved in the focused input.",
     'keyboard-shortcut-search'),
    # 2. command-palette (Cmd+K / Ctrl+K)
    ("On any page, press Cmd+K (or Ctrl+K) and type '{city}'; report the first suggestion category shown (City / Property / Saved / Trip).",
     'command-palette'),
    ("Open the command palette with Cmd+K, type 'saved', and report the destination URL the top result navigates to.",
     'command-palette'),
    ("From the homepage open the command palette via Cmd+K; report the keyboard hint shown next to the palette title.",
     'command-palette'),
    ("Press Cmd+K, then type 'trip'; report whether 'Trip budget split' appears among the suggestions and at which position.",
     'command-palette'),
    ("Open the command palette and type '{city}'; press Enter on the first result and report the page title you land on.",
     'command-palette'),
    ("In the command palette, type the first three letters of a {city} property name; report whether matching properties appear under a 'Properties' section.",
     'command-palette'),
    # 3. partner-oauth-v3 (/partner/api/v3/oauth/*)
    ("GET /partner/api/v3/oauth/authorize?client_id=demo&redirect_uri=https://example.com; report the JSON 'authorize_url' field returned.",
     'partner-oauth-v3'),
    ("POST to /partner/api/v3/oauth/token with form fields client_id=demo, client_secret=demo, grant_type=client_credentials; report the 'token_type' value in the JSON response.",
     'partner-oauth-v3'),
    ("Hit /partner/api/v3/oauth/token via POST; report the integer 'expires_in' value declared in the response.",
     'partner-oauth-v3'),
    ("Visit /partner/api/v3/oauth/authorize and report which OAuth 2.0 'response_type' values the endpoint advertises as supported.",
     'partner-oauth-v3'),
    ("Open /partner/api/v3 in a browser; report the title of the partner API documentation page.",
     'partner-oauth-v3'),
    ("From /partner/api/v3/oauth/token's JSON response, extract the access_token value and report the prefix it starts with.",
     'partner-oauth-v3'),
    # 4. webhook-new-booking
    ("Open /webhook/new-booking in a browser; report the event-type string the webhook documentation declares.",
     'webhook-new-booking'),
    ("On /webhook/new-booking, find the sample JSON payload; report the field name used for the property's slug.",
     'webhook-new-booking'),
    ("Visit /webhook/new-booking and report the HMAC header name partners must verify against on incoming POSTs.",
     'webhook-new-booking'),
    ("Open /webhook/new-booking; report the documented retry policy (max retries and backoff interval).",
     'webhook-new-booking'),
    ("From the /webhook/new-booking docs, report which HTTP status code partners must return to acknowledge receipt.",
     'webhook-new-booking'),
    # 5. amenity-glossary-tooltip
    ("On a {city} property page, hover the Spa & wellness amenity icon; report the glossary tooltip text that appears.",
     'amenity-glossary-tooltip'),
    ("Hover the 'Free WiFi' icon on a {city} property's amenity grid and report the WCAG-style alt description shown.",
     'amenity-glossary-tooltip'),
    ("Open the amenity glossary at /amenity-glossary; report the definition listed for 'Travel Sustainable Level 3'.",
     'amenity-glossary-tooltip'),
    ("On /amenity-glossary, find the entry for 'Airport shuttle'; report what fees the definition mentions.",
     'amenity-glossary-tooltip'),
    ("Hover the 'Pet-friendly' icon on a {city} property; report which two clarifying questions the tooltip prompts a guest to check before booking.",
     'amenity-glossary-tooltip'),
    ("On a {city} property page, hover the 'Free cancellation' badge; report the days-before-check-in cutoff in the glossary tooltip.",
     'amenity-glossary-tooltip'),
    # 6. refer-friend
    ("Open /refer-friend on Booking; report the referral bonus amount and currency shown.",
     'refer-friend'),
    ("Sign in and visit /refer-friend; report your personal referral code shown in the share panel.",
     'refer-friend'),
    ("On /refer-friend, click 'Copy link' and report the canonical referral URL format the page exposes.",
     'refer-friend'),
    ("Visit /refer-friend; report how many active referral slots the page says a Genius level 3 member has per calendar year.",
     'refer-friend'),
    ("On /refer-friend, report the eligibility rule shown for the referred friend (minimum stay value and number of nights).",
     'refer-friend'),
    ("Open /refer-friend/code/SOPHIE; report the friend-side discount the landing page advertises.",
     'refer-friend'),
    # 7. group-trip-budget-split
    ("Open /trip/split; enter 4 travellers and a total stay cost of 1200 USD; report the per-person split shown.",
     'group-trip-budget-split'),
    ("On /trip/split, enable 'Even split with shared meals' and add a 200 USD shared meals row; report the new per-person total for 4 travellers on a 1200 USD stay.",
     'group-trip-budget-split'),
    ("Visit /trip/split; report which currencies the budget split selector supports out-of-the-box (count the options).",
     'group-trip-budget-split'),
    ("On /trip/split with 5 travellers and 1500 EUR stay, switch the split mode to 'Weighted by income'; report what additional input fields appear.",
     'group-trip-budget-split'),
    ("Open /trip/split, set 3 travellers, 900 GBP stay, then add a single 'Airport taxi 60 GBP' shared line; report the per-person final total.",
     'group-trip-budget-split'),
    ("On /trip/split for a {city} group trip, report the maximum number of travellers the splitter supports in a single calculation.",
     'group-trip-budget-split'),
    # 8. multi-step compounds
    ("Press '/' on the {city} city page, type 'pool', then submit; report the count of matching {city} properties shown on the result page.",
     'multi-step-kbd-search'),
    ("Open the command palette via Cmd+K, jump to a {city} property, then add the Standard Double Room to your bag; report the bag count shown in the header.",
     'multi-step-palette-bag'),
    ("On /trip/split, compute a 4-traveller split for a 1600 USD stay, then click 'Book this stay'; report the URL you are routed to.",
     'multi-step-split-book'),
    ("Visit /refer-friend, copy the share link, then open it in a private window; report the welcome banner copy shown to the referred guest.",
     'multi-step-refer-link'),
    ("Hover the 'Spa & wellness' icon on a {city} property, then click the glossary 'Learn more' link; report which /amenity-glossary section anchor it scrolls to.",
     'multi-step-glossary-anchor'),
    ("Press Cmd+K, type '{city}', hit Enter on the top city result, then press '/' and start typing 'shuttle'; report whether the search input is now scoped to {city}.",
     'multi-step-palette-keyword'),
    ("From /healthz, confirm db_md5 is present, then open a {city} property page; report the X-Request-ID header value present on the response.",
     'multi-step-healthz-prop'),
    ("Open /metrics, locate the booking_property_count gauge, then visit /city/{cslug}; report whether the city's properties_count on the page matches the city-level metrics row.",
     'multi-step-metrics-city'),
]


def gen_tasks(cities, start_id, target_total=700):
    city_to_slug = {
        'paris': 'paris', 'london': 'london', 'nyc': 'new-york',
        'tokyo': 'tokyo', 'rome': 'rome', 'barcelona': 'barcelona',
        'dubai': 'dubai', 'singapore': 'singapore', 'bali': 'bali',
        'sydney': 'sydney', 'amsterdam': 'amsterdam', 'bangkok': 'bangkok',
        'maldives': 'maldives', 'istanbul': 'istanbul',
        'losangeles': 'los-angeles', 'berlin': 'berlin',
        'prague': 'prague', 'vienna': 'vienna', 'venice': 'venice',
        'santorini': 'santorini', 'mexicocity': 'mexico-city',
        'rio': 'rio-de-janeiro', 'jakarta': 'jakarta',
        'ohio': 'ohio', 'varanasi': 'varanasi', 'chennai': 'chennai',
        'chicago': 'chicago', 'lisbon': 'lisbon',
        'melbourne': 'melbourne', 'toronto': 'toronto',
        'shenzhen': 'shenzhen', 'sapporo': 'sapporo',
        'hongkong': 'hong-kong',
    }
    out = []
    seen = set()
    idx = start_id
    for tmpl, kind in R8_TASK_TEMPLATES:
        if len(out) >= target_total:
            break
        for ck in TASK_CITIES_BIG:
            if len(out) >= target_total:
                break
            if ck not in cities:
                continue
            disp = cities[ck]['display']
            cslug = city_to_slug.get(ck, ck)
            ques = tmpl.format(city=disp, ck=ck, cslug=cslug)
            if ques in seen:
                continue
            seen.add(ques)
            out.append({
                'web_name': 'Booking',
                'id': f'Booking--{idx}',
                'ques': ques,
                'web': 'http://localhost:40005/',
                'upstream_url': 'https://www.booking.com/',
            })
            idx += 1
    return out


def _next_task_id():
    p = BASE / 'tasks.jsonl'
    if not p.exists():
        return 0
    mx = -1
    with open(p) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
                ident = row.get('id', '')
                if '--' in ident:
                    n = int(ident.split('--')[1])
                    mx = max(mx, n)
            except Exception:
                continue
    return mx + 1


def main():
    cities = _load_cities()
    print(f"  cities: {len(cities)}")

    hotels = gen_hotels(cities, target_total=5800)
    print(f"  hotels generated: {len(hotels)}")
    with open(SCRAPED / 'expansion_hotels_r8.json', 'w') as f:
        json.dump(hotels, f, indent=1, ensure_ascii=False, sort_keys=True)

    start_id = _next_task_id()
    print(f"  task start id: Booking--{start_id}")
    tasks = gen_tasks(cities, start_id=start_id, target_total=700)
    print(f"  tasks generated: {len(tasks)}")
    with open(SCRAPED / 'expansion_tasks_r8.jsonl', 'w') as f:
        for t in tasks:
            f.write(json.dumps(t, ensure_ascii=False) + '\n')


if __name__ == '__main__':
    main()
