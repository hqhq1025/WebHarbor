#!/usr/bin/env python3
"""R2 polish: appends ON TOP of the R1 seed db (instance_seed/wolfram_alpha.db).

R1 baseline (md5 eeec946a):
  subcategories 60, topics 61, computation_results 573, notebook_entries 84,
  topic_feedback 32.

R2 targets:
  topics       100+  (+50)
  comp_results 1200+ (+700)
  notebook_ent 200+  (+120)
  topic_feedb  60+   (+35)

Deterministic — no datetime.now(), no random. Run twice = same md5.
"""
from __future__ import annotations
import json, sqlite3, shutil, os, math
from datetime import datetime, timedelta

SRC = 'instance_seed/wolfram_alpha.db'
DST = 'instance/wolfram_alpha.db'

REF = datetime(2026, 4, 20, 12, 0, 0)
def ts(off_hours: int = 0) -> str:
    return (REF + timedelta(hours=off_hours)).isoformat(sep=' ')

def J(x): return json.dumps(x)

# ---------------------------------------------------------------------------
# (1) New topics — all NEW slugs (verified not in R1 set)
# ---------------------------------------------------------------------------
# Format: (cat_slug, sub_slug_or_None, name, slug, desc, image, feat, new, examples)
NEW_TOPICS = [
    # --- Mathematics extras (advanced) ---
    ("mathematics", "algebra", "Advanced Algebra", "algebra-advanced",
     "Higher-order polynomial systems, symbolic manipulation, abstract algebra basics.",
     "algebra.png", False, True, J([
        {"query":"solve x^4 - 10x^2 + 9 = 0","type":"polynomial","result":"x = ±1 or ±3"},
        {"query":"resultant of x^2-1 and x-1","type":"resultant","result":"0"},
        {"query":"discriminant of x^2 + 4x + 3","type":"discriminant","result":"4"},
     ])),
    ("mathematics", "calculus", "Advanced Calculus", "calculus-advanced",
     "Multivariable, vector calculus, Taylor expansions, and series convergence.",
     "calculus.png", False, True, J([
        {"query":"gradient of x^2 + y^2","type":"vector","result":"(2x, 2y)"},
        {"query":"divergence of (x, y, z)","type":"vector","result":"3"},
        {"query":"curl of (-y, x, 0)","type":"vector","result":"(0, 0, 2)"},
        {"query":"Taylor series ln(1+x) at 0","type":"series","result":"x − x²/2 + x³/3 − x⁴/4 + ..."},
     ])),
    ("mathematics", "statistics", "Advanced Statistics", "statistics-advanced",
     "Hypothesis testing, confidence intervals, ANOVA, and Bayesian inference.",
     "statistics.png", False, True, J([
        {"query":"95% confidence interval n=30 mean=50 sd=8","type":"ci","result":"≈ (47.1, 52.9)"},
        {"query":"t-test two-sample","type":"test","result":"t = (x̄₁ − x̄₂)/SE"},
        {"query":"chi-square critical value df=5 alpha=0.05","type":"critical","result":"11.07"},
     ])),
    ("mathematics", "geometry", "Solid Geometry", "geometry-3d",
     "Volumes and surface areas of 3D solids: prisms, pyramids, cones, spheres, tori.",
     "geometry.png", False, False, J([
        {"query":"volume cylinder r=4 h=10","type":"solid","result":"160π ≈ 502.65"},
        {"query":"volume cone r=3 h=9","type":"solid","result":"27π ≈ 84.82"},
        {"query":"surface area torus R=5 r=2","type":"solid","result":"4π²Rr ≈ 394.78"},
     ])),
    ("mathematics", "linear-algebra", "Advanced Linear Algebra", "linear-algebra-advanced",
     "Eigenspaces, diagonalization, SVD, Jordan forms, and orthogonal projections.",
     "linear-algebra.png", False, True, J([
        {"query":"eigenvalues {{1,2,0},{0,3,0},{0,0,4}}","type":"eigen","result":"1, 3, 4"},
        {"query":"SVD of {{1,2},{2,1}}","type":"svd","result":"σ = 3, 1; orthogonal U,V"},
     ])),
    ("mathematics", "trigonometry", "Advanced Trigonometry", "trigonometry-advanced",
     "Identities, inverse trig, hyperbolic functions, and Fourier-style decompositions.",
     "trigonometry.png", False, False, J([
        {"query":"sin(3x) expansion","type":"identity","result":"3 sin x − 4 sin³ x"},
        {"query":"cos(2x) expansion","type":"identity","result":"cos²x − sin²x"},
        {"query":"tanh(x) derivative","type":"hyperbolic","result":"sech²(x)"},
     ])),
    ("mathematics", "discrete-math", "Combinatorics", "combinatorics",
     "Permutations, combinations, generating functions, and counting principles.",
     "discrete-math.png", False, False, J([
        {"query":"C(10,3)","type":"combo","result":"120"},
        {"query":"permutations of 'ABCDE'","type":"permutation","result":"120"},
        {"query":"derangements of 5","type":"derangement","result":"44"},
     ])),
    ("mathematics", "discrete-math", "Recurrence Relations", "recurrences",
     "Linear and nonlinear recurrences; characteristic equations and closed forms.",
     "discrete-math.png", False, False, J([
        {"query":"closed form Fibonacci","type":"recurrence","result":"F_n = (φⁿ − ψⁿ)/√5"},
        {"query":"a_n = 2 a_{n-1} + 1, a_0=1","type":"recurrence","result":"a_n = 2^(n+1) − 1"},
     ])),
    ("mathematics", "number-theory", "Advanced Number Theory", "number-theory-advanced",
     "Modular arithmetic, Euler's totient, Chinese remainder theorem, quadratic residues.",
     "number-theory.png", False, False, J([
        {"query":"phi(360)","type":"totient","result":"96"},
        {"query":"inverse of 7 mod 26","type":"modular","result":"15 (since 7·15 = 105 = 4·26 + 1)"},
        {"query":"CRT x≡2 mod 3, x≡3 mod 5","type":"crt","result":"x ≡ 8 mod 15"},
     ])),
    ("mathematics", "discrete-math", "Graph Theory", "graph-theory",
     "Vertices, edges, paths, cycles, matchings, and graph coloring.",
     "discrete-math.png", False, True, J([
        {"query":"number of edges in K_5","type":"graph","result":"10"},
        {"query":"chromatic polynomial cycle C_4","type":"graph","result":"(k−1)⁴ + (k−1)"},
        {"query":"is Petersen graph planar","type":"graph","result":"No — contains K₃,₃ subdivision"},
     ])),
    ("mathematics", "math-puzzles", "Logic Puzzles", "logic-puzzles",
     "Boolean logic, truth tables, knights-and-knaves, and propositional puzzles.",
     "discrete-math.png", False, False, J([
        {"query":"truth table A and (B or C)","type":"logic","result":"8 rows; T only when A∧(B∨C)"},
        {"query":"DeMorgan's laws","type":"logic","result":"¬(A∧B) = ¬A∨¬B; ¬(A∨B) = ¬A∧¬B"},
     ])),

    # --- Science & Technology extras ---
    ("science-and-technology", "physics", "Quantum Physics", "quantum-physics",
     "Wavefunctions, operators, eigenstates, and quantum mechanical principles.",
     "physics.png", True, True, J([
        {"query":"Heisenberg uncertainty","type":"principle","result":"Δx · Δp ≥ ℏ/2"},
        {"query":"hydrogen ground state energy","type":"atom","result":"−13.6 eV"},
        {"query":"de Broglie wavelength electron 1 keV","type":"matter wave","result":"≈ 38.8 pm"},
     ])),
    ("science-and-technology", "physics", "Nuclear Physics", "nuclear-physics",
     "Radioactive decay, half-lives, mass-energy equivalence, and nuclear reactions.",
     "physics.png", False, False, J([
        {"query":"half-life of uranium-238","type":"decay","result":"≈ 4.468 × 10⁹ years"},
        {"query":"half-life of carbon-14","type":"decay","result":"5,730 years"},
        {"query":"binding energy iron-56","type":"nuclear","result":"≈ 492.3 MeV (≈ 8.79 MeV/nucleon)"},
        {"query":"E = mc^2 for 1 g","type":"relativity","result":"≈ 8.988 × 10¹³ J"},
     ])),
    ("science-and-technology", "physics", "Thermodynamics", "thermodynamics",
     "Heat, entropy, the laws of thermodynamics, and ideal-gas computations.",
     "physics.png", False, False, J([
        {"query":"first law of thermodynamics","type":"law","result":"ΔU = Q − W"},
        {"query":"ideal gas PV = nRT, n=2 T=300 V=0.05","type":"ideal","result":"P = 99.77 kPa"},
        {"query":"entropy change melting ice 1 mol","type":"entropy","result":"≈ 22.0 J/(mol·K)"},
     ])),
    ("science-and-technology", "chemistry", "Biochemistry", "biochemistry",
     "Amino acids, proteins, nucleic acids, and metabolic reactions.",
     "chemistry.png", False, False, J([
        {"query":"amino acids essential humans","type":"biochem","result":"9 essential (His, Ile, Leu, Lys, Met, Phe, Thr, Trp, Val)"},
        {"query":"ATP molecular weight","type":"biochem","result":"507.18 g/mol"},
        {"query":"length human DNA stretched","type":"biochem","result":"≈ 2 m per cell"},
     ])),
    ("science-and-technology", "chemistry", "Organic Chemistry", "organic-chemistry",
     "Functional groups, reactions, isomerism, and aromatic systems.",
     "chemistry.png", False, True, J([
        {"query":"functional group alcohol","type":"group","result":"−OH (hydroxyl)"},
        {"query":"functional group carboxylic acid","type":"group","result":"−COOH"},
        {"query":"isomers of butane","type":"isomers","result":"n-butane and isobutane (2)"},
     ])),
    ("science-and-technology", "chemistry", "Inorganic Chemistry", "inorganic-chemistry",
     "Salts, oxides, coordination compounds, and main-group periodicity.",
     "chemistry.png", False, False, J([
        {"query":"NaCl crystal structure","type":"crystal","result":"Face-centered cubic (rock salt)"},
        {"query":"oxidation state of Cr in K2Cr2O7","type":"redox","result":"+6"},
        {"query":"common transition metals","type":"periodic","result":"Sc to Zn (3d series) and beyond"},
     ])),
    ("science-and-technology", "earth-science", "Minerals & Rocks", "minerals-rocks",
     "Mineral hardness, rock classification, and crystallography.",
     "earth-science.png", False, False, J([
        {"query":"Mohs scale diamond","type":"hardness","result":"10 (hardest)"},
        {"query":"three rock types","type":"classification","result":"Igneous, sedimentary, metamorphic"},
        {"query":"density of granite","type":"rock","result":"≈ 2.65–2.75 g/cm³"},
     ])),
    ("science-and-technology", "weather", "Atmospheric Science", "atmospheric-science",
     "Pressure, humidity, cloud formation, and atmospheric layers.",
     "weather.png", False, False, J([
        {"query":"layers of Earth atmosphere","type":"atmosphere","result":"Troposphere, stratosphere, mesosphere, thermosphere, exosphere"},
        {"query":"average sea-level pressure","type":"pressure","result":"101.325 kPa (1 atm)"},
        {"query":"dew point at 25°C 60% humidity","type":"humidity","result":"≈ 16.7 °C"},
     ])),
    ("science-and-technology", "astronomy", "Exoplanets", "exoplanets",
     "Confirmed exoplanets, transit detection, and habitable-zone computations.",
     "astronomy.png", False, True, J([
        {"query":"closest exoplanet","type":"exoplanet","result":"Proxima Centauri b — ~4.24 ly away"},
        {"query":"confirmed exoplanets count","type":"exoplanet","result":"5,500+ as of 2024"},
        {"query":"TRAPPIST-1 system","type":"system","result":"7 Earth-sized planets, 3 in habitable zone"},
     ])),
    ("science-and-technology", "astronomy", "Stellar Evolution", "stellar-evolution",
     "Main sequence, red giants, supernovae, neutron stars, black holes.",
     "astronomy.png", False, False, J([
        {"query":"Sun lifetime","type":"star","result":"≈ 10 billion years total; 5 Gyr remaining"},
        {"query":"Chandrasekhar limit","type":"mass","result":"≈ 1.4 solar masses"},
        {"query":"Schwarzschild radius Sun","type":"black hole","result":"≈ 2.95 km"},
     ])),
    ("science-and-technology", "astronomy", "Constellations", "constellations",
     "88 official constellations, brightest stars, and seasonal visibility.",
     "astronomy.png", False, False, J([
        {"query":"number of constellations","type":"sky","result":"88 (IAU official)"},
        {"query":"brightest star in Orion","type":"star","result":"Rigel (β Ori) — magnitude 0.13"},
        {"query":"largest constellation","type":"sky","result":"Hydra (1303 sq deg)"},
     ])),
    ("science-and-technology", "computer-science", "Cryptography", "cryptography",
     "Symmetric and asymmetric ciphers, hashing, and digital signatures.",
     "discrete-math.png", False, True, J([
        {"query":"AES key sizes","type":"cipher","result":"128, 192, 256 bits"},
        {"query":"RSA 2048-bit security","type":"asymmetric","result":"≈ 112-bit symmetric equivalent"},
        {"query":"SHA-256 output size","type":"hash","result":"256 bits / 64 hex chars"},
     ])),
    ("science-and-technology", "computer-science", "Algorithms & Complexity", "algorithms",
     "Big-O complexity, sorting, searching, and graph algorithms.",
     "discrete-math.png", False, False, J([
        {"query":"complexity of quicksort","type":"complexity","result":"O(n log n) avg, O(n²) worst"},
        {"query":"complexity of binary search","type":"complexity","result":"O(log n)"},
        {"query":"complexity of Dijkstra with heap","type":"complexity","result":"O((V+E) log V)"},
     ])),

    # --- Society & Culture extras ---
    ("society-and-culture", "history", "Ancient History", "ancient-history",
     "Civilizations from Sumer to Rome, key dynasties, and the classical era.",
     "history.png", False, False, J([
        {"query":"first Egyptian pharaoh","type":"history","result":"Narmer (Menes), c. 3100 BC"},
        {"query":"Roman Republic founded","type":"history","result":"509 BC"},
        {"query":"length of the Great Wall","type":"history","result":"≈ 21,196 km total (all periods)"},
     ])),
    ("society-and-culture", "history", "Modern History", "modern-history",
     "Industrial revolution, world wars, decolonization, and 20th-century events.",
     "history.png", False, False, J([
        {"query":"start of World War I","type":"event","result":"July 28, 1914"},
        {"query":"fall of Berlin Wall","type":"event","result":"November 9, 1989"},
        {"query":"Apollo 11 moon landing","type":"event","result":"July 20, 1969"},
     ])),
    ("society-and-culture", "arts-media", "Cinema", "cinema",
     "Films, directors, awards, and box-office statistics.",
     "arts-media.png", False, False, J([
        {"query":"first Academy Award Best Picture","type":"film","result":"Wings (1928)"},
        {"query":"most Oscars won by a film","type":"film","result":"Ben-Hur, Titanic, LOTR: ROTK — 11 each"},
        {"query":"highest grossing film","type":"film","result":"Avatar (2009), $2.92 B"},
     ])),
    ("society-and-culture", "arts-media", "Music History", "music-history",
     "Composers, eras, genres, and milestones in music.",
     "arts-media.png", False, False, J([
        {"query":"Mozart birth year","type":"music","result":"1756"},
        {"query":"Beatles formed","type":"music","result":"Liverpool, 1960"},
        {"query":"length Bach's catalog BWV","type":"music","result":"1128 numbered works"},
     ])),
    ("society-and-culture", "arts-media", "Literature", "literature",
     "Authors, novels, poetry, and literary movements.",
     "arts-media.png", False, False, J([
        {"query":"longest novel","type":"book","result":"In Search of Lost Time — ~1.27 million words"},
        {"query":"Shakespeare plays count","type":"book","result":"39 plays (37 canon + 2 collaborations)"},
        {"query":"Pulitzer Prize for Fiction first","type":"award","result":"His Family by Ernest Poole, 1918"},
     ])),
    ("society-and-culture", "philosophy", "Modern Philosophy", "modern-philosophy",
     "From Descartes onward — rationalism, empiricism, existentialism.",
     "people.png", False, False, J([
        {"query":"Descartes cogito","type":"philosophy","result":"Cogito, ergo sum — 'I think, therefore I am'"},
        {"query":"Kant categorical imperative","type":"philosophy","result":"Act only on maxims you can universalize"},
        {"query":"Sartre existentialism","type":"philosophy","result":"'Existence precedes essence'"},
     ])),
    ("society-and-culture", "politics", "Elections & Voting", "elections",
     "Voting systems, electoral history, and turnout statistics.",
     "people.png", False, False, J([
        {"query":"US electoral votes total","type":"election","result":"538 (270 to win)"},
        {"query":"UK general election cycle","type":"election","result":"Up to 5 years between elections"},
        {"query":"first-past-the-post countries","type":"system","result":"US, UK, India, Canada"},
     ])),
    ("society-and-culture", "geography", "Demographics", "demographics",
     "Population counts, density, age distribution, and migration.",
     "geography.png", False, False, J([
        {"query":"world population 2024","type":"population","result":"≈ 8.1 billion"},
        {"query":"most populous country","type":"population","result":"India — ≈ 1.44 billion (2024)"},
        {"query":"world median age","type":"population","result":"≈ 30.5 years"},
     ])),
    ("society-and-culture", "finance", "Cryptocurrency", "cryptocurrency",
     "Bitcoin, Ethereum, market capitalization, and blockchain fundamentals.",
     "finance.png", False, True, J([
        {"query":"Bitcoin max supply","type":"crypto","result":"21 million BTC (capped)"},
        {"query":"Ethereum block time","type":"crypto","result":"~12 seconds (post-Merge)"},
        {"query":"first cryptocurrency","type":"crypto","result":"Bitcoin, launched Jan 3 2009"},
     ])),
    ("society-and-culture", "linguistics", "Word Etymology", "etymology",
     "Word origins, language families, and borrowed terms.",
     "linguistics.png", False, False, J([
        {"query":"etymology algebra","type":"etymology","result":"From Arabic 'al-jabr' (reunion of broken parts)"},
        {"query":"etymology algorithm","type":"etymology","result":"From Al-Khwarizmi, 9th-century mathematician"},
        {"query":"oldest written language","type":"language","result":"Sumerian cuneiform — c. 3200 BC"},
     ])),
    ("society-and-culture", "people", "Nobel Laureates", "nobel-laureates",
     "Nobel Prize winners across all categories from 1901.",
     "people.png", False, False, J([
        {"query":"first Nobel Prize in Physics","type":"award","result":"Wilhelm Röntgen, 1901 (X-rays)"},
        {"query":"only person two unshared Nobels","type":"award","result":"Marie Curie (Physics 1903, Chemistry 1911)"},
        {"query":"youngest Nobel laureate","type":"award","result":"Malala Yousafzai — age 17, Peace 2014"},
     ])),

    # --- Everyday Life extras ---
    ("everyday-life", "cooking", "Baking", "baking",
     "Ratios, leavening times, oven temperatures, and ingredient substitutions.",
     "food-science.png", False, False, J([
        {"query":"baking soda vs baking powder","type":"substitute","result":"1 tsp baking powder ≈ ¼ tsp baking soda + ½ tsp cream of tartar"},
        {"query":"bread flour to all-purpose","type":"substitute","result":"1 cup AP + 1 tbsp gluten ≈ 1 cup bread flour"},
        {"query":"convert grams cups all-purpose flour","type":"convert","result":"1 cup ≈ 125 g"},
     ])),
    ("everyday-life", "cooking", "Recipe Conversions", "recipe-conversions",
     "Cups to grams to ounces, scaling recipes, and oven-temp conversions.",
     "household-math.png", False, False, J([
        {"query":"1 cup butter in grams","type":"convert","result":"≈ 227 g"},
        {"query":"1 cup sugar in grams","type":"convert","result":"≈ 200 g"},
        {"query":"convert 425 F to C","type":"temperature","result":"≈ 218 °C"},
     ])),
    ("everyday-life", "personal-health", "Nutrition Detail", "nutrition",
     "Macronutrients, vitamins, daily intake, and nutrition labels.",
     "personal-health.png", False, True, J([
        {"query":"protein per gram calories","type":"macro","result":"4 kcal/g"},
        {"query":"fat per gram calories","type":"macro","result":"9 kcal/g"},
        {"query":"recommended daily vitamin C","type":"vitamin","result":"75–90 mg/day adults"},
     ])),
    ("everyday-life", "personal-health", "Fitness Metrics", "fitness",
     "Heart rate zones, VO2 max, METs, and exercise calorie burn.",
     "personal-health.png", False, False, J([
        {"query":"max heart rate age 40","type":"cardio","result":"≈ 180 bpm (220 − age)"},
        {"query":"MET running 10 km/h","type":"mets","result":"≈ 9.8 METs"},
        {"query":"calories cycling 1 hour 20 km/h","type":"exercise","result":"≈ 600 kcal (70 kg)"},
     ])),
    ("everyday-life", "personal-health", "Sleep & Recovery", "sleep",
     "Sleep cycles, recommended duration by age, and recovery science.",
     "personal-health.png", False, False, J([
        {"query":"recommended sleep adult","type":"sleep","result":"7–9 hours / night"},
        {"query":"sleep cycle length","type":"sleep","result":"≈ 90 minutes (4–6 cycles / night)"},
        {"query":"REM percent of sleep","type":"sleep","result":"≈ 20–25%"},
     ])),
    ("everyday-life", "travel", "Distances & Driving", "distances-driving",
     "Road distances, average driving times, and fuel consumption.",
     "travel.png", False, False, J([
        {"query":"driving distance NYC to LA","type":"drive","result":"≈ 4500 km (45 hr nonstop)"},
        {"query":"fuel cost 1000 km 8 L/100km","type":"fuel","result":"80 L of fuel"},
        {"query":"average driving speed highway","type":"speed","result":"≈ 100–120 km/h"},
     ])),
    ("everyday-life", "household-math", "Fraction & Percent Drills", "fraction-percent",
     "Common fraction-to-decimal conversions and percent computations.",
     "household-math.png", False, False, J([
        {"query":"1/4 as decimal","type":"fraction","result":"0.25"},
        {"query":"1/3 as decimal","type":"fraction","result":"0.3333... = 33.33%"},
        {"query":"50% of $80","type":"percent","result":"$40"},
     ])),
    ("everyday-life", "pets", "Dog Breeds", "dog-breeds",
     "Breed sizes, lifespans, and grooming needs.",
     "life-sciences.png", False, False, J([
        {"query":"longest-lived dog breed","type":"breed","result":"Chihuahua — often 14–16 years"},
        {"query":"largest dog breed","type":"breed","result":"Great Dane / Irish Wolfhound"},
        {"query":"AKC recognized breeds","type":"breed","result":"200+ breeds"},
     ])),
    ("everyday-life", "pets", "Cat Breeds", "cat-breeds",
     "Breed characteristics, temperament, lifespan, and care.",
     "life-sciences.png", False, False, J([
        {"query":"longest-lived cat breed","type":"breed","result":"Siamese, Burmese — often 15–20 years"},
        {"query":"largest domestic cat breed","type":"breed","result":"Maine Coon — up to 11 kg"},
        {"query":"CFA recognized breeds","type":"breed","result":"45 recognized breeds"},
     ])),
    ("everyday-life", "gardening", "Growing Zones", "growing-zones",
     "USDA hardiness zones, plant zone maps, and frost-date calculators.",
     "food-science.png", False, False, J([
        {"query":"USDA zone NYC","type":"zone","result":"7b"},
        {"query":"USDA zone Miami","type":"zone","result":"10b/11a"},
        {"query":"frost-free days zone 5","type":"zone","result":"≈ 150–180 days"},
     ])),
    ("everyday-life", "music-audio", "Note Frequencies", "note-frequencies",
     "Standard pitch frequencies for musical notes across octaves.",
     "household-science.png", False, False, J([
        {"query":"frequency C4 (middle C)","type":"note","result":"261.626 Hz"},
        {"query":"frequency A4","type":"note","result":"440 Hz"},
        {"query":"frequency E2 (bass E)","type":"note","result":"82.41 Hz"},
     ])),
    ("everyday-life", "hobbies-games", "Chess", "chess",
     "Openings, ratings, famous games, and chess computations.",
     "probability.png", False, False, J([
        {"query":"squares on a chessboard","type":"chess","result":"64 squares (8x8)"},
        {"query":"highest FIDE rating ever","type":"chess","result":"Magnus Carlsen — 2882 (May 2014)"},
        {"query":"number of legal chess games","type":"chess","result":"≈ 10^{120} (Shannon estimate)"},
     ])),
    ("everyday-life", "hobbies-games", "Board Game Probabilities", "board-games",
     "Dice odds, card draws, and combinatorial outcomes.",
     "probability.png", False, False, J([
        {"query":"probability rolling double six","type":"dice","result":"1/36 ≈ 2.78%"},
        {"query":"probability flush poker 5 cards","type":"cards","result":"≈ 0.1965%"},
        {"query":"expected sum 2d6","type":"dice","result":"7"},
     ])),
    ("everyday-life", "photography", "Camera Settings", "camera-settings",
     "Aperture-shutter-ISO triangle, exposure values, and reciprocity.",
     "household-science.png", False, False, J([
        {"query":"shutter doubled aperture compensation","type":"exposure","result":"Open aperture by 1 stop"},
        {"query":"ISO doubled exposure compensation","type":"exposure","result":"Reduce light by 1 stop"},
        {"query":"hyperfocal distance 50mm f/8","type":"dof","result":"≈ 16.4 m (35mm full frame)"},
     ])),
    ("everyday-life", "personal-finance", "Mortgages", "mortgages",
     "Amortization schedules, refinancing, and mortgage-payment calculators.",
     "personal-finance.png", False, False, J([
        {"query":"mortgage $400k 6.5% 30yr","type":"mortgage","result":"Monthly ≈ $2528"},
        {"query":"mortgage $300k 4% 15yr","type":"mortgage","result":"Monthly ≈ $2219"},
        {"query":"refinance break-even months","type":"mortgage","result":"Closing costs ÷ monthly savings"},
     ])),
    ("everyday-life", "personal-finance", "Retirement Planning", "retirement",
     "Compounding, withdrawal rates, and retirement-savings strategies.",
     "personal-finance.png", False, False, J([
        {"query":"4% rule retirement","type":"rule","result":"Withdraw 4% / yr; ≈30 yr safe"},
        {"query":"401(k) contribution limit 2024","type":"limit","result":"$23,000 ($30,500 if 50+)"},
        {"query":"compound $500/month 7% 30yr","type":"investment","result":"≈ $612,000"},
     ])),

    # --- Generalist cross-cutting (subcategory = NULL for some) ---
    ("mathematics", None, "Famous Constants", "famous-constants",
     "π, e, γ, φ, and other mathematical constants.",
     "calculus.png", False, False, J([
        {"query":"value of pi","type":"constant","result":"3.141592653589793..."},
        {"query":"value of e","type":"constant","result":"2.718281828459045..."},
        {"query":"golden ratio","type":"constant","result":"(1+√5)/2 ≈ 1.61803..."},
     ])),
    ("science-and-technology", None, "Physical Constants", "physical-constants",
     "Universal physical constants from CODATA.",
     "physics.png", False, False, J([
        {"query":"electron charge","type":"constant","result":"e = 1.602176634 × 10⁻¹⁹ C (exact)"},
        {"query":"electron mass","type":"constant","result":"9.1093837 × 10⁻³¹ kg"},
        {"query":"vacuum permittivity","type":"constant","result":"ε₀ = 8.854188 × 10⁻¹² F/m"},
     ])),
    ("everyday-life", None, "Calendars & Holidays", "calendars-holidays",
     "Holiday dates, calendar conversions, and date arithmetic.",
     "household-math.png", False, False, J([
        {"query":"days in February 2024","type":"calendar","result":"29 (leap year)"},
        {"query":"Thanksgiving 2026 USA","type":"holiday","result":"November 26, 2026 (4th Thursday)"},
        {"query":"Chinese New Year 2027","type":"holiday","result":"February 6, 2027 (Year of the Goat)"},
     ])),
    ("everyday-life", None, "Conversions Reference", "conversions-reference",
     "Quick-reference table of common unit conversions.",
     "household-math.png", False, False, J([
        {"query":"1 meter in feet","type":"length","result":"≈ 3.281 ft"},
        {"query":"1 kg in lbs","type":"mass","result":"≈ 2.205 lb"},
        {"query":"1 liter in cups","type":"volume","result":"≈ 4.227 cups"},
     ])),
]

