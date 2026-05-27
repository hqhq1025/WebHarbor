#!/usr/bin/env python3
"""R7 expansion generator (booking mirror).

Run once on the build host:

    python3 sites/booking/scripts/gen_r7_expansion.py

Outputs (deterministic, hash-derived; rerunning produces the same bytes):
- scraped_data/expansion_hotels_r7.json
- scraped_data/expansion_tasks_r7.jsonl

R7 focus:
- Push property count from ~16795 -> ~22000+ by adding ~5400 procedural hotels
  with R7-specific prefixes that don't collide with R4/R5/R6 output.
- Add 7 new task categories: SEO-Hotel-schema-LDJSON, locale-currency,
  AMP-property-stub, accessibility-WCAG-AA-audit, multi-language-description,
  TripAdvisor-cross-link-stub, multi-step (locale->book / AMP->full).
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


# R7 hotels — distinctive name shapes so they don't collide with R4/R5/R6.
# Structure: "{Adjective} {City} {NounSuffix} by {Operator}" or 3-token boutique.
R7_ADJECTIVES = [
    'Ardent', 'Boreal', 'Coastal', 'Dappled', 'Emerald',
    'Fjord', 'Glacier', 'Harmony', 'Iris', 'Juniper',
    'Kelpie', 'Lantern', 'Mosaic', 'Nimbus', 'Obsidian',
    'Pinnacle', 'Quasar', 'Reverie', 'Solstice', 'Tundra',
    'Umber', 'Verdant', 'Wildflower', 'Xanadu', 'Yarrow',
    'Zephyr',
]
R7_NOUN_SUFFIXES = [
    'Pavilion', 'Conservatorium', 'Belvedere', 'Hideaway', 'Outpost',
    'Compound', 'Sanctuary', 'Retreat', 'Domicile', 'Aerie',
    'Lodgings', 'Quarters', 'Roost', 'Perch', 'Chateau',
    'Manor', 'Studios', 'Lofts', 'Annex', 'Wing',
]
R7_OPERATORS = [
    'Aurelius Hospitality', 'Borealis Group', 'Cumulus Stays',
    'Dovetail Hotels', 'Empyrean Collection', 'Foundry Hospitality',
    'Grove Hotels', 'Halyard Resorts', 'Ivory Suites',
    'Jubilee Hotels', 'Keystone Stays', 'Liminal Hospitality',
    'Meander Hotels', 'Northstar Lodgings', 'Origin Stays',
    'Patron Hotels', 'Quill Collection', 'Riverbend Hotels',
    'Sundial Hospitality', 'Tideline Hotels',
]
R7_NEIGHBORHOODS = [
    'Lantern Square', 'Coastal Mile', 'Old Mint Quarter', 'Cathedral Walk',
    'Botanical Strip', 'Heritage Yard', 'Studio Row', 'Designer Court',
    'Riverside Crescent', 'Market Promenade', 'Civic Quarter',
    'Innovation Walk', 'Skyline Boulevard', 'Garden Reach',
    'Theatre Annex', 'Atelier Mile', 'Plaza Annex', 'Esplanade Walk',
    'Cultural Strip', 'University Quarter',
]
R7_TYPES = ['Hotel', 'Apartment', 'Resort', 'Villa',
            'Bed and Breakfast', 'Hostel', 'Guest House', 'Cabin']


def gen_hotels(cities, target_total=5400):
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
            adj = R7_ADJECTIVES[_hkey('r7-ad', city_key, i) % len(R7_ADJECTIVES)]
            noun = R7_NOUN_SUFFIXES[_hkey('r7-nn', city_key, i) % len(R7_NOUN_SUFFIXES)]
            op = R7_OPERATORS[_hkey('r7-op', city_key, i) % len(R7_OPERATORS)]
            nbh = R7_NEIGHBORHOODS[_hkey('r7-nb', city_key, i) % len(R7_NEIGHBORHOODS)]
            stars_pool = [2, 3, 3, 3, 4, 4, 4, 4, 5, 5]
            stars = stars_pool[_hkey('r7-st', city_key, i, adj) % len(stars_pool)]
            ptype = R7_TYPES[_hkey('r7-pt', city_key, i) % len(R7_TYPES)]
            # Composition variant: half use "by {Operator}", half are
            # 3-token "Adjective City Noun" — both shapes are distinct
            # from R6's "Prefix Brand City Suffix".
            if (_hkey('r7-shape', city_key, i) % 2) == 0:
                name = f"{adj} {cdisp} {noun} by {op}"
            else:
                name = f"{adj} {cdisp} {noun}"
            key = (name.lower(), city_key)
            if key in seen:
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


TASK_CITIES_BIG = [
    'paris', 'london', 'nyc', 'tokyo', 'rome', 'barcelona', 'dubai',
    'singapore', 'bali', 'sydney', 'amsterdam', 'bangkok', 'maldives',
    'istanbul', 'losangeles', 'berlin', 'prague', 'vienna', 'venice',
    'santorini', 'mexicocity', 'rio', 'jakarta', 'chicago', 'lisbon',
    'melbourne', 'toronto', 'hongkong', 'sapporo', 'shenzhen',
    'chennai', 'varanasi', 'ohio',
]

R7_TASK_TEMPLATES = [
    # 1. SEO-Hotel-schema-LDJSON
    ("Open a {city} property detail page and view the page source; report the value of the `priceRange` field inside the `application/ld+json` Hotel schema block.",
     'seo-hotel-schema'),
    ("On a {city} hotel page, locate the JSON-LD Hotel schema in the head; report the `aggregateRating.ratingValue` it declares.",
     'seo-hotel-schema'),
    ("From the {city} property detail HTML source, extract the `address` object inside the Hotel JSON-LD block and report the postal locality.",
     'seo-hotel-schema'),
    ("On any {city} property page, count how many `amenityFeature` entries the JSON-LD Hotel block lists.",
     'seo-hotel-schema'),
    # 2. locale-EUR-USD-GBP-AUD-currency
    ("On the {city} search results page, switch the currency selector to EUR and report the converted price displayed on the first card.",
     'locale-currency-eur'),
    ("Open /search?city={ck}&currency=GBP for {city}; report the GBP price shown on the top-ranked property.",
     'locale-currency-gbp'),
    ("Switch currency to AUD on a {city} property page and report the AUD nightly rate plus the conversion rate disclosed in the footer.",
     'locale-currency-aud'),
    ("In {city}, compare the same property's price in USD, EUR, GBP, and AUD; report which currency yields the lowest displayed number.",
     'locale-currency-multi'),
    # 3. AMP-property-stub
    ("Open the AMP version of a {city} property at /amp/property/<slug>; report the canonical link rel='canonical' URL it points back to.",
     'amp-stub'),
    ("On /amp/property/<slug> for a {city} hotel, confirm the page declares `<html amp>` and report which AMP boilerplate scripts are loaded.",
     'amp-stub'),
    ("From a {city} property's AMP page, scroll to the reviews section; report the headline of the first review shown.",
     'amp-stub'),
    # 4. accessibility-WCAG-AA-audit
    ("Open /accessibility on the booking site; report which WCAG conformance level the site claims (A / AA / AAA).",
     'wcag-audit'),
    ("On a {city} property page, find the accessibility-statement link in the footer; report the date of the latest WCAG-AA audit listed.",
     'wcag-audit'),
    ("Visit /accessibility and report the count of accessible-room features the site commits to supporting under WCAG-AA.",
     'wcag-audit'),
    # 5. multi-language-property-description
    ("Open a {city} property detail page in German (locale /de-de/); report the first sentence of the German-language `Über diese Unterkunft` description.",
     'multi-lang-de'),
    ("Switch the locale to /fr-fr/ on a {city} property page; report the French heading shown in place of `About this property`.",
     'multi-lang-fr'),
    ("On a {city} hotel page in Spanish (/es-es/), report the Spanish translation of the cancellation policy label.",
     'multi-lang-es'),
    ("Open a {city} property in Italian (/it-it/) and report the Italian word shown in place of `Amenities`.",
     'multi-lang-it'),
    ("Switch to /zh-cn/ on a {city} property; report the Chinese-language label used for `Reviews`.",
     'multi-lang-zh'),
    ("Open the same {city} property in /ja-jp/ Japanese; report the Japanese rendering of the property's star rating row.",
     'multi-lang-ja'),
    # 6. TripAdvisor-cross-link-stub
    ("On a {city} property detail page, scroll to the bottom; report the TripAdvisor cross-link badge's declared review count.",
     'tripadvisor-link'),
    ("From a {city} hotel page, click the `Compare on TripAdvisor` stub link and report the destination URL it points to.",
     'tripadvisor-link'),
    ("On any {city} property, find the TripAdvisor traveller-rating star count in the cross-link section and report the number.",
     'tripadvisor-link'),
    # 7. multi-step compound
    ("Switch locale to /de-de/, open a {city} property, change currency to EUR, then proceed to checkout; report the EUR total shown.",
     'multi-step-locale-book'),
    ("Open the AMP version of a {city} property; tap `View full site` to land on the canonical page, then add the Standard Double Room to the bag and report the bag total.",
     'multi-step-amp-book'),
    ("From /sitemap-properties.xml, pick the first {city} URL listed, open it, switch to /zh-cn/, and report the Chinese title of the page.",
     'multi-step-sitemap-locale'),
    ("Open /robots.txt, confirm /amp/ is allowed, then navigate to /amp/property/<slug> for a {city} property and report the Last-Modified header value or page-footer date.",
     'multi-step-robots-amp'),
    ("From a {city} property, follow the TripAdvisor stub link, return, switch currency to AUD, and reserve the cheapest available room; report the AUD subtotal at checkout.",
     'multi-step-tripadvisor-book'),
    # extra SEO meta variants
    ("Open the {city} property detail page source; report the value of the `og:title` Open Graph meta tag.",
     'seo-og-title'),
    ("On a {city} hotel page, locate the `og:image` meta tag in the head; report whether it points to the property's primary image.",
     'seo-og-image'),
    ("Find the `og:price:amount` and `og:price:currency` meta tags on a {city} property page; report both values.",
     'seo-og-price'),
]


def gen_tasks(cities, start_id, target_total=1000):
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
    for tmpl, kind in R7_TASK_TEMPLATES:
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

    hotels = gen_hotels(cities, target_total=5900)
    print(f"  hotels generated: {len(hotels)}")
    with open(SCRAPED / 'expansion_hotels_r7.json', 'w') as f:
        json.dump(hotels, f, indent=1, ensure_ascii=False, sort_keys=True)

    start_id = _next_task_id()
    print(f"  task start id: Booking--{start_id}")
    tasks = gen_tasks(cities, start_id=start_id, target_total=1000)
    print(f"  tasks generated: {len(tasks)}")
    with open(SCRAPED / 'expansion_tasks_r7.jsonl', 'w') as f:
        for t in tasks:
            f.write(json.dumps(t, ensure_ascii=False) + '\n')


if __name__ == '__main__':
    main()
