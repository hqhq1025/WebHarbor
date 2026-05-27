"""Compass.com mirror — Flask app with real-estate browse + account features."""
import json
import math
import os
import re
import secrets
from datetime import date, datetime, timedelta
from functools import wraps

from flask import (Flask, abort, flash, jsonify, redirect, render_template,
                   request, session, url_for)
from flask_bcrypt import Bcrypt
from flask_login import (LoginManager, UserMixin, current_user, login_required,
                         login_user, logout_user)
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect, generate_csrf
from sqlalchemy import or_, func


BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__, instance_path=os.path.join(BASE_DIR, "instance"))
app.config["SECRET_KEY"] = "compass-mirror-secret-key-not-for-prod"
app.config["SQLALCHEMY_DATABASE_URI"] = (
    f"sqlite:///{os.path.join(BASE_DIR, 'instance', 'compass.db')}"
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["WTF_CSRF_TIME_LIMIT"] = None

os.makedirs(os.path.join(BASE_DIR, "instance"), exist_ok=True)

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = "login"
login_manager.login_message = "Sign in to save homes, schedule tours, or contact an agent."
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
    city = db.Column(db.String(80), default="")
    state = db.Column(db.String(40), default="")
    budget_min = db.Column(db.Integer, default=0)
    budget_max = db.Column(db.Integer, default=0)
    beds_min = db.Column(db.Integer, default=0)
    preferred_property_types = db.Column(db.Text, default="[]")
    move_timeline = db.Column(db.String(40), default="")
    has_agent = db.Column(db.Boolean, default=False)
    receive_alerts = db.Column(db.Boolean, default=True)
    agent_id = db.Column(db.Integer, db.ForeignKey("agents.id"))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    saved_homes = db.relationship("SavedHome", backref="user", lazy=True,
                                  cascade="all, delete-orphan")
    saved_searches = db.relationship("SavedSearch", backref="user", lazy=True,
                                     cascade="all, delete-orphan")
    tours = db.relationship("Tour", backref="user", lazy=True,
                            cascade="all, delete-orphan")
    inquiries = db.relationship("Inquiry", backref="user", lazy=True,
                                cascade="all, delete-orphan")
    collections = db.relationship("Collection", backref="user", lazy=True,
                                  cascade="all, delete-orphan")

    def set_password(self, pw):
        self.password_hash = bcrypt.generate_password_hash(pw).decode("utf-8")

    def check_password(self, pw):
        # Support both bcrypt hashes (live registrations) and the
        # deterministic pbkdf2 hashes used for benchmark-seed users so the
        # seed DB stays byte-identical.
        from werkzeug.security import check_password_hash as wz_check
        try:
            if (self.password_hash or "").startswith("pbkdf2:"):
                return wz_check(self.password_hash, pw)
            return bcrypt.check_password_hash(self.password_hash, pw)
        except Exception:
            return False

    def get_property_types(self):
        try:
            return json.loads(self.preferred_property_types or "[]")
        except Exception:
            return []


class Agent(db.Model):
    __tablename__ = "agents"
    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(120), unique=True, nullable=False, index=True)
    name = db.Column(db.String(120), nullable=False)
    title = db.Column(db.String(120), default="Real Estate Agent")
    photo = db.Column(db.String(250), default="")
    bio = db.Column(db.Text, default="")
    email = db.Column(db.String(120), default="")
    phone = db.Column(db.String(40), default="")
    license_number = db.Column(db.String(60), default="")
    city = db.Column(db.String(80), default="")
    state = db.Column(db.String(40), default="")
    years_experience = db.Column(db.Integer, default=0)
    sales_volume_usd = db.Column(db.BigInteger, default=0)
    transactions_count = db.Column(db.Integer, default=0)
    languages = db.Column(db.Text, default="[]")
    specialties = db.Column(db.Text, default="[]")
    is_top_agent = db.Column(db.Boolean, default=False)

    listings = db.relationship("Listing", backref="agent", lazy=True)

    def get_languages(self):
        try:
            return json.loads(self.languages or "[]")
        except Exception:
            return []

    def get_specialties(self):
        try:
            return json.loads(self.specialties or "[]")
        except Exception:
            return []

    def sales_volume_display(self):
        v = self.sales_volume_usd or 0
        if v >= 1_000_000_000:
            return f"${v/1_000_000_000:.1f}B"
        if v >= 1_000_000:
            return f"${v/1_000_000:.0f}M"
        if v >= 1_000:
            return f"${v/1_000:.0f}K"
        return f"${v}"


class City(db.Model):
    __tablename__ = "cities"
    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(80), unique=True, nullable=False, index=True)
    name = db.Column(db.String(80), nullable=False)
    state = db.Column(db.String(40), nullable=False)
    hero_image = db.Column(db.String(250), default="")
    blurb = db.Column(db.Text, default="")
    is_featured = db.Column(db.Boolean, default=False)


class Listing(db.Model):
    __tablename__ = "listings"
    id = db.Column(db.Integer, primary_key=True)
    listing_id_sha = db.Column(db.String(40), unique=True, index=True)
    slug = db.Column(db.String(200), unique=True, nullable=False, index=True)
    address = db.Column(db.String(200), nullable=False)
    unit = db.Column(db.String(60), default="")
    neighborhood = db.Column(db.String(80), default="")
    city = db.Column(db.String(80), index=True)
    state = db.Column(db.String(40), index=True)
    zip = db.Column(db.String(20), default="")
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)

    status = db.Column(db.String(20), default="for-sale", index=True)
    price = db.Column(db.Integer, default=0)
    beds = db.Column(db.Integer, default=0)
    baths_full = db.Column(db.Integer, default=0)
    baths_half = db.Column(db.Integer, default=0)
    sqft = db.Column(db.Integer, default=0)
    lot_sqft = db.Column(db.Integer, default=0)
    year_built = db.Column(db.Integer, default=0)
    property_type = db.Column(db.String(40), default="Single Family", index=True)

    description = db.Column(db.Text, default="")
    features = db.Column(db.Text, default="[]")
    hero_image = db.Column(db.String(250), default="")
    gallery_images = db.Column(db.Text, default="[]")

    mls_number = db.Column(db.String(40), default="")
    hoa_fee_usd_month = db.Column(db.Integer, default=0)
    days_on_compass = db.Column(db.Integer, default=0)
    listed_at = db.Column(db.DateTime, default=datetime.utcnow)

    is_open_house = db.Column(db.Boolean, default=False, index=True)
    open_house_date = db.Column(db.String(20), default="")
    open_house_time = db.Column(db.String(40), default="")

    is_new = db.Column(db.Boolean, default=False)
    is_compass_exclusive = db.Column(db.Boolean, default=False)
    is_luxury = db.Column(db.Boolean, default=False)
    is_pending = db.Column(db.Boolean, default=False)

    has_parking = db.Column(db.Boolean, default=False)
    has_pool = db.Column(db.Boolean, default=False)
    has_doorman = db.Column(db.Boolean, default=False)
    has_elevator = db.Column(db.Boolean, default=False)
    has_garage = db.Column(db.Boolean, default=False)
    has_waterfront = db.Column(db.Boolean, default=False)
    pets_allowed = db.Column(db.Boolean, default=True)
    furnished = db.Column(db.Boolean, default=False)

    agent_id = db.Column(db.Integer, db.ForeignKey("agents.id"))

    saved_by = db.relationship("SavedHome", backref="listing", lazy=True,
                               cascade="all, delete-orphan")
    tours = db.relationship("Tour", backref="listing", lazy=True,
                            cascade="all, delete-orphan")
    inquiries = db.relationship("Inquiry", backref="listing", lazy=True,
                                cascade="all, delete-orphan")

    def get_features(self):
        try:
            return json.loads(self.features or "[]")
        except Exception:
            return []

    def get_gallery(self):
        try:
            g = json.loads(self.gallery_images or "[]")
            return g if isinstance(g, list) else []
        except Exception:
            return []

    @property
    def baths(self):
        return (self.baths_full or 0) + 0.5 * (self.baths_half or 0)

    def price_display(self):
        if self.status == "for-rent":
            return f"${self.price:,}/mo"
        return f"${self.price:,}"

    def price_per_sqft(self):
        if not self.sqft or not self.price or self.status == "for-rent":
            return 0
        return round(self.price / self.sqft)


class SavedHome(db.Model):
    __tablename__ = "saved_homes"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    listing_id = db.Column(db.Integer, db.ForeignKey("listings.id"), nullable=False)
    note = db.Column(db.Text, default="")
    saved_at = db.Column(db.DateTime, default=datetime.utcnow)
    __table_args__ = (db.UniqueConstraint("user_id", "listing_id"),)


