#!/usr/bin/env python3
"""Deterministic seed-DB extender for the Wolfram Alpha mirror.

Reads `instance_seed/wolfram_alpha.db` and APPENDS new rows for:
  - subcategories  (28 -> 65)
  - topics         (23 -> 61) — fills the 5 missing subcategory-slug topics
                                so /topic/<life-sciences|engineering|history|
                                arts-media|entertainment> no longer 404s
  - computation_results (163 -> ~510) — generic Wolfram-style queries; no
                                        required_specifiers (won't interfere
                                        with existing task-tuned records).
  - notebook_entries (24 -> ~84) — extends the 8 existing notebooks
  - topic_feedback   (0  -> ~32) — spread across topics + 5 users

Existing rows are NEVER touched.  Run twice on a fresh source = byte-identical.
All timestamps come from a single REFERENCE date so the output is fully
deterministic.

Usage (inside the build container):
    python3 _build_seed.py --in  instance_seed/wolfram_alpha.db \
                           --out instance/wolfram_alpha.db
"""
from __future__ import annotations
import argparse, json, sqlite3, shutil
from datetime import datetime, timedelta

REF = datetime(2026, 4, 15, 12, 0, 0)
def ts(off_hours: int = 0) -> str:
    return (REF + timedelta(hours=off_hours)).isoformat(sep=' ')

# ---------------------------------------------------------------------------
# (1)  Subcategories — additions
# ---------------------------------------------------------------------------
# category_id mapping (from app.py CATEGORIES order):
#   1 = mathematics, 2 = science-and-technology, 3 = society-and-culture,
#   4 = everyday-life.  sort_order starts after existing max-per-cat.

NEW_SUBCATEGORIES = [
    # Mathematics (existing 8 → +8 = 16)
    (1, "Applied Mathematics",     "applied-math",        9,  "Mathematical modelling, numerical methods, and applied analysis."),
    (1, "Discrete Mathematics",    "discrete-math",       10, "Graph theory, combinatorics, recurrences, and discrete structures."),
    (1, "Complex Analysis",        "complex-analysis",    11, "Complex numbers, analytic functions, contour integrals, residues."),
    (1, "Differential Equations",  "differential-equations", 12, "Ordinary and partial differential equations and their solutions."),
    (1, "Mathematical Functions",  "math-functions",      13, "Elementary and special functions: gamma, Bessel, hypergeometric."),
    (1, "Optimization",            "optimization",        14, "Linear, nonlinear, integer, and convex optimization problems."),
    (1, "Math Puzzles & Games",    "math-puzzles",        15, "Classic puzzles, Rubik's-cube counts, magic squares, paradoxes."),
    (1, "Mathematical History",    "math-history",        16, "Famous theorems, mathematicians, and milestones in mathematics."),
    # Science & Technology (existing 8 → +8 = 16)
    (2, "Biological Sciences",     "biological-sciences", 9,  "Cells, organisms, anatomy, ecology, and molecular biology."),
    (2, "Computer Science",        "computer-science",    10, "Algorithms, complexity, data structures, encoding, and software."),
    (2, "Materials Science",       "materials-science",   11, "Properties of metals, polymers, composites, and crystal structures."),
    (2, "Engineering",             "engineering-detail",  12, "Electrical, mechanical, civil, and chemical engineering calculations."),
    (2, "Transportation",          "transportation",      13, "Vehicles, fuel economy, aerodynamics, and travel logistics."),
    (2, "Space & Spaceflight",     "space-spaceflight",   14, "Rockets, satellites, orbital mechanics, and mission profiles."),
    (2, "Technological World",     "tech-world",          15, "Phones, photography, networks, and consumer electronics specs."),
    (2, "Web & Software",          "web-software",        16, "HTTP status codes, IP, regular expressions, encoding & hashing."),
    # Society & Culture (existing 6 → +8 = 14)
    (3, "Economics",               "economics",           7,  "Macroeconomic data, inflation, currencies, GDP, and trade."),
    (3, "Education",               "education",           8,  "Schools, universities, degrees, and educational statistics."),
    (3, "Religion",                "religion",            9,  "World religions, demographics, and holy-day computations."),
    (3, "Philosophy",              "philosophy",          10, "Philosophers, schools, logic, and ethics references."),
    (3, "Mythology",               "mythology",           11, "Greek, Roman, Norse, and world mythology references."),
    (3, "Politics",                "politics",            12, "Political systems, elections, parliaments, and indices."),
    (3, "Popular Culture",         "popular-culture",     13, "Movies, music, TV, video games, and cultural icons."),
    (3, "Sports & Society",        "sports-society",      14, "Olympics, leagues, athletes, and major sporting events."),
    # Everyday Life (existing 6 → +8 = 14)
    (4, "Cooking & Recipes",       "cooking",             7,  "Recipes, cooking-time math, substitutions, and food chemistry."),
    (4, "Gardening & Plants",      "gardening",           8,  "Plant facts, growing zones, soil, and gardening computations."),
    (4, "Pets",                    "pets",                9,  "Dog and cat breeds, lifespan, weight ranges, and care data."),
    (4, "Dates & Times",           "dates-times",         10, "Calendars, time zones, ages, holidays, and date arithmetic."),
    (4, "Hobbies & Games",         "hobbies-games",       11, "Card games, board games, RPG dice, and probability of play."),
    (4, "Music & Audio",           "music-audio",         12, "Notes, frequencies, scales, decibels, and audio computations."),
    (4, "Photography",             "photography",         13, "Aperture, shutter, ISO, depth of field, and exposure math."),
    (4, "Words & Letters",         "words-letters",       14, "Word lengths, frequencies, scrabble scores, and palindromes."),
]
# 32 new subcategories ⇒ 28 + 32 = 60 ✓

# ---------------------------------------------------------------------------
# (2)  Topics — additions.  Crucial: the first 5 fix /topic/<subcat-slug> 404
# ---------------------------------------------------------------------------
# Each topic: (category_slug, subcategory_slug, name, slug, description,
#             image_basename, is_featured, is_new, examples_list_of_dict)

def J(examples):  # short helper
    return json.dumps(examples)