# Sanity: assert all new slugs are unique among themselves
_seen = set()
for t in NEW_TOPICS:
    s = t[3]
    assert s not in _seen, f"duplicate new slug: {s}"
    _seen.add(s)
assert len(NEW_TOPICS) >= 50, f"need 50+ topics, got {len(NEW_TOPICS)}"

# ---------------------------------------------------------------------------
# (2) Computation results — bulk additions (700+)
# ---------------------------------------------------------------------------
EXTRA_RESULTS: list[tuple] = []

def E(q, parsed, ans, cat, sub, kw, related, slug):
    EXTRA_RESULTS.append((q, parsed, ans, cat, sub, kw, related, slug))

# --- (A) More factorizations 240..420 ---
def _factor(n):
    out, d = [], 2
    while d*d <= n:
        while n % d == 0:
            out.append(d); n //= d
        d += 1
    if n > 1:
        out.append(n)
    from collections import Counter
    c = Counter(out)
    return " × ".join(f"{p}^{e}" if e > 1 else f"{p}" for p, e in sorted(c.items()))

for n in range(240, 420):
    E(f"factor {n}", str(n), f"{n} = {_factor(n)}",
      "mathematics", "number-theory",
      f"factor factorize {n}", [f"factor {n+1}"], "number-theory")

