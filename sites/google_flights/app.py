"""
Google Flights mirror — Flask application.

Data model adapted for flight booking:
  - Airport/City = taxonomy (from -> to)
  - Flight = entity (route, airline, price, dates, stops)
  - Cart/Bag -> "Trip Cart" (selected flights pending checkout)
  - Order -> Booking (confirmed flight purchase with PNR)
  - Wishlist -> "Tracked Flights" (price tracking)
  - Review -> Flight Review (rating + comment after flight)
  - Plus: PriceAlert (notify when price drops), SavedSearch (flexible explore)
"""
import os
import json
import random
import string
from datetime import datetime, date, timedelta
from pathlib import Path

from flask import (Flask, render_template, request, redirect, url_for,
                   flash, jsonify, session, abort)
from flask_sqlalchemy import SQLAlchemy
from flask_login import (LoginManager, UserMixin, login_user, logout_user,
                         current_user, login_required)
from flask_wtf import CSRFProtect
from flask_bcrypt import Bcrypt
from sqlalchemy import or_, and_
from werkzeug.exceptions import HTTPException

BASE_DIR = Path(__file__).parent

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'google-flights-dev-secret-key-change-me')
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{BASE_DIR}/instance/google_flights.db"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['WTF_CSRF_TIME_LIMIT'] = None

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please sign in to continue.'
csrf = CSRFProtect(app)


# ============================================================
# MODELS
# ============================================================

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(200), nullable=False)
    first_name = db.Column(db.String(60), default='')
    last_name = db.Column(db.String(60), default='')
    phone = db.Column(db.String(30), default='')
    address = db.Column(db.String(200), default='')
    city = db.Column(db.String(60), default='')
    country = db.Column(db.String(60), default='')
    passport_number = db.Column(db.String(30), default='')
    frequent_flyer = db.Column(db.String(30), default='')
    date_of_birth = db.Column(db.Date)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    cart_items = db.relationship('CartItem', backref='user', lazy='dynamic',
                                 cascade='all, delete-orphan')
    bookings = db.relationship('Booking', backref='user', lazy='dynamic',
                               cascade='all, delete-orphan')
    tracked = db.relationship('TrackedFlight', backref='user', lazy='dynamic',
                              cascade='all, delete-orphan')
    reviews = db.relationship('Review', backref='user', lazy='dynamic',
                              cascade='all, delete-orphan')
    alerts = db.relationship('PriceAlert', backref='user', lazy='dynamic',
                             cascade='all, delete-orphan')
    saved_searches = db.relationship('SavedSearch', backref='user', lazy='dynamic',
                                     cascade='all, delete-orphan')
    payment_methods = db.relationship('PaymentMethod', backref='user', lazy='dynamic',
                                      cascade='all, delete-orphan')

    @property
    def full_name(self):
        n = f"{self.first_name} {self.last_name}".strip()
        return n or self.email.split('@')[0]