class SavedSearch(db.Model):
    __tablename__ = "saved_searches"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    name = db.Column(db.String(120), nullable=False)
    criteria_json = db.Column(db.Text, nullable=False, default="{}")
    notify = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def get_criteria(self):
        try:
            return json.loads(self.criteria_json or "{}")
        except Exception:
            return {}


class Tour(db.Model):
    __tablename__ = "tours"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    listing_id = db.Column(db.Integer, db.ForeignKey("listings.id"), nullable=False)
    requested_date = db.Column(db.String(20), default="")
    requested_time = db.Column(db.String(40), default="")
    tour_type = db.Column(db.String(40), default="in-person")
    contact_phone = db.Column(db.String(40), default="")
    notes = db.Column(db.Text, default="")
    status = db.Column(db.String(20), default="requested")
    requested_at = db.Column(db.DateTime, default=datetime.utcnow)


class Inquiry(db.Model):
    __tablename__ = "inquiries"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    listing_id = db.Column(db.Integer, db.ForeignKey("listings.id"), nullable=False)
    agent_id = db.Column(db.Integer, db.ForeignKey("agents.id"))
    name = db.Column(db.String(120), default="")
    email = db.Column(db.String(120), default="")
    phone = db.Column(db.String(40), default="")
    subject = db.Column(db.String(160), default="")
    message = db.Column(db.Text, default="")
    sent_at = db.Column(db.DateTime, default=datetime.utcnow)


class Collection(db.Model):
    __tablename__ = "collections"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, default="")
    listing_ids_json = db.Column(db.Text, default="[]")
    share_token = db.Column(db.String(20), default="")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    invited_emails_json = db.Column(db.Text, default="[]")

    def get_invited_emails(self):
        try:
            return json.loads(self.invited_emails_json or "[]")
        except Exception:
            return []

    def get_listing_ids(self):
        try:
            return json.loads(self.listing_ids_json or "[]")
        except Exception:
            return []

    def set_listing_ids(self, ids):
        self.listing_ids_json = json.dumps(list(ids))

    def get_listings(self):
        ids = self.get_listing_ids()
        if not ids:
            return []
        rows = Listing.query.filter(Listing.id.in_(ids)).all()
        by_id = {r.id: r for r in rows}
        return [by_id[i] for i in ids if i in by_id]


# ─── New deep-content models ──────────────────────────────────────────────────


class Neighborhood(db.Model):
    __tablename__ = "neighborhoods"
    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(120), unique=True, nullable=False, index=True)
    name = db.Column(db.String(120), nullable=False)
    city = db.Column(db.String(80), index=True)
    state = db.Column(db.String(40), index=True)
    blurb = db.Column(db.Text, default="")
    walk_score = db.Column(db.Integer, default=0)
    transit_score = db.Column(db.Integer, default=0)
    bike_score = db.Column(db.Integer, default=0)
    median_sale_price = db.Column(db.Integer, default=0)
    median_rent = db.Column(db.Integer, default=0)
    population = db.Column(db.Integer, default=0)
    median_age = db.Column(db.Integer, default=0)
    median_household_income = db.Column(db.Integer, default=0)
    hero_image = db.Column(db.String(250), default="")
    dining_blurb = db.Column(db.Text, default="")
    parks_blurb = db.Column(db.Text, default="")
    transit_blurb = db.Column(db.Text, default="")


class School(db.Model):
    __tablename__ = "schools"
    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(120), unique=True, nullable=False, index=True)
    name = db.Column(db.String(120), nullable=False)
    city = db.Column(db.String(80), index=True)
    state = db.Column(db.String(40), index=True)
    school_type = db.Column(db.String(20), default="Public")  # Public / Private / Charter
    grade_low = db.Column(db.String(8), default="K")
    grade_high = db.Column(db.String(8), default="5")
    rating = db.Column(db.Integer, default=0)  # 1-10
    students = db.Column(db.Integer, default=0)
    student_teacher_ratio = db.Column(db.String(16), default="")
    address = db.Column(db.String(200), default="")


class ListingSchool(db.Model):
    __tablename__ = "listing_schools"
    id = db.Column(db.Integer, primary_key=True)
    listing_id = db.Column(db.Integer, db.ForeignKey("listings.id"), nullable=False, index=True)
    school_id = db.Column(db.Integer, db.ForeignKey("schools.id"), nullable=False)
    distance_miles = db.Column(db.Float, default=0)
    is_assigned = db.Column(db.Boolean, default=False)
    __table_args__ = (db.UniqueConstraint("listing_id", "school_id"),)


class Office(db.Model):
    __tablename__ = "offices"
    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(120), unique=True, nullable=False, index=True)
    name = db.Column(db.String(120), nullable=False)
    city = db.Column(db.String(80), index=True)
    state = db.Column(db.String(40), index=True)
    address = db.Column(db.String(200), default="")
    phone = db.Column(db.String(40), default="")
    hours = db.Column(db.String(120), default="Mon-Fri 9am-6pm")
    director_name = db.Column(db.String(120), default="")
    agent_count = db.Column(db.Integer, default=0)


class Team(db.Model):
    __tablename__ = "teams"
    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(120), unique=True, nullable=False, index=True)
    name = db.Column(db.String(120), nullable=False)
    city = db.Column(db.String(80), index=True)
    state = db.Column(db.String(40), index=True)
    bio = db.Column(db.Text, default="")
    lead_agent_id = db.Column(db.Integer, db.ForeignKey("agents.id"))
    sales_volume_usd = db.Column(db.BigInteger, default=0)
    transactions_count = db.Column(db.Integer, default=0)


class TeamMember(db.Model):
    __tablename__ = "team_members"
    id = db.Column(db.Integer, primary_key=True)
    team_id = db.Column(db.Integer, db.ForeignKey("teams.id"), nullable=False, index=True)
    agent_id = db.Column(db.Integer, db.ForeignKey("agents.id"), nullable=False)
    role = db.Column(db.String(60), default="Agent")
    __table_args__ = (db.UniqueConstraint("team_id", "agent_id"),)


class MarketReport(db.Model):
    __tablename__ = "market_reports"
    id = db.Column(db.Integer, primary_key=True)
    city_slug = db.Column(db.String(80), index=True)
    city = db.Column(db.String(80))
    state = db.Column(db.String(40))
    month = db.Column(db.String(8), index=True)  # YYYY-MM
    median_sale_price = db.Column(db.Integer, default=0)
    median_price_per_sqft = db.Column(db.Integer, default=0)
    homes_sold = db.Column(db.Integer, default=0)
    median_days_on_market = db.Column(db.Integer, default=0)
    sale_to_list_ratio = db.Column(db.Float, default=0)
    inventory = db.Column(db.Integer, default=0)
    new_listings = db.Column(db.Integer, default=0)
    yoy_price_change_pct = db.Column(db.Float, default=0)
    __table_args__ = (db.UniqueConstraint("city_slug", "month"),)


class BlogPost(db.Model):
    __tablename__ = "blog_posts"
    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(160), unique=True, nullable=False, index=True)
    title = db.Column(db.String(220), nullable=False)
    category = db.Column(db.String(60), index=True)
    author = db.Column(db.String(120), default="Compass Editorial")
    excerpt = db.Column(db.Text, default="")
    body = db.Column(db.Text, default="")
    hero_image = db.Column(db.String(250), default="")
    published_at = db.Column(db.DateTime)
    read_minutes = db.Column(db.Integer, default=4)


class PriceHistory(db.Model):
    __tablename__ = "price_history"
    id = db.Column(db.Integer, primary_key=True)
    listing_id = db.Column(db.Integer, db.ForeignKey("listings.id"), nullable=False, index=True)
    event_date = db.Column(db.String(20))  # YYYY-MM-DD
    event_type = db.Column(db.String(40))  # Listed, Price reduced, Pending, Sold, Relisted
    price = db.Column(db.Integer, default=0)


