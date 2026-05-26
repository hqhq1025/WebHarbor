#!/usr/bin/env python3
"""R6 expansion generator (booking mirror).

Run once on the build host:

    python3 sites/booking/scripts/gen_r6_expansion.py

Outputs (deterministic, hash-derived; rerunning produces the same bytes):
- scraped_data/expansion_hotels_r6.json
- scraped_data/expansion_tasks_r6.jsonl

R6 focus:
- Push property count from ~11080 -> ~16000+ by adding ~5000 procedural hotels
  with R6-specific prefixes that don't collide with R4/R5 output.
- Add 6 edge-case task categories (fully-booked-suggest-similar /
  dates-not-available-flex-suggest / payment-3DSecure-fail /
  cancellation-window-passed / room-removed-during-booking /
  currency-conversion-rate-disclosure) and a wide multi-step cross-page set
  to push task count from 1972 -> 3000+.
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
# Cities — mirror the R4/R5 core list and fold in expansion_cities.json.
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
# R6 hotels — distinctive name shapes so they don't collide with R4 / R5.
# Structure: "{R6_PREFIX} {Brand} {City} {Suffix}" (or boutique 3-token form).
# ---------------------------------------------------------------------------
R6_PREFIXES = [
    'Beacon', 'Meridian', 'Cascade', 'Arcadia', 'Hemisphere',
    'Polaris', 'Tessera', 'Marquee', 'Sundial', 'Wayfarer',
    'Lumiere', 'Halcyon', 'Quartz', 'Onyx', 'Indigo',
    'Driftwood', 'Sapphire', 'Ember', 'Sterling', 'Crescent',
    'Hummingbird', 'Sequoia', 'Magnolia', 'Heron', 'Falcon',
]
R6_BRANDS = [
    'Hilton', 'Marriott', 'Accor', 'IHG', 'Hyatt',
    'Wyndham', 'Best Western', 'Independent', 'Luxury Collection',
    'Boutique', 'Hostel Group',
]
R6_SUFFIXES = [
    'Heights', 'Plaza', 'Terrace', 'Crossing', 'Embassy',
    'Annex', 'Chambers', 'Loft', 'Atelier', 'Penthouse',
    'Mews', 'Conservatory', 'Estate', 'Refuge', 'Quarter',
    'Promenade',
]
R6_NEIGHBORHOODS = [
    'Old Quarter', 'Theatre Lane', 'Embassy District', 'Cathedral Row',
    'Greenway', 'Stadium Quarter', 'Heritage Boulevard', 'Marina Front',
    'Studio Quarter', 'Festival Street', 'Tech Mile', 'Garden Crescent',
    'Riverside Walk', 'Designer Row', 'Promenade Side', 'Botanic Reach',
]
R6_TYPES = ['Hotel', 'Apartment', 'Resort', 'Villa',
            'Bed and Breakfast', 'Hostel', 'Guest House', 'Cabin']


def gen_hotels(cities, target_total=5000):
    out = []
    keys = list(cities.keys())
    core_keys = [k for k in [c[0] for c in CORE] if k in cities]
    exp_keys = [k for k in keys if k not in core_keys]
    # Heavier weighting on core cities so popular destinations get richer.
    core_per = max(1, target_total * 55 // 100 // max(1, len(core_keys)))
    exp_per = max(1, target_total * 45 // 100 // max(1, len(exp_keys))) if exp_keys else 0
    seen = set()

    def emit(city_key, n):
        c = cities[city_key]
        cdisp = c['display']
        for i in range(n):
            prefix = R6_PREFIXES[_hkey('r6-pf', city_key, i) % len(R6_PREFIXES)]
            brand = R6_BRANDS[_hkey('r6-br', city_key, i) % len(R6_BRANDS)]
            suffix = R6_SUFFIXES[_hkey('r6-sf', city_key, i) % len(R6_SUFFIXES)]
            nbh = R6_NEIGHBORHOODS[_hkey('r6-nb', city_key, i) % len(R6_NEIGHBORHOODS)]
            stars_pool = [2, 3, 3, 3, 4, 4, 4, 4, 5, 5]
            stars = stars_pool[_hkey('r6-st', city_key, i, brand) % len(stars_pool)]
            ptype = R6_TYPES[_hkey('r6-pt', city_key, i) % len(R6_TYPES)]
            # Name composition — keep distinct from R4 ("{Brand} {Suffix}
            # {City}{flavour}") and R5 ("{Concept} {Brand} {City} {Suffix}").
            if brand in ('Luxury Collection', 'Boutique', 'Hostel Group',
                         'Independent'):
                name = f"{prefix} {cdisp} {suffix}"
            else:
                name = f"{prefix} {brand} {cdisp} {suffix}"
            key = (name.lower(), city_key)
            if key in seen:
                # Disambiguate with a numeric suffix; keep deterministic.
                name = f"{name} {i + 1}"
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
# R6 tasks — 6 mandated edge-case categories + multi-step cross-page set +
# cross-link sections (same-area / you-might-also-like / compare / wishlist).
# ---------------------------------------------------------------------------
TASK_CITIES_BIG = [
    'paris', 'london', 'nyc', 'tokyo', 'rome', 'barcelona', 'dubai',
    'singapore', 'bali', 'sydney', 'amsterdam', 'bangkok', 'maldives',
    'istanbul', 'losangeles', 'berlin', 'prague', 'vienna', 'venice',
    'santorini', 'mexicocity', 'rio', 'jakarta', 'chicago', 'lisbon',
    'melbourne', 'toronto', 'hongkong', 'sapporo', 'shenzhen',
    'chennai', 'varanasi', 'ohio',
]

R6_TASK_TEMPLATES = [
    # -------------------- EDGE CASES (6 categories) --------------------
    # 1. property-fully-booked-suggest-similar
    ("Open a popular {city} property and pick a check-in 2 days out; if the property is fully booked, scroll to 'Similar properties nearby' and report the first suggested name.",
     'edge-fullybooked'),
    ("Try to reserve a {city} 5-star hotel for tonight; if the room shows as fully booked, report which similar property the page recommends instead.",
     'edge-fullybooked'),
    ("On a {city} hotel detail page, attempt to add a Penthouse Suite on a peak weekend; if it's sold out, report the alternative property the 'Similar properties nearby' section surfaces first.",
     'edge-fullybooked'),
    # 2. dates-not-available-flex-suggest
    ("On a {city} property, pick a check-in/checkout pair that the calendar shows unavailable; report what date range the flex-date tool then suggests.",
     'edge-flexdate'),
    ("On /tools/calendar-availability for a {city} property, select an unavailable weekend; report the nearest available 3-night window the calendar offers.",
     'edge-flexdate'),
    ("In {city}, try a 4-night stay across dates that span the calendar's red 'unavailable' cells; report the closest available 4-night window suggested.",
     'edge-flexdate'),
    # 3. payment-3DSecure-fail
    ("On the {city} checkout flow, submit payment with a card whose 3D Secure step fails; report exactly what the page says the user should do next.",
     'edge-3ds'),
    ("During the {city} checkout, simulate a failed 3D Secure verification on a Visa card; report whether the booking is held or cancelled.",
     'edge-3ds'),
    ("Open the {city} checkout page and review the 3D Secure / Strong Customer Authentication disclosure; report which card types require the extra step.",
     'edge-3ds'),
    # 4. cancellation-window-passed
    ("In manage-trip, open a {city} booking whose free-cancellation window has passed; report what fee the page now shows for cancelling.",
     'edge-cancwindow'),
    ("For a confirmed {city} booking past its cancellation deadline, click 'Cancel booking' and report the wording about the non-refundable amount.",
     'edge-cancwindow'),
    ("On a {city} booking detail page where cancellation is no longer free, report whether the 'Cancel booking' button is still clickable.",
     'edge-cancwindow'),
    # 5. room-removed-during-booking
    ("Add a {city} property's Executive Suite to your bag, then return to the property; report what the page says if the Executive Suite is no longer available.",
     'edge-roomgone'),
    ("On the {city} checkout review screen, simulate a room being removed mid-flow (Family Room sold out); report which room type the page substitutes.",
     'edge-roomgone'),
    ("In a {city} cart, refresh the bag and report what is shown if a Junior Suite line item gets pulled from availability before checkout.",
     'edge-roomgone'),
    # 6. currency-conversion-rate-disclosure
    ("On a {city} property page, switch the currency selector to CNY and report the conversion rate disclosed at the bottom of the price line.",
     'edge-currency'),
    ("Open /search?city={ck}&currency=EUR for {city}; report whether the search cards disclose the USD->EUR conversion rate used.",
     'edge-currency'),
    ("On the {city} checkout page in JPY, scroll to the price breakdown and report the disclosed JPY rate plus whether a 'rates subject to change' notice is visible.",
     'edge-currency'),

    # -------------------- CROSS-PAGE / CROSS-LINK -----------------------
    # Breadcrumb (Home > City > Neighborhood > Property)
    ("On a {city} property detail page, copy the full breadcrumb trail (Home > City > Neighborhood > Property) and report all four segments.",
     'crumb'),
    ("Open a {city} hotel detail page and report the neighbourhood name shown in the breadcrumb between the city and the property name.",
     'crumb'),
    # Other properties in same area
    ("On a {city} property page, scroll to 'Other properties in same area' and report how many properties are listed there.",
     'samearea'),
    ("Open a {city} property and report the cheapest property listed in 'Other properties in same area'.",
     'samearea'),
    ("On a {city} hotel page, find a property in the 'Other properties in same area' carousel that has free cancellation; report its name.",
     'samearea'),
    # You might also like (different city, same dest_category)
    ("On a {city} property detail page, scroll to 'You might also like'; report the first city that appears (it should be different from {city}).",
     'mightlike'),
    ("Open a luxury hotel in {city}; the 'You might also like' panel should suggest similar luxury stays in other cities — report the top 3 city names.",
     'mightlike'),
    # Compare 3
    ("On a {city} property page, use the 'Compare' tool to add 3 hotels and report which property has the highest review score.",
     'compare3'),
    ("In {city}, pick 3 hotels with different brands and use 'Compare 3' to report which one has the lowest price per night.",
     'compare3'),
    ("Use the Compare-3 cross-link from a {city} property detail; report which amenity is present in all three compared properties.",
     'compare3'),
    # Wishlist cross-link
    ("On a {city} property detail page, click 'Save to wishlist' and confirm the wishlist counter in the header increases by 1.",
     'wishlistlink'),
    ("From a {city} property page, follow the 'Wishlist' cross-link to /saved and report whether the property appears in the list.",
     'wishlistlink'),

    # -------------------- LONG MULTI-STEP COMPOUND ----------------------
    # home -> search -> city -> property -> rooms -> reviews -> photos ->
    # booking-flow -> confirmation -> manage-trip (10-step)
    ("Walk the full booking journey for {city}: home -> Stays -> /search?city={ck} -> /city/{cslug} -> property -> /property/<slug>/rooms -> reviews -> photos lightbox -> reserve -> confirmation. Report the final confirmation booking number prefix.",
     'long10'),
    ("In one continuous flow, from the homepage navigate Stays > {city} > top property > Rooms > Reviews > Photos > Reserve > Manage trip; report the title of the manage-trip page.",
     'long10'),
    ("Plan a {city} trip end-to-end: search, open the first result, view all photos in the lightbox, scroll to reviews and read the most-recent review's title, then add to cart; report that review title.",
     'long10'),
    # Multi-step split-stay + flight + car
    ("Build a 5-night split-stay in {city} (3 nights + 2 nights at two different hotels), add a return flight to your bag, then add a car rental for the same dates; report the bag's grand total.",
     'split-plus-fc'),
    ("In {city}, create a split-stay (2 hotels of different star tiers) and stack on /flights and /car-rentals; report the cheapest combination total found.",
     'split-plus-fc'),
    ("Plan a {city} family trip with a 4-night split-stay + airport taxi + car rental + return flight, all added via the bag; report the count of distinct items in the bag.",
     'split-plus-fc'),
    # Saved -> calendar -> add-room -> checkout
    ("Open a saved {city} property from /saved, click through to /tools/calendar-availability/<slug>, pick the cheapest available 2-night window, then add a Standard Double Room and proceed to checkout; report the displayed nightly rate.",
     'saved-to-checkout'),
    ("From /saved, pick a wishlisted {city} hotel, open its calendar-availability page, choose a weekday window, add an Executive Suite, and arrive at /checkout; report the room subtotal.",
     'saved-to-checkout'),
    ("Starting at /saved, open a saved {city} hotel, jump to calendar-availability, pick the first available 3-night window, add a Family Room, and proceed to checkout; report the room type confirmed on the checkout page.",
     'saved-to-checkout'),
]


def gen_tasks(cities, start_id, target_total=1100):
    """Walk (template, city) once per pair; uniqueness guaranteed by
    construction (every (template, city_display) pair is distinct)."""
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
    for tmpl, kind in R6_TASK_TEMPLATES:
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

    hotels = gen_hotels(cities, target_total=5800)
    print(f"  hotels generated: {len(hotels)}")
    with open(SCRAPED / 'expansion_hotels_r6.json', 'w') as f:
        json.dump(hotels, f, indent=1, ensure_ascii=False, sort_keys=True)

    start_id = _next_task_id()
    print(f"  task start id: Booking--{start_id}")
    tasks = gen_tasks(cities, start_id=start_id, target_total=1100)
    print(f"  tasks generated: {len(tasks)}")
    with open(SCRAPED / 'expansion_tasks_r6.jsonl', 'w') as f:
        for t in tasks:
            f.write(json.dumps(t, ensure_ascii=False) + '\n')


if __name__ == '__main__':
    main()
