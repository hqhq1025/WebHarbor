#!/usr/bin/env python3
"""Booking R3-R10 deepen-polish task generator.

Run once on the build host:

    PYTHONHASHSEED=0 python3 sites/booking/scripts/gen_polish_deepen.py

Generates ~1700 tasks across 8 themed buckets and appends them to
sites/booking/tasks.jsonl. Each bucket targets one of the new R3-R10
"deepen" surfaces (multi-room / extended-stay / business / addon /
subtype / insurance / genius-points / api) and produces 200+ tasks.

Determinism contract (PYTHONHASHSEED=0): every parameter (adults,
children ages, nights, city order, room count) is derived from
sha256(bucket, idx) so reruns produce byte-identical tasks.jsonl.
"""
import hashlib
import json
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
TASKS_PATH = BASE / 'tasks.jsonl'


def _hkey(*parts):
    h = hashlib.sha256('|'.join(str(p) for p in parts).encode('utf-8')).digest()
    return int.from_bytes(h[:4], 'big')


# Stable city pool — same shape used by gen_r4..r10 so task vocab stays
# consistent across rounds. Slug column matches Booking.City.slug.
CITIES = [
    ('paris', 'Paris', 'fr'), ('london', 'London', 'gb'),
    ('new-york', 'New York', 'us'), ('tokyo', 'Tokyo', 'jp'),
    ('rome', 'Rome', 'it'), ('barcelona', 'Barcelona', 'es'),
    ('dubai', 'Dubai', 'ae'), ('singapore', 'Singapore', 'sg'),
    ('bali', 'Bali', 'id'), ('sydney', 'Sydney', 'au'),
    ('amsterdam', 'Amsterdam', 'nl'), ('bangkok', 'Bangkok', 'th'),
    ('maldives', 'Maldives', 'mv'), ('istanbul', 'Istanbul', 'tr'),
    ('los-angeles', 'Los Angeles', 'us'), ('berlin', 'Berlin', 'de'),
    ('prague', 'Prague', 'cz'), ('vienna', 'Vienna', 'at'),
    ('venice', 'Venice', 'it'), ('santorini', 'Santorini', 'gr'),
    ('mexico-city', 'Mexico City', 'mx'), ('rio-de-janeiro', 'Rio de Janeiro', 'br'),
    ('jakarta', 'Jakarta', 'id'), ('lisbon', 'Lisbon', 'pt'),
    ('melbourne', 'Melbourne', 'au'), ('toronto', 'Toronto', 'ca'),
    ('chicago', 'Chicago', 'us'), ('hong-kong', 'Hong Kong', 'hk'),
]


def _next_task_id():
    if not TASKS_PATH.exists():
        return 0
    mx = -1
    with open(TASKS_PATH) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
                ident = row.get('id', '')
                if '--' in ident:
                    n_str = ident.split('--')[1]
                    if n_str.isdigit():
                        mx = max(mx, int(n_str))
            except Exception:
                continue
    return mx + 1


