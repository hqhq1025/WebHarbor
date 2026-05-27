"""Apartments.com mirror — Flask app.

A rental-real-estate marketplace clone. Buildings → floor plans → units,
with neighborhood/city pages, scored search, schools, reviews, saved searches,
tour requests, side-by-side compare, and a lightweight account.

Self-contained: all paths go through BASE_DIR. No cross-site imports.
"""
import json
import math
import os
import re
import secrets
from datetime import date, datetime, timedelta
from functools import wraps
from urllib.parse import urlencode

from flask import (Flask, abort, flash, jsonify, redirect, render_template,
                   request, session, url_for)
from flask_bcrypt import Bcrypt
from flask_login import (LoginManager, UserMixin, current_user, login_required,
                         login_user, logout_user)
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect, generate_csrf
from sqlalchemy import or_, and_, func


BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__, instance_path=os.path.join(BASE_DIR, "instance"))
app.config["SECRET_KEY"] = "apartments-com-mirror-secret-key-not-for-prod"
app.config["SQLALCHEMY_DATABASE_URI"] = (
    f"sqlite:///{os.path.join(BASE_DIR, 'instance', 'apartments_com.db')}"
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["WTF_CSRF_TIME_LIMIT"] = None
os.makedirs(os.path.join(BASE_DIR, "instance"), exist_ok=True)

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = "login"
login_manager.login_message = "Sign in to save searches, favorite listings, or schedule a tour."
login_manager.login_message_category = "info"
csrf = CSRFProtect(app)


# ─── Models ────────────────────────────────────────────────────────────────────


class User(db.Model, UserMixin):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    name = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(40), default="")
    budget_max = db.Column(db.Integer, default=0)
    beds_min = db.Column(db.Integer, default=0)
    preferred_cities = db.Column(db.Text, default="[]")
    receive_alerts = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, pw):
        self.password_hash = bcrypt.generate_password_hash(pw).decode("utf-8")

    def check_password(self, pw):
        from werkzeug.security import check_password_hash as wz_check
        try:
            if (self.password_hash or "").startswith("pbkdf2:"):
                return wz_check(self.password_hash, pw)
            return bcrypt.check_password_hash(self.password_hash, pw)
        except Exception:
            return False


class City(db.Model):
    __tablename__ = "cities"
    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(80), unique=True, nullable=False, index=True)
    name = db.Column(db.String(80), nullable=False)
    state = db.Column(db.String(8), nullable=False)
    state_full = db.Column(db.String(40), default="")
    blurb = db.Column(db.Text, default="")
    hero_image = db.Column(db.String(250), default="")
    avg_rent_studio = db.Column(db.Integer, default=0)
    avg_rent_1br = db.Column(db.Integer, default=0)
    avg_rent_2br = db.Column(db.Integer, default=0)
    avg_rent_3br = db.Column(db.Integer, default=0)
    is_featured = db.Column(db.Boolean, default=False)


class Neighborhood(db.Model):
    __tablename__ = "neighborhoods"
    id = db.Column(db.Integer, primary_key=True)
    city_id = db.Column(db.Integer, db.ForeignKey("cities.id"), index=True)
    slug = db.Column(db.String(120), nullable=False, index=True)
    name = db.Column(db.String(80), nullable=False)
    blurb = db.Column(db.Text, default="")
    walk_score = db.Column(db.Integer, default=0)
    transit_score = db.Column(db.Integer, default=0)
    bike_score = db.Column(db.Integer, default=0)
    sound_score = db.Column(db.Integer, default=0)
    avg_rent = db.Column(db.Integer, default=0)
    city = db.relationship("City", backref=db.backref("neighborhoods", lazy=True))


