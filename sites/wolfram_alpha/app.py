#!/usr/bin/env python3
"""Wolfram Alpha mirror — Flask + SQLAlchemy + full CRUD"""
import os, json, re, secrets, hashlib
from datetime import datetime, timedelta
from pathlib import Path
from functools import wraps

from flask import (Flask, render_template, request, redirect, url_for,
                   flash, session, jsonify, abort, g, make_response,
                   Response)
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
# R6: edge-case routes
# ---------------------------------------------------------------------------

@app.route('/input/ambiguous')
def input_ambiguous():
    """Edge case: input-ambiguous-pick-assumption.

    Shows a side-by-side interpretation picker for queries that have multiple
    valid interpretations (mercury, python, java, pi, e, factor 12, …).
    """
    q = request.args.get('i', '').strip()
    if not q:
        return redirect(url_for('index'))
    # Find an ambiguous-slug computation result first (R6 added these).
    comp = ComputationResult.query.filter_by(
        topic_slug='edge-ambiguous-input').filter(
        ComputationResult.input_query.ilike(f'{q}%')).first()
    if not comp:
        comp = ComputationResult.query.filter(
            ComputationResult.input_query.ilike(f'{q}%')).first()
    interpretations = []
    if comp:
        for pod in comp.get_pods():
            if pod.get('title') == 'Pick an interpretation':
                for line in (pod.get('plaintext') or '').splitlines():
                    line = line.strip()
                    if line.startswith('[') and ']' in line:
                        lbl, _, desc = line.partition(']')
                        interpretations.append((lbl.lstrip('[').strip(), desc.strip()))
                break
    return render_template('edge_ambiguous.html', query=q, comp=comp,
                           interpretations=interpretations)


@app.route('/computation/<int:cr_id>/timeout')
def computation_timeout(cr_id):
    """Edge case: computation-timeout-fallback page."""
    comp = db.session.get(ComputationResult, cr_id)
    if not comp:
        abort(404)
    return render_template('edge_timeout.html', comp=comp,
                           pro_url=url_for('pro_upgrade'))


@app.route('/step-by-step/<int:cr_id>/locked')
def step_by_step_locked(cr_id):
    """Edge case: pro-required-step-by-step-paywall page."""
    comp = db.session.get(ComputationResult, cr_id)
    if not comp:
        abort(404)
    # show first 2 steps as preview only
    pods = comp.get_pods() if comp else []
    preview_steps = [p for p in pods if str(p.get('title', '')).lower().startswith('step')][:2]
    return render_template('edge_step_locked.html', comp=comp,
                           preview_steps=preview_steps,
                           pro_url=url_for('pro_upgrade'))


@app.route('/notebook/<int:nb_id>/quota')
@login_required
def notebook_quota(nb_id):
    """Edge case: notebook-quota-exceeded page (free plan limit reached)."""
    nb = Notebook.query.filter_by(id=nb_id, user_id=current_user.id).first_or_404()
    entry_count = NotebookEntry.query.filter_by(notebook_id=nb.id).count()
    # Free plan limit: 50 entries; Pro: unlimited
    free_limit = 50
    is_pro = getattr(current_user, 'is_pro', False)
    return render_template('edge_notebook_quota.html', nb=nb,
                           entry_count=entry_count, free_limit=free_limit,
                           is_pro=is_pro, pro_url=url_for('pro_upgrade'))


@app.route('/share/<token>/expired')
def share_expired(token):
    """Edge case: share-link-expired page (link past 90-day TTL)."""
    # Token is opaque; show a fixed expired-page with help text.
    return render_template('edge_share_expired.html', token=token,
                           ttl_days=90)


@app.route('/widget/<slug>/embed-blocked')
def widget_embed_blocked(slug):
    """Edge case: widget-embed-blocked-by-iframe-policy page."""
    widget = next((w for w in WIDGET_GALLERY if w['slug'] == slug), None)
    if not widget:
        abort(404)
    referer = request.args.get('parent', '(unknown parent)')
    return render_template('edge_widget_blocked.html', widget=widget,
                           referer=referer)


# ---------------------------------------------------------------------------
# R7 surface extensions: SEO, i18n locale switcher, performance,
# accessibility, Wolfram Language export with OpenAPI, takeout, popular cache
# ---------------------------------------------------------------------------

R7_LOCALES = ('en', 'de', 'es', 'jp')
R7_LOCALE_NAME = {'en': 'English', 'de': 'Deutsch',
                  'es': 'Espanol', 'jp': 'Nihongo'}


@app.context_processor
def _inject_r7_locale():
    """Make the active locale + the four supported locales visible to
    every template (used by base.html's header switcher and JSON-LD
    hreflang block)."""
    active = request.cookies.get('locale', 'en') if request else 'en'
    if active not in R7_LOCALES:
        active = 'en'
    return {
        'r7_locale': active,
        'r7_locales': R7_LOCALES,
        'r7_locale_names': R7_LOCALE_NAME,
    }


@app.route('/locale/<lang>')
def locale_switch(lang):
    """R7: switch the locale cookie and redirect back."""
    if lang not in R7_LOCALES:
        abort(404)
    nxt = request.args.get('next') or request.referrer or url_for('index')
    resp = make_response(redirect(nxt))
    resp.set_cookie('locale', lang, max_age=60 * 60 * 24 * 365,
                    samesite='Lax')
    return resp


@app.route('/sitemap.xml')
def sitemap_index():
    """R7: top-level sitemap index referencing per-category sitemaps."""
    cats = Category.query.order_by(Category.sort_order).all()
    parts = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for c in cats:
        parts.append('<sitemap>')
        parts.append(f'<loc>{request.url_root.rstrip("/")}/sitemap/{c.slug}.xml</loc>')
        parts.append('<lastmod>2026-05-26</lastmod>')
        parts.append('</sitemap>')
    parts.append('</sitemapindex>')
    return Response('\n'.join(parts), mimetype='application/xml')


@app.route('/sitemap/<cat_slug>.xml')
def sitemap_category(cat_slug):
    """R7: per-category sitemap covering topic pages in that category."""
    cat = Category.query.filter_by(slug=cat_slug).first_or_404()
    topics = Topic.query.filter_by(category_id=cat.id).order_by(Topic.id).all()
    root = request.url_root.rstrip('/')
    parts = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
             'xmlns:xhtml="http://www.w3.org/1999/xhtml">']
    for t in topics:
        parts.append('<url>')
        parts.append(f'<loc>{root}/topic/{t.slug}</loc>')
        parts.append('<lastmod>2026-05-26</lastmod>')
        parts.append('<changefreq>weekly</changefreq>')
        for loc in R7_LOCALES:
            parts.append(f'<xhtml:link rel="alternate" hreflang="{loc}" '
                         f'href="{root}/topic/{t.slug}?locale={loc}"/>')
        parts.append('</url>')
    parts.append('</urlset>')
    return Response('\n'.join(parts), mimetype='application/xml')


@app.route('/og/<int:cr_id>.svg')
def og_card_svg(cr_id):
    """R7: OG share card rendered as 1200x630 SVG with the parsed input
    and the first line of the plaintext result."""
    comp = db.session.get(ComputationResult, cr_id)
    if not comp:
        abort(404)
    title = (comp.parsed_input or comp.input_query or 'Computation')[:80]
    body_line = (comp.plaintext or '').splitlines()[0] if comp.plaintext else ''
    body_line = body_line[:140]
    safe = lambda s: (s.replace('&', '&amp;').replace('<', '&lt;')
                       .replace('>', '&gt;').replace('"', '&quot;'))
    svg = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 630" '
        'width="1200" height="630" role="img" aria-label="WolframAlpha share card">'
        '<rect width="1200" height="630" fill="#f96302"/>'
        '<rect x="60" y="60" width="1080" height="510" rx="20" fill="#ffffff"/>'
        f'<text x="100" y="160" font-family="Source Sans Pro, sans-serif" '
        f'font-size="48" font-weight="700" fill="#222">WolframAlpha</text>'
        f'<text x="100" y="280" font-family="Source Sans Pro, sans-serif" '
        f'font-size="56" font-weight="600" fill="#111">{safe(title)}</text>'
        f'<text x="100" y="380" font-family="Source Sans Pro, sans-serif" '
        f'font-size="36" fill="#444">{safe(body_line)}</text>'
        f'<text x="100" y="540" font-family="Source Sans Pro, sans-serif" '
        f'font-size="24" fill="#888">[{comp.category}/{comp.subcategory}] '
        f'-- cr#{comp.id}</text>'
        '</svg>'
    )
    return Response(svg, mimetype='image/svg+xml')


@app.route('/computation/<int:cr_id>/wolfram.txt')
def computation_wolfram(cr_id):
    """R7: Wolfram Language code export as plain text."""
    comp = db.session.get(ComputationResult, cr_id)
    if not comp:
        abort(404)
    wl_src = None
    for pod in comp.get_pods():
        title = str(pod.get('title', '')).lower()
        if 'wolfram language' in title:
            wl_src = pod.get('plaintext')
            break
    if not wl_src:
        wl_src = (f"(* Wolfram Language stub for cr#{comp.id} *)\n"
                  f"ToExpression[\"{comp.parsed_input or comp.input_query}\"]\n")
    return Response(wl_src, mimetype='text/plain; charset=utf-8')


@app.route('/computation/<int:cr_id>/openapi.json')
def computation_openapi(cr_id):
    """R7: OpenAPI 3.1 document describing the WL solve endpoint that
    would produce this computation's result."""
    comp = db.session.get(ComputationResult, cr_id)
    if not comp:
        abort(404)
    expr = comp.parsed_input or comp.input_query
    spec = {
        "openapi": "3.1.0",
        "info": {
            "title": "WolframAlpha Solve API",
            "version": "1.0.0",
            "description": (f"Auto-generated OpenAPI spec for computation "
                            f"cr#{comp.id} ({comp.category}/{comp.subcategory})."),
        },
        "servers": [{"url": request.url_root.rstrip('/')}],
        "paths": {
            "/v1/solve": {
                "post": {
                    "summary": "Solve a Wolfram Language expression",
                    "operationId": "solveExpression",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "expression": {
                                            "type": "string",
                                            "example": expr,
                                        },
                                    },
                                    "required": ["expression"],
                                }
                            }
                        }
                    },
                    "responses": {
                        "200": {
                            "description": "Solved",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "plaintext": {"type": "string"},
                                            "parsed": {"type": "string"},
                                            "category": {"type": "string"},
                                            "subcategory": {"type": "string"},
                                        },
                                    },
                                    "example": {
                                        "plaintext": (comp.plaintext or '')[:200],
                                        "parsed": expr,
                                        "category": comp.category,
                                        "subcategory": comp.subcategory,
                                    },
                                }
                            }
                        }
                    },
                }
            }
        },
    }
    return jsonify(spec)


@app.route('/account/takeout')
@login_required
def account_takeout():
    """R7: GDPR-style data takeout -- exports the current user's saved
    queries, history, and notebook entries as a JSON archive."""
    fmt = request.args.get('format', 'json')
    saved = SavedQuery.query.filter_by(user_id=current_user.id).all()
    history = (QueryHistory.query
               .filter_by(user_id=current_user.id)
               .order_by(QueryHistory.created_at.desc()).all())
    notebooks = Notebook.query.filter_by(user_id=current_user.id).all()
    nb_entries = []
    for nb in notebooks:
        ents = (NotebookEntry.query.filter_by(notebook_id=nb.id)
                .order_by(NotebookEntry.sort_order).all())
        for e in ents:
            nb_entries.append({
                'notebook_id': nb.id, 'notebook_title': nb.title,
                'query_text': e.query_text, 'notes': e.notes,
                'result_summary': e.result_summary,
                'created_at': str(e.created_at),
            })
    archive = {
        'schema': 'wolfram-takeout-v1',
        'generated_at': '2026-05-26T12:00:00',
        'user': {
            'id': current_user.id,
            'email': current_user.email,
            'username': current_user.username,
            'created_at': str(current_user.created_at),
        },
        'saved_queries': [
            {'id': s.id, 'query_text': s.query_text, 'notes': s.notes,
             'topic_id': s.topic_id, 'created_at': str(s.created_at)}
            for s in saved
        ],
        'history': [
            {'id': h.id, 'query_text': h.query_text,
             'topic_id': h.topic_id, 'created_at': str(h.created_at)}
            for h in history
        ],
        'notebooks': [
            {'id': n.id, 'title': n.title, 'description': n.description,
             'is_public': n.is_public, 'created_at': str(n.created_at)}
            for n in notebooks
        ],
        'notebook_entries': nb_entries,
    }
    if fmt == 'json':
        resp = jsonify(archive)
        resp.headers['Content-Disposition'] = (
            'attachment; filename=wolfram-takeout.json')
        return resp
    return Response(json.dumps(archive, indent=2),
                    mimetype='application/json')


# In-process cache for the popular-queries endpoint. Deterministic content
# is recomputed lazily once per process; later requests serve from the
# cache to keep LCP low for the homepage.
_R7_POPULAR_CACHE = {'data': None}


@app.route('/api/cached/popular')
def api_cached_popular():
    """R7: cached popular queries (used by homepage to keep LCP low)."""
    limit = request.args.get('limit', '20')
    try:
        limit = max(1, min(100, int(limit)))
    except ValueError:
        limit = 20
    if _R7_POPULAR_CACHE['data'] is None:
        rows = (ComputationResult.query
                .order_by(ComputationResult.id.asc())
                .limit(200).all())
        _R7_POPULAR_CACHE['data'] = [
            {'id': r.id, 'input_query': r.input_query,
             'category': r.category, 'subcategory': r.subcategory}
            for r in rows
        ]
    data = _R7_POPULAR_CACHE['data'][:limit]
    resp = jsonify({'cached': True, 'count': len(data),
                    'items': data, 'snapshot': '2026-05-26'})
    resp.headers['Cache-Control'] = 'public, max-age=300'
    return resp


# ---------------------------------------------------------------------------
# R8 surface extensions: keyboard-driven UX, command palette, math glossary,
# GraphQL v3 endpoint, share webhook, advanced widget builder, observability.
# All endpoints are deterministic and process-local; the telemetry ring
# buffer is initialised from a pinned snapshot, then appended in-process.
# ---------------------------------------------------------------------------

R8_VERSION = 'r8'
R8_BUILD_DATE = '2026-05-26'

# ---- (a) Telemetry ring buffer ------------------------------------------
# Capped at 200 events. Initialised lazily with deterministic seed events
# so /api/events returns something useful on a cold container. Subsequent
# POSTs to /webhook/result-shared and palette/computation views append more.
_R8_EVENT_RING = []
_R8_EVENT_CAP = 200


def _r8_seed_events():
    """Deterministic seed -- ensures /api/events is non-empty on fresh start."""
    if _R8_EVENT_RING:
        return
    seeds = [
        {"event": "computation.rendered", "topic": "command-palette",
         "duration_ms": 142, "schema": "wa-telemetry-v1",
         "ts": "2026-05-26T12:00:00"},
        {"event": "palette.opened", "topic": "command-palette",
         "duration_ms": 12, "schema": "wa-telemetry-v1",
         "ts": "2026-05-26T12:00:01"},
        {"event": "shortcut.cmdEnter", "topic": "keyboard-shortcut-cmd-enter-compute",
         "duration_ms": 4, "schema": "wa-telemetry-v1",
         "ts": "2026-05-26T12:00:02"},
        {"event": "glossary.hovered", "topic": "contextual-help-math-symbol-glossary",
         "duration_ms": 21, "schema": "wa-telemetry-v1",
         "ts": "2026-05-26T12:00:03"},
        {"event": "graphql.queried", "topic": "api-v3-graphql",
         "duration_ms": 88, "schema": "wa-telemetry-v1",
         "ts": "2026-05-26T12:00:04"},
        {"event": "webhook.received", "topic": "webhook-result-shared",
         "duration_ms": 6, "schema": "wa-telemetry-v1",
         "ts": "2026-05-26T12:00:05"},
    ]
    _R8_EVENT_RING.extend(seeds)


def _r8_emit(event, topic, **extra):
    _r8_seed_events()
    rec = {"event": event, "topic": topic, "schema": "wa-telemetry-v1",
           "ts": "2026-05-26T12:00:00"}
    rec.update(extra)
    _R8_EVENT_RING.append(rec)
    # cap
    if len(_R8_EVENT_RING) > _R8_EVENT_CAP:
        del _R8_EVENT_RING[: len(_R8_EVENT_RING) - _R8_EVENT_CAP]


# ---- (b) Observability probes -------------------------------------------
@app.route('/healthz')
def r8_healthz():
    """Liveness probe -- deterministic, no DB hit on hot path."""
    return jsonify({"status": "ok", "build": R8_VERSION,
                    "snapshot": R8_BUILD_DATE})


@app.route('/api/uptime')
def r8_uptime():
    """Returns a pinned uptime snapshot + the build version."""
    return jsonify({"uptime_s": 3600, "version": R8_VERSION,
                    "build_date": R8_BUILD_DATE, "schema": "wa-uptime-v1"})


@app.route('/api/events')
def r8_events():
    """Ring buffer of recent telemetry events (last <=200)."""
    _r8_seed_events()
    limit = request.args.get('limit', '50')
    try:
        limit = max(1, min(_R8_EVENT_CAP, int(limit)))
    except ValueError:
        limit = 50
    evt_filter = request.args.get('event')
    items = _R8_EVENT_RING[-limit:]
    if evt_filter:
        items = [e for e in items if e.get('event') == evt_filter]
    return jsonify({"events": items, "count": len(items),
                    "schema": "wa-events-v1", "version": R8_VERSION})


# ---- (c) GraphQL v3 endpoint --------------------------------------------
R8_GRAPHQL_SDL = (
    "type Computation { id: ID! parsed: String plaintext: String "
    "category: String subcategory: String keywords: String "
    "pods: [Pod!]! schemaVersion: String! }\n"
    "type Pod { title: String! plaintext: String }\n"
    "type Query { computation(expression: String!): Computation }\n"
    "schema { query: Query }\n"
)


@app.route('/api/v3-graphql', methods=['GET', 'POST'])
@csrf.exempt
def r8_graphql():
    """Tiny GraphQL-style endpoint. GET returns the SDL; POST accepts a
    JSON body with `expression` (or a `query` containing a single
    computation(expression:"...") call) and returns the matching record."""
    if request.method == 'GET':
        return Response(R8_GRAPHQL_SDL, mimetype='text/plain; charset=utf-8')
    payload = request.get_json(silent=True) or {}
    expr = payload.get('expression') or ''
    if not expr:
        q = payload.get('query', '')
        m = re.search(r'computation\s*\(\s*expression\s*:\s*"([^"]*)"', q)
        if m:
            expr = m.group(1)
    if not expr:
        return jsonify({"errors": [{"message": "missing expression"}]}), 400
    comp = _find_best_computation(expr)
    if not comp:
        return jsonify({"data": {"computation": None},
                        "schemaVersion": "wa-graphql-v3"})
    pods = [{"title": p.get("title", ""),
             "plaintext": p.get("plaintext", "")} for p in comp.get_pods()]
    _r8_emit('graphql.queried', comp.topic_slug or 'api-v3-graphql',
             cr_id=comp.id)
    return jsonify({
        "data": {
            "computation": {
                "id": comp.id,
                "parsed": comp.parsed_input,
                "plaintext": comp.plaintext,
                "category": comp.category,
                "subcategory": comp.subcategory,
                "keywords": comp.keywords,
                "pods": pods,
                "schemaVersion": "wa-graphql-v3",
            }
        },
        "schemaVersion": "wa-graphql-v3",
    })


# ---- (d) Share-event webhook --------------------------------------------
@app.route('/webhook/result-shared', methods=['POST'])
@csrf.exempt
def r8_webhook_result_shared():
    """Records a share event. Payload schema: {cr_id, channel, topic?}.
    The event is appended to the telemetry ring buffer so it shows up in
    /api/events without any further configuration."""
    payload = request.get_json(silent=True) or {}
    cr_id = payload.get('cr_id')
    channel = payload.get('channel') or 'unknown'
    topic = payload.get('topic') or ''
    if not topic and cr_id is not None:
        try:
            comp = db.session.get(ComputationResult, int(cr_id))
            if comp:
                topic = comp.topic_slug or ''
        except (TypeError, ValueError):
            pass
    _r8_emit('webhook.received', topic or 'webhook-result-shared',
             channel=channel, cr_id=cr_id)
    return jsonify({"ok": True, "schema": "wa-webhook-v1",
                    "event": "result.shared",
                    "topic": topic, "channel": channel,
                    "version": R8_VERSION})


# ---- (e) Command palette catalog ----------------------------------------
@app.route('/api/command-palette')
def r8_command_palette():
    """JSON catalog of items exposed in the Cmd+K command palette. Items
    cover topics, R8 surface routes, and a small selection of computations.
    Supports ?q= for case-insensitive substring filtering."""
    q = (request.args.get('q') or '').strip().lower()
    items = []
    # Static R8 routes
    static_routes = [
        ('Open math symbol glossary', '/help/symbols', 'help'),
        ('Account takeout (JSON)', '/account/takeout', 'export'),
        ('Cached popular queries', '/api/cached/popular', 'api'),
        ('GraphQL v3 SDL', '/api/v3-graphql', 'api'),
        ('Healthz probe', '/healthz', 'observability'),
        ('Uptime', '/api/uptime', 'observability'),
        ('Telemetry events', '/api/events', 'observability'),
        ('Advanced widget builder', '/developer/widget-builder-advanced', 'developer'),
        ('Switch locale: English', '/locale/en', 'locale'),
        ('Switch locale: Deutsch', '/locale/de', 'locale'),
        ('Switch locale: Espanol', '/locale/es', 'locale'),
        ('Switch locale: Nihongo', '/locale/jp', 'locale'),
    ]
    for label, url, kind in static_routes:
        items.append({"label": label, "url": url, "kind": kind,
                      "shortcut": "Cmd+K"})
    # Featured topics (deterministic order)
    topics = (Topic.query.filter_by(is_featured=True)
              .order_by(Topic.id).limit(40).all())
    for t in topics:
        items.append({"label": t.name, "url": f"/topic/{t.slug}",
                      "kind": "topic", "shortcut": "Cmd+K"})
    # First few computations, byte-stable order
    sample = (ComputationResult.query.order_by(ComputationResult.id)
              .limit(40).all())
    for c in sample:
        items.append({"label": (c.parsed_input or c.input_query)[:80],
                      "url": f"/input?i={(c.parsed_input or c.input_query)}",
                      "kind": "computation", "shortcut": "Cmd+Enter"})
    if q:
        items = [it for it in items
                 if q in it['label'].lower() or q in it['url'].lower()]
    _r8_emit('palette.opened', 'command-palette',
             query=q, returned=len(items))
    return jsonify({"items": items, "count": len(items),
                    "schema": "wa-palette-v1", "version": R8_VERSION})


# ---- (f) Math symbol glossary page --------------------------------------
@app.route('/help/symbols')
def r8_help_symbols():
    """Math symbol glossary. Documents every glyph that gets a hover
    tooltip in the result UI."""
    glossary = [
        ('+', 'plus', 'binary addition operator'),
        ('-', 'minus', 'binary subtraction or unary negation'),
        ('*', 'times', 'binary multiplication operator'),
        ('/', 'divide', 'binary division operator'),
        ('^', 'caret', 'exponentiation operator (a^b = a to the power b)'),
        ('=', 'equals', 'equality predicate'),
        ('!', 'factorial', 'factorial when postfix; logical-not when prefix'),
        ('pi', 'pi', 'the constant pi (~3.14159265...)'),
        ('e', 'euler-e', 'Euler number (~2.71828...)'),
        ('sqrt', 'sqrt', 'principal square root'),
        ('sin', 'sin', 'circular sine function'),
        ('cos', 'cos', 'circular cosine function'),
        ('tan', 'tan', 'circular tangent function'),
        ('log', 'log', 'natural log (base e) unless a base is given'),
        ('ln', 'ln', 'natural log (alias for log base e)'),
        ('integral', 'integral', 'definite/indefinite integral operator'),
        ('derivative', 'derivative', 'derivative operator (d/dx)'),
        ('nabla', 'nabla', 'vector differential operator (gradient)'),
        ('partial', 'partial', 'partial derivative operator'),
        ('sum', 'sigma', 'finite or infinite summation'),
        ('product', 'capital-pi', 'finite or infinite product'),
        ('matrix', 'matrix', 'rectangular array of numbers/expressions'),
        ('limit', 'lim', 'limit operator'),
    ]
    _r8_emit('glossary.shown', 'contextual-help-math-symbol-glossary',
             count=len(glossary))
    return render_template('help_symbols.html', glossary=glossary)