# ---------------------------------------------------------------------
# R3 DEEPEN — multi-room / family pricing (target 220 tasks)
# ---------------------------------------------------------------------
def gen_r3_tasks():
    out = []
    seed_base = 'r3'
    # (adults, children-csv, rooms, nights) tuples — varied combos.
    combos = []
    for i in range(220):
        h = _hkey(seed_base, 'combo', i)
        adults = 2 + (h % 4)             # 2..5
        rooms = 1 + ((h >> 4) % 3)       # 1..3
        nights = 2 + ((h >> 8) % 6)      # 2..7
        n_children = ((h >> 12) % 4)     # 0..3
        ages = []
        for ci in range(n_children):
            h2 = _hkey(seed_base, 'age', i, ci)
            ages.append(h2 % 18)         # 0..17
        combos.append((adults, ages, rooms, nights))

    templates = [
        "On /family-rooms, compute the stay total for {adults} adults"
        " {children_clause} across {rooms} room(s) for {nights} nights"
        " and report the nightly subtotal.",
        "On /family-rooms?adults={adults}&rooms={rooms}&children={children_csv}"
        "&nights={nights}, report whether each child is priced free, 25%,"
        " 50% or 75% of the adult rate.",
        "On /api/family-rooms/quote?adults={adults}&rooms={rooms}"
        "&children={children_csv}&nights={nights}&format=json, parse"
        " 'nightly_total' from the JSON response and report it.",
        "Open /family-rooms with adults={adults}, rooms={rooms},"
        " children ages '{children_csv}', and nights={nights}; report the"
        " number of room-type rows in the breakdown.",
        "On /family-rooms?adults={adults}&rooms={rooms}&children={children_csv}"
        "&nights={nights}, identify whether the extra-bed surcharge"
        " applies (it triggers when any child age is 6-11).",
    ]

    for i, (adults, ages, rooms, nights) in enumerate(combos):
        tmpl = templates[i % len(templates)]
        children_csv = ','.join(str(a) for a in ages) or ''
        if ages:
            kids_part = ', '.join(f'age {a}' for a in ages)
            children_clause = f"and {len(ages)} child(ren) ({kids_part})"
        else:
            children_clause = 'with no children'
        q = tmpl.format(adults=adults, children_clause=children_clause,
                        children_csv=children_csv, rooms=rooms, nights=nights)
        out.append(q)
    return out


# ---------------------------------------------------------------------
# R4 DEEPEN — extended-stay monthly billing (target 220 tasks)
# ---------------------------------------------------------------------
def gen_r4_tasks():
    out = []
    tiers = [(28, 10), (60, 18), (90, 25), (180, 32)]
    templates = [
        "On /extended-stay?dest={cslug}&nights={nights}, report which"
        " monthly tier is active and its discount percentage.",
        "Open /extended-stay?dest={cslug}&nights={nights}; report the"
        " discounted nightly rate and the stay total.",
        "On /api/extended-stay/quote?dest={cslug}&nights={nights}"
        "&format=json, parse 'monthly_bill' and report it.",
        "On /long-stay?dest={cslug}&nights={nights}, verify that nights"
        " under 28 are rejected — report yes/no.",
        "Open /monthly-rentals?dest={cslug}&nights={nights} and list"
        " the available extended-stay apartments.",
        "On /extended-stay?dest={cslug}&nights={nights}, identify the"
        " months count used for monthly billing equivalent.",
    ]
    idx = 0
    for n_nights in [28, 31, 35, 42, 60, 75, 90, 120, 150, 180, 210, 240, 300, 365]:
        for cslug, city, _cc in CITIES:
            if len(out) >= 220:
                break
            tmpl = templates[idx % len(templates)]
            q = tmpl.format(cslug=cslug, city=city, nights=n_nights)
            out.append(q)
            idx += 1
        if len(out) >= 220:
            break
    return out