NEW_TOPICS = [
    # --- 404 fixers (subcategory slugs without a matching topic) ---
    ("science-and-technology", "life-sciences", "Life Sciences", "life-sciences",
     "Biology, anatomy, genetics, ecology, and species data — from cells to ecosystems.",
     "life-sciences.png", True, False, J([
        {"query":"human heart rate at rest","type":"physiology","result":"60–100 beats per minute (typical adult)"},
        {"query":"DNA base pairs in human genome","type":"genetics","result":"≈ 3.2 × 10⁹ base pairs"},
        {"query":"gestation period of an elephant","type":"biology","result":"≈ 645 days (≈ 22 months)"},
        {"query":"E. coli generation time","type":"microbiology","result":"≈ 20 minutes (optimal conditions)"},
        {"query":"chlorophyll absorption peak","type":"plant biology","result":"Chl-a: 430 nm and 662 nm"},
     ])),
    ("science-and-technology", "engineering", "Engineering", "engineering",
     "Electrical, mechanical, civil, and chemical engineering computations — circuits, beams, fluids, and reactions.",
     "engineering.png", False, False, J([
        {"query":"resistors 100Ω and 220Ω in parallel","type":"electrical","result":"68.75 Ω"},
        {"query":"beam deflection cantilever L=2m F=500N E=200GPa I=8e-6","type":"mechanical","result":"δ = 0.83 mm"},
        {"query":"Reynolds number water 0.5 m/s 50 mm pipe","type":"fluid","result":"Re ≈ 25,000 (turbulent)"},
        {"query":"power 24V 3A circuit","type":"electrical","result":"P = 72 W"},
        {"query":"belt length 2 pulleys d1=100 d2=300 C=400","type":"mechanical","result":"≈ 1430 mm"},
     ])),
    ("society-and-culture", "history", "History", "history",
     "Historical events, timelines, civilizations, and the dates of key moments.",
     "history.png", False, False, J([
        {"query":"when did World War II end","type":"event","result":"September 2, 1945 (V-J Day)"},
        {"query":"Roman Empire founded","type":"civilization","result":"Traditionally 27 BC (Augustus)"},
        {"query":"days between July 4 1776 and today","type":"timeline","result":"Computed from today's date"},
        {"query":"signers of the US Declaration of Independence","type":"document","result":"56 signers"},
        {"query":"length of Hundred Years' War","type":"war","result":"116 years (1337–1453)"},
     ])),
    ("society-and-culture", "arts-media", "Arts & Media", "arts-media",
     "Movies, music, literature, painting, and popular media data.",
     "arts-media.png", False, False, J([
        {"query":"Mona Lisa painting","type":"art","result":"Leonardo da Vinci, 1503–1519, oil on poplar"},
        {"query":"highest grossing film","type":"film","result":"Avatar (2009), $2.92 B worldwide"},
        {"query":"length of War and Peace","type":"book","result":"≈ 587,287 words (Russian original)"},
        {"query":"Beethoven symphonies","type":"music","result":"9 numbered symphonies"},
        {"query":"oldest opera","type":"music","result":"Dafne by Peri, c. 1597 (lost)"},
     ])),
    ("everyday-life", "entertainment", "Entertainment", "entertainment",
     "Movies, music, sports, video games, and pop culture computations.",
     "entertainment.png", False, False, J([
        {"query":"top grossing video game","type":"game","result":"Minecraft (300M+ copies sold)"},
        {"query":"NBA all-time scoring leader","type":"sport","result":"LeBron James (40,000+ points)"},
        {"query":"longest song on the Billboard Hot 100","type":"music","result":"'American Pie' — 8:42"},
        {"query":"Olympic Games host 2024","type":"event","result":"Paris, France"},
        {"query":"Tetris score 999999","type":"game","result":"Theoretical max line clear scoring"},
     ])),

    # --- Mathematics extras ---
    ("mathematics", "applied-math", "Applied Mathematics", "applied-mathematics",
     "Numerical methods, mathematical modelling, and applied analysis.",
     "calculus.png", False, True, J([
        {"query":"Newton's method x^3 - 2 = 0","type":"numerical","result":"x ≈ 1.2599 (root in 4 iterations)"},
        {"query":"trapezoidal rule sin(x) 0 to pi n=8","type":"quadrature","result":"≈ 1.9742"},
        {"query":"FFT of {1,0,-1,0}","type":"fft","result":"{0, 2, 0, 2}"},
        {"query":"least squares fit (1,1)(2,3)(3,5)(4,8)","type":"fitting","result":"y = 2.3x − 0.5"},
     ])),
    ("mathematics", "discrete-math", "Discrete Mathematics", "discrete-mathematics",
     "Graph theory, combinatorics, recurrences, and discrete structures.",
     "discrete-math.png", False, False, J([
        {"query":"Fibonacci(20)","type":"sequence","result":"6765"},
        {"query":"Catalan number C(7)","type":"combinatorics","result":"429"},
        {"query":"chromatic number Petersen graph","type":"graph","result":"3"},
        {"query":"how many ways to arrange MISSISSIPPI","type":"permutation","result":"34,650"},
     ])),
    ("mathematics", "complex-analysis", "Complex Analysis", "complex-analysis",
     "Complex numbers, analytic functions, residues, and conformal maps.",
     "calculus.png", False, False, J([
        {"query":"|3 + 4i|","type":"modulus","result":"5"},
        {"query":"arg(1 + i)","type":"argument","result":"π/4"},
        {"query":"e^(i*pi)","type":"identity","result":"−1 (Euler's identity)"},
        {"query":"residue 1/(z^2 + 1) at z=i","type":"residue","result":"−i/2"},
     ])),
    ("mathematics", "differential-equations", "Differential Equations", "differential-equations",
     "Ordinary and partial differential equations and their analytic solutions.",
     "differential-equations.png", False, True, J([
        {"query":"solve y' = y","type":"ode","result":"y(x) = C · e^x"},
        {"query":"solve y'' + y = 0","type":"linear ode","result":"y(x) = A cos x + B sin x"},
        {"query":"y' = x*y","type":"separable","result":"y = C · e^(x^2/2)"},
        {"query":"heat equation u_t = u_xx","type":"pde","result":"Solution via separation of variables"},
     ])),
    ("mathematics", "math-functions", "Mathematical Functions", "mathematical-functions",
     "Elementary and special functions: gamma, Bessel, hypergeometric.",
     "calculus.png", False, False, J([
        {"query":"Gamma(7)","type":"special","result":"720"},
        {"query":"erf(1)","type":"special","result":"0.8427"},
        {"query":"BesselJ(0, 5)","type":"bessel","result":"≈ −0.1776"},
        {"query":"zeta(2)","type":"zeta","result":"π²/6 ≈ 1.6449"},
     ])),
    ("mathematics", "optimization", "Optimization", "optimization",
     "Linear, nonlinear, integer, and convex optimization problems.",
     "calculus.png", False, False, J([
        {"query":"minimize x^2 + y^2 subject to x + y = 1","type":"lagrange","result":"x = y = 1/2, min = 1/2"},
        {"query":"maximize 2x + 3y, x+y<=4, x,y>=0","type":"linear","result":"x=0, y=4, max = 12"},
        {"query":"travelling salesman 4 cities","type":"combinatorial","result":"3 distinct cycles"},
     ])),
    ("mathematics", "math-puzzles", "Math Puzzles", "math-puzzles",
     "Classic puzzles, magic squares, and combinatorial games.",
     "discrete-math.png", False, False, J([
        {"query":"3x3 magic square sum","type":"puzzle","result":"15"},
        {"query":"number of Rubik's cube positions","type":"combinatorics","result":"4.3 × 10¹⁹"},
        {"query":"Monty Hall switch probability","type":"probability","result":"2/3"},
        {"query":"Tower of Hanoi 10 disks","type":"recursion","result":"1023 moves"},
     ])),
    ("mathematics", "math-history", "Mathematical History", "mathematical-history",
     "Mathematicians, famous theorems, and milestones.",
     "people.png", False, False, J([
        {"query":"Pythagoras","type":"person","result":"Greek mathematician, c. 570 BC, Pythagorean theorem"},
        {"query":"Fermat's Last Theorem proved","type":"theorem","result":"Andrew Wiles, 1994"},
        {"query":"Euler publications count","type":"trivia","result":"≈ 866 publications"},
        {"query":"Ramanujan birth year","type":"trivia","result":"1887"},
     ])),

    # --- Science & Technology extras ---
    ("science-and-technology", "biological-sciences", "Cells & Genetics", "cells-genetics",
     "Cells, DNA, genes, and the molecular machinery of life.",
     "life-sciences.png", False, False, J([
        {"query":"genes in human genome","type":"genetics","result":"≈ 19,900–20,500 protein-coding genes"},
        {"query":"mitochondrial DNA length","type":"genetics","result":"16,569 base pairs"},
        {"query":"ribosome size eukaryotic","type":"cell","result":"80S (60S + 40S subunits)"},
     ])),
    ("science-and-technology", "biological-sciences", "Ecology", "ecology",
     "Populations, ecosystems, biodiversity, and food webs.",
     "life-sciences.png", False, False, J([
        {"query":"largest biome by area","type":"ecology","result":"Oceanic — covers 71% of Earth"},
        {"query":"species described globally","type":"biodiversity","result":"≈ 1.9 million described"},
        {"query":"carbon stored in Amazon rainforest","type":"climate","result":"≈ 100 billion tonnes"},
     ])),
    ("science-and-technology", "computer-science", "Computer Science", "computer-science",
     "Algorithms, complexity, data structures, encoding & cryptography.",
     "discrete-math.png", True, True, J([
        {"query":"O(n log n) sorting algorithms","type":"algorithm","result":"Merge sort, heap sort, Tim sort"},
        {"query":"binary 11010","type":"encoding","result":"= 26 in decimal"},
        {"query":"SHA-256 of 'hello'","type":"hash","result":"2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824"},
        {"query":"P vs NP","type":"theory","result":"Major open problem; P ⊆ NP, equality unknown"},
     ])),
    ("science-and-technology", "materials-science", "Materials Science", "materials",
     "Properties of metals, polymers, composites, and crystals.",
     "physics.png", False, False, J([
        {"query":"Young's modulus steel","type":"property","result":"≈ 200 GPa"},
        {"query":"density of titanium","type":"property","result":"4.506 g/cm³"},
        {"query":"melting point of tungsten","type":"property","result":"3422 °C"},
     ])),
    ("science-and-technology", "engineering-detail", "Civil Engineering", "civil-engineering",
     "Structural calculations, beams, materials, and concrete.",
     "engineering.png", False, False, J([
        {"query":"compressive strength of standard concrete","type":"material","result":"≈ 20–40 MPa (typical mix)"},
        {"query":"steel rebar grade 60 yield","type":"material","result":"413 MPa"},
        {"query":"deflection simply-supported beam 4m UDL 2 kN/m","type":"structural","result":"depends on EI; ≈ 5wL^4/384EI"},
     ])),
    ("science-and-technology", "transportation", "Transportation", "transportation",
     "Cars, planes, ships, and fuel economy data.",
     "engineering.png", False, False, J([
        {"query":"cruising speed Boeing 787","type":"aviation","result":"≈ 903 km/h (Mach 0.85)"},
        {"query":"top speed Bugatti Chiron","type":"car","result":"≈ 420 km/h"},
        {"query":"fuel economy of a Toyota Prius","type":"car","result":"≈ 5.0 L/100 km combined"},
     ])),
    ("science-and-technology", "space-spaceflight", "Spaceflight", "spaceflight",
     "Rockets, missions, payloads, and orbital mechanics.",
     "astronomy.png", False, False, J([
        {"query":"Saturn V payload to LEO","type":"rocket","result":"≈ 140,000 kg"},
        {"query":"Falcon 9 payload to GTO","type":"rocket","result":"≈ 8,300 kg"},
        {"query":"distance Earth to Moon","type":"orbital","result":"≈ 384,400 km (mean)"},
     ])),
    ("science-and-technology", "tech-world", "Technological World", "tech-world",
     "Phones, cameras, networks, and consumer-tech specs.",
     "engineering.png", False, False, J([
        {"query":"4G LTE peak download","type":"network","result":"≈ 1 Gbps theoretical"},
        {"query":"WiFi 6 max speed","type":"network","result":"≈ 9.6 Gbps theoretical"},
        {"query":"USB-C max power delivery","type":"hardware","result":"240 W (USB PD 3.1)"},
     ])),
    ("science-and-technology", "web-software", "Web & Software", "web-software",
     "HTTP, IP, regex, encoding, and developer utilities.",
     "discrete-math.png", False, False, J([
        {"query":"HTTP status 418","type":"http","result":"I'm a teapot"},
        {"query":"IPv6 address length","type":"network","result":"128 bits"},
        {"query":"base64 of 'hello'","type":"encoding","result":"aGVsbG8="},
        {"query":"regex match email","type":"regex","result":"^[\\w.+-]+@[\\w-]+\\.[\\w.-]+$"},
     ])),

    # --- Society & Culture extras ---
    ("society-and-culture", "economics", "Economics", "economics",
     "GDP, inflation, trade flows, and macroeconomic indicators.",
     "economics.png", False, False, J([
        {"query":"world GDP 2023","type":"macro","result":"≈ $105 trillion (nominal)"},
        {"query":"inflation US 2022","type":"macro","result":"≈ 8.0% (CPI annual)"},
        {"query":"countries by GDP","type":"ranking","result":"US, China, Germany, Japan, India top 5"},
     ])),
    ("society-and-culture", "education", "Education", "education",
     "Schools, universities, degrees, and education indicators.",
     "people.png", False, False, J([
        {"query":"oldest university in the world","type":"history","result":"University of Bologna, 1088"},
        {"query":"literacy rate world 2022","type":"stat","result":"≈ 87%"},
        {"query":"Nobel Prize categories","type":"award","result":"6 categories incl. Economic Sciences"},
     ])),
    ("society-and-culture", "religion", "Religion", "religion",
     "Major world religions, demographics, and holy-day calculations.",
     "people.png", False, False, J([
        {"query":"largest religion","type":"demographics","result":"Christianity (~31% of world population)"},
        {"query":"date of Easter 2026","type":"date","result":"April 5, 2026"},
        {"query":"Ramadan 2026 start","type":"date","result":"≈ February 17, 2026"},
     ])),
    ("society-and-culture", "philosophy", "Philosophy", "philosophy",
     "Philosophers, schools, logic, and ethics references.",
     "people.png", False, False, J([
        {"query":"Socrates birth year","type":"trivia","result":"c. 470 BC"},
        {"query":"three laws of logic","type":"logic","result":"Identity, non-contradiction, excluded middle"},
        {"query":"trolley problem","type":"ethics","result":"Classic thought experiment in ethics"},
     ])),
    ("society-and-culture", "mythology", "Mythology", "mythology",
     "Greek, Norse, Roman, and world mythology references.",
     "people.png", False, False, J([
        {"query":"twelve Olympian gods","type":"greek","result":"Zeus, Hera, Poseidon, Demeter, Athena, Apollo, Artemis, Ares, Aphrodite, Hephaestus, Hermes, Dionysus"},
        {"query":"Norse mythology Asgard","type":"norse","result":"Realm of the Aesir gods, ruled by Odin"},
     ])),
    ("society-and-culture", "politics", "Politics", "politics",
     "Political systems, elections, parliaments, and indices.",
     "people.png", False, False, J([
        {"query":"members of UN Security Council","type":"un","result":"15 (5 permanent + 10 elected)"},
        {"query":"US Senate seats","type":"us","result":"100 (2 per state)"},
        {"query":"countries with parliamentary systems","type":"government","result":"UK, Germany, Japan, Canada, India, and 50+ more"},
     ])),
    ("society-and-culture", "popular-culture", "Popular Culture", "popular-culture",
     "Movies, music, TV, video games, and cultural icons.",
     "arts-media.png", False, False, J([
        {"query":"Beatles albums","type":"music","result":"13 studio albums (UK discography)"},
        {"query":"Marvel Cinematic Universe films","type":"film","result":"30+ feature films and counting"},
        {"query":"highest-rated TV show IMDb","type":"tv","result":"Breaking Bad / Band of Brothers — 9.5"},
     ])),
    ("society-and-culture", "sports-society", "Sports History", "sports-history",
     "Olympics, leagues, athletes, and major events.",
     "entertainment.png", False, False, J([
        {"query":"first modern Olympics","type":"olympics","result":"Athens 1896"},
        {"query":"FIFA World Cup winners","type":"football","result":"Brazil (5), Germany (4), Italy (4), Argentina (3)"},
        {"query":"NBA Finals MVP record","type":"basketball","result":"Michael Jordan — 6 times"},
     ])),

    # --- Everyday Life extras ---
    ("everyday-life", "cooking", "Cooking & Recipes", "cooking",
     "Recipes, cooking-time math, substitutions, and food chemistry.",
     "food-science.png", False, True, J([
        {"query":"tbsp in a cup","type":"conversion","result":"16 tablespoons"},
        {"query":"convert 350 F to C","type":"temperature","result":"≈ 177 °C"},
        {"query":"egg substitute baking","type":"recipe","result":"1/4 cup applesauce or 1 tbsp flax + 3 tbsp water"},
        {"query":"cooking time turkey 12 lb","type":"recipe","result":"≈ 3 hrs at 325 °F"},
     ])),
    ("everyday-life", "gardening", "Gardening", "gardening",
     "Plant facts, growing zones, soil, and gardening computations.",
     "food-science.png", False, False, J([
        {"query":"USDA zone Boston","type":"zone","result":"6b/7a"},
        {"query":"tomato germination temperature","type":"plant","result":"21–27 °C optimal"},
        {"query":"compost C:N ratio target","type":"soil","result":"≈ 25–30 : 1"},
     ])),
    ("everyday-life", "pets", "Pets", "pets",
     "Dog and cat breeds, lifespans, weights, and care.",
     "life-sciences.png", False, False, J([
        {"query":"golden retriever lifespan","type":"dog","result":"≈ 10–12 years"},
        {"query":"cat normal body temperature","type":"cat","result":"38.1–39.2 °C (100.5–102.5 °F)"},
        {"query":"how much to feed a 30 lb dog","type":"care","result":"≈ 1¾ cups dry food / day"},
     ])),
    ("everyday-life", "dates-times", "Dates & Times", "dates-times",
     "Calendars, time zones, ages, holidays, and date arithmetic.",
     "household-math.png", False, False, J([
        {"query":"days in 2024","type":"calendar","result":"366 (leap year)"},
        {"query":"days between Jan 1 2025 and Dec 31 2025","type":"diff","result":"364"},
        {"query":"current time UTC","type":"clock","result":"Server time in UTC"},
     ])),
    ("everyday-life", "hobbies-games", "Hobbies & Games", "hobbies-games",
     "Card games, board games, RPG dice, and probability of play.",
     "probability.png", False, False, J([
        {"query":"poker hand royal flush probability","type":"cards","result":"≈ 1 in 649,740"},
        {"query":"expected sum of 4d6","type":"dice","result":"14"},
        {"query":"chess possible positions","type":"games","result":"≈ 10⁴⁰ legal positions (Shannon estimate 10¹²⁰ games)"},
     ])),
    ("everyday-life", "music-audio", "Music & Audio", "music-audio",
     "Notes, frequencies, scales, decibels, audio computations.",
     "household-science.png", False, False, J([
        {"query":"frequency of A4","type":"note","result":"440 Hz (concert pitch)"},
        {"query":"semitone ratio","type":"interval","result":"2^(1/12) ≈ 1.05946"},
        {"query":"decibel doubling","type":"audio","result":"≈ +3 dB doubles power"},
     ])),
    ("everyday-life", "photography", "Photography", "photography",
     "Aperture, shutter, ISO, depth of field, exposure.",
     "household-science.png", False, False, J([
        {"query":"f-stop sequence","type":"aperture","result":"f/1.4, 2, 2.8, 4, 5.6, 8, 11, 16, 22"},
        {"query":"sunny 16 rule","type":"exposure","result":"At f/16, shutter ≈ 1/ISO in bright sun"},
        {"query":"DoF 50mm f/4 distance 3m","type":"dof","result":"≈ 0.5 m (sensor-dependent)"},
     ])),
    ("everyday-life", "words-letters", "Words & Letters", "words-letters",
     "Word lengths, frequencies, scrabble scores, palindromes.",
     "linguistics.png", False, False, J([
        {"query":"longest English word","type":"word","result":"pneumonoultramicroscopicsilicovolcanoconiosis (45)"},
        {"query":"scrabble score 'quizzes'","type":"scrabble","result":"34 (Q=10, U=1, I=1, Z=10, Z=10, E=1, S=1)"},
        {"query":"palindrome examples","type":"word","result":"racecar, level, deified, rotator"},
     ])),
]

