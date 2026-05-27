#!/usr/bin/env python3
"""R11 GUI deepen seed: creates 14 new tables (r11_*) for the WolframAlpha
mirror and seeds them with the page constants previously hardcoded in
`_r11_gui_extend.py`. No `db.create_all` -- raw SQL CREATE TABLE that exactly
mirrors what SQLAlchemy emits, so byte-id reset is preserved.

Run twice -> identical md5. Reads `instance_seed/wolfram_alpha.db`, writes
`instance/wolfram_alpha.db`. Promote with `cp instance/... instance_seed/...`.

R11 tables (16):
  r11_example_sections, r11_widgets, r11_pub_notebooks,
  r11_lang_tutorials, r11_courses, r11_certificates,
  r11_blog_categories, r11_blog_posts,
  r11_community_groups, r11_community_topics,
  r11_jobs, r11_store_products, r11_research_papers,
  r11_conferences, r11_demonstrations, r11_mathworld_entries
"""
from __future__ import annotations
import os, sqlite3, shutil

SRC = 'instance_seed/wolfram_alpha.db'
DST = 'instance/wolfram_alpha.db'


# Hand-written CREATE TABLE strings whose stored form mirrors what
# `SQLAlchemy.create_all()` emits on equivalent models (tab-indent, trailing
# space after each `,` before newline). Verified empirically; any deviation
# breaks byte-id reset across `db.create_all` runs.
def _mk(table, cols, pk_cols):
    body = ', \n'.join('\t' + c for c in cols)
    pk   = '\tPRIMARY KEY (' + ', '.join(pk_cols) + ')'
    return 'CREATE TABLE ' + table + ' (\n' + body + ', \n' + pk + '\n)'


CREATE_TABLES = [
    _mk('r11_example_sections',
        ['slug VARCHAR(80) NOT NULL',
         'name VARCHAR(120) NOT NULL',
         'count INTEGER',
         'description TEXT',
         'sort_order INTEGER'], ['slug']),
    _mk('r11_widgets',
        ['slug VARCHAR(80) NOT NULL',
         'name VARCHAR(120) NOT NULL',
         'topic VARCHAR(60)',
         'installs INTEGER',
         'rating FLOAT',
         'embed_size VARCHAR(30)'], ['slug']),
    _mk('r11_pub_notebooks',
        ['slug VARCHAR(120) NOT NULL',
         'title VARCHAR(200) NOT NULL',
         'author VARCHAR(120)',
         'cells INTEGER',
         'abstract TEXT',
         'license VARCHAR(40)',
         'language VARCHAR(40)'], ['slug']),
    _mk('r11_lang_tutorials',
        ['slug VARCHAR(80) NOT NULL',
         'title VARCHAR(160) NOT NULL',
         'abstract TEXT',
         'sort_order INTEGER'], ['slug']),
    _mk('r11_courses',
        ['slug VARCHAR(120) NOT NULL',
         'name VARCHAR(200) NOT NULL',
         'category VARCHAR(60)',
         'lessons INTEGER',
         'level VARCHAR(20)'], ['slug']),
    _mk('r11_certificates',
        ['cert_id VARCHAR(40) NOT NULL',
         'course_slug VARCHAR(120)',
         'awarded_to VARCHAR(120)',
         'issued_date VARCHAR(20)'], ['cert_id']),
    _mk('r11_blog_categories',
        ['slug VARCHAR(60) NOT NULL',
         'name VARCHAR(120) NOT NULL'], ['slug']),
    _mk('r11_blog_posts',
        ['slug VARCHAR(160) NOT NULL',
         'title VARCHAR(300) NOT NULL',
         'author VARCHAR(120)',
         'date VARCHAR(20)',
         'category_slug VARCHAR(60)',
         'abstract TEXT'], ['slug']),
    _mk('r11_community_groups',
        ['slug VARCHAR(60) NOT NULL',
         'name VARCHAR(120) NOT NULL',
         'members INTEGER'], ['slug']),
    _mk('r11_community_topics',
        ['tid INTEGER NOT NULL',
         'title VARCHAR(240)',
         'group_slug VARCHAR(60)',
         'replies INTEGER',
         'author VARCHAR(120)'], ['tid']),
    _mk('r11_jobs',
        ['job_id VARCHAR(20) NOT NULL',
         'title VARCHAR(200) NOT NULL',
         'department VARCHAR(60)',
         'location VARCHAR(80)',
         'salary VARCHAR(40)'], ['job_id']),
    _mk('r11_store_products',
        ['slug VARCHAR(80) NOT NULL',
         'name VARCHAR(200) NOT NULL',
         'category VARCHAR(40)',
         'price FLOAT',
         'description TEXT'], ['slug']),
    _mk('r11_research_papers',
        ['slug VARCHAR(120) NOT NULL',
         'title VARCHAR(300) NOT NULL',
         'author VARCHAR(120)',
         'year INTEGER',
         'area VARCHAR(60)',
         'abstract TEXT'], ['slug']),
    _mk('r11_conferences',
        ['slug VARCHAR(40) NOT NULL',
         'name VARCHAR(200) NOT NULL',
         'year INTEGER',
         'location VARCHAR(80)',
         'attendees INTEGER'], ['slug']),
    _mk('r11_demonstrations',
        ['did INTEGER NOT NULL',
         'name VARCHAR(200) NOT NULL',
         'topic VARCHAR(60)',
         'description TEXT'], ['did']),
    _mk('r11_mathworld_entries',
        ['slug VARCHAR(120) NOT NULL',
         'name VARCHAR(200) NOT NULL',
         'topic VARCHAR(60)',
         'body TEXT'], ['slug']),
]