# ---------------------------------------------------------------------
# R5 DEEPEN — business account / corporate invoicing (target 220 tasks)
# ---------------------------------------------------------------------
def gen_r5_tasks():
    out = []
    invoices = ['INV-2026-02', 'INV-2026-03', 'INV-2026-04', 'INV-2026-05']
    pay_methods = ['Acme Corporate Visa', 'Acme AmEx Travel', 'Acme Wire Account']
    formats = ['json', 'pdf', 'csv']

    base_templates = [
        "On /business/account, report the company name on the business account.",
        "On /business/account, report the cost centre on the business account.",
        "On /business/account, report the monthly spend cap in USD.",
        "On /business/account, report how many shared payment methods are listed.",
        "On /business/account, report the VAT ID shown.",
        "On /business/account, list the invoice numbers visible.",
        "On /business/account, report the billing email shown on the page.",
        "On /business/account, report the account ID shown.",
        "On /business/account, report the active travellers count.",
        "On /business/account?format=json, parse 'account.id' and report it.",
        "On /business/account?format=csv, verify the response type is JSON stub.",
        "On /business/account?format=pdf, verify the response type is JSON stub.",
    ]
    for t in base_templates:
        out.append(t)

    for inv in invoices:
        out.append(f"Open /business/account/invoice/{inv} and report the amount in USD.")
        out.append(f"On /business/account/invoice/{inv}, report the status of the invoice.")
        out.append(f"On /business/account/invoice/{inv}, report the period covered.")
        out.append(f"On /business/account/invoice/{inv}, report the company name on the invoice.")
        out.append(f"On /business/account/invoice/{inv}, report the VAT ID on the invoice.")
        out.append(f"On /business/account/invoice/{inv}, report the cost centre on the invoice.")

    for pm in pay_methods:
        out.append(f"On /business/account, find the pooled budget USD for '{pm}'.")
        out.append(f"On /business/account, find the last-4 digits for '{pm}'.")
        out.append(f"On /business/account, find the card type for '{pm}'.")

    for fmt in formats:
        out.append(f"On /business?format={fmt}, parse the response and report the format field.")
        out.append(f"On /business/account?format={fmt}, report the company name.")

    # Compound tasks — combine business with cancellation / insurance / addon.
    compound_templates = [
        "Open /business/account then /cancellation-policies and report"
        " how many policy rows exist on the comparison page.",
        "Open /business/account then /travel-insurance?trip_cost=1500&"
        "travellers=3&days=7 and report the Standard plan premium.",
        "Open /business/account then /addons and list 3 add-on titles"
        " visible on the cross-sell hub.",
        "Open /business/account then /genius/points-calculator?"
        "stay_total=2000&current_level=2 and report points earned.",
        "Open /business/account then /extended-stay?dest=paris&nights=60"
        " and report the active tier label.",
        "Open /business/account?format=json then /business/account/invoice/"
        "INV-2026-05?format=json and report the status field of the invoice.",
        "Open /business/account then /price-match and report the SLA hours.",
        "Open /business/account then /family-rooms?adults=4&rooms=2&"
        "children=4,9&nights=3 and report the stay total.",
        "Open /business/account then /api/v1/properties/search?"
        "city=paris&limit=5 and report the JSON count.",
        "Open /business/account then /loyalty/upgrade and report"
        " what Genius Level 2 unlocks.",
    ]
    for t in compound_templates:
        out.append(t)

    # Per-city business expansion: business search in N cities.
    for cslug, city, _cc in CITIES:
        out.append(
            f"On /business/account, verify travellers count is at least 1,"
            f" then open /search?dest={city} and report whether any business-"
            f"category property appears in the first 5 results."
        )
        out.append(
            f"Open /business/account then /property-subtype/aparthotel?"
            f"city={cslug} and report how many aparthotels match in {city}."
        )
        out.append(
            f"Open /business/account then /extended-stay?dest={cslug}&"
            f"nights=30 and report the discounted nightly rate."
        )
        out.append(
            f"Open /business/account then /travel-insurance?"
            f"trip_cost=2000&travellers=2&days=5 and report the Premium plan premium."
        )
        out.append(
            f"Open /business/account then /api/v1/properties/search?"
            f"city={cslug}&limit=3 and report the JSON count for {city}."
        )

    # Different invoice formats, deterministic claim variations.
    for inv in invoices:
        for fmt in formats:
            out.append(
                f"On /business/account/invoice/{inv}?format={fmt}, parse the"
                f" JSON and report the invoice number."
            )

    # Extra deterministic compound tasks: business + R6/R7/R8 cross-links per city.
    for cslug, city, _cc in CITIES:
        out.append(
            f"Open /business/account then /addons/restaurants?city={city}&"
            f"cuisine=Italian and count Italian restaurants returned."
        )
        out.append(
            f"Open /business/account then /property-subtype/resort?city={cslug}"
            f" and report whether any resort property is listed for {city}."
        )
        if len(out) >= 240:
            break
    return out[:240]