class Building(db.Model):
    __tablename__ = "buildings"
    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(200), unique=True, nullable=False, index=True)
    name = db.Column(db.String(120), nullable=False)
    address = db.Column(db.String(200), nullable=False)
    city = db.Column(db.String(80), index=True)
    state = db.Column(db.String(8), index=True)
    zip = db.Column(db.String(20), default="", index=True)
    neighborhood = db.Column(db.String(80), index=True)
    neighborhood_id = db.Column(db.Integer, db.ForeignKey("neighborhoods.id"), index=True)
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)

    property_type = db.Column(db.String(40), default="Apartment", index=True)
    year_built = db.Column(db.Integer, default=0)
    total_units = db.Column(db.Integer, default=0)
    stories = db.Column(db.Integer, default=0)

    rent_min = db.Column(db.Integer, default=0, index=True)
    rent_max = db.Column(db.Integer, default=0, index=True)
    beds_min = db.Column(db.Integer, default=0, index=True)
    beds_max = db.Column(db.Integer, default=0, index=True)
    sqft_min = db.Column(db.Integer, default=0)
    sqft_max = db.Column(db.Integer, default=0)

    description = db.Column(db.Text, default="")
    hero_image = db.Column(db.String(250), default="")
    gallery_images = db.Column(db.Text, default="[]")

    walk_score = db.Column(db.Integer, default=0)
    transit_score = db.Column(db.Integer, default=0)
    bike_score = db.Column(db.Integer, default=0)
    sound_score = db.Column(db.Integer, default=0)

    pet_friendly = db.Column(db.Boolean, default=True)
    cats_allowed = db.Column(db.Boolean, default=True)
    dogs_allowed = db.Column(db.Boolean, default=True)
    dog_weight_limit = db.Column(db.Integer, default=0)
    pet_deposit = db.Column(db.Integer, default=0)
    pet_rent = db.Column(db.Integer, default=0)

    has_parking = db.Column(db.Boolean, default=False, index=True)
    parking_type = db.Column(db.String(40), default="")
    parking_fee = db.Column(db.Integer, default=0)
    has_pool = db.Column(db.Boolean, default=False, index=True)
    has_gym = db.Column(db.Boolean, default=False, index=True)
    has_doorman = db.Column(db.Boolean, default=False, index=True)
    has_elevator = db.Column(db.Boolean, default=False)
    has_rooftop = db.Column(db.Boolean, default=False, index=True)
    has_ev_charging = db.Column(db.Boolean, default=False, index=True)
    has_laundry_in_unit = db.Column(db.Boolean, default=True)
    has_concierge = db.Column(db.Boolean, default=False)
    has_business_center = db.Column(db.Boolean, default=False)
    has_dog_park = db.Column(db.Boolean, default=False)
    has_storage = db.Column(db.Boolean, default=False)
    is_furnished = db.Column(db.Boolean, default=False)
    is_student_housing = db.Column(db.Boolean, default=False, index=True)
    is_senior_housing = db.Column(db.Boolean, default=False, index=True)
    is_military_housing = db.Column(db.Boolean, default=False, index=True)
    is_luxury = db.Column(db.Boolean, default=False, index=True)

    amenities = db.Column(db.Text, default="[]")
    lease_terms = db.Column(db.Text, default="[]")
    deposit = db.Column(db.Integer, default=0)
    app_fee = db.Column(db.Integer, default=50)
    admin_fee = db.Column(db.Integer, default=200)

    property_manager = db.Column(db.String(120), default="")
    contact_phone = db.Column(db.String(40), default="")
    contact_email = db.Column(db.String(120), default="")
    tour_url = db.Column(db.String(250), default="")
    has_3d_tour = db.Column(db.Boolean, default=False)

    rating_avg = db.Column(db.Float, default=0.0)
    review_count = db.Column(db.Integer, default=0)

    listed_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    is_new = db.Column(db.Boolean, default=False, index=True)

    def get_gallery(self):
        try: return json.loads(self.gallery_images or "[]")
        except Exception: return []

    def get_amenities(self):
        try: return json.loads(self.amenities or "[]")
        except Exception: return []

    def get_lease_terms(self):
        try: return json.loads(self.lease_terms or "[]")
        except Exception: return []

    @property
    def rent_display(self):
        if self.rent_min == self.rent_max:
            return f"${self.rent_min:,}"
        return f"${self.rent_min:,} – ${self.rent_max:,}"

    @property
    def beds_display(self):
        if self.beds_min == 0 and self.beds_max == 0:
            return "Studio"
        if self.beds_min == 0:
            return f"Studio – {self.beds_max} bd"
        if self.beds_min == self.beds_max:
            return f"{self.beds_min} bd"
        return f"{self.beds_min} – {self.beds_max} bd"


class FloorPlan(db.Model):
    __tablename__ = "floor_plans"
    id = db.Column(db.Integer, primary_key=True)
    building_id = db.Column(db.Integer, db.ForeignKey("buildings.id"), index=True)
    slug = db.Column(db.String(80), nullable=False)
    name = db.Column(db.String(80), nullable=False)
    beds = db.Column(db.Integer, default=0)
    baths = db.Column(db.Float, default=1.0)
    sqft_min = db.Column(db.Integer, default=0)
    sqft_max = db.Column(db.Integer, default=0)
    rent_min = db.Column(db.Integer, default=0)
    rent_max = db.Column(db.Integer, default=0)
    available_count = db.Column(db.Integer, default=0)
    plan_image = db.Column(db.String(250), default="")
    description = db.Column(db.Text, default="")
    building = db.relationship("Building", backref=db.backref("floor_plans", lazy=True))


class Unit(db.Model):
    __tablename__ = "units"
    id = db.Column(db.Integer, primary_key=True)
    building_id = db.Column(db.Integer, db.ForeignKey("buildings.id"), index=True)
    floor_plan_id = db.Column(db.Integer, db.ForeignKey("floor_plans.id"), index=True)
    unit_number = db.Column(db.String(40), nullable=False)
    floor = db.Column(db.Integer, default=1)
    beds = db.Column(db.Integer, default=0)
    baths = db.Column(db.Float, default=1.0)
    sqft = db.Column(db.Integer, default=0)
    rent = db.Column(db.Integer, default=0, index=True)
    deposit = db.Column(db.Integer, default=0)
    available_date = db.Column(db.String(20), default="", index=True)
    lease_terms = db.Column(db.Text, default="[]")
    is_available = db.Column(db.Boolean, default=True, index=True)
    is_featured = db.Column(db.Boolean, default=False)
    view = db.Column(db.String(80), default="")
    building = db.relationship("Building", backref=db.backref("units", lazy=True))
    floor_plan = db.relationship("FloorPlan", backref=db.backref("units", lazy=True))

    def get_lease_terms(self):
        try: return json.loads(self.lease_terms or "[]")
        except Exception: return []