class AgentReview(db.Model):
    __tablename__ = "agent_reviews"
    id = db.Column(db.Integer, primary_key=True)
    agent_id = db.Column(db.Integer, db.ForeignKey("agents.id"), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    reviewer_name = db.Column(db.String(120), default="")
    rating = db.Column(db.Integer, default=5)
    title = db.Column(db.String(160), default="")
    body = db.Column(db.Text, default="")
    transaction_type = db.Column(db.String(20), default="Buyer")  # Buyer / Seller / Renter
    created_at = db.Column(db.DateTime)


class AgentAward(db.Model):
    __tablename__ = "agent_awards"
    id = db.Column(db.Integer, primary_key=True)
    agent_id = db.Column(db.Integer, db.ForeignKey("agents.id"), nullable=False, index=True)
    year = db.Column(db.Integer)
    name = db.Column(db.String(160))


class SoldListing(db.Model):
    """Recently-sold homes — separate table so live listings stay clean."""
    __tablename__ = "sold_listings"
    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(200), unique=True, nullable=False, index=True)
    address = db.Column(db.String(200), nullable=False)
    unit = db.Column(db.String(60), default="")
    neighborhood = db.Column(db.String(80), default="")
    city = db.Column(db.String(80), index=True)
    state = db.Column(db.String(40), index=True)
    zip = db.Column(db.String(20), default="")
    beds = db.Column(db.Integer, default=0)
    baths_full = db.Column(db.Integer, default=0)
    baths_half = db.Column(db.Integer, default=0)
    sqft = db.Column(db.Integer, default=0)
    year_built = db.Column(db.Integer, default=0)
    property_type = db.Column(db.String(40), default="Single Family")
    list_price = db.Column(db.Integer, default=0)
    sold_price = db.Column(db.Integer, default=0)
    sold_date = db.Column(db.String(20))
    days_on_market = db.Column(db.Integer, default=0)
    hero_image = db.Column(db.String(250), default="")
    agent_id = db.Column(db.Integer, db.ForeignKey("agents.id"))

    @property
    def baths(self):
        return (self.baths_full or 0) + 0.5 * (self.baths_half or 0)

    def price_display(self):
        return f"${self.sold_price:,}"


class Note(db.Model):
    __tablename__ = "notes"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    listing_id = db.Column(db.Integer, db.ForeignKey("listings.id"))
    body = db.Column(db.Text, default="")
    created_at = db.Column(db.DateTime)


class Offer(db.Model):
    __tablename__ = "offers"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    listing_id = db.Column(db.Integer, db.ForeignKey("listings.id"), nullable=False)
    amount = db.Column(db.Integer, default=0)
    earnest_money = db.Column(db.Integer, default=0)
    contingencies = db.Column(db.String(200), default="")
    close_date = db.Column(db.String(20), default="")
    financing = db.Column(db.String(40), default="Conventional")
    notes = db.Column(db.Text, default="")
    status = db.Column(db.String(20), default="submitted")
    created_at = db.Column(db.DateTime)


class MortgageScenario(db.Model):
    __tablename__ = "mortgage_scenarios"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    label = db.Column(db.String(120), default="Saved scenario")
    home_price = db.Column(db.Integer, default=0)
    down_payment = db.Column(db.Integer, default=0)
    rate_pct = db.Column(db.Float, default=0)
    term_years = db.Column(db.Integer, default=30)
    annual_tax = db.Column(db.Integer, default=0)
    annual_insurance = db.Column(db.Integer, default=0)
    monthly_hoa = db.Column(db.Integer, default=0)
    monthly_payment = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime)


class AffordabilityResult(db.Model):
    __tablename__ = "affordability_results"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    annual_income = db.Column(db.Integer, default=0)
    monthly_debts = db.Column(db.Integer, default=0)
    down_payment = db.Column(db.Integer, default=0)
    rate_pct = db.Column(db.Float, default=0)
    max_home_price = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime)


class HomeEvaluation(db.Model):
    __tablename__ = "home_evaluations"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    address = db.Column(db.String(200))
    city = db.Column(db.String(80))
    state = db.Column(db.String(40))
    zip = db.Column(db.String(20), default="")
    beds = db.Column(db.Integer, default=0)
    baths = db.Column(db.Float, default=0)
    sqft = db.Column(db.Integer, default=0)
    estimated_value = db.Column(db.Integer, default=0)
    timeline = db.Column(db.String(40), default="3-6mo")
    created_at = db.Column(db.DateTime)


class CMARequest(db.Model):
    __tablename__ = "cma_requests"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    address = db.Column(db.String(200))
    city = db.Column(db.String(80))
    state = db.Column(db.String(40))
    contact_name = db.Column(db.String(120), default="")
    contact_email = db.Column(db.String(120), default="")
    contact_phone = db.Column(db.String(40), default="")
    notes = db.Column(db.Text, default="")
    created_at = db.Column(db.DateTime)


class NewsletterSignup(db.Model):
    __tablename__ = "newsletter_signups"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    name = db.Column(db.String(120), default="")
    city_interest = db.Column(db.String(80), default="")
    created_at = db.Column(db.DateTime)


class NeighborhoodAlertSubscription(db.Model):
    __tablename__ = "neighborhood_alerts"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    email = db.Column(db.String(120))
    neighborhood_slug = db.Column(db.String(120))
    frequency = db.Column(db.String(20), default="weekly")
    created_at = db.Column(db.DateTime)


class MarketReportSubscription(db.Model):
    __tablename__ = "market_report_subscriptions"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    email = db.Column(db.String(120))
    city_slug = db.Column(db.String(80))
    created_at = db.Column(db.DateTime)


# ─── Login loader ──────────────────────────────────────────────────────────────

@login_manager.user_loader
def load_user(uid):
    return User.query.get(int(uid))


@app.context_processor
def inject_globals():
    saved_count = 0
    if current_user.is_authenticated:
        saved_count = SavedHome.query.filter_by(user_id=current_user.id).count()
    return {
        "now": datetime.utcnow(),
        "csrf_token": generate_csrf,
        "FEATURED_CITIES": _featured_cities(),
        "saved_count": saved_count,
    }


def _featured_cities():
    return City.query.filter_by(is_featured=True).order_by(City.name).all()


# ─── Helpers ───────────────────────────────────────────────────────────────────


def _tokens(s: str):
    if not s:
        return []
    return [t for t in re.split(r"[^a-z0-9]+", s.lower()) if t and len(t) > 1]


def _listing_corpus(L) -> str:
    parts = [
        L.address, L.unit or "", L.neighborhood or "", L.city or "", L.state or "",
        L.zip or "", L.property_type or "", L.status or "",
        L.description or "", " ".join(L.get_features()),
    ]
    if L.agent:
        parts.append(L.agent.name)
        parts.append(" ".join(L.agent.get_specialties()))
    return " ".join(parts).lower()


def search_listings(query: str, base_query=None):
    """Token-overlap scored search. Returns list of (Listing, score)."""
    q = (query or "").strip()
    if base_query is None:
        base_query = Listing.query
    listings = base_query.all()
    if not q:
        return [(L, 0) for L in listings]
    qtoks = _tokens(q)
    if not qtoks:
        return [(L, 0) for L in listings]
    qset = set(qtoks)
    scored = []
    for L in listings:
        corpus = _listing_corpus(L)
        ctoks = _tokens(corpus)
        cset = set(ctoks)
        overlap = qset & cset
        if not overlap:
            continue
        tf = sum(ctoks.count(t) for t in overlap)
        boost = 0
        ql = q.lower()
        if L.city and L.city.lower() in ql: boost += 5
        if L.state and L.state.lower() in ql: boost += 5
        if L.neighborhood and L.neighborhood.lower() in ql: boost += 4
        if L.zip and L.zip in q: boost += 5
        score = len(overlap) * 3 + tf + boost
        scored.append((L, score))
    scored.sort(key=lambda x: (-x[1], -(x[0].price or 0)))
    return scored


def filter_listings(qs, args):
    status = args.get("status")
    if status:
        qs = qs.filter(Listing.status == status)
    pt = args.get("type") or args.get("property_type")
    if pt:
        qs = qs.filter(Listing.property_type == pt)
    pmin = args.get("price_min")
    pmax = args.get("price_max")
    if pmin and pmin.isdigit():
        qs = qs.filter(Listing.price >= int(pmin))
    if pmax and pmax.isdigit():
        qs = qs.filter(Listing.price <= int(pmax))
    beds = args.get("beds")
    if beds and beds.isdigit():
        qs = qs.filter(Listing.beds >= int(beds))
    baths = args.get("baths")
    if baths and baths.isdigit():
        qs = qs.filter((Listing.baths_full + Listing.baths_half) >= int(baths))
    sqft_min = args.get("sqft_min")
    if sqft_min and sqft_min.isdigit():
        qs = qs.filter(Listing.sqft >= int(sqft_min))
    year_built = args.get("year_built_min")
    if year_built and year_built.isdigit():
        qs = qs.filter(Listing.year_built >= int(year_built))
    if args.get("pool"):
        qs = qs.filter(Listing.has_pool == True)
    if args.get("garage"):
        qs = qs.filter(Listing.has_garage == True)
    if args.get("waterfront"):
        qs = qs.filter(Listing.has_waterfront == True)
    if args.get("doorman"):
        qs = qs.filter(Listing.has_doorman == True)
    if args.get("open_house"):
        qs = qs.filter(Listing.is_open_house == True)
    if args.get("new"):
        qs = qs.filter(Listing.is_new == True)
    if args.get("compass_exclusive"):
        qs = qs.filter(Listing.is_compass_exclusive == True)
    return qs


