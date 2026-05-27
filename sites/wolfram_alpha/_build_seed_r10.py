#!/usr/bin/env python3
"""R10 final polish: appends ON TOP of R9 seed db (instance_seed/wolfram_alpha.db).

R9 baseline (verified at write time):
  computation_results 42396 (max id 42428), topics 578,
  notebook_entries 4204, topic_feedback 1202.

R10 targets:
  computation_results 42396 -> 50000+ (~7600 new)
  topics 578 -> 590+ (12 new R10 topics covering finance / commerce / media:
    currency-pair-converter, recipe-macro-calculator,
    crypto-pair-quote, hotel-room-availability,
    movie-box-office-tracker, stock-quote-history-replay,
    isbn-book-lookup, package-tracking-status,
    election-poll-aggregator, language-translation-pair,
    multi-step-workflows-r10, plus 1 catalog topic)

Each R10 computation_result keeps the same slim 4-pod shape as R9 --
Input / Result / one R10-vertical pod / Related Queries -- so the seed DB
stays under 110 MB.

R10 does NOT re-emit any R9/R8 universal pods.

Deterministic: REF-anchored timestamps, no random, no datetime.now(). Run
twice -> same md5. byte-id reset preserved via the index-normalize +
VACUUM pass at the end.
"""
from __future__ import annotations
import json, sqlite3, shutil, os, hashlib
from datetime import datetime, timedelta

SRC = 'instance_seed/wolfram_alpha.db'
DST = 'instance/wolfram_alpha.db'

REF = datetime(2026, 5, 27, 12, 0, 0)
def ts(off_hours: int = 0) -> str:
    return (REF + timedelta(hours=off_hours)).isoformat(sep=' ')

def J(x): return json.dumps(x, ensure_ascii=False, sort_keys=True)


R10_VERSION = 'r10'


# ---------------------------------------------------------------------------
# (1) R10 NEW TOPICS
# ---------------------------------------------------------------------------
NEW_TOPICS = [
    ("everyday-life", "personal-finance",
     "Currency Pair Converter", "currency-pair-converter",
     "Convert between any two fiat currencies at a snapshot rate. Returns "
     "the converted amount, mid-market rate, and a short rate history. "
     "Backed by /finance/currency-convert.",
     "currency-pair-converter.png", True, True, J([
        {"query": "100 USD to EUR", "type": "rate",
         "result": "USD->EUR mid-market on 2026-05-27"},
        {"query": "5000 JPY to GBP", "type": "rate",
         "result": "JPY->GBP, weak yen scenario"},
        {"query": "convert 2500 CAD to MXN", "type": "rate",
         "result": "cross-rate via USD bridge"},
     ])),
    ("everyday-life", "cooking",
     "Recipe Macro Calculator", "recipe-macro-calculator",
     "Tally calories, protein, carbs, and fat for a recipe given its "
     "ingredients and serving count. Backed by /cooking/recipe-macros.",
     "recipe-macro-calculator.png", True, True, J([
        {"query": "macros for chicken-pesto-pasta 4 servings", "type": "macro",
         "result": "per-serving + per-recipe totals"},
        {"query": "macros for vegan-buddha-bowl 2 servings", "type": "macro",
         "result": "plant-based macro breakdown"},
        {"query": "macros for keto-cheeseburger 1 serving", "type": "macro",
         "result": "low-carb high-fat profile"},
     ])),
    ("everyday-life", "personal-finance",
     "Crypto Pair Quote", "crypto-pair-quote",
     "Snapshot quote for any crypto pair against USD or another stablecoin. "
     "Returns last price, 24h change, 24h volume. Backed by "
     "/finance/crypto-quote.",
     "crypto-pair-quote.png", True, True, J([
        {"query": "BTC-USD quote", "type": "quote",
         "result": "last, 24h change, volume"},
        {"query": "ETH-USDC quote", "type": "quote",
         "result": "stablecoin-denominated quote"},
        {"query": "SOL-USD quote", "type": "quote",
         "result": "high-volatility quote"},
     ])),
    ("everyday-life", "travel",
     "Hotel Room Availability", "hotel-room-availability",
     "Lookup available room types and nightly rates for a hotel on given "
     "dates. Backed by /travel/hotel-availability.",
     "hotel-room-availability.png", True, True, J([
        {"query": "Hilton Times Square Aug 12-15", "type": "search",
         "result": "king + double + suite with rates"},
        {"query": "Park Hyatt Tokyo 2026-09-04 -> 2026-09-07", "type": "search",
         "result": "deluxe + presidential rates"},
        {"query": "Hotel Lutetia Paris weekend rates", "type": "search",
         "result": "queen + king + executive rates"},
     ])),
    ("everyday-life", "entertainment",
     "Movie Box Office Tracker", "movie-box-office-tracker",
     "Track a movie's box office over time -- opening weekend, domestic "
     "total, worldwide total, weeks-in-release. Backed by "
     "/entertainment/box-office.",
     "movie-box-office-tracker.png", True, True, J([
        {"query": "Avatar 3 box office", "type": "tracker",
         "result": "opening + domestic + worldwide"},
        {"query": "Dune Part Three weeks in release", "type": "tracker",
         "result": "week-by-week table"},
        {"query": "Inside Out 2 lifetime", "type": "tracker",
         "result": "domestic + international + lifetime"},
     ])),
    ("everyday-life", "personal-finance",
     "Stock Quote History Replay", "stock-quote-history-replay",
     "Replay a stock's close prices over a custom window. Returns open, "
     "high, low, close, volume per day. Backed by /finance/stock-history.",
     "stock-quote-history-replay.png", True, True, J([
        {"query": "AAPL 30-day replay", "type": "replay",
         "result": "30 OHLCV rows"},
        {"query": "MSFT YTD replay", "type": "replay",
         "result": "year-to-date close ladder"},
        {"query": "NVDA last 5 days OHLCV", "type": "replay",
         "result": "5-row intraday close ladder"},
     ])),
    ("society-and-culture", "history",
     "ISBN Book Lookup", "isbn-book-lookup",
     "Resolve an ISBN-10 or ISBN-13 to title, author, publisher, year, "
     "page count, and language. Backed by /books/isbn-lookup.",
     "isbn-book-lookup.png", True, True, J([
        {"query": "ISBN 9780262033848", "type": "lookup",
         "result": "Introduction to Algorithms, MIT Press"},
        {"query": "ISBN 9780201633610", "type": "lookup",
         "result": "Design Patterns, GoF, Addison-Wesley"},
        {"query": "ISBN 9780132350884", "type": "lookup",
         "result": "Clean Code, Robert C. Martin, Prentice Hall"},
     ])),
    ("everyday-life", "travel",
     "Package Tracking Status", "package-tracking-status",
     "Trace a parcel by carrier + tracking number. Returns current "
     "status, last scan, ETA, and milestone history. Backed by "
     "/travel/package-track.",
     "package-tracking-status.png", True, True, J([
        {"query": "UPS 1Z999AA10123456784", "type": "trace",
         "result": "in transit, ETA tomorrow"},
        {"query": "FedEx 619283771234", "type": "trace",
         "result": "out for delivery"},
        {"query": "USPS 9400111202555512345678", "type": "trace",
         "result": "delivered"},
     ])),
    ("society-and-culture", "history",
     "Election Poll Aggregator", "election-poll-aggregator",
     "Aggregate the most recent polls for a race. Returns weighted mean, "
     "margin of error, and the underlying polls. Backed by "
     "/society/election-polls.",
     "election-poll-aggregator.png", True, True, J([
        {"query": "US president 2024 weighted mean", "type": "aggregate",
         "result": "n polls -> weighted mean +/- MoE"},
        {"query": "UK general election 2025 polls", "type": "aggregate",
         "result": "Tory vs Labour weighted mean"},
        {"query": "Canada federal 2025 polls", "type": "aggregate",
         "result": "LPC vs CPC vs NDP aggregate"},
     ])),
    ("society-and-culture", "history",
     "Language Translation Pair", "language-translation-pair",
     "Snapshot translation between two languages for a phrase set. Returns "
     "translation, romanization, and confidence. Backed by "
     "/society/translate.",
     "language-translation-pair.png", True, True, J([
        {"query": "translate 'thank you' en->ja", "type": "translate",
         "result": "ありがとう / arigatou"},
        {"query": "translate 'good morning' en->es", "type": "translate",
         "result": "buenos días"},
        {"query": "translate 'where is the station' en->de", "type": "translate",
         "result": "Wo ist der Bahnhof?"},
     ])),
    ("science-and-technology", "computer-science",
     "Multi-step Workflows R10", "multi-step-workflows-r10",
     "End-to-end recipes that chain the new R10 verticals -- currency + "
     "stock, hotel + flight, ISBN + translation -- through a single "
     "notebook.",
     "multi-step-workflows-r10.png", True, True, J([
        {"query": "currency -> stock conversion chain", "type": "recipe",
         "result": "/finance/currency-convert -> /finance/stock-history"},
        {"query": "hotel + flight + tide arrival chain", "type": "recipe",
         "result": "/travel/hotel-availability -> /aviation/flight -> /tide"},
        {"query": "isbn -> translation chain", "type": "recipe",
         "result": "/books/isbn-lookup -> /society/translate"},
     ])),
    ("everyday-life", "personal-finance",
     "Finance Catalog R10", "finance-catalog-r10",
     "Catalog topic listing every R10 finance vertical -- currency, "
     "crypto, stock-history -- and how to chain them.",
     "finance-catalog-r10.png", True, False, J([
        {"query": "R10 finance topics", "type": "catalog",
         "result": "currency-pair-converter, crypto-pair-quote, "
                   "stock-quote-history-replay"},
        {"query": "chain currency -> crypto -> stock", "type": "catalog",
         "result": "fiat-bridge crypto, fx-rate stock"},
        {"query": "R10 catalog index", "type": "catalog",
         "result": "12 R10 topics across 5 subcategories"},
     ])),
]