class School(db.Model):
    __tablename__ = "schools"
    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(120), unique=True, nullable=False, index=True)
    name = db.Column(db.String(120), nullable=False)
    grade_level = db.Column(db.String(40), default="")
    grades = db.Column(db.String(40), default="")
    type = db.Column(db.String(20), default="Public")
    rating = db.Column(db.Integer, default=5)
    district = db.Column(db.String(120), default="")
    city = db.Column(db.String(80), index=True)
    state = db.Column(db.String(8), index=True)
    student_count = db.Column(db.Integer, default=0)
    student_teacher_ratio = db.Column(db.Float, default=15.0)
    description = db.Column(db.Text, default="")


class BuildingSchool(db.Model):
    __tablename__ = "building_schools"
    id = db.Column(db.Integer, primary_key=True)
    building_id = db.Column(db.Integer, db.ForeignKey("buildings.id"), index=True)
    school_id = db.Column(db.Integer, db.ForeignKey("schools.id"), index=True)
    distance_mi = db.Column(db.Float, default=0.5)
    school = db.relationship("School")


class POI(db.Model):
    __tablename__ = "pois"
    id = db.Column(db.Integer, primary_key=True)
    building_id = db.Column(db.Integer, db.ForeignKey("buildings.id"), index=True)
    name = db.Column(db.String(120), nullable=False)
    category = db.Column(db.String(40), default="Restaurant")
    distance_mi = db.Column(db.Float, default=0.5)
    walk_min = db.Column(db.Integer, default=10)


class Review(db.Model):
    __tablename__ = "reviews"
    id = db.Column(db.Integer, primary_key=True)
    building_id = db.Column(db.Integer, db.ForeignKey("buildings.id"), index=True)
    author_name = db.Column(db.String(80), default="Verified Resident")
    rating = db.Column(db.Integer, default=5)
    rating_value = db.Column(db.Integer, default=5)
    rating_location = db.Column(db.Integer, default=5)
    rating_office_staff = db.Column(db.Integer, default=5)
    rating_maintenance = db.Column(db.Integer, default=5)
    rating_amenities = db.Column(db.Integer, default=5)
    title = db.Column(db.String(200), default="")
    body = db.Column(db.Text, default="")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    building = db.relationship("Building", backref=db.backref("reviews", lazy=True))


class SavedSearch(db.Model):
    __tablename__ = "saved_searches"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), index=True)
    name = db.Column(db.String(120), default="My search")
    query_string = db.Column(db.Text, default="")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Favorite(db.Model):
    __tablename__ = "favorites"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), index=True)
    building_id = db.Column(db.Integer, db.ForeignKey("buildings.id"), index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    building = db.relationship("Building")


class TourRequest(db.Model):
    __tablename__ = "tour_requests"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True, index=True)
    building_id = db.Column(db.Integer, db.ForeignKey("buildings.id"), index=True)
    unit_id = db.Column(db.Integer, db.ForeignKey("units.id"), nullable=True)
    name = db.Column(db.String(120), default="")
    email = db.Column(db.String(120), default="")
    phone = db.Column(db.String(40), default="")
    preferred_date = db.Column(db.String(20), default="")
    preferred_time = db.Column(db.String(40), default="")
    tour_type = db.Column(db.String(40), default="In-Person")
    move_in_date = db.Column(db.String(20), default="")
    message = db.Column(db.Text, default="")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    building = db.relationship("Building")
    unit = db.relationship("Unit")


class Message(db.Model):
    __tablename__ = "messages"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True, index=True)
    building_id = db.Column(db.Integer, db.ForeignKey("buildings.id"), index=True)
    name = db.Column(db.String(120), default="")
    email = db.Column(db.String(120), default="")
    phone = db.Column(db.String(40), default="")
    body = db.Column(db.Text, default="")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    building = db.relationship("Building")


class Article(db.Model):
    __tablename__ = "articles"
    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(200), unique=True, nullable=False, index=True)
    title = db.Column(db.String(200), nullable=False)
    summary = db.Column(db.Text, default="")
    body = db.Column(db.Text, default="")
    category = db.Column(db.String(80), default="Renters Guide", index=True)
    hero_image = db.Column(db.String(250), default="")
    author = db.Column(db.String(80), default="Apartments.com Editorial")
    published_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    reading_time_min = db.Column(db.Integer, default=5)


class Newsletter(db.Model):
    __tablename__ = "newsletter_subs"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class PropertyLead(db.Model):
    __tablename__ = "property_leads"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), default="")
    company = db.Column(db.String(120), default="")
    email = db.Column(db.String(120), default="")
    phone = db.Column(db.String(40), default="")
    portfolio_size = db.Column(db.String(40), default="")
    notes = db.Column(db.Text, default="")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


# ─── Login + CSRF helpers ────────────────────────────────────────────────────


@login_manager.user_loader
def load_user(uid):
    return db.session.get(User, int(uid))


@app.context_processor
def inject_globals():
    cmp_ids = session.get("compare", [])
    cmp_buildings = []
    if cmp_ids:
        cmp_buildings = Building.query.filter(Building.id.in_(cmp_ids)).all()
    fav_ids = set()
    if current_user.is_authenticated:
        fav_ids = {f.building_id for f in Favorite.query.filter_by(user_id=current_user.id).all()}
    return {
        "csrf_token": generate_csrf,
        "current_year": datetime.utcnow().year,
        "compare_buildings": cmp_buildings,
        "favorite_building_ids": fav_ids,
    }


# ─── Helpers ─────────────────────────────────────────────────────────────────