class Airport(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    iata = db.Column(db.String(4), unique=True, nullable=False, index=True)
    icao = db.Column(db.String(8), default='', index=True)        # 4-letter ICAO code
    city_slug = db.Column(db.String(60), index=True)
    city = db.Column(db.String(80), nullable=False)
    country = db.Column(db.String(80), nullable=False)
    name = db.Column(db.String(120), default='')  # Full airport name
    region = db.Column(db.String(40), default='')
    is_popular = db.Column(db.Boolean, default=False)
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    timezone = db.Column(db.String(64), default='')  # tz database name e.g. America/New_York
    image = db.Column(db.String(300), default='')
    gallery_json = db.Column(db.Text, default='[]')
    description = db.Column(db.Text, default='')

    def get_gallery(self):
        try:
            return json.loads(self.gallery_json) if self.gallery_json else []
        except Exception:
            return []


class Flight(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    flight_number = db.Column(db.String(10), nullable=False, index=True)
    airline = db.Column(db.String(80), nullable=False)
    airline_code = db.Column(db.String(4), default='')
    airline_logo = db.Column(db.String(200), default='')

    origin_id = db.Column(db.Integer, db.ForeignKey('airport.id'), nullable=False)
    destination_id = db.Column(db.Integer, db.ForeignKey('airport.id'), nullable=False)

    departure_date = db.Column(db.Date, nullable=False)
    departure_time = db.Column(db.String(8), default='08:00')  # HH:MM
    arrival_date = db.Column(db.Date, nullable=False)
    arrival_time = db.Column(db.String(8), default='12:00')
    duration_minutes = db.Column(db.Integer, default=180)

    stops = db.Column(db.Integer, default=0)
    stop_cities = db.Column(db.String(200), default='')  # comma-separated IATA codes

    aircraft = db.Column(db.String(60), default='Boeing 737')
    cabin_class = db.Column(db.String(20), default='Economy')
    price = db.Column(db.Float, nullable=False)  # base economy
    price_premium = db.Column(db.Float, default=0.0)
    price_business = db.Column(db.Float, default=0.0)
    price_first = db.Column(db.Float, default=0.0)

    co2_emissions_kg = db.Column(db.Integer, default=200)
    co2_vs_typical = db.Column(db.Integer, default=0)  # % diff vs typical

    baggage_free = db.Column(db.Integer, default=1)  # free checked bags
    baggage_included = db.Column(db.Boolean, default=True)
    return_date = db.Column(db.Date)  # used when row represents a round-trip leg pairing
    legroom_inches = db.Column(db.Integer, default=31)
    wifi = db.Column(db.Boolean, default=True)
    power = db.Column(db.Boolean, default=True)
    entertainment = db.Column(db.Boolean, default=True)
    meal_service = db.Column(db.String(120), default='')     # e.g. "Full meal service", "Snack box"
    seat_type = db.Column(db.String(80), default='')         # e.g. "Lie-flat seat", "Recliner", "Standard"
    seat_pitch = db.Column(db.String(40), default='')        # e.g. "78 in", "32 in"

    rating = db.Column(db.Float, default=4.2)
    is_best = db.Column(db.Boolean, default=False)  # top recommendation
    is_cheapest = db.Column(db.Boolean, default=False)
    is_fastest = db.Column(db.Boolean, default=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    origin = db.relationship('Airport', foreign_keys=[origin_id])
    destination = db.relationship('Airport', foreign_keys=[destination_id])

    @property
    def duration_str(self):
        h = self.duration_minutes // 60
        m = self.duration_minutes % 60
        return f"{h}h {m}m" if m else f"{h}h"

    @property
    def stops_str(self):
        if self.stops == 0:
            return "Nonstop"
        elif self.stops == 1:
            return "1 stop"
        return f"{self.stops} stops"

    @property
    def route_label(self):
        return f"{self.origin.iata} - {self.destination.iata}"


class CartItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    flight_id = db.Column(db.Integer, db.ForeignKey('flight.id'), nullable=False)
    return_flight_id = db.Column(db.Integer, db.ForeignKey('flight.id'))
    passengers = db.Column(db.Integer, default=1)
    cabin_class = db.Column(db.String(20), default='Economy')
    added_at = db.Column(db.DateTime, default=datetime.utcnow)

    flight = db.relationship('Flight', foreign_keys=[flight_id])
    return_flight = db.relationship('Flight', foreign_keys=[return_flight_id])

    @property
    def line_total(self):
        base = self.flight.price if self.flight else 0
        if self.return_flight:
            base += self.return_flight.price
        return round(base * self.passengers, 2)


class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    pnr = db.Column(db.String(10), unique=True, nullable=False, index=True)
    status = db.Column(db.String(20), default='confirmed')  # confirmed, ticketed, flown, cancelled
    trip_type = db.Column(db.String(20), default='one-way')

    total_amount = db.Column(db.Float, default=0.0)
    taxes_fees = db.Column(db.Float, default=0.0)
    currency = db.Column(db.String(4), default='USD')

    passenger_names_json = db.Column(db.Text, default='[]')
    contact_email = db.Column(db.String(120), default='')
    contact_phone = db.Column(db.String(30), default='')

    payment_last4 = db.Column(db.String(4), default='')
    payment_brand = db.Column(db.String(20), default='Visa')

    booked_at = db.Column(db.DateTime, default=datetime.utcnow)
    cancelled_at = db.Column(db.DateTime)

    items = db.relationship('BookingItem', backref='booking', lazy='dynamic',
                            cascade='all, delete-orphan')

    def get_passengers(self):
        try:
            return json.loads(self.passenger_names_json) if self.passenger_names_json else []
        except Exception:
            return []

    @property
    def item_count(self):
        return self.items.count()


class BookingItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    booking_id = db.Column(db.Integer, db.ForeignKey('booking.id'), nullable=False)
    flight_id = db.Column(db.Integer, db.ForeignKey('flight.id'), nullable=False)
    leg = db.Column(db.String(12), default='outbound')  # outbound, return
    passengers = db.Column(db.Integer, default=1)
    cabin_class = db.Column(db.String(20), default='Economy')
    seat = db.Column(db.String(8), default='')
    price = db.Column(db.Float, default=0.0)

    flight = db.relationship('Flight')


class TrackedFlight(db.Model):
    """Price-tracking wishlist item."""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    flight_id = db.Column(db.Integer, db.ForeignKey('flight.id'), nullable=False)
    target_price = db.Column(db.Float, default=0.0)
    starting_price = db.Column(db.Float, default=0.0)
    added_at = db.Column(db.DateTime, default=datetime.utcnow)

    flight = db.relationship('Flight')


class PriceAlert(db.Model):
    """Email alert for a route price drop."""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    origin_iata = db.Column(db.String(4), nullable=False)
    destination_iata = db.Column(db.String(4), nullable=False)
    threshold_price = db.Column(db.Float, default=0.0)
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class SavedSearch(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    label = db.Column(db.String(120), default='')
    origin_iata = db.Column(db.String(4), default='')
    destination_iata = db.Column(db.String(4), default='')
    departure_date = db.Column(db.Date)
    return_date = db.Column(db.Date)
    passengers = db.Column(db.Integer, default=1)
    cabin_class = db.Column(db.String(20), default='Economy')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Review(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    flight_id = db.Column(db.Integer, db.ForeignKey('flight.id'), nullable=False)
    rating = db.Column(db.Integer, default=5)  # 1-5
    title = db.Column(db.String(200), default='')
    body = db.Column(db.Text, default='')
    punctuality = db.Column(db.Integer, default=5)
    comfort = db.Column(db.Integer, default=5)
    service = db.Column(db.Integer, default=5)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    flight = db.relationship('Flight')


class PaymentMethod(db.Model):
    __tablename__ = 'payment_methods'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    card_type = db.Column(db.String(20), nullable=False)  # Visa, Mastercard, Amex
    last4 = db.Column(db.String(4), nullable=False)
    exp_month = db.Column(db.Integer, nullable=False)
    exp_year = db.Column(db.Integer, nullable=False)
    cardholder_name = db.Column(db.String(120), default='')
    is_default = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    @property
    def display(self):
        return f"{self.card_type} ending {self.last4} (exp {self.exp_month:02d}/{self.exp_year})"


# ============================================================
# LOGIN + HELPERS
# ============================================================

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


def make_pnr():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))


@app.context_processor
def inject_globals():
    cart_count = 0
    if current_user.is_authenticated:
        cart_count = current_user.cart_items.count()
    from flask_wtf.csrf import generate_csrf
    return {
        'cart_count': cart_count,
        'now': datetime.utcnow(),
        'current_year': datetime.utcnow().year,
        'csrf_token_value': generate_csrf(),
    }


@app.template_filter('money')
def money(value):
    try:
        return f"${value:,.0f}" if value == int(value) else f"${value:,.2f}"
    except Exception:
        return f"${value}"


@app.template_filter('datefmt')
def datefmt(value, fmt='%b %d, %Y'):
    if not value:
        return ''
    if isinstance(value, str):
        try:
            value = datetime.strptime(value, '%Y-%m-%d').date()
        except Exception:
            return value
    return value.strftime(fmt)


@app.context_processor
def _inject_airport_groups():
    """Surface multi-airport cities (New York → JFK/LGA/EWR, London → LHR/LGW,
    Tokyo → HND/NRT, …) as their own datalist entries so users can search by
    city name without picking one specific airport."""
    from collections import defaultdict
    by_city = defaultdict(list)
    for a in Airport.query.all():
        by_city[a.city].append(a.iata)
    multi = sorted(
        [(city, sorted(iatas)) for city, iatas in by_city.items() if len(iatas) > 1]
    )
    return {'multi_city_groups': multi}


# ============================================================
# ROUTES — Static
# ============================================================

@app.route('/')
def index():
    # Popular departure cities
    popular_origins = Airport.query.filter_by(is_popular=True, country='United States').limit(8).all()
    # Featured deals: one is_best flight per destination CITY so multi-airport
    # cities (London = LHR + LGW, Tokyo = HND + NRT) and per-date duplication
    # (every JFK→LHR date carries an is_best flag) don't fill the grid with
    # the same city image. Pick the lowest-id is_best per city via SQL so we
    # don't have to scan thousands of rows in Python.
    first_id_per_city = (
        db.session.query(db.func.min(Flight.id))
        .join(Airport, Airport.id == Flight.destination_id)
        .filter(Flight.is_best == True)
        .group_by(Airport.city)
        .subquery()
    )
    featured = (
        Flight.query
        .filter(Flight.id.in_(db.session.query(first_id_per_city)))
        .order_by(Flight.price)
        .limit(12).all()
    )
    if len(featured) < 12:
        seen_cities = {f.destination.city for f in featured}
        for f in (Flight.query.filter_by(is_cheapest=True)
                  .order_by(Flight.id).limit(800).all()):
            city = f.destination.city
            if city in seen_cities:
                continue
            seen_cities.add(city)
            featured.append(f)
            if len(featured) >= 12:
                break

    # Popular destinations — pick one airport per CITY so multi-airport cities
    # (London = LHR + LGW, Tokyo = HND + NRT) don't render twice.
    first_airport_per_city = (
        db.session.query(db.func.min(Airport.id))
        .filter(Airport.is_popular == True)
        .filter(Airport.country != 'United States')
        .group_by(Airport.city)
        .subquery()
    )
    popular_dests = (
        Airport.query
        .filter(Airport.id.in_(db.session.query(first_airport_per_city)))
        .order_by(Airport.city)
        .limit(8).all()
    )
    all_airports = Airport.query.order_by(Airport.is_popular.desc(), Airport.city).all()

    return render_template('index.html',
                           popular_origins=popular_origins,
                           popular_dests=popular_dests,
                           all_airports=all_airports,
                           featured=featured)


@app.route('/explore')
def explore():
    origin = request.args.get('origin', 'SEA').upper()
    origin_airport = Airport.query.filter_by(iata=origin).first()
    all_dests = Airport.query.filter_by(is_popular=True).all()
    flights_by_dest = {}
    if origin_airport:
        # Get cheapest flight FROM this origin to each destination
        dests_with_flights = db.session.query(Flight.destination_id).filter(
            Flight.origin_id == origin_airport.id
        ).distinct().all()
        dest_ids_reachable = {d[0] for d in dests_with_flights}
        # Group destinations by whether origin has flights to them
        reachable_dests = []
        for dest in all_dests:
            if dest.id in dest_ids_reachable and dest.id != origin_airport.id:
                f = Flight.query.filter_by(
                    origin_id=origin_airport.id,
                    destination_id=dest.id,
                ).order_by(Flight.price).first()
                if f:
                    flights_by_dest[dest.iata] = f
                    reachable_dests.append(dest)
        # Filter visible list to reachable destinations only, preserving popularity sort
        all_dests = reachable_dests
    else:
        # No matching origin: fall back to showing all popular destinations with global
        # cheapest flight, but mark the origin as unknown.
        for dest in all_dests:
            f = Flight.query.filter_by(destination_id=dest.id).order_by(Flight.price).first()
            if f:
                flights_by_dest[dest.iata] = f

    all_airports = Airport.query.filter_by(is_popular=True).order_by(Airport.city).all()
    view = request.args.get('view', 'grid').lower()
    if view not in ('grid', 'map'):
        view = 'grid'

    # Pre-compute deterministic pin positions for the map view so the
    # template doesn't need an ord() filter (Jinja2 default env has none).
    # Project each destination IATA into a [region anchor + IATA-hash jitter]
    # equirectangular layout on a flat 100% x 100% canvas.
    region_xy = {
        'North America': (0.20, 0.32), 'Latin America': (0.28, 0.62),
        'Europe':        (0.52, 0.28), 'Africa':        (0.55, 0.55),
        'Middle East':   (0.62, 0.42), 'Asia':          (0.78, 0.36),
        'Oceania':       (0.85, 0.72),
    }
    pin_positions = {}
    for d in all_dests:
        bx, by = region_xy.get(d.region, (0.5, 0.5))
        iata = (d.iata or '').ljust(3, 'A')
        xoff = ((ord(iata[0]) * 13 + ord(iata[1]) * 7) % 100) / 600.0 - 0.08
        yoff = ((ord(iata[2]) * 17 + ord(iata[1]) * 5) % 100) / 600.0 - 0.08
        pin_positions[d.iata] = (round((bx + xoff) * 100, 1),
                                  round((by + yoff) * 100, 1))

    return render_template('explore.html',
                           origin=origin,
                           origin_airport=origin_airport,
                           destinations=all_dests,
                           flights_by_dest=flights_by_dest,
                           all_airports=all_airports,
                           view=view,
                           pin_positions=pin_positions)


# Landmarks / place names that WebVoyager users sometimes type instead of an
# airport. Map lowercase substring -> IATA code of the nearest / primary airport.
# The substring is matched case-insensitively against the full query.
_LANDMARK_TO_IATA = {
    'glacier national park': 'FCA',
    'glacier park': 'FCA',
    'kalispell': 'FCA',
    'flathead': 'FCA',
    'montana': 'FCA',
}

# Multi-word city / airport phrases that the loose token matcher would
# otherwise resolve to the wrong airport. Maps lower-case phrase -> IATA.
_PHRASE_TO_IATA = {
    'tokyo narita': 'NRT',
    'narita': 'NRT',
    'tokyo haneda': 'HND',
    'haneda': 'HND',
    'new york jfk': 'JFK',
    'jfk': 'JFK',
    'newark': 'EWR',
    'laguardia': 'LGA',
    'london heathrow': 'LHR',
    'heathrow': 'LHR',
    'london gatwick': 'LGW',
    'gatwick': 'LGW',
    'paris cdg': 'CDG',
    'charles de gaulle': 'CDG',
    'athens greece': 'ATH',
    'hong kong': 'HKG',
    'los angeles': 'LAX',
    'san francisco': 'SFO',
    'las vegas': 'LAS',
    'mexico city': 'MEX',
    'sao paulo': 'GRU',
    'rio de janeiro': 'GIG',
    'buenos aires': 'EZE',
    'cape town': 'CPT',
    'abu dhabi': 'AUH',
    'tel aviv': 'TLV',
    'kuala lumpur': 'KUL',
    'osaka kansai': 'KIX',
    'punta cana': 'PUJ',
    'san juan': 'SJU',
}


def _resolve_airport_ids(query_str):
    """Resolve a query (IATA, city, city_slug, landmark, or free-form phrase)
    to a list of Airport ids.

    Handles multi-word inputs like "Tokyo Narita", "Athens Greece",
    "Lisbon LIS", "Hong Kong", and landmarks like "Glacier National Park".

    Returns (primary_airport_or_None, [ids]) — primary is first popular hit for display.
    """
    if not query_str:
        return None, []
    q = query_str.strip()
    if not q:
        return None, []
    q_lower = q.lower()

    # 1) Try IATA exact match first (case-insensitive, ignoring surrounding words)
    iata_exact = Airport.query.filter(Airport.iata == q.upper()).first()
    if iata_exact:
        return iata_exact, [iata_exact.id]

    # 2) Landmark / named-place aliases (e.g. "Glacier National Park" -> FCA)
    for phrase, iata in _LANDMARK_TO_IATA.items():
        if phrase in q_lower:
            a = Airport.query.filter_by(iata=iata).first()
            if a:
                return a, [a.id]

    # 3) Phrase aliases for well-known multi-word cities / airports.
    for phrase, iata in _PHRASE_TO_IATA.items():
        if phrase in q_lower:
            a = Airport.query.filter_by(iata=iata).first()
            if a:
                # If the phrase matches a city-level slug (Tokyo, New York),
                # return every airport in that city so user gets full inventory.
                siblings = Airport.query.filter_by(city_slug=a.city_slug).all()
                ids = [s.id for s in siblings] if siblings else [a.id]
                return a, ids

    # 4) Any 3-letter token in the query matching an IATA (e.g. "Lisbon LIS")
    import re
    tokens = [t for t in re.split(r'[\s,()/\-]+', q) if t]
    for t in tokens:
        if len(t) == 3 and t.isalpha():
            a = Airport.query.filter(Airport.iata == t.upper()).first()
            if a:
                siblings = Airport.query.filter_by(city_slug=a.city_slug).all()
                ids = [s.id for s in siblings] if siblings else [a.id]
                return a, ids

    # 5) Full-string contains match on city / slug / name.
    ql = f"%{q}%"
    hits = Airport.query.filter(
        or_(
            Airport.iata.ilike(q.upper()),
            Airport.city.ilike(ql),
            Airport.city_slug.ilike(f"%{q.lower().replace(' ', '-')}%"),
            Airport.name.ilike(ql),
        )
    ).all()

    # 6) Multi-token fallback: gather airports that match ANY meaningful token
    # in city/name/slug/country. Rank by number of tokens matched so that
    # "Tokyo Narita" prefers NRT over HND.
    if not hits and tokens:
        score_map = {}  # airport_id -> (score, airport)
        for t in tokens:
            if len(t) < 3:
                continue
            tl = f"%{t.lower()}%"
            tok_hits = Airport.query.filter(
                or_(
                    Airport.city.ilike(tl),
                    Airport.city_slug.ilike(tl),
                    Airport.name.ilike(tl),
                    Airport.country.ilike(tl),
                )
            ).all()
            for h in tok_hits:
                prev_score, _ = score_map.get(h.id, (0, h))
                score_map[h.id] = (prev_score + 1, h)
        if score_map:
            ranked = sorted(score_map.values(),
                            key=lambda x: (-x[0], 0 if x[1].is_popular else 1))
            max_score = ranked[0][0]
            hits = [h for s, h in ranked if s == max_score]

    if not hits:
        return None, []
    # Prefer popular airport as display primary
    primary = next((h for h in hits if h.is_popular), hits[0])
    return primary, [h.id for h in hits]


def _replace_year(d, target_year):
    if d is None or target_year is None:
        return d
    try:
        return d.replace(year=target_year)
    except ValueError:
        # Feb 29 in a non-leap target year
        return d.replace(year=target_year, month=2, day=28)


def _shift_flight_year(flight, dep_target, ret_target):
    """Overlay flight dates so a search for an arbitrary year displays with that
    year while the underlying inventory stays canonical. Mutates in place; the
    GET request never commits, so changes don't persist."""
    if dep_target is not None and flight.departure_date is not None:
        offset = (flight.arrival_date - flight.departure_date).days if flight.arrival_date else 0
        flight.departure_date = dep_target
        if flight.arrival_date is not None:
            flight.arrival_date = dep_target + timedelta(days=offset)
    if flight.return_date is not None:
        # Same-day round-trips (return_date == departure_date stored): keep them
        # same-day in the requested year. Otherwise carry the return year through.
        target = ret_target if ret_target is not None else dep_target
        flight.return_date = _replace_year(flight.return_date, target.year if target else None)


@app.route('/flights')
def flights_list():
    origin_query = request.args.get('from', '')
    dest_query = request.args.get('to', '')
    depart = request.args.get('depart', '')
    ret = request.args.get('return', '')
    passengers_raw = request.args.get('passengers', '1')
    try:
        passengers = int(passengers_raw or 1)
    except (TypeError, ValueError):
        passengers = 1
    if passengers < 1:
        passengers = 1
    elif passengers > 9:
        passengers = 9
    cabin = request.args.get('class', '') or request.args.get('cabin', '')
    trip_type = request.args.get('trip', 'round')
    sort = request.args.get('sort', 'best')
    max_stops = request.args.get('max_stops', '')
    max_price = request.args.get('max_price', '')
    min_price = request.args.get('min_price', '')
    airline = request.args.get('airline', '').strip()

    origin, origin_ids = _resolve_airport_ids(origin_query)
    dest, dest_ids = _resolve_airport_ids(dest_query)
    origin_iata = (origin.iata if origin else origin_query.upper() if origin_query else '')
    dest_iata = (dest.iata if dest else dest_query.upper() if dest_query else '')

    # ---- Input validation: collect human-readable errors so we never silently
    # return data for nonsense queries (return < depart, same airport, etc).
    validation_errors = []

    # Parse dates up-front so subsequent checks can compare them.
    dep_d = None
    if depart:
        try:
            dep_d = datetime.strptime(depart, '%Y-%m-%d').date()
        except ValueError:
            validation_errors.append(
                f"Invalid departure date '{depart}'. Use the format YYYY-MM-DD."
            )
    ret_d = None
    if ret:
        try:
            ret_d = datetime.strptime(ret, '%Y-%m-%d').date()
        except ValueError:
            validation_errors.append(
                f"Invalid return date '{ret}'. Use the format YYYY-MM-DD."
            )

    if dep_d and ret_d and ret_d < dep_d:
        validation_errors.append(
            f"Return date ({ret_d.isoformat()}) must be on or after the departure date "
            f"({dep_d.isoformat()})."
        )

    if origin_iata and dest_iata and origin_iata == dest_iata:
        validation_errors.append(
            f"Origin and destination cannot be the same airport ({origin_iata})."
        )

    if origin_query and not origin_ids:
        validation_errors.append(f"We don't recognize the origin '{origin_query}'.")
    if dest_query and not dest_ids:
        validation_errors.append(f"We don't recognize the destination '{dest_query}'.")

    try:
        mn_val = float(min_price) if min_price else None
    except ValueError:
        mn_val = None
        validation_errors.append(f"Invalid minimum price '{min_price}'.")
    try:
        mx_val = float(max_price) if max_price else None
    except ValueError:
        mx_val = None
        validation_errors.append(f"Invalid maximum price '{max_price}'.")
    if mn_val is not None and mx_val is not None and mn_val > mx_val:
        validation_errors.append(
            f"Minimum price (${mn_val:g}) cannot exceed maximum price (${mx_val:g})."
        )

    if max_stops != '':
        try:
            ms_val = int(max_stops)
            if ms_val < 0 or ms_val > 3:
                validation_errors.append(
                    f"Stops filter must be between 0 and 3 (got {max_stops})."
                )
        except ValueError:
            validation_errors.append(f"Invalid stops filter '{max_stops}'.")

    valid_cabins = {'', 'economy', 'coach', 'premium', 'premium economy',
                    'premium-economy', 'business', 'first'}
    if cabin and cabin.strip().lower() not in valid_cabins:
        validation_errors.append(
            f"Unknown cabin class '{cabin}'. Valid: Economy, Premium, Business, First."
        )

    # If validation failed, short-circuit: render empty results with the errors so
    # the user sees the problem rather than getting unrelated rows.
    if validation_errors:
        all_airports = Airport.query.order_by(Airport.is_popular.desc(), Airport.city).all()
        return render_template('flights.html',
                               flights=[],
                               origin=origin,
                               destination=dest,
                               origin_iata=origin_iata,
                               dest_iata=dest_iata,
                               depart=depart,
                               return_date=ret,
                               passengers=passengers,
                               cabin=cabin,
                               trip_type=trip_type,
                               sort=sort,
                               max_stops=max_stops,
                               min_price=min_price,
                               max_price=max_price,
                               airline=airline,
                               airline_options=[],
                               all_airports=all_airports,
                               not_found_hint='',
                               validation_errors=validation_errors,
                               origin_input=origin_query,
                               dest_input=dest_query)

    q = Flight.query
    if origin_query:
        q = q.filter(Flight.origin_id.in_(origin_ids))
    if dest_query:
        q = q.filter(Flight.destination_id.in_(dest_ids))

    # Date filtering: match by (month, day) across any year so the same
    # underlying inventory serves searches for any future year.
    if dep_d is not None:
        q = q.filter(
            db.func.strftime('%m-%d', Flight.departure_date)
            == f'{dep_d.month:02d}-{dep_d.day:02d}'
        )
    # Note: `ret` (return date) is displayed back in the form / price label, but
    # we do NOT filter rows by `Flight.return_date` — the return date is satisfied
    # by separately looking up a reciprocal flight on the return date (see
    # flight_detail). Filtering outbound inventory on the exact return_date
    # would incorrectly hide valid outbound flights when the user requests a
    # return date different from the seeded pairing.

    # Cabin class: match either the row's own cabin_class OR allow rows where the
    # class has a valid price set (price_business>0 etc.) so the same row can represent
    # different cabins for the user. Here we treat cabin_class as the requested filter
    # and keep rows whose cabin_class matches (case-insensitive) OR whose alternative
    # price field is populated.
    if cabin:
        cl = cabin.strip().lower()
        if cl in ('economy', 'coach'):
            pass  # every row has economy price
        elif cl in ('premium', 'premium economy', 'premium-economy'):
            q = q.filter(Flight.price_premium > 0)
        elif cl == 'business':
            q = q.filter(Flight.price_business > 0)
        elif cl == 'first':
            q = q.filter(Flight.price_first > 0)

    if max_stops != '':
        try:
            q = q.filter(Flight.stops <= int(max_stops))
        except ValueError:
            pass

    # Price filtering — interpret against the cabin's price column
    def _price_col():
        cl = (cabin or '').strip().lower()
        if cl == 'business':
            return Flight.price_business
        if cl == 'first':
            return Flight.price_first
        if cl in ('premium', 'premium economy', 'premium-economy'):
            return Flight.price_premium
        return Flight.price
    pc = _price_col()
    if max_price:
        try:
            q = q.filter(pc <= float(max_price))
        except ValueError:
            pass
    if min_price:
        try:
            q = q.filter(pc >= float(min_price))
        except ValueError:
            pass
    if airline:
        q = q.filter(Flight.airline.ilike(f'%{airline}%'))

    # Sort options mirror real Google Flights: Top / Price / Duration /
    # Departure time / Arrival time / Emissions. Stops sorts (asc/desc) don't
    # exist upstream; they fall through to "Top flights".
    if sort == 'price' or sort == 'price_asc':
        q = q.order_by(pc.asc())
    elif sort == 'duration':
        q = q.order_by(Flight.duration_minutes.asc())
    elif sort == 'departure':
        q = q.order_by(Flight.departure_time.asc())
    elif sort == 'arrival':
        q = q.order_by(Flight.arrival_time.asc())
    elif sort in ('emissions', 'co2'):
        q = q.order_by(Flight.co2_emissions_kg.asc())
    else:  # best — composite of price, duration, stops (mirrors real Google
        # Flights "Top flights" sort: balances cost and convenience, NOT
        # cheapest-first). is_best DESC keeps a curated top pick; everything
        # else falls through to the heuristic so cheap-but-painful flights
        # don't win.
        best_score = pc + Flight.duration_minutes * 0.4 + Flight.stops * 80
        q = q.order_by(Flight.is_best.desc(), best_score.asc())

    flights = q.limit(50).all()

    # If user provided route inputs but they resolved to nothing (bad IATA / unknown city),
    # show an empty state rather than falling back to all flights.
    # If NOTHING was provided at all, show top featured so /flights bare works.
    not_found_hint = ''
    if not flights:
        if origin_query and dest_query and (origin_ids and dest_ids):
            # route resolved but date / filters removed everything — suggest alt date
            any_route = Flight.query.filter(
                Flight.origin_id.in_(origin_ids),
                Flight.destination_id.in_(dest_ids),
            ).order_by(Flight.departure_date).first()
            if any_route:
                not_found_hint = f"This route has flights on {any_route.departure_date.strftime('%b %d')} (and other days) — try a different date or clearing filters."
        if not origin_query and not dest_query:
            flights = Flight.query.order_by(Flight.is_best.desc(), Flight.price).limit(30).all()

    # Year-shift displayed dates so searches for any year render with the
    # requested year (canonical inventory stays year-2024 etc).
    if dep_d is not None and flights:
        with db.session.no_autoflush:
            for f in flights:
                _shift_flight_year(f, dep_d, ret_d)

    # Unique airline list for the filter dropdown (scoped to this route if set)
    airline_q = db.session.query(Flight.airline).distinct()
    if origin_ids:
        airline_q = airline_q.filter(Flight.origin_id.in_(origin_ids))
    if dest_ids:
        airline_q = airline_q.filter(Flight.destination_id.in_(dest_ids))
    airline_options = sorted({row[0] for row in airline_q.limit(100).all()})

    all_airports = Airport.query.order_by(Airport.is_popular.desc(), Airport.city).all()

    return render_template('flights.html',
                           flights=flights,
                           origin=origin,
                           destination=dest,
                           origin_iata=origin_iata,
                           dest_iata=dest_iata,
                           depart=depart,
                           return_date=ret,
                           passengers=passengers,
                           cabin=cabin,
                           trip_type=trip_type,
                           sort=sort,
                           max_stops=max_stops,
                           min_price=min_price,
                           max_price=max_price,
                           airline=airline,
                           airline_options=airline_options,
                           all_airports=all_airports,
                           not_found_hint=not_found_hint,
                           validation_errors=[],
                           origin_input=origin_query,
                           dest_input=dest_query)


def _booking_sites_for_flight(flight):
    """Return a deterministic list of 'Booking sites' offering this flight,
    with synthetic prices per site. Used on the flight detail page so users
    can compare which third-party agency is cheapest.

    Prices are anchored to the flight's own economy price with site-specific
    multipliers so ordering is stable across requests.
    """
    # site label, multiplier vs economy price
    sites = [
        ('Expedia', 1.00),
        ('Kiwi.com', 0.96),
        ('Booking.com', 1.04),
        ('Kayak', 0.98),
        ('Priceline', 1.02),
    ]
    # Prefer the airline's own direct channel (slight discount) when plausible
    airline_site = {
        'KLM': ('KLM.com', 0.94),
        'Delta': ('Delta.com', 0.95),
        'United': ('United.com', 0.95),
        'British Airways': ('BritishAirways.com', 0.95),
        'Lufthansa': ('Lufthansa.com', 0.95),
        'Air France': ('AirFrance.com', 0.95),
        'American Airlines': ('AA.com', 0.95),
        'Japan Airlines': ('JAL.com', 0.95),
        'ANA': ('ANA.co.jp', 0.95),
        'Emirates': ('Emirates.com', 0.95),
        'Qatar Airways': ('QatarAirways.com', 0.95),
        'Etihad': ('EtihadAirways.com', 0.95),
        'Singapore Airlines': ('SingaporeAir.com', 0.94),
        'Cathay Pacific': ('CathayPacific.com', 0.95),
        'Turkish Airlines': ('TurkishAirlines.com', 0.95),
    }.get(flight.airline)
    entries = []
    base = flight.price_business if flight.price_business and flight.cabin_class.lower() == 'business' else flight.price
    for name, mult in sites:
        entries.append({
            'site': name,
            'economy_price': round(flight.price * mult, 0),
            'business_price': round(flight.price_business * mult, 0) if flight.price_business else None,
            'label': 'Third-party agency',
        })
    if airline_site:
        name, mult = airline_site
        entries.append({
            'site': name,
            'economy_price': round(flight.price * mult, 0),
            'business_price': round(flight.price_business * mult, 0) if flight.price_business else None,
            'label': 'Airline direct',
        })
    # Sort by economy price ascending so cheapest is first
    entries.sort(key=lambda e: e['economy_price'])
    return entries


@app.route('/flight/<int:flight_id>')
def flight_detail(flight_id):
    flight = db.session.get(Flight, flight_id) or abort(404)
    reviews = Review.query.filter_by(flight_id=flight_id).order_by(Review.created_at.desc()).all()
    avg_rating = sum(r.rating for r in reviews) / len(reviews) if reviews else flight.rating
    booking_sites = _booking_sites_for_flight(flight)
    # Related flights on same route
    related = Flight.query.filter(
        Flight.id != flight_id,
        Flight.origin_id == flight.origin_id,
        Flight.destination_id == flight.destination_id,
    ).limit(6).all()

    # Parse the requested departure year (used for date overlay) up front so we
    # can validate return >= depart before resolving a return flight.
    dep_str = request.args.get('dep', '') or request.args.get('depart', '')
    dep_target = None
    if dep_str:
        try:
            dep_target = datetime.strptime(dep_str, '%Y-%m-%d').date()
        except ValueError:
            dep_target = None

    # Resolve return flight:
    # 1) explicit ?return_flight_id= wins
    # 2) else if ?return=YYYY-MM-DD on the query string, pick cheapest inventory
    #    on the reciprocal route (dest -> origin) for that date (year-agnostic)
    # 3) else if flight.return_date is set, pick cheapest reciprocal on that date
    # If the requested return is earlier than the departure, refuse to pair —
    # an inverted-date itinerary is not valid.
    return_flight = None
    rf_id = request.args.get('return_flight_id', type=int)
    ret_d = None
    ret_invalid = False
    if rf_id:
        return_flight = db.session.get(Flight, rf_id)
    else:
        ret_str = request.args.get('return', '')
        if ret_str:
            try:
                ret_d = datetime.strptime(ret_str, '%Y-%m-%d').date()
            except ValueError:
                pass
        if dep_target and ret_d and ret_d < dep_target:
            ret_invalid = True
            ret_d = None
        if ret_d is None and flight.return_date and not ret_invalid:
            ret_d = flight.return_date
        if ret_d:
            return_flight = Flight.query.filter(
                Flight.origin_id == flight.destination_id,
                Flight.destination_id == flight.origin_id,
                db.func.strftime('%m-%d', Flight.departure_date)
                == f'{ret_d.month:02d}-{ret_d.day:02d}',
            ).order_by(Flight.price).first()

    if dep_target is not None:
        with db.session.no_autoflush:
            _shift_flight_year(flight, dep_target, ret_d)
    if return_flight is not None and ret_d is not None:
        with db.session.no_autoflush:
            _shift_flight_year(return_flight, ret_d, dep_target)

    return render_template('flight_detail.html',
                           flight=flight,
                           reviews=reviews,
                           avg_rating=avg_rating,
                           related=related,
                           booking_sites=booking_sites,
                           return_flight=return_flight)


@app.route('/destination/<slug>')
def destination(slug):
    airport = Airport.query.filter_by(city_slug=slug).first() or abort(404)
    # Flights arriving to this airport
    inbound = Flight.query.filter_by(destination_id=airport.id).order_by(Flight.price).limit(16).all()
    # Flights departing from this airport
    outbound = Flight.query.filter_by(origin_id=airport.id).order_by(Flight.price).limit(16).all()
    return render_template('destination.html',
                           airport=airport,
                           inbound=inbound,
                           outbound=outbound)


@app.route('/hotels')
def hotels():
    dests = Airport.query.filter_by(is_popular=True).all()
    return render_template('hotels.html', destinations=dests)


@app.route('/vacation-rentals')
def vacation_rentals():
    dests = Airport.query.filter_by(is_popular=True).all()
    return render_template('vacation_rentals.html', destinations=dests)


@app.route('/deals')
def deals():
    cheap = Flight.query.filter_by(is_cheapest=True).order_by(Flight.price).limit(24).all()
    if len(cheap) < 24:
        more = Flight.query.order_by(Flight.price).limit(24 - len(cheap)).all()
        cheap.extend(more)
    return render_template('deals.html', flights=cheap)


@app.route('/tools')
def tools():
    return render_template('tools.html')


@app.route('/tools/date-grid')
def date_grid():
    return render_template('date_grid.html')


@app.route('/tools/price-graph')
def price_graph():
    origin_query = request.args.get('from', '')
    dest_query = request.args.get('to', '')
    depart_str = request.args.get('depart', '')
    try:
        months = max(1, min(6, int(request.args.get('months', 2))))
    except ValueError:
        months = 2

    origin, origin_ids = _resolve_airport_ids(origin_query)
    dest, dest_ids = _resolve_airport_ids(dest_query)

    # If no route specified, default to a sensible demo
    if not origin_ids:
        origin = Airport.query.filter_by(iata='JFK').first()
        if origin:
            origin_ids = [origin.id]
    if not dest_ids:
        dest = Airport.query.filter_by(iata='LAX').first()
        if dest:
            dest_ids = [dest.id]

    # Anchor the graph window to the user's intended departure date so the
    # rendered dates match what they searched. Inventory is queried
    # year-agnostically (by month-day) since the canonical seed year may be
    # different from what the user is browsing.
    today = datetime.utcnow().date()
    anchor = None
    if depart_str:
        try:
            anchor = datetime.strptime(depart_str, '%Y-%m-%d').date()
        except ValueError:
            anchor = None
    if anchor is None:
        anchor = today

    series = []
    md_min = {}        # (month, day) -> min price across all years for this route
    observed_avg = None
    if origin_ids and dest_ids:
        rows = Flight.query.filter(
            Flight.origin_id.in_(origin_ids),
            Flight.destination_id.in_(dest_ids),
        ).all()
        if rows:
            observed_avg = sum(r.price for r in rows) / len(rows)
            for r in rows:
                key = (r.departure_date.month, r.departure_date.day)
                md_min[key] = min(md_min.get(key, r.price), r.price)

    # Build the daily series in the user's requested year. For days with no
    # seeded inventory on the same month-day, synthesize a deterministic trend
    # anchored on the observed average so the chart still shows ~60+ points.
    if observed_avg is not None:
        total_days = months * 30
        import math
        seed_base = hash((origin_ids[0], dest_ids[0])) & 0xFFFF
        for i in range(total_days):
            current = anchor + timedelta(days=i)
            md = (current.month, current.day)
            if md in md_min:
                series.append({'date': current, 'price': round(md_min[md], 0)})
                continue
            phase = (i + seed_base) % 30
            swing = math.sin(phase / 30.0 * 2 * math.pi) * 0.18
            micro = ((i * 37 + seed_base) % 11) / 100.0 - 0.05  # -5%..+5%
            weekend_boost = 0.06 if current.weekday() in (4, 5) else 0.0
            price = observed_avg * (1.0 + swing + micro + weekend_boost)
            series.append({'date': current, 'price': round(max(40.0, price), 0)})

    if series:
        prices_only = [s['price'] for s in series]
        lowest = min(prices_only)
        highest = max(prices_only)
        average = round(sum(prices_only) / len(prices_only), 0)
    else:
        lowest = highest = average = 0

    return render_template('price_graph.html',
                           origin=origin,
                           destination=dest,
                           origin_iata=origin.iata if origin else origin_query.upper(),
                           dest_iata=dest.iata if dest else dest_query.upper(),
                           depart=anchor.isoformat(),
                           months=months,
                           series=series,
                           lowest=lowest,
                           highest=highest,
                           average=average)


@app.route('/tools/price-insights')
def price_insights():
    origin_query = request.args.get('from', '')
    dest_query = request.args.get('to', '')
    origin, origin_ids = _resolve_airport_ids(origin_query)
    dest, dest_ids = _resolve_airport_ids(dest_query)
    insight = None
    if origin_ids and dest_ids:
        rows = Flight.query.filter(
            Flight.origin_id.in_(origin_ids),
            Flight.destination_id.in_(dest_ids),
        ).all()
        if rows:
            prices = [r.price for r in rows]
            insight = {
                'count': len(rows),
                'low': round(min(prices), 0),
                'avg': round(sum(prices)/len(prices), 0),
                'high': round(max(prices), 0),
            }
    return render_template('price_insights.html',
                           origin=origin,
                           destination=dest,
                           origin_iata=origin.iata if origin else origin_query.upper(),
                           dest_iata=dest.iata if dest else dest_query.upper(),
                           insight=insight)


@app.route('/tools/price-tracking')
def price_tracking():
    return render_template('price_tracking.html')


@app.route('/search')
def search():
    q = request.args.get('q', '').strip()
    results_flights = []
    results_airports = []

    if q:
        # Try to parse "origin to destination" patterns
        import re as _re
        route_match = _re.split(r'\s+to\s+|\s*->\s*|\s*→\s*|\s*–\s+', q, maxsplit=1, flags=_re.IGNORECASE)

        if len(route_match) == 2:
            # Route search: e.g. "SFO to London", "Chicago -> Barcelona"
            origin_q = route_match[0].strip()
            dest_q = route_match[1].strip()
            origin_ql = f"%{origin_q}%"
            dest_ql = f"%{dest_q}%"

            origin_airports = Airport.query.filter(
                or_(
                    Airport.city.ilike(origin_ql),
                    Airport.iata.ilike(origin_ql),
                    Airport.country.ilike(origin_ql),
                    Airport.name.ilike(origin_ql),
                )
            ).all()
            dest_airports = Airport.query.filter(
                or_(
                    Airport.city.ilike(dest_ql),
                    Airport.iata.ilike(dest_ql),
                    Airport.country.ilike(dest_ql),
                    Airport.name.ilike(dest_ql),
                )
            ).all()

            results_airports = list({a.id: a for a in origin_airports + dest_airports}.values())

            origin_ids = [a.id for a in origin_airports]
            dest_ids = [a.id for a in dest_airports]

            if origin_ids and dest_ids:
                # Best case: match flights from origin to destination
                results_flights = Flight.query.filter(
                    Flight.origin_id.in_(origin_ids),
                    Flight.destination_id.in_(dest_ids),
                ).limit(30).all()
                # If no exact route matches, also try reverse and individual
                if not results_flights:
                    results_flights = Flight.query.filter(
                        or_(
                            Flight.origin_id.in_(origin_ids),
                            Flight.destination_id.in_(dest_ids),
                        )
                    ).limit(20).all()
            elif origin_ids:
                results_flights = Flight.query.filter(
                    Flight.origin_id.in_(origin_ids)
                ).limit(20).all()
            elif dest_ids:
                results_flights = Flight.query.filter(
                    Flight.destination_id.in_(dest_ids)
                ).limit(20).all()
        else:
            # Single-term search (original behaviour)
            ql = f"%{q}%"
            results_airports = Airport.query.filter(
                or_(
                    Airport.city.ilike(ql),
                    Airport.iata.ilike(ql),
                    Airport.country.ilike(ql),
                    Airport.name.ilike(ql),
                )
            ).limit(20).all()
            airport_ids = [a.id for a in results_airports]
            if airport_ids:
                results_flights = Flight.query.filter(
                    or_(
                        Flight.origin_id.in_(airport_ids),
                        Flight.destination_id.in_(airport_ids),
                    )
                ).limit(20).all()
            else:
                results_flights = Flight.query.filter(
                    or_(
                        Flight.airline.ilike(ql),
                        Flight.flight_number.ilike(ql),
                    )
                ).limit(20).all()

    return render_template('search.html',
                           q=q,
                           airports=results_airports,
                           flights=results_flights)


# ============================================================
# AUTH
# ============================================================

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('account'))
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        user = User.query.filter_by(email=email).first()
        if user and bcrypt.check_password_hash(user.password_hash, password):
            login_user(user, remember=True)
            flash('Welcome back!', 'success')
            return redirect(request.args.get('next') or url_for('account'))
        flash('Invalid email or password.', 'error')
    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('account'))
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        first_name = request.form.get('first_name', '').strip()
        last_name = request.form.get('last_name', '').strip()

        if not email or not password or len(password) < 6:
            flash('Email and a password of at least 6 characters are required.', 'error')
            return render_template('register.html')
        if User.query.filter_by(email=email).first():
            flash('An account with this email already exists.', 'error')
            return render_template('register.html')

        user = User(
            email=email,
            password_hash=bcrypt.generate_password_hash(password).decode('utf-8'),
            first_name=first_name,
            last_name=last_name,
        )
        db.session.add(user)
        db.session.commit()
        login_user(user, remember=True)
        flash('Your Google Flights account is ready. Happy travels!', 'success')
        return redirect(url_for('account'))
    return render_template('register.html')


@app.route('/logout')
def logout():
    logout_user()
    flash('You have been signed out.', 'info')
    return redirect(url_for('index'))


# ============================================================
# ACCOUNT
# ============================================================

@app.route('/account')
@login_required
def account():
    bookings = current_user.bookings.order_by(Booking.booked_at.desc()).all()
    tracked = current_user.tracked.order_by(TrackedFlight.added_at.desc()).all()
    alerts = current_user.alerts.order_by(PriceAlert.created_at.desc()).all()
    saved = current_user.saved_searches.order_by(SavedSearch.created_at.desc()).all()
    return render_template('account.html',
                           bookings=bookings,
                           tracked=tracked,
                           alerts=alerts,
                           saved_searches=saved)


@app.route('/account/edit', methods=['GET', 'POST'])
@login_required
def account_edit():
    if request.method == 'POST':
        current_user.first_name = request.form.get('first_name', '').strip()
        current_user.last_name = request.form.get('last_name', '').strip()
        current_user.phone = request.form.get('phone', '').strip()
        current_user.address = request.form.get('address', '').strip()
        current_user.city = request.form.get('city', '').strip()
        current_user.country = request.form.get('country', '').strip()
        current_user.passport_number = request.form.get('passport_number', '').strip()
        current_user.frequent_flyer = request.form.get('frequent_flyer', '').strip()
        dob = request.form.get('date_of_birth', '').strip()
        if dob:
            try:
                current_user.date_of_birth = datetime.strptime(dob, '%Y-%m-%d').date()
            except ValueError:
                pass
        db.session.commit()
        flash('Profile updated.', 'success')
        return redirect(url_for('account'))
    return render_template('account_edit.html')


@app.route('/account/password', methods=['GET', 'POST'])
@login_required
def change_password():
    if request.method == 'POST':
        current = request.form.get('current_password', '')
        new_pw = request.form.get('new_password', '')
        confirm = request.form.get('confirm_password', '')
        if not bcrypt.check_password_hash(current_user.password_hash, current):
            flash('Current password incorrect.', 'error')
        elif len(new_pw) < 6:
            flash('New password must be at least 6 characters.', 'error')
        elif new_pw != confirm:
            flash('New password confirmation does not match.', 'error')
        else:
            current_user.password_hash = bcrypt.generate_password_hash(new_pw).decode('utf-8')
            db.session.commit()
            flash('Password changed.', 'success')
            return redirect(url_for('account'))
    return render_template('change_password.html')


@app.route('/account/delete', methods=['POST'])
@login_required
def delete_account():
    u = db.session.get(User, current_user.id)
    logout_user()
    db.session.delete(u)
    db.session.commit()
    flash('Your account has been deleted.', 'info')
    return redirect(url_for('index'))


# ============================================================
# CART (BAG) + CHECKOUT
# ============================================================

@app.route('/bag')
@login_required
def bag():
    items = current_user.cart_items.order_by(CartItem.added_at.desc()).all()
    subtotal = sum(i.line_total for i in items)
    taxes = round(subtotal * 0.14, 2)
    total = round(subtotal + taxes, 2)
    return render_template('bag.html',
                           items=items,
                           subtotal=subtotal,
                           taxes=taxes,
                           total=total)


@app.route('/api/cart/add', methods=['POST'])
@csrf.exempt
@login_required
def api_cart_add():
    data = request.get_json(silent=True) or {}
    flight_id = int(data.get('flight_id', 0))
    passengers = int(data.get('passengers', 1))
    cabin = data.get('cabin_class', 'Economy')
    return_id = data.get('return_flight_id')

    flight = db.session.get(Flight, flight_id)
    if not flight:
        return jsonify({'success': False, 'message': 'Flight not found'}), 404

    existing = current_user.cart_items.filter_by(flight_id=flight_id).first()
    if existing:
        existing.passengers = passengers
        existing.cabin_class = cabin
    else:
        item = CartItem(
            user_id=current_user.id,
            flight_id=flight_id,
            passengers=passengers,
            cabin_class=cabin,
            return_flight_id=int(return_id) if return_id else None,
        )
        db.session.add(item)
    db.session.commit()
    return jsonify({
        'success': True,
        'message': f'Added {flight.airline} {flight.flight_number} to your bag',
        'cart_count': current_user.cart_items.count(),
    })


@app.route('/api/cart/update', methods=['POST'])
@csrf.exempt
@login_required
def api_cart_update():
    data = request.get_json(silent=True) or {}
    item_id = int(data.get('item_id', 0))
    passengers = int(data.get('passengers', 1))
    item = db.session.get(CartItem, item_id)
    if not item or item.user_id != current_user.id:
        return jsonify({'success': False}), 404
    item.passengers = max(1, passengers)
    db.session.commit()
    return jsonify({'success': True,
                    'line_total': item.line_total,
                    'cart_count': current_user.cart_items.count()})


@app.route('/api/cart/remove', methods=['POST'])
@csrf.exempt
@login_required
def api_cart_remove():
    data = request.get_json(silent=True) or {}
    item_id = int(data.get('item_id', 0))
    item = db.session.get(CartItem, item_id)
    if not item or item.user_id != current_user.id:
        return jsonify({'success': False}), 404
    db.session.delete(item)
    db.session.commit()
    return jsonify({'success': True, 'cart_count': current_user.cart_items.count()})


# ------ Form-based cart routes (for browser agents) ------

@app.route('/cart/add/<int:flight_id>', methods=['POST'])
@login_required
def cart_add_form(flight_id):
    flight = db.session.get(Flight, flight_id) or abort(404)
    passengers = int(request.form.get('passengers', 1) or 1)
    cabin = request.form.get('cabin_class', 'Economy')
    return_id = request.form.get('return_flight_id')
    existing = current_user.cart_items.filter_by(flight_id=flight_id).first()
    if existing:
        existing.passengers = passengers
        existing.cabin_class = cabin
    else:
        item = CartItem(
            user_id=current_user.id,
            flight_id=flight_id,
            passengers=passengers,
            cabin_class=cabin,
            return_flight_id=int(return_id) if return_id else None,
        )
        db.session.add(item)
    db.session.commit()
    flash(f'{flight.airline} {flight.flight_number} added to your bag.', 'success')
    return redirect(url_for('bag'))


@app.route('/cart/remove/<int:item_id>', methods=['POST'])
@login_required
def cart_remove_form(item_id):
    item = db.session.get(CartItem, item_id)
    if item and item.user_id == current_user.id:
        db.session.delete(item)
        db.session.commit()
        flash('Flight removed from bag.', 'info')
    return redirect(url_for('bag'))


@app.route('/cart/update/<int:item_id>', methods=['POST'])
@login_required
def cart_update_form(item_id):
    item = db.session.get(CartItem, item_id)
    if not item or item.user_id != current_user.id:
        abort(404)
    passengers = int(request.form.get('passengers', item.passengers) or item.passengers)
    cabin = request.form.get('cabin_class', item.cabin_class)
    item.passengers = max(1, passengers)
    item.cabin_class = cabin
    db.session.commit()
    flash('Bag updated.', 'success')
    return redirect(url_for('bag'))


# ------ Form-based track route ------

@app.route('/track/add/<int:flight_id>', methods=['POST'])
@login_required
def track_add_form(flight_id):
    flight = db.session.get(Flight, flight_id) or abort(404)
    existing = current_user.tracked.filter_by(flight_id=flight_id).first()
    if not existing:
        target = float(request.form.get('target_price', flight.price * 0.9) or flight.price * 0.9)
        db.session.add(TrackedFlight(
            user_id=current_user.id,
            flight_id=flight_id,
            starting_price=flight.price,
            target_price=target,
        ))
        db.session.commit()
        flash(f'{flight.airline} {flight.flight_number} is now being tracked.', 'success')
    else:
        flash('Flight already tracked.', 'info')
    return redirect(url_for('flight_detail', flight_id=flight_id))


@app.route('/track/remove/<int:flight_id>', methods=['POST'])
@login_required
def track_remove_form(flight_id):
    existing = current_user.tracked.filter_by(flight_id=flight_id).first()
    if existing:
        db.session.delete(existing)
        db.session.commit()
        flash('Stopped tracking flight.', 'info')
    return redirect(url_for('tracked_flights'))


@app.route('/checkout', methods=['GET', 'POST'])
@login_required
def checkout():
    items = current_user.cart_items.all()
    if not items:
        flash('Your bag is empty.', 'info')
        return redirect(url_for('bag'))

    subtotal = sum(i.line_total for i in items)
    taxes = round(subtotal * 0.14, 2)
    total = round(subtotal + taxes, 2)

    if request.method == 'POST':
        contact_email = request.form.get('contact_email', current_user.email)
        contact_phone = request.form.get('contact_phone', '')
        passengers_json = []
        for i, ci in enumerate(items):
            for p in range(ci.passengers):
                passengers_json.append({
                    'first_name': request.form.get(f'pax_first_{i}_{p}', current_user.first_name or 'Guest'),
                    'last_name': request.form.get(f'pax_last_{i}_{p}', current_user.last_name or 'Traveler'),
                })

        # Support saved payment method selection
        saved_pm_id = request.form.get('saved_payment_id')
        if saved_pm_id:
            pm = db.session.get(PaymentMethod, int(saved_pm_id))
            if pm and pm.user_id == current_user.id:
                card_last4 = pm.last4
                card_brand = pm.card_type
            else:
                card_last4 = request.form.get('card_number', '0000')[-4:] or '0000'
                card_brand = 'Visa'
        else:
            card_last4 = request.form.get('card_number', '0000')[-4:] or '0000'
            card_brand = 'Visa'

        booking = Booking(
            user_id=current_user.id,
            pnr=make_pnr(),
            status='confirmed',
            trip_type='round' if any(i.return_flight_id for i in items) else 'one-way',
            total_amount=total,
            taxes_fees=taxes,
            currency='USD',
            passenger_names_json=json.dumps(passengers_json),
            contact_email=contact_email,
            contact_phone=contact_phone,
            payment_last4=card_last4,
            payment_brand=card_brand,
        )
        db.session.add(booking)
        db.session.flush()

        for ci in items:
            bi = BookingItem(
                booking_id=booking.id,
                flight_id=ci.flight_id,
                leg='outbound',
                passengers=ci.passengers,
                cabin_class=ci.cabin_class,
                price=ci.flight.price if ci.flight else 0,
                seat=random.choice(['12A', '14C', '22F', '9D', '31B']),
            )
            db.session.add(bi)
            if ci.return_flight_id:
                bi2 = BookingItem(
                    booking_id=booking.id,
                    flight_id=ci.return_flight_id,
                    leg='return',
                    passengers=ci.passengers,
                    cabin_class=ci.cabin_class,
                    price=ci.return_flight.price if ci.return_flight else 0,
                    seat=random.choice(['12A', '14C', '22F', '9D', '31B']),
                )
                db.session.add(bi2)
            db.session.delete(ci)
        db.session.commit()
        flash(f'Booking confirmed — PNR {booking.pnr}', 'success')
        return redirect(url_for('booking_confirmation', booking_id=booking.id))

    saved_payments = current_user.payment_methods.order_by(
        PaymentMethod.is_default.desc(), PaymentMethod.created_at.desc()).all()
    return render_template('checkout.html',
                           items=items,
                           subtotal=subtotal,
                           taxes=taxes,
                           total=total,
                           saved_payments=saved_payments)


@app.route('/booking/<int:booking_id>')
@login_required
def booking_detail(booking_id):
    b = db.session.get(Booking, booking_id) or abort(404)
    if b.user_id != current_user.id:
        abort(403)
    return render_template('booking_detail.html', booking=b)


@app.route('/booking/<int:booking_id>/confirmation')
@login_required
def booking_confirmation(booking_id):
    b = db.session.get(Booking, booking_id) or abort(404)
    if b.user_id != current_user.id:
        abort(403)
    return render_template('booking_confirmation.html', booking=b)


@app.route('/booking/<int:booking_id>/cancel', methods=['POST'])
@login_required
def booking_cancel(booking_id):
    b = db.session.get(Booking, booking_id) or abort(404)
    if b.user_id != current_user.id:
        abort(403)
    if b.status == 'confirmed':
        b.status = 'cancelled'
        b.cancelled_at = datetime.utcnow()
        db.session.commit()
        flash(f'Booking {b.pnr} cancelled.', 'info')
    return redirect(url_for('account'))


@app.route('/booking/<int:booking_id>/rebook', methods=['POST'])
@login_required
def booking_rebook(booking_id):
    b = db.session.get(Booking, booking_id) or abort(404)
    if b.user_id != current_user.id:
        abort(403)
    for bi in b.items:
        existing = current_user.cart_items.filter_by(flight_id=bi.flight_id).first()
        if not existing:
            db.session.add(CartItem(
                user_id=current_user.id,
                flight_id=bi.flight_id,
                passengers=bi.passengers,
                cabin_class=bi.cabin_class,
            ))
    db.session.commit()
    flash('Flights added back to your bag.', 'success')
    return redirect(url_for('bag'))


# ============================================================
# TRACKED FLIGHTS / WISHLIST
# ============================================================

@app.route('/api/track/toggle', methods=['POST'])
@csrf.exempt
@login_required
def api_track_toggle():
    data = request.get_json(silent=True) or {}
    flight_id = int(data.get('flight_id', 0))
    existing = current_user.tracked.filter_by(flight_id=flight_id).first()
    if existing:
        db.session.delete(existing)
        tracked = False
    else:
        flight = db.session.get(Flight, flight_id)
        if not flight:
            return jsonify({'success': False}), 404
        db.session.add(TrackedFlight(
            user_id=current_user.id,
            flight_id=flight_id,
            starting_price=flight.price,
            target_price=flight.price * 0.9,
        ))
        tracked = True
    db.session.commit()
    return jsonify({
        'success': True,
        'tracked': tracked,
        'tracked_count': current_user.tracked.count(),
    })


@app.route('/tracked')
@login_required
def tracked_flights():
    items = current_user.tracked.order_by(TrackedFlight.added_at.desc()).all()
    return render_template('tracked.html', items=items)


@app.route('/tracked/remove/<int:item_id>', methods=['POST'])
@login_required
def tracked_remove(item_id):
    item = db.session.get(TrackedFlight, item_id)
    if item and item.user_id == current_user.id:
        db.session.delete(item)
        db.session.commit()
        flash('Removed from tracked flights.', 'info')
    return redirect(url_for('tracked_flights'))


# ============================================================
# PRICE ALERTS
# ============================================================

@app.route('/alerts', methods=['GET', 'POST'])
@login_required
def price_alerts():
    if request.method == 'POST':
        origin_iata = request.form.get('origin_iata', '').upper().strip()
        dest_iata = request.form.get('destination_iata', '').upper().strip()
        threshold = float(request.form.get('threshold_price', 0) or 0)
        if origin_iata and dest_iata:
            db.session.add(PriceAlert(
                user_id=current_user.id,
                origin_iata=origin_iata,
                destination_iata=dest_iata,
                threshold_price=threshold,
            ))
            db.session.commit()
            flash(f'Alert created for {origin_iata} - {dest_iata}', 'success')
        return redirect(url_for('price_alerts'))
    items = current_user.alerts.order_by(PriceAlert.created_at.desc()).all()
    return render_template('alerts.html', alerts=items)


@app.route('/alerts/<int:alert_id>/delete', methods=['POST'])
@login_required
def alert_delete(alert_id):
    a = db.session.get(PriceAlert, alert_id)
    if a and a.user_id == current_user.id:
        db.session.delete(a)
        db.session.commit()
        flash('Alert removed.', 'info')
    return redirect(url_for('price_alerts'))


# ============================================================
# SAVED SEARCHES
# ============================================================

@app.route('/saved-searches', methods=['GET', 'POST'])
@login_required
def saved_searches():
    if request.method == 'POST':
        label = request.form.get('label', 'My search')
        db.session.add(SavedSearch(
            user_id=current_user.id,
            label=label,
            origin_iata=request.form.get('origin_iata', '').upper(),
            destination_iata=request.form.get('destination_iata', '').upper(),
            passengers=int(request.form.get('passengers', 1) or 1),
            cabin_class=request.form.get('cabin_class', 'Economy'),
        ))
        db.session.commit()
        flash('Search saved.', 'success')
        return redirect(url_for('saved_searches'))
    items = current_user.saved_searches.order_by(SavedSearch.created_at.desc()).all()
    return render_template('saved_searches.html', searches=items)


@app.route('/saved-searches/<int:search_id>/delete', methods=['POST'])
@login_required
def saved_search_delete(search_id):
    s = db.session.get(SavedSearch, search_id)
    if s and s.user_id == current_user.id:
        db.session.delete(s)
        db.session.commit()
        flash('Saved search removed.', 'info')
    return redirect(url_for('saved_searches'))


# ============================================================
# PAYMENT METHODS
# ============================================================

@app.route('/payment-methods')
@login_required
def payment_methods():
    methods = current_user.payment_methods.order_by(
        PaymentMethod.is_default.desc(), PaymentMethod.created_at.desc()).all()
    return render_template('payment_methods.html', methods=methods)


@app.route('/payment-methods/add', methods=['GET', 'POST'])
@login_required
def payment_method_add():
    if request.method == 'POST':
        card_type = request.form.get('card_type', 'Visa').strip()
        card_number = request.form.get('card_number', '').replace(' ', '')
        last4 = card_number[-4:] if len(card_number) >= 4 else '0000'
        exp_month = int(request.form.get('exp_month', 12) or 12)
        exp_year = int(request.form.get('exp_year', 2028) or 2028)
        cardholder_name = request.form.get('cardholder_name', current_user.full_name).strip()
        is_default = bool(request.form.get('is_default'))
        if is_default:
            # un-default others
            for m in current_user.payment_methods:
                m.is_default = False
        elif current_user.payment_methods.count() == 0:
            is_default = True
        pm = PaymentMethod(
            user_id=current_user.id,
            card_type=card_type,
            last4=last4,
            exp_month=exp_month,
            exp_year=exp_year,
            cardholder_name=cardholder_name,
            is_default=is_default,
        )
        db.session.add(pm)
        db.session.commit()
        flash(f'{card_type} ending {last4} added.', 'success')
        return redirect(url_for('payment_methods'))
    return render_template('payment_method_add.html')


@app.route('/payment-methods/<int:pm_id>/delete', methods=['POST'])
@login_required
def payment_method_delete(pm_id):
    pm = db.session.get(PaymentMethod, pm_id)
    if pm and pm.user_id == current_user.id:
        db.session.delete(pm)
        db.session.commit()
        flash('Card removed.', 'info')
    return redirect(url_for('payment_methods'))


@app.route('/payment-methods/<int:pm_id>/set-default', methods=['POST'])
@login_required
def payment_method_set_default(pm_id):
    pm = db.session.get(PaymentMethod, pm_id)
    if pm and pm.user_id == current_user.id:
        for m in current_user.payment_methods:
            m.is_default = False
        pm.is_default = True
        db.session.commit()
        flash(f'{pm.card_type} ending {pm.last4} set as default.', 'success')
    return redirect(url_for('payment_methods'))


# ============================================================
# REVIEWS
# ============================================================

@app.route('/flight/<int:flight_id>/review', methods=['POST'])
@login_required
def review_submit(flight_id):
    flight = db.session.get(Flight, flight_id) or abort(404)
    rating = int(request.form.get('rating', 5))
    title = request.form.get('title', '').strip()
    body = request.form.get('body', '').strip()
    punctuality = int(request.form.get('punctuality', 5))
    comfort = int(request.form.get('comfort', 5))
    service = int(request.form.get('service', 5))
    r = Review(
        user_id=current_user.id,
        flight_id=flight_id,
        rating=max(1, min(5, rating)),
        title=title,
        body=body,
        punctuality=punctuality,
        comfort=comfort,
        service=service,
    )
    db.session.add(r)
    db.session.commit()
    flash('Thanks for your review!', 'success')
    return redirect(url_for('flight_detail', flight_id=flight_id))


@app.route('/review/<int:review_id>/delete', methods=['POST'])
@login_required
def review_delete(review_id):
    r = db.session.get(Review, review_id)
    if r and r.user_id == current_user.id:
        fid = r.flight_id
        db.session.delete(r)
        db.session.commit()
        flash('Review removed.', 'info')
        return redirect(url_for('flight_detail', flight_id=fid))
    return redirect(url_for('index'))


# ============================================================
# JSON API
# ============================================================

@app.route('/api/airports')
def api_airports():
    q = request.args.get('q', '').strip()
    query = Airport.query
    if q:
        ql = f"%{q}%"
        query = query.filter(or_(
            Airport.city.ilike(ql),
            Airport.iata.ilike(ql),
            Airport.name.ilike(ql),
        ))
    items = query.limit(20).all()
    return jsonify([{
        'iata': a.iata,
        'city': a.city,
        'country': a.country,
        'name': a.name,
    } for a in items])


@app.route('/api/flights/<origin>/<destination>')
def api_flights_route(origin, destination):
    o = Airport.query.filter_by(iata=origin.upper()).first()
    d = Airport.query.filter_by(iata=destination.upper()).first()
    if not o or not d:
        return jsonify([])
    flights = Flight.query.filter_by(origin_id=o.id, destination_id=d.id).order_by(Flight.price).limit(20).all()
    return jsonify([{
        'id': f.id,
        'airline': f.airline,
        'flight_number': f.flight_number,
        'price': f.price,
        'duration': f.duration_str,
        'stops': f.stops_str,
        'departure_time': f.departure_time,
        'arrival_time': f.arrival_time,
    } for f in flights])


# ============================================================
# STATIC INFO PAGES
# ============================================================

@app.route('/about')
def about():
    return render_template('about.html')


@app.route('/help')
@app.route('/help/')
def help_page():
    topic = request.args.get('topic', '').strip().lower()
    return render_template('help.html', topic=topic)


@app.route('/privacy')
def privacy():
    return render_template('privacy.html')


@app.route('/terms')
def terms():
    return render_template('privacy.html', _terms=True)


@app.route('/trips')
@login_required
def trips():
    # Real Google Flights surfaces a "Trips" tab summarising upcoming/past
    # bookings. Reuse the bookings list as the canonical trips view.
    bookings = (current_user.bookings
                .order_by(Booking.booked_at.desc()).all())
    return render_template('trips.html', bookings=bookings)


# ---- R3: trip management ("Manage trip" surface) ----
@app.route('/trips/<int:booking_id>/manage', methods=['GET', 'POST'])
@login_required
def trip_manage(booking_id):
    """Mirror of Google Flights' 'Manage trip' page: change date, add bag,
    select seat, request meal, or cancel. Read-mostly: only seat assignment
    and meal preference are persisted (cancel uses the existing route).
    """
    b = db.session.get(Booking, booking_id) or abort(404)
    if b.user_id != current_user.id:
        abort(403)
    if request.method == 'POST':
        action = request.form.get('action', '')
        if action == 'select-seat':
            seat = request.form.get('seat', '').strip().upper()
            if seat and len(seat) <= 4:
                for bi in b.items:
                    bi.seat = seat
                db.session.commit()
                flash(f'Seat {seat} assigned to PNR {b.pnr}.', 'success')
        elif action == 'add-bag':
            # Synthetic: bumps total_amount by $35 per bag, max +2 bags.
            try:
                bags = max(0, min(2, int(request.form.get('bags', '0'))))
            except ValueError:
                bags = 0
            fee = 35.0 * bags
            b.total_amount = round(b.total_amount + fee, 2)
            db.session.commit()
            flash(f'Added {bags} checked bag(s) (+${fee:.0f}).', 'success')
        elif action == 'change-date':
            # Synthetic re-issue: parse new_date, attach to outbound items'
            # flight reference if a matching flight exists, otherwise just
            # record the request as a flash. Real airlines hand off to OFP.
            try:
                new_date = datetime.strptime(
                    request.form.get('new_date', ''), '%Y-%m-%d').date()
            except ValueError:
                new_date = None
            if new_date:
                for bi in b.items:
                    orig = db.session.get(Flight, bi.flight_id)
                    if not orig:
                        continue
                    candidate = (Flight.query
                                 .filter_by(origin_id=orig.origin_id,
                                            destination_id=orig.destination_id,
                                            departure_date=new_date)
                                 .order_by(Flight.price)
                                 .first())
                    if candidate:
                        bi.flight_id = candidate.id
                        bi.price = candidate.price
                db.session.commit()
                flash(f'Trip date updated to {new_date.strftime("%b %d, %Y")}.', 'success')
            else:
                flash('Pick a valid date to change your trip.', 'error')
        return redirect(url_for('trip_manage', booking_id=booking_id))

    # Sample seat map (4 rows x 6 letters) for visual selection.
    seat_rows = list(range(10, 35))
    seat_letters = ['A', 'B', 'C', 'D', 'E', 'F']
    return render_template('trip_manage.html', booking=b,
                           seat_rows=seat_rows, seat_letters=seat_letters)


# ---- R3: baggage fees calculator ----
@app.route('/baggage-fees-calculator', methods=['GET', 'POST'])
def baggage_calculator():
    """Standalone surface (no auth) — picks airline + cabin + bag count and
    computes carry-on/checked/overweight totals. Real Google Flights links to
    each carrier's policy page; we synthesize from a small policy matrix.
    """
    # (airline_name, code, slug, carry_on_free, checked_first, checked_second,
    #  overweight, cabin_business_free, cabin_first_free)
    POLICIES = [
        ('Delta',                 'DL', 'delta',         True, 35,  45, 100, 2, 3),
        ('American Airlines',     'AA', 'american',      True, 40,  45, 100, 2, 3),
        ('United Airlines',       'UA', 'united',        True, 40,  50, 100, 2, 3),
        ('JetBlue',               'B6', 'jetblue',       True, 35,  45, 150, 2, 2),
        ('Southwest',             'WN', 'southwest',     True,  0,   0, 100, 0, 0),
        ('Alaska Airlines',       'AS', 'alaska',        True, 35,  45, 100, 2, 3),
        ('British Airways',       'BA', 'britishairways',True, 75,  90, 110, 2, 3),
        ('Air France',            'AF', 'airfrance',     True, 70,  90, 100, 2, 3),
        ('Lufthansa',             'LH', 'lufthansa',     True, 65,  90, 100, 2, 3),
        ('KLM',                   'KL', 'klm',           True, 70,  90, 100, 2, 3),
        ('Iberia',                'IB', 'iberia',        True, 55,  85, 100, 2, 3),
        ('Emirates',              'EK', 'emirates',      True,  0,   0,  85, 3, 3),  # 30kg/40kg incl.
        ('Qatar Airways',         'QR', 'qatar',         True,  0,   0,  85, 3, 3),
        ('Singapore Airlines',    'SQ', 'singapore',     True,  0,   0,  85, 3, 3),
        ('Japan Airlines',        'JL', 'jal',           True,  0,   0,  85, 3, 3),
        ('ANA',                   'NH', 'ana',           True,  0,   0,  85, 3, 3),
        ('Cathay Pacific',        'CX', 'cathay',        True,  0,   0,  85, 3, 3),
        ('Korean Air',            'KE', 'koreanair',     True,  0,   0,  85, 3, 3),
        ('Turkish Airlines',      'TK', 'turkish',       True,  0,   0,  85, 3, 3),
        ('Air Canada',            'AC', 'aircanada',     True, 35,  50, 100, 2, 3),
        ('Qantas',                'QF', 'qantas',        True,  0,   0,  85, 2, 3),
    ]
    result = None
    if request.method == 'POST':
        airline = request.form.get('airline', '').strip()
        cabin = request.form.get('cabin', 'Economy')
        try:
            bags = max(0, min(5, int(request.form.get('bags', '0'))))
            overweight = max(0, min(5, int(request.form.get('overweight', '0'))))
        except ValueError:
            bags, overweight = 0, 0
        match = next((p for p in POLICIES if p[0] == airline or p[1] == airline.upper()), None)
        if match:
            (name, code, _, _, first, second, ow, biz_free, first_free) = match
            if cabin == 'Business':
                free_count = biz_free
            elif cabin == 'First':
                free_count = first_free
            else:
                free_count = 0
            chargeable = max(0, bags - free_count)
            fee = 0.0
            if chargeable >= 1:
                fee += first
            if chargeable >= 2:
                fee += second
            if chargeable >= 3:
                fee += second + 50  # 3rd+ bag premium
            if chargeable >= 4:
                fee += second + 100
            fee += overweight * ow
            result = {
                'airline': name, 'code': code, 'cabin': cabin,
                'free_count': free_count, 'bags': bags, 'overweight': overweight,
                'chargeable': chargeable, 'total_fee': round(fee, 2),
                'overweight_each': ow,
            }
    return render_template('baggage_calculator.html', policies=POLICIES, result=result)


# ---- R3: explore-map alias ----
# Real Google Flights exposes the world map under /travel/explore. Our /explore
# already renders that surface. Add /tools/explore-map as a tools-shelf entry
# that points at the same view so users browsing the Tools page can find it.
@app.route('/tools/explore-map')
def tools_explore_map():
    return redirect(url_for('explore'))


# ---- R3: frequent-flyer programs reference ----
@app.route('/frequent-flyer-programs')
def frequent_flyer_programs():
    """Reference list of loyalty programs by airline. Helpful for tasks like
    'list which alliance Delta belongs to' or 'which program covers Lufthansa'.
    """
    PROGRAMS = [
        ('Delta', 'SkyMiles', 'SkyTeam', 'Silver -> Diamond Medallion'),
        ('American Airlines', 'AAdvantage', 'oneworld', 'Gold -> Executive Platinum'),
        ('United Airlines', 'MileagePlus', 'Star Alliance', 'Silver -> Global Services'),
        ('JetBlue', 'TrueBlue', 'None (partner network)', 'Mosaic 1-4'),
        ('Southwest', 'Rapid Rewards', 'None', 'A-List -> A-List Preferred'),
        ('Alaska Airlines', 'Mileage Plan', 'oneworld', 'MVP -> 100K'),
        ('British Airways', 'Executive Club', 'oneworld', 'Bronze -> Gold Guest List'),
        ('Air France', 'Flying Blue', 'SkyTeam', 'Silver -> Platinum'),
        ('KLM', 'Flying Blue', 'SkyTeam', 'Silver -> Platinum'),
        ('Lufthansa', 'Miles & More', 'Star Alliance', 'Frequent -> HON Circle'),
        ('Iberia', 'Iberia Plus', 'oneworld', 'Classic -> Platinum'),
        ('Emirates', 'Skywards', 'None (partner network)', 'Silver -> Platinum'),
        ('Qatar Airways', 'Privilege Club', 'oneworld', 'Silver -> Platinum'),
        ('Singapore Airlines', 'KrisFlyer', 'Star Alliance', 'Elite Silver -> PPS Club'),
        ('Japan Airlines', 'JAL Mileage Bank', 'oneworld', 'Crystal -> Diamond'),
        ('ANA', 'Mileage Club', 'Star Alliance', 'Bronze -> Diamond'),
        ('Cathay Pacific', 'Asia Miles', 'oneworld', 'Silver -> Diamond'),
        ('Korean Air', 'SKYPASS', 'SkyTeam', 'Silver -> Million Miler'),
        ('Turkish Airlines', 'Miles&Smiles', 'Star Alliance', 'Classic Plus -> Elite Plus'),
        ('Air Canada', 'Aeroplan', 'Star Alliance', '25K -> Super Elite'),
        ('Qantas', 'Frequent Flyer', 'oneworld', 'Silver -> Chairman'),
    ]
    return render_template('frequent_flyer.html', programs=PROGRAMS)


@app.route('/tools/calendar-cheapest')
def calendar_cheapest():
    """30-day price calendar for a single origin/destination pair. Returns a
    grid of (date, cheapest_price) for the requested route — mirror of
    Google Flights' price calendar."""
    origin = request.args.get('from', '').strip().upper()
    dest = request.args.get('to', '').strip().upper()
    grid_rows = []
    cheapest_date = None
    cheapest_price = None
    if origin and dest:
        o = Airport.query.filter_by(iata=origin).first()
        d = Airport.query.filter_by(iata=dest).first()
        if o and d:
            # Aggregate min price per departure_date for this route
            from sqlalchemy import func
            rows = (db.session.query(Flight.departure_date,
                                     func.min(Flight.price).label('p'))
                    .filter_by(origin_id=o.id, destination_id=d.id)
                    .group_by(Flight.departure_date)
                    .order_by(Flight.departure_date)
                    .limit(60)
                    .all())
            grid_rows = [(r[0], r[1]) for r in rows]
            if grid_rows:
                cheapest = min(grid_rows, key=lambda r: r[1])
                cheapest_date, cheapest_price = cheapest
    return render_template('calendar_cheapest.html',
                           origin=origin, dest=dest,
                           grid_rows=grid_rows,
                           cheapest_date=cheapest_date,
                           cheapest_price=cheapest_price)


# ============================================================
# ERROR HANDLERS
# ============================================================

@app.errorhandler(404)
def not_found(e):
    return render_template('404.html'), 404


@app.errorhandler(500)
def server_error(e):
    return render_template('500.html'), 500


# ============================================================
# SEED DATA
# ============================================================

def seed_database():
    from seed_data import seed_all
    seed_all(db, Airport, Flight)


def normalize_db_for_byte_identity():
    """Drop+reinsert all ix_* indexes in alphabetical order then VACUUM.
    Required so a rebuild on machine B produces byte-identical SQLite pages
    (SQLAlchemy emits CREATE INDEX from a set, whose iteration order depends
    on object id() — different per process). Idempotent.
    """
    from seed_data import normalize_seed_db_layout
    normalize_seed_db_layout(db)


def seed_benchmark_users():
    """Seed 4 benchmark users with payment methods, bookings, tracked flights and alerts.
    Idempotent — checks if alice already exists before creating."""
    if User.query.filter_by(email='alice.j@test.com').first():
        return  # already seeded

    # Pinned monotonic counter for booking timestamps (see _make_booking).
    _booking_counter = {'n': 0}

    def _make_user(email, pw, first, last, phone, passport, ff, dob_str):
        # NOTE: pw is unused on the seed path. We pin the bcrypt hash so two
        # rebuilds on different machines produce byte-identical instance_seed
        # SQLite files (bcrypt mixes a fresh salt every call, which otherwise
        # shifts the users.password_hash bytes). bcrypt.check_password_hash
        # validates 'TestPass123!' against this literal at login time.
        from seed_data import PINNED_PASSWORD_HASH
        u = User(
            email=email,
            password_hash=PINNED_PASSWORD_HASH,
            first_name=first,
            last_name=last,
            phone=phone,
            passport_number=passport,
            frequent_flyer=ff,
        )
        if dob_str:
            u.date_of_birth = datetime.strptime(dob_str, '%Y-%m-%d').date()
        db.session.add(u)
        db.session.flush()
        return u

    def _add_pm(user, card_type, last4, exp_m, exp_y, name, is_default=False):
        pm = PaymentMethod(
            user_id=user.id,
            card_type=card_type,
            last4=last4,
            exp_month=exp_m,
            exp_year=exp_y,
            cardholder_name=name,
            is_default=is_default,
        )
        db.session.add(pm)
        return pm

    def _get_flight(origin_iata, dest_iata, stops_filter=None, prefer_nonstop=True):
        o = Airport.query.filter_by(iata=origin_iata).first()
        d = Airport.query.filter_by(iata=dest_iata).first()
        if not o or not d:
            return None
        q = Flight.query.filter_by(origin_id=o.id, destination_id=d.id)
        if stops_filter is not None:
            q = q.filter(Flight.stops == stops_filter)
        elif prefer_nonstop:
            nonstop = q.filter(Flight.stops == 0).first()
            if nonstop:
                return nonstop
        return q.order_by(Flight.price).first()

    def _make_booking(user, flight, cabin='Economy', passengers=1,
                      status='confirmed', card_last4='4242', card_brand='Visa'):
        if not flight:
            return None
        from seed_data import MIRROR_REFERENCE_DATE
        pnr = make_pnr()
        price = flight.price * passengers
        taxes = round(price * 0.14, 2)
        total = round(price + taxes, 2)
        pax = [{'first_name': user.first_name, 'last_name': user.last_name}
               for _ in range(passengers)]
        b = Booking(
            user_id=user.id,
            pnr=pnr,
            status=status,
            trip_type='one-way',
            total_amount=total,
            taxes_fees=taxes,
            currency='USD',
            passenger_names_json=json.dumps(pax),
            contact_email=user.email,
            contact_phone=user.phone or '',
            payment_last4=card_last4,
            payment_brand=card_brand,
        )
        # Pinned booked_at so every rebuild matches byte-for-byte (Column
        # default=datetime.utcnow would otherwise capture wall-clock time).
        # Offset by counter so bookings sort sensibly in /trips listings.
        idx = _booking_counter['n']
        _booking_counter['n'] += 1
        b.booked_at = MIRROR_REFERENCE_DATE - timedelta(days=120 + idx)
        if status == 'cancelled':
            # Pinned offset (random.randint would advance the global random
            # stream between rebuilds and ripple through later seed calls).
            b.cancelled_at = MIRROR_REFERENCE_DATE - timedelta(days=5 + idx % 7)
        db.session.add(b)
        db.session.flush()
        bi = BookingItem(
            booking_id=b.id,
            flight_id=flight.id,
            leg='outbound',
            passengers=passengers,
            cabin_class=cabin,
            price=flight.price,
            seat=random.choice(['12A', '14C', '22F', '9D', '31B']),
        )
        db.session.add(bi)
        return b

    # ---- Alice Johnson — frequent flyer, prefers nonstop, Business when possible ----
    alice = _make_user(
        'alice.j@test.com', 'TestPass123!',
        'Alice', 'Johnson', '+1-212-555-0101',
        'US123456789', 'AA-FF-987654321', '1985-03-15')
    _add_pm(alice, 'Visa', '4321', 12, 2028, 'Alice Johnson', is_default=True)
    _add_pm(alice, 'Amex', '7890', 6, 2027, 'Alice Johnson')

    f1 = _get_flight('JFK', 'LHR', prefer_nonstop=True)
    f2 = _get_flight('JFK', 'CDG', prefer_nonstop=True)
    f3 = _get_flight('JFK', 'HND', prefer_nonstop=True)
    _make_booking(alice, f1, 'Business', 1, 'confirmed', '4321', 'Visa')
    _make_booking(alice, f2, 'Economy', 1, 'confirmed', '4321', 'Visa')
    _make_booking(alice, f3, 'Business', 1, 'cancelled', '7890', 'Amex')

    # tracked flights
    if f1:
        db.session.add(TrackedFlight(user_id=alice.id, flight_id=f1.id,
                                      starting_price=f1.price, target_price=round(f1.price * 0.85, 2)))
    # Add JFK->LAX tracked flight for T08 task (Alice should have 2 tracked flights: LHR to keep, LAX to remove)
    f_lax = _get_flight('JFK', 'LAX')
    if f_lax:
        db.session.add(TrackedFlight(user_id=alice.id, flight_id=f_lax.id,
                                      starting_price=f_lax.price, target_price=round(f_lax.price * 0.85, 2)))
    # price alerts
    db.session.add(PriceAlert(user_id=alice.id, origin_iata='JFK', destination_iata='LHR',
                               threshold_price=400.0, active=True))
    db.session.add(PriceAlert(user_id=alice.id, origin_iata='JFK', destination_iata='CDG',
                               threshold_price=420.0, active=True))

    # ---- Bob Chen — budget traveller, accepts 1-stop, Economy ----
    bob = _make_user(
        'bob.c@test.com', 'TestPass123!',
        'Bob', 'Chen', '+1-415-555-0202',
        'CN987654321', '', '1990-07-22')
    _add_pm(bob, 'Mastercard', '5678', 9, 2026, 'Bob Chen', is_default=True)
    _add_pm(bob, 'Visa', '1234', 3, 2029, 'Bob Chen')
    _add_pm(bob, 'Visa', '9999', 11, 2027, 'Bob Chen')

    f4 = _get_flight('SFO', 'LHR')
    f5 = _get_flight('LAX', 'HND')
    f6 = _get_flight('SFO', 'CDG')
    _make_booking(bob, f4, 'Economy', 1, 'confirmed', '5678', 'Mastercard')
    _make_booking(bob, f5, 'Economy', 1, 'confirmed', '1234', 'Visa')
    _make_booking(bob, f6, 'Economy', 1, 'cancelled', '5678', 'Mastercard')

    if f4:
        db.session.add(TrackedFlight(user_id=bob.id, flight_id=f4.id,
                                      starting_price=f4.price, target_price=round(f4.price * 0.80, 2)))
    db.session.add(PriceAlert(user_id=bob.id, origin_iata='SFO', destination_iata='LHR',
                               threshold_price=500.0, active=True))

    # ---- Carol Davis — family traveller, multi-pax, Economy/Premium ----
    carol = _make_user(
        'carol.d@test.com', 'TestPass123!',
        'Carol', 'Davis', '+1-312-555-0303',
        'US998877665', 'UA-FF-112233445', '1978-11-04')
    _add_pm(carol, 'Visa', '2468', 5, 2028, 'Carol Davis', is_default=True)
    _add_pm(carol, 'Mastercard', '1357', 8, 2026, 'Carol Davis')

    f7 = _get_flight('ORD', 'FCO')
    f8 = _get_flight('ORD', 'LHR')
    f9 = _get_flight('ORD', 'CDG')
    _make_booking(carol, f7, 'Economy', 3, 'confirmed', '2468', 'Visa')
    _make_booking(carol, f8, 'Economy', 4, 'confirmed', '2468', 'Visa')
    _make_booking(carol, f9, 'Economy', 2, 'cancelled', '1357', 'Mastercard')

    if f7:
        db.session.add(TrackedFlight(user_id=carol.id, flight_id=f7.id,
                                      starting_price=f7.price, target_price=round(f7.price * 0.88, 2)))
    if f8:
        db.session.add(TrackedFlight(user_id=carol.id, flight_id=f8.id,
                                      starting_price=f8.price, target_price=round(f8.price * 0.90, 2)))
    db.session.add(PriceAlert(user_id=carol.id, origin_iata='ORD', destination_iata='FCO',
                               threshold_price=450.0, active=True))

    # ---- David Kim — business traveller, Business/First, short booking windows ----
    david = _make_user(
        'david.k@test.com', 'TestPass123!',
        'David', 'Kim', '+1-202-555-0404',
        'KR112233445', 'DL-FF-556677889', '1982-05-30')
    _add_pm(david, 'Amex', '6543', 2, 2030, 'David Kim', is_default=True)
    _add_pm(david, 'Visa', '8765', 7, 2028, 'David Kim')
    _add_pm(david, 'Mastercard', '3210', 10, 2029, 'David Kim')

    f10 = _get_flight('JFK', 'DXB', prefer_nonstop=True)
    f11 = _get_flight('JFK', 'CDG', prefer_nonstop=True)
    f12 = _get_flight('BOS', 'BCN')
    _make_booking(david, f10, 'Business', 1, 'confirmed', '6543', 'Amex')
    _make_booking(david, f11, 'Business', 1, 'confirmed', '6543', 'Amex')
    _make_booking(david, f12, 'Economy', 1, 'cancelled', '8765', 'Visa')

    if f10:
        db.session.add(TrackedFlight(user_id=david.id, flight_id=f10.id,
                                      starting_price=f10.price, target_price=round(f10.price * 0.85, 2)))
    db.session.add(PriceAlert(user_id=david.id, origin_iata='JFK', destination_iata='DXB',
                               threshold_price=400.0, active=True))
    db.session.add(PriceAlert(user_id=david.id, origin_iata='JFK', destination_iata='CDG',
                               threshold_price=450.0, active=True))

    # ----------------------------------------------------------------
    # Phase 2 expansion: populate previously-empty tables
    # (saved_search, cart_item, review) and densify price_alert /
    # tracked_flight so account pages feel realistically populated for
    # benchmark scenarios that read or modify these entities.
    # ----------------------------------------------------------------
    REF_DATE = date(2026, 4, 15)  # pinned reference date for seed timestamps

    def _add_saved(user, label, origin, dest, departure_offset=None,
                   return_offset=None, passengers=1, cabin='Economy'):
        ss = SavedSearch(
            user_id=user.id,
            label=label,
            origin_iata=origin,
            destination_iata=dest,
            passengers=passengers,
            cabin_class=cabin,
        )
        if departure_offset is not None:
            ss.departure_date = REF_DATE + timedelta(days=departure_offset)
        if return_offset is not None:
            ss.return_date = REF_DATE + timedelta(days=return_offset)
        db.session.add(ss)
        return ss

    def _add_cart(user, origin, dest, cabin='Economy', passengers=1):
        f = _get_flight(origin, dest)
        if not f:
            return None
        ci = CartItem(
            user_id=user.id,
            flight_id=f.id,
            passengers=passengers,
            cabin_class=cabin,
        )
        db.session.add(ci)
        return ci

    def _add_tracked(user, origin, dest, discount=0.85):
        f = _get_flight(origin, dest)
        if not f:
            return None
        # Skip duplicates (TrackedFlight has no unique constraint but we
        # don't want noisy doubles for the same user+flight).
        existing = TrackedFlight.query.filter_by(
            user_id=user.id, flight_id=f.id).first()
        if existing:
            return existing
        tf = TrackedFlight(
            user_id=user.id,
            flight_id=f.id,
            starting_price=f.price,
            target_price=round(f.price * discount, 2),
        )
        db.session.add(tf)
        return tf

    def _add_alert(user, origin, dest, threshold, active=True):
        db.session.add(PriceAlert(
            user_id=user.id,
            origin_iata=origin,
            destination_iata=dest,
            threshold_price=float(threshold),
            active=active,
        ))

    def _add_review(user, origin, dest, rating, title, body,
                    punct=None, comfort=None, service=None):
        f = _get_flight(origin, dest)
        if not f:
            return None
        r = Review(
            user_id=user.id,
            flight_id=f.id,
            rating=rating,
            title=title,
            body=body,
            punctuality=punct if punct is not None else rating,
            comfort=comfort if comfort is not None else rating,
            service=service if service is not None else rating,
        )
        db.session.add(r)
        return r

    # ---- Saved searches (16 total: 4 per user) ----
    _add_saved(alice, 'NYC -> London business trip', 'JFK', 'LHR', 21, 28, 1, 'Business')
    _add_saved(alice, 'Paris weekend', 'JFK', 'CDG', 35, 39, 1, 'Premium')
    _add_saved(alice, 'Tokyo cherry blossoms', 'JFK', 'HND', 56, 70, 1, 'Business')
    _add_saved(alice, 'Dubai stopover', 'JFK', 'DXB', 90, 97, 1, 'Business')

    _add_saved(bob, 'Cheapest SFO -> LHR', 'SFO', 'LHR', 14, 28, 1, 'Economy')
    _add_saved(bob, 'LA to Tokyo deal hunt', 'LAX', 'HND', 30, 44, 1, 'Economy')
    _add_saved(bob, 'Paris on a budget', 'SFO', 'CDG', 45, 60, 1, 'Economy')
    _add_saved(bob, 'Bangkok backpack', 'SFO', 'BKK', 70, 90, 1, 'Economy')

    _add_saved(carol, 'Family trip to Rome', 'ORD', 'FCO', 60, 75, 4, 'Economy')
    _add_saved(carol, 'School-break London', 'ORD', 'LHR', 28, 42, 4, 'Economy')
    _add_saved(carol, 'Anniversary Paris', 'ORD', 'CDG', 120, 127, 2, 'Premium')
    _add_saved(carol, 'Barcelona summer', 'ORD', 'BCN', 100, 114, 4, 'Economy')

    _add_saved(david, 'Frequent Dubai client trips', 'JFK', 'DXB', 7, 11, 1, 'Business')
    _add_saved(david, 'Paris client meeting', 'JFK', 'CDG', 14, 17, 1, 'Business')
    _add_saved(david, 'Boston -> Barcelona summit', 'BOS', 'BCN', 21, 25, 1, 'Business')
    _add_saved(david, 'Seoul investor roadshow', 'JFK', 'ICN', 45, 52, 1, 'First')

    # ---- Cart items (11 total) ----
    _add_cart(alice, 'JFK', 'LHR', 'Business', 1)
    _add_cart(alice, 'JFK', 'CDG', 'Economy', 1)
    _add_cart(alice, 'JFK', 'HND', 'Business', 1)

    _add_cart(bob, 'SFO', 'LHR', 'Economy', 1)
    _add_cart(bob, 'LAX', 'HND', 'Economy', 1)
    _add_cart(bob, 'SFO', 'CDG', 'Economy', 1)

    _add_cart(carol, 'ORD', 'FCO', 'Economy', 3)
    _add_cart(carol, 'ORD', 'LHR', 'Economy', 4)
    _add_cart(carol, 'ORD', 'BCN', 'Economy', 2)

    _add_cart(david, 'JFK', 'DXB', 'Business', 1)
    _add_cart(david, 'JFK', 'CDG', 'Business', 1)

    # ---- Reviews (32 total: 8 per user across various routes) ----
    _add_review(alice, 'JFK', 'LHR', 5,
                'Exceptional transatlantic experience',
                'Smooth boarding, lie-flat seat was spotless, and the crew kept the cabin '
                'quiet for the overnight flight. Arrived rested and ready for meetings.',
                5, 5, 5)
    _add_review(alice, 'JFK', 'CDG', 4,
                'Solid Paris run',
                'On-time departure and good service. Could use more recent inflight movies '
                'but the meal was a step above what I expected on this route.',
                5, 4, 4)
    _add_review(alice, 'JFK', 'HND', 5,
                'Best long-haul I have flown this year',
                'Cabin crew checked in often without hovering. The seat reclined fully and '
                'the bedding felt almost hotel-grade. Will rebook this airline for Tokyo.',
                5, 5, 5)
    _add_review(alice, 'JFK', 'DXB', 4,
                'Reliable for business travel',
                'Priority boarding worked as advertised, lounge was crowded but the flight '
                'itself was punctual. Wi-fi held up for emails the whole way.',
                5, 4, 4)
    _add_review(alice, 'JFK', 'LGA', 3,
                'Fine for what it was',
                'Quick hop, gate was changed twice which was annoying, but the flight itself '
                'left within ten minutes of schedule. Nothing memorable either way.',
                4, 3, 3)
    _add_review(alice, 'BOS', 'LHR', 5,
                'Great red-eye option from Boston',
                'Boarded efficiently, dimmed cabin within an hour, and breakfast was served '
                'just before landing. Painless arrival into Heathrow Terminal 5.',
                5, 5, 5)
    _add_review(alice, 'LAX', 'HND', 4,
                'Comfortable Pacific crossing',
                'Seat was wider than I expected and the entertainment selection was deep. '
                'Only knock is that boarding took longer than necessary.',
                5, 4, 4)
    _add_review(alice, 'JFK', 'FCO', 4,
                'Good value to Rome',
                'Crew was friendly, food was hit-or-miss, but the flight was on time and '
                'baggage came out fast at FCO. I would book this fare again.',
                5, 4, 4)

    _add_review(bob, 'SFO', 'LHR', 3,
                'You get what you pay for',
                'Cheapest fare I could find, seat was tight but legroom was acceptable. '
                'Snacks were sold a la carte. Fine if you sleep through it.',
                4, 2, 3)
    _add_review(bob, 'LAX', 'HND', 4,
                'Solid economy for the price',
                'Surprised by how decent the meal service was. One-stop routing added two '
                'hours but the layover at HND was easy to navigate.',
                4, 4, 4)
    _add_review(bob, 'SFO', 'CDG', 3,
                'Average overnight',
                'Plane felt full and the seat in front reclined into my knees the whole '
                'flight. Crew was professional but stretched thin in the back of the cabin.',
                4, 2, 3)
    _add_review(bob, 'SFO', 'BKK', 4,
                'Best deal to Thailand right now',
                'Booked four weeks out for half the price of the direct option. Long layover '
                'in Tokyo but the connection was smooth and the second leg felt quick.',
                4, 4, 4)
    _add_review(bob, 'SFO', 'NRT', 4,
                'Great window seat to Tokyo',
                'Decent legroom for economy, free checked bag was a nice surprise. The '
                'Boeing 787 cabin pressure made the long flight far less draining.',
                4, 4, 5)
    _add_review(bob, 'LAX', 'CDG', 3,
                'OK but boarding was chaotic',
                'Two separate gate changes and a late inbound aircraft pushed our departure. '
                'Once airborne the flight was fine, but the start really set the wrong tone.',
                2, 3, 4)
    _add_review(bob, 'SFO', 'SEA', 5,
                'Perfect short hop',
                'Quick boarding, on-time departure, and the airline did not nickel-and-dime '
                'me for water. Wish more short-haul carriers worked this smoothly.',
                5, 5, 5)
    _add_review(bob, 'LAX', 'JFK', 4,
                'Transcontinental done right',
                'Power outlets at every seat actually worked, Wi-fi was usable for video '
                'calls, and the snack box was generous. Five hours felt like three.',
                5, 4, 4)

    _add_review(carol, 'ORD', 'FCO', 5,
                'Family trip made easy',
                'Travelling with three kids and the crew could not have been more helpful — '
                'priority boarding, kids meals on request, and patience with our circus.',
                5, 5, 5)
    _add_review(carol, 'ORD', 'LHR', 4,
                'Comfortable to London with the family',
                'Four of us in economy and the seats felt roomier than other carriers. Kids '
                'entertainment selection was strong enough to last the whole flight.',
                5, 4, 4)
    _add_review(carol, 'ORD', 'CDG', 4,
                'Romantic getaway, well executed',
                'Booked premium for our anniversary. Champagne on boarding, attentive crew, '
                'and the meal was genuinely good. Worth the upgrade for a special trip.',
                5, 4, 5)
    _add_review(carol, 'ORD', 'BCN', 4,
                'Smooth jump to Barcelona',
                'Late-night arrival but the flight was on time and the kids slept the whole '
                'way. Bags came out within twenty minutes — could not ask for more.',
                5, 4, 4)
    _add_review(carol, 'ATL', 'CDG', 3,
                'Tight seat pitch hurt this one',
                'Knees against the seat for nine hours is not the right way to do an Atlantic '
                'crossing. Crew was kind, food was fine, but I would not rebook this carrier.',
                4, 2, 4)
    _add_review(carol, 'DFW', 'LHR', 4,
                'Reliable transatlantic option',
                'Family of four, no surprises. Pre-ordering kids meals on the app actually '
                'worked, which saved us from a meltdown over chicken vs. pasta at 38,000 ft.',
                5, 4, 4)
    _add_review(carol, 'ORD', 'BOS', 5,
                'Easy short-haul',
                'Quick, on-time, and the kids loved that they got their own snacks. Wish '
                'more domestic flights ran this smoothly.',
                5, 5, 5)
    _add_review(carol, 'ORD', 'MIA', 4,
                'Vacation-mode flight',
                'Plane was warm and bright, crew was upbeat, and we landed on time. Great '
                'start to a Florida trip with the family.',
                5, 4, 5)

    _add_review(david, 'JFK', 'DXB', 5,
                'Worth every dollar in business',
                'Lie-flat seat, attentive service, and a quiet cabin for the full 14 hours. '
                'Landed in Dubai ready to head straight into client meetings.',
                5, 5, 5)
    _add_review(david, 'JFK', 'CDG', 4,
                'Solid business product',
                'Cabin crew was polished and the meal pacing was perfect for an overnight. '
                'Knock half a point for the older seat hardware compared to other long-hauls.',
                5, 4, 5)
    _add_review(david, 'BOS', 'BCN', 4,
                'Good Boston -> Barcelona option',
                'Direct flight, on time both ways, and the lounge at BOS was actually '
                'usable. Recommended for anyone heading to the summit next quarter.',
                5, 4, 4)
    _add_review(david, 'JFK', 'NRT', 5,
                'Best first class I have flown',
                'Private suite, restaurant-style dining on my own schedule, and the crew '
                'remembered my name across two meal services. Hard to go back to business.',
                5, 5, 5)
    _add_review(david, 'JFK', 'ICN', 4,
                'Reliable for Seoul roadshows',
                'Punctual, comfortable, and the airline lounge at JFK is excellent. The '
                'business cabin felt full but the crew never seemed rushed.',
                5, 4, 4)
    _add_review(david, 'JFK', 'HND', 5,
                'Top-tier transpacific',
                'Boarding by zone actually worked, the seat went fully horizontal, and I '
                'slept seven hours straight. Best long-haul rest I have had in years.',
                5, 5, 5)
    _add_review(david, 'JFK', 'FCO', 4,
                'Good Rome run',
                'Crew was friendly and the wine selection was a step above the usual. Only '
                'gripe is the entertainment system rebooted twice in flight.',
                5, 4, 4)
    _add_review(david, 'JFK', 'LHR', 4,
                'Dependable for London',
                'Pretty much what you would expect from a flagship business product — quick '
                'turnaround at JFK, attentive service, and an on-time landing at Heathrow.',
                5, 4, 5)

    # ---- R2 expansion: extra bookings (12 -> 60+) ----
    # Each tuple: (user, origin, dest, cabin, pax, status, last4, brand).
    # Routes pull from existing flight catalogue via _get_flight, so they
    # never reference missing rows. Distribute statuses 70% confirmed /
    # 15% flown / 10% cancelled / 5% ticketed so /trips listings look real.
    extra_bookings = [
        (alice, 'JFK', 'NRT', 'Business', 1, 'flown',     '4321', 'Visa'),
        (alice, 'JFK', 'FCO', 'Business', 1, 'flown',     '4321', 'Visa'),
        (alice, 'BOS', 'LHR', 'Economy',  1, 'confirmed', '7890', 'Amex'),
        (alice, 'JFK', 'AMS', 'Business', 1, 'confirmed', '4321', 'Visa'),
        (alice, 'JFK', 'BCN', 'Economy',  1, 'flown',     '4321', 'Visa'),
        (alice, 'JFK', 'ZRH', 'Business', 1, 'confirmed', '4321', 'Visa'),
        (alice, 'JFK', 'MIA', 'Economy',  1, 'flown',     '7890', 'Amex'),
        (alice, 'JFK', 'SFO', 'Business', 1, 'ticketed',  '4321', 'Visa'),
        (alice, 'JFK', 'LAX', 'Business', 1, 'confirmed', '4321', 'Visa'),
        (alice, 'JFK', 'DXB', 'Business', 2, 'confirmed', '4321', 'Visa'),
        (alice, 'JFK', 'ICN', 'Business', 1, 'flown',     '4321', 'Visa'),
        (alice, 'JFK', 'SIN', 'Business', 1, 'confirmed', '7890', 'Amex'),
        (alice, 'JFK', 'HKG', 'Business', 1, 'confirmed', '4321', 'Visa'),

        (bob,   'SFO', 'NRT', 'Economy',  1, 'flown',     '1234', 'Visa'),
        (bob,   'SFO', 'BKK', 'Economy',  1, 'flown',     '5678', 'Mastercard'),
        (bob,   'LAX', 'CDG', 'Economy',  1, 'confirmed', '5678', 'Mastercard'),
        (bob,   'LAX', 'NRT', 'Economy',  1, 'flown',     '1234', 'Visa'),
        (bob,   'SFO', 'BCN', 'Economy',  1, 'cancelled', '5678', 'Mastercard'),
        (bob,   'LAX', 'JFK', 'Economy',  1, 'flown',     '1234', 'Visa'),
        (bob,   'LAX', 'BOS', 'Economy',  1, 'confirmed', '9999', 'Visa'),
        (bob,   'SEA', 'LAX', 'Economy',  1, 'flown',     '9999', 'Visa'),
        (bob,   'SFO', 'SEA', 'Economy',  1, 'flown',     '5678', 'Mastercard'),
        (bob,   'LAX', 'LAS', 'Economy',  2, 'confirmed', '5678', 'Mastercard'),
        (bob,   'SFO', 'HNL', 'Economy',  1, 'flown',     '9999', 'Visa'),
        (bob,   'LAX', 'CUN', 'Economy',  1, 'confirmed', '1234', 'Visa'),
        (bob,   'SFO', 'MEX', 'Economy',  1, 'flown',     '1234', 'Visa'),

        (carol, 'ORD', 'CDG', 'Economy',  3, 'flown',     '2468', 'Visa'),
        (carol, 'ORD', 'AMS', 'Economy',  4, 'confirmed', '2468', 'Visa'),
        (carol, 'ORD', 'FCO', 'Economy',  3, 'flown',     '2468', 'Visa'),
        (carol, 'ATL', 'CDG', 'Premium',  2, 'flown',     '2468', 'Visa'),
        (carol, 'DFW', 'LHR', 'Premium',  4, 'confirmed', '2468', 'Visa'),
        (carol, 'ORD', 'BOS', 'Economy',  3, 'flown',     '1357', 'Mastercard'),
        (carol, 'ORD', 'MIA', 'Economy',  4, 'flown',     '2468', 'Visa'),
        (carol, 'ORD', 'LAX', 'Economy',  3, 'confirmed', '2468', 'Visa'),
        (carol, 'ORD', 'CUN', 'Economy',  4, 'confirmed', '1357', 'Mastercard'),
        (carol, 'DFW', 'CUN', 'Economy',  3, 'flown',     '1357', 'Mastercard'),
        (carol, 'ORD', 'SFO', 'Economy',  3, 'flown',     '2468', 'Visa'),
        (carol, 'ORD', 'LAS', 'Economy',  4, 'confirmed', '2468', 'Visa'),
        (carol, 'ATL', 'MIA', 'Economy',  3, 'flown',     '2468', 'Visa'),

        (david, 'JFK', 'NRT', 'Business', 1, 'flown',     '6543', 'Amex'),
        (david, 'JFK', 'ICN', 'Business', 1, 'flown',     '6543', 'Amex'),
        (david, 'JFK', 'HND', 'Business', 1, 'flown',     '6543', 'Amex'),
        (david, 'BOS', 'BCN', 'Business', 1, 'confirmed', '6543', 'Amex'),
        (david, 'JFK', 'SIN', 'First',    1, 'flown',     '6543', 'Amex'),
        (david, 'JFK', 'HKG', 'Business', 1, 'flown',     '6543', 'Amex'),
        (david, 'JFK', 'FCO', 'Business', 1, 'flown',     '8765', 'Visa'),
        (david, 'JFK', 'AMS', 'Business', 1, 'confirmed', '6543', 'Amex'),
        (david, 'JFK', 'ZRH', 'Business', 1, 'confirmed', '3210', 'Mastercard'),
        (david, 'JFK', 'CDG', 'Business', 1, 'ticketed',  '6543', 'Amex'),
        (david, 'JFK', 'LHR', 'First',    1, 'confirmed', '6543', 'Amex'),
        (david, 'JFK', 'DXB', 'Business', 1, 'flown',     '6543', 'Amex'),
        (david, 'JFK', 'TPE', 'Business', 1, 'flown',     '8765', 'Visa'),
    ]
    for user, o, d, cabin, pax, status, l4, brand in extra_bookings:
        f = _get_flight(o, d, prefer_nonstop=True)
        _make_booking(user, f, cabin, pax, status, l4, brand)

    # ---- Extra tracked flights (densify 6 -> 25+) ----
    _add_tracked(alice, 'JFK', 'CDG', 0.85)
    _add_tracked(alice, 'BOS', 'LHR', 0.87)
    _add_tracked(alice, 'JFK', 'FCO', 0.88)
    _add_tracked(alice, 'JFK', 'DXB', 0.83)
    _add_tracked(alice, 'JFK', 'HND', 0.85)

    _add_tracked(bob, 'LAX', 'HND', 0.78)
    _add_tracked(bob, 'SFO', 'CDG', 0.80)
    _add_tracked(bob, 'SFO', 'NRT', 0.78)
    _add_tracked(bob, 'SFO', 'BKK', 0.75)
    _add_tracked(bob, 'LAX', 'CDG', 0.80)

    _add_tracked(carol, 'ORD', 'BCN', 0.88)
    _add_tracked(carol, 'ORD', 'CDG', 0.85)
    _add_tracked(carol, 'DFW', 'LHR', 0.85)
    _add_tracked(carol, 'ATL', 'CDG', 0.87)

    _add_tracked(david, 'JFK', 'CDG', 0.85)
    _add_tracked(david, 'JFK', 'NRT', 0.85)
    _add_tracked(david, 'JFK', 'ICN', 0.85)
    _add_tracked(david, 'JFK', 'HND', 0.83)
    _add_tracked(david, 'BOS', 'BCN', 0.85)

    # ---- Extra price alerts (densify 6 -> 25+) ----
    _add_alert(alice, 'JFK', 'HND', 850.0)
    _add_alert(alice, 'JFK', 'FCO', 480.0)
    _add_alert(alice, 'BOS', 'LHR', 450.0)
    _add_alert(alice, 'JFK', 'DXB', 700.0)
    _add_alert(alice, 'LAX', 'HND', 750.0)

    _add_alert(bob, 'LAX', 'HND', 600.0)
    _add_alert(bob, 'SFO', 'CDG', 480.0)
    _add_alert(bob, 'SFO', 'BKK', 720.0)
    _add_alert(bob, 'SFO', 'NRT', 650.0)
    _add_alert(bob, 'LAX', 'CDG', 520.0)

    _add_alert(carol, 'ORD', 'LHR', 420.0)
    _add_alert(carol, 'ORD', 'CDG', 460.0)
    _add_alert(carol, 'ORD', 'BCN', 500.0)
    _add_alert(carol, 'DFW', 'LHR', 470.0)

    _add_alert(david, 'JFK', 'NRT', 950.0)
    _add_alert(david, 'JFK', 'HND', 920.0)
    _add_alert(david, 'JFK', 'ICN', 880.0)
    _add_alert(david, 'BOS', 'BCN', 520.0, active=False)
    _add_alert(david, 'JFK', 'FCO', 500.0)

    # ----------------------------------------------------------------
    # R3 expansion: densify reviews, saved searches, and price alerts so
    # account pages and per-airline review aggregates feel realistic. Also
    # adds reviews against newly-added regional airports (LAX/SAN/CLT/MIA etc).
    # ----------------------------------------------------------------
    _r3_extra_reviews = [
        # Alice — additional long-haul + transatlantic experience
        (alice, 'JFK', 'AMS', 5, 'Easy connection through Schiphol',
         'Boarding wrapped quickly, lie-flat seat had a working privacy screen, '
         'and the breakfast omelet was honestly better than what most hotels serve. '
         'Bag was on the carousel by the time I cleared customs.', 5, 5, 5),
        (alice, 'JFK', 'ZRH', 4, 'Smooth Swiss overnight',
         'Cabin was quiet within 30 minutes of departure and the duvet plus mattress '
         'topper actually let me sleep five hours. Wine pairing with the late-night '
         'snack was a nice touch.', 5, 4, 5),
        (alice, 'JFK', 'ICN', 5, 'Top transpacific business product',
         'Suite door, full mattress, restaurant-style dining whenever I wanted. '
         'Crew was attentive without hovering. I would happily fly this 14 hours '
         'again next month.', 5, 5, 5),
        (alice, 'JFK', 'SIN', 4, 'Ultra-long-haul handled well',
         'Eighteen hours is a lot, but the meal pacing kept me on my arrival '
         'schedule. Only knock is that the entertainment library could use more '
         'recent releases.', 5, 4, 5),
        (alice, 'JFK', 'HKG', 5, 'Best connection through HKG',
         'Lounge access in Hong Kong was excellent and the inbound flight was on '
         'time despite weather over the Pacific. Crew on this route is consistently '
         'one of the best.', 5, 5, 5),
        (alice, 'JFK', 'TLV', 4, 'Solid trip to Tel Aviv',
         'Long-haul went smoothly, security screening at JFK for TLV was thorough '
         'but moved fast. Lie-flat seat was comfortable for sleeping.', 5, 4, 4),
        (alice, 'JFK', 'BCN', 4, 'Direct to Barcelona done right',
         'Quick taxi, on-time pushback, and a smooth red-eye to BCN. Arrival '
         'gate connected directly to baggage claim — perfect for an 8am business '
         'meeting.', 5, 4, 4),
        (alice, 'JFK', 'CDG', 5, 'Repeat customer for a reason',
         'Crew remembered preferences from a prior flight without me mentioning '
         'it. Champagne on boarding, the seat-side closet, and the breakfast '
         'pastry all made this feel premium.', 5, 5, 5),
        (alice, 'LAX', 'HND', 5, 'Pacific crossing in true comfort',
         'Cabin felt new — the door on the suite plus the wireless charging pad '
         'were nice touches. Slept seven hours and woke up genuinely rested.', 5, 5, 5),
        (alice, 'JFK', 'DOH', 4, 'New Doha service',
         'Inaugural-week flight had a few teething issues at gate boarding but '
         'once on board the experience was excellent. The shower spa in DOH on '
         'connection was a delightful surprise.', 4, 5, 5),
        (alice, 'JFK', 'YVR', 4, 'Cross-continent comfort',
         'JFK to Vancouver felt like a short hop in business — clean cabin, '
         'attentive crew, and an on-time arrival. Good option for the once-a-year '
         'visit to family.', 5, 4, 4),
        (alice, 'JFK', 'YYZ', 3, 'Short hop, expected nothing fancy',
         'Quick flight, basic premium cabin. Crew was friendly but the food was '
         'a sad cheese plate. Fine for the price and the time saved.', 4, 3, 4),
        (alice, 'JFK', 'LGB', 3, 'New route, ironing things out',
         'Boarding was a mess at JFK because the gate kept changing. Once on board '
         'everything was fine. The IFE froze twice but the crew rebooted it both '
         'times without complaint.', 3, 3, 4),
        (alice, 'JFK', 'SFO', 4, 'Coast-to-coast in business',
         'Worth the upgrade — full lie-flat for the red-eye, breakfast was '
         'restaurant-quality, and I landed at SFO ready to head straight into a '
         '9am keynote.', 5, 4, 5),
        (alice, 'JFK', 'MIA', 4, 'Easy Miami escape',
         'Short flight, decent meal in domestic first, and the cabin crew were '
         'warm without being chatty. Bags came out before I made it to the '
         'carousel.', 5, 4, 4),
        # Bob — budget traveller covering more routes
        (bob, 'SFO', 'HNL', 5, 'Beach trip for a fair price',
         'Flight was packed but the crew kept everyone moving. Free movies on the '
         'seat-back screen and the snack box was actually pretty good. Already '
         'booked the return.', 4, 5, 5),
        (bob, 'LAX', 'CUN', 4, 'Cheap Cancun runs',
         'Boarding scrum at LAX is what it is, but once on the plane the flight '
         'was smooth and on time. Saved a couple hundred dollars vs the direct '
         'competitor.', 4, 4, 4),
        (bob, 'SFO', 'MEX', 3, 'Service was fine, plane felt tight',
         'Got a middle seat at the back of the cabin. Engine noise was loud and '
         'the seat in front reclined a lot. Got me there safely though.', 4, 2, 3),
        (bob, 'SFO', 'SEA', 4, 'Quick and easy',
         'Boarded in 12 minutes, wheels-up on time, and I was through SEA security '
         '90 minutes later. Best short-haul experience in years.', 5, 4, 4),
        (bob, 'LAX', 'BOS', 4, 'Transcon survived',
         'Six hours of cramped seating but the airline kept us hydrated and the '
         'pilot kept us informed. Power outlet at every seat actually worked.', 5, 3, 5),
        (bob, 'SEA', 'LAX', 5, 'Pacific Northwest hop',
         'Boarded fast, on time, and the crew was genuinely friendly. Wish '
         'every short-haul flight ran like this one.', 5, 5, 5),
        (bob, 'LAX', 'LAS', 4, 'Vegas weekender',
         'Got the cheapest seat and it was fine. Quick flight, on-time arrival, '
         'and the airport tram at LAS made everything easy. Solid value.', 5, 4, 4),
        (bob, 'SFO', 'YVR', 3, 'Cross-border short hop',
         'Border procedures added 30 minutes total but the flight itself was '
         'short and smooth. Premium economy on this route is not worth the upcharge.', 4, 3, 4),
        (bob, 'LAX', 'YYZ', 4, 'Toronto trip on a budget',
         'Cleared US preclearance at LAX which made arrival in YYZ effortless. '
         'Seat pitch is what it is on economy but I had an aisle so it worked.', 5, 3, 4),
        (bob, 'SFO', 'DEN', 4, 'Mountain views',
         'Window seat over the Sierra Nevada was worth the trip on its own. Crew '
         'was professional, snacks were generous, and we landed early. No complaints.', 5, 4, 4),
        (bob, 'LAX', 'PHX', 4, 'Quick Arizona run',
         'Forty-five minute flight, in and out without drama. Boarding pass on '
         'my phone, baggage carry-on only, perfect short trip.', 5, 4, 4),
        (bob, 'LAX', 'SAN', 5, 'Easier than driving I-5',
         'Booked last-minute and still got a decent fare. Flight was 25 minutes '
         'in the air, baggage came out fast, and I beat the freeway traffic.', 5, 5, 5),
        (bob, 'SFO', 'PDX', 4, 'PNW connector',
         'Reliable short-haul. Crew was warm, beverages came around twice in a '
         '90-minute flight, and the airport at PDX is a delight.', 5, 4, 5),
        # Carol — family travel reviews
        (carol, 'ORD', 'NRT', 4, 'Long flight, kids did great',
         'Pre-ordered kids meals worked perfectly and the crew gave my youngest '
         'extra snacks without being asked. Direct flight beats any one-stop on '
         'this route.', 5, 4, 5),
        (carol, 'ORD', 'HND', 4, 'Tokyo with the whole family',
         'Pre-flight planning paid off — boarding was painless and the crew was '
         'kind to the kids. Long-haul economy is what it is but the IFE library '
         'kept the youngest happy.', 5, 4, 5),
        (carol, 'ORD', 'AMS', 5, 'Family magic to Amsterdam',
         'Hard to get a transatlantic right with four kids but this one nailed it. '
         'Bassinets for the youngest, kids meals on time, friendly crew. Will '
         'rebook for next summer.', 5, 5, 5),
        (carol, 'ORD', 'DUB', 4, 'Dublin family week',
         'Eight hours felt long but the crew handled us professionally. Bags came '
         'out within 20 minutes and the airport was easy to navigate with a stroller.', 5, 4, 4),
        (carol, 'DFW', 'CUN', 5, 'Beach week win',
         'Direct flight saved us a connection nightmare. The crew was warm with '
         'the kids and the timing worked perfectly with the all-inclusive checkin.', 5, 5, 5),
        (carol, 'ATL', 'PUJ', 4, 'Caribbean family run',
         'Smooth flight, on-time arrival in Punta Cana, and the airline made it '
         'easy to roll all four of our seats together. Good experience overall.', 5, 4, 4),
        (carol, 'ORD', 'SFO', 4, 'Transcontinental family flight',
         'Four hours felt longer than it should but the crew was great and the '
         'seat-back screens kept the kids occupied. Bags came out fast in SFO.', 5, 4, 4),
        (carol, 'ORD', 'LAS', 4, 'Vegas family adventure',
         'Flight was full but the crew handled boarding efficiently. Free '
         'entertainment library was a lifesaver for the kids on the flight back.', 4, 4, 4),
        (carol, 'ORD', 'PHX', 4, 'Spring break to Arizona',
         'Boarding was quick, the kids loved the window seats over the desert, '
         'and we landed 20 minutes early. Crew was patient with our circus.', 5, 4, 5),
        (carol, 'DFW', 'MCO', 4, 'Orlando theme park trip',
         'Easy direct flight, friendly crew, decent kids snacks. Pre-paying for '
         'seats together was worth every penny.', 5, 4, 4),
        (carol, 'ATL', 'DEN', 4, 'Mountain getaway',
         'Smooth flight, on-time both ways, and the crew was warm. The view of '
         'the Rockies on descent into DEN kept the kids glued to the window.', 5, 4, 4),
        (carol, 'ORD', 'YYZ', 4, 'Quick run to Toronto',
         'Short cross-border hop, no surprises, easy customs at YYZ. Bags came '
         'out fast. Solid family-friendly carrier.', 5, 4, 4),
        # David — premium-cabin business reviews on new long-hauls
        (david, 'JFK', 'PVG', 5, 'Top-tier Shanghai flight',
         'Suite was spacious, restaurant-style dining at my own pace, and the '
         'crew remembered me from a prior trip. Slept 8 hours straight, landed '
         'in PVG ready to head into back-to-back client meetings.', 5, 5, 5),
        (david, 'JFK', 'BOM', 4, 'Long-haul to Mumbai',
         'Sixteen hours is long but the lie-flat product is dialed in. Lounge '
         'access at JFK and BOM made the connection painless. Will rebook for '
         'next quarter.', 5, 5, 4),
        (david, 'JFK', 'DEL', 5, 'Excellent Delhi service',
         'New aircraft, attentive crew, and the meal service felt restaurant-grade. '
         'The Indian thali option was a thoughtful touch and the wine list was '
         'genuinely good.', 5, 5, 5),
        (david, 'JFK', 'SYD', 4, 'Ultra-long-haul handled well',
         'Twenty-plus hours is brutal but the crew kept the cabin quiet, paced '
         'meals for sleep, and the suite was as good as advertised. Worth the '
         'redemption.', 5, 5, 4),
        (david, 'JFK', 'GRU', 5, 'Best South America service I have flown',
         'Lie-flat for the overnight to GRU, lounge access on both ends, and the '
         'breakfast service was paced perfectly. Highly recommended for the route.', 5, 5, 5),
        (david, 'BOS', 'LHR', 4, 'Quick Boston transatlantic',
         'Direct flight beats any connection on this route. Crew was polished, '
         'meal was timed for an early morning arrival, and immigration at LHR '
         'was fast.', 5, 4, 5),
        (david, 'BOS', 'CDG', 4, 'Solid Paris overnight',
         'Lie-flat seat slept seven hours, breakfast was light but tasty, and '
         'the cabin crew never seemed rushed even on a full flight. Will rebook.', 5, 5, 4),
        (david, 'JFK', 'GVA', 4, 'Geneva business trip',
         'Smooth direct flight, on time both ways, lounge at JFK was excellent. '
         'Knock half a point for older seat hardware compared to flagship aircraft.', 5, 4, 4),
        (david, 'JFK', 'MUC', 5, 'Munich done right',
         'Cabin was new, suite door was a nice touch, and the breakfast pastry '
         'was honestly better than most cafes. Crew remembered my coffee from '
         'first service.', 5, 5, 5),
        (david, 'BOS', 'AMS', 5, 'Schiphol connection',
         'Direct Boston to Amsterdam in business is criminally underrated. Quick '
         'boarding, great seat, attentive crew, and AMS is a breeze for connections.', 5, 5, 5),
        (david, 'JFK', 'YVR', 4, 'Vancouver short-haul in business',
         'Five-hour cross-continent flight passed quickly. Cabin was clean, '
         'lunch service was decent, and I got real work done with the wifi.', 5, 4, 4),
        (david, 'JFK', 'EZE', 4, 'Buenos Aires overnight',
         'Eleven hours south felt easier than expected — lie-flat seat plus the '
         'right meal pacing meant I slept seven hours. Lounge at EZE was a nice '
         'surprise.', 5, 4, 5),
        # Route-level reviews from new users implicitly (cover newly-added airports)
        (alice, 'JFK', 'OPO', 4, 'Porto direct service',
         'Boarding was quick, crew was warm, and the breakfast pastry was a '
         'genuine highlight. New aircraft on this route makes a real difference.', 5, 4, 4),
        (bob, 'LAX', 'GUA', 3, 'Guatemala City run',
         'Cheap fare to Central America, no surprises. Seat was tight but the '
         'flight was on time and bags arrived intact.', 4, 3, 3),
        (carol, 'ORD', 'BSB', 4, 'Brasilia trip',
         'Long flight, decent meal service in economy, and the family was '
         'comfortable enough. Bags took 45 minutes which was annoying.', 4, 4, 4),
        (david, 'JFK', 'RUH', 5, 'Riyadh business trip',
         'Lie-flat product was excellent, crew was polished and discreet, and '
         'the late-night arrival was paced perfectly for a noon client meeting.', 5, 5, 5),
        # Negative / mixed reviews so aggregates feel real
        (alice, 'JFK', 'SAN', 2, 'Two delays back to back',
         'Mechanical issue at JFK then a weather hold meant we arrived three '
         'hours late. Crew apologized but the airline never offered compensation '
         'or rebooking help. Disappointing.', 1, 3, 2),
        (bob, 'SFO', 'JFK', 2, 'Old aircraft, broken IFE',
         'Got stuck with a refurb plane where half the seatback screens did not '
         'work. Crew was apologetic but there was no real fix for a six-hour '
         'transcon flight.', 4, 2, 3),
        (carol, 'DFW', 'CDG', 2, 'Service felt strained',
         'Family of four in economy, flight was packed, crew was clearly '
         'stretched. Kids meals never arrived and the dinner ran out before they '
         'got to our row.', 2, 2, 2),
        (david, 'JFK', 'CDG', 2, 'Second flight, much worse',
         'Booked the same route as last month — different crew, totally different '
         'experience. Cabin felt run-down, breakfast was a cold pastry, and the '
         'lie-flat seat had a torn cushion.', 3, 2, 2),
    ]
    for u, o, d, rating, title, body, p, c, s in _r3_extra_reviews:
        _add_review(u, o, d, rating, title, body, p, c, s)

    # ---- R3: additional saved searches (16 -> 50+) ----
    _add_saved(alice, 'Athens spring trip',   'JFK', 'ATH', 60,  72,  1, 'Premium')
    _add_saved(alice, 'Singapore client run', 'JFK', 'SIN', 30,  37,  1, 'Business')
    _add_saved(alice, 'Hong Kong layover',    'JFK', 'HKG', 45,  52,  1, 'Business')
    _add_saved(alice, 'Zurich Alps escape',   'JFK', 'ZRH', 80,  90,  1, 'Premium')
    _add_saved(alice, 'Doha winter route',    'JFK', 'DOH', 14,  21,  1, 'Business')
    _add_saved(alice, 'Vancouver family',     'JFK', 'YVR', 100, 110, 2, 'Premium')
    _add_saved(alice, 'Rome culinary',        'JFK', 'FCO', 150, 158, 1, 'Business')
    _add_saved(alice, 'Stockholm summer',     'JFK', 'ARN', 180, 192, 1, 'Premium')

    _add_saved(bob, 'Honolulu surf',          'SFO', 'HNL', 25,  35,  1, 'Economy')
    _add_saved(bob, 'Tokyo backpacker',       'SFO', 'NRT', 35,  55,  1, 'Economy')
    _add_saved(bob, 'Seoul food tour',        'SFO', 'ICN', 50,  60,  1, 'Economy')
    _add_saved(bob, 'Mexico City weekend',    'SFO', 'MEX', 18,  21,  1, 'Economy')
    _add_saved(bob, 'Vegas getaway',          'LAX', 'LAS', 14,  17,  1, 'Economy')
    _add_saved(bob, 'Cancun reset',           'LAX', 'CUN', 25,  32,  1, 'Economy')
    _add_saved(bob, 'NYC visit',              'LAX', 'JFK', 90,  97,  1, 'Economy')
    _add_saved(bob, 'Portland weekend',       'SFO', 'PDX',  9,  12,  1, 'Economy')

    _add_saved(carol, 'Amsterdam school break','ORD','AMS', 90, 104, 4, 'Economy')
    _add_saved(carol, 'Dublin family week',   'ORD', 'DUB', 110, 120, 4, 'Economy')
    _add_saved(carol, 'Orlando theme parks',  'DFW', 'MCO', 25,  32,  4, 'Economy')
    _add_saved(carol, 'Vegas with the kids',  'ORD', 'LAS', 30,  35,  4, 'Economy')
    _add_saved(carol, 'Punta Cana resort',    'ATL', 'PUJ', 50,  58,  4, 'Economy')
    _add_saved(carol, 'Mexico family trip',   'ORD', 'MEX', 80,  90,  4, 'Economy')
    _add_saved(carol, 'Phoenix spring break', 'ORD', 'PHX', 21,  28,  4, 'Economy')

    _add_saved(david, 'Shanghai roadshow',    'JFK', 'PVG', 12,  18,  1, 'Business')
    _add_saved(david, 'Mumbai client meeting','JFK', 'BOM', 18,  25,  1, 'Business')
    _add_saved(david, 'Delhi expansion',      'JFK', 'DEL', 30,  37,  1, 'Business')
    _add_saved(david, 'Sydney offsite',       'JFK', 'SYD', 60,  72,  1, 'Business')
    _add_saved(david, 'Sao Paulo summit',     'JFK', 'GRU', 40,  47,  1, 'Business')
    _add_saved(david, 'Munich client',        'JFK', 'MUC', 21,  25,  1, 'Business')
    _add_saved(david, 'Geneva talks',         'JFK', 'GVA', 28,  31,  1, 'First')
    _add_saved(david, 'Amsterdam summit',     'BOS', 'AMS', 35,  42,  1, 'Business')
    _add_saved(david, 'Riyadh visit',         'JFK', 'RUH', 50,  58,  1, 'Business')
    _add_saved(david, 'Buenos Aires offsite', 'JFK', 'EZE', 60,  70,  1, 'Business')
    _add_saved(david, 'Hong Kong investors',  'JFK', 'HKG', 75,  82,  1, 'First')
    _add_saved(david, 'Singapore expansion',  'JFK', 'SIN', 90,  100, 1, 'First')

    # ---- R3: additional price alerts (25 -> 100+) ----
    _alert_specs = [
        # alice
        ('alice','JFK','AMS', 520.0, True),  ('alice','JFK','ZRH', 540.0, True),
        ('alice','JFK','SIN',1180.0, True),  ('alice','JFK','HKG', 980.0, True),
        ('alice','JFK','DOH', 720.0, True),  ('alice','JFK','ATH', 540.0, True),
        ('alice','JFK','BCN', 480.0, True),  ('alice','JFK','TLV', 720.0, True),
        ('alice','JFK','ICN',1020.0, True),  ('alice','JFK','PVG', 980.0, True),
        ('alice','BOS','CDG', 470.0, True),  ('alice','JFK','MAD', 460.0, False),
        ('alice','JFK','VIE', 510.0, True),  ('alice','JFK','PRG', 540.0, False),
        ('alice','JFK','OPO', 460.0, True),  ('alice','JFK','LIS', 460.0, True),
        ('alice','JFK','BUD', 540.0, False),
        # bob
        ('bob','SFO','HNL', 280.0, True),    ('bob','SFO','MEX', 240.0, True),
        ('bob','SFO','PDX', 140.0, True),    ('bob','SFO','SEA', 120.0, True),
        ('bob','LAX','LAS', 110.0, True),    ('bob','LAX','CUN', 300.0, True),
        ('bob','LAX','PHX', 130.0, True),    ('bob','LAX','SAN',  90.0, True),
        ('bob','SFO','YVR', 200.0, True),    ('bob','LAX','BOS', 320.0, True),
        ('bob','LAX','JFK', 280.0, True),    ('bob','SFO','DEN', 220.0, True),
        ('bob','LAX','SFO', 100.0, True),    ('bob','LAX','SEA', 150.0, True),
        ('bob','SFO','LAX', 100.0, True),    ('bob','LAX','PDX', 130.0, False),
        # carol
        ('carol','ORD','AMS', 480.0, True),  ('carol','ORD','DUB', 460.0, True),
        ('carol','ORD','MCO', 220.0, True),  ('carol','ORD','LAS', 240.0, True),
        ('carol','ORD','PHX', 220.0, True),  ('carol','ORD','SFO', 260.0, True),
        ('carol','ORD','LAX', 240.0, True),  ('carol','ATL','CDG', 460.0, True),
        ('carol','ATL','PUJ', 360.0, True),  ('carol','ATL','MIA', 180.0, True),
        ('carol','DFW','MCO', 220.0, True),  ('carol','DFW','LAS', 220.0, True),
        ('carol','DFW','CUN', 280.0, True),  ('carol','DFW','LHR', 480.0, False),
        ('carol','ORD','BSB', 700.0, True),  ('carol','ORD','GRU', 740.0, True),
        # david
        ('david','JFK','PVG', 980.0, True),  ('david','JFK','BOM', 920.0, True),
        ('david','JFK','DEL', 960.0, True),  ('david','JFK','SYD',1480.0, True),
        ('david','JFK','GRU', 980.0, True),  ('david','JFK','MUC', 560.0, True),
        ('david','JFK','GVA', 580.0, True),  ('david','JFK','AMS', 520.0, True),
        ('david','BOS','AMS', 480.0, True),  ('david','BOS','LHR', 480.0, True),
        ('david','BOS','CDG', 480.0, True),  ('david','JFK','RUH',1180.0, True),
        ('david','JFK','EZE', 920.0, True),  ('david','JFK','HKG', 980.0, True),
        ('david','JFK','SIN',1180.0, True),  ('david','JFK','BKK',1080.0, False),
        ('david','JFK','DXB',1080.0, False),
    ]
    _user_obj = {'alice': alice, 'bob': bob, 'carol': carol, 'david': david}
    for who, o, d, thresh, active in _alert_specs:
        _add_alert(_user_obj[who], o, d, thresh, active=active)

    # R3 bonus alerts to clear 100 total across all four users.
    _bonus_alerts = [
        ('alice','JFK','SYD',1480.0, True),  ('alice','LAX','SYD',1380.0, True),
        ('alice','JFK','BKK',1080.0, True),  ('alice','JFK','MNL',1180.0, False),
        ('bob','LAX','HNL', 320.0, True),    ('bob','SFO','HNL', 280.0, True),
        ('bob','LAX','HND', 580.0, True),    ('bob','SFO','HND', 560.0, True),
        ('carol','ORD','DXB',900.0, True),   ('carol','ATL','LAS',240.0, True),
        ('david','BOS','FCO', 540.0, True),  ('david','JFK','MAD', 520.0, True),
        ('david','JFK','SAW',780.0, True),
    ]
    for who, o, d, thresh, active in _bonus_alerts:
        _add_alert(_user_obj[who], o, d, thresh, active=active)

    # ---- R3: programmatic review fill — guarantee 200+ reviews ----
    # Hand-written reviews cover named experiences. To hit 200+ for
    # airline-aggregate questions ("what is the average rating for route X")
    # we fill remaining slots with templated short-form reviews. Each review
    # uses a deterministic random.Random seeded with (user_id, origin, dest)
    # so rebuilds are byte-stable.
    import random as _r3rand
    _r3_routes = [
        ('JFK','LHR'),('JFK','CDG'),('JFK','HND'),('JFK','NRT'),('JFK','DXB'),
        ('JFK','FCO'),('JFK','BCN'),('JFK','AMS'),('JFK','ZRH'),('JFK','ICN'),
        ('JFK','SIN'),('JFK','HKG'),('JFK','PVG'),('JFK','SYD'),('JFK','MAD'),
        ('JFK','LIS'),('JFK','MEX'),('JFK','CUN'),('JFK','MIA'),('JFK','LAX'),
        ('JFK','SFO'),('JFK','SEA'),('JFK','YYZ'),('JFK','YVR'),('JFK','ATH'),
        ('JFK','PRG'),('JFK','DUB'),('JFK','DOH'),('JFK','BKK'),('JFK','GIG'),
        ('SFO','LHR'),('SFO','CDG'),('SFO','HND'),('SFO','NRT'),('SFO','PVG'),
        ('SFO','SYD'),('SFO','HNL'),('SFO','MEX'),('SFO','BCN'),('SFO','FCO'),
        ('SFO','BKK'),('SFO','AMS'),('SFO','SEA'),('SFO','LAX'),('SFO','JFK'),
        ('LAX','HND'),('LAX','NRT'),('LAX','SYD'),('LAX','HKG'),('LAX','PEK'),
        ('LAX','CDG'),('LAX','CUN'),('LAX','PVR'),('LAX','LAS'),('LAX','SFO'),
        ('LAX','BOS'),('LAX','JFK'),('LAX','MIA'),
        ('ORD','LHR'),('ORD','CDG'),('ORD','FCO'),('ORD','BCN'),('ORD','AMS'),
        ('ORD','HND'),('ORD','NRT'),('ORD','DUB'),('ORD','CUN'),('ORD','MEX'),
        ('ORD','LAX'),('ORD','SFO'),('ORD','MIA'),('ORD','BOS'),('ORD','LAS'),
        ('BOS','LHR'),('BOS','CDG'),('BOS','BCN'),('BOS','FCO'),('BOS','AMS'),
        ('BOS','DUB'),
        ('DFW','LHR'),('DFW','CDG'),('DFW','CUN'),('DFW','MIA'),
        ('ATL','CDG'),('ATL','LHR'),('ATL','CUN'),('ATL','MIA'),('ATL','DEN'),
        ('ATL','PUJ'),
        ('SEA','HND'),('SEA','LAX'),('SEA','LAS'),
        ('MIA','CDG'),('MIA','LHR'),('MIA','MAD'),('MIA','GIG'),('MIA','BOG'),
        ('MIA','PTY'),('MIA','CUN'),
    ]
    _r3_users = [alice, bob, carol, david]
    _r3_titles_pos = [
        'Smooth and professional', 'Best flight in a while',
        'On-time and comfortable', 'Pleasant experience',
        'Great value for the route', 'Crew really delivered',
        'Direct flight done right', 'No surprises, all good',
        'Solid long-haul', 'Comfortable cabin',
    ]
    _r3_titles_neg = [
        'Tight seats, long flight', 'Boarding was chaotic',
        'Average at best', 'Delayed but they handled it',
        'IFE issues again', 'Crew was stretched thin',
    ]
    _r3_bodies_pos = [
        'Boarded on time, crew was attentive, and the flight was on time both ways. '
        'Bag came out fast. I would book this airline again on this route.',
        'Decent meal service for the cabin class, the seat was clean and well-maintained, '
        'and the entertainment library was deeper than I expected. Solid trip.',
        'The crew kept the cabin running quietly and the meal pacing was right for the '
        'overnight flight. Slept enough to be productive on arrival.',
        'Quick taxi, smooth flight, friendly cabin crew. The Wi-Fi was usable for emails '
        'most of the way which is rare on this airline.',
        'Aircraft was newer than the last time I flew this route — power outlets actually '
        'worked, seat-back screen was responsive, and the snack box was generous.',
    ]
    _r3_bodies_neg = [
        'Plane felt tight and the seat in front reclined all the way back. Crew was '
        'professional but the experience was just average overall.',
        'Gate changed twice before boarding, then we sat at the gate for 40 minutes. '
        'Once airborne everything was fine but the start really hurt the experience.',
        'IFE rebooted three times in flight which got old quickly. Crew was apologetic '
        'but there was nothing they could do about a system bug.',
    ]
    _r3_review_count_target = 200
    _r3_existing_review_routes = set()  # (user_id, flight_id) to avoid dup constraint
    for u in _r3_users:
        for o, d in _r3_routes:
            if Review.query.count() + len(db.session.new) >= _r3_review_count_target + 20:
                break
            f = _get_flight(o, d)
            if f is None:
                continue
            key = (u.id, f.id)
            if key in _r3_existing_review_routes:
                continue
            _r3_existing_review_routes.add(key)
            # Deterministic seed: stable across rebuilds. NOTE: Python's
            # built-in hash() randomises strings per-process (PYTHONHASHSEED),
            # so we must use a stable hash (sha1 of a deterministic byte
            # serialisation) — otherwise rebuilds drift and md5 differs.
            import hashlib
            seed_bytes = f'{u.id}|{o}|{d}'.encode('utf-8')
            seed = int(hashlib.sha1(seed_bytes).hexdigest(), 16) % (2**31)
            rnd = _r3rand.Random(seed)
            rating = rnd.choice([5, 5, 4, 4, 4, 4, 3, 3, 2])
            if rating >= 4:
                title = rnd.choice(_r3_titles_pos)
                body = rnd.choice(_r3_bodies_pos)
            else:
                title = rnd.choice(_r3_titles_neg)
                body = rnd.choice(_r3_bodies_neg)
            r = Review(
                user_id=u.id, flight_id=f.id, rating=rating,
                title=title, body=body,
                punctuality=rnd.choice([rating, rating, max(1, rating - 1), min(5, rating + 1)]),
                comfort=rnd.choice([rating, rating, max(1, rating - 1)]),
                service=rnd.choice([rating, min(5, rating + 1), max(1, rating - 1)]),
            )
            db.session.add(r)
        # Commit per user so the Review.query.count() check sees progress
        db.session.flush()

    db.session.commit()
    print('Benchmark users seeded: alice, bob, carol, david')


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        fresh_seed = Airport.query.count() == 0
        if fresh_seed:
            seed_database()
        seed_benchmark_users()
        if fresh_seed:
            # Only run on a true fresh build so warm restarts skip the
            # VACUUM cost. See gotcha #2 in harden-env/gotchas.md.
            normalize_db_for_byte_identity()
    port = int(os.environ.get('PORT', 28849))
    app.run(host='0.0.0.0', port=port, debug=False)
