#!/usr/bin/env python3
"""R11 GUI tasks generator — appends ~600 GUI-style tasks for the new
real wolframalpha.com page families (examples / widgets / cloud / language /
courseware / blog / community / about / jobs / store / mathworld /
demonstrations / research / conferences / public notebooks).

Deterministic. Idempotent: ID space uses string suffix `gui_<page>_<NNN>` so
we don't collide with the int-suffix legacy ids. Task text de-duplicated.
"""
from __future__ import annotations
import json, os

TASKS_PATH = 'tasks.jsonl'
WEB_NAME = 'Wolfram Alpha'
WEB_NAME_ID = 'WolframAlpha'
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
existing_ids = {t.get('id', '') for t in existing}
existing_questions = {t.get('ques', '') for t in existing}

EXAMPLES_TOPICS = ['mathematics', 'science-and-technology', 'society-and-culture',
                   'everyday-life', 'pro-features']
WIDGETS = ['tip-calculator', 'unit-converter', 'derivative-step', 'integral-step',
           'matrix-solver', 'periodic-table', 'bmi-calculator', 'loan-amortization',
           'mortgage-payment', 'mole-calculator', 'projectile-motion',
           'standard-deviation']
NOTEBOOKS = ['introduction-to-machine-learning', 'visualizing-pi',
             'cellular-automata-explorer', 'covid-pandemic-data',
             'us-election-poll-aggregate', 'mortgage-affordability-model',
             'sars-cov2-variant-tree', 'galaxy-rotation-curves',
             'fourier-series-sandbox', 'matrix-decompositions',
             'pendulum-phase-space', 'crispr-target-finder']
LANG_TUTORIALS = ['lists', 'symbols-and-patterns', 'functions',
                  'differential-equations', 'statistical-distributions',
                  'strings-and-text', 'files-and-streams',
                  'notebooks-as-documents', 'geometric-computation',
                  'plotting', 'numerical-mathematics', 'machine-learning']
COURSES = ['introduction-to-wolfram-language', 'introduction-to-game-theory',
           'introduction-to-partial-differential-equations',
           'introduction-to-laplace-transforms', 'quick-start-wolfram-tech',
           'visual-explorations-in-data-science', 'machine-learning-fundamentals',
           'image-processing-101', 'multivariable-calculus', 'linear-algebra',
           'introduction-to-finance', 'introduction-to-statistics']
CERTS = ['WU-2026-0421', 'WU-2026-0590', 'WU-2026-0612',
         'WU-2026-0733', 'WU-2026-0815', 'WU-2026-0901']
BLOG_POSTS = ['making-wolfram-tech-foundation-llm', 'instant-supercompute-launch',
              'laplace-transforms-etextbook', 'checkmate-game-theory-wolfram',
              'compression-recompression-jpeg', 'data-adventure-boston-1929',
              'llms-symbolic-mathematics', 'vinor-prague-neolithic',
              'elementary-functions-single-operator',
              'computational-breast-cancer-detection', 'transmon-cqed-qolab',
              'mathematica-14-1-release', 'wolfram-13-3-llm-functions',
              'wolfram-language-data-types', 'pi-day-2026',
              'wolfram-summer-school-2025', 'finance-platform-update',
              'astronomy-image-of-the-day']
BLOG_CATS = ['wolfram-language', 'mathematics', 'education', 'image-processing',
             'digital-humanities', 'wolfram-news', 'mathematica-news',
             'life-sciences-and-medicine', 'recreational-computation', 'events',
             'finance', 'astronomy']
COMMUNITY_TIDS = [3678635, 3682277, 3711368, 3710432, 3694198, 3649858,
                  3666356, 3601822, 3589104, 3522345, 3501776, 3478910]
COMMUNITY_GROUPS = ['wolfram-language', 'wolfram-alpha', 'mathematica',
                    'wolfram-cloud', 'wolfram-u', 'general']
JOBS = ['JOB-2026-101', 'JOB-2026-102', 'JOB-2026-103', 'JOB-2026-104',
        'JOB-2026-105', 'JOB-2026-106', 'JOB-2026-107', 'JOB-2026-108',
        'JOB-2026-109', 'JOB-2026-110', 'JOB-2026-111', 'JOB-2026-112']
