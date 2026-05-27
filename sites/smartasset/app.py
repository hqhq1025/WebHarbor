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
    return render_template("state.html", st=st, advisors=advisors,
                            related_articles=related_articles)


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
    return render_template("advisor_detail.html", a=a, similar=similar)


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
    return render_template("account.html", saved=saved, matches=matches)


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


@app.route("/_health")
def health():
    return jsonify({"ok": True, "site": "smartasset",
                     "articles": Article.query.count(),
                     "advisors": Advisor.query.count(),
                     "states": State.query.count(),
                     "calculators": len(CALC_HUB)})


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


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
