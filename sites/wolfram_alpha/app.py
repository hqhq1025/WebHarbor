#!/usr/bin/env python3
"""Wolfram Alpha mirror — Flask + SQLAlchemy + full CRUD"""
import os, json, re, secrets, hashlib
from datetime import datetime, timedelta
from pathlib import Path
from functools import wraps

from flask import (Flask, render_template, request, redirect, url_for,
                   flash, session, jsonify, abort, g)
from flask_sqlalchemy import SQLAlchemy
from flask_login import (LoginManager, UserMixin, login_user, logout_user,
                         login_required, current_user)
from flask_bcrypt import Bcrypt
from flask_wtf.csrf import CSRFProtect

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).parent
app = Flask(__name__)
app.config['SECRET_KEY'] = secrets.token_hex(32)
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{BASE_DIR / 'instance' / 'wolfram_alpha.db'}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['WTF_CSRF_TIME_LIMIT'] = None

(BASE_DIR / 'instance').mkdir(exist_ok=True)

db     = SQLAlchemy(app)
bcrypt = Bcrypt(app)
csrf   = CSRFProtect(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please sign in to access that page.'
login_manager.login_message_category = 'info'

# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class User(db.Model, UserMixin):
    __tablename__ = 'users'
    id            = db.Column(db.Integer, primary_key=True)
    email         = db.Column(db.String(120), unique=True, nullable=False)
    username      = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    full_name     = db.Column(db.String(120), default='')
    institution   = db.Column(db.String(120), default='')
    bio           = db.Column(db.Text, default='')
    is_pro        = db.Column(db.Boolean, default=False)
    pro_plan      = db.Column(db.String(30), default='')   # 'professional', 'premium', 'student'
    pro_since     = db.Column(db.DateTime, nullable=True)
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)

    favorites     = db.relationship('Favorite', backref='user', cascade='all, delete-orphan', lazy=True)
    saved_queries = db.relationship('SavedQuery', backref='user', cascade='all, delete-orphan', lazy=True)
    notebooks     = db.relationship('Notebook', backref='user', cascade='all, delete-orphan', lazy=True)
    history       = db.relationship('QueryHistory', backref='user', cascade='all, delete-orphan', lazy=True)
    feedback      = db.relationship('TopicFeedback', backref='user', cascade='all, delete-orphan', lazy=True)

    def set_password(self, pw): self.password_hash = bcrypt.generate_password_hash(pw).decode()
    def check_password(self, pw): return bcrypt.check_password_hash(self.password_hash, pw)


class Category(db.Model):
    __tablename__ = 'categories'
    id          = db.Column(db.Integer, primary_key=True)
    name        = db.Column(db.String(80), unique=True, nullable=False)
    slug        = db.Column(db.String(80), unique=True, nullable=False)
    description = db.Column(db.Text, default='')
    color       = db.Column(db.String(20), default='#cc4400')  # brand color (WA red-orange)
    icon        = db.Column(db.String(10), default='∑')
    sort_order  = db.Column(db.Integer, default=0)

    subcategories = db.relationship('Subcategory', backref='category', cascade='all, delete-orphan', lazy=True)
    topics        = db.relationship('Topic', backref='category', lazy=True)


class Subcategory(db.Model):
    __tablename__ = 'subcategories'
    id          = db.Column(db.Integer, primary_key=True)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=False)
    name        = db.Column(db.String(80), nullable=False)
    slug        = db.Column(db.String(80), unique=True, nullable=False)
    description = db.Column(db.Text, default='')
    sort_order  = db.Column(db.Integer, default=0)

    topics      = db.relationship('Topic', backref='subcategory', lazy=True)


class Topic(db.Model):
    __tablename__ = 'topics'
    id             = db.Column(db.Integer, primary_key=True)
    category_id    = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=False)
    subcategory_id = db.Column(db.Integer, db.ForeignKey('subcategories.id'), nullable=True)
    name           = db.Column(db.String(120), nullable=False)
    slug           = db.Column(db.String(120), unique=True, nullable=False)
    description    = db.Column(db.Text, default='')
    image          = db.Column(db.String(255), default='')
    examples       = db.Column(db.Text, default='[]')   # JSON list of {query, result, type}
    is_featured    = db.Column(db.Boolean, default=False)
    is_new         = db.Column(db.Boolean, default=False)
    view_count     = db.Column(db.Integer, default=0)
    created_at     = db.Column(db.DateTime, default=datetime.utcnow)

    favorites      = db.relationship('Favorite', backref='topic', cascade='all, delete-orphan', lazy=True)
    feedback       = db.relationship('TopicFeedback', backref='topic', cascade='all, delete-orphan', lazy=True)

    def get_examples(self):
        try: return json.loads(self.examples)
        except: return []

    def avg_rating(self):
        if not self.feedback: return 0
        return round(sum(f.rating for f in self.feedback) / len(self.feedback), 1)


# Cart equivalent: saved queries to run later
class SavedQuery(db.Model):
    __tablename__ = 'saved_queries'
    id         = db.Column(db.Integer, primary_key=True)
    user_id    = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    query_text = db.Column(db.String(500), nullable=False)
    topic_id   = db.Column(db.Integer, db.ForeignKey('topics.id'), nullable=True)
    notes      = db.Column(db.Text, default='')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    topic = db.relationship('Topic')


# Order equivalent: a named notebook (collection of saved queries/results)
class Notebook(db.Model):
    __tablename__ = 'notebooks'
    id          = db.Column(db.Integer, primary_key=True)
    user_id     = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    title       = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, default='')
    is_public   = db.Column(db.Boolean, default=False)
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at  = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    entries     = db.relationship('NotebookEntry', backref='notebook', cascade='all, delete-orphan', lazy=True)


# Order-item equivalent: individual entries in a notebook
class NotebookEntry(db.Model):
    __tablename__ = 'notebook_entries'
    id            = db.Column(db.Integer, primary_key=True)
    notebook_id   = db.Column(db.Integer, db.ForeignKey('notebooks.id'), nullable=False)
    query_text    = db.Column(db.String(500), nullable=False)
    result_summary= db.Column(db.Text, default='')
    notes         = db.Column(db.Text, default='')
    sort_order    = db.Column(db.Integer, default=0)
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)


