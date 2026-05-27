#!/usr/bin/env python3
"""R10 expansion generator (booking mirror, FINAL polish iter 10/10).

Run once on the build host:

    PYTHONHASHSEED=0 python3 sites/booking/scripts/gen_r10_expansion.py

Outputs (deterministic, hash-derived; rerunning produces the same bytes):
- scraped_data/expansion_hotels_r10.json   (~5000 procedural Signature listings)
- scraped_data/expansion_tasks_r10.jsonl   (~700 cross-business-line tasks)

R10 focus:
- Push property count from ~35389 -> ~40000+ by adding ~5000 "Signature" /
  "Curator's Choice" / "Atelier" tier procedural listings.  Tier label and
  brand pool are chosen so two fresh rebuilds of instance/booking.db produce
  the same md5 (no random / time / id leak) and so the names do not collide
  with R4..R9 outputs.
- Add ~700 cross-business-line compound tasks spanning 7 surfaces:
    stay+flight, stay+car, stay+attraction, stay+taxi,
    business+loyalty, flight+attraction, car+taxi
  Each task references existing R0..R9 routes only — no new app surfaces are
  added in R10, so the byte-id contract is preserved end-to-end.

Determinism contract (PYTHONHASHSEED=0): every value below derives from
sha256 of a stable key. No `random`, no `time.time()`, no dict iteration
order leak.
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


# R10 listing taxonomy — Signature / Curator's Choice / Atelier prefix.
# Distinct from R9 ("Plus / Boutique / Curated") + R4..R8 procedural prefixes.
R10_BRANDS = [
    'Alba', 'Briar', 'Cypress', 'Dune', 'Echo', 'Fern',
    'Glade', 'Halcyon', 'Iris', 'Jasmine', 'Kelp', 'Linden',
    'Marsh', 'Noor', 'Olive', 'Pine', 'Quill', 'Reed',
    'Stone', 'Tessera', 'Umber', 'Vellum', 'Willow', 'Yew', 'Zinnia',
]
R10_STYLES = [
    'Conservatory', 'Cabinet', 'Atrium', 'Library', 'Studio',
    'Garden-wing', 'Loft-wing', 'Rooftop', 'Riverwalk', 'Hillside',
    'Pavilion', 'Annex', 'Wing', 'Reserve', 'Estate',
    'Townhouse', 'Lodge', 'House', 'Court', 'Quarter',
    'Manor', 'Hall', 'Refuge',
]
R10_TIERS = [
    'Signature', 'Signature', 'Signature', 'Signature',
    'Curator’s Choice', 'Curator’s Choice', 'Curator’s Choice',
    'Atelier', 'Atelier',
]
R10_NEIGHBORHOODS = [
    'Linden Court', 'Conservatory Row', 'Painters Lane', 'Editor’s Mile',
    'Heritage Sq', 'Cathedral Walk', 'Print Quarter', 'Foundry Lane',
    'Pavilion Walk', 'Riverwalk East', 'Riverwalk West', 'Garden Annex',
    'Botanical Reserve', 'Civic Lane', 'Civic Lane West', 'Botanical Square',
    'Promenade East', 'Promenade West', 'Theatre Mews', 'Studio Row',
    'Atelier Square', 'Press Yard', 'Lantern Row', 'Concourse North',
    'Concourse South', 'Curators Walk', 'Vellum Lane', 'Embassy Lane',
]
# Signature-tier skews 4/5 star.
R10_STAR_POOL = [3, 4, 4, 4, 5, 5, 5, 5, 5]


def gen_hotels(cities, target_total=5200):
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
            brand = R10_BRANDS[_hkey('r10-br', city_key, i) % len(R10_BRANDS)]
            style = R10_STYLES[_hkey('r10-st', city_key, i) % len(R10_STYLES)]
            tier = R10_TIERS[_hkey('r10-ti', city_key, i) % len(R10_TIERS)]
            nbh = R10_NEIGHBORHOODS[_hkey('r10-nb', city_key, i) % len(R10_NEIGHBORHOODS)]
            stars = R10_STAR_POOL[_hkey('r10-rs', city_key, i, brand) % len(R10_STAR_POOL)]
            listing_id = 60000 + (_hkey('r10-lid', city_key, i) % 39999)
            shape = _hkey('r10-shape', city_key, i) % 4
            if shape == 0:
                name = f"{tier} #{listing_id}: {brand} {style} in {nbh}, {cdisp}"
            elif shape == 1:
                name = f"{brand} {tier} {style} House — {nbh}, {cdisp}"
            elif shape == 2:
                name = f"{tier} {brand}: {style} {nbh} Residences, {cdisp}"
            else:
                name = f"{brand} {style} — {tier} Edition, {nbh}, {cdisp}"
            key = (name.lower(), city_key)
            if key in seen:
                name = f"{name} (#{i + 1})"
                key = (name.lower(), city_key)
            seen.add(key)
            # Signature-tier listings — Hotel / Apart-hotel only.
            ptype = 'Apart-hotel' if (i % 5 == 0) else 'Hotel'
            out.append({
                'name': name,
                'type': ptype,
                'neighborhood': nbh,
                'city_key': city_key,
                'stars': stars,
                'is_signature_tier': True,
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


# R10 task templates — cross-business-line compounds across the 7 routes
# already exposed by R0..R9. Each template is emitted once per
# TASK_CITIES_BIG entry (no new app surfaces are introduced).
R10_TASK_TEMPLATES = [
    # 1. stay + flight
    ("Find a 4-star property in {city}, then on /flights search for flights to {city}; report whether any nonstop economy flight exists under $600.",
     'cross-stay-flight'),
    ("On /search?dest={city}&stars=5 pick the cheapest hotel, then open /flights?to={city}&cabin=Economy and report the cheapest flight price displayed.",
     'cross-stay-flight'),
    ("From the {city} city page, click 'Add a flight'; report the URL it routes to and whether the destination is preset to {city}.",
     'cross-stay-flight'),
    ("Open /search?dest={city}, click the top property, then visit /flights?to={city}&nonstop=1; report the nonstop result count.",
     'cross-stay-flight'),
    # 2. stay + car
    ("On /search?dest={city} pick the top property, then visit /car-rentals?city={city}; report the cheapest daily rate shown.",
     'cross-stay-car'),
    ("From the {city} city page, navigate to /car-rentals?city={city}&class=SUV; report how many SUV options are listed.",
     'cross-stay-car'),
    ("Open /property/<slug-of-top-{city}-hotel>, then /car-rentals?city={city}&transmission=Automatic; report the lowest automatic-transmission rate.",
     'cross-stay-car'),
    # 3. stay + attraction
    ("From /search?dest={city} pick a 5-star hotel, then visit /attractions?city={city}&sort=rating; report the top-rated attraction's name and rating.",
     'cross-stay-attraction'),
    ("Open the {city} city page, then /attractions?city={city}&category=Tours; report how many tours are listed in {city}.",
     'cross-stay-attraction'),
    ("Visit /attractions?city={city}&max_price=50, then click the first attraction; report whether it offers instant confirmation.",
     'cross-stay-attraction'),
    # 4. stay + taxi
    ("On /search?dest={city} pick the top hotel, then on /airport-taxis filter by an airport serving {city}; report the cheapest standard-vehicle quote.",
     'cross-stay-taxi'),
    ("From /city/{city}, navigate to /airport-taxis?vehicle=Sedan; report how many sedan quotes are shown overall.",
     'cross-stay-taxi'),
    ("Visit /airport-taxis?vehicle=Minivan&max_price=200; report whether any minivan quote serves {city}.",
     'cross-stay-taxi'),
    # 5. business + loyalty (cross expense report + Genius)
    ("Open /business/expense-report/BK20260518A, then visit /loyalty/upgrade; report whether the expense total can be applied to Genius night counts (per the FAQ).",
     'cross-business-loyalty'),
    ("From /loyalty/upgrade, navigate to /business/expense-report/BK20260601D and report whether the report exposes a 'Genius tier' field.",
     'cross-business-loyalty'),
    ("Visit /business/expense-report/BK20260524N?format=json; report the JSON key (if any) that links the booking to a loyalty tier.",
     'cross-business-loyalty'),
    # 6. flight + attraction
    ("On /flights?to={city} pick the cheapest flight, then on /attractions?city={city} pick the top attraction; report whether the attraction's free_cancellation matches the flight's free_cancellation.",
     'cross-flight-attraction'),
    ("Visit /flights?to={city}&cabin=Business and /attractions?city={city}&category=Tours; report whether business-cabin price is higher than the priciest tour price.",
     'cross-flight-attraction'),
    # 7. car + taxi
    ("Open /car-rentals?city={city} (cheapest first) then /airport-taxis (filter by an airport that serves {city}); report which option is cheaper per day vs per ride.",
     'cross-car-taxi'),
    ("On /car-rentals?city={city}&class=Compact, then /airport-taxis?vehicle=Standard; report whether the daily compact rate is cheaper than the standard taxi quote.",
     'cross-car-taxi'),
    # 8. final-polish single-axis checks (no-{city} templates run once)
    ("Visit /sitemap.xml; report whether it includes <sitemap> entries for sitemap-properties.xml, sitemap-cities.xml and sitemap-attractions.xml.",
     'final-polish-sitemap'),
    ("Open /sitemap-properties.xml; report the count of <url> entries (the property catalogue size as advertised to crawlers).",
     'final-polish-sitemap'),
    ("Open /amenity-glossary; report how many amenity rows appear in the table.",
     'final-polish-amenities'),
    ("Open /api/amenity-glossary; report the JSON top-level key holding the amenity list.",
     'final-polish-amenities'),
    ("Visit /booking-plus then /api/booking-plus; report whether the JSON 'monthly_price' matches the page price.",
     'final-polish-plus-api'),
    ("Open /healthz; report the HTTP status and the JSON 'status' field value.",
     'final-polish-health'),
    ("Visit /robots.txt; report whether /api/ and /partner/ are listed as Disallow entries.",
     'final-polish-robots'),
    ("Open /metrics; report the metric line that reports the total property count.",
     'final-polish-metrics'),
    # 9. form validation (login / register / payment)
    ("Open /register and submit the form with an empty email field; report the validation error message displayed.",
     'form-validation-register'),
    ("Open /register and submit with mismatched password / confirm; report the error wording.",
     'form-validation-register'),
    ("Open /login and submit with a non-existent email; report the error wording.",
     'form-validation-login'),
    ("From /account/payments/add, submit a card with an obviously invalid expiry month (13); report the validation error.",
     'form-validation-payment'),
    ("From /property/<any-slug>/review, submit a review with no rating selected; report the validation error.",
     'form-validation-review'),
    # 10. city pages must all return 200 — randomized city probes
    ("Visit /city/{cslug}; report the H1 text on the page.",
     'city-page-200'),
    ("Visit /city/{cslug}/things-to-do; report whether the page lists at least 5 attractions for {city}.",
     'city-page-200'),
    # 11. Signature-tier (R10) discoverability — verify expansion is reachable.
    ("On /search?dest={city}&q=Signature, report how many Signature-tier listings surface in the result count.",
     'r10-signature-discover'),
    ("On /search?dest={city}&q=Curator, report whether at least one Curator’s Choice property is listed.",
     'r10-signature-discover'),
    ("On /search?dest={city}&q=Atelier, report whether the top result mentions 'Atelier' in its name.",
     'r10-signature-discover'),
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

    for tmpl, kind in R10_TASK_TEMPLATES:
        if len(out) >= target_total:
            break
        has_city = '{city}' in tmpl or '{cslug}' in tmpl
        if not has_city:
            _push(tmpl)
            continue
        for ck in TASK_CITIES_BIG:
            if len(out) >= target_total:
                break
            if ck not in cities:
                continue
            disp = cities[ck]['display']
            cslug = city_to_slug.get(ck, ck)
            ques = tmpl.format(city=disp, ck=ck, cslug=cslug)
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

    hotels = gen_hotels(cities, target_total=5200)
    print(f"  hotels generated: {len(hotels)}")
    with open(SCRAPED / 'expansion_hotels_r10.json', 'w') as f:
        json.dump(hotels, f, indent=1, ensure_ascii=False, sort_keys=True)

    start_id = _next_task_id()
    print(f"  task start id: Booking--{start_id}")
    tasks = gen_tasks(cities, start_id=start_id, target_total=700)
    print(f"  tasks generated: {len(tasks)}")
    with open(SCRAPED / 'expansion_tasks_r10.jsonl', 'w') as f:
        for t in tasks:
            f.write(json.dumps(t, ensure_ascii=False) + '\n')


if __name__ == '__main__':
    main()