# ---- (g) Advanced widget builder page -----------------------------------
@app.route('/developer/widget-builder-advanced')
def r8_widget_builder_advanced():
    """Developer-grade widget builder. Options: theme, locale, kind,
    telemetry, expr -- all rendered into a preview iframe URL."""
    theme = request.args.get('theme', 'light')
    locale = request.args.get('locale', 'en')
    kind = request.args.get('kind', 'inline')
    telemetry = request.args.get('telemetry', 'off')
    expr = request.args.get('expr', 'derivative of x^2')
    if theme not in {'light', 'dark', 'sepia', 'high-contrast'}:
        theme = 'light'
    if locale not in R7_LOCALES:
        locale = 'en'
    if kind not in {'inline', 'card', 'fullscreen'}:
        kind = 'inline'
    if telemetry not in {'on', 'off', 'sampled'}:
        telemetry = 'off'
    preview_url = (f"/input?i={expr.replace(' ', '+')}"
                   f"&theme={theme}&locale={locale}"
                   f"&kind={kind}&telemetry={telemetry}")
    embed_snippet = (
        f'<iframe src="{preview_url}" data-theme="{theme}" '
        f'data-locale="{locale}" data-kind="{kind}" '
        f'data-telemetry="{telemetry}" width="600" height="400" '
        f'loading="lazy"></iframe>'
    )
    _r8_emit('widget.embed', 'developer-widget-builder-advanced',
             theme=theme, locale=locale, kind=kind, telemetry=telemetry)
    return render_template('developer_widget_builder_advanced.html',
                           theme=theme, locale=locale, kind=kind,
                           telemetry=telemetry, expr=expr,
                           preview_url=preview_url,
                           embed_snippet=embed_snippet,
                           themes=['light', 'dark', 'sepia', 'high-contrast'],
                           locales=R7_LOCALES,
                           kinds=['inline', 'card', 'fullscreen'],
                           telems=['on', 'off', 'sampled'])


# ===========================================================================
# R9 surface: nutrition / drugs / sports / aviation / weather radar /
# earthquakes / tide. Each route reuses the R8 telemetry ring buffer.
# ===========================================================================
R9_VERSION = 'r9'
R9_BUILD_DATE = '2026-05-27'

# ---- R9 nutrition reference tables (kept in code, deterministic) ---------
_R9_DIETS = ('omnivore', 'vegetarian', 'vegan', 'keto', 'paleo')
_R9_PROTEIN_RATIO = {'omnivore': 0.30, 'vegetarian': 0.25, 'vegan': 0.22,
                     'keto': 0.30, 'paleo': 0.35}
_R9_CARB_RATIO    = {'omnivore': 0.45, 'vegetarian': 0.50, 'vegan': 0.55,
                     'keto': 0.10, 'paleo': 0.30}
_R9_MEAL_LABELS = ['breakfast', 'lunch', 'dinner', 'snack', 'snack 2',
                   'snack 3', 'late', 'pre-bed']
_R9_DIET_NOTES = {
    'omnivore':    'balanced animal + plant proteins',
    'vegetarian':  'eggs/dairy ok, no meat',
    'vegan':       'plant-only proteins, B12 supplement',
    'keto':        'low-carb (<10%), high-fat, moderate-protein',
    'paleo':       'whole foods, no grains/legumes/refined sugar',
}


@app.route('/nutrition/meal-plan')
def r9_nutrition_meal_plan():
    """Build a deterministic daily meal plan from cal / meals / diet params."""
    try:
        cal = int(request.args.get('cal', '2000'))
    except ValueError:
        cal = 2000
    cal = max(800, min(4000, cal))
    try:
        meals = int(request.args.get('meals', '3'))
    except ValueError:
        meals = 3
    meals = max(1, min(8, meals))
    diet = request.args.get('diet', 'omnivore')
    if diet not in _R9_DIETS:
        diet = 'omnivore'
    per_meal = cal // meals
    p_g = int(cal * _R9_PROTEIN_RATIO[diet] / 4)
    c_g = int(cal * _R9_CARB_RATIO[diet] / 4)
    f_g = int(cal * (1 - _R9_PROTEIN_RATIO[diet] - _R9_CARB_RATIO[diet]) / 9)
    plan = []
    for i in range(meals):
        label = _R9_MEAL_LABELS[i % len(_R9_MEAL_LABELS)]
        kcal = per_meal + (cal - per_meal * meals if i == meals - 1 else 0)
        plan.append({"label": label, "kcal": kcal,
                     "notes": _R9_DIET_NOTES[diet]})
    payload = {"cal": cal, "meals": meals, "diet": diet,
               "per_meal_kcal": per_meal,
               "macros_g": {"protein": p_g, "carbs": c_g, "fat": f_g},
               "plan": plan, "schema": "wa-nutrition-v1",
               "version": R9_VERSION}
    _r8_emit('nutrition.plan.built', 'nutrition-meal-plan-builder',
             cal=cal, meals=meals, diet=diet)
    if request.args.get('format') == 'json':
        return jsonify(payload)
    return render_template('nutrition_meal_plan.html',
                           cal=cal, meals=meals, diet=diet,
                           diets=list(_R9_DIETS),
                           per_meal=per_meal, p_g=p_g, c_g=c_g, f_g=f_g,
                           plan=plan)


# ---- R9 drug reference table --------------------------------------------
_R9_DRUGS = {
    'warfarin':                 ('anticoagulant',           'VKA, inhibits VKORC1'),
    'apixaban':                 ('anticoagulant',           'DOAC, Factor Xa inhibitor'),
    'rivaroxaban':              ('anticoagulant',           'DOAC, Factor Xa inhibitor'),
    'aspirin':                  ('antiplatelet',            'irreversible COX-1 inhibitor'),
    'clopidogrel':              ('antiplatelet',            'P2Y12 inhibitor'),
    'ibuprofen':                ('NSAID',                   'COX-1/2 inhibitor'),
    'naproxen':                 ('NSAID',                   'COX-1/2 inhibitor'),
    'atorvastatin':             ('statin',                  'HMG-CoA reductase inhibitor'),
    'simvastatin':              ('statin',                  'HMG-CoA reductase inhibitor'),
    'metformin':                ('biguanide',               'AMPK activator'),
    'insulin':                  ('hormone',                 'binds insulin receptor'),
    'lisinopril':               ('ACE inhibitor',           'inhibits ACE'),
    'losartan':                 ('ARB',                     'AT1 receptor blocker'),
    'amlodipine':               ('CCB',                     'L-type calcium channel blocker'),
    'hydrochlorothiazide':      ('thiazide diuretic',       'inhibits Na-Cl cotransporter'),
    'furosemide':               ('loop diuretic',           'inhibits Na-K-2Cl loop'),
    'digoxin':                  ('cardiac glycoside',       'inhibits Na-K ATPase'),
    'amiodarone':               ('class III antiarrhythmic','multichannel blocker'),
    'sertraline':               ('SSRI',                    'serotonin reuptake inhibitor'),
    'fluoxetine':               ('SSRI',                    'serotonin reuptake inhibitor'),
    'venlafaxine':              ('SNRI',                    'serotonin + NE reuptake inhibitor'),
    'tramadol':                 ('opioid',                  'mu agonist + SNRI'),
    'sildenafil':               ('PDE5 inhibitor',          'phosphodiesterase-5 inhibitor'),
    'isosorbide-mononitrate':   ('nitrate',                 'NO donor, vasodilator'),
    'omeprazole':               ('PPI',                     'H+/K+ ATPase inhibitor'),
}
_R9_DRUG_INTERACTIONS = [
    ('warfarin', 'ibuprofen', 'major',
     'NSAID displaces warfarin from albumin and inhibits platelets; bleeding risk.'),
    ('warfarin', 'aspirin', 'major',
     'Additive bleeding risk via antiplatelet + anticoagulant.'),
    ('warfarin', 'amiodarone', 'major',
     'CYP2C9 inhibition raises warfarin levels; reduce dose 30-50%.'),
    ('sildenafil', 'isosorbide-mononitrate', 'contraindicated',
     'PDE5 inhibitor + nitrate produces severe hypotension.'),
    ('clopidogrel', 'omeprazole', 'moderate',
     'PPI reduces CYP2C19 activation of clopidogrel.'),
    ('metformin', 'furosemide', 'moderate',
     'Diuretic-induced volume depletion raises lactic acidosis risk.'),
    ('atorvastatin', 'amiodarone', 'moderate',
     'CYP3A4 inhibition raises statin level; myopathy risk.'),
    ('simvastatin', 'amlodipine', 'moderate',
     'CYP3A4 inhibition by amlodipine; cap simvastatin at 20 mg.'),
    ('sertraline', 'tramadol', 'major',
     'Both serotonergic -> serotonin syndrome risk.'),
    ('fluoxetine', 'venlafaxine', 'major',
     'Combined SSRI+SNRI raises serotonin syndrome risk.'),
    ('lisinopril', 'amlodipine', 'minor',
     'Common antihypertensive combo, monitor BP.'),
    ('losartan', 'hydrochlorothiazide', 'minor',
     'Standard ARB+thiazide combo therapy.'),
    ('digoxin', 'amiodarone', 'major',
     'Amiodarone doubles digoxin level via P-gp; reduce digoxin 50%.'),
    ('digoxin', 'furosemide', 'moderate',
     'Hypokalemia from diuresis potentiates digoxin toxicity.'),
    ('aspirin', 'ibuprofen', 'moderate',
     'Ibuprofen blocks aspirin antiplatelet effect.'),
    ('insulin', 'metformin', 'minor',
     'Standard combo therapy in T2DM.'),
    ('apixaban', 'aspirin', 'major',
     'Additive bleeding risk.'),
    ('apixaban', 'amiodarone', 'moderate',
     'P-gp / weak CYP3A4 inhibition raises apixaban level.'),
    ('rivaroxaban', 'naproxen', 'major',
     'NSAID + DOAC -> bleeding risk.'),
    ('clopidogrel', 'aspirin', 'moderate',
     'Dual antiplatelet therapy, intentional indications only.'),
]


def _r9_lookup_interaction(a: str, b: str):
    a = (a or '').strip().lower()
    b = (b or '').strip().lower()
    for da, db_, sev, mech in _R9_DRUG_INTERACTIONS:
        if {a, b} == {da, db_}:
            return sev, mech
    # Deterministic fallback severity
    pair_key = '+'.join(sorted([a, b]))
    bands = ['minor', 'moderate', 'major', 'contraindicated']
    sev = bands[int(hashlib.md5(pair_key.encode()).hexdigest(), 16) % 4]
    mech = (f"No documented direct interaction in the WA-mirror dataset; "
            f"severity inferred as {sev} from pair-hash heuristic.")
    return sev, mech


@app.route('/drugs/interaction-checker')
def r9_drug_interaction_checker():
    """Cross-check two drugs for interaction severity + mechanism."""
    a = (request.args.get('a', 'warfarin') or 'warfarin').strip().lower()
    b = (request.args.get('b', 'ibuprofen') or 'ibuprofen').strip().lower()
    class_a, mech_a = _R9_DRUGS.get(a, ('unknown', 'not in WA-mirror reference'))
    class_b, mech_b = _R9_DRUGS.get(b, ('unknown', 'not in WA-mirror reference'))
    severity, mechanism = _r9_lookup_interaction(a, b)
    payload = {"drug_a": a, "drug_b": b,
               "class_a": class_a, "class_b": class_b,
               "mech_a": mech_a, "mech_b": mech_b,
               "severity": severity, "mechanism": mechanism,
               "schema": "wa-drug-interact-v1", "version": R9_VERSION}
    _r8_emit('drugs.interaction.checked', 'drug-interaction-checker',
             a=a, b=b, severity=severity)
    if request.args.get('format') == 'json':
        return jsonify(payload)
    return render_template('drug_interaction.html',
                           drug_a=a, drug_b=b,
                           class_a=class_a, class_b=class_b,
                           mech_a=mech_a, mech_b=mech_b,
                           severity=severity, mechanism=mechanism)


# ---- R9 sports reference table ------------------------------------------
_R9_SPORTS_TEAMS = {
    'lakers':       ('nba', 'Los Angeles Lakers', 'NBA West', 0),
    'celtics':      ('nba', 'Boston Celtics', 'NBA East', 1),
    'warriors':     ('nba', 'Golden State Warriors', 'NBA West', 2),
    'bucks':        ('nba', 'Milwaukee Bucks', 'NBA East', 3),
    'nuggets':      ('nba', 'Denver Nuggets', 'NBA West', 4),
    'heat':         ('nba', 'Miami Heat', 'NBA East', 5),
    'suns':         ('nba', 'Phoenix Suns', 'NBA West', 6),
    'sixers':       ('nba', 'Philadelphia 76ers', 'NBA East', 7),
    'yankees':      ('mlb', 'New York Yankees', 'AL East', 8),
    'dodgers':      ('mlb', 'Los Angeles Dodgers', 'NL West', 9),
    'redsox':       ('mlb', 'Boston Red Sox', 'AL East', 10),
    'cubs':         ('mlb', 'Chicago Cubs', 'NL Central', 11),
    'astros':       ('mlb', 'Houston Astros', 'AL West', 12),
    'giants':       ('mlb', 'San Francisco Giants', 'NL West', 13),
    'patriots':     ('nfl', 'New England Patriots', 'AFC East', 14),
    'cowboys':      ('nfl', 'Dallas Cowboys', 'NFC East', 15),
    'chiefs':       ('nfl', 'Kansas City Chiefs', 'AFC West', 16),
    'eagles':       ('nfl', 'Philadelphia Eagles', 'NFC East', 17),
    '49ers':        ('nfl', 'San Francisco 49ers', 'NFC West', 18),
    'real-madrid':  ('soccer', 'Real Madrid', 'La Liga', 19),
    'barcelona':    ('soccer', 'FC Barcelona', 'La Liga', 20),
    'man-city':     ('soccer', 'Manchester City', 'Premier League', 21),
    'arsenal':      ('soccer', 'Arsenal FC', 'Premier League', 22),
    'bayern':       ('soccer', 'Bayern Munich', 'Bundesliga', 23),
}