STORE_PRODUCTS = ['mathematica-home', 'mathematica-student', 'mathematica-pro',
                  'wolfram-one', 'wolfram-alpha-pro', 'system-modeler',
                  'finance-platform', 'cloud-credits-1k', 'cloud-credits-10k',
                  'book-tnws', 'book-elementary', 'tshirt-wl']
RESEARCH_PAPERS = ['computational-equivalence-2002', 'multiway-systems-2020',
                   'symbolic-vs-llm-2024', 'cellular-automata-class-1985',
                   'wolfram-physics-graphs-2020', 'compute-everything-2023',
                   'pattern-matching-rewriting-1998',
                   'large-language-models-symbolic-2024',
                   'physical-units-2019', 'wolfram-language-history-2014',
                   'knowledge-based-2010', 'multivariate-polynomials-2017']
CONFERENCES = ['wtc-2018', 'wtc-2019', 'wtc-2020', 'wtc-2021', 'wtc-2022',
               'wtc-2023', 'wtc-2024', 'wtc-2025']
DEMOS = [1101, 1212, 1325, 1448, 1551, 1672, 1789, 1820, 1953, 2076,
         2191, 2204, 2317, 2430, 2543, 2666, 2789, 2802]
MATHWORLD = ['Pythagorean-Theorem', 'Pi', 'e', 'Golden-Ratio',
             'Fibonacci-Number', 'Riemann-Hypothesis', 'Eulers-Identity',
             'Prime-Number-Theorem', 'Twin-Prime-Conjecture',
             'Goldbach-Conjecture', 'Mandelbrot-Set', 'Julia-Set',
             'Lorenz-Attractor', 'Gaussian-Distribution',
             'Binomial-Coefficient', 'Catalan-Number', 'Eulers-Totient',
             'Riemann-Zeta', 'Pascals-Triangle', 'Fermats-Last-Theorem',
             'Cauchy-Schwarz', 'Triangle-Inequality',
             'Chebyshev-Polynomials', 'Bessel-Function',
             'Legendre-Polynomial', 'Hermite-Polynomial',
             'Gamma-Function', 'Beta-Function', 'Eulers-Formula',
             'Continued-Fraction', 'Greens-Theorem', 'Stokes-Theorem',
             'Bayes-Theorem', 'Central-Limit-Theorem']

# Page-family -> list of natural-language task questions.
FAMILIES = {}


def add(family, q):
    FAMILIES.setdefault(family, []).append(q)


# --- 1. examples (index) — 30 tasks ---
add('examples', "Open the Wolfram|Alpha examples index page and confirm 'Mathematics' is listed as one of the top-level sections.")
add('examples', "On the examples index page, find the count of top-level example sections shown.")
add('examples', "From the examples index, click into the 'Mathematics' section and verify the URL changes to a /examples/mathematics path.")
add('examples', "Open the examples index page and check that 'Pro Features' is one of the listed sections.")
add('examples', "On the examples index page, list any three of the five top-level example sections.")
add('examples', "Visit the examples index page and confirm it mentions 'Pro Features' as a section.")
add('examples', "Open the examples index and find the section dedicated to 'Society & Culture'.")
add('examples', "Navigate to the examples index page from the home page and confirm Mathematics appears.")
add('examples', "On the examples index page, identify which section would include 'Personal Health'.")
add('examples', "From the examples index, open the 'Everyday Life' section.")
add('examples', "Open the examples index page and read off the schema label used by its JSON representation.")
add('examples', "On the examples index, confirm a section called 'Science & Technology' is shown.")
add('examples', "Open the examples index and check that the page mentions browsing example queries.")
add('examples', "Use the examples index to navigate to Society & Culture section's page.")
add('examples', "Open the examples index page and verify the snapshot date is shown.")
add('examples', "From the examples index, click 'Mathematics' and then return to the index via the back link.")
add('examples', "Open the examples index page and confirm there are exactly five top-level sections.")
add('examples', "On the examples index, find the parsed-input field at the top of the page.")
add('examples', "Use the examples index to find which top-level section contains 'Geometry'.")
add('examples', "From the examples index page, confirm the related-queries footer lists each top-level section.")
add('examples', "Open the examples index and verify it links to /examples/pro-features somewhere on the page.")
add('examples', "Open the examples index page and check that 'Everyday Life' is one of the related queries.")
add('examples', "On the examples index, look at the parameters block and find the 'sections' count.")
add('examples', "Open the examples index and verify a Cmd+K palette link is present in the page footer.")
add('examples', "Navigate to /examples and verify the page title mentions 'Examples'.")
add('examples', "From the examples index, open the topic page for the 'examples-index' related topic slug.")
add('examples', "Open the examples index page and confirm the build version is 'r11'.")
add('examples', "From /examples, click into Science & Technology and confirm the URL is /examples/science-and-technology.")
add('examples', "Open the examples index and check the count of indexed sections matches 5.")
add('examples', "On the examples index, verify the page describes browsing expert-level example queries.")

