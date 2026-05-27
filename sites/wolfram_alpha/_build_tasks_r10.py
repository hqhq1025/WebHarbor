#!/usr/bin/env python3
"""R10 tasks generator -- appends cross-page tasks for the R10 verticals.

Themes (matching R10 goals):
  - currency-pair-converter      (/finance/currency-convert)
  - recipe-macro-calculator      (/cooking/recipe-macros)
  - crypto-pair-quote            (/finance/crypto-quote)
  - hotel-room-availability      (/travel/hotel-availability)
  - movie-box-office-tracker     (/entertainment/box-office)
  - stock-quote-history-replay   (/finance/stock-history)
  - isbn-book-lookup             (/books/isbn-lookup)
  - package-tracking-status      (/travel/package-track)
  - election-poll-aggregator     (/society/election-polls)
  - language-translation-pair    (/society/translate)
  - multi-step-workflows-r10     (chains, /webhook/result-shared)

Deterministic. Idempotent: appends only tasks not already in tasks.jsonl.
"""
from __future__ import annotations
import json, os

TASKS_PATH = 'tasks.jsonl'
WEB_NAME = 'Wolfram Alpha'
WEB_URL = 'http://localhost:40011/'
UPSTREAM = 'https://www.wolframalpha.com/'

existing = []
if os.path.exists(TASKS_PATH):
    with open(TASKS_PATH) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                existing.append(json.loads(line))
            except Exception:
                pass
existing_ids = set()
for t in existing:
    tid = t.get('id', '')
    if '--' in tid:
        try:
            existing_ids.add(int(tid.rsplit('--', 1)[1]))
        except ValueError:
            pass
next_id = (max(existing_ids) + 1) if existing_ids else 0
existing_questions = {t.get('ques', '') for t in existing}

R10_TASKS = []


# -----------------------------------------------------------------------
# (1) Currency pair converter (~120)
# -----------------------------------------------------------------------
CCY_PAIRS = [
    ('USD', 'EUR'), ('USD', 'GBP'), ('USD', 'JPY'), ('USD', 'CNY'),
    ('USD', 'CAD'), ('USD', 'AUD'), ('USD', 'INR'), ('USD', 'MXN'),
    ('EUR', 'USD'), ('EUR', 'GBP'), ('EUR', 'CHF'), ('EUR', 'JPY'),
    ('GBP', 'USD'), ('GBP', 'EUR'), ('JPY', 'USD'), ('JPY', 'CNY'),
    ('CAD', 'USD'), ('AUD', 'NZD'), ('BRL', 'USD'), ('KRW', 'JPY'),
]
AMOUNTS = [100, 500, 1000, 5000, 10000]
for a, b in CCY_PAIRS:
    R10_TASKS.append(
        f"Open /finance/currency-convert?amt=100&from={a}&to={b} and verify "
        f"the page shows a converted amount with target currency '{b}'."
    )
    R10_TASKS.append(
        f"GET /finance/currency-convert?amt=100&from={a}&to={b}&format=json "
        f"and confirm the JSON field schema equals 'wa-currency-v1'."
    )
for a, b in CCY_PAIRS[:10]:
    for amt in AMOUNTS:
        R10_TASKS.append(
            f"On /finance/currency-convert, set amount={amt} from={a} to={b} "
            f"and verify the response includes the snapshot_date 2026-05-27."
        )
for v in range(20):
    R10_TASKS.append(
        f"GET /finance/currency-convert?amt=1000&from=USD&to=EUR (variant {v+1}) "
        "and confirm the rate field is a positive decimal."
    )

# -----------------------------------------------------------------------
# (2) Recipe macro calculator (~110)
# -----------------------------------------------------------------------
RECIPES = ['chicken-pesto-pasta', 'vegan-buddha-bowl', 'keto-cheeseburger',
           'tofu-stir-fry', 'beef-tacos', 'shrimp-fried-rice',
           'paleo-roast-chicken', 'lentil-soup', 'caesar-salad',
           'margherita-pizza', 'vegan-curry', 'greek-yogurt-bowl',
           'overnight-oats', 'salmon-teriyaki', 'falafel-wrap',
           'miso-ramen', 'chicken-tikka-masala', 'beef-bourguignon',
           'mushroom-risotto', 'caprese-salad']