# ---------------------------------------------------------------------
# R6 DEEPEN — addon cross-sell hub (target 220 tasks)
# ---------------------------------------------------------------------
def gen_r6_tasks():
    out = []
    cuisines = ['French', 'Italian', 'Japanese', 'Thai', 'Indian',
                'Mexican', 'Spanish', 'Chinese', 'American',
                'Mediterranean', 'Vegetarian', 'Seafood']
    addon_titles = ['Airport transfer', 'Car rental', 'Attractions & tickets',
                    'Restaurant reservation', 'Travel insurance',
                    'Stadium / event tickets']

    out.append("On /addons, list every add-on category title visible on the hub.")
    out.append("On /extras, verify the page renders identical content to /addons.")
    out.append("On /addons?format=json, parse 'bundle_rules' and report the"
               " discount when 3 add-ons are selected.")
    out.append("On /addons?format=json, parse 'bundle_rules' and report the"
               " discount when 2 add-ons are selected.")
    out.append("On /addons?format=json, parse the count of add-ons returned.")
    for title in addon_titles:
        out.append(f"On /addons, find the 'from price' shown for '{title}'.")
        out.append(f"On /addons, click '{title}' and verify the destination URL"
                   f" matches the documented detail_url.")
        out.append(f"On /addons, report the category for the add-on '{title}'.")
        out.append(f"On /addons, report the description text for '{title}'.")

    for cslug, city, _cc in CITIES:
        out.append(f"On /addons/restaurants?city={city}, list up to 6"
                   f" restaurant names returned.")
        for cu in cuisines[:4]:
            out.append(f"On /addons/restaurants?city={city}&cuisine={cu},"
                       f" report how many restaurants match the cuisine filter.")
        if len(out) >= 220:
            break

    # Reservation flow tasks.
    for i in range(24):
        out.append(f"On /addons/restaurants?city=Paris&reserve=R10{i:02d},"
                   f" parse the JSON and report the reservation_id prefix.")
        out.append(f"On /addons/restaurants?city=Tokyo&reserve=T20{i:02d},"
                   f" parse the JSON and report the reservation_id value.")

    # Bundle compound tasks.
    out += [
        "Open /addons then /airport-taxis and verify the airport-transfer add-on"
        " on /addons links to the airport-taxis page.",
        "Open /addons then /car-rentals and verify the car-rental add-on links match.",
        "Open /addons then /attractions and verify the attractions add-on links match.",
        "Open /addons then /travel-insurance and verify the travel-insurance link.",
        "Open /addons then /addons/restaurants and verify the restaurant link.",
        "Open /addons then /price-match and verify the price-match guarantee page loads.",
        "Open /addons then /cancellation-policies and verify the comparison renders.",
    ]
    return out[:230]


# ---------------------------------------------------------------------
# R7 DEEPEN — property subtype directories (target 220 tasks)
# ---------------------------------------------------------------------
def gen_r7_tasks():
    out = []
    subtypes = ['resort', 'vacation-rental', 'bnb', 'capsule', 'ryokan', 'aparthotel']
    for st in subtypes:
        out.append(f"On /property-subtype/{st}, list any 3 {st} properties visible.")
        out.append(f"On /property-subtype/{st}, report the page-subtitle blurb.")
        out.append(f"On /property-subtype/{st}, count how many properties are shown.")
        out.append(f"On /property-subtype/{st}?format=json, report the 'count' field.")
        out.append(f"On /property-subtype/{st}?format=json, report the 'label' field.")
        out.append(f"On /property-subtype/{st}?format=json, report the 'blurb' field.")
        out.append(f"On /property/subtype/{st}, verify it renders the same"
                   f" content as /property-subtype/{st}.")
    out.append("On /resorts, verify it 302-redirects to /property-subtype/resort.")
    out.append("On /resort, verify it 302-redirects to /property-subtype/resort.")
    out.append("On /vacation-rentals, verify it 302-redirects to"
               " /property-subtype/vacation-rental.")
    out.append("On /bnb, verify it 302-redirects to /property-subtype/bnb.")
    out.append("On /bed-and-breakfast, verify it 302-redirects to"
               " /property-subtype/bnb.")
    out.append("On /capsule-hotels, verify it 302-redirects to"
               " /property-subtype/capsule.")

    for cslug, city, _cc in CITIES:
        for st in subtypes:
            if len(out) >= 230:
                break
            out.append(
                f"On /property-subtype/{st}?city={cslug}, report how"
                f" many properties match the {st} filter in {city}."
            )
        if len(out) >= 230:
            break
    return out[:230]