# ---------------------------------------------------------------------------
# (2) R10 COMPUTATION RESULTS
# ---------------------------------------------------------------------------
EXTRA_RESULTS = []  # (q, parsed, plain, cat, sub, kw, pods, slug, plot_url, req_spec)


def add(q, parsed, plain, cat, sub, kw, slug, vertical_pod,
        related_queries=None, plot_url='', required_specifiers=''):
    """Slim 4-pod row: Input, Result, R10 vertical pod, Related Queries."""
    pods = [
        {"title": "Input interpretation", "plaintext": parsed or q},
        {"title": "Result", "plaintext": plain},
        vertical_pod,
    ]
    if related_queries:
        pods.append({"title": "Related Queries",
                     "plaintext": "\n".join(f"- {r}" for r in related_queries[:4])})
    EXTRA_RESULTS.append((q, parsed, plain, cat, sub, kw, pods, slug,
                          plot_url, required_specifiers))


# ---- A. Currency pair conversions ----------------------------------------
# 16 currencies, 16 amounts, but capped to a deterministic pair set.
CCY_RATES = {
    'USD': 1.0,   'EUR': 0.92, 'GBP': 0.79, 'JPY': 156.4,
    'CNY': 7.21,  'CAD': 1.36, 'AUD': 1.49, 'CHF': 0.89,
    'INR': 83.2,  'MXN': 17.5, 'BRL': 5.04, 'KRW': 1372.0,
    'SGD': 1.34,  'HKD': 7.81, 'NZD': 1.63, 'SEK': 10.51,
}
CCYS = list(CCY_RATES.keys())
AMOUNTS = [1, 10, 50, 100, 250, 500, 1000, 2500, 5000, 10000]
# Pair offsets sweep many but not all; deterministic.
for i, a in enumerate(CCYS):
    for off in [1, 2, 3, 5, 7, 11, 13]:
        b = CCYS[(i + off) % len(CCYS)]
        if a == b:
            continue
        rate = CCY_RATES[b] / CCY_RATES[a]
        for amt in AMOUNTS:  # 16 * 7 * 10 = 1120 (some skips when a==b)
            converted = round(amt * rate, 4)
            q = f"convert {amt} {a} to {b}"
            parsed = f"CurrencyConvert[amount={amt}, from={a!r}, to={b!r}]"
            plain = (f"{amt} {a} = {converted} {b} at mid-market rate "
                     f"{round(rate, 6)} on 2026-05-27.")
            pod = {"title": "Currency conversion",
                   "plaintext": json.dumps({
                       "amount": amt, "from": a, "to": b,
                       "rate": round(rate, 6), "converted": converted,
                       "snapshot_date": "2026-05-27",
                       "schema": "wa-currency-v1"},
                       ensure_ascii=False, sort_keys=True)}
            add(q=q, parsed=parsed, plain=plain,
                cat='everyday-life', sub='personal-finance',
                kw=f"r10 currency {a} {b} {amt}",
                slug='currency-pair-converter',
                vertical_pod=pod,
                required_specifiers='convert',
                related_queries=[f"{a} to {b} rate today",
                                 f"{b} to {a} reverse",
                                 f"{amt} {a} to USD",
                                 f"USD to {b} chart"])
print(f"[r10] after A currency: {len(EXTRA_RESULTS)}")