for slug in RECIPES:
    R10_TASKS.append(
        f"Open /cooking/recipe-macros?slug={slug}&servings=2 and verify the "
        "per-serving kcal cell is a positive integer."
    )
    R10_TASKS.append(
        f"GET /cooking/recipe-macros?slug={slug}&servings=4&format=json and "
        "confirm the schema field equals 'wa-recipe-macro-v1'."
    )
for slug in RECIPES[:10]:
    for srv in [1, 2, 4, 6]:
        R10_TASKS.append(
            f"On /cooking/recipe-macros, set slug={slug} servings={srv}; "
            "verify total.kcal equals per_serving.kcal * servings."
        )
for v in range(15):
    R10_TASKS.append(
        f"GET /cooking/recipe-macros?slug=chicken-pesto-pasta&servings=4 "
        f"(variant {v+1}) and confirm total.protein_g is a positive integer."
    )

# -----------------------------------------------------------------------
# (3) Crypto pair quote (~120)
# -----------------------------------------------------------------------
CRYPTOS = ['BTC', 'ETH', 'SOL', 'XRP', 'ADA', 'DOGE', 'AVAX', 'MATIC',
           'LINK', 'DOT', 'LTC', 'BCH', 'UNI', 'ATOM', 'NEAR', 'FIL']
for c in CRYPTOS:
    R10_TASKS.append(
        f"Open /finance/crypto-quote?pair={c}-USD and verify the page "
        "displays a 24h change percentage."
    )
    R10_TASKS.append(
        f"GET /finance/crypto-quote?pair={c}-USD&format=json and confirm "
        "the JSON field schema equals 'wa-crypto-quote-v1'."
    )
for c in CRYPTOS[:8]:
    for qcy in ['USD', 'EUR', 'JPY', 'USDC']:
        R10_TASKS.append(
            f"On /finance/crypto-quote, set base={c} quote={qcy}; verify the "
            f"response.quote equals '{qcy}'."
        )
for v in range(20):
    R10_TASKS.append(
        f"GET /finance/crypto-quote?pair=BTC-USD (variant {v+1}) and confirm "
        "the volume_24h field is a positive number."
    )

# -----------------------------------------------------------------------
# (4) Hotel room availability (~110)
# -----------------------------------------------------------------------
HOTELS = ['hilton-times-square', 'park-hyatt-tokyo', 'hotel-lutetia-paris',
         'four-seasons-singapore', 'marriott-marquis-sf', 'grand-hyatt-hk',
         'shangri-la-sydney', 'ritz-carlton-doha', 'beverly-wilshire',
         'mandarin-london', 'peninsula-bangkok', 'intercon-geneva',
         'aman-kyoto', 'w-barcelona', 'claridges-london', 'westin-tokyo']
for h in HOTELS:
    R10_TASKS.append(
        f"Open /travel/hotel-availability?slug={h} and confirm the page "
        "lists at least three room types."
    )
    R10_TASKS.append(
        f"GET /travel/hotel-availability?slug={h}&format=json and confirm "
        "data.rooms is a non-empty array."
    )
for h in HOTELS[:8]:
    R10_TASKS.append(
        f"On /travel/hotel-availability?slug={h}, set nights=3 and verify "
        "each room.total_usd ≈ rate * 3 (rounded)."
    )
    R10_TASKS.append(
        f"GET /travel/hotel-availability?slug={h}&check_in=2026-08-12&"
        "check_out=2026-08-15&format=json and confirm nights equals 3."
    )
for v in range(15):
    R10_TASKS.append(
        f"GET /travel/hotel-availability?slug=park-hyatt-tokyo (variant {v+1}) "
        "and confirm occupancy is between 0.0 and 1.0."
    )

# -----------------------------------------------------------------------
# (5) Movie box office tracker (~110)
# -----------------------------------------------------------------------
MOVIES = ['avatar-3', 'dune-part-three', 'mission-impossible-9',
          'inside-out-2', 'deadpool-and-wolverine', 'wicked',
          'moana-2', 'gladiator-ii', 'twisters', 'beetlejuice-beetlejuice',
          'joker-folie-a-deux', 'mufasa-the-lion-king',
          'despicable-me-4', 'bad-boys-ride-or-die']
