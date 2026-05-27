"""SmartAsset mirror — Flask + SQLAlchemy.

Mirrors smartasset.com: a personal-finance hub featuring 20+ deterministic
calculators (mortgage, paycheck, retirement, taxes, savings, ...), an advisor
matching multi-step wizard, ~80 SmartReads articles, per-state tax pages,
author bios, and lightweight auth + comments.

All math is implemented server-side in Python (see ``calc.py``) so agent
benchmarks get deterministic numeric output regardless of client JS.
"""
import os
import re
import math
import json
import hashlib
from datetime import datetime, timedelta
from functools import wraps
from collections import defaultdict

from flask import (Flask, render_template, request, redirect, url_for,
                   flash, jsonify, session, abort, g, make_response,
                   send_from_directory, Response)
from flask_sqlalchemy import SQLAlchemy
from flask_login import (LoginManager, UserMixin, login_user, logout_user,
                         login_required, current_user)
from flask_wtf.csrf import CSRFProtect, generate_csrf
from flask_bcrypt import Bcrypt
from sqlalchemy import or_, and_, func

import calc

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INSTANCE_DIR = os.path.join(BASE_DIR, "instance")
os.makedirs(INSTANCE_DIR, exist_ok=True)

app = Flask(__name__, instance_path=INSTANCE_DIR)
app.config["SECRET_KEY"] = "smartasset-webharbor-dev-secret-2026"
app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{os.path.join(INSTANCE_DIR, 'smartasset.db')}"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["WTF_CSRF_TIME_LIMIT"] = None

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
csrf = CSRFProtect(app)
login_manager = LoginManager(app)
login_manager.login_view = "login"
login_manager.login_message = "Please sign in to access this feature."


# ───────────────────────────────────────────────────────────
# Models
# ───────────────────────────────────────────────────────────

class User(db.Model, UserMixin):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(160), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    name = db.Column(db.String(120), nullable=False)
    state = db.Column(db.String(40), default="")
    zip_code = db.Column(db.String(10), default="")
    is_advisor = db.Column(db.Boolean, default=False)
    tax_filing_status = db.Column(db.String(20), default="single")  # single|married|head
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)

    def check_password_match(self, pw):
        try:
            return bcrypt.check_password_hash(self.password_hash, pw)
        except Exception:
            return False


class Author(db.Model):
    __tablename__ = "authors"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    slug = db.Column(db.String(140), unique=True, nullable=False, index=True)
    title = db.Column(db.String(140), default="")
    credentials = db.Column(db.String(60), default="")
    bio = db.Column(db.Text, default="")
    location = db.Column(db.String(80), default="")
    twitter = db.Column(db.String(40), default="")
    linkedin = db.Column(db.String(120), default="")
    articles = db.relationship("Article", backref="author", lazy="dynamic")


class Category(db.Model):
    __tablename__ = "categories"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    slug = db.Column(db.String(80), unique=True, nullable=False, index=True)
    blurb = db.Column(db.String(280), default="")
    articles = db.relationship("Article", backref="category", lazy="dynamic")


class Article(db.Model):
    __tablename__ = "articles"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(240), nullable=False, index=True)
    slug = db.Column(db.String(260), unique=True, nullable=False, index=True)
    dek = db.Column(db.String(400), default="")
    body = db.Column(db.Text, default="")
    hero_image = db.Column(db.String(160), default="")
    category_id = db.Column(db.Integer, db.ForeignKey("categories.id"), nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey("authors.id"), nullable=False)
    published_at = db.Column(db.Date, nullable=False)
    reading_minutes = db.Column(db.Integer, default=4)
    view_count = db.Column(db.Integer, default=0)
    related_calc = db.Column(db.String(60), default="")
    tags = db.Column(db.String(240), default="")

    comments = db.relationship("Comment", backref="article", lazy="dynamic",
                                cascade="all, delete-orphan")


class Comment(db.Model):
    __tablename__ = "comments"
    id = db.Column(db.Integer, primary_key=True)
    article_id = db.Column(db.Integer, db.ForeignKey("articles.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    body = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user = db.relationship("User", lazy="joined")


class State(db.Model):
    __tablename__ = "states"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(40), unique=True, nullable=False, index=True)
    abbr = db.Column(db.String(2), unique=True, nullable=False, index=True)
    slug = db.Column(db.String(60), unique=True, nullable=False, index=True)
    income_tax_type = db.Column(db.String(20), default="bracket")
    state_income_top_rate = db.Column(db.Float, default=0.0)
    state_income_flat_rate = db.Column(db.Float, default=0.0)
    property_tax_rate = db.Column(db.Float, default=0.0)
    sales_tax_rate = db.Column(db.Float, default=0.0)
    median_home_price = db.Column(db.Integer, default=0)
    median_household_income = db.Column(db.Integer, default=0)
    cost_of_living_index = db.Column(db.Float, default=100.0)
    top_metro = db.Column(db.String(120), default="")
    overview = db.Column(db.Text, default="")


class Advisor(db.Model):
    __tablename__ = "advisors"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    slug = db.Column(db.String(140), unique=True, nullable=False, index=True)
    firm = db.Column(db.String(180), nullable=False)
    city = db.Column(db.String(80), default="")
    state_abbr = db.Column(db.String(2), default="", index=True)
    credentials = db.Column(db.String(60), default="")
    years_experience = db.Column(db.Integer, default=10)
    aum_millions = db.Column(db.Integer, default=100)
    min_assets = db.Column(db.Integer, default=100_000)
    fee_structure = db.Column(db.String(60), default="Fee-only")
    specialty = db.Column(db.String(80), default="")
    bio = db.Column(db.Text, default="")
    fiduciary = db.Column(db.Boolean, default=True)
    rating = db.Column(db.Float, default=4.6)
    review_count = db.Column(db.Integer, default=0)


class SavedCalculation(db.Model):
    __tablename__ = "saved_calcs"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    calc_slug = db.Column(db.String(60), nullable=False)
    label = db.Column(db.String(140), default="")
    inputs_json = db.Column(db.Text, default="{}")
    summary = db.Column(db.String(240), default="")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class AdvisorMatch(db.Model):
    __tablename__ = "advisor_matches"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    email = db.Column(db.String(160), default="")
    state_abbr = db.Column(db.String(2), default="")
    investable_assets = db.Column(db.Integer, default=0)
    goal = db.Column(db.String(80), default="")
    age = db.Column(db.Integer, default=0)
    marital_status = db.Column(db.String(20), default="")
    matched_ids = db.Column(db.String(60), default="")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Newsletter(db.Model):
    __tablename__ = "newsletter"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(160), unique=True, nullable=False)
    subscribed_at = db.Column(db.DateTime, default=datetime.utcnow)


class ContactMessage(db.Model):
    __tablename__ = "contact_messages"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), default="")
    email = db.Column(db.String(160), default="")
    topic = db.Column(db.String(80), default="")
    body = db.Column(db.Text, default="")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class GlossaryTerm(db.Model):
    __tablename__ = "glossary_terms"
    id = db.Column(db.Integer, primary_key=True)
    term = db.Column(db.String(120), nullable=False, index=True)
    slug = db.Column(db.String(140), unique=True, nullable=False, index=True)
    letter = db.Column(db.String(1), nullable=False, index=True)
    short_def = db.Column(db.String(280), default="")
    long_def = db.Column(db.Text, default="")
    related_calc = db.Column(db.String(60), default="")
    related_category = db.Column(db.String(60), default="")


class City(db.Model):
    __tablename__ = "cities"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    slug = db.Column(db.String(120), unique=True, nullable=False, index=True)
    state_abbr = db.Column(db.String(2), index=True)
    population = db.Column(db.Integer, default=0)
    median_home_price = db.Column(db.Integer, default=0)
    median_rent = db.Column(db.Integer, default=0)
    median_household_income = db.Column(db.Integer, default=0)
    cost_of_living_index = db.Column(db.Float, default=100.0)
    crime_index = db.Column(db.Float, default=50.0)
    walk_score = db.Column(db.Integer, default=60)
    avg_property_tax_rate = db.Column(db.Float, default=1.0)
    overview = db.Column(db.Text, default="")


