#!/usr/bin/env python3
"""R9 expansion generator (booking mirror).

Run once on the build host:

    python3 sites/booking/scripts/gen_r9_expansion.py

Outputs (deterministic, hash-derived; rerunning produces the same bytes):
- scraped_data/expansion_hotels_r9.json
- scraped_data/expansion_tasks_r9.jsonl

R9 focus:
- Push property count from ~28316 -> ~35000+ by adding ~7000 procedural
  "Booking Plus" tier and curated boutique listings. R9 listings use the
  distinctive "Plus #NNNN" or "Boutique #NNNN" prefix so they don't collide
  with R4 / R5 / R6 / R7 / R8 outputs.
- Add 7 new task categories (+ multi-step compounds):
  1. loyalty-tier-upgrade-flow   (/loyalty/upgrade)
  2. business-traveler-expense   (/business/expense-report/<booking_ref>)
  3. weekend-getaway-recommend   (/weekend-getaway)
  4. repeat-guest-discount       (/repeat-guest)
  5. booking-plus-tier           (/booking-plus subscription tier)
  6. host-quality-score-explain  (/host/<host_id>/quality-score)
  7. multi-step                  (compounds chaining the above with R8)

Determinism contract (PYTHONHASHSEED=0): every value below derives from
sha256 of a stable key, so two fresh builds of instance/booking.db produce
the same md5. No `random` / `time.time()` / `id()`-leaking dict iteration.
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


# R9 listing taxonomy — Plus-tier boutique stays.
# Distinct from R8 ("Host #NNNN" / "{Host}'s {Style}") via "Plus #NNNN" prefix.
R9_BRANDS = [
    'Aurora', 'Beacon', 'Cinder', 'Daybreak', 'Ember', 'Folio',
    'Granite', 'Hearth', 'Indigo', 'Juniper', 'Kestrel', 'Lumen',
    'Moss', 'Nimbus', 'Ostro', 'Petal', 'Quay', 'Rune',
    'Sable', 'Tide', 'Umbra', 'Verdant', 'Wren', 'Yarrow', 'Zephyr',
]
R9_STYLES = [
    'Sunlit', 'Modernist', 'Atelier', 'Brutalist-soft', 'Mid-century',
    'Scandinavian', 'Heritage', 'Maximalist', 'Minimalist', 'Loft',
    'Garden', 'Top-floor', 'Courtyard', 'Light-filled',
    'Designer', 'Riverview', 'Skyline', 'Plaza',
    'Penthouse', 'Tower-suite', 'Annex', 'Retreat',
]
R9_TIERS = ['Plus', 'Plus', 'Plus', 'Plus', 'Boutique', 'Boutique', 'Curated']
R9_NEIGHBORHOODS = [
    'Old Town', 'Riverside Walk', 'Studio Quarter', 'Designer Lane',
    'Botanical Strip', 'Heritage Row', 'Market Yard', 'Civic Crescent',
    'Garden Court', 'Theatre Walk', 'Bay Promenade', 'University Mile',
    'Cathedral Reach', 'Plaza Loop', 'Atelier Block', 'Esplanade Court',
    'Cultural Crescent', 'Innovation Lane', 'Boulevard Annex', 'Skyline Reach',
    'Harbor Reach', 'Foundry Court', 'Lantern Quarter', 'Embassy Row',
    'Observatory Hill', 'Vineyard Lane',
]
# Plus-tier skews upmarket — stars 4/5 dominate.
R9_STAR_POOL = [3, 4, 4, 4, 4, 4, 5, 5, 5, 5]


def gen_hotels(cities, target_total=7200):
    out = []
    keys = list(cities.keys())
    core_keys = [k for k in [c[0] for c in CORE] if k in cities]
    exp_keys = [k for k in keys if k not in core_keys]
    core_per = max(1, target_total * 55 // 100 // max(1, len(core_keys)))
    exp_per = max(1, target_total * 45 // 100 // max(1, len(exp_keys))) if exp_keys else 0
    seen = set()

    def emit(city_key, n):
        c = cities[city_key]
        cdisp = c['display']
        for i in range(n):
            brand = R9_BRANDS[_hkey('r9-br', city_key, i) % len(R9_BRANDS)]
            style = R9_STYLES[_hkey('r9-st', city_key, i) % len(R9_STYLES)]
            tier = R9_TIERS[_hkey('r9-ti', city_key, i) % len(R9_TIERS)]
            nbh = R9_NEIGHBORHOODS[_hkey('r9-nb', city_key, i) % len(R9_NEIGHBORHOODS)]
            stars = R9_STAR_POOL[_hkey('r9-rs', city_key, i, brand) % len(R9_STAR_POOL)]
            listing_id = 10000 + (_hkey('r9-lid', city_key, i) % 89999)
            shape = _hkey('r9-shape', city_key, i) % 3
            if shape == 0:
                name = f"{tier} #{listing_id}: {brand} {style} in {nbh}, {cdisp}"
            elif shape == 1:
                name = f"{brand} {tier} {style} Suites — {nbh}, {cdisp}"
            else:
                name = f"{tier} {brand}: {style} {nbh} Stay, {cdisp}"
            key = (name.lower(), city_key)
            if key in seen:
                name = f"{name} (#{i + 1})"
                key = (name.lower(), city_key)
            seen.add(key)
            # Plus-tier listings are always Hotel/Apart-hotel — never STR-style.
            ptype = 'Apart-hotel' if (i % 4 == 0) else 'Hotel'
            out.append({
                'name': name,
                'type': ptype,
                'neighborhood': nbh,
                'city_key': city_key,
                'stars': stars,
                'is_plus_tier': True,
                'tier_label': tier,
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


# R9 task templates. Each item:
#   (question_template, surface_pattern)
# Surface patterns mirror the WebHarbor taxonomy so the SFT factory can
# rebalance later. Templates that contain `{city}` are emitted once per
# TASK_CITIES_BIG entry; templates without are emitted once. To balance
# the per-city axis with the per-host / per-booking axes we also accept
# `{host}` (-> R9_HOST_IDS) and `{bref}` (-> R9_BOOKING_REFS) tokens.
R9_TASK_TEMPLATES = [
    # 1. loyalty-tier-upgrade-flow (/loyalty/upgrade)
    ("Visit /loyalty/upgrade; report how many bookings the page says are required to move from Genius level 1 to level 2.",
     'loyalty-tier-upgrade-flow'),
    ("On /loyalty/upgrade, report the calendar-year stay-night threshold required to reach Genius level 3.",
     'loyalty-tier-upgrade-flow'),
    ("Open /loyalty/upgrade and click the 'See full benefits' link; report the URL it points to.",
     'loyalty-tier-upgrade-flow'),
    ("Visit /loyalty/upgrade?from=2&to=3; report the headline discount percentage advertised for level 3.",
     'loyalty-tier-upgrade-flow'),
    ("On /loyalty/upgrade, report which payment-related benefit is exclusive to Genius level 3 (a feature not on level 2).",
     'loyalty-tier-upgrade-flow'),
    ("Open /loyalty/upgrade; report the number of completed bookings the page claims the median Genius level 2 member needs to reach level 3.",
     'loyalty-tier-upgrade-flow'),
    ("On /loyalty/upgrade, report the calendar window the page uses for counting qualifying bookings (e.g. rolling 12 months vs calendar year).",
     'loyalty-tier-upgrade-flow'),
    ("From the {city} city page, navigate to /loyalty/upgrade; report whether the page shows a personalised next-tier banner referencing {city}.",
     'loyalty-tier-upgrade-flow'),
    ("Visit /loyalty/upgrade after booking a stay in {city}; report the number of qualifying nights remaining before level 2 is unlocked.",
     'loyalty-tier-upgrade-flow'),
    # 2. business-traveler-expense-report (/business/expense-report/<ref>)
    ("Open /business/expense-report/{bref}; report the total amount line on the expense report.",
     'business-traveler-expense-report'),
    ("Visit /business/expense-report/{bref}; report which file format buttons are exposed for download (count them).",
     'business-traveler-expense-report'),
    ("On /business/expense-report/{bref}, report the VAT or tax-line label the page lists as a separate row.",
     'business-traveler-expense-report'),
    ("From /business/expense-report/{bref}, report the property name used in the line-item description.",
     'business-traveler-expense-report'),
    ("Open /business/expense-report/{bref}?format=csv; report the column header used for the per-night rate.",
     'business-traveler-expense-report'),
    ("Visit /business/expense-report/{bref}; report the cost-center field default and how to override it via query string.",
     'business-traveler-expense-report'),
    ("On /business/expense-report/{bref}?format=json, report the JSON key used for the gross subtotal field.",
     'business-traveler-expense-report'),
    # 3. weekend-getaway-recommendation (/weekend-getaway)
    ("Open /weekend-getaway; report how many recommended destinations are shown on the default landing.",
     'weekend-getaway-recommendation'),
    ("On /weekend-getaway?origin={city}, report the top recommended destination shown.",
     'weekend-getaway-recommendation'),
    ("Visit /weekend-getaway?origin={city}&max_drive_hours=3; report whether the top recommendation is within a 3-hour drive radius.",
     'weekend-getaway-recommendation'),
    ("On /weekend-getaway, report the default 'budget per traveller' value the form pre-fills.",
     'weekend-getaway-recommendation'),
    ("Open /weekend-getaway?origin={city}&theme=beach; report which destination type the second slot recommends.",
     'weekend-getaway-recommendation'),
    ("Visit /weekend-getaway; report which two days of the week the weekend window defaults to.",
     'weekend-getaway-recommendation'),
    # 4. repeat-guest-discount (/repeat-guest)
    ("Open /repeat-guest; report the percentage discount the page advertises for guests returning to the same property.",
     'repeat-guest-discount'),
    ("On /repeat-guest, report the minimum number of nights from the previous stay required to unlock the repeat-guest discount.",
     'repeat-guest-discount'),
    ("Visit /repeat-guest?property=demo-paris-hotel-001; report whether the page surfaces a personalised discount banner for the demo property.",
     'repeat-guest-discount'),
    ("On /repeat-guest, report the time window (in months) within which a repeat booking still qualifies for the discount.",
     'repeat-guest-discount'),
    ("Open /repeat-guest; click the 'My eligible properties' link and report the URL it routes to.",
     'repeat-guest-discount'),
    ("On /repeat-guest, report whether the discount stacks with Genius rewards (yes / no) per the FAQ.",
     'repeat-guest-discount'),
    # 5. booking-plus-tier (/booking-plus)
    ("Open /booking-plus; report the monthly subscription price and currency listed for the Booking Plus tier.",
     'booking-plus-tier'),
    ("On /booking-plus, report how many concierge requests per month the Booking Plus tier includes.",
     'booking-plus-tier'),
    ("Visit /booking-plus; report the cancellation window (in hours) Plus members get for last-minute changes.",
     'booking-plus-tier'),
    ("On /booking-plus, report which two extra perks separate Plus from the free Genius level 3 tier.",
     'booking-plus-tier'),
    ("Open /booking-plus/checkout; report the trial duration (in days) advertised on the subscription confirm step.",
     'booking-plus-tier'),
    ("Visit /booking-plus; report the count of Plus-tier properties available across the Booking catalogue (per the headline metric).",
     'booking-plus-tier'),
    ("On /booking-plus, report whether airport-taxi credit is included in the monthly tier and the credit amount.",
     'booking-plus-tier'),
    # 6. host-quality-score-explain (/host/<id>/quality-score)
    ("Open /host/{host}/quality-score; report the host's overall quality score (out of 10).",
     'host-quality-score-explain'),
    ("On /host/{host}/quality-score, report the sub-score for 'Communication speed' shown in the breakdown.",
     'host-quality-score-explain'),
    ("Visit /host/{host}/quality-score; report how many of the six sub-categories the page evaluates a host on.",
     'host-quality-score-explain'),
    ("On /host/{host}/quality-score, report the explanation paragraph for the 'Listing accuracy' score.",
     'host-quality-score-explain'),
    ("Open /host/{host}/quality-score?format=json; report the JSON key used for the rolling 90-day cancellation rate.",
     'host-quality-score-explain'),
    ("On /host/{host}/quality-score, report the threshold (score) below which a host is flagged for review.",
     'host-quality-score-explain'),
    ("Visit /host/{host}/quality-score; report the date format used for the 'last evaluated' timestamp.",
     'host-quality-score-explain'),
    # 7. multi-step compounds (chain R9 + R8 surfaces)
    ("Open /loyalty/upgrade, click through to the Genius benefits table, then visit /booking-plus; report which two perks appear in both tiers' benefit lists.",
     'multi-step-loyalty-plus'),
    ("Visit /weekend-getaway?origin={city}, click the top recommendation card, then add the cheapest room to your bag; report the bag total currency.",
     'multi-step-getaway-bag'),
    ("Open /repeat-guest, follow the 'My eligible properties' link, then open the first property; report whether a 'Repeat guest discount' badge is shown on the property card.",
     'multi-step-repeat-prop'),
    ("Open /business/expense-report/{bref}, click 'Download CSV', then verify the CSV's first data row property name matches the page's line-item header.",
     'multi-step-expense-csv'),
    ("From /host/{host}/quality-score, navigate to the host's listed properties, then sort by rating ascending; report the lowest-rated property's name.",
     'multi-step-host-properties'),
    ("Open /booking-plus, scroll to the 'Plus catalogue' headline metric, then visit /search?plus=1 in {city}; report whether the result count matches.",
     'multi-step-plus-catalogue'),
    ("Press Cmd+K, type 'plus', hit Enter on the Booking Plus result, then click the 'Compare with Genius' link; report the URL you land on.",
     'multi-step-palette-plus'),
    ("On /loyalty/upgrade, press '/' to focus the search bar, then type '{city}'; report whether the search remains scoped to the loyalty context or jumps back to property search.",
     'multi-step-loyalty-kbd'),
]


def gen_tasks(cities, start_id, target_total=500):
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
    # Per-axis variation lists. Deterministic (no random module).
    host_ids = [1001, 1002, 1003, 1004, 1005, 1006, 1007, 1008, 1009, 1010,
                1011, 1012, 1013, 1014, 1015]
    booking_refs = [
        'BK20260512X', 'BK20260518A', 'BK20260524N', 'BK20260601D',
        'BK20260608K', 'BK20260615T', 'BK20260622R', 'BK20260629M',
        'BK20260706L', 'BK20260713Z',
    ]
    out = []
    seen = set()
    idx = start_id

    def _push(question):
        nonlocal idx
        if question in seen:
            return False
        seen.add(question)
        out.append({
            'web_name': 'Booking',
            'id': f'Booking--{idx}',
            'ques': question,
            'web': 'http://localhost:40005/',
            'upstream_url': 'https://www.booking.com/',
        })
        idx += 1
        return True

    for tmpl, kind in R9_TASK_TEMPLATES:
        if len(out) >= target_total:
            break
        has_city = '{city}' in tmpl or '{cslug}' in tmpl
        has_host = '{host}' in tmpl
        has_bref = '{bref}' in tmpl

        # No-placeholder template -> emit once.
        if not (has_city or has_host or has_bref):
            _push(tmpl)
            continue

        # Build the iteration axis. Use the most-specific axis present.
        if has_city:
            for ck in TASK_CITIES_BIG:
                if len(out) >= target_total:
                    break
                if ck not in cities:
                    continue
                disp = cities[ck]['display']
                cslug = city_to_slug.get(ck, ck)
                ques = tmpl.format(city=disp, ck=ck, cslug=cslug,
                                   host=host_ids[_hkey('r9-h', ck, tmpl) % len(host_ids)],
                                   bref=booking_refs[_hkey('r9-b', ck, tmpl) % len(booking_refs)])
                _push(ques)
        elif has_host:
            for hid in host_ids:
                if len(out) >= target_total:
                    break
                ques = tmpl.format(host=hid,
                                   bref=booking_refs[_hkey('r9-bh', hid, tmpl) % len(booking_refs)])
                _push(ques)
        elif has_bref:
            for bref in booking_refs:
                if len(out) >= target_total:
                    break
                ques = tmpl.format(bref=bref,
                                   host=host_ids[_hkey('r9-hb', bref, tmpl) % len(host_ids)])
                _push(ques)
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

    hotels = gen_hotels(cities, target_total=7200)
    print(f"  hotels generated: {len(hotels)}")
    with open(SCRAPED / 'expansion_hotels_r9.json', 'w') as f:
        json.dump(hotels, f, indent=1, ensure_ascii=False, sort_keys=True)

    start_id = _next_task_id()
    print(f"  task start id: Booking--{start_id}")
    tasks = gen_tasks(cities, start_id=start_id, target_total=500)
    print(f"  tasks generated: {len(tasks)}")
    with open(SCRAPED / 'expansion_tasks_r9.jsonl', 'w') as f:
        for t in tasks:
            f.write(json.dumps(t, ensure_ascii=False) + '\n')


if __name__ == '__main__':
    main()