def sort_listings(items, key: str):
    is_pair = items and isinstance(items[0], tuple)

    def L(x): return x[0] if is_pair else x

    if key == "price_asc":
        items.sort(key=lambda x: (L(x).price or 0))
    elif key == "price_desc":
        items.sort(key=lambda x: -(L(x).price or 0))
    elif key == "newest":
        items.sort(key=lambda x: (L(x).days_on_compass or 9999))
    elif key == "sqft_desc":
        items.sort(key=lambda x: -(L(x).sqft or 0))
    elif key == "beds_desc":
        items.sort(key=lambda x: -(L(x).beds or 0))
    elif key == "ppsf_asc":
        items.sort(key=lambda x: L(x).price_per_sqft() or 10**12)
    elif key == "ppsf_desc":
        items.sort(key=lambda x: -(L(x).price_per_sqft() or 0))
    return items


def city_state_slug(slug: str):
    m = re.match(r"^(.*)-([a-z]{2})$", slug.lower())
    if not m:
        return None, None
    city = m.group(1).replace("-", " ").title()
    state = m.group(2).upper()
    return city, state


# ─── Public browse ─────────────────────────────────────────────────────────────


@app.route("/")
def index():
    # Curated mixes — explicitly NOT sorted by price/recency so the homepage
    # doesn't trivially surface the top luxury / cheapest listing / freshest
    # listing of any market (those should require navigating into the
    # relevant section).
    featured = (Listing.query.filter_by(is_compass_exclusive=True)
                .order_by(Listing.id).limit(6).all())
    new_listings = (Listing.query.filter_by(is_new=True)
                    .order_by(Listing.id.desc()).limit(6).all())
    luxury = (Listing.query.filter_by(is_luxury=True)
              .order_by(Listing.id).limit(6).all())
    return render_template("index.html",
                           featured=featured, new_listings=new_listings,
                           luxury=luxury)


@app.route("/homes-for-sale")
def homes_for_sale_index():
    cities = City.query.order_by(City.name).all()
    return render_template("homes_for_sale.html", cities=cities,
                           status_label="For Sale", status="for-sale")


@app.route("/homes-for-rent")
def homes_for_rent_index():
    cities = City.query.order_by(City.name).all()
    return render_template("homes_for_sale.html", cities=cities,
                           status_label="For Rent", status="for-rent")


@app.route("/homes-for-sale/<city_state>/")
def city_for_sale(city_state):
    return _city_listing_page(city_state, status="for-sale")


@app.route("/homes-for-rent/<city_state>/")
def city_for_rent(city_state):
    return _city_listing_page(city_state, status="for-rent")


def _city_listing_page(city_state, status):
    city, state = city_state_slug(city_state)
    if not city:
        abort(404)
    qs = Listing.query.filter_by(city=city, state=state, status=status)
    qs = filter_listings(qs, request.args)
    listings = qs.all()
    sort = request.args.get("sort", "newest")
    sort_listings(listings, sort)
    city_row = City.query.filter_by(slug=city_state).first()
    return render_template(
        "city.html",
        city_name=city, state=state,
        city_slug=city_state,
        city_row=city_row,
        status=status,
        status_label="For Sale" if status == "for-sale" else "For Rent",
        listings=listings,
        sort=sort,
        active_filters=dict(request.args),
        page_title=f"{city} {state} {('Homes For Sale' if status=='for-sale' else 'Homes For Rent')}",
    )


@app.route("/listing/<slug>")
def listing_detail(slug):
    L = Listing.query.filter_by(slug=slug).first()
    if not L:
        abort(404)
    similar = (Listing.query
               .filter(Listing.id != L.id, Listing.city == L.city,
                       Listing.status == L.status)
               .order_by(func.abs(Listing.price - L.price)).limit(4).all())
    is_saved = False
    if current_user.is_authenticated:
        is_saved = (SavedHome.query
                    .filter_by(user_id=current_user.id, listing_id=L.id).first()
                    is not None)
    return render_template("listing_detail.html", listing=L, similar=similar,
                           is_saved=is_saved)


@app.route("/agents")
def agents_index():
    city = request.args.get("city", "")
    qs = Agent.query
    if city:
        qs = qs.filter(Agent.city.ilike(f"%{city}%"))
    agents = qs.order_by(Agent.sales_volume_usd.desc()).all()
    return render_template("agents.html", agents=agents, filter_city=city,
                           all_cities=sorted(set(a.city for a in Agent.query.all() if a.city)))


@app.route("/agents/<slug>")
def agent_detail(slug):
    a = Agent.query.filter_by(slug=slug).first()
    if not a:
        abort(404)
    listings = (Listing.query.filter_by(agent_id=a.id)
                .order_by(Listing.price.desc()).all())
    return render_template("agent_detail.html", agent=a, listings=listings)


@app.route("/search")
def search():
    q = request.args.get("q", "").strip()
    base = Listing.query
    base = filter_listings(base, request.args)
    results = search_listings(q, base_query=base)
    sort = request.args.get("sort", "")
    if sort:
        sort_listings(results, sort)
    listings = [L for L, _ in results]
    return render_template("search.html", q=q, listings=listings,
                           result_count=len(listings),
                           active_filters=dict(request.args),
                           sort=sort)


@app.route("/open-houses")
def open_houses():
    city = request.args.get("city", "")
    qs = Listing.query.filter(Listing.is_open_house == True)
    if city:
        qs = qs.filter(Listing.city.ilike(f"%{city}%"))
    listings = qs.order_by(Listing.open_house_date).all()
    all_cities = sorted(set(c[0] for c in db.session.query(Listing.city)
                            .filter(Listing.is_open_house == True).distinct()))
    return render_template("open_houses.html", listings=listings,
                           filter_city=city, all_cities=all_cities)


@app.route("/new-listings")
def new_listings():
    listings = (Listing.query.filter_by(is_new=True)
                .order_by(Listing.days_on_compass.asc()).all())
    return render_template("new_listings.html", listings=listings)


@app.route("/luxury")
def luxury():
    listings = (Listing.query.filter_by(is_luxury=True)
                .order_by(Listing.price.desc()).all())
    return render_template("luxury.html", listings=listings)


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/help")
def help_page():
    return render_template("help.html")


# ─── Auth ─────────────────────────────────────────────────────────────────────


@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("account"))
    error = None
    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        pw = request.form.get("password") or ""
        u = User.query.filter_by(email=email).first()
        if not u or not u.check_password(pw):
            error = "Invalid email or password."
        else:
            login_user(u, remember=bool(request.form.get("remember")))
            return redirect(request.args.get("next") or url_for("account"))
    return render_template("login.html", error=error)


@app.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("account"))
    error = None
    if request.method == "POST":
        name = (request.form.get("name") or "").strip()
        email = (request.form.get("email") or "").strip().lower()
        pw = request.form.get("password") or ""
        pw2 = request.form.get("confirm") or ""
        if not name or not email or not pw:
            error = "Name, email and password are required."
        elif pw != pw2:
            error = "Passwords do not match."
        elif User.query.filter_by(email=email).first():
            error = "An account with this email already exists."
        else:
            u = User(name=name, email=email)
            u.set_password(pw)
            db.session.add(u)
            db.session.commit()
            login_user(u)
            return redirect(url_for("account"))
    return render_template("register.html", error=error)


@app.route("/logout", methods=["GET", "POST"])
def logout():
    logout_user()
    return redirect(url_for("index"))


# ─── Account ───────────────────────────────────────────────────────────────────


@app.route("/account")
@login_required
def account():
    saved = (SavedHome.query.filter_by(user_id=current_user.id)
             .order_by(SavedHome.saved_at.desc()).limit(4).all())
    tours = (Tour.query.filter_by(user_id=current_user.id)
             .order_by(Tour.requested_at.desc()).limit(3).all())
    inquiries = (Inquiry.query.filter_by(user_id=current_user.id)
                 .order_by(Inquiry.sent_at.desc()).limit(3).all())
    return render_template("account.html", user=current_user,
                           saved=saved, tours=tours, inquiries=inquiries)


@app.route("/account/edit", methods=["GET", "POST"])
@login_required
def account_edit():
    if request.method == "POST":
        current_user.name = (request.form.get("name") or "").strip() or current_user.name
        current_user.phone = (request.form.get("phone") or "").strip()
        current_user.city = (request.form.get("city") or "").strip()
        current_user.state = (request.form.get("state") or "").strip()
        db.session.commit()
        flash("Profile updated.", "success")
        return redirect(url_for("account"))
    return render_template("account_edit.html", user=current_user)