class Review(db.Model):
    """Firm / product review pages (Fidelity, Vanguard, Ally, etc.)."""
    __tablename__ = "reviews"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(140), nullable=False)
    slug = db.Column(db.String(160), unique=True, nullable=False, index=True)
    kind = db.Column(db.String(40), index=True)  # brokerage / bank / robo / lender / insurer / advisor-firm
    overall_rating = db.Column(db.Float, default=4.0)
    fees = db.Column(db.String(120), default="")
    minimum = db.Column(db.String(80), default="")
    pros = db.Column(db.Text, default="")  # newline-separated
    cons = db.Column(db.Text, default="")
    body = db.Column(db.Text, default="")
    headquarters = db.Column(db.String(120), default="")
    founded_year = db.Column(db.Integer, default=2000)


class ArticleVote(db.Model):
    """Per-user up/down on an article (one row per (user, article))."""
    __tablename__ = "article_votes"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    article_id = db.Column(db.Integer, db.ForeignKey("articles.id"),
                           nullable=False)
    direction = db.Column(db.Integer, default=1)  # 1 or -1
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    __table_args__ = (db.UniqueConstraint("user_id", "article_id",
                                          name="uq_user_article_vote"),)


class CommentReply(db.Model):
    __tablename__ = "comment_replies"
    id = db.Column(db.Integer, primary_key=True)
    parent_id = db.Column(db.Integer, db.ForeignKey("comments.id"),
                          nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    body = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user = db.relationship("User", lazy="joined")


class SavedAdvisor(db.Model):
    __tablename__ = "saved_advisors"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    advisor_id = db.Column(db.Integer, db.ForeignKey("advisors.id"),
                           nullable=False)
    notes = db.Column(db.String(280), default="")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    __table_args__ = (db.UniqueConstraint("user_id", "advisor_id",
                                          name="uq_user_advisor"),)


class ContactAdvisor(db.Model):
    __tablename__ = "contact_advisors"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    advisor_id = db.Column(db.Integer, db.ForeignKey("advisors.id"),
                           nullable=False)
    email = db.Column(db.String(160), default="")
    phone = db.Column(db.String(40), default="")
    message = db.Column(db.Text, default="")
    consult_requested = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class AskQuestion(db.Model):
    """User-submitted 'Ask an Advisor' questions."""
    __tablename__ = "ask_questions"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    email = db.Column(db.String(160), default="")
    topic = db.Column(db.String(80), default="")
    question = db.Column(db.Text, nullable=False)
    state_abbr = db.Column(db.String(2), default="")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class CalcFeedback(db.Model):
    __tablename__ = "calc_feedback"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    calc_slug = db.Column(db.String(60), nullable=False, index=True)
    rating = db.Column(db.Integer, default=5)  # 1-5
    body = db.Column(db.Text, default="")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class CalcEmail(db.Model):
    """Email-result events (the 'email this to me' button)."""
    __tablename__ = "calc_emails"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    calc_slug = db.Column(db.String(60), nullable=False)
    email = db.Column(db.String(160), nullable=False)
    inputs_json = db.Column(db.Text, default="{}")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class CategorySubscription(db.Model):
    __tablename__ = "category_subscriptions"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(160), nullable=False)
    category_slug = db.Column(db.String(60), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    __table_args__ = (db.UniqueConstraint("email", "category_slug",
                                          name="uq_email_category"),)


class Promo(db.Model):
    __tablename__ = "promos"
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(40), unique=True, nullable=False, index=True)
    description = db.Column(db.String(240), default="")
    discount_pct = db.Column(db.Integer, default=10)
    active = db.Column(db.Boolean, default=True)


class PromoApplication(db.Model):
    __tablename__ = "promo_applications"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    code = db.Column(db.String(40), nullable=False)
    accepted = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


# ───────────────────────────────────────────────────────────
# Helpers
# ───────────────────────────────────────────────────────────

CALC_HUB = calc.CALCULATORS


def slugify(s):
    s = re.sub(r"[^a-zA-Z0-9\s\-]", "", s or "").strip().lower()
    return re.sub(r"\s+", "-", s) or "x"


def fmt_money(n):
    try:
        n = float(n)
    except (TypeError, ValueError):
        return "$0"
    sign = "-" if n < 0 else ""
    n = abs(n)
    if n >= 1_000_000_000:
        return f"{sign}${n/1_000_000_000:.2f}B"
    if n >= 1_000_000:
        return f"{sign}${n/1_000_000:.2f}M"
    if n >= 100:
        return sign + "$" + f"{n:,.0f}"
    return sign + "$" + f"{n:,.2f}"


def fmt_pct(n, decimals=2):
    try:
        return f"{float(n):.{decimals}f}%"
    except (TypeError, ValueError):
        return "0%"


@login_manager.user_loader
def load_user(uid):
    return db.session.get(User, int(uid))


@app.context_processor
def inject_globals():
    return {
        "csrf_token": generate_csrf,
        "fmt_money": fmt_money,
        "fmt_pct": fmt_pct,
        "now": datetime.utcnow,
        "calc_hub": CALC_HUB,
    }


@app.template_filter("commafy")
def commafy(n):
    try:
        return f"{int(round(float(n))):,}"
    except (TypeError, ValueError):
        return n


@app.template_filter("money")
def money(n):
    return fmt_money(n)


@app.template_filter("pct")
def pct(n, d=2):
    return fmt_pct(n, d)


# ───────────────────────────────────────────────────────────
# Routes — home + meta
# ───────────────────────────────────────────────────────────

@app.route("/")
def index():
    featured = (Article.query.order_by(Article.published_at.desc())
                .limit(8).all())
    categories = Category.query.order_by(Category.name).all()
    top_calcs = [c for c in CALC_HUB if c.get("featured")]
    states = State.query.order_by(State.name).all()
    return render_template("index.html", featured=featured,
                            categories=categories,
                            top_calcs=top_calcs[:9], states=states)


@app.route("/calculators")
def calculators_index():
    groups = defaultdict(list)
    for c in CALC_HUB:
        groups[c["group"]].append(c)
    return render_template("calculators_index.html", groups=dict(groups))


@app.route("/calculators/<slug>", methods=["GET", "POST"])
def calculator(slug):
    spec = calc.find(slug)
    if not spec:
        abort(404)
    inputs, result, error = {}, None, None
    if request.method == "POST" or any(
            k in request.values for k in spec["fields"]):
        inputs = {k: request.values.get(k, "") for k in spec["fields"]}
        try:
            result = calc.run(slug, inputs)
        except calc.CalcError as e:
            error = str(e)
    related = [c for c in CALC_HUB if c["group"] == spec["group"]
               and c["slug"] != slug][:6]
    related_articles = (Article.query.filter(Article.related_calc == slug)
                        .limit(5).all())
    return render_template("calculator.html", spec=spec, inputs=inputs,
                            result=result, error=error,
                            related=related,
                            related_articles=related_articles)


@app.route("/api/calculate/<slug>", methods=["POST"])
@csrf.exempt
def api_calculate(slug):
    spec = calc.find(slug)
    if not spec:
        return jsonify({"error": "unknown_calculator"}), 404
    payload = request.get_json(silent=True) or request.form.to_dict()
    inputs = {k: payload.get(k, "") for k in spec["fields"]}
    try:
        result = calc.run(slug, inputs)
    except calc.CalcError as e:
        return jsonify({"error": str(e)}), 400
    return jsonify({"slug": slug, "inputs": inputs, "result": result})


@app.route("/save-calculation", methods=["POST"])
@login_required
def save_calculation():
    slug = request.form.get("calc_slug", "")
    spec = calc.find(slug)
    if not spec:
        abort(400)
    inputs = {k: request.form.get(k, "") for k in spec["fields"]}
    summary = ""
    try:
        result = calc.run(slug, inputs)
        summary = result.get("headline", "")
    except calc.CalcError:
        pass
    sc = SavedCalculation(
        user_id=current_user.id,
        calc_slug=slug,
        label=request.form.get("label", spec["title"]),
        inputs_json=json.dumps(inputs),
        summary=summary,
    )
    db.session.add(sc)
    db.session.commit()
    flash("Calculation saved to your account.", "success")
    return redirect(url_for("calculator", slug=slug, **inputs))