# --- (B) GCD pairs ---
GCD_PAIRS_R2 = [
    (45,75),(80,100),(108,144),(252,180),(315,420),
    (560,720),(125,175),(91,143),(360,540),(450,675),
    (770,910),(525,945),(660,924),(132,176),(220,286),
    (245,294),(396,540),(504,672),(750,1125),(180,240),
    (96,128),(168,252),(840,1260),(308,484),(1024,1280),
    (192,240),(450,750),(666,999),(1000,2500),(729,486),
]
for a, b in GCD_PAIRS_R2:
    g = math.gcd(a, b)
    E(f"gcd({a},{b})", f"gcd({a}, {b})", str(g),
      "mathematics", "number-theory",
      f"gcd greatest common divisor {a} {b}",
      [f"lcm({a},{b})"], "number-theory")
    lcm = a*b//g
    E(f"lcm({a},{b})", f"lcm({a}, {b})", str(lcm),
      "mathematics", "number-theory",
      f"lcm least common multiple {a} {b}",
      [f"gcd({a},{b})"], "number-theory")

# --- (C) Primality tests 100..200 (selected odd numbers) ---
def _is_prime(n):
    if n < 2: return False
    if n % 2 == 0: return n == 2
    d = 3
    while d*d <= n:
        if n % d == 0: return False
        d += 2
    return True