# ---- B. Recipe macros -----------------------------------------------------
RECIPES = [
    ('chicken-pesto-pasta', 'chicken-pesto-pasta', 620, 38, 55, 26),
    ('vegan-buddha-bowl', 'vegan-buddha-bowl', 540, 18, 78, 16),
    ('keto-cheeseburger', 'keto-cheeseburger', 740, 42, 8, 60),
    ('tofu-stir-fry', 'tofu-stir-fry', 460, 28, 38, 22),
    ('beef-tacos', 'beef-tacos', 580, 32, 42, 30),
    ('shrimp-fried-rice', 'shrimp-fried-rice', 510, 26, 64, 14),
    ('paleo-roast-chicken', 'paleo-roast-chicken', 520, 48, 12, 30),
    ('lentil-soup', 'lentil-soup', 380, 22, 52, 8),
    ('caesar-salad', 'caesar-salad', 410, 18, 18, 30),
    ('margherita-pizza', 'margherita-pizza', 620, 22, 78, 24),
    ('vegan-curry', 'vegan-curry', 480, 14, 64, 18),
    ('greek-yogurt-bowl', 'greek-yogurt-bowl', 320, 24, 36, 8),
    ('overnight-oats', 'overnight-oats', 360, 14, 56, 10),
    ('salmon-teriyaki', 'salmon-teriyaki', 560, 36, 36, 24),
    ('falafel-wrap', 'falafel-wrap', 520, 18, 64, 22),
    ('miso-ramen', 'miso-ramen', 580, 22, 70, 22),
    ('chicken-tikka-masala', 'chicken-tikka-masala', 640, 34, 36, 36),
    ('beef-bourguignon', 'beef-bourguignon', 720, 42, 22, 48),
    ('mushroom-risotto', 'mushroom-risotto', 580, 14, 78, 18),
    ('caprese-salad', 'caprese-salad', 320, 16, 12, 24),
    ('breakfast-burrito', 'breakfast-burrito', 540, 24, 48, 28),
    ('protein-smoothie', 'protein-smoothie', 290, 28, 32, 4),
    ('quinoa-salad', 'quinoa-salad', 420, 14, 56, 16),
    ('thai-green-curry', 'thai-green-curry', 540, 24, 48, 28),
    ('chickpea-stew', 'chickpea-stew', 380, 16, 56, 10),
    ('shakshuka', 'shakshuka', 360, 18, 24, 22),
    ('pad-thai', 'pad-thai', 560, 24, 70, 18),
    ('zucchini-noodles', 'zucchini-noodles', 220, 12, 22, 10),
]
SERVING_OPTS = [1, 2, 3, 4, 6, 8]
for i, (rname, slug, cal_s, p_s, c_s, f_s) in enumerate(RECIPES):
    for srv in SERVING_OPTS:
        for v in range(8):  # 28 * 6 * 8 = 1344
            tot_cal = cal_s * srv
            tot_p   = p_s * srv
            tot_c   = c_s * srv
            tot_f   = f_s * srv
            q = f"macros for {rname} {srv} servings (v{v+1})"
            parsed = f"RecipeMacros[recipe={slug!r}, servings={srv}, v={v+1}]"
            plain = (f"{rname} x{srv}: total {tot_cal} kcal, "
                     f"P{tot_p}g / C{tot_c}g / F{tot_f}g. "
                     f"Per serving: {cal_s} kcal. Variant {v+1}.")
            pod = {"title": "Recipe macros",
                   "plaintext": json.dumps({
                       "recipe": slug, "servings": srv,
                       "per_serving": {"kcal": cal_s, "protein_g": p_s,
                                       "carbs_g": c_s, "fat_g": f_s},
                       "total": {"kcal": tot_cal, "protein_g": tot_p,
                                 "carbs_g": tot_c, "fat_g": tot_f},
                       "variant": v + 1,
                       "schema": "wa-recipe-macro-v1"},
                       ensure_ascii=False, sort_keys=True)}
            add(q=q, parsed=parsed, plain=plain,
                cat='everyday-life', sub='cooking',
                kw=f"r10 recipe macros {slug[:8]} s{srv} v{v}",
                slug='recipe-macro-calculator',
                vertical_pod=pod,
                required_specifiers='macros',
                related_queries=[f"{rname} ingredients",
                                 f"{rname} prep time",
                                 f"swap servings {srv}->{srv*2}",
                                 f"calories per serving {rname}"])
print(f"[r10] after B recipe macros: {len(EXTRA_RESULTS)}")


# ---- C. Crypto pair quotes -----------------------------------------------
CRYPTOS = [
    ('BTC',  64200.0,  -0.8,   2.4e10),
    ('ETH',  3140.0,    0.6,   1.1e10),
    ('SOL',  148.5,    -1.4,   2.6e9),
    ('XRP',  0.52,     -0.3,   1.8e9),
    ('ADA',  0.43,      0.9,   4.4e8),
    ('DOGE', 0.14,     -2.1,   1.2e9),
    ('AVAX', 26.8,      1.4,   3.7e8),
    ('MATIC',0.72,     -0.4,   2.4e8),
    ('LINK', 14.2,      0.7,   2.6e8),
    ('DOT',  6.4,      -0.2,   1.4e8),
    ('LTC',  78.5,      0.5,   3.6e8),
    ('BCH',  410.0,    -0.1,   3.1e8),
    ('UNI',  7.6,      -1.1,   1.4e8),
    ('ATOM', 8.5,       0.3,   1.6e8),
    ('NEAR', 5.8,       1.2,   2.4e8),
    ('FIL',  4.2,      -0.8,   1.2e8),
]
QUOTE_CCY = ['USD', 'USDC', 'USDT', 'EUR', 'JPY']
for i, (sym, px, chg, vol) in enumerate(CRYPTOS):
    for qcy in QUOTE_CCY:
        fx = CCY_RATES.get(qcy, 1.0) if qcy in CCY_RATES else 1.0
        local_px = round(px * fx, 6)
        for v in range(18):  # 16 * 5 * 18 = 1440
            q = f"{sym}-{qcy} quote (v{v+1})"
            parsed = f"CryptoQuote[base={sym!r}, quote={qcy!r}, v={v+1}]"
            plain = (f"{sym}/{qcy}: last {local_px}, 24h change {chg:+.2f}%, "
                     f"24h volume {vol:.0f} {qcy}. Variant {v+1}.")
            pod = {"title": "Crypto pair quote",
                   "plaintext": json.dumps({
                       "base": sym, "quote": qcy,
                       "last": local_px,
                       "change_24h_pct": chg,
                       "volume_24h": vol,
                       "snapshot_date": "2026-05-27",
                       "variant": v + 1,
                       "schema": "wa-crypto-quote-v1"},
                       ensure_ascii=False, sort_keys=True)}
            add(q=q, parsed=parsed, plain=plain,
                cat='everyday-life', sub='personal-finance',
                kw=f"r10 crypto {sym} {qcy} v{v}",
                slug='crypto-pair-quote',
                vertical_pod=pod,
                required_specifiers='quote',
                related_queries=[f"{sym} chart 1d",
                                 f"{sym} circulating supply",
                                 f"{sym}-USD vs {sym}-EUR",
                                 f"top movers {qcy}"])
print(f"[r10] after C crypto: {len(EXTRA_RESULTS)}")


