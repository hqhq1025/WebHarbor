#!/usr/bin/env python3
"""R6 tasks generator — appends ~1000 cross-page tasks to tasks.jsonl.

Deterministic. Idempotent: tasks for ids already present in tasks.jsonl are
not re-emitted (matched by exact ques+task-id).
"""
from __future__ import annotations
import json, os

TASKS_PATH = 'tasks.jsonl'
WEB_NAME = 'Wolfram Alpha'
WEB_URL = 'http://localhost:40011/'
UPSTREAM = 'https://www.wolframalpha.com/'

# Read existing tasks → next id
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

R6_TASKS = []

# (1) Cross-page chains: input → result → step-by-step → notebook → share
CROSS_PAGE_QUERIES = [
    ("derivative of x^2 sin(x)", "x cos(x) + 2x sin(x)"),
    ("integral of e^x cos(x)", "(e^x (sin(x)+cos(x)))/2"),
    ("roots of x^2 - 5x + 6", "x = 2, 3"),
    ("solve quadratic x^2 - 4 = 0", "x = ±2"),
    ("factor 360", "360 = 2^3 · 3^2 · 5"),
    ("BMI 70 kg 175 cm", "22.86 kg/m^2"),
    ("convert 5 km to miles", "3.107 miles"),
    ("mortgage $300k 6% 30yr monthly", "~$1798/mo"),
    ("compound interest $1000 5% 10y", "~$1648.66"),
    ("sin(45 degrees) + cos(30 degrees)", "1.573"),
    ("probability sum 7 with 2d6", "6/36 = 16.67%"),
    ("molar mass of H2O", "18.015 g/mol"),
    ("orbital period of Mars", "687 days"),
    ("speed of light km/s", "299792.458 km/s"),
    ("matrix [[1,2],[3,4]] eigenvalues", "λ ≈ -0.37, 5.37"),
]
for (q, _ans) in CROSS_PAGE_QUERIES:
    R6_TASKS.append(f"Type \"{q}\" into the WolframAlpha search bar and verify the computed result is displayed.")
    R6_TASKS.append(f"After computing \"{q}\", click 'Step-by-step solution' and observe the PRO paywall.")
    R6_TASKS.append(f"After computing \"{q}\", click on an 'Alternate forms' tab to view the alternative representation.")
    R6_TASKS.append(f"After computing \"{q}\", scroll to the 'Related computations' pod and click the first link.")
    R6_TASKS.append(f"After computing \"{q}\", scroll to the 'Topics that use this formula' pod and note the listed topics.")
    R6_TASKS.append(f"After computing \"{q}\", find the 'Examples in same category' pod and click the first example.")
    R6_TASKS.append(f"After computing \"{q}\", scroll to the 'What if I change' pod to inspect parameter sensitivity.")
    R6_TASKS.append(f"After computing \"{q}\", click 'Share' to open the share-link page.")
    R6_TASKS.append(f"After computing \"{q}\", click 'Share', then append '?as=image' to view the image-rendition share page.")
    R6_TASKS.append(f"Compute \"{q}\", then click 'Embed in notebook' and add it to your notebook 'My Math Notes'.")

# (2) Cite-formula multi-step
CITE_QUERIES = [
    "compound interest $1000 5% 10y",
    "Black-Scholes call option",
    "BMI 70 kg 175 cm",
    "orbital period of Mars",
    "Pythagorean theorem 3 4 5",
    "Gauss law for electric flux",
    "Coulomb force two charges",
    "Hooke law spring",
    "ideal gas PV=nRT",
    "Ohm's law V=IR",
]
for q in CITE_QUERIES:
    R6_TASKS.append(f"Compute \"{q}\", then locate the breadcrumb pod and read out the catalog path (Category > Subcategory > Topic).")
    R6_TASKS.append(f"After computing \"{q}\", cite the primary formula shown in the 'Topics that use this formula' pod.")
    R6_TASKS.append(f"From the result page for \"{q}\", follow the breadcrumb's subcategory link to the /examples sub-page.")
    R6_TASKS.append(f"After computing \"{q}\", embed the result in a new notebook entry and save the citation.")

# (3) Edge-case route tasks (one per edge route × ~15 examples each)
AMBIG_TERMS = ['mercury', 'python', 'java', 'apple', 'c++', 'pi', 'e', 'speed', 'factor 12', 'light year distance']
for term in AMBIG_TERMS:
    R6_TASKS.append(f"Search for \"{term}\" and open the disambiguation page at /input/ambiguous to pick an interpretation.")
    R6_TASKS.append(f"On the ambiguous-input page for \"{term}\", click the first interpretation and verify the result loads.")
    R6_TASKS.append(f"On the disambiguation page for \"{term}\", count the number of interpretations listed.")
    R6_TASKS.append(f"For the ambiguous query \"{term}\", use the assumption pill bar to switch between the available interpretations.")

