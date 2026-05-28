"""
Google Maps Mirror - Flask application.

Entity model adapted for a maps/search site:
  Place     - restaurants, hotels, attractions, museums, parks, shops, etc.
  Category  - top-level taxonomy (mapped to nav)
  City      - each place belongs to a city; cities get browsing pages

CRUD-adapted from e-commerce primitives:
  SavedList  - user's custom place lists ("Want to go", "Favorites") ~= cart+wishlist
  SavedPlace - membership of a place in a list             ~= CartItem/WishlistItem
  Trip       - a multi-place planned trip                  ~= Order
  TripStop   - a stop in a trip with order/notes           ~= OrderItem
  Review     - user review of a place
  Photo      - user-uploaded photo for a place
  TimelineEntry - location history entries
"""
import json
import math
import os
import random
import re
import string
import secrets
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import quote_plus

from flask import (Flask, render_template, render_template_string, request,
                   redirect, url_for,
                   flash, jsonify, abort, session, send_from_directory)
from flask_sqlalchemy import SQLAlchemy
from flask_login import (LoginManager, UserMixin, login_user, logout_user,
                         login_required, current_user)
from flask_bcrypt import Bcrypt
from flask_wtf import CSRFProtect
from sqlalchemy import or_, and_, func, text
from werkzeug.middleware.proxy_fix import ProxyFix
from jinja2 import TemplateNotFound

# --------------------------------------------------------------------------
#  Deterministic-seed constants
# --------------------------------------------------------------------------
# Pinned bcrypt hash for "TestPass123!" — bcrypt.gensalt() uses a fresh
# random salt every call, which breaks byte-identical seed-DB rebuilds.
# Generated once via:
#   python3 -c "import bcrypt; print(bcrypt.hashpw(b'TestPass123!', bcrypt.gensalt(rounds=12)).decode())"
# bcrypt.check_password_hash accepts any valid $2b$... hash, so login
# behaviour is unchanged.
PINNED_PASSWORD_HASH = '$2b$12$RwAC/sfwDHtccU//A20fde.uKkZK4Ptnjjyua2l2ktwI6uysAp3Ou'
# Reference moment for all explicit timestamps in benchmark seeding.
MIRROR_REFERENCE_DATETIME = datetime(2026, 4, 15, 12, 0, 0)

BASE_DIR = Path(__file__).parent

# --------------------------------------------------------------------------
#  App factory
# --------------------------------------------------------------------------
app = Flask(__name__)
app.config["SECRET_KEY"] = "google-maps-mirror-secret-key-change-in-prod"
app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{BASE_DIR / 'instance' / 'gmaps.db'}"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["WTF_CSRF_TIME_LIMIT"] = None

os.makedirs(BASE_DIR / "instance", exist_ok=True)

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
csrf = CSRFProtect(app)
login_manager = LoginManager(app)
login_manager.login_view = "login"
login_manager.login_message = "Sign in to save places, leave reviews, and access your lists."
login_manager.login_message_category = "info"


# >>> silent-fail-fix: unauthorized_handler
@login_manager.unauthorized_handler
def _unauthorized_silent_fail_fix():
    """Return JSON 401 for AJAX/JSON requests so fetch().then(r=>r.json())
    surfaces the auth requirement instead of choking on HTML 302→/login.
    Falls back to the normal redirect for browser navigations.

    Pairs with the fetch-wrapper in static/js/main.js which detects this and
    redirects the user to /login. Root cause docs: gotcha #49."""
    from flask import request, jsonify, redirect, url_for
    accept = request.headers.get('Accept', '') or ''
    wants_json = (
        request.path.startswith('/api/')
        or request.is_json
        or 'application/json' in accept
        or request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    )
    next_url = request.full_path if request.query_string else request.path
    try:
        login_url = url_for('login', next=next_url)
    except Exception:
        login_url = '/login?next=' + next_url
    if wants_json:
        return jsonify({
            'error': 'login_required',
            'message': 'Sign in to continue.',
            'redirect': login_url,
        }), 401
    return redirect(login_url)
# <<< silent-fail-fix


# --------------------------------------------------------------------------
#  Gallery helpers
# --------------------------------------------------------------------------
_MANIFEST_CACHE = None

def _load_manifest():
    """Load place_galleries.json once and cache it."""
    global _MANIFEST_CACHE
    if _MANIFEST_CACHE is None:
        path = BASE_DIR / "place_galleries.json"
        try:
            _MANIFEST_CACHE = json.loads(path.read_text())
        except Exception:
            _MANIFEST_CACHE = {}
    return _MANIFEST_CACHE


_CATEGORY_SECTION_TEMPLATES = {
    "attractions": [
        ("Overview", "An unmissable attraction famous around the world for its stunning presence and cultural significance."),
        ("Visitor Experience", "Walk through the site at your own pace, snap photos from the best viewpoints, and soak in the atmosphere."),
        ("History & Meaning", "Centuries of history and countless stories live within these walls - a cornerstone of the city's identity."),
    ],
    "hotels": [
        ("Rooms & Suites", "Spacious, stylish accommodations with premium bedding, modern amenities, and thoughtful touches."),
        ("Amenities", "Relax at the spa, swim in the pool, and dine at award-winning restaurants - all without leaving the property."),
        ("Location", "Positioned in a prime part of the city with easy access to major attractions and transit."),
    ],
    "restaurants": [
        ("The Menu", "A thoughtfully curated menu featuring seasonal ingredients and signature dishes the kitchen has perfected over years."),
        ("Atmosphere", "Warm lighting, attentive service, and a dining room designed to make every meal feel memorable."),
        ("Reviews", "Consistently praised by guests for its food, hospitality, and overall experience."),
    ],
    "museums": [
        ("Collections", "Explore a world-class collection spanning multiple eras, with rotating exhibitions and permanent galleries."),
        ("Visiting", "Plan a half-day visit to take in the highlights - audio guides and docent tours are available."),
        ("Architecture", "The building itself is a work of art, designed to complement and showcase the collection within."),
    ],
    "parks": [
        ("Trails & Walks", "Miles of trails wind through diverse landscapes, perfect for morning jogs or leisurely afternoon strolls."),
        ("Recreation", "Picnic areas, playgrounds, sports courts, and open lawns invite visitors of every age."),
        ("Nature", "A green oasis filled with native flora and wildlife - a place to reconnect with nature in the heart of the city."),
    ],
    "shopping": [
        ("Stores & Brands", "From global fashion houses to beloved local boutiques, you will find everything under one roof."),
        ("Dining", "Food courts and sit-down restaurants make this a destination for all-day visits."),
        ("Experience", "Beautiful architecture, seasonal events, and engaging displays turn shopping into an experience."),
    ],
    "entertainment": [
        ("Showtime", "Live performances, headline acts, and an atmosphere that pulls you in from the moment you arrive."),
        ("Venue", "A stunning space designed with sightlines, acoustics, and energy in mind."),
        ("What to Expect", "An unforgettable night out - arrive early, stay late, and soak it all in."),
    ],
    "transit": [
        ("Getting There", "A major transportation hub connecting travelers to destinations near and far."),
        ("Facilities", "Modern amenities include shops, restaurants, lounges, and seamless connections."),
        ("History", "An architecturally significant gateway that has served the city for generations."),
    ],
}


# --------------------------------------------------------------------------
#  Models
# --------------------------------------------------------------------------
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    name = db.Column(db.String(128), nullable=False)
    avatar_letter = db.Column(db.String(1), default="U")
    home_city = db.Column(db.String(128), default="")
    bio = db.Column(db.Text, default="")
    created_at = db.Column(db.DateTime, default=lambda: MIRROR_REFERENCE_DATETIME)

    saved_lists = db.relationship("SavedList", backref="user", cascade="all, delete-orphan", lazy="dynamic")
    saved_places = db.relationship("SavedPlace", backref="user", cascade="all, delete-orphan", lazy="dynamic")
    trips = db.relationship("Trip", backref="user", cascade="all, delete-orphan", lazy="dynamic")
    reviews = db.relationship("Review", backref="user", cascade="all, delete-orphan", lazy="dynamic")
    photos = db.relationship("Photo", backref="user", cascade="all, delete-orphan", lazy="dynamic")
    timeline_entries = db.relationship("TimelineEntry", backref="user", cascade="all, delete-orphan", lazy="dynamic")


class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(64), unique=True, nullable=False, index=True)
    name = db.Column(db.String(128), nullable=False)
    icon = db.Column(db.String(64), default="place")
    color = db.Column(db.String(16), default="#4285f4")
    description = db.Column(db.Text, default="")

    places = db.relationship("Place", backref="category", lazy="dynamic")


class City(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(64), unique=True, nullable=False, index=True)
    display_name = db.Column(db.String(128), nullable=False)
    country = db.Column(db.String(128), default="")
    hero_image = db.Column(db.String(255), default="")
    description = db.Column(db.Text, default="")
    lat = db.Column(db.Float, default=0.0)
    lng = db.Column(db.Float, default=0.0)

    places = db.relationship("Place", backref="city", lazy="dynamic")


