#!/usr/bin/env python3
"""R5 expansion generator (booking mirror).

Run once on the build host:

    python3 sites/booking/scripts/gen_r5_expansion.py

Outputs (deterministic, hash-derived; rerunning produces the same bytes):
- scraped_data/expansion_hotels_r5.json
- scraped_data/expansion_tasks_r5.jsonl

R5 focus:
- Push property count from 7869 → 11000+ by adding ~3300 procedural hotels
  with distinctive prefixes that don't collide with R4 output.
- Introduce 7 new task categories (split-stay / flexible-date-cheapest-week /
  group-booking / late-checkout / room-upgrade / dietary-meal / multi-step
  compound), targeting 1900+ total task count.
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


# ---------------------------------------------------------------------------
# Cities — same source as R4. Pull city_keys + display names so we can
# distribute hotels across all cities.
# ---------------------------------------------------------------------------
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

CITY_TO_SLUG = {
    'paris': 'paris', 'london': 'london', 'nyc': 'new-york', 'tokyo': 'tokyo',
    'rome': 'rome', 'barcelona': 'barcelona', 'dubai': 'dubai',
    'singapore': 'singapore', 'bali': 'bali', 'sydney': 'sydney',
    'amsterdam': 'amsterdam', 'bangkok': 'bangkok', 'maldives': 'maldives',
    'istanbul': 'istanbul', 'losangeles': 'los-angeles', 'berlin': 'berlin',
    'prague': 'prague', 'vienna': 'vienna', 'venice': 'venice',
    'santorini': 'santorini', 'mexicocity': 'mexico-city',
    'rio': 'rio-de-janeiro', 'jakarta': 'jakarta', 'lisbon': 'lisbon',
    'melbourne': 'melbourne', 'toronto': 'toronto', 'shenzhen': 'shenzhen',
    'sapporo': 'sapporo', 'chicago': 'chicago', 'ohio': 'ohio',
    'varanasi': 'varanasi', 'chennai': 'chennai', 'hongkong': 'hong-kong',
}


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


# ---------------------------------------------------------------------------
# R5 hotels — use distinctive prefixes so names don't collide with R4 output.
# R4 used "{Brand} {Suffix} {City}{flavour}". R5 uses "{ConceptPrefix} {Brand}
# {City} {Suite/Residence/etc.}" so the namespace is disjoint.
# ---------------------------------------------------------------------------
NEIGHBORHOODS_R5 = [
    'Riverside Quarter', 'Marina Promenade', 'Cathedral Square',
    'Olympic Village', 'Embassy Row', 'Arts & Crafts District',
    'Tech Park', 'Wine District', 'Innovation Hub', 'Botanic Garden',
    'Stadium Quarter', 'Heritage Mile', 'Boutique Lane',
    'Festival Park', 'Designer Quarter', 'Lakeside',
]
CONCEPT_PREFIXES = [
    'Skyline', 'Harbour', 'Capitol', 'Heritage', 'Lantern',
    'Botanic', 'Atrium', 'Echo', 'Mosaic', 'Lighthouse',
    'Citrus', 'Velvet', 'Saffron', 'Opal', 'Cedar',
    'Cobalt', 'Lumen', 'Vista', 'Solstice', 'Aurora',
]
SUFFIXES_R5 = [
    'Residences', 'Suites', 'House', 'Court', 'Quarters',
    'Pavilion', 'Lofts', 'Manor', 'Boutique', 'Collection',
    'Sky Lounge', 'Garden', 'Tower',
]
BRANDS_R5 = ['Hilton', 'Marriott', 'Accor', 'IHG', 'Hyatt',
             'Wyndham', 'Best Western', 'Independent',
             'Luxury Collection']
TYPES_R5 = ['Hotel', 'Apartment', 'Resort', 'Villa',
            'Bed and Breakfast', 'Hostel', 'Guest House', 'Cabin']


def gen_hotels(cities, target_total=3500):
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
            concept = CONCEPT_PREFIXES[_hkey('r5-cp', city_key, i) % len(CONCEPT_PREFIXES)]
            suffix = SUFFIXES_R5[_hkey('r5-sf', city_key, i) % len(SUFFIXES_R5)]
            brand = BRANDS_R5[_hkey('r5-br', city_key, i) % len(BRANDS_R5)]
            nbh = NEIGHBORHOODS_R5[_hkey('r5-nb', city_key, i) % len(NEIGHBORHOODS_R5)]
            stars_pool = [2, 3, 3, 3, 4, 4, 4, 4, 5, 5]
            stars = stars_pool[_hkey('r5-st', city_key, i, brand) % len(stars_pool)]
            ptype = TYPES_R5[_hkey('r5-pt', city_key, i) % len(TYPES_R5)]
            if brand == 'Luxury Collection':
                name = f"{concept} {cdisp} {suffix}"
            elif brand == 'Independent':
                name = f"{concept} {cdisp} {suffix}"
            else:
                name = f"{concept} {brand} {cdisp} {suffix}"
            key = (name.lower(), city_key)
            if key in seen:
                name = f"{name} #{i+1}"
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


# ---------------------------------------------------------------------------
# R5 tasks — 7 new categories specified in the R5 brief, plus a handful of
# multi-step compounds. We assign IDs starting at the current max+1 inside
# the post-processing step that appends to tasks.jsonl.
# ---------------------------------------------------------------------------
TASK_CITIES_BIG = [
    'paris', 'london', 'nyc', 'tokyo', 'rome', 'barcelona', 'dubai',
    'singapore', 'bali', 'sydney', 'amsterdam', 'bangkok', 'maldives',
    'istanbul', 'losangeles', 'berlin', 'prague', 'vienna', 'venice',
    'santorini', 'mexicocity', 'rio', 'jakarta', 'chicago', 'lisbon',
    'melbourne', 'toronto', 'hongkong',
    # R5 — add more cities for unique-task headroom
    'sapporo', 'shenzhen', 'chennai', 'varanasi', 'ohio',
]


R5_TASK_TEMPLATES = [
    # split-stay
    ("Plan a 5-night split-stay in {city}: 3 nights at a 5-star property + 2 nights at a 3-star property in a different neighbourhood; report both property names.",
     'split-stay'),
    ("Build a split-stay in {city} starting next Friday — one beach-area hotel for 2 nights then a city-centre hotel for 2 nights; report the total estimated price.",
     'split-stay'),
    ("Use search to assemble a 4-night split-stay in {city} across two properties from different brands; report each brand.",
     'split-stay'),
    # flexible-date-cheapest-week
    ("In {city}, open the flexible-date tool for next month and report the cheapest 3-night week.",
     'flex-date'),
    ("Use the calendar-availability flex view to find the cheapest 7-night window in {city} during the next 60 days; report start and end date.",
     'flex-date'),
    ("In {city}, sort properties by price and use the flexible-date toggle to find a sub-$100/night week; report the dates.",
     'flex-date'),
    # group-booking 10+rooms
    ("Request a group booking quote in {city} for 10 rooms for 3 nights; report whether a dedicated coordinator is offered.",
     'group'),
    ("Open the group-booking form for a hotel in {city} with at least 12 rooms requested; report the quote turnaround time stated.",
     'group'),
    ("On a {city} property detail page, switch to group mode (10+ rooms) and report what discount tier the page promises.",
     'group'),
    # late-checkout-request
    ("On a booking in {city}, open the manage-stay flow and submit a late-checkout request (3pm); report whether the request is auto-confirmed.",
     'late-checkout'),
    ("Open the booking detail for a confirmed {city} stay and request a 4pm checkout; report any surcharge displayed.",
     'late-checkout'),
    # room-upgrade-offer
    ("On a {city} property detail page, scroll to room types and check whether an 'upgrade offer' is shown for a Deluxe Queen Room; report the upgrade price.",
     'upgrade'),
    ("Open the manage-stay flow for a {city} reservation and accept the room upgrade offer; report the new room type.",
     'upgrade'),
    # dietary-meal-preference
    ("On the checkout flow for a {city} hotel, set dietary preferences (vegan + gluten-free) and report whether the property confirms it can accommodate both.",
     'dietary'),
    ("On a {city} property detail page, check the breakfast section for halal options; report the listed options.",
     'dietary'),
    ("In {city}, find a property whose amenities include 'Vegan / vegetarian menu' AND 'Gluten-free options'; report its name.",
     'dietary'),
    # multi-step compound
    ("Search {city} hotels with pool + spa + free cancellation, sort by review score, open the top result, and report its sustainability certification.",
     'compound'),
    ("In {city}, find an eco-certified property under $250 with airport shuttle and breakfast included; report its name, rating, and certification level.",
     'compound'),
    ("Open a 5-star hotel in {city}, check the languages spoken at the front desk, and report whether Mandarin Chinese is listed.",
     'compound'),
    ("Search {city}, apply 'wheelchair accessible' + 'pet-friendly' filters, sort by price ascending; report the cheapest property and its accepted payment methods.",
     'compound'),
    ("On a {city} property page, click the photo lightbox to expand the gallery and report how many photos are listed in total.",
     'compound'),
    ("Use the search page map view in {city}, click 'Search this area' after panning, and report whether the result count changes.",
     'compound'),
    # New field tasks — sustainability_certification / payment_options / languages / neighborhood_summary
    ("On a {city} property detail page, find the sustainability section and report the certification level shown.",
     'sustain'),
    ("Open a 4-star hotel in {city} and report the list of payment options the property accepts.",
     'payment'),
    ("On a {city} hotel detail page, find the languages-spoken section and report whether Japanese is listed.",
     'language'),
    ("Open a {city} property and read the neighbourhood summary; report the first landmark mentioned.",
     'neighborhood'),
    # Extra R5 templates — fill out the unique-question quota.
    ("On a {city} property page, click 'See all photos' to open the lightbox gallery; report the total photo count.",
     'lightbox'),
    ("On /search?city={city}, narrow to 5-star + free cancellation, click Apply filters, and report the top property name.",
     'sidebar-apply'),
    ("Open the calendar-availability page for a {city} property; report whether weekend dates enforce a minimum stay.",
     'min-stay'),
    ("On the mobile-style ≤480 layout for a {city} search, scroll to the sticky-bottom price bar; report whether a 'Reserve' CTA is visible.",
     'mobile'),
]


def gen_tasks(cities, start_id, target_total=800):
    """Round-robin: for each template, walk the city list deterministically.
    Skips duplicate (template, city) pairs so every emitted ques is unique.

    `start_id` is the next free Booking--N id (>= current tasks.jsonl max+1).
    """
    out = []
    seen = set()
    idx = start_id
    # Walk (template, city) once — uniqueness guaranteed because the pair
    # is unique by construction and no template uses extra entropy.
    for tmpl, kind in R5_TASK_TEMPLATES:
        if len(out) >= target_total:
            break
        for ck in TASK_CITIES_BIG:
            if len(out) >= target_total:
                break
            if ck not in cities:
                continue
            disp = cities[ck]['display']
            ques = tmpl.format(city=disp)
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
    """Read tasks.jsonl and return max(N)+1 from Booking--N ids."""
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

    hotels = gen_hotels(cities, target_total=3500)
    print(f"  hotels generated: {len(hotels)}")
    with open(SCRAPED / 'expansion_hotels_r5.json', 'w') as f:
        json.dump(hotels, f, indent=1, ensure_ascii=False, sort_keys=True)

    start_id = _next_task_id()
    print(f"  task start id: Booking--{start_id}")
    tasks = gen_tasks(cities, start_id=start_id, target_total=820)
    print(f"  tasks generated: {len(tasks)}")
    with open(SCRAPED / 'expansion_tasks_r5.jsonl', 'w') as f:
        for t in tasks:
            f.write(json.dumps(t, ensure_ascii=False) + '\n')


if __name__ == '__main__':
    main()