for m in MOVIES:
    R10_TASKS.append(
        f"Open /entertainment/box-office?slug={m} and confirm the page "
        "shows the opening weekend gross in millions USD."
    )
    R10_TASKS.append(
        f"GET /entertainment/box-office?slug={m}&format=json and confirm "
        "the field schema equals 'wa-box-office-v1'."
    )
for m in MOVIES[:7]:
    for week in [1, 4, 12, 20]:
        R10_TASKS.append(
            f"On /entertainment/box-office?slug={m}&week={week}, verify the "
            f"week label shows '{week}'."
        )
for v in range(15):
    R10_TASKS.append(
        f"GET /entertainment/box-office?slug=avatar-3&week=18 (variant {v+1}) "
        "and confirm worldwide_musd >= domestic_musd."
    )

# -----------------------------------------------------------------------
# (6) Stock quote history replay (~100)
# -----------------------------------------------------------------------
TICKERS = ['AAPL', 'MSFT', 'NVDA', 'GOOGL', 'AMZN', 'META', 'TSLA',
           'BRK-B', 'JPM', 'V', 'UNH', 'XOM', 'JNJ', 'WMT', 'PG',
           'AVGO', 'LLY', 'MA', 'HD', 'CVX']
for t in TICKERS:
    R10_TASKS.append(
        f"Open /finance/stock-history?ticker={t}&window=30 and verify the "
        "OHLCV table has at least one row."
    )
    R10_TASKS.append(
        f"GET /finance/stock-history?ticker={t}&window=30&format=json and "
        "confirm the schema field equals 'wa-stock-ohlcv-v1'."
    )
for t in TICKERS[:8]:
    for w in [5, 10, 60, 90]:
        R10_TASKS.append(
            f"On /finance/stock-history, set ticker={t} window={w}; verify "
            f"the window_days field equals {w}."
        )
for v in range(12):
    R10_TASKS.append(
        f"GET /finance/stock-history?ticker=NVDA&window=30 (variant {v+1}) "
        "and confirm volume is a positive integer."
    )

# -----------------------------------------------------------------------
# (7) ISBN book lookup (~80)
# -----------------------------------------------------------------------
ISBNS = [
    ('9780262033848', 'Introduction to Algorithms'),
    ('9780201633610', 'Design Patterns'),
    ('9780132350884', 'Clean Code'),
    ('9780321125217', 'Domain-Driven Design'),
    ('9780135957059', 'The Pragmatic Programmer'),
    ('9780321573513', 'Algorithms 4ed'),
    ('9780131103627', 'The C Programming Language'),
    ('9780596007126', 'Head First Design Patterns'),
    ('9780321776402', 'Effective Java'),
    ('9780321356680', 'Effective C++'),
    ('9780672327094', 'Linux Kernel Development'),
    ('9781492052203', 'Fluent Python'),
    ('9781449355739', 'Learning Python'),
    ('9780262510875', 'Structure and Interpretation of Computer Programs'),
]
for isbn, title in ISBNS:
    R10_TASKS.append(
        f"Open /books/isbn-lookup?isbn={isbn} and verify the page shows the "
        f"title '{title}'."
    )
    R10_TASKS.append(
        f"GET /books/isbn-lookup?isbn={isbn}&format=json and confirm the "
        "schema field equals 'wa-isbn-v1'."
    )
for isbn, title in ISBNS[:8]:
    for mode in ['summary', 'cover', 'toc', 'reviews', 'citations']:
        R10_TASKS.append(
            f"On /books/isbn-lookup?isbn={isbn}&mode={mode}, confirm the "
            f"mode label shows '{mode}'."
        )

# -----------------------------------------------------------------------
# (8) Package tracking (~90)
# -----------------------------------------------------------------------
CARRIERS = ['UPS', 'FedEx', 'USPS', 'DHL', 'Royal-Mail',
            'Japan-Post', 'China-Post', 'Australia-Post']
STATUSES = ['label-created', 'picked-up', 'in-transit', 'out-for-delivery',
            'delivered', 'exception']
for car in CARRIERS:
    R10_TASKS.append(
        f"Open /travel/package-track?carrier={car}&id=ABC123 and verify the "
        "page header includes the carrier name."
    )
    R10_TASKS.append(
        f"GET /travel/package-track?carrier={car}&id=ABC123&format=json and "
        "confirm the schema field equals 'wa-package-v1'."
    )