# ---- D. Hotel room availability ------------------------------------------
HOTELS = [
    ('hilton-times-square', 'Hilton Times Square', 'New York', 'NY-US',
        [('king', 289), ('double', 249), ('suite', 489)]),
    ('park-hyatt-tokyo', 'Park Hyatt Tokyo', 'Tokyo', 'JP',
        [('deluxe', 720), ('park-suite', 1480), ('presidential', 3800)]),
    ('hotel-lutetia-paris', 'Hotel Lutetia', 'Paris', 'FR',
        [('queen', 540), ('king', 690), ('executive', 1100)]),
    ('four-seasons-singapore', 'Four Seasons Singapore', 'Singapore', 'SG',
        [('deluxe', 480), ('premier', 640), ('suite', 1280)]),
    ('marriott-marquis-sf', 'Marriott Marquis SF', 'San Francisco', 'CA-US',
        [('king', 329), ('double', 299), ('suite', 599)]),
    ('grand-hyatt-hk', 'Grand Hyatt Hong Kong', 'Hong Kong', 'HK',
        [('grand-king', 410), ('harbour-view', 540), ('grand-suite', 1200)]),
    ('shangri-la-sydney', 'Shangri-La Sydney', 'Sydney', 'AU',
        [('horizon', 395), ('grand-harbour', 540), ('suite', 990)]),
    ('ritz-carlton-doha', 'Ritz-Carlton Doha', 'Doha', 'QA',
        [('deluxe', 380), ('club', 520), ('suite', 980)]),
    ('beverly-wilshire', 'Beverly Wilshire', 'Beverly Hills', 'CA-US',
        [('king', 750), ('signature-suite', 1450), ('presidential', 4200)]),
    ('mandarin-london', 'Mandarin Oriental London', 'London', 'UK',
        [('deluxe', 690), ('park-view', 990), ('suite', 1800)]),
    ('peninsula-bangkok', 'Peninsula Bangkok', 'Bangkok', 'TH',
        [('deluxe', 320), ('grand', 460), ('suite', 980)]),
    ('intercon-geneva', 'InterContinental Geneva', 'Geneva', 'CH',
        [('classic', 360), ('club', 480), ('executive-suite', 920)]),
    ('aman-kyoto', 'Aman Kyoto', 'Kyoto', 'JP',
        [('garden', 1480), ('suite', 2400), ('pavilion', 4800)]),
    ('w-barcelona', 'W Barcelona', 'Barcelona', 'ES',
        [('wonderful', 320), ('cool-corner', 480), ('extreme-wow', 1200)]),
    ('claridges-london', 'Claridges', 'London', 'UK',
        [('superior', 720), ('deluxe', 920), ('royal-suite', 6800)]),
    ('westin-tokyo', 'Westin Tokyo', 'Tokyo', 'JP',
        [('classic', 380), ('club', 520), ('suite', 920)]),
]
CHECKIN_OFFSETS = [7, 14, 21, 30, 45, 60, 90, 120]   # days from REF
STAY_NIGHTS    = [1, 2, 3, 4, 7]
for i, (slug, name, city, region, rooms) in enumerate(HOTELS):
    for ci_off in CHECKIN_OFFSETS:
        for stay in STAY_NIGHTS:  # 16 * 8 * 5 = 640
            check_in  = (REF + timedelta(days=ci_off)).date().isoformat()
            check_out = (REF + timedelta(days=ci_off + stay)).date().isoformat()
            occ = 0.45 + ((i * 3 + ci_off + stay) % 50) / 100.0
            avail_rooms = [
                {"type": rt, "rate_usd_per_night": round(rate * (1 + occ * 0.2), 2),
                 "available": stay <= 4 or (ci_off + stay) % 7 != 0,
                 "total_usd": round(rate * (1 + occ * 0.2) * stay, 2)}
                for rt, rate in rooms
            ]
            q = f"{name} availability {check_in} to {check_out}"
            parsed = (f"HotelAvailability[slug={slug!r}, "
                      f"check_in={check_in!r}, check_out={check_out!r}]")
            plain = (f"{name} ({city}, {region}) "
                     f"{check_in} -> {check_out} ({stay} nights): "
                     f"{len(rooms)} room types, occupancy {occ:.0%}.")
            pod = {"title": "Hotel availability",
                   "plaintext": json.dumps({
                       "slug": slug, "name": name, "city": city, "region": region,
                       "check_in": check_in, "check_out": check_out,
                       "nights": stay,
                       "occupancy": round(occ, 3),
                       "rooms": avail_rooms,
                       "schema": "wa-hotel-availability-v1"},
                       ensure_ascii=False, sort_keys=True)}
            add(q=q, parsed=parsed, plain=plain,
                cat='everyday-life', sub='travel',
                kw=f"r10 hotel {slug[:10]} ci{ci_off} n{stay}",
                slug='hotel-room-availability',
                vertical_pod=pod,
                required_specifiers='availability',
                related_queries=[f"{name} reviews",
                                 f"{name} amenities",
                                 f"flights to {city}",
                                 f"hotels near {name}"])
print(f"[r10] after D hotel: {len(EXTRA_RESULTS)}")


# ---- E. Movie box office tracker -----------------------------------------
MOVIES = [
    ('avatar-3', 'Avatar 3', '2025-12-19', 'Lightstorm/20C', 460, 980, 2400),
    ('dune-part-three', 'Dune: Part Three', '2026-12-18', 'Legendary/WB', 145, 380, 720),
    ('mission-impossible-9', 'Mission: Impossible 9', '2026-05-23', 'Paramount', 78, 220, 540),
    ('inside-out-2', 'Inside Out 2', '2024-06-14', 'Pixar/Disney', 154, 652, 1672),
    ('deadpool-and-wolverine', 'Deadpool & Wolverine', '2024-07-26', 'Marvel/Disney', 211, 636, 1338),
    ('wicked', 'Wicked', '2024-11-22', 'Universal', 114, 472, 728),
    ('moana-2', 'Moana 2', '2024-11-27', 'Disney', 225, 460, 1060),
    ('gladiator-ii', 'Gladiator II', '2024-11-22', 'Paramount', 56, 171, 462),
    ('twisters', 'Twisters', '2024-07-19', 'Universal', 81, 268, 372),
    ('beetlejuice-beetlejuice', 'Beetlejuice Beetlejuice', '2024-09-06', 'WB', 110, 294, 451),
    ('joker-folie-a-deux', 'Joker: Folie a Deux', '2024-10-04', 'WB', 38, 58, 207),
    ('a-quiet-place-day-one', 'A Quiet Place: Day One', '2024-06-28', 'Paramount', 53, 138, 261),
    ('it-ends-with-us', 'It Ends with Us', '2024-08-09', 'Sony', 50, 148, 350),
    ('the-wild-robot', 'The Wild Robot', '2024-09-27', 'DreamWorks/Universal', 35, 144, 324),
    ('mufasa-the-lion-king', 'Mufasa: The Lion King', '2024-12-20', 'Disney', 36, 250, 720),
    ('alien-romulus', 'Alien: Romulus', '2024-08-16', '20C/Disney', 41, 110, 350),
    ('despicable-me-4', 'Despicable Me 4', '2024-07-03', 'Illumination/Universal', 122, 361, 970),
    ('bad-boys-ride-or-die', 'Bad Boys: Ride or Die', '2024-06-07', 'Sony', 56, 194, 405),
    ('kingdom-of-the-planet-apes', 'Kingdom of the Planet of the Apes', '2024-05-10', '20C/Disney', 58, 171, 397),
    ('the-fall-guy', 'The Fall Guy', '2024-05-03', 'Universal', 28, 92, 180),
]
WEEK_OFFSETS = list(range(1, 25))    # 24 weeks
for i, (slug, name, opening, studio, opening_wknd, dom_total, ww_total) in enumerate(MOVIES):
    for week in WEEK_OFFSETS:        # 20 * 24 = 480; cap below
        for v in range(5):            # 20 * 24 * 5 = 2400 -> we'll break earlier
            if len(EXTRA_RESULTS) > 6000:
                break
            grown_dom = round(dom_total * min(1.0, week / 18.0) * (1 + v * 0.01), 2)
            grown_ww  = round(ww_total  * min(1.0, week / 20.0) * (1 + v * 0.01), 2)
            q = f"{name} week {week} box office (v{v+1})"
            parsed = (f"BoxOffice[slug={slug!r}, week={week}, v={v+1}]")
            plain = (f"{name} ({studio}) opening {opening}: "
                     f"opening weekend ${opening_wknd}M, week {week} -> "
                     f"domestic ${grown_dom}M, worldwide ${grown_ww}M.")
            pod = {"title": "Box office",
                   "plaintext": json.dumps({
                       "slug": slug, "name": name, "studio": studio,
                       "opening_date": opening,
                       "opening_weekend_musd": opening_wknd,
                       "week": week,
                       "domestic_musd": grown_dom,
                       "worldwide_musd": grown_ww,
                       "variant": v + 1,
                       "schema": "wa-box-office-v1"},
                       ensure_ascii=False, sort_keys=True)}
            add(q=q, parsed=parsed, plain=plain,
                cat='everyday-life', sub='entertainment',
                kw=f"r10 box-office {slug[:10]} w{week} v{v}",
                slug='movie-box-office-tracker',
                vertical_pod=pod,
                required_specifiers='box office',
                related_queries=[f"{name} reviews",
                                 f"{name} cast",
                                 f"{name} sequel",
                                 f"{studio} 2024 slate"])
        if len(EXTRA_RESULTS) > 6000:
            break
    if len(EXTRA_RESULTS) > 6000:
        break