# --- 2. widgets/<slug> — 30 tasks ---
for w in WIDGETS:
    add('widgets', f"Open the Wolfram Widget page for '{w}' and find its install count.")
    add('widgets', f"On /widgets/{w}, find which topic the widget is filed under.")
    add('widgets', f"Open the Wolfram Widget '{w}' and check the average user rating.")
WIDGET_EXTRA = [
    "Search the widget gallery for the 'Tip Calculator' and open its page.",
    "Open the 'Periodic Table Lookup' Wolfram Widget and find its embed size.",
    "On the 'BMI Calculator' widget page, verify the install count is over 10000.",
    "Open the 'Derivative Step-by-Step' widget and find the public URL listed on its page.",
    "On the 'Mortgage Payment Calculator' widget page, check the install count.",
    "Compare the install counts of the 'Tip Calculator' and 'Unit Converter' widgets.",
]
for q in WIDGET_EXTRA:
    add('widgets', q)

# --- 3. widget-gallery — 30 tasks ---
add('widget-gallery', "Open the Wolfram Widget Gallery and find the total number of widgets indexed.")
add('widget-gallery', "On the widget gallery page, find the top widget by install count.")
add('widget-gallery', "Open /widget-gallery and verify the top widget listed is for finance topic.")
add('widget-gallery', "Use the widget gallery topic filter and view only widgets in the 'finance' topic.")
add('widget-gallery', "Open the widget gallery with topic filter 'calculus' and find how many widgets match.")
add('widget-gallery', "From the widget gallery, click into the highest-install widget and verify the URL pattern /widgets/<slug>.")
add('widget-gallery', "Open the widget gallery, filter by topic 'chemistry', and find which widgets match.")
add('widget-gallery', "Open the widget gallery and confirm the schema label is 'wa-widget-gallery-v1'.")
add('widget-gallery', "From the widget gallery, find a widget related to BMI calculations.")
add('widget-gallery', "Use the widget gallery to find a widget for solving matrix equations.")
add('widget-gallery', "Open /widget-gallery?topic=units and verify exactly one widget matches.")
add('widget-gallery', "On the widget gallery, find the widget with the lowest install count.")
add('widget-gallery', "From the widget gallery, count how many widgets are listed under 'physics' topic.")
add('widget-gallery', "Open the widget gallery and check how many distinct topics are represented.")
add('widget-gallery', "On the widget gallery, click into the 'Standard Deviation' widget if present.")
add('widget-gallery', "Open the widget gallery and confirm the page mentions 12 total widgets.")
add('widget-gallery', "From the widget gallery, locate the 'Projectile Motion' widget.")
add('widget-gallery', "Open the widget gallery with topic filter 'statistics' and verify Standard Deviation appears.")
add('widget-gallery', "Open the widget gallery, find a calculus widget, and follow its page link.")
add('widget-gallery', "Use the widget gallery to confirm the topic-filter parameter is reflected in the parameters block.")
add('widget-gallery', "Open the widget gallery and find the topic of the top-ranked widget.")
add('widget-gallery', "Open the widget gallery and verify the version label shown is r11.")
add('widget-gallery', "From the widget gallery, open the gallery's JSON representation and check the count field.")
add('widget-gallery', "Use the widget gallery topic filter 'health' and confirm at least one widget is listed.")
add('widget-gallery', "On the widget gallery, sort or browse and identify which widget has the most installs.")
add('widget-gallery', "Open the widget gallery and find the install count of the second-highest widget.")
add('widget-gallery', "Use the widget gallery to navigate into the 'Loan Amortization Schedule' widget.")
add('widget-gallery', "From the widget gallery, locate the 'Mole / Mass Calculator' widget.")
add('widget-gallery', "Open the widget gallery and confirm the snapshot date is 2026-05-27.")
add('widget-gallery', "From the widget gallery, view the page that lists the 12 widgets ordered by installs.")