# ---------------------------------------------------------------------------
# Seed data — formerly hardcoded in `_r11_gui_extend.py`.
# ---------------------------------------------------------------------------
EXAMPLE_SECTIONS = [
    ('mathematics',            'Mathematics',           5,
     'Elementary math, algebra, geometry, calculus, statistics.', 1),
    ('science-and-technology', 'Science & Technology',  5,
     'Physics, chemistry, units, engineering, computational sciences.', 2),
    ('society-and-culture',    'Society & Culture',     5,
     'People, arts, history, money, demographics, words.', 3),
    ('everyday-life',          'Everyday Life',         5,
     'Personal health, finance, entertainment, household science.', 4),
    ('pro-features',           'Pro Features',          4,
     'Step-by-step solutions, data/image/file inputs.', 5),
]

WIDGETS = [
    ('tip-calculator',     'Tip Calculator',              'finance',        41200, 4.7, '420x300'),
    ('unit-converter',     'Unit Converter',              'units',          38900, 4.8, '420x300'),
    ('derivative-step',    'Derivative Step-by-Step',     'calculus',       27500, 4.6, '420x300'),
    ('integral-step',      'Integral Step-by-Step',       'calculus',       26100, 4.6, '420x300'),
    ('matrix-solver',      'Matrix Equation Solver',      'linear-algebra', 18900, 4.5, '420x300'),
    ('periodic-table',     'Periodic Table Lookup',       'chemistry',      22100, 4.7, '420x300'),
    ('bmi-calculator',     'BMI Calculator',              'health',         16400, 4.4, '420x300'),
    ('loan-amortization',  'Loan Amortization Schedule',  'finance',        13800, 4.5, '420x300'),
    ('mortgage-payment',   'Mortgage Payment Calculator', 'finance',        19200, 4.6, '420x300'),
    ('mole-calculator',    'Mole / Mass Calculator',      'chemistry',      11700, 4.5, '420x300'),
    ('projectile-motion',  'Projectile Motion',           'physics',        14600, 4.6, '420x300'),
    ('standard-deviation', 'Standard Deviation',          'statistics',     9800,  4.4, '420x300'),
]

PUB_NOTEBOOKS = [
    ('introduction-to-machine-learning', 'Introduction to Machine Learning',
     'Stephen Wolfram', 18, 'Tour of Classify, Predict, and FeatureExtraction with worked examples.',
     'CC-BY-4.0', 'Wolfram'),
    ('visualizing-pi', 'Visualizing Pi',
     'Daniel Lichtblau', 9, 'Several visualizations of digits of pi using Wolfram Language.',
     'CC-BY-4.0', 'Wolfram'),
    ('cellular-automata-explorer', 'Cellular Automata Explorer',
     'Wolfram Research', 14, 'Browse the 256 elementary cellular automaton rules interactively.',
     'CC-BY-4.0', 'Wolfram'),
    ('covid-pandemic-data', 'COVID Pandemic Data',
     'Wolfram Curated', 22, 'Time series of cases, deaths and vaccinations across 195 countries.',
     'CC-BY-4.0', 'Wolfram'),
    ('us-election-poll-aggregate', 'US Election Poll Aggregate',
     'Wolfram Curated', 12, 'Polling averages with confidence intervals for major US races.',
     'CC-BY-4.0', 'Wolfram'),
    ('mortgage-affordability-model', 'Mortgage Affordability Model',
     'Wolfram Finance', 16, 'Interactive model linking income, interest rate, and PMI.',
     'CC-BY-4.0', 'Wolfram'),
    ('sars-cov2-variant-tree', 'SARS-CoV-2 Variant Tree',
     'Wolfram Life Sciences', 11, 'Phylogenetic tree of major SARS-CoV-2 variants annotated with dates.',
     'CC-BY-4.0', 'Wolfram'),
    ('galaxy-rotation-curves', 'Galaxy Rotation Curves',
     'Wolfram Astronomy', 10, 'Observed vs predicted rotation curves for 8 nearby galaxies.',
     'CC-BY-4.0', 'Wolfram'),
    ('fourier-series-sandbox', 'Fourier Series Sandbox',
     'Wolfram Education', 13, 'Manipulate components of a Fourier series and view the time signal.',
     'CC-BY-4.0', 'Wolfram'),
    ('matrix-decompositions', 'Matrix Decompositions',
     'Wolfram Linear Algebra', 17, 'SVD, QR, LU, Cholesky decompositions of worked-example matrices.',
     'CC-BY-4.0', 'Wolfram'),
    ('pendulum-phase-space', 'Pendulum Phase Space',
     'Wolfram Physics', 8, 'Phase-space plots for damped/driven pendulums across regimes.',
     'CC-BY-4.0', 'Wolfram'),
    ('crispr-target-finder', 'CRISPR Target Finder',
     'Wolfram Bioinformatics', 14, 'PAM-aware sgRNA candidate scoring across selected genomes.',
     'CC-BY-4.0', 'Wolfram'),
]

