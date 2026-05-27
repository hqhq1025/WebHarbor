"""Eventbrite mirror — Flask app (WebHarbor).

A self-contained event-ticketing site cloning Eventbrite's UX:
- Discovery (home, city, category, search with facets, calendar view)
- Event detail (hero, agenda, speakers, organizer, FAQ, refund, related, map)
- Organizer profile (bio, upcoming/past events, follower count, follow)
- Multi-step checkout (select tickets -> attendee info -> payment -> confirmation)
- Account (profile, interests, following, saved, tickets/orders)
- Create-an-event flow (stub)
- ICS download, calendar grid, share, save
"""
import os, json, re, random, hashlib, math, secrets
from datetime import datetime, timedelta, date, time as dtime
from functools import wraps
from urllib.parse import urlencode

from flask import (Flask, render_template, request, redirect, url_for,
                   flash, jsonify, session, abort, g, Response, make_response,
                   send_from_directory)
from flask_sqlalchemy import SQLAlchemy
from flask_login import (LoginManager, UserMixin, login_user, logout_user,
                         login_required, current_user)
from flask_bcrypt import Bcrypt

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
os.makedirs(os.path.join(BASE_DIR, 'instance'), exist_ok=True)

app = Flask(__name__, instance_path=os.path.join(BASE_DIR, 'instance'))
app.config['SECRET_KEY'] = 'eventbrite-webharbor-dev-secret-2026'
app.config['SQLALCHEMY_DATABASE_URI'] = (
    f"sqlite:///{os.path.join(BASE_DIR, 'instance', 'eventbrite.db')}")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Sign in to continue.'

# ─── Constants ────────────────────────────────────────────────────────────────

CATEGORIES = [
    ('music',       'Music',                       '#F05537'),
    ('business',    'Business',                    '#3659E3'),
    ('food-drink',  'Food & Drink',                '#D14A1A'),
    ('arts',        'Performing & Visual Arts',    '#9D2BB8'),
    ('holiday',     'Holiday',                     '#16823D'),
    ('health',      'Health',                      '#2BAB85'),
    ('hobbies',     'Hobbies',                     '#7A4FCF'),
    ('family',      'Family & Education',          '#1F7AB8'),
    ('sports',      'Sports & Fitness',            '#E5A300'),
    ('travel',      'Travel & Outdoor',            '#0E7C66'),
    ('charity',     'Charity & Causes',            '#C92450'),
    ('spirituality','Spirituality',                '#6E59A0'),
    ('community',   'Community & Culture',         '#B86B1F'),
    ('fashion',     'Fashion',                     '#D81C7B'),
    ('film',        'Film & Media',                '#1F2A44'),
    ('home',        'Home & Lifestyle',            '#7D8A3D'),
    ('auto',        'Auto, Boat & Air',            '#444B59'),
    ('school',      'School Activities',           '#E36F1E'),
]
CAT_MAP = {s: (n, c) for (s, n, c) in CATEGORIES}

CITIES = [
    ('ny--new-york',          'New York',         'NY', 40.7128, -74.0060),
    ('ca--los-angeles',       'Los Angeles',      'CA', 34.0522, -118.2437),
    ('il--chicago',           'Chicago',          'IL', 41.8781, -87.6298),
    ('tx--houston',           'Houston',          'TX', 29.7604, -95.3698),
    ('tx--austin',            'Austin',           'TX', 30.2672, -97.7431),
    ('ca--san-francisco',     'San Francisco',    'CA', 37.7749, -122.4194),
    ('wa--seattle',           'Seattle',          'WA', 47.6062, -122.3321),
    ('co--denver',            'Denver',           'CO', 39.7392, -104.9903),
    ('ma--boston',            'Boston',           'MA', 42.3601, -71.0589),
    ('dc--washington',        'Washington',       'DC', 38.9072, -77.0369),
    ('ga--atlanta',           'Atlanta',          'GA', 33.7490, -84.3880),
    ('fl--miami',             'Miami',            'FL', 25.7617, -80.1918),
    ('pa--philadelphia',      'Philadelphia',     'PA', 39.9526, -75.1652),
    ('mn--minneapolis',       'Minneapolis',      'MN', 44.9778, -93.2650),
    ('or--portland',          'Portland',         'OR', 45.5152, -122.6784),
    ('az--phoenix',           'Phoenix',          'AZ', 33.4484, -112.0740),
    ('nv--las-vegas',         'Las Vegas',        'NV', 36.1699, -115.1398),
    ('ca--san-diego',         'San Diego',        'CA', 32.7157, -117.1611),
    ('tn--nashville',         'Nashville',        'TN', 36.1627, -86.7816),
    ('la--new-orleans',       'New Orleans',      'LA', 29.9511, -90.0715),
    ('mi--detroit',           'Detroit',          'MI', 42.3314, -83.0458),
    ('nc--raleigh',           'Raleigh',          'NC', 35.7796, -78.6382),
    ('md--baltimore',         'Baltimore',        'MD', 39.2904, -76.6122),
]
CITY_MAP = {s: (n, st, lat, lng) for (s, n, st, lat, lng) in CITIES}