# --- 4. pub-notebook (12 slugs * 3) — 36 tasks ---
for nb in NOTEBOOKS:
    add('pub-notebook', f"Open the public notebook '{nb}' and find the author name.")
    add('pub-notebook', f"On the public notebook /pub/notebook/{nb}, find how many cells it has.")
    add('pub-notebook', f"Open the public notebook '{nb}' and verify the license is CC-BY-4.0.")

# --- 5. cloud (3 pages, 10 each + extra) — 30 tasks ---
add('cloud', "Open the Wolfram Cloud home page and find the free monthly compute-minutes quota.")
add('cloud', "On /cloud, find the free storage quota in gigabytes.")
add('cloud', "Open the Wolfram Cloud home and confirm it shows the number of public notebooks indexed.")
add('cloud', "From /cloud, navigate to the Cloud upload page.")
add('cloud', "On the Wolfram Cloud home, find whether a Pro plan is active for the current visitor.")
add('cloud', "Open the Wolfram Cloud home and verify the related-queries list links to upload and share.")
add('cloud', "Open /cloud and find the schema label used by the page.")
add('cloud', "On the Cloud home page, verify the snapshot date is 2026-05-27.")
add('cloud', "Open the Wolfram Cloud upload page and submit name='demo' visibility='public'.")
add('cloud', "On /cloud/upload, choose visibility='public' for a notebook named 'pi-experiment'.")
add('cloud', "Open the Cloud upload page and find the cloud_token generated for name='hello' visibility='private'.")
add('cloud', "Submit a Cloud upload with name='my-notebook' visibility='shared' and read the public_url shown.")
add('cloud', "On the Cloud upload page, leave defaults and find which visibility is chosen by default.")
add('cloud', "Open /cloud/upload?name=test&visibility=invalid and confirm the page normalizes visibility to 'private'.")
add('cloud', "Open the Cloud upload page and find the JSON schema label.")
add('cloud', "Open the Wolfram Cloud share page and find the default audience setting.")
add('cloud', "On /cloud/share, provide a custom token 'demo-token' and audience='public'.")
add('cloud', "From the Cloud share page with audience='public', find the share_url displayed.")
add('cloud', "Open the Cloud share page with audience='internal' (default normalization expected).")
add('cloud', "On the Cloud share page, find which audience value is used when none is provided.")
add('cloud', "Open the Cloud share page and verify the page links back to /cloud/upload.")
add('cloud', "From the Cloud share page, follow the related-query link to public notebooks.")
add('cloud', "Open the Wolfram Cloud home and follow the link to the Pro upgrade page.")
add('cloud', "Open the Wolfram Cloud home and find the link to the Wolfram Language page.")
add('cloud', "Open the Cloud upload page and find which related query mentions notebook templates.")
add('cloud', "Open the Cloud share page and verify the parameter table shows 'token' and 'audience'.")
add('cloud', "Open /cloud and confirm the page describes running notebooks in the browser.")
add('cloud', "Open /cloud/upload and verify the parsed-input pod mentions CloudUpload.")
add('cloud', "Open /cloud/share and verify the parsed-input pod mentions CloudShare.")
add('cloud', "Open the Wolfram Cloud home and read off the count of public notebooks indexed.")