# ---------------------------------------------------------------------------
# (3)  Computation results — additions (generic, no required_specifiers)
# ---------------------------------------------------------------------------
# Each item: (input_query, parsed_input, plaintext, category, subcategory,
#             keywords, related_list, topic_slug)
# pods will be built as [{"title":"Result","plaintext":...},{"title":"Parsed input",...}]

EXTRA_RESULTS: list[tuple[str, str, str, str, str, str, list[str], str]] = []

def E(q, parsed, ans, cat, sub, kw, related, slug):
    EXTRA_RESULTS.append((q, parsed, ans, cat, sub, kw, related, slug))

# --- Arithmetic & algebra (curated) ---
E("2 + 2", "2 + 2", "4", "mathematics", "algebra",
  "arithmetic addition basic", ["3 + 3", "100 + 200"], "algebra")
E("100!", "100!", "9.3326215443944152681699238856266700e157",
  "mathematics", "algebra", "factorial 100 large number",
  ["10!", "50!", "200!"], "algebra")
E("solve x^2 - 5x + 6 = 0", "x^2 − 5x + 6 = 0", "x = 2 or x = 3",
  "mathematics", "algebra", "quadratic equation roots",
  ["solve x^2 - x - 1 = 0", "solve x^2 + 1 = 0"], "algebra")