LANG_TUTORIALS = [
    ('lists',                     'Lists',
     'Compose, transform, and structure lists in Wolfram Language.', 1),
    ('symbols-and-patterns',      'Symbols and Patterns',
     'Pattern matching, replacement, and symbolic transforms.', 2),
    ('functions',                 'Functions',
     'Define pure functions, options, and overloads.', 3),
    ('differential-equations',    'Differential Equations',
     'Solve ODEs and PDEs symbolically with DSolve.', 4),
    ('statistical-distributions', 'Statistical Distributions',
     '70+ built-in distributions with derived quantities.', 5),
    ('strings-and-text',          'Strings and Text',
     'Tokenize, search, and rewrite text via patterns.', 6),
    ('files-and-streams',         'Files and Streams',
     'Import/export 200+ formats; streaming IO.', 7),
    ('notebooks-as-documents',    'Notebooks as Interactive Documents',
     'Cells, dynamics, and stylesheets.', 8),
    ('geometric-computation',     'Geometric Computation',
     'Polygons, regions, mesh and boundary representations.', 9),
    ('plotting',                  'Plotting',
     'Plot, ListPlot, Plot3D and Manipulate-driven dynamics.', 10),
    ('numerical-mathematics',     'Numerical Mathematics',
     'NSolve, NIntegrate, NDSolve and tolerance control.', 11),
    ('machine-learning',          'Machine Learning',
     'Classify, Predict, NetTrain end-to-end pipelines.', 12),
]

COURSES = [
    ('introduction-to-wolfram-language', 'Introduction to Wolfram Language', 'Programming',       8, 'beginner'),
    ('introduction-to-game-theory',      'Introduction to Game Theory',       'Mathematics',       6, 'intermediate'),
    ('introduction-to-partial-differential-equations',
     'Introduction to Partial Differential Equations',                        'Mathematics',       7, 'advanced'),
    ('introduction-to-laplace-transforms','Introduction to Laplace Transforms','Mathematics',      6, 'intermediate'),
    ('quick-start-wolfram-tech',         'Quick Start to Wolfram Tech',       'Wolfram Language', 5, 'beginner'),
    ('visual-explorations-in-data-science','Proficiency in Visual Explorations','Data Science',   7, 'intermediate'),
    ('machine-learning-fundamentals',    'Machine Learning Fundamentals',     'Machine Learning', 8, 'intermediate'),
    ('image-processing-101',             'Image Processing 101',              'Image Processing', 6, 'beginner'),
    ('multivariable-calculus',           'Multivariable Calculus',            'Mathematics',      9, 'intermediate'),
    ('linear-algebra',                   'Linear Algebra',                    'Mathematics',      8, 'intermediate'),
    ('introduction-to-finance',          'Introduction to Finance',           'Finance',          6, 'beginner'),
    ('introduction-to-statistics',       'Introduction to Statistics',        'Mathematics',      7, 'beginner'),
]

CERTIFICATES = [
    ('WU-2026-0421', 'introduction-to-wolfram-language',           'alice.j@test.com', '2026-04-20'),
    ('WU-2026-0590', 'introduction-to-game-theory',                'alice.j@test.com', '2026-04-21'),
    ('WU-2026-0612', 'introduction-to-partial-differential-equations',
                                                                  'alice.j@test.com', '2026-04-22'),
    ('WU-2026-0733', 'introduction-to-laplace-transforms',         'alice.j@test.com', '2026-04-23'),
    ('WU-2026-0815', 'quick-start-wolfram-tech',                   'alice.j@test.com', '2026-04-24'),
    ('WU-2026-0901', 'visual-explorations-in-data-science',        'alice.j@test.com', '2026-04-25'),
]

BLOG_CATEGORIES = [
    ('wolfram-language',          'Wolfram Language'),
    ('mathematics',               'Mathematics'),
    ('education',                 'Education'),
    ('image-processing',          'Image Processing'),
    ('digital-humanities',        'Digital Humanities'),
    ('wolfram-news',              'Wolfram News'),
    ('mathematica-news',          'Mathematica News'),
    ('life-sciences-and-medicine','Life Sciences and Medicine'),
    ('recreational-computation',  'Recreational Computation'),
    ('events',                    'Events'),
    ('finance',                   'Finance'),
    ('astronomy',                 'Astronomy'),
]