REFUND_POLICIES = [
    ('strict',   'No refunds'),
    ('moderate', 'Refunds up to 7 days before event'),
    ('flexible', 'Refunds up to 1 day before event'),
    ('any',      'Refunds anytime up to 24 hours before'),
]

# ─── Models ───────────────────────────────────────────────────────────────────

class User(db.Model, UserMixin):
    __tablename__ = 'users'
    id            = db.Column(db.Integer, primary_key=True)
    email         = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    name          = db.Column(db.String(120), nullable=False)
    phone         = db.Column(db.String(40),  default='')
    city          = db.Column(db.String(80),  default='New York')
    interests     = db.Column(db.Text,        default='[]')  # JSON list of category slugs
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)

    saved   = db.relationship('SavedEvent',  backref='user', lazy=True, cascade='all, delete-orphan')
    follows = db.relationship('Follow',      backref='user', lazy=True, cascade='all, delete-orphan')
    orders  = db.relationship('Order',       backref='user', lazy=True, cascade='all, delete-orphan')

    def set_password(self, pw):
        self.password_hash = bcrypt.generate_password_hash(pw).decode('utf-8')
    def check_password(self, pw):
        return bcrypt.check_password_hash(self.password_hash, pw)
    def get_interests(self):
        try: return json.loads(self.interests or '[]')
        except Exception: return []


class Organizer(db.Model):
    __tablename__ = 'organizers'
    id             = db.Column(db.Integer, primary_key=True)
    slug           = db.Column(db.String(160), unique=True, nullable=False, index=True)
    name           = db.Column(db.String(200), nullable=False)
    bio            = db.Column(db.Text, default='')
    city_slug      = db.Column(db.String(60), default='ny--new-york', index=True)
    website        = db.Column(db.String(200), default='')
    contact_email  = db.Column(db.String(120), default='')
    follower_seed  = db.Column(db.Integer, default=0)  # baseline followers (the visible count = this + len(follows))
    avatar_color   = db.Column(db.String(20), default='#F05537')
    verified       = db.Column(db.Boolean, default=False)
    created_at     = db.Column(db.DateTime, default=datetime.utcnow)

    events  = db.relationship('Event',  backref='organizer', lazy=True)
    follows = db.relationship('Follow', backref='organizer', lazy=True, cascade='all, delete-orphan')

    def follower_count(self):
        return (self.follower_seed or 0) + len(self.follows)
    def past_count(self):
        return Event.query.filter_by(organizer_id=self.id).filter(Event.start_dt < datetime.utcnow()).count()
    def upcoming_count(self):
        return Event.query.filter_by(organizer_id=self.id).filter(Event.start_dt >= datetime.utcnow()).count()