E("solve x^2 + 2x + 5 = 0", "x^2 + 2x + 5 = 0",
  "x = −1 + 2i or x = −1 − 2i",
  "mathematics", "algebra", "quadratic complex roots",
  ["solve x^2 + 4 = 0"], "algebra")
E("quadratic formula", "(-b ± sqrt(b^2 - 4ac))/(2a)",
  "Roots of ax^2 + bx + c = 0 are x = (−b ± √(b²−4ac))/(2a)",
  "mathematics", "algebra", "quadratic formula roots",
  ["discriminant"], "algebra")
E("factor x^4 - 16", "x^4 − 16",
  "(x − 2)(x + 2)(x² + 4)",
  "mathematics", "algebra", "factoring polynomial difference squares",
  ["factor x^3 - 27"], "algebra")
E("solve 2^x = 32", "2^x = 32", "x = 5",
  "mathematics", "algebra", "exponential equation power 2 32",
  ["solve 3^x = 81"], "algebra")
E("solve log(x) = 2", "log10(x) = 2", "x = 100",
  "mathematics", "algebra", "logarithm equation log base 10",
  ["solve ln(x) = 1"], "algebra")

# --- Calculus curated ---
E("d/dx sin(x)", "d/dx [sin(x)]", "cos(x)",
  "mathematics", "calculus", "derivative sine trig", ["d/dx cos(x)"], "calculus")
E("d/dx cos(x)", "d/dx [cos(x)]", "−sin(x)",
  "mathematics", "calculus", "derivative cosine trig", ["d/dx sin(x)"], "calculus")
E("d/dx e^x", "d/dx [e^x]", "e^x",
  "mathematics", "calculus", "derivative exponential e",
  ["d/dx ln(x)"], "calculus")
E("d/dx ln(x)", "d/dx [ln(x)]", "1/x",
  "mathematics", "calculus", "derivative natural log",
  ["d/dx log(x)"], "calculus")
E("integrate 1/x dx", "∫ 1/x dx", "ln|x| + C",
  "mathematics", "calculus", "integral logarithm 1/x antiderivative",
  ["integrate 1/(x^2+1) dx"], "calculus")
E("integrate e^x dx", "∫ e^x dx", "e^x + C",
  "mathematics", "calculus", "integral exponential e antiderivative",
  ["integrate e^(-x) dx"], "calculus")
E("integrate cos(x) dx", "∫ cos(x) dx", "sin(x) + C",
  "mathematics", "calculus", "integral cosine antiderivative",
  ["integrate sin(x) dx"], "calculus")
E("integrate x^n dx", "∫ x^n dx", "x^(n+1)/(n+1) + C   (n ≠ −1)",
  "mathematics", "calculus", "power rule integral antiderivative",
  ["integrate x^2 dx"], "calculus")
E("limit x->infinity of (1 + 1/x)^x", "lim_{x→∞} (1 + 1/x)^x", "e ≈ 2.71828",
  "mathematics", "calculus", "limit e definition infinity",
  ["limit (1 + 1/n)^n"], "calculus")
E("limit x->0 of (e^x - 1)/x", "lim_{x→0} (e^x − 1)/x", "1",
  "mathematics", "calculus", "limit exponential L'Hopital",
  ["limit x->0 (sin x)/x"], "calculus")

# --- Statistics curated ---
E("standard deviation {2,4,4,4,5,5,7,9}", "σ({2,4,4,4,5,5,7,9})",
  "Sample SD ≈ 2.138, population SD = 2",
  "mathematics", "statistics", "standard deviation sample population",
  ["variance {2,4,4,4,5,5,7,9}"], "statistics")
E("variance {1,2,3,4,5}", "Var({1,...,5})", "Sample variance = 2.5, population = 2.0",
  "mathematics", "statistics", "variance dataset",
  ["mean {1,2,3,4,5}"], "statistics")
E("median {3,1,4,1,5,9,2,6,5}", "median",
  "Median = 4 (sorted: 1,1,2,3,4,5,5,6,9)",
  "mathematics", "statistics", "median sorted middle dataset",
  ["mode {3,1,4,1,5,9,2,6,5}"], "statistics")
E("z-score x=85 mean=75 sd=5", "(x − μ)/σ", "z = 2.0",
  "mathematics", "statistics", "z-score standardize",
  ["t-score"], "statistics")
E("correlation (1,2)(2,4)(3,6)(4,8)", "Pearson r", "r = 1.0 (perfect linear)",
  "mathematics", "statistics", "correlation pearson linear",
  ["covariance"], "statistics")

# --- Geometry curated ---
E("area circle r=10", "π r^2 with r=10",
  "≈ 314.159 square units (exact: 100π)",
  "mathematics", "geometry", "circle area radius",
  ["circumference circle r=10"], "geometry")
E("circumference circle r=10", "2π r with r=10",
  "≈ 62.832 units (exact: 20π)",
  "mathematics", "geometry", "circle circumference radius",
  ["area circle r=10"], "geometry")
E("volume sphere r=5", "(4/3) π r^3 with r=5",
  "≈ 523.599 cubic units (exact: 500π/3)",
  "mathematics", "geometry", "sphere volume radius",
  ["surface area sphere r=5"], "geometry")
E("surface area sphere r=5", "4π r^2 with r=5",
  "≈ 314.159 square units (exact: 100π)",
  "mathematics", "geometry", "sphere surface area",
  ["volume sphere r=5"], "geometry")
E("area triangle base=6 height=8", "(1/2)·b·h",
  "24 square units",
  "mathematics", "geometry", "triangle area base height",
  ["area triangle sides 3 4 5"], "geometry")
E("Pythagorean theorem", "a^2 + b^2 = c^2",
  "Right-triangle hypotenuse: c = √(a² + b²)",
  "mathematics", "geometry", "pythagorean right triangle",
  ["distance two points"], "geometry")

# --- Number theory curated ---
E("is 97 prime?", "PrimeQ[97]", "Yes — 97 is prime.",
  "mathematics", "number-theory", "primality test",
  ["is 91 prime?", "is 100 prime?"], "number-theory")
E("is 91 prime?", "PrimeQ[91]",
  "No — 91 = 7 × 13.",
  "mathematics", "number-theory", "primality composite factor",
  ["is 89 prime?"], "number-theory")
E("nth prime n=100", "Prime[100]", "541",
  "mathematics", "number-theory", "nth prime sequence",
  ["nth prime n=1000"], "number-theory")
E("prime counting pi(100)", "π(100)", "25 primes ≤ 100",
  "mathematics", "number-theory", "prime counting function",
  ["pi(1000)"], "number-theory")
E("Mersenne prime", "M_p = 2^p − 1", "Examples: 3, 7, 31, 127, 8191, ...",
  "mathematics", "number-theory", "mersenne prime power 2",
  ["perfect numbers"], "number-theory")
E("Fermat prime", "F_n = 2^(2^n) + 1",
  "Known Fermat primes: 3, 5, 17, 257, 65537.",
  "mathematics", "number-theory", "fermat prime",
  ["Mersenne prime"], "number-theory")

# --- Trigonometry curated ---
for d, v in [(0, "0"), (30, "1/2"), (45, "√2/2"), (60, "√3/2"), (90, "1")]:
    E(f"sin({d} degrees)", f"sin({d}°)", v,
      "mathematics", "trigonometry", f"sine {d} degrees value",
      [f"cos({d} degrees)", f"tan({d} degrees)"], "trigonometry")