# --- 6. language (3 pages + 12 tutorials*2) — 30 tasks ---
add('language', "Open the Wolfram Language home page and find when the language was first released.")
add('language', "On /language, find the number of getting-started tutorials listed.")
add('language', "Open the Wolfram Language home page and find which core paradigms it lists.")
add('language', "Open the Wolfram Language home and follow the link to getting-started.")
add('language', "On the Wolfram Language home, locate the related-query link to the Lists tutorial.")
add('language', "Open /language and confirm the page mentions Mathematica.")
add('language', "Open the Getting Started page and find how many sections it has.")
add('language', "On /language/getting-started, find the sample input shown.")
add('language', "Open the Getting Started page and find the sixth section topic.")
add('language', "On /language/getting-started, follow the related link to a plotting tutorial.")
add('language', "Open the Getting Started page and verify the parsed-input pod is GettingStarted[WolframLanguage].")
add('language', "Open the Wolfram Language home and verify the schema label is 'wa-language-home-v1'.")
for slug in LANG_TUTORIALS:
    add('language', f"Open the Wolfram Language tutorial on '{slug}' and read its abstract.")
for slug in LANG_TUTORIALS[:6]:
    add('language', f"On /language/tutorial/{slug}, find which tutorial is suggested as the next one.")
add('language', "Open the Wolfram Language tutorial on 'plotting' and find the section count.")
add('language', "Open the Wolfram Language tutorial on 'lists' and find its abstract length in sections.")

# --- 7. courseware (4 routes) — 32 tasks ---
add('courseware', "Open the Wolfram-U courseware catalog and find the total course count.")
add('courseware', "On /courseware, find how many distinct course categories are listed.")
add('courseware', "Open the courseware catalog and identify the top course by listing order.")
add('courseware', "Open the courseware catalog and find a course in the 'Data Science' category.")
add('courseware', "Open /courseware and locate the 'Multivariable Calculus' course.")
add('courseware', "Open the courseware catalog and follow the link to the 'Linear Algebra' course detail page.")
for c in COURSES:
    add('courseware', f"Open the Wolfram-U course '{c}' and find its lesson count.")
for c in COURSES:
    add('courseware', f"On the course page /courseware/{c}, find which level (beginner/intermediate/advanced) the course is.")
for cert in CERTS:
    add('courseware', f"Open the courseware certificate page for ID {cert} and find which course it was awarded for.")

# --- 8. blog (3 routes) — 36 tasks ---
add('blog', "Open the Wolfram Blog index and find the latest post slug.")
add('blog', "On /blog, find the number of indexed posts.")
add('blog', "Open the Wolfram Blog and identify the most recent post title.")
add('blog', "Open the Wolfram Blog and read the title of the second-most-recent post.")
add('blog', "Open the blog index and find the number of distinct blog categories.")
add('blog', "From the blog index, follow the link to the 'mathematics' category.")
for p in BLOG_POSTS:
    add('blog', f"Open the Wolfram blog post '{p}' and find its author.")
for c in BLOG_CATS:
    add('blog', f"Open the Wolfram blog category page for '{c}' and find how many posts it lists.")

# --- 9. community (3 routes) — 30 tasks ---
add('community', "Open the Wolfram Community home and find the total number of groups.")
add('community', "On /community, find the total indexed topics count.")
add('community', "Open the Wolfram Community home and find how many total members across all groups are indexed.")
add('community', "Open /community and follow the related link to the Wolfram Language group.")
add('community', "Open the Wolfram Community home and verify the schema label is 'wa-community-home-v1'.")
add('community', "From the community home, identify which group has the most members.")
for tid in COMMUNITY_TIDS:
    add('community', f"Open the Wolfram Community topic with ID {tid} and find which group it is in.")
for g in COMMUNITY_GROUPS:
    add('community', f"Open the Wolfram Community group page for '{g}' and find the member count.")
for g in COMMUNITY_GROUPS:
    add('community', f"On /community/group/{g}, find how many indexed topics belong to this group.")