@app.route("/account/change-password", methods=["GET", "POST"])
@login_required
def change_password():
    error = None
    if request.method == "POST":
        cur = request.form.get("current") or ""
        new = request.form.get("new") or ""
        new2 = request.form.get("confirm") or ""
        if not current_user.check_password(cur):
            error = "Current password is incorrect."
        elif new != new2:
            error = "New passwords do not match."
        elif len(new) < 6:
            error = "Password must be at least 6 characters."
        else:
            current_user.set_password(new)
            db.session.commit()
            flash("Password updated.", "success")
            return redirect(url_for("account"))
    return render_template("change_password.html", error=error)


@app.route("/account/preferences", methods=["GET", "POST"])
@login_required
def preferences():
    if request.method == "POST":
        try:
            current_user.budget_min = int(request.form.get("budget_min") or 0)
            current_user.budget_max = int(request.form.get("budget_max") or 0)
            current_user.beds_min = int(request.form.get("beds_min") or 0)
        except ValueError:
            current_user.budget_min = current_user.budget_min or 0
        types = request.form.getlist("property_types")
        current_user.preferred_property_types = json.dumps(types)
        current_user.move_timeline = request.form.get("move_timeline") or ""
        current_user.has_agent = bool(request.form.get("has_agent"))
        current_user.receive_alerts = bool(request.form.get("receive_alerts"))
        db.session.commit()
        flash("Preferences updated.", "success")
        return redirect(url_for("preferences"))
    return render_template("preferences.html", user=current_user)


# ─── Saved homes / searches / collections / tours / inquiries ──────────────────


@app.route("/saved")
@login_required
def saved_list():
    rows = (SavedHome.query.filter_by(user_id=current_user.id)
            .order_by(SavedHome.saved_at.desc()).all())
    return render_template("saved.html", saved=rows)


@app.route("/save/<int:listing_id>", methods=["POST"])
@login_required
def save_home(listing_id):
    L = Listing.query.get_or_404(listing_id)
    existing = SavedHome.query.filter_by(user_id=current_user.id,
                                         listing_id=L.id).first()
    if not existing:
        db.session.add(SavedHome(user_id=current_user.id, listing_id=L.id))
        db.session.commit()
        flash(f"Saved {L.address}.", "success")
    return redirect(request.referrer or url_for("listing_detail", slug=L.slug))


@app.route("/unsave/<int:listing_id>", methods=["POST"])
@login_required
def unsave_home(listing_id):
    row = SavedHome.query.filter_by(user_id=current_user.id,
                                    listing_id=listing_id).first()
    if row:
        db.session.delete(row)
        db.session.commit()
        flash("Removed from saved homes.", "info")
    return redirect(request.referrer or url_for("saved_list"))


@app.route("/saved-searches", methods=["GET", "POST"])
@login_required
def saved_searches():
    if request.method == "POST":
        name = (request.form.get("name") or "").strip()
        criteria = {
            "q": (request.form.get("q") or "").strip(),
            "city": (request.form.get("city") or "").strip(),
            "price_min": request.form.get("price_min") or "",
            "price_max": request.form.get("price_max") or "",
            "beds": request.form.get("beds") or "",
            "property_type": request.form.get("property_type") or "",
        }
        if name:
            ss = SavedSearch(user_id=current_user.id, name=name,
                             criteria_json=json.dumps(criteria))
            db.session.add(ss)
            db.session.commit()
            flash(f'Saved search "{name}".', "success")
        return redirect(url_for("saved_searches"))
    rows = (SavedSearch.query.filter_by(user_id=current_user.id)
            .order_by(SavedSearch.created_at.desc()).all())
    return render_template("saved_searches.html", searches=rows)


@app.route("/saved-searches/<int:ssid>/delete", methods=["POST"])
@login_required
def delete_saved_search(ssid):
    row = SavedSearch.query.filter_by(id=ssid, user_id=current_user.id).first_or_404()
    db.session.delete(row)
    db.session.commit()
    flash("Saved search deleted.", "info")
    return redirect(url_for("saved_searches"))


@app.route("/collections")
@login_required
def collections_index():
    rows = (Collection.query.filter_by(user_id=current_user.id)
            .order_by(Collection.created_at.desc()).all())
    return render_template("collections.html", collections=rows)


@app.route("/collections/new", methods=["GET", "POST"])
@login_required
def collection_new():
    if request.method == "POST":
        name = (request.form.get("name") or "").strip()
        if not name:
            flash("Collection name required.", "warning")
            return redirect(url_for("collection_new"))
        c = Collection(user_id=current_user.id, name=name,
                       description=(request.form.get("description") or "").strip(),
                       share_token=secrets.token_urlsafe(8))
        db.session.add(c)
        db.session.commit()
        return redirect(url_for("collection_detail", cid=c.id))
    return render_template("collection_new.html")


@app.route("/collections/<int:cid>")
@login_required
def collection_detail(cid):
    c = Collection.query.filter_by(id=cid, user_id=current_user.id).first_or_404()
    return render_template("collection_detail.html", collection=c,
                           listings=c.get_listings())


@app.route("/collections/<int:cid>/add/<int:listing_id>", methods=["POST"])
@login_required
def collection_add(cid, listing_id):
    c = Collection.query.filter_by(id=cid, user_id=current_user.id).first_or_404()
    L = Listing.query.get_or_404(listing_id)
    ids = c.get_listing_ids()
    if L.id not in ids:
        ids.append(L.id)
        c.set_listing_ids(ids)
        db.session.commit()
        flash(f'Added {L.address} to "{c.name}".', "success")
    return redirect(request.referrer or url_for("collection_detail", cid=c.id))


@app.route("/collections/<int:cid>/remove/<int:listing_id>", methods=["POST"])
@login_required
def collection_remove(cid, listing_id):
    c = Collection.query.filter_by(id=cid, user_id=current_user.id).first_or_404()
    ids = c.get_listing_ids()
    if listing_id in ids:
        ids.remove(listing_id)
        c.set_listing_ids(ids)
        db.session.commit()
    return redirect(url_for("collection_detail", cid=c.id))


@app.route("/collections/<int:cid>/delete", methods=["POST"])
@login_required
def collection_delete(cid):
    c = Collection.query.filter_by(id=cid, user_id=current_user.id).first_or_404()
    db.session.delete(c)
    db.session.commit()
    flash("Collection deleted.", "info")
    return redirect(url_for("collections_index"))


@app.route("/collections/share/<token>")
def collection_share(token):
    c = Collection.query.filter_by(share_token=token).first_or_404()
    return render_template("collection_share.html", collection=c,
                           listings=c.get_listings())


@app.route("/tours", methods=["GET"])
@login_required
def tours_list():
    rows = (Tour.query.filter_by(user_id=current_user.id)
            .order_by(Tour.requested_at.desc()).all())
    return render_template("tours.html", tours=rows)


@app.route("/tour/<int:listing_id>", methods=["GET", "POST"])
@login_required
def tour_request(listing_id):
    L = Listing.query.get_or_404(listing_id)
    if request.method == "POST":
        t = Tour(
            user_id=current_user.id, listing_id=L.id,
            requested_date=(request.form.get("date") or "").strip(),
            requested_time=(request.form.get("time") or "").strip(),
            tour_type=(request.form.get("tour_type") or "in-person").strip(),
            contact_phone=(request.form.get("phone") or current_user.phone),
            notes=(request.form.get("notes") or "").strip(),
            status="requested",
        )
        db.session.add(t)
        db.session.commit()
        flash(f"Tour requested for {L.address} on {t.requested_date}.", "success")
        return redirect(url_for("tours_list"))
    return render_template("tour_request.html", listing=L)


@app.route("/tour/<int:tour_id>/cancel", methods=["POST"])
@login_required
def tour_cancel(tour_id):
    t = Tour.query.filter_by(id=tour_id, user_id=current_user.id).first_or_404()
    t.status = "cancelled"
    db.session.commit()
    flash("Tour cancelled.", "info")
    return redirect(url_for("tours_list"))


@app.route("/inquiries", methods=["GET"])
@login_required
def inquiries_list():
    rows = (Inquiry.query.filter_by(user_id=current_user.id)
            .order_by(Inquiry.sent_at.desc()).all())
    return render_template("inquiries.html", inquiries=rows)