def _slug(s):
    return re.sub(r"[^a-z0-9]+", "-", (s or "").lower()).strip("-")


def _score_color(score):
    if score is None: return "score-0"
    if score >= 90: return "score-90"
    if score >= 70: return "score-70"
    if score >= 50: return "score-50"
    if score >= 25: return "score-25"
    return "score-0"


app.jinja_env.filters["score_color"] = _score_color


def _parse_int(v, default=0):
    try: return int(v)
    except Exception: return default


def _parse_search(args):
    q = (args.get("q") or "").strip()
    city = (args.get("city") or "").strip()
    state = (args.get("state") or "").strip()
    nbhd = (args.get("neighborhood") or "").strip()
    price_min = _parse_int(args.get("price_min"), 0)
    price_max = _parse_int(args.get("price_max"), 0)
    beds_options = args.getlist("beds")
    baths_min = _parse_int(args.get("baths_min"), 0)
    prop_types = args.getlist("type")
    amenities = args.getlist("amenity")
    pet_filter = (args.get("pet") or "").strip()
    lease = (args.get("lease") or "").strip()
    avail_by = (args.get("available_by") or "").strip()
    mode = (args.get("mode") or "").strip()
    sort = (args.get("sort") or "popular").strip()
    polygon = (args.get("polygon") or "").strip()
    return {
        "q": q, "city": city, "state": state, "neighborhood": nbhd,
        "price_min": price_min, "price_max": price_max,
        "beds": beds_options, "baths_min": baths_min,
        "type": prop_types, "amenity": amenities,
        "pet": pet_filter, "lease": lease,
        "available_by": avail_by, "mode": mode,
        "sort": sort, "polygon": polygon,
    }


def _apply_filters(query, f):
    if f["q"]:
        tokens = [t for t in re.split(r"\s+", f["q"].lower()) if t]
        for t in tokens:
            like = f"%{t}%"
            query = query.filter(or_(
                func.lower(Building.name).like(like),
                func.lower(Building.address).like(like),
                func.lower(Building.city).like(like),
                func.lower(Building.state).like(like),
                func.lower(Building.zip).like(like),
                func.lower(Building.neighborhood).like(like),
                func.lower(Building.description).like(like),
            ))
    if f["city"]:
        query = query.filter(func.lower(Building.city) == f["city"].lower())
    if f["state"]:
        query = query.filter(func.upper(Building.state) == f["state"].upper())
    if f["neighborhood"]:
        query = query.filter(func.lower(Building.neighborhood) == f["neighborhood"].lower())
    if f["price_min"]:
        query = query.filter(Building.rent_max >= f["price_min"])
    if f["price_max"]:
        query = query.filter(Building.rent_min <= f["price_max"])
    if f["beds"]:
        bed_clauses = []
        for b in f["beds"]:
            if b == "studio":
                bed_clauses.append(Building.beds_min == 0)
            elif b == "4+":
                bed_clauses.append(Building.beds_max >= 4)
            else:
                try:
                    n = int(b)
                    bed_clauses.append(and_(Building.beds_min <= n, Building.beds_max >= n))
                except Exception:
                    pass
        if bed_clauses:
            query = query.filter(or_(*bed_clauses))
    if f["type"]:
        query = query.filter(Building.property_type.in_(f["type"]))
    for a in f["amenity"]:
        col = {
            "pool": Building.has_pool,
            "gym": Building.has_gym,
            "doorman": Building.has_doorman,
            "rooftop": Building.has_rooftop,
            "ev_charging": Building.has_ev_charging,
            "parking": Building.has_parking,
            "dog_park": Building.has_dog_park,
            "concierge": Building.has_concierge,
            "business_center": Building.has_business_center,
            "in_unit_laundry": Building.has_laundry_in_unit,
            "elevator": Building.has_elevator,
            "storage": Building.has_storage,
            "furnished": Building.is_furnished,
        }.get(a)
        if col is not None:
            query = query.filter(col.is_(True))
    if f["pet"] == "dogs":
        query = query.filter(Building.dogs_allowed.is_(True))
    elif f["pet"] == "cats":
        query = query.filter(Building.cats_allowed.is_(True))
    elif f["pet"] == "any":
        query = query.filter(Building.pet_friendly.is_(True))
    if f["mode"] == "student":
        query = query.filter(Building.is_student_housing.is_(True))
    elif f["mode"] == "senior":
        query = query.filter(Building.is_senior_housing.is_(True))
    elif f["mode"] == "military":
        query = query.filter(Building.is_military_housing.is_(True))
    elif f["mode"] == "luxury":
        query = query.filter(Building.is_luxury.is_(True))
    if f["available_by"]:
        try:
            d = f["available_by"]
            sub = db.session.query(Unit.building_id).filter(
                Unit.is_available.is_(True),
                Unit.available_date <= d,
            ).distinct().subquery()
            query = query.filter(Building.id.in_(db.session.query(sub.c.building_id)))
        except Exception:
            pass
    if f["polygon"]:
        try:
            pts = [tuple(float(x) for x in p.split(",")) for p in f["polygon"].split(";") if "," in p]
            if len(pts) >= 3:
                lats = [p[0] for p in pts]; lngs = [p[1] for p in pts]
                query = query.filter(
                    Building.latitude >= min(lats),
                    Building.latitude <= max(lats),
                    Building.longitude >= min(lngs),
                    Building.longitude <= max(lngs),
                )
        except Exception:
            pass

    sort = f["sort"]
    if sort == "price_asc":
        query = query.order_by(Building.rent_min.asc(), Building.id.asc())
    elif sort == "price_desc":
        query = query.order_by(Building.rent_max.desc(), Building.id.asc())
    elif sort == "sqft":
        query = query.order_by(Building.sqft_max.desc(), Building.id.asc())
    elif sort == "newest":
        query = query.order_by(Building.listed_at.desc(), Building.id.asc())
    elif sort == "rating":
        query = query.order_by(Building.rating_avg.desc(), Building.id.asc())
    else:
        query = query.order_by(Building.rating_avg.desc(), Building.review_count.desc(), Building.id.asc())
    return query