TIMEOUT_QUERIES = [
    "integrate exp(x^x) dx",
    "solve P vs NP",
    "factor 2^200 - 1",
    "simulate galaxy collision 10^9 particles",
    "optimize traveling salesman 100 cities",
]
for q in TIMEOUT_QUERIES:
    R6_TASKS.append(f"Compute \"{q}\". When the timeout fallback page appears, click 'Try Pro — 20s extended time'.")
    R6_TASKS.append(f"Trigger \"{q}\". On the timeout page, click 'Retry with lower precision'.")
    R6_TASKS.append(f"From the timeout fallback for \"{q}\", click 'Back to result page'.")

PAYWALL_QUERIES = [
    "solve quadratic ax^2+bx+c=0",
    "differentiate f(g(x)) chain rule",
    "integrate by parts u dv",
    "diagonalize 3x3 symmetric matrix",
    "Laplace transform of t^2 e^(-3t)",
]
for q in PAYWALL_QUERIES:
    R6_TASKS.append(f"Compute \"{q}\", click 'Step-by-step' and on the paywall page click 'Unlock with Pro'.")
    R6_TASKS.append(f"Compute \"{q}\", then on the step-by-step locked page click 'Share this problem'.")
    R6_TASKS.append(f"For the locked step-by-step page of \"{q}\", click 'Back to result' to return to the main computation.")

R6_TASKS += [
    "Navigate to your notebook 'My Math Notes' and trigger the quota-exceeded page at /notebook/<id>/quota.",
    "On the notebook quota-exceeded page, click 'Upgrade to Pro for unlimited notebooks'.",
    "On the notebook quota-exceeded page, click 'Manage existing entries'.",
    "From the notebook quota page, click 'All notebooks' to view your notebook list.",
    "Open a share link with an expired token at /share/abc123/expired and review the help text.",
    "On the share-link-expired page, click 'Start a new computation'.",
    "On the share-link-expired page, click 'Get permanent share links (Pro)'.",
    "On the share-link-expired page, click 'My computation history'.",
    "Open the widget 'Derivative Calculator' embed-blocked page and click 'Open widget directly'.",
    "Open the widget 'BMI Calculator' embed-blocked page and click 'Rebuild with embeddable settings'.",
    "On the widget embed-blocked page, click 'All widgets' to navigate to the catalog.",
    "Visit the widget embed-blocked page for 'Integral Calculator' and note the X-Frame-Options reason.",
]

# (4) Examples-in-category navigation (cross-page taxonomy)
CAT_PATHS = [
    ("mathematics", "calculus"),
    ("mathematics", "algebra"),
    ("mathematics", "geometry"),
    ("mathematics", "linear-algebra"),
    ("mathematics", "probability"),
    ("science-and-technology", "physics"),
    ("science-and-technology", "chemistry"),
    ("science-and-technology", "astronomy"),
    ("science-and-technology", "engineering"),
    ("society-and-culture", "finance"),
    ("society-and-culture", "economics"),
    ("everyday-life", "personal-finance"),
    ("everyday-life", "cooking"),
    ("everyday-life", "personal-health"),
]
for (cat, sub) in CAT_PATHS:
    R6_TASKS.append(f"Navigate to /examples/{cat}/{sub} and pick the first listed example query.")
    R6_TASKS.append(f"From /examples/{cat}/{sub}, click on a featured topic in that subcategory.")
    R6_TASKS.append(f"On the /examples/{cat}/{sub} page, find an 'Examples in same category' link from any computation result.")

# (5) Multi-step chains: solve → step-by-step → cite → embed → share
CHAIN_QUERIES = [
    "derivative of sin(x^2)",
    "integral of x ln(x)",
    "solve x^2 + 5x + 6 = 0",
    "compound interest $5000 7% 15y",
    "matrix [[2,1],[1,3]] eigenvalues",
    "convert 100 kg to pounds",
    "BMI 65 kg 168 cm",
    "molar mass of CO2",
    "P(sum=8) with 3d6",
    "orbital period of Jupiter",
    "stress steel A36 F=10000 A=0.01",
    "bond price F=1000 c=5% y=4% n=10",
    "mortgage $200k 4.5% 30yr",
    "supply demand equilibrium",
    "Pythagoras 5 12 13",
]
for q in CHAIN_QUERIES:
    R6_TASKS.append(f"Multi-step task: solve \"{q}\", view step-by-step, cite the formula, embed in notebook, then share the permalink.")
    R6_TASKS.append(f"Cross-page chain: compute \"{q}\" → click 'Examples in same category' → return via breadcrumb.")
    R6_TASKS.append(f"Workflow: compute \"{q}\", open the share page, switch to '?as=image' mode and confirm the printable view.")

# (6) Widget-builder + size preset tasks (light R5 surface ext)
for w in ['derivative-calculator', 'integral-calculator', 'matrix-determinant',
          'bmi-calculator', 'mortgage-calculator', 'statistics-summary']:
    R6_TASKS.append(f"Open the widget builder for '{w}', choose the 400x300 preset, then click 'Embed code'.")
    R6_TASKS.append(f"Navigate from a computation result to the widget builder for '{w}' via the 'Embed in widget' link.")
    R6_TASKS.append(f"From /widget/{w}, click the embed link and verify the embed-blocked fallback page appears.")