class Event(db.Model):
    __tablename__ = 'events'
    id              = db.Column(db.Integer, primary_key=True)
    slug            = db.Column(db.String(220), unique=True, nullable=False, index=True)
    title           = db.Column(db.String(300), nullable=False)
    summary         = db.Column(db.String(400), default='')
    description     = db.Column(db.Text, default='')   # long body 300-700 words
    category_slug   = db.Column(db.String(40), index=True, default='music')
    subcategory     = db.Column(db.String(80), default='')
    tags            = db.Column(db.Text, default='[]')  # JSON list
    organizer_id    = db.Column(db.Integer, db.ForeignKey('organizers.id'), nullable=False)
    is_online       = db.Column(db.Boolean, default=False, index=True)
    city_slug       = db.Column(db.String(60), default='ny--new-york', index=True)
    venue_name      = db.Column(db.String(160), default='')
    venue_address   = db.Column(db.String(200), default='')
    online_url      = db.Column(db.String(240), default='')
    timezone        = db.Column(db.String(40), default='America/New_York')
    start_dt        = db.Column(db.DateTime, nullable=False, index=True)
    end_dt          = db.Column(db.DateTime, nullable=False)
    image_token     = db.Column(db.String(40), default='gradient-1')   # used to pick CSS gradient
    refund_policy   = db.Column(db.String(20), default='moderate')
    language        = db.Column(db.String(20), default='English')
    format          = db.Column(db.String(30), default='Class')  # Class, Conference, Festival, Networking, Party, Performance, Seminar, Tour
    age_restriction = db.Column(db.String(30), default='All ages')
    is_featured     = db.Column(db.Boolean, default=False)
    agenda_json     = db.Column(db.Text, default='[]')   # [{time,title,description}]
    speakers_json   = db.Column(db.Text, default='[]')   # [{name,title,bio}]
    faq_json        = db.Column(db.Text, default='[]')   # [{q,a}]

    tickets = db.relationship('TicketTier', backref='event', lazy=True, order_by='TicketTier.position', cascade='all, delete-orphan')
    saves   = db.relationship('SavedEvent', backref='event', lazy=True, cascade='all, delete-orphan')
    orders  = db.relationship('Order',      backref='event', lazy=True)

    def get_tags(self):
        try: return json.loads(self.tags or '[]')
        except Exception: return []
    def get_agenda(self):
        try: return json.loads(self.agenda_json or '[]')
        except Exception: return []
    def get_speakers(self):
        try: return json.loads(self.speakers_json or '[]')
        except Exception: return []
    def get_faq(self):
        try: return json.loads(self.faq_json or '[]')
        except Exception: return []
    def min_price(self):
        prices = [t.price for t in self.tickets if t.price > 0]
        return min(prices) if prices else 0.0
    def max_price(self):
        prices = [t.price for t in self.tickets]
        return max(prices) if prices else 0.0
    def is_free(self):
        return all(t.price == 0 for t in self.tickets) if self.tickets else False
    def is_sold_out(self):
        return all(t.is_sold_out() for t in self.tickets) if self.tickets else False
    def total_capacity(self):
        return sum(t.capacity for t in self.tickets)
    def total_sold(self):
        return sum(t.sold for t in self.tickets)
    def category_name(self):
        return CAT_MAP.get(self.category_slug, ('Music', '#F05537'))[0]
    def category_color(self):
        return CAT_MAP.get(self.category_slug, ('Music', '#F05537'))[1]
    def city_name(self):
        if self.is_online: return 'Online'
        return CITY_MAP.get(self.city_slug, ('New York','NY',0,0))[0]
    def starts_in_window(self, start_d, end_d):
        return start_d <= self.start_dt.date() <= end_d


class TicketTier(db.Model):
    __tablename__ = 'ticket_tiers'
    id            = db.Column(db.Integer, primary_key=True)
    event_id      = db.Column(db.Integer, db.ForeignKey('events.id'), nullable=False, index=True)
    name          = db.Column(db.String(80), nullable=False)  # General Admission, VIP, Early Bird...
    price         = db.Column(db.Float, default=0.0)
    capacity      = db.Column(db.Integer, default=100)
    sold          = db.Column(db.Integer, default=0)
    position      = db.Column(db.Integer, default=0)
    description   = db.Column(db.String(240), default='')
    sale_start    = db.Column(db.DateTime, default=datetime.utcnow)
    sale_end      = db.Column(db.DateTime, default=datetime.utcnow)
    min_per_order = db.Column(db.Integer, default=1)
    max_per_order = db.Column(db.Integer, default=10)

    def remaining(self):
        return max(0, self.capacity - self.sold)
    def is_sold_out(self):
        return self.remaining() <= 0
    def price_str(self):
        return 'Free' if self.price == 0 else f'${self.price:,.2f}'


class SavedEvent(db.Model):
    __tablename__ = 'saved_events'
    id        = db.Column(db.Integer, primary_key=True)
    user_id   = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    event_id  = db.Column(db.Integer, db.ForeignKey('events.id'), nullable=False)
    saved_at  = db.Column(db.DateTime, default=datetime.utcnow)
    __table_args__ = (db.UniqueConstraint('user_id', 'event_id', name='uq_save'),)


class Follow(db.Model):
    __tablename__ = 'follows'
    id            = db.Column(db.Integer, primary_key=True)
    user_id       = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    organizer_id  = db.Column(db.Integer, db.ForeignKey('organizers.id'), nullable=False)
    followed_at   = db.Column(db.DateTime, default=datetime.utcnow)
    __table_args__ = (db.UniqueConstraint('user_id', 'organizer_id', name='uq_follow'),)