E("law of sines", "a/sin A = b/sin B = c/sin C",
  "Law of sines relates sides to opposite angles.",
  "mathematics", "trigonometry", "law of sines triangle",
  ["law of cosines"], "trigonometry")

# --- Linear algebra curated ---
E("identity matrix 3x3", "I_3",
  "{{1,0,0},{0,1,0},{0,0,1}}",
  "mathematics", "linear-algebra", "identity matrix 3 by 3",
  ["zero matrix 3x3"], "linear-algebra")
E("rank of {{1,2,3},{2,4,6},{1,1,1}}", "rank",
  "rank = 2 (rows 1 and 2 are linearly dependent)",
  "mathematics", "linear-algebra", "matrix rank linearly dependent",
  ["nullity"], "linear-algebra")
E("transpose {{1,2,3},{4,5,6}}", "M^T",
  "{{1,4},{2,5},{3,6}}",
  "mathematics", "linear-algebra", "matrix transpose",
  ["inverse matrix"], "linear-algebra")

# --- Probability curated ---
E("expected value of a die", "E[X], fair d6", "3.5",
  "mathematics", "probability", "expected value dice fair",
  ["variance of a die"], "probability")
E("variance of a die", "Var[X], fair d6", "35/12 ≈ 2.9167",
  "mathematics", "probability", "variance dice fair",
  ["expected value of a die"], "probability")
E("Bayes theorem", "P(A|B) = P(B|A) P(A) / P(B)",
  "Bayes' theorem inverts conditional probabilities.",
  "mathematics", "probability", "bayes theorem conditional",
  ["conditional probability"], "probability")

# --- Physics curated ---
E("speed of light", "c", "299,792,458 m/s (exact)",
  "science-and-technology", "physics", "speed of light constant c",
  ["Planck constant"], "physics")
E("Planck constant", "h", "6.62607015 × 10⁻³⁴ J·s (exact)",
  "science-and-technology", "physics", "planck constant h",
  ["reduced Planck"], "physics")
E("gravitational constant", "G", "6.67430 × 10⁻¹¹ N·m²/kg²",
  "science-and-technology", "physics", "gravitational constant newton G",
  ["acceleration due to gravity"], "physics")
E("acceleration due to gravity Earth", "g", "9.80665 m/s² (standard)",
  "science-and-technology", "physics", "gravity g standard earth",
  ["gravity moon"], "physics")
E("kinetic energy m=2kg v=10m/s", "½ m v²", "100 J",
  "science-and-technology", "physics", "kinetic energy formula",
  ["potential energy"], "physics")
E("Bohr radius", "a_0", "5.29177 × 10⁻¹¹ m ≈ 52.9 pm",
  "science-and-technology", "physics", "bohr radius hydrogen",
  ["Rydberg constant"], "physics")
E("Rydberg constant", "R", "1.0973731568160 × 10⁷ m⁻¹",
  "science-and-technology", "physics", "rydberg constant hydrogen",
  ["Bohr radius"], "physics")
E("Avogadro number", "N_A", "6.02214076 × 10²³ /mol (exact)",
  "science-and-technology", "physics", "avogadro number mole",
  ["Boltzmann constant"], "physics")
E("Boltzmann constant", "k_B", "1.380649 × 10⁻²³ J/K (exact)",
  "science-and-technology", "physics", "boltzmann constant",
  ["gas constant"], "physics")
E("gas constant", "R", "8.314462618 J/(mol·K)",
  "science-and-technology", "physics", "gas constant ideal gas",
  ["Avogadro number"], "physics")

# --- Chemistry curated (elements + properties) ---
ELEMENTS = [
    ("hydrogen", 1, 1.008, "1s¹", "−259.16 °C", "−252.87 °C"),
    ("helium",   2, 4.0026, "1s²", "−272.20 °C", "−268.93 °C"),
    ("lithium",  3, 6.94,  "[He] 2s¹", "180.50 °C", "1342 °C"),
    ("oxygen",   8, 15.999,"[He] 2s² 2p⁴", "−218.79 °C", "−182.96 °C"),
    ("nitrogen", 7, 14.007,"[He] 2s² 2p³", "−210.00 °C", "−195.79 °C"),
    ("sodium",  11, 22.989,"[Ne] 3s¹", "97.79 °C", "883 °C"),
    ("aluminum",13, 26.982,"[Ne] 3s² 3p¹", "660.32 °C", "2519 °C"),
    ("silicon", 14, 28.085,"[Ne] 3s² 3p²", "1414 °C", "3265 °C"),
    ("iron",    26, 55.845,"[Ar] 3d⁶ 4s²", "1538 °C", "2862 °C"),
    ("copper",  29, 63.546,"[Ar] 3d¹⁰ 4s¹","1084.62 °C","2562 °C"),
    ("zinc",    30, 65.38, "[Ar] 3d¹⁰ 4s²","419.53 °C","907 °C"),
    ("silver",  47, 107.87,"[Kr] 4d¹⁰ 5s¹","961.78 °C","2162 °C"),
    ("gold",    79, 196.97,"[Xe] 4f¹⁴ 5d¹⁰ 6s¹","1064.18 °C","2856 °C"),
    ("mercury", 80, 200.59,"[Xe] 4f¹⁴ 5d¹⁰ 6s²","−38.83 °C","356.73 °C"),
    ("lead",    82, 207.2, "[Xe] 4f¹⁴ 5d¹⁰ 6s² 6p²","327.46 °C","1749 °C"),
    ("uranium", 92, 238.03,"[Rn] 5f³ 6d¹ 7s²","1135 °C","4131 °C"),
]
for name, z, mass, conf, mp, bp in ELEMENTS:
    E(name, name.title(),
      f"Atomic number {z}, mass {mass}, electron config {conf}. mp {mp}, bp {bp}.",
      "science-and-technology", "chemistry",
      f"element {name} atomic number {z} mass {mass}",
      [f"melting point {name}", f"boiling point {name}"], "chemistry")

MOLECULES = [
    ("water", "H2O", 18.015),
    ("carbon dioxide", "CO2", 44.009),
    ("methane", "CH4", 16.043),
    ("ethanol", "C2H6O", 46.069),
    ("glucose", "C6H12O6", 180.156),
    ("ammonia", "NH3", 17.031),
    ("sodium chloride", "NaCl", 58.443),
    ("sulfuric acid", "H2SO4", 98.079),
    ("acetic acid", "C2H4O2", 60.052),
    ("benzene", "C6H6", 78.114),
    ("aspirin", "C9H8O4", 180.158),
    ("caffeine", "C8H10N4O2", 194.194),
]
for name, formula, mw in MOLECULES:
    E(f"molecular weight {name}", f"M({formula})",
      f"{formula}: {mw} g/mol",
      "science-and-technology", "chemistry",
      f"molecular weight mass {name} {formula}",
      [f"{name} structure"], "chemistry")

# --- Astronomy curated ---
PLANETS = [
    ("Mercury", "4879 km", "3.301e23 kg", "57.91 million km", "88 days"),
    ("Venus",   "12104 km","4.867e24 kg","108.21 million km","224.7 days"),
    ("Earth",   "12742 km","5.972e24 kg","149.60 million km","365.25 days"),
    ("Mars",    "6779 km", "6.39e23 kg", "227.94 million km","687 days"),
    ("Jupiter","139820 km","1.898e27 kg","778.41 million km","11.86 years"),
    ("Saturn", "116460 km","5.683e26 kg","1.434 billion km","29.46 years"),
    ("Uranus",  "50724 km","8.681e25 kg","2.871 billion km","84.01 years"),
    ("Neptune","49244 km","1.024e26 kg","4.495 billion km","164.79 years"),
]
for p, diam, mass, dist, period in PLANETS:
    E(f"planet {p}", p,
      f"{p}: diameter {diam}, mass {mass}, distance from Sun {dist}, orbital period {period}.",
      "science-and-technology", "astronomy",
      f"planet {p.lower()} diameter mass orbit",
      [f"moons of {p}", f"mass of {p}"], "astronomy")

E("number of moons Jupiter", "moons", "95 confirmed (as of 2024)",
  "science-and-technology", "astronomy", "jupiter moons count",
  ["moons of Saturn"], "astronomy")
E("number of moons Saturn", "moons", "146 confirmed (as of 2024)",
  "science-and-technology", "astronomy", "saturn moons count",
  ["moons of Jupiter"], "astronomy")
E("Andromeda Galaxy distance", "M31 distance", "≈ 2.537 million ly",
  "science-and-technology", "astronomy", "andromeda galaxy distance",
  ["Milky Way diameter"], "astronomy")
E("Milky Way diameter", "Milky Way", "≈ 100,000 light years",
  "science-and-technology", "astronomy", "milky way galaxy diameter",
  ["Andromeda Galaxy distance"], "astronomy")