# --- 10. about (3 routes) — 30 tasks ---
add('about', "Open the /about/team page and find the size of the team listed.")
add('about', "On /about/team, find the email address listed for Stephen Wolfram.")
add('about', "Open the about-team page and identify who is listed as Strategic Director.")
add('about', "Open /about/team and find who serves as Director of R&D.")
add('about', "On the about-team page, find which role Theodore Gray holds.")
add('about', "Open /about/team and verify Daniel Lichtblau is listed as a kernel developer.")
add('about', "Open the about-team page and read off the 'team_size' parameter.")
add('about', "Open the about-team page and find which member is listed as CEO.")
add('about', "Open /about/team and identify a Senior Research Mathematician.")
add('about', "On the about-team page, find who is listed as a Research Programmer.")
add('about', "Open /about/history and find the year Mathematica 1.0 was released.")
add('about', "On the about-history page, find when Wolfram|Alpha was launched publicly.")
add('about', "Open /about/history and find the year MathWorld was launched.")
add('about', "Open the about-history page and find when the Wolfram Cloud was released.")
add('about', "On /about/history, find the year ChatGPT-style LLM functions were added to Wolfram Language.")
add('about', "Open /about/history and find the total number of milestones listed.")
add('about', "On the about-history page, find the year the Wolfram Language was announced separately from Mathematica.")
add('about', "Open /about/history and find when Mathematica 12.0 shipped.")
add('about', "Open the about-history page and find when the UK office opened.")
add('about', "On /about/history, locate the latest milestone year shown.")
add('about', "Open /contact-us and find the support email address.")
add('about', "On /contact-us, find the US phone number listed.")
add('about', "Open the contact-us page and find Wolfram Research's mailing address.")
add('about', "Open /contact-us and find the sales email address.")
add('about', "On the contact-us page, find the response SLA in hours.")
add('about', "Open /contact-us and verify the page links to /about/team.")
add('about', "Open /contact-us and verify the page links to /jobs.")
add('about', "On the contact-us page, find the city and state of Wolfram's headquarters.")
add('about', "Open /contact-us and verify the schema label is 'wa-contact-us-v1'.")
add('about', "Open /contact-us and find which postal address ZIP code is listed.")

# --- 11. jobs (2 routes) — 32 tasks ---
add('jobs', "Open the /jobs page and find the total number of open positions.")
add('jobs', "On /jobs, find how many distinct departments are listed.")
add('jobs', "Open the jobs index with department filter 'engineering' and find how many matches there are.")
add('jobs', "Open /jobs?dept=research and find the count of research positions.")
add('jobs', "From the jobs index, follow the link to the first listed position.")
add('jobs', "Open /jobs and identify any role located in 'Boston, MA'.")
add('jobs', "On /jobs, find any role with an intern-band salary.")
add('jobs', "Open the jobs index and find a position with a salary band starting at $160k.")
for j in JOBS:
    add('jobs', f"Open the job posting {j} and find its department.")
for j in JOBS:
    add('jobs', f"On /jobs/{j}, find the location.")
add('jobs', "Open job JOB-2026-102 and find the salary band offered.")
add('jobs', "Open job JOB-2026-108 and find the role title.")
add('jobs', "On /jobs/JOB-2026-112, confirm the role is an internship.")
add('jobs', "Open job JOB-2026-105 and find which location is listed.")

# --- 12. store (2 routes) — 32 tasks ---
add('store', "Open the /store page and find the total number of products listed.")
add('store', "On /store, find which categories are represented.")
add('store', "Open /store?cat=software and find how many software products are listed.")
add('store', "Open the store with the 'book' category filter and find which books are listed.")
add('store', "From the store index, follow the link to 'Mathematica Professional'.")
add('store', "Open the store and find the cheapest product listed.")
add('store', "Open the store and find any product priced exactly $50.")
add('store', "On /store, find any product in the 'Apparel' category.")
for p in STORE_PRODUCTS:
    add('store', f"Open the store product page for '{p}' and find its USD price.")
for p in STORE_PRODUCTS:
    add('store', f"On /store/product/{p}, find which category the product is in.")
add('store', "Open /store/product/mathematica-home and find whether it is in stock.")
add('store', "Open the store product 'book-tnws' and find how many days shipping takes.")
add('store', "Open store product 'cloud-credits-10k' and find its price per credit (approximate from the page).")
add('store', "On /store/product/tshirt-wl, find the price of the T-shirt.")