@app.route("/inquiry/<int:listing_id>", methods=["GET", "POST"])
def inquiry_send(listing_id):
    L = Listing.query.get_or_404(listing_id)
    if request.method == "POST":
        uid = current_user.id if current_user.is_authenticated else None
        i = Inquiry(
            user_id=uid, listing_id=L.id, agent_id=L.agent_id,
            name=(request.form.get("name") or (current_user.name if uid else "")),
            email=(request.form.get("email") or (current_user.email if uid else "")),
            phone=(request.form.get("phone") or ""),
            subject=(request.form.get("subject") or
                     f"Inquiry about {L.address}"),
            message=(request.form.get("message") or "").strip(),
        )
        db.session.add(i)
        db.session.commit()
        flash("Your message has been sent. The agent will reach out shortly.",
              "success")
        if uid:
            return redirect(url_for("inquiries_list"))
        return redirect(url_for("listing_detail", slug=L.slug))
    return render_template("inquiry_send.html", listing=L)


# ─── Misc ──────────────────────────────────────────────────────────────────────


@app.route("/_health")
def health():
    return {"ok": True, "site": "compass",
            "listings": Listing.query.count(),
            "users": User.query.count()}


# ─── Listing deep-dive pages ──────────────────────────────────────────────────


def _get_listing_or_404(slug):
    L = Listing.query.filter_by(slug=slug).first()
    if not L:
        abort(404)
    return L


@app.route("/listing/<slug>/photos")
def listing_photos(slug):
    L = _get_listing_or_404(slug)
    return render_template("listing_photos.html", listing=L,
                           gallery=L.get_gallery())


@app.route("/listing/<slug>/floor-plan")
def listing_floorplan(slug):
    L = _get_listing_or_404(slug)
    return render_template("listing_floorplan.html", listing=L)


@app.route("/listing/<slug>/video-tour")
def listing_video(slug):
    L = _get_listing_or_404(slug)
    return render_template("listing_video.html", listing=L)


@app.route("/listing/<slug>/price-history")
def listing_price_history(slug):
    L = _get_listing_or_404(slug)
    history = (PriceHistory.query.filter_by(listing_id=L.id)
               .order_by(PriceHistory.event_date.desc()).all())
    return render_template("listing_price_history.html", listing=L,
                           history=history)


@app.route("/listing/<slug>/walkscore")
def listing_walkscore(slug):
    L = _get_listing_or_404(slug)
    n = None
    if L.neighborhood:
        n = Neighborhood.query.filter_by(name=L.neighborhood,
                                         city=L.city).first()
    return render_template("listing_walkscore.html", listing=L, neighborhood=n)


@app.route("/listing/<slug>/schools")
def listing_schools(slug):
    L = _get_listing_or_404(slug)
    rows = (ListingSchool.query.filter_by(listing_id=L.id)
            .order_by(ListingSchool.distance_miles).all())
    pairs = []
    for r in rows:
        s = School.query.get(r.school_id)
        if s:
            pairs.append((s, r))
    return render_template("listing_schools.html", listing=L, schools=pairs)


@app.route("/listing/<slug>/neighborhood")
def listing_neighborhood(slug):
    L = _get_listing_or_404(slug)
    n = None
    if L.neighborhood:
        n = Neighborhood.query.filter_by(name=L.neighborhood,
                                         city=L.city).first()
    return render_template("listing_neighborhood.html", listing=L,
                           neighborhood=n)


@app.route("/listing/<slug>/contact-agent", methods=["GET", "POST"])
def listing_contact_agent(slug):
    L = _get_listing_or_404(slug)
    return redirect(url_for("inquiry_send", listing_id=L.id), code=307)


@app.route("/listing/<slug>/schedule-tour", methods=["GET", "POST"])
def listing_schedule_tour(slug):
    L = _get_listing_or_404(slug)
    if not current_user.is_authenticated:
        return redirect(url_for("login",
                                next=url_for("listing_schedule_tour", slug=slug)))
    return redirect(url_for("tour_request", listing_id=L.id), code=307)


# ─── Neighborhoods ────────────────────────────────────────────────────────────


@app.route("/neighborhoods")
def neighborhood_index():
    city = request.args.get("city", "")
    qs = Neighborhood.query
    if city:
        qs = qs.filter(Neighborhood.city.ilike(f"%{city}%"))
    rows = qs.order_by(Neighborhood.city, Neighborhood.name).all()
    all_cities = sorted(set(n.city for n in Neighborhood.query.all() if n.city))
    return render_template("neighborhood_index.html",
                           neighborhoods=rows, filter_city=city,
                           all_cities=all_cities)


@app.route("/neighborhood/<city_state>/<slug>")
def neighborhood_detail(city_state, slug):
    n = Neighborhood.query.filter_by(slug=slug).first()
    if not n:
        abort(404)
    listings = (Listing.query
                .filter_by(city=n.city, state=n.state, neighborhood=n.name,
                           status="for-sale")
                .order_by(Listing.price).limit(12).all())
    return render_template("neighborhood_detail.html",
                           neighborhood=n, listings=listings)


@app.route("/neighborhood/<city_state>/<slug>/subscribe", methods=["POST"])
def neighborhood_alert_subscribe(city_state, slug):
    n = Neighborhood.query.filter_by(slug=slug).first_or_404()
    email = (request.form.get("email") or "").strip().lower()
    if current_user.is_authenticated and not email:
        email = current_user.email
    if email:
        db.session.add(NeighborhoodAlertSubscription(
            user_id=current_user.id if current_user.is_authenticated else None,
            email=email, neighborhood_slug=n.slug,
            frequency=(request.form.get("frequency") or "weekly"),
            created_at=datetime.utcnow(),
        ))
        db.session.commit()
        flash(f"Alerts on for {n.name}. We'll email {email}.", "success")
    return redirect(url_for("neighborhood_detail",
                            city_state=city_state, slug=n.slug))


# ─── Sold homes ───────────────────────────────────────────────────────────────


@app.route("/sold-homes")
def sold_homes_index():
    pairs = sorted({(s.city, s.state) for s in SoldListing.query.all()
                    if s.city and s.state})
    counts = {(c, st): SoldListing.query.filter_by(city=c, state=st).count()
              for (c, st) in pairs}
    return render_template("sold_homes_index.html",
                           city_state_pairs=pairs, counts=counts)


@app.route("/sold-homes/<city_state>/")
def sold_homes_city(city_state):
    city, state = city_state_slug(city_state)
    if not city:
        abort(404)
    qs = SoldListing.query.filter_by(city=city, state=state)
    rows = qs.order_by(SoldListing.sold_date.desc()).all()
    return render_template("sold_homes_city.html",
                           city=city, state=state, city_slug=city_state,
                           sold=rows)


@app.route("/sold-home/<slug>")
def sold_home_detail(slug):
    s = SoldListing.query.filter_by(slug=slug).first_or_404()
    similar = (SoldListing.query
               .filter(SoldListing.id != s.id, SoldListing.city == s.city)
               .order_by(func.abs(SoldListing.sold_price - s.sold_price))
               .limit(4).all())
    return render_template("sold_home_detail.html", sold=s, similar=similar)


# ─── Market reports ───────────────────────────────────────────────────────────


@app.route("/market-reports")
def market_reports_index():
    pairs = sorted({(m.city, m.state) for m in MarketReport.query.all()
                    if m.city and m.state})
    return render_template("market_reports_index.html", city_state_pairs=pairs)


@app.route("/market-report/<city_state>/")
def market_report_detail(city_state):
    city, state = city_state_slug(city_state)
    if not city:
        abort(404)
    rows = (MarketReport.query
            .filter_by(city_slug=city_state)
            .order_by(MarketReport.month.desc()).all())
    if not rows:
        abort(404)
    latest = rows[0]
    return render_template("market_report_detail.html",
                           city=city, state=state, city_slug=city_state,
                           latest=latest, history=rows)


@app.route("/market-report/<city_state>/subscribe", methods=["POST"])
def market_report_subscribe(city_state):
    email = (request.form.get("email") or "").strip().lower()
    if current_user.is_authenticated and not email:
        email = current_user.email
    if email:
        db.session.add(MarketReportSubscription(
            user_id=current_user.id if current_user.is_authenticated else None,
            email=email, city_slug=city_state,
            created_at=datetime.utcnow(),
        ))
        db.session.commit()
        flash(f"You'll receive the {city_state} market report at {email}.",
              "success")
    return redirect(url_for("market_report_detail", city_state=city_state))


# ─── Agent extras ─────────────────────────────────────────────────────────────


@app.route("/agent/<slug>")
def agent_alias(slug):
    return redirect(url_for("agent_detail", slug=slug), code=301)


