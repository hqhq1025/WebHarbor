#!/usr/bin/env python3
"""R7 tasks generator -- appends ~800 cross-page tasks to tasks.jsonl.

Themes (matching R7 goals):
  - SEO-MathSolver-schema             JSON-LD detection on result pages
  - locale-EN/DE/ES/JP                header switcher cookie + variants
  - performance-LCP                   /api/cached/popular + perf pod
  - accessibility-MathML-aria         MathML aria-label exercises
  - WolframLanguage-Code-export-OpenAPI-doc
  - computation-history-takeout       /account/takeout
  - multi-step                        SEO->JSON-LD->locale->takeout chains

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

R7_TASKS = []

# -----------------------------------------------------------------------
# (1) SEO-MathSolver-schema tasks (~120)
# -----------------------------------------------------------------------
SEO_QUERIES = [
    "derivative of x^2 sin(x)",
    "factor 360",
    "convert 100 USD to EUR",
    "molar mass of H2O",
    "orbital period of Mars",
    "is 97 prime",
    "BMI 70 kg 175 cm",
    "C(10,3)",
    "sin(45 degrees)",
    "sum 1 to 100",
    "log_2(64)",
    "pH of 1.00e-04 M HCl",
    "P(X<1.96) for X~N(0,1)",
    "Ohm's law V=12 R=100",
    "kinetic energy m=10 v=20",
]
for q in SEO_QUERIES:
    R7_TASKS.append(f"Compute \"{q}\", then view page source and confirm the <script type=\"application/ld+json\"> MathSolver block is present.")
    R7_TASKS.append(f"After computing \"{q}\", find the 'JSON-LD MathSolver schema' pod and verify the @type field equals MathSolver.")
    R7_TASKS.append(f"After computing \"{q}\", open /og/<id>.svg (the OG share card) and confirm the result text is rendered as SVG.")
    R7_TASKS.append(f"After computing \"{q}\", open the 'SEO snippet' pod and copy the one-line summary for use as the meta-description.")
    R7_TASKS.append(f"From /sitemap.xml, follow the per-category sitemap that contains the result page for \"{q}\".")
    R7_TASKS.append(f"Compute \"{q}\", open the share card image (?as=image), and verify the og:title equals the parsed input.")
    R7_TASKS.append(f"From the result page for \"{q}\", click the SEO snippet pod and verify it ends with a [category/subcategory] tag.")
    R7_TASKS.append(f"Compute \"{q}\" and confirm the JSON-LD includes mainEntity.acceptedAnswer.text.")

# -----------------------------------------------------------------------
# (2) Locale switcher tasks EN/DE/ES/JP (~200)
# -----------------------------------------------------------------------
LOCALES = ['en', 'de', 'es', 'jp']
LOCALE_NAME = {'en': 'English', 'de': 'Deutsch', 'es': 'Espanol', 'jp': 'Nihongo'}
for loc in LOCALES:
    R7_TASKS.append(f"Open /locale/{loc} and verify the page redirects back and sets the locale cookie to '{loc}'.")
    R7_TASKS.append(f"From the homepage header, click the '{LOCALE_NAME[loc]}' locale switcher link.")
    R7_TASKS.append(f"After switching locale to '{loc}', open any result page and find the 'Locale variants' pod for the active locale.")
    R7_TASKS.append(f"In locale '{loc}', verify the header switcher highlights '{LOCALE_NAME[loc]}' as the active locale.")
    R7_TASKS.append(f"Switch the locale cookie to '{loc}', compute \"derivative of x^2\", and verify the 'Locale variants' pod shows the {loc} result line.")
    R7_TASKS.append(f"Visit /locale/{loc}?next=/topic/calculus and confirm you land on the calculus topic page with locale '{loc}' active.")
    R7_TASKS.append(f"In locale '{loc}', open the page source and verify the <html lang> attribute reflects the active locale code.")
    R7_TASKS.append(f"In locale '{loc}', open /sitemap.xml and verify the hreflang= attribute is set on alternate links.")

for loc_a in LOCALES:
    for loc_b in LOCALES:
        if loc_a == loc_b: continue
        R7_TASKS.append(f"Switch locale from '{loc_a}' to '{loc_b}' via the header switcher and verify the locale cookie value changed.")

# -----------------------------------------------------------------------
# (3) Performance / LCP tasks (~80)
# -----------------------------------------------------------------------
LCP_PAGES = [
    '/', '/input?i=derivative+of+x%5E2', '/input?i=factor+360',
    '/examples/mathematics', '/examples/science-and-technology/physics',
    '/topic/calculus', '/topic/algebra', '/widgets', '/products',
    '/pro', '/pro/pricing',
]
for page in LCP_PAGES:
    R7_TASKS.append(f"Open {page} and read the 'Performance LCP hints' pod (or page metric) to identify the LCP budget.")
    R7_TASKS.append(f"From {page}, fetch /api/cached/popular and verify the response is a JSON list of popular queries.")
    R7_TASKS.append(f"On {page}, identify the LCP element by class (e.g. .pod-result-plaintext) using the perf hint pod.")
    R7_TASKS.append(f"Open {page}, then call /api/cached/popular?limit=5 and read the cached popular query strings.")

# -----------------------------------------------------------------------
# (4) Accessibility MathML aria tasks (~80)
# -----------------------------------------------------------------------
MATHML_QUERIES = [
    "fraction 1/2", "sqrt(2)", "x^2", "sum 1..n",
    "integral sin(x) dx", "matrix 2x2",
    "derivative of x^2", "log_2(64)",
    "factor 360", "C(10,3)",
]
for q in MATHML_QUERIES:
    R7_TASKS.append(f"Compute \"aria-label for {q}\" and inspect the 'MathML aria expression' pod for a <math role=math aria-label=...> element.")
    R7_TASKS.append(f"After computing \"aria-label for {q}\", verify the MathML pod uses role=\"math\" and an aria-label attribute.")
    R7_TASKS.append(f"From the MathML aria pod for \"{q}\", verify the screen-reader hint text matches the parsed input.")
    R7_TASKS.append(f"On the result page for \"aria-label for {q}\", confirm the MathML namespace is http://www.w3.org/1998/Math/MathML.")

# -----------------------------------------------------------------------
# (5) Wolfram Language code export / OpenAPI doc (~100)
# -----------------------------------------------------------------------
WL_QUERIES = [
    "solve x^2-4=0", "integrate sin(x)", "plot x^2 -5<x<5",
    "derivative of e^x sin(x)", "factor 360",
    "eigenvalues [[1,2],[3,4]]", "mean {1,2,3,4,5}",
    "stddev {1,2,3,4,5}", "Pi 50 digits", "sqrt 2 30 digits",
]
for q in WL_QUERIES:
    R7_TASKS.append(f"Compute \"{q}\" and click 'Wolfram Language code (OpenAPI)' pod; copy the WL snippet.")
    R7_TASKS.append(f"After computing \"{q}\", open /computation/<id>/wolfram.txt and download the WL code as a plain-text export.")
    R7_TASKS.append(f"After computing \"{q}\", open /computation/<id>/openapi.json and verify the spec has a POST /v1/solve operation.")
    R7_TASKS.append(f"From the OpenAPI doc for \"{q}\", read the request schema for the 'expression' field.")
    R7_TASKS.append(f"Compute \"{q}\", export the WL code, and paste it back into the search bar to verify round-trip.")
    R7_TASKS.append(f"Open the OpenAPI doc for \"{q}\" and verify the response schema includes a 'plaintext' field.")
    R7_TASKS.append(f"Compute \"{q} (variant 1)\" and verify the WL pod renders the same WL expression as the base query.")
    R7_TASKS.append(f"From /computation/<id>/openapi.json for \"{q}\", verify the info.version field is present.")

# -----------------------------------------------------------------------
# (6) Computation history takeout (~60)
# -----------------------------------------------------------------------
R7_TASKS += [
    "Log in as demo@wolframalpha.com, open /account/takeout, and download the JSON archive.",
    "From /account, click the 'Takeout' link and verify the archive contains saved_queries, history, and notebooks keys.",
    "After downloading the takeout archive, count the number of entries under saved_queries.",
    "From the takeout JSON, verify the user object includes email, username, and created_at.",
    "Open /account/takeout?format=json and confirm the Content-Type header is application/json.",
    "Log in as demo@wolframalpha.com and save a query 'factor 360', then re-download the takeout and verify the new entry appears.",
    "On /account, click 'Export computation history' which links to /account/takeout.",
    "After login, open /account/takeout and confirm the schema field equals 'wolfram-takeout-v1'.",
    "Use the takeout JSON to count the user's notebooks and cross-check against /notebooks.",
    "Download the takeout, open it, and verify the history list is sorted newest first.",
]
for u in ['demo@wolframalpha.com', 'student@wolframalpha.com',
          'researcher@wolframalpha.com', 'pro@wolframalpha.com']:
    R7_TASKS.append(f"Log in as {u} and verify /account/takeout returns a complete JSON archive for that user.")

# -----------------------------------------------------------------------
# (7) Multi-step chains (SEO -> i18n -> WL -> takeout) (~100)
# -----------------------------------------------------------------------
CHAIN_QUERIES = [
    "derivative of x^3", "integral of sin(x) cos(x)",
    "convert 50 km to miles", "mortgage $250k 5.5% 30yr",
    "molar mass of NaCl", "is 4093 prime",
    "factor 4096", "P(X<1.96) for X~N(0,1)",
    "sum 1 to 50", "log_10(2.5)",
    "BMI 65 kg 170 cm", "orbital period of Jupiter",
]
for q in CHAIN_QUERIES:
    R7_TASKS.append(f"Multi-step: compute \"{q}\", view the JSON-LD MathSolver pod, switch locale to 'de', re-check the Locale variants pod.")
    R7_TASKS.append(f"Multi-step: compute \"{q}\", open /computation/<id>/wolfram.txt, then add the entry to a notebook.")
    R7_TASKS.append(f"Multi-step: compute \"{q}\", switch locale to 'jp', open the OG card SVG, then download takeout from /account/takeout.")
    R7_TASKS.append(f"Multi-step: navigate via /sitemap/mathematics.xml to \"{q}\", open it, then export the WL code.")
    R7_TASKS.append(f"Multi-step: compute \"{q}\" in locale 'es', verify Locale variants pod, then click 'Add to notebook'.")

# -----------------------------------------------------------------------
# (8) Sitemap navigation tasks (~30)
# -----------------------------------------------------------------------
for cat in ['mathematics', 'science-and-technology', 'society-and-culture', 'everyday-life']:
    R7_TASKS.append(f"Open /sitemap/{cat}.xml and count the number of <url> entries listed.")
    R7_TASKS.append(f"From /sitemap.xml, follow the link to /sitemap/{cat}.xml and verify the loc fields start with /topic/.")
    R7_TASKS.append(f"On /sitemap/{cat}.xml, verify each <url> has a <lastmod> and <changefreq> field.")
    R7_TASKS.append(f"On /sitemap.xml, verify there is a <sitemap> entry for the '{cat}' category.")

# -----------------------------------------------------------------------
# (9) New R7 topic page navigation (~25)
# -----------------------------------------------------------------------
R7_TOPICS = [
    'structured-data-seo', 'locale-aware-interfaces',
    'computation-history-takeout', 'math-accessibility',
]
for t in R7_TOPICS:
    R7_TASKS.append(f"Navigate to /topic/{t} and view the topic description.")
    R7_TASKS.append(f"On /topic/{t}, click the first example query to land on the result page.")
    R7_TASKS.append(f"From /topic/{t}, follow the breadcrumb back to the category index.")
    R7_TASKS.append(f"On /topic/{t}, find the rating widget and submit a 5-star rating with comment.")
    R7_TASKS.append(f"From /topic/{t}, click 'Favorite' (logged in) and confirm it appears in /favorites.")

# -----------------------------------------------------------------------
# (10) New R7 fillers (broad coverage of new comp results) (~150)
# -----------------------------------------------------------------------
for cur_pair in [('USD','EUR'), ('USD','JPY'), ('USD','GBP'), ('EUR','USD'),
                 ('EUR','JPY'), ('GBP','USD'), ('CNY','USD'), ('JPY','USD'),
                 ('INR','USD'), ('AUD','USD'), ('CAD','USD'), ('CHF','USD')]:
    for amt in [1, 100, 1000]:
        R7_TASKS.append(f"Type \"convert {amt} {cur_pair[0]} to {cur_pair[1]}\" and read the converted amount.")
for n in [73, 89, 97, 101, 257, 401, 619, 911, 1009, 1597, 2003, 2521,
          3163, 3457, 1024, 360, 2048, 4096, 60, 720, 5040, 999]:
    R7_TASKS.append(f"Type \"is {n} prime\" and verify the prime/composite verdict.")
    R7_TASKS.append(f"Type \"factor {n}\" and read the prime factorization.")
for body in ['Mercury', 'Venus', 'Earth', 'Mars', 'Jupiter', 'Saturn',
             'Uranus', 'Neptune', 'Pluto', 'Moon', 'Titan']:
    R7_TASKS.append(f"Type \"orbital period of {body}\" and read the result.")
    R7_TASKS.append(f"Type \"escape velocity of {body}\" and read the result.")
for sym in ['H2O', 'CO2', 'NaCl', 'CH4', 'NH3', 'H2SO4', 'HCl', 'NaOH',
            'KOH', 'CaCO3', 'Fe2O3', 'KMnO4']:
    R7_TASKS.append(f"Type \"molar mass of {sym}\" and read the result.")
    R7_TASKS.append(f"Type \"moles in 100 g of {sym}\" and read the result.")

# -----------------------------------------------------------------------
# (11) Extra R7 fillers covering compound/quadratic/binary/tip/limits/cooling/roman (~300)
# -----------------------------------------------------------------------
for P in [1000, 5000, 10000, 50000]:
    for r in [3.0, 5.0, 7.0]:
        for n in [5, 10, 20, 30]:
            R7_TASKS.append(f"Type \"compound interest ${P} {r}% {n}y\" and read the final amount.")
for a in [1, 2, 3]:
    for b in [-5, -2, 0, 3, 5]:
        for c in [-4, -1, 2, 4]:
            R7_TASKS.append(f"Type \"solve {a}x^2 + {b}x + {c} = 0\" and read both roots.")
            if len([t for t in R7_TASKS if t.startswith('Type \"solve')]) >= 80:
                break
        if len([t for t in R7_TASKS if t.startswith('Type \"solve')]) >= 80:
            break
    if len([t for t in R7_TASKS if t.startswith('Type \"solve')]) >= 80:
        break
for n in [10, 25, 50, 100, 128, 256, 500, 999]:
    R7_TASKS.append(f"Type \"{n} to binary\" and read the binary representation.")
    R7_TASKS.append(f"Type \"{n} to hex\" and read the hex representation.")
    R7_TASKS.append(f"Type \"{n} to octal\" and read the octal representation.")
for bill in [25, 50, 100]:
    for pct in [15, 18, 20]:
        for ppl in [2, 3, 4, 5]:
            R7_TASKS.append(f"Type \"tip {pct}% on ${bill} split {ppl} ways\" and read per-person total.")
for q in [
    "limit of sin(x)/x as x->0",
    "limit of (1-cos(x))/x^2 as x->0",
    "limit of (1+1/n)^n as n->infinity",
    "limit of ln(x)/x as x->infinity",
    "limit of (x^2-1)/(x-1) as x->1",
]:
    R7_TASKS.append(f"Type \"{q} (variant 1)\" and read the limit value.")
    R7_TASKS.append(f"Type \"{q} (variant 5)\" and read the limit value.")
for T_env, T0, k, t in [(20, 80, 0.05, 10), (25, 100, 0.1, 30), (15, 60, 0.01, 60)]:
    R7_TASKS.append(f"Type \"Newton cooling T_env={T_env} T0={T0} k={k} t={t}\" and read the temperature.")
for n in [4, 9, 14, 19, 24, 49, 99]:
    R7_TASKS.append(f"Type \"{n} in Roman numerals\" and read the numeral string.")

# -----------------------------------------------------------------------
# (12) Locale-aware SEO + takeout combo tasks (~80)
# -----------------------------------------------------------------------
for loc in LOCALES:
    for q in ["derivative of x^2", "factor 360", "molar mass of H2O",
              "orbital period of Mars"]:
        R7_TASKS.append(f"In locale '{loc}', compute \"{q}\" and verify the meta-description tag is set from the SEO snippet pod.")
        R7_TASKS.append(f"In locale '{loc}', compute \"{q}\", then open /og/<id>.svg and confirm the share card renders.")
        R7_TASKS.append(f"In locale '{loc}', open /sitemap/{('mathematics' if 'derivative' in q or 'factor' in q else 'science-and-technology')}.xml and find a <url> for \"{q}\".")
        R7_TASKS.append(f"In locale '{loc}', after computing \"{q}\", download /account/takeout (logged in) and verify the entry is in history.")

# -----------------------------------------------------------------------
# (13) New R7 topic feedback / saved-query tasks (~30)
# -----------------------------------------------------------------------
for t in ['structured-data-seo', 'locale-aware-interfaces',
          'computation-history-takeout', 'math-accessibility']:
    for verb in ['save', 'favorite', 'rate 5 stars on', 'comment on']:
        R7_TASKS.append(f"Logged in, {verb} the /topic/{t} page and verify the action persists in /account.")

# Emit
with open(TASKS_PATH, 'a') as out:
    emitted = 0
    for q_text in R7_TASKS:
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
print(f"[r7 tasks] emitted {emitted}; pool size {len(R7_TASKS)}")