# --- 13. research (2 routes) — 32 tasks ---
add('research', "Open /research and find the total number of indexed papers.")
add('research', "On /research, find the span of years covered by the index.")
add('research', "Open the research index and find the most recent paper listed.")
add('research', "Open /research and identify any paper authored by Daniel Lichtblau.")
add('research', "From the research index, follow the link to the cellular automata classification paper.")
add('research', "Open /research and find a paper from the year 2002.")
add('research', "Open /research and locate a paper in the 'numerics' area.")
add('research', "On /research, find which paper is the oldest in the catalog.")
for paper in RESEARCH_PAPERS:
    add('research', f"Open the research paper page for '{paper}' and find its author.")
for paper in RESEARCH_PAPERS:
    add('research', f"On /research/{paper}, find its publication year.")

# --- 14. conferences (2 routes) — 30 tasks ---
add('conferences', "Open /conferences and find the total number of conference editions listed.")
add('conferences', "On /conferences, find the latest edition shown.")
add('conferences', "Open the conferences index and identify which editions were held virtually.")
add('conferences', "From the conferences index, follow the link to the 2023 conference page.")
add('conferences', "Open /conferences and find any edition held in 2020.")
add('conferences', "Open the conferences index and find which editions were held in Champaign, IL.")
for slug in CONFERENCES:
    add('conferences', f"Open the conference page for '{slug}' and find the attendee count.")
for slug in CONFERENCES:
    add('conferences', f"On /conferences/{slug}, find the location of that edition.")
for slug in CONFERENCES[:8]:
    add('conferences', f"Open /conferences/{slug} and find the year that edition was held.")

# --- 15. demonstrations (2 routes) — 36 tasks ---
add('demonstrations', "Open /demonstrations and find the total number of indexed demos.")
add('demonstrations', "On /demonstrations, find which topics are represented.")
add('demonstrations', "Open /demonstrations and identify a demo about the Mandelbrot set.")
add('demonstrations', "From the demonstrations index, follow the link to the Game of Life demo.")
add('demonstrations', "Open /demonstrations and locate a physics-topic demo.")
add('demonstrations', "On /demonstrations, find a chemistry-topic demo.")
for did in DEMOS:
    add('demonstrations', f"Open the Wolfram Demonstration with ID {did} and find its topic.")
for did in DEMOS[:12]:
    add('demonstrations', f"On /demonstrations/{did}, find the CDF size in KB.")

# --- 16. mathworld (2 routes) — 70 tasks ---
add('mathworld', "Open the MathWorld index and find the total number of indexed entries.")
add('mathworld', "On /mathworld, find which topics are represented.")
add('mathworld', "Open /mathworld?topic=number-theory and find how many entries match.")
add('mathworld', "Open /mathworld?topic=fractals and find how many entries match.")
add('mathworld', "From the MathWorld index, follow the link to the entry on Pi.")
add('mathworld', "Open /mathworld and locate the entry on Bayes' Theorem.")
for entry in MATHWORLD:
    add('mathworld', f"Open the MathWorld entry for '{entry}' and find its topic.")
for entry in MATHWORLD[:30]:
    add('mathworld', f"On /mathworld/{entry}, find the reference count shown for that entry.")

# --- Emit ---
def slugify_family(f):
    return f.replace('-', '_')

with open(TASKS_PATH, 'a') as out:
    emitted = 0
    for family, qs in FAMILIES.items():
        counter = 0
        for q in qs:
            if q in existing_questions:
                continue
            counter += 1
            tid = f"{WEB_NAME_ID}--gui_{slugify_family(family)}_{counter:03d}"
            while tid in existing_ids:
                counter += 1
                tid = f"{WEB_NAME_ID}--gui_{slugify_family(family)}_{counter:03d}"
            rec = {"web_name": WEB_NAME,
                   "id": tid,
                   "ques": q,
                   "web": WEB_URL,
                   "upstream_url": UPSTREAM}
            out.write(json.dumps(rec, ensure_ascii=False) + "\n")
            existing_ids.add(tid)
            existing_questions.add(q)
            emitted += 1
print(f"[r11 gui tasks] emitted {emitted}; families {len(FAMILIES)}; "
      f"pool size {sum(len(v) for v in FAMILIES.values())}")
for f, qs in FAMILIES.items():
    print(f"  {f}: {len(qs)} tasks")