# --- Earth sciences curated ---
E("highest mountain on Earth", "Mt Everest",
  "Mount Everest — 8,848.86 m above sea level (Nepal/Tibet).",
  "science-and-technology", "earth-science",
  "highest mountain everest elevation",
  ["tallest mountain measured from base"], "earth-science")
E("deepest ocean trench", "Mariana Trench",
  "Mariana Trench, Challenger Deep — 10,994 m.",
  "science-and-technology", "earth-science",
  "deepest ocean trench mariana challenger",
  ["depth of Pacific Ocean"], "earth-science")
E("Earth circumference", "C", "≈ 40,075 km (equatorial)",
  "science-and-technology", "earth-science",
  "earth circumference equatorial",
  ["Earth radius"], "earth-science")
E("Earth radius", "R", "Equatorial: 6,378 km; polar: 6,357 km",
  "science-and-technology", "earth-science", "earth radius equatorial polar",
  ["Earth mass"], "earth-science")
E("Earth mass", "M_Earth", "5.972 × 10²⁴ kg",
  "science-and-technology", "earth-science", "earth mass",
  ["Earth radius"], "earth-science")

# --- Weather curated ---
E("hottest temperature ever recorded", "record T",
  "≈ 56.7 °C (134 °F), Furnace Creek, CA — July 10, 1913.",
  "science-and-technology", "weather", "hottest temperature record death valley",
  ["coldest temperature recorded"], "weather")
E("coldest temperature ever recorded", "record T",
  "−89.2 °C (−128.6 °F), Vostok Station, Antarctica — July 21, 1983.",
  "science-and-technology", "weather", "coldest temperature record vostok",
  ["hottest temperature recorded"], "weather")
E("Saffir-Simpson scale", "categories",
  "Cat 1: 119–153 km/h; Cat 2: 154–177; Cat 3: 178–208; Cat 4: 209–251; Cat 5: ≥252.",
  "science-and-technology", "weather", "hurricane saffir simpson scale",
  ["Fujita scale"], "weather")
E("Fujita scale", "F-scale",
  "EF0: 105–137 km/h … EF5: >322 km/h (tornado intensity).",
  "science-and-technology", "weather", "tornado fujita scale categories",
  ["Saffir-Simpson scale"], "weather")

# --- Units & measures (auto-generated conversions) ---
CONVERSIONS = [
    ("1 mile in km", "1 mi", "≈ 1.609344 km"),
    ("1 km in miles", "1 km", "≈ 0.621371 mi"),
    ("1 foot in cm", "1 ft", "30.48 cm"),
    ("1 inch in mm", "1 in", "25.4 mm"),
    ("1 yard in meters", "1 yd", "0.9144 m"),
    ("1 light year in km", "1 ly", "≈ 9.461 × 10¹² km"),
    ("1 parsec in light years", "1 pc", "≈ 3.262 ly"),
    ("1 AU in km", "1 AU", "149,597,870.7 km (exact)"),
    ("1 acre in m^2", "1 ac", "4046.86 m²"),
    ("1 hectare in m^2", "1 ha", "10,000 m²"),
    ("1 gallon (US) in liters", "1 gal", "3.78541 L"),
    ("1 gallon (UK) in liters", "1 gal (UK)", "4.54609 L"),
    ("1 ounce in grams", "1 oz", "28.3495 g"),
    ("1 pound in kg", "1 lb", "0.453592 kg"),
    ("1 ton (metric) in kg", "1 t", "1000 kg"),
    ("1 calorie in joules", "1 cal", "4.184 J"),
    ("1 kWh in joules", "1 kWh", "3.6 × 10⁶ J"),
    ("1 horsepower in watts", "1 hp", "745.7 W"),
    ("1 bar in pascals", "1 bar", "100,000 Pa"),
    ("1 atmosphere in kPa", "1 atm", "101.325 kPa"),
    ("0 Celsius in Fahrenheit", "0 °C", "32 °F"),
    ("100 Celsius in Fahrenheit", "100 °C", "212 °F"),
    ("0 Kelvin in Celsius", "0 K", "−273.15 °C"),
    ("knot to km/h", "1 knot", "≈ 1.852 km/h"),
    ("mach 1 in km/h", "Mach 1 (sea level)", "≈ 1235 km/h"),
]
for q, parsed, ans in CONVERSIONS:
    E(q, parsed, ans, "science-and-technology", "units-measures",
      "unit conversion " + q.lower(), [], "units-measures")

# --- People & geography quick facts ---
PEOPLE_FACTS = [
    ("Isaac Newton", "English physicist (1643–1727); laws of motion, calculus, gravitation."),
    ("Galileo Galilei", "Italian astronomer (1564–1642); telescopic observation of Jupiter's moons."),
    ("Nikola Tesla", "Serbian-American inventor (1856–1943); AC electrical system."),
    ("Charles Darwin", "English naturalist (1809–1882); theory of evolution by natural selection."),
    ("Ada Lovelace", "English mathematician (1815–1852); first computer programmer."),
    ("Alan Turing", "English mathematician (1912–1954); foundational computer science."),
    ("Stephen Hawking", "English physicist (1942–2018); black-hole thermodynamics."),
    ("Carl Friedrich Gauss", "German mathematician (1777–1855); 'Prince of Mathematicians'."),
    ("Srinivasa Ramanujan", "Indian mathematician (1887–1920); deep results in number theory."),
    ("Emmy Noether", "German mathematician (1882–1935); Noether's theorem in physics."),
]
for who, fact in PEOPLE_FACTS:
    E(who, who, fact,
      "society-and-culture", "people",
      "person biography " + who.lower(),
      [], "people")

COUNTRIES = [
    ("France", "Paris", "67.97 million", "643,801 km²", "Euro (€)"),
    ("Japan", "Tokyo", "125.7 million", "377,975 km²", "Yen (¥)"),
    ("Canada", "Ottawa", "40.1 million", "9,984,670 km²", "Canadian dollar (CAD)"),
    ("Australia", "Canberra", "26.5 million", "7,692,024 km²", "Australian dollar (AUD)"),
    ("India", "New Delhi", "1.43 billion", "3,287,263 km²", "Indian rupee (₹)"),
    ("Mexico", "Mexico City", "128.5 million", "1,964,375 km²", "Mexican peso ($)"),
    ("Egypt", "Cairo", "111.0 million", "1,001,450 km²", "Egyptian pound (E£)"),
    ("Italy", "Rome", "58.85 million", "301,340 km²", "Euro (€)"),
    ("Spain", "Madrid", "48.59 million", "505,990 km²", "Euro (€)"),
    ("South Korea", "Seoul", "51.74 million", "100,210 km²", "Korean won (₩)"),
    ("Sweden", "Stockholm", "10.55 million", "450,295 km²", "Swedish krona (kr)"),
    ("Argentina", "Buenos Aires", "46.23 million", "2,780,400 km²", "Argentine peso ($)"),
    ("Nigeria", "Abuja", "223.8 million", "923,768 km²", "Naira (₦)"),
    ("Switzerland", "Bern", "8.85 million", "41,285 km²", "Swiss franc (CHF)"),
    ("Norway", "Oslo", "5.49 million", "385,207 km²", "Norwegian krone (kr)"),
]
for c, cap, pop, area, curr in COUNTRIES:
    E(c, c,
      f"{c}: capital {cap}, population {pop}, area {area}, currency {curr}.",
      "society-and-culture", "geography",
      f"country {c.lower()} capital population area",
      [f"capital of {c}"], "geography")
    E(f"capital of {c}", "capital", cap,
      "society-and-culture", "geography",
      f"capital {c.lower()} {cap.lower()}",
      [c], "geography")

# --- Finance curated ---
E("S&P 500 index components", "S&P 500", "500 large-cap US stocks",
  "society-and-culture", "finance", "s&p 500 index components",
  ["Dow Jones"], "finance")
E("compound interest formula", "A = P(1 + r/n)^(nt)",
  "Future value A given principal P, rate r, n compounding periods, time t.",
  "society-and-culture", "finance", "compound interest formula",
  ["simple interest"], "finance")
E("simple interest formula", "I = P r t", "Interest = principal × rate × time.",
  "society-and-culture", "finance", "simple interest formula",
  ["compound interest"], "finance")
E("rule of 72", "72 / rate(%)",
  "Years to double an investment ≈ 72 ÷ annual rate.",
  "society-and-culture", "finance", "rule of 72 doubling time",
  ["compound interest formula"], "finance")

# --- Linguistics curated ---
E("how many words in English", "English vocabulary",
  "≈ 170,000 in current use (Oxford English Dictionary).",
  "society-and-culture", "linguistics", "english language words count vocabulary",
  ["how many languages"], "linguistics")
E("most spoken language", "first language speakers",
  "Mandarin Chinese — ≈ 920 million native speakers.",
  "society-and-culture", "linguistics", "most spoken language mandarin",
  ["most spoken language total speakers"], "linguistics")