BLOG_POSTS = [
    ('making-wolfram-tech-foundation-llm',
     'Making Wolfram Tech Available as a Foundation Tool for LLM Systems',
     'Stephen Wolfram', '2026-02-14', 'wolfram-language',
     'How Wolfram Language augments LLM systems with symbolic reasoning.'),
    ('instant-supercompute-launch',
     'Instant Supercompute: Launching Wolfram Compute Services',
     'Stephen Wolfram', '2025-12-04', 'wolfram-news',
     'Launch announcement for Wolfram Compute Services.'),
    ('laplace-transforms-etextbook',
     'A Modern eTextbook on Laplace Transforms for Engineering, Science and More',
     'Devendra Kapadia', '2026-05-11', 'education',
     'New interactive eTextbook covering Laplace transforms.'),
    ('checkmate-game-theory-wolfram',
     'Checkmate! Dominate the Competition by Learning Game Theory with Wolfram Language',
     'Vitaliy Kaurov', '2026-04-22', 'mathematics',
     'Game theory tutorial using Wolfram Language workflows.'),
    ('compression-recompression-jpeg',
     'Compression and Recompression of JPEG: Stability, Artifacts and Iterative Image Collapse',
     'Roman Maeder', '2026-03-30', 'image-processing',
     'What happens when you re-compress a JPEG many times.'),
    ('data-adventure-boston-1929',
     'A Data Adventure in Boston, 1929: Historical Census Corpus Analysis',
     'Alan Joyce', '2026-03-12', 'digital-humanities',
     'Computational study of 1929 Boston census data.'),
    ('llms-symbolic-mathematics',
     'LLMs, Symbolic Computation and the Future of Mathematical Discovery',
     'Stephen Wolfram', '2026-02-28', 'mathematics',
     'Where LLMs and symbolic computation meet in math research.'),
    ('vinor-prague-neolithic',
     'Computational Geometry Modeling of the Neolithic Circular Ditch in Vinor, Prague',
     'Silvia Hroncova', '2026-02-15', 'digital-humanities',
     'Geometric reconstruction of an ancient earthwork.'),
    ('elementary-functions-single-operator',
     'All Elementary Functions from a Single Binary Operator',
     'Stephen Wolfram', '2026-01-25', 'mathematics',
     'Reducing the elementary function basis to one binary operator.'),
    ('computational-breast-cancer-detection',
     'A Computational Approach to Early Breast Cancer Detection Using Wolfram',
     'Marina Shchitkova', '2025-11-30', 'life-sciences-and-medicine',
     'Image-classification pipeline applied to breast cancer screening.'),
    ('transmon-cqed-qolab',
     'Transmon cQED: Wolfram x Qolab Collaboration',
     'Wolfram Research', '2025-10-22', 'wolfram-news',
     'Joint quantum-hardware collaboration with Qolab.'),
    ('mathematica-14-1-release',
     'Mathematica 14.1: New Features Across the Board',
     'Roger Germundsson', '2025-07-11', 'mathematica-news',
     'Highlights of the 14.1 release.'),
    ('wolfram-13-3-llm-functions',
     'LLM Functions, Chat Notebooks and What is Next',
     'Stephen Wolfram', '2025-06-04', 'wolfram-language',
     'New LLM functions and chat notebooks.'),
    ('wolfram-language-data-types',
     'A Tour of New Wolfram Language Data Types',
     'Roger Germundsson', '2025-05-15', 'wolfram-language',
     'Tour of typed arrays, packed lists, and structured data.'),
    ('pi-day-2026',
     'Pi Day 2026: Computing 100 Trillion Digits',
     'Alan Joyce', '2026-03-14', 'recreational-computation',
     'Pi day post on record-breaking digit computations.'),
    ('wolfram-summer-school-2025',
     'Wolfram Summer School 2025 Recap',
     'Vitaliy Kaurov', '2025-09-01', 'events',
     'Project highlights from the 2025 Summer School.'),
    ('finance-platform-update',
     'Wolfram Finance Platform 14 Update',
     'Roger Germundsson', '2025-08-20', 'finance',
     'New Finance Platform features.'),
    ('astronomy-image-of-the-day',
     'Building an Astronomy Image of the Day Notebook',
     'Jeffrey Bryant', '2025-04-02', 'astronomy',
     'Daily astronomy image notebook tutorial.'),
]

COMMUNITY_GROUPS = [
    ('wolfram-language',  'Wolfram Language',  18420),
    ('wolfram-alpha',     'Wolfram|Alpha',      4180),
    ('mathematica',       'Mathematica',       21330),
    ('wolfram-cloud',     'Wolfram Cloud',      2210),
    ('wolfram-u',         'Wolfram U',          1480),
    ('general',           'General Discussion',12890),
]