# ─── Routes: home / city / neighborhood ──────────────────────────────────────


@app.route("/")
def index():
    featured_cities = City.query.filter_by(is_featured=True).order_by(City.name).limit(8).all()
    if not featured_cities:
        featured_cities = City.query.order_by(City.name).limit(8).all()
    featured_buildings = Building.query.order_by(Building.rating_avg.desc(), Building.id.asc()).limit(8).all()
    new_buildings = Building.query.filter_by(is_new=True).order_by(Building.id.asc()).limit(6).all()
    recent_articles = Article.query.order_by(Article.published_at.desc()).limit(4).all()
    return render_template(
        "index.html",
        featured_cities=featured_cities,
        featured_buildings=featured_buildings,
        new_buildings=new_buildings,
        recent_articles=recent_articles,
        total_buildings=Building.query.count(),
    )


@app.route("/cities")
def cities_index():
    all_cities = City.query.order_by(City.name).all()
    return render_template("cities_index.html", cities=all_cities)


@app.route("/<city_slug>/")
def city_page(city_slug):
    city = City.query.filter_by(slug=city_slug).first_or_404()
    buildings = Building.query.filter_by(city=city.name, state=city.state)\
        .order_by(Building.rating_avg.desc(), Building.id.asc()).limit(24).all()
    nbhds = Neighborhood.query.filter_by(city_id=city.id).order_by(Neighborhood.name).all()
    total = Building.query.filter_by(city=city.name, state=city.state).count()
    return render_template("city.html", city=city, buildings=buildings,
                           neighborhoods=nbhds, total=total)


@app.route("/<city_slug>/<nbhd_slug>/")
def neighborhood_page(city_slug, nbhd_slug):
    city = City.query.filter_by(slug=city_slug).first_or_404()
    nbhd = Neighborhood.query.filter_by(city_id=city.id, slug=nbhd_slug).first_or_404()
    buildings = Building.query.filter_by(neighborhood_id=nbhd.id)\
        .order_by(Building.rating_avg.desc()).all()
    schools = School.query.filter_by(city=city.name, state=city.state)\
        .order_by(School.rating.desc()).limit(8).all()
    return render_template("neighborhood.html", city=city, nbhd=nbhd,
                           buildings=buildings, schools=schools)


# ─── Search ──────────────────────────────────────────────────────────────────


@app.route("/search", methods=["GET", "POST"])
def search():
    if request.method == "POST":
        flat = []
        for key, vals in request.form.lists():
            if key == "csrf_token":
                continue
            for v in vals:
                if v:
                    flat.append((key, v))
        return redirect(url_for("search") + ("?" + urlencode(flat) if flat else ""))

    f = _parse_search(request.args)
    page = max(1, _parse_int(request.args.get("page"), 1))
    per_page = 24
    base = _apply_filters(Building.query, f)
    total = base.count()
    pages = max(1, math.ceil(total / per_page))
    buildings = base.offset((page - 1) * per_page).limit(per_page).all()
    cities = City.query.order_by(City.name).all()
    view = (request.args.get("view") or "list").strip()
    return render_template("search.html",
                           buildings=buildings, total=total, page=page, pages=pages,
                           cities=cities, filters=f, view=view, request_args=request.args)


@app.route("/search/draw", methods=["GET", "POST"])
def search_draw():
    if request.method == "POST":
        polygon = (request.form.get("polygon") or "").strip()
        return redirect(url_for("search", polygon=polygon))
    return render_template("draw_search.html")


# ─── Building detail ────────────────────────────────────────────────────────


@app.route("/<state>/<city_slug>/<building_slug>/")
def building_detail(state, city_slug, building_slug):
    b = Building.query.filter_by(slug=building_slug).first_or_404()
    plans = FloorPlan.query.filter_by(building_id=b.id).order_by(FloorPlan.beds, FloorPlan.rent_min).all()
    units = Unit.query.filter_by(building_id=b.id, is_available=True)\
        .order_by(Unit.beds, Unit.rent).all()
    pois = POI.query.filter_by(building_id=b.id).order_by(POI.distance_mi).all()
    schools = (db.session.query(School, BuildingSchool.distance_mi)
               .join(BuildingSchool, BuildingSchool.school_id == School.id)
               .filter(BuildingSchool.building_id == b.id)
               .order_by(School.rating.desc()).all())
    reviews = Review.query.filter_by(building_id=b.id)\
        .order_by(Review.created_at.desc()).limit(8).all()
    similar = Building.query.filter(Building.city == b.city,
                                    Building.state == b.state,
                                    Building.id != b.id)\
        .order_by(Building.rating_avg.desc()).limit(4).all()
    return render_template("building.html",
                           b=b, plans=plans, units=units, pois=pois,
                           schools=schools, reviews=reviews, similar=similar)