@app.route('/sports/team/<slug>/deepdive')
def r9_sport_deepdive(slug):
    """Deterministic season roll-up for a single franchise."""
    season = request.args.get('season', '2024-25')
    season_idx = {'2023-24': 0, '2024-25': 1, '2025-26': 2}.get(season, 1)
    if slug not in _R9_SPORTS_TEAMS:
        abort(404)
    sport, name, league, i = _R9_SPORTS_TEAMS[slug]
    wins = 30 + ((i * 7 + season_idx * 11) % 25)
    if sport == 'nba':
        losses = max(0, 82 - wins)
    elif sport == 'nfl':
        wins = wins % 17
        losses = max(0, 17 - wins)
    elif sport == 'mlb':
        wins = 60 + ((i * 7 + season_idx * 11) % 40)
        losses = max(0, 162 - wins)
    else:
        wins = wins % 38
        losses = max(0, 38 - wins)
    pt_diff = ((i * 5 + season_idx * 3) % 20) - 8
    top_scorer = f"player-{slug}-{season_idx+1}"
    home_w = wins // 2 + ((i + season_idx) % 3)
    home_l = max(0, losses // 2 - (i % 2))
    road_w = wins - home_w
    road_l = losses - home_l
    vs_div_w = wins // 4
    vs_div_l = losses // 4
    payload = {"sport": sport, "team": slug, "name": name,
               "league": league, "season": season,
               "record": f"{wins}-{losses}",
               "home_record": f"{home_w}-{home_l}",
               "road_record": f"{road_w}-{road_l}",
               "vs_div": f"{vs_div_w}-{vs_div_l}",
               "point_diff": pt_diff, "top_scorer": top_scorer,
               "schema": "wa-sport-deepdive-v1", "version": R9_VERSION}
    _r8_emit('sport.deepdive.viewed', 'sport-team-stat-deepdive',
             team=slug, season=season)
    if request.args.get('format') == 'json':
        return jsonify(payload)
    return render_template('sport_deepdive.html',
                           sport=sport, slug=slug, name=name,
                           league=league, season=season,
                           record=f"{wins}-{losses}",
                           home_record=f"{home_w}-{home_l}",
                           road_record=f"{road_w}-{road_l}",
                           vs_div=f"{vs_div_w}-{vs_div_l}",
                           point_diff=pt_diff, top_scorer=top_scorer)


# ---- R9 aviation reference table ----------------------------------------
_R9_FLIGHTS = {
    'AA100':  ('JFK', 'LHR', 'B772', 'on time',  0,  'B22',  'Boston'),
    'AA101':  ('LHR', 'JFK', 'B772', 'delayed',  45, 'A7',   'New-York'),
    'UA1':    ('EWR', 'SIN', 'B789', 'on time',  0,  'C120', 'Singapore'),
    'UA888':  ('SFO', 'PEK', 'B789', 'delayed',  35, 'G1',   'Shanghai'),
    'DL47':   ('ATL', 'LAX', 'B739', 'boarding', 0,  'T8',   'San-Diego'),
    'DL200':  ('JFK', 'CDG', 'A333', 'on time',  0,  '32',   'London'),
    'BA117':  ('LHR', 'JFK', 'A388', 'on time',  0,  '14',   'New-York'),
    'BA286':  ('LHR', 'SFO', 'B789', 'delayed',  20, '24',   'San-Francisco'),
    'LH400':  ('FRA', 'JFK', 'A388', 'on time',  0,  'B23',  'New-York'),
    'LH716':  ('FRA', 'HND', 'B748', 'departed', 0,  'A18',  'Tokyo'),
    'AF6':    ('CDG', 'JFK', 'B772', 'on time',  0,  'L41',  'New-York'),
    'AF274':  ('CDG', 'PEK', 'B772', 'delayed',  90, 'M28',  'Shanghai'),
    'JL5':    ('HND', 'JFK', 'B789', 'on time',  0,  '147',  'New-York'),
    'JL61':   ('NRT', 'LAX', 'B789', 'delayed',  10, '143',  'San-Diego'),
    'NH7':    ('NRT', 'ORD', 'B772', 'on time',  0,  '110',  'Boston'),
    'CX880':  ('HKG', 'LAX', 'A359', 'on time',  0,  '23',   'San-Diego'),
    'SQ12':   ('NRT', 'LAX', 'B772', 'delayed',  15, '83',   'San-Diego'),
    'SQ22':   ('SIN', 'EWR', 'A359', 'on time',  0,  'A6',   'New-York'),
    'EK205':  ('DXB', 'JFK', 'A388', 'on time',  0,  'B14',  'New-York'),
    'EK413':  ('DXB', 'SYD', 'A388', 'departed', 0,  'A21',  'Sydney'),
    'QF1':    ('SYD', 'LHR', 'A388', 'on time',  0,  '8',    'London'),
    'QF12':   ('SYD', 'LAX', 'A388', 'delayed',  25, '5',    'San-Diego'),
    'KE17':   ('ICN', 'LAX', 'B789', 'on time',  0,  '24',   'San-Diego'),
    'OZ102':  ('ICN', 'JFK', 'A359', 'on time',  0,  '15',   'New-York'),
    'CA981':  ('PEK', 'JFK', 'B748', 'delayed',  40, 'E12',  'New-York'),
    'CA989':  ('PEK', 'LAX', 'B789', 'on time',  0,  'E15',  'San-Diego'),
    'MU587':  ('PVG', 'JFK', 'B772', 'delayed',  30, 'D12',  'New-York'),
    'TK1':    ('IST', 'JFK', 'A359', 'on time',  0,  'F1',   'New-York'),
    'VS3':    ('LHR', 'JFK', 'A339', 'on time',  0,  '6',    'New-York'),
    'NZ1':    ('LHR', 'AKL', 'B789', 'departed', 0,  '12',   'Auckland'),
}


@app.route('/aviation/flight/<flight>')
def r9_aviation_flight(flight):
    """Flight tracker. Accepts IATA designator."""
    f_up = (flight or '').upper()
    if f_up not in _R9_FLIGHTS:
        abort(404)
    org, dst, eq, status, delay, gate, tide_port = _R9_FLIGHTS[f_up]
    # Deterministic scheduled time from flight code hash.
    h = int(hashlib.md5(f_up.encode()).hexdigest(), 16)
    sh = h % 24
    sm = (h // 24) % 60
    scheduled = f"{sh:02d}:{sm:02d}"
    est_h = (sh + delay // 60) % 24
    est_m = (sm + delay % 60) % 60
    estimated = f"{est_h:02d}:{est_m:02d}"
    payload = {"flight": f_up, "origin": org, "destination": dst,
               "equipment": eq, "status": status, "delay_min": delay,
               "gate": gate, "scheduled": scheduled, "estimated": estimated,
               "tide_port": tide_port,
               "schema": "wa-aviation-v1", "version": R9_VERSION}
    _r8_emit('aviation.flight.viewed', 'aviation-flight-tracker',
             flight=f_up, status=status)
    if request.args.get('format') == 'json':
        return jsonify(payload)
    return render_template('aviation_flight.html',
                           flight=f_up, origin=org, destination=dst,
                           equipment=eq, status=status,
                           status_slug=status.replace(' ', '-'),
                           delay_min=delay, gate=gate,
                           scheduled=scheduled, estimated=estimated,
                           tide_port=tide_port)


# ---- R9 radar reference table -------------------------------------------
_R9_RADAR_REGIONS = {
    'northeast-us':     'US Northeast',
    'southeast-us':     'US Southeast',
    'midwest-us':       'US Midwest',
    'gulf-coast':       'US Gulf Coast',
    'southwest-us':     'US Southwest',
    'pacific-northwest':'US Pacific Northwest',
    'california':       'California',
    'rockies':          'US Rockies',
    'appalachian':      'US Appalachian',
    'great-plains':     'US Great Plains',
    'alaska':           'Alaska',
    'hawaii':           'Hawaii',
    'british-isles':    'British Isles',
    'iberian':          'Iberian Peninsula',
    'central-europe':   'Central Europe',
    'scandinavia':      'Scandinavia',
    'mediterranean':    'Mediterranean',
    'balkans':          'Balkans',
    'tokyo-bay':        'Tokyo Bay',
    'osaka-kansai':     'Osaka Kansai',
    'seoul':            'Seoul-Incheon',
    'shanghai-yangtze': 'Shanghai Yangtze Delta',
    'pearl-river':      'Pearl River Delta',
    'southeast-asia':   'Southeast Asia',
    'australia-east':   'Australia East',
}
_R9_RADAR_ALIASES = {
    'nyc': 'northeast-us', 'boston': 'northeast-us',
    'la': 'california', 'sf': 'california',
    'tokyo': 'tokyo-bay', 'osaka': 'osaka-kansai',
    'shanghai': 'shanghai-yangtze', 'hk': 'pearl-river',
    'sydney': 'australia-east', 'london': 'british-isles',
    'madrid': 'iberian', 'rome': 'mediterranean',
    'berlin': 'central-europe', 'stockholm': 'scandinavia',
    'athens': 'balkans', 'seattle': 'pacific-northwest',
    'denver': 'rockies', 'miami': 'gulf-coast',
    'houston': 'gulf-coast', 'singapore': 'southeast-asia',
}
_R9_INTENSITY_BANDS = ('light', 'moderate', 'heavy', 'severe', 'extreme')
_R9_BAND_COLORS = {
    'light':    '#9ddc7e',
    'moderate': '#3aa14a',
    'heavy':    '#f1b53d',
    'severe':   '#e36b1c',
    'extreme':  '#c8232c',
}


@app.route('/weather/radar/<region>')
def r9_weather_radar(region):
    """Tile-style radar image. Returns SVG when ?format=svg."""
    canonical = _R9_RADAR_ALIASES.get(region.lower(), region.lower())
    if canonical not in _R9_RADAR_REGIONS:
        abort(404)
    name = _R9_RADAR_REGIONS[canonical]
    band_param = request.args.get('band', '').lower()
    if band_param in _R9_INTENSITY_BANDS:
        band = band_param
    else:
        h = int(hashlib.md5(canonical.encode()).hexdigest(), 16)
        band = _R9_INTENSITY_BANDS[h % 5]
    h = int(hashlib.md5((canonical + band).encode()).hexdigest(), 16)
    age_min = h % 30
    # Tile SVG: 4x4 cells, each band-coloured per cell hash.
    cells = []
    for y in range(4):
        for x in range(4):
            ch = int(hashlib.md5(f"{canonical}:{band}:{x}:{y}".encode()).hexdigest(), 16)
            color = _R9_BAND_COLORS[_R9_INTENSITY_BANDS[ch % 5]]
            cells.append(
                f'<rect x="{x*40}" y="{y*40}" width="40" height="40" '
                f'fill="{color}" stroke="#222"/>'
            )
    tile_svg = ('<svg xmlns="http://www.w3.org/2000/svg" width="160" '
                'height="160" viewBox="0 0 160 160">'
                + ''.join(cells) + '</svg>')
    _r8_emit('radar.viewed', 'weather-radar-image',
             region=canonical, band=band)
    if request.args.get('format') == 'svg':
        return Response(tile_svg, mimetype='image/svg+xml')
    if request.args.get('format') == 'json':
        return jsonify({"region": canonical, "name": name, "band": band,
                        "age_min": age_min, "tile_svg": tile_svg,
                        "schema": "wa-radar-v1", "version": R9_VERSION})
    return render_template('weather_radar.html',
                           region=canonical, name=name, band=band,
                           age_min=age_min, tile_svg=tile_svg)


# ---- R9 earthquake list -------------------------------------------------
_R9_QUAKE_REGIONS = [
    'Pacific Ring of Fire', 'Mid-Atlantic Ridge', 'Sumatra',
    'Aleutian Islands', 'Japan Trench', 'Kermadec Trench',
    'Chile Trench', 'Hellenic Arc', 'Anatolian Fault',
    'San Andreas Fault', 'Cascadia Subduction', 'New Madrid',
    'Iceland Rift', 'East African Rift', 'Himalayan Arc',
    'Indonesia Banda Arc', 'Mariana Trench', 'Tonga Trench',
    'Kuril Trench', 'Iran Plateau', 'Mexico Subduction',
]
_R9_QUAKE_BUCKETS = [
    (3.0, 3.9, 'minor'),
    (4.0, 4.9, 'light'),
    (5.0, 5.9, 'moderate'),
    (6.0, 6.9, 'strong'),
    (7.0, 7.9, 'major'),
    (8.0, 9.5, 'great'),
]


@app.route('/earthquakes')
def r9_earthquakes():
    """Magnitude-filtered list of recent quakes."""
    try:
        mag_min = float(request.args.get('mag_min', '4.0'))
    except ValueError:
        mag_min = 4.0
    mag_min = max(1.0, min(9.5, mag_min))
    region_q = (request.args.get('region', '') or '').strip()
    quakes = []
    for i, region in enumerate(_R9_QUAKE_REGIONS):
        if region_q and region_q.lower() not in region.lower():
            continue
        for b_idx, (lo, hi, descriptor) in enumerate(_R9_QUAKE_BUCKETS):
            mag = round(lo + (i % 9) * (hi - lo) / 9, 1)
            if mag < mag_min:
                continue
            depth_km = 5 + ((i * 7 + b_idx * 3) % 60)
            lat = round(-60 + (i * 17) % 120, 2)
            lng = round(-180 + (i * 23) % 360, 2)
            quakes.append({"magnitude": mag, "descriptor": descriptor,
                           "region": region, "depth_km": depth_km,
                           "lat": lat, "lng": lng,
                           "event_id": f"wa{i:02d}{b_idx}"})
    quakes.sort(key=lambda q: q['magnitude'], reverse=True)
    payload = {"count": len(quakes), "mag_min": mag_min,
               "region": region_q, "quakes": quakes,
               "schema": "wa-quake-v1", "version": R9_VERSION}
    _r8_emit('earthquakes.listed', 'earthquake-recent-list',
             count=len(quakes), mag_min=mag_min)
    if request.args.get('format') == 'json':
        return jsonify(payload)
    return render_template('earthquakes.html',
                           quakes=quakes, mag_min=mag_min, region=region_q)


# ---- R9 tide table ------------------------------------------------------
_R9_TIDE_LOCATIONS = {
    'Boston':         ('semidiurnal', 2, 2, 'northeast-us'),
    'New-York':       ('semidiurnal', 2, 2, 'northeast-us'),
    'Norfolk':        ('semidiurnal', 2, 2, 'southeast-us'),
    'Charleston':     ('semidiurnal', 2, 2, 'southeast-us'),
    'Miami':          ('semidiurnal', 2, 2, 'gulf-coast'),
    'New-Orleans':    ('diurnal', 1, 1, 'gulf-coast'),
    'Galveston':      ('diurnal', 1, 1, 'gulf-coast'),
    'San-Diego':      ('mixed-semidiurnal', 2, 2, 'california'),
    'San-Francisco':  ('mixed-semidiurnal', 2, 2, 'california'),
    'Seattle':        ('mixed-semidiurnal', 2, 2, 'pacific-northwest'),
    'Anchorage':      ('mixed-semidiurnal', 2, 2, 'alaska'),
    'Honolulu':       ('mixed-semidiurnal', 2, 2, 'hawaii'),
    'Vancouver':      ('mixed-semidiurnal', 2, 2, 'pacific-northwest'),
    'Halifax':        ('semidiurnal', 2, 2, 'northeast-us'),
    'St-Johns':       ('semidiurnal', 2, 2, 'northeast-us'),
    'London':         ('semidiurnal', 2, 2, 'british-isles'),
    'Liverpool':      ('semidiurnal', 2, 2, 'british-isles'),
    'Hamburg':        ('semidiurnal', 2, 2, 'central-europe'),
    'Rotterdam':      ('semidiurnal', 2, 2, 'central-europe'),
    'Lisbon':         ('semidiurnal', 2, 2, 'iberian'),
    'Barcelona':      ('semidiurnal', 2, 2, 'iberian'),
    'Marseille':      ('semidiurnal', 2, 2, 'mediterranean'),
    'Naples':         ('semidiurnal', 2, 2, 'mediterranean'),
    'Athens':         ('semidiurnal', 2, 2, 'balkans'),
    'Tokyo':          ('semidiurnal', 2, 2, 'tokyo-bay'),
    'Yokohama':       ('semidiurnal', 2, 2, 'tokyo-bay'),
    'Osaka':          ('semidiurnal', 2, 2, 'osaka-kansai'),
    'Busan':          ('semidiurnal', 2, 2, 'seoul'),
    'Shanghai':       ('semidiurnal', 2, 2, 'shanghai-yangtze'),
    'Hong-Kong':      ('mixed-semidiurnal', 2, 2, 'pearl-river'),
    'Singapore':      ('mixed-semidiurnal', 2, 2, 'southeast-asia'),
    'Mumbai':         ('semidiurnal', 2, 2, 'southeast-asia'),
    'Sydney':         ('semidiurnal', 2, 2, 'australia-east'),
    'Auckland':       ('semidiurnal', 2, 2, 'australia-east'),
    'Cape-Town':      ('semidiurnal', 2, 2, 'iberian'),
    'Buenos-Aires':   ('semidiurnal', 2, 2, 'mediterranean'),
    'Rio-de-Janeiro': ('semidiurnal', 2, 2, 'mediterranean'),
}


@app.route('/tide/<location>')
def r9_tide_tomorrow(location):
    """Tomorrow tide schedule for any registered coastal location."""
    if location not in _R9_TIDE_LOCATIONS:
        # Try a case-insensitive alias.
        match = next((k for k in _R9_TIDE_LOCATIONS
                      if k.lower() == location.lower()), None)
        if not match:
            abort(404)
        location = match
    pattern, n_hi, n_lo, radar_region = _R9_TIDE_LOCATIONS[location]
    h = int(hashlib.md5(location.encode()).hexdigest(), 16)
    coef = 30 + (h % 70)
    base_h = h % 12
    base_m = (h // 12) % 60
    height_hi = round(1.0 + ((h // 60) % 35) * 0.1, 2)
    height_lo = round(0.1 + ((h // 100) % 9) * 0.08, 2)
    # Build events spread across the 24h.
    events = []
    interval = 24 // (n_hi + n_lo)
    for i in range(n_hi + n_lo):
        kind = 'high' if i % 2 == 0 else 'low'
        height = height_hi if kind == 'high' else height_lo
        hh_ = (base_h + i * interval) % 24
        mm_ = (base_m + i * 7) % 60
        events.append({"kind": kind, "time": f"{hh_:02d}:{mm_:02d}",
                       "height": height})
    payload = {"location": location, "day": "tomorrow",
               "pattern": pattern, "highs": n_hi, "lows": n_lo,
               "coefficient": coef, "events": events,
               "radar_region": radar_region,
               "schema": "wa-tide-v1", "version": R9_VERSION}
    _r8_emit('tide.viewed', 'tide-tomorrow',
             location=location, coefficient=coef)
    if request.args.get('format') == 'json':
        return jsonify(payload)
    return render_template('tide_tomorrow.html',
                           location=location, pattern=pattern,
                           highs=n_hi, lows=n_lo, coefficient=coef,
                           events=events, radar_region=radar_region)


# ---------------------------------------------------------------------------
# R10 vertical tools (10 routes + 1 shared template)
# ---------------------------------------------------------------------------
# Each handler reads query params, computes a deterministic payload that
# matches the schema strings advertised in `_build_seed_r10.py`, and renders
# either JSON (`?format=json`) or `templates/r10/vertical.html`.  Lookup
# tables below mirror the seed builder so the live response is consistent
# with the rows already present in `computation_results`; for parameters
# outside the seed catalog the handler still returns a valid 200 with a
# deterministic fallback computed from the same formula.
R10_VERSION = 'r10'
R10_SNAPSHOT_DATE = '2026-05-27'

_R10_CCY_RATES = {
    'USD': 1.0,   'EUR': 0.92, 'GBP': 0.79, 'JPY': 156.4,
    'CNY': 7.21,  'CAD': 1.36, 'AUD': 1.49, 'CHF': 0.89,
    'INR': 83.2,  'MXN': 17.5, 'BRL': 5.04, 'KRW': 1372.0,
    'SGD': 1.34,  'HKD': 7.81, 'NZD': 1.63, 'SEK': 10.51,
}

_R10_RECIPES = {
    'chicken-pesto-pasta':  (620, 38, 55, 26),
    'vegan-buddha-bowl':    (540, 18, 78, 16),
    'keto-cheeseburger':    (740, 42,  8, 60),
    'tofu-stir-fry':        (460, 28, 38, 22),
    'beef-tacos':           (580, 32, 42, 30),
    'shrimp-fried-rice':    (510, 26, 64, 14),
    'paleo-roast-chicken':  (520, 48, 12, 30),
    'lentil-soup':          (380, 22, 52,  8),
    'caesar-salad':         (410, 18, 18, 30),
    'margherita-pizza':     (620, 22, 78, 24),
    'vegan-curry':          (480, 14, 64, 18),
    'greek-yogurt-bowl':    (320, 24, 36,  8),
    'overnight-oats':       (360, 14, 56, 10),
    'salmon-teriyaki':      (560, 36, 36, 24),
    'falafel-wrap':         (520, 18, 64, 22),
    'miso-ramen':           (580, 22, 70, 22),
    'chicken-tikka-masala': (640, 34, 36, 36),
    'beef-bourguignon':     (720, 42, 22, 48),
    'mushroom-risotto':     (580, 14, 78, 18),
    'caprese-salad':        (320, 16, 12, 24),
    'breakfast-burrito':    (540, 24, 48, 28),
    'protein-smoothie':     (290, 28, 32,  4),
    'quinoa-salad':         (420, 14, 56, 16),
    'thai-green-curry':     (540, 24, 48, 28),
    'chickpea-stew':        (380, 16, 56, 10),
    'shakshuka':            (360, 18, 24, 22),
    'pad-thai':             (560, 24, 70, 18),
    'zucchini-noodles':     (220, 12, 22, 10),
}

_R10_CRYPTOS = {
    'BTC':   (64200.0, -0.8, 2.4e10),
    'ETH':   (3140.0,   0.6, 1.1e10),
    'SOL':   (148.5,   -1.4, 2.6e9),
    'XRP':   (0.52,    -0.3, 1.8e9),
    'ADA':   (0.43,     0.9, 4.4e8),
    'DOGE':  (0.14,    -2.1, 1.2e9),
    'AVAX':  (26.8,     1.4, 3.7e8),
    'MATIC': (0.72,    -0.4, 2.4e8),
    'LINK':  (14.2,     0.7, 2.6e8),
    'DOT':   (6.4,     -0.2, 1.4e8),
    'LTC':   (78.5,     0.5, 3.6e8),
    'BCH':   (410.0,   -0.1, 3.1e8),
    'UNI':   (7.6,     -1.1, 1.4e8),
    'ATOM':  (8.5,      0.3, 1.6e8),
    'NEAR':  (5.8,      1.2, 2.4e8),
    'FIL':   (4.2,     -0.8, 1.2e8),
}

_R10_HOTELS = {
    'hilton-times-square':    ('Hilton Times Square', 'New York', 'NY-US',
        [('king', 289), ('double', 249), ('suite', 489)]),
    'park-hyatt-tokyo':       ('Park Hyatt Tokyo', 'Tokyo', 'JP',
        [('deluxe', 720), ('park-suite', 1480), ('presidential', 3800)]),
    'hotel-lutetia-paris':    ('Hotel Lutetia', 'Paris', 'FR',
        [('queen', 540), ('king', 690), ('executive', 1100)]),
    'four-seasons-singapore': ('Four Seasons Singapore', 'Singapore', 'SG',
        [('deluxe', 480), ('premier', 640), ('suite', 1280)]),
    'marriott-marquis-sf':    ('Marriott Marquis SF', 'San Francisco', 'CA-US',
        [('king', 329), ('double', 299), ('suite', 599)]),
    'grand-hyatt-hk':         ('Grand Hyatt Hong Kong', 'Hong Kong', 'HK',
        [('grand-king', 410), ('harbour-view', 540), ('grand-suite', 1200)]),
    'shangri-la-sydney':      ('Shangri-La Sydney', 'Sydney', 'AU',
        [('horizon', 395), ('grand-harbour', 540), ('suite', 990)]),
    'ritz-carlton-doha':      ('Ritz-Carlton Doha', 'Doha', 'QA',
        [('deluxe', 380), ('club', 520), ('suite', 980)]),
    'beverly-wilshire':       ('Beverly Wilshire', 'Beverly Hills', 'CA-US',
        [('king', 750), ('signature-suite', 1450), ('presidential', 4200)]),
    'mandarin-london':        ('Mandarin Oriental London', 'London', 'UK',
        [('deluxe', 690), ('park-view', 990), ('suite', 1800)]),
    'peninsula-bangkok':      ('Peninsula Bangkok', 'Bangkok', 'TH',
        [('deluxe', 320), ('grand', 460), ('suite', 980)]),
    'intercon-geneva':        ('InterContinental Geneva', 'Geneva', 'CH',
        [('classic', 360), ('club', 480), ('executive-suite', 920)]),
    'aman-kyoto':             ('Aman Kyoto', 'Kyoto', 'JP',
        [('garden', 1480), ('suite', 2400), ('pavilion', 4800)]),
    'w-barcelona':            ('W Barcelona', 'Barcelona', 'ES',
        [('wonderful', 320), ('cool-corner', 480), ('extreme-wow', 1200)]),
    'claridges-london':       ('Claridges', 'London', 'UK',
        [('superior', 720), ('deluxe', 920), ('royal-suite', 6800)]),
    'westin-tokyo':           ('Westin Tokyo', 'Tokyo', 'JP',
        [('classic', 380), ('club', 520), ('suite', 920)]),
}

_R10_MOVIES = {
    'avatar-3':                   ('Avatar 3', '2025-12-19', 'Lightstorm/20C', 460, 980, 2400),
    'dune-part-three':            ('Dune: Part Three', '2026-12-18', 'Legendary/WB', 145, 380, 720),
    'mission-impossible-9':       ('Mission: Impossible 9', '2026-05-23', 'Paramount', 78, 220, 540),
    'inside-out-2':               ('Inside Out 2', '2024-06-14', 'Pixar/Disney', 154, 652, 1672),
    'deadpool-and-wolverine':     ('Deadpool & Wolverine', '2024-07-26', 'Marvel/Disney', 211, 636, 1338),
    'wicked':                     ('Wicked', '2024-11-22', 'Universal', 114, 472, 728),
    'moana-2':                    ('Moana 2', '2024-11-27', 'Disney', 225, 460, 1060),
    'gladiator-ii':               ('Gladiator II', '2024-11-22', 'Paramount', 56, 171, 462),
    'twisters':                   ('Twisters', '2024-07-19', 'Universal', 81, 268, 372),
    'beetlejuice-beetlejuice':    ('Beetlejuice Beetlejuice', '2024-09-06', 'WB', 110, 294, 451),
    'joker-folie-a-deux':         ('Joker: Folie a Deux', '2024-10-04', 'WB', 38, 58, 207),
    'a-quiet-place-day-one':      ('A Quiet Place: Day One', '2024-06-28', 'Paramount', 53, 138, 261),
    'it-ends-with-us':            ('It Ends with Us', '2024-08-09', 'Sony', 50, 148, 350),
    'the-wild-robot':             ('The Wild Robot', '2024-09-27', 'DreamWorks/Universal', 35, 144, 324),
    'mufasa-the-lion-king':       ('Mufasa: The Lion King', '2024-12-20', 'Disney', 36, 250, 720),
    'alien-romulus':              ('Alien: Romulus', '2024-08-16', '20C/Disney', 41, 110, 350),
    'despicable-me-4':            ('Despicable Me 4', '2024-07-03', 'Illumination/Universal', 122, 361, 970),
    'bad-boys-ride-or-die':       ('Bad Boys: Ride or Die', '2024-06-07', 'Sony', 56, 194, 405),
    'kingdom-of-the-planet-apes': ('Kingdom of the Planet of the Apes', '2024-05-10', '20C/Disney', 58, 171, 397),
    'the-fall-guy':               ('The Fall Guy', '2024-05-03', 'Universal', 28, 92, 180),
}

_R10_TICKERS = {
    'AAPL':  ('Apple Inc.', 198.4),
    'MSFT':  ('Microsoft Corp.', 423.7),
    'NVDA':  ('NVIDIA Corp.', 928.5),
    'GOOGL': ('Alphabet Inc.', 168.2),
    'AMZN':  ('Amazon.com Inc.', 184.3),
    'META':  ('Meta Platforms Inc.', 471.6),
    'TSLA':  ('Tesla Inc.', 178.4),
    'BRK-B': ('Berkshire Hathaway B', 408.1),
    'JPM':   ('JPMorgan Chase', 198.8),
    'V':     ('Visa Inc.', 275.2),
    'UNH':   ('UnitedHealth', 521.4),
    'XOM':   ('ExxonMobil', 111.9),
    'JNJ':   ('Johnson & Johnson', 148.6),
    'WMT':   ('Walmart', 64.2),
    'PG':    ('Procter & Gamble', 167.3),
    'AVGO':  ('Broadcom', 1390.6),
    'LLY':   ('Eli Lilly', 802.5),
    'MA':    ('Mastercard', 458.7),
    'HD':    ('Home Depot', 348.2),
    'CVX':   ('Chevron', 158.5),
}

_R10_BOOKS = {
    '9780262033848': ('Introduction to Algorithms', 'Cormen, Leiserson, Rivest, Stein', 'MIT Press', 2009, 1312, 'en'),
    '9780201633610': ('Design Patterns', 'Gamma, Helm, Johnson, Vlissides', 'Addison-Wesley', 1994, 395, 'en'),
    '9780132350884': ('Clean Code', 'Robert C. Martin', 'Prentice Hall', 2008, 464, 'en'),
    '9780321125217': ('Domain-Driven Design', 'Eric Evans', 'Addison-Wesley', 2003, 560, 'en'),
    '9780135957059': ('The Pragmatic Programmer', 'Hunt, Thomas', 'Addison-Wesley', 2019, 352, 'en'),
    '9780321573513': ('Algorithms 4ed', 'Sedgewick, Wayne', 'Addison-Wesley', 2011, 976, 'en'),
    '9780131103627': ('The C Programming Language', 'Kernighan, Ritchie', 'Prentice Hall', 1988, 272, 'en'),
    '9780596007126': ('Head First Design Patterns', 'Freeman, Robson', "O'Reilly", 2004, 694, 'en'),
    '9780321776402': ('Effective Java', 'Joshua Bloch', 'Addison-Wesley', 2017, 412, 'en'),
    '9780321356680': ('Effective C++', 'Scott Meyers', 'Addison-Wesley', 2005, 320, 'en'),
    '9780672327094': ('Linux Kernel Development', 'Robert Love', 'Addison-Wesley', 2010, 472, 'en'),
    '9780596009205': ('Programming Collective Intelligence', 'Toby Segaran', "O'Reilly", 2007, 360, 'en'),
    '9780596002817': ('Programming Perl', 'Wall, Christiansen, Orwant', "O'Reilly", 2000, 1067, 'en'),
    '9781492052203': ('Fluent Python', 'Luciano Ramalho', "O'Reilly", 2022, 1014, 'en'),
    '9781449355739': ('Learning Python', 'Mark Lutz', "O'Reilly", 2013, 1648, 'en'),
    '9780136708558': ('Computer Networks', 'Tanenbaum, Feamster, Wetherall', 'Pearson', 2020, 944, 'en'),
    '9780133594140': ('Computer Networking 7ed', 'Kurose, Ross', 'Pearson', 2016, 864, 'en'),
    '9780136083450': ('Computer Organization and Design', 'Patterson, Hennessy', 'Morgan Kaufmann', 2013, 800, 'en'),
    '9780124077263': ('Computer Architecture 5ed', 'Hennessy, Patterson', 'Morgan Kaufmann', 2011, 856, 'en'),
    '9780321486813': ('Compilers: Principles, Techniques, Tools', 'Aho, Lam, Sethi, Ullman', 'Pearson', 2006, 1009, 'en'),
    '9780262510875': ('Structure and Interpretation of Computer Programs', 'Abelson, Sussman', 'MIT Press', 1996, 657, 'en'),
    '9780134685991': ('Effective Modern C++', 'Scott Meyers', "O'Reilly", 2014, 334, 'en'),
    '9780136291558': ('Operating Systems Internals and Design Principles', 'William Stallings', 'Pearson', 2017, 800, 'en'),
    '9780133970777': ('Database System Concepts', 'Silberschatz, Korth, Sudarshan', 'McGraw-Hill', 2019, 1376, 'en'),
    '9780321125521': ('Patterns of Enterprise Application Architecture', 'Martin Fowler', 'Addison-Wesley', 2002, 560, 'en'),
}
_R10_ISBN_MODES = ['summary', 'cover', 'toc', 'reviews', 'citations']

_R10_CARRIERS = ['UPS', 'FedEx', 'USPS', 'DHL', 'Royal-Mail',
                 'Japan-Post', 'China-Post', 'Australia-Post']
_R10_PKG_STATUSES = {
    'label-created':    ('Label created at origin',          5),
    'picked-up':        ('Picked up by carrier',             4),
    'in-transit':       ('In transit between facilities',    3),
    'out-for-delivery': ('Out for delivery',                 1),
    'delivered':        ('Delivered to recipient',           0),
    'exception':        ('Delivery exception',               2),
}

_R10_RACES = {
    'us-president-2024':         ('US President 2024', 'Harris', 'Trump'),
    'uk-general-2025':           ('UK General Election 2025', 'Labour', 'Conservative'),
    'canada-federal-2025':       ('Canada Federal 2025', 'LPC', 'CPC'),
    'germany-federal-2025':      ('Germany Federal 2025', 'SPD', 'CDU/CSU'),
    'france-presidential-2027':  ('France Presidential 2027', 'Renaissance', 'RN'),
    'australia-federal-2025':    ('Australia Federal 2025', 'Labor', 'Coalition'),
    'india-general-2024':        ('India General 2024', 'INC', 'BJP'),
    'japan-lower-house-2025':    ('Japan Lower House 2025', 'LDP', 'CDP'),
    'south-korea-2027':          ('South Korea Presidential 2027', 'PPP', 'DP'),
    'brazil-2026':               ('Brazil Presidential 2026', 'PT', 'PL'),
    'mexico-2024':               ('Mexico Presidential 2024', 'Morena', 'PAN-PRI-PRD'),
    'argentina-2027':            ('Argentina Presidential 2027', 'LLA', 'UxP'),
    'italy-general-2027':        ('Italy General 2027', 'PD', 'FdI'),
    'spain-general-2027':        ('Spain General 2027', 'PSOE', 'PP'),
    'netherlands-2025':          ('Netherlands General 2025', 'GL-PvdA', 'VVD'),
    'poland-presidential-2025':  ('Poland Presidential 2025', 'KO', 'PiS'),
}
_R10_POLL_FIRMS = ['YouGov', 'Ipsos', 'Gallup', 'Pew', 'Quinnipiac',
                   'Morning-Consult', 'AtlasIntel', 'Datafolha']

_R10_TRANSLATE_DEMO = {
    ('en', 'es'): 'hola',     ('en', 'fr'): 'bonjour',
    ('en', 'de'): 'hallo',    ('en', 'it'): 'ciao',
    ('en', 'pt'): 'ola',      ('en', 'ja'): 'konnichiwa',
    ('en', 'ko'): 'annyeong', ('en', 'zh'): 'nihao',
    ('en', 'ru'): 'privet',   ('en', 'ar'): 'marhaba',
    ('en', 'hi'): 'namaste',  ('en', 'nl'): 'hallo',
    ('en', 'sv'): 'hej',      ('en', 'tr'): 'merhaba',
}


def _r10_render(slug, title, intro, params, parsed, plaintext, pod_title,
                payload, related, topic_slug):
    """Shared HTML/JSON renderer for every R10 vertical route."""
    if request.args.get('format') == 'json':
        return jsonify(payload)
    payload_rows = [(k, payload[k]) for k in sorted(payload)
                    if k not in ('schema',)]
    return render_template(
        'r10/vertical.html',
        r10_slug=slug, r10_title=title, r10_intro=intro,
        r10_params=params, r10_parsed_input=parsed,
        r10_plaintext=plaintext, r10_pod_title=pod_title,
        r10_payload_rows=payload_rows, r10_schema=payload.get('schema', ''),
        r10_version=R10_VERSION, r10_related=related,
        r10_topic_slug=topic_slug,
    )


# ---- R10 (1) Currency converter -----------------------------------------
@app.route('/finance/currency-convert')
def r10_currency_convert():
    try:
        amt = float(request.args.get('amt', '100'))
    except (TypeError, ValueError):
        amt = 100.0
    a = (request.args.get('from', 'USD') or 'USD').upper()
    b = (request.args.get('to', 'EUR') or 'EUR').upper()
    rate_a = _R10_CCY_RATES.get(a, 1.0)
    rate_b = _R10_CCY_RATES.get(b, 1.0)
    rate = round(rate_b / rate_a, 6)
    converted = round(amt * rate, 4)
    parsed = f"CurrencyConvert[amount={amt}, from={a!r}, to={b!r}]"
    plain = (f"{amt} {a} = {converted} {b} at mid-market rate {rate} "
             f"on {R10_SNAPSHOT_DATE}.")
    payload = {"amount": amt, "from": a, "to": b, "rate": rate,
               "converted": converted, "snapshot_date": R10_SNAPSHOT_DATE,
               "schema": "wa-currency-v1", "version": R10_VERSION}
    _r8_emit('r10.currency.converted', 'currency-pair-converter',
             a=a, b=b, amt=amt)
    return _r10_render(
        'currency-convert', 'Currency Pair Converter',
        'Convert between two fiat currencies at the snapshot mid-market rate.',
        [('amt', amt), ('from', a), ('to', b)],
        parsed, plain, 'Currency conversion', payload,
        [f"{a} to {b} rate today", f"{b} to {a} reverse",
         f"{amt} {a} to USD", f"USD to {b} chart"],
        'currency-pair-converter')


# ---- R10 (2) Recipe macros ----------------------------------------------
@app.route('/cooking/recipe-macros')
def r10_recipe_macros():
    slug = (request.args.get('slug', 'chicken-pesto-pasta')
            or 'chicken-pesto-pasta').strip().lower()
    try:
        servings = int(request.args.get('servings', '1'))
    except (TypeError, ValueError):
        servings = 1
    servings = max(1, min(16, servings))
    if slug in _R10_RECIPES:
        cal_s, p_s, c_s, f_s = _R10_RECIPES[slug]
    else:
        h = int(hashlib.md5(slug.encode()).hexdigest(), 16)
        cal_s = 300 + (h % 500)
        p_s = 10 + (h // 7 % 40)
        c_s = 20 + (h // 11 % 60)
        f_s = 5 + (h // 13 % 30)
    tot_cal = cal_s * servings
    tot_p   = p_s * servings
    tot_c   = c_s * servings
    tot_f   = f_s * servings
    parsed = f"RecipeMacros[recipe={slug!r}, servings={servings}]"
    plain = (f"{slug} x{servings}: total {tot_cal} kcal, "
             f"P{tot_p}g / C{tot_c}g / F{tot_f}g. "
             f"Per serving: {cal_s} kcal.")
    payload = {"recipe": slug, "servings": servings,
               "per_serving": {"kcal": cal_s, "protein_g": p_s,
                               "carbs_g": c_s, "fat_g": f_s},
               "total": {"kcal": tot_cal, "protein_g": tot_p,
                         "carbs_g": tot_c, "fat_g": tot_f},
               "snapshot_date": R10_SNAPSHOT_DATE,
               "schema": "wa-recipe-macro-v1", "version": R10_VERSION}
    _r8_emit('r10.recipe.macros', 'recipe-macro-calculator',
             slug=slug, servings=servings)
    return _r10_render(
        'recipe-macros', 'Recipe Macro Calculator',
        'Tally calories, protein, carbs, fat for a recipe and serving count.',
        [('slug', slug), ('servings', servings)],
        parsed, plain, 'Recipe macros', payload,
        [f"{slug} ingredients", f"{slug} prep time",
         f"swap servings {servings}->{servings*2}",
         f"calories per serving {slug}"],
        'recipe-macro-calculator')


# ---- R10 (3) Crypto pair quote ------------------------------------------
@app.route('/finance/crypto-quote')
def r10_crypto_quote():
    pair = request.args.get('pair', '')
    if pair and '-' in pair:
        base, quote = pair.split('-', 1)
    else:
        base = request.args.get('base', 'BTC')
        quote = request.args.get('quote', 'USD')
    base = (base or 'BTC').upper()
    quote = (quote or 'USD').upper()
    if base in _R10_CRYPTOS:
        px, chg, vol = _R10_CRYPTOS[base]
    else:
        h = int(hashlib.md5(base.encode()).hexdigest(), 16)
        px = round(1 + (h % 100000) / 100.0, 6)
        chg = round(((h // 7) % 800 - 400) / 100.0, 2)
        vol = float(1_000_000 + (h % 5_000_000))
    fx = _R10_CCY_RATES.get(quote, 1.0)
    local_px = round(px * fx, 6)
    parsed = f"CryptoQuote[base={base!r}, quote={quote!r}]"
    plain = (f"{base}/{quote}: last {local_px}, 24h change {chg:+.2f}%, "
             f"24h volume {vol:.0f} {quote}.")
    payload = {"base": base, "quote": quote, "last": local_px,
               "change_24h_pct": chg, "volume_24h": vol,
               "snapshot_date": R10_SNAPSHOT_DATE,
               "schema": "wa-crypto-quote-v1", "version": R10_VERSION}
    _r8_emit('r10.crypto.quoted', 'crypto-pair-quote',
             base=base, quote=quote)
    return _r10_render(
        'crypto-quote', 'Crypto Pair Quote',
        'Snapshot last price, 24h change, and 24h volume for a crypto pair.',
        [('base', base), ('quote', quote)],
        parsed, plain, 'Crypto pair quote', payload,
        [f"{base} chart 1d", f"{base} circulating supply",
         f"{base}-USD vs {base}-EUR", f"top movers {quote}"],
        'crypto-pair-quote')


# ---- R10 (4) Hotel room availability ------------------------------------
@app.route('/travel/hotel-availability')
def r10_hotel_availability():
    slug = (request.args.get('slug', 'hilton-times-square')
            or 'hilton-times-square').strip().lower()
    if slug in _R10_HOTELS:
        name, city, region, rooms = _R10_HOTELS[slug]
    else:
        h = int(hashlib.md5(slug.encode()).hexdigest(), 16)
        name = slug.replace('-', ' ').title()
        city = 'Unknown'
        region = 'XX'
        rates = [200 + h % 200, 350 + (h // 7) % 300, 800 + (h // 11) % 600]
        rooms = [('standard', rates[0]), ('deluxe', rates[1]), ('suite', rates[2])]
    check_in = request.args.get('check_in', '2026-06-03')
    check_out = request.args.get('check_out', '2026-06-04')
    try:
        ci_d = datetime.strptime(check_in, '%Y-%m-%d').date()
        co_d = datetime.strptime(check_out, '%Y-%m-%d').date()
        nights_default = max(1, (co_d - ci_d).days)
    except ValueError:
        nights_default = 1
    try:
        nights = int(request.args.get('nights', str(nights_default)))
    except (TypeError, ValueError):
        nights = nights_default
    nights = max(1, min(60, nights))
    # Deterministic occupancy mirrors seed formula.
    seed_hash = int(hashlib.md5(slug.encode()).hexdigest(), 16)
    occ = 0.45 + ((seed_hash + nights) % 50) / 100.0
    avail_rooms = []
    for rt, rate in rooms:
        rate_eff = round(rate * (1 + occ * 0.2), 2)
        avail_rooms.append({"type": rt, "rate_usd_per_night": rate_eff,
                            "available": True,
                            "total_usd": round(rate_eff * nights, 2)})
    parsed = (f"HotelAvailability[slug={slug!r}, check_in={check_in!r}, "
              f"check_out={check_out!r}]")
    plain = (f"{name} ({city}, {region}) {check_in} -> {check_out} "
             f"({nights} nights): {len(rooms)} room types, "
             f"occupancy {occ:.0%}.")
    payload = {"slug": slug, "name": name, "city": city, "region": region,
               "check_in": check_in, "check_out": check_out,
               "nights": nights, "occupancy": round(occ, 3),
               "rooms": avail_rooms,
               "snapshot_date": R10_SNAPSHOT_DATE,
               "schema": "wa-hotel-availability-v1",
               "version": R10_VERSION}
    _r8_emit('r10.hotel.availability', 'hotel-room-availability',
             slug=slug, nights=nights)
    return _r10_render(
        'hotel-availability', 'Hotel Room Availability',
        'Room types and per-night rates for a hotel + date window.',
        [('slug', slug), ('check_in', check_in),
         ('check_out', check_out), ('nights', nights)],
        parsed, plain, 'Hotel availability', payload,
        [f"{name} reviews", f"{name} amenities",
         f"flights to {city}", f"hotels near {name}"],
        'hotel-room-availability')


# ---- R10 (5) Movie box office ------------------------------------------
@app.route('/entertainment/box-office')
def r10_box_office():
    slug = (request.args.get('slug', 'avatar-3')
            or 'avatar-3').strip().lower()
    try:
        week = int(request.args.get('week', '1'))
    except (TypeError, ValueError):
        week = 1
    week = max(1, min(52, week))
    if slug in _R10_MOVIES:
        name, opening, studio, opening_w, dom_total, ww_total = _R10_MOVIES[slug]
    else:
        h = int(hashlib.md5(slug.encode()).hexdigest(), 16)
        name = slug.replace('-', ' ').title()
        opening = '2026-01-01'
        studio = 'Studio X'
        opening_w = 20 + (h % 80)
        dom_total = opening_w * 3
        ww_total = opening_w * 6
    grown_dom = round(dom_total * min(1.0, week / 18.0), 2)
    grown_ww  = round(ww_total  * min(1.0, week / 20.0), 2)
    if grown_ww < grown_dom:
        grown_ww = grown_dom
    parsed = f"BoxOffice[slug={slug!r}, week={week}]"
    plain = (f"{name} ({studio}) opening {opening}: opening weekend "
             f"${opening_w}M, week {week} -> domestic ${grown_dom}M, "
             f"worldwide ${grown_ww}M.")
    payload = {"slug": slug, "name": name, "studio": studio,
               "opening_date": opening,
               "opening_weekend_musd": opening_w,
               "week": week,
               "domestic_musd": grown_dom,
               "worldwide_musd": grown_ww,
               "snapshot_date": R10_SNAPSHOT_DATE,
               "schema": "wa-box-office-v1", "version": R10_VERSION}
    _r8_emit('r10.boxoffice.viewed', 'movie-box-office-tracker',
             slug=slug, week=week)
    return _r10_render(
        'box-office', 'Movie Box Office Tracker',
        'Track a film’s opening weekend, domestic, and worldwide grosses.',
        [('slug', slug), ('week', week)],
        parsed, plain, 'Box office', payload,
        [f"{name} reviews", f"{name} cast", f"{name} sequel",
         f"{studio} 2024 slate"],
        'movie-box-office-tracker')


# ---- R10 (6) Stock history replay ---------------------------------------
@app.route('/finance/stock-history')
def r10_stock_history():
    ticker = (request.args.get('ticker', 'AAPL')
              or 'AAPL').strip().upper()
    try:
        window = int(request.args.get('window', '30'))
    except (TypeError, ValueError):
        window = 30
    window = max(1, min(365, window))
    if ticker in _R10_TICKERS:
        name, base_px = _R10_TICKERS[ticker]
    else:
        h = int(hashlib.md5(ticker.encode()).hexdigest(), 16)
        name = f"{ticker} Corp."
        base_px = 50 + (h % 950)
    d_open = round(base_px, 2)
    d_high = round(d_open * (1 + (window % 7) / 200.0), 2)
    d_low  = round(d_open * (1 - (window % 5) / 200.0), 2)
    d_close = round((d_high + d_low) / 2, 2)
    volume = 1_000_000 + (window % 500) * 100_000
    parsed = f"StockHistory[ticker={ticker!r}, window={window}]"
    plain = (f"{name} ({ticker}) {window}-day replay: open {d_open}, "
             f"high {d_high}, low {d_low}, close {d_close}, "
             f"vol {volume:,}.")
    payload = {"ticker": ticker, "name": name, "window_days": window,
               "open": d_open, "high": d_high, "low": d_low,
               "close": d_close, "volume": volume,
               "snapshot_date": R10_SNAPSHOT_DATE,
               "schema": "wa-stock-ohlcv-v1", "version": R10_VERSION}
    _r8_emit('r10.stock.history', 'stock-quote-history-replay',
             ticker=ticker, window=window)
    return _r10_render(
        'stock-history', 'Stock Quote History Replay',
        'Replay a stock’s OHLCV over a custom window.',
        [('ticker', ticker), ('window', window)],
        parsed, plain, 'Stock OHLCV', payload,
        [f"{ticker} fundamentals", f"{ticker} earnings calendar",
         f"{ticker} option chain", f"{name} peers"],
        'stock-quote-history-replay')


# ---- R10 (7) ISBN book lookup -------------------------------------------
@app.route('/books/isbn-lookup')
def r10_isbn_lookup():
    isbn = (request.args.get('isbn', '9780262033848')
            or '9780262033848').strip().replace('-', '')
    mode = (request.args.get('mode', 'summary') or 'summary').strip().lower()
    if mode not in _R10_ISBN_MODES:
        mode = 'summary'
    if isbn in _R10_BOOKS:
        title, author, pub, year, pages, lang = _R10_BOOKS[isbn]
    else:
        h = int(hashlib.md5(isbn.encode()).hexdigest(), 16)
        title = f"Unknown Title {isbn[-4:]}"
        author = 'Unknown Author'
        pub = 'Unknown Publisher'
        year = 2000 + (h % 26)
        pages = 200 + (h % 800)
        lang = 'en'
    parsed = f"ISBNLookup[isbn={isbn!r}, mode={mode!r}]"
    plain = (f"{title} by {author} ({pub}, {year}), {pages} pages, "
             f"language {lang}. View: {mode}.")
    payload = {"isbn": isbn, "title": title, "author": author,
               "publisher": pub, "year": year, "pages": pages,
               "language": lang, "mode": mode,
               "snapshot_date": R10_SNAPSHOT_DATE,
               "schema": "wa-isbn-v1", "version": R10_VERSION}
    _r8_emit('r10.isbn.lookup', 'isbn-book-lookup',
             isbn=isbn, mode=mode)
    return _r10_render(
        'isbn-lookup', 'ISBN Book Lookup',
        'Resolve an ISBN to title, author, publisher, year, pages, language.',
        [('isbn', isbn), ('mode', mode)],
        parsed, plain, 'ISBN lookup', payload,
        [f"{title} editions", f"{author} bibliography",
         f"{pub} catalog", f"books like {title}"],
        'isbn-book-lookup')


# ---- R10 (8) Package tracking -------------------------------------------
@app.route('/travel/package-track')
def r10_package_track():
    carrier_q = (request.args.get('carrier', 'UPS') or 'UPS').strip()
    # Carrier-name match is case-insensitive against the canonical list.
    canon = {c.lower(): c for c in _R10_CARRIERS}
    carrier = canon.get(carrier_q.lower(), carrier_q)
    tracking_id = (request.args.get('id', 'ABC123') or 'ABC123').strip()
    status_q = (request.args.get('status', 'label-created')
                or 'label-created').strip().lower()
    if status_q not in _R10_PKG_STATUSES:
        # Deterministic hash-bucket fallback.
        bucket = list(_R10_PKG_STATUSES)
        h = int(hashlib.md5(status_q.encode()).hexdigest(), 16)
        status_q = bucket[h % len(bucket)]
    status_desc, eta_days = _R10_PKG_STATUSES[status_q]
    eta_date = (datetime(2026, 5, 27) + timedelta(days=eta_days)).date().isoformat()
    parsed = f"PackageTrack[carrier={carrier!r}, id={tracking_id!r}]"
    plain = f"{carrier} {tracking_id}: {status_desc}. ETA {eta_date}."
    payload = {"carrier": carrier, "tracking_id": tracking_id,
               "status_code": status_q, "status_desc": status_desc,
               "eta_date": eta_date,
               "snapshot_date": R10_SNAPSHOT_DATE,
               "schema": "wa-package-v1", "version": R10_VERSION}
    _r8_emit('r10.package.tracked', 'package-tracking-status',
             carrier=carrier, status=status_q)
    return _r10_render(
        'package-track', 'Package Tracking Status',
        'Trace a parcel by carrier and tracking number.',
        [('carrier', carrier), ('id', tracking_id), ('status', status_q)],
        parsed, plain, 'Package status', payload,
        [f"{carrier} contact", f"{carrier} service map",
         f"shipment exceptions {carrier}",
         f"refund {carrier} late delivery"],
        'package-tracking-status')


# ---- R10 (9) Election poll aggregator -----------------------------------
@app.route('/society/election-polls')
def r10_election_polls():
    race_slug = (request.args.get('race', 'us-president-2024')
                 or 'us-president-2024').strip().lower()
    if race_slug in _R10_RACES:
        race_name, party_a, party_b = _R10_RACES[race_slug]
    else:
        race_name = race_slug.replace('-', ' ').title()
        party_a, party_b = 'Party A', 'Party B'
    firm = (request.args.get('firm', 'YouGov') or 'YouGov').strip()
    if firm not in _R10_POLL_FIRMS:
        # Keep client-supplied firm name; it lands in the response either way.
        pass
    # Deterministic hash for non-seeded races + firms (still sums to 100).
    seed = f"{race_slug}|{firm}"
    h = int(hashlib.md5(seed.encode()).hexdigest(), 16)
    a_pct = 30 + (h % 35)
    b_pct = 30 + ((h // 7) % 35)
    other = 100 - a_pct - b_pct
    moe = 2 + ((h // 11) % 4)
    parsed = f"PollAggregate[race={race_slug!r}, firm={firm!r}]"
    plain = (f"{race_name}: {party_a} {a_pct}% vs {party_b} {b_pct}% "
             f"(other {other}%) per {firm} +/- {moe}%.")
    payload = {"race_slug": race_slug, "race_name": race_name,
               "firm": firm,
               "party_a": party_a, "pct_a": a_pct,
               "party_b": party_b, "pct_b": b_pct,
               "other_pct": other, "moe": moe,
               "snapshot_date": R10_SNAPSHOT_DATE,
               "schema": "wa-poll-v1", "version": R10_VERSION}
    _r8_emit('r10.polls.aggregated', 'election-poll-aggregator',
             race=race_slug, firm=firm)
    return _r10_render(
        'election-polls', 'Election Poll Aggregator',
        'Weighted-mean poll snapshot for a national race.',
        [('race', race_slug), ('firm', firm)],
        parsed, plain, 'Poll aggregate', payload,
        [f"{race_name} polls history", f"{party_a} platform",
         f"{party_b} platform", f"{race_name} debate transcript"],
        'election-poll-aggregator')


# ---- R10 (10) Translate pair --------------------------------------------
@app.route('/society/translate')
def r10_translate():
    phrase = request.args.get('phrase', 'hello') or 'hello'
    src = (request.args.get('src', 'en') or 'en').strip().lower()
    tgt = (request.args.get('tgt', 'es') or 'es').strip().lower()
    demo = _R10_TRANSLATE_DEMO.get((src, tgt))
    if phrase == 'hello' and demo:
        translation = demo
    else:
        translation = f"[{tgt}] {phrase}"
    h = int(hashlib.md5(f"{phrase}|{src}|{tgt}".encode()).hexdigest(), 16)
    confidence = 70 + (h % 30)
    label = 'hi' if phrase == 'hello' else 'phrase'
    parsed = f"Translate[src={src!r}, tgt={tgt!r}, phrase={phrase!r}]"
    plain = (f"'{phrase}' [{src}] -> '{translation}' [{tgt}] "
             f"(label: {label}, confidence {confidence}%).")
    payload = {"phrase": phrase, "label": label,
               "src_lang": src, "tgt_lang": tgt,
               "translation": translation,
               "confidence_pct": confidence,
               "snapshot_date": R10_SNAPSHOT_DATE,
               "schema": "wa-translate-v1", "version": R10_VERSION}
    _r8_emit('r10.translate.done', 'language-translation-pair',
             src=src, tgt=tgt)
    return _r10_render(
        'translate', 'Language Translation Pair',
        'Snapshot translation, romanization, and confidence for a phrase.',
        [('phrase', phrase), ('src', src), ('tgt', tgt)],
        parsed, plain, 'Translation', payload,
        [f"romanize {phrase!r} in {tgt}",
         f"pronunciation of {translation}",
         f"useful {tgt} phrases",
         f"{src} <-> {tgt} dictionary"],
        'language-translation-pair')


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


# === R2-R3 backfill BEGIN — auto-generated, do not hand-edit between markers ===
# Added 2026-05-27 to backfill the R2 (i18n / a11y / l10n) and
# R3 (observability + static chrome) surfaces that the verify subagent
# flagged as missing.  No DB writes — instance_seed/*.db md5 is unchanged.

import hashlib as _r23_hashlib

# ---------------------------------------------------------------------------
# R2 — Internationalization / accessibility / localization surface
# ---------------------------------------------------------------------------

R2_LOCALES = (
    ('en', 'English',     'ltr'),
    ('zh', '简体中文',     'ltr'),
    ('ja', '日本語',       'ltr'),
    ('es', 'Español',     'ltr'),
    ('fr', 'Français',    'ltr'),
    ('de', 'Deutsch',     'ltr'),
    ('pt', 'Português',   'ltr'),
    ('ar', 'العربية',     'rtl'),
    ('he', 'עברית',       'rtl'),
)
R2_RTL = {'ar', 'he'}
R2_SITE_NAME = "Wolfram Alpha"
R2_DOMAIN = "wolframalpha.com"
R2_ACCESSIBILITY_BLURB = "Wolfram Alpha renders equations as MathML with text alternatives so that answers remain comprehensible to assistive technologies."


def r2_normalize_locale(code):
    code = (code or '').strip().lower()
    if any(code == c for c, _, _ in R2_LOCALES):
        return code
    primary = code.split('-')[0].split('_')[0]
    return primary if any(primary == c for c, _, _ in R2_LOCALES) else 'en'


def r2_label_for(code):
    for c, label, _ in R2_LOCALES:
        if c == code:
            return label
    return 'English'


@app.route('/r2/lang/<code>')
def r2_lang_switch(code):
    norm = r2_normalize_locale(code)
    direction = 'rtl' if norm in R2_RTL else 'ltr'
    label = r2_label_for(norm)
    return (
        '<!doctype html><html lang="' + norm + '" dir="' + direction + '">'
        '<head><meta charset="utf-8"><title>' + label + ' – ' + R2_SITE_NAME + '</title>'
        '<link rel="alternate" hreflang="' + norm + '" href="/r2/lang/' + norm + '">'
        '</head><body>'
        '<header role="banner">' + R2_SITE_NAME + ' locale switcher</header>'
        '<main role="main" aria-label="Locale switch result">'
        '<h1>Locale set to ' + label + ' (' + norm + ')</h1>'
        '<p>Page direction: <strong>' + direction + '</strong>.</p>'
        '<p><a href="/r2/locales">Back to locale catalog</a>.</p>'
        '</main><footer role="contentinfo">/r2/lang</footer>'
        '</body></html>'
    )


@app.route('/r2/locales')
def r2_locales_catalog():
    return {
        'site': R2_SITE_NAME,
        'default': 'en',
        'locales': [
            {'code': c, 'label': l, 'dir': d} for c, l, d in R2_LOCALES
        ],
    }


@app.route('/r2/hreflang')
def r2_hreflang_index():
    links = '\n'.join(
        '<link rel="alternate" hreflang="' + c + '" href="/r2/lang/' + c + '">'
        for c, _, _ in R2_LOCALES
    )
    rows = '\n'.join(
        '<tr><td>' + c + '</td><td>' + l + '</td><td>' + d + '</td></tr>'
        for c, l, d in R2_LOCALES
    )
    return (
        '<!doctype html><html lang="en"><head>' + links +
        '<title>hreflang catalog</title></head><body>'
        '<main role="main" aria-labelledby="hreflang-h1">'
        '<h1 id="hreflang-h1">' + R2_SITE_NAME + ' hreflang catalog</h1>'
        '<table><thead><tr><th>code</th><th>label</th><th>dir</th></tr></thead>'
        '<tbody>' + rows + '</tbody></table></main></body></html>'
    )


@app.route('/r2/accessibility-policy')
def r2_accessibility_policy():
    return (
        '<!doctype html><html lang="en"><body>'
        '<header role="banner">' + R2_SITE_NAME + '</header>'
        '<nav role="navigation" aria-label="Policies"><ul>'
        '<li><a href="/r2/accessibility-policy">Accessibility</a></li>'
        '<li><a href="/r2/aria-tour">ARIA tour</a></li>'
        '<li><a href="/r2/locales">Locales</a></li>'
        '</ul></nav>'
        '<main role="main" aria-labelledby="a11y-h1">'
        '<h1 id="a11y-h1">Accessibility Policy</h1>'
        '<p>' + R2_ACCESSIBILITY_BLURB + '</p>'
        '<h2>Conformance target</h2>'
        '<p>This site targets <strong>WCAG 2.1 Level AA</strong> with ARIA 1.2 patterns and Section 508 alignment.</p>'
        '<h2>Reporting an issue</h2>'
        '<p>Email <a href="mailto:accessibility@' + R2_DOMAIN + '">accessibility@' + R2_DOMAIN + '</a>.</p>'
        '<h2>Last reviewed</h2><p>2026-05-27</p>'
        '</main><footer role="contentinfo">/r2/accessibility-policy</footer>'
        '</body></html>'
    )


@app.route('/r2/aria-tour')
def r2_aria_tour():
    landmarks = (
        ('banner', 'Site-wide header.'),
        ('navigation', 'Primary menu.'),
        ('main', 'Primary content.'),
        ('search', 'Site search.'),
        ('form', 'Forms outside main.'),
        ('region', 'Generic region with aria-label.'),
        ('complementary', 'Sidebar / aside.'),
        ('contentinfo', 'Footer area.'),
    )
    items = ''.join(
        '<li role="listitem"><strong>' + role + '</strong> — ' + desc + '</li>'
        for role, desc in landmarks
    )
    return (
        '<!doctype html><html lang="en"><body>'
        '<header role="banner">' + R2_SITE_NAME + ' banner</header>'
        '<nav role="navigation" aria-label="Primary">primary nav</nav>'
        '<main role="main" aria-labelledby="aria-h1">'
        '<h1 id="aria-h1">ARIA landmark tour</h1>'
        '<ul role="list">' + items + '</ul>'
        '</main>'
        '<aside role="complementary" aria-label="Related">complementary region</aside>'
        '<footer role="contentinfo">/r2/aria-tour</footer>'
        '</body></html>'
    )


@app.route('/r2/i18n.json')
def r2_i18n_json():
    return {
        'site': R2_SITE_NAME,
        'default_locale': 'en',
        'locales': [c for c, _, _ in R2_LOCALES],
        'rtl': sorted(R2_RTL),
        'fallback_chain': ['en'],
        'updated': '2026-05-27',
    }


@app.route('/r2/keyboard-shortcuts')
def r2_keyboard_shortcuts():
    pairs = (
        ('?', 'Open shortcuts help'),
        ('/', 'Focus search'),
        ('g h', 'Go to home'),
        ('g l', 'Go to locale picker'),
        ('g a', 'Go to accessibility policy'),
        ('Esc', 'Close dialog'),
        ('Tab', 'Move focus forward'),
        ('Shift+Tab', 'Move focus backward'),
    )
    rows = ''.join(
        '<tr><td><kbd>' + k + '</kbd></td><td>' + v + '</td></tr>'
        for k, v in pairs
    )
    return (
        '<!doctype html><html lang="en"><body>'
        '<main role="main" aria-labelledby="kbd-h1">'
        '<h1 id="kbd-h1">Keyboard shortcuts</h1>'
        '<table><thead><tr><th>Keys</th><th>Action</th></tr></thead><tbody>' + rows + '</tbody></table>'
        '</main></body></html>'
    )


# ---------------------------------------------------------------------------
# R3 — Observability + static chrome
# ---------------------------------------------------------------------------

R3_BOOT_TS = '2024-04-10T12:00:00Z'
R3_UPTIME_SECONDS = 31_557_600  # one anchor-year — fixed for determinism
R3_SITE_NAME = "Wolfram Alpha"
R3_DOMAIN = "wolframalpha.com"


def r3_event_id(seq):
    return _r23_hashlib.md5(('r3-evt-' + R3_SITE_NAME + '-' + str(seq)).encode()).hexdigest()[:12]


def r3_event_kind(seq):
    kinds = ('page_view', 'search', 'click', 'login', 'logout',
             'feed_open', 'api_hit', 'error_404', 'job_done', 'webhook_in')
    return kinds[seq % len(kinds)]


@app.route('/r3/healthz')
def r3_healthz():
    return {
        'status': 'ok',
        'site': R3_SITE_NAME,
        'version': '1.0.0',
        'boot': R3_BOOT_TS,
        'checks': {
            'web': 'ok',
            'db': 'ok',
            'cache': 'ok',
            'search': 'ok',
        },
    }


@app.route('/r3/uptime')
def r3_uptime():
    return {
        'uptime_seconds': R3_UPTIME_SECONDS,
        'since': R3_BOOT_TS,
        'replicas': 3,
        'region': 'us-east-1',
    }


@app.route('/r3/events')
def r3_events():
    out = []
    for i in range(50):
        out.append({
            'id': r3_event_id(i),
            'kind': r3_event_kind(i),
            'ts': R3_BOOT_TS,
            'seq': i,
        })
    return {'site': R3_SITE_NAME, 'count': len(out), 'events': out}


@app.route('/r3/robots.txt')
def r3_robots_alt():
    body = (
        'User-agent: *\n'
        'Allow: /\n'
        'Disallow: /admin\n'
        'Disallow: /api/internal\n'
        'Sitemap: /r3/sitemap.xml\n'
        '# ' + R3_SITE_NAME + ' (WebHarbor mirror)\n'
    )
    return body, 200, {'Content-Type': 'text/plain; charset=utf-8'}


@app.route('/r3/humans.txt')
def r3_humans_txt():
    body = (
        '/* TEAM */\n'
        'Site: ' + R3_SITE_NAME + '\n'
        'Maintainer: WebHarbor mirror project\n'
        'Location: Redmond / Chapel Hill\n'
        '\n/* THANKS */\n'
        'Upstream content authors retain copyright over scraped material.\n'
        '\n/* SITE */\n'
        'Domain: ' + R3_DOMAIN + '\n'
        'Standards: HTML5, ARIA 1.2, ISO 8601\n'
        'Last updated: 2026-05-27\n'
    )
    return body, 200, {'Content-Type': 'text/plain; charset=utf-8'}


@app.route('/r3/.well-known/security.txt')
def r3_security_txt():
    body = (
        'Contact: mailto:security@' + R3_DOMAIN + '\n'
        'Expires: 2099-12-31T23:59:59Z\n'
        'Preferred-Languages: en\n'
        'Canonical: /r3/.well-known/security.txt\n'
        'Policy: /r3/security-policy\n'
        'Acknowledgments: /r3/security-policy\n'
    )
    return body, 200, {'Content-Type': 'text/plain; charset=utf-8'}


@app.route('/r3/security-policy')
def r3_security_policy():
    return (
        '<!doctype html><html lang="en"><body>'
        '<main role="main" aria-labelledby="sec-h1">'
        '<h1 id="sec-h1">Security Policy</h1>'
        '<p>Report vulnerabilities to <code>security@' + R3_DOMAIN + '</code>.</p>'
        '<h2>Scope</h2><ul>'
        '<li>This WebHarbor mirror — server-side bugs</li>'
        '<li>Authentication issues on r2/r3 endpoints</li>'
        '</ul>'
        '<h2>Out of scope</h2><ul>'
        '<li>Upstream third-party services</li>'
        '<li>Denial-of-service against the dev mirror</li>'
        '</ul></main></body></html>'
    )


@app.route('/r3/status')
def r3_status_page():
    return (
        '<!doctype html><html lang="en"><body>'
        '<main role="main" aria-labelledby="status-h1">'
        '<h1 id="status-h1">' + R3_SITE_NAME + ' – System Status</h1>'
        '<p>All systems operational.</p>'
        '<table><thead><tr><th>Component</th><th>Status</th><th>Last incident</th></tr></thead>'
        '<tbody>'
        '<tr><td>web</td><td>ok</td><td>none</td></tr>'
        '<tr><td>db</td><td>ok</td><td>none</td></tr>'
        '<tr><td>cache</td><td>ok</td><td>none</td></tr>'
        '<tr><td>search</td><td>ok</td><td>none</td></tr>'
        '<tr><td>cdn</td><td>ok</td><td>none</td></tr>'
        '</tbody></table>'
        '<p>Uptime: ' + str(R3_UPTIME_SECONDS) + ' seconds since ' + R3_BOOT_TS + '.</p>'
        '</main></body></html>'
    )


@app.route('/r3/version')
def r3_version():
    return {
        'site': R3_SITE_NAME,
        'version': '1.0.0',
        'commit': _r23_hashlib.md5(('r3-version-' + R3_SITE_NAME).encode()).hexdigest()[:10],
        'built': R3_BOOT_TS,
        'channel': 'stable',
    }


@app.route('/r3/sitemap.xml')
def r3_sitemap_xml():
    urls = [
        '/r2/locales',
        '/r2/hreflang',
        '/r2/accessibility-policy',
        '/r2/aria-tour',
        '/r2/i18n.json',
        '/r2/keyboard-shortcuts',
        '/r3/healthz',
        '/r3/uptime',
        '/r3/events',
        '/r3/robots.txt',
        '/r3/humans.txt',
        '/r3/.well-known/security.txt',
        '/r3/security-policy',
        '/r3/status',
        '/r3/version',
    ]
    items = ''.join('<url><loc>' + u + '</loc></url>' for u in urls)
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        + items + '</urlset>'
    )
    return xml, 200, {'Content-Type': 'application/xml; charset=utf-8'}

# === R2-R3 backfill END ===


# === R4-R5-R6 backfill BEGIN — auto-generated, do not hand-edit between markers ===
# Added 2026-05-27 to backfill the R4 (formula editor + step-by-step + Pro
# paywall), R5 (Mathematica .nb notebook + executable cells + share), and
# R6 (curated datasets + tabular query + visualization) surfaces flagged
# missing by the verify subagent. APPEND-ONLY, no DB writes -- instance_seed/
# md5 unchanged; routes are net-new (none shadow R7-R10 verticals).

# ---------------------------------------------------------------------------
# R4 backfill: equation editor + step-by-step deriver + Pro paywall sim
# ---------------------------------------------------------------------------
R4_VERSION = 'r4'
R4_SNAPSHOT_DATE = '2026-05-27'

_R4_FORMULA_SAMPLES = {
    'derivative-x2':   ('d/dx x^2', 'Derivative[Power[x, 2], x]',     '2 x'),
    'integral-sin':    ('int sin(x) dx', 'Integrate[Sin[x], x]',      '-cos(x) + C'),
    'taylor-cos':      ('taylor cos(x) at 0', 'Series[Cos[x], {x,0,4}]',
                        '1 - x^2/2 + x^4/24 + O(x^6)'),
    'quadratic-roots': ('solve x^2-5x+6=0', 'Solve[x^2-5x+6==0, x]',  'x = 2 or x = 3'),
    'matrix-inv-2x2':  ('inverse {{a,b},{c,d}}', 'Inverse[{{a,b},{c,d}}]',
                        '1/(a d - b c) * {{d,-b},{-c,a}}'),
    'limit-sinx-x':    ('lim x->0 sin(x)/x', 'Limit[Sin[x]/x, x->0]', '1'),
    'series-geom':     ('sum_{k=0}^infty r^k', 'Sum[r^k, {k,0,Infinity}]',
                        '1/(1 - r)  (|r| < 1)'),
    'fourier-rect':    ('fourier rect pulse', 'FourierTransform[Rect[t], t, w]',
                        'sinc(w/2)'),
    'eigen-2x2':       ('eigenvalues {{2,1},{1,2}}', 'Eigenvalues[{{2,1},{1,2}}]',
                        '{3, 1}'),
    'ode-decay':       ("solve y'+ky=0", "DSolve[y'[t]+k y[t]==0, y[t], t]",
                        'y(t) = C1 e^{-k t}'),
}

_R4_PRO_TIERS = [
    ('pro-monthly',  'WolframAlpha Pro (monthly)',  7.25,  'monthly'),
    ('pro-yearly',   'WolframAlpha Pro (yearly)',   60.0,  'yearly'),
    ('pro-student',  'Pro Student',                 4.75,  'monthly'),
    ('pro-edu',      'Pro for Educators',           9.99,  'monthly'),
    ('pro-premium',  'Pro Premium',                 14.99, 'monthly'),
]


def _r4_parse_latex(src):
    s = (src or '').strip()
    if s.startswith('\\int '): return 'Integrate[' + s[5:].rstrip(' dx') + ', x]'
    if s.startswith('\\sum '): return 'Sum[' + s[5:] + ', k]'
    if s.startswith('\\frac{d}{dx}'): return 'Derivative[' + s[12:] + ', x]'
    if s.startswith('\\lim_'): return 'Limit[' + s[6:] + ', x->0]'
    return 'Hold[' + s + ']'


def _r4_steps_for(slug, is_pro):
    sample = _R4_FORMULA_SAMPLES.get(slug)
    if not sample:
        h = int(hashlib.md5(slug.encode()).hexdigest(), 16)
        depth = 3 + (h % 3)
        steps = []
        for i in range(depth):
            steps.append({
                'title': 'Step ' + str(i + 1),
                'body':  'Transform stage ' + str(i + 1) + ' for ' + repr(slug) + '.',
                'locked': (not is_pro) and (i >= 1),
            })
        return steps
    _, parsed, result = sample
    return [
        {'title': 'Step 1 (rewrite)',
         'body':  'Rewrite input as canonical form: ' + parsed,
         'locked': False},
        {'title': 'Step 2 (apply rule)',
         'body':  'Apply standard rule for ' + slug + '.',
         'locked': not is_pro},
        {'title': 'Step 3 (simplify)',
         'body':  'Simplify to: ' + result,
         'locked': not is_pro},
        {'title': 'Step 4 (verify)',
         'body':  'Verify: substituting back yields the original form.',
         'locked': not is_pro},
    ]


# ---- R4 (1) Equation editor ---------------------------------------------
@app.route('/editor/equation')
def r4_editor_equation():
    slug = (request.args.get('slug', 'derivative-x2') or 'derivative-x2').strip().lower()
    sample = _R4_FORMULA_SAMPLES.get(slug, _R4_FORMULA_SAMPLES['derivative-x2'])
    latex_text, parsed, _result = sample
    is_pro = current_user.is_authenticated and getattr(current_user, 'is_pro', False)
    step_pods = _r4_steps_for(slug, is_pro)
    _r8_emit('r4.editor.opened', 'equation-editor-formula-input',
             slug=slug, is_pro=int(is_pro))
    if request.args.get('format') == 'json':
        return jsonify({'slug': slug, 'latex': latex_text, 'parsed': parsed,
                        'steps': step_pods, 'is_pro': bool(is_pro),
                        'snapshot_date': R4_SNAPSHOT_DATE,
                        'schema': 'wa-equation-editor-v1', 'version': R4_VERSION})
    return render_template('r4_editor.html',
                           r4_slug=slug, r4_title='Equation Editor',
                           r4_intro='Compose, render, and step through a formula in LaTeX.',
                           r4_latex=latex_text, r4_mode='latex',
                           r4_parsed=parsed, r4_render_text=latex_text,
                           r4_step_pods=step_pods,
                           r4_snapshot=R4_SNAPSHOT_DATE,
                           r4_demo_cr_id=2)


# ---- R4 (2) Equation preview --------------------------------------------
@app.route('/editor/equation/preview')
def r4_editor_preview():
    latex = (request.args.get('latex', '') or '').strip()
    mode = (request.args.get('mode', 'latex') or 'latex').strip().lower()
    parsed = _r4_parse_latex(latex)
    h = int(hashlib.md5((latex + '|' + mode).encode()).hexdigest(), 16)
    width  = 200 + (h % 240)
    height = 60 + (h // 7 % 60)
    if request.args.get('format') == 'json':
        return jsonify({'latex': latex, 'parsed': parsed, 'mode': mode,
                        'width_px': width, 'height_px': height,
                        'snapshot_date': R4_SNAPSHOT_DATE,
                        'schema': 'wa-equation-preview-v1', 'version': R4_VERSION})
    _r8_emit('r4.editor.preview', 'equation-editor-preview-render',
             mode=mode, length=len(latex))
    return render_template('r4_editor.html',
                           r4_slug='preview', r4_title='Equation Preview',
                           r4_intro='Live render + parsed-input preview for an arbitrary LaTeX source.',
                           r4_latex=latex or 'd/dx x^2', r4_mode=mode,
                           r4_parsed=parsed,
                           r4_render_text=latex or 'd/dx x^2',
                           r4_step_pods=[],
                           r4_snapshot=R4_SNAPSHOT_DATE,
                           r4_demo_cr_id=2)


# ---- R4 (3) Equation export ---------------------------------------------
@app.route('/editor/equation/export')
def r4_editor_export():
    latex = (request.args.get('latex', '') or '').strip()
    fmt = (request.args.get('fmt', 'png') or 'png').strip().lower()
    if fmt not in ('png', 'svg', 'tex', 'mml'):
        fmt = 'png'
    h = hashlib.md5((latex + '|' + fmt).encode()).hexdigest()[:12]
    parsed = _r4_parse_latex(latex)
    _r8_emit('r4.editor.export', 'equation-editor-export-asset',
             fmt=fmt, latex_len=len(latex))
    if fmt == 'tex':
        body = ('% wa-equation-export v1 (' + R4_SNAPSHOT_DATE + ')\n'
                '% sha-prefix: ' + h + '\n'
                '\\begin{equation}\n' + (latex or 'x^2') + '\n\\end{equation}\n'
                '% parsed: ' + parsed + '\n')
        return Response(body, mimetype='text/x-tex')
    if fmt == 'svg':
        svg = ('<svg viewBox="0 0 200 60" xmlns="http://www.w3.org/2000/svg">'
               '<rect width="200" height="60" fill="#fafafa"/>'
               '<text x="8" y="38" font-family="serif" font-size="20">'
               + (latex or 'x^2')[:40] + '</text></svg>')
        return Response(svg, mimetype='image/svg+xml')
    return jsonify({'latex': latex, 'fmt': fmt, 'parsed': parsed,
                    'asset_id': h, 'snapshot_date': R4_SNAPSHOT_DATE,
                    'schema': 'wa-equation-export-v1', 'version': R4_VERSION})


# ---- R4 (4) Derive step-by-step -----------------------------------------
@app.route('/step-by-step/derive/<int:cr_id>')
def r4_step_derive(cr_id):
    comp = db.session.get(ComputationResult, cr_id)
    if not comp:
        abort(404)
    slug = comp.topic_slug or 'derivative-x2'
    is_pro = current_user.is_authenticated and getattr(current_user, 'is_pro', False)
    steps = _r4_steps_for(slug, is_pro)
    _r8_emit('r4.stepbystep.derived', 'step-by-step-derivation',
             cr_id=cr_id, is_pro=int(is_pro))
    if request.args.get('format') == 'json':
        return jsonify({'cr_id': cr_id, 'slug': slug, 'is_pro': bool(is_pro),
                        'steps': steps, 'snapshot_date': R4_SNAPSHOT_DATE,
                        'schema': 'wa-derive-stepbystep-v1', 'version': R4_VERSION})
    return render_template('r4_editor.html',
                           r4_slug=slug, r4_title='Derive: ' + str(comp.input_query),
                           r4_intro=('Show full derivation steps for this '
                                     'computation result.'),
                           r4_latex=comp.input_query or 'x^2',
                           r4_mode='derive',
                           r4_parsed=comp.parsed_input or comp.input_query,
                           r4_render_text=comp.input_query or 'x^2',
                           r4_step_pods=steps,
                           r4_snapshot=R4_SNAPSHOT_DATE,
                           r4_demo_cr_id=cr_id)


# ---- R4 (5) Walkthrough --------------------------------------------------
@app.route('/step-by-step/walkthrough/<int:cr_id>')
def r4_step_walkthrough(cr_id):
    comp = db.session.get(ComputationResult, cr_id)
    if not comp:
        abort(404)
    is_pro = current_user.is_authenticated and getattr(current_user, 'is_pro', False)
    try:
        idx = int(request.args.get('i', '1'))
    except (TypeError, ValueError):
        idx = 1
    steps = _r4_steps_for(comp.topic_slug or 'derivative-x2', is_pro)
    idx = max(1, min(len(steps), idx))
    cur = steps[idx - 1]
    payload = {'cr_id': cr_id, 'step_index': idx, 'step_count': len(steps),
               'title': cur['title'], 'body': cur['body'],
               'locked': cur['locked'], 'is_pro': bool(is_pro),
               'next': '/step-by-step/walkthrough/' + str(cr_id) + '?i=' + str(min(idx + 1, len(steps))),
               'prev': '/step-by-step/walkthrough/' + str(cr_id) + '?i=' + str(max(idx - 1, 1)),
               'snapshot_date': R4_SNAPSHOT_DATE,
               'schema': 'wa-step-walkthrough-v1', 'version': R4_VERSION}
    _r8_emit('r4.stepbystep.walkthrough', 'step-by-step-walkthrough',
             cr_id=cr_id, idx=idx)
    if request.args.get('format') == 'json':
        return jsonify(payload)
    return render_template('r4_editor.html',
                           r4_slug='walkthrough-' + str(cr_id),
                           r4_title='Walkthrough step ' + str(idx) + '/' + str(len(steps)),
                           r4_intro=('Step-at-a-time walkthrough of a '
                                     'derivation; next/prev to advance.'),
                           r4_latex=comp.input_query or 'x^2',
                           r4_mode='walkthrough',
                           r4_parsed=cur['title'],
                           r4_render_text=cur['body'],
                           r4_step_pods=steps,
                           r4_snapshot=R4_SNAPSHOT_DATE,
                           r4_demo_cr_id=cr_id)


# ---- R4 (6) Pro paywall preview -----------------------------------------
@app.route('/pro/paywall/preview')
def r4_pro_paywall_preview():
    src = (request.args.get('from', 'derivative-x2') or 'derivative-x2').strip().lower()
    step = request.args.get('step', '2')
    tiers = [{'slug': s, 'name': n, 'price': p, 'cycle': c}
             for (s, n, p, c) in _R4_PRO_TIERS]
    payload = {'paywall_id': hashlib.md5((src + '|' + step).encode()).hexdigest()[:10],
               'from': src, 'step': step, 'tiers': tiers,
               'unlocked_count': 1, 'locked_count': 3,
               'cta_url': '/pro/checkout?tier=pro-monthly&from=' + src,
               'snapshot_date': R4_SNAPSHOT_DATE,
               'schema': 'wa-pro-paywall-v1', 'version': R4_VERSION}
    _r8_emit('r4.paywall.shown', 'pro-paywall-preview-modal',
             src=src, step=step)
    if request.args.get('format') == 'json':
        return jsonify(payload)
    rows = [(k, payload[k]) for k in sorted(payload) if k not in ('schema', 'tiers')]
    return render_template('r10/vertical.html',
        r10_slug='pro-paywall', r10_title='Pro Paywall Preview',
        r10_intro='Simulated paywall modal showing locked steps + tier choices.',
        r10_params=[('from', src), ('step', step)],
        r10_parsed_input='ProPaywall[from=' + repr(src) + ', step=' + repr(step) + ']',
        r10_plaintext=('Paywall on step ' + str(step) + ': 1 of '
                       + str(payload['unlocked_count'] + payload['locked_count'])
                       + ' steps unlocked; sign in to Pro to view the remaining '
                       + str(payload['locked_count']) + '.'),
        r10_pod_title='Paywall', r10_payload_rows=rows,
        r10_schema=payload['schema'], r10_version=R4_VERSION,
        r10_related=['Pro features', 'Pro pricing',
                     'Step-by-step locked example'],
        r10_topic_slug='pro-paywall-preview-modal')


# ---- R4 (7) Pro checkout sim --------------------------------------------
@app.route('/pro/checkout', methods=['GET', 'POST'])
def r4_pro_checkout():
    tier = (request.values.get('tier', 'pro-monthly') or 'pro-monthly').strip().lower()
    src = (request.values.get('from', 'editor') or 'editor').strip().lower()
    selected = next((t for t in _R4_PRO_TIERS if t[0] == tier), _R4_PRO_TIERS[0])
    payload = {'tier': selected[0], 'name': selected[1],
               'price_usd': selected[2], 'cycle': selected[3],
               'from': src,
               'cart_id': hashlib.md5((tier + '|' + src).encode()).hexdigest()[:10],
               'estimated_tax_usd': round(selected[2] * 0.08, 2),
               'total_usd': round(selected[2] * 1.08, 2),
               'snapshot_date': R4_SNAPSHOT_DATE,
               'schema': 'wa-pro-checkout-v1', 'version': R4_VERSION}
    _r8_emit('r4.paywall.checkout', 'pro-paywall-checkout-sim',
             tier=tier, src=src)
    if request.method == 'POST' or request.args.get('format') == 'json':
        return jsonify(payload)
    rows = [(k, payload[k]) for k in sorted(payload) if k not in ('schema',)]
    return render_template('r10/vertical.html',
        r10_slug='pro-checkout', r10_title='Pro Checkout (sim)',
        r10_intro='Simulated Pro checkout summary, not a real purchase flow.',
        r10_params=[('tier', tier), ('from', src)],
        r10_parsed_input='ProCheckout[tier=' + repr(tier) + ', from=' + repr(src) + ']',
        r10_plaintext=('Cart for ' + selected[1] + ' at $' + str(selected[2])
                       + ' / ' + selected[3] + '; estimated total $'
                       + str(payload['total_usd']) + ' including 8% tax.'),
        r10_pod_title='Checkout', r10_payload_rows=rows,
        r10_schema=payload['schema'], r10_version=R4_VERSION,
        r10_related=['Pro features', 'Pro pricing',
                     'Step-by-step paywall examples'],
        r10_topic_slug='pro-paywall-checkout-sim')


# ---------------------------------------------------------------------------
# R5 backfill: Mathematica .nb notebook container + executable cells + share
# ---------------------------------------------------------------------------
R5_VERSION = 'r5'
R5_SNAPSHOT_DATE = '2026-05-27'
_R5_KERNEL_DEFAULT = 'WolframKernel-14.1'

_R5_NB_TEMPLATES = {
    'starter-calculus':     ('Starter: calculus walkthrough',
                             ['D[x^2, x]', 'Integrate[Sin[x], x]', 'Limit[Sin[x]/x, x->0]']),
    'starter-linalg':       ('Starter: linear algebra',
                             ['Inverse[{{1,2},{3,4}}]',
                              'Eigenvalues[{{2,1},{1,2}}]',
                              'NullSpace[{{1,2,3},{2,4,6}}]']),
    'starter-stats':        ('Starter: statistics',
                             ['Mean[{1,2,3,4,5}]', 'Variance[{1,2,3,4,5}]',
                              'Quantile[{1,2,3,4,5,6,7,8,9,10}, 0.75]']),
    'demo-ode':             ('Demo: ODE solver',
                             ["DSolve[y'[t]+y[t]==0, y[t], t]",
                              "NDSolve[{y'[t]==-y[t], y[0]==1}, y, {t,0,5}]"]),
    'demo-units':           ('Demo: unit conversion',
                             ['Convert[100 mph, kph]',
                              'Convert[1 atm, Pa]',
                              'Convert[6 ft, m]']),
    'tutorial-pattern':     ('Tutorial: pattern matching',
                             ['{1,2,3,4,5} /. x_ /; x>2 -> "big"',
                              'Cases[{a, 1, b, 2}, _Integer]',
                              'Replace[f[x,y], f[a_,b_]->a+b]']),
    'tutorial-plot':        ('Tutorial: plotting',
                             ['Plot[Sin[x], {x,0,2 Pi}]',
                              'ListPlot[Range[10]]',
                              'ContourPlot[x^2+y^2, {x,-2,2}, {y,-2,2}]']),
}


def _r5_cells_for(template):
    label, srcs = _R5_NB_TEMPLATES.get(template, _R5_NB_TEMPLATES['starter-calculus'])
    cells = []
    for i, src in enumerate(srcs):
        h = int(hashlib.md5((template + '|' + src).encode()).hexdigest(), 16)
        cells.append({
            'id': i + 1,
            'kind': 'code',
            'label': 'In[' + str(i + 1) + ']',
            'src': src,
            'out': '(* result-' + ('%04d' % (h % 9999)) + ' *)',
        })
        cells.append({
            'id': len(cells) + 1,
            'kind': 'markdown',
            'label': 'Note',
            'src': 'Result above is a deterministic snapshot of `' + src + '`.',
            'out': '',
        })
    return label, cells


# ---- R5 (1) Mathematica-style notebook create ----------------------------
@app.route('/nb/create-mathematica', methods=['GET', 'POST'])
def r5_nb_create_mathematica():
    template = (request.values.get('template', 'starter-calculus')
                or 'starter-calculus').strip().lower()
    label, cells = _r5_cells_for(template)
    nb_id = (int(hashlib.md5(template.encode()).hexdigest(), 16) % 9000) + 1000
    payload = {'nb_id': nb_id, 'template': template, 'label': label,
               'cells': cells, 'kernel': _R5_KERNEL_DEFAULT,
               'format': 'mathematica-nb',
               'snapshot_date': R5_SNAPSHOT_DATE,
               'schema': 'wa-nb-mathematica-v1', 'version': R5_VERSION}
    _r8_emit('r5.nb.created', 'mathematica-notebook-create',
             template=template, cells=len(cells))
    if request.args.get('format') == 'json':
        return jsonify(payload)
    return render_template('r5_notebook_mathematica.html',
                           r5_slug='create-' + template, r5_title=label,
                           r5_intro=('A Mathematica-style notebook seeded from a '
                                     'template; every code cell is evaluatable.'),
                           r5_nb_id=nb_id, r5_format='mathematica-nb',
                           r5_kernel=_R5_KERNEL_DEFAULT,
                           r5_snapshot=R5_SNAPSHOT_DATE,
                           r5_cells=cells, r5_share_token=None)


# ---- R5 (2) Cell detail --------------------------------------------------
@app.route('/nb/<int:nb_id>/cell/<int:cell_id>')
def r5_nb_cell(nb_id, cell_id):
    template = request.args.get('template', 'starter-calculus')
    label, cells = _r5_cells_for(template)
    cell = next((c for c in cells if c['id'] == cell_id), None)
    if not cell:
        abort(404)
    payload = {'nb_id': nb_id, 'cell_id': cell_id, 'template': template,
               'cell': cell, 'snapshot_date': R5_SNAPSHOT_DATE,
               'schema': 'wa-nb-cell-v1', 'version': R5_VERSION}
    _r8_emit('r5.nb.cell.viewed', 'mathematica-notebook-cell-detail',
             nb_id=nb_id, cell_id=cell_id)
    if request.args.get('format') == 'json':
        return jsonify(payload)
    return render_template('r5_notebook_mathematica.html',
                           r5_slug='nb-' + str(nb_id) + '-cell-' + str(cell_id),
                           r5_title='Cell ' + str(cell_id) + ' in nb ' + str(nb_id),
                           r5_intro='Single-cell view of cell ' + str(cell_id) + '.',
                           r5_nb_id=nb_id, r5_format='mathematica-nb',
                           r5_kernel=_R5_KERNEL_DEFAULT,
                           r5_snapshot=R5_SNAPSHOT_DATE,
                           r5_cells=[cell], r5_share_token=None)


# ---- R5 (3) Evaluate cell ------------------------------------------------
@app.route('/nb/<int:nb_id>/cell/<int:cell_id>/evaluate', methods=['POST', 'GET'])
def r5_nb_cell_evaluate(nb_id, cell_id):
    template = request.values.get('template', 'starter-calculus')
    src_override = request.values.get('src')
    label, cells = _r5_cells_for(template)
    cell = next((c for c in cells if c['id'] == cell_id), None)
    if not cell:
        abort(404)
    src = src_override or cell['src']
    h = int(hashlib.md5((str(nb_id) + '|' + str(cell_id) + '|' + src).encode()).hexdigest(), 16)
    result = 'Out[' + str(cell_id) + '] = sim-' + ('%05d' % (h % 99999))
    payload = {'nb_id': nb_id, 'cell_id': cell_id, 'src': src,
               'kernel': _R5_KERNEL_DEFAULT, 'result': result,
               'elapsed_ms': 4 + (h % 30),
               'snapshot_date': R5_SNAPSHOT_DATE,
               'schema': 'wa-nb-evaluate-v1', 'version': R5_VERSION}
    _r8_emit('r5.nb.cell.evaluated', 'mathematica-notebook-cell-evaluate',
             nb_id=nb_id, cell_id=cell_id)
    return jsonify(payload)


# ---- R5 (4) Share notebook -----------------------------------------------
@app.route('/nb/<int:nb_id>/share', methods=['POST', 'GET'])
def r5_nb_share(nb_id):
    audience = (request.values.get('audience', 'link') or 'link').strip().lower()
    template = request.values.get('template', 'starter-calculus')
    token = hashlib.md5(('nb-share|' + str(nb_id) + '|' + audience + '|' + template).encode()).hexdigest()[:12]
    payload = {'nb_id': nb_id, 'audience': audience, 'template': template,
               'share_token': token,
               'share_url': '/nb/share/' + token,
               'expires_at': '2026-08-25 12:00:00',
               'snapshot_date': R5_SNAPSHOT_DATE,
               'schema': 'wa-nb-share-v1', 'version': R5_VERSION}
    _r8_emit('r5.nb.shared', 'mathematica-notebook-share-link',
             nb_id=nb_id, audience=audience)
    if request.args.get('format') == 'json':
        return jsonify(payload)
    label, cells = _r5_cells_for(template)
    return render_template('r5_notebook_mathematica.html',
                           r5_slug='nb-' + str(nb_id) + '-share',
                           r5_title='Share notebook ' + str(nb_id),
                           r5_intro='Created a ' + audience + '-scope share link.',
                           r5_nb_id=nb_id, r5_format='mathematica-nb',
                           r5_kernel=_R5_KERNEL_DEFAULT,
                           r5_snapshot=R5_SNAPSHOT_DATE,
                           r5_cells=cells, r5_share_token=token)


# ---- R5 (5) View shared notebook ----------------------------------------
@app.route('/nb/share/<token>')
def r5_nb_share_view(token):
    h = int(hashlib.md5(token.encode()).hexdigest(), 16)
    template_keys = list(_R5_NB_TEMPLATES.keys())
    template = template_keys[h % len(template_keys)]
    label, cells = _r5_cells_for(template)
    nb_id = 9000 + (h % 999)
    payload = {'share_token': token, 'template': template, 'label': label,
               'cell_count': len(cells), 'nb_id': nb_id,
               'snapshot_date': R5_SNAPSHOT_DATE,
               'schema': 'wa-nb-share-view-v1', 'version': R5_VERSION}
    _r8_emit('r5.nb.share.viewed', 'mathematica-notebook-share-view',
             token=token, template=template)
    if request.args.get('format') == 'json':
        return jsonify(payload)
    return render_template('r5_notebook_mathematica.html',
                           r5_slug='share-' + token,
                           r5_title='Shared: ' + label,
                           r5_intro=('Read-only view of a notebook shared via '
                                     'a tokenized link.'),
                           r5_nb_id=nb_id, r5_format='mathematica-nb',
                           r5_kernel=_R5_KERNEL_DEFAULT,
                           r5_snapshot=R5_SNAPSHOT_DATE,
                           r5_cells=cells, r5_share_token=token)


# ---- R5 (6) Export .nb file ---------------------------------------------
@app.route('/nb/<int:nb_id>/export-nb')
def r5_nb_export_nb(nb_id):
    template = request.args.get('template', 'starter-calculus')
    label, cells = _r5_cells_for(template)
    lines = [
        '(* Content-type: application/vnd.wolfram.mathematica *)',
        '(* Wolfram Notebook File *)',
        '(* https://www.wolfram.com/nb *)',
        '(* CreatedBy=WolframAlpha mirror ' + R5_VERSION + ' *)',
        '(* nb_id=' + str(nb_id) + ' *)',
        '(* template=' + template + ' *)',
        '(* snapshot=' + R5_SNAPSHOT_DATE + ' *)',
        'Notebook[{',
    ]
    for c in cells:
        kind = 'Input' if c['kind'] == 'code' else 'Text'
        body = (c['src'] or '').replace('"', '\\"')
        lines.append('  Cell[BoxData["' + body + '"], "' + kind + '"],')
    lines.append('}]')
    _r8_emit('r5.nb.export', 'mathematica-notebook-export-nb',
             nb_id=nb_id, template=template)
    return Response('\n'.join(lines), mimetype='application/vnd.wolfram.mathematica')


# ---- R5 (7) Notebook templates gallery ----------------------------------
@app.route('/nb/templates')
def r5_nb_templates():
    rows = [{'slug': k, 'label': v[0], 'cell_count': len(v[1]) * 2}
            for k, v in _R5_NB_TEMPLATES.items()]
    payload = {'templates': rows, 'count': len(rows),
               'snapshot_date': R5_SNAPSHOT_DATE,
               'schema': 'wa-nb-templates-v1', 'version': R5_VERSION}
    _r8_emit('r5.nb.templates.listed', 'mathematica-notebook-templates-gallery',
             count=len(rows))
    if request.args.get('format') == 'json':
        return jsonify(payload)
    rows_kv = [(r['slug'], r['label'] + ' (' + str(r['cell_count']) + ' cells)') for r in rows]
    return render_template('r10/vertical.html',
        r10_slug='nb-templates', r10_title='Notebook Templates',
        r10_intro='Gallery of starter notebook templates (Mathematica .nb compatible).',
        r10_params=[('count', len(rows))],
        r10_parsed_input='NotebookTemplates[]',
        r10_plaintext=str(len(rows)) + ' notebook templates available.',
        r10_pod_title='Templates', r10_payload_rows=rows_kv,
        r10_schema=payload['schema'], r10_version=R5_VERSION,
        r10_related=['Create a notebook', 'Notebook share',
                     'Notebook export .nb'],
        r10_topic_slug='mathematica-notebook-templates-gallery')


# ---------------------------------------------------------------------------
# R6 backfill: curated datasets + tabular query + visualization
# ---------------------------------------------------------------------------
R6_VERSION = 'r6'
R6_SNAPSHOT_DATE = '2026-05-27'

_R6_DATASETS = {
    'world-population-2024':   (250, ['country', 'population_m', 'gdp_b_usd', 'area_km2'],
                                'CC-BY-4.0', 'Curated 2024 country totals.'),
    'planet-orbital-params':   (8,   ['planet', 'au', 'period_yr', 'mass_earth'],
                                'CC0', 'Snapshot of solar-system orbital parameters.'),
    'periodic-table':          (118, ['symbol', 'atomic_number', 'mass_amu', 'group'],
                                'CC0', 'Curated periodic-table snapshot.'),
    'sp500-snapshot-2026q1':   (500, ['ticker', 'cap_b_usd', 'pe_ratio', 'div_pct'],
                                'CC-BY-4.0', 'S&P 500 snapshot 2026 Q1.'),
    'us-city-demographics':    (300, ['city', 'pop_k', 'median_inc_k', 'area_km2'],
                                'CC-BY-4.0', 'US city demographic snapshot.'),
    'world-airport-codes':     (5000, ['iata', 'lat', 'lon', 'elev_ft'],
                                'CC-BY-4.0', 'World airport IATA codes + geo.'),
    'covid-cases-2020-2024':   (1825, ['date', 'cases_k', 'deaths_k', 'tests_m'],
                                'CC-BY-4.0', 'Daily worldwide COVID totals 2020-2024.'),
    'movies-imdb-top-1000':    (1000, ['title', 'year', 'rating', 'votes_k'],
                                'IMDb-non-commercial', 'IMDb top 1000 snapshot.'),
    'olympic-medals-1896-2024':(750, ['country', 'gold', 'silver', 'bronze'],
                                'CC-BY-4.0', 'Olympic medal totals by country.'),
    'global-volcanoes':        (1500, ['name', 'lat', 'lon', 'elev_m'],
                                'CC-BY-4.0', 'Catalog of global volcanoes.'),
    'us-zip-codes':            (40000, ['zip', 'lat', 'lon', 'pop_k'],
                                'CC-BY-4.0', 'US ZIP code snapshot.'),
    'currency-exchange-2026':  (180, ['code', 'rate_to_usd', 'rate_to_eur', 'rate_to_jpy'],
                                'CC-BY-4.0', 'Fiat FX rate snapshot 2026-05-27.'),
}


def _r6_sample_rows(slug, n=5):
    spec = _R6_DATASETS.get(slug, _R6_DATASETS['world-population-2024'])
    rows_count, cols, _lic, _desc = spec
    out = []
    for i in range(min(n, rows_count)):
        h = int(hashlib.md5((slug + '|' + str(i)).encode()).hexdigest(), 16)
        row = []
        for j, c in enumerate(cols):
            if j == 0:
                row.append(slug.split('-')[0][:4] + '-' + ('%04d' % i))
            else:
                row.append(round(((h >> (j * 7)) % 9999) / 7.3, 2))
        out.append(row)
    return cols, out


def _r6_chart_svg(slug, kind, col='', x='', y=''):
    h = int(hashlib.md5((slug + '|' + kind + '|' + col + '|' + x + '|' + y).encode()).hexdigest(), 16)
    if kind == 'histogram':
        bins = []
        for k in range(10):
            bins.append(20 + ((h >> (k * 3)) % 80))
        bars = ''
        for k, v in enumerate(bins):
            bars += ('<rect x="' + str(10 + k * 28) + '" y="' + str(120 - v)
                     + '" width="24" height="' + str(v) + '" fill="#f96302"/>')
        return ('<svg viewBox="0 0 320 140" xmlns="http://www.w3.org/2000/svg" '
                'class="wa-r6-chart wa-r6-chart-histogram">'
                '<rect width="320" height="140" fill="#fafafa"/>'
                + bars + '<text x="8" y="14" font-size="11" fill="#666">'
                'histogram[' + slug + '.' + col + ']</text></svg>')
    if kind == 'scatter':
        pts = ''
        for k in range(30):
            cx = 10 + ((h >> (k * 2)) % 300)
            cy = 10 + ((h >> (k * 3 + 1)) % 120)
            pts += '<circle cx="' + str(cx) + '" cy="' + str(cy) + '" r="2.5" fill="#1d4ed8"/>'
        return ('<svg viewBox="0 0 320 140" xmlns="http://www.w3.org/2000/svg" '
                'class="wa-r6-chart wa-r6-chart-scatter">'
                '<rect width="320" height="140" fill="#fafafa"/>'
                + pts + '<text x="8" y="14" font-size="11" fill="#666">'
                'scatter[' + slug + '.' + x + ' vs ' + slug + '.' + y + ']</text></svg>')
    return ('<svg viewBox="0 0 320 140" xmlns="http://www.w3.org/2000/svg">'
            '<rect width="320" height="140" fill="#fafafa"/>'
            '<text x="8" y="80" font-size="14">chart[' + slug + ']</text></svg>')


# ---- R6 (1) Dataset catalog --------------------------------------------
@app.route('/datasets')
def r6_datasets_index():
    rows = []
    for k, v in _R6_DATASETS.items():
        rows.append({'slug': k, 'rows': v[0], 'columns': v[1],
                     'license': v[2], 'description': v[3]})
    payload = {'datasets': rows, 'count': len(rows),
               'snapshot_date': R6_SNAPSHOT_DATE,
               'schema': 'wa-dataset-catalog-v1', 'version': R6_VERSION}
    _r8_emit('r6.datasets.listed', 'curated-dataset-catalog',
             count=len(rows))
    if request.args.get('format') == 'json':
        return jsonify(payload)
    rows_kv = [(r['slug'], str(r['rows']) + ' rows, license ' + r['license'])
               for r in rows]
    return render_template('r10/vertical.html',
        r10_slug='datasets', r10_title='Curated Datasets',
        r10_intro=('Curated datasets (Wolfram Data Drop style) browsable, '
                   'queryable, and chartable from the dataset detail page.'),
        r10_params=[('count', len(rows))],
        r10_parsed_input='DatasetCatalog[]',
        r10_plaintext=str(len(rows)) + ' curated datasets available.',
        r10_pod_title='Catalog', r10_payload_rows=rows_kv,
        r10_schema=payload['schema'], r10_version=R6_VERSION,
        r10_related=['Dataset query', 'Histogram visualization',
                     'Scatter visualization', 'Dataset CSV download'],
        r10_topic_slug='curated-dataset-catalog')


# ---- R6 (2) Dataset detail ---------------------------------------------
@app.route('/datasets/<slug>')
def r6_dataset_detail(slug):
    spec = _R6_DATASETS.get(slug)
    if not spec:
        abort(404)
    rows_count, cols, license_str, description = spec
    cols_seen, sample = _r6_sample_rows(slug, n=8)
    default_col = cols[1] if len(cols) > 1 else cols[0]
    if request.args.get('format') == 'json':
        return jsonify({'slug': slug, 'rows': rows_count, 'columns': cols,
                        'license': license_str, 'description': description,
                        'sample': sample,
                        'snapshot_date': R6_SNAPSHOT_DATE,
                        'schema': 'wa-dataset-detail-v1', 'version': R6_VERSION})
    _r8_emit('r6.dataset.viewed', 'curated-dataset-detail',
             slug=slug, rows=rows_count)
    return render_template('r6_dataset.html',
                           r6_slug=slug, r6_title=slug.replace('-', ' ').title(),
                           r6_intro=description,
                           r6_columns=cols, r6_rows=sample,
                           r6_rows_count=rows_count,
                           r6_snapshot=R6_SNAPSHOT_DATE,
                           r6_license=license_str,
                           r6_query_demo='Filter[' + (cols[1] if len(cols) > 1 else cols[0]) + ' > 100]',
                           r6_query_result=None,
                           r6_default_col=default_col,
                           r6_chart_svg='')


# ---- R6 (3) Dataset query -----------------------------------------------
@app.route('/datasets/<slug>/query')
def r6_dataset_query(slug):
    spec = _R6_DATASETS.get(slug)
    if not spec:
        abort(404)
    rows_count, cols, license_str, description = spec
    q = (request.args.get('q', '') or '').strip()
    h = int(hashlib.md5((slug + '|' + q).encode()).hexdigest(), 16)
    matched = (h % max(1, rows_count // 4)) + 1
    cols_seen, sample = _r6_sample_rows(slug, n=min(10, matched))
    result_text = ('Query: ' + repr(q) + '\n'
                   'Matched: ' + str(matched) + ' of ' + str(rows_count) + ' rows\n'
                   'Engine: WL-emulator-r6\n'
                   'Snapshot: ' + R6_SNAPSHOT_DATE)
    payload = {'slug': slug, 'query': q, 'matched': matched,
               'rows_total': rows_count, 'sample': sample,
               'columns': cols, 'snapshot_date': R6_SNAPSHOT_DATE,
               'schema': 'wa-dataset-query-v1', 'version': R6_VERSION}
    _r8_emit('r6.dataset.queried', 'curated-dataset-query',
             slug=slug, q_len=len(q))
    if request.args.get('format') == 'json':
        return jsonify(payload)
    return render_template('r6_dataset.html',
                           r6_slug=slug,
                           r6_title='Query result on ' + slug,
                           r6_intro='Filtered ' + str(matched) + ' rows for ' + repr(q) + '.',
                           r6_columns=cols, r6_rows=sample,
                           r6_rows_count=rows_count,
                           r6_snapshot=R6_SNAPSHOT_DATE,
                           r6_license=license_str,
                           r6_query_demo=q,
                           r6_query_result=result_text,
                           r6_default_col=cols[1] if len(cols) > 1 else cols[0],
                           r6_chart_svg='')


# ---- R6 (4) Histogram visualization ------------------------------------
@app.route('/datasets/<slug>/viz/histogram')
def r6_dataset_viz_histogram(slug):
    spec = _R6_DATASETS.get(slug)
    if not spec:
        abort(404)
    rows_count, cols, license_str, description = spec
    col = (request.args.get('col', cols[1] if len(cols) > 1 else cols[0])
           or cols[0]).strip()
    svg = _r6_chart_svg(slug, 'histogram', col=col)
    _r8_emit('r6.dataset.viz', 'curated-dataset-histogram',
             slug=slug, col=col)
    if request.args.get('format') == 'svg':
        return Response(svg, mimetype='image/svg+xml')
    if request.args.get('format') == 'json':
        return jsonify({'slug': slug, 'kind': 'histogram', 'col': col,
                        'snapshot_date': R6_SNAPSHOT_DATE,
                        'schema': 'wa-dataset-viz-histogram-v1',
                        'version': R6_VERSION})
    cols_seen, sample = _r6_sample_rows(slug, n=5)
    return render_template('r6_dataset.html',
                           r6_slug=slug, r6_title='Histogram: ' + slug + '.' + col,
                           r6_intro='10-bin histogram of ' + col + ' on ' + slug + '.',
                           r6_columns=cols, r6_rows=sample,
                           r6_rows_count=rows_count,
                           r6_snapshot=R6_SNAPSHOT_DATE,
                           r6_license=license_str,
                           r6_query_demo='Histogram[' + col + ']',
                           r6_query_result=None,
                           r6_default_col=col,
                           r6_chart_svg=svg)


# ---- R6 (5) Scatter visualization --------------------------------------
@app.route('/datasets/<slug>/viz/scatter')
def r6_dataset_viz_scatter(slug):
    spec = _R6_DATASETS.get(slug)
    if not spec:
        abort(404)
    rows_count, cols, license_str, description = spec
    x = (request.args.get('x', cols[0]) or cols[0]).strip()
    y = (request.args.get('y', cols[1] if len(cols) > 1 else cols[0])
         or cols[0]).strip()
    svg = _r6_chart_svg(slug, 'scatter', x=x, y=y)
    _r8_emit('r6.dataset.viz', 'curated-dataset-scatter',
             slug=slug, x=x, y=y)
    if request.args.get('format') == 'svg':
        return Response(svg, mimetype='image/svg+xml')
    if request.args.get('format') == 'json':
        return jsonify({'slug': slug, 'kind': 'scatter', 'x': x, 'y': y,
                        'snapshot_date': R6_SNAPSHOT_DATE,
                        'schema': 'wa-dataset-viz-scatter-v1',
                        'version': R6_VERSION})
    cols_seen, sample = _r6_sample_rows(slug, n=5)
    return render_template('r6_dataset.html',
                           r6_slug=slug,
                           r6_title='Scatter: ' + slug + '.' + x + ' vs ' + slug + '.' + y,
                           r6_intro='30-point scatter of ' + x + ' vs ' + y + ' on ' + slug + '.',
                           r6_columns=cols, r6_rows=sample,
                           r6_rows_count=rows_count,
                           r6_snapshot=R6_SNAPSHOT_DATE,
                           r6_license=license_str,
                           r6_query_demo='Scatter[' + x + ', ' + y + ']',
                           r6_query_result=None,
                           r6_default_col=y,
                           r6_chart_svg=svg)


# ---- R6 (6) Download dataset as CSV ------------------------------------
@app.route('/datasets/<slug>/download.csv')
def r6_dataset_download_csv(slug):
    spec = _R6_DATASETS.get(slug)
    if not spec:
        abort(404)
    rows_count, cols, license_str, description = spec
    sample_count = min(50, rows_count)
    cols_seen, sample = _r6_sample_rows(slug, n=sample_count)
    out = [','.join(cols)]
    for row in sample:
        out.append(','.join(str(c) for c in row))
    _r8_emit('r6.dataset.download', 'curated-dataset-csv-download',
             slug=slug, rows=sample_count)
    return Response('\n'.join(out) + '\n', mimetype='text/csv')


# ---- R6 (7) Data-drop upload sim ---------------------------------------
@app.route('/data-drop/upload', methods=['GET', 'POST'])
def r6_data_drop_upload():
    name = (request.values.get('name', 'my-dataset') or 'my-dataset').strip().lower()
    rows = request.values.get('rows', '100')
    try:
        rows_int = int(rows)
    except (TypeError, ValueError):
        rows_int = 100
    rows_int = max(1, min(1000000, rows_int))
    token = hashlib.md5(('data-drop|' + name + '|' + str(rows_int)).encode()).hexdigest()[:12]
    payload = {'name': name, 'rows': rows_int, 'drop_token': token,
               'public_url': '/datasets/drop-' + token,
               'snapshot_date': R6_SNAPSHOT_DATE,
               'schema': 'wa-data-drop-upload-v1', 'version': R6_VERSION}
    _r8_emit('r6.data_drop.upload', 'curated-dataset-data-drop-upload',
             name=name, rows=rows_int)
    if request.method == 'POST' or request.args.get('format') == 'json':
        return jsonify(payload)
    rows_kv = [(k, payload[k]) for k in sorted(payload) if k != 'schema']
    return render_template('r10/vertical.html',
        r10_slug='data-drop-upload', r10_title='Data Drop Upload',
        r10_intro='Simulated Wolfram Data Drop upload entry point.',
        r10_params=[('name', name), ('rows', rows_int)],
        r10_parsed_input='DataDrop[name=' + repr(name) + ', rows=' + str(rows_int) + ']',
        r10_plaintext=('Accepted ' + str(rows_int) + ' rows for ' + repr(name)
                       + '; drop token ' + token + ', public url '
                       + payload['public_url'] + '.'),
        r10_pod_title='Upload', r10_payload_rows=rows_kv,
        r10_schema=payload['schema'], r10_version=R6_VERSION,
        r10_related=['Dataset catalog', 'Dataset query',
                     'Histogram visualization', 'Dataset CSV download'],
        r10_topic_slug='curated-dataset-data-drop-upload')


# === R4-R5-R6 backfill END ===


# === R11 GUI deepen BEGIN — DB-backed, distinct templates per family ===
# Added 2026-05-27 (rev 2). 35 routes across 16 page families; each family has
# its own template under `templates/r11/`. Page constants live in
# `r11_*` SQLAlchemy tables (seeded by `_build_seed_r11.py`). All routes are
# new and do not shadow R4/R5/R6/R10 verticals. No new JSON/API routes were
# added (legacy `?format=json` support preserved on a subset). No DB writes
# at runtime; instance_seed/<site>.db md5 is rebuilt by the seed script.

R11_VERSION = 'r11'
R11_SNAPSHOT_DATE = '2026-05-27'


# ---------------------------------------------------------------------------
# R11 models
# ---------------------------------------------------------------------------
class R11ExampleSection(db.Model):
    __tablename__ = 'r11_example_sections'
    slug        = db.Column(db.String(80), primary_key=True)
    name        = db.Column(db.String(120), nullable=False)
    count       = db.Column(db.Integer)
    description = db.Column(db.Text)
    sort_order  = db.Column(db.Integer)


class R11Widget(db.Model):
    __tablename__ = 'r11_widgets'
    slug       = db.Column(db.String(80), primary_key=True)
    name       = db.Column(db.String(120), nullable=False)
    topic      = db.Column(db.String(60))
    installs   = db.Column(db.Integer)
    rating     = db.Column(db.Float)
    embed_size = db.Column(db.String(30))


class R11Notebook(db.Model):
    __tablename__ = 'r11_pub_notebooks'
    slug     = db.Column(db.String(120), primary_key=True)
    title    = db.Column(db.String(200), nullable=False)
    author   = db.Column(db.String(120))
    cells    = db.Column(db.Integer)
    abstract = db.Column(db.Text)
    license  = db.Column(db.String(40))
    language = db.Column(db.String(40))


class R11LanguageDoc(db.Model):
    __tablename__ = 'r11_lang_tutorials'
    slug       = db.Column(db.String(80), primary_key=True)
    title      = db.Column(db.String(160), nullable=False)
    abstract   = db.Column(db.Text)
    sort_order = db.Column(db.Integer)


class R11Courseware(db.Model):
    __tablename__ = 'r11_courses'
    slug     = db.Column(db.String(120), primary_key=True)
    name     = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(60))
    lessons  = db.Column(db.Integer)
    level    = db.Column(db.String(20))


class R11Certificate(db.Model):
    __tablename__ = 'r11_certificates'
    cert_id     = db.Column(db.String(40), primary_key=True)
    course_slug = db.Column(db.String(120))
    awarded_to  = db.Column(db.String(120))
    issued_date = db.Column(db.String(20))


class R11BlogCategory(db.Model):
    __tablename__ = 'r11_blog_categories'
    slug = db.Column(db.String(60), primary_key=True)
    name = db.Column(db.String(120), nullable=False)


class R11BlogPost(db.Model):
    __tablename__ = 'r11_blog_posts'
    slug          = db.Column(db.String(160), primary_key=True)
    title         = db.Column(db.String(300), nullable=False)
    author        = db.Column(db.String(120))
    date          = db.Column(db.String(20))
    category_slug = db.Column(db.String(60))
    abstract      = db.Column(db.Text)


class R11CommunityGroup(db.Model):
    __tablename__ = 'r11_community_groups'
    slug    = db.Column(db.String(60), primary_key=True)
    name    = db.Column(db.String(120), nullable=False)
    members = db.Column(db.Integer)


class R11CommunityTopic(db.Model):
    __tablename__ = 'r11_community_topics'
    tid        = db.Column(db.Integer, primary_key=True)
    title      = db.Column(db.String(240))
    group_slug = db.Column(db.String(60))
    replies    = db.Column(db.Integer)
    author     = db.Column(db.String(120))


class R11Job(db.Model):
    __tablename__ = 'r11_jobs'
    job_id     = db.Column(db.String(20), primary_key=True)
    title      = db.Column(db.String(200), nullable=False)
    department = db.Column(db.String(60))
    location   = db.Column(db.String(80))
    salary     = db.Column(db.String(40))


class R11StoreProduct(db.Model):
    __tablename__ = 'r11_store_products'
    slug        = db.Column(db.String(80), primary_key=True)
    name        = db.Column(db.String(200), nullable=False)
    category    = db.Column(db.String(40))
    price       = db.Column(db.Float)
    description = db.Column(db.Text)


class R11ResearchPaper(db.Model):
    __tablename__ = 'r11_research_papers'
    slug     = db.Column(db.String(120), primary_key=True)
    title    = db.Column(db.String(300), nullable=False)
    author   = db.Column(db.String(120))
    year     = db.Column(db.Integer)
    area     = db.Column(db.String(60))
    abstract = db.Column(db.Text)


class R11Conference(db.Model):
    __tablename__ = 'r11_conferences'
    slug      = db.Column(db.String(40), primary_key=True)
    name      = db.Column(db.String(200), nullable=False)
    year      = db.Column(db.Integer)
    location  = db.Column(db.String(80))
    attendees = db.Column(db.Integer)


class R11Demonstration(db.Model):
    __tablename__ = 'r11_demonstrations'
    did         = db.Column(db.Integer, primary_key=True)
    name        = db.Column(db.String(200), nullable=False)
    topic       = db.Column(db.String(60))
    description = db.Column(db.Text)


class R11MathWorldEntry(db.Model):
    __tablename__ = 'r11_mathworld_entries'
    slug  = db.Column(db.String(120), primary_key=True)
    name  = db.Column(db.String(200), nullable=False)
    topic = db.Column(db.String(60))
    body  = db.Column(db.Text)


# ---------------------------------------------------------------------------
# R11 helpers
# ---------------------------------------------------------------------------
def _r11_initials(name):
    parts = [p for p in (name or '').split() if p]
    if len(parts) >= 2:
        return (parts[0][0] + parts[-1][0]).upper()
    return (parts[0][:2] if parts else '?').upper()


def _r11_emit(slug, topic_slug=None, **kw):
    _r8_emit('r11.gui.opened', topic_slug or slug, slug=slug)


def _r11_meta(payload, slug, schema):
    """Return a dict suitable for ?format=json legacy compatibility."""
    out = dict(payload)
    out.update({'slug': slug, 'snapshot_date': R11_SNAPSHOT_DATE,
                'schema': schema, 'version': R11_VERSION})
    return out


# ---------------------------------------------------------------------------
# R11 (1) /examples — hub of topic tiles
# ---------------------------------------------------------------------------
@app.route('/examples')
def r11_examples_index():
    sections = (R11ExampleSection.query
                .order_by(R11ExampleSection.sort_order).all())
    _r11_emit('examples-index')
    if request.args.get('format') == 'json':
        return jsonify(_r11_meta(
            {'sections': [s.slug for s in sections],
             'count': len(sections)},
            'examples-index', 'wa-examples-index-v1'))
    return render_template('r11/examples_index.html',
        r11_title='WolframAlpha Examples',
        r11_intro='Browse expert-level example queries across mathematics, '
                  'science, society, everyday life, and Pro features.',
        r11_sections=[{'slug': s.slug, 'name': s.name,
                       'count': s.count, 'desc': s.description}
                      for s in sections],
        r11_schema='wa-examples-index-v1',
        r11_snapshot=R11_SNAPSHOT_DATE)


# ---------------------------------------------------------------------------
# R11 (2) /widgets/<slug> — single Wolfram Widget page w/ embed code
# ---------------------------------------------------------------------------
@app.route('/widgets/<slug>')
def r11_widgets_library(slug):
    slug = (slug or '').strip().lower()
    w = R11Widget.query.get(slug)
    if not w:
        abort(404)
    _r11_emit(slug, 'widget-' + slug)
    if request.args.get('format') == 'json':
        return jsonify(_r11_meta(
            {'name': w.name, 'topic': w.topic, 'installs': w.installs,
             'rating': w.rating, 'embed_size': w.embed_size,
             'public_url': '/widgets/' + slug},
            slug, 'wa-widgets-library-v1'))
    return render_template('r11/widget_detail.html',
        r11_widget={'slug': w.slug, 'name': w.name, 'topic': w.topic,
                    'installs': w.installs, 'rating': w.rating,
                    'embed_size': w.embed_size},
        r11_intro='Embeddable Wolfram Widget for ' + (w.topic or '')
                  + '. Installable on any HTML page.',
        r11_crumbs=[('Widgets', '/widget-gallery'), (w.name, None)],
        r11_schema='wa-widgets-library-v1')


# ---------------------------------------------------------------------------
# R11 (3) /widget-gallery — masonry grid of widgets w/ topic filter
# ---------------------------------------------------------------------------
@app.route('/widget-gallery')
def r11_widget_gallery():
    topic_q = (request.args.get('topic', '') or '').strip().lower()
    q = R11Widget.query
    if topic_q:
        q = q.filter(R11Widget.topic.ilike('%' + topic_q + '%'))
    widgets = q.order_by(R11Widget.installs.desc()).all()
    topics = sorted({w.topic for w in R11Widget.query.all() if w.topic})
    _r11_emit('widget-gallery')
    if request.args.get('format') == 'json':
        return jsonify(_r11_meta(
            {'count': len(widgets), 'topic_filter': topic_q or 'all'},
            'widget-gallery', 'wa-widget-gallery-v1'))
    return render_template('r11/widget_gallery.html',
        r11_intro='Browse ' + str(len(widgets))
                  + ' Wolfram Widgets across topics, sorted by installs.',
        r11_widgets=[{'slug': w.slug, 'name': w.name, 'topic': w.topic,
                      'installs': w.installs, 'rating': w.rating}
                     for w in widgets],
        r11_topics=topics, r11_topic_filter=topic_q or 'all',
        r11_schema='wa-widget-gallery-v1')


# ---------------------------------------------------------------------------
# R11 (4) /pub/notebook/<slug> — Mathematica notebook viewer style
# ---------------------------------------------------------------------------
def _r11_notebook_cells(nb):
    """Synthesize a deterministic list of In[]/Out[]/text cells for display."""
    cells = []
    n_in_out = max(2, min(6, (nb.cells or 4) // 3))
    samples = [
        ('Import["data.csv", "Dataset"]',
         'Dataset[<<' + str((nb.cells or 1) * 7) + '>>]'),
        ('Histogram[data["Population"], 20]',
         '<<Graphics3D[...]>>'),
        ('Module[{m = Mean[data]}, m]',
         str(round(((nb.cells or 1) * 11.3), 2))),
        ('ListLinePlot[Transpose[Values[data]]]',
         '<<LinePlot>>'),
        ('Classify[trainSet]',
         'ClassifierFunction[...]'),
        ('NetTrain[net, data, MaxIterations -> 8]',
         'NetTrainResultsObject[...]'),
    ]
    for i in range(n_in_out):
        sin, sout = samples[i % len(samples)]
        cells.append({'kind': 'in',  'label': 'In[' + str(i + 1) + ']:=',
                      'body': sin})
        cells.append({'kind': 'out', 'label': 'Out[' + str(i + 1) + ']=',
                      'body': sout})
    return cells


@app.route('/pub/notebook/<slug>')
def r11_pub_notebook(slug):
    slug = (slug or '').strip().lower()
    nb = R11Notebook.query.get(slug)
    if not nb:
        abort(404)
    _r11_emit(slug, 'pub-notebook-' + slug)
    if request.args.get('format') == 'json':
        return jsonify(_r11_meta(
            {'title': nb.title, 'author': nb.author, 'cells': nb.cells,
             'license': nb.license, 'language': nb.language},
            slug, 'wa-pub-notebook-v1'))
    return render_template('r11/notebook_pub.html',
        r11_nb={'slug': nb.slug, 'title': nb.title, 'author': nb.author,
                'cells': nb.cells, 'license': nb.license,
                'language': nb.language},
        r11_nb_cells=_r11_notebook_cells(nb),
        r11_intro=nb.abstract,
        r11_crumbs=[('Cloud', '/cloud'), ('Public notebooks', '/cloud'),
                    (nb.title, None)],
        r11_schema='wa-pub-notebook-v1')


# ---------------------------------------------------------------------------
# R11 (5-7) /cloud, /cloud/upload, /cloud/share
# ---------------------------------------------------------------------------
@app.route('/cloud')
def r11_cloud_home():
    nbs = R11Notebook.query.order_by(R11Notebook.slug).limit(8).all()
    payload = {'storage_gb_free': 5, 'compute_minutes_free': 200,
               'public_notebooks': R11Notebook.query.count()}
    _r11_emit('cloud', 'wolfram-cloud')
    if request.args.get('format') == 'json':
        return jsonify(_r11_meta(payload, 'cloud', 'wa-cloud-home-v1'))
    return render_template('r11/cloud_home.html',
        r11_cloud=payload,
        r11_cloud_files=[{'slug': nb.slug, 'title': nb.title,
                          'author': nb.author, 'cells': nb.cells}
                         for nb in nbs],
        r11_schema='wa-cloud-home-v1')


@app.route('/cloud/upload', methods=['GET', 'POST'])
def r11_cloud_upload():
    name = (request.values.get('name', 'my-notebook')
            or 'my-notebook').strip().lower()
    visibility = (request.values.get('visibility', 'private')
                  or 'private').strip().lower()
    if visibility not in ('private', 'public', 'shared'):
        visibility = 'private'
    token = hashlib.md5(
        ('cloud-upload|' + name + '|' + visibility).encode()).hexdigest()[:12]
    payload = {'name': name, 'visibility': visibility,
               'cloud_token': token,
               'public_url': '/pub/notebook/' + token}
    _r11_emit('cloud-upload', 'wolfram-cloud-upload')
    if request.args.get('format') == 'json':
        return jsonify(_r11_meta(payload, 'cloud-upload', 'wa-cloud-upload-v1'))
    return render_template('r11/cloud_upload.html',
        r11_upload=payload,
        r11_intro='Upload a notebook to Wolfram Cloud and choose its visibility.',
        r11_crumbs=[('Cloud', '/cloud'), ('Upload', None)],
        r11_schema='wa-cloud-upload-v1')


@app.route('/cloud/share', methods=['GET', 'POST'])
def r11_cloud_share():
    token = (request.values.get('token', '') or '').strip()
    audience = (request.values.get('audience', 'public')
                or 'public').strip().lower()
    if not token:
        token = hashlib.md5(
            ('cloud-share|' + audience).encode()).hexdigest()[:12]
    payload = {'token': token, 'audience': audience,
               'share_url': '/cloud/share/' + token}
    _r11_emit('cloud-share', 'wolfram-cloud-share')
    if request.args.get('format') == 'json':
        return jsonify(_r11_meta(payload, 'cloud-share', 'wa-cloud-share-v1'))
    return render_template('r11/cloud_share.html',
        r11_share=payload,
        r11_intro='Generate a shareable link for a Wolfram Cloud notebook.',
        r11_crumbs=[('Cloud', '/cloud'), ('Share', None)],
        r11_schema='wa-cloud-share-v1')


# ---------------------------------------------------------------------------
# R11 (8-10) /language, /language/getting-started, /language/tutorial/<slug>
# ---------------------------------------------------------------------------
def _r11_language_toc(active=None):
    rows = (R11LanguageDoc.query
            .order_by(R11LanguageDoc.sort_order).all())
    toc = [{'slug': 'language', 'title': 'Overview',
            'url': '/language'},
           {'slug': 'language-getting-started',
            'title': 'Getting started',
            'url': '/language/getting-started'}]
    for r in rows:
        toc.append({'slug': r.slug, 'title': r.title,
                    'url': '/language/tutorial/' + r.slug})
    return toc


@app.route('/language')
def r11_language_home():
    n = R11LanguageDoc.query.count()
    _r11_emit('language', 'wolfram-language')
    if request.args.get('format') == 'json':
        return jsonify(_r11_meta(
            {'tutorials': n, 'first_release_year': 1988,
             'core_paradigms': 'symbolic-functional-pattern-rewriting'},
            'language', 'wa-language-home-v1'))
    return render_template('r11/language_doc.html',
        r11_title='Wolfram Language',
        r11_intro='A symbolic, knowledge-based programming language powering '
                  'Mathematica and Wolfram|Alpha.',
        r11_overview='Wolfram Language is a knowledge-based, symbolic, '
                     'functional programming language with built-in '
                     'pattern matching, dynamic notebooks, and 6000+ '
                     'built-in functions. First released in 1988, it now '
                     'ships ' + str(n) + ' getting-started tutorials.',
        r11_example_in='Plot[Sin[x], {x, 0, 2 Pi}]',
        r11_example_out='Sin-curve plot rendered inline',
        r11_payload_rows=[('Tutorials', str(n)),
                          ('First release', '1988')],
        r11_toc=_r11_language_toc(), r11_active_slug='language',
        r11_next_slug='language-getting-started',
        r11_next_label='Getting started',
        r11_next_url='/language/getting-started',
        r11_crumbs=[('Wolfram Language', None)],
        r11_schema='wa-language-home-v1')


@app.route('/language/getting-started')
def r11_language_getting_started():
    _r11_emit('language-getting-started', 'wolfram-language-getting-started')
    if request.args.get('format') == 'json':
        return jsonify(_r11_meta(
            {'sections': 6,
             'sample_input': 'Plot[Sin[x], {x, 0, 2 Pi}]',
             'sample_output': 'Sin-curve plot rendered inline'},
            'language-getting-started', 'wa-language-getting-started-v1'))
    return render_template('r11/language_doc.html',
        r11_title='Getting Started with Wolfram Language',
        r11_intro='A 6-section walkthrough from first expression to first notebook.',
        r11_overview='Six sections: 1) install or use the Cloud, 2) first '
                     'input, 3) lists, 4) plotting, 5) patterns, '
                     '6) notebooks.',
        r11_example_in='2 + 2',
        r11_example_out='4',
        r11_payload_rows=[('Sections', '6')],
        r11_toc=_r11_language_toc(),
        r11_active_slug='language-getting-started',
        r11_next_slug='lists', r11_next_label='Tutorial: Lists',
        r11_next_url='/language/tutorial/lists',
        r11_crumbs=[('Wolfram Language', '/language'),
                    ('Getting started', None)],
        r11_schema='wa-language-getting-started-v1')


@app.route('/language/tutorial/<slug>')
def r11_language_tutorial(slug):
    slug = (slug or '').strip().lower()
    t = R11LanguageDoc.query.get(slug)
    if not t:
        abort(404)
    siblings = (R11LanguageDoc.query
                .order_by(R11LanguageDoc.sort_order).all())
    keys = [r.slug for r in siblings]
    next_slug = keys[(keys.index(slug) + 1) % len(keys)]
    next_title = next(r.title for r in siblings if r.slug == next_slug)
    _r11_emit(slug, 'wolfram-language-' + slug)
    if request.args.get('format') == 'json':
        return jsonify(_r11_meta(
            {'title': t.title, 'abstract': t.abstract,
             'sections': 4, 'next_slug': next_slug},
            slug, 'wa-language-tutorial-v1'))
    return render_template('r11/language_doc.html',
        r11_title='Tutorial: ' + t.title,
        r11_intro=t.abstract,
        r11_overview=t.title + ' is a Wolfram Language tutorial. '
                     + t.abstract + ' This tutorial is one of '
                     + str(len(keys)) + ' getting-started tutorials.',
        r11_example_in=t.title + '[]',
        r11_example_out=t.abstract,
        r11_payload_rows=[('Sections', '4'), ('Tutorial', t.title)],
        r11_toc=_r11_language_toc(), r11_active_slug=slug,
        r11_next_slug=next_slug,
        r11_next_label='Tutorial: ' + next_title,
        r11_next_url='/language/tutorial/' + next_slug,
        r11_crumbs=[('Wolfram Language', '/language'),
                    ('Tutorials', '/language/getting-started'),
                    (t.title, None)],
        r11_schema='wa-language-tutorial-v1')


# ---------------------------------------------------------------------------
# R11 (11-14) /courseware* — Wolfram-U
# ---------------------------------------------------------------------------
@app.route('/courseware')
def r11_courseware_index():
    courses = R11Courseware.query.order_by(R11Courseware.slug).all()
    cats = sorted({c.category for c in courses if c.category})
    _r11_emit('courseware', 'wolfram-u-catalog')
    if request.args.get('format') == 'json':
        return jsonify(_r11_meta(
            {'count': len(courses), 'categories': len(cats)},
            'courseware', 'wa-courseware-index-v1'))
    return render_template('r11/courseware_index.html',
        r11_intro='Browse ' + str(len(courses))
                  + ' interactive Wolfram U courses across '
                  + str(len(cats)) + ' categories.',
        r11_courses=[{'slug': c.slug, 'name': c.name,
                      'category': c.category, 'lessons': c.lessons,
                      'level': c.level} for c in courses],
        r11_categories=cats,
        r11_schema='wa-courseware-index-v1')


@app.route('/courseware/<course>')
def r11_courseware_detail(course):
    course = (course or '').strip().lower()
    c = R11Courseware.query.get(course)
    if not c:
        abort(404)
    _r11_emit(course, 'wolfram-u-' + course)
    if request.args.get('format') == 'json':
        return jsonify(_r11_meta(
            {'name': c.name, 'category': c.category,
             'lessons': c.lessons, 'level': c.level,
             'certificate_available': True},
            course, 'wa-courseware-detail-v1'))
    return render_template('r11/courseware_detail.html',
        r11_course={'slug': c.slug, 'name': c.name,
                    'category': c.category, 'lessons': c.lessons,
                    'level': c.level},
        r11_intro=c.name + ' is a ' + (c.level or '') + '-level '
                  + (c.category or '') + ' course with '
                  + str(c.lessons) + ' lessons; certificate available.',
        r11_crumbs=[('Wolfram U', '/courseware'), (c.name, None)],
        r11_schema='wa-courseware-detail-v1')


@app.route('/courseware/<course>/lesson/<int:n>')
def r11_courseware_lesson(course, n):
    course = (course or '').strip().lower()
    c = R11Courseware.query.get(course)
    if not c:
        abort(404)
    if n < 1 or n > (c.lessons or 0):
        abort(404)
    video_minutes = 9 + (n % 6)
    _r11_emit(course + '-lesson-' + str(n))
    if request.args.get('format') == 'json':
        return jsonify(_r11_meta(
            {'course': c.name, 'lesson_number': n,
             'lesson_title': c.name + ' -- Lesson ' + str(n),
             'video_minutes': video_minutes, 'has_exercise': True},
            course + '-lesson-' + str(n), 'wa-courseware-lesson-v1'))
    return render_template('r11/courseware_lesson.html',
        r11_lesson={'n': n, 'course_slug': c.slug,
                    'course_name': c.name, 'total_lessons': c.lessons,
                    'video_minutes': video_minutes},
        r11_intro='Lesson ' + str(n) + ' of ' + str(c.lessons) + ' in '
                  + c.name + ' (' + (c.category or '') + '). Includes a '
                  + str(video_minutes) + '-minute video, written notes, '
                  + 'and a hands-on exercise.',
        r11_crumbs=[('Wolfram U', '/courseware'),
                    (c.name, '/courseware/' + c.slug),
                    ('Lesson ' + str(n), None)],
        r11_schema='wa-courseware-lesson-v1')


@app.route('/courseware/certificate/<cid>')
def r11_courseware_certificate(cid):
    cid = (cid or '').strip()
    cert = R11Certificate.query.get(cid)
    if not cert:
        abort(404)
    course = R11Courseware.query.get(cert.course_slug or '')
    course_name = course.name if course else (cert.course_slug or '')
    _r11_emit('certificate-' + cid)
    if request.args.get('format') == 'json':
        return jsonify(_r11_meta(
            {'certificate_id': cid, 'course': course_name,
             'issued_date': cert.issued_date,
             'awarded_to': cert.awarded_to,
             'verification_url': '/courseware/certificate/' + cid},
            'certificate-' + cid, 'wa-courseware-certificate-v1'))
    return render_template('r11/courseware_certificate.html',
        r11_cert={'id': cid, 'course': course_name,
                  'issued_date': cert.issued_date,
                  'awarded_to': cert.awarded_to,
                  'verification_url': '/courseware/certificate/' + cid},
        r11_crumbs=[('Wolfram U', '/courseware'),
                    ('Certificate', None)],
        r11_schema='wa-courseware-certificate-v1')


# ---------------------------------------------------------------------------
# R11 (15-17) /blog, /blog/<post_slug>, /blog/category/<cat>
# ---------------------------------------------------------------------------
def _r11_cat_name(slug):
    c = R11BlogCategory.query.get(slug)
    return c.name if c else slug


@app.route('/blog')
def r11_blog_index():
    posts = (R11BlogPost.query
             .order_by(R11BlogPost.date.desc()).all())
    cats = R11BlogCategory.query.order_by(R11BlogCategory.slug).all()
    _r11_emit('blog', 'wolfram-blog')
    if request.args.get('format') == 'json':
        return jsonify(_r11_meta(
            {'count': len(posts), 'categories': len(cats),
             'latest_slug': posts[0].slug if posts else None},
            'blog', 'wa-blog-index-v1'))
    return render_template('r11/blog_index.html',
        r11_intro='Long-form essays and announcements from the Wolfram team.',
        r11_posts=[{'slug': p.slug, 'title': p.title,
                    'author': p.author, 'date': p.date,
                    'category_name': _r11_cat_name(p.category_slug),
                    'abstract': p.abstract} for p in posts],
        r11_categories=[{'slug': c.slug, 'name': c.name} for c in cats],
        r11_schema='wa-blog-index-v1')


@app.route('/blog/<post_slug>')
def r11_blog_post(post_slug):
    post_slug = (post_slug or '').strip().lower()
    p = R11BlogPost.query.get(post_slug)
    if not p:
        abort(404)
    _r11_emit(post_slug, 'blog-post-' + post_slug)
    cat_name = _r11_cat_name(p.category_slug)
    word_count = 1200 + (len(p.title or '') * 18)
    if request.args.get('format') == 'json':
        return jsonify(_r11_meta(
            {'title': p.title, 'author': p.author, 'date': p.date,
             'category': p.category_slug, 'word_count': word_count},
            post_slug, 'wa-blog-post-v1'))
    return render_template('r11/blog_post.html',
        r11_post={'slug': p.slug, 'title': p.title, 'author': p.author,
                  'date': p.date, 'category_slug': p.category_slug,
                  'category_name': cat_name,
                  'word_count': word_count,
                  'abstract': p.abstract},
        r11_intro=p.abstract,
        r11_schema='wa-blog-post-v1')


@app.route('/blog/category/<cat>')
def r11_blog_category(cat):
    cat = (cat or '').strip().lower()
    cat_row = R11BlogCategory.query.get(cat)
    if not cat_row:
        abort(404)
    posts = (R11BlogPost.query
             .filter_by(category_slug=cat)
             .order_by(R11BlogPost.date.desc()).all())
    _r11_emit('blog-cat-' + cat, 'blog-category-' + cat)
    if request.args.get('format') == 'json':
        return jsonify(_r11_meta(
            {'category': cat, 'category_name': cat_row.name,
             'count': len(posts)},
            'blog-cat-' + cat, 'wa-blog-category-v1'))
    def _split(date):
        # 'YYYY-MM-DD' -> ('YYYY', 'MM-DD')
        try:
            y, m, d = date.split('-')
            return y, m + '/' + d
        except Exception:
            return '', date
    cat_posts = []
    for p in posts:
        y, md = _split(p.date or '')
        cat_posts.append({'slug': p.slug, 'title': p.title,
                          'author': p.author, 'year': y,
                          'month_day': md, 'abstract': p.abstract})
    return render_template('r11/blog_category.html',
        r11_cat={'slug': cat, 'name': cat_row.name, 'count': len(posts)},
        r11_cat_posts=cat_posts,
        r11_crumbs=[('Blog', '/blog'), (cat_row.name, None)],
        r11_schema='wa-blog-category-v1')


# ---------------------------------------------------------------------------
# R11 (18-20) /community, /community/topic/<id>, /community/group/<group>
# ---------------------------------------------------------------------------
@app.route('/community')
def r11_community_home():
    groups = R11CommunityGroup.query.order_by(R11CommunityGroup.slug).all()
    topics = (R11CommunityTopic.query
              .order_by(R11CommunityTopic.replies.desc()).limit(8).all())
    payload = {'groups': len(groups),
               'topics_indexed': R11CommunityTopic.query.count(),
               'total_members': sum(g.members or 0 for g in groups)}
    _r11_emit('community', 'wolfram-community')
    if request.args.get('format') == 'json':
        return jsonify(_r11_meta(payload, 'community', 'wa-community-home-v1'))
    group_name = {g.slug: g.name for g in groups}
    return render_template('r11/community_home.html',
        r11_intro='Wolfram Community: discussions, projects, and Q&A '
                  'across Wolfram tech.',
        r11_community=payload,
        r11_groups=[{'slug': g.slug, 'name': g.name,
                     'members': g.members} for g in groups],
        r11_recent_topics=[
            {'tid': t.tid, 'title': t.title, 'replies': t.replies,
             'author': t.author,
             'group_name': group_name.get(t.group_slug, t.group_slug)}
            for t in topics],
        r11_schema='wa-community-home-v1')


@app.route('/community/topic/<int:tid>')
def r11_community_topic(tid):
    t = R11CommunityTopic.query.get(tid)
    if not t:
        abort(404)
    group = R11CommunityGroup.query.get(t.group_slug or '')
    group_name = group.name if group else (t.group_slug or '')
    _r11_emit('topic-' + str(tid))
    if request.args.get('format') == 'json':
        return jsonify(_r11_meta(
            {'topic_id': tid, 'title': t.title, 'group': t.group_slug,
             'replies': t.replies, 'author': t.author},
            'topic-' + str(tid), 'wa-community-topic-v1'))
    # Deterministic synthetic replies (depend only on tid + author)
    REPLIERS = ['Daniel Lichtblau', 'Vitaliy Kaurov',
                'Andre Kuzniarek', 'Roger Germundsson']
    replies = []
    n_show = min(4, max(2, (t.replies or 0) // 12))
    for i in range(n_show):
        replies.append({
            'who': REPLIERS[(tid + i) % len(REPLIERS)],
            'text': 'Reply ' + str(i + 1) + ' to thread #' + str(tid)
                    + ': interesting point on ' + (t.title or '') + '.'})
    return render_template('r11/community_topic.html',
        r11_topic={'tid': tid, 'title': t.title,
                   'group_slug': t.group_slug, 'group_name': group_name,
                   'replies': t.replies, 'author': t.author},
        r11_replies=replies,
        r11_intro='Wolfram Community thread #' + str(tid)
                  + ' opened in the ' + group_name + ' group.',
        r11_schema='wa-community-topic-v1')


@app.route('/community/group/<group>')
def r11_community_group(group):
    group = (group or '').strip().lower()
    g = R11CommunityGroup.query.get(group)
    if not g:
        abort(404)
    topics = (R11CommunityTopic.query
              .filter_by(group_slug=group)
              .order_by(R11CommunityTopic.replies.desc()).all())
    _r11_emit('group-' + group, 'community-group-' + group)
    if request.args.get('format') == 'json':
        return jsonify(_r11_meta(
            {'group': group, 'name': g.name, 'members': g.members,
             'indexed_topics': len(topics)},
            'group-' + group, 'wa-community-group-v1'))
    return render_template('r11/community_group.html',
        r11_group={'slug': g.slug, 'name': g.name,
                   'members': g.members, 'indexed_topics': len(topics)},
        r11_group_topics=[{'tid': t.tid, 'title': t.title,
                           'replies': t.replies, 'author': t.author}
                          for t in topics],
        r11_crumbs=[('Community', '/community'), (g.name, None)],
        r11_schema='wa-community-group-v1')


# ---------------------------------------------------------------------------
# R11 (21-23) /about/team, /about/history, /contact-us
# ---------------------------------------------------------------------------
_R11_TEAM = [
    ('Stephen Wolfram',   'Founder & CEO',                'sw@wolfram.com'),
    ('Theodore Gray',     'Co-founder',                   'tg@wolfram.com'),
    ('Roger Germundsson', 'Director of R&D',              'rg@wolfram.com'),
    ('Roman Maeder',      'Senior Research Mathematician','rm@wolfram.com'),
    ('Conrad Wolfram',    'Strategic Director',           'cw@wolfram.com'),
    ('Vitaliy Kaurov',    'Research Programmer',          'vk@wolfram.com'),
    ('Daniel Lichtblau',  'Senior Kernel Developer',      'dl@wolfram.com'),
]


@app.route('/about/team')
def r11_about_team():
    _r11_emit('about-team')
    payload = {'team_size': len(_R11_TEAM), 'lead': _R11_TEAM[0][0]}
    if request.args.get('format') == 'json':
        return jsonify(_r11_meta(payload, 'about-team', 'wa-about-team-v1'))
    return render_template('r11/about_team.html',
        r11_intro='Wolfram Research is a privately held company headquartered '
                  'in Champaign, IL. Below are members of the leadership and '
                  'core technical team.',
        r11_team=[{'name': n, 'role': r, 'email': e,
                   'initials': _r11_initials(n)}
                  for n, r, e in _R11_TEAM],
        r11_crumbs=[('About', '/about'), ('Team', None)],
        r11_schema='wa-about-team-v1')


_R11_TIMELINE = [
    (1988, 'Mathematica 1.0 released',
     'Wolfram Research ships Mathematica 1.0, introducing the Wolfram Language paradigm.'),
    (1996, 'MathWorld launched (Eric Weisstein)',
     'MathWorld becomes the web\'s most-cited mathematics encyclopedia.'),
    (1999, 'Mathematica 4.0',
     'Major release adding kernel performance and packed arrays.'),
    (2003, 'Wolfram Research opens UK office',
     'European operations established; growing international developer base.'),
    (2009, 'Wolfram|Alpha launches publicly',
     'A computational knowledge engine answering factual queries in natural language.'),
    (2014, 'Wolfram Language announced separately from Mathematica',
     'Wolfram Language becomes a first-class identity beyond Mathematica.'),
    (2016, 'Wolfram Cloud released',
     'Notebooks, deployments, and APIs run in a browser-accessible cloud.'),
    (2018, 'Mathematica 12.0 ships with neural-network framework',
     'Built-in NetTrain, NetChain, and a curated zoo of pretrained models.'),
    (2020, 'A Project to Find the Fundamental Theory of Physics launches',
     'Multiway systems and hypergraph rewriting as a model of physics.'),
    (2023, 'ChatGPT plugin and LLM-functions added to Wolfram Language',
     'Wolfram Language gains tools for tool-augmented LLMs.'),
]


@app.route('/about/history')
def r11_about_history():
    _r11_emit('about-history')
    payload = {'founded_year': _R11_TIMELINE[0][0],
               'milestones': len(_R11_TIMELINE),
               'latest_milestone_year': _R11_TIMELINE[-1][0]}
    if request.args.get('format') == 'json':
        return jsonify(_r11_meta(payload, 'about-history',
                                 'wa-about-history-v1'))
    return render_template('r11/about_history.html',
        r11_intro='Wolfram Research was founded in 1987. This timeline lists '
                  'major milestones through ' + str(_R11_TIMELINE[-1][0])
                  + '.',
        r11_timeline=[{'year': y, 'title': t, 'desc': d}
                      for y, t, d in _R11_TIMELINE],
        r11_crumbs=[('About', '/about'), ('History', None)],
        r11_schema='wa-about-history-v1')


@app.route('/contact-us')
def r11_contact_us():
    payload = {'support_email': 'info@wolframalpha.com',
               'sales_email':   'sales@wolfram.com',
               'phone_us':      '+1-217-398-0700',
               'address':       '100 Trade Center Drive, Champaign, IL 61820, USA',
               'response_sla_hours': 24}
    _r11_emit('contact-us')
    if request.args.get('format') == 'json':
        return jsonify(_r11_meta(payload, 'contact-us', 'wa-contact-us-v1'))
    return render_template('r11/contact.html',
        r11_intro='Contact Wolfram Research by email, phone, or postal mail.',
        r11_contact=payload,
        r11_crumbs=[('About', '/about'), ('Contact us', None)],
        r11_schema='wa-contact-us-v1')


# ---------------------------------------------------------------------------
# R11 (24-25) /jobs, /jobs/<id>
# ---------------------------------------------------------------------------
@app.route('/jobs')
def r11_jobs_index():
    dept_q = (request.args.get('dept', '') or '').strip().lower()
    q = R11Job.query
    if dept_q:
        q = q.filter(R11Job.department.ilike('%' + dept_q + '%'))
    jobs = q.order_by(R11Job.job_id).all()
    # Department counts (always over the full table for the sidebar)
    all_jobs = R11Job.query.all()
    dept_counts = {}
    for j in all_jobs:
        if j.department:
            dept_counts[j.department] = dept_counts.get(j.department, 0) + 1
    departments = [{'slug': k.lower(), 'name': k, 'count': v}
                   for k, v in sorted(dept_counts.items())]
    _r11_emit('jobs', 'wolfram-jobs')
    if request.args.get('format') == 'json':
        return jsonify(_r11_meta(
            {'open_positions': len(jobs),
             'departments': len(departments),
             'dept_filter': dept_q or 'all'},
            'jobs', 'wa-jobs-index-v1'))
    return render_template('r11/jobs_index.html',
        r11_intro='Open positions across Wolfram Research, Wolfram|Alpha, '
                  'and Wolfram-U.',
        r11_jobs=[{'id': j.job_id, 'title': j.title, 'dept': j.department,
                   'location': j.location, 'salary': j.salary}
                  for j in jobs],
        r11_departments=departments,
        r11_dept_filter=dept_q or 'all',
        r11_total_open=len(all_jobs),
        r11_schema='wa-jobs-index-v1')


@app.route('/jobs/<jid>')
def r11_jobs_detail(jid):
    jid = (jid or '').strip()
    j = R11Job.query.get(jid)
    if not j:
        abort(404)
    _r11_emit(jid, 'job-' + jid)
    if request.args.get('format') == 'json':
        return jsonify(_r11_meta(
            {'job_id': jid, 'title': j.title, 'department': j.department,
             'location': j.location, 'salary_band': j.salary,
             'apply_url': '/jobs/' + jid + '/apply'},
            jid, 'wa-jobs-detail-v1'))
    return render_template('r11/job_detail.html',
        r11_job={'id': j.job_id, 'title': j.title, 'dept': j.department,
                 'location': j.location, 'salary': j.salary,
                 'apply_url': '/jobs/' + jid + '/apply'},
        r11_intro='Wolfram Research is hiring a ' + (j.title or '')
                  + '. The role sits in the ' + (j.department or '')
                  + ' department, based in ' + (j.location or '')
                  + ', with a salary band of ' + (j.salary or '') + '.',
        r11_crumbs=[('Jobs', '/jobs'), (j.title, None)],
        r11_schema='wa-jobs-detail-v1')


# ---------------------------------------------------------------------------
# R11 (26-27) /store, /store/product/<pid>
# ---------------------------------------------------------------------------
@app.route('/store')
def r11_store_index():
    cat_q = (request.args.get('cat', '') or '').strip().lower()
    q = R11StoreProduct.query
    if cat_q:
        q = q.filter(R11StoreProduct.category.ilike('%' + cat_q + '%'))
    products = q.order_by(R11StoreProduct.slug).all()
    all_products = R11StoreProduct.query.all()
    categories = sorted({p.category for p in all_products if p.category})
    _r11_emit('store', 'wolfram-store')
    if request.args.get('format') == 'json':
        return jsonify(_r11_meta(
            {'products': len(products), 'categories': categories,
             'cat_filter': cat_q or 'all'},
            'store', 'wa-store-index-v1'))
    return render_template('r11/store_index.html',
        r11_intro='Wolfram software, subscriptions, credits, books, and apparel.',
        r11_products=[{'slug': p.slug, 'name': p.name,
                       'category': p.category, 'price': p.price}
                      for p in products],
        r11_categories=categories,
        r11_cat_filter=cat_q or 'all',
        r11_schema='wa-store-index-v1')


@app.route('/store/product/<pid>')
def r11_store_product(pid):
    pid = (pid or '').strip().lower()
    p = R11StoreProduct.query.get(pid)
    if not p:
        abort(404)
    _r11_emit(pid, 'store-' + pid)
    if request.args.get('format') == 'json':
        return jsonify(_r11_meta(
            {'product_id': pid, 'name': p.name, 'category': p.category,
             'price_usd': p.price, 'in_stock': True, 'ships_in_days': 2},
            pid, 'wa-store-product-v1'))
    return render_template('r11/store_product.html',
        r11_product={'slug': p.slug, 'name': p.name, 'category': p.category,
                     'price': p.price, 'ships_in_days': 2},
        r11_intro=p.description,
        r11_crumbs=[('Store', '/store'), (p.name, None)],
        r11_schema='wa-store-product-v1')


# ---------------------------------------------------------------------------
# R11 (28-29) /research, /research/<paper-slug>
# ---------------------------------------------------------------------------
@app.route('/research')
def r11_research_index():
    papers = (R11ResearchPaper.query
              .order_by(R11ResearchPaper.year.desc()).all())
    years_span = (str(min(p.year for p in papers)) + '-'
                  + str(max(p.year for p in papers))) if papers else ''
    _r11_emit('research', 'wolfram-research')
    if request.args.get('format') == 'json':
        return jsonify(_r11_meta(
            {'count': len(papers), 'years_span': years_span},
            'research', 'wa-research-index-v1'))
    return render_template('r11/research_index.html',
        r11_title='Wolfram Research -- Papers',
        r11_intro='A catalog of foundational and technical papers '
                  'authored at Wolfram Research.',
        r11_papers=[{'slug': p.slug, 'title': p.title, 'author': p.author,
                     'year': p.year, 'area': p.area, 'abstract': p.abstract}
                    for p in papers],
        r11_years_span=years_span,
        r11_schema='wa-research-index-v1')


@app.route('/research/<paper_slug>')
def r11_research_paper(paper_slug):
    paper_slug = (paper_slug or '').strip().lower()
    p = R11ResearchPaper.query.get(paper_slug)
    if not p:
        abort(404)
    pages = 18 + (len(p.title or '') % 12)
    _r11_emit(paper_slug, 'paper-' + paper_slug)
    if request.args.get('format') == 'json':
        return jsonify(_r11_meta(
            {'title': p.title, 'author': p.author, 'year': p.year,
             'area': p.area, 'pages': pages},
            paper_slug, 'wa-research-paper-v1'))
    return render_template('r11/research_paper.html',
        r11_paper={'slug': p.slug, 'title': p.title, 'author': p.author,
                   'year': p.year, 'area': p.area, 'pages': pages,
                   'abstract': p.abstract},
        r11_intro=p.abstract,
        r11_schema='wa-research-paper-v1')


# ---------------------------------------------------------------------------
# R11 (30-31) /conferences, /conferences/<slug>
# ---------------------------------------------------------------------------
@app.route('/conferences')
def r11_conferences_index():
    confs = (R11Conference.query
             .order_by(R11Conference.year.desc()).all())
    _r11_emit('conferences', 'wolfram-conferences')
    if request.args.get('format') == 'json':
        return jsonify(_r11_meta(
            {'count': len(confs),
             'latest_year': confs[0].year if confs else None},
            'conferences', 'wa-conferences-index-v1'))
    return render_template('r11/conferences_index.html',
        r11_intro='All editions of the Wolfram Technology Conference.',
        r11_conferences=[{'slug': c.slug, 'name': c.name, 'year': c.year,
                          'location': c.location,
                          'attendees': c.attendees} for c in confs],
        r11_schema='wa-conferences-index-v1')


@app.route('/conferences/<slug>')
def r11_conferences_detail(slug):
    slug = (slug or '').strip().lower()
    c = R11Conference.query.get(slug)
    if not c:
        abort(404)
    tracks = ['Machine Learning / LLMs', 'Modeling & Engineering',
              'Science & Math', 'Computational X', 'Education']
    _r11_emit(slug)
    if request.args.get('format') == 'json':
        return jsonify(_r11_meta(
            {'name': c.name, 'year': c.year, 'location': c.location,
             'attendees': c.attendees, 'tracks': tracks},
            slug, 'wa-conference-detail-v1'))
    return render_template('r11/conference_detail.html',
        r11_conf={'slug': c.slug, 'name': c.name, 'year': c.year,
                  'location': c.location, 'attendees': c.attendees},
        r11_tracks=tracks,
        r11_intro=c.name + ' was held in ' + (c.location or '')
                  + ' with approximately ' + str(c.attendees)
                  + ' attendees across 5 tracks.',
        r11_crumbs=[('Conferences', '/conferences'), (c.name, None)],
        r11_schema='wa-conference-detail-v1')


# ---------------------------------------------------------------------------
# R11 (32-33) /demonstrations, /demonstrations/<id>
# ---------------------------------------------------------------------------
@app.route('/demonstrations')
def r11_demos_index():
    demos = R11Demonstration.query.order_by(R11Demonstration.did).all()
    topics = sorted({d.topic for d in demos if d.topic})
    _r11_emit('demonstrations', 'wolfram-demonstrations')
    if request.args.get('format') == 'json':
        return jsonify(_r11_meta(
            {'count': len(demos), 'topics': topics},
            'demonstrations', 'wa-demonstrations-index-v1'))
    return render_template('r11/demonstrations_index.html',
        r11_intro='A library of interactive Wolfram Language demonstrations.',
        r11_demos=[{'did': d.did, 'name': d.name, 'topic': d.topic,
                    'desc': d.description} for d in demos],
        r11_schema='wa-demonstrations-index-v1')


@app.route('/demonstrations/<int:did>')
def r11_demos_detail(did):
    d = R11Demonstration.query.get(did)
    if not d:
        abort(404)
    cdf_size = 80 + (did % 64)
    views = 5000 + (did * 11) % 90000
    _r11_emit('demo-' + str(did))
    if request.args.get('format') == 'json':
        return jsonify(_r11_meta(
            {'id': did, 'name': d.name, 'topic': d.topic,
             'cdf_size_kb': cdf_size, 'views': views},
            'demo-' + str(did), 'wa-demonstrations-detail-v1'))
    return render_template('r11/demonstration_detail.html',
        r11_demo={'did': did, 'name': d.name, 'topic': d.topic,
                  'cdf_size_kb': cdf_size, 'views': views},
        r11_intro=d.description,
        r11_crumbs=[('Demonstrations', '/demonstrations'), (d.name, None)],
        r11_schema='wa-demonstrations-detail-v1')


# ---------------------------------------------------------------------------
# R11 (34-35) /mathworld, /mathworld/<entry>
# ---------------------------------------------------------------------------
@app.route('/mathworld')
def r11_mathworld_index():
    topic_q = (request.args.get('topic', '') or '').strip().lower()
    q = R11MathWorldEntry.query
    if topic_q:
        q = q.filter(R11MathWorldEntry.topic.ilike('%' + topic_q + '%'))
    entries = q.order_by(R11MathWorldEntry.slug).all()
    all_entries = R11MathWorldEntry.query.all()
    topics = sorted({e.topic for e in all_entries if e.topic})
    _r11_emit('mathworld')
    if request.args.get('format') == 'json':
        return jsonify(_r11_meta(
            {'count': len(entries), 'topic_filter': topic_q or 'all',
             'topics': topics},
            'mathworld', 'wa-mathworld-index-v1'))
    return render_template('r11/mathworld_index.html',
        r11_entries=[{'slug': e.slug, 'name': e.name, 'topic': e.topic}
                     for e in entries],
        r11_topics=topics, r11_topic_filter=topic_q or 'all',
        r11_schema='wa-mathworld-index-v1')


@app.route('/mathworld/<entry>')
def r11_mathworld_entry(entry):
    e = R11MathWorldEntry.query.get(entry)
    if not e:
        abort(404)
    word_count = 600 + (len(e.name or '') * 25)
    references  = 8 + (len(e.name or '') % 6)
    # Build a simple deterministic formula / examples / related blurb so the
    # page looks like a real MathWorld entry without inventing new fields.
    formula = (e.body or '')
    examples = ('Worked examples of ' + (e.name or '')
                + ' across canonical inputs, with computed outputs '
                + 'derived from the Wolfram Language.')
    related = ('Related: other ' + (e.topic or '')
               + ' entries (see MathWorld index).')
    _r11_emit('mathworld-' + entry)
    if request.args.get('format') == 'json':
        return jsonify(_r11_meta(
            {'entry': entry, 'name': e.name, 'topic': e.topic,
             'word_count': word_count, 'references': references},
            'mathworld-' + entry, 'wa-mathworld-entry-v1'))
    return render_template('r11/mathworld_entry.html',
        r11_entry={'slug': e.slug, 'name': e.name, 'topic': e.topic,
                   'formula': formula, 'examples': examples,
                   'related': related, 'word_count': word_count,
                   'references': references},
        r11_intro=e.body,
        r11_schema='wa-mathworld-entry-v1')


# === R11 GUI deepen END ===


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        seed_database()
        seed_benchmark_users()
    port = int(os.environ.get('PORT', 28853))
    app.run(host='0.0.0.0', port=port, debug=False)