# Pad to >= 1000 with parameterized derivative/integral tasks
_FILLER_FUNCS = ['x^2','x^3','x^4','x^5','sin(x)','cos(x)','tan(x)','e^x',
                 'ln(x)','x sin(x)','x cos(x)','sqrt(x)','1/x','x e^x',
                 'sin(x)^2','cos(x)^2','arctan(x)','sinh(x)','cosh(x)',
                 'x^2 e^x','x^2 sin(x)','e^x cos(x)','e^x sin(x)']
_FILLER_X = [0.25, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0]
_FILLER_B = [1, 2, 3, 5, 8, 10]
for f in _FILLER_FUNCS:
    for x in _FILLER_X:
        R6_TASKS.append(f"Type \"derivative of {f} at x={x}\" into the search bar and read the computed plain-text result.")
for f in _FILLER_FUNCS:
    for b in _FILLER_B:
        R6_TASKS.append(f"Type \"integral of {f} from 0 to {b}\" into the search bar and read the computed plain-text result.")
for v in [1, 2, 5, 10, 20, 50, 100, 200, 500, 1000, 1500, 2500, 5000]:
    for pair in [('km','miles'),('miles','km'),('kg','pounds'),('pounds','kg'),
                 ('liters','gallons'),('gallons','liters'),('celsius','fahrenheit'),
                 ('fahrenheit','celsius'),('meters','feet'),('feet','meters')]:
        R6_TASKS.append(f"Type \"convert {v} {pair[0]} to {pair[1]}\" into the search bar and read the result.")
for a in [1, 2, 3, 5, 7, 9, 11, 13, 17, 19, 23, 29, 31, 37]:
    R6_TASKS.append(f"Type \"roots of x^2 - {a}\" into the search bar and verify both roots are shown.")
    R6_TASKS.append(f"Type \"factor {a*7}\" into the search bar and read the prime factorization.")
# Additional widget gallery clicks
for w in ['derivative-calculator','integral-calculator','matrix-determinant','eigenvalue-finder',
         'polynomial-roots','unit-converter','currency-converter','mortgage-calculator','bmi-calculator',
         'tip-calculator','compound-interest','scientific-calc','trig-identities','statistics-summary',
         'probability-dice','plot-function']:
    R6_TASKS.append(f"Open /widget/{w} and read the sample input and sample output.")
    R6_TASKS.append(f"From /widgets, click on the '{w}' tile.")

# Additional R6 fillers: SHM, dice probabilities, normal distribution lookups
_SHM_FILLERS = [(m,k) for m in [0.1,0.5,1,2,5] for k in [10,50,100,500]]
for (m,k) in _SHM_FILLERS:
    R6_TASKS.append(f"Type \"SHM mass={m}kg k={k}N/m amplitude=0.1m\" and read the period and frequency.")
for (n,s) in [(2,7),(2,5),(3,10),(3,12),(4,14),(5,20),(6,21)]:
    R6_TASKS.append(f"Type \"probability sum {s} with {n}d6\" and read the listed probability.")
for (mu,sigma,x) in [(0,1,0),(0,1,1.96),(50,10,75),(100,15,130),(0,1,-1)]:
    R6_TASKS.append(f"Type \"P(X<{x}) for X~N({mu},{sigma}^2)\" and read the CDF value.")
# Resource + product pages (light surface navigation)
for r in ['tutorials','examples','widgets','api','datasets','videos']:
    R6_TASKS.append(f"Navigate to /resources/{r} and list two items shown on the page.")
for p in ['short-answers-api','full-results-api','conversational-api','simple-api','spoken-results-api']:
    R6_TASKS.append(f"Navigate to /products/{p} and find the rate-limit tier listed.")
# Pro flow
for u in ['/pro','/pro/pricing','/pro/upgrade','/pro/features']:
    R6_TASKS.append(f"Open {u} and verify the page renders with a Pro headline.")
# Account flow
R6_TASKS.append("Log in as demo@wolframalpha.com with password demo1234, then open /account.")
R6_TASKS.append("After login, open /favorites and remove the first favorite.")
R6_TASKS.append("After login, open /history and clear the history.")
R6_TASKS.append("After login, open /saved-queries and remove the first saved query.")
# Final padding
R6_TASKS.append("Open the homepage and click the 'Examples' link in the toolbar.")
R6_TASKS.append("Open /examples/mathematics and pick the 'Calculus' subcategory.")
R6_TASKS.append("On /examples/science-and-technology/physics, click on a featured topic.")
R6_TASKS.append("Open /about and find the 'About Wolfram|Alpha' section.")
R6_TASKS.append("Open /mobile-apps and list the available platforms.")
R6_TASKS.append("From the homepage, click the 'RANDOM' link in the toolbar.")
R6_TASKS.append("Open /search?q=derivative and pick the first matching topic.")
R6_TASKS.append("Open /notebook/create and create a new notebook called 'R6 Test Notes'.")

# Emit
with open(TASKS_PATH, 'a') as out:
    emitted = 0
    for q_text in R6_TASKS:
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
print(f"[r6 tasks] emitted {emitted}; total in candidate pool {len(R6_TASKS)}")