@app.route("/agent/<slug>/reviews", methods=["GET", "POST"])
def agent_reviews(slug):
    a = Agent.query.filter_by(slug=slug).first_or_404()
    error = None
    if request.method == "POST":
        if not current_user.is_authenticated:
            return redirect(url_for("login",
                                    next=url_for("agent_reviews", slug=slug)))
        try:
            rating = int(request.form.get("rating") or "5")
            rating = max(1, min(5, rating))
        except ValueError:
            rating = 5
        body = (request.form.get("body") or "").strip()
        title = (request.form.get("title") or "").strip()
        tx = (request.form.get("transaction_type") or "Buyer").strip()
        if not body:
            error = "Please share a few words about your experience."
        else:
            db.session.add(AgentReview(
                agent_id=a.id, user_id=current_user.id,
                reviewer_name=current_user.name,
                rating=rating, title=title, body=body,
                transaction_type=tx, created_at=datetime.utcnow(),
            ))
            db.session.commit()
            flash("Thanks — your review has been posted.", "success")
            return redirect(url_for("agent_reviews", slug=slug))
    reviews = (AgentReview.query.filter_by(agent_id=a.id)
               .order_by(AgentReview.created_at.desc()).all())
    avg = (sum(r.rating for r in reviews) / len(reviews)) if reviews else 0
    return render_template("agent_reviews.html", agent=a,
                           reviews=reviews, avg_rating=avg, error=error)


@app.route("/agent/<slug>/sold")
def agent_sold(slug):
    a = Agent.query.filter_by(slug=slug).first_or_404()
    sold = (SoldListing.query.filter_by(agent_id=a.id)
            .order_by(SoldListing.sold_date.desc()).all())
    return render_template("agent_sold.html", agent=a, sold=sold)


@app.route("/agent/<slug>/awards")
def agent_awards(slug):
    a = Agent.query.filter_by(slug=slug).first_or_404()
    awards = (AgentAward.query.filter_by(agent_id=a.id)
              .order_by(AgentAward.year.desc()).all())
    return render_template("agent_awards.html", agent=a, awards=awards)


# ─── Teams & Offices ──────────────────────────────────────────────────────────


@app.route("/teams")
def teams_index():
    rows = Team.query.order_by(Team.sales_volume_usd.desc()).all()
    return render_template("teams_index.html", teams=rows)


@app.route("/team/<slug>")
def team_detail(slug):
    t = Team.query.filter_by(slug=slug).first_or_404()
    members = []
    for tm in TeamMember.query.filter_by(team_id=t.id).all():
        a = Agent.query.get(tm.agent_id)
        if a:
            members.append((a, tm.role))
    lead = Agent.query.get(t.lead_agent_id) if t.lead_agent_id else None
    listings = []
    if members:
        ids = [a.id for a, _ in members]
        listings = (Listing.query.filter(Listing.agent_id.in_(ids))
                    .order_by(Listing.price.desc()).limit(12).all())
    return render_template("team_detail.html", team=t, members=members,
                           lead=lead, listings=listings)


@app.route("/offices")
def offices_index():
    rows = Office.query.order_by(Office.state, Office.city, Office.name).all()
    return render_template("offices_index.html", offices=rows)


@app.route("/office/<slug>")
def office_detail(slug):
    o = Office.query.filter_by(slug=slug).first_or_404()
    agents = (Agent.query.filter_by(city=o.city, state=o.state)
              .order_by(Agent.sales_volume_usd.desc()).limit(12).all())
    return render_template("office_detail.html", office=o, agents=agents)


# ─── Buy / Sell hubs + Blog ───────────────────────────────────────────────────


@app.route("/buy/<city_state>/")
def buy_city_hub(city_state):
    city, state = city_state_slug(city_state)
    if not city:
        abort(404)
    qs = Listing.query.filter_by(city=city, state=state, status="for-sale")
    total = qs.count()
    featured = qs.order_by(Listing.price.desc()).limit(3).all()
    new_listings_in_city = (qs.filter_by(is_new=True)
                            .order_by(Listing.id.desc()).limit(4).all())
    open_houses_in_city = (qs.filter_by(is_open_house=True)
                           .order_by(Listing.open_house_date).limit(4).all())
    nbhd = (Neighborhood.query.filter_by(city=city, state=state)
            .order_by(Neighborhood.median_sale_price.desc()).limit(6).all())
    report = (MarketReport.query.filter_by(city_slug=city_state)
              .order_by(MarketReport.month.desc()).first())
    return render_template("buy_city_hub.html",
                           city=city, state=state, city_slug=city_state,
                           total=total, featured=featured,
                           new_in_city=new_listings_in_city,
                           open_houses_in_city=open_houses_in_city,
                           neighborhoods=nbhd, report=report)


@app.route("/sell")
def sell_hub():
    return render_template("sell_hub.html")


@app.route("/sell/evaluate-home", methods=["GET", "POST"])
def sell_evaluate():
    if request.method == "POST":
        try:
            beds = int(request.form.get("beds") or 0)
            baths = float(request.form.get("baths") or 0)
            sqft = int(request.form.get("sqft") or 0)
        except ValueError:
            beds, baths, sqft = 0, 0.0, 0
        addr = (request.form.get("address") or "").strip()
        city = (request.form.get("city") or "").strip()
        state = (request.form.get("state") or "").strip()
        # Lightweight estimate: $/sqft baseline by state with a beds bonus.
        baseline = {"CA": 750, "NY": 950, "FL": 420, "MA": 600, "TX": 280,
                    "WA": 580, "CO": 520, "IL": 350, "DC": 700}.get(state, 380)
        est = max(150_000, sqft * baseline + beds * 25_000)
        ev = HomeEvaluation(
            user_id=current_user.id if current_user.is_authenticated else None,
            address=addr, city=city, state=state,
            zip=(request.form.get("zip") or ""),
            beds=beds, baths=baths, sqft=sqft,
            estimated_value=int(est),
            timeline=(request.form.get("timeline") or "3-6mo"),
            created_at=datetime.utcnow(),
        )
        db.session.add(ev)
        db.session.commit()
        flash(f"Your home is estimated at ${int(est):,}. A Compass agent will be in touch.",
              "success")
        return render_template("sell_evaluate.html", result=ev)
    return render_template("sell_evaluate.html", result=None)


@app.route("/sell/cma-report", methods=["GET", "POST"])
def sell_cma():
    if request.method == "POST":
        c = CMARequest(
            user_id=current_user.id if current_user.is_authenticated else None,
            address=(request.form.get("address") or "").strip(),
            city=(request.form.get("city") or "").strip(),
            state=(request.form.get("state") or "").strip(),
            contact_name=(request.form.get("name") or "").strip(),
            contact_email=(request.form.get("email") or "").strip().lower(),
            contact_phone=(request.form.get("phone") or "").strip(),
            notes=(request.form.get("notes") or "").strip(),
            created_at=datetime.utcnow(),
        )
        db.session.add(c)
        db.session.commit()
        flash("Thanks — your CMA report request is in. Expect a reply within one business day.",
              "success")
        return redirect(url_for("sell_cma"))
    return render_template("sell_cma.html")


@app.route("/blog")
def blog_index():
    cat = request.args.get("category", "")
    qs = BlogPost.query
    if cat:
        qs = qs.filter_by(category=cat)
    posts = qs.order_by(BlogPost.published_at.desc()).all()
    cats = sorted(set(p.category for p in BlogPost.query.all() if p.category))
    return render_template("blog_index.html", posts=posts, categories=cats,
                           filter_category=cat)


@app.route("/blog/<slug>")
def blog_post(slug):
    p = BlogPost.query.filter_by(slug=slug).first_or_404()
    related = (BlogPost.query.filter(BlogPost.id != p.id,
                                     BlogPost.category == p.category)
               .order_by(BlogPost.published_at.desc()).limit(3).all())
    return render_template("blog_post.html", post=p, related=related)


# ─── Calculators ──────────────────────────────────────────────────────────────


def _monthly_payment(P, rate_pct, term_years):
    n = term_years * 12
    if n <= 0:
        return 0
    r = (rate_pct or 0) / 100.0 / 12.0
    if r == 0:
        return int(round(P / n)) if n else 0
    pay = P * (r * (1 + r) ** n) / ((1 + r) ** n - 1)
    return int(round(pay))


@app.route("/mortgage-calculator", methods=["GET", "POST"])
def mortgage_calculator():
    result = None
    if request.method == "POST":
        try:
            home_price = int(request.form.get("home_price") or 0)
            down = int(request.form.get("down_payment") or 0)
            rate = float(request.form.get("rate_pct") or 6.5)
            term = int(request.form.get("term_years") or 30)
            tax = int(request.form.get("annual_tax") or 0)
            ins = int(request.form.get("annual_insurance") or 0)
            hoa = int(request.form.get("monthly_hoa") or 0)
        except ValueError:
            flash("Please enter valid numbers.", "warning")
            return redirect(url_for("mortgage_calculator"))
        principal = max(0, home_price - down)
        pi = _monthly_payment(principal, rate, term)
        total = pi + tax // 12 + ins // 12 + hoa
        result = {
            "home_price": home_price, "down_payment": down,
            "rate_pct": rate, "term_years": term,
            "principal_interest": pi,
            "monthly_tax": tax // 12,
            "monthly_insurance": ins // 12,
            "monthly_hoa": hoa,
            "monthly_total": total,
        }
        if request.form.get("save"):
            label = (request.form.get("label") or "Saved scenario").strip()
            db.session.add(MortgageScenario(
                user_id=current_user.id if current_user.is_authenticated else None,
                label=label,
                home_price=home_price, down_payment=down,
                rate_pct=rate, term_years=term,
                annual_tax=tax, annual_insurance=ins,
                monthly_hoa=hoa, monthly_payment=total,
                created_at=datetime.utcnow(),
            ))
            db.session.commit()
            flash(f'Scenario "{label}" saved.', "success")
    return render_template("mortgage_calculator.html", result=result)