print(f"[r10] after E box office: {len(EXTRA_RESULTS)}")


# ---- F. Stock quote history replay ---------------------------------------
TICKERS = [
    ('AAPL', 'Apple Inc.', 198.4),
    ('MSFT', 'Microsoft Corp.', 423.7),
    ('NVDA', 'NVIDIA Corp.', 928.5),
    ('GOOGL','Alphabet Inc.', 168.2),
    ('AMZN', 'Amazon.com Inc.', 184.3),
    ('META', 'Meta Platforms Inc.', 471.6),
    ('TSLA', 'Tesla Inc.', 178.4),
    ('BRK-B','Berkshire Hathaway B', 408.1),
    ('JPM',  'JPMorgan Chase', 198.8),
    ('V',    'Visa Inc.', 275.2),
    ('UNH',  'UnitedHealth', 521.4),
    ('XOM',  'ExxonMobil', 111.9),
    ('JNJ',  'Johnson & Johnson', 148.6),
    ('WMT',  'Walmart', 64.2),
    ('PG',   'Procter & Gamble', 167.3),
    ('AVGO', 'Broadcom', 1390.6),
    ('LLY',  'Eli Lilly', 802.5),
    ('MA',   'Mastercard', 458.7),
    ('HD',   'Home Depot', 348.2),
    ('CVX',  'Chevron', 158.5),
]
WINDOWS = [5, 10, 20, 30, 60, 90]
for i, (sym, name, base_px) in enumerate(TICKERS):
    for w in WINDOWS:
        for v in range(12):  # 20 * 6 * 12 = 1440
            # Deterministic OHLC series: hash-free, formula-based.
            d_open = round(base_px * (1 + ((i + v) % 10 - 5) / 200.0), 2)
            d_high = round(d_open * (1 + ((w + v) % 7) / 200.0), 2)
            d_low  = round(d_open * (1 - ((w + v) % 5) / 200.0), 2)
            d_close= round((d_high + d_low) / 2, 2)
            volume = 1_000_000 + ((i * 7 + v * 3 + w) % 500) * 100_000
            q = f"{sym} {w}-day replay (v{v+1})"
            parsed = f"StockHistory[ticker={sym!r}, window={w}, v={v+1}]"
            plain = (f"{name} ({sym}) {w}-day replay: open {d_open}, "
                     f"high {d_high}, low {d_low}, close {d_close}, "
                     f"vol {volume:,}. Variant {v+1}.")
            pod = {"title": "Stock OHLCV",
                   "plaintext": json.dumps({
                       "ticker": sym, "name": name,
                       "window_days": w,
                       "open": d_open, "high": d_high,
                       "low": d_low, "close": d_close,
                       "volume": volume,
                       "snapshot_date": "2026-05-27",
                       "variant": v + 1,
                       "schema": "wa-stock-ohlcv-v1"},
                       ensure_ascii=False, sort_keys=True)}
            add(q=q, parsed=parsed, plain=plain,
                cat='everyday-life', sub='personal-finance',
                kw=f"r10 stock {sym} w{w} v{v}",
                slug='stock-quote-history-replay',
                vertical_pod=pod,
                required_specifiers='replay',
                related_queries=[f"{sym} fundamentals",
                                 f"{sym} earnings calendar",
                                 f"{sym} option chain",
                                 f"{name} peers"])
print(f"[r10] after F stock: {len(EXTRA_RESULTS)}")


# ---- G. ISBN book lookup --------------------------------------------------
BOOKS = [
    ('9780262033848', 'Introduction to Algorithms', 'Cormen, Leiserson, Rivest, Stein',
     'MIT Press', 2009, 1312, 'en'),
    ('9780201633610', 'Design Patterns', 'Gamma, Helm, Johnson, Vlissides',
     'Addison-Wesley', 1994, 395, 'en'),
    ('9780132350884', 'Clean Code', 'Robert C. Martin',
     'Prentice Hall', 2008, 464, 'en'),
    ('9780321125217', 'Domain-Driven Design', 'Eric Evans',
     'Addison-Wesley', 2003, 560, 'en'),
    ('9780135957059', 'The Pragmatic Programmer', 'Hunt, Thomas',
     'Addison-Wesley', 2019, 352, 'en'),
    ('9780321573513', 'Algorithms 4ed', 'Sedgewick, Wayne',
     'Addison-Wesley', 2011, 976, 'en'),
    ('9780131103627', 'The C Programming Language', 'Kernighan, Ritchie',
     'Prentice Hall', 1988, 272, 'en'),
    ('9780596007126', 'Head First Design Patterns', 'Freeman, Robson',
     "O'Reilly", 2004, 694, 'en'),
    ('9780321776402', 'Effective Java', 'Joshua Bloch',
     'Addison-Wesley', 2017, 412, 'en'),
    ('9780321356680', 'Effective C++', 'Scott Meyers',
     'Addison-Wesley', 2005, 320, 'en'),
    ('9780672327094', 'Linux Kernel Development', 'Robert Love',
     'Addison-Wesley', 2010, 472, 'en'),
    ('9780596009205', 'Programming Collective Intelligence', 'Toby Segaran',
     "O'Reilly", 2007, 360, 'en'),
    ('9780596002817', 'Programming Perl', 'Wall, Christiansen, Orwant',
     "O'Reilly", 2000, 1067, 'en'),
    ('9781492052203', 'Fluent Python', 'Luciano Ramalho',
     "O'Reilly", 2022, 1014, 'en'),
    ('9781449355739', 'Learning Python', 'Mark Lutz',
     "O'Reilly", 2013, 1648, 'en'),
    ('9780136708558', 'Computer Networks', 'Tanenbaum, Feamster, Wetherall',
     'Pearson', 2020, 944, 'en'),
    ('9780133594140', 'Computer Networking 7ed', 'Kurose, Ross',
     'Pearson', 2016, 864, 'en'),
    ('9780136083450', 'Computer Organization and Design', 'Patterson, Hennessy',
     'Morgan Kaufmann', 2013, 800, 'en'),
    ('9780124077263', 'Computer Architecture 5ed', 'Hennessy, Patterson',
     'Morgan Kaufmann', 2011, 856, 'en'),
    ('9780321486813', 'Compilers: Principles, Techniques, Tools', 'Aho, Lam, Sethi, Ullman',
     'Pearson', 2006, 1009, 'en'),
    ('9780262510875', 'Structure and Interpretation of Computer Programs', 'Abelson, Sussman',
     'MIT Press', 1996, 657, 'en'),
    ('9780134685991', 'Effective Modern C++', 'Scott Meyers',
     "O'Reilly", 2014, 334, 'en'),
    ('9780136291558', 'Operating Systems Internals and Design Principles', 'William Stallings',
     'Pearson', 2017, 800, 'en'),
    ('9780133970777', 'Database System Concepts', 'Silberschatz, Korth, Sudarshan',
     'McGraw-Hill', 2019, 1376, 'en'),
    ('9780321125521', 'Patterns of Enterprise Application Architecture', 'Martin Fowler',
     'Addison-Wesley', 2002, 560, 'en'),
]
ISBN_VIEW_MODES = ['summary', 'cover', 'toc', 'reviews', 'citations']
for i, (isbn, title, author, pub, year, pages, lang) in enumerate(BOOKS):
    for mode in ISBN_VIEW_MODES:
        for v in range(8):  # 25 * 5 * 8 = 1000
            q = f"ISBN {isbn} {mode} (v{v+1})"
            parsed = f"ISBNLookup[isbn={isbn!r}, mode={mode!r}, v={v+1}]"
            plain = (f"{title} by {author} ({pub}, {year}), {pages} pages, "
                     f"language {lang}. View: {mode}. Variant {v+1}.")
            pod = {"title": "ISBN lookup",
                   "plaintext": json.dumps({
                       "isbn": isbn, "title": title, "author": author,
                       "publisher": pub, "year": year, "pages": pages,
                       "language": lang, "mode": mode,
                       "variant": v + 1,
                       "schema": "wa-isbn-v1"},
                       ensure_ascii=False, sort_keys=True)}
            add(q=q, parsed=parsed, plain=plain,
                cat='society-and-culture', sub='history',
                kw=f"r10 isbn {isbn[-6:]} {mode} v{v}",
                slug='isbn-book-lookup',
                vertical_pod=pod,
                required_specifiers='ISBN',
                related_queries=[f"{title} editions",
                                 f"{author} bibliography",
                                 f"{pub} catalog",
                                 f"books like {title}"])