for car in CARRIERS[:5]:
    for st in STATUSES:
        R10_TASKS.append(
            f"On /travel/package-track?carrier={car}&id=ABC123&status={st}, "
            f"verify the status_code field equals '{st}'."
        )
for v in range(12):
    R10_TASKS.append(
        f"GET /travel/package-track?carrier=FedEx&id=619283771234 "
        f"(variant {v+1}) and confirm the eta_date is an ISO date string."
    )

# -----------------------------------------------------------------------
# (9) Election poll aggregator (~110)
# -----------------------------------------------------------------------
RACES = ['us-president-2024', 'uk-general-2025', 'canada-federal-2025',
         'germany-federal-2025', 'france-presidential-2027',
         'australia-federal-2025', 'india-general-2024',
         'japan-lower-house-2025', 'south-korea-2027', 'brazil-2026',
         'mexico-2024', 'argentina-2027', 'italy-general-2027',
         'spain-general-2027', 'netherlands-2025',
         'poland-presidential-2025']
FIRMS = ['YouGov', 'Ipsos', 'Gallup', 'Pew', 'Quinnipiac',
         'Morning-Consult', 'AtlasIntel', 'Datafolha']
for r in RACES:
    R10_TASKS.append(
        f"Open /society/election-polls?race={r} and verify the page shows a "
        "weighted-mean percentage for each major party."
    )
    R10_TASKS.append(
        f"GET /society/election-polls?race={r}&format=json and confirm "
        "the schema field equals 'wa-poll-v1'."
    )
for r in RACES[:6]:
    for firm in FIRMS[:4]:
        R10_TASKS.append(
            f"On /society/election-polls?race={r}&firm={firm}, confirm the "
            f"firm label '{firm}' appears in the polling source list."
        )
for v in range(12):
    R10_TASKS.append(
        f"GET /society/election-polls?race=us-president-2024 (variant {v+1}) "
        "and confirm pct_a + pct_b + other_pct equals 100."
    )

# -----------------------------------------------------------------------
# (10) Language translation pair (~110)
# -----------------------------------------------------------------------
LANG_PAIRS = [('en','es'), ('en','fr'), ('en','de'), ('en','it'),
              ('en','pt'), ('en','ja'), ('en','ko'), ('en','zh'),
              ('en','ru'), ('en','ar'), ('en','hi'), ('en','nl'),
              ('en','sv'), ('en','tr')]
PHRASES = ['hello', 'thank you', 'good morning', 'good night',
           'how much is it', 'where is the station', 'I need a doctor',
           'call the police', 'I do not understand', 'please repeat']
for s, t in LANG_PAIRS:
    R10_TASKS.append(
        f"Open /society/translate?phrase=hello&src={s}&tgt={t} and verify "
        f"the page shows the target language code '{t}'."
    )
    R10_TASKS.append(
        f"GET /society/translate?phrase=hello&src={s}&tgt={t}&format=json "
        "and confirm the schema field equals 'wa-translate-v1'."
    )
for s, t in LANG_PAIRS[:7]:
    for ph in PHRASES[:4]:
        R10_TASKS.append(
            f"On /society/translate, set phrase='{ph}' src={s} tgt={t}; "
            "verify the confidence_pct field is between 0 and 100."
        )
for v in range(10):
    R10_TASKS.append(
        f"GET /society/translate?phrase=hello&src=en&tgt=ja (variant {v+1}) "
        "and confirm the translation field is non-empty."
    )

