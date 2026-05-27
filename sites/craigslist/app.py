"""Craigslist mirror - Flask app."""
import hashlib
import json
import os
import re
from datetime import datetime, timedelta

from flask import Flask, abort, flash, redirect, render_template, request, Response, session, url_for
from flask_login import LoginManager, UserMixin, current_user, login_required, login_user, logout_user
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import or_, text

from seed_data import (
    CATEGORY_GROUPS,
    FORUM_BOARDS,
    HELP_TOPICS,
    NEIGHBORHOOD_HUBS,
    SAFETY_TIPS,
    SCAM_PATTERNS,
    SYSTEM_STATUS_ENTRIES,
    deterministic_password,
    seed_benchmark_users,
    seed_database,
    seed_forum_content,
)


BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__, instance_path=os.path.join(BASE_DIR, "instance"))
app.config["SECRET_KEY"] = "webharbor-craigslist-dev-key"
app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{os.path.join(BASE_DIR, 'instance', 'craigslist.db')}"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

os.makedirs(os.path.join(BASE_DIR, "instance"), exist_ok=True)

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = "login"
login_manager.login_message_category = "info"


class User(db.Model, UserMixin):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(140), unique=True, nullable=False, index=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    name = db.Column(db.String(120), nullable=False)
    area = db.Column(db.String(80), default="san francisco")
    phone = db.Column(db.String(40), default="")
    password_hash = db.Column(db.String(120), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    listings = db.relationship("Listing", backref="owner", lazy=True)
    saved_listings = db.relationship("SavedListing", backref="user", cascade="all, delete-orphan")
    saved_searches = db.relationship("SavedSearch", backref="user", cascade="all, delete-orphan")
    messages = db.relationship("Message", backref="user", cascade="all, delete-orphan")

    def set_password(self, password):
        self.password_hash = deterministic_password(self.email, password)

    def check_password(self, password):
        return self.password_hash == deterministic_password(self.email, password)


class Category(db.Model):
    __tablename__ = "categories"

    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(80), unique=True, nullable=False, index=True)
    name = db.Column(db.String(120), nullable=False)
    abbrev = db.Column(db.String(20), default="")
    group_slug = db.Column(db.String(50), index=True)
    group_name = db.Column(db.String(80), default="")
    display_order = db.Column(db.Integer, default=0)

    listings = db.relationship("Listing", backref="category", lazy=True)