@app.route("/<state>/<city_slug>/<building_slug>/photos/")
def building_photos(state, city_slug, building_slug):
    b = Building.query.filter_by(slug=building_slug).first_or_404()
    return render_template("building_photos.html", b=b)


@app.route("/<state>/<city_slug>/<building_slug>/reviews/")
def building_reviews(state, city_slug, building_slug):
    b = Building.query.filter_by(slug=building_slug).first_or_404()
    reviews = Review.query.filter_by(building_id=b.id).order_by(Review.created_at.desc()).all()
    return render_template("building_reviews.html", b=b, reviews=reviews)


@app.route("/<state>/<city_slug>/<building_slug>/floorplan/<plan_slug>/")
def floor_plan_detail(state, city_slug, building_slug, plan_slug):
    b = Building.query.filter_by(slug=building_slug).first_or_404()
    plan = FloorPlan.query.filter_by(building_id=b.id, slug=plan_slug).first_or_404()
    units = Unit.query.filter_by(floor_plan_id=plan.id).order_by(Unit.unit_number).all()
    return render_template("floor_plan.html", b=b, plan=plan, units=units)


@app.route("/<state>/<city_slug>/<building_slug>/unit/<int:unit_id>/")
def unit_detail(state, city_slug, building_slug, unit_id):
    b = Building.query.filter_by(slug=building_slug).first_or_404()
    u = Unit.query.filter_by(id=unit_id, building_id=b.id).first_or_404()
    return render_template("unit.html", b=b, u=u, plan=u.floor_plan)


# ─── Reviews submit ─────────────────────────────────────────────────────────


@app.route("/<state>/<city_slug>/<building_slug>/reviews/submit", methods=["POST"])
def submit_review(state, city_slug, building_slug):
    b = Building.query.filter_by(slug=building_slug).first_or_404()
    r = Review(
        building_id=b.id,
        author_name=request.form.get("author_name", "Anonymous")[:80] or "Anonymous",
        rating=max(1, min(5, _parse_int(request.form.get("rating"), 5))),
        rating_value=max(1, min(5, _parse_int(request.form.get("rating_value"), 5))),
        rating_location=max(1, min(5, _parse_int(request.form.get("rating_location"), 5))),
        rating_office_staff=max(1, min(5, _parse_int(request.form.get("rating_office_staff"), 5))),
        rating_maintenance=max(1, min(5, _parse_int(request.form.get("rating_maintenance"), 5))),
        rating_amenities=max(1, min(5, _parse_int(request.form.get("rating_amenities"), 5))),
        title=request.form.get("title", "")[:200],
        body=request.form.get("body", ""),
        user_id=(current_user.id if current_user.is_authenticated else None),
    )
    db.session.add(r)
    db.session.commit()
    flash("Thanks for your review!", "success")
    return redirect(url_for("building_reviews", state=state, city_slug=city_slug,
                            building_slug=building_slug))


# ─── Tour requests / messaging ──────────────────────────────────────────────


@app.route("/<state>/<city_slug>/<building_slug>/tour", methods=["GET", "POST"])
def request_tour(state, city_slug, building_slug):
    b = Building.query.filter_by(slug=building_slug).first_or_404()
    step = _parse_int(request.args.get("step"), 1)
    unit_id = _parse_int(request.args.get("unit_id"), 0) or _parse_int(request.form.get("unit_id"), 0)
    unit = Unit.query.get(unit_id) if unit_id else None
    if request.method == "POST":
        post_step = _parse_int(request.form.get("step"), step)
        if post_step >= 3:
            tr = TourRequest(
                user_id=(current_user.id if current_user.is_authenticated else None),
                building_id=b.id, unit_id=unit_id or None,
                name=request.form.get("name", "")[:120],
                email=request.form.get("email", "")[:120],
                phone=request.form.get("phone", "")[:40],
                preferred_date=request.form.get("preferred_date", "")[:20],
                preferred_time=request.form.get("preferred_time", "")[:40],
                tour_type=request.form.get("tour_type", "In-Person")[:40],
                move_in_date=request.form.get("move_in_date", "")[:20],
                message=request.form.get("message", ""),
            )
            db.session.add(tr)
            db.session.commit()
            return render_template("tour_confirmed.html", b=b, tr=tr, unit=unit)
        for k in ("tour_type", "preferred_date", "preferred_time"):
            if request.form.get(k):
                session[f"tour_{k}"] = request.form.get(k)
        return render_template("tour.html", b=b, unit=unit,
                               step=post_step + 1)
    return render_template("tour.html", b=b, unit=unit, step=step)


@app.route("/<state>/<city_slug>/<building_slug>/message", methods=["GET", "POST"])
def send_message(state, city_slug, building_slug):
    b = Building.query.filter_by(slug=building_slug).first_or_404()
    if request.method == "POST":
        m = Message(
            user_id=(current_user.id if current_user.is_authenticated else None),
            building_id=b.id,
            name=request.form.get("name", "")[:120],
            email=request.form.get("email", "")[:120],
            phone=request.form.get("phone", "")[:40],
            body=request.form.get("body", ""),
        )
        db.session.add(m)
        db.session.commit()
        flash("Message sent to the property.", "success")
        return redirect(url_for("building_detail", state=state, city_slug=city_slug,
                                building_slug=building_slug))
    return render_template("message.html", b=b)