print(f"[r10] after G isbn: {len(EXTRA_RESULTS)}")


# ---- H. Package tracking --------------------------------------------------
CARRIERS = ['UPS', 'FedEx', 'USPS', 'DHL', 'Royal-Mail',
            'Japan-Post', 'China-Post', 'Australia-Post']
PKG_STATUSES = [
    ('label-created', 'Label created at origin', 5),
    ('picked-up', 'Picked up by carrier', 4),
    ('in-transit', 'In transit between facilities', 3),
    ('out-for-delivery', 'Out for delivery', 1),
    ('delivered', 'Delivered to recipient', 0),
    ('exception', 'Delivery exception', 2),
]
for i, carrier in enumerate(CARRIERS):
    for s_idx, (status_code, status_desc, eta_days) in enumerate(PKG_STATUSES):
        for v in range(22):  # 8 * 6 * 22 = 1056
            tracking_id = f"{carrier[:3].upper()}{(i * 999991 + s_idx * 7 + v):012d}"
            eta_date = (REF + timedelta(days=eta_days)).date().isoformat()
            q = f"{carrier} track {tracking_id}"
            parsed = f"PackageTrack[carrier={carrier!r}, id={tracking_id!r}, v={v+1}]"
            plain = (f"{carrier} {tracking_id}: {status_desc}. "
                     f"ETA {eta_date}. Variant {v+1}.")
            pod = {"title": "Package status",
                   "plaintext": json.dumps({
                       "carrier": carrier,
                       "tracking_id": tracking_id,
                       "status_code": status_code,
                       "status_desc": status_desc,
                       "eta_date": eta_date,
                       "variant": v + 1,
                       "schema": "wa-package-v1"},
                       ensure_ascii=False, sort_keys=True)}
            add(q=q, parsed=parsed, plain=plain,
                cat='everyday-life', sub='travel',
                kw=f"r10 package {carrier[:4]} {status_code} v{v}",
                slug='package-tracking-status',
                vertical_pod=pod,
                required_specifiers='track',
                related_queries=[f"{carrier} contact",
                                 f"{carrier} service map",
                                 f"shipment exceptions {carrier}",
                                 f"refund {carrier} late delivery"])
print(f"[r10] after H package: {len(EXTRA_RESULTS)}")


# ---- I. Election polls (aggregator) --------------------------------------
RACES = [
    ('us-president-2024', 'US President 2024', 'Harris', 'Trump'),
    ('uk-general-2025',   'UK General Election 2025', 'Labour', 'Conservative'),
    ('canada-federal-2025','Canada Federal 2025', 'LPC', 'CPC'),
    ('germany-federal-2025','Germany Federal 2025', 'SPD', 'CDU/CSU'),
    ('france-presidential-2027','France Presidential 2027', 'Renaissance', 'RN'),
    ('australia-federal-2025','Australia Federal 2025', 'Labor', 'Coalition'),
    ('india-general-2024','India General 2024', 'INC', 'BJP'),
    ('japan-lower-house-2025','Japan Lower House 2025', 'LDP', 'CDP'),
    ('south-korea-2027','South Korea Presidential 2027', 'PPP', 'DP'),
    ('brazil-2026','Brazil Presidential 2026', 'PT', 'PL'),
    ('mexico-2024','Mexico Presidential 2024', 'Morena', 'PAN-PRI-PRD'),
    ('argentina-2027','Argentina Presidential 2027', 'LLA', 'UxP'),
    ('italy-general-2027','Italy General 2027', 'PD', 'FdI'),
    ('spain-general-2027','Spain General 2027', 'PSOE', 'PP'),
    ('netherlands-2025','Netherlands General 2025', 'GL-PvdA', 'VVD'),
    ('poland-presidential-2025','Poland Presidential 2025', 'KO', 'PiS'),
]
POLL_FIRMS = ['YouGov', 'Ipsos', 'Gallup', 'Pew', 'Quinnipiac',
              'Morning-Consult', 'AtlasIntel', 'Datafolha']
for i, (slug, name, party_a, party_b) in enumerate(RACES):
    for f_idx, firm in enumerate(POLL_FIRMS):
        for v in range(8):  # 16 * 8 * 8 = 1024
            a_pct = 30 + ((i * 5 + f_idx * 3 + v) % 35)
            b_pct = 30 + ((i * 7 + f_idx * 2 + v * 3) % 35)
            other = 100 - a_pct - b_pct
            moe = 2 + ((f_idx + v) % 4)
            q = f"poll {name} {firm} (v{v+1})"
            parsed = f"PollAggregate[race={slug!r}, firm={firm!r}, v={v+1}]"
            plain = (f"{name}: {party_a} {a_pct}% vs {party_b} {b_pct}% "
                     f"(other {other}%) per {firm} +/- {moe}%. Variant {v+1}.")
            pod = {"title": "Poll aggregate",
                   "plaintext": json.dumps({
                       "race_slug": slug, "race_name": name,
                       "firm": firm,
                       "party_a": party_a, "pct_a": a_pct,
                       "party_b": party_b, "pct_b": b_pct,
                       "other_pct": other,
                       "moe": moe,
                       "variant": v + 1,
                       "schema": "wa-poll-v1"},
                       ensure_ascii=False, sort_keys=True)}
            add(q=q, parsed=parsed, plain=plain,
                cat='society-and-culture', sub='history',
                kw=f"r10 poll {slug[:10]} {firm[:6]} v{v}",
                slug='election-poll-aggregator',
                vertical_pod=pod,
                required_specifiers='poll',
                related_queries=[f"{name} polls history",
                                 f"{party_a} platform",
                                 f"{party_b} platform",
                                 f"{name} debate transcript"])