class Listing(db.Model):
    __tablename__ = "listings"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(220), nullable=False, index=True)
    slug = db.Column(db.String(240), unique=True, nullable=False, index=True)
    category_id = db.Column(db.Integer, db.ForeignKey("categories.id"), nullable=False)
    category_slug = db.Column(db.String(80), index=True)
    category_group = db.Column(db.String(50), index=True)
    area = db.Column(db.String(80), index=True)
    neighborhood = db.Column(db.String(120), default="")
    price = db.Column(db.Integer, nullable=True, index=True)
    bedrooms = db.Column(db.Integer, nullable=True)
    sqft = db.Column(db.Integer, nullable=True)
    condition = db.Column(db.String(60), default="")
    compensation = db.Column(db.String(120), default="")
    company = db.Column(db.String(140), default="")
    employment_type = db.Column(db.String(80), default="")
    description = db.Column(db.Text, default="")
    details_json = db.Column(db.Text, default="{}")
    image = db.Column(db.String(260), default="")
    seller_name = db.Column(db.String(120), default="craigslist user")
    seller_email = db.Column(db.String(160), default="")
    reply_phone = db.Column(db.String(40), default="")
    owner_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    posted_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(40), default="active")
    view_count = db.Column(db.Integer, default=0)
    flag_count = db.Column(db.Integer, default=0)

    saved_by = db.relationship("SavedListing", backref="listing", cascade="all, delete-orphan")
    messages = db.relationship("Message", backref="listing", cascade="all, delete-orphan")

    def details(self):
        try:
            return json.loads(self.details_json or "{}")
        except json.JSONDecodeError:
            return {}

    @property
    def display_price(self):
        if self.price is None:
            return self.compensation or ""
        if self.price == 0:
            return "free"
        return f"${self.price:,}"

    @property
    def age_label(self):
        delta = datetime(2026, 5, 12, 15, 0, 0) - self.posted_at
        hours = max(1, int(delta.total_seconds() // 3600))
        if hours < 24:
            return f"{hours}h ago"
        return f"{hours // 24}d ago"


class SavedListing(db.Model):
    __tablename__ = "saved_listings"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    listing_id = db.Column(db.Integer, db.ForeignKey("listings.id"), nullable=False)
    note = db.Column(db.String(240), default="")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class SavedSearch(db.Model):
    __tablename__ = "saved_searches"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    name = db.Column(db.String(120), nullable=False)
    query_text = db.Column(db.String(180), default="")
    category_slug = db.Column(db.String(80), default="")
    area = db.Column(db.String(80), default="")
    min_price = db.Column(db.Integer, nullable=True)
    max_price = db.Column(db.Integer, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class HiddenListing(db.Model):
    __tablename__ = "hidden_listings"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    listing_id = db.Column(db.Integer, db.ForeignKey("listings.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Message(db.Model):
    __tablename__ = "messages"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    listing_id = db.Column(db.Integer, db.ForeignKey("listings.id"), nullable=False)
    sender_name = db.Column(db.String(120), default="")
    sender_email = db.Column(db.String(160), default="")
    body = db.Column(db.Text, default="")
    direction = db.Column(db.String(20), default="outbound")
    is_read = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class AbuseReport(db.Model):
    __tablename__ = "abuse_reports"

    id = db.Column(db.Integer, primary_key=True)
    listing_id = db.Column(db.Integer, db.ForeignKey("listings.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    reason = db.Column(db.String(80), default="other")
    body = db.Column(db.Text, default="")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class ContactInquiry(db.Model):
    __tablename__ = "contact_inquiries"

    id = db.Column(db.Integer, primary_key=True)
    topic = db.Column(db.String(80), default="general")
    sender_name = db.Column(db.String(120), default="")
    sender_email = db.Column(db.String(160), default="")
    body = db.Column(db.Text, default="")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class ForumThread(db.Model):
    __tablename__ = "forum_threads"

    id = db.Column(db.Integer, primary_key=True)
    board_slug = db.Column(db.String(60), index=True, nullable=False)
    title = db.Column(db.String(200), nullable=False)
    author_name = db.Column(db.String(120), default="cl user")
    author_email = db.Column(db.String(160), default="")
    body = db.Column(db.Text, default="")
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    is_pinned = db.Column(db.Boolean, default=False)
    view_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)

    replies = db.relationship("ForumReply", backref="thread", cascade="all, delete-orphan")


class ForumReply(db.Model):
    __tablename__ = "forum_replies"

    id = db.Column(db.Integer, primary_key=True)
    thread_id = db.Column(db.Integer, db.ForeignKey("forum_threads.id"), nullable=False)
    author_name = db.Column(db.String(120), default="cl user")
    author_email = db.Column(db.String(160), default="")
    body = db.Column(db.Text, default="")
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


def slugify(value):
    value = value.lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-") or "listing"


def tokenize(value):
    return [t for t in re.split(r"[^a-z0-9]+", (value or "").lower()) if len(t) > 1]


def normalize_phrase(value):
    return " ".join(t for t in re.split(r"[^a-z0-9]+", (value or "").lower()) if t)


def parse_int(value):
    if value is None or value == "":
        return None
    try:
        return int(re.sub(r"[^0-9]", "", str(value)))
    except ValueError:
        return None


def listing_score(listing, query):
    tokens = tokenize(query)
    if not tokens:
        return 1
    category = listing.category.name if listing.category else ""
    details = " ".join(f"{k} {v}" for k, v in listing.details().items())
    haystacks = {
        "title": listing.title.lower(),
        "category": category.lower(),
        "area": f"{listing.area} {listing.neighborhood}".lower(),
        "body": f"{listing.description} {details} {listing.condition} {listing.compensation} {listing.company}".lower(),
    }
    score = 0
    phrase = normalize_phrase(query)
    normalized = {key: normalize_phrase(value) for key, value in haystacks.items()}
    if phrase:
        if phrase in normalized["title"]:
            score += 25
        if phrase in normalized["body"]:
            score += 10
    for token in tokens:
        if token in haystacks["title"]:
            score += 5
        if token in haystacks["category"]:
            score += 3
        if token in haystacks["area"]:
            score += 2
        if token in haystacks["body"]:
            score += 1
    return score


def category_groups():
    cats = {c.slug: c for c in Category.query.order_by(Category.display_order).all()}
    groups = []
    for group in CATEGORY_GROUPS:
        rows = []
        for slug, _name, _abbrev in group["columns"]:
            if slug in cats:
                rows.append(cats[slug])
        groups.append({"slug": group["slug"], "name": group["name"], "categories": rows})
    return groups


def hidden_listing_ids():
    if not current_user.is_authenticated:
        return set(session.get("hidden_listing_ids", []))
    return {h.listing_id for h in HiddenListing.query.filter_by(user_id=current_user.id).all()}


def is_saved(listing_id):
    if not current_user.is_authenticated:
        return False
    return SavedListing.query.filter_by(user_id=current_user.id, listing_id=listing_id).first() is not None


def listing_images(listing):
    details = listing.details()
    values = details.get("images", [])
    if isinstance(values, str):
        values = [values]
    images = []
    if listing.image:
        images.append(listing.image)
    for value in values:
        if value and value not in images:
            images.append(value)
    return images


def listing_map_point(listing):
    details = listing.details()
    try:
        x = float(details.get("map_x", 50))
        y = float(details.get("map_y", 50))
        lat = float(details.get("map_lat", 37.7749))
        lng = float(details.get("map_lng", -122.4194))
    except (TypeError, ValueError):
        digest = hashlib.md5(f"{listing.id}:{listing.neighborhood}".encode()).hexdigest()
        x = 18 + (int(digest[:2], 16) % 64)
        y = 16 + (int(digest[2:4], 16) % 58)
        lat = 37.7749
        lng = -122.4194
    return {
        "x": max(6, min(94, x)),
        "y": max(8, min(92, y)),
        "lat": lat,
        "lng": lng,
    }


def listing_public_details(listing):
    hidden = {"images", "map_x", "map_y", "map_lat", "map_lng"}
    return [
        (key, value)
        for key, value in listing.details().items()
        if key not in hidden
    ]


def base_listing_query(category_slug=None):
    query = Listing.query.filter_by(status="active")
    if category_slug:
        category = Category.query.filter_by(slug=category_slug).first_or_404()
        query = query.filter(Listing.category_slug == category.slug)
    return query


def filter_listings(category_slug=None):
    q = request.args.get("q", "").strip()
    area = request.args.get("area", "").strip()
    min_price = parse_int(request.args.get("min_price"))
    max_price = parse_int(request.args.get("max_price"))
    has_image = request.args.get("has_image") == "1"
    sort = request.args.get("sort", "relevance")
    include_hidden = request.args.get("include_hidden") == "1"

    query = base_listing_query(category_slug)
    if area:
        query = query.filter(or_(Listing.area == area, Listing.neighborhood.ilike(f"%{area}%")))
    if min_price is not None:
        query = query.filter(or_(Listing.price == None, Listing.price >= min_price))  # noqa: E711
    if max_price is not None:
        query = query.filter(or_(Listing.price == None, Listing.price <= max_price))  # noqa: E711
    if has_image:
        query = query.filter(Listing.image != "")

    listings = query.all()
    hidden_ids = hidden_listing_ids()
    if not include_hidden:
        listings = [listing for listing in listings if listing.id not in hidden_ids]

    if q:
        scored = [(listing_score(listing, q), listing) for listing in listings]
        listings = [listing for score, listing in scored if score > 0]
        listings.sort(key=lambda pair: (listing_score(pair, q), pair.posted_at), reverse=True)
    elif sort == "price_asc":
        listings.sort(key=lambda listing: (listing.price is None, listing.price or 0, -listing.posted_at.timestamp()))
    elif sort == "price_desc":
        listings.sort(key=lambda listing: (listing.price is None, -(listing.price or 0), -listing.posted_at.timestamp()))
    elif sort == "oldest":
        listings.sort(key=lambda listing: listing.posted_at)
    else:
        listings.sort(key=lambda listing: listing.posted_at, reverse=True)

    return listings


@app.context_processor
def inject_globals():
    def saved_count():
        if not current_user.is_authenticated:
            return 0
        return SavedListing.query.filter_by(user_id=current_user.id).count()

    return {
        "category_groups": category_groups,
        "is_saved": is_saved,
        "saved_count": saved_count,
        "listing_images": listing_images,
        "listing_map_point": listing_map_point,
        "listing_public_details": listing_public_details,
    }


@app.route("/")
def index():
    featured = Listing.query.filter(Listing.image != "", Listing.status == "active").order_by(Listing.posted_at.desc()).limit(8).all()
    recent = Listing.query.filter_by(status="active").order_by(Listing.posted_at.desc()).limit(12).all()
    counts = {
        category.slug: Listing.query.filter_by(category_slug=category.slug, status="active").count()
        for category in Category.query.all()
    }
    return render_template("index.html", featured=featured, recent=recent, counts=counts)


@app.route("/favicon.ico")
def favicon():
    return Response(status=204)


@app.route("/search")
def search():
    listings = filter_listings()
    return render_template(
        "search.html",
        listings=listings,
        category=None,
        query=request.args.get("q", "").strip(),
        areas=["san francisco", "east bay", "south bay", "peninsula", "north bay", "santa cruz"],
    )


@app.route("/search/<category_slug>")
def category_search(category_slug):
    category = Category.query.filter_by(slug=category_slug).first_or_404()
    listings = filter_listings(category_slug)
    return render_template(
        "search.html",
        listings=listings,
        category=category,
        query=request.args.get("q", "").strip(),
        areas=["san francisco", "east bay", "south bay", "peninsula", "north bay", "santa cruz"],
    )


@app.route("/d/<slug>/<int:listing_id>.html")
def listing_detail(slug, listing_id):
    listing = Listing.query.get_or_404(listing_id)
    if listing.slug != slug:
        return redirect(url_for("listing_detail", slug=listing.slug, listing_id=listing.id), code=301)
    listing.view_count += 1
    db.session.commit()
    nearby = Listing.query.filter(
        Listing.id != listing.id,
        Listing.category_slug == listing.category_slug,
        Listing.status == "active",
    ).order_by(Listing.posted_at.desc()).limit(6).all()
    return render_template("listing_detail.html", listing=listing, nearby=nearby)


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            login_user(user)
            flash("logged in", "success")
            return redirect(request.args.get("next") or url_for("account"))
        flash("invalid email or password", "error")
    return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        username = request.form.get("username", "").strip().lower()
        name = request.form.get("name", "").strip() or username
        password = request.form.get("password", "")
        if not email or not username or not password:
            flash("email, username, and password are required", "error")
        elif User.query.filter(or_(User.email == email, User.username == username)).first():
            flash("that account already exists", "error")
        else:
            user = User(email=email, username=username, name=name, area=request.form.get("area", "san francisco"))
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            login_user(user)
            flash("account created", "success")
            return redirect(url_for("account"))
    return render_template("register.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("logged out", "info")
    return redirect(url_for("index"))


@app.route("/account")
@login_required
def account():
    posts = Listing.query.filter_by(owner_id=current_user.id).order_by(Listing.posted_at.desc()).all()
    searches = SavedSearch.query.filter_by(user_id=current_user.id).order_by(SavedSearch.created_at.desc()).all()
    messages = Message.query.filter_by(user_id=current_user.id).order_by(Message.created_at.desc()).limit(5).all()
    return render_template("account.html", posts=posts, searches=searches, messages=messages)


@app.route("/account/edit", methods=["GET", "POST"])
@login_required
def account_edit():
    if request.method == "POST":
        current_user.name = request.form.get("name", current_user.name).strip()
        current_user.area = request.form.get("area", current_user.area).strip()
        current_user.phone = request.form.get("phone", current_user.phone).strip()
        db.session.commit()
        flash("account updated", "success")
        return redirect(url_for("account"))
    return render_template("account_edit.html")


@app.route("/saved")
@login_required
def saved():
    rows = SavedListing.query.filter_by(user_id=current_user.id).order_by(SavedListing.created_at.desc()).all()
    return render_template("saved.html", rows=rows)


@app.route("/save-search", methods=["POST"])
@login_required
def save_search():
    name = request.form.get("name", "").strip() or "saved craigslist search"
    saved_search = SavedSearch(
        user_id=current_user.id,
        name=name,
        query_text=request.form.get("q", "").strip(),
        category_slug=request.form.get("category_slug", "").strip(),
        area=request.form.get("area", "").strip(),
        min_price=parse_int(request.form.get("min_price")),
        max_price=parse_int(request.form.get("max_price")),
    )
    db.session.add(saved_search)
    db.session.commit()
    flash("search saved", "success")
    return redirect(url_for("account"))


@app.route("/listing/<int:listing_id>/save", methods=["POST"])
@login_required
def save_listing(listing_id):
    listing = Listing.query.get_or_404(listing_id)
    existing = SavedListing.query.filter_by(user_id=current_user.id, listing_id=listing.id).first()
    if not existing:
        db.session.add(SavedListing(
            user_id=current_user.id,
            listing_id=listing.id,
            note=request.form.get("note", "").strip(),
        ))
        db.session.commit()
        flash("listing saved", "success")
    return redirect(request.form.get("next") or url_for("listing_detail", slug=listing.slug, listing_id=listing.id))


@app.route("/listing/<int:listing_id>/unsave", methods=["POST"])
@login_required
def unsave_listing(listing_id):
    saved_row = SavedListing.query.filter_by(user_id=current_user.id, listing_id=listing_id).first()
    if saved_row:
        db.session.delete(saved_row)
        db.session.commit()
        flash("listing removed", "info")
    return redirect(request.form.get("next") or url_for("saved"))


@app.route("/listing/<int:listing_id>/hide", methods=["POST"])
def hide_listing(listing_id):
    listing = Listing.query.get_or_404(listing_id)
    if current_user.is_authenticated:
        existing = HiddenListing.query.filter_by(user_id=current_user.id, listing_id=listing.id).first()
        if not existing:
            db.session.add(HiddenListing(user_id=current_user.id, listing_id=listing.id))
            db.session.commit()
    else:
        ids = set(session.get("hidden_listing_ids", []))
        ids.add(listing.id)
        session["hidden_listing_ids"] = sorted(ids)
    flash("listing hidden", "info")
    return redirect(request.form.get("next") or url_for("search"))


@app.route("/listing/<int:listing_id>/flag", methods=["POST"])
def flag_listing(listing_id):
    listing = Listing.query.get_or_404(listing_id)
    listing.flag_count += 1
    db.session.commit()
    flash("thanks for flagging", "info")
    return redirect(url_for("listing_detail", slug=listing.slug, listing_id=listing.id))


@app.route("/reply/<int:listing_id>", methods=["GET", "POST"])
def reply(listing_id):
    listing = Listing.query.get_or_404(listing_id)
    if request.method == "POST":
        name = request.form.get("name", "").strip() or (current_user.name if current_user.is_authenticated else "craigslist user")
        email = request.form.get("email", "").strip() or (current_user.email if current_user.is_authenticated else "anonymous@example.test")
        body = request.form.get("body", "").strip()
        if not body:
            flash("message body is required", "error")
        else:
            db.session.add(Message(
                user_id=current_user.id if current_user.is_authenticated else None,
                listing_id=listing.id,
                sender_name=name,
                sender_email=email,
                body=body,
                direction="outbound",
                is_read=True,
            ))
            db.session.commit()
            flash("reply sent", "success")
            return redirect(url_for("listing_detail", slug=listing.slug, listing_id=listing.id))
    return render_template("reply.html", listing=listing)


@app.route("/messages")
@login_required
def messages():
    rows = Message.query.filter_by(user_id=current_user.id).order_by(Message.created_at.desc()).all()
    unread = Message.query.filter_by(user_id=current_user.id, is_read=False).all()
    for row in unread:
        row.is_read = True
    db.session.commit()
    return render_template("messages.html", rows=rows)


@app.route("/post", methods=["GET", "POST"])
@login_required
def post_listing():
    categories = Category.query.order_by(Category.group_slug, Category.display_order).all()
    if request.method == "POST":
        category = Category.query.filter_by(slug=request.form.get("category_slug", "")).first()
        if not category:
            flash("choose a valid category", "error")
            return render_template("post.html", categories=categories)
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        if not title or not description:
            flash("title and description are required", "error")
            return render_template("post.html", categories=categories)
        details = {
            "posted_by": "owner",
            "availability": request.form.get("availability", "available now").strip(),
            "contact_preference": request.form.get("contact_preference", "email").strip(),
        }
        listing = Listing(
            title=title,
            slug=f"{slugify(title)}-{hashlib.md5((title + current_user.email).encode()).hexdigest()[:6]}",
            category_id=category.id,
            category_slug=category.slug,
            category_group=category.group_slug,
            area=request.form.get("area", current_user.area).strip(),
            neighborhood=request.form.get("neighborhood", "").strip(),
            price=parse_int(request.form.get("price")),
            bedrooms=parse_int(request.form.get("bedrooms")),
            sqft=parse_int(request.form.get("sqft")),
            condition=request.form.get("condition", "").strip(),
            compensation=request.form.get("compensation", "").strip(),
            company=request.form.get("company", "").strip(),
            employment_type=request.form.get("employment_type", "").strip(),
            description=description,
            details_json=json.dumps(details, sort_keys=True),
            seller_name=current_user.name,
            seller_email=current_user.email,
            reply_phone=current_user.phone,
            owner_id=current_user.id,
            status="active",
        )
        db.session.add(listing)
        db.session.commit()
        flash("posting published", "success")
        return redirect(url_for("listing_detail", slug=listing.slug, listing_id=listing.id))
    return render_template("post.html", categories=categories)


@app.route("/posting/<int:listing_id>/delete", methods=["POST"])
@login_required
def delete_posting(listing_id):
    listing = Listing.query.get_or_404(listing_id)
    if listing.owner_id != current_user.id:
        abort(403)
    listing.status = "deleted"
    db.session.commit()
    flash("posting deleted", "info")
    return redirect(url_for("account"))


# ---- post wizard (multi-step) ----

@app.route("/post/category")
@login_required
def post_choose_category():
    return render_template(
        "post_choose_category.html",
        groups=category_groups(),
    )


@app.route("/post/area")
@login_required
def post_choose_area():
    cat_slug = request.args.get("category_slug", "").strip()
    category = Category.query.filter_by(slug=cat_slug).first() if cat_slug else None
    return render_template(
        "post_choose_area.html",
        category=category,
        areas=AREAS,
        neighborhoods_by_area=NEIGHBORHOOD_HUBS,
    )


# ---- manage individual posting ----

@app.route("/manage/<int:listing_id>")
@login_required
def manage_posting(listing_id):
    listing = Listing.query.get_or_404(listing_id)
    if listing.owner_id != current_user.id:
        abort(403)
    return render_template("manage.html", listing=listing)


@app.route("/manage/<int:listing_id>/edit", methods=["GET", "POST"])
@login_required
def edit_posting(listing_id):
    listing = Listing.query.get_or_404(listing_id)
    if listing.owner_id != current_user.id:
        abort(403)
    categories = Category.query.order_by(Category.group_slug, Category.display_order).all()
    if request.method == "POST":
        listing.title = request.form.get("title", listing.title).strip() or listing.title
        listing.description = request.form.get("description", listing.description).strip() or listing.description
        new_price = request.form.get("price", "")
        if new_price:
            listing.price = parse_int(new_price)
        new_area = request.form.get("area", "").strip()
        if new_area:
            listing.area = new_area
        new_neighborhood = request.form.get("neighborhood", "").strip()
        if new_neighborhood:
            listing.neighborhood = new_neighborhood
        new_condition = request.form.get("condition", "").strip()
        if new_condition:
            listing.condition = new_condition
        listing.updated_at = datetime.utcnow()
        db.session.commit()
        flash("posting updated", "success")
        return redirect(url_for("manage_posting", listing_id=listing.id))
    return render_template("manage_edit.html", listing=listing, categories=categories)


@app.route("/manage/<int:listing_id>/repost", methods=["POST"])
@login_required
def repost_listing(listing_id):
    listing = Listing.query.get_or_404(listing_id)
    if listing.owner_id != current_user.id:
        abort(403)
    listing.status = "active"
    listing.posted_at = datetime.utcnow()
    listing.updated_at = datetime.utcnow()
    db.session.commit()
    flash("posting reposted", "success")
    return redirect(url_for("manage_posting", listing_id=listing.id))


@app.route("/manage/<int:listing_id>/extend", methods=["POST"])
@login_required
def extend_listing(listing_id):
    listing = Listing.query.get_or_404(listing_id)
    if listing.owner_id != current_user.id:
        abort(403)
    listing.updated_at = datetime.utcnow() + timedelta(days=7)
    db.session.commit()
    flash("posting extended by 7 days", "success")
    return redirect(url_for("manage_posting", listing_id=listing.id))


# ---- account: password, delete, alias ----

@app.route("/account/password", methods=["GET", "POST"])
@login_required
def account_password():
    if request.method == "POST":
        current = request.form.get("current_password", "")
        new = request.form.get("new_password", "")
        confirm = request.form.get("confirm_password", "")
        if not current_user.check_password(current):
            flash("current password is incorrect", "error")
        elif not new or new != confirm:
            flash("new password does not match the confirmation", "error")
        else:
            current_user.set_password(new)
            db.session.commit()
            flash("password updated", "success")
            return redirect(url_for("account"))
    return render_template("account_password.html")


@app.route("/account/delete", methods=["POST"])
@login_required
def account_delete():
    confirm = request.form.get("confirm", "")
    if confirm.strip().lower() != "delete":
        flash("type the word delete to confirm", "error")
        return redirect(url_for("account_edit"))
    user = current_user
    logout_user()
    db.session.delete(user)
    db.session.commit()
    flash("account deleted", "info")
    return redirect(url_for("index"))


@app.route("/myaccount")
def myaccount_alias():
    if current_user.is_authenticated:
        return redirect(url_for("account"))
    return redirect(url_for("login", next=url_for("account")))


@app.route("/myaccount/posts")
@login_required
def myaccount_posts():
    posts = Listing.query.filter_by(owner_id=current_user.id).order_by(Listing.posted_at.desc()).all()
    return render_template("myaccount_posts.html", posts=posts)


@app.route("/myaccount/favorites")
@login_required
def myaccount_favorites():
    return redirect(url_for("saved"))


# ---- saved search delete, message delete, listing unhide ----

@app.route("/saved-search/<int:search_id>/delete", methods=["POST"])
@login_required
def delete_saved_search(search_id):
    row = SavedSearch.query.filter_by(id=search_id, user_id=current_user.id).first_or_404()
    db.session.delete(row)
    db.session.commit()
    flash("saved search removed", "info")
    return redirect(url_for("account"))


@app.route("/messages/<int:message_id>/delete", methods=["POST"])
@login_required
def delete_message(message_id):
    row = Message.query.filter_by(id=message_id, user_id=current_user.id).first_or_404()
    db.session.delete(row)
    db.session.commit()
    flash("message removed", "info")
    return redirect(url_for("messages"))


@app.route("/listing/<int:listing_id>/unhide", methods=["POST"])
def unhide_listing(listing_id):
    listing = Listing.query.get_or_404(listing_id)
    if current_user.is_authenticated:
        row = HiddenListing.query.filter_by(user_id=current_user.id, listing_id=listing.id).first()
        if row:
            db.session.delete(row)
            db.session.commit()
    else:
        ids = set(session.get("hidden_listing_ids", []))
        if listing.id in ids:
            ids.discard(listing.id)
            session["hidden_listing_ids"] = sorted(ids)
    flash("listing restored", "info")
    return redirect(request.form.get("next") or url_for("search"))


# ---- alternate contact + abuse report ----

@app.route("/listing/<int:listing_id>/contact", methods=["GET", "POST"])
def contact_seller(listing_id):
    listing = Listing.query.get_or_404(listing_id)
    if request.method == "POST":
        name = request.form.get("name", "").strip() or (current_user.name if current_user.is_authenticated else "craigslist user")
        email = request.form.get("email", "").strip() or (current_user.email if current_user.is_authenticated else "anonymous@example.test")
        phone = request.form.get("phone", "").strip()
        body = request.form.get("body", "").strip()
        if not body:
            flash("message body is required", "error")
        else:
            db.session.add(Message(
                user_id=current_user.id if current_user.is_authenticated else None,
                listing_id=listing.id,
                sender_name=name,
                sender_email=email,
                body=f"[via contact form, phone: {phone}] {body}" if phone else body,
                direction="outbound",
                is_read=True,
            ))
            db.session.commit()
            flash("contact request sent", "success")
            return redirect(url_for("listing_detail", slug=listing.slug, listing_id=listing.id))
    return render_template("contact.html", listing=listing)


@app.route("/listing/<int:listing_id>/report", methods=["GET", "POST"])
def report_listing(listing_id):
    listing = Listing.query.get_or_404(listing_id)
    if request.method == "POST":
        reason = request.form.get("reason", "other").strip()
        body = request.form.get("body", "").strip()
        db.session.add(AbuseReport(
            listing_id=listing.id,
            user_id=current_user.id if current_user.is_authenticated else None,
            reason=reason,
            body=body,
        ))
        listing.flag_count += 1
        db.session.commit()
        flash("thank you, this posting has been reported", "success")
        return redirect(url_for("listing_detail", slug=listing.slug, listing_id=listing.id))
    return render_template("report.html", listing=listing)


# ---- city / area subhubs ----

AREAS = ["san francisco", "east bay", "south bay", "peninsula", "north bay", "santa cruz"]

AREA_SLUGS = {
    "sfc": "san francisco",
    "eby": "east bay",
    "sby": "south bay",
    "pen": "peninsula",
    "nby": "north bay",
    "scz": "santa cruz",
}


@app.route("/<area_slug>/sites")
def area_hub_alias(area_slug):
    area = AREA_SLUGS.get(area_slug.lower())
    if not area:
        abort(404)
    return redirect(url_for("area_hub", area_slug=area_slug.lower()))


@app.route("/area/<area_slug>")
def area_hub(area_slug):
    area = AREA_SLUGS.get(area_slug.lower())
    if not area:
        abort(404)
    counts = {}
    for cat in Category.query.all():
        counts[cat.slug] = Listing.query.filter_by(category_slug=cat.slug, area=area, status="active").count()
    featured = Listing.query.filter_by(area=area, status="active").filter(Listing.image != "").order_by(Listing.posted_at.desc()).limit(8).all()
    recent = Listing.query.filter_by(area=area, status="active").order_by(Listing.posted_at.desc()).limit(20).all()
    hubs = NEIGHBORHOOD_HUBS.get(area, [])
    return render_template("area_hub.html", area=area, area_slug=area_slug.lower(), counts=counts, featured=featured, recent=recent, hubs=hubs)


@app.route("/area/<area_slug>/<neighborhood_slug>")
def neighborhood_hub(area_slug, neighborhood_slug):
    area = AREA_SLUGS.get(area_slug.lower())
    if not area:
        abort(404)
    neighborhood = neighborhood_slug.replace("-", " ")
    listings = Listing.query.filter_by(area=area, status="active").filter(Listing.neighborhood.ilike(f"%{neighborhood}%")).order_by(Listing.posted_at.desc()).all()
    return render_template("neighborhood.html", area=area, neighborhood=neighborhood, listings=listings)


# ---- group hubs (for-sale / housing / jobs / services / community) ----

GROUP_PATH_ALIASES = {
    "for-sale": "for_sale",
    "for_sale": "for_sale",
    "housing": "housing",
    "jobs": "jobs",
    "services": "services",
    "community": "community",
}


@app.route("/group/<group_path>")
def group_hub(group_path):
    group_slug = GROUP_PATH_ALIASES.get(group_path.lower())
    if not group_slug:
        abort(404)
    group_meta = next((g for g in CATEGORY_GROUPS if g["slug"] == group_slug), None)
    if not group_meta:
        abort(404)
    cats = Category.query.filter_by(group_slug=group_slug).order_by(Category.display_order).all()
    counts = {c.slug: Listing.query.filter_by(category_slug=c.slug, status="active").count() for c in cats}
    featured = Listing.query.filter_by(category_group=group_slug, status="active").filter(Listing.image != "").order_by(Listing.posted_at.desc()).limit(8).all()
    return render_template("group_hub.html", group=group_meta, categories=cats, counts=counts, featured=featured)


@app.route("/<group_path>/sub/<sub_slug>")
def group_sub(group_path, sub_slug):
    group_slug = GROUP_PATH_ALIASES.get(group_path.lower())
    if not group_slug:
        abort(404)
    return redirect(url_for("category_search", category_slug=sub_slug))


@app.route("/jobs/cat/<sub_slug>")
def jobs_sub(sub_slug):
    return redirect(url_for("category_search", category_slug=sub_slug))


# ---- about / help / safety / legal ----

@app.route("/about")
def about():
    return render_template("about.html", topics=HELP_TOPICS)


@app.route("/about/help")
def about_help_index():
    return render_template("about_help_index.html", topics=HELP_TOPICS)


@app.route("/about/help/<topic>")
def about_help(topic):
    item = next((t for t in HELP_TOPICS if t["slug"] == topic), None)
    if not item:
        abort(404)
    return render_template("about_help.html", topic=item, topics=HELP_TOPICS)


@app.route("/about/legal")
def about_legal():
    return render_template("about_legal.html")


@app.route("/about/terms")
def about_terms():
    return render_template("about_terms.html")


@app.route("/about/privacy")
def about_privacy():
    return render_template("about_privacy.html")


@app.route("/about/system-status")
def about_system_status():
    return render_template("system_status.html", entries=SYSTEM_STATUS_ENTRIES)


@app.route("/about/best-of")
def about_best_of():
    listings = Listing.query.filter(Listing.image != "", Listing.status == "active").order_by(Listing.view_count.desc(), Listing.posted_at.desc()).limit(40).all()
    return render_template("best_of.html", listings=listings)


@app.route("/about/apps")
def about_apps():
    return render_template("apps.html")


@app.route("/about/contact", methods=["GET", "POST"])
def about_contact():
    if request.method == "POST":
        topic = request.form.get("topic", "general").strip()
        name = request.form.get("name", "").strip() or "anonymous"
        email = request.form.get("email", "").strip() or "anonymous@example.test"
        body = request.form.get("body", "").strip()
        if not body:
            flash("please describe your issue", "error")
        else:
            db.session.add(ContactInquiry(topic=topic, sender_name=name, sender_email=email, body=body))
            db.session.commit()
            flash("thanks, your note has been logged", "success")
            return redirect(url_for("about"))
    return render_template("about_contact.html")


@app.route("/safety")
def safety():
    return render_template("safety.html", tips=SAFETY_TIPS)


@app.route("/scams")
def scams():
    return render_template("scams.html", patterns=SCAM_PATTERNS)


# ---- discussion forums ----

@app.route("/discussion-forums")
def discussion_forums():
    boards = []
    for board in FORUM_BOARDS:
        thread_count = ForumThread.query.filter_by(board_slug=board["slug"]).count()
        latest = ForumThread.query.filter_by(board_slug=board["slug"]).order_by(ForumThread.updated_at.desc()).first()
        boards.append({"slug": board["slug"], "name": board["name"], "description": board["description"], "thread_count": thread_count, "latest": latest})
    return render_template("discussion_forums.html", boards=boards)


@app.route("/forum/<slug>")
def forum_board(slug):
    board = next((b for b in FORUM_BOARDS if b["slug"] == slug), None)
    if not board:
        abort(404)
    threads = ForumThread.query.filter_by(board_slug=slug).order_by(ForumThread.is_pinned.desc(), ForumThread.updated_at.desc()).all()
    return render_template("forum_board.html", board=board, threads=threads)


@app.route("/forum/<slug>/thread/<int:thread_id>")
def forum_thread_detail(slug, thread_id):
    thread = ForumThread.query.get_or_404(thread_id)
    if thread.board_slug != slug:
        return redirect(url_for("forum_thread_detail", slug=thread.board_slug, thread_id=thread.id), code=301)
    thread.view_count += 1
    db.session.commit()
    replies = ForumReply.query.filter_by(thread_id=thread.id).order_by(ForumReply.created_at.asc()).all()
    board = next((b for b in FORUM_BOARDS if b["slug"] == slug), None)
    return render_template("forum_thread.html", board=board, thread=thread, replies=replies)


@app.route("/forum/<slug>/new", methods=["GET", "POST"])
def forum_new_thread(slug):
    board = next((b for b in FORUM_BOARDS if b["slug"] == slug), None)
    if not board:
        abort(404)
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        body = request.form.get("body", "").strip()
        if not title or not body:
            flash("title and body are required", "error")
        else:
            thread = ForumThread(
                board_slug=slug,
                title=title,
                body=body,
                author_name=current_user.name if current_user.is_authenticated else (request.form.get("name", "").strip() or "anon"),
                author_email=current_user.email if current_user.is_authenticated else (request.form.get("email", "").strip() or "anon@example.test"),
                user_id=current_user.id if current_user.is_authenticated else None,
            )
            db.session.add(thread)
            db.session.commit()
            flash("thread posted", "success")
            return redirect(url_for("forum_thread_detail", slug=slug, thread_id=thread.id))
    return render_template("forum_new_thread.html", board=board)


@app.route("/forum/thread/<int:thread_id>/reply", methods=["POST"])
def forum_reply(thread_id):
    thread = ForumThread.query.get_or_404(thread_id)
    body = request.form.get("body", "").strip()
    if not body:
        flash("reply body is required", "error")
        return redirect(url_for("forum_thread_detail", slug=thread.board_slug, thread_id=thread.id))
    reply = ForumReply(
        thread_id=thread.id,
        body=body,
        author_name=current_user.name if current_user.is_authenticated else (request.form.get("name", "").strip() or "anon"),
        author_email=current_user.email if current_user.is_authenticated else (request.form.get("email", "").strip() or "anon@example.test"),
        user_id=current_user.id if current_user.is_authenticated else None,
    )
    thread.updated_at = datetime.utcnow()
    db.session.add(reply)
    db.session.commit()
    flash("reply posted", "success")
    return redirect(url_for("forum_thread_detail", slug=thread.board_slug, thread_id=thread.id))


# ---- generic simple landing fallbacks for craigslist.org links ----

@app.route("/jobs")
def jobs_alias():
    return redirect(url_for("group_hub", group_path="jobs"))


@app.route("/housing")
def housing_alias():
    return redirect(url_for("group_hub", group_path="housing"))


@app.route("/for-sale")
def forsale_alias():
    return redirect(url_for("group_hub", group_path="for-sale"))


@app.route("/services")
def services_alias():
    return redirect(url_for("group_hub", group_path="services"))


@app.route("/community")
def community_alias():
    return redirect(url_for("group_hub", group_path="community"))


@app.route("/_health")
def health():
    return {"ok": True, "site": "craigslist", "listings": Listing.query.count()}


with app.app_context():
    fresh_seed = not os.path.exists(os.path.join(BASE_DIR, "instance", "craigslist.db"))
    db.create_all()
    seed_database(BASE_DIR, db, Category, Listing)
    seed_benchmark_users(db, User, Listing, SavedListing, SavedSearch, Message)
    seed_forum_content(db, ForumThread, ForumReply, User)
    if fresh_seed:
        # Normalize index order + VACUUM so rebuilds on different machines match
        # byte-for-byte. See harden-env/gotchas.md §2.
        conn = db.engine.connect()
        idx_rows = conn.execute(text(
            "SELECT name, sql FROM sqlite_master WHERE type='index' AND name LIKE 'ix_%'"
        )).fetchall()
        for name, _sql in idx_rows:
            conn.execute(text(f"DROP INDEX IF EXISTS {name}"))
        for name, sql in sorted(idx_rows, key=lambda r: r[0]):
            if sql:
                conn.execute(text(sql))
        conn.execute(text("VACUUM"))
        conn.commit()
        conn.close()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)


# --- perf: long-term cache for /static/ assets (added 2026-05-27) ---
@app.after_request
def _add_static_cache_headers(resp):
    try:
        if request.path.startswith('/static/'):
            resp.headers.setdefault('Cache-Control', 'public, max-age=86400, immutable')
    except Exception:
        pass
    return resp
# --- end perf ---