for n in range(101, 200, 2):
    if _is_prime(n):
        E(f"is {n} prime?", f"PrimeQ[{n}]", f"Yes — {n} is prime.",
          "mathematics", "number-theory",
          f"primality test prime {n}",
          [f"factor {n}"], "number-theory")
    else:
        E(f"is {n} prime?", f"PrimeQ[{n}]", f"No — {n} = {_factor(n)}.",
          "mathematics", "number-theory",
          f"primality composite {n}",
          [f"factor {n}"], "number-theory")

# --- (D) Square roots and powers ---
for n in [2,3,5,6,7,8,10,11,12,13,14,15,17,19,20,23,29,31,37,41,43,47,50,73,97]:
    v = math.sqrt(n)
    E(f"sqrt({n})", f"√{n}",
      f"≈ {v:.10f}",
      "mathematics", "algebra",
      f"square root {n}", [f"sqrt({n+1})"], "algebra")

POWERS = [(2,8),(2,10),(2,16),(2,20),(2,32),(3,5),(3,10),(5,6),(7,5),(10,6),(10,9),(10,12),
          (11,3),(12,3),(13,3),(2,40),(2,50),(2,64),(3,15),(5,10),(7,7),(8,5),(9,4),(11,5),
          (6,5),(15,4),(20,3),(25,3),(50,2),(99,2),(100,3),(123,2),(256,2),(1024,2),(1000,2)]
for a, b in POWERS:
    E(f"{a}^{b}", f"{a}^{b}", str(a**b),
      "mathematics", "algebra",
      f"power exponent {a} {b}",
      [f"{a}^{b+1}"], "algebra")

# --- (E) Modular arithmetic ---
MOD_QS = [
    (123, 7), (456, 11), (789, 13), (1024, 17), (2025, 19),
    (1234, 23), (5678, 29), (9999, 31), (100, 41), (256, 47),
    (333, 5), (777, 7), (1000, 11), (314, 13), (271, 17),
]
for a, m in MOD_QS:
    E(f"{a} mod {m}", f"{a} mod {m}", str(a % m),
      "mathematics", "number-theory",
      f"modulo modular arithmetic {a} {m}",
      [], "number-theory-advanced")

# --- (F) More derivatives & integrals ---
EXTRA_DERIVS = [
    ("x^5", "5 x^4"), ("x^6", "6 x^5"), ("x^7", "7 x^6"),
    ("x^10", "10 x^9"), ("x^(-1)", "−x^(-2)"), ("x^(1/2)", "1/(2 sqrt(x))"),
    ("x^(1/3)", "1/(3 x^(2/3))"), ("x^(3/2)", "(3/2) sqrt(x)"),
    ("2x^3 - 3x + 1", "6 x^2 − 3"), ("3x^4 - 2x^2 + x", "12 x^3 − 4 x + 1"),
    ("e^(3x)", "3 e^(3x)"), ("e^(-x)", "−e^(-x)"),
    ("ln(2x)", "1/x"), ("ln(x^3)", "3/x"),
    ("log10(x)", "1/(x ln 10)"), ("log2(x)", "1/(x ln 2)"),
    ("sin(5x)", "5 cos(5x)"), ("cos(7x)", "−7 sin(7x)"),
    ("tan(2x)", "2 sec^2(2x)"), ("cot(x)", "−csc^2(x)"),
    ("csc(x)", "−csc(x) cot(x)"), ("sec(x) + tan(x)", "sec(x) (sec(x) + tan(x))"),
    ("arcsin(2x)", "2/sqrt(1 − 4 x^2)"), ("arccos(x)", "−1/sqrt(1 − x^2)"),
    ("arctan(2x)", "2/(1 + 4 x^2)"), ("sinh(2x)", "2 cosh(2x)"),
    ("cosh(3x)", "3 sinh(3x)"), ("tanh(x)", "sech^2(x)"),
    ("x^2 e^(-x)", "x (2 − x) e^(-x)"), ("(sin x)/(cos x)", "sec^2(x)"),
    ("ln(cos(x))", "−tan(x)"), ("e^(sin x)", "cos(x) e^(sin x)"),
    ("(x + 1)^5", "5 (x + 1)^4"), ("(2x − 3)^4", "8 (2x − 3)^3"),
    ("1/(x + 1)", "−1/(x + 1)^2"), ("1/(x^2 + 4)", "−2 x/(x^2 + 4)^2"),
]
for fn, deriv in EXTRA_DERIVS:
    E(f"d/dx {fn}", f"d/dx [{fn}]", deriv,
      "mathematics", "calculus",
      f"derivative {fn}", [f"integrate {fn} dx"], "calculus")