@app.route("/share/<slug>")
def share_calc(slug):
    spec = calc.find(slug)
    if not spec:
        abort(404)
    params = {k: request.args.get(k, "") for k in spec["fields"]
              if request.args.get(k, "")}
    return render_template("share.html", spec=spec, params=params,
                            share_url=url_for("calculator", slug=slug,
                                              _external=False, **params))


@app.route("/calculators/<slug>/print")
def print_calc(slug):
    spec = calc.find(slug)
    if not spec:
        abort(404)
    inputs = {k: request.args.get(k, "") for k in spec["fields"]}
    result = None
    if any(inputs.values()):
        try:
            result = calc.run(slug, inputs)
        except calc.CalcError:
            result = None
    return render_template("calculator_print.html", spec=spec,
                            inputs=inputs, result=result)


# ───────────────────────────────────────────────────────────
# Articles
# ───────────────────────────────────────────────────────────

@app.route("/smartreads")
def smartreads_index():
    page = max(1, request.args.get("page", 1, type=int))
    per = 12
    q = Article.query.order_by(Article.published_at.desc())
    total = q.count()
    articles = q.offset((page - 1) * per).limit(per).all()
    categories = Category.query.order_by(Category.name).all()
    return render_template("smartreads_index.html", articles=articles,
                            categories=categories, page=page,
                            pages=max(1, (total + per - 1) // per),
                            total=total)


@app.route("/smartreads/<slug>")
def article_detail(slug):
    art = Article.query.filter_by(slug=slug).first_or_404()
    related = (Article.query.filter(Article.category_id == art.category_id,
                                     Article.id != art.id)
               .order_by(Article.published_at.desc()).limit(5).all())
    related_calc = calc.find(art.related_calc) if art.related_calc else None
    return render_template("article_detail.html", a=art, related=related,
                            related_calc=related_calc)


@app.route("/category/<slug>")
def category_page(slug):
    cat = Category.query.filter_by(slug=slug).first_or_404()
    page = max(1, request.args.get("page", 1, type=int))
    per = 15
    q = (Article.query.filter_by(category_id=cat.id)
         .order_by(Article.published_at.desc()))
    total = q.count()
    articles = q.offset((page - 1) * per).limit(per).all()
    return render_template("category.html", cat=cat, articles=articles,
                            page=page,
                            pages=max(1, (total + per - 1) // per),
                            total=total)


@app.route("/author/<slug>")
def author_page(slug):
    au = Author.query.filter_by(slug=slug).first_or_404()
    articles = au.articles.order_by(Article.published_at.desc()).all()
    return render_template("author.html", au=au, articles=articles)


@app.route("/authors")
def authors_index():
    authors = Author.query.order_by(Author.name).all()
    return render_template("authors_index.html", authors=authors)


@app.route("/smartreads/<slug>/comment", methods=["POST"])
@login_required
def post_comment(slug):
    art = Article.query.filter_by(slug=slug).first_or_404()
    body = (request.form.get("body") or "").strip()
    if not body:
        flash("Comment cannot be empty.", "danger")
    elif len(body) > 1200:
        flash("Comment too long (max 1200 chars).", "danger")
    else:
        c = Comment(article_id=art.id, user_id=current_user.id, body=body)
        db.session.add(c)
        db.session.commit()
        flash("Comment posted.", "success")
    return redirect(url_for("article_detail", slug=slug) + "#comments")


# ───────────────────────────────────────────────────────────
# States
# ───────────────────────────────────────────────────────────

@app.route("/states")
def states_index():
    states = State.query.order_by(State.name).all()
    return render_template("states_index.html", states=states)


@app.route("/state/<slug>")
def state_detail(slug):
    st = State.query.filter_by(slug=slug).first_or_404()
    related_articles = (Article.query.filter(Article.tags.like(f"%{st.abbr}%"))
                        .order_by(Article.published_at.desc()).limit(6).all())
    advisors = (Advisor.query.filter_by(state_abbr=st.abbr)
                .order_by(Advisor.rating.desc()).limit(8).all())
    metros = (City.query.filter_by(state_abbr=st.abbr)
              .order_by(City.population.desc()).limit(6).all())
    return render_template("state.html", st=st, advisors=advisors,
                            related_articles=related_articles, metros=metros)


# ───────────────────────────────────────────────────────────
# Advisor match (multi-step wizard)
# ───────────────────────────────────────────────────────────

WIZARD_STEPS = [
    "retirement_status", "investable_assets", "goal",
    "marital_status", "age", "location", "contact",
]


@app.route("/advisor-match", methods=["GET", "POST"])
def advisor_match_start():
    if request.method == "POST":
        session["wizard"] = {
            "retirement_status": request.form.get("retirement_status", "planning")
        }
        return redirect(url_for("advisor_match_step", step="investable_assets"))
    return render_template("advisor_match_start.html")


@app.route("/advisor-match/<step>", methods=["GET", "POST"])
def advisor_match_step(step):
    if step not in WIZARD_STEPS:
        abort(404)
    wiz = dict(session.get("wizard", {}))
    idx = WIZARD_STEPS.index(step)
    if idx > 0 and not wiz:
        return redirect(url_for("advisor_match_start"))
    if request.method == "POST":
        for k in request.form:
            if k in WIZARD_STEPS or k in ("zip_code", "first_name",
                                          "email", "phone", "state"):
                wiz[k] = request.form.get(k, "")
        session["wizard"] = wiz
        nxt = idx + 1
        if nxt >= len(WIZARD_STEPS):
            return redirect(url_for("advisor_match_results"))
        return redirect(url_for("advisor_match_step",
                                step=WIZARD_STEPS[nxt]))
    states = State.query.order_by(State.name).all()
    return render_template(f"wizard_{step}.html", wiz=wiz,
                            step_idx=idx + 1, total_steps=len(WIZARD_STEPS),
                            states=states)


def _match_advisors(wiz):
    state_abbr = (wiz.get("location") or wiz.get("state") or "NY")[:2].upper()
    try:
        assets = int(re.sub(r"[^0-9]", "",
                              wiz.get("investable_assets", "0")) or 0)
    except ValueError:
        assets = 0
    goal = wiz.get("goal", "retirement")
    spec_map = {
        "retirement": ["Retirement", "Tax", "Estate"],
        "growth": ["Wealth Management", "Investment", "Tax"],
        "taxes": ["Tax", "Retirement", "Estate"],
        "estate": ["Estate", "Tax", "Retirement"],
        "education": ["Education", "Investment", "Tax"],
        "general": ["Wealth Management", "Retirement", "Investment"],
    }
    pref = spec_map.get(goal, ["Wealth Management", "Retirement"])
    pool = Advisor.query.filter_by(state_abbr=state_abbr).all()
    if not pool:
        pool = Advisor.query.order_by(Advisor.rating.desc()).limit(40).all()
    pool = [a for a in pool if a.min_assets <= max(50_000, assets)]
    if not pool:
        pool = Advisor.query.filter(
            Advisor.min_assets <= max(50_000, assets)).all()

    def score(a):
        s = a.rating * 10
        if a.specialty in pref:
            s += (len(pref) - pref.index(a.specialty)) * 4
        s += min(a.years_experience, 30) * 0.1
        s += a.aum_millions * 0.0001
        return s

    pool.sort(key=score, reverse=True)
    return pool[:3]


@app.route("/advisor-match/results", methods=["GET", "POST"])
def advisor_match_results():
    wiz = session.get("wizard", {})
    if not wiz:
        return redirect(url_for("advisor_match_start"))
    matches = _match_advisors(wiz)
    rec = AdvisorMatch(
        user_id=current_user.id if current_user.is_authenticated else None,
        email=wiz.get("email", ""),
        state_abbr=(wiz.get("location") or wiz.get("state") or "")[:2].upper(),
        investable_assets=int(re.sub(r"[^0-9]", "",
                                       wiz.get("investable_assets", "0")) or 0),
        goal=wiz.get("goal", ""),
        age=int(re.sub(r"[^0-9]", "", wiz.get("age", "0")) or 0),
        marital_status=wiz.get("marital_status", ""),
        matched_ids=",".join(str(a.id) for a in matches),
    )
    db.session.add(rec)
    db.session.commit()
    return render_template("advisor_match_results.html", matches=matches,
                            wiz=wiz)


@app.route("/financial-advisor")
def advisor_landing():
    top = Advisor.query.order_by(Advisor.rating.desc()).limit(12).all()
    states = State.query.order_by(State.name).all()
    return render_template("advisor_landing.html", top=top, states=states)


@app.route("/advisor/<slug>")
def advisor_detail(slug):
    a = Advisor.query.filter_by(slug=slug).first_or_404()
    similar = (Advisor.query.filter(Advisor.specialty == a.specialty,
                                     Advisor.state_abbr == a.state_abbr,
                                     Advisor.id != a.id)
               .order_by(Advisor.rating.desc()).limit(4).all())
    state = State.query.filter_by(abbr=a.state_abbr).first()
    already_saved = False
    if current_user.is_authenticated:
        already_saved = (SavedAdvisor.query
                          .filter_by(user_id=current_user.id, advisor_id=a.id)
                          .first() is not None)
    return render_template("advisor_detail.html", a=a, similar=similar,
                            state=state, already_saved=already_saved)


@app.route("/financial-advisor/<state_slug>")
def advisors_by_state(state_slug):
    st = State.query.filter_by(slug=state_slug).first_or_404()
    page = max(1, request.args.get("page", 1, type=int))
    per = 12
    q = (Advisor.query.filter_by(state_abbr=st.abbr)
         .order_by(Advisor.rating.desc()))
    total = q.count()
    advisors = q.offset((page - 1) * per).limit(per).all()
    return render_template("advisors_state.html", st=st, advisors=advisors,
                            page=page,
                            pages=max(1, (total + per - 1) // per),
                            total=total)


# ───────────────────────────────────────────────────────────
# Auth
# ───────────────────────────────────────────────────────────

@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("account"))
    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        pw = request.form.get("password") or ""
        u = User.query.filter_by(email=email).first()
        if u and u.check_password_match(pw):
            login_user(u, remember=True)
            flash(f"Welcome back, {u.name}.", "success")
            return redirect(request.args.get("next") or url_for("account"))
        flash("Invalid email or password.", "danger")
    return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("account"))
    if request.method == "POST":
        name = (request.form.get("name") or "").strip()
        email = (request.form.get("email") or "").strip().lower()
        pw = request.form.get("password") or ""
        if not (name and email and len(pw) >= 6):
            flash("Please complete all fields (password 6+ chars).", "danger")
        elif User.query.filter_by(email=email).first():
            flash("That email is already registered.", "danger")
        else:
            u = User(name=name, email=email,
                     state=request.form.get("state", ""),
                     zip_code=request.form.get("zip_code", ""))
            u.password_hash = bcrypt.generate_password_hash(pw).decode("utf-8")
            db.session.add(u)
            db.session.commit()
            login_user(u)
            flash("Account created. Welcome to SmartAsset.", "success")
            return redirect(url_for("account"))
    return render_template("register.html")


@app.route("/logout")
def logout():
    logout_user()
    flash("Signed out.", "info")
    return redirect(url_for("index"))


@app.route("/account")
@login_required
def account():
    saved = (SavedCalculation.query.filter_by(user_id=current_user.id)
             .order_by(SavedCalculation.created_at.desc()).all())
    matches = (AdvisorMatch.query.filter_by(user_id=current_user.id)
               .order_by(AdvisorMatch.created_at.desc()).all())
    saved_advisors_q = (SavedAdvisor.query.filter_by(user_id=current_user.id)
                         .order_by(SavedAdvisor.created_at.desc()).all())
    # Attach .advisor object onto each row for the template
    saved_advisors = []
    for sa in saved_advisors_q:
        adv = db.session.get(Advisor, sa.advisor_id)
        if adv:
            sa.advisor = adv
            saved_advisors.append(sa)
    return render_template("account.html", saved=saved, matches=matches,
                            saved_advisors=saved_advisors)


@app.route("/account/edit", methods=["GET", "POST"])
@login_required
def account_edit():
    if request.method == "POST":
        current_user.name = (request.form.get("name") or current_user.name).strip()
        current_user.state = request.form.get("state", current_user.state)
        current_user.zip_code = request.form.get("zip_code", current_user.zip_code)
        db.session.commit()
        flash("Profile updated.", "success")
        return redirect(url_for("account"))
    return render_template("account_edit.html")


@app.route("/account/saved/<int:sc_id>/delete", methods=["POST"])
@login_required
def delete_saved(sc_id):
    sc = db.session.get(SavedCalculation, sc_id)
    if sc and sc.user_id == current_user.id:
        db.session.delete(sc)
        db.session.commit()
        flash("Calculation removed.", "info")
    return redirect(url_for("account"))


# ───────────────────────────────────────────────────────────
# Search
# ───────────────────────────────────────────────────────────

@app.route("/search")
def search():
    q = (request.args.get("q") or "").strip()
    arts, calcs, advisors, states_hits = [], [], [], []
    if q:
        like = f"%{q}%"
        tokens = [t.lower() for t in re.findall(r"[A-Za-z0-9]+", q)
                  if len(t) > 1]

        def score_article(a):
            text = f"{a.title} {a.dek} {a.tags}".lower()
            return sum(text.count(t) for t in tokens)

        articles_q = (Article.query.filter(or_(
            Article.title.ilike(like),
            Article.dek.ilike(like),
            Article.tags.ilike(like),
            Article.body.ilike(like),
        )).all())
        articles_q.sort(key=score_article, reverse=True)
        arts = articles_q[:30]

        ql = q.lower()
        calcs = [c for c in CALC_HUB
                 if ql in c["title"].lower() or ql in c["blurb"].lower()
                 or any(t in c["title"].lower() for t in tokens)]
        calcs = calcs[:8]

        advisors = (Advisor.query.filter(or_(
            Advisor.name.ilike(like), Advisor.firm.ilike(like),
            Advisor.city.ilike(like), Advisor.specialty.ilike(like)
        )).limit(10).all())

        states_hits = (State.query.filter(or_(
            State.name.ilike(like), State.abbr.ilike(like),
            State.top_metro.ilike(like)
        )).limit(8).all())

    return render_template("search.html", q=q, articles=arts, calcs=calcs,
                            advisors=advisors, states=states_hits)


# ───────────────────────────────────────────────────────────
# Newsletter, contact, static pages
# ───────────────────────────────────────────────────────────

@app.route("/newsletter/subscribe", methods=["POST"])
def newsletter_subscribe():
    email = (request.form.get("email") or "").strip().lower()
    if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
        flash("Please provide a valid email address.", "danger")
        return redirect(request.referrer or url_for("index"))
    if not Newsletter.query.filter_by(email=email).first():
        db.session.add(Newsletter(email=email))
        db.session.commit()
        flash("Subscribed to SmartMoney Minute.", "success")
    else:
        flash("You're already subscribed.", "info")
    return redirect(request.referrer or url_for("index"))


@app.route("/contact", methods=["GET", "POST"])
def contact():
    if request.method == "POST":
        msg = ContactMessage(
            name=(request.form.get("name") or "").strip(),
            email=(request.form.get("email") or "").strip(),
            topic=request.form.get("topic", "General"),
            body=(request.form.get("body") or "").strip(),
        )
        db.session.add(msg)
        db.session.commit()
        flash("Message received. We'll reply within 2 business days.",
              "success")
        return redirect(url_for("contact"))
    return render_template("contact.html")


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/about/careers")
def careers():
    return render_template("careers.html")


@app.route("/about/press")
def press():
    return render_template("press.html")


@app.route("/privacy")
def privacy():
    return render_template("privacy.html")


@app.route("/terms")
def terms():
    return render_template("terms.html")


@app.route("/disclosure")
def disclosure():
    return render_template("disclosure.html")


@app.route("/sitemap")
def sitemap():
    cats = Category.query.order_by(Category.name).all()
    states = State.query.order_by(State.name).all()
    return render_template("sitemap.html", cats=cats, states=states)


@app.route("/about/press-releases")
def press_releases():
    return render_template("press_releases.html")


@app.route("/taxes/tax-brackets")
def tax_brackets():
    return render_template("tax_brackets.html")


@app.route("/refer")
def refer():
    return render_template("refer.html")


@app.route("/_health")
def health():
    return jsonify({"ok": True, "site": "smartasset",
                     "articles": Article.query.count(),
                     "advisors": Advisor.query.count(),
                     "states": State.query.count(),
                     "calculators": len(CALC_HUB)})


# ───────────────────────────────────────────────────────────
# Hub pages — banking / mortgage / investing / retirement / taxes
# ───────────────────────────────────────────────────────────

HUBS = {
    "banking": {
        "title": "Banking",
        "tagline": "Find the highest yields, lowest fees, and safest banks.",
        "category_slug": "banking",
        "calc_slugs": ["savings", "cd"],
        "review_kinds": ["bank", "robo"],
        "sub_pages": [
            ("Best Savings Accounts", "best-savings-accounts"),
            ("Best CD Rates", "best-cd-rates"),
            ("Best Money Market Accounts", "best-money-market-accounts"),
            ("Best Checking Accounts", "best-checking-accounts"),
            ("Best Online Banks", "best-online-banks"),
            ("Best High-Yield Savings", "best-high-yield-savings"),
        ],
    },
    "mortgage": {
        "title": "Mortgage",
        "tagline": "Compare mortgage rates, lenders, and refi options.",
        "category_slug": "mortgage",
        "calc_slugs": ["mortgage", "affordability", "refinance",
                       "closing-costs", "rent-vs-buy", "property-tax"],
        "review_kinds": ["lender"],
        "sub_pages": [
            ("Best Mortgage Lenders", "best-mortgage-lenders"),
            ("Best Refinance Lenders", "best-refinance-lenders"),
            ("Today's Mortgage Rates", "todays-mortgage-rates"),
            ("FHA Loans Guide", "fha-loans-guide"),
            ("VA Loans Guide", "va-loans-guide"),
            ("First-Time Buyer Guide", "first-time-buyer-guide"),
            ("Jumbo Loans", "jumbo-loans-guide"),
        ],
    },
    "investing": {
        "title": "Investing",
        "tagline": "Brokerages, robo-advisors, ETFs, and asset allocation.",
        "category_slug": "investing",
        "calc_slugs": ["investment", "capital-gains", "inflation"],
        "review_kinds": ["brokerage", "robo"],
        "sub_pages": [
            ("Best Online Brokerages", "best-online-brokerages"),
            ("Best Robo-Advisors", "best-robo-advisors"),
            ("Best IRA Providers", "best-ira-providers"),
            ("Best Target-Date Funds", "best-target-date-funds"),
            ("Best Investment Apps", "best-investment-apps"),
        ],
    },
    "retirement": {
        "title": "Retirement",
        "tagline": "Plan your retirement income, Social Security and 401(k).",
        "category_slug": "retirement",
        "calc_slugs": ["retirement", "401k", "ira"],
        "review_kinds": ["brokerage"],
        "sub_pages": [
            ("Best States to Retire", "best-states-to-retire"),
            ("Social Security Guide", "social-security-guide"),
            ("Pension Guide", "pension-guide"),
            ("401(k) vs IRA", "401k-vs-ira"),
            ("Required Minimum Distributions", "required-minimum-distributions"),
            ("Retirement Withdrawal Strategies", "retirement-withdrawal-strategies"),
        ],
    },
    "taxes": {
        "title": "Taxes",
        "tagline": "Federal, state and local tax guides plus deadlines.",
        "category_slug": "taxes",
        "calc_slugs": ["income-tax", "state-tax", "paycheck",
                       "capital-gains", "property-tax"],
        "review_kinds": [],
        "sub_pages": [
            ("Federal Tax Brackets 2026", "federal-tax-brackets-2026"),
            ("State Income Tax Map", "state-income-tax-map"),
            ("IRS Forms Guide", "irs-forms-guide"),
            ("Business Taxes Guide", "business-taxes-guide"),
            ("Tax Filing Deadlines", "tax-filing-deadlines"),
            ("Estimated Quarterly Taxes", "estimated-quarterly-taxes"),
        ],
    },
    "credit": {
        "title": "Credit",
        "tagline": "Cards, credit scores, and debt-consolidation strategy.",
        "category_slug": "credit-cards",
        "calc_slugs": ["credit-card"],
        "review_kinds": ["card"],
        "sub_pages": [
            ("Best Credit Cards", "best-credit-cards"),
            ("Best Rewards Cards", "best-rewards-cards"),
            ("Best Balance Transfer Cards", "best-balance-transfer-cards"),
            ("Best Cards for Bad Credit", "best-cards-for-bad-credit"),
            ("Credit Score Guide", "credit-score-guide"),
            ("Debt Consolidation Guide", "debt-consolidation-guide"),
        ],
    },
    "insurance": {
        "title": "Insurance",
        "tagline": "Life, auto, home and disability — rate comparisons.",
        "category_slug": "insurance",
        "calc_slugs": ["net-worth", "paycheck"],
        "review_kinds": ["insurer"],
        "sub_pages": [
            ("Best Life Insurance", "best-life-insurance"),
            ("Best Auto Insurance", "best-auto-insurance"),
            ("Best Home Insurance", "best-home-insurance"),
            ("Best Disability Insurance", "best-disability-insurance"),
            ("Term vs Whole Life", "term-vs-whole-life"),
        ],
    },
}


def _hub_context(hub_key):
    h = HUBS.get(hub_key)
    if not h:
        abort(404)
    cat = Category.query.filter_by(slug=h["category_slug"]).first()
    articles = []
    if cat:
        articles = (Article.query.filter_by(category_id=cat.id)
                    .order_by(Article.published_at.desc()).limit(10).all())
    calcs = [c for c in CALC_HUB if c["slug"] in h["calc_slugs"]]
    reviews = []
    if h["review_kinds"]:
        reviews = (Review.query.filter(Review.kind.in_(h["review_kinds"]))
                   .order_by(Review.overall_rating.desc()).limit(8).all())
    return {"h": h, "key": hub_key, "category": cat,
            "articles": articles, "calcs": calcs, "reviews": reviews}


@app.route("/banking")
def hub_banking():
    return render_template("hub.html", **_hub_context("banking"))


@app.route("/mortgage")
def hub_mortgage():
    return render_template("hub.html", **_hub_context("mortgage"))


@app.route("/investing")
def hub_investing():
    return render_template("hub.html", **_hub_context("investing"))


@app.route("/retirement")
def hub_retirement():
    return render_template("hub.html", **_hub_context("retirement"))


@app.route("/taxes")
def hub_taxes():
    return render_template("hub.html", **_hub_context("taxes"))


@app.route("/credit")
def hub_credit():
    return render_template("hub.html", **_hub_context("credit"))


@app.route("/insurance")
def hub_insurance():
    return render_template("hub.html", **_hub_context("insurance"))


@app.route("/<hub>/<page_slug>")
def hub_subpage(hub, page_slug):
    h = HUBS.get(hub)
    if not h:
        abort(404)
    page = next((p for p in h["sub_pages"] if p[1] == page_slug), None)
    if not page:
        abort(404)
    ctx = _hub_context(hub)
    # Pick reviews most relevant; for "best X" pages we just sort top 10
    top_reviews = (Review.query.filter(Review.kind.in_(h["review_kinds"]))
                   .order_by(Review.overall_rating.desc()).limit(10).all()
                   if h["review_kinds"] else [])
    return render_template("hub_subpage.html", page_title=page[0],
                            page_slug=page_slug, hub=hub,
                            ctx=ctx, top_reviews=top_reviews)


# ───────────────────────────────────────────────────────────
# Reviews
# ───────────────────────────────────────────────────────────

REVIEW_KIND_LABELS = {
    "brokerage": "Brokerages", "bank": "Banks", "robo": "Robo-Advisors",
    "lender": "Mortgage Lenders", "insurer": "Insurers",
    "card": "Credit Cards", "advisor-firm": "Advisor Firms",
}


@app.route("/reviews")
def reviews_index():
    by_kind = defaultdict(list)
    for r in Review.query.order_by(Review.overall_rating.desc()).all():
        by_kind[r.kind].append(r)
    return render_template("reviews_index.html", by_kind=dict(by_kind),
                            labels=REVIEW_KIND_LABELS)


@app.route("/reviews/<slug>")
def review_detail(slug):
    r = Review.query.filter_by(slug=slug).first_or_404()
    similar = (Review.query.filter(Review.kind == r.kind, Review.id != r.id)
               .order_by(Review.overall_rating.desc()).limit(5).all())
    return render_template("review_detail.html", r=r, similar=similar,
                            labels=REVIEW_KIND_LABELS)


# ───────────────────────────────────────────────────────────
# Cities
# ───────────────────────────────────────────────────────────

@app.route("/cities")
def cities_index():
    cities = City.query.order_by(City.population.desc()).all()
    return render_template("cities_index.html", cities=cities)


@app.route("/city/<slug>")
def city_detail(slug):
    c = City.query.filter_by(slug=slug).first_or_404()
    st = State.query.filter_by(abbr=c.state_abbr).first()
    advisors = (Advisor.query.filter_by(state_abbr=c.state_abbr,
                                         city=c.name)
                .order_by(Advisor.rating.desc()).limit(6).all())
    if not advisors:  # broaden to state
        advisors = (Advisor.query.filter_by(state_abbr=c.state_abbr)
                    .order_by(Advisor.rating.desc()).limit(6).all())
    nearby = (City.query.filter(City.state_abbr == c.state_abbr,
                                  City.id != c.id)
              .order_by(City.population.desc()).limit(5).all())
    return render_template("city_detail.html", c=c, st=st,
                            advisors=advisors, nearby=nearby)


# ───────────────────────────────────────────────────────────
# Comparison pages (e.g. roth-vs-401k)
# ───────────────────────────────────────────────────────────

COMPARISONS = [
    ("roth-ira-vs-401k", "Roth IRA vs 401(k)",
     "Roth IRA", "401(k)",
     [("Contribution limit (2026)", "$7,000", "$23,500"),
      ("Tax treatment", "After-tax", "Pre-tax"),
      ("Employer match", "No", "Often yes"),
      ("Income limits", "Yes (phase-out)", "None"),
      ("Required minimum distributions", "No (lifetime)", "Yes at 73"),
      ("Early withdrawal penalty", "10% on growth", "10% on whole"),
      ("Best for", "Younger savers, low bracket", "Mid/late career, high bracket")]),
    ("etf-vs-mutual-fund", "ETF vs Mutual Fund",
     "ETF", "Mutual Fund",
     [("Trading", "Throughout day", "End-of-day only"),
      ("Min investment", "1 share", "$500-$3,000"),
      ("Expense ratio", "0.03%-0.20%", "0.10%-1.00%"),
      ("Tax efficiency", "High (in-kind)", "Lower"),
      ("Active management", "Mostly index", "Both active + index"),
      ("Buying mechanism", "Brokerage", "Brokerage or direct")]),
    ("renting-vs-buying", "Renting vs Buying a Home",
     "Rent", "Buy",
     [("Upfront cost", "1-2 mo rent + deposit", "Down payment + closing 3-5%"),
      ("Monthly cost", "Rent only", "P&I + taxes + insurance + maintenance"),
      ("Build equity", "No", "Yes (after ~5 yrs typically)"),
      ("Flexibility", "High (12-mo lease)", "Lower (selling costs ~8%)"),
      ("Tax benefit", "None", "Mortgage interest + property tax (if itemizing)"),
      ("Maintenance", "Landlord", "You")]),
    ("term-vs-whole-life", "Term vs Whole Life Insurance",
     "Term Life", "Whole Life",
     [("Coverage period", "10/20/30 years", "Lifetime"),
      ("Premium (35yo, $500k)", "$25-$45/mo", "$400-$700/mo"),
      ("Cash value", "None", "Yes, grows tax-deferred"),
      ("Investment returns", "N/A", "Low (~2-4%)"),
      ("Recommended for", "Most households", "Estate planning, high-income")]),
    ("fha-vs-conventional", "FHA vs Conventional Loan",
     "FHA", "Conventional",
     [("Min down payment", "3.5%", "3% (conventional 97)"),
      ("Min credit score", "580", "620-640"),
      ("Mortgage insurance", "Required for life (mostly)", "Drops at 78% LTV"),
      ("Loan limit (2026)", "$524,225", "$806,500 conforming"),
      ("Property condition", "Strict (FHA appraisal)", "Standard"),
      ("Funding fee", "1.75% upfront", "None")]),
    ("debt-snowball-vs-avalanche", "Debt Snowball vs Avalanche",
     "Snowball", "Avalanche",
     [("Order of attack", "Smallest balance first", "Highest APR first"),
      ("Total interest paid", "Higher", "Lower"),
      ("Time to payoff", "Slightly longer", "Slightly shorter"),
      ("Psychological wins", "Frequent (early wins)", "Delayed"),
      ("Best for", "Motivation-driven payers", "Math-driven payers")]),
    ("hsa-vs-fsa", "HSA vs FSA",
     "HSA", "FSA",
     [("Eligibility", "Requires HDHP", "Any qualifying plan"),
      ("Contribution limit (2026)", "$4,400 single / $8,750 family", "$3,300"),
      ("Rolls over", "Yes (lifetime)", "No (mostly use-it-or-lose-it)"),
      ("Investable", "Yes, after threshold", "No"),
      ("Triple tax advantage", "Yes", "No (pre-tax only)"),
      ("Portability", "Stays with you", "Tied to employer")]),
    ("traditional-vs-roth-ira", "Traditional vs Roth IRA",
     "Traditional", "Roth",
     [("Tax now", "Deductible", "After-tax"),
      ("Tax later", "Taxed on withdrawal", "Tax-free"),
      ("Income limit (2026)", "None for contributions", "$165k single / $246k joint"),
      ("Required distributions", "Yes at 73", "No"),
      ("Early withdrawal", "Penalty + tax", "Contributions out tax-free"),
      ("Best for", "High earners now", "Low/mid earners now")]),
    ("cd-vs-treasury", "CD vs Treasury Bill",
     "CD", "T-Bill",
     [("Issuer", "Bank", "U.S. Treasury"),
      ("Insurance", "FDIC up to $250k", "Full faith & credit"),
      ("Min purchase", "$500-$1,000", "$100"),
      ("State tax", "Yes", "No"),
      ("Liquidity", "Penalty for early withdraw", "Sellable on secondary"),
      ("Typical yield (2026)", "4.6%", "4.4%")]),
    ("lease-vs-buy-car", "Lease vs Buy a Car",
     "Lease", "Buy",
     [("Monthly payment", "Lower", "Higher"),
      ("Equity at end", "None", "You own it"),
      ("Mileage limit", "~12-15k/yr", "None"),
      ("Customization", "Restricted", "Free"),
      ("End-of-term fees", "Excess wear / mileage", "None"),
      ("Total cost over 6 yrs", "$28k", "$23k (then resale)")]),
]


@app.route("/compare")
def compare_index():
    return render_template("compare_index.html", comparisons=COMPARISONS)


@app.route("/compare/<slug>")
def compare_detail(slug):
    comp = next((c for c in COMPARISONS if c[0] == slug), None)
    if not comp:
        abort(404)
    slug_, title, a, b, rows = comp
    related = [c for c in COMPARISONS if c[0] != slug][:5]
    return render_template("compare_detail.html", slug=slug_, title=title,
                            a=a, b=b, rows=rows, related=related)


# ───────────────────────────────────────────────────────────
# Glossary
# ───────────────────────────────────────────────────────────

import string


@app.route("/glossary")
def glossary_index():
    letters = sorted({t.letter for t in GlossaryTerm.query.all()})
    by_letter = defaultdict(list)
    for t in (GlossaryTerm.query.order_by(GlossaryTerm.term).all()):
        by_letter[t.letter].append(t)
    return render_template("glossary_index.html", letters=letters,
                            by_letter=dict(by_letter))


@app.route("/glossary/<letter>")
def glossary_letter(letter):
    letter = (letter or "").upper()[:1]
    if letter not in string.ascii_uppercase:
        abort(404)
    terms = (GlossaryTerm.query.filter_by(letter=letter)
             .order_by(GlossaryTerm.term).all())
    if not terms:
        abort(404)
    return render_template("glossary_letter.html", letter=letter, terms=terms,
                            letters=sorted({t.letter for t in
                                            GlossaryTerm.query.all()}))


@app.route("/glossary/term/<slug>")
def glossary_term(slug):
    t = GlossaryTerm.query.filter_by(slug=slug).first_or_404()
    related = (GlossaryTerm.query.filter(GlossaryTerm.letter == t.letter,
                                          GlossaryTerm.id != t.id)
               .order_by(func.random()).limit(6).all())
    related_calc = calc.find(t.related_calc) if t.related_calc else None
    return render_template("glossary_term.html", t=t, related=related,
                            related_calc=related_calc)


@app.route("/glossary/lookup", methods=["GET", "POST"])
def glossary_lookup():
    """Combined search box for the glossary; accepts GET or POST."""
    q = (request.values.get("q") or "").strip()
    hits = []
    if q:
        like = f"%{q}%"
        hits = (GlossaryTerm.query.filter(or_(
            GlossaryTerm.term.ilike(like),
            GlossaryTerm.short_def.ilike(like),
        )).order_by(GlossaryTerm.term).limit(20).all())
    return render_template("glossary_lookup.html", q=q, hits=hits)


# ───────────────────────────────────────────────────────────
# Tools / salary / calendar / newsletter / faq / leadership
# ───────────────────────────────────────────────────────────

@app.route("/tools")
def tools_hub():
    cat = request.args.get("category", "").strip()
    groups = defaultdict(list)
    for c in CALC_HUB:
        groups[c["group"]].append(c)
    filtered = None
    if cat:
        filtered = [c for c in CALC_HUB if c["group"].lower() == cat.lower()]
    return render_template("tools.html", groups=dict(groups),
                            filtered=filtered, current_cat=cat)


SALARY_CITIES = [
    ("San Francisco, CA", 145000, 1.45),
    ("New York, NY", 138000, 1.42),
    ("Boston, MA", 122000, 1.30),
    ("Seattle, WA", 130000, 1.30),
    ("Washington, DC", 124000, 1.28),
    ("Los Angeles, CA", 110000, 1.25),
    ("Chicago, IL", 96000, 1.05),
    ("Denver, CO", 102000, 1.13),
    ("Austin, TX", 108000, 1.10),
    ("Atlanta, GA", 92000, 0.97),
    ("Miami, FL", 88000, 1.08),
    ("Dallas, TX", 95000, 1.00),
    ("Phoenix, AZ", 88000, 1.05),
    ("Philadelphia, PA", 92000, 1.03),
    ("Houston, TX", 92000, 0.97),
    ("Portland, OR", 100000, 1.20),
    ("Minneapolis, MN", 94000, 1.00),
    ("San Diego, CA", 112000, 1.30),
    ("Charlotte, NC", 84000, 0.96),
    ("Nashville, TN", 84000, 0.99),
]


@app.route("/salary")
def salary_hub():
    return render_template("salary.html", rows=SALARY_CITIES)


CALENDAR_EVENTS = [
    ("2026-01-15", "Q4 2025 estimated quarterly taxes due", "tax"),
    ("2026-01-29", "IRS opens 2025 tax filing season", "tax"),
    ("2026-01-31", "1099 / W-2 forms must be mailed", "tax"),
    ("2026-03-17", "S-Corp & partnership returns due", "tax"),
    ("2026-04-15", "Federal income tax day (1040 deadline)", "tax"),
    ("2026-04-15", "Q1 2026 estimated quarterly taxes due", "tax"),
    ("2026-04-15", "IRA & HSA contribution deadline (2025 year)", "retirement"),
    ("2026-06-15", "Q2 2026 estimated quarterly taxes due", "tax"),
    ("2026-09-15", "Q3 2026 estimated quarterly taxes due", "tax"),
    ("2026-10-15", "Extended federal tax return deadline", "tax"),
    ("2026-12-31", "401(k) employee contribution deadline", "retirement"),
    ("2026-12-31", "RMD deadline for age 73+", "retirement"),
    ("2026-01-28", "FOMC rate decision (Jan)", "markets"),
    ("2026-03-18", "FOMC rate decision (Mar)", "markets"),
    ("2026-05-07", "FOMC rate decision (May)", "markets"),
    ("2026-06-18", "FOMC rate decision (Jun)", "markets"),
    ("2026-07-30", "FOMC rate decision (Jul)", "markets"),
    ("2026-09-17", "FOMC rate decision (Sep)", "markets"),
    ("2026-11-05", "FOMC rate decision (Nov)", "markets"),
    ("2026-12-17", "FOMC rate decision (Dec)", "markets"),
    ("2026-02-13", "Q4 2025 earnings season peak", "markets"),
    ("2026-10-15", "Medicare Open Enrollment begins", "insurance"),
    ("2026-12-07", "Medicare Open Enrollment ends", "insurance"),
    ("2026-11-01", "ACA Open Enrollment begins", "insurance"),
    ("2026-01-15", "ACA Open Enrollment ends", "insurance"),
]


@app.route("/calendar")
def calendar():
    return render_template("calendar.html", events=CALENDAR_EVENTS)


@app.route("/newsletter")
def newsletter_landing():
    sample_articles = (Article.query.order_by(Article.published_at.desc())
                       .limit(5).all())
    return render_template("newsletter_landing.html",
                            sample_articles=sample_articles)


@app.route("/about/leadership")
def leadership():
    return render_template("leadership.html")


@app.route("/about/methodology")
def methodology():
    return render_template("methodology.html")


@app.route("/faq")
def faq():
    return render_template("faq.html")


@app.route("/ask-an-advisor", methods=["GET", "POST"])
def ask_advisor():
    if request.method == "POST":
        q = (request.form.get("question") or "").strip()
        if not q:
            flash("Question cannot be empty.", "danger")
        else:
            rec = AskQuestion(
                user_id=current_user.id if current_user.is_authenticated else None,
                email=(request.form.get("email") or "").strip(),
                topic=request.form.get("topic", "General"),
                question=q[:4000],
                state_abbr=(request.form.get("state") or "")[:2].upper(),
            )
            db.session.add(rec)
            db.session.commit()
            flash("Question submitted. A SmartAsset advisor will respond within 2 business days.", "success")
            return redirect(url_for("ask_advisor"))
    states = State.query.order_by(State.name).all()
    return render_template("ask_advisor.html", states=states)


# ───────────────────────────────────────────────────────────
# Additional POST handlers
# ───────────────────────────────────────────────────────────

@app.route("/calculators/<slug>/email-result", methods=["POST"])
def email_calc_result(slug):
    spec = calc.find(slug)
    if not spec:
        abort(400)
    email = (request.form.get("email") or "").strip().lower()
    if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
        flash("Please provide a valid email address.", "danger")
        return redirect(url_for("calculator", slug=slug))
    inputs = {k: request.form.get(k, "") for k in spec["fields"]}
    rec = CalcEmail(
        user_id=current_user.id if current_user.is_authenticated else None,
        calc_slug=slug, email=email,
        inputs_json=json.dumps(inputs),
    )
    db.session.add(rec)
    db.session.commit()
    flash(f"Result emailed to {email}.", "success")
    return redirect(url_for("calculator", slug=slug, **inputs))


@app.route("/calculators/<slug>/feedback", methods=["POST"])
def calc_feedback(slug):
    spec = calc.find(slug)
    if not spec:
        abort(400)
    try:
        rating = int(request.form.get("rating", "5"))
    except ValueError:
        rating = 5
    rating = max(1, min(5, rating))
    rec = CalcFeedback(
        user_id=current_user.id if current_user.is_authenticated else None,
        calc_slug=slug, rating=rating,
        body=(request.form.get("body") or "").strip()[:1000],
    )
    db.session.add(rec)
    db.session.commit()
    flash("Thanks for the feedback.", "success")
    return redirect(url_for("calculator", slug=slug))


@app.route("/calculators/compare/add", methods=["POST"])
def compare_calc_add():
    slug = request.form.get("calc_slug", "")
    if not calc.find(slug):
        abort(400)
    tray = session.get("compare_tray", [])
    if slug not in tray and len(tray) < 4:
        tray.append(slug)
    session["compare_tray"] = tray
    flash(f"{slug} added to compare tray ({len(tray)}/4).", "info")
    return redirect(request.referrer or url_for("calculators_index"))


@app.route("/calculators/compare/clear", methods=["POST"])
def compare_calc_clear():
    session.pop("compare_tray", None)
    flash("Compare tray cleared.", "info")
    return redirect(request.referrer or url_for("calculators_index"))


@app.route("/category/<slug>/subscribe", methods=["POST"])
def category_subscribe(slug):
    cat = Category.query.filter_by(slug=slug).first_or_404()
    email = (request.form.get("email") or "").strip().lower()
    if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
        flash("Please provide a valid email.", "danger")
    elif CategorySubscription.query.filter_by(email=email,
                                                category_slug=cat.slug).first():
        flash(f"You're already subscribed to {cat.name}.", "info")
    else:
        db.session.add(CategorySubscription(email=email,
                                              category_slug=cat.slug))
        db.session.commit()
        flash(f"Subscribed to {cat.name} updates.", "success")
    return redirect(url_for("category_page", slug=cat.slug))


@app.route("/smartreads/<slug>/comment/<int:comment_id>/reply",
           methods=["POST"])
@login_required
def post_comment_reply(slug, comment_id):
    art = Article.query.filter_by(slug=slug).first_or_404()
    parent = Comment.query.get_or_404(comment_id)
    if parent.article_id != art.id:
        abort(400)
    body = (request.form.get("body") or "").strip()
    if not body:
        flash("Reply cannot be empty.", "danger")
    elif len(body) > 1200:
        flash("Reply too long.", "danger")
    else:
        db.session.add(CommentReply(parent_id=parent.id,
                                      user_id=current_user.id,
                                      body=body))
        db.session.commit()
        flash("Reply posted.", "success")
    return redirect(url_for("article_detail", slug=slug) + "#comments")


@app.route("/smartreads/<slug>/vote", methods=["POST"])
@login_required
def article_vote(slug):
    art = Article.query.filter_by(slug=slug).first_or_404()
    direction = 1 if request.form.get("direction") == "up" else -1
    existing = ArticleVote.query.filter_by(user_id=current_user.id,
                                             article_id=art.id).first()
    if existing:
        existing.direction = direction
    else:
        db.session.add(ArticleVote(user_id=current_user.id,
                                     article_id=art.id, direction=direction))
    db.session.commit()
    flash(f"Vote recorded ({'up' if direction == 1 else 'down'}).", "info")
    return redirect(url_for("article_detail", slug=slug))


@app.route("/advisor/<slug>/save", methods=["POST"])
@login_required
def save_advisor(slug):
    a = Advisor.query.filter_by(slug=slug).first_or_404()
    if not SavedAdvisor.query.filter_by(user_id=current_user.id,
                                          advisor_id=a.id).first():
        db.session.add(SavedAdvisor(user_id=current_user.id, advisor_id=a.id,
                                      notes=(request.form.get("notes") or "")[:280]))
        db.session.commit()
        flash(f"Saved {a.name} to your shortlist.", "success")
    else:
        flash(f"{a.name} is already on your shortlist.", "info")
    return redirect(url_for("advisor_detail", slug=slug))


@app.route("/advisor/<slug>/unsave", methods=["POST"])
@login_required
def unsave_advisor(slug):
    a = Advisor.query.filter_by(slug=slug).first_or_404()
    sa = SavedAdvisor.query.filter_by(user_id=current_user.id,
                                        advisor_id=a.id).first()
    if sa:
        db.session.delete(sa)
        db.session.commit()
        flash(f"Removed {a.name} from your shortlist.", "info")
    return redirect(url_for("advisor_detail", slug=slug))


@app.route("/advisor/<slug>/contact", methods=["POST"])
def contact_advisor(slug):
    a = Advisor.query.filter_by(slug=slug).first_or_404()
    email = (request.form.get("email") or "").strip().lower()
    if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
        flash("Please provide a valid email.", "danger")
        return redirect(url_for("advisor_detail", slug=slug))
    rec = ContactAdvisor(
        user_id=current_user.id if current_user.is_authenticated else None,
        advisor_id=a.id, email=email,
        phone=(request.form.get("phone") or "").strip()[:40],
        message=(request.form.get("message") or "").strip()[:2000],
        consult_requested=False,
    )
    db.session.add(rec)
    db.session.commit()
    flash(f"Message sent to {a.name}. They'll reach out within 2 business days.",
          "success")
    return redirect(url_for("advisor_detail", slug=slug))


@app.route("/advisor/<slug>/consult", methods=["POST"])
def request_consultation(slug):
    a = Advisor.query.filter_by(slug=slug).first_or_404()
    email = (request.form.get("email") or "").strip().lower()
    if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
        flash("Please provide a valid email.", "danger")
        return redirect(url_for("advisor_detail", slug=slug))
    rec = ContactAdvisor(
        user_id=current_user.id if current_user.is_authenticated else None,
        advisor_id=a.id, email=email,
        phone=(request.form.get("phone") or "").strip()[:40],
        message="Free consultation requested.",
        consult_requested=True,
    )
    db.session.add(rec)
    db.session.commit()
    flash("Consultation requested. The advisor will reach out shortly.",
          "success")
    return redirect(url_for("advisor_detail", slug=slug))


@app.route("/promo/apply", methods=["POST"])
def apply_promo():
    code = (request.form.get("code") or "").strip().upper()
    promo = Promo.query.filter_by(code=code, active=True).first()
    accepted = bool(promo)
    rec = PromoApplication(
        user_id=current_user.id if current_user.is_authenticated else None,
        code=code, accepted=accepted)
    db.session.add(rec)
    db.session.commit()
    if accepted:
        flash(f"Promo applied: {promo.description}", "success")
    else:
        flash(f"Promo code '{code}' is invalid or expired.", "danger")
    return redirect(request.referrer or url_for("index"))


@app.route("/account/tax-status", methods=["POST"])
@login_required
def update_tax_status():
    s = (request.form.get("tax_filing_status") or "single").strip().lower()
    if s not in {"single", "married", "head"}:
        flash("Invalid filing status.", "danger")
    else:
        current_user.tax_filing_status = s
        db.session.commit()
        flash("Default tax filing status updated.", "success")
    return redirect(url_for("account"))


@app.route("/account/location", methods=["POST"])
@login_required
def update_location():
    state = (request.form.get("state") or "").strip()[:40]
    zip_code = (request.form.get("zip_code") or "").strip()[:10]
    if state:
        current_user.state = state
    if zip_code:
        current_user.zip_code = zip_code
    db.session.commit()
    flash("Default location updated — calculators will pre-fill it.",
          "success")
    return redirect(url_for("account"))


@app.errorhandler(404)
def not_found(e):
    return render_template("404.html"), 404


@app.errorhandler(500)
def server_error(e):
    return render_template("500.html"), 500


# ───────────────────────────────────────────────────────────
# Bootstrap
# ───────────────────────────────────────────────────────────

with app.app_context():
    db.create_all()
    import seed_data
    seed_data.seed_database(db, User, Author, Category, Article, State,
                             Advisor, bcrypt)
    seed_data.seed_benchmark_users(db, User, bcrypt)
    seed_data.seed_extras(db, GlossaryTerm, City, Review, Promo)


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

