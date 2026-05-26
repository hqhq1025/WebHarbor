#!/usr/bin/env python3
"""R4 expansion generator (booking mirror).

Run once on the build host:

    python3 sites/booking/scripts/gen_r4_expansion.py

Outputs (deterministic, hash-derived; rerunning produces the same bytes):
- scraped_data/expansion_hotels_r4.json
- scraped_data/expansion_attractions_r4.json
- scraped_data/expansion_taxis_r4.json
- scraped_data/expansion_tasks_r4.jsonl

The expansion files are folded into the seed pipeline by seed_data.py /
app.py at boot time, so re-running this script after editing constants
re-derives byte-identical seed data.
"""
import hashlib
import json
import os
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
SCRAPED = BASE / 'scraped_data'
SCRAPED.mkdir(exist_ok=True)


def _hkey(*parts):
    """Stable hash-based numeric key in [0, 2**32)."""
    h = hashlib.sha256('|'.join(str(p) for p in parts).encode('utf-8')).digest()
    return int.from_bytes(h[:4], 'big')


def _pick(parts, items):
    return items[_hkey(*parts) % len(items)]


# ---------------------------------------------------------------------------
# Source: existing expansion_cities.json gives us 280+ city_keys with display
# names + country + property counts. We'll generate procedural hotels for the
# top N cities (where we already have property images and basic geometry).
# ---------------------------------------------------------------------------
def _load_existing_cities():
    """Pull city_key -> display from the existing expansion file and the
    main CITY_INFO dict (the latter via re-parse of seed_data.py - simpler
    to mirror the list here so the script is self-contained)."""
    cities = {}
    # Core city_keys with native gallery directories (mirrors seed_data.py
    # CITY_INFO entries that have native image_map gallery keys).
    core = [
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
    for k, disp, cc in core:
        cities[k] = {'display': disp, 'country_code': cc}

    # Also fold in any expansion_cities.json entries (~280 rows).
    exp = SCRAPED / 'expansion_cities.json'
    if exp.exists():
        for row in json.load(open(exp)):
            k, disp, slug, country, cc = row[0], row[1], row[2], row[3], row[4]
            if k not in cities:
                cities[k] = {'display': disp, 'country_code': cc}
    return cities


# ---------------------------------------------------------------------------
# HOTELS — procedural expansion. Each (city, neighborhood, brand, style)
# tuple becomes a hotel name. We pick a small per-city set so we hit a clean
# +2500 total without over-saturating any single city.
# ---------------------------------------------------------------------------
NEIGHBORHOODS_GENERIC = [
    'Downtown', 'Old Town', 'Riverside', 'Harbor District', 'Financial District',
    'Theatre District', 'Cathedral Quarter', 'Museum Quarter', 'University District',
    'Garden District', 'Park View', 'Airport Area', 'Convention Center',
]
BRAND_TEMPLATES = [
    # (brand, suffix_pool, stars)
    ('Hilton',    ['Garden Inn', 'Hotel', 'DoubleTree', 'Curio Collection', 'Tapestry'], 4),
    ('Marriott',  ['Hotel', 'Courtyard', 'Residence Inn', 'AC Hotel', 'Element'], 4),
    ('Accor',     ['Novotel', 'Pullman', 'Sofitel', 'Mercure', 'Ibis Styles'], 4),
    ('IHG',       ['Holiday Inn', 'Crowne Plaza', 'Holiday Inn Express', 'Indigo'], 3),
    ('Hyatt',     ['Hyatt Place', 'Hyatt House', 'Andaz', 'Hyatt Regency'], 4),
    ('Wyndham',   ['Wyndham', 'Days Inn', 'Ramada', 'La Quinta'], 3),
    ('Best Western', ['Best Western', 'Best Western Plus'], 3),
    ('Independent', ['Boutique', 'Suites', 'Inn', 'Residence', 'Lodge', 'Place', 'House'], 3),
    ('Luxury Collection', ['Grand', 'Palace', 'Imperial', 'Royal', 'Heritage'], 5),
]
PROP_TYPES = ['Hotel', 'Apartment', 'Resort', 'Villa', 'Bed and Breakfast', 'Hostel', 'Guest House', 'Cabin']


def _make_hotel_name(brand, suffix, city_display, neighborhood, salt):
    """Compose a plausible property name."""
    flavour = _pick(('flav', brand, suffix, city_display, neighborhood, salt),
                    ['', f' {neighborhood}', f' City Centre', f' Downtown',
                     f' Airport', f' Express', f' Plaza'])
    if brand == 'Luxury Collection':
        return f"The {suffix} {city_display}{flavour}".strip()
    if brand == 'Independent':
        prefixes = ['The', 'Hotel', 'Casa', 'Maison', 'Villa']
        pfx = _pick(('pfx', city_display, suffix, salt), prefixes)
        return f"{pfx} {suffix} {city_display}{flavour}".strip()
    return f"{brand} {suffix} {city_display}{flavour}".strip()


def _make_prop_type(brand):
    if brand == 'Luxury Collection':
        return _pick(('pt-lux', brand), ['Hotel', 'Resort', 'Villa'])
    if brand == 'Independent':
        return _pick(('pt-ind',), PROP_TYPES)
    return 'Hotel'


def gen_hotels(cities, target_total=2500):
    """Yield approximately target_total procedural hotels distributed
    across cities, weighted by city tier (core cities get more)."""
    out = []
    # Weighted: core cities get ~50 each, expansion cities ~5 each.
    core_keys = list(cities.keys())[:33]   # first 33 = core
    exp_keys = list(cities.keys())[33:]
    core_per = max(1, target_total * 60 // 100 // max(1, len(core_keys)))  # ~45 ea
    exp_per = max(1, target_total * 40 // 100 // max(1, len(exp_keys))) if exp_keys else 0

    seen_names = set()

    def emit(city_key, n):
        city = cities[city_key]
        for i in range(n):
            brand, suffixes, base_stars = BRAND_TEMPLATES[_hkey('bt', city_key, i) % len(BRAND_TEMPLATES)]
            suffix = suffixes[_hkey('sf', city_key, i, brand) % len(suffixes)]
            nbh = NEIGHBORHOODS_GENERIC[_hkey('nbh', city_key, i) % len(NEIGHBORHOODS_GENERIC)]
            star_bump = (_hkey('bump', city_key, i, brand) % 3) - 1  # -1, 0, +1
            stars = max(1, min(5, base_stars + star_bump))
            ptype = _make_prop_type(brand)
            name = _make_hotel_name(brand, suffix, city['display'], nbh, i)
            key = (name.lower(), city_key)
            if key in seen_names:
                # Fallback: append numeric to disambiguate
                name = f"{name} {i+1}"
            seen_names.add((name.lower(), city_key))
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
# ATTRACTIONS — generate procedural tour/ticket variants for each city.
# Schema must match Attraction model: city_key, city_display, category, name,
# description_short, price_usd, duration_hours, rating, review_count,
# instant_confirmation, free_cancellation, mobile_voucher
# ---------------------------------------------------------------------------
TOUR_VARIANTS = [
    ('Skip-the-line', 30, 2),
    ('Private Guided', 65, 3),
    ('Half-Day Walking', 28, 4),
    ('Full-Day', 85, 8),
    ('Sunset', 42, 2),
    ('Evening Lights', 38, 2),
    ('Photography', 55, 3),
    ('Family Fun', 35, 3),
    ('Audio Tour', 18, 2),
    ('VIP Access', 120, 3),
    ('Cultural Heritage', 48, 4),
    ('Food & Drink', 72, 4),
    ('Bike', 33, 3),
    ('Boat', 60, 2),
    ('Helicopter', 280, 1),
    ('Hop-on Hop-off Bus', 22, 8),
    ('Behind-the-Scenes', 88, 3),
    ('Eco-friendly Nature', 45, 4),
    ('Wellness & Spa Day', 95, 5),
    ('Wine Tasting', 65, 3),
]
ATTR_TOPICS = [
    ('Historic Old Town', 'tour'),
    ('Famous Cathedral', 'tour'),
    ('Royal Palace', 'tour'),
    ('Sky Observation Deck', 'ticket'),
    ('Botanical Gardens', 'ticket'),
    ('Iconic Museum', 'museum'),
    ('National Gallery', 'museum'),
    ('Historic Castle', 'tour'),
    ('River Cruise', 'cruise'),
    ('Harbour Cruise', 'cruise'),
    ('Cooking Class', 'experience'),
    ('Street Food', 'tour'),
    ('Theme Park', 'theme_park'),
    ('Theatre Show', 'show'),
    ('Open-air Market', 'tour'),
    ('Cycling Loop', 'sport'),
    ('Day Trip Excursion', 'day_trip'),
    ('Heritage Train Ride', 'transport'),
]


def gen_attractions(cities, target_total=2700):
    out = []
    # Distribute roughly 30 per core city, 5 per expansion city.
    keys = list(cities.keys())
    core_keys = keys[:33]
    exp_keys = keys[33:]
    per_core = target_total // 2 // max(1, len(core_keys))   # ~40
    per_exp = target_total // 2 // max(1, len(exp_keys))     # ~5

    seen = set()

    def emit(city_key, n):
        c = cities[city_key]
        for i in range(n):
            topic, category = ATTR_TOPICS[_hkey('attr-topic', city_key, i) % len(ATTR_TOPICS)]
            variant, base_price, base_dur = TOUR_VARIANTS[_hkey('attr-var', city_key, i) % len(TOUR_VARIANTS)]
            name = f"{c['display']} {topic}: {variant}"
            if (name, city_key) in seen:
                name = f"{name} #{i+1}"
            seen.add((name, city_key))
            price_jitter = (_hkey('attr-pj', city_key, i) % 21) - 10  # -10..+10
            price = max(8.0, round(base_price + price_jitter * 1.3, 2))
            rating = round(7.5 + (_hkey('attr-r', city_key, i) % 26) / 10.0, 1)  # 7.5-10.0
            reviews_n = 30 + (_hkey('attr-rc', city_key, i) % 2000)
            insta = bool(_hkey('attr-ic', city_key, i) % 2)
            cancel = bool(_hkey('attr-fc', city_key, i) % 3)  # ~2/3
            voucher = bool(_hkey('attr-mv', city_key, i) % 4 != 0)  # ~3/4
            duration = max(1, base_dur + ((_hkey('attr-dh', city_key, i) % 5) - 2))
            out.append({
                'city_key': city_key,
                'city_display': c['display'],
                'category': category,
                'name': name,
                'description_short':
                    f"Discover {c['display']}'s {topic.lower()} with a {variant.lower()} experience. "
                    f"Approximately {duration} hour{'s' if duration > 1 else ''}.",
                'price_usd': price,
                'duration_hours': duration,
                'rating': rating,
                'review_count': reviews_n,
                'instant_confirmation': insta,
                'free_cancellation': cancel,
                'mobile_voucher': voucher,
            })

    for k in core_keys:
        emit(k, per_core)
    for k in exp_keys:
        emit(k, per_exp)
    return out


# ---------------------------------------------------------------------------
# AIRPORT TAXIS — schema:
#   airport_code, city_key, city_display, destination, distance_km, vehicle,
#   vehicle_desc, seats, quote_usd, free_cancellation, meet_and_greet,
#   flight_tracking
# ---------------------------------------------------------------------------
AIRPORT_BY_CITY = {
    'nyc': ('JFK', 'JFK Airport', 32), 'paris': ('CDG', 'Charles de Gaulle', 28),
    'london': ('LHR', 'Heathrow', 30), 'tokyo': ('HND', 'Haneda', 18),
    'dubai': ('DXB', 'Dubai Intl', 12), 'rome': ('FCO', 'Fiumicino', 30),
    'barcelona': ('BCN', 'El Prat', 15), 'bali': ('DPS', 'Ngurah Rai', 14),
    'amsterdam': ('AMS', 'Schiphol', 17), 'singapore': ('SIN', 'Changi', 22),
    'maldives': ('MLE', 'Velana Intl', 9), 'bangkok': ('BKK', 'Suvarnabhumi', 33),
    'hongkong': ('HKG', 'Chek Lap Kok', 35), 'istanbul': ('IST', 'New IST', 50),
    'sydney': ('SYD', 'Kingsford Smith', 12), 'losangeles': ('LAX', 'LAX', 25),
    'berlin': ('BER', 'Brandenburg', 25), 'prague': ('PRG', 'Vaclav Havel', 17),
    'vienna': ('VIE', 'Schwechat', 18), 'venice': ('VCE', 'Marco Polo', 13),
    'mexicocity': ('MEX', 'Benito Juarez', 13), 'rio': ('GIG', 'Galeao', 25),
    'jakarta': ('CGK', 'Soekarno-Hatta', 28), 'chicago': ('ORD', 'O\'Hare', 28),
    'lisbon': ('LIS', 'Portela', 9), 'melbourne': ('MEL', 'Tullamarine', 23),
    'toronto': ('YYZ', 'Pearson', 25), 'shenzhen': ('SZX', 'Baoan', 32),
    'sapporo': ('CTS', 'New Chitose', 50),
}
VEHICLE_TIERS = [
    ('Economy Sedan', '3 passengers, 2 bags', 3, 1.0),
    ('Comfort Sedan', '3 passengers, 3 bags', 3, 1.3),
    ('Business Class', '3 passengers, 3 bags, executive', 3, 1.8),
    ('SUV', '5 passengers, 5 bags', 5, 1.6),
    ('Minivan', '7 passengers, 6 bags', 7, 1.7),
    ('Luxury Limo', '4 passengers, premium service', 4, 2.6),
    ('Electric Vehicle', '3 passengers, 2 bags, zero-emission', 3, 1.4),
    ('Wheelchair Accessible', 'Lift-equipped, ramp access', 3, 1.4),
]
DEST_VARIANTS = [
    'City Centre', 'Old Town', 'Convention Center', 'Beach District',
    'Financial District', 'University District', 'Theatre District',
    'Cruise Port', 'Train Station',
]


def gen_taxis(cities, target_total=1500):
    out = []
    keys_with_air = [k for k in AIRPORT_BY_CITY.keys() if k in cities]
    per_city = max(1, target_total // max(1, len(keys_with_air)))  # ~50
    for ck in keys_with_air:
        airport, _ap_name, base_km = AIRPORT_BY_CITY[ck]
        cdisp = cities[ck]['display']
        for i in range(per_city):
            tier_idx = _hkey('taxi-tier', ck, i) % len(VEHICLE_TIERS)
            v_name, v_desc, seats, mult = VEHICLE_TIERS[tier_idx]
            dest_pick = DEST_VARIANTS[_hkey('taxi-dest', ck, i) % len(DEST_VARIANTS)]
            distance_jit = (_hkey('taxi-dj', ck, i) % 11) - 5  # +/-5
            distance = max(5, base_km + distance_jit)
            base = 20 + base_km * 1.2
            quote_jit = (_hkey('taxi-qj', ck, i) % 9) - 4
            quote = round(base * mult + quote_jit, 2)
            cancel = bool(_hkey('taxi-cancel', ck, i) % 4 != 0)
            meet = bool(_hkey('taxi-meet', ck, i) % 2)
            track = bool(_hkey('taxi-track', ck, i) % 5 != 0)
            out.append({
                'airport_code': airport,
                'city_key': ck,
                'city_display': cdisp,
                'destination': f"{cdisp} {dest_pick}",
                'distance_km': distance,
                'vehicle': v_name,
                'vehicle_desc': v_desc,
                'seats': seats,
                'quote_usd': quote,
                'free_cancellation': cancel,
                'meet_and_greet': meet,
                'flight_tracking': track,
            })
    return out


# ---------------------------------------------------------------------------
# TASKS — generate procedural natural-language tasks for new templates.
# ---------------------------------------------------------------------------
TASK_TEMPLATES = [
    # (template, sample city list, kind)
    ("On /city/{slug}/things-to-do, list 3 attractions in {city} with their rating.",
     ['paris', 'london', 'nyc', 'tokyo', 'rome', 'barcelona', 'dubai', 'singapore', 'bali'], 'sub'),
    ("Open /property/{slug}/rooms for a hotel in {city} and report how many room types it offers.",
     ['paris', 'london', 'nyc', 'tokyo'], 'sub'),
    ("On /awards, find a Traveller Review Award winner in {city} and report its rating.",
     ['paris', 'london', 'nyc', 'tokyo', 'rome', 'barcelona', 'sydney', 'amsterdam'], 'sub'),
    ("Visit /tools/value-checker, enter '{city}' for check-in next week, and report what the tool says about average nightly price.",
     ['paris', 'london', 'nyc', 'tokyo', 'rome', 'bangkok', 'bali'], 'tool'),
    ("Use /tools/calendar-availability for a property in {city}, browse the 2-month calendar and report whether any weekend dates are unavailable.",
     ['paris', 'london', 'nyc', 'tokyo', 'rome', 'maldives'], 'tool'),
    ("On /list-your-property, walk through host onboarding and report the final-step CTA text.",
     ['paris'], 'tool'),
    ("On /reviews-tool, search '{city}' and report the top property by sub-score 'Cleanliness'.",
     ['paris', 'london', 'nyc', 'tokyo', 'rome', 'barcelona', 'dubai'], 'tool'),
    # New filters
    ("On /search?city={ck}, apply the 'Pet-friendly' filter and report how many properties remain.",
     ['paris', 'london', 'nyc', 'tokyo', 'rome', 'sydney', 'amsterdam'], 'filter'),
    ("On /search?city={ck}, apply the 'Accessibility' filter (wheelchair accessible) and report top-3 names.",
     ['paris', 'london', 'nyc', 'rome', 'tokyo'], 'filter'),
    ("On /search?city={ck}, apply the 'Eco-certified' filter and report how many properties remain.",
     ['paris', 'london', 'amsterdam', 'tokyo', 'bali', 'singapore'], 'filter'),
    ("On /property/{slug}, click 'Virtual tour' and report whether a virtual tour is available.",
     ['paris', 'london', 'nyc', 'maldives'], 'sub'),
    ("On /airport-taxis, request a quote from {airport} to {city} city centre and report the cheapest vehicle class.",
     ['paris', 'london', 'nyc', 'tokyo', 'dubai'], 'taxi'),
    ("On /genius-rewards, use frequent-flyer redeem-points-for-stay and report how many points are needed for a 1-night stay in {city}.",
     ['paris', 'london', 'nyc'], 'sub'),
    # Compound multi-step
    ("Search hotels in {city} with pool + gym + breakfast included, then sort by review score and report top-3 names.",
     ['paris', 'london', 'nyc', 'tokyo', 'rome', 'barcelona', 'bali'], 'compound'),
    ("Find a hotel in {city} priced under $200 that offers airport shuttle AND is eco-certified; report its name and rating.",
     ['paris', 'london', 'amsterdam', 'singapore', 'tokyo'], 'compound'),
    ("On /search?city={ck}, switch to map view and report how many cluster pins are visible at default zoom.",
     ['paris', 'london', 'nyc', 'tokyo', 'rome', 'barcelona'], 'mapview'),
    # Visual / accordion
    ("Open a {city} property detail page, expand the room accordion, and report how many room types are listed.",
     ['paris', 'london', 'nyc', 'tokyo'], 'sub'),
]


CITY_TO_SLUG = {
    'paris': 'paris', 'london': 'london', 'nyc': 'new-york', 'tokyo': 'tokyo',
    'rome': 'rome', 'barcelona': 'barcelona', 'dubai': 'dubai',
    'singapore': 'singapore', 'bali': 'bali', 'sydney': 'sydney',
    'amsterdam': 'amsterdam', 'bangkok': 'bangkok', 'maldives': 'maldives',
}
AIRPORT_LOOKUP = {ck: AIRPORT_BY_CITY[ck][0] for ck in AIRPORT_BY_CITY}


def gen_tasks(cities, start_id=552, target_total=600):
    """Round-robin through templates and city lists, deterministically."""
    out = []
    idx = start_id
    counter = 0
    while len(out) < target_total:
        for tmpl, city_list, kind in TASK_TEMPLATES:
            if len(out) >= target_total:
                break
            for city_key in city_list:
                if len(out) >= target_total:
                    break
                c_disp = cities.get(city_key, {}).get('display', city_key.title())
                c_slug = CITY_TO_SLUG.get(city_key, city_key)
                # Some templates use {slug} (property slug). We'll inject a
                # synthetic slug derived from city for those.
                synth_slug = f"hilton-hotel-{c_slug}"
                airport = AIRPORT_LOOKUP.get(city_key, '')
                rep = tmpl.format(
                    city=c_disp, ck=city_key, slug=synth_slug, airport=airport,
                )
                # ensure determinism: add a salt per (idx, kind, counter)
                _ = _hkey('tk', idx, kind, counter)
                out.append({
                    'web_name': 'Booking',
                    'id': f'Booking--{idx}',
                    'ques': rep,
                    'web': 'http://localhost:40005/',
                    'upstream_url': 'https://www.booking.com/',
                })
                idx += 1
                counter += 1
    return out


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------
def main():
    cities = _load_existing_cities()
    print(f"  cities: {len(cities)}")

    hotels = gen_hotels(cities, target_total=2900)
    print(f"  hotels generated: {len(hotels)}")
    with open(SCRAPED / 'expansion_hotels_r4.json', 'w') as f:
        json.dump(hotels, f, indent=1, ensure_ascii=False, sort_keys=True)

    attrs = gen_attractions(cities, target_total=2900)
    print(f"  attractions generated: {len(attrs)}")
    with open(SCRAPED / 'expansion_attractions_r4.json', 'w') as f:
        json.dump(attrs, f, indent=1, ensure_ascii=False, sort_keys=True)

    taxis = gen_taxis(cities, target_total=1500)
    print(f"  taxis generated: {len(taxis)}")
    with open(SCRAPED / 'expansion_taxis_r4.json', 'w') as f:
        json.dump(taxis, f, indent=1, ensure_ascii=False, sort_keys=True)

    tasks = gen_tasks(cities, start_id=552, target_total=600)
    print(f"  tasks generated: {len(tasks)}")
    with open(SCRAPED / 'expansion_tasks_r4.jsonl', 'w') as f:
        for t in tasks:
            f.write(json.dumps(t, ensure_ascii=False) + '\n')


if __name__ == '__main__':
    main()