EXTRA_INTEGRALS = [
    ("integrate x^2 dx from 0 to 1", "x³/3 |_0^1", "1/3"),
    ("integrate x^3 dx from 0 to 1", "x⁴/4 |_0^1", "1/4"),
    ("integrate x^5 dx from 0 to 1", "x⁶/6 |_0^1", "1/6"),
    ("integrate x^2 dx from 0 to 10", "x³/3 |_0^10", "1000/3 ≈ 333.33"),
    ("integrate 1 dx from 0 to 5", "x |_0^5", "5"),
    ("integrate 3 dx from 0 to 4", "3x |_0^4", "12"),
    ("integrate 2x dx from 0 to 5", "x² |_0^5", "25"),
    ("integrate 4x^3 dx from 0 to 2", "x⁴ |_0^2", "16"),
    ("integrate sin(x) dx from 0 to 2pi", "−cos(x)", "0"),
    ("integrate cos(x) dx from 0 to pi", "sin(x)", "0"),
    ("integrate sin(x) dx from 0 to pi/2", "−cos(x)", "1"),
    ("integrate cos(x) dx from 0 to pi/4", "sin(x)", "√2/2 ≈ 0.7071"),
    ("integrate e^x dx from 0 to 2", "e^x", "e² − 1 ≈ 6.389"),
    ("integrate e^x dx from -1 to 1", "e^x", "e − 1/e ≈ 2.350"),
    ("integrate 1/x dx from 1 to 10", "ln x", "ln(10) ≈ 2.3026"),
    ("integrate 1/x dx from 1 to 100", "ln x", "ln(100) ≈ 4.6052"),
    ("integrate x^4 dx from -1 to 1", "x⁵/5", "2/5 = 0.4"),
    ("integrate (3x^2 + 2x) dx from 0 to 2", "x³ + x²", "12"),
    ("integrate x^2 + x dx from 0 to 3", "x³/3 + x²/2", "13.5"),
    ("integrate sin(2x) dx from 0 to pi", "−cos(2x)/2", "0"),
    ("integrate cos(2x) dx from 0 to pi/2", "sin(2x)/2", "0"),
    ("integrate x cos(x) dx from 0 to pi/2", "x sin x + cos x", "π/2 − 1 ≈ 0.5708"),
    ("integrate sqrt(x) dx from 0 to 4", "(2/3) x^{3/2}", "16/3 ≈ 5.333"),
    ("integrate 1/sqrt(x) dx from 1 to 9", "2 sqrt(x)", "4"),
    ("integrate 1/(1 + x^2) dx from -1 to 1", "arctan(x)", "π/2 ≈ 1.5708"),
    ("integrate 1/(x ln x) dx from e to e^2", "ln(ln x)", "ln(2) ≈ 0.6931"),
    ("integrate e^(2x) dx from 0 to 2", "e^(2x)/2", "(e⁴ − 1)/2 ≈ 26.80"),
    ("integrate x e^x dx from 0 to 2", "(x − 1) e^x", "e² + 1 ≈ 8.389"),
    ("integrate ln(x) dx from 1 to 5", "x ln x − x", "5 ln 5 − 4 ≈ 4.047"),
    ("integrate sin(x)^3 dx from 0 to pi", "(reduction)", "4/3"),
]
for q, parsed, ans in EXTRA_INTEGRALS:
    E(q, parsed, ans, "mathematics", "calculus",
      "definite integral " + q.lower(), [], "calculus")

# --- (G) More statistics curated ---
STAT_Q = [
    ("mean {10, 20, 30, 40, 50}", "x̄", "30"),
    ("mean {2, 4, 6, 8, 10, 12}", "x̄", "7"),
    ("mean {1, 1, 1, 1}", "x̄", "1"),
    ("median {1, 2, 3, 4, 5, 6, 7, 8}", "median", "4.5"),
    ("median {7, 7, 7, 7, 100}", "median", "7"),
    ("mode {1, 2, 2, 3, 4, 4, 4, 5}", "mode", "4"),
    ("range {3, 7, 2, 8, 5}", "max − min", "6"),
    ("standard deviation {1, 2, 3, 4, 5}", "σ", "≈ 1.4142 (population), ≈ 1.5811 (sample)"),
    ("variance {10, 20, 30}", "Var", "Population: 66.67; Sample: 100"),
    ("z-score x=120 mean=100 sd=15", "(x − μ)/σ", "z ≈ 1.333"),
    ("z-score x=70 mean=80 sd=5", "(x − μ)/σ", "z = −2"),
    ("percentile 70 out of 100", "rank/N", "30% of the data exceeds this value (30th percentile from top)"),
    ("Pearson r perfect anticorrelation", "r", "−1.0"),
    ("normal 68-95-99 rule", "rule", "≈68% within 1σ, 95% within 2σ, 99.7% within 3σ"),
    ("binomial mean n=10 p=0.5", "np", "5"),
    ("binomial variance n=10 p=0.5", "np(1−p)", "2.5"),
    ("Poisson variance lambda=4", "λ", "4"),
    ("expected value uniform[0,10]", "(a+b)/2", "5"),
    ("variance uniform[0,10]", "(b−a)²/12", "100/12 ≈ 8.333"),
    ("expected value geometric p=0.2", "1/p", "5"),
]
for q, parsed, ans in STAT_Q:
    E(q, parsed, ans, "mathematics", "statistics",
      "statistics " + q.lower(), [], "statistics")

# --- (H) More physics curated ---
PHYS_Q = [
    ("speed of sound in air at 20C", "v", "343 m/s"),
    ("speed of sound in water", "v", "≈ 1480 m/s (20 °C)"),
    ("acceleration due to gravity Moon", "g_moon", "1.62 m/s²"),
    ("acceleration due to gravity Mars", "g_mars", "3.71 m/s²"),
    ("acceleration due to gravity Jupiter", "g_jup", "24.79 m/s²"),
    ("escape velocity Earth", "v_e", "≈ 11.186 km/s"),
    ("escape velocity Moon", "v_e", "≈ 2.376 km/s"),
    ("escape velocity Sun surface", "v_e", "≈ 617.5 km/s"),
    ("Stefan-Boltzmann constant", "σ", "5.670374419 × 10⁻⁸ W/(m²·K⁴)"),
    ("Wien displacement constant", "b", "2.897771955 × 10⁻³ m·K"),
    ("vacuum permeability", "μ₀", "1.25663706212 × 10⁻⁶ N/A² (exact)"),
    ("vacuum permittivity", "ε₀", "8.854187817 × 10⁻¹² F/m"),
    ("Coulomb constant", "k_e", "8.9875517923 × 10⁹ N·m²/C²"),
    ("elementary charge", "e", "1.602176634 × 10⁻¹⁹ C (exact)"),
    ("Faraday constant", "F", "96485.33212 C/mol"),
    ("electron rest mass", "m_e", "9.1093837 × 10⁻³¹ kg"),
    ("proton rest mass", "m_p", "1.67262192 × 10⁻²⁷ kg"),
    ("neutron rest mass", "m_n", "1.67492749 × 10⁻²⁷ kg"),
    ("fine structure constant", "α", "≈ 7.2973525693 × 10⁻³ (≈ 1/137.036)"),
    ("Compton wavelength electron", "λ_C", "2.42631023867 × 10⁻¹² m"),
    ("classical electron radius", "r_e", "2.8179403262 × 10⁻¹⁵ m"),
    ("Hubble constant", "H_0", "≈ 67–73 km/s/Mpc (Planck/SH0ES range)"),
    ("Earth orbital speed", "v_E", "≈ 29.78 km/s"),
    ("Earth-Sun distance (1 AU)", "1 AU", "149,597,870.7 km (exact)"),
    ("solar luminosity", "L_sun", "3.828 × 10²⁶ W"),
    ("solar mass", "M_sun", "1.989 × 10³⁰ kg"),
    ("light-year in km", "1 ly", "≈ 9.461 × 10¹² km"),
    ("parsec in km", "1 pc", "≈ 3.0857 × 10¹³ km"),
]
for q, parsed, ans in PHYS_Q:
    E(q, parsed, ans, "science-and-technology", "physics",
      "physics constant " + q.lower(), [], "physics")