# Wishlist equivalent: favorited topics
class Favorite(db.Model):
    __tablename__ = 'favorites'
    id         = db.Column(db.Integer, primary_key=True)
    user_id    = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    topic_id   = db.Column(db.Integer, db.ForeignKey('topics.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


# Review equivalent: topic feedback/rating
class TopicFeedback(db.Model):
    __tablename__ = 'topic_feedback'
    id         = db.Column(db.Integer, primary_key=True)
    user_id    = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    topic_id   = db.Column(db.Integer, db.ForeignKey('topics.id'), nullable=False)
    rating     = db.Column(db.Integer, default=5)   # 1–5
    comment    = db.Column(db.Text, default='')
    is_helpful = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


# Query history
class QueryHistory(db.Model):
    __tablename__ = 'query_history'
    id         = db.Column(db.Integer, primary_key=True)
    user_id    = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    query_text = db.Column(db.String(500), nullable=False)
    topic_id   = db.Column(db.Integer, db.ForeignKey('topics.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    topic = db.relationship('Topic')


# Computation results — precomputed answers keyed on input queries.
# Used by /input to render Wolfram|Alpha-style response pods for any task.
class ComputationResult(db.Model):
    __tablename__ = 'computation_results'
    id             = db.Column(db.Integer, primary_key=True)
    input_query    = db.Column(db.String(500), nullable=False)          # raw user-style input
    parsed_input   = db.Column(db.String(500), default='')              # Wolfram-style parsed
    plaintext      = db.Column(db.Text, default='')                     # main plain-text result
    pods           = db.Column(db.Text, default='[]')                   # JSON list of pod dicts
    category       = db.Column(db.String(80), default='')               # e.g. "calculus"
    subcategory    = db.Column(db.String(80), default='')
    units          = db.Column(db.String(80), default='')
    plot_url       = db.Column(db.String(255), default='')
    related_queries= db.Column(db.Text, default='[]')                   # JSON list of strings
    keywords       = db.Column(db.Text, default='')                     # space-joined keywords
    # Comma-separated list of phrases — the user's typed query MUST contain
    # at least ONE of these (case-insensitive substring) for this record to
    # be eligible. Prevents leaks where typing only the operand (e.g. just a
    # polynomial) returns the operation-specific answer (e.g. arc length).
    # Empty/null = no specifier gate (legacy / generic record).
    required_specifiers = db.Column(db.Text, default='')
    topic_slug     = db.Column(db.String(120), default='')              # optional linked topic
    created_at     = db.Column(db.DateTime, default=datetime.utcnow)

    def get_pods(self):
        try: return json.loads(self.pods)
        except: return []

    def get_related(self):
        try: return json.loads(self.related_queries)
        except: return []


@login_manager.user_loader
def load_user(uid): return db.session.get(User, int(uid))

# ---------------------------------------------------------------------------
# Gallery helper
# ---------------------------------------------------------------------------
def load_gallery(slug):
    path = BASE_DIR / 'topic_galleries.json'
    if path.exists():
        with open(path) as f:
            return json.load(f).get(slug, [])
    return []

# ---------------------------------------------------------------------------
# Seed data
# ---------------------------------------------------------------------------
CATEGORIES = [
    {"name": "Mathematics",           "slug": "mathematics",         "color": "#a855f7", "icon": "∑",
     "description": "Compute expert-level answers in mathematics — from elementary arithmetic to symbolic calculus.", "sort_order": 1},
    {"name": "Science & Technology",  "slug": "science-and-technology","color": "#22c55e", "icon": "⚛",
     "description": "Physics, chemistry, astronomy, biology, engineering — factual and computational answers.", "sort_order": 2},
    {"name": "Society & Culture",     "slug": "society-and-culture",  "color": "#ef4444", "icon": "🌍",
     "description": "People, history, geography, finance, arts and more — data-driven knowledge.", "sort_order": 3},
    {"name": "Everyday Life",         "slug": "everyday-life",        "color": "#3b82f6", "icon": "☀",
     "description": "Health, food, travel, sports, personal finance — knowledge for daily decisions.", "sort_order": 4},
]

SUBCATEGORIES = [
    # Mathematics
    {"category_slug":"mathematics","name":"Algebra","slug":"algebra","sort_order":1,
     "description":"Solve equations, factor polynomials, work with algebraic expressions."},
    {"category_slug":"mathematics","name":"Calculus & Analysis","slug":"calculus","sort_order":2,
     "description":"Derivatives, integrals, limits, series, differential equations."},
    {"category_slug":"mathematics","name":"Statistics","slug":"statistics","sort_order":3,
     "description":"Statistical distributions, regression, hypothesis testing, data analysis."},
    {"category_slug":"mathematics","name":"Geometry","slug":"geometry","sort_order":4,
     "description":"Areas, volumes, coordinates, transformations, and geometric proofs."},
    {"category_slug":"mathematics","name":"Number Theory","slug":"number-theory","sort_order":5,
     "description":"Primes, factorization, modular arithmetic, Diophantine equations."},
    {"category_slug":"mathematics","name":"Trigonometry","slug":"trigonometry","sort_order":6,
     "description":"Trigonometric functions, identities, and applications."},
    {"category_slug":"mathematics","name":"Linear Algebra","slug":"linear-algebra","sort_order":7,
     "description":"Matrices, vectors, eigenvalues, and linear transformations."},
    {"category_slug":"mathematics","name":"Probability","slug":"probability","sort_order":8,
     "description":"Probability spaces, random variables, distributions, and combinatorics."},
    # Science
    {"category_slug":"science-and-technology","name":"Physics","slug":"physics","sort_order":1,
     "description":"Classical mechanics, electromagnetism, thermodynamics, quantum physics."},
    {"category_slug":"science-and-technology","name":"Chemistry","slug":"chemistry","sort_order":2,
     "description":"Elements, compounds, reactions, molecular properties, and thermochemistry."},
    {"category_slug":"science-and-technology","name":"Astronomy","slug":"astronomy","sort_order":3,
     "description":"Planets, stars, galaxies, orbital mechanics, and sky charts."},
    {"category_slug":"science-and-technology","name":"Earth Sciences","slug":"earth-science","sort_order":4,
     "description":"Geology, meteorology, oceanography, and physical geography."},
    {"category_slug":"science-and-technology","name":"Life Sciences","slug":"life-sciences","sort_order":5,
     "description":"Biology, anatomy, genetics, ecology, and medical data."},
    {"category_slug":"science-and-technology","name":"Engineering","slug":"engineering","sort_order":6,
     "description":"Electrical, mechanical, civil, and chemical engineering calculations."},
    {"category_slug":"science-and-technology","name":"Units & Measures","slug":"units-measures","sort_order":7,
     "description":"Convert and compute with any unit of measurement."},
    {"category_slug":"science-and-technology","name":"Weather","slug":"weather","sort_order":8,
     "description":"Current conditions, forecasts, and historical weather data."},
    # Society
    {"category_slug":"society-and-culture","name":"People","slug":"people","sort_order":1,
     "description":"Biographical data, demographics, and historical figures."},
    {"category_slug":"society-and-culture","name":"Linguistics","slug":"linguistics","sort_order":2,
     "description":"Word definitions, etymology, linguistics, and language data."},
    {"category_slug":"society-and-culture","name":"Geography","slug":"geography","sort_order":3,
     "description":"Countries, cities, regions, and geopolitical data."},
    {"category_slug":"society-and-culture","name":"Finance","slug":"finance","sort_order":4,
     "description":"Stocks, currencies, mortgages, economic indicators."},
    {"category_slug":"society-and-culture","name":"History","slug":"history","sort_order":5,
     "description":"Historical events, timelines, and civilizations."},
    {"category_slug":"society-and-culture","name":"Arts & Media","slug":"arts-media","sort_order":6,
     "description":"Movies, music, art, literature, and popular culture."},
    # Everyday
    {"category_slug":"everyday-life","name":"Personal Health","slug":"personal-health","sort_order":1,
     "description":"BMI, nutrition, fitness metrics, and health calculations."},
    {"category_slug":"everyday-life","name":"Entertainment","slug":"entertainment","sort_order":2,
     "description":"Movies, music, sports, games, and pop culture."},
    {"category_slug":"everyday-life","name":"Personal Finance","slug":"personal-finance","sort_order":3,
     "description":"Loans, mortgages, savings, tax, and investment calculations."},
    {"category_slug":"everyday-life","name":"Travel","slug":"travel","sort_order":4,
     "description":"Distances, flight times, time zones, and travel data."},
    {"category_slug":"everyday-life","name":"Household Math","slug":"household-math","sort_order":5,
     "description":"Fractions, unit conversions, tips, and practical arithmetic."},
    {"category_slug":"everyday-life","name":"Household Science","slug":"household-science","sort_order":6,
     "description":"Cooking, gardening, weather, animals, and practical science."},
]

TOPICS = [
    # ---- Mathematics ----
    {"category_slug":"mathematics","subcategory_slug":"algebra","name":"Algebra","slug":"algebra",
     "description":"Solve equations, factor polynomials, work with expressions and inequalities. Wolfram Alpha handles everything from simple linear equations to complex polynomial systems.",
     "image":"/static/images/topics/algebra.png","is_featured":True,"is_new":False,
     "examples":json.dumps([
         {"query":"solve 3x + 4 = 19","type":"equation","result":"x = 5"},
         {"query":"factor x^3 - 8","type":"factoring","result":"(x - 2)(x² + 2x + 4)"},
         {"query":"expand (a+b)^6","type":"expansion","result":"a⁶ + 6a⁵b + 15a⁴b² + 20a³b³ + 15a²b⁴ + 6ab⁵ + b⁶"},
         {"query":"solve system 2x+y=5, x-y=1","type":"system","result":"x=2, y=1"},
         {"query":"simplify (x^2-4)/(x+2)","type":"simplification","result":"x - 2"},
     ])},

    {"category_slug":"mathematics","subcategory_slug":"calculus","name":"Calculus & Analysis","slug":"calculus",
     "description":"Compute derivatives, integrals, limits, series expansions, and much more. Wolfram Alpha delivers step-by-step solutions for calculus problems.",
     "image":"/static/images/topics/calculus.png","is_featured":True,"is_new":False,
     "examples":json.dumps([
         {"query":"integrate sin(x) dx","type":"integral","result":"−cos(x) + C"},
         {"query":"d/dx [x^3 * ln(x)]","type":"derivative","result":"x²(1 + 3 ln x)"},
         {"query":"lim x->0 sin(x)/x","type":"limit","result":"1"},
         {"query":"Taylor series e^x around x=0","type":"series","result":"1 + x + x²/2! + x³/3! + ..."},
         {"query":"integrate x^2 from 0 to 3","type":"definite","result":"9"},
     ])},

    {"category_slug":"mathematics","subcategory_slug":"statistics","name":"Statistics","slug":"statistics",
     "description":"Statistical computations including distributions, regression, hypothesis testing, and data analysis. Input your data for instant statistical summaries.",
     "image":"/static/images/topics/statistics.png","is_featured":False,"is_new":False,
     "examples":json.dumps([
         {"query":"mean {1, 4, 7, 2, 8, 3}","type":"descriptive","result":"4.17"},
         {"query":"normal distribution mean=0 sd=1","type":"distribution","result":"PDF/CDF plot and properties"},
         {"query":"linear regression (1,2),(2,3),(3,5),(4,4),(5,6)","type":"regression","result":"y = 0.9x + 1.1"},
         {"query":"binomial distribution n=20 p=0.3","type":"probability","result":"Mean=6, Variance=4.2"},
         {"query":"chi-squared test","type":"hypothesis","result":"Critical values and p-values"},
     ])},

    {"category_slug":"mathematics","subcategory_slug":"geometry","name":"Geometry","slug":"geometry",
     "description":"Compute geometric properties of 2D shapes, 3D solids, and coordinate geometry. From basic areas to advanced differential geometry.",
     "image":"/static/images/topics/geometry.png","is_featured":False,"is_new":False,
     "examples":json.dumps([
         {"query":"area of ellipse a=5, b=3","type":"2d","result":"47.12 square units"},
         {"query":"volume of cone r=4, h=9","type":"3d","result":"150.8 cubic units"},
         {"query":"distance (1,2) to (4,6)","type":"coordinate","result":"5"},
         {"query":"triangle with sides 3,4,5","type":"triangle","result":"Right triangle, area=6"},
         {"query":"regular hexagon side 7","type":"polygon","result":"Area=127.3, Perimeter=42"},
     ])},

    {"category_slug":"mathematics","subcategory_slug":"number-theory","name":"Number Theory","slug":"number-theory",
     "description":"Explore prime factorization, divisibility, modular arithmetic, and number-theoretic functions.",
     "image":"/static/images/topics/number-theory.png","is_featured":False,"is_new":False,
     "examples":json.dumps([
         {"query":"factor 70560","type":"factoring","result":"2⁵ × 3² × 5 × 7²"},
         {"query":"is 1997 prime?","type":"primality","result":"Yes, 1997 is prime"},
         {"query":"gcd(48, 180)","type":"gcd","result":"12"},
         {"query":"phi(100)","type":"euler","result":"40"},
         {"query":"primes up to 50","type":"list","result":"2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47"},
     ])},

    {"category_slug":"mathematics","subcategory_slug":"trigonometry","name":"Trigonometry","slug":"trigonometry",
     "description":"Work with trigonometric functions, identities, inverse functions, and applications in triangles and oscillations.",
     "image":"/static/images/topics/trigonometry.png","is_featured":False,"is_new":False,
     "examples":json.dumps([
         {"query":"sin(pi/6)","type":"value","result":"1/2"},
         {"query":"arctan(1)","type":"inverse","result":"π/4 = 45°"},
         {"query":"simplify sin^2(x) + cos^2(x)","type":"identity","result":"1"},
         {"query":"solve sin(x) = 0.5","type":"equation","result":"x = π/6 + 2πk or 5π/6 + 2πk"},
         {"query":"law of cosines a=5,b=7,C=60°","type":"triangle","result":"c = 6.24"},
     ])},

    {"category_slug":"mathematics","subcategory_slug":"linear-algebra","name":"Linear Algebra","slug":"linear-algebra",
     "description":"Matrix operations, eigenvalues, eigenvectors, vector spaces, and linear transformations.",
     "image":"/static/images/topics/linear-algebra.png","is_featured":False,"is_new":True,
     "examples":json.dumps([
         {"query":"inverse of {{1,2},{3,4}}","type":"matrix","result":"{{-2, 1}, {3/2, -1/2}}"},
         {"query":"eigenvalues {{4,1},{2,3}}","type":"eigenvalues","result":"λ = 2, 5"},
         {"query":"determinant {{1,2,3},{4,5,6},{7,8,9}}","type":"determinant","result":"0"},
         {"query":"solve Ax=b where A={{2,1},{1,3}},b={{5},{10}}","type":"system","result":"x = {1, 3}"},
         {"query":"dot product {1,2,3} {4,5,6}","type":"vectors","result":"32"},
     ])},

    {"category_slug":"mathematics","subcategory_slug":"probability","name":"Probability","slug":"probability",
     "description":"Compute probabilities, work with random variables, and analyze stochastic processes.",
     "image":"/static/images/topics/probability.png","is_featured":False,"is_new":False,
     "examples":json.dumps([
         {"query":"probability of rolling 2 dice summing to 7","type":"dice","result":"6/36 = 1/6 ≈ 16.67%"},
         {"query":"C(52,5)","type":"combinations","result":"2,598,960"},
         {"query":"Poisson distribution lambda=3 k=5","type":"distribution","result":"P(X=5) ≈ 10.08%"},
         {"query":"birthday problem 23 people","type":"paradox","result":"~50.7% chance of shared birthday"},
         {"query":"P(A and B) given P(A)=0.4,P(B)=0.3,P(A|B)=0.5","type":"conditional","result":"P(A∩B) = 0.15"},
     ])},

    # ---- Science & Technology ----
    {"category_slug":"science-and-technology","subcategory_slug":"physics","name":"Physics","slug":"physics",
     "description":"Classical mechanics, electromagnetism, thermodynamics, quantum physics — compute with any physical formula.",
     "image":"/static/images/topics/physics.png","is_featured":True,"is_new":False,
     "examples":json.dumps([
         {"query":"force F = ma, m=5kg a=9.8m/s²","type":"mechanics","result":"F = 49 N"},
         {"query":"photon energy 435nm","type":"quantum","result":"E = 4.57 × 10⁻¹⁹ J (2.85 eV)"},
         {"query":"relativistic mass m=1kg v=0.9c","type":"relativity","result":"m_rel = 2.294 kg"},
         {"query":"Ohm's law V=12V R=4Ω","type":"electricity","result":"I = 3 A"},
         {"query":"escape velocity Earth","type":"gravity","result":"v = 11.19 km/s"},
     ])},

    {"category_slug":"science-and-technology","subcategory_slug":"chemistry","name":"Chemistry","slug":"chemistry",
     "description":"Elements, compounds, chemical reactions, molecular properties — comprehensive chemical data.",
     "image":"/static/images/topics/chemistry.png","is_featured":True,"is_new":False,
     "examples":json.dumps([
         {"query":"carbon","type":"element","result":"Atomic number 6, mass 12.011, [He]2s²2p²"},
         {"query":"balance H2 + O2 -> H2O","type":"equation","result":"2H₂ + O₂ → 2H₂O"},
         {"query":"molecular weight caffeine","type":"molecular","result":"C₈H₁₀N₄O₂ = 194.19 g/mol"},
         {"query":"boiling point of ethanol","type":"properties","result":"78.37 °C (173.07 °F)"},
         {"query":"pH of 0.01 M HCl","type":"acid-base","result":"pH = 2"},
     ])},

    {"category_slug":"science-and-technology","subcategory_slug":"astronomy","name":"Astronomy","slug":"astronomy",
     "description":"Planets, stars, galaxies, orbital mechanics, and sky charts — explore the cosmos.",
     "image":"/static/images/topics/astronomy.png","is_featured":True,"is_new":False,
     "examples":json.dumps([
         {"query":"distance to Mars","type":"planet","result":"54.6 million km (closest approach)"},
         {"query":"mass of Jupiter","type":"planet","result":"1.898 × 10²⁷ kg (317.8 × Earth)"},
         {"query":"Sirius","type":"star","result":"Brightest star, 8.6 ly away, type A1V"},
         {"query":"orbital period of Halley's Comet","type":"orbital","result":"75.32 years"},
         {"query":"ISS orbital speed","type":"satellite","result":"7.66 km/s (27,576 km/h)"},
     ])},

    {"category_slug":"science-and-technology","subcategory_slug":"earth-science","name":"Earth Sciences","slug":"earth-science",
     "description":"Geology, meteorology, oceanography, and physical geography computations.",
     "image":"/static/images/topics/earth-science.png","is_featured":False,"is_new":False,
     "examples":json.dumps([
         {"query":"elevation of Mount Everest","type":"geography","result":"8,848.86 m (29,031.7 ft)"},
         {"query":"richter 7.0 earthquake energy","type":"seismology","result":"≈ 2 petajoules"},
         {"query":"depth of Pacific Ocean","type":"ocean","result":"Max depth: 11,034 m (Mariana Trench)"},
         {"query":"latitude of New York City","type":"location","result":"40.71° N"},
         {"query":"speed of sound in seawater","type":"acoustics","result":"~1,480 m/s"},
     ])},

    {"category_slug":"science-and-technology","subcategory_slug":"weather","name":"Weather","slug":"weather",
     "description":"Real-time weather conditions, forecasts, and historical climate data for any location.",
     "image":"/static/images/topics/weather.png","is_featured":False,"is_new":False,
     "examples":json.dumps([
         {"query":"weather New York City","type":"current","result":"Temperature, humidity, wind, conditions"},
         {"query":"average temperature London in July","type":"climate","result":"22°C (72°F) average high"},
         {"query":"coldest city in the world","type":"extremes","result":"Oymyakon, Russia: −67.7°C"},
         {"query":"UV index today","type":"uv","result":"Real-time UV index for your location"},
         {"query":"hurricane categories","type":"scale","result":"Saffir-Simpson scale: Cat 1–5"},
     ])},

    {"category_slug":"science-and-technology","subcategory_slug":"units-measures","name":"Units & Measures","slug":"units-measures",
     "description":"Convert between any units — length, mass, energy, temperature, currency, and more.",
     "image":"/static/images/topics/units-measures.png","is_featured":False,"is_new":False,
     "examples":json.dumps([
         {"query":"120 meters in feet","type":"length","result":"393.7 feet"},
         {"query":"100 miles per hour in km/h","type":"speed","result":"160.93 km/h"},
         {"query":"1 pound in grams","type":"mass","result":"453.59 g"},
         {"query":"98.6 Fahrenheit in Celsius","type":"temperature","result":"37 °C"},
         {"query":"1 kilowatt-hour in joules","type":"energy","result":"3.6 × 10⁶ J"},
     ])},

    # ---- Society & Culture ----
    {"category_slug":"society-and-culture","subcategory_slug":"people","name":"People","slug":"people",
     "description":"Biographical data, demographics, and information about notable individuals from history and today.",
     "image":"/static/images/topics/people.png","is_featured":False,"is_new":False,
     "examples":json.dumps([
         {"query":"Albert Einstein","type":"person","result":"Physicist, born 1879, Nobel Prize 1921"},
         {"query":"Marie Curie","type":"person","result":"Physicist/chemist, born 1867, 2 Nobel Prizes"},
         {"query":"population of Tokyo","type":"demographics","result":"13.96 million (city), 37.4 million (metro)"},
         {"query":"US presidents list","type":"history","result":"46 presidents from Washington to Biden"},
         {"query":"age of Leonardo da Vinci when he painted Mona Lisa","type":"trivia","result":"≈ 51–53 years old"},
     ])},

    {"category_slug":"society-and-culture","subcategory_slug":"geography","name":"Geography","slug":"geography",
     "description":"Explore countries, cities, regions, and geopolitical data worldwide.",
     "image":"/static/images/topics/geography.png","is_featured":False,"is_new":False,
     "examples":json.dumps([
         {"query":"area of Brazil","type":"country","result":"8,515,767 km²"},
         {"query":"capital of Australia","type":"capital","result":"Canberra"},
         {"query":"distance New York to London","type":"distance","result":"5,570 km (3,459 miles)"},
         {"query":"GDP of Germany","type":"economy","result":"$4.26 trillion (2023)"},
         {"query":"population density Netherlands","type":"density","result":"508 people/km²"},
     ])},

    {"category_slug":"society-and-culture","subcategory_slug":"finance","name":"Finance","slug":"finance",
     "description":"Stock prices, currency exchange, mortgage calculations, and economic data.",
     "image":"/static/images/topics/finance.png","is_featured":True,"is_new":False,
     "examples":json.dumps([
         {"query":"AAPL stock","type":"stock","result":"Apple Inc. current price and historical chart"},
         {"query":"USD to EUR","type":"currency","result":"Current exchange rate"},
         {"query":"mortgage $300,000 6% 30 years","type":"mortgage","result":"Monthly payment: $1,798.65"},
         {"query":"compound interest $1000 5% 10 years","type":"investment","result":"$1,628.89"},
         {"query":"US GDP 2023","type":"economic","result":"$27.36 trillion"},
     ])},

    {"category_slug":"society-and-culture","subcategory_slug":"linguistics","name":"Linguistics","slug":"linguistics",
     "description":"Word definitions, etymology, linguistics analysis, and language data.",
     "image":"/static/images/topics/linguistics.png","is_featured":False,"is_new":False,
     "examples":json.dumps([
         {"query":"etymology of mathematics","type":"etymology","result":"From Greek: mathema (learning, study)"},
         {"query":"anagram of listen","type":"anagram","result":"Silent, Tinsel, Enlist, Inlets"},
         {"query":"words rhyming with orange","type":"rhyme","result":"Sporange, Blorenge (very few!)"},
         {"query":"translate hello in French","type":"translation","result":"Bonjour"},
         {"query":"number of languages in world","type":"linguistics","result":"~7,168 living languages"},
     ])},

    # ---- Everyday Life ----
    {"category_slug":"everyday-life","subcategory_slug":"personal-health","name":"Personal Health","slug":"personal-health",
     "description":"BMI calculations, caloric needs, nutritional analysis, and health metrics.",
     "image":"/static/images/topics/personal-health.png","is_featured":True,"is_new":False,
     "examples":json.dumps([
         {"query":"BMI 5ft10in 170lb","type":"bmi","result":"BMI = 24.4 (Normal weight)"},
         {"query":"calories burned running 5km","type":"exercise","result":"~350 kcal (70 kg person)"},
         {"query":"nutrition facts 100g broccoli","type":"nutrition","result":"34 kcal, 2.8g protein, 6.6g carbs"},
         {"query":"how much water should I drink daily","type":"hydration","result":"~2-3 liters/day (8-10 cups)"},
         {"query":"heart rate zones 30 year old","type":"cardio","result":"Max HR≈190, zones 57-190 bpm"},
     ])},

    {"category_slug":"everyday-life","subcategory_slug":"personal-finance","name":"Personal Finance","slug":"personal-finance",
     "description":"Loans, mortgages, savings, taxes, tips, and financial planning calculations.",
     "image":"/static/images/topics/personal-finance.png","is_featured":False,"is_new":False,
     "examples":json.dumps([
         {"query":"15% tip on $47.50","type":"tip","result":"Tip: $7.13, Total: $54.63"},
         {"query":"loan $20,000 at 7% for 5 years","type":"loan","result":"Monthly: $396.02, Total interest: $3,761"},
         {"query":"$100 savings at 4% for 20 years","type":"savings","result":"Future value: $219.11"},
         {"query":"inflation $1 1980 to 2024","type":"inflation","result":"Equivalent to $3.89 in 2024"},
         {"query":"tax bracket $85,000 income USA","type":"tax","result":"22% federal bracket (MFJ: 12%)"},
     ])},

    {"category_slug":"everyday-life","subcategory_slug":"travel","name":"Travel","slug":"travel",
     "description":"Distances, flight times, time zones, and travel-related computations.",
     "image":"/static/images/topics/travel.png","is_featured":False,"is_new":False,
     "examples":json.dumps([
         {"query":"time difference New York to Tokyo","type":"timezone","result":"+14 hours (EST to JST)"},
         {"query":"flight distance LAX to JFK","type":"flight","result":"3,975 km (2,469 miles)"},
         {"query":"drive time from Boston to Washington DC","type":"drive","result":"~7.5 hours (700 km)"},
         {"query":"currency exchange 100 USD to JPY","type":"currency","result":"~14,900 JPY"},
         {"query":"weather in Paris","type":"weather","result":"Current conditions and forecast"},
     ])},

    {"category_slug":"everyday-life","subcategory_slug":"household-math","name":"Household Math","slug":"household-math",
     "description":"Fractions, percentages, unit conversions, and practical everyday math.",
     "image":"/static/images/topics/household-math.png","is_featured":False,"is_new":True,
     "examples":json.dumps([
         {"query":"1/3 + 1/4","type":"fractions","result":"7/12"},
         {"query":"20% of 350","type":"percentage","result":"70"},
         {"query":"sqrt(144)","type":"arithmetic","result":"12"},
         {"query":"convert 2.5 cups to mL","type":"cooking","result":"591.47 mL"},
         {"query":"how many days until Christmas","type":"date","result":"Computed from today's date"},
     ])},

    {"category_slug":"everyday-life","subcategory_slug":"household-science","name":"Household Science","slug":"household-science",
     "description":"Practical science for everyday life — cooking, animals, nature, and home.",
     "image":"/static/images/topics/household-science.png","is_featured":False,"is_new":False,
     "examples":json.dumps([
         {"query":"boiling point of water at altitude 5000ft","type":"cooking","result":"95.4°C (203.7°F)"},
         {"query":"caffeine in 24oz coffee","type":"food","result":"~340 mg caffeine"},
         {"query":"domestic cat","type":"animals","result":"Felis catus: lifespan 15 yrs, weight 4-5 kg"},
         {"query":"speed of sound in air","type":"physics","result":"343 m/s at 20°C"},
         {"query":"half-life of carbon-14","type":"nuclear","result":"5,730 years"},
     ])},
]

def seed_benchmark_users():
    """Idempotent: creates 4 benchmark users with saved queries, notebooks,
    favorites, and query history. Safe to call multiple times."""
    if User.query.filter_by(email='alice.j@test.com').first():
        return  # already seeded

    BENCH_USERS = [
        dict(email='alice.j@test.com', username='alice_j',
             full_name='Alice Johnson', institution='MIT',
             bio='Mathematics researcher specialising in calculus and analysis.',
             is_pro=True, pro_plan='professional'),
        dict(email='bob.c@test.com', username='bob_c',
             full_name='Bob Chen', institution='Stanford University',
             bio='Physics PhD student. Loves computational mechanics.',
             is_pro=True, pro_plan='student'),
        dict(email='carol.d@test.com', username='carol_d',
             full_name='Carol Davis', institution='',
             bio='High-school teacher. Uses Wolfram for chemistry demos.',
             is_pro=False, pro_plan=''),
        dict(email='david.k@test.com', username='david_k',
             full_name='David Kim', institution='Financial Analytics Inc.',
             bio='Quantitative analyst; finance and statistics power user.',
             is_pro=True, pro_plan='premium'),
    ]

    # Saved-query seeds per user  [query_text, notes, topic_slug_or_None]
    USER_QUERIES = {
        'alice.j@test.com': [
            ('integrate sin(x) dx',               'Standard integral result',    'calculus'),
            ('d/dx [x^3 * ln(x)]',                'Chain rule example',          'calculus'),
            ('lim x->0 sin(x)/x',                 'Classic limit',               'calculus'),
            ('Taylor series e^x around x=0',      'Series expansion',            'calculus'),
            ('eigenvalues {{4,1},{2,3}}',          'Linear algebra check',        'linear-algebra'),
        ],
        'bob.c@test.com': [
            ('force F = ma, m=5kg a=9.8m/s^2',    'Newton 2nd law',              'physics'),
            ('escape velocity Earth',              'Gravity constant check',      'physics'),
            ('photon energy 435nm',                'Quantum mechanics',           'physics'),
            ('relativistic mass m=1kg v=0.9c',    'Special relativity',          'physics'),
            ('Ohm\'s law V=12V R=4Ohm',           'Circuit basics',              'physics'),
        ],
        'carol.d@test.com': [
            ('molecular weight caffeine',          'Demo molecule',               'chemistry'),
            ('balance H2 + O2 -> H2O',            'Balancing reactions lesson',  'chemistry'),
            ('pH of 0.01 M HCl',                  'Acid base demo',              'chemistry'),
            ('boiling point of ethanol',           'Properties demo',             'chemistry'),
            ('carbon',                             'Element lookup',              'chemistry'),
        ],
        'david.k@test.com': [
            ('mortgage $300,000 6% 30 years',     'Home loan scenario',          'finance'),
            ('compound interest $1000 5% 10 years','Investment growth',           'finance'),
            ('USD to EUR',                         'Currency reference',          'finance'),
            ('mean {1, 4, 7, 2, 8, 3}',           'Quick stats',                 'statistics'),
            ('linear regression (1,2),(2,3),(3,5),(4,4),(5,6)', 'Regression demo', 'statistics'),
        ],
    }

    # Notebook seeds per user  [title, description, is_public, entries]
    USER_NOTEBOOKS = {
        'alice.j@test.com': [
            ('Calculus Review', 'Key calculus computations for my research.', False, [
                ('integrate x^2 from 0 to 3',       '9',                'Definite integral'),
                ('d/dx [x^3 * ln(x)]',              'x^2(1+3 ln x)',    'Product rule'),
                ('lim x->0 sin(x)/x',               '1',                'Classic limit'),
                ('Taylor series e^x around x=0',    '1+x+x^2/2!+...',   'Power series'),
            ]),
            ('Linear Algebra Notes', 'Matrix computations and eigenvalue problems.', True, [
                ('eigenvalues {{4,1},{2,3}}',        'lambda=2,5',       'Eigenvalue'),
                ('inverse of {{1,2},{3,4}}',         '{{-2,1},{3/2,-1/2}}', 'Matrix inverse'),
                ('determinant {{1,2,3},{4,5,6},{7,8,9}}', '0',          'Singular matrix'),
            ]),
        ],
        'bob.c@test.com': [
            ('Physics Formulas', 'Classical and quantum mechanics formulas.', False, [
                ('force F = ma, m=5kg a=9.8m/s^2',  '49 N',             'Newton 2nd'),
                ('escape velocity Earth',           '11.19 km/s',       'Gravity'),
                ('photon energy 435nm',             '4.57e-19 J',       'Quantum'),
            ]),
            ('Thermodynamics', 'Heat and energy calculations.', False, [
                ('Ohm\'s law V=12V R=4Ohm',         'I=3 A',            'Circuit'),
                ('relativistic mass m=1kg v=0.9c',  '2.294 kg',         'Relativity'),
            ]),
        ],
        'carol.d@test.com': [
            ('Chemistry Demos', 'Ready-to-show classroom computations.', True, [
                ('balance H2 + O2 -> H2O',          '2H2+O2->2H2O',     'Balancing'),
                ('molecular weight caffeine',        '194.19 g/mol',     'Molecular weight'),
                ('pH of 0.01 M HCl',               'pH=2',              'Acid base'),
            ]),
        ],
        'david.k@test.com': [
            ('Finance Models', 'Financial calculations and market analysis.', False, [
                ('mortgage $300,000 6% 30 years',   '$1798.65/mo',      'Mortgage'),
                ('compound interest $1000 5% 10 years', '$1628.89',     'Investment'),
                ('USD to EUR',                      'Exchange rate',    'Currency'),
            ]),
            ('Statistics Work', 'Data analysis computations.', False, [
                ('mean {1, 4, 7, 2, 8, 3}',         '4.17',             'Descriptive'),
                ('normal distribution mean=0 sd=1', 'PDF/CDF',          'Distribution'),
                ('linear regression (1,2),(2,3),(3,5),(4,4),(5,6)', 'y=0.9x+1.1', 'Regression'),
            ]),
        ],
    }

    # Favorites per user [topic_slug, ...]
    USER_FAVORITES = {
        'alice.j@test.com':  ['calculus', 'linear-algebra', 'algebra', 'statistics'],
        'bob.c@test.com':    ['physics', 'astronomy', 'chemistry', 'engineering'],
        'carol.d@test.com':  ['chemistry', 'personal-health'],
        'david.k@test.com':  ['finance', 'statistics', 'personal-finance', 'geography', 'probability'],
    }

    # Query history per user [query_text, topic_slug_or_None]
    USER_HISTORY = {
        'alice.j@test.com': [
            ('derivative of x^3',             'calculus'),
            ('integrate x^2 dx',              'calculus'),
            ('eigenvalues {{2,1},{1,3}}',      'linear-algebra'),
            ('solve 2x + 5 = 13',             'algebra'),
            ('Taylor series sin(x)',           'calculus'),
            ('matrix determinant {{a,b},{c,d}}', 'linear-algebra'),
        ],
        'bob.c@test.com': [
            ('kinetic energy m=2kg v=10m/s',  'physics'),
            ('speed of light in vacuum',       'physics'),
            ('orbital period of Mars',         'astronomy'),
            ('Bohr radius hydrogen atom',      'physics'),
            ('gravitational constant G',       'physics'),
        ],
        'carol.d@test.com': [
            ('molar mass of NaCl',             'chemistry'),
            ('calories in apple',              'personal-health'),
            ('boiling point water at altitude', 'household-science'),
            ('BMI 5ft6in 140lb',              'personal-health'),
            ('element gold',                   'chemistry'),
        ],
        'david.k@test.com': [
            ('AAPL stock price',               'finance'),
            ('loan $15000 5% 3 years',         'personal-finance'),
            ('GDP of France',                  'geography'),
            ('population Paris',               'geography'),
            ('standard deviation {2,4,4,4,5,5,7,9}', 'statistics'),
            ('variance of data set',           'statistics'),
        ],
    }

    topic_map = {t.slug: t for t in Topic.query.all()}
    now = datetime.utcnow()

    for ud in BENCH_USERS:
        u = User(email=ud['email'], username=ud['username'],
                 full_name=ud['full_name'], institution=ud['institution'],
                 bio=ud['bio'], is_pro=ud['is_pro'], pro_plan=ud['pro_plan'],
                 pro_since=now if ud['is_pro'] else None)
        u.set_password('TestPass123!')
        db.session.add(u)
        db.session.flush()

        # Saved queries
        for i, (qtext, notes, tslug) in enumerate(USER_QUERIES.get(ud['email'], [])):
            topic = topic_map.get(tslug)
            db.session.add(SavedQuery(
                user_id=u.id, query_text=qtext, notes=notes,
                topic_id=topic.id if topic else None,
                created_at=now - timedelta(days=30-i)))

        # Notebooks + entries
        for nb_title, nb_desc, nb_public, nb_entries in USER_NOTEBOOKS.get(ud['email'], []):
            nb = Notebook(user_id=u.id, title=nb_title, description=nb_desc,
                          is_public=nb_public,
                          created_at=now - timedelta(days=20),
                          updated_at=now - timedelta(days=5))
            db.session.add(nb)
            db.session.flush()
            for j, (equery, eresult, enotes) in enumerate(nb_entries):
                db.session.add(NotebookEntry(
                    notebook_id=nb.id, query_text=equery,
                    result_summary=eresult, notes=enotes, sort_order=j))

        # Favorites
        for fslug in USER_FAVORITES.get(ud['email'], []):
            topic = topic_map.get(fslug)
            if topic:
                db.session.add(Favorite(user_id=u.id, topic_id=topic.id))

        # Query history
        for i, (qtext, tslug) in enumerate(USER_HISTORY.get(ud['email'], [])):
            topic = topic_map.get(tslug)
            db.session.add(QueryHistory(
                user_id=u.id, query_text=qtext,
                topic_id=topic.id if topic else None,
                created_at=now - timedelta(hours=i*4)))

    db.session.commit()
    print("Benchmark users seeded.")


def seed_database():
    if User.query.count() > 0:
        return  # already seeded

    # Categories
    cat_map = {}
    for c in CATEGORIES:
        cat = Category(name=c['name'], slug=c['slug'], color=c['color'],
                       icon=c['icon'], description=c['description'],
                       sort_order=c['sort_order'])
        db.session.add(cat)
        db.session.flush()
        cat_map[c['slug']] = cat

    # Subcategories
    sub_map = {}
    for s in SUBCATEGORIES:
        sub = Subcategory(category_id=cat_map[s['category_slug']].id,
                          name=s['name'], slug=s['slug'],
                          description=s['description'], sort_order=s['sort_order'])
        db.session.add(sub)
        db.session.flush()
        sub_map[s['slug']] = sub

    # Topics
    for t in TOPICS:
        sub_slug = t.get('subcategory_slug', '')
        topic = Topic(
            category_id    = cat_map[t['category_slug']].id,
            subcategory_id = sub_map[sub_slug].id if sub_slug in sub_map else None,
            name=t['name'], slug=t['slug'], description=t['description'],
            image=t['image'], examples=t['examples'],
            is_featured=t.get('is_featured', False),
            is_new=t.get('is_new', False),
        )
        db.session.add(topic)

    # Demo user
    demo = User(email='demo@wolframalpha.com', username='demo_user',
                full_name='Demo User', institution='Wolfram Research',
                bio='Computational knowledge enthusiast.', is_pro=True,
                pro_plan='professional', pro_since=datetime.utcnow())
    demo.set_password('demo1234')
    db.session.add(demo)
    db.session.flush()

    # Sample history + favorites for demo user
    topics_sample = Topic.query.limit(5).all()
    for i, topic in enumerate(topics_sample):
        db.session.add(QueryHistory(user_id=demo.id,
            query_text=topic.get_examples()[0]['query'] if topic.get_examples() else topic.name,
            topic_id=topic.id,
            created_at=datetime.utcnow() - timedelta(hours=i*3)))
        db.session.add(Favorite(user_id=demo.id, topic_id=topic.id))

    # Sample notebook
    nb = Notebook(user_id=demo.id, title='My Math Notes',
                  description='Calculus and algebra computations I want to revisit.')
    db.session.add(nb)
    db.session.flush()
    topics_math = Topic.query.filter_by(category_id=cat_map['mathematics'].id).limit(3).all()
    for i, t in enumerate(topics_math):
        ex = t.get_examples()
        db.session.add(NotebookEntry(
            notebook_id=nb.id,
            query_text=ex[0]['query'] if ex else t.name,
            result_summary=ex[0]['result'] if ex else '',
            notes=f'Important {t.name} example.',
            sort_order=i))

    db.session.commit()
    print("Database seeded.")

# ---------------------------------------------------------------------------
# Routes — Static / Example pages
# ---------------------------------------------------------------------------

@app.route('/')
def index():
    home_query = request.args.get('i', '').strip()
    if home_query:
        return redirect(url_for('input_result', i=home_query))
    categories = Category.query.order_by(Category.sort_order).all()
    featured   = Topic.query.filter_by(is_featured=True).limit(8).all()
    new_topics = Topic.query.filter_by(is_new=True).limit(4).all()
    return render_template('index.html', categories=categories,
                           featured=featured, new_topics=new_topics)


@app.route('/examples/<cat_slug>')
def examples(cat_slug):
    normalized = _slugify_human_path(cat_slug)
    if normalized != cat_slug:
        topic = Topic.query.filter_by(slug=normalized).first()
        if topic:
            return redirect(url_for('topic_detail', slug=topic.slug))
        category = Category.query.filter_by(slug=normalized).first()
        if category:
            return redirect(url_for('examples', cat_slug=category.slug))
    category = Category.query.filter_by(slug=cat_slug).first_or_404()
    subcategories = Subcategory.query.filter_by(
        category_id=category.id).order_by(Subcategory.sort_order).all()
    topics_by_sub = {}
    for sub in subcategories:
        topics_by_sub[sub.slug] = Topic.query.filter_by(subcategory_id=sub.id).all()
    return render_template('examples.html', category=category,
                           subcategories=subcategories, topics_by_sub=topics_by_sub)


@app.route('/examples/<cat_slug>/<path:topic_slug>')
def examples_topic_alias(cat_slug, topic_slug):
    """Accept real/example nested topic URLs and route to the topic page."""
    normalized = _slugify_human_path(topic_slug)
    topic = Topic.query.filter_by(slug=normalized).first()
    if topic:
        return redirect(url_for('topic_detail', slug=topic.slug))
    return redirect(url_for('examples', cat_slug=_slugify_human_path(cat_slug)))


@app.route('/topic/<slug>')
def topic_detail(slug):
    topic    = Topic.query.filter_by(slug=slug).first_or_404()
    gallery  = load_gallery(slug)
    related  = Topic.query.filter_by(category_id=topic.category_id).filter(
                   Topic.slug != slug).limit(6).all()
    feedback = TopicFeedback.query.filter_by(topic_id=topic.id).order_by(
                   TopicFeedback.created_at.desc()).limit(10).all()
    is_fav   = False
    if current_user.is_authenticated:
        is_fav = Favorite.query.filter_by(user_id=current_user.id,
                                          topic_id=topic.id).first() is not None
    topic.view_count += 1
    db.session.commit()
    return render_template('topic_detail.html', topic=topic, gallery=gallery,
                           related=related, feedback=feedback, is_fav=is_fav)


def _slugify_human_path(value):
    value = (value or '').strip().lower()
    value = value.replace('&', ' and ')
    value = re.sub(r'[^a-z0-9]+', '-', value)
    return value.strip('-')


STOPWORDS = {
    'the','a','an','of','in','on','at','to','for','with','and','or','is','are',
    'be','by','from','as','that','this','it','you','your','my','me','we','us',
    'what','when','where','how','why','which','who','i','do','does','did','so',
    'if','then','than','can','will','would','should','have','has','had','use',
    'using','each','please','show','tell','give','find','get','compute','calculate',
    'determine','display','compare','plot','write','identify','solve','print',
    'approximate','about','into','out','over','under','between','there','them',
    'their','its','also','only','one','two','any','all','some','more','most',
    'very','total','result','value','values','wolfram','alpha','wolframalpha',
}


def _tokenize(text):
    # Preserve math atoms: letters, digits, ^, *, ', (, ), +, -, =, /
    # Keep single-digit and single-char numeric / operator tokens (useful for 3, 8, i).
    tokens = re.findall(r"[a-z0-9^*'()+\-=/]+", (text or '').lower())
    out = []
    for t in tokens:
        if t in STOPWORDS:
            continue
        # Allow single-char tokens only if they are digits or math atoms.
        if len(t) >= 2:
            out.append(t)
        elif t.isdigit() or t in {'i', '^', '*', "'", '(', ')', '+', '-', '=', '/'}:
            out.append(t)
    return out


def _normalize_math(s):
    """Normalize a math-ish string for substring comparison.

    Collapses whitespace, lowercases, and strips noisy glyphs that often differ
    between a user-typed query and a stored canonical form (e.g. `0.1*i` vs
    `0.1 i`).
    """
    if not s:
        return ''
    s = s.lower()
    s = s.replace('*', '')
    # Collapse runs of whitespace
    s = re.sub(r"\s+", ' ', s).strip()
    # Collapse space around common math glyphs so "1 + 0.1 i" matches "1+0.1i"
    s = re.sub(r"\s*([+\-()^=/])\s*", r"\1", s)
    s = s.replace(' ', '')
    return s


def _score_computation(comp, tokens):
    haystack = ' '.join([
        (comp.input_query or '').lower(),
        (comp.parsed_input or '').lower(),
        (comp.plaintext or '').lower(),
        (comp.keywords or '').lower(),
        (comp.category or '').lower(),
        (comp.subcategory or '').lower(),
    ])
    return sum(1 for t in tokens if t in haystack)


def _lcs_len(a, b):
    """Length of the longest common (contiguous) substring of a and b."""
    if not a or not b:
        return 0
    # Limit length to keep cost bounded — only need a rough tiebreaker signal.
    a = a[:400]
    b = b[:400]
    la, lb = len(a), len(b)
    # 1D rolling DP
    prev = [0] * (lb + 1)
    best = 0
    for i in range(1, la + 1):
        curr = [0] * (lb + 1)
        ai = a[i - 1]
        for j in range(1, lb + 1):
            if ai == b[j - 1]:
                curr[j] = prev[j - 1] + 1
                if curr[j] > best:
                    best = curr[j]
        prev = curr
    return best


def _tiebreak_key(query, comp):
    """Smarter tiebreaker: exact input-string match, then LCS, then token-overlap ratio."""
    ql_norm = _normalize_math(query)
    iq_norm = _normalize_math(comp.input_query or '')
    pi_norm = _normalize_math(comp.parsed_input or '')
    exact = 1 if (ql_norm and (ql_norm == iq_norm or ql_norm == pi_norm)) else 0
    # Longest-common-substring — take max across input_query / parsed_input.
    lcs = max(_lcs_len(ql_norm, iq_norm), _lcs_len(ql_norm, pi_norm))
    # Token-overlap ratio
    qt = set(_tokenize(query))
    ct = set(_tokenize((comp.input_query or '') + ' ' + (comp.parsed_input or '') +
                       ' ' + (comp.keywords or '')))
    if qt:
        overlap = len(qt & ct) / len(qt)
    else:
        overlap = 0.0
    # Return tuple; negative so sort ascending picks the best first.
    return (-exact, -lcs, -overlap)


def _passes_specifier_gate(comp, query):
    """Per-record gate. AND-of-OR groups separated by ';', alternatives
    by ','. The user query must satisfy EVERY group.

    A group prefixed with '!' is a NEGATIVE group: the user query must
    NOT contain any of its alternatives. This lets a record refuse to
    match verbose wordings whose framing belongs to a different
    interpretation (e.g. a `pentagram` distractor that returns the
    concept page must NOT match the verbose task wording "Give a
    constraint on the set of inequalities for the inner region of the
    pentagram" — real WA fails on that wording, so the mirror must too).

    Examples:
      `arc length, length of curve; from 0 to 3, x = 0 to x = 3`
        → user must mention an arc-length keyword AND specific bounds.
      `pentagram; !inequalit, constraint, inner region`
        → user must mention pentagram AND must NOT mention any of the
          verbose-task framing words.
    """
    spec = (comp.required_specifiers or '').strip()
    if not spec:
        return True
    ql = (query or '').lower()
    for group in spec.split(';'):
        group = group.strip()
        if not group:
            continue
        negative = group.startswith('!')
        if negative:
            group = group[1:].strip()
        alts = [p.strip().lower() for p in group.split(',') if p.strip()]
        if not alts:
            continue
        any_match = any(p in ql for p in alts)
        if negative:
            if any_match:
                return False        # forbidden phrase present → reject
        else:
            if not any_match:
                return False        # required phrase absent → reject
    return True


def _find_best_computation(query):
    """Scored relevance match; normalized-substring + smart tiebreakers.

    Every candidate must also pass the per-record specifier gate
    (`required_specifiers`) — typing just an operand (e.g. a polynomial
    alone, a planet name alone) cannot match a record whose answer is for
    a specific operation (e.g. arc length, mass-vs-Earth comparison).
    """
    if not query:
        return None
    all_comps = ComputationResult.query.all()
    if not all_comps:
        return None

    eligible = [c for c in all_comps if _passes_specifier_gate(c, query)]
    if not eligible:
        return None

    # --- (1) Short-circuit: exact normalized match on input_query/parsed_input.
    ql_norm = _normalize_math(query)
    if ql_norm:
        for c in eligible:
            if _normalize_math(c.input_query) == ql_norm:
                return c
            if c.parsed_input and _normalize_math(c.parsed_input) == ql_norm:
                return c

    tokens = _tokenize(query)
    if tokens:
        scored = []
        for c in eligible:
            s = _score_computation(c, tokens)
            if s > 0:
                scored.append((s, c))
        if scored:
            scored.sort(key=lambda x: (-x[0],) + _tiebreak_key(query, x[1]))
            best_score = scored[0][0]
            min_required = max(1, len(tokens) // 3)
            if best_score >= min_required:
                return scored[0][1]

    # --- (2) Normalized-substring fallback (also handles the tokens=[] case).
    if ql_norm:
        best = None
        best_lcs = 0
        for c in eligible:
            iq_norm = _normalize_math(c.input_query)
            pi_norm = _normalize_math(c.parsed_input or '')
            if not iq_norm and not pi_norm:
                continue
            if (ql_norm and (ql_norm in iq_norm or iq_norm in ql_norm or
                             (pi_norm and (ql_norm in pi_norm or pi_norm in ql_norm)))):
                lcs = max(_lcs_len(ql_norm, iq_norm), _lcs_len(ql_norm, pi_norm))
                if lcs > best_lcs:
                    best, best_lcs = c, lcs
        if best is not None:
            return best

    # --- (3) Legacy fuzzy-contains fallback (case-insensitive, raw strings).
    ql = query.lower()
    for c in eligible:
        iq = (c.input_query or '').lower()
        if iq and (ql in iq or iq in ql):
            return c
    return None


@app.route('/input')
def input_result():
    q = request.args.get('i', '').strip()
    assumption = request.args.get('assumption', '').strip()
    if not q:
        return redirect(url_for('index'))

    # Find best matching precomputed result
    computation = _find_best_computation(q)

    # Find best matching topic for sidebar/related content
    matching_topic = None
    if computation and computation.topic_slug:
        matching_topic = Topic.query.filter_by(slug=computation.topic_slug).first()
    if not matching_topic:
        tokens = _tokenize(q)
        for tok in tokens:
            matching_topic = Topic.query.filter(
                (Topic.name.ilike(f'%{tok}%')) |
                (Topic.slug.ilike(f'%{tok}%')) |
                (Topic.description.ilike(f'%{tok}%'))
            ).first()
            if matching_topic:
                break

    # Build assumption pill bar — derive from category/topic, deterministic.
    pills = _build_assumption_pills(q, computation, matching_topic, assumption)

    # Log history if logged in
    if current_user.is_authenticated:
        hist = QueryHistory(user_id=current_user.id, query_text=q,
                            topic_id=matching_topic.id if matching_topic else None)
        db.session.add(hist)
        db.session.commit()

    if matching_topic:
        related = Topic.query.filter_by(
            category_id=matching_topic.category_id).filter(
            Topic.id != matching_topic.id).limit(4).all()
    else:
        related = Topic.query.limit(4).all()

    return render_template('input_result.html', query=q,
                           computation=computation,
                           matching_topic=matching_topic, related=related,
                           pills=pills, current_assumption=assumption)


def _build_assumption_pills(q, comp, topic, current):
    """Return ordered list of (label, value, is_active) for the assumption bar."""
    # Category-aware default options. Order is stable per (category, query) pair
    # so the pill bar is deterministic.
    cat = (comp.category if comp else (topic.category.slug if topic else '')) or 'general'
    options_by_cat = {
        'mathematics':            ['mathematical operation', 'symbolic expression', 'numerical evaluation', 'word'],
        'science-and-technology': ['physical quantity', 'chemical compound', 'mathematical operation', 'unit'],
        'everyday-life':          ['everyday concept', 'unit', 'mathematical operation', 'word'],
        'society-and-culture':    ['entity name', 'word', 'phrase', 'concept'],
        'general':                ['natural language', 'mathematical operation', 'unit', 'word'],
    }
    opts = options_by_cat.get(cat, options_by_cat['general'])
    return [(o, o, (o == current) if current else (i == 0))
            for i, o in enumerate(opts)]


@app.route('/share/<int:cr_id>')
def share(cr_id):
    """Public share-link page for a single computation result.

    R5: also handles ?as=image to render a printable "image" rendition of the
    result that the user can right-click → 'save as image' to download as PNG.
    The HTML uses CSS print-style framing so screenshots/share-as-PNG look clean.
    """
    comp = db.session.get(ComputationResult, cr_id)
    if not comp:
        abort(404)
    permalink = request.host_url.rstrip('/') + url_for('share', cr_id=cr_id)
    permalink_image = request.host_url.rstrip('/') + url_for('share', cr_id=cr_id) + '?as=image'
    as_image = (request.args.get('as') == 'image')
    return render_template('share.html', comp=comp, permalink=permalink,
                           permalink_image=permalink_image, as_image=as_image)


@app.route('/widget/builder')
def widget_builder():
    """Drag-and-drop widget builder landing page.

    R5: also accepts ?source=<computation_id> to pre-populate the builder with
    a result from the input page. Returns a size-picker (4 presets + custom).
    """
    source_id = request.args.get('source', type=int)
    source_comp = db.session.get(ComputationResult, source_id) if source_id else None
    return render_template('widget_builder.html', widgets=WIDGET_GALLERY,
                           source_comp=source_comp)


# Resource catalog — deterministic listing per type
RESOURCE_CATALOG = {
    'tutorials': {'label': 'Tutorials', 'desc': 'Guided tours of Wolfram|Alpha features.',
                  'items': [
                      ('Getting Started', 'Learn the basics of Wolfram|Alpha.'),
                      ('Math Input Mode', 'Use the math palette and LaTeX-style entry.'),
                      ('Step-by-Step Solutions', 'Unlock guided derivations with Pro.'),
                      ('Data Upload', 'Analyze your own CSV/Excel data.'),
                      ('Image Input', 'Solve handwritten equations from photos.'),
                  ]},
    'examples':  {'label': 'Example Galleries',
                  'desc': 'Curated example queries by domain.',
                  'items': [
                      ('Calculus Examples', '/examples/mathematics/calculus'),
                      ('Physics Examples', '/examples/science-and-technology/physics'),
                      ('Chemistry Examples', '/examples/science-and-technology/chemistry'),
                      ('Personal Finance', '/examples/everyday-life/personal-finance'),
                      ('Geography', '/examples/society-and-culture/geography'),
                  ]},
    'widgets':   {'label': 'Widgets',
                  'desc': 'Embeddable Wolfram|Alpha widgets for blogs and class pages.',
                  'items': [
                      ('Derivative Calculator', '/widget/derivative-calculator'),
                      ('Integral Calculator', '/widget/integral-calculator'),
                      ('BMI Calculator', '/widget/bmi-calculator'),
                      ('Mortgage Calculator', '/widget/mortgage-calculator'),
                      ('Statistics Summary', '/widget/statistics-summary'),
                  ]},
    'api':       {'label': 'API References',
                  'desc': 'Wolfram|Alpha developer API surface.',
                  'items': [
                      ('Short Answers API', '/products/short-answers-api'),
                      ('Full Results API',  '/products/full-results-api'),
                      ('Conversational API','/products/conversational-api'),
                      ('Simple API',        '/products/simple-api'),
                      ('Spoken Results API','/products/spoken-results-api'),
                  ]},
    'datasets':  {'label': 'Datasets',
                  'desc': 'Curated datasets accessible through Wolfram|Alpha.',
                  'items': [
                      ('Country Data', 'Population, GDP, demographics for 200+ countries.'),
                      ('Element Data', '118 elements with full property tables.'),
                      ('Astronomical Data', 'Solar system bodies, stars, galaxies.'),
                      ('Financial Data', 'Stock tickers, indices, currencies.'),
                      ('Word Data', 'Dictionary, etymology, frequency.'),
                  ]},
    'videos':    {'label': 'Videos',
                  'desc': 'Wolfram TV — tutorial and product videos.',
                  'items': [
                      ('Wolfram|Alpha 101', 'Intro video tour.'),
                      ('Pro Walkthrough', 'Tour of every Pro feature.'),
                      ('Wolfram Language in 15 Minutes', 'Whirlwind tour of WL.'),
                  ]},
}


@app.route('/resources/<rtype>')
def resources(rtype):
    info = RESOURCE_CATALOG.get(rtype)
    if not info:
        abort(404)
    return render_template('resources.html', rtype=rtype, info=info,
                           all_types=RESOURCE_CATALOG)


# Wolfram|Alpha API product pages — deterministic, slug-driven
PRODUCT_APIS = {
    'short-answers-api':  {'name': 'Short Answers API',
                           'tagline': 'Get a single short-form text answer.',
                           'endpoint': 'http://api.wolframalpha.com/v1/result',
                           'rate':     '2000 calls/month free tier'},
    'full-results-api':   {'name': 'Full Results API',
                           'tagline': 'Complete result with every pod, image, and asset.',
                           'endpoint': 'http://api.wolframalpha.com/v2/query',
                           'rate':     '2000 calls/month free tier'},
    'conversational-api': {'name': 'Conversational API',
                           'tagline': 'Multi-turn back-and-forth Wolfram|Alpha conversations.',
                           'endpoint': 'http://api.wolframalpha.com/v1/conversation.jsp',
                           'rate':     '500 calls/month free tier'},
    'simple-api':         {'name': 'Simple API',
                           'tagline': 'Single static image of the full result page.',
                           'endpoint': 'http://api.wolframalpha.com/v1/simple',
                           'rate':     '2000 calls/month free tier'},
    'spoken-results-api': {'name': 'Spoken Results API',
                           'tagline': 'Answer optimized for text-to-speech.',
                           'endpoint': 'http://api.wolframalpha.com/v1/spoken',
                           'rate':     '2000 calls/month free tier'},
}


@app.route('/products/<api_slug>')
def product_api(api_slug):
    api = PRODUCT_APIS.get(api_slug)
    if not api:
        abort(404)
    return render_template('product_api.html', api=api, slug=api_slug,
                           all_apis=PRODUCT_APIS)


@app.route('/pro')
def pro():
    return render_template('pro.html')


@app.route('/pro/pricing')
def pro_pricing():
    return render_template('pro_pricing.html')


@app.route('/pro/upgrade')
def pro_upgrade():
    """Upgrade-CTA landing page emphasising the value of switching to Pro.

    Drives the step-by-step paywall conversion funnel (see /step-by-step/<id>).
    """
    return render_template('pro_upgrade.html')


@app.route('/pro/features')
def pro_features():
    """Detailed feature comparison: Free vs Pro vs Pro Premium."""
    return render_template('pro_features.html')


@app.route('/step-by-step/<int:cr_id>')
def step_by_step(cr_id):
    """Pro-gated step-by-step solution display for a computation result."""
    comp = db.session.get(ComputationResult, cr_id)
    if not comp:
        abort(404)
    # Look at all pods named 'Step ...' as the step content
    pods = comp.get_pods()
    step_pods = [p for p in pods if str(p.get('title','')).lower().startswith('step')]
    is_pro = current_user.is_authenticated and getattr(current_user, 'is_pro', False)
    return render_template('step_by_step.html',
                           comp=comp, step_pods=step_pods, is_pro=is_pro)


# Static-but-deterministic widget catalogue. Each widget is a self-contained
# computational mini-app — mirroring developer.wolframalpha.com/widgets.
WIDGET_GALLERY = [
    {"slug": "derivative-calculator", "name": "Derivative Calculator",
     "category": "calculus",
     "description": "Compute the derivative of any expression with respect to a chosen variable.",
     "sample_input": "x^2 sin(x)", "sample_output": "2 x sin(x) + x^2 cos(x)"},
    {"slug": "integral-calculator", "name": "Integral Calculator",
     "category": "calculus",
     "description": "Antiderivative and definite-integral evaluation with bounds.",
     "sample_input": "integrate x^2 from 0 to 3", "sample_output": "9"},
    {"slug": "matrix-determinant", "name": "Matrix Determinant",
     "category": "linear-algebra",
     "description": "Compute the determinant of a square matrix up to 5×5.",
     "sample_input": "{{1,2},{3,4}}", "sample_output": "-2"},
    {"slug": "eigenvalue-finder", "name": "Eigenvalue Finder",
     "category": "linear-algebra",
     "description": "Find eigenvalues and eigenvectors of any matrix.",
     "sample_input": "{{4,1},{2,3}}", "sample_output": "λ = 2, 5"},
    {"slug": "polynomial-roots", "name": "Polynomial Root Finder",
     "category": "algebra",
     "description": "Solve polynomial equations symbolically or numerically.",
     "sample_input": "x^3 - 6x^2 + 11x - 6", "sample_output": "x = 1, 2, 3"},
    {"slug": "unit-converter", "name": "Unit Converter",
     "category": "units",
     "description": "Convert between units across length, mass, volume, energy, and more.",
     "sample_input": "5 km in miles", "sample_output": "≈ 3.107 mi"},
    {"slug": "currency-converter", "name": "Currency Converter",
     "category": "finance",
     "description": "Convert between major world currencies.",
     "sample_input": "100 USD to EUR", "sample_output": "≈ €91.74"},
    {"slug": "mortgage-calculator", "name": "Mortgage Calculator",
     "category": "finance",
     "description": "Compute monthly payments, total interest, and amortization.",
     "sample_input": "$300k 6% 30yr", "sample_output": "Monthly ≈ $1798"},
    {"slug": "bmi-calculator", "name": "BMI Calculator",
     "category": "health",
     "description": "Compute body mass index from height and weight.",
     "sample_input": "70 kg 175 cm", "sample_output": "BMI ≈ 22.86"},
    {"slug": "tip-calculator", "name": "Tip Calculator",
     "category": "everyday",
     "description": "Compute restaurant tip and split bills.",
     "sample_input": "20% on $85", "sample_output": "Tip $17, total $102"},
    {"slug": "compound-interest", "name": "Compound Interest",
     "category": "finance",
     "description": "Future-value of investments under monthly compounding.",
     "sample_input": "$1000 5% 10yr", "sample_output": "≈ $1648.66"},
    {"slug": "scientific-calc", "name": "Scientific Calculator",
     "category": "general",
     "description": "Full scientific calculator with trig, logs, and constants.",
     "sample_input": "sin(45°) + cos(30°)", "sample_output": "≈ 1.5731"},
    {"slug": "trig-identities", "name": "Trig Identity Verifier",
     "category": "trigonometry",
     "description": "Verify and simplify trigonometric identities.",
     "sample_input": "sin²(x) + cos²(x)", "sample_output": "1"},
    {"slug": "statistics-summary", "name": "Statistics Summary",
     "category": "statistics",
     "description": "Compute mean, median, mode, σ, and quartiles for a dataset.",
     "sample_input": "{1, 2, 3, 4, 5, 6, 7}", "sample_output": "x̄=4, σ≈2"},
    {"slug": "probability-dice", "name": "Dice Probability",
     "category": "probability",
     "description": "Compute probabilities for n-dice rolls.",
     "sample_input": "P(sum=7) with 2d6", "sample_output": "6/36 = 16.67%"},
    {"slug": "plot-function", "name": "Function Plotter",
     "category": "calculus",
     "description": "Plot any 1D function on an interval.",
     "sample_input": "plot sin(x) from 0 to 2pi", "sample_output": "[chart]"},
]


@app.route('/widgets')
def widgets_gallery():
    return render_template('widgets_gallery.html', widgets=WIDGET_GALLERY)


@app.route('/widget/<slug>')
def widget_detail(slug):
    widget = next((w for w in WIDGET_GALLERY if w['slug'] == slug), None)
    if not widget:
        abort(404)
    return render_template('widget_detail.html', widget=widget,
                           widgets=WIDGET_GALLERY)


# Input tab types: a vertical slice of the Wolfram|Alpha input modes.
INPUT_TABS = {
    "math":     {"label": "Math Input",   "icon": "∫",
                 "blurb": "Use the math palette to enter LaTeX-like expressions, integrals, summations, matrices, and Greek letters.",
                 "examples": ["integrate sin(x)^2 dx", "matrix {{1,2},{3,4}} determinant",
                              "limit (1+1/n)^n as n -> infinity"]},
    "image":    {"label": "Image Input",  "icon": "📷",
                 "blurb": "Upload a photo to identify objects, read handwritten equations, or extract chemical structures.",
                 "examples": ["plant identification", "handwritten equation", "chemical structure recognition"]},
    "audio":    {"label": "Audio Input",  "icon": "🔊",
                 "blurb": "Upload audio for melody recognition, frequency analysis, or speech transcription.",
                 "examples": ["song identification", "FFT spectrum", "bird call ID"]},
    "code":     {"label": "Code / Wolfram Language", "icon": "{}",
                 "blurb": "Run Wolfram Language expressions directly — Solve, Plot, Integrate, etc.",
                 "examples": ["Solve[x^2-4==0, x]", "Plot[Sin[x], {x,0,2 Pi}]",
                              "FactorInteger[2024]"]},
    "data":     {"label": "Data Input",   "icon": "📊",
                 "blurb": "Paste CSV or structured data for descriptive statistics, regression, and visualization.",
                 "examples": ["1,2,3,4,5 statistics", "linear regression {{1,2},{2,3},{3,5}}",
                              "fit polynomial degree 2"]},
    "natural":  {"label": "Natural Language", "icon": "💬",
                 "blurb": "Just type the question. Wolfram interprets ordinary English/math notation.",
                 "examples": ["distance from New York to Paris",
                              "calories in an apple", "next solar eclipse"]},
}


@app.route('/input-tab/<tab_type>')
def input_tab(tab_type):
    tab = INPUT_TABS.get(tab_type)
    if not tab:
        abort(404)
    return render_template('input_tab.html', tab=tab, tab_type=tab_type,
                           all_tabs=INPUT_TABS)


@app.route('/examples/<cat_slug>/<sub_slug>')
def examples_sub(cat_slug, sub_slug):
    """Drill-down view: examples for a single subcategory within a category."""
    category = Category.query.filter_by(slug=cat_slug).first()
    if not category:
        abort(404)
    subcategory = Subcategory.query.filter_by(slug=sub_slug,
                                              category_id=category.id).first()
    if not subcategory:
        abort(404)
    topics = Topic.query.filter_by(subcategory_id=subcategory.id).order_by(Topic.name).all()
    return render_template('examples_sub.html',
                           category=category, subcategory=subcategory, topics=topics)


@app.route('/about')
def about():
    return render_template('about.html')


@app.route('/products')
def products():
    return render_template('products.html')


@app.route('/mobile-apps')
def mobile_apps():
    return render_template('mobile_apps.html')


@app.route('/search')
def search():
    q = request.args.get('q', '').strip()
    results = []
    if q:
        tokens = _tokenize(q)
        if tokens:
            all_topics = Topic.query.all()
            scored = []
            for t in all_topics:
                hay = ' '.join([(t.name or '').lower(),
                                (t.slug or '').lower(),
                                (t.description or '').lower(),
                                (t.examples or '').lower()])
                s = sum(1 for tok in tokens if tok in hay)
                if s > 0:
                    scored.append((s, t))
            scored.sort(key=lambda x: -x[0])
            results = [t for _, t in scored[:20]]
        if not results:
            results = Topic.query.filter(
                (Topic.name.ilike(f'%{q}%')) |
                (Topic.description.ilike(f'%{q}%'))
            ).limit(20).all()
    categories = Category.query.order_by(Category.sort_order).all()
    return render_template('search.html', query=q, results=results,
                           categories=categories)


# ---------------------------------------------------------------------------
# Auth routes
# ---------------------------------------------------------------------------

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('account'))
    if request.method == 'POST':
        identifier = request.form.get('email', '').strip()
        password   = request.form.get('password', '')
        user = User.query.filter(
            (User.email == identifier) | (User.username == identifier)
        ).first()
        if user and user.check_password(password):
            login_user(user, remember=request.form.get('remember') == 'on')
            flash(f'Welcome back, {user.username}!', 'success')
            nxt = request.args.get('next')
            return redirect(nxt or url_for('account'))
        flash('Invalid email/username or password.', 'danger')
    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('account'))
    if request.method == 'POST':
        email    = request.form.get('email', '').strip().lower()
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        confirm  = request.form.get('confirm', '')
        if not email or not username or not password:
            flash('All fields are required.', 'danger')
        elif password != confirm:
            flash('Passwords do not match.', 'danger')
        elif len(password) < 6:
            flash('Password must be at least 6 characters.', 'danger')
        elif User.query.filter_by(email=email).first():
            flash('Email already registered.', 'danger')
        elif User.query.filter_by(username=username).first():
            flash('Username already taken.', 'danger')
        else:
            user = User(email=email, username=username)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            login_user(user)
            flash('Account created! Welcome to Wolfram Alpha.', 'success')
            return redirect(url_for('account'))
    return render_template('register.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been signed out.', 'info')
    return redirect(url_for('index'))


# ---------------------------------------------------------------------------
# Account routes
# ---------------------------------------------------------------------------

@app.route('/account')
@login_required
def account():
    history   = QueryHistory.query.filter_by(user_id=current_user.id)\
                    .order_by(QueryHistory.created_at.desc()).limit(20).all()
    favorites = Favorite.query.filter_by(user_id=current_user.id)\
                    .order_by(Favorite.created_at.desc()).all()
    notebooks = Notebook.query.filter_by(user_id=current_user.id)\
                    .order_by(Notebook.updated_at.desc()).all()
    queries   = SavedQuery.query.filter_by(user_id=current_user.id)\
                    .order_by(SavedQuery.created_at.desc()).limit(10).all()
    return render_template('account.html', history=history,
                           favorites=favorites, notebooks=notebooks,
                           saved_queries=queries)


@app.route('/account/edit', methods=['GET', 'POST'])
@login_required
def account_edit():
    if request.method == 'POST':
        current_user.full_name   = request.form.get('full_name', '').strip()
        current_user.institution = request.form.get('institution', '').strip()
        current_user.bio         = request.form.get('bio', '').strip()
        new_email = request.form.get('email', '').strip().lower()
        if new_email and new_email != current_user.email:
            if User.query.filter_by(email=new_email).first():
                flash('Email already in use.', 'danger')
                return render_template('account_edit.html')
            current_user.email = new_email
        db.session.commit()
        flash('Profile updated.', 'success')
        return redirect(url_for('account'))
    return render_template('account_edit.html')


@app.route('/account/password', methods=['GET', 'POST'])
@login_required
def change_password():
    if request.method == 'POST':
        current  = request.form.get('current_password', '')
        new_pw   = request.form.get('new_password', '')
        confirm  = request.form.get('confirm_password', '')
        if not current_user.check_password(current):
            flash('Current password is incorrect.', 'danger')
        elif len(new_pw) < 6:
            flash('New password must be at least 6 characters.', 'danger')
        elif new_pw != confirm:
            flash('New passwords do not match.', 'danger')
        else:
            current_user.set_password(new_pw)
            db.session.commit()
            flash('Password changed successfully.', 'success')
            return redirect(url_for('account'))
    return render_template('change_password.html')


@app.route('/account/delete', methods=['POST'])
@login_required
def account_delete():
    user = db.session.get(User, current_user.id)
    logout_user()
    db.session.delete(user)
    db.session.commit()
    flash('Your account has been deleted.', 'info')
    return redirect(url_for('index'))


# ---------------------------------------------------------------------------
# Favorites (Wishlist equivalent)
# ---------------------------------------------------------------------------

@app.route('/favorites')
@login_required
def favorites():
    favs = Favorite.query.filter_by(user_id=current_user.id)\
               .order_by(Favorite.created_at.desc()).all()
    return render_template('favorites.html', favorites=favs)


@app.route('/favorites/remove/<int:fav_id>', methods=['POST'])
@login_required
def remove_favorite(fav_id):
    fav = Favorite.query.filter_by(id=fav_id, user_id=current_user.id).first_or_404()
    db.session.delete(fav)
    db.session.commit()
    flash('Removed from favorites.', 'info')
    return redirect(url_for('favorites'))


@app.route('/favorites/add', methods=['POST'])
@login_required
def favorites_add():
    """Form-POST: add a topic to favorites by topic_id."""
    topic_id = request.form.get('topic_id', type=int)
    topic = db.session.get(Topic, topic_id)
    if not topic:
        flash('Topic not found.', 'danger')
        return redirect(url_for('favorites'))
    existing = Favorite.query.filter_by(user_id=current_user.id, topic_id=topic_id).first()
    if not existing:
        db.session.add(Favorite(user_id=current_user.id, topic_id=topic_id))
        db.session.commit()
        flash(f'"{topic.name}" added to favorites.', 'success')
    else:
        flash(f'"{topic.name}" is already in your favorites.', 'info')
    next_url = request.form.get('next') or url_for('topic_detail', slug=topic.slug)
    return redirect(next_url)


@app.route('/favorites/toggle', methods=['POST'])
@login_required
def favorites_toggle():
    """Form-POST: toggle favorite for topic_id; redirect to topic or favorites page."""
    topic_id = request.form.get('topic_id', type=int)
    topic = db.session.get(Topic, topic_id)
    if not topic:
        flash('Topic not found.', 'danger')
        return redirect(url_for('favorites'))
    existing = Favorite.query.filter_by(user_id=current_user.id, topic_id=topic_id).first()
    if existing:
        db.session.delete(existing)
        db.session.commit()
        flash(f'"{topic.name}" removed from favorites.', 'info')
    else:
        db.session.add(Favorite(user_id=current_user.id, topic_id=topic_id))
        db.session.commit()
        flash(f'"{topic.name}" added to favorites.', 'success')
    next_url = request.form.get('next') or url_for('topic_detail', slug=topic.slug)
    return redirect(next_url)


# ---------------------------------------------------------------------------
# Notebooks (Order equivalent)
# ---------------------------------------------------------------------------

@app.route('/notebooks')
@login_required
def notebooks():
    nbs = Notebook.query.filter_by(user_id=current_user.id)\
              .order_by(Notebook.updated_at.desc()).all()
    return render_template('notebooks.html', notebooks=nbs)


@app.route('/notebook/create', methods=['GET', 'POST'])
@login_required
def notebook_create():
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        if not title:
            flash('Notebook title is required.', 'danger')
        else:
            nb = Notebook(user_id=current_user.id,
                          title=title,
                          description=request.form.get('description', '').strip(),
                          is_public=request.form.get('is_public') == 'on')
            db.session.add(nb)
            db.session.commit()
            flash(f'Notebook "{title}" created.', 'success')
            return redirect(url_for('notebook_detail', nb_id=nb.id))
    return render_template('notebook_create.html')


@app.route('/notebook/<int:nb_id>')
@login_required
def notebook_detail(nb_id):
    nb = Notebook.query.filter_by(id=nb_id, user_id=current_user.id).first_or_404()
    entries = NotebookEntry.query.filter_by(notebook_id=nb.id)\
                  .order_by(NotebookEntry.sort_order).all()
    return render_template('notebook_detail.html', notebook=nb, entries=entries)


@app.route('/notebook/<int:nb_id>/add', methods=['POST'])
@login_required
def notebook_add_entry(nb_id):
    nb = Notebook.query.filter_by(id=nb_id, user_id=current_user.id).first_or_404()
    q = request.form.get('query_text', '').strip()
    if q:
        count = NotebookEntry.query.filter_by(notebook_id=nb.id).count()
        entry = NotebookEntry(
            notebook_id=nb.id,
            query_text=q,
            result_summary=request.form.get('result_summary', '').strip(),
            notes=request.form.get('notes', '').strip(),
            sort_order=count)
        db.session.add(entry)
        nb.updated_at = datetime.utcnow()
        db.session.commit()
        flash('Entry added to notebook.', 'success')
    return redirect(url_for('notebook_detail', nb_id=nb.id))


@app.route('/notebook/<int:nb_id>/delete', methods=['POST'])
@login_required
def notebook_delete(nb_id):
    nb = Notebook.query.filter_by(id=nb_id, user_id=current_user.id).first_or_404()
    db.session.delete(nb)
    db.session.commit()
    flash('Notebook deleted.', 'info')
    return redirect(url_for('notebooks'))


@app.route('/notebook/<int:nb_id>/rename', methods=['GET', 'POST'])
@login_required
def notebook_rename(nb_id):
    nb = Notebook.query.filter_by(id=nb_id, user_id=current_user.id).first_or_404()
    if request.method == 'POST':
        new_title = request.form.get('title', '').strip()
        new_desc  = request.form.get('description', nb.description).strip()
        is_public = request.form.get('is_public') == 'on'
        if not new_title:
            flash('Notebook title is required.', 'danger')
            return render_template('notebook_rename.html', notebook=nb)
        old_title = nb.title
        nb.title = new_title
        nb.description = new_desc
        nb.is_public = is_public
        nb.updated_at = datetime.utcnow()
        db.session.commit()
        flash(f'Notebook renamed from "{old_title}" to "{new_title}".', 'success')
        return redirect(url_for('notebook_detail', nb_id=nb.id))
    return render_template('notebook_rename.html', notebook=nb)


@app.route('/notebook/entry/<int:entry_id>/delete', methods=['POST'])
@login_required
def notebook_entry_delete(entry_id):
    entry = NotebookEntry.query.get_or_404(entry_id)
    nb = Notebook.query.filter_by(id=entry.notebook_id, user_id=current_user.id).first_or_404()
    nb_id = nb.id
    db.session.delete(entry)
    db.session.commit()
    flash('Entry removed.', 'info')
    return redirect(url_for('notebook_detail', nb_id=nb_id))


# ---------------------------------------------------------------------------
# Saved Queries (Cart equivalent)
# ---------------------------------------------------------------------------

@app.route('/saved-queries')
@login_required
def saved_queries():
    queries = SavedQuery.query.filter_by(user_id=current_user.id)\
                  .order_by(SavedQuery.created_at.desc()).all()
    return render_template('saved_queries.html', saved_queries=queries)


@app.route('/saved-queries/remove/<int:sq_id>', methods=['POST'])
@login_required
def remove_saved_query(sq_id):
    sq = SavedQuery.query.filter_by(id=sq_id, user_id=current_user.id).first_or_404()
    db.session.delete(sq)
    db.session.commit()
    flash('Removed from saved queries.', 'info')
    return redirect(url_for('saved_queries'))


@app.route('/saved-queries/add', methods=['POST'])
@login_required
def saved_queries_add():
    """Form-POST: save a query (also handles application/json for legacy JS)."""
    if request.is_json:
        data = request.get_json(force=True) or {}
        q = (data.get('query_text') or '').strip()
        topic_id = data.get('topic_id')
        notes = data.get('notes', '')
    else:
        q = request.form.get('query_text', '').strip()
        topic_id = request.form.get('topic_id', type=int)
        notes = request.form.get('notes', '')
    if not q:
        if request.is_json:
            return jsonify(success=False, message='Query text required'), 400
        flash('Query text is required.', 'danger')
        return redirect(request.referrer or url_for('saved_queries'))
    sq = SavedQuery(user_id=current_user.id, query_text=q,
                    topic_id=topic_id, notes=notes)
    db.session.add(sq)
    db.session.commit()
    if request.is_json:
        return jsonify(success=True, message='Query saved.',
                       count=SavedQuery.query.filter_by(user_id=current_user.id).count())
    flash('Query saved.', 'success')
    next_url = request.form.get('next') or url_for('saved_queries')
    return redirect(next_url)


# ---------------------------------------------------------------------------
# History
# ---------------------------------------------------------------------------

@app.route('/history')
@login_required
def history():
    hist = QueryHistory.query.filter_by(user_id=current_user.id)\
               .order_by(QueryHistory.created_at.desc()).limit(100).all()
    return render_template('history.html', history=hist)


@app.route('/history/clear', methods=['POST'])
@login_required
def history_clear():
    QueryHistory.query.filter_by(user_id=current_user.id).delete()
    db.session.commit()
    flash('History cleared.', 'info')
    return redirect(url_for('history'))


# ---------------------------------------------------------------------------
# Topic feedback (Review equivalent)
# ---------------------------------------------------------------------------

@app.route('/topic/<slug>/feedback', methods=['POST'])
@login_required
def submit_feedback(slug):
    topic = Topic.query.filter_by(slug=slug).first_or_404()
    rating  = int(request.form.get('rating', 5))
    comment = request.form.get('comment', '').strip()
    existing = TopicFeedback.query.filter_by(user_id=current_user.id,
                                             topic_id=topic.id).first()
    if existing:
        existing.rating = rating
        existing.comment = comment
        flash('Feedback updated.', 'success')
    else:
        fb = TopicFeedback(user_id=current_user.id, topic_id=topic.id,
                           rating=rating, comment=comment)
        db.session.add(fb)
        flash('Feedback submitted. Thank you!', 'success')
    db.session.commit()
    return redirect(url_for('topic_detail', slug=slug))


@app.route('/feedback/<int:fb_id>/delete', methods=['POST'])
@login_required
def delete_feedback(fb_id):
    fb = TopicFeedback.query.filter_by(id=fb_id, user_id=current_user.id).first_or_404()
    slug = fb.topic.slug
    db.session.delete(fb)
    db.session.commit()
    flash('Feedback deleted.', 'info')
    return redirect(url_for('topic_detail', slug=slug))


# ---------------------------------------------------------------------------
# JSON APIs
# ---------------------------------------------------------------------------

@app.route('/api/favorites/toggle', methods=['POST'])
@csrf.exempt
@login_required
def api_favorites_toggle():
    data     = request.get_json(force=True) or {}
    topic_id = data.get('topic_id')
    topic    = db.session.get(Topic, topic_id)
    if not topic:
        return jsonify(success=False, message='Topic not found'), 404
    existing = Favorite.query.filter_by(user_id=current_user.id,
                                        topic_id=topic_id).first()
    if existing:
        db.session.delete(existing)
        db.session.commit()
        return jsonify(success=True, action='removed',
                       fav_count=Favorite.query.filter_by(user_id=current_user.id).count())
    else:
        db.session.add(Favorite(user_id=current_user.id, topic_id=topic_id))
        db.session.commit()
        return jsonify(success=True, action='added',
                       fav_count=Favorite.query.filter_by(user_id=current_user.id).count())


@app.route('/api/saved-queries/add', methods=['POST'])
@csrf.exempt
@login_required
def api_save_query():
    data = request.get_json(force=True) or {}
    q    = (data.get('query_text') or '').strip()
    if not q:
        return jsonify(success=False, message='Query text required'), 400
    sq = SavedQuery(user_id=current_user.id, query_text=q,
                    topic_id=data.get('topic_id'),
                    notes=data.get('notes', ''))
    db.session.add(sq)
    db.session.commit()
    return jsonify(success=True, message='Query saved.',
                   count=SavedQuery.query.filter_by(user_id=current_user.id).count())


@app.route('/api/history/add', methods=['POST'])
@csrf.exempt
@login_required
def api_history_add():
    data = request.get_json(force=True) or {}
    q    = (data.get('query_text') or '').strip()
    if q:
        db.session.add(QueryHistory(user_id=current_user.id, query_text=q,
                                    topic_id=data.get('topic_id')))
        db.session.commit()
    return jsonify(success=True)


@app.route('/api/topics')
def api_topics():
    cat_slug = request.args.get('category')
    q_filter = Topic.query
    if cat_slug:
        cat = Category.query.filter_by(slug=cat_slug).first()
        if cat: q_filter = q_filter.filter_by(category_id=cat.id)
    topics = q_filter.all()
    return jsonify([{
        'id': t.id, 'name': t.name, 'slug': t.slug,
        'description': t.description, 'image': t.image,
        'is_featured': t.is_featured, 'view_count': t.view_count,
    } for t in topics])


@app.route('/api/autocomplete')
def api_autocomplete():
    q = request.args.get('q', '').strip()
    if len(q) < 2:
        return jsonify([])
    topics = Topic.query.filter(Topic.name.ilike(f'%{q}%')).limit(8).all()
    examples_matches = []
    for topic in Topic.query.all():
        for ex in topic.get_examples():
            if q.lower() in ex['query'].lower():
                examples_matches.append(ex['query'])
                if len(examples_matches) >= 5:
                    break
        if len(examples_matches) >= 5:
            break
    results = [t.name for t in topics] + examples_matches
    return jsonify(results[:10])


# ---------------------------------------------------------------------------
# Error handlers
# ---------------------------------------------------------------------------

@app.errorhandler(404)
def not_found(e):
    return render_template('404.html'), 404


@app.errorhandler(500)
def server_error(e):
    return render_template('500.html'), 500


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        seed_database()
        seed_benchmark_users()
    port = int(os.environ.get('PORT', 28853))
    app.run(host='0.0.0.0', port=port, debug=False)