# ---------------------------------------------------------------------
# R8 DEEPEN — travel insurance + cancellation comparison + price match
# (target 220 tasks)
# ---------------------------------------------------------------------
def gen_r8_tasks():
    out = []
    plans = ['Basic', 'Standard', 'Premium']

    # Insurance quote tasks.
    for i in range(120):
        h = _hkey('r8-ins', i)
        trip_cost = 500 + (h % 4000)
        travellers = 1 + ((h >> 8) % 5)
        days = 2 + ((h >> 12) % 14)
        plan = plans[i % len(plans)]
        out.append(
            f"On /travel-insurance?trip_cost={trip_cost}&travellers={travellers}"
            f"&days={days}, report the {plan} plan premium."
        )
    for i in range(20):
        h = _hkey('r8-ins-cmp', i)
        trip_cost = 600 + (h % 3000)
        out.append(
            f"On /travel-insurance?trip_cost={trip_cost}&travellers=2&days=7,"
            f" identify which plan offers the highest medical coverage."
        )

    # Cancellation comparison tasks.
    for p in ['Free cancellation', 'Flexible', 'Strict', 'Non-refundable',
              'Genius L2/L3 flex']:
        out.append(f"On /cancellation-policies, report the 'free until' value for '{p}'.")
        out.append(f"On /cancellation-policies, report the no-show charge for '{p}'.")
        out.append(f"On /cancellation-policies, report the partial-refund rule for '{p}'.")
    out.append("On /cancellation-policies?format=json, parse the count of policies.")
    out.append("On /policies/cancellation, verify the route renders the same"
               " comparison as /cancellation-policies.")

    # Price-match tasks.
    out.append("On /price-match, list the eligibility rules visible on the page.")
    out.append("On /price-match-guarantee, verify the route renders identical content.")
    out.append("On /price-match?format=json, parse 'sla_hours' and report the value.")
    out.append("On /price-match?format=json, parse 'refund_to' and report the value.")
    out.append("On /price-match?format=json, count the eligibility rules.")
    for i in range(80):
        h = _hkey('r8-pm', i)
        bref = f"BK-{10000000 + (h % 9000000)}"
        comp_rate = 50 + (h % 350)
        out.append(
            f"On /price-match, submit a claim for booking '{bref}' with"
            f" competitor URL 'https://example.test/{i}' and competitor"
            f" rate ${comp_rate}; report the claim id returned."
        )

    # Compound tasks combining insurance + policy + price-match.
    out += [
        "Open /travel-insurance?trip_cost=1000&travellers=2&days=5 then"
        " /cancellation-policies; report whether 'Free cancellation' appears.",
        "Open /price-match then /cancellation-policies; report whether"
        " 'Genius L2/L3 flex' is listed.",
        "Open /travel-insurance?format=json then /price-match?format=json;"
        " report the SLA hours from price-match.",
        "Open /travel-insurance then /cancellation-policies and report"
        " whether 'Strict' policy is listed.",
    ]
    return out[:230]