@app.route("/affordability-calculator", methods=["GET", "POST"])
def affordability_calculator():
    result = None
    if request.method == "POST":
        try:
            income = int(request.form.get("annual_income") or 0)
            debts = int(request.form.get("monthly_debts") or 0)
            down = int(request.form.get("down_payment") or 0)
            rate = float(request.form.get("rate_pct") or 6.5)
        except ValueError:
            flash("Please enter valid numbers.", "warning")
            return redirect(url_for("affordability_calculator"))
        # 28/36 rule + simple amortization invert.
        max_monthly = int(income * 0.36 / 12) - debts
        max_monthly = max(0, max_monthly)
        # invert _monthly_payment to get principal:
        n = 30 * 12
        r = rate / 100.0 / 12.0
        if r > 0 and max_monthly > 0:
            principal = max_monthly * ((1 + r) ** n - 1) / (r * (1 + r) ** n)
        else:
            principal = max_monthly * n
        max_home = int(principal + down)
        result = {
            "annual_income": income, "monthly_debts": debts,
            "down_payment": down, "rate_pct": rate,
            "max_monthly_payment": max_monthly,
            "max_home_price": max_home,
        }
        if request.form.get("save"):
            db.session.add(AffordabilityResult(
                user_id=current_user.id if current_user.is_authenticated else None,
                annual_income=income, monthly_debts=debts, down_payment=down,
                rate_pct=rate, max_home_price=max_home,
                created_at=datetime.utcnow(),
            ))
            db.session.commit()
            flash(f"Result saved — you could afford up to ${max_home:,}.",
                  "success")
    return render_template("affordability_calculator.html", result=result)


@app.route("/closing-cost-calculator")
def closing_cost_calculator():
    return render_template("closing_cost_calculator.html")


# ─── Account extras: Notes / Offers / Share ───────────────────────────────────


@app.route("/myaccount/notes", methods=["GET", "POST"])
@login_required
def notes_index():
    if request.method == "POST":
        body = (request.form.get("body") or "").strip()
        lid = request.form.get("listing_id")
        if not body:
            flash("Note cannot be empty.", "warning")
        else:
            db.session.add(Note(
                user_id=current_user.id,
                listing_id=int(lid) if lid and lid.isdigit() else None,
                body=body, created_at=datetime.utcnow(),
            ))
            db.session.commit()
            flash("Note added.", "success")
        return redirect(url_for("notes_index"))
    rows = (Note.query.filter_by(user_id=current_user.id)
            .order_by(Note.created_at.desc()).all())
    return render_template("notes_index.html", notes=rows)


@app.route("/myaccount/notes/<int:nid>/delete", methods=["POST"])
@login_required
def note_delete(nid):
    n = Note.query.filter_by(id=nid, user_id=current_user.id).first_or_404()
    db.session.delete(n)
    db.session.commit()
    flash("Note removed.", "info")
    return redirect(url_for("notes_index"))


@app.route("/myaccount/offers")
@login_required
def offers_index():
    rows = (Offer.query.filter_by(user_id=current_user.id)
            .order_by(Offer.created_at.desc()).all())
    return render_template("offers_index.html", offers=rows)


@app.route("/listing/<int:listing_id>/offer", methods=["GET", "POST"])
@login_required
def offer_new(listing_id):
    L = Listing.query.get_or_404(listing_id)
    if request.method == "POST":
        try:
            amount = int(request.form.get("amount") or 0)
            earnest = int(request.form.get("earnest_money") or 0)
        except ValueError:
            amount, earnest = 0, 0
        o = Offer(
            user_id=current_user.id, listing_id=L.id,
            amount=amount, earnest_money=earnest,
            contingencies=(request.form.get("contingencies") or ""),
            close_date=(request.form.get("close_date") or ""),
            financing=(request.form.get("financing") or "Conventional"),
            notes=(request.form.get("notes") or "").strip(),
            status="submitted",
            created_at=datetime.utcnow(),
        )
        db.session.add(o)
        db.session.commit()
        flash(f"Offer of ${amount:,} submitted for {L.address}.", "success")
        return redirect(url_for("offers_index"))
    return render_template("offer_new.html", listing=L)


@app.route("/listing/<int:listing_id>/share", methods=["GET", "POST"])
def listing_share(listing_id):
    L = Listing.query.get_or_404(listing_id)
    if request.method == "POST":
        recipient = (request.form.get("recipient_email") or "").strip().lower()
        note = (request.form.get("note") or "").strip()
        # We record this as an inquiry-like artifact for benchmark verification.
        db.session.add(Inquiry(
            user_id=current_user.id if current_user.is_authenticated else None,
            listing_id=L.id, agent_id=L.agent_id,
            name="Listing share",
            email=recipient,
            phone="",
            subject=f"Shared listing: {L.address}",
            message=note or f"A friend shared this listing with you: {L.address}",
        ))
        db.session.commit()
        flash(f"Sent {L.address} to {recipient}.", "success")
        return redirect(url_for("listing_detail", slug=L.slug))
    return render_template("listing_share.html", listing=L)


@app.route("/collections/<int:cid>/invite", methods=["GET", "POST"])
@login_required
def collection_invite(cid):
    c = Collection.query.filter_by(id=cid, user_id=current_user.id).first_or_404()
    if request.method == "POST":
        em = (request.form.get("email") or "").strip().lower()
        if em:
            invited = c.get_invited_emails()
            if em not in invited:
                invited.append(em)
                c.invited_emails_json = json.dumps(invited)
                db.session.commit()
            flash(f"Invited {em} to view '{c.name}'.", "success")
        return redirect(url_for("collection_detail", cid=c.id))
    return render_template("collection_invite.html", collection=c)


# ─── Newsletter / Careers / Aliases ───────────────────────────────────────────


@app.route("/newsletter", methods=["GET", "POST"])
def newsletter():
    if request.method == "POST":
        em = (request.form.get("email") or "").strip().lower()
        nm = (request.form.get("name") or "").strip()
        ci = (request.form.get("city_interest") or "").strip()
        if em:
            existing = NewsletterSignup.query.filter_by(email=em).first()
            if not existing:
                db.session.add(NewsletterSignup(
                    email=em, name=nm, city_interest=ci,
                    created_at=datetime.utcnow(),
                ))
                db.session.commit()
            flash(f"You're subscribed at {em}.", "success")
        return redirect(url_for("newsletter"))
    return render_template("newsletter.html")


@app.route("/careers")
@app.route("/concierge")
@app.route("/private-exclusives")
def simple_landing():
    topic = request.path.strip("/").replace("-", " ").title()
    return render_template("simple_landing.html", topic=topic)


@app.route("/myaccount/saved-searches")
@login_required
def myaccount_saved_searches_alias():
    return redirect(url_for("saved_searches"), code=301)


@app.route("/myaccount/favorited")
@login_required
def myaccount_favorited_alias():
    return redirect(url_for("saved_list"), code=301)


@app.errorhandler(404)
def not_found(e):
    return render_template("404.html"), 404


@app.errorhandler(500)
def server_error(e):
    return render_template("500.html"), 500


# ─── Boot ──────────────────────────────────────────────────────────────────────


from seed_data import seed_database, seed_benchmark_users  # noqa: E402
from seed_extras import seed_extras_all  # noqa: E402


def _normalize_seed_db_layout():
    """Re-emit CREATE INDEX statements in alpha order + VACUUM so a fresh
    rebuild produces byte-identical sqlite output. Without this, SQLAlchemy
    emits CREATE INDEX in `Table.indexes` set order, which depends on Python
    `id()` allocation and varies between processes. See harden-env gotcha #2.
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
    fresh = not os.path.exists(os.path.join(BASE_DIR, "instance", "compass.db"))
    db.create_all()
    seed_database()
    seed_benchmark_users()
    seed_extras_all()
    if fresh:
        _normalize_seed_db_layout()


if __name__ == "__main__":
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