class Order(db.Model):
    __tablename__ = 'orders'
    id            = db.Column(db.Integer, primary_key=True)
    code          = db.Column(db.String(16), unique=True, nullable=False, index=True)
    user_id       = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    event_id      = db.Column(db.Integer, db.ForeignKey('events.id'), nullable=False)
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)
    total         = db.Column(db.Float, default=0.0)
    status        = db.Column(db.String(20), default='confirmed')  # confirmed|cancelled
    contact_email = db.Column(db.String(120), default='')
    contact_name  = db.Column(db.String(120), default='')
    contact_phone = db.Column(db.String(40),  default='')
    notes         = db.Column(db.Text, default='')  # Q&A answers JSON

    items   = db.relationship('OrderItem',     backref='order', lazy=True, cascade='all, delete-orphan')
    tickets = db.relationship('IssuedTicket', backref='order', lazy=True, cascade='all, delete-orphan')


class OrderItem(db.Model):
    __tablename__ = 'order_items'
    id        = db.Column(db.Integer, primary_key=True)
    order_id  = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False)
    tier_id   = db.Column(db.Integer, db.ForeignKey('ticket_tiers.id'), nullable=False)
    qty       = db.Column(db.Integer, default=1)
    unit_price = db.Column(db.Float, default=0.0)
    tier      = db.relationship('TicketTier')


class IssuedTicket(db.Model):
    __tablename__ = 'issued_tickets'
    id            = db.Column(db.Integer, primary_key=True)
    order_id      = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False)
    tier_id       = db.Column(db.Integer, db.ForeignKey('ticket_tiers.id'), nullable=False)
    code          = db.Column(db.String(20), unique=True, nullable=False)
    attendee_name = db.Column(db.String(120), default='')
    attendee_email = db.Column(db.String(120), default='')
    tier          = db.relationship('TicketTier')


class Review(db.Model):
    __tablename__ = 'reviews'
    id        = db.Column(db.Integer, primary_key=True)
    user_id   = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    event_id  = db.Column(db.Integer, db.ForeignKey('events.id'), nullable=False)
    rating    = db.Column(db.Integer, default=5)
    body      = db.Column(db.Text, default='')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class HelpArticle(db.Model):
    __tablename__ = 'help_articles'
    id    = db.Column(db.Integer, primary_key=True)
    slug  = db.Column(db.String(120), unique=True, nullable=False)
    title = db.Column(db.String(200), nullable=False)
    section = db.Column(db.String(80), default='Attending an event')
    body  = db.Column(db.Text, default='')


class NewsletterSignup(db.Model):
    __tablename__ = 'newsletter'
    id    = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class DraftEvent(db.Model):
    """Create-an-event draft (stub for the create flow)."""
    __tablename__ = 'draft_events'
    id          = db.Column(db.Integer, primary_key=True)
    user_id     = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    title       = db.Column(db.String(300), default='')
    summary     = db.Column(db.String(400), default='')
    category_slug = db.Column(db.String(40), default='music')
    city_slug   = db.Column(db.String(60), default='ny--new-york')
    is_online   = db.Column(db.Boolean, default=False)
    venue_name  = db.Column(db.String(160), default='')
    start_dt    = db.Column(db.DateTime, nullable=True)
    end_dt      = db.Column(db.DateTime, nullable=True)
    description = db.Column(db.Text, default='')
    tickets_json = db.Column(db.Text, default='[]')
    step        = db.Column(db.Integer, default=1)   # 1=basics 2=details 3=tickets 4=publish
    updated_at  = db.Column(db.DateTime, default=datetime.utcnow)


@login_manager.user_loader
def load_user(uid):
    return User.query.get(int(uid))


# ─── Utilities ────────────────────────────────────────────────────────────────

def slugify(s, maxlen=120):
    s = re.sub(r'[^a-zA-Z0-9\s-]', '', s or '').strip().lower()
    s = re.sub(r'\s+', '-', s)
    return s[:maxlen] or 'event'


def short_code(n=10):
    return secrets.token_urlsafe(n)[:n].upper().replace('_','A').replace('-','B')


def fmt_dt(dt):
    if not dt: return ''
    return dt.strftime('%a, %b %-d') + ' · ' + dt.strftime('%-I:%M %p')


def fmt_dt_short(dt):
    if not dt: return ''
    return dt.strftime('%a, %b %-d, %Y')