# ---------------------------------------------------------------------
# R9 DEEPEN — Genius points calculator (target 220 tasks)
# ---------------------------------------------------------------------
def gen_r9_tasks():
    out = []
    for i in range(220):
        h = _hkey('r9-points', i)
        stay = 200 + (h % 3000)
        level = 1 + ((h >> 6) % 3)
        b24 = ((h >> 12) % 30)
        out.append(
            f"On /genius/points-calculator?stay_total={stay}"
            f"&current_level={level}&bookings_24m={b24},"
            f" report the points_earned value."
        )

    # Tier-specific checks.
    for lv in (1, 2, 3):
        out.append(f"On /genius/points-calculator?current_level={lv}"
                   f"&stay_total=1000, report the savings for Level {lv}.")
        out.append(f"On /genius/points-calculator?current_level={lv}"
                   f"&stay_total=1000, report the final price for Level {lv}.")
        out.append(f"On /genius/points-calculator?current_level={lv}"
                   f"&stay_total=1000, identify which row is marked 'Current'.")

    # JSON parse tasks.
    out += [
        "On /loyalty/points-calculator?stay_total=500&current_level=1"
        "&format=json, parse 'point_rate_per_usd' and report it.",
        "On /loyalty/points-calculator?stay_total=500&current_level=3"
        "&format=json, parse 'points_per_stay' and report it.",
        "On /loyalty/points-calculator?stay_total=2000&current_level=2"
        "&bookings_24m=10&format=json, parse 'lifetime_points'.",
        "On /genius/points-calculator?current_level=2&bookings_24m=4"
        "&format=json, find the status_label that mentions 'more bookings needed'.",
    ]

    # Cross-link compound tasks.
    out += [
        "Open /genius then /genius/points-calculator?stay_total=800"
        "&current_level=1 and report the Level 2 savings shown.",
        "Open /loyalty/upgrade then /loyalty/points-calculator?stay_total=600"
        "&current_level=1; report what Level 3 unlocks.",
        "Open /genius/points-calculator?stay_total=1500&current_level=1"
        "&bookings_24m=4 then report whether Level 2 is unlocked yet.",
    ]
    return out[:230]