E("longest word in English", "longest word",
  "pneumonoultramicroscopicsilicovolcanoconiosis (45 letters)",
  "society-and-culture", "linguistics", "longest english word",
  ["palindrome examples"], "linguistics")

# --- Personal health curated ---
E("BMI formula", "BMI = weight(kg) / height(m)^2",
  "Body Mass Index — Underweight <18.5, Normal 18.5–24.9, Overweight 25–29.9, Obese ≥30.",
  "everyday-life", "personal-health", "bmi formula body mass index",
  ["BMR formula"], "personal-health")
E("BMR formula", "Mifflin-St Jeor",
  "Men: 10w + 6.25h − 5a + 5; Women: 10w + 6.25h − 5a − 161  (w in kg, h in cm, a in yr).",
  "everyday-life", "personal-health", "bmr basal metabolic rate mifflin",
  ["BMI formula"], "personal-health")
E("recommended daily calories", "kcal/day",
  "Adult women ≈ 1,800–2,400 kcal; adult men ≈ 2,200–3,000 kcal (varies).",
  "everyday-life", "personal-health", "daily calorie recommendation adult",
  ["BMR formula"], "personal-health")
E("normal blood pressure", "BP",
  "Normal: <120/80 mmHg.",
  "everyday-life", "personal-health", "blood pressure normal range",
  ["resting heart rate"], "personal-health")

# --- Personal finance curated ---
E("20% tip on $80", "20% × $80", "Tip $16.00, total $96.00",
  "everyday-life", "personal-finance", "tip percentage calculation 20",
  ["15% tip on $50"], "personal-finance")
E("15% tip on $50", "15% × $50", "Tip $7.50, total $57.50",
  "everyday-life", "personal-finance", "tip percentage calculation 15",
  ["20% tip on $80"], "personal-finance")
E("loan $25,000 at 5% for 7 years", "amortized monthly payment",
  "Monthly payment ≈ $353.27 (total interest ≈ $4,675).",
  "everyday-life", "personal-finance", "loan payment amortization",
  ["mortgage calculator"], "personal-finance")
E("inflation $100 in 2000 to 2024", "CPI adjustment",
  "≈ $180 in 2024 (US CPI cumulative).",
  "everyday-life", "personal-finance", "inflation adjustment cpi",
  ["compound interest formula"], "personal-finance")

# --- Travel curated ---
E("distance Tokyo to Sydney", "great-circle",
  "≈ 7,830 km (4,866 miles)",
  "everyday-life", "travel", "distance tokyo sydney",
  ["flight time Tokyo to Sydney"], "travel")
E("flight time Tokyo to Sydney", "block time",
  "≈ 9 h 45 m nonstop",
  "everyday-life", "travel", "flight time tokyo sydney",
  ["distance Tokyo to Sydney"], "travel")
E("time zone Los Angeles", "tz",
  "PT (UTC−8 standard, UTC−7 daylight).",
  "everyday-life", "travel", "time zone los angeles pacific",
  ["time zone New York"], "travel")
E("time zone New York", "tz",
  "ET (UTC−5 standard, UTC−4 daylight).",
  "everyday-life", "travel", "time zone new york eastern",
  ["time zone Los Angeles"], "travel")

# --- Household math curated ---
E("how many days until New Year 2027", "diff to 2027-01-01",
  "Computed from today's reference (mirror date 2026-04-15).",
  "everyday-life", "household-math", "days until new year 2027",
  ["days until Christmas"], "household-math")
E("1/2 + 2/3", "1/2 + 2/3", "7/6 ≈ 1.1667",
  "everyday-life", "household-math", "fraction addition",
  ["3/4 + 1/8"], "household-math")
E("3/4 + 1/8", "3/4 + 1/8", "7/8 = 0.875",
  "everyday-life", "household-math", "fraction addition mixed",
  ["1/2 + 2/3"], "household-math")
E("percent change 50 to 65", "(65 − 50)/50",
  "30% increase",
  "everyday-life", "household-math", "percent change increase",
  ["percent change 100 to 75"], "household-math")
E("percent change 100 to 75", "(75 − 100)/100",
  "25% decrease",
  "everyday-life", "household-math", "percent change decrease",
  ["percent change 50 to 65"], "household-math")

# --- Algorithmic batch generators ---
# 30 integer factorizations
import math as _math
def _factor(n):
    out, d = [], 2
    while d*d <= n:
        while n % d == 0:
            out.append(d); n //= d
        d += 1
    if n > 1:
        out.append(n)
    # collapse
    from collections import Counter
    c = Counter(out)
    return " × ".join(f"{p}^{e}" if e > 1 else f"{p}" for p, e in sorted(c.items()))

for n in range(120, 240):
    E(f"factor {n}", str(n), f"{n} = {_factor(n)}",
      "mathematics", "number-theory",
      f"factor factorize {n}", [f"factor {n+1}"], "number-theory")

# 30 GCDs
GCD_PAIRS = [(48,180),(12,18),(252,105),(64,128),(100,75),(360,420),
             (462,1071),(391,299),(81,243),(144,96),(28,42),(56,98),
             (333,111),(625,400),(729,243),(1024,768),(1000,625),
             (2025,1620),(1331,121),(99,77),(343,49),(216,144),(512,128),
             (777,111),(64,40),(2048,1536),(1729,91),(987,1597),(225,150),
             (864,378)]
for a, b in GCD_PAIRS:
    g = _math.gcd(a, b)
    E(f"gcd({a},{b})", f"gcd({a}, {b})", str(g),
      "mathematics", "number-theory",
      f"gcd greatest common divisor {a} {b}",
      [f"lcm({a},{b})"], "number-theory")

# 25 simple derivatives
DERIV_TARGETS = [
    ("x^2", "2 x"), ("x^3", "3 x^2"), ("x^4", "4 x^3"),
    ("sqrt(x)", "1/(2 sqrt(x))"), ("1/x", "−1/x^2"),
    ("tan(x)", "sec^2(x)"), ("sec(x)", "sec(x) tan(x)"),
    ("ln(x^2)", "2/x"), ("e^(2x)", "2 e^(2x)"),
    ("sin(2x)", "2 cos(2x)"), ("cos(3x)", "−3 sin(3x)"),
    ("x sin(x)", "sin(x) + x cos(x)"),
    ("x e^x", "e^x (x + 1)"),
    ("x^2 ln(x)", "x (2 ln(x) + 1)"),
    ("(x^2 + 1)^3", "6 x (x^2 + 1)^2"),
    ("arctan(x)", "1/(1 + x^2)"),
    ("arcsin(x)", "1/sqrt(1 − x^2)"),
    ("ln(sin(x))", "cot(x)"),
    ("e^(-x^2)", "−2 x e^(-x^2)"),
    ("sinh(x)", "cosh(x)"),
    ("cosh(x)", "sinh(x)"),
    ("x^x", "x^x (ln(x) + 1)"),
    ("ln(ln(x))", "1/(x ln(x))"),
    ("x/(1+x^2)", "(1 − x^2)/(1 + x^2)^2"),
    ("sqrt(1+x^2)", "x/sqrt(1+x^2)"),
]
for fn, deriv in DERIV_TARGETS:
    E(f"d/dx {fn}", f"d/dx [{fn}]", deriv,
      "mathematics", "calculus",
      f"derivative {fn}", [f"integrate {fn} dx"], "calculus")

# 25 simple definite integrals (results computed inline)
INTEGRAL_TARGETS = [
    ("integrate x dx from 0 to 5", "x²/2 |_0^5", "25/2 = 12.5"),
    ("integrate x dx from 0 to 10", "x²/2 |_0^10", "50"),
    ("integrate x^2 dx from 1 to 4", "x³/3 |_1^4", "21"),
    ("integrate x^3 dx from 0 to 2", "x⁴/4 |_0^2", "4"),
    ("integrate 1/x dx from 1 to e", "ln(x) |_1^e", "1"),
    ("integrate e^x dx from 0 to 1", "e^x |_0^1", "e − 1 ≈ 1.7183"),
    ("integrate sin(x) dx from 0 to pi", "−cos(x) |_0^π", "2"),
    ("integrate cos(x) dx from 0 to pi/2", "sin(x) |_0^{π/2}", "1"),
    ("integrate 2x + 3 dx from 0 to 4", "x² + 3x |_0^4", "28"),
    ("integrate x*e^x dx from 0 to 1", "(x − 1)e^x |_0^1", "1"),
    ("integrate sqrt(x) dx from 0 to 9", "(2/3) x^(3/2) |_0^9", "18"),
    ("integrate 1/(1+x^2) dx from 0 to 1", "arctan(x) |_0^1", "π/4"),
    ("integrate x^2 + 1 dx from -1 to 1", "x³/3 + x |_-1^1", "8/3 ≈ 2.6667"),
    ("integrate sin(x)^2 dx from 0 to pi", "x/2 − sin(2x)/4 |_0^π", "π/2"),
    ("integrate x dx from -3 to 3", "x²/2", "0"),
    ("integrate ln(x) dx from 1 to e", "x ln(x) − x |_1^e", "1"),
    ("integrate tan(x) dx from 0 to pi/4", "−ln|cos(x)|", "ln(2)/2 ≈ 0.3466"),
    ("integrate sec(x)^2 dx from 0 to pi/4", "tan(x) |_0^{π/4}", "1"),
    ("integrate 1/sqrt(x) dx from 1 to 4", "2 sqrt(x) |_1^4", "2"),
    ("integrate e^(2x) dx from 0 to 1", "e^(2x)/2 |_0^1", "(e² − 1)/2 ≈ 3.1945"),
    ("integrate 1/(x^2) dx from 1 to 2", "−1/x |_1^2", "1/2"),
    ("integrate x sin(x) dx from 0 to pi", "sin x − x cos x |_0^π", "π"),
    ("integrate cos(x)^2 dx from 0 to pi", "x/2 + sin(2x)/4 |_0^π", "π/2"),
    ("integrate x^4 dx from 0 to 1", "x⁵/5 |_0^1", "1/5"),
    ("integrate sinh(x) dx from 0 to 1", "cosh(x) |_0^1", "cosh(1) − 1 ≈ 0.5431"),
]
for q, parsed, ans in INTEGRAL_TARGETS:
    E(q, parsed, ans, "mathematics", "calculus",
      "definite integral " + q.lower(),
      [], "calculus")