# --- (I) Note frequencies (12 chromatic notes × 4 octaves) ---
NOTE_NAMES = ["C","C#","D","D#","E","F","F#","G","G#","A","A#","B"]
def _freq(n_semitones_above_A4):
    return 440.0 * (2 ** (n_semitones_above_A4 / 12))
# A4 = 440Hz. Build octaves 2..5
for octave in [2, 3, 4, 5]:
    for i, name in enumerate(NOTE_NAMES):
        # MIDI: A4 = 69 = 12*4 + 9 (A) ... compute semitones above A4
        midi = 12 * (octave + 1) + i  # C0 = 12, ..., A4 = 69
        n = midi - 69
        f = _freq(n)
        E(f"frequency {name}{octave}", f"freq({name}{octave})",
          f"{f:.3f} Hz",
          "everyday-life", "music-audio",
          f"music note frequency {name.lower()}{octave}",
          [], "note-frequencies")

# --- (J) Constellation list ---
CONSTELLATIONS = [
    ("Orion", "the Hunter", "winter (N hemisphere)", "Rigel (β Ori) — mag 0.13"),
    ("Ursa Major", "the Great Bear", "spring (N hemisphere)", "Alioth (ε UMa) — mag 1.76"),
    ("Cygnus", "the Swan", "summer (N hemisphere)", "Deneb (α Cyg) — mag 1.25"),
    ("Cassiopeia", "the Queen", "autumn (N hemisphere)", "Schedar (α Cas) — mag 2.24"),
    ("Leo", "the Lion", "spring (N hemisphere)", "Regulus (α Leo) — mag 1.35"),
    ("Scorpius", "the Scorpion", "summer (S hemisphere)", "Antares (α Sco) — mag 1.06"),
    ("Sagittarius", "the Archer", "summer (S hemisphere)", "Kaus Australis (ε Sgr) — mag 1.85"),
    ("Crux", "the Southern Cross", "autumn/winter (S)", "Acrux (α Cru) — mag 0.77"),
    ("Centaurus", "the Centaur", "spring (S hemisphere)", "Alpha Centauri — mag −0.27"),
    ("Andromeda", "the Princess", "autumn (N hemisphere)", "Alpheratz (α And) — mag 2.06"),
    ("Perseus", "the Hero", "autumn/winter (N)", "Mirfak (α Per) — mag 1.79"),
    ("Lyra", "the Lyre", "summer (N hemisphere)", "Vega (α Lyr) — mag 0.03"),
    ("Aquila", "the Eagle", "summer (N hemisphere)", "Altair (α Aql) — mag 0.77"),
    ("Bootes", "the Herdsman", "spring (N hemisphere)", "Arcturus (α Boo) — mag −0.05"),
    ("Gemini", "the Twins", "winter (N hemisphere)", "Pollux (β Gem) — mag 1.14"),
]
for name, meaning, season, brightest in CONSTELLATIONS:
    E(f"constellation {name}", name,
      f"{name} ({meaning}); brightest star: {brightest}. Best viewed: {season}.",
      "science-and-technology", "astronomy",
      f"constellation {name.lower()} {meaning.lower()}",
      [], "constellations")

# --- (K) Country additions (extra 20) ---
EXTRA_COUNTRIES = [
    ("Germany", "Berlin", "84.36 million", "357,022 km²", "Euro (€)"),
    ("United Kingdom", "London", "67.74 million", "243,610 km²", "Pound (£)"),
    ("Russia", "Moscow", "144.4 million", "17,098,242 km²", "Russian ruble (₽)"),
    ("China", "Beijing", "1.412 billion", "9,596,961 km²", "Renminbi (¥)"),
    ("Brazil", "Brasília", "215.3 million", "8,515,767 km²", "Brazilian real (R$)"),
    ("Indonesia", "Jakarta", "275.5 million", "1,904,569 km²", "Indonesian rupiah (Rp)"),
    ("Turkey", "Ankara", "85.42 million", "783,562 km²", "Turkish lira (₺)"),
    ("South Africa", "Pretoria", "60.04 million", "1,221,037 km²", "Rand (R)"),
    ("Saudi Arabia", "Riyadh", "36.41 million", "2,149,690 km²", "Riyal (ر.س)"),
    ("Iran", "Tehran", "88.55 million", "1,648,195 km²", "Iranian rial (﷼)"),
    ("Vietnam", "Hanoi", "98.86 million", "331,212 km²", "Vietnamese dong (₫)"),
    ("Thailand", "Bangkok", "71.70 million", "513,120 km²", "Thai baht (฿)"),
    ("Philippines", "Manila", "115.6 million", "300,000 km²", "Philippine peso (₱)"),
    ("Pakistan", "Islamabad", "240.5 million", "881,913 km²", "Pakistani rupee (₨)"),
    ("Bangladesh", "Dhaka", "171.2 million", "147,570 km²", "Bangladeshi taka (৳)"),
    ("Poland", "Warsaw", "37.65 million", "312,696 km²", "Polish złoty (zł)"),
    ("Greece", "Athens", "10.45 million", "131,957 km²", "Euro (€)"),
    ("Portugal", "Lisbon", "10.41 million", "92,212 km²", "Euro (€)"),
    ("Netherlands", "Amsterdam", "17.62 million", "41,850 km²", "Euro (€)"),
    ("Belgium", "Brussels", "11.74 million", "30,528 km²", "Euro (€)"),
]
for c, cap, pop, area, curr in EXTRA_COUNTRIES:
    E(c, c,
      f"{c}: capital {cap}, population {pop}, area {area}, currency {curr}.",
      "society-and-culture", "geography",
      f"country {c.lower()} capital population area",
      [f"capital of {c}"], "geography")
    E(f"capital of {c}", "capital", cap,
      "society-and-culture", "geography",
      f"capital {c.lower()} {cap.lower()}",
      [c], "geography")

# --- (L) More people curated ---
PEOPLE_EXTRA = [
    ("Albert Einstein", "German-American physicist (1879–1955); special and general relativity; Nobel 1921 (photoelectric effect)."),
    ("Marie Curie", "Polish-French physicist/chemist (1867–1934); 2 Nobel Prizes (Physics 1903, Chemistry 1911)."),
    ("Leonhard Euler", "Swiss mathematician (1707–1783); e, Euler's identity, prolific across analysis & number theory."),
    ("Bernhard Riemann", "German mathematician (1826–1866); Riemann hypothesis, integration, geometry."),
    ("Henri Poincaré", "French mathematician (1854–1912); foundational topology, dynamics, special relativity precursor."),
    ("Niels Bohr", "Danish physicist (1885–1962); Bohr model of the atom; Nobel 1922."),
    ("Werner Heisenberg", "German physicist (1901–1976); uncertainty principle; Nobel 1932."),
    ("Erwin Schrödinger", "Austrian physicist (1887–1961); wave equation; Nobel 1933."),
    ("Richard Feynman", "American physicist (1918–1988); path integrals, QED; Nobel 1965."),
    ("James Clerk Maxwell", "Scottish physicist (1831–1879); unified electricity, magnetism, and light."),
    ("Michael Faraday", "English physicist (1791–1867); electromagnetic induction, electrochemistry."),
    ("Tim Berners-Lee", "English computer scientist (b. 1955); invented the World Wide Web (1989)."),
    ("Linus Torvalds", "Finnish-American programmer (b. 1969); creator of Linux and Git."),
    ("Grace Hopper", "American computer scientist (1906–1992); COBOL, first compilers."),
    ("Claude Shannon", "American mathematician (1916–2001); founder of information theory."),
    ("John von Neumann", "Hungarian-American polymath (1903–1957); game theory, computing, quantum mechanics."),
]
for who, fact in PEOPLE_EXTRA:
    E(who, who, fact,
      "society-and-culture", "people",
      "person biography " + who.lower(),
      [], "people")