def fmt_time(dt):
    if not dt: return ''
    return dt.strftime('%-I:%M %p')


def parse_iso_date(s, default=None):
    if not s: return default
    try:
        return datetime.strptime(s, '%Y-%m-%d').date()
    except Exception:
        return default


# Token-overlap scoring (NOT strict AND) per WebHarbor norms.
STOPWORDS = {'the','a','an','of','in','on','at','to','for','with','and','or',
             'is','are','be','by','from','that','this','it','as','about','how',
             'what','which','when','where','event','events','class','classes',
             'tickets','ticket','free'}

def tokenize(s):
    return [t for t in re.findall(r"[a-z0-9]+", (s or '').lower()) if t not in STOPWORDS and len(t) > 1]


def score_event(ev, tokens):
    if not tokens: return 0.0
    hay = ' '.join([
        ev.title or '', ev.summary or '', ev.description or '',
        ev.venue_name or '', ev.subcategory or '', ev.tags or '',
        ev.organizer.name if ev.organizer else '',
        ev.category_name(),
    ]).lower()
    score = 0.0
    for t in tokens:
        if t in hay:
            score += 1.0
            # Title bonus
            if t in (ev.title or '').lower():
                score += 1.5
    return score


# ─── Image / styling helpers (CSS-driven, no real images) ─────────────────────

EVENT_GRADIENTS = [
    'linear-gradient(135deg,#F05537,#FFB169)',
    'linear-gradient(135deg,#3659E3,#9CB5FF)',
    'linear-gradient(135deg,#9D2BB8,#E294FF)',
    'linear-gradient(135deg,#16823D,#7BDA8A)',
    'linear-gradient(135deg,#D14A1A,#FFB169)',
    'linear-gradient(135deg,#1F2A44,#586784)',
    'linear-gradient(135deg,#0E7C66,#5BC4A7)',
    'linear-gradient(135deg,#C92450,#FF7A9C)',
    'linear-gradient(135deg,#E5A300,#FFD86B)',
    'linear-gradient(135deg,#6E59A0,#B2A0E3)',
    'linear-gradient(135deg,#1F7AB8,#7BC8FF)',
    'linear-gradient(135deg,#B86B1F,#FFC57E)',
    'linear-gradient(135deg,#D81C7B,#FF85C8)',
    'linear-gradient(135deg,#7D8A3D,#C8D38F)',
    'linear-gradient(135deg,#444B59,#8C95A6)',
    'linear-gradient(135deg,#7A4FCF,#C5A8FF)',
]

def event_gradient(ev):
    try: idx = int((ev.image_token or 'gradient-1').split('-')[-1]) % len(EVENT_GRADIENTS)
    except Exception: idx = 0
    return EVENT_GRADIENTS[idx]


def organizer_gradient(o):
    h = int(hashlib.md5((o.slug or 'x').encode()).hexdigest()[:6], 16)
    return EVENT_GRADIENTS[h % len(EVENT_GRADIENTS)]


# ─── Context processors ──────────────────────────────────────────────────────

@app.context_processor
def inject_globals():
    return dict(
        categories=CATEGORIES,
        cities=CITIES,
        cat_map=CAT_MAP,
        city_map=CITY_MAP,
        fmt_dt=fmt_dt, fmt_dt_short=fmt_dt_short, fmt_time=fmt_time,
        event_gradient=event_gradient,
        organizer_gradient=organizer_gradient,
        now=datetime.utcnow(),
    )


# Import the rest of the routes / seed code from sibling modules to keep
# this file readable. They are loaded with `exec` to preserve a single
# Flask app object (mirror sites are required to be self-contained — no
# cross-site imports — but inside a site we can split into local files).
def _load_module(rel):
    p = os.path.join(BASE_DIR, rel)
    with open(p) as f:
        code = compile(f.read(), p, 'exec')
    exec(code, globals())


_load_module('routes.py')
_load_module('seed_data.py')
_load_module('routes_more.py')


with app.app_context():
    db.create_all()
    seed_database()
    seed_benchmark_users()
    seed_extra()


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)


# --- perf: long-term cache for /static/ assets (added 2026-05-27) ---
@app.after_request
def _add_static_cache_headers(resp):
    try:
        if request.path.startswith('/static/'):
            resp.headers['Cache-Control'] = 'public, max-age=86400, immutable'
    except Exception:
        pass
    return resp
# --- end perf ---