# 15 percent / arithmetic helpers
PCT_QUERIES = [
    ("15% of 200", "0.15 × 200", "30"),
    ("25% of 480", "0.25 × 480", "120"),
    ("8% of 1250", "0.08 × 1250", "100"),
    ("12% of 750", "0.12 × 750", "90"),
    ("40% of 60", "0.40 × 60", "24"),
    ("60% of 250", "0.60 × 250", "150"),
    ("75% of 96", "0.75 × 96", "72"),
    ("110% of 400", "1.10 × 400", "440"),
    ("0.5% of 5000", "0.005 × 5000", "25"),
    ("33% of 99", "0.33 × 99", "32.67"),
    ("what is 45 of 200", "45/200", "22.5%"),
    ("what is 18 of 90", "18/90", "20%"),
    ("what is 7 of 28", "7/28", "25%"),
    ("what is 250 of 500", "250/500", "50%"),
    ("what is 5 of 200", "5/200", "2.5%"),
]
for q, parsed, ans in PCT_QUERIES:
    E(q, parsed, ans, "everyday-life", "household-math",
      "percentage " + q.lower(), [], "household-math")

# --- (3.b)  Topic-feedback comments pool ---
FB_COMMENTS = [
    "Extremely useful for daily computation work.",
    "The step-by-step output is a lifesaver in my classes.",
    "Good coverage of the basics — wish there were more advanced examples.",
    "Helpful, but the parser sometimes guesses the wrong interpretation.",
    "Excellent! I use it constantly for my homework.",
    "Concise answers with clean formatting — exactly what I needed.",
    "I love being able to cross-check my own calculations here.",
    "Solid reference; the related queries help me dig deeper.",
    "Found the answer in two clicks. Five stars.",
    "Could use a few more worked examples for advanced topics.",
    "Reliable results and clearly written explanations.",
    "Saves a ton of time vs. doing the arithmetic by hand.",
    "Even my high-schoolers can navigate this — clear UI.",
    "The plots are a nice bonus on top of the numeric answers.",
    "Quick, accurate, no fluff.",
    "Best computation reference on the web for my field.",
    "Would love an in-page calculator widget for follow-ups.",
    "Great way to verify textbook results.",
]

# ---------------------------------------------------------------------------
# Writer
# ---------------------------------------------------------------------------
def build(src: str, dst: str) -> None:
    shutil.copyfile(src, dst)
    con = sqlite3.connect(dst)
    cur = con.cursor()
    # Existing IDs / offsets
    cur.execute("SELECT COALESCE(MAX(id), 0) FROM subcategories"); next_sub = cur.fetchone()[0] + 1
    cur.execute("SELECT COALESCE(MAX(id), 0) FROM topics"); next_topic = cur.fetchone()[0] + 1
    cur.execute("SELECT COALESCE(MAX(id), 0) FROM computation_results"); next_cr = cur.fetchone()[0] + 1
    cur.execute("SELECT COALESCE(MAX(id), 0) FROM notebook_entries"); next_ne = cur.fetchone()[0] + 1
    cur.execute("SELECT COALESCE(MAX(id), 0) FROM topic_feedback"); next_fb = cur.fetchone()[0] + 1

    # (1) Subcategories
    for cat_id, name, slug, sort, desc in NEW_SUBCATEGORIES:
        cur.execute("INSERT INTO subcategories(id, category_id, name, slug, description, sort_order) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (next_sub, cat_id, name, slug, desc, sort))
        next_sub += 1

    # category_id by slug (resolved from existing rows)
    cur.execute("SELECT slug, id FROM categories")
    cat_by_slug = dict(cur.fetchall())
    # subcategory_id by slug (resolved after insertion)
    cur.execute("SELECT slug, id FROM subcategories")
    sub_by_slug = dict(cur.fetchall())

    # (2) Topics
    topic_ids_by_slug: dict[str, int] = {}
    for cat_slug, sub_slug, name, slug, desc, image, feat, new, examples_json in NEW_TOPICS:
        img_path = f"/static/images/topics/{image}"
        cur.execute(
            "INSERT INTO topics(id, category_id, subcategory_id, name, slug, description, "
            "image, examples, is_featured, is_new, view_count, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (next_topic, cat_by_slug[cat_slug], sub_by_slug.get(sub_slug),
             name, slug, desc, img_path, examples_json,
             int(feat), int(new), 0, ts(0)))
        topic_ids_by_slug[slug] = next_topic
        next_topic += 1

    # (3) Computation results (no required_specifiers → empty string)
    for i, (q, parsed, plain, cat, sub, kw, related, slug) in enumerate(EXTRA_RESULTS):
        pods = json.dumps([
            {"title": "Input interpretation", "plaintext": parsed or q},
            {"title": "Result",                "plaintext": plain},
        ])
        rel_json = json.dumps(related)
        cur.execute(
            "INSERT INTO computation_results("
            "id, input_query, parsed_input, plaintext, pods, category, subcategory, "
            "units, plot_url, related_queries, keywords, required_specifiers, "
            "topic_slug, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (next_cr, q, parsed, plain, pods, cat, sub, '', '', rel_json, kw, '',
             slug, ts(i % 24)))
        next_cr += 1

    # (4) Notebook entries — distribute extras across the 8 existing notebooks
    cur.execute("SELECT id, title FROM notebooks ORDER BY id")
    notebooks = cur.fetchall()
    # Pull from EXTRA_RESULTS (60 take, evenly spread)
    pool = EXTRA_RESULTS[:60]
    for i, (q, parsed, plain, cat, sub, kw, related, slug) in enumerate(pool):
        nb_id, nb_title = notebooks[i % len(notebooks)]
        cur.execute("SELECT COALESCE(MAX(sort_order), -1) FROM notebook_entries WHERE notebook_id=?",
                    (nb_id,))
        so = cur.fetchone()[0] + 1
        cur.execute(
            "INSERT INTO notebook_entries(id, notebook_id, query_text, result_summary, "
            "notes, sort_order, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (next_ne, nb_id, q, plain[:200], f"Auto-added reference for {cat}/{sub}.",
             so, ts(i % 24)))
        next_ne += 1

    # (5) Topic feedback — 32 entries across topics & users
    cur.execute("SELECT id FROM users ORDER BY id")
    user_ids = [r[0] for r in cur.fetchall()]
    cur.execute("SELECT id FROM topics ORDER BY id")
    all_topic_ids = [r[0] for r in cur.fetchall()]

    FB_PLAN = []  # (user_id, topic_id, rating, comment, is_helpful, hour_offset)
    # 32 deterministic rows
    for i in range(32):
        uid = user_ids[i % len(user_ids)]
        tid = all_topic_ids[(i * 3) % len(all_topic_ids)]
        rating = 3 + ((i * 7) % 3)            # 3/4/5 mix
        helpful = 1 if rating >= 4 else 0
        comment = FB_COMMENTS[i % len(FB_COMMENTS)]
        FB_PLAN.append((uid, tid, rating, comment, helpful, i))

    for uid, tid, rating, comment, helpful, off in FB_PLAN:
        cur.execute(
            "INSERT INTO topic_feedback(id, user_id, topic_id, rating, comment, "
            "is_helpful, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (next_fb, uid, tid, rating, comment, helpful, ts(off)))
        next_fb += 1

    con.commit()
    con.close()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--in",  dest="src", required=True)
    ap.add_argument("--out", dest="dst", required=True)
    args = ap.parse_args()
    build(args.src, args.dst)
    print(f"Built {args.dst}")