# --- (M) Cooking conversions (extra) ---
COOK_Q = [
    ("convert 1 cup to mL", "1 cup", "≈ 236.588 mL (US)"),
    ("convert 1 tablespoon to mL", "1 tbsp", "≈ 14.787 mL (US)"),
    ("convert 1 teaspoon to mL", "1 tsp", "≈ 4.929 mL (US)"),
    ("convert 1 ounce to mL", "1 fl oz", "≈ 29.574 mL"),
    ("convert 1 pint to mL", "1 pt (US)", "≈ 473.176 mL"),
    ("convert 1 quart to L", "1 qt (US)", "≈ 0.9464 L"),
    ("convert 1 gallon to L", "1 gal (US)", "≈ 3.7854 L"),
    ("convert 250 F to C", "T", "≈ 121.1 °C"),
    ("convert 375 F to C", "T", "≈ 190.6 °C"),
    ("convert 425 F to C", "T", "≈ 218.3 °C"),
    ("convert 200 C to F", "T", "≈ 392 °F"),
    ("convert 180 C to F", "T", "≈ 356 °F"),
]
for q, parsed, ans in COOK_Q:
    E(q, parsed, ans, "everyday-life", "cooking",
      "cooking conversion " + q.lower(), [], "recipe-conversions")

# --- (N) Holiday dates curated ---
HOLIDAYS = [
    ("Christmas 2026", "Dec 25 2026", "December 25, 2026 (Friday)"),
    ("New Year's Day 2027", "Jan 1 2027", "January 1, 2027 (Friday)"),
    ("Independence Day USA 2026", "Jul 4 2026", "July 4, 2026 (Saturday)"),
    ("Halloween 2026", "Oct 31 2026", "October 31, 2026 (Saturday)"),
    ("Thanksgiving USA 2026", "4th Thu Nov 2026", "November 26, 2026"),
    ("Valentine's Day 2026", "Feb 14 2026", "February 14, 2026 (Saturday)"),
    ("St. Patrick's Day 2026", "Mar 17 2026", "March 17, 2026 (Tuesday)"),
    ("Easter 2026", "Easter Sunday", "April 5, 2026"),
    ("Mother's Day USA 2026", "2nd Sun May", "May 10, 2026"),
    ("Father's Day USA 2026", "3rd Sun June", "June 21, 2026"),
    ("Labor Day USA 2026", "1st Mon Sept", "September 7, 2026"),
    ("Memorial Day USA 2026", "Last Mon May", "May 25, 2026"),
    ("Veterans Day 2026", "Nov 11 2026", "November 11, 2026"),
    ("Diwali 2026", "Festival of lights", "November 8, 2026 (approx.)"),
    ("Hanukkah 2026", "8-day Jewish festival", "Begins December 4, 2026 evening"),
]
for q, parsed, ans in HOLIDAYS:
    E(q, parsed, ans, "everyday-life", "dates-times",
      "holiday date " + q.lower(), [], "calendars-holidays")

# --- (O) Cryptocurrency facts ---
CRYPTO = [
    ("Bitcoin block reward 2024", "BTC block reward", "3.125 BTC (post 2024 halving)"),
    ("Bitcoin halvings", "halving schedule", "Every 210,000 blocks (~4 years)"),
    ("Ethereum total supply", "ETH supply", "≈ 120 million (post-Merge, deflationary trend)"),
    ("Litecoin block time", "LTC time", "2.5 minutes"),
    ("Ethereum gas limit", "gas/block", "≈ 30 million gas (post-London)"),
    ("Bitcoin Whitepaper year", "BTC paper", "2008 (Satoshi Nakamoto)"),
    ("Ethereum launch year", "ETH launch", "July 30, 2015"),
    ("Bitcoin smallest unit", "satoshi", "1 satoshi = 10⁻⁸ BTC"),
]
for q, parsed, ans in CRYPTO:
    E(q, parsed, ans, "society-and-culture", "finance",
      "crypto " + q.lower(), [], "cryptocurrency")

# --- (P) Trig values curated (extra) ---
TRIG_Q = [
    ("sin(120 degrees)", "sin(120°)", "√3/2 ≈ 0.866"),
    ("sin(135 degrees)", "sin(135°)", "√2/2 ≈ 0.707"),
    ("sin(150 degrees)", "sin(150°)", "1/2"),
    ("sin(180 degrees)", "sin(180°)", "0"),
    ("cos(120 degrees)", "cos(120°)", "−1/2"),
    ("cos(150 degrees)", "cos(150°)", "−√3/2 ≈ −0.866"),
    ("cos(180 degrees)", "cos(180°)", "−1"),
    ("tan(45 degrees)", "tan(45°)", "1"),
    ("tan(60 degrees)", "tan(60°)", "√3 ≈ 1.732"),
    ("tan(30 degrees)", "tan(30°)", "√3/3 ≈ 0.577"),
    ("cot(45 degrees)", "cot(45°)", "1"),
    ("sec(60 degrees)", "sec(60°)", "2"),
    ("csc(30 degrees)", "csc(30°)", "2"),
]
for q, parsed, ans in TRIG_Q:
    E(q, parsed, ans, "mathematics", "trigonometry",
      "trig value " + q.lower(), [], "trigonometry")

# --- (Q) Sleep / health / fitness ---
HEALTH_Q = [
    ("calories per slice pizza", "approx", "≈ 285 kcal (typical cheese slice)"),
    ("calories burned walking 5km", "MET 3.5", "≈ 245 kcal (70 kg person)"),
    ("calories burned swimming 1 hour", "MET 6", "≈ 420 kcal (70 kg)"),
    ("calories burned yoga 1 hour", "MET 2.5", "≈ 175 kcal (70 kg)"),
    ("BMI 70kg 175cm", "kg/m²", "BMI ≈ 22.86 (Normal)"),
    ("BMI 80kg 180cm", "kg/m²", "BMI ≈ 24.69 (Normal)"),
    ("BMI 90kg 175cm", "kg/m²", "BMI ≈ 29.39 (Overweight)"),
    ("water per day 70kg", "≈30 mL/kg", "≈ 2.1 L/day"),
    ("max heart rate 30 yr", "220 − age", "190 bpm"),
    ("max heart rate 50 yr", "220 − age", "170 bpm"),
    ("REM sleep percentage", "of total", "20–25%"),
    ("deep sleep percentage", "of total", "13–23%"),
]
for q, parsed, ans in HEALTH_Q:
    E(q, parsed, ans, "everyday-life", "personal-health",
      "health metric " + q.lower(), [], "personal-health")

# --- (R) Personal finance examples (extra) ---
FIN_Q = [
    ("mortgage $250000 5% 30 years", "amortized", "Monthly ≈ $1342"),
    ("mortgage $500000 4% 30 years", "amortized", "Monthly ≈ $2387"),
    ("mortgage $200000 6% 15 years", "amortized", "Monthly ≈ $1688"),
    ("car loan $25000 7% 5 years", "amortized", "Monthly ≈ $495"),
    ("car loan $40000 6% 6 years", "amortized", "Monthly ≈ $663"),
    ("savings $200/mo 5% 20yr", "FV", "≈ $82,200"),
    ("savings $500/mo 6% 30yr", "FV", "≈ $502,000"),
    ("inflation $1 1970 to 2024", "CPI", "≈ $8.10"),
    ("inflation $100 1990 to 2024", "CPI", "≈ $241"),
    ("inflation $1000 2010 to 2024", "CPI", "≈ $1422"),
    ("18% tip on $60", "0.18 × 60", "Tip $10.80, total $70.80"),
    ("25% tip on $40", "0.25 × 40", "Tip $10.00, total $50.00"),
]
for q, parsed, ans in FIN_Q:
    E(q, parsed, ans, "society-and-culture", "finance",
      "finance " + q.lower(), [], "finance")

# --- (S) Conversion auto-generators (lots, deterministic) ---
LEN_PAIRS = [(1,'mile','km',1.609344), (2,'mile','km',1.609344), (3,'mile','km',1.609344),
             (5,'mile','km',1.609344), (10,'mile','km',1.609344), (20,'mile','km',1.609344),
             (50,'mile','km',1.609344), (100,'mile','km',1.609344),
             (1,'km','mile',0.621371), (5,'km','mile',0.621371), (10,'km','mile',0.621371),
             (42.195,'km','mile',0.621371),
             (1,'foot','meter',0.3048), (6,'foot','meter',0.3048), (100,'foot','meter',0.3048),
             (1,'inch','cm',2.54), (6,'inch','cm',2.54), (12,'inch','cm',2.54), (36,'inch','cm',2.54),
             (1,'meter','foot',3.28084), (10,'meter','foot',3.28084), (100,'meter','foot',3.28084)]
for n, src_u, dst_u, k in LEN_PAIRS:
    v = n * k
    E(f"{n} {src_u} in {dst_u}", f"{n} {src_u}",
      f"≈ {v:.4f} {dst_u}",
      "science-and-technology", "units-measures",
      f"convert {n} {src_u} {dst_u}",
      [], "units-measures")

MASS_PAIRS = [(1,'lb','kg',0.453592), (10,'lb','kg',0.453592), (50,'lb','kg',0.453592),
              (100,'lb','kg',0.453592), (200,'lb','kg',0.453592),
              (1,'kg','lb',2.20462), (10,'kg','lb',2.20462), (50,'kg','lb',2.20462),
              (70,'kg','lb',2.20462), (100,'kg','lb',2.20462),
              (1,'oz','g',28.3495), (8,'oz','g',28.3495), (16,'oz','g',28.3495)]