# ─── Favorites / compare / saved searches ───────────────────────────────────


@app.route("/favorite/<int:building_id>", methods=["POST"])
@login_required
def toggle_favorite(building_id):
    b = Building.query.get_or_404(building_id)
    existing = Favorite.query.filter_by(user_id=current_user.id, building_id=b.id).first()
    if existing:
        db.session.delete(existing)
        state = "removed"
    else:
        db.session.add(Favorite(user_id=current_user.id, building_id=b.id))
        state = "added"
    db.session.commit()
    if request.headers.get("X-Requested-With") == "fetch":
        return jsonify({"state": state})
    return redirect(request.referrer or url_for("index"))


@app.route("/favorites")
@login_required
def favorites_list():
    favs = Favorite.query.filter_by(user_id=current_user.id).order_by(Favorite.created_at.desc()).all()
    return render_template("favorites.html", favs=favs)


@app.route("/compare")
def compare():
    ids = session.get("compare", [])
    buildings = Building.query.filter(Building.id.in_(ids)).all() if ids else []
    return render_template("compare.html", buildings=buildings)


@app.route("/compare/add/<int:building_id>", methods=["POST"])
def compare_add(building_id):
    Building.query.get_or_404(building_id)
    cart = session.get("compare", [])
    if building_id not in cart:
        if len(cart) >= 4:
            cart.pop(0)
        cart.append(building_id)
        session["compare"] = cart
    return redirect(request.referrer or url_for("compare"))


@app.route("/compare/remove/<int:building_id>", methods=["POST"])
def compare_remove(building_id):
    cart = session.get("compare", [])
    if building_id in cart:
        cart.remove(building_id)
        session["compare"] = cart
    return redirect(request.referrer or url_for("compare"))


@app.route("/compare/clear", methods=["POST"])
def compare_clear():
    session["compare"] = []
    return redirect(url_for("compare"))


@app.route("/saved-searches", methods=["GET"])
@login_required
def saved_searches():
    items = SavedSearch.query.filter_by(user_id=current_user.id)\
        .order_by(SavedSearch.created_at.desc()).all()
    return render_template("saved_searches.html", items=items)


@app.route("/saved-searches/save", methods=["POST"])
@login_required
def save_search():
    name = request.form.get("name", "My search")[:120] or "My search"
    qs = request.form.get("query_string", "")
    db.session.add(SavedSearch(user_id=current_user.id, name=name, query_string=qs))
    db.session.commit()
    flash("Search saved. You'll get alerts for new matches.", "success")
    return redirect(url_for("saved_searches"))


@app.route("/saved-searches/<int:sid>/delete", methods=["POST"])
@login_required
def delete_saved_search(sid):
    s = SavedSearch.query.filter_by(id=sid, user_id=current_user.id).first_or_404()
    db.session.delete(s)
    db.session.commit()
    return redirect(url_for("saved_searches"))


# ─── Auth ────────────────────────────────────────────────────────────────────


@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("account"))
    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        pw = request.form.get("password") or ""
        u = User.query.filter_by(email=email).first()
        if u and u.check_password(pw):
            login_user(u, remember=bool(request.form.get("remember")))
            return redirect(request.args.get("next") or url_for("account"))
        flash("Incorrect email or password.", "error")
    return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("account"))
    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        name = (request.form.get("name") or "").strip()
        pw = request.form.get("password") or ""
        confirm = request.form.get("confirm") or ""
        if not email or not name or not pw:
            flash("All fields are required.", "error")
        elif pw != confirm:
            flash("Passwords don't match.", "error")
        elif User.query.filter_by(email=email).first():
            flash("Email already registered. Try signing in.", "error")
        else:
            u = User(email=email, name=name)
            u.set_password(pw)
            db.session.add(u)
            db.session.commit()
            login_user(u)
            return redirect(url_for("account"))
    return render_template("register.html")


@app.route("/logout")
def logout():
    logout_user()
    return redirect(url_for("index"))


@app.route("/account")
@login_required
def account():
    tours = TourRequest.query.filter_by(user_id=current_user.id)\
        .order_by(TourRequest.created_at.desc()).all()
    messages = Message.query.filter_by(user_id=current_user.id)\
        .order_by(Message.created_at.desc()).all()
    favs = Favorite.query.filter_by(user_id=current_user.id).all()
    searches = SavedSearch.query.filter_by(user_id=current_user.id).all()
    return render_template("account.html", tours=tours, messages=messages,
                           favs=favs, searches=searches)


@app.route("/account/edit", methods=["GET", "POST"])
@login_required
def account_edit():
    if request.method == "POST":
        current_user.name = request.form.get("name", current_user.name)[:120]
        current_user.phone = request.form.get("phone", "")[:40]
        current_user.budget_max = _parse_int(request.form.get("budget_max"), 0)
        current_user.beds_min = _parse_int(request.form.get("beds_min"), 0)
        current_user.receive_alerts = bool(request.form.get("receive_alerts"))
        db.session.commit()
        flash("Profile saved.", "success")
        return redirect(url_for("account"))
    return render_template("account_edit.html")


# ─── Schools ─────────────────────────────────────────────────────────────────