COMMUNITY_TOPICS = [
    (3678635, 'Compression and Recompression of JPEG',     'wolfram-language', 42, 'Roman Maeder'),
    (3682277, 'A Data Adventure in Boston, 1929',          'wolfram-language', 31, 'Alan Joyce'),
    (3711368, 'LLMs and Symbolic Computation',             'wolfram-language', 67, 'Stephen Wolfram'),
    (3710432, 'Neolithic Circular Ditch Geometry',         'wolfram-language', 24, 'Silvia Hroncova'),
    (3694198, 'Elementary Functions from a Single Operator','wolfram-language',58, 'Stephen Wolfram'),
    (3649858, 'Computational Early Breast Cancer Detection','wolfram-language',19, 'Marina Shchitkova'),
    (3666356, 'Transmon cQED with Wolfram',                'mathematica',      15, 'Wolfram Research'),
    (3601822, 'Solving a Tricky Definite Integral',        'mathematica',       9, 'Daniel Lichtblau'),
    (3589104, 'Pattern Matching Gotchas',                  'wolfram-language', 13, 'Vitaliy Kaurov'),
    (3522345, 'Plotting a Riemann Surface',                'mathematica',      11, 'Jeffrey Bryant'),
    (3501776, 'Step-by-Step for Calculus 2 Students',      'wolfram-alpha',    22, 'Devendra Kapadia'),
    (3478910, 'Cloud Deployment Recipes',                  'wolfram-cloud',    18, 'Andre Kuzniarek'),
]

JOBS = [
    ('JOB-2026-101', 'Senior Wolfram Language Engineer', 'Engineering',  'Champaign, IL',     '$140k-$180k'),
    ('JOB-2026-102', 'Machine Learning Research Scientist','Research',   'Remote (US)',        '$160k-$210k'),
    ('JOB-2026-103', 'Documentation Writer',             'Content',      'Boston, MA',         '$80k-$110k'),
    ('JOB-2026-104', 'Cloud Platform SRE',               'Engineering',  'Champaign, IL',      '$130k-$170k'),
    ('JOB-2026-105', 'Computational Mathematician',      'Research',     'Remote (worldwide)', '$120k-$160k'),
    ('JOB-2026-106', 'UI/UX Designer for Notebooks',     'Design',       'Boston, MA',         '$110k-$140k'),
    ('JOB-2026-107', 'Wolfram-U Curriculum Lead',        'Education',    'Champaign, IL',      '$90k-$130k'),
    ('JOB-2026-108', 'LLM Integration Engineer',         'Engineering',  'Remote (US)',        '$150k-$200k'),
    ('JOB-2026-109', 'Marketing Copywriter',             'Marketing',    'Champaign, IL',      '$75k-$95k'),
    ('JOB-2026-110', 'Mobile Apps Engineer (iOS)',       'Engineering',  'Remote (US)',        '$130k-$170k'),
    ('JOB-2026-111', 'Customer Support Specialist',      'Support',      'Remote (US)',        '$60k-$80k'),
    ('JOB-2026-112', 'Quantum Computing Research Intern','Research',     'Champaign, IL',      'Intern'),
]

STORE_PRODUCTS = [
    ('mathematica-home',    'Mathematica Home Edition',          'Software',     360.0,
     'Personal-use Mathematica license for home users.'),
    ('mathematica-student', 'Mathematica Student Edition',       'Software',     159.0,
     'Discounted Mathematica license for enrolled students.'),
    ('mathematica-pro',     'Mathematica Professional',          'Software',    2495.0,
     'Standard Mathematica for industry and research.'),
    ('wolfram-one',         'Wolfram|One',                       'Software',    1295.0,
     'Cloud-and-desktop bundle for general use.'),
    ('wolfram-alpha-pro',   'Wolfram|Alpha Pro (1-year)',        'Subscription',  87.0,
     'One-year Wolfram|Alpha Pro subscription.'),
    ('system-modeler',      'Wolfram System Modeler',            'Software',    1495.0,
     'Multi-physics modeling and simulation platform.'),
    ('finance-platform',    'Wolfram Finance Platform',          'Software',    2495.0,
     'Quant finance and risk analytics platform.'),
    ('cloud-credits-1k',    'Cloud Credits - 1000',              'Credits',       50.0,
     '1000 cloud-compute credits for Wolfram Cloud.'),
    ('cloud-credits-10k',   'Cloud Credits - 10,000',            'Credits',      450.0,
     '10,000 cloud-compute credits, bulk discount.'),
    ('book-tnws',           'A New Kind of Science (hardcover)', 'Book',          75.0,
     'Stephen Wolfram, 2002. Hardcover.'),
    ('book-elementary',     'An Elementary Introduction to the Wolfram Language',
                                                                 'Book',          39.95,
     'Free online edition; this is the print copy.'),
    ('tshirt-wl',           'Wolfram Language T-Shirt',          'Apparel',       24.0,
     'Unisex tee with WL syntax.'),
]