for n, src_u, dst_u, k in MASS_PAIRS:
    v = n * k
    E(f"{n} {src_u} in {dst_u}", f"{n} {src_u}",
      f"≈ {v:.4f} {dst_u}",
      "science-and-technology", "units-measures",
      f"convert mass {n} {src_u} {dst_u}",
      [], "units-measures")

TEMP_PAIRS = [(0,'C','F'), (10,'C','F'), (20,'C','F'), (37,'C','F'), (100,'C','F'),
              (-40,'C','F'), (32,'F','C'), (50,'F','C'), (98.6,'F','C'), (212,'F','C'),
              (0,'K','C'), (273.15,'K','C'), (373.15,'K','C')]
for n, src_u, dst_u in TEMP_PAIRS:
    if src_u == 'C' and dst_u == 'F':
        v = n * 9/5 + 32
    elif src_u == 'F' and dst_u == 'C':
        v = (n - 32) * 5/9
    elif src_u == 'K' and dst_u == 'C':
        v = n - 273.15
    E(f"{n} {src_u} in {dst_u}", f"{n} {src_u}",
      f"≈ {v:.3f} {dst_u}",
      "science-and-technology", "units-measures",
      f"convert temperature {n} {src_u} {dst_u}",
      [], "units-measures")

# --- (T) Algorithm complexity / CS factoids ---
CS_Q = [
    ("complexity bubble sort", "BigO", "O(n²) worst, O(n) best (already sorted)"),
    ("complexity merge sort", "BigO", "O(n log n) in all cases, O(n) extra space"),
    ("complexity heap sort", "BigO", "O(n log n) in all cases, in-place"),
    ("complexity quicksort", "BigO", "O(n log n) avg, O(n²) worst (bad pivot)"),
    ("complexity Tim sort", "BigO", "O(n log n) worst, O(n) best (Python's default)"),
    ("complexity counting sort", "BigO", "O(n + k) for keys in 0..k"),
    ("complexity radix sort", "BigO", "O(d (n + k)) for d-digit numbers"),
    ("complexity Dijkstra (heap)", "BigO", "O((V + E) log V)"),
    ("complexity Bellman-Ford", "BigO", "O(V·E)"),
    ("complexity Floyd-Warshall", "BigO", "O(V³)"),
    ("complexity DFS / BFS", "BigO", "O(V + E)"),
    ("complexity KMP string match", "BigO", "O(n + m)"),
    ("complexity hash table average lookup", "BigO", "O(1) amortized, O(n) worst"),
]
for q, parsed, ans in CS_Q:
    E(q, parsed, ans, "science-and-technology", "computer-science",
      "complexity algorithm " + q.lower(), [], "algorithms")

# --- (U) Famous mathematical constants ---
CONST_Q = [
    ("value of pi", "π", "3.14159265358979323846..."),
    ("value of e", "e", "2.71828182845904523536..."),
    ("value of phi (golden ratio)", "φ", "(1 + √5)/2 ≈ 1.61803398875"),
    ("Euler-Mascheroni constant", "γ", "≈ 0.5772156649"),
    ("Catalan constant", "G", "≈ 0.9159655942"),
    ("Apéry's constant", "ζ(3)", "≈ 1.2020569032"),
    ("Khinchin constant", "K_0", "≈ 2.685452001"),
    ("Feigenbaum constant", "δ", "≈ 4.669201609"),
    ("imaginary unit", "i", "i = √(−1); i² = −1"),
    ("square root of 2", "√2", "≈ 1.41421356237"),
]
for q, parsed, ans in CONST_Q:
    E(q, parsed, ans, "mathematics", "algebra",
      "constant " + q.lower(), [], "famous-constants")

# Final check: should have ~700+ new rows
print(f"[r2] prepared {len(EXTRA_RESULTS)} computation rows")

# ---------------------------------------------------------------------------
# (3) Topic feedback comment pool (extras)
# ---------------------------------------------------------------------------
FB_COMMENTS_R2 = [
    "Just what I needed — went straight to the answer.",
    "Loved the worked-example progression.",
    "Bookmarking this topic for the semester.",
    "Beats my calculator app any day.",
    "Helpful, especially the related-queries list.",
    "Crisp explanations and accurate values.",
    "Great refresher before my exam.",
    "Excellent coverage across difficulty levels.",
    "I sent this to all my study-group friends.",
    "Saved me an hour of textbook hunting.",
    "Clean layout, fast loading. Five stars.",
    "Sometimes the parser surprises me but the results are solid.",
    "Could use a few interactive plots, but the data is great.",
    "Coverage is broader than I expected.",
    "Outstanding reference page.",
    "Will use this every week.",
]

# ---------------------------------------------------------------------------
# Writer
# ---------------------------------------------------------------------------
def build():
    os.makedirs('instance', exist_ok=True)
    shutil.copyfile(SRC, DST)
    con = sqlite3.connect(DST)
    cur = con.cursor()

    cur.execute("SELECT COALESCE(MAX(id), 0) FROM topics"); next_topic = cur.fetchone()[0] + 1
    cur.execute("SELECT COALESCE(MAX(id), 0) FROM computation_results"); next_cr = cur.fetchone()[0] + 1
    cur.execute("SELECT COALESCE(MAX(id), 0) FROM notebook_entries"); next_ne = cur.fetchone()[0] + 1
    cur.execute("SELECT COALESCE(MAX(id), 0) FROM topic_feedback"); next_fb = cur.fetchone()[0] + 1

    cur.execute("SELECT slug, id FROM categories"); cat_by_slug = dict(cur.fetchall())
    cur.execute("SELECT slug, id FROM subcategories"); sub_by_slug = dict(cur.fetchall())
    # Verify no slug collisions
    cur.execute("SELECT slug FROM topics"); existing_topic_slugs = set(r[0] for r in cur.fetchall())
    for t in NEW_TOPICS:
        assert t[3] not in existing_topic_slugs, f"topic slug collides: {t[3]}"

    # ---- Topics ----
    for cat_slug, sub_slug, name, slug, desc, image, feat, new, examples_json in NEW_TOPICS:
        img_path = f"/static/images/topics/{image}"
        sub_id = sub_by_slug.get(sub_slug) if sub_slug else None
        cur.execute(
            "INSERT INTO topics(id, category_id, subcategory_id, name, slug, description, "
            "image, examples, is_featured, is_new, view_count, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (next_topic, cat_by_slug[cat_slug], sub_id, name, slug, desc, img_path,
             examples_json, int(feat), int(new), 0, ts(0)))
        next_topic += 1

    # ---- Computation results ----
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

    # ---- Notebook entries ----
    cur.execute("SELECT id, title FROM notebooks ORDER BY id")
    notebooks = cur.fetchall()
    # Distribute 120 extras across the 8 existing notebooks (15 each)
    pool = EXTRA_RESULTS[:120]
    nb_per_count = {nb[0]: 0 for nb in notebooks}
    for i, (q, parsed, plain, cat, sub, kw, related, slug) in enumerate(pool):
        nb_id, nb_title = notebooks[i % len(notebooks)]
        cur.execute("SELECT COALESCE(MAX(sort_order), -1) FROM notebook_entries WHERE notebook_id=?",
                    (nb_id,))
        so = cur.fetchone()[0] + 1
        cur.execute(
            "INSERT INTO notebook_entries(id, notebook_id, query_text, result_summary, "
            "notes, sort_order, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (next_ne, nb_id, q, plain[:200],
             f"R2 reference for {cat}/{sub}.", so, ts(i % 24)))
        next_ne += 1
        nb_per_count[nb_id] += 1

    # ---- Topic feedback ----
    cur.execute("SELECT id FROM users ORDER BY id")
    user_ids = [r[0] for r in cur.fetchall()]
    cur.execute("SELECT id FROM topics ORDER BY id")
    all_topic_ids = [r[0] for r in cur.fetchall()]

    # 35 deterministic rows on top of existing 32
    for i in range(35):
        uid = user_ids[(i * 2) % len(user_ids)]
        # Spread across NEW topics first, then full set
        tid = all_topic_ids[(i * 11 + 5) % len(all_topic_ids)]
        rating = 3 + ((i * 7) % 3)
        helpful = 1 if rating >= 4 else 0
        comment = FB_COMMENTS_R2[i % len(FB_COMMENTS_R2)]
        cur.execute(
            "INSERT INTO topic_feedback(id, user_id, topic_id, rating, comment, "
            "is_helpful, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (next_fb, uid, tid, rating, comment, helpful, ts(i)))
        next_fb += 1

    con.commit()
    con.close()
    print(f"[r2] built {DST}")


if __name__ == "__main__":
    build()