# ---------------------------------------------------------------------
# R10 DEEPEN — public API surface (target 220 tasks)
# ---------------------------------------------------------------------
def gen_r10_tasks():
    out = []
    out.append("On /api/docs, list the documented endpoints visible on the page.")
    out.append("On /developers, verify it renders the developer landing page.")

    # REST search tasks.
    for cslug, city, _cc in CITIES:
        out.append(
            f"On /api/v1/properties/search?city={cslug}&limit=5, parse the"
            f" JSON 'count' and report how many properties matched in {city}."
        )
    for cslug, _city, _cc in CITIES[:14]:
        out.append(
            f"On /api/v1/properties/search?city={cslug}&limit=10&min_rating=8,"
            f" report the highest-rated property name returned."
        )
    for cslug, _city, _cc in CITIES[:14]:
        out.append(
            f"On /api/v1/properties/search?city={cslug}&limit=10&max_price=200,"
            f" report how many properties match the price filter."
        )

    # GraphQL tasks.
    for limit in (1, 3, 5, 10, 20):
        out.append(
            f"On /graphql?query={{cities(limit:{limit}){{slug+display+country}}}},"
            f" parse the 'data.cities' array and report its length."
        )
    for cslug, _city, _cc in CITIES[:10]:
        out.append(
            f"On /graphql?query={{properties(city:\"{cslug}\",limit:3){{name+price+rating}}}},"
            f" parse the 'data.properties' array and report the first name."
        )

    # ICS calendar tasks.
    out += [
        "On /calendar/bookings.ics, verify the Content-Type header is"
        " 'text/calendar; charset=utf-8'.",
        "On /calendar/bookings.ics, verify the response starts with"
        " 'BEGIN:VCALENDAR' and ends with 'END:VCALENDAR'.",
        "On /calendar/bookings.ics, count how many 'BEGIN:VEVENT' lines"
        " appear (anonymous = 0).",
    ]

    # Webhook & exchange-rates & sitemap.
    out += [
        "On /api/v1/webhooks, list every 'event' name in the registry.",
        "On /api/v1/webhooks, report which webhook is currently inactive.",
        "On /api/v1/webhooks, count how many webhooks are active.",
        "On /api/v1/exchange-rates, parse 'base' and report it.",
        "On /api/v1/exchange-rates, report how many currency codes are listed.",
        "On /sitemap-api.xml, count how many <url> entries appear.",
        "On /sitemap-api.xml, verify '/graphql' is listed.",
        "On /sitemap-api.xml, verify '/calendar/bookings.ics' is listed.",
    ]

    # Compound tasks combining API surfaces.
    for cslug, city, _cc in CITIES[:16]:
        out.append(
            f"Open /api/v1/properties/search?city={cslug}&limit=3 then"
            f" /graphql?query={{properties(city:\"{cslug}\",limit:3){{name}}}},"
            f" verify both endpoints return the same first property name."
        )

    # Pad with rate-limit / header tasks.
    rate_ext = [
        "On /api/v1/properties/search?city=paris&limit=5, report the value of"
        " the X-Request-ID response header.",
        "On /api/v1/exchange-rates, report the value of the X-Request-ID header.",
        "On /graphql?query={cities(limit:3){slug}}, report the value of the"
        " X-Request-ID header.",
        "On /api/v1/webhooks, report the value of the X-Request-ID header.",
    ]
    out += rate_ext

    # Additional per-city REST variations: rating + price + limit grid.
    for cslug, _city, _cc in CITIES:
        for min_r in (7, 8, 9):
            for lim in (3, 5, 10):
                out.append(
                    f"On /api/v1/properties/search?city={cslug}&limit={lim}"
                    f"&min_rating={min_r}, parse the JSON 'count' and report it."
                )
                if len(out) >= 250:
                    break
            if len(out) >= 250:
                break
        if len(out) >= 250:
            break

    while len(out) < 240:
        # Pad deterministically with REST search variations.
        i = len(out)
        h = _hkey('r10-pad', i)
        cslug = CITIES[h % len(CITIES)][0]
        out.append(
            f"On /api/v1/properties/search?city={cslug}&limit={2 + (h % 8)}"
            f"&min_rating={6 + (h >> 4) % 4}, parse the JSON 'count' field"
            f" and report the value."
        )
    return out[:240]


GENERATORS = [
    ('R3', gen_r3_tasks),
    ('R4', gen_r4_tasks),
    ('R5', gen_r5_tasks),
    ('R6', gen_r6_tasks),
    ('R7', gen_r7_tasks),
    ('R8', gen_r8_tasks),
    ('R9', gen_r9_tasks),
    ('R10', gen_r10_tasks),
]


def main():
    start_id = _next_task_id()
    print(f"  task start id: Booking--{start_id}")
    idx = start_id
    all_rows = []
    for label, fn in GENERATORS:
        qs = fn()
        # Dedupe within bucket.
        seen = set()
        kept = []
        for q in qs:
            if q in seen:
                continue
            seen.add(q)
            kept.append(q)
        print(f"  {label}: {len(kept)} tasks")
        for q in kept:
            all_rows.append({
                'web_name': 'Booking',
                'id': f'Booking--{idx}',
                'ques': q,
                'web': 'http://localhost:40005/',
                'upstream_url': 'https://www.booking.com/',
            })
            idx += 1

    # Append to tasks.jsonl.
    with open(TASKS_PATH, 'a') as f:
        for row in all_rows:
            f.write(json.dumps(row, ensure_ascii=False) + '\n')
    print(f"  appended {len(all_rows)} tasks -> {TASKS_PATH}")
    print(f"  final next-id: Booking--{idx}")


if __name__ == '__main__':
    main()