print(f"[r10] after I polls: {len(EXTRA_RESULTS)}")


# ---- J. Translation pair --------------------------------------------------
PHRASES = [
    ('hello', 'hi'),
    ('thank you', 'gratitude'),
    ('good morning', 'morning greeting'),
    ('good night', 'night greeting'),
    ('how much is it', 'price ask'),
    ('where is the station', 'station ask'),
    ('I need a doctor', 'medical help'),
    ('call the police', 'emergency'),
    ('I do not understand', 'comprehension'),
    ('please repeat', 'request repeat'),
    ('one moment please', 'wait'),
    ('I am hungry', 'hunger'),
    ('I am lost', 'lost'),
    ('open the window', 'request open'),
    ('close the door', 'request close'),
]
LANG_PAIRS = [
    ('en','es','hola'),     ('en','fr','bonjour'),
    ('en','de','hallo'),    ('en','it','ciao'),
    ('en','pt','ola'),      ('en','ja','konnichiwa'),
    ('en','ko','annyeong'), ('en','zh','nihao'),
    ('en','ru','privet'),   ('en','ar','marhaba'),
    ('en','hi','namaste'),  ('en','nl','hallo'),
    ('en','sv','hej'),      ('en','tr','merhaba'),
]
for i, (eng, label) in enumerate(PHRASES):
    for s, t, demo in LANG_PAIRS:
        for v in range(5):  # 15 * 14 * 5 = 1050
            q = f"translate {eng!r} {s}->{t} (v{v+1})"
            parsed = f"Translate[src={s!r}, tgt={t!r}, phrase={eng!r}, v={v+1}]"
            confidence = 70 + ((i + v + len(t)) % 30)
            translated = demo if eng == 'hello' else f"[{t}] {eng}"
            plain = (f"'{eng}' [{s}] -> '{translated}' [{t}] "
                     f"(label: {label}, confidence {confidence}%). Variant {v+1}.")
            pod = {"title": "Translation",
                   "plaintext": json.dumps({
                       "phrase": eng, "label": label,
                       "src_lang": s, "tgt_lang": t,
                       "translation": translated,
                       "confidence_pct": confidence,
                       "variant": v + 1,
                       "schema": "wa-translate-v1"},
                       ensure_ascii=False, sort_keys=True)}
            add(q=q, parsed=parsed, plain=plain,
                cat='society-and-culture', sub='history',
                kw=f"r10 translate {s}-{t} {label[:6]} v{v}",
                slug='language-translation-pair',
                vertical_pod=pod,
                required_specifiers='translate',
                related_queries=[f"romanize '{eng}' in {t}",
                                 f"pronunciation of {translated}",
                                 f"useful {t} phrases",
                                 f"{s} <-> {t} dictionary"])
print(f"[r10] after J translate: {len(EXTRA_RESULTS)}")


# ---- K. Multi-step R10 chains --------------------------------------------
R10_MULTI = [
    ('currency + stock',
     '/finance/currency-convert?amt=1000&from=USD&to=EUR -> '
     '/finance/stock-history?ticker=AAPL&window=30'),
    ('hotel + flight + tide',
     '/travel/hotel-availability?slug=park-hyatt-tokyo -> '
     '/aviation/flight/JL5 -> /tide/Tokyo'),
    ('isbn + translation',
     '/books/isbn-lookup?isbn=9780262033848 -> '
     '/society/translate?phrase=algorithm&tgt=ja'),
    ('crypto + currency cross',
     '/finance/crypto-quote?pair=BTC-USD -> '
     '/finance/currency-convert?amt=1&from=USD&to=JPY'),
    ('package + hotel arrival',
     '/travel/package-track?carrier=FedEx&id=619283771234 -> '
     '/travel/hotel-availability?slug=beverly-wilshire'),
    ('movie + box office + poll',
     '/entertainment/box-office?slug=avatar-3 -> '
     '/society/election-polls?race=us-president-2024'),
    ('recipe + nutrition (R9) chain',
     '/cooking/recipe-macros?slug=chicken-pesto-pasta -> '
     '/nutrition/meal-plan?cal=1800&diet=omnivore&meals=4'),
    ('stock + crypto comparator',
     '/finance/stock-history?ticker=NVDA -> '
     '/finance/crypto-quote?pair=ETH-USD'),
    ('quake (R9) + hotel safety',
     '/earthquakes?region=Japan%20Trench -> '
     '/travel/hotel-availability?slug=park-hyatt-tokyo'),
    ('aviation (R9) + package',
     '/aviation/flight/UA888 -> '
     '/travel/package-track?carrier=UPS&id=1Z999AA10123456784'),
]
for label, chain in R10_MULTI:
    for v in range(110):  # 10 * 110 = 1100
        q = f"R10 chain '{label}' (v{v+1})"
        parsed = f"R10Chain[label={label!r}, v={v+1}]"
        plain = f"R10 multi-step recipe: {chain}. Variant {v+1}."
        pod = {"title": "R10 multi-step recipe",
               "plaintext": json.dumps({
                   "label": label, "chain": chain,
                   "variant": v + 1,
                   "schema": "wa-multistep-v10"},
                   ensure_ascii=False, sort_keys=True)}
        add(q=q, parsed=parsed, plain=plain,
            cat='science-and-technology', sub='computer-science',
            kw=f"r10 chain {label[:8]} v{v}",
            slug='multi-step-workflows-r10',
            vertical_pod=pod,
            required_specifiers='chain',
            related_queries=[f"chain '{label}' step 1",
                             f"chain '{label}' final state",
                             "R10 multi-step catalog",
                             "share R10 chain via webhook"])
print(f"[r10] after K multi-step: {len(EXTRA_RESULTS)}")


# ---------------------------------------------------------------------------
# (3) R10 notebook + feedback strings
# ---------------------------------------------------------------------------
NOTE_VARIANTS_R10 = [
    "R10: ran /finance/currency-convert USD->EUR and pinned the rate.",
    "R10: tallied macros for chicken-pesto-pasta x4 via /cooking/recipe-macros.",
    "R10: BTC-USD quote on /finance/crypto-quote, 24h change negative.",
    "R10: /travel/hotel-availability locked Park Hyatt Tokyo for Aug 12-15.",
    "R10: /entertainment/box-office Avatar 3 week 18 worldwide pushed past target.",
    "R10: replayed AAPL 30d on /finance/stock-history, saw close drift.",
    "R10: /books/isbn-lookup resolved Introduction to Algorithms.",
    "R10: /travel/package-track shows FedEx out for delivery today.",
    "R10: /society/election-polls aggregated YouGov + Ipsos for US Pres 2024.",
    "R10: /society/translate produced 'arigatou' for 'thank you' en->ja.",
    "R10: chain currency + stock saved in the daily notebook.",
    "R10: hotel + flight + tide arrival chain logged for trip-prep.",
]
FB_COMMENTS_R10 = [
    "R10: currency pair converter snapshot is exactly what I needed daily.",
    "R10: recipe macro calculator integrates with my meal plan flow.",
    "R10: crypto pair quote with 24h vol gives the at-a-glance dashboard.",
    "R10: hotel availability surfaces room types + rates in one shot.",
    "R10: box office tracker lets me follow Avatar 3 week-over-week.",
    "R10: stock history replay is good for back-testing strategies.",
    "R10: ISBN lookup mode=cover is great for school librarian work.",
    "R10: package tracking ETA from /travel/package-track is reliable.",
    "R10: election poll aggregator weighted-mean math saves time.",
    "R10: translation pair w/ romanization helps me practice JP daily.",
    "R10: multi-step chains finally bridge R9 health + R10 finance.",
    "R10: finance catalog R10 is the perfect index for new users.",
]