RESEARCH_PAPERS = [
    ('computational-equivalence-2002',
     'Principle of Computational Equivalence', 'Stephen Wolfram', 2002, 'foundations',
     'Cornerstone principle from A New Kind of Science.'),
    ('multiway-systems-2020',
     'Multiway Systems and the Fundamental Theory of Physics', 'Stephen Wolfram', 2020, 'physics',
     'Multiway systems as a model of physics.'),
    ('symbolic-vs-llm-2024',
     'Symbolic vs Neural: A Case Study in Mathematics', 'Wolfram Research', 2024, 'machine-learning',
     'Comparing symbolic and LLM approaches in math benchmarks.'),
    ('cellular-automata-class-1985',
     'A Classification of Cellular Automaton Rules', 'Stephen Wolfram', 1985, 'foundations',
     'The classic four-class classification.'),
    ('wolfram-physics-graphs-2020',
     'Hypergraph Rewriting Rules and Spacetime', 'Jonathan Gorard', 2020, 'physics',
     'Hypergraph rewriting and emergent spacetime.'),
    ('compute-everything-2023',
     'Computational Foundations of Numeric Linear Algebra', 'Daniel Lichtblau', 2023, 'numerics',
     'Numeric linear algebra implementation notes.'),
    ('pattern-matching-rewriting-1998',
     'Pattern Matching and Term Rewriting in Mathematica', 'Roman Maeder', 1998, 'symbolic-computation',
     'Pattern-matching internals.'),
    ('large-language-models-symbolic-2024',
     'Large Language Models Calling Symbolic Tools', 'Stephen Wolfram', 2024, 'machine-learning',
     'Architecture for tool-augmented LLMs.'),
    ('physical-units-2019',
     'Physical Units in Symbolic Computation', 'Wolfram Research', 2019, 'symbolic-computation',
     'Type-safe physical units in Wolfram Language.'),
    ('wolfram-language-history-2014',
     'A Brief History of the Wolfram Language', 'Stephen Wolfram', 2014, 'history',
     'Timeline of the language and its design.'),
    ('knowledge-based-2010',
     'Knowledge-Based Programming', 'Stephen Wolfram', 2010, 'language-design',
     'The knowledge-based paradigm.'),
    ('multivariate-polynomials-2017',
     'Algorithms for Multivariate Polynomials', 'Daniel Lichtblau', 2017, 'numerics',
     'Implementation of resultants and Groebner bases.'),
]

CONFERENCES = [
    ('wtc-2018', 'Wolfram Technology Conference 2018',           2018, 'Champaign, IL',  380),
    ('wtc-2019', 'Wolfram Technology Conference 2019',           2019, 'Champaign, IL',  410),
    ('wtc-2020', 'Wolfram Technology Conference 2020 (Virtual)', 2020, 'Virtual',       1820),
    ('wtc-2021', 'Wolfram Technology Conference 2021 (Virtual)', 2021, 'Virtual',       1950),
    ('wtc-2022', 'Wolfram Technology Conference 2022',           2022, 'Champaign, IL',  510),
    ('wtc-2023', 'Wolfram Technology Conference 2023',           2023, 'Champaign, IL',  540),
    ('wtc-2024', 'Wolfram Technology Conference 2024 (Virtual)', 2024, 'Virtual',       1610),
    ('wtc-2025', 'Wolfram Virtual Technology Conference 2025',   2025, 'Virtual',       1740),
]

DEMONSTRATIONS = [
    (1101, 'Logistic Map Bifurcation',     'mathematics', 'Bifurcation diagram of the logistic map.'),
    (1212, 'Damped Pendulum',              'physics',     'A draggable damped pendulum with phase-space view.'),
    (1325, 'Fourier Series Approximation', 'mathematics', 'Manipulate Fourier coefficients of a square wave.'),
    (1448, '3D Lorenz Attractor',          'mathematics', 'Adjustable Lorenz attractor in 3D.'),
    (1551, 'Periodic Table Explorer',      'chemistry',   'Browse element properties on the periodic table.'),
    (1672, 'Random Walks on Graphs',       'mathematics', 'Animated random walks on common graphs.'),
    (1789, 'Diffraction Pattern',          'physics',     'Single/double-slit diffraction pattern.'),
    (1820, 'Newton Fractal',               'mathematics', 'Newton fractal for f(z) = z^3 - 1.'),
    (1953, 'Pendulum Wave',                'physics',     'Phase-relationship pendulum wave.'),
    (2076, 'Mandelbrot Set Zoom',          'mathematics', 'Zoom into the Mandelbrot set.'),
    (2191, 'DNA Translation',              'biology',     'Translate mRNA to amino acids interactively.'),
    (2204, 'Game of Life',                 'mathematics', 'Conway Game of Life on a torus.'),
    (2317, 'Black Body Radiation',         'physics',     'Planck black-body curves at adjustable T.'),
    (2430, 'Map Projections',              'geography',   'Compare 8 common map projections.'),
    (2543, 'Hypocycloid Curves',           'mathematics', 'Inner-rolling-circle curves with adjustable ratios.'),
    (2666, 'Buffon Needle',                'statistics',  'Buffon needle Monte Carlo for pi.'),
    (2789, 'Galilean Telescope',           'astronomy',   'Geometric ray-trace of a Galilean telescope.'),
    (2802, 'Logistic Regression',          'statistics',  'Manipulate weights of a binary logistic classifier.'),
]