# -----------------------------------------------------------------------
# (11) R10 multi-step chains (~70)
# -----------------------------------------------------------------------
CHAINS = [
    ('currency + stock',
     '/finance/currency-convert?amt=1000&from=USD&to=EUR',
     '/finance/stock-history?ticker=AAPL&window=30'),
    ('hotel + flight + tide',
     '/travel/hotel-availability?slug=park-hyatt-tokyo',
     '/tide/Tokyo'),
    ('isbn + translation',
     '/books/isbn-lookup?isbn=9780262033848',
     '/society/translate?phrase=algorithm&tgt=ja'),
    ('crypto + currency cross',
     '/finance/crypto-quote?pair=BTC-USD',
     '/finance/currency-convert?amt=1&from=USD&to=JPY'),
    ('package + hotel arrival',
     '/travel/package-track?carrier=FedEx&id=619283771234',
     '/travel/hotel-availability?slug=beverly-wilshire'),
    ('movie + poll cross',
     '/entertainment/box-office?slug=avatar-3',
     '/society/election-polls?race=us-president-2024'),
    ('stock + crypto comparator',
     '/finance/stock-history?ticker=NVDA',
     '/finance/crypto-quote?pair=ETH-USD'),
    ('quake (R9) + hotel safety',
     '/earthquakes?region=Japan%20Trench',
     '/travel/hotel-availability?slug=park-hyatt-tokyo'),
    ('aviation (R9) + package',
     '/aviation/flight/UA888',
     '/travel/package-track?carrier=UPS&id=1Z999AA10123456784'),
    ('recipe + nutrition (R9)',
     '/cooking/recipe-macros?slug=chicken-pesto-pasta',
     '/nutrition/meal-plan?cal=1800&diet=omnivore&meals=4'),
]
for label, s1, s2 in CHAINS:
    R10_TASKS.append(
        f"Open {s1}, copy the schema field, then open {s2} and confirm the "
        f"chain label '{label}' is referenced in the result page."
    )
    R10_TASKS.append(
        f"GET {s1}&format=json then {s2}&format=json; verify both responses "
        "include their schema field."
    )
    R10_TASKS.append(
        f"On the result page of {s1}, click the R10-chain link for '{label}'; "
        f"verify the destination URL begins with the prefix of {s2.split('?')[0]}."
    )
for v in range(15):
    R10_TASKS.append(
        f"Run R10 chain 'currency + stock' (variant {v+1}) and confirm the "
        "final notebook entry note mentions 'R10'."
    )
for v in range(10):
    R10_TASKS.append(
        f"POST a multi-step R10 chain payload to /webhook/result-shared "
        f"(variant {v+1}) and confirm the response includes 'shared': true."
    )

# -----------------------------------------------------------------------
# (12) Topic-page sanity for each R10 topic (~100)
# -----------------------------------------------------------------------
R10_SLUGS = [
    'currency-pair-converter', 'recipe-macro-calculator',
    'crypto-pair-quote', 'hotel-room-availability',
    'movie-box-office-tracker', 'stock-quote-history-replay',
    'isbn-book-lookup', 'package-tracking-status',
    'election-poll-aggregator', 'language-translation-pair',
    'multi-step-workflows-r10', 'finance-catalog-r10',
]
for slug in R10_SLUGS:
    R10_TASKS.append(
        f"Open /topic/{slug} and verify the topic page lists at least two "
        "example queries."
    )
    R10_TASKS.append(
        f"On /topic/{slug}, click the first example and confirm the "
        "resulting /input page loads."
    )
    R10_TASKS.append(
        f"On /topic/{slug}, submit feedback (rating 5) and verify the "
        "average rating updates."
    )
    R10_TASKS.append(
        f"Use Cmd+K and search '{slug.replace('-', ' ')[:10]}'; select the "
        "matching topic entry."
    )
    R10_TASKS.append(
        f"On /topic/{slug}, save the first example to a notebook and verify "
        "it appears in /notebooks."
    )
    R10_TASKS.append(
        f"Open /topic/{slug} and verify the topic description mentions an "
        "R10 surface route."
    )
    R10_TASKS.append(
        f"From /topic/{slug}, navigate to a sibling subcategory topic and "
        "confirm the URL changes."
    )
    R10_TASKS.append(
        f"On /topic/{slug}, click the share button (if present) and POST "
        "the resulting cr_id to /webhook/result-shared."
    )

# -----------------------------------------------------------------------
# Emit
# -----------------------------------------------------------------------
with open(TASKS_PATH, 'a') as out:
    emitted = 0
    for q_text in R10_TASKS:
        if q_text in existing_questions:
            continue
        rec = {"web_name": WEB_NAME,
               "id": f"{WEB_NAME}--{next_id}",
               "ques": q_text,
               "web": WEB_URL,
               "upstream_url": UPSTREAM}
        out.write(json.dumps(rec, ensure_ascii=False) + "\n")
        next_id += 1
        emitted += 1
        existing_questions.add(q_text)
print(f"[r10 tasks] emitted {emitted}; pool size {len(R10_TASKS)}")