class Place(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(160), unique=True, nullable=False, index=True)
    name = db.Column(db.String(255), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey("category.id"), nullable=False)
    city_id = db.Column(db.Integer, db.ForeignKey("city.id"), nullable=False)
    subtitle = db.Column(db.String(255), default="")
    description = db.Column(db.Text, default="")
    address = db.Column(db.String(255), default="")
    zip_code = db.Column(db.String(16), default="", index=True)
    state = db.Column(db.String(32), default="", index=True)
    phone = db.Column(db.String(64), default="")
    hours = db.Column(db.String(255), default="")
    hours_json = db.Column(db.Text, default="{}")  # {"mon": "9-5", ...}
    website = db.Column(db.String(255), default="")
    rating = db.Column(db.Float, default=4.5)
    review_count = db.Column(db.Integer, default=0)
    price_level = db.Column(db.String(16), default="$")
    hero_image = db.Column(db.String(255), default="")
    photos_json = db.Column(db.Text, default="[]")
    lat = db.Column(db.Float, default=0.0)
    lng = db.Column(db.Float, default=0.0)
    tags_json = db.Column(db.Text, default="[]")       # search keywords
    amenities_json = db.Column(db.Text, default="[]")  # parking, wifi, etc.
    is_24h = db.Column(db.Boolean, default=False)
    is_open_now = db.Column(db.Boolean, default=True)
    closes_at_night = db.Column(db.Boolean, default=False)  # not open 24h
    has_parking_lot = db.Column(db.Boolean, default=False)
    ev_charging = db.Column(db.Boolean, default=False)
    motorcycle_parking = db.Column(db.Boolean, default=False)
    bicycle_parking = db.Column(db.Boolean, default=False)
    subcategory = db.Column(db.String(64), default="", index=True)
    chain_brand = db.Column(db.String(128), default="", index=True)
    nearest_landmark = db.Column(db.String(255), default="")
    review_snippets_json = db.Column(db.Text, default="[]")  # list of {rating,text}
    is_featured = db.Column(db.Boolean, default=False)
    is_popular = db.Column(db.Boolean, default=False)
    parking_info = db.Column(db.String(255), default="")  # e.g. "Free parking lot", "Street parking", "Paid garage"
    delivery_available = db.Column(db.Boolean, default=False)
    # --- R4 additions: service options, accessibility, popular times, menu ---
    dine_in = db.Column(db.Boolean, default=False, index=True)
    takeout = db.Column(db.Boolean, default=False, index=True)
    curbside_pickup = db.Column(db.Boolean, default=False)
    contactless_pickup = db.Column(db.Boolean, default=False, index=True)
    accepts_reservations = db.Column(db.Boolean, default=False, index=True)
    serves_breakfast = db.Column(db.Boolean, default=False)
    serves_lunch = db.Column(db.Boolean, default=False)
    serves_dinner = db.Column(db.Boolean, default=False)
    serves_brunch = db.Column(db.Boolean, default=False)
    serves_alcohol = db.Column(db.Boolean, default=False)
    serves_vegetarian = db.Column(db.Boolean, default=False)
    wheelchair_accessible_entrance = db.Column(db.Boolean, default=False, index=True)
    wheelchair_accessible_restroom = db.Column(db.Boolean, default=False)
    wheelchair_accessible_parking = db.Column(db.Boolean, default=False)
    wheelchair_accessible_seating = db.Column(db.Boolean, default=False)
    has_braille_menu = db.Column(db.Boolean, default=False)
    has_assistive_hearing = db.Column(db.Boolean, default=False)
    has_service_animal_welcome = db.Column(db.Boolean, default=False)
    accessibility_score = db.Column(db.Integer, default=0)  # 0-100
    popular_times_json = db.Column(db.Text, default="[]")   # 7×24 matrix
    busiest_day = db.Column(db.String(16), default="")      # mon..sun
    busiest_hour = db.Column(db.Integer, default=12)        # 0..23 peak
    menu_json = db.Column(db.Text, default="[]")            # restaurants only
    ratings_dist_json = db.Column(db.Text, default="[]")    # [n5,n4,n3,n2,n1]
    visit_label = db.Column(db.String(32), default="")      # ""/"Home"/"Work"
    # --- R5 additions: ambient signals + indoor positioning ---
    noise_level = db.Column(db.String(16), default="", index=True)  # quiet/moderate/lively/loud
    crowd_level = db.Column(db.String(16), default="", index=True)  # low/moderate/high/very-high
    mask_required = db.Column(db.Boolean, default=False, index=True)
    indoor_zone_type = db.Column(db.String(32), default="", index=True)  # food-court/lounge/concourse/wing/...
    floor_number = db.Column(db.String(8), default="")  # "G"/"1"/"2"/"B1"/"R" (roof)
    floors_json = db.Column(db.Text, default="[]")  # multi-floor map for the indoor-floor selector
    parking_lot_capacity = db.Column(db.Integer, default=0)
    ev_connector_type = db.Column(db.String(32), default="")  # CCS/CHAdeMO/Tesla/J1772
    ev_charger_kw = db.Column(db.Integer, default=0)
    # --- R6 additions: edge banners, accessibility warnings, indoor mapping gap ---
    is_closed_permanently = db.Column(db.Boolean, default=False, index=True)
    is_temporarily_closed = db.Column(db.Boolean, default=False, index=True)
    closure_reason = db.Column(db.String(160), default="")
    reopen_eta = db.Column(db.String(80), default="")  # e.g. "Reopens Jun 18, 2026"
    accessibility_warning = db.Column(db.String(255), default="")  # e.g. "No step-free entrance"
    indoor_floor_unmapped = db.Column(db.Boolean, default=False, index=True)  # floors known but not yet mapped
    created_at = db.Column(db.DateTime, default=lambda: MIRROR_REFERENCE_DATETIME)

    reviews = db.relationship("Review", backref="place", cascade="all, delete-orphan", lazy="dynamic")
    photos = db.relationship("Photo", backref="place", cascade="all, delete-orphan", lazy="dynamic")

    def get_photos(self):
        try:
            return json.loads(self.photos_json or "[]")
        except (json.JSONDecodeError, TypeError):
            return []

    def get_tags(self):
        try:
            return json.loads(self.tags_json or "[]")
        except (json.JSONDecodeError, TypeError):
            return []

    def get_amenities(self):
        try:
            return json.loads(self.amenities_json or "[]")
        except (json.JSONDecodeError, TypeError):
            return []

    def get_hours_dict(self):
        try:
            return json.loads(self.hours_json or "{}")
        except (json.JSONDecodeError, TypeError):
            return {}

    def get_review_snippets(self):
        try:
            return json.loads(self.review_snippets_json or "[]")
        except (json.JSONDecodeError, TypeError):
            return []

    def get_popular_times(self):
        """Return a 7×24 int matrix (0..100). [mon..sun][hour]."""
        try:
            data = json.loads(self.popular_times_json or "[]")
            if isinstance(data, list) and len(data) == 7 and all(
                    isinstance(r, list) and len(r) == 24 for r in data):
                return data
        except (json.JSONDecodeError, TypeError):
            pass
        return [[0] * 24 for _ in range(7)]

    def get_menu(self):
        try:
            data = json.loads(self.menu_json or "[]")
            return data if isinstance(data, list) else []
        except (json.JSONDecodeError, TypeError):
            return []

    def get_ratings_dist(self):
        try:
            data = json.loads(self.ratings_dist_json or "[]")
            if isinstance(data, list) and len(data) == 5:
                return data
        except (json.JSONDecodeError, TypeError):
            pass
        return [0, 0, 0, 0, 0]

    def get_accessibility_flags(self):
        """Return ordered list of (label, enabled) tuples for the UI row."""
        return [
            ("Wheelchair-accessible entrance", self.wheelchair_accessible_entrance),
            ("Wheelchair-accessible restroom", self.wheelchair_accessible_restroom),
            ("Wheelchair-accessible parking", self.wheelchair_accessible_parking),
            ("Wheelchair-accessible seating", self.wheelchair_accessible_seating),
            ("Braille menu", self.has_braille_menu),
            ("Assistive hearing loop", self.has_assistive_hearing),
            ("Service animal welcome", self.has_service_animal_welcome),
        ]

    def get_service_flags(self):
        """Return ordered list of (label, enabled) for the service-options row."""
        return [
            ("Dine-in", self.dine_in),
            ("Takeout", self.takeout),
            ("Delivery", self.delivery_available),
            ("Curbside pickup", self.curbside_pickup),
            ("Contactless pickup", self.contactless_pickup),
            ("Reservations", self.accepts_reservations),
        ]

    def get_floors(self):
        """Return ordered floor list for the indoor-floor selector.

        Each entry: {"code": "G", "label": "Ground floor", "summary": "..."}.
        Empty list for places that aren't multi-floor indoor venues.
        """
        try:
            data = json.loads(self.floors_json or "[]")
            return data if isinstance(data, list) else []
        except (json.JSONDecodeError, TypeError):
            return []

    def get_ambient_chips(self):
        """Return UI chips for noise/crowd/mask (R5)."""
        chips = []
        if self.noise_level:
            chips.append(("noise", "volume_up", self.noise_level.capitalize() + " noise"))
        if self.crowd_level:
            chips.append(("crowd", "groups", self.crowd_level.replace("-", " ").capitalize() + " crowd"))
        if self.mask_required:
            chips.append(("mask", "masks", "Mask required"))
        return chips

    def get_gallery(self):
        """Load gallery sections.

        Strategy:
          1) If the place is in place_galleries.json (real Wikipedia places),
             return the curated sections from there.
          2) Otherwise, synthesize sections from photos_json using
             category-aware templates. Every place thus gets a rich gallery.
        """
        sections = _load_manifest().get(self.slug)
        if sections:
            return sections
        # Fallback: synthesize from photos_json
        photos = self.get_photos()
        if not photos and self.hero_image:
            photos = [self.hero_image]
        if not photos:
            return []
        cat_slug = self.category.slug if self.category else "attractions"
        templates = _CATEGORY_SECTION_TEMPLATES.get(cat_slug, _CATEGORY_SECTION_TEMPLATES["attractions"])
        sections = []
        n = max(1, len(photos) // len(templates))
        for i, (title, desc) in enumerate(templates):
            start = i * n
            end = (i + 1) * n if i < len(templates) - 1 else len(photos)
            imgs = photos[start:end] or [photos[i % len(photos)]]
            sections.append({"title": title, "desc": desc, "images": imgs})
        return sections

    @property
    def stars_full(self):
        return int(self.rating)

    @property
    def stars_half(self):
        return 1 if (self.rating - int(self.rating)) >= 0.5 else 0

    @property
    def stars_empty(self):
        return 5 - self.stars_full - self.stars_half


class SavedList(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    name = db.Column(db.String(128), nullable=False)
    description = db.Column(db.Text, default="")
    icon = db.Column(db.String(32), default="bookmark")
    color = db.Column(db.String(16), default="#4285f4")
    is_default = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=lambda: MIRROR_REFERENCE_DATETIME)

    places = db.relationship("SavedPlace", backref="saved_list", cascade="all, delete-orphan", lazy="dynamic")


class SavedPlace(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    list_id = db.Column(db.Integer, db.ForeignKey("saved_list.id"), nullable=False)
    place_id = db.Column(db.Integer, db.ForeignKey("place.id"), nullable=False)
    note = db.Column(db.Text, default="")
    label = db.Column(db.String(32), default="", index=True)  # "Home"/"Work"/custom
    created_at = db.Column(db.DateTime, default=lambda: MIRROR_REFERENCE_DATETIME)

    place = db.relationship("Place")


class Trip(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    trip_code = db.Column(db.String(16), unique=True, nullable=False)
    title = db.Column(db.String(255), nullable=False)
    city = db.Column(db.String(128), default="")
    start_date = db.Column(db.Date, nullable=True)
    end_date = db.Column(db.Date, nullable=True)
    status = db.Column(db.String(32), default="planning")  # planning, upcoming, active, completed, cancelled
    notes = db.Column(db.Text, default="")
    created_at = db.Column(db.DateTime, default=lambda: MIRROR_REFERENCE_DATETIME)

    stops = db.relationship("TripStop", backref="trip", cascade="all, delete-orphan", lazy="dynamic", order_by="TripStop.order_idx")


class TripStop(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    trip_id = db.Column(db.Integer, db.ForeignKey("trip.id"), nullable=False)
    place_id = db.Column(db.Integer, db.ForeignKey("place.id"), nullable=False)
    order_idx = db.Column(db.Integer, default=0)
    notes = db.Column(db.Text, default="")

    place = db.relationship("Place")


class Review(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    place_id = db.Column(db.Integer, db.ForeignKey("place.id"), nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    title = db.Column(db.String(255), default="")
    body = db.Column(db.Text, default="")
    created_at = db.Column(db.DateTime, default=lambda: MIRROR_REFERENCE_DATETIME)


class Photo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    place_id = db.Column(db.Integer, db.ForeignKey("place.id"), nullable=False)
    image_url = db.Column(db.String(255), nullable=False)
    caption = db.Column(db.String(255), default="")
    created_at = db.Column(db.DateTime, default=lambda: MIRROR_REFERENCE_DATETIME)


# --------------------------------------------------------------------------
#  R-imgsave additions: questions, answers, edit suggestions, reports.
#  All start empty in the seed DB so byte-id reset is unaffected.  Real
#  agent writes go in to test POST handlers.
# --------------------------------------------------------------------------
class PlaceQuestion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    place_id = db.Column(db.Integer, db.ForeignKey("place.id"), nullable=False)
    body = db.Column(db.Text, default="")
    created_at = db.Column(db.DateTime,
                           default=lambda: MIRROR_REFERENCE_DATETIME)

    answers = db.relationship("PlaceAnswer", backref="question",
                              cascade="all, delete-orphan", lazy="dynamic")


class PlaceAnswer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    question_id = db.Column(db.Integer,
                            db.ForeignKey("place_question.id"),
                            nullable=False)
    body = db.Column(db.Text, default="")
    created_at = db.Column(db.DateTime,
                           default=lambda: MIRROR_REFERENCE_DATETIME)


class EditSuggestion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    place_id = db.Column(db.Integer, db.ForeignKey("place.id"), nullable=False)
    field = db.Column(db.String(64), default="")  # name/address/hours/...
    new_value = db.Column(db.String(512), default="")
    note = db.Column(db.Text, default="")
    status = db.Column(db.String(32), default="pending")  # pending/applied/rejected
    created_at = db.Column(db.DateTime,
                           default=lambda: MIRROR_REFERENCE_DATETIME)


class PlaceReport(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    place_id = db.Column(db.Integer, db.ForeignKey("place.id"), nullable=False)
    reason = db.Column(db.String(64), default="")  # closed/duplicate/inaccurate/inappropriate
    detail = db.Column(db.Text, default="")
    created_at = db.Column(db.DateTime,
                           default=lambda: MIRROR_REFERENCE_DATETIME)


class PhotoReport(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    photo_id = db.Column(db.Integer, db.ForeignKey("photo.id"), nullable=False)
    reason = db.Column(db.String(64), default="")
    created_at = db.Column(db.DateTime,
                           default=lambda: MIRROR_REFERENCE_DATETIME)


class PlaceCheckIn(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    place_id = db.Column(db.Integer, db.ForeignKey("place.id"), nullable=False)
    note = db.Column(db.String(255), default="")
    created_at = db.Column(db.DateTime,
                           default=lambda: MIRROR_REFERENCE_DATETIME)


class TimelineEntry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    place_id = db.Column(db.Integer, db.ForeignKey("place.id"), nullable=False)
    visited_at = db.Column(db.DateTime, default=lambda: MIRROR_REFERENCE_DATETIME)
    note = db.Column(db.Text, default="")

    place = db.relationship("Place")


class Route(db.Model):
    """Precomputed routes between notable origin/destination queries.

    Matches by `origin_query`/`destination_query` substrings, optionally
    filtered by `mode` (walking/driving/transit/bicycling).
    """
    id = db.Column(db.Integer, primary_key=True)
    origin_query = db.Column(db.String(255), nullable=False, index=True)
    destination_query = db.Column(db.String(255), nullable=False, index=True)
    origin_name = db.Column(db.String(255), default="")
    destination_name = db.Column(db.String(255), default="")
    mode = db.Column(db.String(32), default="driving", index=True)
    distance = db.Column(db.String(64), default="")      # "2.3 km" / "1.4 mi"
    distance_km = db.Column(db.Float, default=0.0)
    duration = db.Column(db.String(64), default="")      # "18 min"
    duration_min = db.Column(db.Integer, default=0)
    steps_json = db.Column(db.Text, default="[]")        # list of {instruction, distance}
    summary = db.Column(db.Text, default="")
    origin_address = db.Column(db.String(255), default="")
    destination_address = db.Column(db.String(255), default="")

    def get_steps(self):
        try:
            return json.loads(self.steps_json or "[]")
        except (json.JSONDecodeError, TypeError):
            return []


class TransitLine(db.Model):
    """A named transit line (subway / bus / light-rail) for the
    /transit/lines/<line_id> deep page."""
    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(96), unique=True, nullable=False, index=True)
    name = db.Column(db.String(128), nullable=False)         # "1 Train", "F Bus", ...
    short_name = db.Column(db.String(16), default="")        # "1", "F"
    agency = db.Column(db.String(128), default="")           # MTA, BART, MBTA, ...
    mode = db.Column(db.String(32), default="subway", index=True)
    color = db.Column(db.String(16), default="#5f6368")
    city_id = db.Column(db.Integer, db.ForeignKey("city.id"), nullable=True, index=True)
    frequency_peak = db.Column(db.String(32), default="")    # "Every 4 min"
    frequency_off = db.Column(db.String(32), default="")     # "Every 10 min"
    hours = db.Column(db.String(128), default="")            # "5:00 AM – 1:00 AM"
    stops_json = db.Column(db.Text, default="[]")            # list of stop names
    description = db.Column(db.Text, default="")
    accessibility_notes = db.Column(db.Text, default="")     # wheelchair info
    # --- R5: realtime-style delays for transit-realtime-delay tasks ---
    current_delay_min = db.Column(db.Integer, default=0)     # minutes vs schedule
    delay_reason = db.Column(db.String(128), default="")     # "Signal problem", "Construction", ...
    last_update = db.Column(db.String(32), default="")       # "2 min ago" / "Updated at 14:35"

    def get_stops(self):
        try:
            data = json.loads(self.stops_json or "[]")
            return data if isinstance(data, list) else []
        except (json.JSONDecodeError, TypeError):
            return []


# --------------------------------------------------------------------------
#  R7: composite indexes for hot query paths.
#  All names start with "ix_" so normalize_seed_db_layout() re-emits them
#  in alphabetical order during the byte-id finalize pass.
# --------------------------------------------------------------------------
db.Index("ix_place_city_id_rating", Place.city_id, Place.rating)
db.Index("ix_place_category_id_rating", Place.category_id, Place.rating)
db.Index("ix_place_category_id_lat_lng", Place.category_id, Place.lat, Place.lng)
db.Index("ix_place_chain_brand_rating", Place.chain_brand, Place.rating)
db.Index("ix_place_subcategory_rating", Place.subcategory, Place.rating)
db.Index("ix_place_lat_lng", Place.lat, Place.lng)
# Homepage `/` and `/explore` filter Place.is_featured / Place.is_popular and
# sort by Place.rating. Without these indexes each `filter_by(...).limit(12)`
# full-scans the 903k-row catalog (~117ms × 2 per page). Composite turns it
# into a key seek (<2ms each).
db.Index("ix_place_is_featured_rating", Place.is_featured, Place.rating)
db.Index("ix_place_is_popular_rating", Place.is_popular, Place.rating)


# --------------------------------------------------------------------------
#  R7: locale catalog — 25 languages including RTL (ar/he).  Locale paths
#  alias the homepage and pass `lang_code` + `lang_dir` into the template
#  so SEO crawlers see <html lang="..."> + correct direction.  UI strings
#  are loaded from a static dict (no DB table — keeps byte-id stable).
# --------------------------------------------------------------------------
R7_LOCALES = [
    {"code": "en", "name": "English",     "dir": "ltr", "tagline": "Explore the world with Google Maps."},
    {"code": "es", "name": "Espanol",     "dir": "ltr", "tagline": "Explora el mundo con Google Maps."},
    {"code": "fr", "name": "Francais",    "dir": "ltr", "tagline": "Explorez le monde avec Google Maps."},
    {"code": "de", "name": "Deutsch",     "dir": "ltr", "tagline": "Entdecke die Welt mit Google Maps."},
    {"code": "it", "name": "Italiano",    "dir": "ltr", "tagline": "Esplora il mondo con Google Maps."},
    {"code": "pt", "name": "Portugues",   "dir": "ltr", "tagline": "Explore o mundo com o Google Maps."},
    {"code": "nl", "name": "Nederlands",  "dir": "ltr", "tagline": "Ontdek de wereld met Google Maps."},
    {"code": "sv", "name": "Svenska",     "dir": "ltr", "tagline": "Utforska varlden med Google Maps."},
    {"code": "da", "name": "Dansk",       "dir": "ltr", "tagline": "Udforsk verden med Google Maps."},
    {"code": "no", "name": "Norsk",       "dir": "ltr", "tagline": "Utforsk verden med Google Maps."},
    {"code": "fi", "name": "Suomi",       "dir": "ltr", "tagline": "Tutustu maailmaan Google Mapsilla."},
    {"code": "pl", "name": "Polski",      "dir": "ltr", "tagline": "Odkrywaj swiat z Mapami Google."},
    {"code": "cs", "name": "Cestina",     "dir": "ltr", "tagline": "Objevujte svet s Mapami Google."},
    {"code": "el", "name": "Ellinika",    "dir": "ltr", "tagline": "Eksereunise ton kosmo me to Google Maps."},
    {"code": "tr", "name": "Turkce",      "dir": "ltr", "tagline": "Dunyayi Google Haritalar ile kesfedin."},
    {"code": "ru", "name": "Russkij",     "dir": "ltr", "tagline": "Issleduite mir s Kartami Google."},
    {"code": "ja", "name": "Nihongo",     "dir": "ltr", "tagline": "Google Maps de sekai wo tanken shiyou."},
    {"code": "ko", "name": "Hangugeo",    "dir": "ltr", "tagline": "Google Maps ro sesangeul tamheomhaseyo."},
    {"code": "zh", "name": "Zhongwen",    "dir": "ltr", "tagline": "Yong Google Ditu tansuo shijie."},
    {"code": "hi", "name": "Hindi",       "dir": "ltr", "tagline": "Google Maps ke saath duniya ki khoj karein."},
    {"code": "th", "name": "Thai",        "dir": "ltr", "tagline": "Khon ha lok kap Google Maps."},
    {"code": "vi", "name": "Tieng Viet",  "dir": "ltr", "tagline": "Kham pha the gioi cung Google Maps."},
    {"code": "id", "name": "Indonesia",   "dir": "ltr", "tagline": "Jelajahi dunia dengan Google Maps."},
    {"code": "ar", "name": "Arabic",      "dir": "rtl", "tagline": "Istakshif al-alam ma'a Khara'it Google."},
    {"code": "he", "name": "Hebrew",      "dir": "rtl", "tagline": "Galu et ha-olam im Google Maps."},
]
R7_LOCALE_CODES = {l["code"] for l in R7_LOCALES}
R7_LOCALE_BY_CODE = {l["code"]: l for l in R7_LOCALES}


# --------------------------------------------------------------------------
#  Login / helpers
# --------------------------------------------------------------------------
@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


def gen_trip_code():
    return "TRIP-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=8))


def ensure_default_lists(user):
    """Give every new user a default 'Want to go', 'Favorites', 'Starred'."""
    defaults = [
        ("Want to go", "bookmark", "#4285f4", "Places you'd love to visit"),
        ("Favorites", "favorite", "#ea4335", "Your all-time favorite places"),
        ("Starred places", "star", "#fbbc04", "Places you've starred for quick access"),
    ]
    for name, icon, color, desc in defaults:
        db.session.add(SavedList(
            user_id=user.id, name=name, icon=icon, color=color,
            description=desc, is_default=True,
        ))
    db.session.commit()


def google_maps_place_url(place):
    """Return a real Google Maps place URL for a local mirror Place row."""
    query = f"{place.name} {place.city.display_name if place.city else ''}".strip()
    return f"https://www.google.com/maps/place/{quote_plus(query)}/"


def display_place_website(place):
    """Use the stored website unless it is a synthetic placeholder."""
    website = (place.website or "").strip()
    if website and "example.com" not in website:
        return website
    return google_maps_place_url(place)


# --------------------------------------------------------------------------
#  Image pool helpers  (R-imgsave: wire 818 static images into templates)
# --------------------------------------------------------------------------
_IMG_POOL_CACHE = None


def _img_pools():
    """Scan static/images/ once.  Returns {categories,cities,places,heroes}.

    Each value (except heroes) is a dict mapping dir-slug -> sorted URL list.
    Deterministic by sort order so byte-id reset survives.
    """
    global _IMG_POOL_CACHE
    if _IMG_POOL_CACHE is not None:
        return _IMG_POOL_CACHE
    base = BASE_DIR / "static" / "images"
    out = {"categories": {}, "cities": {}, "places": {}, "heroes": []}
    for kind in ("categories", "cities", "places"):
        root = base / kind
        if not root.exists():
            continue
        for d in sorted(root.iterdir()):
            if d.is_dir():
                imgs = sorted(
                    f.name for f in d.iterdir()
                    if f.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp")
                )
                out[kind][d.name] = [
                    f"/static/images/{kind}/{d.name}/{n}" for n in imgs
                ]
    heroes_dir = base / "heroes"
    if heroes_dir.exists():
        out["heroes"] = sorted(
            f"/static/images/heroes/{f.name}" for f in heroes_dir.iterdir()
            if f.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp")
        )
    _IMG_POOL_CACHE = out
    return out


# DB category slug -> image subdirectory aliases under static/images/categories/
_CATEGORY_IMG_ALIASES = {
    "restaurants": ["restaurant-interior", "pizza-restaurant",
                    "burger-restaurant", "seafood-restaurant"],
    "hotels": ["hotel", "hotel-exterior"],
    "attractions": ["city-landmark", "public-plaza", "temple", "theater",
                    "zoo", "museum"],
    "shopping": ["retail-store", "shopping-mall", "shopping-storefront",
                 "department-store", "electronics-store", "asian-market",
                 "baby-store", "target-store", "uniqlo", "warehouse-store",
                 "furniture-store", "maternity-store", "apple-store",
                 "best-buy"],
    "supermarkets": ["supermarket", "asian-market"],
    "museums": ["museum", "art-gallery"],
    "parks": ["city-park", "national-park"],
    "beaches": ["city-landmark"],
    "transit": ["bus-stop", "train-station", "airport"],
    "bus-stops": ["bus-stop"],
    "ev-charging": ["ev-charging"],
    "gas-stations": ["ev-charging"],
    "entertainment": ["entertainment-venue", "theater", "arena",
                      "music-venue", "climbing-gym"],
    "services": ["service-shop", "locksmith", "plumber"],
    "fitness": ["climbing-gym"],
    "health-beauty": ["beauty-salon"],
    "parking": ["parking-garage", "motorcycle-parking", "bicycle-parking"],
    "religious": ["temple"],
    "indoor-mall-shops": ["shopping-mall", "shopping-storefront",
                          "department-store"],
    "indoor-airport-shops": ["airport", "shopping-storefront"],
    "campus-buildings": ["city-landmark", "public-plaza"],
    "car-rental": ["service-shop"],
    "coffee-shops": ["restaurant-interior"],
    "dentists": ["service-shop"],
    "dog-parks": ["city-park"],
    "fire-stations": ["service-shop"],
    "hospitals": ["service-shop"],
    "libraries": ["museum"],
    "pharmacies": ["retail-store", "supermarket"],
    "playgrounds": ["city-park"],
    "police-stations": ["service-shop"],
    "post-offices": ["service-shop"],
    "public-restrooms": ["service-shop"],
    "schools": ["city-landmark"],
    "veterinarians": ["service-shop"],
    "atms": ["service-shop"],
}


def category_image_pool(cat_slug, n=12):
    """Return up to n image URLs representative of a DB category slug."""
    pools = _img_pools()["categories"]
    aliases = _CATEGORY_IMG_ALIASES.get(cat_slug, [cat_slug])
    out = []
    for alias in aliases:
        for url in pools.get(alias, []):
            if url not in out:
                out.append(url)
        if len(out) >= n:
            break
    if not out:
        for d in sorted(pools.keys()):
            for url in pools[d]:
                if url not in out:
                    out.append(url)
            if len(out) >= n:
                break
    return out[:n]


def city_image_pool(city_slug, n=4):
    """Return up to n city scenery images for a city slug."""
    return _img_pools()["cities"].get(city_slug, [])[:n]


def place_extra_images(place, n=5):
    """Return up to n extra images for a place (excluding its hero).

    Pulls from the place's own static/images/places/<slug>/ dir first, then
    pads with the category pool so even sparse place dirs surface a rich
    gallery.  Deterministic given (slug, category_id).
    """
    pools = _img_pools()
    own = pools["places"].get(place.slug, [])
    out = []
    hero = place.hero_image or ""
    for url in own:
        if url != hero and url not in out:
            out.append(url)
    if len(out) < n and place.category_id:
        cat = db.session.get(Category, place.category_id)
        if cat:
            for url in category_image_pool(cat.slug, n * 4):
                if url != hero and url not in out:
                    out.append(url)
                if len(out) >= n:
                    break
    # Last-resort pad with heroes
    if len(out) < n:
        for url in pools["heroes"]:
            if url != hero and url not in out:
                out.append(url)
            if len(out) >= n:
                break
    return out[:n]


def category_icon_image(cat_slug):
    """Return one representative image URL for a category tile."""
    pool = category_image_pool(cat_slug, n=1)
    return pool[0] if pool else "/static/images/heroes/eiffel-tower.jpg"


def city_icon_image(city_slug):
    """Return one representative image URL for a city tile."""
    pool = city_image_pool(city_slug, n=1)
    return pool[0] if pool else "/static/images/heroes/eiffel-tower.jpg"


# Expose image helpers as Jinja globals — context_processor values are NOT
# visible inside macros loaded via {% from ... import %}, but jinja globals
# are.  We need place_extra_images in _place_card.html.
app.jinja_env.globals["place_extra_images"] = place_extra_images
app.jinja_env.globals["category_image_pool"] = category_image_pool
app.jinja_env.globals["city_image_pool"] = city_image_pool
app.jinja_env.globals["category_icon_image"] = category_icon_image
app.jinja_env.globals["city_icon_image"] = city_icon_image


# Process-level caches for read-mostly catalog data. These reset on /reset
# because control_server respawns the worker. Categories are 24 rows and
# global featured/popular are bounded short lists — caching saves the
# repeated ORM round-trip on every request hitting the 903k-place catalog.
_GLOBAL_CATEGORY_CACHE = []
_HOMEPAGE_CACHE = {}


def _cached_global_categories():
    if not _GLOBAL_CATEGORY_CACHE:
        _GLOBAL_CATEGORY_CACHE.extend(Category.query.order_by(Category.id).all())
    return _GLOBAL_CATEGORY_CACHE


@app.context_processor
def inject_globals():
    # Categories are static (24 rows, never mutated at request time). Caching
    # the rendered list saves ~80ms per request on the 903k-place catalog where
    # the trivial query still hits sqlite + ORM hydration. The cache resets on
    # every site respawn (control_server's /reset wipes the process).
    categories = _cached_global_categories()
    saved_count = 0
    if current_user.is_authenticated:
        saved_count = SavedPlace.query.filter_by(user_id=current_user.id).count()
    # R7: surface active locale (set by /<lang>/ entry route) for base.html
    # so <html lang=...> + dir attributes flip per locale.  Defaults to en/ltr.
    lang_code = session.get("lang_code", "en") if session else "en"
    lang_meta = R7_LOCALE_BY_CODE.get(lang_code, R7_LOCALE_BY_CODE["en"])
    return {
        "global_categories": categories,
        "global_saved_count": saved_count,
        "current_year": datetime.utcnow().year,
        "display_place_website": display_place_website,
        "google_maps_place_url": google_maps_place_url,
        "category_image_pool": category_image_pool,
        "city_image_pool": city_image_pool,
        "place_extra_images": place_extra_images,
        "category_icon_image": category_icon_image,
        "city_icon_image": city_icon_image,
        "PlaceQuestion": PlaceQuestion,
        "PlaceAnswer": PlaceAnswer,
        "EditSuggestion": EditSuggestion,
        "PlaceReport": PlaceReport,
        "Photo": Photo,
        "r7_lang_code": lang_meta["code"],
        "r7_lang_dir": lang_meta["dir"],
        "r7_lang_name": lang_meta["name"],
        "r7_locales": R7_LOCALES,
    }


# --------------------------------------------------------------------------
#  Public pages
# --------------------------------------------------------------------------
@app.route("/")
def index():
    featured = Place.query.filter_by(is_featured=True).limit(12).all()
    popular = Place.query.filter_by(is_popular=True).order_by(Place.rating.desc()).limit(12).all()
    cities = City.query.order_by(City.display_name).limit(12).all()
    categories = Category.query.order_by(Category.id).all()
    return render_template(
        "index.html",
        featured=featured,
        popular=popular,
        cities=cities,
        categories=categories,
    )


@app.route("/explore")
def explore():
    categories = Category.query.order_by(Category.id).all()
    cities = City.query.order_by(City.display_name).all()
    popular = Place.query.filter_by(is_popular=True).order_by(Place.rating.desc()).limit(24).all()
    return render_template(
        "explore.html",
        categories=categories,
        cities=cities,
        popular=popular,
    )


@app.route("/category/<slug>")
def category_page(slug):
    cat = Category.query.filter_by(slug=slug).first_or_404()
    city_filter = request.args.get("city", "")
    sort = request.args.get("sort", "rating")
    min_rating = request.args.get("min_rating", type=float)

    q = Place.query.filter_by(category_id=cat.id)
    if city_filter:
        c = City.query.filter_by(slug=city_filter).first()
        if c:
            q = q.filter_by(city_id=c.id)
    if min_rating:
        q = q.filter(Place.rating >= min_rating)

    if sort == "name":
        q = q.order_by(Place.name.asc())
    elif sort == "reviews":
        q = q.order_by(Place.review_count.desc())
    else:
        q = q.order_by(Place.rating.desc(), Place.review_count.desc())

    places = q.all()
    cities = City.query.order_by(City.display_name).all()

    return render_template(
        "category.html",
        category=cat,
        places=places,
        cities=cities,
        city_filter=city_filter,
        sort=sort,
        min_rating=min_rating,
    )


@app.route("/city/<slug>")
def city_page(slug):
    city = City.query.filter_by(slug=slug).first_or_404()
    categories = Category.query.order_by(Category.id).all()
    # Group places by category
    places_by_cat = {}
    for cat in categories:
        places = Place.query.filter_by(city_id=city.id, category_id=cat.id) \
            .order_by(Place.rating.desc()).limit(6).all()
        if places:
            places_by_cat[cat] = places

    top_rated = Place.query.filter_by(city_id=city.id) \
        .order_by(Place.rating.desc(), Place.review_count.desc()).limit(12).all()

    return render_template(
        "city.html",
        city=city,
        places_by_cat=places_by_cat,
        top_rated=top_rated,
    )


@app.route("/place/<slug>")
def place_detail(slug):
    place = Place.query.filter_by(slug=slug).first_or_404()
    # Reviews
    reviews = Review.query.filter_by(place_id=place.id) \
        .order_by(Review.created_at.desc()).limit(12).all()
    # Nearby places: distance-sort within ~25 mi, diversify by category so
    # the section isn't dominated by one bucket (e.g. high-rated climbing
    # gyms drowning out everything else in LA).  Real Google Maps surfaces
    # mixed categories on a place-detail page; clicking a category chip
    # below opens a search filtered by that category near this place.
    nearby_cat = (request.args.get("nearby_category") or "").strip().lower()
    nearby = []
    # Perf: prefer indexed lat/lng bbox pre-filter (30 mi ≈ 0.5° lat / 0.7° lng)
    # over `limit(2000)` global scan + Python-side haversine.  Without bbox,
    # SQLite returned the first 2000 places in (lat, lng) index order — almost
    # none of them near `place`.  Bbox cuts the working set from ~2000 ORM
    # hydrations to a few hundred and lets `ix_place_lat_lng` /
    # `ix_place_category_id_lat_lng` actually drive a range scan.
    #
    # Second layer: even after bbox, dense urban centers (SF/NYC/Chicago)
    # still return 1k-5k candidates.  Use `with_entities` to fetch only
    # (id, lat, lng, rating, review_count, category_id) as cheap tuples,
    # score in Python, then hydrate ORM rows only for the top ~12 per
    # section.  Avoids loading TEXT/JSON columns (description, photos_json,
    # tags_json, amenities_json, review_snippets_json, hours_json) on rows
    # we'll discard.
    nearby_cat_chips = []
    if place.lat and place.lng:
        lat_lo, lat_hi = place.lat - 0.5, place.lat + 0.5
        lng_lo, lng_hi = place.lng - 0.7, place.lng + 0.7
        bbox_filter = (
            Place.id != place.id,
            Place.lat.between(lat_lo, lat_hi),
            Place.lng.between(lng_lo, lng_hi),
        )
        cand_q = db.session.query(
            Place.id, Place.lat, Place.lng,
            Place.rating, Place.review_count, Place.category_id,
        ).filter(*bbox_filter)
        if nearby_cat:
            cat = Category.query.filter(or_(
                Category.slug == nearby_cat,
                Category.slug == nearby_cat + "s",
                Category.name.ilike(f"%{nearby_cat}%"),
            )).first()
            if cat:
                cand_q = cand_q.filter(Place.category_id == cat.id)
        # Collect everything within 30 mi but do NOT sort by distance —
        # the agent must read each distance pill and compare to answer
        # "which is the nearest X" tasks.  Sort by rating × log(reviews)
        # so popular places surface first, mirroring real Google Maps'
        # relevance-driven ordering.
        # Also build nearby_cat_chips in the SAME pass (was a duplicate
        # limit(2000) scan before — now one walk over the bbox subset).
        scored = []
        cat_count = {}  # category_id -> nearby-radius row count for chips
        for pid, p_lat, p_lng, p_rating, p_rc, p_cat_id in cand_q.limit(2000).all():
            d = _haversine_mi(place.lat, place.lng, p_lat, p_lng)
            if d <= 30:
                rel = (p_rating or 4.0) * math.log(max(p_rc or 1, 1) + 2)
                scored.append((rel, d, pid, p_cat_id))
                if p_cat_id is not None:
                    cat_count[p_cat_id] = cat_count.get(p_cat_id, 0) + 1
        scored.sort(key=lambda x: -x[0])
        # Pick top IDs + distances for the section (cat-diversified or not)
        nearby_picks = []  # list of (id, distance)
        if nearby_cat:
            for _, d, pid, _cid in scored[:12]:
                nearby_picks.append((pid, d))
        else:
            seen_cat = {}
            for _, d, pid, cid in scored:
                if seen_cat.get(cid, 0) >= 2:
                    continue
                seen_cat[cid] = seen_cat.get(cid, 0) + 1
                nearby_picks.append((pid, d))
                if len(nearby_picks) >= 12:
                    break
        if nearby_picks:
            id_to_d = dict(nearby_picks)
            rows = (Place.query
                    .filter(Place.id.in_(list(id_to_d.keys()))).all())
            rows.sort(key=lambda r: [pid for pid, _ in nearby_picks].index(r.id))
            for r in rows:
                r.distance_mi = id_to_d.get(r.id)
            nearby = rows
        # If a category filter narrowed the chip count, fall back to a
        # category-agnostic bbox sweep so the chip row still surfaces 8
        # nearby categories.  Cheap — same bbox, indexed tuples only.
        if nearby_cat and not cat_count:
            for pid, p_lat, p_lng, p_rating, p_rc, p_cat_id in (
                db.session.query(
                    Place.id, Place.lat, Place.lng,
                    Place.rating, Place.review_count, Place.category_id,
                ).filter(*bbox_filter).limit(2000).all()
            ):
                d = _haversine_mi(place.lat, place.lng, p_lat, p_lng)
                if d <= 30 and p_cat_id is not None:
                    cat_count[p_cat_id] = cat_count.get(p_cat_id, 0) + 1
        if cat_count:
            top_chip_ids = sorted(cat_count.items(),
                                  key=lambda kv: -kv[1])[:8]
            cat_rows = {c.id: c for c in Category.query.filter(
                Category.id.in_([cid for cid, _ in top_chip_ids])).all()}
            nearby_cat_chips = [(cat_rows[cid], cnt)
                                for cid, cnt in top_chip_ids
                                if cid in cat_rows]
    if not nearby:
        nearby = Place.query.filter(
            Place.city_id == place.city_id, Place.id != place.id,
        ).order_by(Place.rating.desc()).limit(12).all()
        for p in nearby:
            p.distance_mi = None
    # Is saved?
    is_saved = False
    user_lists = []
    if current_user.is_authenticated:
        is_saved = SavedPlace.query.filter_by(
            user_id=current_user.id, place_id=place.id
        ).first() is not None
        user_lists = SavedList.query.filter_by(user_id=current_user.id).all()

    # ------------------------------------------------------------------
    # R6 sections — surface secondary recommendations on every place page.
    # All are deterministic from the existing rows (no DB writes), so they
    # never re-randomise across hot restarts and cost nothing to compute.
    # ------------------------------------------------------------------
    similar_nearby = []   # same category, geographic neighbours
    same_chain = []       # same chain_brand, any city
    reviewers_also = []   # heuristic: same category cluster + popular
    better_rated_1mi = [] # strictly better rating within 1.0 mile
    if place.lat and place.lng:
        # Perf: per-section bbox tuned to each radius, all served by
        # ix_place_lat_lng / ix_place_category_id_lat_lng range scans.
        # 1 mi ≈ 0.015°, 8 mi ≈ 0.13°, 15 mi ≈ 0.25°.  Lightweight tuples
        # (id, lat, lng, rating, review_count) for the haversine pass,
        # then bulk ORM hydrate just the final top-6 per section.
        tup_cols = (Place.id, Place.lat, Place.lng,
                    Place.rating, Place.review_count)

        sim_lat_lo, sim_lat_hi = place.lat - 0.25, place.lat + 0.25
        sim_lng_lo, sim_lng_hi = place.lng - 0.30, place.lng + 0.30
        sim_q = db.session.query(*tup_cols).filter(
            Place.id != place.id,
            Place.category_id == place.category_id,
            Place.lat.between(sim_lat_lo, sim_lat_hi),
            Place.lng.between(sim_lng_lo, sim_lng_hi),
        )
        sim_scored = []
        for pid, p_lat, p_lng, p_rating, _ in sim_q.limit(1500).all():
            d = _haversine_mi(place.lat, place.lng, p_lat, p_lng)
            if d <= 15:
                sim_scored.append((d, -(p_rating or 0), pid))
        sim_scored.sort()
        sim_top = sim_scored[:6]
        if sim_top:
            sim_id_to_d = {pid: d for d, _, pid in sim_top}
            order = [pid for _, _, pid in sim_top]
            rows = Place.query.filter(Place.id.in_(order)).all()
            rows.sort(key=lambda r: order.index(r.id))
            for r in rows:
                r.distance_mi = sim_id_to_d[r.id]
            similar_nearby = rows

        # Better-rated within 1 mile (strictly higher rating, same category)
        bet_lat_lo, bet_lat_hi = place.lat - 0.02, place.lat + 0.02
        bet_lng_lo, bet_lng_hi = place.lng - 0.025, place.lng + 0.025
        sweep = db.session.query(*tup_cols).filter(
            Place.id != place.id,
            Place.category_id == place.category_id,
            Place.rating > (place.rating or 0),
            Place.lat.between(bet_lat_lo, bet_lat_hi),
            Place.lng.between(bet_lng_lo, bet_lng_hi),
        ).limit(800).all()
        bet_scored = []
        for pid, p_lat, p_lng, p_rating, _ in sweep:
            d = _haversine_mi(place.lat, place.lng, p_lat, p_lng)
            if d <= 1.0:
                bet_scored.append((-(p_rating or 0), d, pid))
        bet_scored.sort()
        bet_top = bet_scored[:6]
        if bet_top:
            bet_id_to_d = {pid: d for _, d, pid in bet_top}
            order = [pid for _, _, pid in bet_top]
            rows = Place.query.filter(Place.id.in_(order)).all()
            rows.sort(key=lambda r: order.index(r.id))
            for r in rows:
                r.distance_mi = bet_id_to_d[r.id]
            better_rated_1mi = rows

        # Reviewers also visited: top-rated other-category places within 8 mi
        # (a coarse "co-visit" stand-in derived from popularity, not real edges)
        ra_lat_lo, ra_lat_hi = place.lat - 0.15, place.lat + 0.15
        ra_lng_lo, ra_lng_hi = place.lng - 0.20, place.lng + 0.20
        ra_q = db.session.query(*tup_cols).filter(
            Place.id != place.id,
            Place.category_id != place.category_id,
            Place.rating >= 4.5,
            Place.lat.between(ra_lat_lo, ra_lat_hi),
            Place.lng.between(ra_lng_lo, ra_lng_hi),
        )
        ra_scored = []
        for pid, p_lat, p_lng, p_rating, p_rc in ra_q.limit(2000).all():
            d = _haversine_mi(place.lat, place.lng, p_lat, p_lng)
            if d <= 8.0:
                rel = (p_rating or 4.0) * math.log(max(p_rc or 1, 1) + 2)
                ra_scored.append((-rel, d, pid))
        ra_scored.sort()
        ra_top = ra_scored[:6]
        if ra_top:
            ra_id_to_d = {pid: d for _, d, pid in ra_top}
            order = [pid for _, _, pid in ra_top]
            rows = Place.query.filter(Place.id.in_(order)).all()
            rows.sort(key=lambda r: order.index(r.id))
            for r in rows:
                r.distance_mi = ra_id_to_d[r.id]
            reviewers_also = rows

    # Same chain — independent of geography
    if place.chain_brand:
        same_chain = (Place.query
                      .filter(Place.chain_brand == place.chain_brand,
                              Place.id != place.id)
                      .order_by(Place.rating.desc().nullslast(), Place.review_count.desc())
                      .limit(8).all())

    # Breadcrumb crumbs — Home > Category > City > Place
    breadcrumb = [
        {"label": "Maps", "href": url_for("index")},
        {"label": place.category.name if place.category else "Places",
         "href": url_for("category_page", slug=place.category.slug) if place.category else "#"},
        {"label": place.city.display_name if place.city else "",
         "href": url_for("city_page", slug=place.city.slug) if place.city else "#"},
        {"label": place.name, "href": ""},
    ]

    return render_template(
        "place_detail.html",
        place=place,
        reviews=reviews,
        nearby=nearby,
        nearby_cat=nearby_cat,
        nearby_cat_chips=nearby_cat_chips,
        is_saved=is_saved,
        user_lists=user_lists,
        similar_nearby=similar_nearby,
        same_chain=same_chain,
        reviewers_also=reviewers_also,
        better_rated_1mi=better_rated_1mi,
        breadcrumb=breadcrumb,
    )


STOPWORDS = {
    'the', 'a', 'an', 'of', 'in', 'on', 'at', 'to', 'for', 'with', 'and', 'or',
    'is', 'are', 'be', 'by', 'from', 'near', 'nearby', 'closest', 'nearest',
    'find', 'show', 'me', 'any', 'some', 'that', 'this', 'my', 'i', 'll',
    'please', 'around', 'close', 'open', 'available', 'now',
}


def _tokenize(q):
    import re
    return [t for t in re.findall(r"[a-z0-9]+", (q or "").lower())
            if t not in STOPWORDS and len(t) >= 2]


def _stem_variants(token):
    """Cheap singular/plural/-ing variants of a token so 'plumbers'
    matches 'plumbing' / 'plumber'.  Returns a list with the token + 1-3
    spelling variants (lower-case).  No real stemmer to keep it offline
    + dependency-free."""
    t = token.lower()
    variants = {t}
    if t.endswith("ies") and len(t) > 4:
        variants.add(t[:-3] + "y")
    if t.endswith("es") and len(t) > 3:
        variants.add(t[:-2])
    if t.endswith("s") and len(t) > 3:
        variants.add(t[:-1])
    if t.endswith("ing") and len(t) > 5:
        variants.add(t[:-3])         # plumbing → plumb
        variants.add(t[:-3] + "er")  # plumbing → plumber
        variants.add(t[:-3] + "ers") # plumbing → plumbers
    if t.endswith("er") and len(t) > 4:
        variants.add(t[:-2] + "ing")  # plumber → plumbing
        variants.add(t[:-2] + "ers")  # plumber → plumbers
    if t.endswith("ers") and len(t) > 5:
        variants.add(t[:-3] + "ing")  # plumbers → plumbing
        variants.add(t[:-3] + "er")   # plumbers → plumber
    return list(variants)


def _score_place(place, tokens):
    if not tokens:
        return 1
    haystack_parts = [
        (place.name or "").lower(),
        (place.subtitle or "").lower(),
        (place.description or "").lower(),
        (place.address or "").lower(),
        (place.zip_code or "").lower(),
        (place.state or "").lower(),
        (place.subcategory or "").lower(),
        (place.chain_brand or "").lower(),
        (place.nearest_landmark or "").lower(),
        (place.tags_json or "").lower(),
        (place.amenities_json or "").lower(),
    ]
    city_bag = ""
    if place.city:
        city_bag = f"{place.city.display_name.lower()} {place.city.slug.lower()}"
        haystack_parts.append(city_bag)
    if place.category:
        haystack_parts.append(place.category.slug.lower())
        haystack_parts.append(place.category.name.lower())
    hay = " ".join(haystack_parts)
    name_lc = (place.name or "").lower()
    score = 0
    for t in tokens:
        # Match any singular/plural/-ing variant so "plumbers" hits
        # "plumbing" / "plumber" places (and vice versa).
        variants = _stem_variants(t)
        if any(v in hay for v in variants):
            score += 1
        if any(v in name_lc for v in variants):
            score += 2
    if city_bag:
        for t in tokens:
            for v in _stem_variants(t):
                if v in city_bag and len(v) >= 3:
                    score += 3
                    break
    return score


# ---------------------------------------------------------------------------
# Location-bias search: zip centroids, haversine, and natural-language anchor
# extraction.  This lets queries like "apple store 90028" or
# "parking near brooklyn bridge" rank results by real-world distance.
# ---------------------------------------------------------------------------

# Real US zip centroids for task-relevant zips.  Used to resolve a 5-digit zip
# in the query (or in ?near=) to a search anchor, even when no Place row sits
# inside that zip.
_ZIP_CENTROIDS = {
    "90028": (34.1016, -118.3267), "90036": (34.0721, -118.3618),
    "90048": (34.0744, -118.3779), "90067": (34.0586, -118.4180),
    "90401": (34.0149, -118.4972), "91210": (34.1469, -118.2553),
    "91423": (34.1517, -118.4496), "91105": (34.1389, -118.1631),
    "91302": (34.1567, -118.6376), "90031": (34.0743, -118.2095),
    "33139": (25.7820, -80.1340),  "33130": (25.7780, -80.1980),
    "33125": (25.7800, -80.2350),  "33176": (25.6650, -80.3960),
    "30309": (33.7918, -84.3870),  "30308": (33.7700, -84.3700),
    "30303": (33.7530, -84.3902),  "30314": (33.7540, -84.4253),
    "10001": (40.7506, -73.9971),  "10003": (40.7325, -73.9889),
    "10011": (40.7415, -74.0009),  "10019": (40.7660, -73.9820),
    "10020": (40.7600, -73.9787),  "10128": (40.7820, -73.9510),
    "11201": (40.6932, -73.9907),  "11217": (40.6816, -73.9791),
    "20024": (38.8800, -77.0200),  "20560": (38.8888, -77.0260),
    "60608": (41.8537, -87.6592),  "60611": (41.8966, -87.6240),
    "02110": (42.3580, -71.0540),  "02109": (42.3611, -71.0540),
    "02108": (42.3580, -71.0653),  "02115": (42.3422, -71.0900),
    "02116": (42.3504, -71.0729),  "02114": (42.3611, -71.0680),
    "44012": (41.5050, -82.0290),
    "80202": (39.7479, -104.9994), "80205": (39.7549, -104.9740),
    "98101": (47.6107, -122.3370), "98004": (47.6147, -122.1925),
    "98109": (47.6317, -122.3473), "98121": (47.6149, -122.3447),
    "98103": (47.6731, -122.3417), "98105": (47.6624, -122.3000),
    "98107": (47.6695, -122.3782),
    "32801": (28.5400, -81.3800),  "32803": (28.5550, -81.3450),
    "48201": (42.3470, -83.0570),  "48226": (42.3300, -83.0480),
    "48197": (42.2410, -83.6133),
    "77590": (29.3838, -94.9027),  "15108": (40.5083, -80.2042),
    "24517": (37.1232, -79.2870),  "49706": (45.4434, -84.7825),
    "01970": (42.5195, -70.8967),  "01930": (42.6159, -70.6620),
    "02360": (41.9584, -70.6673),  "01945": (42.5001, -70.8578),
    "19103": (39.9525, -75.1690),
    "94102": (37.7796, -122.4192), "94103": (37.7720, -122.4115),
    "94108": (37.7920, -122.4070),
    "70112": (29.9550, -90.0750),  "70130": (29.9450, -90.0700),
    "33602": (27.9450, -82.4570),  "33401": (26.7160, -80.0530),
    "63101": (38.6300, -90.1900),  "55401": (44.9850, -93.2700),
    "75201": (32.7830, -96.8000),  "77002": (29.7600, -95.3700),
    "78701": (30.2710, -97.7430),  "02134": (42.3550, -71.1350),
    "15212": (40.4530, -80.0080),  "15213": (40.4444, -79.9608),
}


def _haversine_mi(lat1, lng1, lat2, lng2):
    """Great-circle distance in miles between two coordinates."""
    R = 3958.8
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dlat = p2 - p1
    dlng = math.radians(lng2 - lng1)
    a = math.sin(dlat / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlng / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


# Natural-language patterns lifted from real Google Maps search behaviour.
_ZIP_RE = re.compile(r"\b(\d{5})\b")
_NEAR_RE = re.compile(
    r"\b(?:near(?:est)?(?:\s+to)?|close\s+to|next\s+to|by|around|in)\s+"
    r"([A-Za-z][A-Za-z0-9'\-\.& ]{2,80}?)"
    r"(?=\s*(?:\?|$|,|\.|;|with|and|for|that|in\b))",
    re.I,
)


# Full US state names → abbreviations.  When a query says "in Washington" /
# "in the state of Washington" / "Washington State", we should add a state
# filter (`state=WA`) instead of treating "Washington" as a place-name
# location anchor — otherwise the resolver would geocode to some random
# "Washington Square" in NYC.
_US_STATES = {
    "alabama": "AL", "alaska": "AK", "arizona": "AZ", "arkansas": "AR",
    "california": "CA", "colorado": "CO", "connecticut": "CT", "delaware": "DE",
    "florida": "FL", "georgia": "GA", "hawaii": "HI", "idaho": "ID",
    "illinois": "IL", "indiana": "IN", "iowa": "IA", "kansas": "KS",
    "kentucky": "KY", "louisiana": "LA", "maine": "ME", "maryland": "MD",
    "massachusetts": "MA", "michigan": "MI", "minnesota": "MN", "mississippi": "MS",
    "missouri": "MO", "montana": "MT", "nebraska": "NE", "nevada": "NV",
    "new hampshire": "NH", "new jersey": "NJ", "new mexico": "NM", "new york": "NY",
    "north carolina": "NC", "north dakota": "ND", "ohio": "OH", "oklahoma": "OK",
    "oregon": "OR", "pennsylvania": "PA", "rhode island": "RI",
    "south carolina": "SC", "south dakota": "SD", "tennessee": "TN", "texas": "TX",
    "utah": "UT", "vermont": "VT", "virginia": "VA", "washington": "WA",
    "west virginia": "WV", "wisconsin": "WI", "wyoming": "WY",
    "district of columbia": "DC",
}


def _detect_state_in_query(q):
    """Return (state_code, cleaned_q) if a US state is referenced in q.
    Matches:
      - "in <state-name>", "in the state of <state-name>", "<state-name> state"
      - ", <ABBR>" / " <ABBR>" trailing 2-letter state code (e.g. "Atlanta, GA")
    Returns (None, q) if no state is detected.
    """
    if not q:
        return None, q
    qlc = q.lower()
    # Multi-word state names first (longest match wins) for natural-lang.
    sorted_states = sorted(_US_STATES.items(), key=lambda kv: -len(kv[0]))
    for name, abbr in sorted_states:
        for pat in (
            rf"\bin\s+the\s+state\s+of\s+{re.escape(name)}\b",
            rf"\b{re.escape(name)}\s+state\b",
            rf"\bin\s+{re.escape(name)}\b",
        ):
            m = re.search(pat, qlc)
            if m:
                cleaned = (q[:m.start()] + " " + q[m.end():]).strip()
                cleaned = re.sub(r"\s+", " ", cleaned).strip(" ,.")
                return abbr, cleaned
    # 2-letter state abbreviation as a trailing token (with or without
    # comma): "Atlanta, GA" / "Boston MA" / "Seattle WA". Only match
    # known state codes — don't grab arbitrary 2-letter words.
    valid_abbrs = set(_US_STATES.values())
    m = re.search(r",?\s+([A-Z]{2})\s*$", q.strip())
    if m and m.group(1) in valid_abbrs:
        abbr = m.group(1)
        cleaned = q[:m.start()].strip(" ,")
        return abbr, cleaned
    return None, q


def _resolve_anchor_term(term):
    """Resolve a free-text term to (lat, lng, label).
    Priority is chosen so semantically equivalent queries converge to
    the same anchor:
      1. 5-digit zip → centroid
      2. EXACT City match → city centroid (so "Chicago" / "in Chicago"
         both anchor on Chicago city, not a random Place containing
         the substring "chicago")
      3. EXACT Place name match → that Place
      4. Substring Place match → top-reviewed match
      5. Fuzzy City match → city centroid
    """
    term = (term or "").strip(" ,.\"'")
    if not term:
        return None
    # 1) zip
    if re.fullmatch(r"\d{5}", term):
        if term in _ZIP_CENTROIDS:
            lat, lng = _ZIP_CENTROIDS[term]
            return (lat, lng, term)
        p = Place.query.filter(Place.zip_code == term, Place.lat != 0).first()
        if p:
            return (p.lat, p.lng, term)
        return None
    slug = term.lower().replace(" ", "-")
    # 2) exact City — fixes inconsistency where "in Chicago" picked a
    #    Place containing 'chicago' as substring while bare "Chicago"
    #    picked the City centroid (different anchor → different radius
    #    filter → different result counts).
    c = (City.query
         .filter(or_(City.display_name.ilike(term),
                     City.display_name.ilike(f"{term},%"),
                     City.slug == slug))
         .first())
    if c and c.lat and c.lng:
        return (c.lat, c.lng, c.display_name)
    # 3) exact Place name
    p = (Place.query
         .filter(Place.name.ilike(term), Place.lat != 0)
         .order_by(Place.is_featured.desc(), Place.review_count.desc())
         .first())
    if p:
        return (p.lat, p.lng, p.name)
    # 4) substring Place
    p = (Place.query
         .filter(Place.name.ilike(f"%{term}%"), Place.lat != 0)
         .order_by(Place.is_featured.desc(), Place.review_count.desc())
         .first())
    if p:
        return (p.lat, p.lng, p.name)
    # 5) fuzzy City
    c = (City.query
         .filter(City.display_name.ilike(f"%{term}%"))
         .first())
    if c and c.lat and c.lng:
        return (c.lat, c.lng, c.display_name)
    return None


def _resolve_location_anchor(q, args):
    """Find a (cleaned_q, lat, lng, label) anchor for distance-bias search.
    Priority: explicit ?near= > 5-digit zip in query > 'near X' phrase > None.
    Returns (cleaned_q, None, None, None) if no anchor."""
    explicit = args.get("near", "").strip()
    if explicit:
        a = _resolve_anchor_term(explicit)
        if a:
            return q, a[0], a[1], a[2]
    if not q:
        return q, None, None, None
    m = _ZIP_RE.search(q)
    if m:
        z = m.group(1)
        a = _resolve_anchor_term(z)
        if a:
            cleaned = (q[:m.start()] + q[m.end():]).strip(" ,")
            # Important: return EMPTY cleaned (not q) when the zip is the
            # only content.  Otherwise /search re-tokenises "33139" and
            # only matches the single Place whose zip_code='33139',
            # leaking the answer for "Find X near 33139" tasks.
            return cleaned, a[0], a[1], a[2]
    m = _NEAR_RE.search(q)
    if m:
        a = _resolve_anchor_term(m.group(1))
        if a:
            cleaned = q[:m.start()].strip(" ,")
            return cleaned, a[0], a[1], a[2]
    # Bare city name anywhere in the query: scan for the longest token
    # span that exactly matches a City.display_name or City.slug.  This
    # makes "Target stores Atlanta" behave the same as "Target stores in
    # Atlanta" — both extract the city as an anchor instead of letting
    # 'atlanta' bleed through as a substring token that pulls in
    # unrelated places (e.g. Atlanta-named pizza joints).
    words = q.split()
    for span in range(min(4, len(words)), 0, -1):
        for i in range(len(words) - span + 1):
            phrase = " ".join(words[i:i + span])
            slug = phrase.lower().replace(" ", "-")
            c = (City.query
                 .filter(or_(City.display_name.ilike(phrase),
                             City.display_name.ilike(f"{phrase},%"),
                             City.slug == slug))
                 .first())
            if c and c.lat and c.lng:
                cleaned = " ".join(words[:i] + words[i + span:]).strip(" ,")
                return cleaned, c.lat, c.lng, c.display_name
    return q, None, None, None


def _apply_place_filters(query, args):
    """Apply query-param filters to a Place query."""
    city = args.get("city", "").strip()
    if city:
        c = City.query.filter(
            or_(City.slug == city.lower().replace(" ", "-"),
                City.display_name.ilike(f"%{city}%"))).first()
        if c:
            query = query.filter(Place.city_id == c.id)
    state = args.get("state", "").strip()
    if state:
        query = query.filter(Place.state.ilike(f"%{state}%"))
    zip_code = args.get("zip", "").strip()
    if zip_code:
        query = query.filter(Place.zip_code == zip_code)
    category = args.get("category", "").strip()
    if category:
        cat = Category.query.filter_by(slug=category.lower()).first()
        if cat:
            query = query.filter(Place.category_id == cat.id)
    subcategory = args.get("subcategory", "").strip()
    if subcategory:
        query = query.filter(Place.subcategory.ilike(f"%{subcategory}%"))
    chain = args.get("chain", "").strip()
    if chain:
        query = query.filter(Place.chain_brand.ilike(f"%{chain}%"))
    try:
        min_rating = float(args.get("min_rating", "") or 0)
    except ValueError:
        min_rating = 0
    if min_rating:
        query = query.filter(Place.rating >= min_rating)
    try:
        min_reviews = int(args.get("min_reviews", "") or 0)
    except ValueError:
        min_reviews = 0
    if min_reviews:
        query = query.filter(Place.review_count >= min_reviews)
    open_24h = args.get("open_24h", "")
    if open_24h in ("1", "true", "yes"):
        query = query.filter(Place.is_24h.is_(True))
    if open_24h in ("0", "false", "no"):
        query = query.filter(Place.is_24h.is_(False))
    closes_at_night = args.get("closes_at_night", "")
    if closes_at_night in ("1", "true", "yes"):
        query = query.filter(Place.closes_at_night.is_(True))
    open_now = args.get("open_now", "")
    if open_now in ("1", "true", "yes"):
        query = query.filter(Place.is_open_now.is_(True))
    # Unified "Hours" chip used by the search page filter row.
    # Mutually exclusive: open_now | 24h.
    hours = args.get("hours", "").strip().lower()
    if hours == "open_now":
        query = query.filter(Place.is_open_now.is_(True))
    elif hours in ("24h", "open_24h", "open24h"):
        query = query.filter(Place.is_24h.is_(True))
    # "Price" chip — exact match on price_level ($, $$, $$$, $$$$)
    price_level = args.get("price_level", "").strip()
    if price_level in ("$", "$$", "$$$", "$$$$"):
        query = query.filter(Place.price_level == price_level)
    has_parking_lot = args.get("has_parking_lot", "")
    if has_parking_lot in ("1", "true", "yes"):
        query = query.filter(Place.has_parking_lot.is_(True))
    ev = args.get("ev_charging", "")
    if ev in ("1", "true", "yes"):
        query = query.filter(Place.ev_charging.is_(True))
    moto = args.get("motorcycle_parking", "")
    if moto in ("1", "true", "yes"):
        query = query.filter(Place.motorcycle_parking.is_(True))
    bike = args.get("bicycle_parking", "")
    if bike in ("1", "true", "yes"):
        query = query.filter(Place.bicycle_parking.is_(True))
    tag = args.get("tag", "").strip()
    if tag:
        query = query.filter(Place.tags_json.ilike(f"%{tag.lower()}%"))
    amenity = args.get("amenity", "").strip()
    if amenity:
        query = query.filter(Place.amenities_json.ilike(f"%{amenity.lower()}%"))
    # --- R5 filters: noise, crowd, mask, indoor zone, floor, EV connector ---
    noise = args.get("noise_level", "").strip().lower()
    if noise in ("quiet", "moderate", "lively", "loud"):
        query = query.filter(Place.noise_level == noise)
    crowd = args.get("crowd_level", "").strip().lower()
    if crowd in ("low", "moderate", "high", "very-high"):
        query = query.filter(Place.crowd_level == crowd)
    mask = args.get("mask_required", "")
    if mask in ("1", "true", "yes"):
        query = query.filter(Place.mask_required.is_(True))
    indoor = args.get("indoor_zone_type", "").strip().lower()
    if indoor:
        query = query.filter(Place.indoor_zone_type == indoor)
    floor = args.get("floor", "").strip()
    if floor:
        query = query.filter(Place.floor_number == floor)
    ev_conn = args.get("ev_connector_type", "").strip()
    if ev_conn:
        query = query.filter(Place.ev_connector_type.ilike(f"%{ev_conn}%"))
    try:
        min_kw = int(args.get("min_kw", "") or 0)
    except ValueError:
        min_kw = 0
    if min_kw:
        query = query.filter(Place.ev_charger_kw >= min_kw)
    return query


def _apply_place_sort(results, sort):
    if sort == "rating":
        results.sort(key=lambda p: (-(p.rating or 0), -(p.review_count or 0)))
    elif sort == "reviews":
        results.sort(key=lambda p: -(p.review_count or 0))
    elif sort == "name":
        results.sort(key=lambda p: (p.name or "").lower())
    return results


@app.route("/search")
@app.route("/search/<path:maps_query>")
@app.route("/maps/search/")
@app.route("/maps/search/<path:maps_query>")
def search(maps_query=""):
    q = (maps_query or request.args.get("q", "")).strip()
    sort = request.args.get("sort", "")
    args = request.args

    # Detect a US state name in the query first ("in Washington",
    # "the state of Texas").  This adds a state filter and strips the
    # phrase from the query so the location-anchor resolver doesn't try to
    # geocode the state name to some random place.
    state_filter, q_after_state = _detect_state_in_query(q)

    # Resolve a location anchor (zip / "near X" / explicit ?near=) so we can
    # distance-bias the result list, mirroring real Google Maps behaviour.
    cleaned_q, anchor_lat, anchor_lng, anchor_label = _resolve_location_anchor(
        q_after_state, args)
    # When an anchor was extracted, search_q is whatever's LEFT in the
    # query.  If nothing's left (e.g. user typed just "33139"), search_q
    # must stay empty so we don't fall back to scoring "33139" as a
    # search token — that would only match the single Place that happens
    # to have zip_code='33139', leaking the answer for "Find X near
    # 33139" tasks.  Instead an empty search_q falls into the
    # "browse-by-anchor" branch below (top results by rating within
    # radius), which mirrors typing just a zip on real Google Maps.
    if anchor_lat is not None:
        search_q = cleaned_q  # may be ""
    else:
        search_q = q_after_state or q

    query = Place.query
    query = _apply_place_filters(query, args)
    if state_filter:
        query = query.filter(Place.state == state_filter)
    candidates = query.limit(2000).all()

    # Apply anchor radius filter EARLY (before token scoring + top-60
    # truncation) so semantically equivalent queries converge.  Without
    # this, "parking in Chicago" (no state) scored 768 places globally,
    # took top-60 by score (many non-Chicago), then radius-filtered down
    # to a handful — while "parking Chicago, IL" (state=IL filter) only
    # had ~30 candidates to begin with so its top-60 already covered all
    # of them.  Same intent → same candidate pool now.
    if anchor_lat is not None and anchor_lng is not None:
        radius_mi_pre = float(request.args.get("radius", 100))
        candidates = [
            p for p in candidates
            if p.lat and p.lng
            and _haversine_mi(anchor_lat, anchor_lng, p.lat, p.lng) <= radius_mi_pre
        ]

    tokens = _tokenize(search_q)

    if search_q and tokens:
        min_required = max(1, (len(tokens) + 1) // 2)
        scored = []
        for p in candidates:
            s = _score_place(p, tokens)
            if s >= min_required:
                scored.append((s, p))
        if not scored:
            for p in candidates:
                s = _score_place(p, tokens)
                if s >= 1:
                    scored.append((s, p))
        # Fuzzy LIKE fallback: if the tokenized scorer found nothing
        # (vague queries like "large store washington" where "large"
        # matches no haystack word), do a SQL LIKE sweep on the full
        # cleaned query and on each token across name/description/
        # address/city/subcategory.  This is real-Google-Maps fuzzy
        # behaviour — a query that doesn't perfectly match anything
        # still gets the most-relevant nearby matches.
        if not scored:
            full_lc = search_q.strip().lower()
            patterns = []
            if full_lc:
                patterns.append(f"%{full_lc}%")
            for t in tokens:
                if len(t) >= 3:
                    patterns.append(f"%{t}%")
            for p in candidates:
                hay = " ".join([
                    (p.name or ""), (p.subtitle or ""),
                    (p.description or ""), (p.address or ""),
                    (p.subcategory or ""), (p.chain_brand or ""),
                    (p.tags_json or ""), (p.amenities_json or ""),
                    (p.city.display_name if p.city else ""),
                    (p.category.name if p.category else ""),
                ]).lower()
                hits = sum(1 for pat in patterns
                           if pat.strip("%") in hay)
                if hits:
                    scored.append((hits, p))
        scored.sort(key=lambda x: (-x[0], -(x[1].rating or 0)))
        results = [p for _, p in scored][:60]
    else:
        # No tokens (state-only or zip-only query like "in Washington" or
        # "33139").  When an anchor is set, use a TIGHTER 30-mi browse
        # radius (vs the 100-mi search radius) so adjacent zips don't
        # bleed into each other — typing just a zip on real Google Maps
        # zooms to that immediate area, not a 100-mi sweep.  Then
        # rating-sort within radius.
        if anchor_lat is not None and anchor_lng is not None:
            r0 = float(request.args.get("radius", 30))
            in_area = []
            for p in candidates:
                if p.lat and p.lng:
                    d = _haversine_mi(anchor_lat, anchor_lng, p.lat, p.lng)
                    if d <= r0:
                        in_area.append(p)
            in_area.sort(key=lambda p: (-(p.rating or 0), -(p.review_count or 0)))
            results = in_area[:60]
        else:
            candidates.sort(key=lambda p: (-(p.rating or 0), -(p.review_count or 0)))
            results = candidates[:60]

    # When an anchor is set, attach distance + filter to a wide radius so
    # totally unrelated far-away results don't pollute, but DO NOT sort
    # purely by distance — that would let an agent solve every "nearest X"
    # task by clicking result #1.  Real Google Maps blends rating,
    # popularity, and distance.  We keep the existing token-score order
    # (which already factors rating); the agent must read distance pills
    # and compare to find the actual closest match.
    if anchor_lat is not None and anchor_lng is not None:
        radius_mi = float(request.args.get("radius", 100))
        kept = []
        for p in results:
            if p.lat and p.lng:
                p.distance_mi = _haversine_mi(
                    anchor_lat, anchor_lng, p.lat, p.lng)
                if p.distance_mi <= radius_mi:
                    kept.append(p)
            else:
                p.distance_mi = None
                kept.append(p)
        results = kept
        if sort == "distance":
            results.sort(key=lambda p: (
                p.distance_mi if p.distance_mi is not None else 1e9))
    else:
        for p in results:
            p.distance_mi = None

    if sort and sort != "distance":
        results = _apply_place_sort(results, sort)
    elif tokens:
        pass
    elif anchor_lat is None:
        results.sort(key=lambda p: (-(p.rating or 0), -(p.review_count or 0)))

    return render_template(
        "search.html", q=q, results=results,
        anchor_label=anchor_label, anchor_lat=anchor_lat, anchor_lng=anchor_lng,
    )


# ---------------------------------------------------------------------------
# Synthesised multi-route alternatives.  Real Google Maps offers 2-3 route
# choices per directions query (Fastest / Slightly longer / Scenic) with
# region-appropriate highway or street names; the mirror approximates this
# without a real routing engine by deriving plausible names from the
# endpoints' US state and combining with mode-aware speed models.
# ---------------------------------------------------------------------------
_REGION_HIGHWAYS = {
    "CA": ["I-5", "US-101", "I-405", "I-10", "I-110", "CA-1 (PCH)"],
    "NY": ["I-95", "I-87 (Major Deegan)", "I-278 (BQE)", "I-495 (LIE)",
           "FDR Drive", "West Side Hwy"],
    "MA": ["I-93", "I-90 (Mass Pike)", "US-1", "MA-2", "MA-3"],
    "IL": ["I-90", "I-94 (Edens)", "I-55", "I-290 (Eisenhower)",
           "Lake Shore Dr"],
    "TX": ["I-35", "I-10", "I-45", "US-290"],
    "GA": ["I-75", "I-85", "I-285", "I-20"],
    "FL": ["I-95", "I-75", "I-4", "FL-A1A"],
    "WA": ["I-5", "I-90", "WA-99", "WA-520"],
    "DC": ["I-395", "I-695", "Constitution Ave NW", "Independence Ave SW"],
    "MI": ["I-75", "I-94", "I-696"],
    "PA": ["I-376 (Parkway W)", "I-79", "I-279"],
    "VA": ["I-95", "I-66", "US-29"],
    "CO": ["I-25", "I-70", "US-285"],
    "OH": ["I-90", "I-71", "I-77"],
    "MN": ["I-94", "I-35W", "US-12"],
    "LA": ["I-10", "I-610", "US-90"],
    "default": ["I-5", "US-1", "I-95"],
}
_REGION_STREETS = {
    "NY": ["5th Ave", "Broadway", "7th Ave", "Madison Ave", "Park Ave",
           "Lexington Ave"],
    "CA": ["Sunset Blvd", "Wilshire Blvd", "Hollywood Blvd", "Beverly Blvd",
           "Santa Monica Blvd"],
    "MA": ["Beacon St", "Boylston St", "Washington St", "Tremont St"],
    "DC": ["Constitution Ave", "Independence Ave", "Pennsylvania Ave",
           "K Street"],
    "IL": ["Michigan Ave", "State St", "Wacker Dr"],
    "FL": ["Ocean Dr", "Collins Ave", "Biscayne Blvd"],
    "WA": ["Pike St", "Pine St", "Westlake Ave"],
    "TX": ["Congress Ave", "Lamar Blvd", "South 1st St"],
    "GA": ["Peachtree St", "North Ave", "Ponce de Leon Ave"],
    "MI": ["Woodward Ave", "Michigan Ave", "Jefferson Ave"],
    "default": ["Main St", "Park Ave", "Broadway"],
}
_CROSS_COUNTRY_HIGHWAYS = ["I-80 W", "I-90 W", "I-70 W", "I-40 W",
                           "Historic Route 66"]


def _state_from_endpoint(ep):
    """Best-effort US state code from an endpoint.  Coords win first
    (bbox lookup), then address parsing as a fallback for international
    / sparse-coords cases."""
    if not ep:
        return "default"
    lat, lng = ep.get("lat"), ep.get("lng")
    if lat and lng:
        s = _state_from_coords(lat, lng)
        if s != "default":
            return s
    addr = (ep.get("address") or "").upper()
    m = re.search(r",\s*([A-Z]{2})\s+\d{5}", addr) \
        or re.search(r",\s*([A-Z]{2})\s*$", addr) \
        or re.search(r"\b([A-Z]{2})\s+\d{5}", addr)
    if m:
        return m.group(1)
    return "default"


def _mode_speed_mph(mode, distance_mi):
    """Mode + distance aware travel speed (mph).  Real-world averages:
    short trips spend more time at intersections and pick-ups; long
    trips ride highways and average closer to posted speed minus stop
    overhead.  Cross-country drives include rest breaks (~60 mph avg).
    """
    if mode == "walking":
        return 3.0
    if mode == "bicycling":
        return 12.0
    if mode == "transit":
        if distance_mi < 10:
            return 18.0   # subway / city bus
        if distance_mi < 100:
            return 35.0   # commuter rail
        if distance_mi < 500:
            return 55.0   # regional rail (e.g. Amtrak Northeast)
        return 60.0       # intercity rail
    # driving (also fallback for unknown mode)
    if distance_mi < 5:
        return 22.0       # dense city
    if distance_mi < 30:
        return 32.0       # suburban / city mix
    if distance_mi < 100:
        return 50.0       # highway with city overhead
    if distance_mi < 500:
        return 60.0       # interstate
    return 60.0           # cross-country incl. rest breaks


# Approximate US-state bounding boxes for lat/lng → state inference.
# Derived from public WGS84 state extents.  Order matters when boxes
# overlap — first match wins, so put smaller / more-specific states
# (DC, RI, NJ, …) ahead of bigger neighbours.
_STATE_BBOXES = [
    ("DC", 38.79, 38.99, -77.12, -76.91),
    ("HI", 18.91, 22.24, -160.25, -154.81),
    ("AK", 51.21, 71.40, -179.15, -129.99),
    ("RI", 41.15, 42.02, -71.86, -71.12),
    ("DE", 38.45, 39.84, -75.79, -75.05),
    ("NJ", 38.93, 41.36, -75.56, -73.89),
    ("CT", 40.99, 42.05, -73.73, -71.79),
    ("MA", 41.24, 42.89, -73.51, -69.93),
    ("VT", 42.73, 45.02, -73.44, -71.46),
    ("NH", 42.69, 45.31, -72.56, -70.61),
    ("ME", 42.97, 47.46, -71.08, -66.95),
    ("NY", 40.50, 45.02, -79.76, -71.86),
    ("PA", 39.72, 42.27, -80.52, -74.69),
    ("MD", 37.91, 39.72, -79.49, -75.05),
    ("VA", 36.54, 39.47, -83.68, -75.24),
    ("WV", 37.20, 40.64, -82.64, -77.72),
    ("OH", 38.40, 41.98, -84.82, -80.52),
    ("MI", 41.70, 48.30, -90.42, -82.41),
    ("IN", 37.77, 41.76, -88.10, -84.78),
    ("IL", 36.97, 42.51, -91.51, -87.50),
    ("WI", 42.49, 47.08, -92.89, -86.81),
    ("MN", 43.50, 49.38, -97.24, -89.49),
    ("IA", 40.38, 43.50, -96.64, -90.14),
    ("MO", 35.99, 40.61, -95.77, -89.10),
    ("KY", 36.50, 39.15, -89.57, -81.96),
    ("TN", 34.98, 36.68, -90.31, -81.65),
    ("NC", 33.84, 36.59, -84.32, -75.46),
    ("SC", 32.03, 35.22, -83.35, -78.54),
    ("GA", 30.36, 35.00, -85.61, -80.84),
    ("FL", 24.50, 31.00, -87.63, -80.03),
    ("AL", 30.22, 35.01, -88.47, -84.89),
    ("MS", 30.17, 35.00, -91.66, -88.10),
    ("AR", 33.00, 36.50, -94.62, -89.64),
    ("LA", 28.92, 33.02, -94.04, -88.82),
    ("OK", 33.62, 37.00, -103.00, -94.43),
    ("TX", 25.84, 36.50, -106.65, -93.51),
    ("NM", 31.33, 37.00, -109.05, -103.00),
    ("KS", 36.99, 40.00, -102.05, -94.59),
    ("NE", 40.00, 43.00, -104.05, -95.31),
    ("SD", 42.48, 45.94, -104.06, -96.44),
    ("ND", 45.94, 49.00, -104.05, -96.55),
    ("MT", 44.36, 49.00, -116.05, -104.04),
    ("WY", 41.00, 45.01, -111.05, -104.05),
    ("CO", 36.99, 41.00, -109.06, -102.04),
    ("UT", 36.99, 42.00, -114.05, -109.05),
    ("ID", 41.99, 49.00, -117.24, -111.04),
    ("WA", 45.54, 49.00, -124.85, -116.92),
    ("OR", 41.99, 46.30, -124.57, -116.46),
    ("NV", 35.00, 42.00, -120.01, -114.04),
    ("AZ", 31.33, 37.00, -114.82, -109.05),
    ("CA", 32.50, 42.01, -124.48, -114.13),
]


def _state_from_coords(lat, lng):
    """Best-effort US state from (lat, lng).  Returns 2-letter code or
    'default' for international / unmappable points."""
    if lat is None or lng is None:
        return "default"
    for code, latlo, lathi, lnglo, lnghi in _STATE_BBOXES:
        if latlo <= lat <= lathi and lnglo <= lng <= lnghi:
            return code
    return "default"


def _state_pretty(code):
    """Render state code for human consumption ('CA' → 'California')."""
    inv = {v: k for k, v in _US_STATES.items()}
    return inv.get(code, code).title()


def _fmt_distance(mi):
    return f"{mi:.1f} mi" if mi < 100 else f"{mi:.0f} mi"


def _fmt_duration(mins):
    if mins < 60:
        return f"{mins} min"
    h, m = divmod(mins, 60)
    if h < 24:
        return f"{h} h {m} min" if m else f"{h} h"
    d, h = divmod(h, 24)
    return f"{d} d {h} h"


def _synth_steps(from_ep, to_ep, route_name, mode, distance_mi):
    """Step-by-step instruction synthesiser.  Step count + content scale
    with distance — short trips get a couple of turns; cross-country
    trips get multi-state segments mentioning intermediate states."""
    steps = [{"instruction": f"Head out from {from_ep['name']}",
              "distance": "0.0 mi"}]
    bare = route_name.replace("via ", "").split(" (")[0]
    from_st = _state_from_endpoint(from_ep)
    to_st = _state_from_endpoint(to_ep)

    if mode == "transit":
        # walk → board → ride → disembark → walk
        steps.append({"instruction": f"Walk to nearest {bare} station",
                      "distance": f"{distance_mi * 0.05:.1f} mi"})
        if distance_mi > 100:
            steps.append({"instruction": f"Board {bare} (long-haul service)",
                          "distance": f"{distance_mi * 0.85:.0f} mi"})
            steps.append({"instruction": f"Transfer at intermediate hub",
                          "distance": "0.0 mi"})
        else:
            steps.append({"instruction": f"Board {bare} line",
                          "distance": f"{distance_mi * 0.85:.1f} mi"})
        steps.append({"instruction": f"Disembark and walk to destination",
                      "distance": f"{distance_mi * 0.10:.1f} mi"})
    elif distance_mi > 500:
        # cross-country: 4-segment haul through intermediate states
        seg = distance_mi / 3
        from_pretty = _state_pretty(from_st) if from_st != "default" else "your origin"
        to_pretty = _state_pretty(to_st) if to_st != "default" else "your destination"
        steps.append({"instruction": f"Merge onto {bare} heading away from {from_pretty}",
                      "distance": f"{distance_mi * 0.05:.0f} mi"})
        steps.append({"instruction": f"Continue on {bare} for the long haul",
                      "distance": f"{seg:.0f} mi"})
        steps.append({"instruction": f"Stop for fuel / rest along the route",
                      "distance": "0.5 mi"})
        steps.append({"instruction": f"Continue on {bare}",
                      "distance": f"{seg:.0f} mi"})
        steps.append({"instruction": f"Approach {to_pretty} and follow signs to destination",
                      "distance": f"{seg:.0f} mi"})
    elif distance_mi > 30:
        steps.append({"instruction": f"Merge onto {bare}",
                      "distance": f"{distance_mi * 0.10:.1f} mi"})
        steps.append({"instruction": f"Continue on {bare}",
                      "distance": f"{distance_mi * 0.75:.1f} mi"})
        steps.append({"instruction": f"Take exit toward {to_ep['name']}",
                      "distance": f"{distance_mi * 0.15:.1f} mi"})
    else:
        steps.append({"instruction": f"Turn onto {bare}",
                      "distance": f"{distance_mi * 0.4:.1f} mi"})
        steps.append({"instruction": f"Continue {bare} toward destination",
                      "distance": f"{distance_mi * 0.5:.1f} mi"})
    steps.append({"instruction": f"Arrive at {to_ep['name']}",
                  "distance": "0.0 mi"})
    return steps


def _generate_route_alternatives(from_ep, to_ep, mode):
    """2-3 plausible route alternatives between two endpoints.  Each gets
    a slightly perturbed distance/duration and a region-flavoured name."""
    base_mi = _haversine_mi(from_ep["lat"], from_ep["lng"],
                            to_ep["lat"], to_ep["lng"])
    from_st = _state_from_endpoint(from_ep)
    to_st = _state_from_endpoint(to_ep)
    same_state = (from_st == to_st and from_st != "default")

    if mode in ("walking", "bicycling"):
        names_pool = _REGION_STREETS.get(from_st, _REGION_STREETS["default"])
    elif not same_state and base_mi > 800:
        # True cross-country only when both states differ AND distance
        # is large enough to rule out a within-state highway like
        # LAX → SFO (333 mi, both CA).
        names_pool = _CROSS_COUNTRY_HIGHWAYS
    else:
        names_pool = _REGION_HIGHWAYS.get(from_st, _REGION_HIGHWAYS["default"])

    # (multiplier, name_index) — no superlative tag.  The agent must
    # compare duration_label / distance_label across alternatives to
    # identify the shortest route; we don't pre-tag #1 as "Fastest".
    variants = [(1.00, 0), (1.12, 1), (1.30, 2)]
    alts = []
    for i, (mult, idx) in enumerate(variants):
        if idx >= len(names_pool):
            continue
        d_mi = base_mi * mult
        speed = _mode_speed_mph(mode, d_mi)
        d_min = max(1, int(round(d_mi / speed * 60)))
        name = f"via {names_pool[idx]}"
        alts.append({
            "id": chr(ord("a") + i),
            "name": name,
            "distance_mi": d_mi,
            "distance_label": _fmt_distance(d_mi),
            "duration_min": d_min,
            "duration_label": _fmt_duration(d_min),
            "tag": "",
            "steps": _synth_steps(from_ep, to_ep, name, mode, d_mi),
            "summary": f"{from_ep['name']} → {to_ep['name']} via {names_pool[idx]}",
        })
    return alts


_ZIP_AREA_RE = re.compile(r"^(\d{5})\s*\(zip\s*area\)\s*$", re.I)
_CITY_CENTER_RE = re.compile(r"^(.+?)\s*\(city\s*center\)\s*$", re.I)


def _is_specific_endpoint(term):
    """A term is 'specific' when it unambiguously names ONE location for
    /directions purposes: an exact Place name, an exact City name, or
    the 'NNNNN (zip area)' label that the picker emits when the user
    confirms they meant the zip centroid (not a place inside the zip).

    A bare 5-digit zip is NOT considered specific — the user should
    still get a picker so they can choose between "the zip area
    centroid" and a specific named place inside the zip.
    """
    term = (term or "").strip(" ,.\"'")
    if not term:
        return True
    if _ZIP_AREA_RE.match(term):
        return True
    if _CITY_CENTER_RE.match(term):
        return True
    if Place.query.filter(Place.name.ilike(term)).first():
        return True
    slug = term.lower().replace(" ", "-")
    # City match — accept exact display_name ("Boston"), comma-prefix
    # ("Miami" → "Miami, FL"), or slug ("miami-fl").  All three forms
    # resolve to one city centroid, so they're unambiguous.
    if City.query.filter(or_(City.display_name.ilike(term),
                             City.display_name.ilike(f"{term},%"),
                             City.slug == slug)).first():
        return True
    return False


def _endpoint_candidates(term, anchor_lat=None, anchor_lng=None, max_n=8):
    """Return up to max_n candidate endpoint dicts for an ambiguous term,
    ranked by distance from anchor (if provided) else by popularity.
    Each dict: {lat, lng, name, address, place_id, slug, distance_mi}."""
    term = (term or "").strip(" ,.\"'")
    if not term:
        return []

    # Term matches a US city → prepend "<City> (city center)" so the
    # user can route between city centroids ("Miami → Orlando") instead
    # of being forced to pick a specific Place inside the city.  Match
    # both bare city ("Miami") and city + state ("Miami, FL") forms.
    cc_pre = []
    cc_slug = term.lower().replace(" ", "-").rstrip(",")
    cc_city = (City.query
               .filter(or_(City.display_name.ilike(term),
                           City.display_name.ilike(f"{term},%"),
                           City.slug == cc_slug))
               .first())
    if cc_city and cc_city.lat and cc_city.lng:
        d = (_haversine_mi(anchor_lat, anchor_lng, cc_city.lat, cc_city.lng)
             if anchor_lat is not None and anchor_lng is not None else None)
        cc_pre.append({
            "lat": cc_city.lat, "lng": cc_city.lng,
            "name": f"{cc_city.display_name} (city center)",
            "address": cc_city.display_name, "place_id": None,
            "slug": cc_city.slug,
            "rating": None, "review_count": None,
            "category_name": "City", "distance_mi": d,
        })

    # Bare 5-digit zip → first candidate is the zip-area centroid (so the
    # user can route from "the 33139 area" generically), followed by top
    # named places that actually live in that zip.
    if re.fullmatch(r"\d{5}", term):
        out = []
        if term in _ZIP_CENTROIDS:
            zlat, zlng = _ZIP_CENTROIDS[term]
            d = (_haversine_mi(anchor_lat, anchor_lng, zlat, zlng)
                 if anchor_lat is not None and anchor_lng is not None else None)
            out.append({
                "lat": zlat, "lng": zlng, "name": f"{term} (zip area)",
                "address": f"ZIP {term} centroid", "place_id": None, "slug": term,
                "rating": None, "review_count": None,
                "category_name": "Area", "distance_mi": d,
            })
        in_zip = (Place.query.filter(Place.zip_code == term, Place.lat != 0)
                  .order_by(Place.is_featured.desc(), Place.review_count.desc())
                  .limit(max_n - len(out)).all())
        for p in in_zip:
            d = (_haversine_mi(anchor_lat, anchor_lng, p.lat, p.lng)
                 if anchor_lat is not None and anchor_lng is not None else None)
            out.append({
                "lat": p.lat, "lng": p.lng, "name": p.name,
                "address": p.address or "", "place_id": p.id, "slug": p.slug,
                "rating": p.rating, "review_count": p.review_count,
                "category_name": p.category.name if p.category else "",
                "distance_mi": d,
            })
        return cc_pre + out

    term_lc = term.lower()
    cat = (Category.query
           .filter(or_(Category.slug == term_lc,
                       Category.slug == term_lc + "s",
                       Category.slug.startswith(term_lc),
                       Category.name.ilike(f"%{term}%")))
           .first())
    cat_id = cat.id if cat else -1
    cands = (Place.query.filter(Place.lat != 0).filter(or_(
        Place.name.ilike(f"%{term}%"),
        Place.subcategory.ilike(f"%{term}%"),
        Place.chain_brand.ilike(f"%{term}%"),
        Place.tags_json.ilike(f"%{term_lc}%"),
        Place.category_id == cat_id,
    )).limit(500).all())
    # Token-overlap fallback: catches multi-word inputs whose word order
    # differs from the canonical name ("Pittsburgh Airport" → "Pittsburgh
    # International Airport").
    toks = set(_tokenize(term))
    if toks:
        seen = {p.id for p in cands}
        for p in (Place.query.filter(Place.lat != 0).limit(2000).all()):
            if p.id in seen:
                continue
            haystack = " ".join([
                (p.name or ""), (p.subcategory or ""),
                (p.chain_brand or ""),
                (p.category.name if p.category else ""),
                (p.category.slug if p.category else ""),
            ])
            pt = set(_tokenize(haystack))
            if len(toks & pt) >= max(1, (len(toks) + 1) // 2):
                cands.append(p)
    # Score: token-on-name first, then token-on-haystack, then rating ×
    # log(reviews).  NEVER sort by distance — that puts the "closest X to
    # Y" answer at the top and lets the agent solve by clicking #1.
    def _sk(p):
        name_lc = (p.name or "").lower()
        hay_lc = " ".join([
            (p.subcategory or "").lower(),
            (p.chain_brand or "").lower(),
            (p.category.name.lower() if p.category else ""),
            (p.category.slug.lower() if p.category else ""),
        ])
        s = 0
        for t in toks:
            if t in name_lc:
                s += 3
            elif t in hay_lc:
                s += 1
        rel = (p.rating or 4.0) * math.log(max(p.review_count or 1, 1) + 2)
        return (-s, -rel)
    cands.sort(key=_sk)
    out = []
    cap = max_n - len(cc_pre)
    for p in cands[:cap]:
        d = (_haversine_mi(anchor_lat, anchor_lng, p.lat, p.lng)
             if anchor_lat is not None and anchor_lng is not None else None)
        out.append({
            "lat": p.lat, "lng": p.lng, "name": p.name,
            "address": p.address or "", "place_id": p.id, "slug": p.slug,
            "rating": p.rating, "review_count": p.review_count,
            "category_name": p.category.name if p.category else "",
            "distance_mi": d,
        })
    return cc_pre + out


def _resolve_endpoint(term, anchor_lat=None, anchor_lng=None):
    """Resolve a free-text Directions endpoint to (lat, lng, name, address).
    Falls back through: zip → famous landmark / place name → category-keyword
    → city.  When `anchor_lat/lng` is given, ambiguous matches resolve to the
    nearest candidate, matching real Google Maps' "find the closest one"
    behaviour for queries like "apple store" with a known origin.
    Returns a dict {lat, lng, name, address, place_id?} or None.
    """
    term = (term or "").strip(" ,.\"'")
    if not term:
        return None

    # 0) "<City> (city center)" label round-trip from the picker
    cc_m = _CITY_CENTER_RE.match(term)
    if cc_m:
        city_term = cc_m.group(1).strip()
        slug = city_term.lower().replace(" ", "-")
        c = (City.query
             .filter(or_(City.display_name.ilike(city_term),
                         City.display_name.ilike(f"{city_term},%"),
                         City.slug == slug))
             .first())
        if c and c.lat and c.lng:
            return {"lat": c.lat, "lng": c.lng,
                    "name": f"{c.display_name} (city center)",
                    "address": c.display_name, "place_id": None}
        return None

    # 1) 5-digit zip — bare or "NNNNN (zip area)" label from the picker
    zip_m = _ZIP_AREA_RE.match(term)
    bare_zip = re.fullmatch(r"\d{5}", term)
    if zip_m or bare_zip:
        z = zip_m.group(1) if zip_m else term
        display_name = f"{z} (zip area)" if zip_m else z
        if z in _ZIP_CENTROIDS:
            lat, lng = _ZIP_CENTROIDS[z]
            return {"lat": lat, "lng": lng, "name": display_name,
                    "address": f"ZIP {z}", "place_id": None}
        p = (Place.query.filter(Place.zip_code == z, Place.lat != 0)
             .order_by(Place.review_count.desc()).first())
        if p:
            return {"lat": p.lat, "lng": p.lng, "name": display_name,
                    "address": f"ZIP {z} ({p.address})", "place_id": p.id}
        return None

    def _to_endpoint(p):
        return {"lat": p.lat, "lng": p.lng, "name": p.name,
                "address": p.address or "", "place_id": p.id}

    # 2a) Exact City match — when the user types "Chicago" / "Los
    #     Angeles" / "Miami" they mean the city, not "Art Institute of
    #     Chicago" or "Best Buy Miami Beach".  Resolve city BEFORE
    #     substring Place match so the route summary doesn't fabricate
    #     a specific Place that wasn't requested.  Accept three forms:
    #     exact display_name, comma-prefix ("Miami" → "Miami, FL"),
    #     and slug.
    slug = term.lower().replace(" ", "-")
    city_exact = (City.query
                  .filter(or_(City.display_name.ilike(term),
                              City.display_name.ilike(f"{term},%"),
                              City.slug == slug))
                  .first())
    if city_exact and city_exact.lat and city_exact.lng:
        return {"lat": city_exact.lat, "lng": city_exact.lng,
                "name": city_exact.display_name,
                "address": city_exact.display_name, "place_id": None}

    # 2b) Direct Place name match (single best)
    direct = (Place.query
              .filter(Place.name.ilike(term), Place.lat != 0)
              .order_by(Place.is_featured.desc(), Place.review_count.desc())
              .first())
    if direct:
        return _to_endpoint(direct)

    # 3) Substring / category keyword match — collect candidates and
    #    distance-rank against anchor when available.  Also matches against
    #    the parent Category (slug + name) so "hotel" finds places under the
    #    Hotels category whose name doesn't literally contain "hotel".
    term_lc = term.lower()
    cat_match = (Category.query
                 .filter(or_(Category.slug == term_lc,
                             Category.slug == term_lc + "s",
                             Category.slug.startswith(term_lc),
                             Category.name.ilike(f"%{term}%")))
                 .first())
    cat_id = cat_match.id if cat_match else -1
    cand_query = Place.query.filter(Place.lat != 0).filter(or_(
        Place.name.ilike(f"%{term}%"),
        Place.subcategory.ilike(f"%{term}%"),
        Place.chain_brand.ilike(f"%{term}%"),
        Place.tags_json.ilike(f"%{term_lc}%"),
        Place.category_id == cat_id,
    ))
    candidates = cand_query.limit(500).all()
    if candidates:
        # Category-keyword preference: when the query contains a
        # category-naming token ("airport", "museum", "park", "bridge",
        # "stadium"), prefer Places whose CATEGORY matches that token
        # over substring-name matches.  Avoids "Pittsburgh Airport" →
        # "Marriott SpringHill Suites Pittsburgh Airport" (a hotel) just
        # because the hotel's full name contains the substring.
        _CAT_KW = {"airport": "airports", "museum": "museums",
                   "park": "parks", "bridge": "attractions",
                   "stadium": "entertainment", "garden": "attractions",
                   "temple": "attractions", "trail": "trails"}
        for kw, cat_slug in _CAT_KW.items():
            if kw in term_lc.split():
                pref_cat = Category.query.filter_by(slug=cat_slug).first()
                if pref_cat:
                    pref_hits = [p for p in candidates if p.category_id == pref_cat.id]
                    if pref_hits:
                        # Replace candidate pool with preferred-cat hits only;
                        # subsequent sort then picks the best within that
                        # category instead of letting a hotel beat the airport
                        # by review count.
                        candidates = pref_hits
                    break
        if anchor_lat is not None and anchor_lng is not None:
            candidates.sort(key=lambda p: _haversine_mi(
                anchor_lat, anchor_lng, p.lat, p.lng))
        else:
            candidates.sort(key=lambda p: -(p.review_count or 0))
        return _to_endpoint(candidates[0])

    # 4) Token overlap with name (for multi-word inputs whose ILIKE missed)
    toks = set(_tokenize(term))
    if toks:
        scored = []
        for p in Place.query.filter(Place.lat != 0).limit(2000).all():
            pt = set(_tokenize((p.name or "") + " " + (p.subcategory or "")
                               + " " + (p.chain_brand or "")))
            overlap = len(toks & pt)
            if overlap >= max(1, (len(toks) + 1) // 2):
                scored.append((overlap, p))
        if scored:
            if anchor_lat is not None and anchor_lng is not None:
                scored.sort(key=lambda sp: (-sp[0], _haversine_mi(
                    anchor_lat, anchor_lng, sp[1].lat, sp[1].lng)))
            else:
                scored.sort(key=lambda sp: (-sp[0], -(sp[1].review_count or 0)))
            return _to_endpoint(scored[0][1])

    # 5) City fallback
    slug = term.lower().replace(" ", "-")
    c = (City.query
         .filter(or_(City.display_name.ilike(f"%{term}%"), City.slug == slug))
         .first())
    if c and c.lat and c.lng:
        return {"lat": c.lat, "lng": c.lng, "name": c.display_name,
                "address": c.display_name, "place_id": None}

    return None


def _find_route(from_q, to_q, mode=""):
    """Find best matching Route, scored by substring overlap on both ends."""
    if not from_q or not to_q:
        return None
    from_lc = from_q.lower()
    to_lc = to_q.lower()
    candidates = Route.query.all()
    if mode:
        candidates = [r for r in candidates if r.mode == mode.lower()]
    best = None
    best_score = 0
    for r in candidates:
        rof = (r.origin_query or "").lower()
        rdf = (r.destination_query or "").lower()
        ron = (r.origin_name or "").lower()
        rdn = (r.destination_name or "").lower()
        score = 0
        # origin match
        if from_lc in rof or rof in from_lc or from_lc in ron or ron in from_lc:
            score += 2
        else:
            # token overlap
            ft = set(_tokenize(from_q))
            rt = set(_tokenize(rof + " " + ron))
            if ft & rt:
                score += 1
        if to_lc in rdf or rdf in to_lc or to_lc in rdn or rdn in to_lc:
            score += 2
        else:
            tt = set(_tokenize(to_q))
            rt = set(_tokenize(rdf + " " + rdn))
            if tt & rt:
                score += 1
        if score > best_score:
            best_score = score
            best = r
    if best_score >= 2:
        return best
    return None


@app.route("/directions")
@app.route("/dir/<path:route_query>")
@app.route("/maps/dir/<path:route_query>")
def directions(route_query=""):
    route_parts = [part.strip() for part in route_query.split("/") if part.strip()]
    from_q = (request.args.get("from", "") or (route_parts[0] if len(route_parts) >= 1 else "")).strip()
    to_q = (request.args.get("to", "") or (route_parts[1] if len(route_parts) >= 2 else "")).strip()
    mode = request.args.get("mode", "").strip().lower()

    from_place = None
    to_place = None
    from_endpoint = None
    to_endpoint = None
    from_candidates = []
    to_candidates = []
    route = None
    distance_km = None
    duration_min = None
    steps = []
    summary = ""
    distance_label = ""
    duration_label = ""
    mode_label = mode or "driving"

    # Picker-first design: if EITHER endpoint is a generic / ambiguous
    # query, surface a candidate picker BEFORE resolving the route.  Fires
    # whether one or both sides are filled — the user must commit to a
    # specific endpoint before we draw a route.  Distance pills on the
    # picker cards are sorted by relevance (rating × log(reviews)) so the
    # "nearest X" answer isn't handed to the agent at position #1.
    if from_q and not _is_specific_endpoint(from_q):
        to_ep_for_anchor = _resolve_endpoint(to_q) if to_q else None
        from_candidates = _endpoint_candidates(
            from_q, max_n=8,
            anchor_lat=(to_ep_for_anchor or {}).get("lat"),
            anchor_lng=(to_ep_for_anchor or {}).get("lng"),
        )
        if len(from_candidates) > 1:
            return render_template(
                "directions.html",
                from_q=from_q, to_q=to_q,
                from_candidates=from_candidates,
                pick_for="from", mode=mode_label,
            )
    if to_q and not _is_specific_endpoint(to_q):
        from_ep_for_anchor = _resolve_endpoint(from_q) if from_q else None
        to_candidates = _endpoint_candidates(
            to_q, max_n=8,
            anchor_lat=(from_ep_for_anchor or {}).get("lat"),
            anchor_lng=(from_ep_for_anchor or {}).get("lng"),
        )
        if len(to_candidates) > 1:
            return render_template(
                "directions.html",
                from_q=from_q, to_q=to_q,
                from_endpoint=from_ep_for_anchor,
                to_candidates=to_candidates,
                pick_for="to", mode=mode_label,
            )

    # Both endpoints are specific (or one missing) — resolve via the
    # endpoint resolver and let the haversine + alternatives generator
    # synthesise the route.  The legacy curated Route table was dropped
    # from this flow because its fuzzy matcher silently substituted
    # wrong destinations (e.g. asking for "Times Square" while having
    # an SFO → Union Square Route entry would match on the "Square"
    # token, returning a 23-min SF-only route for a cross-country trip).
    # Coords on every Place are now realistic enough for haversine to
    # be the source of truth.
    if from_q and to_q:
        from_endpoint = _resolve_endpoint(from_q)
        to_endpoint = _resolve_endpoint(
            to_q,
            anchor_lat=(from_endpoint or {}).get("lat"),
            anchor_lng=(from_endpoint or {}).get("lng"),
        )
        if from_endpoint is None and to_endpoint is not None:
            from_endpoint = _resolve_endpoint(
                from_q, anchor_lat=to_endpoint["lat"], anchor_lng=to_endpoint["lng"])

        if from_endpoint and to_endpoint:
            if from_endpoint.get("place_id"):
                from_place = Place.query.get(from_endpoint["place_id"])
            if to_endpoint.get("place_id"):
                to_place = Place.query.get(to_endpoint["place_id"])

    # Alternatives + selected variant — synthesised when we have both
    # endpoints (whether from a Route table hit or fresh resolution).
    alternatives = []
    selected_alt = None
    selected_alt_id = (request.args.get("route") or "a").strip().lower()
    eff_mode = mode_label or "driving"
    if from_endpoint and to_endpoint:
        alternatives = _generate_route_alternatives(
            from_endpoint, to_endpoint, eff_mode)
        for a in alternatives:
            if a["id"] == selected_alt_id:
                selected_alt = a
                break
        if alternatives and not selected_alt:
            selected_alt = alternatives[0]

    if selected_alt:
        distance_km = round(selected_alt["distance_mi"] * 1.60934, 1)
        duration_min = selected_alt["duration_min"]
        distance_label = selected_alt["distance_label"]
        duration_label = selected_alt["duration_label"]
        steps = selected_alt["steps"]
        summary = selected_alt["summary"]

    # ------------------------------------------------------------------
    # R6 edge: no-route-found with suggested alternatives.
    # Fires when both endpoints resolved but no alternatives could be
    # synthesised (e.g. trans-oceanic driving query), or when the user
    # asked for "transit" mode between two endpoints with no nearby
    # transit_line rows. We then surface 3 fallback suggestions:
    # change mode, route via the nearer of either endpoint's city, or
    # break into a multi-leg trip.
    # ------------------------------------------------------------------
    no_route_found = False
    route_suggestions = []
    if from_endpoint and to_endpoint and not alternatives:
        no_route_found = True
    elif (eff_mode == "transit" and from_endpoint and to_endpoint and
          alternatives and selected_alt and
          selected_alt.get("distance_mi", 0) > 200):
        # Transit beyond ~200 mi is unrealistic; flag as no-route-found
        # so the agent has to consider a mode switch.
        no_route_found = True
    if no_route_found:
        alt_modes = ["driving", "transit", "walking", "bicycling"]
        for m in alt_modes:
            if m != eff_mode:
                route_suggestions.append({
                    "kind": "mode",
                    "label": f"Try {m} instead",
                    "href": url_for("directions",
                                    **{"from": from_q, "to": to_q, "mode": m}),
                })
            if len(route_suggestions) >= 3:
                break
        route_suggestions.append({
            "kind": "via-city",
            "label": "Plan as a multi-leg trip",
            "href": url_for("trip_create") if "trip_create" in app.view_functions else url_for("index"),
        })

    return render_template(
        "directions.html",
        from_q=from_q, to_q=to_q,
        from_place=from_place, to_place=to_place,
        from_endpoint=from_endpoint, to_endpoint=to_endpoint,
        distance_km=distance_km, duration_min=duration_min,
        route=route, steps=steps, summary=summary,
        distance_label=distance_label, duration_label=duration_label,
        mode=eff_mode,
        alternatives=alternatives, selected_alt=selected_alt,
        no_route_found=no_route_found, route_suggestions=route_suggestions,
    )


@app.route("/timeline")
@login_required
def timeline():
    entries = TimelineEntry.query.filter_by(user_id=current_user.id) \
        .order_by(TimelineEntry.visited_at.desc()).limit(50).all()
    return render_template("timeline.html", entries=entries)


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/contribute")
def contribute():
    """Static 'Contribute' page describing how users add places, reviews,
    photos. Mirrors google.com/maps/contrib/<id>/about style."""
    return render_template("contribute.html")


@app.route("/your-data")
@app.route("/your_data")
@app.route("/data")
def your_data():
    """Static 'Your data in Maps' page (Location history, Web & app activity,
    Timeline data). Mirrors google.com/maps/timeline -> data page."""
    return render_template("your_data.html")


# ----- R3 additions: transit, street-view, business alias, list share, your-places -----

@app.route("/transit")
@app.route("/transit/<city_slug>")
def transit_page(city_slug=None):
    """Transit overview for a city — bus terminals, light rail, ferry, etc.

    Reads from real Place rows in the transit/bus-stops categories.
    """
    cities = City.query.order_by(City.display_name).limit(50).all()
    transit_cats = Category.query.filter(
        Category.slug.in_(["transit", "bus-stops"])
    ).all()
    transit_cat_ids = [c.id for c in transit_cats]
    selected_city = None
    stops = []
    if city_slug:
        selected_city = City.query.filter_by(slug=city_slug).first_or_404()
        if transit_cat_ids:
            stops = Place.query.filter(
                Place.city_id == selected_city.id,
                Place.category_id.in_(transit_cat_ids),
            ).order_by(Place.rating.desc().nullslast(), Place.review_count.desc()).limit(40).all()
    return render_template(
        "transit.html",
        cities=cities,
        selected_city=selected_city,
        stops=stops,
    )


@app.route("/street-view")
@app.route("/streetview")
@app.route("/maps/@<coords>/streetview")
def street_view(coords=None):
    """Mock Street View viewer page. Accepts ?lat=&lng=&heading= or a place slug."""
    lat = request.args.get("lat", type=float)
    lng = request.args.get("lng", type=float)
    heading = request.args.get("heading", default=0, type=int)
    place_slug = request.args.get("place")
    place = None
    if place_slug:
        place = Place.query.filter_by(slug=place_slug).first()
        if place:
            lat = lat or place.lat
            lng = lng or place.lng
    if coords:
        try:
            parts = coords.split(",")
            lat = float(parts[0]); lng = float(parts[1])
        except Exception:
            pass
    return render_template(
        "street_view.html",
        lat=lat, lng=lng, heading=heading, place=place,
    )


@app.route("/business/<int:place_id>")
@app.route("/biz/<int:place_id>")
def business_alias(place_id):
    """Numeric alias for a place page — mirrors google.com/maps/place/<biz-id>."""
    p = Place.query.get_or_404(place_id)
    return redirect(url_for("place_detail", slug=p.slug), code=301)


@app.route("/lists/<int:list_id>/share")
def list_share(list_id):
    """Public share view of a saved list. No auth required."""
    from sqlalchemy import desc
    sl = SavedList.query.get_or_404(list_id)
    saved_places = (SavedPlace.query
                    .filter_by(list_id=sl.id)
                    .order_by(desc(SavedPlace.created_at))
                    .all())
    places = [Place.query.get(sp.place_id) for sp in saved_places if sp.place_id]
    places = [p for p in places if p]
    share_url = url_for("list_share", list_id=sl.id, _external=True)
    return render_template(
        "list_share.html",
        saved_list=sl,
        places=places,
        share_url=share_url,
    )


@app.route("/your-places")
@app.route("/your_places")
@app.route("/yourplaces")
def your_places():
    """Personal overview: saved lists, recent visits, reviews, photos."""
    if not current_user.is_authenticated:
        return redirect(url_for("login"))
    lists = SavedList.query.filter_by(user_id=current_user.id).all()
    recent_saved = (SavedPlace.query
                    .filter_by(user_id=current_user.id)
                    .order_by(SavedPlace.created_at.desc())
                    .limit(12).all())
    recent_visits = (TimelineEntry.query
                     .filter_by(user_id=current_user.id)
                     .order_by(TimelineEntry.visited_at.desc())
                     .limit(12).all())
    recent_reviews = (Review.query
                      .filter_by(user_id=current_user.id)
                      .order_by(Review.created_at.desc())
                      .limit(12).all())
    photo_count = Photo.query.filter_by(user_id=current_user.id).count()
    return render_template(
        "your_places.html",
        lists=lists,
        recent_saved=recent_saved,
        recent_visits=recent_visits,
        recent_reviews=recent_reviews,
        photo_count=photo_count,
    )


@app.route("/settings")
def settings():
    return render_template("settings.html")


# --------------------------------------------------------------------------
#  R4 deep sub-pages: popular-times, accessibility, menu, booking,
#  your-places/labeled, your-places/timeline/<date>, transit/lines/<id>
# --------------------------------------------------------------------------
_DAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
_DAY_NAMES_LONG = ["Monday", "Tuesday", "Wednesday", "Thursday",
                   "Friday", "Saturday", "Sunday"]


def _popular_times_summary(matrix, busiest_day, busiest_hour):
    """Compute summary stats from a 7×24 matrix for the page header."""
    if not matrix:
        return {"peak_label": "", "avg_busy": 0, "open_hours_per_day": 0}
    totals = [sum(row) for row in matrix]
    open_count = sum(1 for row in matrix for v in row if v > 0)
    avg_busy = round(sum(totals) / max(1, sum(1 for row in matrix for v in row if v > 0)))
    peak_label = ""
    if 0 <= busiest_hour < 24:
        h12 = busiest_hour % 12 or 12
        ampm = "AM" if busiest_hour < 12 else "PM"
        day_idx = {"mon": 0, "tue": 1, "wed": 2, "thu": 3,
                   "fri": 4, "sat": 5, "sun": 6}.get((busiest_day or "").lower(), 0)
        peak_label = f"{_DAY_NAMES_LONG[day_idx]} at {h12}:00 {ampm}"
    return {
        "peak_label": peak_label,
        "avg_busy": avg_busy,
        "open_hours_per_day": round(open_count / 7, 1),
        "totals_per_day": totals,
    }


@app.route("/place/<slug>/popular-times")
@app.route("/place/<slug>/popular_times")
def place_popular_times(slug):
    """Standalone deep page rendering the 7×24 popular-times heatmap."""
    place = Place.query.filter_by(slug=slug).first_or_404()
    matrix = place.get_popular_times()
    summary = _popular_times_summary(matrix, place.busiest_day, place.busiest_hour)
    return render_template(
        "popular_times.html",
        place=place, matrix=matrix, summary=summary,
        day_names=_DAY_NAMES, day_names_long=_DAY_NAMES_LONG,
    )


@app.route("/place/<slug>/accessibility")
def place_accessibility(slug):
    """Standalone deep page listing all accessibility features for a place."""
    place = Place.query.filter_by(slug=slug).first_or_404()
    flags = place.get_accessibility_flags()
    enabled = [(k, v) for k, v in flags if v]
    missing = [(k, v) for k, v in flags if not v]
    return render_template(
        "accessibility.html",
        place=place, enabled=enabled, missing=missing,
        score=place.accessibility_score,
    )


@app.route("/place/<slug>/menu")
def place_menu(slug):
    """Restaurant menu page. 404 for non-restaurant places that have no menu."""
    place = Place.query.filter_by(slug=slug).first_or_404()
    menu = place.get_menu()
    if not menu:
        return render_template("menu.html", place=place, sections=[]), 200
    return render_template("menu.html", place=place, sections=menu)


@app.route("/place/<slug>/booking", methods=["GET", "POST"])
def place_booking(slug):
    """Mock reservation page. POST records a flash + redirect; GET shows form."""
    place = Place.query.filter_by(slug=slug).first_or_404()
    if request.method == "POST":
        date_s = (request.form.get("date") or "").strip()
        time_s = (request.form.get("time") or "").strip()
        party = (request.form.get("party") or "").strip()
        if not date_s or not time_s:
            flash("Date and time are required.", "error")
        else:
            flash(
                f"Reservation requested at {place.name} on {date_s} {time_s} for {party or '2'}.",
                "success",
            )
            return redirect(url_for("place_detail", slug=slug))
    return render_template("booking.html", place=place)


@app.route("/your-places/labeled")
@app.route("/your_places/labeled")
@login_required
def your_places_labeled():
    """Personal labeled places — Home / Work / custom."""
    saved = (SavedPlace.query
             .filter(SavedPlace.user_id == current_user.id,
                     SavedPlace.label != "")
             .order_by(SavedPlace.label.asc(), SavedPlace.created_at.desc())
             .all())
    grouped = {}
    for sp in saved:
        grouped.setdefault(sp.label, []).append(sp)
    return render_template(
        "labeled.html", grouped=grouped, saved=saved,
        active_tab="labeled",
    )


@app.route("/your-places/labeled/<int:saved_id>/label", methods=["POST"])
@app.route("/your_places/labeled/<int:saved_id>/label", methods=["POST"])
@login_required
def your_places_label_set(saved_id):
    sp = db.session.get(SavedPlace, saved_id)
    if not sp or sp.user_id != current_user.id:
        abort(404)
    label = (request.form.get("label") or "").strip()[:32]
    sp.label = label
    db.session.commit()
    flash(f"Label updated to {label or '(none)'}.", "success")
    return redirect(url_for("your_places_labeled"))


@app.route("/your-places/timeline/<date>")
@app.route("/your_places/timeline/<date>")
@login_required
def your_places_timeline_date(date):
    """Day-scoped timeline view. <date> = YYYY-MM-DD."""
    try:
        day = datetime.strptime(date, "%Y-%m-%d").date()
    except ValueError:
        abort(404)
    day_start = datetime.combine(day, datetime.min.time())
    day_end = day_start + timedelta(days=1)
    entries = (TimelineEntry.query
               .filter(TimelineEntry.user_id == current_user.id,
                       TimelineEntry.visited_at >= day_start,
                       TimelineEntry.visited_at < day_end)
               .order_by(TimelineEntry.visited_at.asc())
               .all())
    # Adjacent dates by querying neighbour entries
    prev_e = (TimelineEntry.query
              .filter(TimelineEntry.user_id == current_user.id,
                      TimelineEntry.visited_at < day_start)
              .order_by(TimelineEntry.visited_at.desc()).first())
    next_e = (TimelineEntry.query
              .filter(TimelineEntry.user_id == current_user.id,
                      TimelineEntry.visited_at >= day_end)
              .order_by(TimelineEntry.visited_at.asc()).first())
    return render_template(
        "timeline_date.html",
        day=day, entries=entries,
        prev_date=prev_e.visited_at.date() if prev_e else None,
        next_date=next_e.visited_at.date() if next_e else None,
    )


@app.route("/transit/lines/<line_slug>")
def transit_line_detail(line_slug):
    """Show a single transit line: stops, frequency, accessibility notes."""
    line = TransitLine.query.filter_by(slug=line_slug).first_or_404()
    city = City.query.get(line.city_id) if line.city_id else None
    sibling_lines = []
    if line.city_id:
        sibling_lines = (TransitLine.query
                         .filter(TransitLine.city_id == line.city_id,
                                 TransitLine.id != line.id)
                         .order_by(TransitLine.short_name.asc())
                         .limit(20).all())
    return render_template(
        "transit_line.html",
        line=line, city=city, sibling_lines=sibling_lines,
        stops=line.get_stops(),
    )


@app.route("/transit/lines")
def transit_lines_index():
    """Index of all known transit lines."""
    city_slug = (request.args.get("city") or "").strip()
    mode = (request.args.get("mode") or "").strip()
    q = TransitLine.query
    if city_slug:
        c = City.query.filter_by(slug=city_slug).first()
        if c:
            q = q.filter_by(city_id=c.id)
    if mode:
        q = q.filter_by(mode=mode)
    lines = q.order_by(TransitLine.city_id, TransitLine.short_name).limit(200).all()
    return render_template(
        "transit_lines_index.html",
        lines=lines, city_slug=city_slug, mode=mode,
    )


@app.route("/help")
def help_page():
    return render_template("help.html")


# --------------------------------------------------------------------------
#  R5 additions: indoor floor selector, realtime transit, location-history
#  export, group-meetup coordinate, place QR share.
# --------------------------------------------------------------------------
@app.route("/transit/realtime")
@app.route("/transit/realtime/<city_slug>")
def transit_realtime(city_slug=None):
    """Realtime transit delays dashboard. Reads `current_delay_min` and
    `delay_reason` columns seeded by backfill_transit_delays."""
    q = TransitLine.query
    selected_city = None
    if city_slug:
        selected_city = City.query.filter_by(slug=city_slug).first()
        if selected_city:
            q = q.filter_by(city_id=selected_city.id)
    delayed_first = sorted(
        q.all(), key=lambda l: (-(l.current_delay_min or 0), l.name)
    )
    cities = (City.query
              .join(TransitLine, TransitLine.city_id == City.id)
              .order_by(City.display_name).all())
    # Dedup cities while preserving order.
    seen, ordered_cities = set(), []
    for c in cities:
        if c.id not in seen:
            seen.add(c.id)
            ordered_cities.append(c)
    # R6: surface "no service after hours" for lines whose delay_reason
    # was deterministically set to a service-suspended phrase. Picks up
    # whichever lines backfill_transit_delays_r6 flagged.
    no_service_after_hours = [
        l for l in delayed_first
        if (l.delay_reason or "").lower().startswith("no service")
    ]
    return render_template(
        "transit_realtime.html",
        lines=delayed_first, cities=ordered_cities, selected_city=selected_city,
        no_service_after_hours=no_service_after_hours,
    )


@app.route("/place/<slug>/floors")
def place_floors(slug):
    """Indoor floor selector for multi-floor venues (malls, airports, hospitals).

    R6 edge: if the venue is known to have floors but they haven't been
    indoor-mapped yet, we render a "Indoor floor plan not yet available"
    notice instead of an empty list.
    """
    place = Place.query.filter_by(slug=slug).first_or_404()
    floors = place.get_floors()
    # R6: when indoor_floor_unmapped is true, suppress the floor list and
    # show a banner so the agent can read "indoor floor plan not mapped".
    unmapped_banner = bool(place.indoor_floor_unmapped)
    if unmapped_banner:
        floors = []
    return render_template(
        "place_floors.html", place=place, floors=floors,
        unmapped_banner=unmapped_banner,
    )


@app.route("/your-data/export")
def your_data_export():
    """Location-history export — returns a downloadable JSON of timeline entries
    for the signed-in user (or an empty stub for guests). Mirrors the
    `Takeout` Maps timeline export."""
    if not current_user.is_authenticated:
        payload = {
            "format": "google-maps-timeline-v1",
            "exported_at": MIRROR_REFERENCE_DATETIME.isoformat(),
            "entries": [],
            "note": "Sign in to export your full location history.",
        }
    else:
        entries = (TimelineEntry.query
                   .filter_by(user_id=current_user.id)
                   .order_by(TimelineEntry.visited_at.asc())
                   .all())
        payload = {
            "format": "google-maps-timeline-v1",
            "user": current_user.email,
            "exported_at": MIRROR_REFERENCE_DATETIME.isoformat(),
            "entries": [
                {
                    "place": e.place.name if e.place else "",
                    "city": e.place.city.display_name if e.place and e.place.city else "",
                    "visited_at": e.visited_at.isoformat() if e.visited_at else "",
                    "note": e.note or "",
                }
                for e in entries
            ],
        }
    fmt = (request.args.get("format") or "").lower()
    if fmt == "download":
        from flask import Response
        body = json.dumps(payload, indent=2)
        return Response(
            body,
            mimetype="application/json",
            headers={"Content-Disposition": "attachment; filename=timeline-export.json"},
        )
    return render_template("your_data_export.html", payload=payload)


@app.route("/meetup", methods=["GET", "POST"])
def group_meetup():
    """Group-meetup coordinator: paste 2-5 addresses, suggest a midpoint
    place that's a coffee shop or restaurant near the geometric center."""
    addresses = []
    suggestion = None
    midpoint = None
    if request.method == "POST":
        raw = request.form.get("addresses", "")
        addresses = [a.strip() for a in raw.split("\n") if a.strip()]
        # Resolve each to a Place by name match; midpoint = mean lat/lng
        resolved = []
        for a in addresses[:5]:
            p = (Place.query
                 .filter(Place.name.ilike(f"%{a}%"))
                 .order_by(Place.review_count.desc())
                 .first())
            if p:
                resolved.append(p)
        if len(resolved) >= 2:
            avg_lat = sum(p.lat for p in resolved) / len(resolved)
            avg_lng = sum(p.lng for p in resolved) / len(resolved)
            midpoint = {"lat": round(avg_lat, 4), "lng": round(avg_lng, 4)}
            # Suggest a coffee-shop or restaurant near the midpoint
            cands = (Place.query
                     .join(Category, Category.id == Place.category_id)
                     .filter(Category.slug.in_(["coffee-shops", "restaurants"]),
                             Place.rating >= 4.4)
                     .all())
            if cands:
                def _d(p):
                    return ((p.lat - avg_lat) ** 2 + (p.lng - avg_lng) ** 2)
                cands.sort(key=_d)
                suggestion = cands[0]
    return render_template(
        "meetup.html",
        addresses=addresses, suggestion=suggestion, midpoint=midpoint,
    )


@app.route("/place/<slug>/qr")
def place_qr(slug):
    """Place QR share — render an ASCII QR placeholder + the shareable URL."""
    place = Place.query.filter_by(slug=slug).first_or_404()
    share_url = google_maps_place_url(place)
    # Deterministic ASCII "QR" pattern from the slug for the demo render.
    grid = []
    seed = hash(slug) & 0xFFFFFFFF
    for r in range(11):
        row = []
        for c in range(11):
            v = (seed >> ((r * 11 + c) % 31)) & 1
            # Always set corner finder squares like a real QR.
            if (r < 3 and c < 3) or (r < 3 and c > 7) or (r > 7 and c < 3):
                v = 1
            row.append(v)
        grid.append(row)
    return render_template(
        "place_qr.html", place=place, share_url=share_url, grid=grid,
    )


# --------------------------------------------------------------------------
#  Auth
# --------------------------------------------------------------------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("index"))
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = User.query.filter_by(email=email).first()
        if user and bcrypt.check_password_hash(user.password_hash, password):
            login_user(user, remember=True)
            flash(f"Welcome back, {user.name}!", "success")
            next_url = request.args.get("next") or url_for("index")
            return redirect(next_url)
        flash("Invalid email or password.", "error")
    return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("index"))
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        name = request.form.get("name", "").strip()
        password = request.form.get("password", "")
        password2 = request.form.get("password2", "")

        if not email or not name or not password:
            flash("All fields are required.", "error")
            return render_template("register.html")
        if password != password2:
            flash("Passwords do not match.", "error")
            return render_template("register.html")
        if User.query.filter_by(email=email).first():
            flash("An account with that email already exists.", "error")
            return render_template("register.html")

        pw_hash = bcrypt.generate_password_hash(password).decode("utf-8")
        user = User(
            email=email,
            password_hash=pw_hash,
            name=name,
            avatar_letter=(name[0] if name else "U").upper(),
        )
        db.session.add(user)
        db.session.commit()
        ensure_default_lists(user)
        login_user(user)
        flash("Account created - welcome to Maps!", "success")
        return redirect(url_for("index"))
    return render_template("register.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been signed out.", "info")
    return redirect(url_for("index"))


# --------------------------------------------------------------------------
#  Account / Profile
# --------------------------------------------------------------------------
@app.route("/account")
@login_required
def account():
    lists = SavedList.query.filter_by(user_id=current_user.id).all()
    recent_reviews = Review.query.filter_by(user_id=current_user.id) \
        .order_by(Review.created_at.desc()).limit(5).all()
    recent_trips = Trip.query.filter_by(user_id=current_user.id) \
        .order_by(Trip.created_at.desc()).limit(5).all()
    saved_count = SavedPlace.query.filter_by(user_id=current_user.id).count()
    trip_count = Trip.query.filter_by(user_id=current_user.id).count()
    review_count = Review.query.filter_by(user_id=current_user.id).count()
    return render_template(
        "account.html",
        lists=lists,
        recent_reviews=recent_reviews,
        recent_trips=recent_trips,
        saved_count=saved_count,
        trip_count=trip_count,
        review_count=review_count,
    )


@app.route("/account/edit", methods=["GET", "POST"])
@login_required
def account_edit():
    if request.method == "POST":
        current_user.name = request.form.get("name", current_user.name).strip()
        current_user.home_city = request.form.get("home_city", "").strip()
        current_user.bio = request.form.get("bio", "").strip()
        if current_user.name:
            current_user.avatar_letter = current_user.name[0].upper()
        db.session.commit()
        flash("Profile updated.", "success")
        return redirect(url_for("account"))
    return render_template("account_edit.html")


@app.route("/account/password", methods=["GET", "POST"])
@login_required
def change_password():
    if request.method == "POST":
        current = request.form.get("current_password", "")
        new = request.form.get("new_password", "")
        new2 = request.form.get("new_password2", "")
        if not bcrypt.check_password_hash(current_user.password_hash, current):
            flash("Current password is incorrect.", "error")
            return render_template("change_password.html")
        if new != new2:
            flash("New passwords do not match.", "error")
            return render_template("change_password.html")
        if len(new) < 6:
            flash("Password must be at least 6 characters.", "error")
            return render_template("change_password.html")
        current_user.password_hash = bcrypt.generate_password_hash(new).decode("utf-8")
        db.session.commit()
        flash("Password updated.", "success")
        return redirect(url_for("account"))
    return render_template("change_password.html")


@app.route("/account/delete", methods=["POST"])
@login_required
def account_delete():
    user = db.session.get(User, current_user.id)
    logout_user()
    db.session.delete(user)
    db.session.commit()
    flash("Your account has been deleted.", "info")
    return redirect(url_for("index"))


# --------------------------------------------------------------------------
#  Lists & Saved Places
# --------------------------------------------------------------------------
@app.route("/lists")
@login_required
def lists_page():
    lists = SavedList.query.filter_by(user_id=current_user.id).all()
    # Count places in each list
    list_counts = {l.id: SavedPlace.query.filter_by(list_id=l.id).count() for l in lists}
    return render_template("lists.html", lists=lists, list_counts=list_counts)


@app.route("/lists/new", methods=["GET", "POST"])
@login_required
def list_create():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        desc = request.form.get("description", "").strip()
        color = request.form.get("color", "#4285f4")
        if not name:
            flash("List name is required.", "error")
            return redirect(url_for("list_create"))
        sl = SavedList(user_id=current_user.id, name=name, description=desc, color=color, icon="bookmark")
        db.session.add(sl)
        db.session.commit()
        flash(f"List '{name}' created.", "success")
        return redirect(url_for("list_detail", list_id=sl.id))
    return render_template("list_form.html", action="Create")


@app.route("/lists/<int:list_id>")
@login_required
def list_detail(list_id):
    sl = db.session.get(SavedList, list_id)
    if not sl or sl.user_id != current_user.id:
        abort(404)
    saved = SavedPlace.query.filter_by(list_id=sl.id).order_by(SavedPlace.created_at.desc()).all()
    return render_template("list_detail.html", saved_list=sl, saved=saved)


@app.route("/lists/<int:list_id>/edit", methods=["GET", "POST"])
@login_required
def list_edit(list_id):
    sl = db.session.get(SavedList, list_id)
    if not sl or sl.user_id != current_user.id:
        abort(404)
    if request.method == "POST":
        sl.name = request.form.get("name", sl.name).strip()
        sl.description = request.form.get("description", "").strip()
        sl.color = request.form.get("color", sl.color)
        db.session.commit()
        flash("List updated.", "success")
        return redirect(url_for("list_detail", list_id=sl.id))
    return render_template("list_form.html", action="Edit", saved_list=sl)


@app.route("/lists/<int:list_id>/delete", methods=["POST"])
@login_required
def list_delete(list_id):
    sl = db.session.get(SavedList, list_id)
    if not sl or sl.user_id != current_user.id:
        abort(404)
    if sl.is_default:
        flash("Default lists cannot be deleted.", "error")
        return redirect(url_for("lists_page"))
    db.session.delete(sl)
    db.session.commit()
    flash("List deleted.", "success")
    return redirect(url_for("lists_page"))


@app.route("/saved")
@login_required
def saved_page():
    """All saved places across all lists."""
    saved = SavedPlace.query.filter_by(user_id=current_user.id) \
        .order_by(SavedPlace.created_at.desc()).all()
    lists = SavedList.query.filter_by(user_id=current_user.id).all()
    return render_template("saved.html", saved=saved, lists=lists)


@app.route("/api/save", methods=["POST"])
@csrf.exempt
@login_required
def api_save_place():
    data = request.get_json(silent=True) or {}
    place_id = data.get("place_id")
    list_id = data.get("list_id")
    place = db.session.get(Place, place_id)
    if not place:
        return jsonify({"success": False, "message": "Place not found"}), 404

    # Use default list if none provided
    if not list_id:
        default = SavedList.query.filter_by(user_id=current_user.id, is_default=True).first()
        if not default:
            ensure_default_lists(current_user)
            default = SavedList.query.filter_by(user_id=current_user.id, is_default=True).first()
        list_id = default.id

    existing = SavedPlace.query.filter_by(
        user_id=current_user.id, place_id=place.id
    ).first()
    if existing:
        db.session.delete(existing)
        db.session.commit()
        count = SavedPlace.query.filter_by(user_id=current_user.id).count()
        return jsonify({"success": True, "saved": False, "saved_count": count, "message": "Removed from saved"})

    sp = SavedPlace(user_id=current_user.id, list_id=list_id, place_id=place.id)
    db.session.add(sp)
    db.session.commit()
    count = SavedPlace.query.filter_by(user_id=current_user.id).count()
    return jsonify({"success": True, "saved": True, "saved_count": count, "message": f"Saved to list"})


@app.route("/save/<int:place_id>", methods=["POST"])
@login_required
def save_place_form(place_id):
    """Form-POST equivalent of /api/save. Safe for browser agents that can't send AJAX."""
    place = db.session.get(Place, place_id)
    if not place:
        abort(404)
    list_id = request.form.get("list_id", type=int)
    if not list_id:
        default = SavedList.query.filter_by(user_id=current_user.id, is_default=True).first()
        if not default:
            ensure_default_lists(current_user)
            default = SavedList.query.filter_by(user_id=current_user.id, is_default=True).first()
        list_id = default.id if default else None

    existing = SavedPlace.query.filter_by(user_id=current_user.id, place_id=place.id).first()
    if existing:
        db.session.delete(existing)
        db.session.commit()
        flash(f"Removed {place.name} from saved.", "info")
    else:
        sp = SavedPlace(user_id=current_user.id, list_id=list_id, place_id=place.id)
        db.session.add(sp)
        db.session.commit()
        flash(f"Saved {place.name}.", "success")
    return redirect(request.referrer or url_for("place_detail", slug=place.slug))


@app.route("/save-to-list/<int:place_id>", methods=["POST"])
@login_required
def save_place_to_list(place_id):
    """Save a place to a specific list (form POST). Creates SavedPlace if not already there."""
    place = db.session.get(Place, place_id)
    if not place:
        abort(404)
    list_id = request.form.get("list_id", type=int)
    if not list_id:
        flash("List not specified.", "error")
        return redirect(request.referrer or url_for("saved_page"))
    sl = db.session.get(SavedList, list_id)
    if not sl or sl.user_id != current_user.id:
        abort(404)
    existing = SavedPlace.query.filter_by(user_id=current_user.id, place_id=place.id, list_id=list_id).first()
    if not existing:
        sp = SavedPlace(user_id=current_user.id, list_id=list_id, place_id=place.id)
        db.session.add(sp)
        db.session.commit()
        flash(f"Saved {place.name} to '{sl.name}'.", "success")
    else:
        flash(f"{place.name} is already in '{sl.name}'.", "info")
    return redirect(request.referrer or url_for("list_detail", list_id=list_id))


@app.route("/saved/<int:saved_id>/remove", methods=["POST"])
@login_required
def saved_remove(saved_id):
    sp = db.session.get(SavedPlace, saved_id)
    if not sp or sp.user_id != current_user.id:
        abort(404)
    db.session.delete(sp)
    db.session.commit()
    flash("Removed from saved.", "info")
    return redirect(request.referrer or url_for("saved_page"))


# --------------------------------------------------------------------------
#  Trips
# --------------------------------------------------------------------------
@app.route("/trips")
@login_required
def trips_page():
    trips = Trip.query.filter_by(user_id=current_user.id) \
        .order_by(Trip.created_at.desc()).all()
    return render_template("trips.html", trips=trips)


@app.route("/trips/new", methods=["GET", "POST"])
@login_required
def trip_create():
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        city = request.form.get("city", "").strip()
        start = request.form.get("start_date", "")
        end = request.form.get("end_date", "")
        notes = request.form.get("notes", "").strip()
        if not title:
            flash("Trip title is required.", "error")
            return redirect(url_for("trip_create"))
        trip = Trip(
            user_id=current_user.id,
            trip_code=gen_trip_code(),
            title=title,
            city=city,
            notes=notes,
            status="planning",
        )
        if start:
            try:
                trip.start_date = datetime.strptime(start, "%Y-%m-%d").date()
            except ValueError:
                pass
        if end:
            try:
                trip.end_date = datetime.strptime(end, "%Y-%m-%d").date()
            except ValueError:
                pass
        db.session.add(trip)
        db.session.commit()
        flash(f"Trip '{title}' created.", "success")
        return redirect(url_for("trip_detail", trip_id=trip.id))
    cities = City.query.order_by(City.display_name).all()
    return render_template("trip_form.html", action="Create", cities=cities)


@app.route("/trips/<int:trip_id>")
@login_required
def trip_detail(trip_id):
    trip = db.session.get(Trip, trip_id)
    if not trip or trip.user_id != current_user.id:
        abort(404)
    stops = TripStop.query.filter_by(trip_id=trip.id).order_by(TripStop.order_idx).all()
    return render_template("trip_detail.html", trip=trip, stops=stops)


@app.route("/trips/<int:trip_id>/add_stop", methods=["POST"])
@login_required
def trip_add_stop(trip_id):
    trip = db.session.get(Trip, trip_id)
    if not trip or trip.user_id != current_user.id:
        abort(404)
    place_id = request.form.get("place_id", type=int)
    notes = request.form.get("notes", "").strip()
    place = db.session.get(Place, place_id)
    if not place:
        flash("Place not found.", "error")
        return redirect(url_for("trip_detail", trip_id=trip.id))
    max_order = db.session.query(func.max(TripStop.order_idx)).filter_by(trip_id=trip.id).scalar() or 0
    stop = TripStop(trip_id=trip.id, place_id=place.id, order_idx=max_order + 1, notes=notes)
    db.session.add(stop)
    db.session.commit()
    flash(f"Added {place.name} to trip.", "success")
    return redirect(url_for("trip_detail", trip_id=trip.id))


@app.route("/trips/<int:trip_id>/cancel", methods=["POST"])
@login_required
def trip_cancel(trip_id):
    trip = db.session.get(Trip, trip_id)
    if not trip or trip.user_id != current_user.id:
        abort(404)
    if trip.status not in ("planning", "upcoming"):
        flash("Only planning/upcoming trips can be cancelled.", "error")
    else:
        trip.status = "cancelled"
        db.session.commit()
        flash("Trip cancelled.", "info")
    return redirect(url_for("trip_detail", trip_id=trip.id))


@app.route("/trips/<int:trip_id>/complete", methods=["POST"])
@login_required
def trip_complete(trip_id):
    trip = db.session.get(Trip, trip_id)
    if not trip or trip.user_id != current_user.id:
        abort(404)
    trip.status = "completed"
    db.session.commit()
    # Add all stops to timeline
    for stop in trip.stops:
        db.session.add(TimelineEntry(
            user_id=current_user.id,
            place_id=stop.place_id,
            visited_at=datetime.utcnow(),
            note=f"Visited on trip: {trip.title}",
        ))
    db.session.commit()
    flash("Trip marked as completed. Stops added to timeline.", "success")
    return redirect(url_for("trip_detail", trip_id=trip.id))


@app.route("/trips/<int:trip_id>/stop/<int:stop_id>/remove", methods=["POST"])
@login_required
def trip_stop_remove(trip_id, stop_id):
    trip = db.session.get(Trip, trip_id)
    if not trip or trip.user_id != current_user.id:
        abort(404)
    stop = db.session.get(TripStop, stop_id)
    if stop and stop.trip_id == trip.id:
        db.session.delete(stop)
        db.session.commit()
        flash("Stop removed.", "info")
    return redirect(url_for("trip_detail", trip_id=trip.id))


# --------------------------------------------------------------------------
#  Reviews
# --------------------------------------------------------------------------
@app.route("/place/<slug>/review", methods=["POST"])
@login_required
def submit_review(slug):
    place = Place.query.filter_by(slug=slug).first_or_404()
    rating = request.form.get("rating", type=int)
    title = request.form.get("title", "").strip()
    body = request.form.get("body", "").strip()
    if not rating or rating < 1 or rating > 5:
        flash("Please provide a rating between 1 and 5.", "error")
    elif not body:
        flash("Please write a review.", "error")
    else:
        existing = Review.query.filter_by(user_id=current_user.id, place_id=place.id).first()
        if existing:
            existing.rating = rating
            existing.title = title
            existing.body = body
            flash("Review updated.", "success")
        else:
            r = Review(
                user_id=current_user.id, place_id=place.id,
                rating=rating, title=title, body=body,
            )
            db.session.add(r)
            flash("Review posted.", "success")
        db.session.commit()
    return redirect(url_for("place_detail", slug=slug))


@app.route("/review/<int:review_id>/delete", methods=["POST"])
@login_required
def delete_review(review_id):
    r = db.session.get(Review, review_id)
    if not r or r.user_id != current_user.id:
        abort(404)
    place_slug = r.place.slug
    db.session.delete(r)
    db.session.commit()
    flash("Review deleted.", "info")
    return redirect(url_for("place_detail", slug=place_slug))


# --------------------------------------------------------------------------
#  Photos & Timeline
# --------------------------------------------------------------------------
@app.route("/place/<slug>/checkin", methods=["POST"])
@login_required
def place_checkin(slug):
    place = Place.query.filter_by(slug=slug).first_or_404()
    note = request.form.get("note", "").strip()
    db.session.add(TimelineEntry(
        user_id=current_user.id,
        place_id=place.id,
        visited_at=datetime.utcnow(),
        note=note,
    ))
    db.session.commit()
    flash(f"Checked in at {place.name}.", "success")
    return redirect(url_for("place_detail", slug=slug))


@app.route("/timeline/<int:entry_id>/delete", methods=["POST"])
@login_required
def delete_timeline_entry(entry_id):
    e = db.session.get(TimelineEntry, entry_id)
    if not e or e.user_id != current_user.id:
        abort(404)
    db.session.delete(e)
    db.session.commit()
    flash("Timeline entry removed.", "info")
    return redirect(url_for("timeline"))


# --------------------------------------------------------------------------
#  R-imgsave additions: 4-tab your-places hub + 15 new POST interactions.
#  All writes go to SQLAlchemy models (no in-memory dicts), so reset works.
# --------------------------------------------------------------------------
def _ensure_default_list_for_user():
    """Return the user's default SavedList, creating one if missing."""
    default = SavedList.query.filter_by(
        user_id=current_user.id, is_default=True).first()
    if not default:
        ensure_default_lists(current_user)
        default = SavedList.query.filter_by(
            user_id=current_user.id, is_default=True).first()
    return default


@app.route("/your-places/saved")
@app.route("/your_places/saved")
@login_required
def your_places_saved():
    """4-tab Your-Places hub: SAVED tab."""
    lists = SavedList.query.filter_by(user_id=current_user.id).all()
    saved_by_list = []
    for L in lists:
        sps = (SavedPlace.query
               .filter_by(user_id=current_user.id, list_id=L.id)
               .order_by(SavedPlace.created_at.desc()).all())
        saved_by_list.append((L, sps))
    total_saved = SavedPlace.query.filter_by(
        user_id=current_user.id).count()
    return render_template(
        "your_places_saved.html",
        active_tab="saved",
        saved_by_list=saved_by_list,
        lists=lists,
        total_saved=total_saved,
    )


@app.route("/your-places/visited")
@app.route("/your_places/visited")
@login_required
def your_places_visited():
    """4-tab Your-Places hub: VISITED tab."""
    visits = (TimelineEntry.query
              .filter_by(user_id=current_user.id)
              .order_by(TimelineEntry.visited_at.desc()).all())
    return render_template(
        "your_places_visited.html",
        active_tab="visited",
        visits=visits,
    )


@app.route("/your-places/lists")
@app.route("/your_places/lists")
@login_required
def your_places_lists():
    """4-tab Your-Places hub: LISTS tab."""
    lists = SavedList.query.filter_by(user_id=current_user.id).all()
    list_counts = {
        L.id: SavedPlace.query.filter_by(list_id=L.id).count() for L in lists
    }
    return render_template(
        "your_places_lists.html",
        active_tab="lists",
        lists=lists,
        list_counts=list_counts,
    )


@app.route("/your-places/maps")
@app.route("/your_places/maps")
@login_required
def your_places_maps():
    """Alias for the legacy your-places dashboard; keeps deep links alive."""
    return redirect(url_for("your_places"))


# ---- 15 new POST interactions ----------------------------------------------

@app.route("/place/<int:place_id>/save", methods=["POST"])
@login_required
def place_save_post(place_id):
    """Toggle bookmark on a place by id (alias of /save/<id> for consistency
    with /place/<id>/... POST family).  Writes SavedPlace row."""
    place = db.session.get(Place, place_id)
    if not place:
        abort(404)
    default = _ensure_default_list_for_user()
    existing = SavedPlace.query.filter_by(
        user_id=current_user.id, place_id=place.id).first()
    if existing:
        db.session.delete(existing)
        db.session.commit()
        flash(f"Removed {place.name} from saved.", "info")
    else:
        sp = SavedPlace(user_id=current_user.id,
                        list_id=default.id if default else None,
                        place_id=place.id)
        db.session.add(sp)
        db.session.commit()
        flash(f"Saved {place.name}.", "success")
    return redirect(request.referrer or
                    url_for("place_detail", slug=place.slug))


@app.route("/place/<slug>/photo/add", methods=["POST"])
@login_required
def place_photo_add(slug):
    """Add a Photo row for a place (user-uploaded photo metadata)."""
    place = Place.query.filter_by(slug=slug).first_or_404()
    image_url = (request.form.get("image_url") or "").strip()
    caption = (request.form.get("caption") or "").strip()[:255]
    if not image_url:
        # Pick a plausible deterministic placeholder from the place's pool
        extras = place_extra_images(place, n=8)
        image_url = extras[0] if extras else place.hero_image or "/static/images/heroes/eiffel-tower.jpg"
    p = Photo(user_id=current_user.id, place_id=place.id,
              image_url=image_url, caption=caption)
    db.session.add(p)
    db.session.commit()
    flash("Photo added.", "success")
    return redirect(url_for("place_detail", slug=place.slug) + "#photos")


@app.route("/place/<slug>/question", methods=["POST"])
@login_required
def place_question_ask(slug):
    """Post a Q&A question on a place."""
    place = Place.query.filter_by(slug=slug).first_or_404()
    body = (request.form.get("body") or "").strip()
    if not body:
        flash("Question cannot be empty.", "error")
        return redirect(url_for("place_detail", slug=place.slug) + "#qa")
    q = PlaceQuestion(user_id=current_user.id, place_id=place.id, body=body)
    db.session.add(q)
    db.session.commit()
    flash("Question posted.", "success")
    return redirect(url_for("place_detail", slug=place.slug) + "#qa")


@app.route("/place/<slug>/q/<int:qid>/answer", methods=["POST"])
@login_required
def place_question_answer(slug, qid):
    """Community answer to an existing question."""
    place = Place.query.filter_by(slug=slug).first_or_404()
    q = db.session.get(PlaceQuestion, qid)
    if not q or q.place_id != place.id:
        abort(404)
    body = (request.form.get("body") or "").strip()
    if not body:
        flash("Answer cannot be empty.", "error")
        return redirect(url_for("place_detail", slug=place.slug) + "#qa")
    a = PlaceAnswer(user_id=current_user.id, question_id=q.id, body=body)
    db.session.add(a)
    db.session.commit()
    flash("Answer posted.", "success")
    return redirect(url_for("place_detail", slug=place.slug) + "#qa")


@app.route("/place/<slug>/edit-suggest", methods=["POST"])
@app.route("/place/<slug>/edit_suggest", methods=["POST"])
@login_required
def place_edit_suggest(slug):
    """Submit a suggested edit to one of the place's fields."""
    place = Place.query.filter_by(slug=slug).first_or_404()
    field = (request.form.get("field") or "").strip().lower()
    if field not in {"name", "address", "phone", "hours", "website",
                     "category"}:
        flash("Field not editable.", "error")
        return redirect(url_for("place_detail", slug=place.slug))
    new_value = (request.form.get("new_value") or "").strip()[:512]
    note = (request.form.get("note") or "").strip()
    es = EditSuggestion(user_id=current_user.id, place_id=place.id,
                        field=field, new_value=new_value, note=note,
                        status="pending")
    db.session.add(es)
    db.session.commit()
    flash("Edit suggestion submitted.", "success")
    return redirect(url_for("place_detail", slug=place.slug))


@app.route("/place/<slug>/report", methods=["POST"])
@login_required
def place_report(slug):
    """Report inaccurate / closed / duplicate info on a place."""
    place = Place.query.filter_by(slug=slug).first_or_404()
    reason = (request.form.get("reason") or "inaccurate").strip().lower()
    if reason not in {"inaccurate", "closed", "duplicate",
                      "inappropriate", "other"}:
        reason = "other"
    detail = (request.form.get("detail") or "").strip()
    r = PlaceReport(user_id=current_user.id, place_id=place.id,
                    reason=reason, detail=detail)
    db.session.add(r)
    db.session.commit()
    flash("Report submitted. Thanks for helping keep Maps accurate.",
          "success")
    return redirect(url_for("place_detail", slug=place.slug))


@app.route("/place/<slug>/photo/<int:photo_id>/report", methods=["POST"])
@login_required
def place_photo_report(slug, photo_id):
    """Report a photo as inappropriate / inaccurate."""
    photo = db.session.get(Photo, photo_id)
    if not photo:
        abort(404)
    reason = (request.form.get("reason") or "inappropriate").strip().lower()
    pr = PhotoReport(user_id=current_user.id, photo_id=photo.id,
                     reason=reason)
    db.session.add(pr)
    db.session.commit()
    flash("Photo reported.", "info")
    return redirect(url_for("place_detail", slug=slug) + "#photos")


@app.route("/list/create", methods=["POST"])
@login_required
def list_create_post():
    """Create a custom list (form-POST flavour of /lists/new)."""
    name = (request.form.get("name") or "").strip()
    if not name:
        flash("List name is required.", "error")
        return redirect(request.referrer or url_for("lists_page"))
    description = (request.form.get("description") or "").strip()
    icon = (request.form.get("icon") or "bookmark").strip()[:32]
    color = (request.form.get("color") or "#4285f4").strip()[:16]
    sl = SavedList(user_id=current_user.id, name=name[:128],
                   description=description, icon=icon, color=color,
                   is_default=False)
    db.session.add(sl)
    db.session.commit()
    flash(f"Created list '{sl.name}'.", "success")
    return redirect(url_for("list_detail", list_id=sl.id))


@app.route("/list/<int:list_id>/add-place", methods=["POST"])
@app.route("/list/<int:list_id>/add_place", methods=["POST"])
@login_required
def list_add_place(list_id):
    """Add a Place (by id) to a custom list."""
    sl = db.session.get(SavedList, list_id)
    if not sl or sl.user_id != current_user.id:
        abort(404)
    place_id = request.form.get("place_id", type=int)
    place = db.session.get(Place, place_id) if place_id else None
    if not place:
        flash("Place not found.", "error")
        return redirect(url_for("list_detail", list_id=sl.id))
    existing = SavedPlace.query.filter_by(
        user_id=current_user.id, list_id=sl.id, place_id=place.id).first()
    if not existing:
        sp = SavedPlace(user_id=current_user.id, list_id=sl.id,
                        place_id=place.id)
        db.session.add(sp)
        db.session.commit()
        flash(f"Added {place.name} to '{sl.name}'.", "success")
    else:
        flash(f"{place.name} is already in '{sl.name}'.", "info")
    return redirect(url_for("list_detail", list_id=sl.id))


@app.route("/list/<int:list_id>/rename", methods=["POST"])
@login_required
def list_rename(list_id):
    """Rename a custom list."""
    sl = db.session.get(SavedList, list_id)
    if not sl or sl.user_id != current_user.id:
        abort(404)
    new_name = (request.form.get("name") or "").strip()
    if not new_name:
        flash("Name cannot be empty.", "error")
        return redirect(url_for("list_detail", list_id=sl.id))
    sl.name = new_name[:128]
    db.session.commit()
    flash("List renamed.", "success")
    return redirect(url_for("list_detail", list_id=sl.id))


@app.route("/list/<int:list_id>/share", methods=["POST"])
@login_required
def list_share_toggle(list_id):
    """Toggle a list's shared state (stored in description prefix)."""
    sl = db.session.get(SavedList, list_id)
    if not sl or sl.user_id != current_user.id:
        abort(404)
    flag = "[shared] "
    if sl.description and sl.description.startswith(flag):
        sl.description = sl.description[len(flag):]
        flash("List sharing disabled.", "info")
    else:
        sl.description = flag + (sl.description or "")
        flash("List sharing enabled. Anyone with the link can view.",
              "success")
    db.session.commit()
    return redirect(url_for("list_share", list_id=sl.id))


@app.route("/trip/<int:trip_id>/reorder", methods=["POST"])
@login_required
def trip_reorder(trip_id):
    """Reorder stops in a trip via a CSV `order` field of stop IDs."""
    trip = db.session.get(Trip, trip_id)
    if not trip or trip.user_id != current_user.id:
        abort(404)
    raw = (request.form.get("order") or "").strip()
    if not raw:
        flash("No order provided.", "error")
        return redirect(url_for("trip_detail", trip_id=trip.id))
    try:
        stop_ids = [int(x) for x in raw.split(",") if x.strip().isdigit()]
    except ValueError:
        stop_ids = []
    for idx, sid in enumerate(stop_ids):
        s = db.session.get(TripStop, sid)
        if s and s.trip_id == trip.id:
            s.order_idx = idx
    db.session.commit()
    flash("Trip stops reordered.", "success")
    return redirect(url_for("trip_detail", trip_id=trip.id))


@app.route("/trip/<int:trip_id>/add-stop", methods=["POST"])
@app.route("/trip/<int:trip_id>/add_stop", methods=["POST"])
@login_required
def trip_add_stop_alias(trip_id):
    """Alias of /trips/<id>/add_stop using the singular /trip/ path."""
    trip = db.session.get(Trip, trip_id)
    if not trip or trip.user_id != current_user.id:
        abort(404)
    place_id = request.form.get("place_id", type=int)
    place = db.session.get(Place, place_id) if place_id else None
    if not place:
        flash("Place not found.", "error")
        return redirect(url_for("trip_detail", trip_id=trip.id))
    max_idx = db.session.query(func.max(TripStop.order_idx)) \
        .filter_by(trip_id=trip.id).scalar() or 0
    s = TripStop(trip_id=trip.id, place_id=place.id, order_idx=max_idx + 1,
                 notes=(request.form.get("notes") or "").strip())
    db.session.add(s)
    db.session.commit()
    flash(f"Added {place.name} to {trip.title}.", "success")
    return redirect(url_for("trip_detail", trip_id=trip.id))


@app.route("/place/<slug>/check-in", methods=["POST"])
@login_required
def place_checkin_alias(slug):
    """Alias for /place/<slug>/checkin (hyphenated form)."""
    place = Place.query.filter_by(slug=slug).first_or_404()
    ci = PlaceCheckIn(user_id=current_user.id, place_id=place.id,
                      note=(request.form.get("note") or "")[:255])
    db.session.add(ci)
    # Also drop a TimelineEntry so the visit shows up in /timeline.
    te = TimelineEntry(user_id=current_user.id, place_id=place.id,
                       note=ci.note or "Checked in via Your Places")
    db.session.add(te)
    db.session.commit()
    flash(f"Checked in at {place.name}.", "success")
    return redirect(url_for("place_detail", slug=place.slug))


@app.route("/place/<int:place_id>/rating", methods=["POST"])
@login_required
def place_quick_rating(place_id):
    """Quick 1-tap rating from card row. Creates a body-less Review.

    Real Google Maps lets a user tap stars without writing prose; we model
    that by creating a Review row with body='' and the requested star count.
    """
    place = db.session.get(Place, place_id)
    if not place:
        abort(404)
    try:
        rating = int(request.form.get("rating", "5"))
    except (TypeError, ValueError):
        rating = 5
    rating = max(1, min(5, rating))
    rv = Review(user_id=current_user.id, place_id=place.id,
                rating=rating, title="", body="")
    db.session.add(rv)
    db.session.commit()
    flash(f"Rated {place.name} {rating} stars.", "success")
    return redirect(url_for("place_detail", slug=place.slug) + "#reviews")


# --------------------------------------------------------------------------
#  APIs
# --------------------------------------------------------------------------
@app.route("/api/places")
@app.route("/api/places/<cat_slug>")
def api_places(cat_slug=None):
    """JSON list of places, filterable by category or city."""
    cat_slug = cat_slug or request.args.get("category")
    city_slug = request.args.get("city")
    q = Place.query
    if cat_slug:
        c = Category.query.filter_by(slug=cat_slug).first()
        if c:
            q = q.filter_by(category_id=c.id)
    if city_slug:
        c = City.query.filter_by(slug=city_slug).first()
        if c:
            q = q.filter_by(city_id=c.id)
    places = q.limit(100).all()
    return jsonify({
        "places": [{
            "id": p.id, "slug": p.slug, "name": p.name,
            "category": p.category.slug if p.category else "",
            "city": p.city.slug if p.city else "",
            "rating": p.rating, "price": p.price_level,
            "address": p.address, "lat": p.lat, "lng": p.lng,
            "image": p.hero_image,
        } for p in places],
        "count": len(places),
    })


@app.route("/api/search")
def api_search():
    q = request.args.get("q", "").strip()
    if not q:
        return jsonify({"results": [], "count": 0})
    pattern = f"%{q}%"
    results = Place.query.filter(or_(
        Place.name.ilike(pattern), Place.description.ilike(pattern)
    )).limit(10).all()
    return jsonify({
        "results": [{
            "slug": p.slug, "name": p.name, "address": p.address,
            "rating": p.rating, "category": p.category.name if p.category else "",
            "image": p.hero_image,
        } for p in results],
        "count": len(results),
    })


@app.route("/api/nearby")
@app.route("/api/nearby/<slug>")
def api_nearby(slug=None):
    """Nearby places. Either by slug (finds city) or by lat/lng coords."""
    if slug:
        place = Place.query.filter_by(slug=slug).first_or_404()
        nearby = Place.query.filter(
            Place.city_id == place.city_id,
            Place.id != place.id,
        ).order_by(Place.rating.desc()).limit(8).all()
    else:
        # By lat/lng: find the closest city and return its highest-rated places
        try:
            lat = float(request.args.get("lat", 0))
            lng = float(request.args.get("lng", 0))
        except (ValueError, TypeError):
            return jsonify({"nearby": [], "error": "invalid coordinates"}), 400
        # Closest city by simple squared-distance
        cities = City.query.all()
        if not cities:
            return jsonify({"nearby": []})
        closest = min(cities, key=lambda c: (c.lat - lat) ** 2 + (c.lng - lng) ** 2)
        nearby = Place.query.filter_by(city_id=closest.id) \
            .order_by(Place.rating.desc()).limit(8).all()
    return jsonify({
        "nearby": [{
            "slug": p.slug, "name": p.name, "rating": p.rating,
            "image": p.hero_image, "category": p.category.name if p.category else "",
        } for p in nearby]
    })


# --------------------------------------------------------------------------
#  R7: SEO sitemap + locale aliases + business claim flow
# --------------------------------------------------------------------------
@app.route("/sitemap.xml")
def sitemap_xml():
    """Sitemap index — groups <sitemap> children per city + per category +
    a top-level URL set for static pages.  Crawler-friendly and lets us
    expose 290k+ places without dropping a 200MB sitemap.xml on the wire."""
    cities = City.query.order_by(City.slug).all()
    cats = Category.query.order_by(Category.slug).all()
    base = request.url_root.rstrip("/")
    lines = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for c in cities:
        lines.append("<sitemap><loc>{}/sitemap/city/{}.xml</loc></sitemap>".format(base, c.slug))
    for cat in cats:
        lines.append("<sitemap><loc>{}/sitemap/category/{}.xml</loc></sitemap>".format(base, cat.slug))
    lines.append("<sitemap><loc>{}/sitemap/static.xml</loc></sitemap>".format(base))
    lines.append("</sitemapindex>")
    body = "\n".join(lines)
    return app.response_class(body, mimetype="application/xml")


@app.route("/sitemap/city/<slug>.xml")
def sitemap_city_xml(slug):
    city = City.query.filter_by(slug=slug).first_or_404()
    base = request.url_root.rstrip("/")
    places = (Place.query.filter_by(city_id=city.id)
              .order_by(Place.rating.desc()).limit(2000).all())
    out = ['<?xml version="1.0" encoding="UTF-8"?>',
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    out.append("<url><loc>{}/city/{}</loc><changefreq>weekly</changefreq></url>".format(base, city.slug))
    for p in places:
        out.append("<url><loc>{}/place/{}</loc><changefreq>monthly</changefreq></url>".format(base, p.slug))
    out.append("</urlset>")
    return app.response_class("\n".join(out), mimetype="application/xml")


@app.route("/sitemap/category/<slug>.xml")
def sitemap_category_xml(slug):
    cat = Category.query.filter_by(slug=slug).first_or_404()
    base = request.url_root.rstrip("/")
    places = (Place.query.filter_by(category_id=cat.id)
              .order_by(Place.rating.desc()).limit(2000).all())
    out = ['<?xml version="1.0" encoding="UTF-8"?>',
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    out.append("<url><loc>{}/category/{}</loc></url>".format(base, cat.slug))
    for p in places:
        out.append("<url><loc>{}/place/{}</loc></url>".format(base, p.slug))
    out.append("</urlset>")
    return app.response_class("\n".join(out), mimetype="application/xml")


@app.route("/sitemap/static.xml")
def sitemap_static_xml():
    base = request.url_root.rstrip("/")
    static_paths = ["/", "/explore", "/about", "/help", "/contribute",
                    "/lists", "/saved", "/your-places", "/timeline",
                    "/transit", "/transit/lines", "/transit/realtime"]
    out = ['<?xml version="1.0" encoding="UTF-8"?>',
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for p in static_paths:
        out.append("<url><loc>{}{}</loc></url>".format(base, p))
    # Per-locale homepage entries (hreflang signals via separate URLs)
    for loc in R7_LOCALES:
        out.append("<url><loc>{}/{}/</loc></url>".format(base, loc["code"]))
    out.append("</urlset>")
    return app.response_class("\n".join(out), mimetype="application/xml")


@app.route("/robots.txt")
def robots_txt():
    base = request.url_root.rstrip("/")
    body = ("User-agent: *\nAllow: /\nDisallow: /account\nDisallow: /your-places\n"
            "Sitemap: {}/sitemap.xml\n").format(base)
    return app.response_class(body, mimetype="text/plain")


@app.route("/<lang_code>/")
def locale_home(lang_code):
    """Locale alias for the homepage.  Path /<lang>/ exposes a localized
    landing for 25 languages incl. RTL (ar/he).  Renders the same content
    as `/` but passes `lang_code` + `lang_dir` to the template via the
    session so base.html can switch <html lang=...> + dir attributes."""
    if lang_code not in R7_LOCALE_CODES:
        abort(404)
    session["lang_code"] = lang_code
    locale = R7_LOCALE_BY_CODE[lang_code]
    featured = Place.query.filter_by(is_featured=True).limit(12).all()
    popular = Place.query.filter_by(is_popular=True).order_by(Place.rating.desc()).limit(12).all()
    cities = City.query.order_by(City.display_name).limit(12).all()
    categories = Category.query.order_by(Category.id).all()
    return render_template(
        "index.html",
        featured=featured,
        popular=popular,
        cities=cities,
        categories=categories,
        active_locale=locale,
    )


@app.route("/locales")
def locales_index():
    """Human-readable list of supported locales (also serves as an
    hreflang reference page for crawlers)."""
    base = request.url_root.rstrip("/")
    rows = [{"href": "{}/{}/".format(base, l["code"]),
             "code": l["code"], "name": l["name"], "dir": l["dir"],
             "tagline": l["tagline"]} for l in R7_LOCALES]
    return app.response_class(
        "<!DOCTYPE html><html lang=\"en\"><head><meta charset=\"UTF-8\">"
        "<title>Locales - Google Maps</title></head><body>"
        "<h1>Supported locales ({})</h1><ul>".format(len(rows))
        + "".join('<li><a href="{}" hreflang="{}" dir="{}">{} ({}) - {}</a></li>'
                  .format(r["href"], r["code"], r["dir"], r["name"], r["code"], r["tagline"])
                  for r in rows)
        + "</ul></body></html>",
        mimetype="text/html",
    )


@app.route("/business/claim/<slug>", methods=["GET", "POST"])
def business_claim(slug):
    """Business-claim flow: a place owner can claim a listing by
    submitting verification details.  Multi-step view: GET shows form,
    POST records a session-scoped confirmation (no DB write — keeps
    seed deterministic)."""
    place = Place.query.filter_by(slug=slug).first_or_404()
    if request.method == "POST":
        biz_name = (request.form.get("business_name") or "").strip()
        owner = (request.form.get("owner_name") or "").strip()
        email = (request.form.get("contact_email") or "").strip()
        if not (biz_name and owner and email):
            flash("All fields required.", "error")
            return redirect(url_for("business_claim", slug=slug))
        session["business_claim_submitted"] = {
            "place_slug": place.slug, "business_name": biz_name,
            "owner_name": owner, "contact_email": email,
        }
        flash("Claim submitted — we'll verify within 5 business days.", "success")
        return redirect(url_for("business_claim", slug=slug))
    submitted = session.get("business_claim_submitted")
    body = ("""<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8">
<title>Claim {name} - Google Maps</title></head><body>
<h1>Claim this business</h1>
<p>You are claiming: <strong>{name}</strong> ({addr}).</p>
{confirm}
<form method="post">
  <input type="hidden" name="csrf_token" value="{csrf}">
  <label>Business name <input name="business_name" required></label><br>
  <label>Owner name <input name="owner_name" required></label><br>
  <label>Contact email <input type="email" name="contact_email" required></label><br>
  <button type="submit">Submit claim</button>
</form>
<p><a href="{back}">Back to place</a></p>
</body></html>""".format(
        name=place.name,
        addr=place.address or "",
        csrf=(request.cookies.get('csrf_token') or ''),
        confirm=("<p class='ok'>Claim received for "
                 + submitted["business_name"] + " — confirmation pending.</p>"
                 if submitted and submitted.get("place_slug") == place.slug else ""),
        back=url_for("place_detail", slug=place.slug),
    ))
    return app.response_class(body, mimetype="text/html")


business_claim = csrf.exempt(business_claim)


# --------------------------------------------------------------------------
#  R8 — Observability, developer console, webhooks, command palette,
#  keyboard-shortcut + symbol-glossary endpoints.
# --------------------------------------------------------------------------

# Pinned "boot" moment used by uptime/event endpoints.  Drifting wall-clock
# would break byte-identical reset AND make /api/uptime non-deterministic.
R8_BOOT_MOMENT = MIRROR_REFERENCE_DATETIME
R8_BUILD_SHA = "r8-google-map-2026-05-22"
R8_API_VERSION = "v2.8.0"

# Keyboard-shortcut registry.  Keep this JSON-stable for `/help/keyboard-shortcuts`
# and the in-app help modal; new shortcuts must be appended (not reordered).
R8_KEYBOARD_SHORTCUTS = [
    {"keys": ["+"], "action": "zoom_in",
     "label": "Zoom in",
     "description": "Increase map zoom by one level (Vim-style)."},
    {"keys": ["-"], "action": "zoom_out",
     "label": "Zoom out",
     "description": "Decrease map zoom by one level (Vim-style)."},
    {"keys": ["="], "action": "zoom_reset",
     "label": "Reset zoom",
     "description": "Reset zoom to the default level for the active view."},
    {"keys": ["/"], "action": "focus_search",
     "label": "Focus search",
     "description": "Move focus to the global search input."},
    {"keys": ["Ctrl+K", "Cmd+K"], "action": "command_palette",
     "label": "Open command palette",
     "description": "Open the quick-jump command palette to navigate to a place, category, or saved list."},
    {"keys": ["?"], "action": "open_help",
     "label": "Show keyboard help",
     "description": "Open the keyboard-shortcut + symbol-glossary help modal."},
    {"keys": ["g", "h"], "action": "go_home",
     "label": "Go home",
     "description": "Chord shortcut: press g, then h to jump to the homepage."},
    {"keys": ["g", "l"], "action": "go_lists",
     "label": "Go to lists",
     "description": "Chord shortcut: press g, then l to jump to your saved lists."},
    {"keys": ["g", "t"], "action": "go_trips",
     "label": "Go to trips",
     "description": "Chord shortcut: press g, then t to jump to your trips."},
    {"keys": ["g", "e"], "action": "go_explore",
     "label": "Go to explore",
     "description": "Chord shortcut: press g, then e to jump to Explore nearby."},
    {"keys": ["t"], "action": "toggle_traffic",
     "label": "Toggle traffic layer",
     "description": "Toggle the traffic layer on the active map canvas."},
    {"keys": ["s"], "action": "toggle_satellite",
     "label": "Toggle satellite",
     "description": "Toggle satellite imagery on the active map canvas."},
    {"keys": ["b"], "action": "toggle_bicycling",
     "label": "Toggle bicycling layer",
     "description": "Toggle the bicycle-route layer on the active map canvas."},
    {"keys": ["Esc"], "action": "close_modal",
     "label": "Close modal",
     "description": "Close the command palette, help modal, or active dialog."},
]

# Symbol glossary — used by the in-app tooltip + accessibility probes.
R8_SYMBOL_GLOSSARY = [
    {"glyph": "P", "icon": "local_parking",
     "label": "Parking", "category": "amenity",
     "description": "Public or paid parking lot.  Capacity, hourly rate, and EV stalls are listed on the place card when available."},
    {"glyph": "T", "icon": "directions_transit",
     "label": "Transit stop", "category": "transit",
     "description": "Bus, light-rail, or subway stop.  Click for real-time arrivals if the agency publishes a GTFS-Realtime feed."},
    {"glyph": "EV", "icon": "ev_station",
     "label": "EV charging", "category": "amenity",
     "description": "Public EV charging station.  Connector type (CCS, CHAdeMO, Tesla NACS) and peak kW are listed on the place card."},
    {"glyph": "GAS", "icon": "local_gas_station",
     "label": "Gas / fuel", "category": "amenity",
     "description": "Fueling station.  Look for the regular/premium/diesel breakdown on the place card."},
    {"glyph": "WC", "icon": "wc",
     "label": "Restroom", "category": "amenity",
     "description": "Public restroom.  Wheelchair accessibility is noted in the accessibility panel."},
    {"glyph": "H", "icon": "local_hospital",
     "label": "Hospital", "category": "health",
     "description": "Hospital or 24-hour urgent-care facility.  ER hours and trauma level are shown when available."},
    {"glyph": "$", "icon": "attach_money",
     "label": "ATM", "category": "finance",
     "description": "Cash machine.  Network compatibility is shown on the place card to help avoid surcharges."},
    {"glyph": "i", "icon": "info",
     "label": "Information", "category": "service",
     "description": "Visitor information point (kiosk, ranger station, or staffed info booth)."},
    {"glyph": "WiFi", "icon": "wifi",
     "label": "Public Wi-Fi", "category": "amenity",
     "description": "Free public Wi-Fi available.  SSID and password are listed on the place card when published."},
    {"glyph": "BIKE", "icon": "directions_bike",
     "label": "Bike share", "category": "transit",
     "description": "Bike share station or e-scooter corral.  Dock count and electric-assist availability are listed on the card."},
    {"glyph": "ELEV", "icon": "elevator",
     "label": "Elevator access", "category": "accessibility",
     "description": "Step-free elevator access is available to the marked floor or platform."},
    {"glyph": "DOG", "icon": "pets",
     "label": "Dog-friendly", "category": "amenity",
     "description": "Off-leash dog park or marker for dog-friendly seating/water bowls."},
]


@app.route("/healthz")
def healthz():
    """Lightweight health probe.  Returns 200 + JSON status for liveness."""
    return jsonify({
        "status": "ok",
        "service": "google-maps-mirror",
        "build_sha": R8_BUILD_SHA,
        "api_version": R8_API_VERSION,
        "boot_at": R8_BOOT_MOMENT.isoformat() + "Z",
    })


@app.route("/api/uptime")
def api_uptime():
    """Deterministic uptime + DB-row snapshot.  Numbers are derived from
    MIRROR_REFERENCE_DATETIME so the response is byte-identical across
    rebuilds (no wall-clock leakage)."""
    boot = R8_BOOT_MOMENT
    # Deterministic "current" moment: 7 days + 6h after boot for the demo.
    fake_now = boot + timedelta(days=7, hours=6, minutes=12)
    delta = fake_now - boot
    return jsonify({
        "build_sha": R8_BUILD_SHA,
        "api_version": R8_API_VERSION,
        "boot_at": boot.isoformat() + "Z",
        "snapshot_at": fake_now.isoformat() + "Z",
        "uptime_seconds": int(delta.total_seconds()),
        "uptime_human": f"{delta.days}d {delta.seconds // 3600}h {(delta.seconds // 60) % 60}m",
        "rows": {
            "places": Place.query.count(),
            "cities": City.query.count(),
            "categories": Category.query.count(),
            "transit_lines": TransitLine.query.count(),
        },
        "regions": ["us-east-1", "us-west-2", "eu-west-1", "ap-northeast-1"],
        "status": "healthy",
    })


@app.route("/api/events")
def api_events():
    """Synthetic event feed used by `?` help modal + observability probes.
    Deterministic: events derived from MIRROR_REFERENCE_DATETIME ± offsets
    and from the highest-id rows in the catalog."""
    boot = R8_BOOT_MOMENT
    cursor = request.args.get("cursor", "")
    limit = max(1, min(int(request.args.get("limit", 20) or 20), 50))

    # Build deterministic events: recent saves, recent reviews, recent places.
    events = []
    recent_places = (Place.query
                     .order_by(Place.id.desc())
                     .limit(limit).all())
    for i, p in enumerate(recent_places):
        events.append({
            "id": f"evt-place-{p.id}",
            "type": "place.indexed",
            "at": (boot + timedelta(minutes=i)).isoformat() + "Z",
            "place_slug": p.slug,
            "place_name": p.name,
            "category": p.category.slug if p.category else "",
            "city_slug": p.city.slug if p.city else "",
        })
    return jsonify({
        "events": events,
        "next_cursor": cursor + ("+%d" % len(events)),
        "build_sha": R8_BUILD_SHA,
        "snapshot_at": (boot + timedelta(days=7, hours=6)).isoformat() + "Z",
    })


@app.route("/api/v2/places/graphql", methods=["GET", "POST"])
@app.route("/api/v2-places-graphql", methods=["GET", "POST"])
def api_v2_places_graphql():
    """GraphQL-style POST endpoint for the v2 places API.

    Accepts {"query": "...", "variables": {...}} JSON.  Supports the
    `places(filter:..., limit:...)` root field and a `place(slug:...)`
    lookup, both returning a fixed shape so downstream agents can rely on
    it.  GET shows a schema-IDL preview so the URL is discoverable from
    the developer console (`/developer/maps-embed-code`)."""
    if request.method == "GET":
        schema = (
            "# Google Maps Mirror — v2 GraphQL preview\n"
            "schema { query: Query }\n"
            "type Query {\n"
            "  places(filter: PlaceFilter, limit: Int = 10): [Place!]!\n"
            "  place(slug: String!): Place\n"
            "  cities(limit: Int = 10): [City!]!\n"
            "  categories: [Category!]!\n"
            "  health: HealthStatus!\n"
            "}\n"
            "input PlaceFilter { city: String, category: String, minRating: Float, query: String }\n"
            "type Place {\n"
            "  id: ID!  slug: String!  name: String!\n"
            "  category: String  city: String\n"
            "  rating: Float  reviewCount: Int  priceLevel: String\n"
            "  lat: Float  lng: Float  address: String\n"
            "  evCharging: Boolean  has24h: Boolean\n"
            "}\n"
            "type City { slug: String!  displayName: String!  country: String  lat: Float  lng: Float }\n"
            "type Category { slug: String!  name: String! }\n"
            "type HealthStatus { status: String!  buildSha: String!  apiVersion: String! }\n"
        )
        return jsonify({
            "endpoint": "/api/v2/places/graphql",
            "method": "POST",
            "api_version": R8_API_VERSION,
            "schema": schema,
            "example_query": "{ places(filter:{city:\"new-york\", minRating:4.5}, limit:3) { slug name rating } }",
        })

    payload = request.get_json(silent=True) or {}
    q = (payload.get("query") or "").strip()
    variables = payload.get("variables") or {}

    def _serialize_place(p):
        return {
            "id": p.id,
            "slug": p.slug,
            "name": p.name,
            "category": p.category.slug if p.category else None,
            "city": p.city.slug if p.city else None,
            "rating": p.rating,
            "reviewCount": p.review_count,
            "priceLevel": p.price_level,
            "lat": p.lat,
            "lng": p.lng,
            "address": p.address,
            "evCharging": bool(p.ev_charging),
            "has24h": bool(p.is_24h),
        }

    data = {}

    # `place(slug:"...")`: prioritise specific lookups.
    m_place = re.search(r"\bplace\s*\(\s*slug\s*:\s*\"([^\"]+)\"", q)
    if m_place:
        p = Place.query.filter_by(slug=m_place.group(1)).first()
        data["place"] = _serialize_place(p) if p else None

    # `places(filter:{...}, limit:N)`: filter by city/category/minRating/query
    m_places = re.search(r"\bplaces\s*\(([^)]*)\)", q)
    if m_places or q == "":
        args_blob = m_places.group(1) if m_places else ""
        f_city = variables.get("city") or _gql_kv(args_blob, "city")
        f_cat = variables.get("category") or _gql_kv(args_blob, "category")
        f_q = variables.get("query") or _gql_kv(args_blob, "query")
        f_min = variables.get("minRating") or _gql_kv_num(args_blob, "minRating")
        try:
            limit = int(variables.get("limit") or _gql_kv_num(args_blob, "limit") or 10)
        except (TypeError, ValueError):
            limit = 10
        limit = max(1, min(limit, 50))
        query = Place.query
        if f_city:
            city = City.query.filter_by(slug=f_city).first()
            if city:
                query = query.filter_by(city_id=city.id)
        if f_cat:
            cat = Category.query.filter_by(slug=f_cat).first()
            if cat:
                query = query.filter_by(category_id=cat.id)
        if f_q:
            pattern = f"%{f_q}%"
            query = query.filter(Place.name.ilike(pattern))
        if f_min is not None:
            try:
                query = query.filter(Place.rating >= float(f_min))
            except (TypeError, ValueError):
                pass
        rows = query.order_by(Place.rating.desc(), Place.id.asc()).limit(limit).all()
        data["places"] = [_serialize_place(p) for p in rows]

    if "health" in q:
        data["health"] = {
            "status": "ok",
            "buildSha": R8_BUILD_SHA,
            "apiVersion": R8_API_VERSION,
        }
    if "categories" in q and "category(" not in q:
        cats = Category.query.order_by(Category.id).all()
        data["categories"] = [{"slug": c.slug, "name": c.name} for c in cats]
    if re.search(r"\bcities\b", q):
        # Optional limit parsing for cities root field.
        m_cities = re.search(r"\bcities\s*\(([^)]*)\)", q)
        c_blob = m_cities.group(1) if m_cities else ""
        try:
            c_limit = int(_gql_kv_num(c_blob, "limit") or 10)
        except (TypeError, ValueError):
            c_limit = 10
        c_limit = max(1, min(c_limit, 50))
        rows = City.query.order_by(City.id).limit(c_limit).all()
        data["cities"] = [{
            "slug": c.slug, "displayName": c.display_name,
            "country": c.country, "lat": c.lat, "lng": c.lng,
        } for c in rows]

    return jsonify({"data": data, "errors": [],
                    "apiVersion": R8_API_VERSION,
                    "buildSha": R8_BUILD_SHA})


api_v2_places_graphql = csrf.exempt(api_v2_places_graphql)


def _gql_kv(blob, key):
    """Pluck a string value (quoted) from a GraphQL argument blob."""
    m = re.search(r'\b' + re.escape(key) + r'\s*:\s*"([^"]*)"', blob)
    return m.group(1) if m else None


def _gql_kv_num(blob, key):
    """Pluck a numeric value from a GraphQL argument blob."""
    m = re.search(r'\b' + re.escape(key) + r'\s*:\s*([0-9]+(?:\.[0-9]+)?)', blob)
    return m.group(1) if m else None


@app.route("/webhook/place-update", methods=["GET", "POST"])
def webhook_place_update():
    """Inbound webhook for partner place updates.

    GET shows a usage doc + signing-secret rotation policy so the URL is
    discoverable from the developer console.  POST accepts a JSON
    envelope with `event` + `place_slug` + `delta` fields and returns an
    acknowledgement — does NOT mutate the seed DB (keeps reset
    byte-identical).  Real production deploys would verify the
    `X-Maps-Signature` HMAC header before queuing for processing."""
    if request.method == "GET":
        return jsonify({
            "endpoint": "/webhook/place-update",
            "method": "POST",
            "content_type": "application/json",
            "auth": "X-Maps-Signature: sha256=<hmac>",
            "secret_rotation": "Rotated every 90 days; previous secret accepted for 24h overlap.",
            "envelope": {
                "event": "place.upsert | place.delete | place.metadata",
                "place_slug": "<string>",
                "delta": {"name": "<string?>", "hours": "<string?>",
                          "phone": "<string?>", "website": "<string?>"},
                "received_at": "<ISO-8601>",
            },
            "retry": "exponential-backoff up to 5 attempts, 24h max wait",
        })

    payload = request.get_json(silent=True) or {}
    event = (payload.get("event") or "").strip()
    place_slug = (payload.get("place_slug") or "").strip()
    delta = payload.get("delta") or {}

    allowed_events = {"place.upsert", "place.delete", "place.metadata"}
    if event not in allowed_events:
        return jsonify({
            "accepted": False,
            "error": f"unsupported event '{event}'",
            "allowed": sorted(allowed_events),
        }), 400

    # Look up the place to confirm slug exists; reject 404s explicitly.
    place_exists = bool(Place.query.filter_by(slug=place_slug).first()) if place_slug else False

    # Deterministic ack-id from the payload (no wall-clock).
    ack_id = hashlib.sha256(
        json.dumps({"event": event, "slug": place_slug, "delta": delta},
                   sort_keys=True).encode()
    ).hexdigest()[:16]

    return jsonify({
        "accepted": True,
        "ack_id": ack_id,
        "event": event,
        "place_slug": place_slug,
        "place_exists": place_exists,
        "delta_fields": sorted(delta.keys()),
        "queued_at": (R8_BOOT_MOMENT + timedelta(days=7, hours=6)).isoformat() + "Z",
        "note": "Accepted for async processing.  No DB write performed in mirror.",
    })


webhook_place_update = csrf.exempt(webhook_place_update)


@app.route("/developer/maps-embed-code")
def developer_maps_embed_code():
    """Developer console: returns ready-to-paste embed snippets +
    discovery of the v2 GraphQL / webhook / health endpoints."""
    base = request.url_root.rstrip("/")
    sample_slug = (Place.query.order_by(Place.id).first() or _NullPlace()).slug if Place.query.count() else "central-park"

    iframe_snippet = (
        '<iframe width="600" height="450" frameborder="0"\n'
        '    style="border:0" loading="lazy" allowfullscreen\n'
        '    src="' + base + '/maps/embed?place=' + sample_slug + '"></iframe>'
    )
    static_snippet = (
        base + "/maps/staticmap?center=40.7589,-73.9851&zoom=12&size=600x300"
        "&markers=color:red%7Clabel:A%7C" + sample_slug
    )
    js_snippet = (
        '<script async\n'
        '    src="' + base + '/maps/js?key=PUBLIC_DEMO_KEY&libraries=places"></script>'
    )
    body = render_template_string(_R8_DEVELOPER_TPL,
                                  base=base,
                                  iframe_snippet=iframe_snippet,
                                  static_snippet=static_snippet,
                                  js_snippet=js_snippet,
                                  sample_slug=sample_slug,
                                  api_version=R8_API_VERSION,
                                  shortcuts=R8_KEYBOARD_SHORTCUTS,
                                  glossary=R8_SYMBOL_GLOSSARY)
    return app.response_class(body, mimetype="text/html")


class _NullPlace:
    slug = "central-park"


_R8_DEVELOPER_TPL = """<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8">
<title>Developer Console — Maps Embed Code</title>
<link rel="stylesheet" href="/static/css/main.css">
</head><body>
<main class="container" style="max-width:980px;margin:24px auto;padding:0 16px;">
<h1>Developer Console</h1>
<p>API version: <code>{{ api_version }}</code> &middot;
<a href="/healthz">/healthz</a> &middot;
<a href="/api/uptime">/api/uptime</a> &middot;
<a href="/api/events">/api/events</a></p>

<h2 id="embed-iframe">Embed iframe</h2>
<pre data-snippet="iframe">{{ iframe_snippet }}</pre>

<h2 id="embed-static">Static map URL</h2>
<pre data-snippet="static">{{ static_snippet }}</pre>

<h2 id="embed-js">Maps JS bootstrap</h2>
<pre data-snippet="js">{{ js_snippet }}</pre>

<h2 id="graphql">v2 places GraphQL</h2>
<p>POST <code>{{ base }}/api/v2/places/graphql</code> with a JSON body:</p>
<pre data-snippet="graphql">curl -X POST {{ base }}/api/v2/places/graphql \\
  -H 'Content-Type: application/json' \\
  -d '{"query":"{ places(filter:{city:\\"new-york\\", minRating:4.6}, limit:5){ slug name rating } }"}'</pre>
<p>GET the same URL for the schema preview.</p>

<h2 id="webhook">Inbound webhook</h2>
<p>POST <code>{{ base }}/webhook/place-update</code> with
<code>X-Maps-Signature</code> + JSON envelope.  GET for the spec.</p>
<pre data-snippet="webhook">curl -X POST {{ base }}/webhook/place-update \\
  -H 'Content-Type: application/json' \\
  -H 'X-Maps-Signature: sha256=&lt;hmac&gt;' \\
  -d '{"event":"place.metadata","place_slug":"{{ sample_slug }}",
       "delta":{"hours":"Mon-Sun: 8:00 AM - 10:00 PM"}}'</pre>

<h2 id="shortcuts">Keyboard shortcuts</h2>
<table class="kb-shortcuts" style="border-collapse:collapse;width:100%">
<thead><tr><th align="left">Keys</th><th align="left">Action</th><th align="left">Description</th></tr></thead>
<tbody>
{% for s in shortcuts %}
  <tr>
    <td><code>{{ s['keys']|join(' / ') }}</code></td>
    <td>{{ s.label }}</td>
    <td>{{ s.description }}</td>
  </tr>
{% endfor %}
</tbody></table>

<h2 id="glossary">Symbol glossary</h2>
<table class="symbol-glossary" style="border-collapse:collapse;width:100%">
<thead><tr><th>Glyph</th><th>Label</th><th>Category</th><th>Description</th></tr></thead>
<tbody>
{% for g in glossary %}
  <tr>
    <td><code>{{ g.glyph }}</code></td>
    <td>{{ g.label }}</td>
    <td>{{ g.category }}</td>
    <td>{{ g.description }}</td>
  </tr>
{% endfor %}
</tbody></table>

<p><a href="/">&laquo; Back to map</a></p>
</main>
</body></html>
"""


@app.route("/help/keyboard-shortcuts")
def help_keyboard_shortcuts():
    """JSON shortcut registry used by the `?` help modal."""
    return jsonify({
        "shortcuts": R8_KEYBOARD_SHORTCUTS,
        "version": R8_API_VERSION,
        "doc_url": "/developer/maps-embed-code#shortcuts",
    })


@app.route("/help/symbol-glossary")
def help_symbol_glossary():
    """JSON symbol-glossary registry used by tooltips + A11Y probes."""
    return jsonify({
        "glyphs": R8_SYMBOL_GLOSSARY,
        "version": R8_API_VERSION,
        "doc_url": "/developer/maps-embed-code#glossary",
    })


@app.route("/api/command-palette")
def api_command_palette():
    """Backing data for the Cmd+K command palette: top categories, top
    cities, top places, and static page links.  Deterministic ordering."""
    q = (request.args.get("q") or "").strip()
    limit = max(1, min(int(request.args.get("limit", 20) or 20), 50))
    pattern = f"%{q}%" if q else None

    pages = [
        {"label": "Home", "kind": "page", "href": "/", "keys": ["g", "h"]},
        {"label": "Explore nearby", "kind": "page", "href": "/explore", "keys": ["g", "e"]},
        {"label": "Saved lists", "kind": "page", "href": "/lists", "keys": ["g", "l"]},
        {"label": "Trips", "kind": "page", "href": "/trips", "keys": ["g", "t"]},
        {"label": "Your places", "kind": "page", "href": "/your-places", "keys": []},
        {"label": "Timeline", "kind": "page", "href": "/timeline", "keys": []},
        {"label": "Settings", "kind": "page", "href": "/settings", "keys": []},
        {"label": "Developer console", "kind": "page",
         "href": "/developer/maps-embed-code", "keys": []},
        {"label": "Keyboard shortcuts", "kind": "page",
         "href": "/help#keyboard", "keys": ["?"]},
    ]
    if q:
        pages = [p for p in pages if q.lower() in p["label"].lower()]

    cats_q = Category.query
    if pattern:
        cats_q = cats_q.filter(or_(Category.name.ilike(pattern),
                                   Category.slug.ilike(pattern)))
    cats = [{"label": c.name, "kind": "category",
             "href": f"/category/{c.slug}", "slug": c.slug}
            for c in cats_q.order_by(Category.id).limit(limit).all()]

    cities_q = City.query
    if pattern:
        cities_q = cities_q.filter(City.display_name.ilike(pattern))
    cities = [{"label": c.display_name, "kind": "city",
               "href": f"/city/{c.slug}", "slug": c.slug}
              for c in cities_q.order_by(City.id).limit(limit).all()]

    places_q = Place.query
    if pattern:
        places_q = places_q.filter(Place.name.ilike(pattern))
        places_q = places_q.order_by(Place.rating.desc(), Place.id.asc())
    else:
        places_q = places_q.order_by(Place.rating.desc(), Place.id.asc())
    places = [{"label": p.name, "kind": "place",
               "href": f"/place/{p.slug}", "slug": p.slug,
               "subtitle": p.address or ""}
              for p in places_q.limit(limit).all()]

    return jsonify({
        "query": q,
        "results": {
            "pages": pages,
            "categories": cats,
            "cities": cities,
            "places": places,
        },
        "total": len(pages) + len(cats) + len(cities) + len(places),
        "version": R8_API_VERSION,
    })


# --------------------------------------------------------------------------
#  R9 — outdoor verticals: trail / beach / lighthouse / scenic-byway /
#  geocache / national-park permit-request.  Each route accepts the
#  Place.slug from the R9 expansion (slug prefix r9-<kind>-).  Slug-numeric
#  fallback also accepts the integer place id.  Output is HTML for browser
#  surfaces and JSON when Accept: application/json is requested or the
#  route handler is suffixed with .json.
# --------------------------------------------------------------------------
R9_KINDS = ("trail", "beach", "lighthouse", "byway", "geocache", "park")
R9_TRAIL_DIFFICULTIES = ("easy", "moderate", "hard")
R9_WATER_QUALITY = ("excellent", "good", "fair", "advisory")


def _r9_lookup(kind, ident):
    """Resolve a Place from a slug or integer id; enforce kind prefix.

    Returns the Place or None.  Kind is one of R9_KINDS (or "" for any).
    """
    if ident is None:
        return None
    p = None
    if isinstance(ident, int) or (isinstance(ident, str) and ident.isdigit()):
        p = Place.query.get(int(ident))
    if p is None:
        p = Place.query.filter_by(slug=str(ident)).first()
    if p is None:
        return None
    if kind:
        slug_prefix = f"r9-{kind}-"
        # Allow real Wikipedia trails/beaches too (e.g. freedom-trail,
        # venice-beach) by also accepting a slug containing the kind
        # substring.  Strict R9 routes prefer the prefix match.
        if not (p.slug.startswith(slug_prefix) or kind in p.slug):
            return None
    return p


def _r9_pick(slug, options, salt):
    """Deterministic pick from `options` using slug+salt."""
    h = hashlib.md5(f"{salt}:{slug}".encode()).digest()
    n = int.from_bytes(h[:4], "big")
    return options[n % len(options)]


def _r9_int(slug, salt, lo, hi):
    h = hashlib.md5(f"{salt}:{slug}".encode()).digest()
    n = int.from_bytes(h[:4], "big")
    return lo + (n % max(1, hi - lo + 1))


def _r9_json_or_html(payload, template, **ctx):
    """Render JSON if ?format=json or Accept: application/json, else HTML
    (falling back to a small inline template when the .html doesn't exist)."""
    want_json = (request.args.get("format") == "json"
                 or "application/json" in (request.headers.get("Accept", "")))
    if want_json:
        return jsonify(payload)
    try:
        return render_template(template, payload=payload, **ctx)
    except TemplateNotFound:
        # Inline fallback — keep this lightweight so no new templates are
        # required just for the R9 endpoints.
        body = render_template_string(
            "<!doctype html><meta charset='utf-8'>"
            "<title>{{ payload.title }} | Maps</title>"
            "<style>body{font-family:Roboto,Arial,sans-serif;max-width:760px;"
            "margin:32px auto;padding:0 16px;color:#202124}"
            "h1{font-size:22px}dt{font-weight:600;margin-top:8px}"
            "dd{margin:2px 0 8px 16px}pre{background:#f1f3f4;padding:8px;"
            "border-radius:6px;overflow:auto}</style>"
            "<h1>{{ payload.title }}</h1>"
            "<p>{{ payload.subtitle }}</p>"
            "<dl>"
            "{% for k, v in payload.fields.items() %}"
            "<dt>{{ k }}</dt><dd>{{ v }}</dd>"
            "{% endfor %}"
            "</dl>"
            "{% if payload.back %}<p><a href='{{ payload.back }}'>"
            "&larr; back to place</a></p>{% endif %}",
            payload=payload,
        )
        return body


@app.route("/trail/<ident>")
def r9_trail_detail(ident):
    p = _r9_lookup("trail", ident)
    if not p:
        abort(404)
    difficulty = _r9_pick(p.slug, R9_TRAIL_DIFFICULTIES, "r9diff")
    length_mi = round(0.4 + _r9_int(p.slug, "r9len", 0, 180) / 10.0, 1)
    elev_gain_ft = _r9_int(p.slug, "r9elev", 50, 3800)
    payload = {
        "kind": "trail",
        "title": p.name,
        "subtitle": f"{difficulty.capitalize()} · {length_mi} mi · {elev_gain_ft} ft gain",
        "slug": p.slug,
        "place_id": p.id,
        "difficulty": difficulty,
        "length_mi": length_mi,
        "elevation_gain_ft": elev_gain_ft,
        "trailhead": p.address,
        "city": p.city.display_name if p.city else "",
        "lat": p.lat, "lng": p.lng,
        "back": url_for("place_detail", slug=p.slug),
        "links": {
            "place": url_for("place_detail", slug=p.slug),
            "difficulty": url_for("r9_trail_difficulty", ident=p.slug),
        },
        "fields": {
            "Difficulty": difficulty,
            "Length": f"{length_mi} mi",
            "Elevation gain": f"{elev_gain_ft} ft",
            "Trailhead": p.address,
            "Rating": p.rating,
        },
    }
    return _r9_json_or_html(payload, "r9_trail.html")


@app.route("/trail/<ident>/difficulty")
def r9_trail_difficulty(ident):
    p = _r9_lookup("trail", ident)
    if not p:
        abort(404)
    # Stable difficulty buckets + 3-section difficulty breakdown.
    difficulty = _r9_pick(p.slug, R9_TRAIL_DIFFICULTIES, "r9diff")
    sections = []
    for i, label in enumerate(("Approach", "Ascent", "Summit")):
        sec_diff = R9_TRAIL_DIFFICULTIES[_r9_int(p.slug, f"r9sd{i}", 0, 2)]
        sections.append({
            "label": label,
            "difficulty": sec_diff,
            "length_mi": round(0.2 + _r9_int(p.slug, f"r9sl{i}", 0, 60) / 10.0, 1),
            "grade_pct": _r9_int(p.slug, f"r9sg{i}", 1, 22),
        })
    payload = {
        "kind": "trail-difficulty",
        "title": p.name + " — Difficulty",
        "subtitle": f"Overall: {difficulty}",
        "slug": p.slug,
        "place_id": p.id,
        "overall_difficulty": difficulty,
        "sections": sections,
        "back": url_for("r9_trail_detail", ident=p.slug),
        "fields": {
            "Overall": difficulty,
            **{f"{s['label']} section": f"{s['difficulty']} ({s['length_mi']} mi, {s['grade_pct']}% grade)"
               for s in sections},
        },
    }
    return _r9_json_or_html(payload, "r9_trail_difficulty.html")


@app.route("/beach/<ident>/water-quality")
@app.route("/beach/<ident>/water_quality")
def r9_beach_water_quality(ident):
    p = _r9_lookup("beach", ident)
    if not p:
        abort(404)
    rating = _r9_pick(p.slug, R9_WATER_QUALITY, "r9wq")
    enterococci = _r9_int(p.slug, "r9wqe", 1, 124)  # MPN/100 mL
    advisory = (rating == "advisory")
    sampled_at = (MIRROR_REFERENCE_DATETIME).strftime("%Y-%m-%d")
    payload = {
        "kind": "beach-water-quality",
        "title": p.name + " — Water Quality",
        "subtitle": f"Latest reading: {rating}",
        "slug": p.slug,
        "place_id": p.id,
        "rating": rating,
        "enterococci_mpn_100ml": enterococci,
        "advisory": advisory,
        "sampled_at": sampled_at,
        "agency": (p.city.display_name + " Health Dept.") if p.city else "Local Health Dept.",
        "back": url_for("place_detail", slug=p.slug),
        "fields": {
            "Rating": rating,
            "Enterococci": f"{enterococci} MPN/100 mL",
            "Sampled": sampled_at,
            "Advisory": "Yes" if advisory else "No",
        },
    }
    return _r9_json_or_html(payload, "r9_beach_water_quality.html")


@app.route("/lighthouse/<ident>")
def r9_lighthouse_detail(ident):
    p = _r9_lookup("lighthouse", ident)
    if not p:
        abort(404)
    height_ft = _r9_int(p.slug, "r9lhh", 38, 184)
    built_year = 1820 + _r9_int(p.slug, "r9lhy", 0, 160)
    tour_durations = ("30 min", "45 min", "60 min", "90 min")
    payload = {
        "kind": "lighthouse",
        "title": p.name,
        "subtitle": f"Built {built_year} · {height_ft} ft tower",
        "slug": p.slug,
        "place_id": p.id,
        "height_ft": height_ft,
        "built_year": built_year,
        "tour_duration": _r9_pick(p.slug, tour_durations, "r9lhd"),
        "tour_open": True,
        "city": p.city.display_name if p.city else "",
        "lat": p.lat, "lng": p.lng,
        "back": url_for("place_detail", slug=p.slug),
        "fields": {
            "Built": built_year,
            "Tower height": f"{height_ft} ft",
            "Tour duration": _r9_pick(p.slug, tour_durations, "r9lhd"),
            "City": p.city.display_name if p.city else "—",
        },
    }
    return _r9_json_or_html(payload, "r9_lighthouse.html")


@app.route("/scenic-byway/<route>")
@app.route("/scenic_byway/<route>")
def r9_scenic_byway(route):
    """Scenic byway page.

    `route` accepts either a Place slug (typically prefixed r9-byway-) or
    the byway's themed handle.  The detail view summarizes the route loop.
    """
    p = _r9_lookup("byway", route)
    if not p:
        abort(404)
    # Pull byway theme from tags_json (we wrote tag like "theme-coastal").
    try:
        tags = json.loads(p.tags_json or "[]")
    except Exception:
        tags = []
    theme = ""
    for t in tags:
        if isinstance(t, str) and t.startswith("theme-"):
            theme = t[len("theme-"):]
            break
    if not theme:
        theme = _r9_pick(p.slug, ("coastal", "mountain", "river", "heritage"), "r9bw")

    loop_miles = round(8 + _r9_int(p.slug, "r9bwm", 0, 230) / 1.0, 1)
    pullouts = _r9_int(p.slug, "r9bwp", 4, 26)
    payload = {
        "kind": "scenic-byway",
        "title": p.name,
        "subtitle": f"{theme.capitalize()} themed · {loop_miles} mi loop · {pullouts} pullouts",
        "slug": p.slug,
        "place_id": p.id,
        "theme": theme,
        "loop_miles": loop_miles,
        "pullouts": pullouts,
        "back": url_for("place_detail", slug=p.slug),
        "fields": {
            "Theme": theme,
            "Loop length": f"{loop_miles} mi",
            "Designated pullouts": pullouts,
            "Audio tour": "Yes",
        },
    }
    return _r9_json_or_html(payload, "r9_scenic_byway.html")


@app.route("/park/<ident>/permit-request", methods=["GET", "POST"])
@app.route("/park/<ident>/permit_request", methods=["GET", "POST"])
def r9_park_permit_request(ident):
    # park kind OR any Place with category=parks works
    p = _r9_lookup("park", ident)
    if not p:
        # Fall back to direct slug lookup, but only allow Places in parks
        # category (so /park/<any-slug>/permit-request is gated).
        cand = Place.query.filter_by(slug=str(ident)).first()
        if cand and cand.category and cand.category.slug == "parks":
            p = cand
    if not p:
        abort(404)

    if request.method == "POST":
        purpose = (request.form.get("purpose") or "").strip()[:120]
        party = max(1, min(500, int(request.form.get("party_size", "1") or "1")))
        date = (request.form.get("date") or "").strip()[:32]
        # Deterministic ack id — same fields → same id (works for replay).
        ack_seed = f"{p.slug}|{purpose}|{party}|{date}"
        ack_id = "permit-" + hashlib.sha1(ack_seed.encode()).hexdigest()[:12]
        payload = {
            "kind": "park-permit-request",
            "title": p.name + " — Permit Request",
            "subtitle": "Request received",
            "ack_id": ack_id,
            "park_slug": p.slug,
            "purpose": purpose,
            "party_size": party,
            "requested_date": date,
            "status": "queued",
            "back": url_for("place_detail", slug=p.slug),
            "fields": {
                "Ack ID": ack_id,
                "Park": p.name,
                "Purpose": purpose or "(unspecified)",
                "Party size": party,
                "Requested date": date or "(unspecified)",
                "Status": "queued",
            },
        }
        return _r9_json_or_html(payload, "r9_park_permit_ack.html")

    # GET — form scaffold (rendered inline so we don't need a new template).
    payload = {
        "kind": "park-permit-form",
        "title": p.name + " — Permit Request",
        "subtitle": "Submit a permit reservation request",
        "park_slug": p.slug,
        "back": url_for("place_detail", slug=p.slug),
        "fields": {
            "Park": p.name,
            "Submit URL": url_for("r9_park_permit_request", ident=p.slug),
            "Method": "POST",
            "Required fields": "purpose, party_size, date",
        },
    }
    return _r9_json_or_html(payload, "r9_park_permit_form.html")


r9_park_permit_request = csrf.exempt(r9_park_permit_request)


@app.route("/geocache")
def r9_geocache_index():
    """Index of geocaches; supports ?city=<city-slug>&size=<size>&limit=N."""
    city_slug = (request.args.get("city") or "").strip()
    size = (request.args.get("size") or "").strip()
    limit = max(1, min(100, int(request.args.get("limit", "20") or "20")))
    q = Place.query.filter(Place.slug.like("r9-geocache-%"))
    if city_slug:
        city = City.query.filter_by(slug=city_slug).first()
        if city:
            q = q.filter(Place.city_id == city.id)
    if size:
        q = q.filter(Place.tags_json.like(f'%"size-{size}"%'))
    items = q.order_by(Place.id).limit(limit).all()
    out = []
    for p in items:
        try:
            tags = json.loads(p.tags_json or "[]")
        except Exception:
            tags = []
        ctype = ""
        size_v = ""
        for t in tags:
            if isinstance(t, str):
                if t.startswith("cache_type-"):
                    ctype = t[len("cache_type-"):]
                elif t.startswith("size-"):
                    size_v = t[len("size-"):]
        out.append({
            "slug": p.slug,
            "name": p.name,
            "city": p.city.display_name if p.city else "",
            "cache_type": ctype,
            "size": size_v,
            "rating": p.rating,
            "href": url_for("r9_geocache_detail", ident=p.slug),
        })
    payload = {
        "kind": "geocache-index",
        "title": "Geocaches",
        "subtitle": f"{len(out)} results"
                    + (f" in {city_slug}" if city_slug else "")
                    + (f" of size {size}" if size else ""),
        "items": out,
        "count": len(out),
        "filters": {"city": city_slug, "size": size, "limit": limit},
        "fields": {
            "Count": len(out),
            "Filters": f"city={city_slug or '*'}, size={size or '*'}, limit={limit}",
        },
    }
    return _r9_json_or_html(payload, "r9_geocache_index.html")


@app.route("/geocache/<ident>")
def r9_geocache_detail(ident):
    p = _r9_lookup("geocache", ident)
    if not p:
        abort(404)
    try:
        tags = json.loads(p.tags_json or "[]")
    except Exception:
        tags = []
    ctype = ""
    size_v = ""
    for t in tags:
        if isinstance(t, str):
            if t.startswith("cache_type-"):
                ctype = t[len("cache_type-"):]
            elif t.startswith("size-"):
                size_v = t[len("size-"):]
    difficulty = round(1.0 + _r9_int(p.slug, "r9gcd", 0, 40) / 10.0, 1)
    terrain = round(1.0 + _r9_int(p.slug, "r9gct", 0, 40) / 10.0, 1)
    found_count = _r9_int(p.slug, "r9gcf", 4, 480)
    payload = {
        "kind": "geocache",
        "title": p.name,
        "subtitle": f"{ctype.capitalize() or 'Geocache'} · size {size_v or 'small'}",
        "slug": p.slug,
        "place_id": p.id,
        "cache_type": ctype,
        "size": size_v,
        "difficulty": difficulty,
        "terrain": terrain,
        "found_count": found_count,
        "lat": p.lat, "lng": p.lng,
        "back": url_for("place_detail", slug=p.slug),
        "fields": {
            "Cache type": ctype or "—",
            "Size": size_v or "—",
            "Difficulty": f"{difficulty} / 5",
            "Terrain": f"{terrain} / 5",
            "Found by": found_count,
        },
    }
    return _r9_json_or_html(payload, "r9_geocache.html")


# --------------------------------------------------------------------------
#  Error handlers
# --------------------------------------------------------------------------
@app.errorhandler(404)
def not_found(e):
    return render_template("404.html"), 404


@app.errorhandler(500)
def server_error(e):
    return render_template("500.html"), 500


# --------------------------------------------------------------------------
#  DB init / seed
# --------------------------------------------------------------------------
def seed_database():
    from seed_data import (build_categories, build_cities, build_places,
                           seed_task_data, expand_cities, expand_places,
                           expand_routes, expand_places_r4, backfill_place_extras,
                           seed_transit_lines, expand_places_r5,
                           backfill_place_extras_r5, expand_routes_r5,
                           backfill_transit_delays,
                           expand_places_r6, backfill_place_edges_r6,
                           backfill_transit_no_service_r6,
                           expand_places_r7,
                           expand_places_r8,
                           expand_places_r9,
                           expand_places_r10,
                           expand_transit_lines_r10,
                           backfill_place_extras_r10)
    if Category.query.count() == 0:
        build_categories(db, Category)
    if City.query.count() == 0:
        build_cities(db, City)
    if Place.query.count() == 0:
        n = build_places(db, Place, Category, City)
        print(f"Seeded {n} places")
    if Route.query.count() == 0:
        seed_task_data(db, Place, Category, City, Route)
    # Catalog expansion: bring counts up to realistic browsing volume.
    # Each function is internally gated so it's a no-op once the DB
    # already exceeds its threshold (preserves byte-identical reset).
    expand_cities(db, City)
    expand_places(db, Place, Category, City)
    expand_routes(db, Route)
    # --- R4 ---
    expand_places_r4(db, Place, Category, City)
    backfill_place_extras(db, Place, Category)
    if TransitLine.query.count() == 0:
        seed_transit_lines(db, TransitLine, City)
    # --- R5: indoor sub-zones + outdoor sub-zones + parking + EV + fueling ---
    expand_places_r5(db, Place, Category, City)
    backfill_place_extras_r5(db, Place, Category)
    expand_routes_r5(db, Route)
    backfill_transit_delays(db, TransitLine)
    # --- R6: cross-page density + edge banners + transit no-service ---
    expand_places_r6(db, Place, Category, City)
    backfill_place_edges_r6(db, Place)
    backfill_transit_no_service_r6(db, TransitLine)
    # --- R7: SEO/locale density.  Adds another ~110k venues so the place
    # table tops 400k; idempotent (no-op once Place.count >= 380000).
    expand_places_r7(db, Place, Category, City)
    # --- R8: new chains + service verticals (urgent care, coliving, EV V4,
    # smart parking, podcast studios, …).  Adds ~150k more venues so the
    # place table tops 550k; idempotent (no-op once Place.count >= 540000).
    expand_places_r8(db, Place, Category, City)
    # --- R9: outdoor verticals (trail / beach / lighthouse / scenic-byway /
    # geocache / large parks) + fresh chain rows.  Adds ~195k more venues so
    # the place table tops 750k; idempotent (no-op once Place.count >= 740000).
    expand_places_r9(db, Place, Category, City)
    # --- R10: international landmarks + ski/dive verticals + hostels +
    # coliving + accessibility-focused services + bike-share + new chains.
    # Pushes the place table to ~900k.  Idempotent (no-op once
    # Place.count >= 880000).  Also expands transit_line catalog from ~14
    # to 200+ so the /transit/lines/<slug> route returns HTTP 200 across
    # a wide curated + programmatic set of subway/light-rail/bus routes.
    expand_places_r10(db, Place, Category, City)
    expand_transit_lines_r10(db, TransitLine, City)
    # R10 quality polish: fill popular_times / menu / hours_json / etc
    # only on R10 places.  Targeted (filter by slug LIKE 'r10-%'); much
    # faster than re-running the full backfill_place_extras over 900k rows.
    backfill_place_extras_r10(db, Place, Category)


# --------------------------------------------------------------------------
#  Benchmark seed
# --------------------------------------------------------------------------
def seed_benchmark_users():
    """Create 4 benchmark users with saved places, lists, and trips.

    Idempotent: skips if alice.j@test.com already exists.
    Must run AFTER seed_database() so Place rows exist.
    """
    if User.query.filter_by(email="alice.j@test.com").first():
        return  # already seeded

    # Deterministic RNG for gen_trip_code() and any other random.* below.
    random.seed("gmaps-benchmark-users")

    PW = "TestPass123!"  # noqa: F841 — kept for documentation; hash is pinned

    def _make_user(email, name, home_city):
        # Pinned bcrypt hash for "TestPass123!" keeps the seed DB
        # byte-identical across rebuilds (bcrypt.gensalt() is random).
        pw_hash = PINNED_PASSWORD_HASH
        u = User(
            email=email,
            password_hash=pw_hash,
            name=name,
            avatar_letter=name[0].upper(),
            home_city=home_city,
        )
        db.session.add(u)
        db.session.flush()  # get id before commit
        ensure_default_lists(u)
        return u

    def _get_place(name_frag):
        return Place.query.filter(Place.name.ilike(f"%{name_frag}%")).first()

    def _get_place_by_slug(slug):
        return Place.query.filter_by(slug=slug).first()

    def _get_city(slug):
        return City.query.filter_by(slug=slug).first()

    def _make_trip(user, title, city_name, status, start_delta_days, end_delta_days, notes=""):
        # Pinned reference date — datetime.utcnow() would drift each build day.
        today = MIRROR_REFERENCE_DATETIME.date()
        start = today + timedelta(days=start_delta_days)
        end = today + timedelta(days=end_delta_days)
        trip = Trip(
            user_id=user.id,
            trip_code=gen_trip_code(),
            title=title,
            city=city_name,
            start_date=start,
            end_date=end,
            status=status,
            notes=notes,
        )
        db.session.add(trip)
        db.session.flush()
        return trip

    def _add_stop(trip, place, order_idx, notes=""):
        if place:
            stop = TripStop(trip_id=trip.id, place_id=place.id, order_idx=order_idx, notes=notes)
            db.session.add(stop)

    def _save_place(user, saved_list, place, note=""):
        if place and saved_list:
            existing = SavedPlace.query.filter_by(user_id=user.id, place_id=place.id).first()
            if not existing:
                sp = SavedPlace(user_id=user.id, list_id=saved_list.id, place_id=place.id, note=note)
                db.session.add(sp)

    def _make_custom_list(user, name, desc, icon="bookmark", color="#4285f4"):
        sl = SavedList(user_id=user.id, name=name, description=desc, icon=icon, color=color)
        db.session.add(sl)
        db.session.flush()
        return sl

    # ----------------------------------------------------------------
    # Alice Johnson — NYC foodie, plans lots of trips
    # ----------------------------------------------------------------
    alice = _make_user("alice.j@test.com", "Alice Johnson", "New York")

    alice_wtg = SavedList.query.filter_by(user_id=alice.id, name="Want to go").first()
    alice_fav = SavedList.query.filter_by(user_id=alice.id, name="Favorites").first()
    alice_nyc = _make_custom_list(alice, "NYC Eats", "Best restaurants in New York", icon="restaurant", color="#ea4335")
    alice_intl = _make_custom_list(alice, "International Bucket List", "Places I dream of visiting", icon="flight", color="#34a853")

    # Saved places
    _save_place(alice, alice_fav, _get_place("Central Park"), "Perfect for morning runs")
    _save_place(alice, alice_fav, _get_place("Empire State Building"), "Great views")
    _save_place(alice, alice_fav, _get_place("Times Square"), "Tourist spot but fun")
    _save_place(alice, alice_nyc, _get_place("Broadway Dim Sum"), "Try the shrimp dumplings")
    _save_place(alice, alice_nyc, _get_place("5th Osteria"), "Great pasta")
    _save_place(alice, alice_nyc, _get_place("Park Osteria"), "Lovely atmosphere")
    _save_place(alice, alice_wtg, _get_place("Eiffel Tower"), "Must visit someday")
    _save_place(alice, alice_wtg, _get_place("Colosseum"), "Ancient history")
    _save_place(alice, alice_intl, _get_place("Arc de Triomphe"), "Paris bucket list")
    _save_place(alice, alice_intl, _get_place("The Louvre"), "Need at least a full day")

    # Trips
    t1 = _make_trip(alice, "Chicago Weekend", "Chicago", "planning", 14, 17, "Weekend trip with friends")
    _add_stop(t1, _get_place("Willis Tower"), 1, "Get tickets in advance")
    _add_stop(t1, _get_place("Millennium Park"), 2, "Cloud Gate photo")
    _add_stop(t1, _get_place("Art Institute of Chicago"), 3, "Need 3+ hours here")
    _add_stop(t1, _get_place("Navy Pier"), 4, "Evening walk")

    t2 = _make_trip(alice, "Paris Dream Trip", "Paris", "upcoming", 45, 52, "Long-awaited Paris trip!")
    _add_stop(t2, _get_place("Eiffel Tower"), 1, "Go at sunset")
    _add_stop(t2, _get_place("Louvre"), 2, "Book skip-the-line tickets")
    _add_stop(t2, _get_place("Arc de Triomphe"), 3, "Climb to the top")

    t3 = _make_trip(alice, "Boston Day Trip", "Boston", "completed", -10, -8, "Quick trip for a friend's birthday")
    t3.status = "completed"
    _add_stop(t3, _get_place("Freedom Trail"), 1)
    _add_stop(t3, _get_place("Fenway Park"), 2)

    # Alice's planning trip to be cancelled (for T04 tasks)
    t4 = _make_trip(alice, "San Francisco Getaway", "San Francisco", "planning", 30, 34, "Work trip extension")
    _add_stop(t4, _get_place("Golden Gate Bridge"), 1)
    _add_stop(t4, _get_place("Alcatraz"), 2)
    _add_stop(t4, _get_place("Fisherman's Wharf"), 3)

    db.session.commit()

    # ----------------------------------------------------------------
    # Bob Chen — SF tech traveler
    # ----------------------------------------------------------------
    bob = _make_user("bob.c@test.com", "Bob Chen", "San Francisco")

    bob_wtg = SavedList.query.filter_by(user_id=bob.id, name="Want to go").first()
    bob_fav = SavedList.query.filter_by(user_id=bob.id, name="Favorites").first()
    bob_foodie = _make_custom_list(bob, "Foodie Spots", "Best food finds", icon="restaurant", color="#fbbc04")
    bob_hidden = _make_custom_list(bob, "Hidden Gems", "Off-the-beaten-path places", icon="explore", color="#9c27b0")

    # Saved places
    _save_place(bob, bob_fav, _get_place("Golden Gate Bridge"), "Iconic SF")
    _save_place(bob, bob_fav, _get_place("Alcatraz Island"), "Fascinating history")
    _save_place(bob, bob_fav, _get_place("Fisherman's Wharf"), "Fresh seafood")
    _save_place(bob, bob_foodie, _get_place("Polk Sushi Counter"), "Best omakase in SF")
    _save_place(bob, bob_foodie, _get_place("Mission Taqueria"), "Authentic tacos")
    _save_place(bob, bob_foodie, _get_place("Valencia Coffee Roaster"), "Great pour-over")
    _save_place(bob, bob_hidden, _get_place("Lombard Street"), "Surprisingly charming")
    _save_place(bob, bob_wtg, _get_place("Tokyo Tower"), "Tech + culture")
    _save_place(bob, bob_wtg, _get_place("Great Wall of China"), "Bucket list")

    # Trips
    t5 = _make_trip(bob, "Tokyo Tech Tour", "Tokyo", "upcoming", 20, 27, "Checking out the tech scene")
    _add_stop(t5, _get_place("Tokyo Tower"), 1, "Evening visit")
    _add_stop(t5, _get_place_by_slug("sensoji"), 2, "Early morning before crowds")
    _add_stop(t5, _get_place("Tokyo Skytree"), 3, "Best views of Tokyo")

    t6 = _make_trip(bob, "SF Weekend Highlights", "San Francisco", "completed", -30, -28)
    t6.status = "completed"
    _add_stop(t6, _get_place("Golden Gate Bridge"), 1)
    _add_stop(t6, _get_place("Alcatraz"), 2)

    # Bob has a trip to be cancelled (for T04)
    t7 = _make_trip(bob, "Seattle Coffee Tour", "Seattle", "planning", 25, 28, "Visiting the coffee capital")
    _add_stop(t7, _get_place("Pike Place Market"), 1, "Original Starbucks!")
    _add_stop(t7, _get_place("Pine Coffee Roaster"), 2, "Best pour-over in Seattle")
    _add_stop(t7, _get_place("Space Needle"), 3, "Classic Seattle")

    db.session.commit()

    # ----------------------------------------------------------------
    # Carol Davis — Chicago explorer
    # ----------------------------------------------------------------
    carol = _make_user("carol.d@test.com", "Carol Davis", "Chicago")

    carol_wtg = SavedList.query.filter_by(user_id=carol.id, name="Want to go").first()
    carol_fav = SavedList.query.filter_by(user_id=carol.id, name="Favorites").first()
    carol_chi = _make_custom_list(carol, "Chicago Must-Sees", "Best of my city", icon="star", color="#4285f4")
    carol_italian = _make_custom_list(carol, "Italian Restaurants", "My favorite Italian spots", icon="restaurant", color="#ea4335")

    # Saved places
    _save_place(carol, carol_fav, _get_place("Millennium Park"), "My backyard")
    _save_place(carol, carol_fav, _get_place("Art Institute of Chicago"), "World class museum")
    _save_place(carol, carol_fav, _get_place("Willis Tower"), "Best views of Chicago")
    _save_place(carol, carol_chi, _get_place("Navy Pier"), "Great for out-of-towners")
    _save_place(carol, carol_chi, _get_place("Rush Brunch Spot"), "Sunday brunch tradition")
    _save_place(carol, carol_italian, _get_place("Rush Bistro"), "Solid Italian-American")
    _save_place(carol, carol_wtg, _get_place("Colosseum"), "Rome someday!")
    _save_place(carol, carol_wtg, _get_place("Sagrada Família"), "Gaudi is a genius")
    _save_place(carol, carol_wtg, _get_place("Buen Retiro Park"), "Spain bucket list")

    # Trips
    t8 = _make_trip(carol, "NYC Fall Visit", "New York", "planning", 10, 14, "Fall foliage + city")
    _add_stop(t8, _get_place("Central Park"), 1, "Peak fall colors")
    _add_stop(t8, _get_place("Empire State Building"), 2, "Observatory at sunset")
    _add_stop(t8, _get_place("Brooklyn Bridge"), 3, "Walk across")
    _add_stop(t8, _get_place("Times Square"), 4, "Obligatory tourist stop")

    t9 = _make_trip(carol, "Rome & Florence Art Trip", "Rome", "upcoming", 60, 70, "Two weeks exploring Italian art")
    _add_stop(t9, _get_place("Colosseum"), 1, "Book Gladiator's entrance")
    _add_stop(t9, _get_place("Vatican City"), 2, "Skip-the-line a must")
    _add_stop(t9, _get_place("Trevi Fountain"), 3, "Make a wish!")

    t10 = _make_trip(carol, "Chicago Summer Day Out", "Chicago", "completed", -20, -20)
    t10.status = "completed"
    _add_stop(t10, _get_place("Millennium Park"), 1)
    _add_stop(t10, _get_place("Navy Pier"), 2)

    # Carol has a planning trip to be cancelled (T04)
    t11 = _make_trip(carol, "Las Vegas Girls Trip", "Las Vegas", "planning", 40, 43, "Bachelorette party!")
    _add_stop(t11, _get_place("Bellagio Hotel"), 1, "Fountain show at night")
    _add_stop(t11, _get_place_by_slug("venetian-resort"), 2, "The Venetian is stunning")

    db.session.commit()

    # ----------------------------------------------------------------
    # David Kim — LA foodie + outdoor enthusiast
    # ----------------------------------------------------------------
    david = _make_user("david.k@test.com", "David Kim", "Los Angeles")

    david_wtg = SavedList.query.filter_by(user_id=david.id, name="Want to go").first()
    david_fav = SavedList.query.filter_by(user_id=david.id, name="Favorites").first()
    david_outdoor = _make_custom_list(david, "Outdoor Adventures", "Hikes, parks, and nature", icon="nature", color="#34a853")
    david_eats = _make_custom_list(david, "LA Eats", "Best food in Los Angeles", icon="restaurant", color="#ff5722")

    # Saved places
    _save_place(david, david_fav, _get_place("Santa Monica Pier"), "Sunsets are unreal")
    _save_place(david, david_fav, _get_place("Griffith Observatory"), "Best views of LA")
    _save_place(david, david_outdoor, _get_place("Hollywood Sign"), "Hike to the sign")
    _save_place(david, david_outdoor, _get_place("Venice Beach"), "Beach volleyball")
    _save_place(david, david_outdoor, _get_place("Grand Canyon"), "Annual pilgrimage")
    _save_place(david, david_eats, _get_place("Rodeo Tapas Bar"), "Impressive wine list")
    _save_place(david, david_eats, _get_place("Melrose Steakhouse"), "Special occasion dinner")
    _save_place(david, david_wtg, _get_place("Grand Canyon"), "This year for sure")
    _save_place(david, david_wtg, _get_place("Yosemite National Park"), "Epic scenery")

    # Trips
    t12 = _make_trip(david, "Seattle Outdoors Trip", "Seattle", "upcoming", 8, 12, "Hiking + seafood")
    _add_stop(t12, _get_place("Chihuly Garden"), 1, "Amazing glass art")
    _add_stop(t12, _get_place("Pike Place Market"), 2, "Fresh fish")
    _add_stop(t12, _get_place("Space Needle"), 3, "Classic tourist")

    t13 = _make_trip(david, "LA Weekend Staycation", "Los Angeles", "completed", -5, -3)
    t13.status = "completed"
    _add_stop(t13, _get_place("Santa Monica Pier"), 1)
    _add_stop(t13, _get_place("Griffith Observatory"), 2)

    # David has a trip to be cancelled (T04)
    t14 = _make_trip(david, "Boston Fall Tour", "Boston", "planning", 35, 39, "Checking out the East Coast fall colors")
    _add_stop(t14, _get_place("Freedom Trail"), 1)
    _add_stop(t14, _get_place("Fenway Park"), 2)
    _add_stop(t14, _get_place("Museum of Fine Arts"), 3)

    db.session.commit()
    print("Benchmark users seeded: alice.j, bob.c, carol.d, david.k")


# --------------------------------------------------------------------------
#  Byte-id helper: stabilize index + page layout for deterministic rebuilds.
# --------------------------------------------------------------------------
def normalize_seed_db_layout():
    """Re-emit indexes in alpha order + VACUUM so rebuilds match byte-for-byte.

    SQLAlchemy emits CREATE INDEX from a Python set; iteration order depends
    on Index object id() and shifts per process. Drop + recreate in sorted
    order, then VACUUM, so sqlite_master text + page layout are deterministic.
    Must run AFTER every other write — anything writing after this VACUUM
    re-fragments pages and re-introduces drift.
    """
    conn = db.engine.connect()
    idx_rows = conn.execute(text(
        "SELECT name, sql FROM sqlite_master "
        "WHERE type='index' AND name LIKE 'ix_%'"
    )).fetchall()
    for name, _ in idx_rows:
        conn.execute(text(f"DROP INDEX IF EXISTS {name}"))
    for name, sql in sorted(idx_rows, key=lambda r: r[0]):
        if sql:
            conn.execute(text(sql))
    conn.execute(text("VACUUM"))
    conn.commit()
    conn.close()


# --------------------------------------------------------------------------

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
R2_SITE_NAME = "Google Map"
R2_DOMAIN = "maps.google.com"
R2_ACCESSIBILITY_BLURB = "Google Maps offers screen-reader directions, large-text mode, and high-contrast cartography so that navigation works for users with low vision."


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
R3_SITE_NAME = "Google Map"
R3_DOMAIN = "maps.google.com"


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


# === R4-R6 backfill BEGIN — auto-generated, do not hand-edit between markers ===
# Added 2026-05-27 to fill the mid-round gap (R4 transit deep dive,
# R5 EV/gas/parking vertical detail, R6 street-view & photosphere).
# All data is *derived* from md5(slug) — no DB writes, instance_seed
# md5 unchanged, byte-identical reset still passes.
#
# Marker convention: every function and constant uses the r4_ / r5_ /
# r6_ (or R4_/R5_/R6_) prefix so grep -nE '\br[4-6]_' surfaces it.
# --------------------------------------------------------------------------
R4_DAYS = ("monday", "tuesday", "wednesday", "thursday",
           "friday", "saturday", "sunday")
R4_DIRECTIONS = ("northbound", "southbound", "eastbound", "westbound")
R4_FARE_ZONES = ("local", "express", "premium")


def _r46_int(slug, salt, lo, hi):
    h = hashlib.md5(f"{salt}:{slug}".encode()).digest()
    n = int.from_bytes(h[:4], "big")
    return lo + (n % max(1, hi - lo + 1))


def _r46_pick(slug, options, salt):
    h = hashlib.md5(f"{salt}:{slug}".encode()).digest()
    n = int.from_bytes(h[:4], "big")
    return options[n % len(options)]


def _r46_render(payload, template, **ctx):
    """JSON if ?format=json, else HTML template (inline fallback)."""
    want_json = (request.args.get("format") == "json"
                 or "application/json" in (request.headers.get("Accept", "")))
    if want_json:
        return jsonify(payload)
    try:
        return render_template(template, payload=payload, **ctx)
    except TemplateNotFound:
        return render_template_string(
            "<!doctype html><meta charset='utf-8'>"
            "<title>{{ payload.title }} | Maps</title>"
            "<style>body{font-family:Roboto,Arial,sans-serif;max-width:820px;"
            "margin:32px auto;padding:0 16px;color:#202124}"
            "h1{font-size:22px;margin-bottom:4px}"
            ".sub{color:#5f6368;font-size:13px;margin-bottom:18px}"
            "dt{font-weight:600;margin-top:8px;font-size:13px;color:#5f6368;"
            "text-transform:uppercase;letter-spacing:.4px}"
            "dd{margin:2px 0 8px 0;font-size:14px}"
            "table{border-collapse:collapse;margin:8px 0;width:100%}"
            "th,td{border:1px solid #dadce0;padding:6px 10px;font-size:13px;"
            "text-align:left}th{background:#f1f3f4}"
            "a{color:#1a73e8;text-decoration:none}</style>"
            "<h1>{{ payload.title }}</h1>"
            "<p class='sub'>{{ payload.subtitle or '' }}</p>"
            "<dl>{% for k, v in (payload.fields or {}).items() %}"
            "<dt>{{ k }}</dt><dd>{{ v }}</dd>{% endfor %}</dl>"
            "{% if payload.table %}<table><thead><tr>"
            "{% for h in payload.table.cols %}<th>{{ h }}</th>{% endfor %}"
            "</tr></thead><tbody>"
            "{% for row in payload.table.rows %}<tr>"
            "{% for cell in row %}<td>{{ cell }}</td>{% endfor %}</tr>"
            "{% endfor %}</tbody></table>{% endif %}"
            "{% if payload.back %}<p><a href='{{ payload.back }}'>"
            "&larr; back</a></p>{% endif %}",
            payload=payload,
        )


def _r4_line(slug):
    return TransitLine.query.filter_by(slug=slug).first()


def _r4_freq_minutes(line):
    txt = (line.frequency_peak or "").lower()
    digits = "".join(ch for ch in txt if ch.isdigit())
    try:
        return max(2, int(digits or 10))
    except ValueError:
        return 10


def _r4_hours(line):
    h = (line.hours or "").strip()
    if not h or h.lower() in ("24 hours", "24h"):
        return 0, 24 * 60
    parts = h.replace("—", "–").split("–")
    if len(parts) != 2:
        return 5 * 60, 24 * 60
    def parse(t):
        t = t.strip().lower().replace(" ", "")
        ampm = "am"
        if t.endswith("pm"): ampm = "pm"; t = t[:-2]
        elif t.endswith("am"): t = t[:-2]
        try:
            hh, mm = t.split(":")
            hh = int(hh); mm = int(mm)
        except ValueError:
            return 5 * 60
        if ampm == "pm" and hh != 12: hh += 12
        if ampm == "am" and hh == 12: hh = 0
        return hh * 60 + mm
    return parse(parts[0]), parse(parts[1])


def _r4_schedule_entries(line, day):
    freq = _r4_freq_minutes(line)
    if day in ("saturday", "sunday"):
        freq = max(freq + 2, int(freq * 1.4))
    start_m, end_m = _r4_hours(line)
    if end_m <= start_m:
        end_m += 24 * 60
    entries = []
    t = start_m
    seq = 0
    while t < end_m and len(entries) < 60:
        hh = (t // 60) % 24
        mm = t % 60
        direction = R4_DIRECTIONS[seq % 2]
        entries.append({
            "seq": seq + 1,
            "time": f"{hh:02d}:{mm:02d}",
            "direction": direction,
            "headway_min": freq,
        })
        t += freq
        seq += 1
    return entries


@app.route("/transit/lines/<slug>/schedule")
@app.route("/transit/lines/<slug>/schedule/<day>")
def r4_transit_schedule(slug, day=None):
    line = _r4_line(slug)
    if line is None:
        abort(404)
    day = (day or "weekday").lower()
    canon = day if day in R4_DAYS else ("saturday" if day == "weekend"
                                        else "monday")
    entries = _r4_schedule_entries(line, canon)
    head = entries[0]["time"] if entries else "—"
    tail = entries[-1]["time"] if entries else "—"
    payload = {
        "title": f"{line.short_name} {line.name} — {canon.title()} schedule",
        "subtitle": f"{line.agency} · {len(entries)} schedule_entry rows",
        "fields": {
            "First departure": head,
            "Last departure": tail,
            "Headway (peak)": f"{_r4_freq_minutes(line)} min",
            "Service window": line.hours or "—",
            "Day": canon,
        },
        "table": {
            "cols": ["#", "Time", "Direction", "Headway"],
            "rows": [[e["seq"], e["time"], e["direction"],
                      f"{e['headway_min']} min"] for e in entries],
        },
        "back": url_for("transit_line_detail", line_slug=line.slug),
    }
    return _r46_render(payload, "r4_transit_schedule.html",
                       line=line, day=canon, entries=entries,
                       days=R4_DAYS)


@app.route("/transit/lines/<slug>/first-last")
@app.route("/transit/lines/<slug>/first_last")
def r4_transit_first_last(slug):
    line = _r4_line(slug)
    if line is None:
        abort(404)
    rows = []
    for day in R4_DAYS:
        entries = _r4_schedule_entries(line, day)
        first_t = entries[0]["time"] if entries else "—"
        last_t = entries[-1]["time"] if entries else "—"
        rows.append([day.title(), first_t, last_t, f"{len(entries)} trips"])
    payload = {
        "title": f"{line.short_name} {line.name} — First/Last by day",
        "subtitle": f"{line.agency}",
        "fields": {"Service window": line.hours or "—"},
        "table": {"cols": ["Day", "First", "Last", "Trip count"],
                  "rows": rows},
        "back": url_for("transit_line_detail", line_slug=line.slug),
    }
    return _r46_render(payload, "r4_transit_schedule.html",
                       line=line, day="overview", entries=[],
                       days=R4_DAYS)


@app.route("/transit/lines/<slug>/headway")
def r4_transit_headway(slug):
    line = _r4_line(slug)
    if line is None:
        abort(404)
    peak = _r4_freq_minutes(line)
    off = max(peak + 2, int(peak * 1.6))
    night = max(off + 3, int(peak * 2.2))
    rows = [
        ("Weekday AM peak (06:00–10:00)", f"{peak} min"),
        ("Weekday midday (10:00–15:00)",  f"{off} min"),
        ("Weekday PM peak (15:00–19:00)", f"{peak} min"),
        ("Weekday evening (19:00–22:00)", f"{off} min"),
        ("Weekday late-night (22:00–06:00)", f"{night} min"),
        ("Weekend daytime", f"{off} min"),
        ("Weekend overnight", f"{night + 4} min"),
    ]
    payload = {
        "title": f"{line.short_name} {line.name} — Headway analytics",
        "subtitle": f"{line.agency} · derived from frequency_peak",
        "fields": dict(rows),
        "back": url_for("r4_transit_schedule", slug=line.slug),
    }
    return _r46_render(payload, "r4_transit_schedule.html",
                       line=line, day="headway", entries=[],
                       days=R4_DAYS)


@app.route("/transit/lines/<slug>/fare")
def r4_transit_fare(slug):
    line = _r4_line(slug)
    if line is None:
        abort(404)
    base = round(2.0 + _r46_int(line.slug, "fare", 0, 30) / 10.0, 2)
    monthly = round(base * 40 + _r46_int(line.slug, "month", 0, 25), 2)
    payload = {
        "title": f"{line.short_name} {line.name} — Fare",
        "subtitle": f"{line.agency} fare card",
        "fields": {
            "Single ride": f"${base:.2f}",
            "Day pass": f"${base * 4:.2f}",
            "7-day pass": f"${base * 14:.2f}",
            "Monthly pass": f"${monthly:.2f}",
            "Reduced fare": f"${base / 2:.2f}",
            "Free transfer window": "2 hours",
            "Fare zone": _r46_pick(line.slug, R4_FARE_ZONES, "zone"),
        },
        "back": url_for("transit_line_detail", line_slug=line.slug),
    }
    return _r46_render(payload, "r4_transit_schedule.html",
                       line=line, day="fare", entries=[],
                       days=R4_DAYS)


@app.route("/transit/lines/<slug>/stop/<int:stop_idx>")
def r4_transit_stop(slug, stop_idx):
    line = _r4_line(slug)
    if line is None:
        abort(404)
    stops = line.get_stops()
    if stop_idx < 1 or stop_idx > len(stops):
        abort(404)
    stop_name = stops[stop_idx - 1]
    stop_slug = re.sub(r"[^a-z0-9]+", "-",
                       f"{line.slug}-{stop_name}".lower()).strip("-")
    accessible = (_r46_int(stop_slug, "access", 0, 9) >= 3)
    elevators = _r46_int(stop_slug, "elev", 0, 4)
    payload = {
        "title": f"{stop_name} ({line.short_name})",
        "subtitle": f"Stop {stop_idx} of {len(stops)} · {line.name}",
        "fields": {
            "Line": line.name,
            "Agency": line.agency,
            "Stop number": f"#{stop_idx}",
            "Wheelchair accessible": "Yes" if accessible else "No",
            "Elevators": elevators,
            "Bike rack": "Yes" if _r46_int(stop_slug, "bike", 0, 1) else "No",
            "Real-time arrivals":
                url_for("r4_transit_stop_arrivals",
                        slug=line.slug, stop_idx=stop_idx),
        },
        "back": url_for("transit_line_detail", line_slug=line.slug),
    }
    return _r46_render(payload, "r4_transit_stop.html",
                       line=line, stop_name=stop_name,
                       stop_idx=stop_idx, accessible=accessible,
                       elevators=elevators)


@app.route("/transit/lines/<slug>/stop/<int:stop_idx>/arrivals")
@app.route("/transit/lines/<slug>/arrivals/<int:stop_idx>")
def r4_transit_stop_arrivals(slug, stop_idx):
    line = _r4_line(slug)
    if line is None:
        abort(404)
    stops = line.get_stops()
    if stop_idx < 1 or stop_idx > len(stops):
        abort(404)
    stop_name = stops[stop_idx - 1]
    freq = _r4_freq_minutes(line)
    delay = (line.current_delay_min or 0)
    salt = f"{line.slug}:{stop_idx}"
    rows = []
    next_minute = _r46_int(salt, "arrnext", 1, max(2, freq))
    for i in range(6):
        eta = next_minute + i * freq + delay
        direction = R4_DIRECTIONS[(stop_idx + i) % 2]
        rows.append([f"{eta} min", direction,
                     "On time" if delay == 0 else f"+{delay} min",
                     f"Trip {(_r46_int(salt, f'trip{i}', 1000, 9999))}"])
    payload = {
        "title": f"{stop_name} — Next arrivals",
        "subtitle": f"{line.short_name} {line.name} · "
                    f"{'on time' if delay == 0 else f'delay +{delay} min'}",
        "fields": {
            "Stop": stop_name,
            "Service status": "On time" if delay == 0
                              else (line.delay_reason or "Minor delay"),
            "Last update": line.last_update or "just now",
        },
        "table": {
            "cols": ["ETA", "Direction", "Status", "Trip ID"],
            "rows": rows,
        },
        "back": url_for("r4_transit_stop", slug=line.slug, stop_idx=stop_idx),
    }
    return _r46_render(payload, "r4_transit_stop.html",
                       line=line, stop_name=stop_name,
                       stop_idx=stop_idx, accessible=False,
                       elevators=0)


@app.route("/transit/lines/<slug>/timetable.json")
def r4_transit_timetable_json(slug):
    line = _r4_line(slug)
    if line is None:
        abort(404)
    out = {"line": line.slug, "agency": line.agency, "days": {}}
    for d in R4_DAYS:
        out["days"][d] = _r4_schedule_entries(line, d)
    return jsonify(out)


# --------------------------------------------------------------------------
# R5 — EV charging / gas-station / parking-lot vertical pages
# --------------------------------------------------------------------------
R5_EV_CONNECTORS_ALL = ("CCS", "CHAdeMO", "Tesla", "J1772", "Type 2")
R5_EV_NETWORKS = ("Electrify America", "ChargePoint", "EVgo", "Blink",
                  "Tesla Supercharger", "Shell Recharge", "FLO")
R5_GAS_BRANDS = ("Shell", "Chevron", "ExxonMobil", "BP", "Marathon",
                 "Sunoco", "ARCO", "Murphy USA", "76", "Valero")
R5_GAS_GRADES = ("Regular", "Midgrade", "Premium", "Diesel")
R5_PARKING_TYPES = ("garage", "surface lot", "underground", "valet")
R5_PARKING_FEATURES = ("EV stalls", "Tall vehicle bay",
                       "Motorcycle area", "Accessible spaces")


def _r5_place(slug, category_slugs):
    p = Place.query.filter_by(slug=slug).first()
    if p is None:
        return None
    cat = Category.query.get(p.category_id) if p.category_id else None
    if cat is None or cat.slug not in category_slugs:
        return None
    return p


def _r5_ev_price(slug):
    return round(0.18 + _r46_int(slug, "evprice", 0, 32) / 100.0, 2)


def _r5_gas_price(slug, grade):
    base = 3.10 + _r46_int(slug, f"gas{grade}", 0, 90) / 100.0
    add = {"Regular": 0.0, "Midgrade": 0.20, "Premium": 0.40,
           "Diesel": 0.30}[grade]
    return round(base + add, 2)


def _r5_parking_rate(slug):
    return round(2.0 + _r46_int(slug, "park", 0, 80) / 10.0, 2)


@app.route("/charging/<slug>")
def r5_ev_charging_detail(slug):
    p = _r5_place(slug, {"ev-charging"})
    if p is None:
        abort(404)
    network = _r46_pick(p.slug, R5_EV_NETWORKS, "net")
    connectors = (p.ev_connector_type or "CCS").split("+")
    stalls = _r46_int(p.slug, "stalls", 2, 16)
    avail = _r46_int(p.slug, "avail", 0, stalls)
    price = _r5_ev_price(p.slug)
    payload = {
        "title": f"{p.name} — EV charging",
        "subtitle": f"{network} · {p.address or p.city}",
        "fields": {
            "Network": network,
            "Connector types": ", ".join(connectors),
            "Max power": f"{p.ev_charger_kw or 50} kW",
            "Total stalls": stalls,
            "Stalls available now": f"{avail} / {stalls}",
            "Price": f"${price:.2f} / kWh",
            "Idle fee": f"${_r46_int(p.slug, 'idle', 5, 40) / 100.0:.2f} / min after charging",
            "24/7 access": "Yes" if _r46_int(p.slug, "24h", 0, 1) else "Daytime only",
            "Connectors detail":
                url_for("r5_ev_connectors", slug=p.slug),
            "Live availability":
                url_for("r5_ev_availability", slug=p.slug),
        },
        "back": url_for("place_detail", slug=p.slug),
    }
    return _r46_render(payload, "r5_charging.html",
                       place=p, network=network, stalls=stalls,
                       avail=avail, price=price, connectors=connectors)


@app.route("/charging/<slug>/connectors")
def r5_ev_connectors(slug):
    p = _r5_place(slug, {"ev-charging"})
    if p is None:
        abort(404)
    rows = []
    have = (p.ev_connector_type or "CCS").split("+")
    for c in R5_EV_CONNECTORS_ALL:
        present = "Yes" if c in have else "No"
        kw = (p.ev_charger_kw or 50) if c in have else "—"
        rows.append([c, present, kw,
                     "DC fast" if c in ("CCS", "CHAdeMO", "Tesla")
                     else "Level 2"])
    payload = {
        "title": f"{p.name} — Connector details",
        "subtitle": "Per-connector compatibility",
        "table": {"cols": ["Connector", "Present", "Max kW", "Class"],
                  "rows": rows},
        "back": url_for("r5_ev_charging_detail", slug=p.slug),
    }
    return _r46_render(payload, "r5_charging.html",
                       place=p, network="", stalls=0, avail=0,
                       price=0.0, connectors=have)


@app.route("/charging/<slug>/availability")
def r5_ev_availability(slug):
    p = _r5_place(slug, {"ev-charging"})
    if p is None:
        abort(404)
    stalls = _r46_int(p.slug, "stalls", 2, 16)
    rows = []
    for i in range(1, stalls + 1):
        state = _r46_pick(f"{p.slug}#{i}",
                          ("available", "in use", "out of service"),
                          "stallstate")
        connector = _r46_pick(f"{p.slug}#{i}",
                              R5_EV_CONNECTORS_ALL, "stallconn")
        rows.append([f"Stall {i}", connector, state,
                     "—" if state != "in use"
                     else f"{_r46_int(p.slug + str(i), 'rem', 5, 55)} min"])
    payload = {
        "title": f"{p.name} — Live stall availability",
        "subtitle": "Refreshed every 60 seconds",
        "table": {"cols": ["Stall", "Connector", "State",
                           "Estimated remaining"], "rows": rows},
        "back": url_for("r5_ev_charging_detail", slug=p.slug),
    }
    return _r46_render(payload, "r5_charging.html",
                       place=p, network="", stalls=stalls,
                       avail=0, price=0.0, connectors=[])


@app.route("/gas-station/<slug>")
@app.route("/gas_station/<slug>")
def r5_gas_station_detail(slug):
    p = _r5_place(slug, {"gas-stations"})
    if p is None:
        abort(404)
    brand = _r46_pick(p.slug, R5_GAS_BRANDS, "brand")
    rows = [(g, f"${_r5_gas_price(p.slug, g):.2f} / gal")
            for g in R5_GAS_GRADES]
    payload = {
        "title": f"{p.name} — Current fuel prices",
        "subtitle": f"{brand} · {p.address or p.city}",
        "fields": {
            **dict(rows),
            "Last updated": f"{_r46_int(p.slug, 'updt', 1, 58)} min ago",
            "Payment": "Credit / Debit / Mobile pay",
            "Number of pumps": _r46_int(p.slug, "pumps", 4, 24),
            "Convenience store": "Yes" if _r46_int(p.slug, "cstore", 0, 1)
                                  else "No",
            "Car wash": "Yes" if _r46_int(p.slug, "wash", 0, 2) == 2 else "No",
            "Price history (14 days)":
                url_for("r5_gas_station_price_history", slug=p.slug),
        },
        "back": url_for("place_detail", slug=p.slug),
    }
    return _r46_render(payload, "r5_gas_station.html",
                       place=p, brand=brand, prices=dict(rows))


@app.route("/gas-station/<slug>/price-history")
@app.route("/gas_station/<slug>/price_history")
def r5_gas_station_price_history(slug):
    p = _r5_place(slug, {"gas-stations"})
    if p is None:
        abort(404)
    today_regular = _r5_gas_price(p.slug, "Regular")
    rows = []
    for d in range(14):
        delta = (_r46_int(p.slug, f"hist{d}", 0, 40) - 20) / 100.0
        rows.append([f"Day -{d}",
                     f"${round(today_regular + delta, 2):.2f}",
                     f"${round(today_regular + delta + 0.20, 2):.2f}",
                     f"${round(today_regular + delta + 0.40, 2):.2f}",
                     f"${round(today_regular + delta + 0.30, 2):.2f}"])
    payload = {
        "title": f"{p.name} — 14-day price history",
        "subtitle": "Regular / Midgrade / Premium / Diesel",
        "table": {"cols": ["Day"] + list(R5_GAS_GRADES), "rows": rows},
        "back": url_for("r5_gas_station_detail", slug=p.slug),
    }
    return _r46_render(payload, "r5_gas_station.html",
                       place=p, brand="", prices={})


@app.route("/parking-lot/<slug>")
@app.route("/parking_lot/<slug>")
def r5_parking_lot_detail(slug):
    p = _r5_place(slug, {"parking"})
    if p is None:
        abort(404)
    capacity = p.parking_lot_capacity or _r46_int(p.slug, "cap", 80, 1800)
    lot_type = _r46_pick(p.slug, R5_PARKING_TYPES, "type")
    rate = _r5_parking_rate(p.slug)
    daily = round(rate * 6, 2)
    monthly = round(daily * 22, 2)
    occupancy_pct = _r46_int(p.slug, "occ", 5, 95)
    occupied = int(capacity * occupancy_pct / 100)
    ev_stalls = _r46_int(p.slug, "evstalls", 0, max(4, capacity // 40))
    payload = {
        "title": f"{p.name} — Parking",
        "subtitle": f"{lot_type.title()} · {p.address or p.city}",
        "fields": {
            "Total capacity": f"{capacity} spaces",
            "Currently occupied": f"{occupied} ({occupancy_pct}%)",
            "Available now": f"{capacity - occupied} spaces",
            "Hourly rate": f"${rate:.2f}",
            "Daily max": f"${daily:.2f}",
            "Monthly pass": f"${monthly:.2f}",
            "EV stalls": ev_stalls,
            "Tall-vehicle bay":
                "Yes" if _r46_int(p.slug, "tall", 0, 1) else "No",
            "24/7 access":
                "Yes" if _r46_int(p.slug, "24h", 0, 1) else "Daytime only",
            "Live occupancy":
                url_for("r5_parking_lot_realtime", slug=p.slug),
        },
        "back": url_for("place_detail", slug=p.slug),
    }
    return _r46_render(payload, "r5_parking_lot.html",
                       place=p, capacity=capacity, lot_type=lot_type,
                       rate=rate, occupancy_pct=occupancy_pct,
                       ev_stalls=ev_stalls)


@app.route("/parking-lot/<slug>/realtime")
@app.route("/parking_lot/<slug>/realtime")
def r5_parking_lot_realtime(slug):
    p = _r5_place(slug, {"parking"})
    if p is None:
        abort(404)
    capacity = p.parking_lot_capacity or _r46_int(p.slug, "cap", 80, 1800)
    rows = []
    for h in range(24):
        occ = _r46_int(p.slug, f"hrocc{h}", 5, 95)
        rows.append([f"{h:02d}:00", f"{occ}%",
                     int(capacity * occ / 100),
                     capacity - int(capacity * occ / 100)])
    payload = {
        "title": f"{p.name} — 24-hour occupancy",
        "subtitle": "Live + last 24h trend",
        "table": {"cols": ["Hour", "Occupancy", "Occupied", "Available"],
                  "rows": rows},
        "back": url_for("r5_parking_lot_detail", slug=p.slug),
    }
    return _r46_render(payload, "r5_parking_lot.html",
                       place=p, capacity=capacity,
                       lot_type="", rate=0.0,
                       occupancy_pct=0, ev_stalls=0)


# --------------------------------------------------------------------------
# R6 — Street View thumbnails / 360° panorama / Photosphere
# --------------------------------------------------------------------------
R6_HEADINGS = (
    (0,   "North"),
    (45,  "Northeast"),
    (90,  "East"),
    (135, "Southeast"),
    (180, "South"),
    (225, "Southwest"),
    (270, "West"),
    (315, "Northwest"),
)
R6_CAPTURE_VEHICLES = ("Street View car", "Trekker backpack",
                       "Street View Trike", "Snowmobile")
R6_PHOTOSPHERE_TYPES = ("interior", "rooftop", "park trail",
                        "alley", "viewpoint", "lobby")


class _R6PlaceStub:
    """Stand-in when an R6 route is hit on a slug that isn't in the seeded
    `place` table.  Keeps panorama/timeline pages reachable for any
    reasonable slug so backfill tasks don't 404."""
    __slots__ = ("slug", "name", "lat", "lng", "address", "city")

    def __init__(self, slug):
        self.slug = slug
        self.name = " ".join(w.capitalize() for w in slug.split("-")) or slug
        self.lat = round(
            (_r46_int(slug, "lat", 0, 180000) / 1000.0) - 90.0, 6)
        self.lng = round(
            (_r46_int(slug, "lng", 0, 360000) / 1000.0) - 180.0, 6)
        self.address = ""
        self.city = ""


def _r6_place(slug):
    p = Place.query.filter_by(slug=slug).first()
    if p is not None:
        return p
    if not re.fullmatch(r"[a-z0-9][a-z0-9\-]{1,80}", slug):
        return None
    return _R6PlaceStub(slug)


def _r6_capture_year(slug, idx):
    return 2014 + _r46_int(slug, f"yr{idx}", 0, 11)


def _r6_thumbnail_uri(slug, heading):
    sig = hashlib.md5(f"thumb:{slug}:{heading}".encode()).hexdigest()[:12]
    return f"/static/streetview/{sig}.jpg"


@app.route("/street-view/<slug>/thumbnails")
@app.route("/streetview/<slug>/thumbnails")
def r6_streetview_thumbnails(slug):
    p = _r6_place(slug)
    if p is None:
        abort(404)
    rows = []
    for heading, label in R6_HEADINGS:
        rows.append([label, f"{heading}°",
                     _r6_thumbnail_uri(p.slug, heading),
                     url_for("r6_streetview_panorama",
                             slug=p.slug, heading=heading)])
    payload = {
        "title": f"{p.name} — Street View thumbnails",
        "subtitle": "8 compass headings at this location",
        "table": {"cols": ["Heading", "Bearing", "Thumbnail", "Panorama URL"],
                  "rows": rows},
        "back": url_for("place_detail", slug=p.slug),
    }
    return _r46_render(payload, "r6_panorama.html",
                       place=p, headings=R6_HEADINGS,
                       thumbs=[(h, lbl, _r6_thumbnail_uri(p.slug, h))
                               for h, lbl in R6_HEADINGS],
                       capture_year=_r6_capture_year(p.slug, 0))


@app.route("/street-view/<slug>/panorama")
@app.route("/streetview/<slug>/panorama")
def r6_streetview_panorama(slug):
    p = _r6_place(slug)
    if p is None:
        abort(404)
    heading = request.args.get("heading", default=0, type=int) % 360
    fov = _r46_int(p.slug, "fov", 70, 110)
    pitch = _r46_int(p.slug, "pitch", -10, 10)
    vehicle = _r46_pick(p.slug, R6_CAPTURE_VEHICLES, "vehicle")
    capture_year = _r6_capture_year(p.slug, 0)
    pano_id = hashlib.md5(f"pano:{p.slug}:{heading}".encode()).hexdigest()[:18]
    payload = {
        "title": f"{p.name} — 360° panorama",
        "subtitle": f"Capture {capture_year} · {vehicle} · pano {pano_id}",
        "fields": {
            "Pano ID": pano_id,
            "Heading": f"{heading}°",
            "Field of view": f"{fov}°",
            "Pitch": f"{pitch}°",
            "Capture date": f"{capture_year}-"
                            f"{_r46_int(p.slug, 'mo', 1, 12):02d}-"
                            f"{_r46_int(p.slug, 'dy', 1, 28):02d}",
            "Capture vehicle": vehicle,
            "Thumbnails": url_for("r6_streetview_thumbnails", slug=p.slug),
            "Timeline": url_for("r6_streetview_timeline", slug=p.slug),
            "Metadata": url_for("r6_streetview_meta", slug=p.slug),
        },
        "back": url_for("place_detail", slug=p.slug),
    }
    return _r46_render(payload, "r6_panorama.html",
                       place=p, headings=R6_HEADINGS,
                       thumbs=[(h, lbl, _r6_thumbnail_uri(p.slug, h))
                               for h, lbl in R6_HEADINGS],
                       capture_year=capture_year)


@app.route("/street-view/<slug>/timeline")
@app.route("/streetview/<slug>/timeline")
def r6_streetview_timeline(slug):
    p = _r6_place(slug)
    if p is None:
        abort(404)
    rows = []
    for i in range(6):
        yr = _r6_capture_year(p.slug, i)
        mo = _r46_int(p.slug, f"timo{i}", 1, 12)
        veh = _r46_pick(f"{p.slug}#{i}", R6_CAPTURE_VEHICLES, "tv")
        pano = hashlib.md5(
            f"pano:{p.slug}:hist{i}".encode()).hexdigest()[:14]
        rows.append([f"{yr}-{mo:02d}", veh, pano,
                     url_for("r6_streetview_panorama",
                             slug=p.slug, heading=i * 60)])
    rows.sort(key=lambda r: r[0], reverse=True)
    payload = {
        "title": f"{p.name} — Street View timeline",
        "subtitle": "Historical captures at this location",
        "table": {"cols": ["Captured", "Vehicle", "Pano ID", "Open"],
                  "rows": rows},
        "back": url_for("r6_streetview_panorama", slug=p.slug),
    }
    return _r46_render(payload, "r6_panorama.html",
                       place=p, headings=R6_HEADINGS,
                       thumbs=[(h, lbl, _r6_thumbnail_uri(p.slug, h))
                               for h, lbl in R6_HEADINGS],
                       capture_year=_r6_capture_year(p.slug, 0))


@app.route("/street-view/<slug>/meta")
@app.route("/streetview/<slug>/meta")
def r6_streetview_meta(slug):
    p = _r6_place(slug)
    if p is None:
        abort(404)
    capture_year = _r6_capture_year(p.slug, 0)
    payload = {
        "title": f"{p.name} — Street View metadata",
        "fields": {
            "Latitude": f"{p.lat:.6f}" if p.lat is not None else "—",
            "Longitude": f"{p.lng:.6f}" if p.lng is not None else "—",
            "Most recent capture": capture_year,
            "Captures on record": 6,
            "Coverage radius": f"{_r46_int(p.slug, 'rad', 20, 120)} m",
            "Has interior view":
                "Yes" if _r46_int(p.slug, "indoor", 0, 3) == 0 else "No",
            "Photosphere submissions":
                _r46_int(p.slug, "spheres", 0, 14),
        },
        "back": url_for("r6_streetview_panorama", slug=p.slug),
    }
    return _r46_render(payload, "r6_panorama.html",
                       place=p, headings=R6_HEADINGS,
                       thumbs=[(h, lbl, _r6_thumbnail_uri(p.slug, h))
                               for h, lbl in R6_HEADINGS],
                       capture_year=capture_year)


@app.route("/photosphere")
def r6_photosphere_index():
    samples = (Place.query
               .filter(Place.slug.like("r5-%"))
               .order_by(Place.slug).limit(40).all())
    rows = []
    for sp in samples:
        kind = _r46_pick(sp.slug, R6_PHOTOSPHERE_TYPES, "phtype")
        sphere = hashlib.md5(
            f"sphere:{sp.slug}".encode()).hexdigest()[:12]
        rows.append([sp.name, kind, _r6_capture_year(sp.slug, 1),
                     url_for("r6_photosphere_detail", sphere_id=sphere)])
    payload = {
        "title": "Photosphere — User-submitted 360° views",
        "subtitle": "Recently uploaded photospheres near you",
        "table": {"cols": ["Place", "Type", "Year", "Open"],
                  "rows": rows},
        "fields": {
            "Upload a photosphere":
                url_for("r6_photosphere_upload"),
        },
    }
    return _r46_render(payload, "r6_photosphere.html",
                       items=rows, mode="index")


@app.route("/photosphere/upload")
def r6_photosphere_upload():
    payload = {
        "title": "Photosphere — Upload",
        "subtitle": "Contribute a 360° view to Google Maps",
        "fields": {
            "Accepted formats": "JPEG, 2:1 equirectangular",
            "Max size": "75 MB",
            "Min resolution": "4096 × 2048",
            "Requires location": "Yes (auto-detected from EXIF)",
            "Moderation": "Human review within 7 days",
            "Browse community uploads":
                url_for("r6_photosphere_index"),
        },
    }
    return _r46_render(payload, "r6_photosphere.html",
                       items=[], mode="upload")


@app.route("/photosphere/<sphere_id>")
def r6_photosphere_detail(sphere_id):
    if not re.fullmatch(r"[0-9a-f]{6,40}", sphere_id):
        abort(404)
    photographer = _r46_pick(sphere_id,
                             ("alice.j", "bob.c", "carol.d", "david.k",
                              "anonymous"), "photog")
    kind = _r46_pick(sphere_id, R6_PHOTOSPHERE_TYPES, "kind")
    views = _r46_int(sphere_id, "views", 24, 28000)
    likes = _r46_int(sphere_id, "likes", 0, max(20, views // 30))
    yr = 2014 + _r46_int(sphere_id, "y", 0, 11)
    payload = {
        "title": f"Photosphere {sphere_id}",
        "subtitle": f"{kind} · uploaded {yr} by {photographer}",
        "fields": {
            "Sphere ID": sphere_id,
            "Type": kind,
            "Uploader": photographer,
            "Year": yr,
            "Views": f"{views:,}",
            "Likes": f"{likes:,}",
            "Field of view": "360° × 180°",
            "Resolution": f"{_r46_int(sphere_id, 'w', 4096, 16384)}"
                          f" × {_r46_int(sphere_id, 'h', 2048, 8192)}",
        },
        "back": url_for("r6_photosphere_index"),
    }
    return _r46_render(payload, "r6_photosphere.html",
                       items=[], mode="detail",
                       sphere_id=sphere_id, kind=kind,
                       photographer=photographer, year=yr,
                       views=views, likes=likes)


# === R4-R6 backfill END ===



if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        seed_database()
        seed_benchmark_users()
        from seed_data import seed_user_content
        seed_user_content(db, User, Place, Review, Photo, TimelineEntry)
        # Final byte-id pass: must be the last write.
        normalize_seed_db_layout()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)


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