MATHWORLD_ENTRIES = [
    ('Pythagorean-Theorem',  'Pythagorean Theorem',  'geometry',
     'a^2 + b^2 = c^2 for a right triangle.'),
    ('Pi',                   'Pi',                   'numbers',
     'Ratio of a circles circumference to its diameter; ~3.14159.'),
    ('e',                    'e',                    'numbers',
     'Eulers number, base of the natural logarithm; ~2.71828.'),
    ('Golden-Ratio',         'Golden Ratio',         'numbers',
     '(1 + sqrt(5)) / 2; ~1.61803.'),
    ('Fibonacci-Number',     'Fibonacci Number',     'numbers',
     'Sequence 1, 1, 2, 3, 5, 8, 13, ...'),
    ('Riemann-Hypothesis',   'Riemann Hypothesis',   'number-theory',
     'Conjecture on the zeros of the Riemann zeta function.'),
    ('Eulers-Identity',      'Eulers Identity',      'analysis',
     'e^{i pi} + 1 = 0.'),
    ('Prime-Number-Theorem', 'Prime Number Theorem', 'number-theory',
     'Density of primes near n is ~1 / log(n).'),
    ('Twin-Prime-Conjecture','Twin Prime Conjecture','number-theory',
     'Infinitely many primes p with p+2 also prime.'),
    ('Goldbach-Conjecture',  'Goldbach Conjecture',  'number-theory',
     'Every even integer >2 is the sum of two primes.'),
    ('Mandelbrot-Set',       'Mandelbrot Set',       'fractals',
     'Complex c for which iterating z->z^2+c stays bounded.'),
    ('Julia-Set',            'Julia Set',            'fractals',
     'Boundary of the basin of attraction for z->z^2+c.'),
    ('Lorenz-Attractor',     'Lorenz Attractor',     'chaos',
     'Three-dimensional strange attractor of the Lorenz equations.'),
    ('Gaussian-Distribution','Gaussian Distribution','statistics',
     'Bell-shaped continuous probability distribution.'),
    ('Binomial-Coefficient', 'Binomial Coefficient', 'combinatorics',
     'C(n,k) = n! / (k! (n-k)!).'),
    ('Catalan-Number',       'Catalan Number',       'combinatorics',
     'C_n = (2n)! / ((n+1)! n!); 1, 1, 2, 5, 14, 42, ...'),
    ('Eulers-Totient',       'Eulers Totient Function','number-theory',
     'phi(n): count of integers <=n coprime to n.'),
    ('Riemann-Zeta',         'Riemann Zeta Function','analysis',
     'zeta(s) = sum_{n>=1} 1/n^s.'),
    ('Pascals-Triangle',     'Pascals Triangle',     'combinatorics',
     'Triangular array of binomial coefficients.'),
    ('Fermats-Last-Theorem', 'Fermats Last Theorem', 'number-theory',
     'No x,y,z in Z with x^n+y^n=z^n for n>2.'),
    ('Cauchy-Schwarz',       'Cauchy-Schwarz Inequality','analysis',
     '<x,y>^2 <= <x,x><y,y> in any inner-product space.'),
    ('Triangle-Inequality',  'Triangle Inequality',  'analysis',
     '|x+y| <= |x|+|y|.'),
    ('Chebyshev-Polynomials','Chebyshev Polynomials','special-functions',
     'Family of orthogonal polynomials T_n(cos theta)=cos(n theta).'),
    ('Bessel-Function',      'Bessel Function',      'special-functions',
     'Solutions to x^2 y + x y + (x^2 - n^2) y = 0.'),
    ('Legendre-Polynomial',  'Legendre Polynomial',  'special-functions',
     'Orthogonal polynomials P_n(x) on [-1,1].'),
    ('Hermite-Polynomial',   'Hermite Polynomial',   'special-functions',
     'Orthogonal polynomials H_n(x) wrt e^{-x^2}.'),
    ('Gamma-Function',       'Gamma Function',       'special-functions',
     'Gamma(z) = int_0^infty t^{z-1} e^{-t} dt.'),
    ('Beta-Function',        'Beta Function',        'special-functions',
     'B(x,y) = Gamma(x) Gamma(y) / Gamma(x+y).'),
    ('Eulers-Formula',       'Eulers Formula',       'analysis',
     'e^{i theta} = cos(theta) + i sin(theta).'),
    ('Continued-Fraction',   'Continued Fraction',   'number-theory',
     'a_0 + 1/(a_1 + 1/(a_2 + ...)).'),
    ('Greens-Theorem',       'Greens Theorem',       'analysis',
     'Relates a double integral over a region to a line integral.'),
    ('Stokes-Theorem',       'Stokes Theorem',       'analysis',
     'int_M d omega = int_{dM} omega.'),
    ('Bayes-Theorem',        'Bayes Theorem',        'statistics',
     'P(A|B) = P(B|A) P(A) / P(B).'),
    ('Central-Limit-Theorem','Central Limit Theorem','statistics',
     'Sum of i.i.d. RVs converges in distribution to Gaussian.'),
]