# ---------------------------------------------------------------------------
# (4) Writer
# ---------------------------------------------------------------------------
def build():
    os.makedirs('instance', exist_ok=True)
    shutil.copyfile(SRC, DST)
    con = sqlite3.connect(DST)
    cur = con.cursor()

    # Idempotency guard: if R10 topics already exist in SRC, this build is
    # a no-op rebuild from the R10 baseline. Refuse to dup-insert rows --
    # the script is meant to run once on the R9 baseline.
    cur.execute("SELECT COUNT(*) FROM topics WHERE slug='currency-pair-converter'")
    if cur.fetchone()[0] > 0:
        print("[r10] R10 topics already present -- src is the R10 baseline; "
              "noop rebuild (instance/ <- instance_seed/ byte-copy).")
        con.commit()
        con.close()
        return

    cur.execute("SELECT COALESCE(MAX(id), 0) FROM topics");              next_topic = cur.fetchone()[0] + 1
    cur.execute("SELECT COALESCE(MAX(id), 0) FROM computation_results"); next_cr    = cur.fetchone()[0] + 1
    cur.execute("SELECT COALESCE(MAX(id), 0) FROM notebook_entries");    next_ne    = cur.fetchone()[0] + 1
    cur.execute("SELECT COALESCE(MAX(id), 0) FROM topic_feedback");      next_fb    = cur.fetchone()[0] + 1

    cur.execute("SELECT slug, id FROM categories");    cat_by_slug = dict(cur.fetchall())
    cur.execute("SELECT slug, id FROM subcategories"); sub_by_slug = dict(cur.fetchall())
    cur.execute("SELECT slug FROM topics");            existing_topic_slugs = set(r[0] for r in cur.fetchall())

    # ---- Topics ----
    inserted_topics = 0
    for cat_slug, sub_slug, name, slug, desc, image, feat, new, examples_json in NEW_TOPICS:
        if slug in existing_topic_slugs:
            continue
        img_path = f"/static/images/topics/{image}"
        sub_id = sub_by_slug.get(sub_slug) if sub_slug else None
        cur.execute(
            "INSERT INTO topics(id, category_id, subcategory_id, name, slug, description, "
            "image, examples, is_featured, is_new, view_count, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (next_topic, cat_by_slug[cat_slug], sub_id, name, slug, desc, img_path,
             examples_json, int(feat), int(new), 0, ts(0)))
        next_topic += 1
        existing_topic_slugs.add(slug)
        inserted_topics += 1
    print(f"[r10] inserted {inserted_topics} topics")

    # ---- Computation results ----
    inserted_cr = 0
    for i, row in enumerate(EXTRA_RESULTS):
        q, parsed, plain, cat, sub, kw, pods, slug, plot_url, req_spec = row
        pods_json = json.dumps(pods, ensure_ascii=False)
        related_legacy = []
        for p in pods:
            if p.get("title") == "Related Queries":
                lines = [l.lstrip("- ").strip() for l in p.get("plaintext", "").splitlines()
                         if l.strip().startswith("-")]
                related_legacy = lines[:6]
                break
        rel_json = json.dumps(related_legacy, ensure_ascii=False)
        cur.execute(
            "INSERT INTO computation_results("
            "id, input_query, parsed_input, plaintext, pods, category, subcategory, "
            "units, plot_url, related_queries, keywords, required_specifiers, "
            "topic_slug, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (next_cr, q, parsed, plain, pods_json, cat, sub, '',
             plot_url, rel_json, kw, req_spec, slug, ts(i % 96)))
        next_cr += 1
        inserted_cr += 1
    print(f"[r10] inserted {inserted_cr} computation_results")

    # ---- Notebook entries: 600 new ----
    cur.execute("SELECT id FROM notebooks ORDER BY id")
    notebooks = [r[0] for r in cur.fetchall()]
    if notebooks:
        pool = EXTRA_RESULTS[:600]
        for i, row in enumerate(pool):
            q, parsed, plain, cat, sub, kw, pods, slug, plot_url, req_spec = row
            nb_id = notebooks[i % len(notebooks)]
            cur.execute("SELECT COALESCE(MAX(sort_order), -1) FROM notebook_entries WHERE notebook_id=?",
                        (nb_id,))
            so = cur.fetchone()[0] + 1
            note = NOTE_VARIANTS_R10[i % len(NOTE_VARIANTS_R10)] + f" ({cat}/{sub})"
            cur.execute(
                "INSERT INTO notebook_entries(id, notebook_id, query_text, result_summary, "
                "notes, sort_order, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (next_ne, nb_id, q[:500], str(plain)[:200], note, so, ts(i % 96)))
            next_ne += 1
    print(f"[r10] inserted notebook entries up to {next_ne-1}")

    # ---- Topic feedback: 220 new ----
    cur.execute("SELECT id FROM users ORDER BY id")
    user_ids = [r[0] for r in cur.fetchall()]
    cur.execute("SELECT id FROM topics ORDER BY id")
    all_topic_ids = [r[0] for r in cur.fetchall()]
    if user_ids and all_topic_ids:
        for i in range(220):
            uid = user_ids[(i * 13 + 1) % len(user_ids)]
            tid = all_topic_ids[(i * 23 + 5) % len(all_topic_ids)]
            rating = 5 if (i % 7 != 6) else 3 + (i % 3)
            helpful = 1 if rating >= 4 else 0
            comment = FB_COMMENTS_R10[i % len(FB_COMMENTS_R10)]
            cur.execute(
                "INSERT INTO topic_feedback(id, user_id, topic_id, rating, comment, "
                "is_helpful, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (next_fb, uid, tid, rating, comment, helpful, ts(i)))
            next_fb += 1
    print(f"[r10] inserted feedback up to {next_fb-1}")

    # ---- R10 performance indexes (idempotent) ----
    cur.execute("CREATE INDEX IF NOT EXISTS ix_cr_topic_slug "
                "ON computation_results(topic_slug)")
    cur.execute("CREATE INDEX IF NOT EXISTS ix_cr_subcategory "
                "ON computation_results(subcategory)")

    con.commit()

    # Normalize index ordering for byte-identical rebuilds across processes.
    cur.execute(
        "SELECT name, sql FROM sqlite_master WHERE type='index' AND name LIKE 'ix_%'"
    )
    idx_rows = cur.fetchall()
    for name, _ in idx_rows:
        cur.execute(f"DROP INDEX IF EXISTS {name}")
    for name, sql in sorted(idx_rows, key=lambda r: r[0]):
        if sql:
            cur.execute(sql)
    con.commit()
    con.execute("VACUUM")
    con.commit()
    con.close()
    print(f"[r10] built {DST}")


if __name__ == "__main__":
    build()