@app.route("/schools")
def schools_index():
    rows = School.query.order_by(School.rating.desc(), School.name).limit(60).all()
    return render_template("schools_index.html", schools=rows)


@app.route("/school/<slug>")
def school_detail(slug):
    s = School.query.filter_by(slug=slug).first_or_404()
    nearby = (db.session.query(Building, BuildingSchool.distance_mi)
              .join(BuildingSchool, BuildingSchool.building_id == Building.id)
              .filter(BuildingSchool.school_id == s.id)
              .order_by(BuildingSchool.distance_mi).limit(8).all())
    return render_template("school.html", s=s, nearby=nearby)


# ─── Renters Guide articles ──────────────────────────────────────────────────


@app.route("/renters-guide")
def articles_index():
    cat = (request.args.get("category") or "").strip()
    q = Article.query
    if cat:
        q = q.filter_by(category=cat)
    items = q.order_by(Article.published_at.desc()).all()
    categories = sorted({c[0] for c in db.session.query(Article.category).distinct().all()})
    return render_template("articles_index.html", articles=items, categories=categories,
                           current_category=cat)


@app.route("/renters-guide/<slug>")
def article_detail(slug):
    a = Article.query.filter_by(slug=slug).first_or_404()
    related = Article.query.filter(Article.category == a.category, Article.id != a.id)\
        .order_by(Article.published_at.desc()).limit(4).all()
    return render_template("article.html", a=a, related=related)


# ─── Specialty housing flows ────────────────────────────────────────────────


@app.route("/student-housing")
def student_housing():
    rows = Building.query.filter_by(is_student_housing=True)\
        .order_by(Building.rating_avg.desc()).limit(24).all()
    return render_template("specialty.html",
                           title="Student Housing",
                           subtitle="Apartments designed for college life: short leases, by-the-bed pricing, walk-to-campus.",
                           buildings=rows, mode="student")


@app.route("/senior-housing")
def senior_housing():
    rows = Building.query.filter_by(is_senior_housing=True)\
        .order_by(Building.rating_avg.desc()).limit(24).all()
    return render_template("specialty.html",
                           title="Senior Housing",
                           subtitle="55+ communities with accessibility features and engagement programs.",
                           buildings=rows, mode="senior")


@app.route("/military-housing")
def military_housing():
    rows = Building.query.filter_by(is_military_housing=True)\
        .order_by(Building.rating_avg.desc()).limit(24).all()
    return render_template("specialty.html",
                           title="Military Housing",
                           subtitle="On-base and nearby rentals with flexible PCS-friendly leases.",
                           buildings=rows, mode="military")


# ─── List your property landing ─────────────────────────────────────────────


@app.route("/list-your-property", methods=["GET", "POST"])
def list_property():
    if request.method == "POST":
        lead = PropertyLead(
            name=request.form.get("name", "")[:120],
            company=request.form.get("company", "")[:120],
            email=request.form.get("email", "")[:120],
            phone=request.form.get("phone", "")[:40],
            portfolio_size=request.form.get("portfolio_size", "")[:40],
            notes=request.form.get("notes", ""),
        )
        db.session.add(lead)
        db.session.commit()
        flash("Thanks! Our team will follow up within 1 business day.", "success")
        return redirect(url_for("list_property"))
    return render_template("list_property.html")


# ─── Newsletter ─────────────────────────────────────────────────────────────


@app.route("/newsletter", methods=["POST"])
def newsletter_signup():
    email = (request.form.get("email") or "").strip().lower()
    if email and not Newsletter.query.filter_by(email=email).first():
        db.session.add(Newsletter(email=email))
        db.session.commit()
        flash("You're subscribed to weekly market updates.", "success")
    elif email:
        flash("You're already subscribed.", "info")
    return redirect(request.referrer or url_for("index"))


# ─── Static support pages ───────────────────────────────────────────────────


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/help")
def help_page():
    return render_template("help.html")


# ─── Errors ─────────────────────────────────────────────────────────────────


@app.errorhandler(404)
def not_found(e):
    return render_template("404.html"), 404


@app.errorhandler(500)
def server_error(e):
    return render_template("500.html"), 500


# ─── Bootstrap ──────────────────────────────────────────────────────────────


from seed_data import seed_database, seed_benchmark_users  # noqa: E402


def _normalize_seed_db_layout():
    """Re-emit CREATE INDEX statements in alpha order + VACUUM so a fresh
    rebuild produces byte-identical sqlite output. Without this, SQLAlchemy
    emits CREATE INDEX in `Table.indexes` set order — set iteration depends
    on Python `id()` allocation and varies between processes.
    """
    from sqlalchemy import text
    with db.engine.begin() as conn:
        rows = conn.execute(text(
            "SELECT name, sql FROM sqlite_master WHERE type='index' AND name LIKE 'ix_%'"
        )).fetchall()
        for name, _ in rows:
            conn.execute(text(f'DROP INDEX IF EXISTS "{name}"'))
        for name, sql in sorted(rows, key=lambda r: r[0]):
            if sql:
                conn.execute(text(sql))
    with db.engine.connect() as conn:
        conn.exec_driver_sql("VACUUM")


with app.app_context():
    fresh = not os.path.exists(os.path.join(BASE_DIR, "instance", "apartments_com.db"))
    db.create_all()
    seed_database()
    seed_benchmark_users()
    if fresh:
        _normalize_seed_db_layout()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