INSERTS = [
    ('r11_example_sections',
     '(slug, name, count, description, sort_order) VALUES (?, ?, ?, ?, ?)', EXAMPLE_SECTIONS),
    ('r11_widgets',
     '(slug, name, topic, installs, rating, embed_size) VALUES (?, ?, ?, ?, ?, ?)', WIDGETS),
    ('r11_pub_notebooks',
     '(slug, title, author, cells, abstract, license, language) VALUES (?, ?, ?, ?, ?, ?, ?)', PUB_NOTEBOOKS),
    ('r11_lang_tutorials',
     '(slug, title, abstract, sort_order) VALUES (?, ?, ?, ?)', LANG_TUTORIALS),
    ('r11_courses',
     '(slug, name, category, lessons, level) VALUES (?, ?, ?, ?, ?)', COURSES),
    ('r11_certificates',
     '(cert_id, course_slug, awarded_to, issued_date) VALUES (?, ?, ?, ?)', CERTIFICATES),
    ('r11_blog_categories',
     '(slug, name) VALUES (?, ?)', BLOG_CATEGORIES),
    ('r11_blog_posts',
     '(slug, title, author, date, category_slug, abstract) VALUES (?, ?, ?, ?, ?, ?)', BLOG_POSTS),
    ('r11_community_groups',
     '(slug, name, members) VALUES (?, ?, ?)', COMMUNITY_GROUPS),
    ('r11_community_topics',
     '(tid, title, group_slug, replies, author) VALUES (?, ?, ?, ?, ?)', COMMUNITY_TOPICS),
    ('r11_jobs',
     '(job_id, title, department, location, salary) VALUES (?, ?, ?, ?, ?)', JOBS),
    ('r11_store_products',
     '(slug, name, category, price, description) VALUES (?, ?, ?, ?, ?)', STORE_PRODUCTS),
    ('r11_research_papers',
     '(slug, title, author, year, area, abstract) VALUES (?, ?, ?, ?, ?, ?)', RESEARCH_PAPERS),
    ('r11_conferences',
     '(slug, name, year, location, attendees) VALUES (?, ?, ?, ?, ?)', CONFERENCES),
    ('r11_demonstrations',
     '(did, name, topic, description) VALUES (?, ?, ?, ?)', DEMONSTRATIONS),
    ('r11_mathworld_entries',
     '(slug, name, topic, body) VALUES (?, ?, ?, ?)', MATHWORLD_ENTRIES),
]


def build():
    os.makedirs('instance', exist_ok=True)
    shutil.copyfile(SRC, DST)
    con = sqlite3.connect(DST)
    cur = con.cursor()

    # Idempotency: if r11_widgets exists with rows, this is a no-op rebuild
    # from an already-promoted seed. Just byte-copy and exit.
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='r11_widgets'")
    if cur.fetchone():
        cur.execute("SELECT COUNT(*) FROM r11_widgets")
        if cur.fetchone()[0] > 0:
            print('[r11] r11_widgets already populated; noop rebuild '
                  '(instance/ <- instance_seed/ byte-copy).')
            con.close()
            return

    total = 0
    for ddl in CREATE_TABLES:
        cur.execute(ddl)

    for tname, cols, rows in INSERTS:
        sql = 'INSERT INTO ' + tname + ' ' + cols
        cur.executemany(sql, rows)
        total += len(rows)
        print(f'[r11] inserted {len(rows):4d} rows into {tname}')

    con.commit()

    # Normalize ix_* index order for byte-id reset (matches r10 pattern).
    cur.execute("SELECT name, sql FROM sqlite_master "
                "WHERE type='index' AND name LIKE 'ix_%'")
    idx_rows = cur.fetchall()
    for name, _ in idx_rows:
        cur.execute(f'DROP INDEX IF EXISTS {name}')
    for name, sql in sorted(idx_rows, key=lambda r: r[0]):
        if sql:
            cur.execute(sql)
    con.commit()
    con.execute('VACUUM')
    con.commit()
    con.close()
    print(f'[r11] built {DST} with {total} R11 rows across {len(INSERTS)} tables')


if __name__ == '__main__':
    build()
