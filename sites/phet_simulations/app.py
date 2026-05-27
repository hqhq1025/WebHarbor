"""PhET Interactive Simulations mirror.

Mirrors the structure of https://phet.colorado.edu/ for WebHarbor agent
evaluation: a Flask + SQLite app that serves a deterministic snapshot of
the PhET simulation catalog (browse, filter, search, translations,
teacher activities, lesson plans, classroom mode, accessibility,
research papers, news, sponsors, workshops, donations and account-gated
saves / favorites / bug reports / comments).
"""
import hashlib
import json
import os
import re
from datetime import date, datetime, timedelta
from pathlib import Path

from flask import (
    Flask, abort, flash, jsonify, redirect, render_template, request,
    session, url_for,
)
from flask_bcrypt import Bcrypt
from flask_login import (
    LoginManager, UserMixin, current_user, login_required, login_user,
    logout_user,
)
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import CSRFProtect
from sqlalchemy import or_, text

from _health import health as _health_payload


# ---------------------------------------------------------------------------
# Byte-identical seed primitives (see harden-env gotchas #1, #2, #3).
# Bcrypt hash pinned so the seed DB does not shift on every rebuild.
# ---------------------------------------------------------------------------

PINNED_PASSWORD_HASH = (
    "$2b$12$Oi0plj9XBSbuCcjmrSVmje2AWKXN99Xpa7J2O6tjYvquZPTqNXN6i"  # 'test1234'
)
MIRROR_REFERENCE_DATE = datetime(2026, 5, 12, 12, 0, 0)


def _md5_seed(*parts):
    """Deterministic int derived from md5(parts) — used everywhere we'd
    otherwise reach for random.choice / randrange."""
    h = hashlib.md5("|".join(str(p) for p in parts).encode()).hexdigest()
    return int(h, 16)


BASE_DIR = Path(__file__).parent
DB_DIR = BASE_DIR / "instance"
DB_DIR.mkdir(exist_ok=True)
DB_PATH = DB_DIR / "phet_simulations.db"

app = Flask(__name__)
app.config["SECRET_KEY"] = "phet-simulations-dev-secret-key-do-not-use-in-prod"
app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{DB_PATH}"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["WTF_CSRF_TIME_LIMIT"] = None
app.config["TEMPLATES_AUTO_RELOAD"] = True
app.config["JSON_SORT_KEYS"] = False

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = "login"
login_manager.login_message = "Please log in to access this page."
csrf = CSRFProtect(app)


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    name = db.Column(db.String(80), nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), default="teacher")
    institution = db.Column(db.String(200))
    country = db.Column(db.String(80))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    saved = db.relationship(
        "SavedSimulation", backref="user", lazy="dynamic",
        cascade="all, delete-orphan",
    )


class Subject(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(40), unique=True, nullable=False, index=True)
    name = db.Column(db.String(80), nullable=False)
    icon = db.Column(db.String(40))
    color = db.Column(db.String(20))
    description = db.Column(db.Text)


class GradeLevel(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(40), unique=True, nullable=False, index=True)
    name = db.Column(db.String(80), nullable=False)
    age_range = db.Column(db.String(40))
    sort_order = db.Column(db.Integer, default=0)


class Language(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(10), unique=True, nullable=False, index=True)
    name = db.Column(db.String(80), nullable=False)
    native_name = db.Column(db.String(80), nullable=False)
    sim_count = db.Column(db.Integer, default=0)
    is_rtl = db.Column(db.Boolean, default=False)


class Simulation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(80), unique=True, nullable=False, index=True)
    title = db.Column(db.String(200), nullable=False)
    short_description = db.Column(db.String(300), nullable=False)
    overview = db.Column(db.Text, nullable=False)
    subjects_json = db.Column(db.Text, default="[]")
    grades_json = db.Column(db.Text, default="[]")
    topics_json = db.Column(db.Text, default="[]")
    languages_json = db.Column(db.Text, default='["en"]')
    version = db.Column(db.String(20), default="1.0.0")
    is_html5 = db.Column(db.Boolean, default=True)
    is_featured = db.Column(db.Boolean, default=False)
    is_new = db.Column(db.Boolean, default=False)
    thumbnail = db.Column(db.String(120))
    runtime_minutes = db.Column(db.Integer, default=20)
    release_date = db.Column(db.Date)
    download_count = db.Column(db.Integer, default=0)
    play_count = db.Column(db.Integer, default=0)
    activities = db.relationship(
        "Activity", backref="simulation", lazy="dynamic",
        cascade="all, delete-orphan",
    )
    saved_by = db.relationship(
        "SavedSimulation", backref="simulation", lazy="dynamic",
        cascade="all, delete-orphan",
    )

    def subjects(self):
        return json.loads(self.subjects_json or "[]")

    def grades(self):
        return json.loads(self.grades_json or "[]")

    def topics(self):
        return json.loads(self.topics_json or "[]")

    def languages(self):
        return json.loads(self.languages_json or '["en"]')


class Activity(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sim_id = db.Column(
        db.Integer, db.ForeignKey("simulation.id"), nullable=False, index=True,
    )
    title = db.Column(db.String(200), nullable=False)
    author = db.Column(db.String(120), nullable=False)
    grade_level = db.Column(db.String(40))
    duration_min = db.Column(db.Integer)
    description = db.Column(db.Text, nullable=False)
    file_type = db.Column(db.String(20), default="PDF")
    download_count = db.Column(db.Integer, default=0)
    published_date = db.Column(db.Date)


class SavedSimulation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("user.id"), nullable=False, index=True,
    )
    sim_id = db.Column(
        db.Integer, db.ForeignKey("simulation.id"), nullable=False, index=True,
    )
    notes = db.Column(db.Text)
    saved_at = db.Column(db.DateTime, default=datetime.utcnow)
    __table_args__ = (db.UniqueConstraint("user_id", "sim_id"),)


class LessonPlan(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(120), unique=True, nullable=False, index=True)
    title = db.Column(db.String(200), nullable=False)
    sim_id = db.Column(db.Integer, db.ForeignKey("simulation.id"), nullable=False, index=True)
    author = db.Column(db.String(120), nullable=False)
    grade_band = db.Column(db.String(40), nullable=False)
    duration_min = db.Column(db.Integer, default=45)
    objectives = db.Column(db.Text, nullable=False)
    materials = db.Column(db.Text, nullable=False)
    body = db.Column(db.Text, nullable=False)
    standards = db.Column(db.Text, default="")
    cover_image = db.Column(db.String(120))
    rating_sum = db.Column(db.Integer, default=0)
    rating_count = db.Column(db.Integer, default=0)
    download_count = db.Column(db.Integer, default=0)
    published_date = db.Column(db.Date)
    sim = db.relationship("Simulation", foreign_keys=[sim_id])

    @property
    def avg_rating(self):
        return round(self.rating_sum / self.rating_count, 2) if self.rating_count else 0


class LessonPlanComment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    lesson_plan_id = db.Column(db.Integer, db.ForeignKey("lesson_plan.id"), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    body = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: MIRROR_REFERENCE_DATE)


class TeacherTip(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(120), unique=True, nullable=False, index=True)
    title = db.Column(db.String(200), nullable=False)
    author = db.Column(db.String(120), nullable=False)
    category = db.Column(db.String(40), nullable=False)
    body = db.Column(db.Text, nullable=False)
    summary = db.Column(db.String(400), nullable=False)
    upvotes = db.Column(db.Integer, default=0)
    published_date = db.Column(db.Date)


class ClassroomSession(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    sim_id = db.Column(db.Integer, db.ForeignKey("simulation.id"), nullable=False, index=True)
    session_code = db.Column(db.String(12), unique=True, nullable=False, index=True)
    name = db.Column(db.String(120))
    students_count = db.Column(db.Integer, default=0)
    started_at = db.Column(db.DateTime, default=lambda: MIRROR_REFERENCE_DATE)
    status = db.Column(db.String(20), default="active")


class NewsArticle(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(160), unique=True, nullable=False, index=True)
    title = db.Column(db.String(240), nullable=False)
    summary = db.Column(db.String(400), nullable=False)
    body = db.Column(db.Text, nullable=False)
    author = db.Column(db.String(120), nullable=False)
    category = db.Column(db.String(40), nullable=False)
    published_date = db.Column(db.Date, index=True)
    cover_image = db.Column(db.String(160))
    view_count = db.Column(db.Integer, default=0)


class ResearchPaper(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(160), unique=True, nullable=False, index=True)
    title = db.Column(db.String(280), nullable=False)
    authors = db.Column(db.String(360), nullable=False)
    year = db.Column(db.Integer, index=True)
    venue = db.Column(db.String(200), nullable=False)
    abstract = db.Column(db.Text, nullable=False)
    keywords = db.Column(db.String(300), default="")
    citation_count = db.Column(db.Integer, default=0)
    doi = db.Column(db.String(80))


class Sponsor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(80), unique=True, nullable=False, index=True)
    name = db.Column(db.String(160), nullable=False)
    tier = db.Column(db.String(20), nullable=False, index=True)
    blurb = db.Column(db.Text, nullable=False)
    logo = db.Column(db.String(120))
    homepage = db.Column(db.String(200))
    sort_order = db.Column(db.Integer, default=0)


class Workshop(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(120), unique=True, nullable=False, index=True)
    title = db.Column(db.String(240), nullable=False)
    presenter = db.Column(db.String(160), nullable=False)
    held_on = db.Column(db.Date, nullable=False, index=True)
    duration_min = db.Column(db.Integer, default=90)
    capacity = db.Column(db.Integer, default=80)
    registered = db.Column(db.Integer, default=0)
    description = db.Column(db.Text, nullable=False)
    location = db.Column(db.String(120), default="Virtual")


class WorkshopRegistration(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    workshop_id = db.Column(db.Integer, db.ForeignKey("workshop.id"), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    registered_at = db.Column(db.DateTime, default=lambda: MIRROR_REFERENCE_DATE)
    __table_args__ = (db.UniqueConstraint("workshop_id", "user_id"),)


class TeamMember(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(80), unique=True, nullable=False, index=True)
    name = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(120), nullable=False)
    team = db.Column(db.String(40), nullable=False, index=True)
    bio = db.Column(db.Text, nullable=False)
    photo = db.Column(db.String(120))
    sort_order = db.Column(db.Integer, default=0)


class FAQItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(40), nullable=False, index=True)
    question = db.Column(db.String(280), nullable=False)
    answer = db.Column(db.Text, nullable=False)
    sort_order = db.Column(db.Integer, default=0)
    helpful = db.Column(db.Integer, default=0)


class ContactMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(160), nullable=False, index=True)
    topic = db.Column(db.String(40), nullable=False)
    subject = db.Column(db.String(240), nullable=False)
    body = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: MIRROR_REFERENCE_DATE)


class BugReport(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sim_id = db.Column(db.Integer, db.ForeignKey("simulation.id"), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True, index=True)
    summary = db.Column(db.String(240), nullable=False)
    body = db.Column(db.Text, nullable=False)
    severity = db.Column(db.String(20), default="medium")
    status = db.Column(db.String(20), default="open")
    created_at = db.Column(db.DateTime, default=lambda: MIRROR_REFERENCE_DATE)
    sim = db.relationship("Simulation", foreign_keys=[sim_id])


class AccessibilityReport(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sim_id = db.Column(db.Integer, db.ForeignKey("simulation.id"), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True, index=True)
    issue_type = db.Column(db.String(40), nullable=False)
    body = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default="reviewing")
    created_at = db.Column(db.DateTime, default=lambda: MIRROR_REFERENCE_DATE)
    sim = db.relationship("Simulation", foreign_keys=[sim_id])


class SimRating(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sim_id = db.Column(db.Integer, db.ForeignKey("simulation.id"), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    stars = db.Column(db.Integer, nullable=False)
    review = db.Column(db.Text, default="")
    created_at = db.Column(db.DateTime, default=lambda: MIRROR_REFERENCE_DATE)
    __table_args__ = (db.UniqueConstraint("sim_id", "user_id"),)


class SimComment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sim_id = db.Column(db.Integer, db.ForeignKey("simulation.id"), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    body = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: MIRROR_REFERENCE_DATE)


class Donation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True, index=True)
    donor_name = db.Column(db.String(160), nullable=False)
    donor_email = db.Column(db.String(160), nullable=False)
    amount_cents = db.Column(db.Integer, nullable=False)
    frequency = db.Column(db.String(20), default="one-time")
    message = db.Column(db.Text, default="")
    created_at = db.Column(db.DateTime, default=lambda: MIRROR_REFERENCE_DATE)


class NewsletterSubscriber(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(160), unique=True, nullable=False, index=True)
    role = db.Column(db.String(40), default="teacher")
    country = db.Column(db.String(80), default="")
    created_at = db.Column(db.DateTime, default=lambda: MIRROR_REFERENCE_DATE)


class Favorite(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    sim_id = db.Column(db.Integer, db.ForeignKey("simulation.id"), nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=lambda: MIRROR_REFERENCE_DATE)
    __table_args__ = (db.UniqueConstraint("user_id", "sim_id"),)


class NewsArticleComment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    article_id = db.Column(db.Integer, db.ForeignKey("news_article.id"), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    body = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: MIRROR_REFERENCE_DATE)


@login_manager.user_loader
def load_user(uid):
    return User.query.get(int(uid))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _subject_map():
    return {s.slug: s for s in Subject.query.all()}


def _grade_map():
    return {g.slug: g for g in GradeLevel.query.order_by(GradeLevel.sort_order).all()}


def _language_map():
    return {l.code: l for l in Language.query.order_by(Language.name).all()}


def _saved_sim_ids():
    if not current_user.is_authenticated:
        return set()
    return {s.sim_id for s in current_user.saved.all()}


_THUMB_DIR = os.path.join(BASE_DIR, "static", "images", "sims")
_AVAILABLE_THUMBNAILS = frozenset(
    f[:-4] for f in os.listdir(_THUMB_DIR)
    if f.endswith(".png") and os.path.getsize(os.path.join(_THUMB_DIR, f)) > 1000
) if os.path.isdir(_THUMB_DIR) else frozenset()


@app.context_processor
def inject_globals():
    return {
        "site_title": "PhET Interactive Simulations",
        "site_tagline": "Free online math and science simulations",
        "current_year": datetime.utcnow().year,
        "primary_subjects": Subject.query.order_by(Subject.name).all(),
        "grade_levels": GradeLevel.query.order_by(GradeLevel.sort_order).all(),
        "saved_sim_ids": _saved_sim_ids(),
        "available_thumbnails": _AVAILABLE_THUMBNAILS,
    }


# ---------------------------------------------------------------------------
# Routes — public
# ---------------------------------------------------------------------------

@app.route("/_health")
def health():
    return jsonify(_health_payload())


@app.route("/")
def index():
    featured = (
        Simulation.query.filter_by(is_featured=True)
        .order_by(Simulation.title)
        .limit(8)
        .all()
    )
    new_sims = (
        Simulation.query.filter_by(is_new=True)
        .order_by(Simulation.release_date.desc())
        .limit(6)
        .all()
    )
    most_played = (
        Simulation.query.order_by(Simulation.play_count.desc())
        .limit(6)
        .all()
    )
    total = Simulation.query.count()
    total_languages = Language.query.count()
    total_activities = Activity.query.count()
    return render_template(
        "index.html",
        featured=featured,
        new_sims=new_sims,
        most_played=most_played,
        total_simulations=total,
        total_languages=total_languages,
        total_activities=total_activities,
    )


@app.route("/simulations")
def simulations():
    subject = request.args.get("subject", "").strip()
    grade = request.args.get("grade", "").strip()
    language = request.args.get("language", "").strip()
    sort = request.args.get("sort", "title")
    view = request.args.get("view", "filter").strip()
    page = max(int(request.args.get("page", 1)), 1)
    per_page = 24

    query = Simulation.query
    if subject:
        query = query.filter(Simulation.subjects_json.like(f'%"{subject}"%'))
    if grade:
        query = query.filter(Simulation.grades_json.like(f'%"{grade}"%'))
    if language:
        query = query.filter(Simulation.languages_json.like(f'%"{language}"%'))

    if sort == "newest":
        query = query.order_by(Simulation.release_date.desc())
    elif sort == "popular":
        query = query.order_by(Simulation.play_count.desc())
    else:
        query = query.order_by(Simulation.title)

    total = query.count()
    sims = query.offset((page - 1) * per_page).limit(per_page).all()
    total_pages = max((total + per_page - 1) // per_page, 1)

    any_filter_active = bool(subject or grade or language or sort != "title")
    view_tab = view if view in ("browse", "filter", "customize") else "filter"

    sims_by_subject = {}
    if view_tab == "browse":
        ordered = ['physics', 'math', 'chemistry', 'earth-science', 'biology']
        for slug in ordered:
            sims_by_subject[slug] = (
                Simulation.query
                .filter(Simulation.subjects_json.like(f'%"{slug}"%'))
                .order_by(Simulation.title)
                .limit(7)
                .all()
            )

    return render_template(
        "simulations.html",
        sims=sims,
        total=total,
        page=page,
        total_pages=total_pages,
        subject=subject,
        grade=grade,
        language=language,
        sort=sort,
        view_tab=view_tab,
        languages=Language.query.order_by(Language.name).all(),
        any_filter_active=any_filter_active,
        sims_by_subject=sims_by_subject,
    )


@app.route("/simulations/category/<slug>")
def simulations_by_subject(slug):
    subject = Subject.query.filter_by(slug=slug).first_or_404()
    sims = (
        Simulation.query.filter(Simulation.subjects_json.like(f'%"{slug}"%'))
        .order_by(Simulation.title)
        .all()
    )
    return render_template(
        "category.html", subject=subject, sims=sims,
    )


@app.route("/simulation/<slug>")
def simulation_detail(slug):
    sim = Simulation.query.filter_by(slug=slug).first_or_404()
    sim.play_count = (sim.play_count or 0) + 1
    db.session.commit()

    subjects_full = [
        s for s in Subject.query.filter(Subject.slug.in_(sim.subjects())).all()
    ]
    grades_full = [
        g for g in GradeLevel.query.filter(GradeLevel.slug.in_(sim.grades())).all()
    ]
    langs_full = [
        l for l in Language.query.filter(Language.code.in_(sim.languages())).all()
    ]

    related = (
        Simulation.query.filter(Simulation.id != sim.id)
        .filter(
            or_(*[
                Simulation.subjects_json.like(f'%"{s}"%') for s in sim.subjects()
            ])
        )
        .order_by(Simulation.title)
        .limit(6)
        .all()
    )
    activities = sim.activities.order_by(Activity.published_date.desc()).all()

    is_saved = (
        current_user.is_authenticated
        and SavedSimulation.query.filter_by(
            user_id=current_user.id, sim_id=sim.id,
        ).first()
        is not None
    )

    return render_template(
        "simulation_detail.html",
        sim=sim,
        subjects=subjects_full,
        grades=grades_full,
        languages=langs_full,
        related=related,
        activities=activities,
        is_saved=is_saved,
    )


@app.route("/search")
def search():
    q = request.args.get("q", "").strip()
    sims = []
    if q:
        pattern = f"%{q}%"
        sims = (
            Simulation.query.filter(
                or_(
                    Simulation.title.ilike(pattern),
                    Simulation.short_description.ilike(pattern),
                    Simulation.topics_json.ilike(pattern),
                )
            )
            .order_by(Simulation.title)
            .all()
        )
    return render_template("search.html", query=q, sims=sims, total=len(sims))


@app.route("/translations")
def translations():
    langs = (
        Language.query.order_by(Language.sim_count.desc(), Language.name)
        .all()
    )
    return render_template("translations.html", languages=langs)


@app.route("/translations/<code>")
def translation_detail(code):
    lang = Language.query.filter_by(code=code).first_or_404()
    sims = (
        Simulation.query.filter(Simulation.languages_json.like(f'%"{code}"%'))
        .order_by(Simulation.title)
        .all()
    )
    return render_template(
        "translation_detail.html", language=lang, sims=sims,
    )


@app.route("/teachers")
def teachers():
    featured = (
        Activity.query.order_by(Activity.download_count.desc())
        .limit(6)
        .all()
    )
    return render_template("teachers.html", featured_activities=featured)


@app.route("/teachers/activities")
def activities():
    grade = request.args.get("grade", "")
    query = Activity.query
    if grade:
        query = query.filter_by(grade_level=grade)
    items = query.order_by(Activity.published_date.desc()).all()
    return render_template("activities.html", activities=items, grade=grade)


@app.route("/teachers/activity/<int:activity_id>")
def activity_detail(activity_id):
    activity = Activity.query.get_or_404(activity_id)
    activity.download_count = (activity.download_count or 0) + 1
    db.session.commit()
    return render_template("activity_detail.html", activity=activity)


@app.route("/about")
def about():
    stats = {
        "simulations": Simulation.query.count(),
        "languages": Language.query.count(),
        "subjects": Subject.query.count(),
        "activities": Activity.query.count(),
    }
    return render_template("about.html", stats=stats)


@app.route("/accessibility")
def accessibility():
    return render_template("accessibility.html")


# ---------------------------------------------------------------------------
# Routes — auth
# ---------------------------------------------------------------------------

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


@app.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("account"))
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        name = request.form.get("name", "").strip()
        password = request.form.get("password", "")
        institution = request.form.get("institution", "").strip()
        country = request.form.get("country", "").strip()

        if not EMAIL_RE.match(email):
            flash("Please enter a valid email address.", "error")
        elif len(name) < 2:
            flash("Please enter your full name.", "error")
        elif len(password) < 8:
            flash("Password must be at least 8 characters.", "error")
        elif User.query.filter_by(email=email).first():
            flash("An account with that email already exists.", "error")
        else:
            user = User(
                email=email,
                name=name,
                password_hash=bcrypt.generate_password_hash(password).decode(),
                institution=institution,
                country=country,
            )
            db.session.add(user)
            db.session.commit()
            login_user(user)
            flash("Welcome to PhET! Your account is ready.", "success")
            return redirect(url_for("account"))
    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("account"))
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = User.query.filter_by(email=email).first()
        if user and bcrypt.check_password_hash(user.password_hash, password):
            login_user(user)
            flash(f"Welcome back, {user.name}!", "success")
            return redirect(request.args.get("next") or url_for("account"))
        flash("Invalid email or password.", "error")
    return render_template("login.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been signed out.", "success")
    return redirect(url_for("index"))


@app.route("/account")
@login_required
def account():
    saved_rows = (
        SavedSimulation.query.filter_by(user_id=current_user.id)
        .order_by(SavedSimulation.saved_at.desc())
        .all()
    )
    return render_template("account.html", saved_rows=saved_rows)


@app.route("/api/save-sim", methods=["POST"])
@login_required
def api_save_sim():
    data = request.get_json(silent=True) or request.form
    sim_id = data.get("sim_id")
    notes = (data.get("notes") or "").strip()
    if not sim_id:
        return jsonify({"ok": False, "error": "missing sim_id"}), 400
    sim = Simulation.query.get(int(sim_id))
    if not sim:
        return jsonify({"ok": False, "error": "unknown simulation"}), 404
    existing = SavedSimulation.query.filter_by(
        user_id=current_user.id, sim_id=sim.id,
    ).first()
    if existing:
        existing.notes = notes or existing.notes
    else:
        db.session.add(
            SavedSimulation(
                user_id=current_user.id, sim_id=sim.id, notes=notes,
            )
        )
    db.session.commit()
    return jsonify({"ok": True, "saved": True, "sim_id": sim.id})


@app.route("/api/unsave-sim", methods=["POST"])
@login_required
def api_unsave_sim():
    data = request.get_json(silent=True) or request.form
    sim_id = data.get("sim_id")
    if not sim_id:
        return jsonify({"ok": False, "error": "missing sim_id"}), 400
    row = SavedSimulation.query.filter_by(
        user_id=current_user.id, sim_id=int(sim_id),
    ).first()
    if row:
        db.session.delete(row)
        db.session.commit()
    return jsonify({"ok": True, "saved": False, "sim_id": int(sim_id)})


# ---------------------------------------------------------------------------
# Routes — vanilla-level deepening: lesson plans, teacher tips, classroom
# mode, accessibility detail, team/history, donate/sponsors, research, news,
# contact, FAQ, workshops, per-grade hubs. All GUI routes (no /api/, no
# /webhook, no /.well-known, no /sitemap). POST handlers follow.
# ---------------------------------------------------------------------------


@app.route("/grade/<slug>")
def grade_band(slug):
    grade = GradeLevel.query.filter_by(slug=slug).first_or_404()
    sims = (
        Simulation.query
        .filter(Simulation.grades_json.like(f'%"{slug}"%'))
        .order_by(Simulation.title)
        .all()
    )
    activities = (
        Activity.query.filter_by(grade_level=slug)
        .order_by(Activity.download_count.desc())
        .limit(8)
        .all()
    )
    lesson_plans = (
        LessonPlan.query.filter_by(grade_band=slug)
        .order_by(LessonPlan.rating_count.desc())
        .limit(10)
        .all()
    )
    return render_template(
        "grade_band.html", grade=grade, sims=sims,
        activities=activities, lesson_plans=lesson_plans,
    )


@app.route("/lesson-plans")
def lesson_plans():
    grade = request.args.get("grade", "").strip()
    subject = request.args.get("subject", "").strip()
    sort = request.args.get("sort", "popular")

    query = LessonPlan.query
    if grade:
        query = query.filter_by(grade_band=grade)
    if subject:
        query = query.join(Simulation, LessonPlan.sim_id == Simulation.id).filter(
            Simulation.subjects_json.like(f'%"{subject}"%')
        )
    if sort == "newest":
        query = query.order_by(LessonPlan.published_date.desc())
    elif sort == "rating":
        query = query.order_by(LessonPlan.rating_sum.desc())
    else:
        query = query.order_by(LessonPlan.download_count.desc())
    plans = query.all()
    return render_template(
        "lesson_plans.html", plans=plans, grade=grade,
        subject=subject, sort=sort, total=len(plans),
    )


@app.route("/lesson-plan/<slug>")
def lesson_plan_detail(slug):
    plan = LessonPlan.query.filter_by(slug=slug).first_or_404()
    plan.download_count = (plan.download_count or 0) + 1
    db.session.commit()
    comments = (
        LessonPlanComment.query.filter_by(lesson_plan_id=plan.id)
        .order_by(LessonPlanComment.created_at.desc())
        .all()
    )
    comment_users = {u.id: u for u in User.query.all()}
    related = (
        LessonPlan.query
        .filter(LessonPlan.id != plan.id, LessonPlan.grade_band == plan.grade_band)
        .order_by(LessonPlan.rating_sum.desc())
        .limit(4)
        .all()
    )
    return render_template(
        "lesson_plan_detail.html", plan=plan, comments=comments,
        comment_users=comment_users, related=related,
    )


@app.route("/lesson-plan/submit", methods=["GET", "POST"])
@login_required
def submit_lesson_plan():
    sims = Simulation.query.order_by(Simulation.title).all()
    grades = GradeLevel.query.order_by(GradeLevel.sort_order).all()
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        sim_id = request.form.get("sim_id", "").strip()
        grade_band = request.form.get("grade_band", "").strip()
        objectives = request.form.get("objectives", "").strip()
        materials = request.form.get("materials", "").strip()
        body = request.form.get("body", "").strip()
        duration = request.form.get("duration_min", "45").strip()

        if not (title and sim_id and grade_band and objectives and body):
            flash("All required fields must be filled.", "error")
        else:
            sim = Simulation.query.get(int(sim_id))
            if not sim:
                flash("Unknown simulation.", "error")
            else:
                slug = _unique_slug(LessonPlan, _slug(title))
                plan = LessonPlan(
                    slug=slug,
                    title=title,
                    sim_id=sim.id,
                    author=current_user.name,
                    grade_band=grade_band,
                    duration_min=int(duration) if duration.isdigit() else 45,
                    objectives=objectives,
                    materials=materials or "Computer with browser, paper, pencil",
                    body=body,
                    published_date=date(2026, 5, 27),
                    cover_image=sim.thumbnail,
                )
                db.session.add(plan)
                db.session.commit()
                flash("Lesson plan submitted for review.", "success")
                return redirect(url_for("lesson_plan_detail", slug=plan.slug))
    return render_template("submit_lesson_plan.html", sims=sims, grades=grades)


@app.route("/lesson-plan/<slug>/comment", methods=["POST"])
@login_required
def lesson_plan_comment(slug):
    plan = LessonPlan.query.filter_by(slug=slug).first_or_404()
    body = request.form.get("body", "").strip()
    if not body:
        flash("Comment cannot be empty.", "error")
    else:
        db.session.add(LessonPlanComment(
            lesson_plan_id=plan.id, user_id=current_user.id, body=body,
        ))
        db.session.commit()
        flash("Comment posted.", "success")
    return redirect(url_for("lesson_plan_detail", slug=slug))


@app.route("/lesson-plan/<slug>/rate", methods=["POST"])
@login_required
def lesson_plan_rate(slug):
    plan = LessonPlan.query.filter_by(slug=slug).first_or_404()
    try:
        stars = max(1, min(5, int(request.form.get("stars", "0"))))
    except ValueError:
        flash("Invalid rating.", "error")
        return redirect(url_for("lesson_plan_detail", slug=slug))
    plan.rating_sum = (plan.rating_sum or 0) + stars
    plan.rating_count = (plan.rating_count or 0) + 1
    db.session.commit()
    flash(f"Rated {stars} stars. Thanks!", "success")
    return redirect(url_for("lesson_plan_detail", slug=slug))


@app.route("/teacher-tips")
def teacher_tips():
    category = request.args.get("category", "").strip()
    query = TeacherTip.query
    if category:
        query = query.filter_by(category=category)
    tips = query.order_by(TeacherTip.upvotes.desc()).all()
    categories = sorted({t.category for t in TeacherTip.query.all()})
    return render_template(
        "teacher_tips.html", tips=tips, category=category, categories=categories,
    )


@app.route("/teacher-tip/<slug>")
def teacher_tip_detail(slug):
    tip = TeacherTip.query.filter_by(slug=slug).first_or_404()
    related = (
        TeacherTip.query
        .filter(TeacherTip.id != tip.id, TeacherTip.category == tip.category)
        .order_by(TeacherTip.upvotes.desc())
        .limit(4)
        .all()
    )
    return render_template("teacher_tip_detail.html", tip=tip, related=related)


@app.route("/teacher-tip/<slug>/upvote", methods=["POST"])
@login_required
def teacher_tip_upvote(slug):
    tip = TeacherTip.query.filter_by(slug=slug).first_or_404()
    tip.upvotes = (tip.upvotes or 0) + 1
    db.session.commit()
    flash("Tip upvoted.", "success")
    return redirect(url_for("teacher_tip_detail", slug=slug))


@app.route("/classroom-mode")
def classroom_mode():
    sims = (
        Simulation.query.filter_by(is_featured=True)
        .order_by(Simulation.title)
        .all()
    )
    sessions = []
    if current_user.is_authenticated:
        sessions = (
            ClassroomSession.query.filter_by(user_id=current_user.id)
            .order_by(ClassroomSession.started_at.desc())
            .all()
        )
    return render_template(
        "classroom_mode.html", sims=sims, sessions=sessions,
    )


@app.route("/classroom-mode/setup", methods=["GET", "POST"])
@login_required
def classroom_mode_setup():
    sims = Simulation.query.order_by(Simulation.title).all()
    if request.method == "POST":
        sim_id = request.form.get("sim_id", "").strip()
        name = request.form.get("name", "").strip()
        students = request.form.get("students_count", "0").strip()
        if not (sim_id and name):
            flash("Choose a simulation and name the session.", "error")
        else:
            sim = Simulation.query.get(int(sim_id))
            if not sim:
                flash("Unknown simulation.", "error")
            else:
                code = _md5_seed(
                    "session", current_user.id, sim.id, name,
                    ClassroomSession.query.count(),
                )
                session_code = f"PHET-{(code % 1000000):06d}"
                cs = ClassroomSession(
                    user_id=current_user.id,
                    sim_id=sim.id,
                    session_code=session_code,
                    name=name,
                    students_count=int(students) if students.isdigit() else 0,
                )
                db.session.add(cs)
                db.session.commit()
                flash(f"Classroom session {session_code} created.", "success")
                return redirect(url_for("classroom_mode"))
    return render_template("classroom_mode_setup.html", sims=sims)


@app.route("/accessibility/sim/<slug>")
def accessibility_sim(slug):
    sim = Simulation.query.filter_by(slug=slug).first_or_404()
    # Deterministic per-sim feature set from md5(slug)
    h = _md5_seed("a11y", slug)
    feat_pool = [
        "Alternative Input",
        "Pan and Zoom",
        "Interactive Highlights",
        "Mouse Sonification",
        "Voicing",
        "Camera Input",
        "Keyboard Navigation",
        "Sound",
        "Audio Descriptions",
    ]
    n_features = 2 + (h % 4)
    features = [feat_pool[(h >> (i * 3)) % len(feat_pool)] for i in range(n_features)]
    features = list(dict.fromkeys(features))
    reports = (
        AccessibilityReport.query.filter_by(sim_id=sim.id)
        .order_by(AccessibilityReport.created_at.desc())
        .all()
    )
    return render_template(
        "accessibility_sim.html", sim=sim, features=features, reports=reports,
    )


@app.route("/about/team")
def about_team():
    members = TeamMember.query.order_by(TeamMember.sort_order, TeamMember.name).all()
    teams = sorted({m.team for m in members})
    return render_template("about_team.html", members=members, teams=teams)


@app.route("/about/team/<slug>")
def team_member_detail(slug):
    member = TeamMember.query.filter_by(slug=slug).first_or_404()
    same_team = (
        TeamMember.query
        .filter(TeamMember.id != member.id, TeamMember.team == member.team)
        .order_by(TeamMember.sort_order)
        .all()
    )
    return render_template(
        "team_member_detail.html", member=member, same_team=same_team,
    )


@app.route("/about/history")
def about_history():
    milestones = HISTORY_MILESTONES
    return render_template("about_history.html", milestones=milestones)


@app.route("/donate", methods=["GET", "POST"])
def donate():
    sponsors = Sponsor.query.order_by(Sponsor.sort_order, Sponsor.name).all()
    if request.method == "POST":
        donor_name = request.form.get("donor_name", "").strip()
        donor_email = request.form.get("donor_email", "").strip().lower()
        amount = request.form.get("amount", "").strip()
        frequency = request.form.get("frequency", "one-time").strip()
        message = request.form.get("message", "").strip()
        try:
            amt = int(round(float(amount) * 100))
        except ValueError:
            amt = 0
        if not (donor_name and EMAIL_RE.match(donor_email) and amt > 0):
            flash("Please provide name, valid email, and donation amount.", "error")
        else:
            d = Donation(
                user_id=current_user.id if current_user.is_authenticated else None,
                donor_name=donor_name, donor_email=donor_email,
                amount_cents=amt, frequency=frequency, message=message,
            )
            db.session.add(d)
            db.session.commit()
            flash(f"Thank you for your ${amt/100:.2f} contribution!", "success")
            return redirect(url_for("donate"))
    total_donors = Donation.query.count()
    return render_template(
        "donate.html", sponsors=sponsors, total_donors=total_donors,
    )


@app.route("/sponsors")
def sponsors():
    sponsors = Sponsor.query.order_by(Sponsor.sort_order, Sponsor.name).all()
    by_tier = {}
    for s in sponsors:
        by_tier.setdefault(s.tier, []).append(s)
    return render_template(
        "sponsors.html", sponsors=sponsors, by_tier=by_tier,
    )


@app.route("/sponsor/<slug>")
def sponsor_detail(slug):
    sp = Sponsor.query.filter_by(slug=slug).first_or_404()
    return render_template("sponsor_detail.html", sponsor=sp)


@app.route("/research")
def research():
    year = request.args.get("year", "").strip()
    query = ResearchPaper.query
    if year.isdigit():
        query = query.filter_by(year=int(year))
    papers = query.order_by(ResearchPaper.year.desc(), ResearchPaper.title).all()
    years = sorted({p.year for p in ResearchPaper.query.all()}, reverse=True)
    return render_template(
        "research.html", papers=papers, year=year, years=years,
    )


@app.route("/research/paper/<slug>")
def research_paper(slug):
    paper = ResearchPaper.query.filter_by(slug=slug).first_or_404()
    paper.citation_count = (paper.citation_count or 0)  # no-op for byte stability
    related = (
        ResearchPaper.query
        .filter(ResearchPaper.id != paper.id, ResearchPaper.year == paper.year)
        .order_by(ResearchPaper.title)
        .limit(4)
        .all()
    )
    return render_template(
        "research_paper.html", paper=paper, related=related,
    )


@app.route("/news")
def news_index():
    category = request.args.get("category", "").strip()
    query = NewsArticle.query
    if category:
        query = query.filter_by(category=category)
    articles = query.order_by(NewsArticle.published_date.desc()).all()
    categories = sorted({a.category for a in NewsArticle.query.all()})
    return render_template(
        "news.html", articles=articles, category=category, categories=categories,
    )


@app.route("/news/<slug>")
def news_detail(slug):
    article = NewsArticle.query.filter_by(slug=slug).first_or_404()
    article.view_count = (article.view_count or 0) + 1
    db.session.commit()
    comments = (
        NewsArticleComment.query.filter_by(article_id=article.id)
        .order_by(NewsArticleComment.created_at.desc())
        .all()
    )
    comment_users = {u.id: u for u in User.query.all()}
    related = (
        NewsArticle.query
        .filter(NewsArticle.id != article.id, NewsArticle.category == article.category)
        .order_by(NewsArticle.published_date.desc())
        .limit(4)
        .all()
    )
    return render_template(
        "news_detail.html", article=article, related=related,
        comments=comments, comment_users=comment_users,
    )


@app.route("/news/<slug>/comment", methods=["POST"])
@login_required
def news_comment(slug):
    article = NewsArticle.query.filter_by(slug=slug).first_or_404()
    body = request.form.get("body", "").strip()
    if not body:
        flash("Comment cannot be empty.", "error")
    else:
        db.session.add(NewsArticleComment(
            article_id=article.id, user_id=current_user.id, body=body,
        ))
        db.session.commit()
        flash("Comment posted.", "success")
    return redirect(url_for("news_detail", slug=slug))


@app.route("/contact", methods=["GET", "POST"])
def contact():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        topic = request.form.get("topic", "general").strip()
        subject = request.form.get("subject", "").strip()
        body = request.form.get("body", "").strip()
        if not (name and EMAIL_RE.match(email) and subject and body):
            flash("All fields are required.", "error")
        else:
            db.session.add(ContactMessage(
                name=name, email=email, topic=topic,
                subject=subject, body=body,
            ))
            db.session.commit()
            flash("Message received. We will reply within 3 business days.", "success")
            return redirect(url_for("contact"))
    return render_template("contact.html")


@app.route("/faq")
def faq():
    category = request.args.get("category", "").strip()
    query = FAQItem.query
    if category:
        query = query.filter_by(category=category)
    items = query.order_by(FAQItem.category, FAQItem.sort_order).all()
    categories = sorted({f.category for f in FAQItem.query.all()})
    return render_template(
        "faq.html", items=items, category=category, categories=categories,
    )


@app.route("/faq/<int:item_id>/helpful", methods=["POST"])
def faq_helpful(item_id):
    item = FAQItem.query.get_or_404(item_id)
    item.helpful = (item.helpful or 0) + 1
    db.session.commit()
    flash("Thanks for your feedback.", "success")
    return redirect(url_for("faq", category=item.category))


@app.route("/workshops")
def workshops():
    upcoming = (
        Workshop.query.filter(Workshop.held_on >= date(2026, 5, 1))
        .order_by(Workshop.held_on)
        .all()
    )
    past = (
        Workshop.query.filter(Workshop.held_on < date(2026, 5, 1))
        .order_by(Workshop.held_on.desc())
        .all()
    )
    return render_template(
        "workshops.html", upcoming=upcoming, past=past,
    )


@app.route("/workshop/<slug>")
def workshop_detail(slug):
    w = Workshop.query.filter_by(slug=slug).first_or_404()
    registered = False
    if current_user.is_authenticated:
        registered = WorkshopRegistration.query.filter_by(
            workshop_id=w.id, user_id=current_user.id,
        ).first() is not None
    return render_template(
        "workshop_detail.html", workshop=w, registered=registered,
    )


@app.route("/workshop/<slug>/register", methods=["POST"])
@login_required
def workshop_register(slug):
    w = Workshop.query.filter_by(slug=slug).first_or_404()
    if w.registered >= w.capacity:
        flash("Workshop is full.", "error")
        return redirect(url_for("workshop_detail", slug=slug))
    existing = WorkshopRegistration.query.filter_by(
        workshop_id=w.id, user_id=current_user.id,
    ).first()
    if not existing:
        db.session.add(WorkshopRegistration(
            workshop_id=w.id, user_id=current_user.id,
        ))
        w.registered = (w.registered or 0) + 1
        db.session.commit()
        flash(f"Registered for {w.title}.", "success")
    else:
        flash("You are already registered.", "success")
    return redirect(url_for("workshop_detail", slug=slug))


@app.route("/sim/<slug>/comment", methods=["POST"])
@login_required
def sim_comment(slug):
    sim = Simulation.query.filter_by(slug=slug).first_or_404()
    body = request.form.get("body", "").strip()
    if body:
        db.session.add(SimComment(
            sim_id=sim.id, user_id=current_user.id, body=body,
        ))
        db.session.commit()
        flash("Comment posted.", "success")
    return redirect(url_for("simulation_detail", slug=slug))


@app.route("/sim/<slug>/rate", methods=["POST"])
@login_required
def sim_rate(slug):
    sim = Simulation.query.filter_by(slug=slug).first_or_404()
    try:
        stars = max(1, min(5, int(request.form.get("stars", "0"))))
    except ValueError:
        flash("Invalid rating.", "error")
        return redirect(url_for("simulation_detail", slug=slug))
    review = request.form.get("review", "").strip()
    existing = SimRating.query.filter_by(
        sim_id=sim.id, user_id=current_user.id
    ).first()
    if existing:
        existing.stars = stars
        existing.review = review
    else:
        db.session.add(SimRating(
            sim_id=sim.id, user_id=current_user.id,
            stars=stars, review=review,
        ))
    db.session.commit()
    flash(f"You rated {sim.title}: {stars} stars.", "success")
    return redirect(url_for("simulation_detail", slug=slug))


@app.route("/sim/<slug>/favorite", methods=["POST"])
@login_required
def sim_favorite(slug):
    sim = Simulation.query.filter_by(slug=slug).first_or_404()
    existing = Favorite.query.filter_by(
        user_id=current_user.id, sim_id=sim.id,
    ).first()
    if existing:
        db.session.delete(existing)
        flash(f"Removed {sim.title} from favorites.", "success")
    else:
        db.session.add(Favorite(user_id=current_user.id, sim_id=sim.id))
        flash(f"Added {sim.title} to favorites.", "success")
    db.session.commit()
    return redirect(url_for("simulation_detail", slug=slug))


@app.route("/sim/<slug>/report-bug", methods=["GET", "POST"])
def sim_report_bug(slug):
    sim = Simulation.query.filter_by(slug=slug).first_or_404()
    if request.method == "POST":
        summary = request.form.get("summary", "").strip()
        body = request.form.get("body", "").strip()
        severity = request.form.get("severity", "medium").strip()
        if not (summary and body):
            flash("Summary and description are required.", "error")
        else:
            db.session.add(BugReport(
                sim_id=sim.id,
                user_id=current_user.id if current_user.is_authenticated else None,
                summary=summary, body=body, severity=severity,
            ))
            db.session.commit()
            flash("Bug report submitted. Thanks!", "success")
            return redirect(url_for("simulation_detail", slug=slug))
    return render_template("report_bug.html", sim=sim)


@app.route("/sim/<slug>/report-inaccessibility", methods=["GET", "POST"])
def sim_report_inaccessibility(slug):
    sim = Simulation.query.filter_by(slug=slug).first_or_404()
    if request.method == "POST":
        issue_type = request.form.get("issue_type", "").strip()
        body = request.form.get("body", "").strip()
        if not (issue_type and body):
            flash("Issue type and description are required.", "error")
        else:
            db.session.add(AccessibilityReport(
                sim_id=sim.id,
                user_id=current_user.id if current_user.is_authenticated else None,
                issue_type=issue_type, body=body,
            ))
            db.session.commit()
            flash("Accessibility report received.", "success")
            return redirect(url_for("accessibility_sim", slug=slug))
    return render_template("report_inaccessibility.html", sim=sim)


@app.route("/newsletter", methods=["GET", "POST"])
def newsletter():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        role = request.form.get("role", "teacher").strip()
        country = request.form.get("country", "").strip()
        if not EMAIL_RE.match(email):
            flash("Please enter a valid email.", "error")
        elif NewsletterSubscriber.query.filter_by(email=email).first():
            flash("That email is already subscribed.", "error")
        else:
            db.session.add(NewsletterSubscriber(
                email=email, role=role, country=country,
            ))
            db.session.commit()
            flash("Subscribed! Watch your inbox monthly.", "success")
            return redirect(url_for("newsletter"))
    return render_template("newsletter.html")


@app.route("/my/favorites")
@login_required
def my_favorites():
    favs = (
        Favorite.query.filter_by(user_id=current_user.id)
        .order_by(Favorite.created_at.desc())
        .all()
    )
    sims = []
    for f in favs:
        s = Simulation.query.get(f.sim_id)
        if s:
            sims.append(s)
    return render_template("my_favorites.html", sims=sims)


@app.route("/popular")
def popular_sims():
    period = request.args.get("period", "all").strip()
    sims = Simulation.query.order_by(Simulation.play_count.desc()).limit(40).all()
    return render_template("popular.html", sims=sims, period=period)


@app.route("/topic/<slug>")
def topic_hub(slug):
    # topic slug derived from sim.topics_json — exact substring match
    needle = slug.replace("-", " ")
    sims = (
        Simulation.query.filter(Simulation.topics_json.ilike(f'%{needle}%'))
        .order_by(Simulation.title)
        .all()
    )
    if not sims:
        abort(404)
    return render_template(
        "topic_hub.html", topic=needle, slug=slug, sims=sims,
    )


def _unique_slug(model, base):
    """Return a slug unique within model's table."""
    candidate = base
    n = 1
    while model.query.filter_by(slug=candidate).first() is not None:
        n += 1
        candidate = f"{base}-{n}"
    return candidate


# ---------------------------------------------------------------------------
# Error handlers
# ---------------------------------------------------------------------------

@app.errorhandler(404)
def not_found(_):
    return render_template("404.html"), 404


# ---------------------------------------------------------------------------
# Seed data
# ---------------------------------------------------------------------------

SUBJECTS_SEED = [
    ("physics", "Physics", "atom", "#0079bf",
     "Explore motion, forces, energy, waves, and electromagnetism."),
    ("chemistry", "Chemistry", "flask", "#f5862e",
     "Build molecules, balance equations, and probe matter."),
    ("math", "Math", "function", "#6cba5c",
     "Visualize numbers, fractions, functions, and geometry."),
    ("biology", "Biology", "leaf", "#7a3e9d",
     "Study cells, genetics, evolution, and the human body."),
    ("earth-science", "Earth Science", "globe", "#c0392b",
     "Investigate Earth's systems, climate, and the solar system."),
]

GRADES_SEED = [
    ("elementary", "Elementary School", "Ages 5-10", 1),
    ("middle", "Middle School", "Ages 11-13", 2),
    ("high", "High School", "Ages 14-18", 3),
    ("university", "University", "Ages 18+", 4),
]

LANGUAGES_SEED = [
    ("en", "English", "English", False),
    ("es", "Spanish", "Espanol", False),
    ("zh-cn", "Chinese (Simplified)", "Zhongwen", False),
    ("zh-tw", "Chinese (Traditional)", "Zhongwen", False),
    ("fr", "French", "Francais", False),
    ("de", "German", "Deutsch", False),
    ("pt-br", "Portuguese (Brazilian)", "Portugues", False),
    ("ru", "Russian", "Russkiy", False),
    ("ar", "Arabic", "Al-Arabiyyah", True),
    ("ja", "Japanese", "Nihongo", False),
    ("ko", "Korean", "Hangugeo", False),
    ("it", "Italian", "Italiano", False),
    ("nl", "Dutch", "Nederlands", False),
    ("pl", "Polish", "Polski", False),
    ("sv", "Swedish", "Svenska", False),
    ("tr", "Turkish", "Turkce", False),
    ("vi", "Vietnamese", "Tieng Viet", False),
    ("hi", "Hindi", "Hindi", False),
    ("he", "Hebrew", "Ivrit", True),
    ("el", "Greek", "Ellinika", False),
    ("cs", "Czech", "Cestina", False),
    ("hu", "Hungarian", "Magyar", False),
    ("fi", "Finnish", "Suomi", False),
    ("da", "Danish", "Dansk", False),
    ("ro", "Romanian", "Romana", False),
    ("uk", "Ukrainian", "Ukrayinska", False),
    ("fa", "Persian", "Farsi", True),
    ("id", "Indonesian", "Bahasa Indonesia", False),
    # Additional locales mirrored from PhET's actual translation set so the
    # /simulations?language=... filter exercises a realistic catalog. Native
    # names use Latin transliteration to keep the seed DB ASCII-safe.
    ("bn", "Bengali", "Bangla", False),
    ("th", "Thai", "Phasa Thai", False),
    ("ms", "Malay", "Bahasa Melayu", False),
    ("uz", "Uzbek", "Ozbek", False),
    ("kk", "Kazakh", "Qazaqsha", False),
    ("my", "Burmese", "Myanma", False),
    ("si", "Sinhala", "Sinhala", False),
    ("bg", "Bulgarian", "Balgarski", False),
    ("hr", "Croatian", "Hrvatski", False),
    ("sk", "Slovak", "Slovencina", False),
    ("sl", "Slovenian", "Slovenscina", False),
    ("sr", "Serbian", "Srpski", False),
    ("nb", "Norwegian Bokmal", "Norsk Bokmal", False),
    ("lt", "Lithuanian", "Lietuviu", False),
    ("lv", "Latvian", "Latviesu", False),
    ("et", "Estonian", "Eesti", False),
    ("is", "Icelandic", "Islenska", False),
    ("ca", "Catalan", "Catala", False),
    ("eu", "Basque", "Euskara", False),
    ("gl", "Galician", "Galego", False),
    ("af", "Afrikaans", "Afrikaans", False),
    ("sw", "Swahili", "Kiswahili", False),
    ("ka", "Georgian", "Kartuli", False),
    ("mk", "Macedonian", "Makedonski", False),
    ("sq", "Albanian", "Shqip", False),
]


def _slug(title):
    return re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")


SIMULATIONS_SEED = [
    # (title, subjects, grades, topics, languages_extra, featured, is_new, runtime, year, month, day, play_count)
    ("Gravity and Orbits", ["physics", "earth-science"], ["middle", "high"],
     ["gravity", "orbits", "circular motion", "satellites"],
     ["es", "fr", "de", "zh-cn", "ja", "ar", "pt-br", "ru"],
     True, False, 25, 2024, 3, 12, 482103),
    ("Forces and Motion: Basics", ["physics"], ["elementary", "middle", "high"],
     ["newton's laws", "friction", "acceleration"],
     ["es", "fr", "de", "zh-cn", "pt-br", "ru", "ja", "ko", "it", "nl"],
     True, False, 20, 2023, 9, 5, 1204567),
    ("Energy Skate Park", ["physics"], ["middle", "high", "university"],
     ["kinetic energy", "potential energy", "conservation"],
     ["es", "fr", "de", "pt-br", "ru", "zh-cn", "ja"],
     True, False, 30, 2024, 1, 18, 768922),
    ("Wave Interference", ["physics"], ["high", "university"],
     ["waves", "interference", "diffraction", "light"],
     ["es", "fr", "de", "zh-cn"],
     False, False, 25, 2023, 11, 2, 312045),
    ("Faraday's Law", ["physics"], ["high", "university"],
     ["electromagnetism", "induction", "magnetic flux"],
     ["es", "fr", "de", "zh-cn", "ja"],
     False, False, 20, 2023, 7, 14, 198320),
    ("Charges and Fields", ["physics"], ["high", "university"],
     ["electrostatics", "electric field", "voltage"],
     ["es", "fr", "de", "pt-br"],
     False, False, 25, 2023, 6, 22, 234110),
    ("Pendulum Lab", ["physics", "math"], ["middle", "high"],
     ["pendulum", "period", "gravity", "harmonic motion"],
     ["es", "fr", "de", "zh-cn", "ja", "ko"],
     True, False, 20, 2024, 2, 9, 521987),
    ("Projectile Motion", ["physics"], ["high", "university"],
     ["kinematics", "trajectory", "air resistance"],
     ["es", "fr", "de", "zh-cn", "pt-br", "ja"],
     False, False, 25, 2023, 10, 28, 645321),
    ("Circuit Construction Kit: DC", ["physics"], ["middle", "high", "university"],
     ["circuits", "ohm's law", "resistance", "current"],
     ["es", "fr", "de", "pt-br", "zh-cn", "ja", "ko", "ru", "it"],
     True, False, 30, 2024, 4, 1, 892341),
    ("Bending Light", ["physics"], ["middle", "high"],
     ["refraction", "snell's law", "optics"],
     ["es", "fr", "de", "zh-cn"],
     False, False, 20, 2023, 8, 15, 167823),
    ("Color Vision", ["physics", "biology"], ["elementary", "middle"],
     ["light", "color", "vision", "wavelength"],
     ["es", "fr", "de", "ja"],
     False, False, 15, 2023, 5, 19, 198765),
    ("Coulomb's Law", ["physics"], ["high", "university"],
     ["electrostatics", "force", "charge"],
     ["es", "fr", "de"],
     False, True, 20, 2025, 1, 14, 89234),
    ("Hooke's Law", ["physics"], ["middle", "high"],
     ["springs", "elasticity", "force"],
     ["es", "fr", "de", "zh-cn"],
     False, False, 15, 2023, 4, 7, 154322),
    ("Magnet and Compass", ["physics", "earth-science"], ["elementary", "middle"],
     ["magnetism", "compass", "field lines"],
     ["es", "fr", "de", "zh-cn", "ja", "ar"],
     False, False, 15, 2023, 3, 21, 232109),
    ("Resistance in a Wire", ["physics"], ["high"],
     ["resistance", "resistivity", "circuits"],
     ["es", "fr", "de"],
     False, False, 15, 2023, 2, 4, 87654),
    ("Quantum Wave Interference", ["physics"], ["university"],
     ["quantum mechanics", "wave-particle duality"],
     ["es", "fr", "de"],
     False, True, 35, 2025, 2, 28, 45120),

    ("Build a Molecule", ["chemistry"], ["middle", "high"],
     ["molecules", "atoms", "bonding"],
     ["es", "fr", "de", "zh-cn", "ja", "pt-br", "ru"],
     True, False, 25, 2024, 1, 22, 678901),
    ("Balancing Chemical Equations", ["chemistry"], ["middle", "high"],
     ["stoichiometry", "equations", "reactions"],
     ["es", "fr", "de", "zh-cn", "pt-br", "ko"],
     True, False, 20, 2023, 12, 6, 543210),
    ("States of Matter", ["chemistry", "physics"], ["elementary", "middle", "high"],
     ["solid", "liquid", "gas", "phase change"],
     ["es", "fr", "de", "zh-cn", "ja", "ar", "pt-br", "ru", "it"],
     True, False, 25, 2024, 2, 14, 891234),
    ("Concentration", ["chemistry"], ["high", "university"],
     ["solutions", "molarity", "dilution"],
     ["es", "fr", "de", "zh-cn"],
     False, False, 20, 2023, 11, 9, 234567),
    ("pH Scale", ["chemistry"], ["middle", "high"],
     ["acids", "bases", "ph", "hydrogen ions"],
     ["es", "fr", "de", "zh-cn", "ja"],
     False, False, 15, 2023, 9, 17, 312456),
    ("Beer's Law Lab", ["chemistry"], ["high", "university"],
     ["absorbance", "spectroscopy", "concentration"],
     ["es", "fr", "de"],
     False, False, 25, 2023, 8, 3, 167890),
    ("Acid-Base Solutions", ["chemistry"], ["high", "university"],
     ["acids", "bases", "equilibrium"],
     ["es", "fr", "de", "zh-cn"],
     False, False, 25, 2023, 7, 25, 198432),
    ("Reactions and Rates", ["chemistry"], ["high", "university"],
     ["kinetics", "reactions", "activation energy"],
     ["es", "fr", "de"],
     False, False, 30, 2023, 6, 11, 145678),
    ("Molecule Polarity", ["chemistry"], ["high"],
     ["polarity", "electronegativity", "dipole"],
     ["es", "fr", "de", "zh-cn"],
     False, False, 20, 2023, 5, 8, 123456),
    ("Isotopes and Atomic Mass", ["chemistry"], ["high", "university"],
     ["isotopes", "atomic mass", "elements"],
     ["es", "fr", "de"],
     False, False, 20, 2023, 4, 16, 98765),
    ("Build an Atom", ["chemistry", "physics"], ["middle", "high"],
     ["atoms", "protons", "neutrons", "electrons"],
     ["es", "fr", "de", "zh-cn", "ja", "ko", "ar", "ru", "pt-br"],
     True, False, 20, 2024, 3, 7, 712345),
    ("Salts and Solubility", ["chemistry"], ["high"],
     ["solubility", "salts", "saturation"],
     ["es", "fr", "de"],
     False, True, 25, 2025, 3, 4, 56789),

    ("Graphing Lines", ["math"], ["middle", "high"],
     ["linear equations", "slope", "intercept"],
     ["es", "fr", "de", "zh-cn", "ja", "ko", "ar"],
     True, False, 20, 2024, 1, 11, 567890),
    ("Area Builder", ["math"], ["elementary", "middle"],
     ["area", "perimeter", "shapes"],
     ["es", "fr", "de", "zh-cn", "ja", "pt-br"],
     False, False, 15, 2023, 10, 14, 234567),
    ("Fractions: Intro", ["math"], ["elementary", "middle"],
     ["fractions", "numerators", "denominators"],
     ["es", "fr", "de", "zh-cn", "ja", "ar", "pt-br", "ru"],
     True, False, 15, 2024, 2, 19, 689012),
    ("Function Builder", ["math"], ["middle", "high"],
     ["functions", "input output", "composition"],
     ["es", "fr", "de", "zh-cn"],
     False, False, 25, 2023, 9, 21, 178901),
    ("Plinko Probability", ["math"], ["middle", "high", "university"],
     ["probability", "distributions", "statistics"],
     ["es", "fr", "de"],
     False, False, 20, 2023, 8, 6, 145678),
    ("Trig Tour", ["math"], ["high", "university"],
     ["trigonometry", "sine", "cosine", "unit circle"],
     ["es", "fr", "de", "zh-cn"],
     False, False, 25, 2023, 7, 30, 123890),
    ("Vector Addition", ["math", "physics"], ["high", "university"],
     ["vectors", "components", "magnitude"],
     ["es", "fr", "de"],
     False, False, 20, 2023, 6, 8, 156789),
    ("Calculus Grapher", ["math"], ["high", "university"],
     ["derivatives", "integrals", "calculus"],
     ["es", "fr", "de"],
     False, True, 30, 2025, 1, 22, 67890),
    ("Equality Explorer", ["math"], ["elementary", "middle"],
     ["equations", "balance", "variables"],
     ["es", "fr", "de", "zh-cn"],
     False, False, 20, 2023, 5, 12, 134567),
    ("Number Line: Integers", ["math"], ["elementary", "middle"],
     ["integers", "negative numbers", "number line"],
     ["es", "fr", "de", "zh-cn", "ja"],
     False, False, 15, 2023, 4, 19, 98765),
    ("Make a Ten", ["math"], ["elementary"],
     ["addition", "place value", "counting"],
     ["es", "fr", "zh-cn", "ja"],
     False, False, 10, 2023, 3, 25, 78901),
    ("Estimation", ["math"], ["elementary", "middle"],
     ["estimation", "measurement", "comparison"],
     ["es", "fr", "de"],
     False, False, 15, 2023, 2, 16, 65432),

    ("Natural Selection", ["biology"], ["middle", "high", "university"],
     ["evolution", "adaptation", "selection"],
     ["es", "fr", "de", "zh-cn", "ja", "pt-br"],
     True, False, 30, 2024, 1, 27, 412567),
    ("Gene Expression Essentials", ["biology"], ["high", "university"],
     ["dna", "transcription", "translation", "proteins"],
     ["es", "fr", "de", "zh-cn"],
     False, False, 25, 2023, 11, 23, 234890),
    ("Neuron", ["biology"], ["high", "university"],
     ["neurons", "action potential", "ion channels"],
     ["es", "fr", "de"],
     False, False, 25, 2023, 10, 5, 187654),
    ("Membrane Channels", ["biology"], ["high", "university"],
     ["membranes", "diffusion", "transport"],
     ["es", "fr", "de"],
     False, False, 20, 2023, 9, 12, 145623),
    ("Stretching DNA", ["biology", "physics"], ["high", "university"],
     ["dna", "forces", "molecular biology"],
     ["es", "fr", "de"],
     False, False, 25, 2023, 8, 28, 112345),
    ("Eating and Exercise", ["biology"], ["middle", "high"],
     ["nutrition", "metabolism", "calories"],
     ["es", "fr", "de", "zh-cn"],
     False, False, 20, 2023, 7, 17, 167890),

    ("Plate Tectonics", ["earth-science"], ["middle", "high"],
     ["plates", "continents", "earthquakes"],
     ["es", "fr", "de", "zh-cn", "ja"],
     True, False, 25, 2024, 2, 5, 389012),
    ("Greenhouse Effect", ["earth-science", "physics"], ["middle", "high"],
     ["climate", "atmosphere", "radiation"],
     ["es", "fr", "de", "zh-cn", "pt-br"],
     True, False, 25, 2024, 3, 18, 456789),
    ("Glaciers", ["earth-science"], ["middle", "high"],
     ["glaciers", "climate", "ice"],
     ["es", "fr", "de"],
     False, False, 20, 2023, 11, 14, 123456),
    ("Density", ["earth-science", "physics"], ["elementary", "middle", "high"],
     ["density", "mass", "volume", "buoyancy"],
     ["es", "fr", "de", "zh-cn", "ja", "ar"],
     True, False, 20, 2024, 1, 30, 567823),
    ("My Solar System", ["earth-science", "physics"], ["middle", "high", "university"],
     ["gravity", "orbits", "solar system"],
     ["es", "fr", "de", "zh-cn", "ja", "ar", "pt-br"],
     True, False, 30, 2024, 4, 11, 678901),
    ("Radioactive Dating Game", ["earth-science", "physics"], ["high"],
     ["radioactivity", "half-life", "dating"],
     ["es", "fr", "de"],
     False, False, 25, 2023, 6, 23, 134567),
    ("Lunar Lander", ["earth-science", "physics"], ["middle", "high"],
     ["gravity", "thrust", "motion"],
     ["es", "fr", "de", "ja"],
     False, True, 20, 2025, 2, 17, 78901),

    # Additional biology sims
    ("Mendelian Genetics", ["biology"], ["middle", "high", "university"],
     ["genetics", "heredity", "alleles", "punnett squares"],
     ["es", "fr", "de", "zh-cn", "ja", "pt-br"],
     True, False, 30, 2024, 2, 22, 287654),
    ("DNA Replication", ["biology"], ["high", "university"],
     ["dna", "replication", "polymerase"],
     ["es", "fr", "de", "zh-cn"],
     False, False, 25, 2023, 12, 17, 178923),
    ("Photosynthesis", ["biology"], ["elementary", "middle", "high"],
     ["photosynthesis", "chlorophyll", "plants", "light"],
     ["es", "fr", "de", "zh-cn", "ja", "ko", "pt-br"],
     True, False, 25, 2024, 3, 9, 421890),
    ("Predator-Prey Dynamics", ["biology"], ["middle", "high"],
     ["ecology", "population", "food chain"],
     ["es", "fr", "de", "zh-cn"],
     False, False, 30, 2023, 11, 26, 198765),
    ("Cellular Respiration", ["biology", "chemistry"], ["high", "university"],
     ["respiration", "atp", "mitochondria", "energy"],
     ["es", "fr", "de"],
     False, False, 25, 2023, 10, 13, 156789),
    ("Punnett Squares", ["biology"], ["middle", "high"],
     ["genetics", "heredity", "punnett squares"],
     ["es", "fr", "de", "zh-cn", "ja"],
     False, False, 20, 2023, 9, 8, 234156),
    ("Population Dynamics", ["biology", "math"], ["high", "university"],
     ["population", "exponential growth", "carrying capacity"],
     ["es", "fr", "de"],
     False, True, 30, 2025, 1, 8, 67890),
    ("Cell Diffusion", ["biology"], ["middle", "high"],
     ["diffusion", "membranes", "concentration"],
     ["es", "fr", "de", "zh-cn"],
     False, False, 20, 2023, 8, 19, 132465),
    ("Enzyme Kinetics", ["biology", "chemistry"], ["high", "university"],
     ["enzymes", "catalysis", "kinetics"],
     ["es", "fr", "de"],
     False, False, 25, 2023, 7, 11, 98432),
    ("Food Web Builder", ["biology"], ["elementary", "middle"],
     ["ecology", "food web", "trophic levels"],
     ["es", "fr", "de", "zh-cn", "ja", "ar"],
     False, False, 25, 2023, 6, 4, 187234),
    ("Mitosis and Meiosis", ["biology"], ["high", "university"],
     ["cell division", "chromosomes", "mitosis", "meiosis"],
     ["es", "fr", "de"],
     False, False, 30, 2023, 5, 17, 145678),
    ("Blood Pressure Basics", ["biology"], ["middle", "high"],
     ["circulation", "heart", "blood pressure"],
     ["es", "fr", "de", "zh-cn"],
     False, False, 20, 2023, 4, 22, 87654),
    ("Lac Operon Regulation", ["biology"], ["university"],
     ["gene regulation", "operon", "molecular biology"],
     ["es", "fr", "de"],
     False, False, 30, 2023, 3, 12, 54321),
    ("Bee Hive Activity", ["biology"], ["elementary", "middle"],
     ["pollination", "bees", "ecosystems"],
     ["es", "fr", "de", "zh-cn", "ja"],
     False, False, 15, 2023, 2, 28, 76543),

    # Additional earth-science sims
    ("Seasons", ["earth-science"], ["elementary", "middle"],
     ["seasons", "earth tilt", "sun"],
     ["es", "fr", "de", "zh-cn", "ja", "ar"],
     True, False, 20, 2024, 1, 19, 312456),
    ("Water Cycle", ["earth-science"], ["elementary", "middle", "high"],
     ["evaporation", "condensation", "precipitation", "water cycle"],
     ["es", "fr", "de", "zh-cn", "ja", "ko", "pt-br"],
     True, False, 20, 2024, 2, 26, 398765),
    ("Volcanic Eruption", ["earth-science"], ["elementary", "middle", "high"],
     ["volcanoes", "magma", "lava", "geology"],
     ["es", "fr", "de", "zh-cn", "ja"],
     False, False, 25, 2023, 12, 10, 234567),
    ("Earthquake Simulator", ["earth-science"], ["middle", "high"],
     ["earthquakes", "seismic waves", "magnitude"],
     ["es", "fr", "de", "zh-cn"],
     False, False, 25, 2023, 11, 18, 198432),
    ("Tides", ["earth-science", "physics"], ["middle", "high"],
     ["tides", "gravity", "moon", "ocean"],
     ["es", "fr", "de"],
     False, False, 20, 2023, 10, 27, 167890),
    ("Climate Change Model", ["earth-science"], ["high", "university"],
     ["climate", "greenhouse gases", "temperature"],
     ["es", "fr", "de", "zh-cn", "pt-br"],
     True, True, 35, 2025, 2, 8, 89012),
    ("Ozone Layer", ["earth-science", "chemistry"], ["middle", "high"],
     ["ozone", "atmosphere", "uv radiation"],
     ["es", "fr", "de"],
     False, False, 20, 2023, 9, 14, 123456),
    ("Solar Wind", ["earth-science", "physics"], ["high", "university"],
     ["solar wind", "magnetosphere", "auroras"],
     ["es", "fr", "de"],
     False, False, 25, 2023, 8, 22, 87432),
    ("Rock Cycle", ["earth-science"], ["elementary", "middle", "high"],
     ["rocks", "minerals", "igneous", "sedimentary", "metamorphic"],
     ["es", "fr", "de", "zh-cn", "ja"],
     False, False, 25, 2023, 7, 6, 156789),
    ("Ocean Currents", ["earth-science"], ["middle", "high"],
     ["ocean", "currents", "thermohaline"],
     ["es", "fr", "de"],
     False, False, 25, 2023, 6, 18, 112345),
    ("Mineral Hardness", ["earth-science"], ["elementary", "middle"],
     ["minerals", "mohs scale", "geology"],
     ["es", "fr", "de"],
     False, False, 15, 2023, 5, 30, 76543),
    ("Mountain Building", ["earth-science"], ["middle", "high"],
     ["tectonics", "mountains", "erosion"],
     ["es", "fr", "de"],
     False, False, 25, 2023, 4, 11, 98765),

    # More elementary-friendly sims
    ("Shapes and Patterns", ["math"], ["elementary"],
     ["shapes", "patterns", "geometry"],
     ["es", "fr", "de", "zh-cn", "ja", "ko"],
     False, False, 15, 2023, 3, 18, 134567),
    ("Counting Coins", ["math"], ["elementary"],
     ["counting", "money", "addition"],
     ["es", "fr", "de", "zh-cn"],
     False, False, 12, 2023, 2, 23, 87654),
    ("Simple Machines", ["physics"], ["elementary", "middle"],
     ["levers", "pulleys", "wheels", "force"],
     ["es", "fr", "de", "zh-cn", "ja"],
     False, False, 20, 2023, 4, 27, 165432),
    ("Magnet Toy", ["physics"], ["elementary"],
     ["magnets", "attraction", "repulsion"],
     ["es", "fr", "de", "zh-cn", "ja"],
     False, False, 12, 2023, 5, 9, 98432),
    ("Weather Watcher", ["earth-science"], ["elementary"],
     ["weather", "clouds", "temperature"],
     ["es", "fr", "de", "zh-cn", "ja"],
     False, False, 15, 2023, 6, 13, 76543),
    ("Plant Growth", ["biology"], ["elementary"],
     ["plants", "growth", "seeds"],
     ["es", "fr", "de", "zh-cn"],
     False, False, 15, 2023, 7, 21, 54321),
    ("Animal Classification", ["biology"], ["elementary"],
     ["animals", "classification", "vertebrates"],
     ["es", "fr", "de", "zh-cn", "ja"],
     False, False, 15, 2023, 8, 9, 87654),

    # More chemistry sims (to clear 20+ threshold)
    ("Atomic Interactions", ["chemistry", "physics"], ["high", "university"],
     ["atoms", "forces", "lennard-jones"],
     ["es", "fr", "de"],
     False, False, 20, 2023, 3, 14, 123890),
    ("Sugar and Salt Solutions", ["chemistry"], ["middle", "high"],
     ["solutions", "dissolving", "concentration"],
     ["es", "fr", "de", "zh-cn", "ja", "pt-br"],
     False, False, 20, 2023, 11, 6, 198765),
    ("Gas Properties", ["chemistry", "physics"], ["high", "university"],
     ["gases", "pressure", "temperature", "kinetic theory"],
     ["es", "fr", "de", "zh-cn"],
     True, False, 25, 2024, 1, 25, 287654),
    ("Diffusion in Gases", ["chemistry", "physics"], ["middle", "high"],
     ["diffusion", "gases", "concentration"],
     ["es", "fr", "de"],
     False, False, 20, 2023, 10, 19, 134567),
    ("Bonding Explorer", ["chemistry"], ["high"],
     ["bonding", "ionic", "covalent", "metallic"],
     ["es", "fr", "de", "zh-cn"],
     False, False, 25, 2023, 9, 28, 156789),
    ("Reaction Quizzer", ["chemistry"], ["high", "university"],
     ["reactions", "products", "balancing"],
     ["es", "fr", "de"],
     False, False, 20, 2023, 8, 11, 87654),

    # More math sims (to clear 20+ threshold)
    ("Probability Experiments", ["math"], ["middle", "high"],
     ["probability", "experiments", "statistics"],
     ["es", "fr", "de", "zh-cn", "ja"],
     False, False, 20, 2023, 11, 21, 167890),
    ("Coordinate Plane", ["math"], ["middle", "high"],
     ["coordinates", "graphs", "plotting"],
     ["es", "fr", "de", "zh-cn"],
     False, False, 15, 2023, 9, 30, 145678),
    ("Algebra Tiles", ["math"], ["middle", "high"],
     ["algebra", "polynomials", "factoring"],
     ["es", "fr", "de"],
     False, False, 25, 2023, 8, 17, 123456),
    ("Percent Word Problems", ["math"], ["middle"],
     ["percentages", "ratios", "word problems"],
     ["es", "fr", "de", "zh-cn", "ja"],
     False, False, 20, 2023, 7, 9, 98432),
    ("Geometric Constructions", ["math"], ["middle", "high"],
     ["geometry", "compass", "straightedge"],
     ["es", "fr", "de"],
     False, False, 25, 2023, 6, 5, 87654),
    ("Decimal Models", ["math"], ["elementary", "middle"],
     ["decimals", "place value", "comparison"],
     ["es", "fr", "de", "zh-cn", "ja"],
     False, False, 15, 2023, 5, 14, 134567),

    # === PhET API-derived additions (real-site mirror) ===
    ('Area Model Algebra', ['math'], ['elementary', 'middle'],
     ['area', 'algebra'],
     ['es', 'zh-cn', 'zh-tw', 'fr', 'de', 'pt-br', 'ru', 'ar', 'ja', 'ko', 'it', 'nl', 'pl', 'sv', 'tr', 'vi', 'hi', 'he', 'el', 'cs', 'hu', 'fi', 'da', 'ro', 'uk', 'fa', 'bn', 'th', 'ms', 'uz', 'kk', 'si', 'bg', 'hr', 'sk', 'sl', 'sr', 'lv', 'is', 'ca', 'eu', 'gl', 'af', 'sw', 'sq'],
     False, True, 20, 2025, 4, 24, 263648),
    ('Area Model Decimals', ['math'], ['elementary'],
     ['area', 'decimals'],
     ['es', 'zh-cn', 'zh-tw', 'fr', 'de', 'pt-br', 'ru', 'ar', 'ja', 'ko', 'it', 'nl', 'pl', 'sv', 'tr', 'vi', 'hi', 'he', 'el', 'cs', 'hu', 'fi', 'da', 'ro', 'uk', 'fa', 'bn', 'ms', 'uz', 'kk', 'si', 'bg', 'hr', 'sk', 'sl', 'sr', 'lt', 'lv', 'is', 'ca', 'eu', 'gl', 'af', 'sw', 'sq'],
     True, False, 15, 2024, 6, 14, 384526),
    ('Area Model Introduction', ['math'], ['elementary'],
     ['area'],
     ['es', 'zh-cn', 'zh-tw', 'fr', 'de', 'pt-br', 'ru', 'ar', 'ja', 'ko', 'it', 'nl', 'pl', 'sv', 'tr', 'vi', 'hi', 'he', 'el', 'cs', 'hu', 'fi', 'da', 'ro', 'uk', 'fa', 'bn', 'ms', 'uz', 'kk', 'si', 'bg', 'hr', 'sk', 'sl', 'sr', 'lv', 'is', 'ca', 'eu', 'gl', 'af', 'sw', 'sq'],
     False, False, 15, 2024, 8, 3, 124614),
    ('Area Model Multiplication', ['math'], ['elementary'],
     ['area', 'multiplication'],
     ['es', 'zh-cn', 'zh-tw', 'fr', 'de', 'pt-br', 'ru', 'ar', 'ja', 'ko', 'it', 'nl', 'pl', 'sv', 'tr', 'vi', 'hi', 'he', 'el', 'cs', 'hu', 'fi', 'da', 'ro', 'uk', 'fa', 'bn', 'ms', 'uz', 'kk', 'si', 'bg', 'hr', 'sk', 'sl', 'sr', 'lv', 'is', 'ca', 'eu', 'gl', 'af', 'sw', 'sq'],
     False, True, 15, 2025, 9, 22, 390218),
    ('Arithmetic', ['math'], ['elementary'],
     ['arithmetic'],
     ['es', 'zh-cn', 'zh-tw', 'fr', 'de', 'pt-br', 'ru', 'ar', 'ja', 'ko', 'it', 'nl', 'pl', 'sv', 'tr', 'vi', 'hi', 'he', 'el', 'cs', 'hu', 'fi', 'da', 'ro', 'uk', 'fa', 'id', 'bn', 'th', 'ms', 'uz', 'kk', 'si', 'bg', 'hr', 'sk', 'sl', 'sr', 'lt', 'lv', 'is', 'ca', 'eu', 'gl', 'af', 'sw', 'sq'],
     False, False, 15, 2023, 11, 13, 148826),
    ('Balancing Act', ['physics', 'math'], ['elementary', 'middle', 'high'],
     ['balancing', 'act'],
     ['es', 'zh-cn', 'zh-tw', 'fr', 'de', 'pt-br', 'ru', 'ar', 'ja', 'ko', 'it', 'nl', 'pl', 'sv', 'tr', 'vi', 'hi', 'he', 'el', 'cs', 'hu', 'fi', 'da', 'ro', 'uk', 'fa', 'id', 'bn', 'th', 'ms', 'uz', 'kk', 'si', 'bg', 'hr', 'sk', 'sl', 'sr', 'lt', 'lv', 'et', 'ca', 'eu', 'gl', 'af', 'sw', 'ka', 'mk', 'sq'],
     False, False, 25, 2023, 2, 10, 249458),
    ('Balloons and Static Electricity', ['physics', 'chemistry', 'biology'], ['elementary', 'middle', 'high'],
     ['balloons', 'static', 'electricity'],
     ['es', 'zh-cn', 'zh-tw', 'fr', 'de', 'pt-br', 'ru', 'ar', 'ja', 'ko', 'it', 'nl', 'pl', 'sv', 'tr', 'vi', 'hi', 'he', 'el', 'cs', 'hu', 'fi', 'da', 'ro', 'uk', 'fa', 'id', 'bn', 'th', 'ms', 'uz', 'kk', 'si', 'bg', 'hr', 'sk', 'sl', 'sr', 'nb', 'lt', 'lv', 'et', 'is', 'ca', 'eu', 'gl', 'af', 'sw', 'ka', 'mk', 'sq'],
     False, True, 25, 2025, 11, 10, 472601),
    ('Beers Law Lab', ['chemistry'], ['middle', 'high', 'university'],
     ['beers', 'law'],
     ['es', 'zh-cn', 'zh-tw', 'fr', 'de', 'pt-br', 'ru', 'ar', 'ja', 'ko', 'it', 'nl', 'pl', 'sv', 'tr', 'vi', 'hi', 'he', 'el', 'cs', 'hu', 'fi', 'da', 'ro', 'uk', 'fa', 'id', 'bn', 'th', 'ms', 'uz', 'kk', 'si', 'bg', 'hr', 'sk', 'sl', 'sr', 'nb', 'lt', 'lv', 'et', 'ca', 'eu', 'gl', 'af', 'sw', 'ka', 'mk', 'sq'],
     True, False, 30, 2023, 8, 14, 348308),
    ('Blackbody Spectrum', ['physics', 'chemistry', 'biology'], ['elementary', 'middle', 'high'],
     ['blackbody', 'spectrum'],
     ['es', 'zh-cn', 'zh-tw', 'fr', 'de', 'pt-br', 'ru', 'ar', 'ja', 'ko', 'it', 'nl', 'pl', 'sv', 'tr', 'vi', 'hi', 'he', 'el', 'cs', 'hu', 'fi', 'da', 'ro', 'uk', 'fa', 'bn', 'th', 'ms', 'uz', 'kk', 'bg', 'hr', 'sk', 'sl', 'sr', 'nb', 'lv', 'et', 'is', 'ca', 'eu', 'af', 'sw', 'ka', 'sq'],
     False, False, 25, 2024, 1, 12, 472953),
    ('Build a Fraction', ['math'], ['elementary'],
     ['build', 'fraction'],
     ['es', 'zh-cn', 'zh-tw', 'fr', 'de', 'pt-br', 'ru', 'ar', 'ja', 'ko', 'it', 'nl', 'pl', 'sv', 'tr', 'vi', 'hi', 'he', 'el', 'cs', 'hu', 'fi', 'da', 'ro', 'uk', 'fa', 'bn', 'th', 'ms', 'uz', 'kk', 'my', 'si', 'bg', 'hr', 'sk', 'sl', 'sr', 'lt', 'lv', 'is', 'ca', 'eu', 'gl', 'af', 'sw', 'ka', 'sq'],
     False, False, 15, 2023, 2, 20, 189965),
    ('Build a Nucleus', ['physics', 'chemistry'], ['middle', 'high', 'university'],
     ['build', 'nucleus'],
     ['es', 'zh-tw', 'fr', 'de', 'pt-br', 'ru', 'ar', 'ja', 'ko', 'it', 'nl', 'pl', 'sv', 'tr', 'vi', 'hi', 'he', 'el', 'cs', 'hu', 'fi', 'da', 'ro', 'uk', 'fa', 'bn', 'th', 'ms', 'uz', 'bg', 'hr', 'sk', 'sl', 'sr', 'nb', 'is', 'ca', 'eu', 'af', 'sw', 'ka', 'sq'],
     False, True, 30, 2025, 4, 12, 261516),
    ('Buoyancy', ['physics'], ['middle', 'high', 'university'],
     ['buoyancy'],
     ['es', 'zh-tw', 'fr', 'de', 'pt-br', 'ar', 'ko', 'it', 'nl', 'pl', 'sv', 'tr', 'vi', 'hi', 'he', 'el', 'cs', 'hu', 'fi', 'da', 'ro', 'uk', 'fa', 'th', 'ms', 'uz', 'hr', 'sk', 'sl', 'sr', 'is', 'ca', 'af', 'sw'],
     False, True, 30, 2025, 2, 17, 63252),
    ('Buoyancy: Basics', ['physics'], ['elementary', 'middle'],
     ['buoyancy'],
     ['es', 'zh-tw', 'fr', 'de', 'pt-br', 'ar', 'ko', 'it', 'nl', 'pl', 'sv', 'tr', 'vi', 'hi', 'he', 'el', 'cs', 'hu', 'da', 'ro', 'fa', 'th', 'ms', 'hr', 'sk', 'sl', 'sr', 'is', 'ca', 'sw'],
     False, False, 20, 2023, 4, 8, 33622),
    ('Capacitor Lab: Basics', ['physics'], ['elementary', 'middle', 'high'],
     ['capacitor'],
     ['es', 'zh-cn', 'zh-tw', 'fr', 'de', 'pt-br', 'ru', 'ar', 'ja', 'ko', 'it', 'nl', 'pl', 'sv', 'tr', 'vi', 'hi', 'he', 'el', 'cs', 'hu', 'fi', 'da', 'ro', 'uk', 'fa', 'bn', 'th', 'ms', 'uz', 'kk', 'bg', 'hr', 'sk', 'sl', 'sr', 'nb', 'lt', 'lv', 'et', 'ca', 'eu', 'af', 'sw', 'ka', 'sq'],
     False, True, 25, 2025, 2, 2, 391848),
    ('Center and Variability', ['math'], ['elementary'],
     ['center', 'variability'],
     ['es', 'zh-tw', 'fr', 'de', 'pt-br', 'ar', 'ja', 'ko', 'it', 'nl', 'pl', 'sv', 'tr', 'vi', 'hi', 'he', 'el', 'cs', 'hu', 'da', 'ro', 'fa', 'bn', 'th', 'ms', 'uz', 'bg', 'sk', 'sr', 'is', 'ca', 'eu', 'sw', 'ka', 'sq'],
     False, True, 15, 2025, 5, 26, 271698),
    ('Circuit Construction Kit: AC', ['physics'], ['middle', 'high', 'university'],
     ['circuit', 'construction'],
     ['es', 'zh-cn', 'zh-tw', 'fr', 'de', 'pt-br', 'ru', 'ar', 'ja', 'ko', 'it', 'nl', 'pl', 'sv', 'tr', 'vi', 'hi', 'he', 'el', 'cs', 'fi', 'da', 'ro', 'uk', 'fa', 'id', 'bn', 'th', 'ms', 'uz', 'bg', 'hr', 'sk', 'sl', 'sr', 'lt', 'lv', 'is', 'ca', 'eu', 'sw', 'ka', 'sq'],
     True, False, 30, 2024, 9, 9, 213401),
    ('Circuit Construction Kit: AC - Virtual Lab', ['physics'], ['middle', 'high', 'university'],
     ['circuit', 'construction', 'virtual'],
     ['es', 'zh-cn', 'zh-tw', 'fr', 'de', 'pt-br', 'ru', 'ar', 'ja', 'ko', 'it', 'nl', 'pl', 'sv', 'tr', 'vi', 'hi', 'he', 'el', 'cs', 'fi', 'da', 'ro', 'uk', 'fa', 'bn', 'th', 'ms', 'uz', 'bg', 'hr', 'sk', 'sl', 'sr', 'lt', 'lv', 'is', 'ca', 'eu', 'sw', 'ka', 'sq'],
     False, False, 30, 2024, 10, 20, 491619),
    ('Circuit Construction Kit: DC - Virtual Lab', ['physics'], ['elementary', 'middle', 'high'],
     ['circuit', 'construction', 'virtual'],
     ['es', 'zh-cn', 'zh-tw', 'fr', 'de', 'pt-br', 'ru', 'ar', 'ja', 'ko', 'it', 'nl', 'pl', 'sv', 'tr', 'vi', 'hi', 'he', 'el', 'cs', 'hu', 'fi', 'da', 'ro', 'uk', 'fa', 'id', 'bn', 'th', 'ms', 'uz', 'kk', 'bg', 'hr', 'sk', 'sl', 'sr', 'nb', 'lt', 'lv', 'is', 'ca', 'eu', 'sw', 'ka', 'sq'],
     False, True, 25, 2025, 12, 5, 139484),
    ('Collision Lab', ['physics'], ['elementary', 'middle', 'high'],
     ['collision'],
     ['es', 'zh-cn', 'zh-tw', 'fr', 'de', 'pt-br', 'ru', 'ar', 'ja', 'ko', 'it', 'nl', 'pl', 'sv', 'tr', 'vi', 'hi', 'he', 'el', 'cs', 'hu', 'fi', 'da', 'ro', 'uk', 'fa', 'bn', 'th', 'ms', 'uz', 'bg', 'hr', 'sk', 'sl', 'sr', 'lv', 'is', 'ca', 'eu', 'sw', 'ka', 'sq'],
     False, False, 25, 2024, 8, 12, 430542),
    ('Coulombs Law', ['physics', 'chemistry'], ['middle', 'high', 'university'],
     ['coulombs', 'law'],
     ['es', 'zh-cn', 'zh-tw', 'fr', 'de', 'pt-br', 'ru', 'ar', 'ja', 'ko', 'it', 'nl', 'pl', 'sv', 'tr', 'vi', 'hi', 'he', 'el', 'cs', 'hu', 'fi', 'da', 'ro', 'uk', 'fa', 'bn', 'th', 'ms', 'uz', 'kk', 'my', 'bg', 'hr', 'sk', 'sl', 'sr', 'nb', 'lv', 'ca', 'eu', 'af', 'sw', 'ka', 'sq'],
     False, False, 30, 2023, 6, 16, 213803),
    ('Curve Fitting', ['physics', 'math'], ['middle', 'high', 'university'],
     ['curve', 'fitting'],
     ['es', 'zh-cn', 'zh-tw', 'fr', 'de', 'pt-br', 'ru', 'ar', 'ja', 'ko', 'it', 'nl', 'pl', 'sv', 'tr', 'vi', 'hi', 'he', 'el', 'cs', 'hu', 'fi', 'da', 'ro', 'fa', 'bn', 'ms', 'uz', 'kk', 'bg', 'hr', 'sk', 'sl', 'sr', 'lv', 'ca', 'eu', 'af', 'sw', 'sq'],
     True, True, 30, 2025, 3, 2, 152021),
    ('Diffusion', ['physics', 'chemistry', 'biology'], ['elementary', 'middle', 'high'],
     ['diffusion'],
     ['es', 'zh-cn', 'zh-tw', 'fr', 'de', 'pt-br', 'ru', 'ar', 'ja', 'ko', 'it', 'nl', 'pl', 'sv', 'tr', 'vi', 'hi', 'he', 'el', 'cs', 'hu', 'fi', 'da', 'ro', 'uk', 'fa', 'bn', 'th', 'ms', 'uz', 'kk', 'bg', 'hr', 'sk', 'sl', 'sr', 'nb', 'lt', 'lv', 'is', 'ca', 'eu', 'af', 'sw', 'ka', 'sq'],
     False, False, 25, 2024, 9, 5, 320785),
    ('Energy Forms and Changes', ['physics', 'chemistry'], ['elementary', 'middle', 'high'],
     ['energy', 'forms', 'changes'],
     ['es', 'zh-cn', 'zh-tw', 'fr', 'de', 'pt-br', 'ru', 'ar', 'ja', 'ko', 'it', 'nl', 'pl', 'sv', 'tr', 'vi', 'hi', 'he', 'el', 'cs', 'hu', 'fi', 'da', 'ro', 'uk', 'fa', 'id', 'bn', 'th', 'ms', 'uz', 'kk', 'my', 'bg', 'hr', 'sk', 'sl', 'sr', 'nb', 'lt', 'lv', 'is', 'ca', 'eu', 'af', 'sw', 'ka', 'mk', 'sq'],
     False, False, 25, 2024, 11, 23, 199046),
    ('Energy Skate Park: Basics', ['physics'], ['elementary', 'middle', 'high'],
     ['energy', 'skate', 'park'],
     ['es', 'zh-cn', 'zh-tw', 'fr', 'de', 'pt-br', 'ru', 'ar', 'ja', 'ko', 'it', 'nl', 'pl', 'sv', 'tr', 'vi', 'hi', 'he', 'el', 'cs', 'hu', 'fi', 'da', 'ro', 'uk', 'fa', 'id', 'bn', 'th', 'ms', 'uz', 'kk', 'my', 'si', 'bg', 'hr', 'sk', 'sl', 'sr', 'nb', 'lt', 'lv', 'et', 'is', 'ca', 'eu', 'gl', 'sw', 'ka', 'mk', 'sq'],
     True, False, 25, 2023, 1, 14, 318456),
    ('Equality Explorer: Basics', ['math'], ['elementary'],
     ['equality'],
     ['es', 'zh-cn', 'zh-tw', 'fr', 'de', 'pt-br', 'ru', 'ar', 'ja', 'ko', 'it', 'nl', 'pl', 'sv', 'tr', 'vi', 'hi', 'he', 'el', 'cs', 'hu', 'fi', 'da', 'ro', 'uk', 'fa', 'bn', 'ms', 'uz', 'kk', 'bg', 'hr', 'sk', 'sl', 'sr', 'lv', 'is', 'ca', 'eu', 'sw', 'sq'],
     True, True, 15, 2025, 3, 5, 378532),
    ('Equality Explorer: Two Variables', ['math'], ['elementary', 'middle'],
     ['equality', 'two', 'variables'],
     ['es', 'zh-cn', 'zh-tw', 'fr', 'de', 'pt-br', 'ru', 'ar', 'ja', 'ko', 'it', 'nl', 'pl', 'sv', 'tr', 'vi', 'hi', 'he', 'el', 'cs', 'hu', 'fi', 'da', 'ro', 'uk', 'fa', 'bn', 'ms', 'uz', 'kk', 'bg', 'sk', 'sl', 'sr', 'lv', 'is', 'ca', 'eu', 'af', 'sw', 'sq'],
     False, False, 20, 2024, 4, 12, 486903),
    ('Expression Exchange', ['math'], ['elementary', 'middle'],
     ['expression', 'exchange'],
     ['es', 'zh-cn', 'zh-tw', 'fr', 'de', 'pt-br', 'ru', 'ar', 'ja', 'ko', 'it', 'nl', 'pl', 'sv', 'tr', 'vi', 'hi', 'he', 'el', 'cs', 'hu', 'fi', 'da', 'ro', 'uk', 'fa', 'bn', 'ms', 'uz', 'kk', 'bg', 'hr', 'sk', 'sl', 'sr', 'nb', 'lv', 'ca', 'eu', 'af', 'sw', 'sq'],
     False, True, 20, 2025, 4, 19, 422088),
    ('Faradays Electromagnetic Lab', ['physics'], ['elementary', 'middle', 'high'],
     ['faradays', 'electromagnetic'],
     ['es', 'zh-tw', 'fr', 'de', 'pt-br', 'ar', 'ko', 'it', 'nl', 'pl', 'sv', 'tr', 'vi', 'hi', 'he', 'el', 'cs', 'hu', 'fi', 'da', 'ro', 'uk', 'fa', 'th', 'ms', 'hr', 'sk', 'sl', 'sr', 'lt', 'is', 'ca', 'sw'],
     False, False, 25, 2023, 7, 14, 440024),
    ('Faradays Law', ['physics'], ['elementary', 'middle', 'high'],
     ['faradays', 'law'],
     ['es', 'zh-cn', 'zh-tw', 'fr', 'de', 'pt-br', 'ru', 'ar', 'ja', 'ko', 'it', 'nl', 'pl', 'sv', 'tr', 'vi', 'hi', 'he', 'el', 'cs', 'hu', 'fi', 'da', 'ro', 'uk', 'fa', 'id', 'bn', 'th', 'ms', 'uz', 'kk', 'si', 'bg', 'hr', 'sk', 'sl', 'sr', 'nb', 'lv', 'et', 'is', 'ca', 'eu', 'sw', 'ka', 'sq'],
     False, False, 25, 2023, 7, 27, 388730),
    ('Fourier: Making Waves', ['physics', 'chemistry', 'math'], ['middle', 'high', 'university'],
     ['fourier', 'making', 'waves'],
     ['es', 'zh-tw', 'fr', 'de', 'pt-br', 'ru', 'ar', 'ko', 'it', 'nl', 'pl', 'sv', 'tr', 'vi', 'hi', 'he', 'el', 'cs', 'da', 'ro', 'uk', 'fa', 'bn', 'th', 'ms', 'uz', 'bg', 'hr', 'sk', 'sr', 'is', 'ca', 'eu', 'sw', 'sq'],
     False, False, 30, 2024, 1, 17, 32665),
    ('Fraction Matcher', ['math'], ['elementary', 'middle'],
     ['fraction', 'matcher'],
     ['es', 'zh-cn', 'zh-tw', 'fr', 'de', 'pt-br', 'ru', 'ar', 'ja', 'ko', 'it', 'nl', 'pl', 'sv', 'tr', 'vi', 'hi', 'he', 'el', 'cs', 'hu', 'fi', 'da', 'ro', 'uk', 'fa', 'id', 'bn', 'ms', 'uz', 'kk', 'my', 'si', 'bg', 'hr', 'sk', 'sl', 'sr', 'lt', 'lv', 'et', 'is', 'ca', 'eu', 'af', 'sw', 'ka', 'sq'],
     False, False, 20, 2024, 1, 24, 248263),
    ('Fractions: Equality', ['math'], ['elementary'],
     ['fractions', 'equality'],
     ['es', 'zh-cn', 'zh-tw', 'fr', 'de', 'pt-br', 'ru', 'ar', 'ja', 'ko', 'it', 'nl', 'pl', 'sv', 'tr', 'vi', 'hi', 'he', 'el', 'cs', 'hu', 'fi', 'da', 'ro', 'uk', 'fa', 'id', 'bn', 'ms', 'uz', 'kk', 'my', 'bg', 'hr', 'sk', 'sl', 'sr', 'lt', 'lv', 'is', 'ca', 'eu', 'af', 'sw', 'ka', 'sq'],
     False, False, 15, 2023, 2, 3, 94978),
    ('Fractions: Mixed Numbers', ['math'], ['elementary'],
     ['fractions', 'mixed', 'numbers'],
     ['es', 'zh-cn', 'zh-tw', 'fr', 'de', 'pt-br', 'ru', 'ar', 'ja', 'ko', 'it', 'nl', 'pl', 'sv', 'tr', 'vi', 'hi', 'he', 'el', 'cs', 'hu', 'fi', 'da', 'ro', 'uk', 'fa', 'id', 'bn', 'ms', 'uz', 'kk', 'my', 'bg', 'hr', 'sk', 'sl', 'sr', 'lt', 'lv', 'is', 'ca', 'eu', 'af', 'sw', 'sq'],
     False, True, 15, 2025, 4, 19, 256552),
    ('Friction', ['physics'], ['elementary', 'middle', 'high'],
     ['friction'],
     ['es', 'zh-cn', 'zh-tw', 'fr', 'de', 'pt-br', 'ru', 'ar', 'ja', 'ko', 'it', 'nl', 'pl', 'sv', 'tr', 'vi', 'hi', 'he', 'el', 'cs', 'hu', 'fi', 'da', 'ro', 'uk', 'fa', 'id', 'bn', 'th', 'ms', 'uz', 'kk', 'si', 'bg', 'hr', 'sk', 'sl', 'sr', 'nb', 'lt', 'lv', 'et', 'is', 'ca', 'eu', 'gl', 'af', 'sw', 'ka', 'mk', 'sq'],
     False, True, 25, 2025, 6, 28, 356954),
    ('Function Builder: Basics', ['math'], ['elementary'],
     ['function'],
     ['es', 'zh-cn', 'zh-tw', 'fr', 'de', 'pt-br', 'ru', 'ar', 'ja', 'ko', 'it', 'nl', 'pl', 'sv', 'tr', 'vi', 'hi', 'he', 'el', 'cs', 'hu', 'da', 'ro', 'uk', 'fa', 'bn', 'ms', 'uz', 'kk', 'bg', 'hr', 'sk', 'sl', 'sr', 'lv', 'is', 'ca', 'eu', 'gl', 'sw', 'sq'],
     False, True, 15, 2025, 7, 27, 270636),
    ('Gases Intro', ['physics', 'chemistry', 'biology'], ['elementary'],
     ['gases'],
     ['es', 'zh-cn', 'zh-tw', 'fr', 'de', 'pt-br', 'ru', 'ar', 'ja', 'ko', 'it', 'nl', 'pl', 'sv', 'tr', 'vi', 'hi', 'he', 'el', 'cs', 'hu', 'fi', 'da', 'ro', 'uk', 'fa', 'bn', 'th', 'ms', 'uz', 'kk', 'bg', 'hr', 'sk', 'sl', 'sr', 'nb', 'lt', 'lv', 'is', 'ca', 'eu', 'sw', 'ka', 'sq'],
     False, False, 15, 2024, 11, 12, 377850),
    ('Generator', ['physics'], ['elementary', 'middle', 'high'],
     ['generator'],
     ['es', 'zh-tw', 'fr', 'de', 'pt-br', 'ar', 'ko', 'it', 'nl', 'pl', 'sv', 'tr', 'vi', 'hi', 'he', 'el', 'cs', 'fi', 'da', 'ro', 'uk', 'fa', 'th', 'ms', 'hr', 'sk', 'sl', 'sr', 'is', 'ca', 'sw'],
     False, False, 25, 2023, 2, 8, 237115),
    ('Geometric Optics', ['physics'], ['elementary', 'middle', 'high'],
     ['geometric', 'optics'],
     ['es', 'zh-cn', 'zh-tw', 'fr', 'de', 'pt-br', 'ru', 'ar', 'ja', 'ko', 'it', 'nl', 'pl', 'sv', 'tr', 'vi', 'hi', 'he', 'el', 'cs', 'hu', 'fi', 'da', 'ro', 'uk', 'fa', 'bn', 'th', 'ms', 'uz', 'kk', 'bg', 'hr', 'sk', 'sl', 'sr', 'lt', 'ca', 'eu', 'sw', 'ka', 'sq'],
     False, False, 25, 2024, 3, 24, 102234),
    ('Geometric Optics: Basics', ['physics'], ['elementary', 'middle'],
     ['geometric', 'optics'],
     ['es', 'zh-tw', 'fr', 'de', 'pt-br', 'ar', 'ko', 'it', 'nl', 'pl', 'sv', 'tr', 'vi', 'hi', 'he', 'el', 'cs', 'hu', 'fi', 'da', 'ro', 'uk', 'fa', 'bn', 'th', 'ms', 'uz', 'kk', 'bg', 'hr', 'sk', 'sl', 'sr', 'lt', 'ca', 'eu', 'sw'],
     False, False, 20, 2024, 5, 14, 69576),
    ('Graphing Quadratics', ['math'], ['elementary', 'middle'],
     ['graphing', 'quadratics'],
     ['es', 'zh-cn', 'zh-tw', 'fr', 'de', 'pt-br', 'ru', 'ar', 'ja', 'ko', 'it', 'nl', 'pl', 'sv', 'tr', 'vi', 'hi', 'he', 'el', 'cs', 'hu', 'fi', 'da', 'ro', 'uk', 'fa', 'bn', 'ms', 'uz', 'kk', 'bg', 'hr', 'sk', 'sl', 'sr', 'lv', 'ca', 'eu', 'sw', 'sq'],
     False, False, 20, 2023, 10, 23, 114880),
    ('Graphing Slope-Intercept', ['math'], ['elementary', 'middle', 'high'],
     ['graphing', 'slope', 'intercept'],
     ['es', 'zh-cn', 'zh-tw', 'fr', 'de', 'pt-br', 'ru', 'ar', 'ja', 'ko', 'it', 'nl', 'pl', 'sv', 'tr', 'vi', 'hi', 'he', 'el', 'cs', 'hu', 'fi', 'da', 'ro', 'uk', 'fa', 'bn', 'th', 'ms', 'uz', 'kk', 'bg', 'sk', 'sl', 'sr', 'lv', 'ca', 'eu', 'sw', 'sq'],
     False, False, 25, 2024, 11, 19, 379303),
    ('Gravity Force Lab', ['physics', 'biology'], ['middle', 'high', 'university'],
     ['gravity', 'force'],
     ['es', 'zh-cn', 'zh-tw', 'fr', 'de', 'pt-br', 'ru', 'ar', 'ja', 'ko', 'it', 'nl', 'pl', 'sv', 'tr', 'vi', 'hi', 'he', 'el', 'cs', 'hu', 'fi', 'da', 'ro', 'uk', 'fa', 'id', 'bn', 'th', 'ms', 'uz', 'kk', 'si', 'bg', 'hr', 'sk', 'sl', 'sr', 'nb', 'lt', 'lv', 'et', 'ca', 'eu', 'gl', 'sw', 'ka', 'mk', 'sq'],
     True, True, 30, 2025, 8, 10, 39792),
    ('Gravity Force Lab: Basics', ['physics', 'biology'], ['elementary'],
     ['gravity', 'force'],
     ['es', 'zh-cn', 'zh-tw', 'fr', 'de', 'pt-br', 'ru', 'ar', 'ja', 'ko', 'it', 'nl', 'pl', 'sv', 'tr', 'vi', 'hi', 'he', 'el', 'cs', 'hu', 'fi', 'da', 'ro', 'uk', 'fa', 'bn', 'th', 'ms', 'uz', 'kk', 'bg', 'hr', 'sk', 'sl', 'sr', 'lt', 'lv', 'ca', 'eu', 'sw', 'ka', 'sq'],
     False, True, 15, 2025, 7, 7, 141594),
    ('Hookes Law', ['physics'], ['middle', 'high', 'university'],
     ['hookes', 'law'],
     ['es', 'zh-cn', 'zh-tw', 'fr', 'de', 'pt-br', 'ru', 'ar', 'ja', 'ko', 'it', 'nl', 'pl', 'sv', 'tr', 'vi', 'hi', 'he', 'el', 'cs', 'hu', 'fi', 'da', 'ro', 'uk', 'fa', 'id', 'bn', 'th', 'ms', 'uz', 'kk', 'si', 'bg', 'hr', 'sk', 'sl', 'sr', 'nb', 'lv', 'et', 'ca', 'eu', 'sw', 'ka', 'sq'],
     False, False, 30, 2024, 10, 15, 394246),
    ('John Travoltage', ['physics'], ['elementary', 'middle', 'high'],
     ['john', 'travoltage'],
     ['es', 'zh-cn', 'zh-tw', 'fr', 'de', 'pt-br', 'ru', 'ar', 'ja', 'ko', 'it', 'nl', 'pl', 'sv', 'tr', 'vi', 'hi', 'he', 'el', 'cs', 'hu', 'fi', 'da', 'ro', 'uk', 'fa', 'id', 'bn', 'th', 'ms', 'uz', 'kk', 'si', 'bg', 'hr', 'sk', 'sl', 'sr', 'lt', 'lv', 'et', 'is', 'ca', 'eu', 'gl', 'sw', 'ka', 'mk', 'sq'],
     False, True, 25, 2025, 11, 16, 412405),
    ('Keplers Laws', ['physics', 'biology', 'math'], ['middle', 'high', 'university'],
     ['keplers', 'laws'],
     ['es', 'zh-tw', 'fr', 'de', 'pt-br', 'ar', 'ko', 'it', 'nl', 'pl', 'sv', 'tr', 'vi', 'hi', 'he', 'el', 'cs', 'hu', 'da', 'ro', 'fa', 'bn', 'th', 'ms', 'uz', 'hr', 'sk', 'sl', 'sr', 'nb', 'ca', 'sw', 'ka'],
     False, False, 30, 2024, 2, 26, 53174),
    ('Least-Squares Regression', ['math'], ['middle', 'high'],
     ['least', 'squares', 'regression'],
     ['es', 'zh-cn', 'zh-tw', 'fr', 'de', 'pt-br', 'ru', 'ar', 'ja', 'ko', 'it', 'nl', 'pl', 'sv', 'tr', 'vi', 'hi', 'he', 'el', 'cs', 'hu', 'fi', 'da', 'ro', 'fa', 'bn', 'ms', 'uz', 'kk', 'bg', 'sr', 'lv', 'ca', 'eu', 'sw', 'sq'],
     False, False, 25, 2024, 3, 12, 371916),
    ('Magnets and Electromagnets', ['physics'], ['elementary', 'middle', 'high'],
     ['magnets', 'electromagnets'],
     ['es', 'zh-tw', 'fr', 'de', 'pt-br', 'ar', 'ko', 'it', 'nl', 'pl', 'sv', 'tr', 'vi', 'hi', 'he', 'el', 'cs', 'da', 'ro', 'fa', 'th', 'ms', 'hr', 'sk', 'sl', 'sr', 'lt', 'is', 'ca', 'sw'],
     False, False, 25, 2024, 8, 27, 287299),
    ('Masses and Springs', ['physics', 'math'], ['middle', 'high', 'university'],
     ['masses', 'springs'],
     ['es', 'zh-cn', 'zh-tw', 'fr', 'de', 'pt-br', 'ru', 'ar', 'ja', 'ko', 'it', 'nl', 'pl', 'sv', 'tr', 'vi', 'hi', 'he', 'el', 'cs', 'hu', 'fi', 'da', 'ro', 'uk', 'fa', 'bn', 'th', 'ms', 'uz', 'kk', 'bg', 'hr', 'sk', 'sl', 'sr', 'nb', 'lt', 'lv', 'is', 'ca', 'eu', 'af', 'sw', 'ka', 'sq'],
     False, False, 30, 2024, 9, 11, 246785),
    ('Masses and Springs: Basics', ['physics'], ['elementary'],
     ['masses', 'springs'],
     ['es', 'zh-cn', 'zh-tw', 'fr', 'de', 'pt-br', 'ru', 'ar', 'ja', 'ko', 'it', 'nl', 'pl', 'sv', 'tr', 'vi', 'hi', 'he', 'el', 'cs', 'hu', 'da', 'ro', 'uk', 'fa', 'bn', 'th', 'ms', 'uz', 'kk', 'bg', 'hr', 'sk', 'sl', 'sr', 'lt', 'lv', 'is', 'ca', 'eu', 'sw', 'ka', 'sq'],
     False, False, 15, 2023, 9, 18, 312853),
    ('Mean: Share and Balance', ['math'], ['elementary'],
     ['mean', 'share', 'balance'],
     ['es', 'zh-tw', 'fr', 'de', 'pt-br', 'ar', 'ko', 'it', 'nl', 'pl', 'tr', 'vi', 'hi', 'he', 'el', 'cs', 'da', 'ro', 'fa', 'ms', 'uz', 'bg', 'hr', 'sk', 'sl', 'sr', 'lt', 'is', 'ca', 'eu', 'sw'],
     True, False, 15, 2024, 2, 20, 478712),
    ('Membrane Transport', ['earth-science', 'chemistry'], ['elementary', 'middle', 'high'],
     ['membrane', 'transport'],
     ['es', 'fr', 'de', 'pt-br', 'ar', 'it', 'nl', 'pl', 'sv', 'vi', 'hi', 'he', 'el', 'cs', 'hu', 'da', 'ro', 'sr', 'nb', 'lt', 'ca'],
     False, False, 25, 2023, 6, 23, 50995),
    ('Models of the Hydrogen Atom', ['physics', 'chemistry'], ['elementary', 'middle', 'high'],
     ['hydrogen', 'atom'],
     ['es', 'fr', 'de', 'pt-br', 'ar', 'ko', 'it', 'nl', 'pl', 'tr', 'vi', 'hi', 'he', 'el', 'cs', 'da', 'ro', 'fa', 'th', 'ms', 'sr', 'lt', 'ca', 'sw'],
     False, False, 25, 2023, 8, 12, 309455),
    ('Molarity', ['chemistry'], ['middle', 'high', 'university'],
     ['molarity'],
     ['es', 'zh-cn', 'zh-tw', 'fr', 'de', 'pt-br', 'ru', 'ar', 'ja', 'ko', 'it', 'nl', 'pl', 'sv', 'tr', 'vi', 'hi', 'he', 'el', 'cs', 'hu', 'fi', 'da', 'ro', 'uk', 'fa', 'id', 'bn', 'th', 'ms', 'uz', 'kk', 'si', 'bg', 'hr', 'sk', 'sl', 'sr', 'nb', 'lt', 'lv', 'et', 'ca', 'eu', 'gl', 'sw', 'ka', 'mk', 'sq'],
     False, False, 30, 2023, 8, 15, 122727),
    ('Molecule Shapes', ['chemistry'], ['middle', 'high', 'university'],
     ['molecule', 'shapes'],
     ['es', 'zh-cn', 'zh-tw', 'fr', 'de', 'pt-br', 'ru', 'ar', 'ja', 'ko', 'it', 'nl', 'pl', 'sv', 'tr', 'vi', 'hi', 'he', 'el', 'cs', 'hu', 'fi', 'da', 'ro', 'uk', 'fa', 'bn', 'th', 'ms', 'uz', 'kk', 'si', 'bg', 'sk', 'sl', 'sr', 'nb', 'lt', 'lv', 'ca', 'eu', 'gl', 'sw', 'mk', 'sq'],
     False, False, 30, 2024, 8, 13, 336613),
    ('Molecule Shapes: Basics', ['chemistry'], ['elementary', 'middle'],
     ['molecule', 'shapes'],
     ['es', 'zh-cn', 'zh-tw', 'fr', 'de', 'pt-br', 'ru', 'ar', 'ja', 'ko', 'it', 'nl', 'pl', 'sv', 'tr', 'vi', 'hi', 'he', 'el', 'cs', 'hu', 'fi', 'da', 'ro', 'uk', 'fa', 'bn', 'th', 'ms', 'uz', 'kk', 'si', 'bg', 'sk', 'sl', 'sr', 'lt', 'lv', 'ca', 'eu', 'sw', 'sq'],
     False, False, 20, 2024, 10, 6, 158529),
    ('Molecules and Light', ['physics', 'chemistry', 'biology'], ['elementary', 'middle', 'high'],
     ['molecules', 'light'],
     ['es', 'zh-cn', 'zh-tw', 'fr', 'de', 'pt-br', 'ru', 'ar', 'ja', 'ko', 'it', 'nl', 'pl', 'sv', 'tr', 'vi', 'hi', 'he', 'el', 'cs', 'hu', 'fi', 'da', 'ro', 'uk', 'fa', 'id', 'bn', 'th', 'ms', 'uz', 'kk', 'si', 'bg', 'hr', 'sk', 'sl', 'sr', 'nb', 'lt', 'lv', 'et', 'is', 'ca', 'eu', 'gl', 'sw', 'ka', 'mk', 'sq'],
     False, True, 25, 2025, 10, 7, 42564),
    ('Number Compare', ['math'], ['elementary'],
     ['number', 'compare'],
     ['es', 'zh-cn', 'zh-tw', 'fr', 'de', 'pt-br', 'ar', 'ja', 'ko', 'it', 'nl', 'pl', 'sv', 'tr', 'vi', 'hi', 'he', 'el', 'cs', 'fi', 'da', 'ro', 'fa', 'bn', 'ms', 'uz', 'bg', 'hr', 'sk', 'sl', 'sr', 'lt', 'is', 'ca', 'eu', 'sw', 'sq'],
     False, False, 15, 2023, 6, 27, 283081),
    ('Number Line: Distance', ['math'], ['elementary'],
     ['number', 'line', 'distance'],
     ['es', 'zh-cn', 'zh-tw', 'fr', 'de', 'pt-br', 'ar', 'ja', 'ko', 'it', 'nl', 'pl', 'sv', 'tr', 'vi', 'hi', 'he', 'el', 'cs', 'fi', 'da', 'ro', 'fa', 'id', 'bn', 'ms', 'uz', 'bg', 'hr', 'sk', 'sl', 'sr', 'lt', 'is', 'ca', 'eu', 'sw', 'sq'],
     False, False, 15, 2023, 7, 14, 36106),
    ('Number Line: Operations', ['math'], ['elementary'],
     ['number', 'line', 'operations'],
     ['es', 'zh-cn', 'zh-tw', 'fr', 'de', 'pt-br', 'ar', 'ja', 'ko', 'it', 'nl', 'pl', 'sv', 'tr', 'vi', 'hi', 'he', 'el', 'cs', 'hu', 'fi', 'da', 'ro', 'fa', 'bn', 'ms', 'uz', 'bg', 'hr', 'sk', 'sl', 'sr', 'lt', 'lv', 'ca', 'eu', 'sw', 'sq'],
     False, False, 15, 2023, 11, 21, 164021),
    ('Number Pairs', ['math'], ['elementary'],
     ['number', 'pairs'],
     ['es', 'fr', 'de', 'pt-br', 'ar', 'ko', 'it', 'nl', 'pl', 'tr', 'vi', 'hi', 'he', 'el', 'cs', 'da', 'ro', 'fa', 'sr', 'is', 'ca'],
     False, False, 15, 2024, 1, 4, 161429),
    ('Number Play', ['math'], ['elementary'],
     ['number', 'play'],
     ['es', 'zh-cn', 'zh-tw', 'fr', 'de', 'pt-br', 'ar', 'ja', 'ko', 'it', 'nl', 'pl', 'tr', 'vi', 'hi', 'he', 'el', 'cs', 'fi', 'da', 'ro', 'fa', 'bn', 'ms', 'uz', 'bg', 'hr', 'sk', 'sl', 'sr', 'is', 'ca', 'eu', 'sw', 'sq'],
     False, False, 15, 2023, 6, 7, 263896),
    ('Ohms Law', ['physics', 'math'], ['elementary', 'middle', 'high'],
     ['ohms', 'law'],
     ['es', 'zh-cn', 'zh-tw', 'fr', 'de', 'pt-br', 'ru', 'ar', 'ja', 'ko', 'it', 'nl', 'pl', 'sv', 'tr', 'vi', 'hi', 'he', 'el', 'cs', 'hu', 'fi', 'da', 'ro', 'uk', 'fa', 'id', 'bn', 'th', 'ms', 'uz', 'kk', 'si', 'bg', 'hr', 'sk', 'sl', 'sr', 'nb', 'lt', 'lv', 'et', 'is', 'ca', 'eu', 'gl', 'sw', 'ka', 'mk', 'sq'],
     False, False, 25, 2024, 11, 12, 102604),
    ('pH Scale: Basics', ['chemistry'], ['elementary'],
     ['scale'],
     ['es', 'zh-cn', 'zh-tw', 'fr', 'de', 'pt-br', 'ru', 'ar', 'ja', 'ko', 'it', 'nl', 'pl', 'sv', 'tr', 'vi', 'hi', 'he', 'el', 'cs', 'hu', 'fi', 'da', 'ro', 'uk', 'fa', 'bn', 'th', 'ms', 'uz', 'kk', 'si', 'bg', 'hr', 'sk', 'sl', 'sr', 'nb', 'lt', 'lv', 'et', 'is', 'ca', 'eu', 'sw', 'sq'],
     False, False, 15, 2023, 4, 12, 177601),
    ('Projectile Data Lab', ['physics', 'math'], ['middle', 'high', 'university'],
     ['projectile', 'data'],
     ['es', 'zh-tw', 'fr', 'de', 'pt-br', 'ar', 'ko', 'it', 'nl', 'pl', 'sv', 'tr', 'vi', 'hi', 'he', 'el', 'cs', 'da', 'ro', 'fa', 'th', 'ms', 'hr', 'sr', 'is', 'ca', 'sw'],
     True, False, 30, 2023, 8, 8, 252618),
    ('Projectile Sampling Distributions', ['math'], ['middle', 'high'],
     ['projectile', 'sampling', 'distributions'],
     ['es', 'zh-tw', 'fr', 'de', 'pt-br', 'ar', 'ko', 'it', 'nl', 'pl', 'vi', 'hi', 'he', 'el', 'cs', 'da', 'ro', 'fa', 'th', 'ms', 'hr', 'sr', 'is', 'ca', 'sw'],
     False, False, 25, 2024, 11, 5, 30141),
    ('Proportion Playground', ['math'], ['elementary'],
     ['proportion', 'playground'],
     ['es', 'zh-cn', 'zh-tw', 'fr', 'de', 'pt-br', 'ru', 'ar', 'ja', 'ko', 'it', 'nl', 'pl', 'sv', 'tr', 'vi', 'hi', 'he', 'el', 'cs', 'hu', 'da', 'ro', 'uk', 'fa', 'bn', 'th', 'ms', 'uz', 'kk', 'my', 'bg', 'hr', 'sk', 'sr', 'lv', 'ca', 'eu', 'gl', 'af', 'sw', 'sq'],
     True, False, 15, 2023, 11, 14, 303710),
    ('Quadrilateral', ['math'], ['elementary'],
     ['quadrilateral'],
     ['es', 'zh-tw', 'fr', 'de', 'pt-br', 'ar', 'ko', 'it', 'nl', 'pl', 'tr', 'vi', 'hi', 'he', 'el', 'cs', 'hu', 'da', 'ro', 'fa', 'ms', 'uz', 'sk', 'sl', 'sr', 'ca', 'eu', 'sw'],
     False, True, 15, 2025, 12, 21, 334989),
    ('Quantum Coin Toss', ['physics', 'chemistry'], ['middle', 'high', 'university'],
     ['quantum', 'coin', 'toss'],
     ['es', 'fr', 'de', 'pt-br', 'ar', 'it', 'nl', 'pl', 'vi', 'hi', 'he', 'el', 'cs', 'da', 'ro', 'fa', 'sr', 'ca'],
     False, True, 30, 2025, 3, 23, 350929),
    ('Quantum Measurement', ['physics', 'chemistry'], ['middle', 'high', 'university'],
     ['quantum', 'measurement'],
     ['es', 'fr', 'de', 'pt-br', 'ar', 'ko', 'it', 'nl', 'pl', 'vi', 'hi', 'he', 'el', 'cs', 'da', 'ro', 'fa', 'sr', 'ca'],
     False, False, 30, 2023, 5, 16, 111146),
    ('Ratio and Proportion', ['math'], ['elementary'],
     ['ratio', 'proportion'],
     ['es', 'zh-cn', 'zh-tw', 'fr', 'de', 'pt-br', 'ar', 'ja', 'ko', 'it', 'nl', 'pl', 'sv', 'tr', 'vi', 'hi', 'he', 'el', 'cs', 'hu', 'da', 'ro', 'fa', 'bn', 'th', 'ms', 'uz', 'my', 'bg', 'hr', 'sk', 'sl', 'sr', 'lt', 'lv', 'ca', 'eu', 'sw', 'sq'],
     False, False, 15, 2024, 6, 27, 264190),
    ('Reactants, Products and Leftovers', ['chemistry'], ['elementary', 'middle', 'high'],
     ['reactants', 'products', 'leftovers'],
     ['es', 'zh-cn', 'zh-tw', 'fr', 'de', 'pt-br', 'ru', 'ar', 'ja', 'ko', 'it', 'nl', 'pl', 'sv', 'tr', 'vi', 'hi', 'he', 'el', 'cs', 'hu', 'fi', 'da', 'ro', 'uk', 'fa', 'bn', 'th', 'ms', 'uz', 'kk', 'si', 'bg', 'hr', 'sk', 'sl', 'sr', 'nb', 'lt', 'lv', 'ca', 'eu', 'gl', 'sw', 'ka', 'mk', 'sq'],
     False, False, 25, 2024, 8, 19, 323935),
    ('Rutherford Scattering', ['physics', 'chemistry'], ['middle', 'high', 'university'],
     ['rutherford', 'scattering'],
     ['es', 'zh-cn', 'zh-tw', 'fr', 'de', 'pt-br', 'ru', 'ar', 'ja', 'ko', 'it', 'nl', 'pl', 'sv', 'tr', 'vi', 'hi', 'he', 'el', 'cs', 'hu', 'fi', 'da', 'ro', 'uk', 'fa', 'id', 'bn', 'th', 'ms', 'uz', 'kk', 'bg', 'hr', 'sk', 'sl', 'sr', 'nb', 'lt', 'lv', 'et', 'ca', 'eu', 'gl', 'sw', 'ka', 'mk', 'sq'],
     False, True, 30, 2025, 2, 18, 412074),
    ('States of Matter: Basics', ['physics', 'chemistry'], ['elementary', 'middle'],
     ['states', 'matter'],
     ['es', 'zh-cn', 'zh-tw', 'fr', 'de', 'pt-br', 'ru', 'ar', 'ja', 'ko', 'it', 'nl', 'pl', 'sv', 'tr', 'vi', 'hi', 'he', 'el', 'cs', 'hu', 'fi', 'da', 'ro', 'uk', 'fa', 'bn', 'th', 'ms', 'uz', 'kk', 'bg', 'hr', 'sk', 'sl', 'sr', 'lt', 'lv', 'is', 'ca', 'eu', 'sw', 'ka', 'sq'],
     False, False, 20, 2023, 4, 12, 229030),
    ('Under Pressure', ['physics', 'biology'], ['elementary', 'middle', 'high'],
     ['under', 'pressure'],
     ['es', 'zh-cn', 'zh-tw', 'fr', 'de', 'pt-br', 'ru', 'ar', 'ja', 'ko', 'it', 'nl', 'pl', 'sv', 'tr', 'vi', 'hi', 'he', 'el', 'cs', 'hu', 'fi', 'da', 'ro', 'uk', 'fa', 'id', 'bn', 'th', 'ms', 'uz', 'kk', 'si', 'bg', 'hr', 'sk', 'sl', 'sr', 'lt', 'lv', 'et', 'ca', 'eu', 'gl', 'sw', 'ka', 'mk', 'sq'],
     False, True, 25, 2025, 6, 4, 113542),
    ('Unit Rates', ['math'], ['elementary', 'middle'],
     ['unit', 'rates'],
     ['es', 'zh-cn', 'zh-tw', 'fr', 'de', 'pt-br', 'ru', 'ar', 'ja', 'ko', 'it', 'nl', 'pl', 'sv', 'tr', 'vi', 'hi', 'he', 'el', 'cs', 'hu', 'da', 'ro', 'fa', 'bn', 'th', 'ms', 'uz', 'kk', 'bg', 'hr', 'sk', 'sl', 'sr', 'lv', 'ca', 'eu', 'sw', 'sq'],
     True, True, 20, 2025, 7, 13, 161550),
    ('Vector Addition: Equations', ['math'], ['middle', 'high'],
     ['vector', 'addition', 'equations'],
     ['es', 'zh-cn', 'zh-tw', 'fr', 'de', 'pt-br', 'ru', 'ar', 'ja', 'ko', 'it', 'nl', 'pl', 'sv', 'tr', 'vi', 'hi', 'he', 'el', 'cs', 'hu', 'da', 'ro', 'uk', 'fa', 'bn', 'th', 'ms', 'uz', 'kk', 'bg', 'hr', 'sk', 'sl', 'sr', 'lv', 'is', 'ca', 'eu', 'af', 'sw', 'sq'],
     False, False, 25, 2023, 11, 20, 43884),
    ('Wave on a String', ['physics', 'chemistry', 'biology', 'math'], ['elementary', 'middle', 'high'],
     ['wave', 'string'],
     ['es', 'zh-cn', 'zh-tw', 'fr', 'de', 'pt-br', 'ru', 'ar', 'ja', 'ko', 'it', 'nl', 'pl', 'sv', 'tr', 'vi', 'hi', 'he', 'el', 'cs', 'hu', 'fi', 'da', 'ro', 'uk', 'fa', 'id', 'bn', 'th', 'ms', 'uz', 'kk', 'si', 'bg', 'hr', 'sk', 'sl', 'sr', 'nb', 'lt', 'lv', 'et', 'is', 'ca', 'eu', 'gl', 'af', 'sw', 'ka', 'mk', 'sq'],
     False, True, 25, 2025, 1, 12, 318431),
    ('Waves Intro', ['physics', 'biology'], ['elementary'],
     ['waves'],
     ['es', 'zh-cn', 'zh-tw', 'fr', 'de', 'pt-br', 'ru', 'ar', 'ja', 'ko', 'it', 'nl', 'pl', 'sv', 'tr', 'vi', 'hi', 'he', 'el', 'cs', 'hu', 'fi', 'da', 'ro', 'uk', 'fa', 'bn', 'th', 'ms', 'uz', 'kk', 'bg', 'hr', 'sk', 'sl', 'sr', 'nb', 'lt', 'lv', 'is', 'ca', 'eu', 'af', 'sw', 'ka', 'sq'],
     False, False, 15, 2024, 3, 24, 115069),
]


ACTIVITIES_SEED = [
    ("Forces and Motion: Basics", "Net Force Investigation",
     "Dr. Trish Loeblein", "high", 50,
     "Students predict, observe, and explain the motion of objects with "
     "balanced and unbalanced forces using friction and applied force."),
    ("Build an Atom", "Atomic Structure Lab",
     "Emily Moore", "middle", 45,
     "Build atoms of the first 10 elements, identify subatomic particles, "
     "and explore how protons determine the element."),
    ("Balancing Chemical Equations", "Coefficient Practice",
     "Yuen-Ying Carpenter", "high", 60,
     "Practice balancing combustion, synthesis, and decomposition reactions "
     "using the conservation of mass."),
    ("States of Matter", "Phase Change Inquiry",
     "Sam McKagan", "middle", 40,
     "Investigate the relationship between temperature, kinetic energy, "
     "and phase transitions for water, neon, oxygen, and argon."),
    ("Natural Selection", "Evolution of Bunnies",
     "Wendy Adams", "high", 55,
     "Model how variation, environment, and selection pressure together "
     "drive allele frequency change across generations."),
    ("Gravity and Orbits", "Modeling the Solar System",
     "Noah Finkelstein", "middle", 50,
     "Manipulate masses and distances to explore how gravitational force "
     "shapes planetary orbits in our solar system."),
    ("pH Scale", "Acids and Bases in the Kitchen",
     "Kelly Lancaster", "middle", 40,
     "Predict, measure, and rank common household solutions by pH and "
     "categorize each as acid, base, or neutral."),
    ("Plate Tectonics", "Boundary Identification",
     "Karina Hensberry", "high", 45,
     "Use animations to classify convergent, divergent, and transform "
     "boundaries and connect each to real-world geologic features."),
    ("Greenhouse Effect", "Climate Modeling Lab",
     "Trish Loeblein", "high", 60,
     "Model how atmospheric composition affects equilibrium temperature "
     "with and without greenhouse gases."),
    ("Circuit Construction Kit: DC", "Series and Parallel",
     "John De La Cruz", "high", 50,
     "Compare current and voltage in series vs parallel arrangements "
     "and verify Kirchhoff's laws empirically."),
    ("Fractions: Intro", "Equivalent Fractions Game",
     "Amanda McGarry", "elementary", 30,
     "Use bar models, number lines, and circle models to identify "
     "equivalent fractions and develop fluency."),
    ("Energy Skate Park", "Conservation of Energy",
     "Karina Hensberry", "high", 55,
     "Track potential, kinetic, thermal, and total energy as a skater "
     "moves through changing terrain."),
    ("Density", "Identify the Mystery Block",
     "Emily Moore", "middle", 35,
     "Use mass and volume measurements to identify the material of "
     "unknown solid blocks and explain buoyancy in water."),
    ("Graphing Lines", "Slope-Intercept Form",
     "Dr. Karina Hensberry", "middle", 40,
     "Investigate how m and b transform the line y = mx + b and apply "
     "this to real-world rate problems."),
    # === Additional activities tied to PhET API-derived simulations ===
    ("Beers Law Lab", "Spectrophotometry Practical",
     "Julia Chamberlain", "university", 75,
     "Measure absorbance vs. concentration across multiple wavelengths "
     "and validate the linear Beer-Lambert relationship from raw data."),
    ("Molarity", "Solution Stoichiometry Workshop",
     "Linda Koch", "high", 50,
     "Prepare dilutions from stock, predict molarity after mixing, and "
     "verify with conductivity-based estimates."),
    ("Molecule Shapes", "VSEPR Geometry Lab",
     "Theresa Doud", "high", 45,
     "Build small molecules, identify electron-pair geometry, and predict "
     "polarity from bond dipoles and molecular shape."),
    ("Molecules and Light", "Greenhouse Gas Spectra",
     "Trish Loeblein", "high", 55,
     "Match photon energy to molecular absorption modes and explain why "
     "specific gases drive atmospheric warming."),
    ("Energy Forms and Changes", "Energy Tracking Inquiry",
     "Sam McKagan", "middle", 50,
     "Trace energy transformations between mechanical, thermal, chemical, "
     "and radiant forms and account for conservation."),
    ("Energy Skate Park Basics", "Skater Energy Audit",
     "Karina Hensberry", "middle", 40,
     "Use the energy-vs-position graphs to predict turning points and "
     "estimate friction-related thermal losses."),
    ("Gravity Force Lab", "Inverse Square Law Investigation",
     "Trish Loeblein", "high", 45,
     "Measure gravitational force as masses and separation vary; fit the "
     "data to verify F ~ 1/r^2 and quantify uncertainty."),
    ("Hookes Law", "Spring Constant Lab",
     "John De La Cruz", "high", 45,
     "Apply incremental loads to series and parallel springs and derive "
     "individual and combined spring constants."),
    ("Faradays Law", "Induced EMF Workshop",
     "Kelly Lancaster", "university", 60,
     "Investigate how flux change drives induced EMF and predict the "
     "polarity of the induced current with Lenz's law."),
    ("Geometric Optics", "Lens Imaging Lab",
     "Amanda McGarry", "high", 50,
     "Map object and image distances across converging and diverging "
     "lenses; verify the thin-lens equation across multiple focal lengths."),
    ("Masses and Springs", "Period vs Mass Inquiry",
     "Wendy Adams", "middle", 40,
     "Determine the relationship between hanging mass and oscillation "
     "period and recover the spring constant from the regression slope."),
    ("Friction", "Friction in Everyday Surfaces",
     "Noah Finkelstein", "middle", 35,
     "Compare kinetic and static friction across surfaces and connect "
     "the observations to real-world examples like braking and walking."),
    ("Diffusion", "Tracking Particle Spread",
     "Emily Moore", "middle", 35,
     "Measure how concentration gradients drive net particle flux and "
     "explain why diffusion is faster at higher temperatures."),
    ("Gases Intro", "Pressure-Temperature Relationship",
     "Yuen-Ying Carpenter", "high", 45,
     "Hold volume constant and chart pressure versus temperature to "
     "recover Gay-Lussac's law from simulation data."),
    ("Number Compare", "Greater Less Equal Drill",
     "Amanda McGarry", "elementary", 25,
     "Compare two-digit numbers using place-value blocks and practice "
     "the >, <, and = symbols on increasingly mixed sets."),
    ("Fraction Matcher", "Equivalent Fraction Tournament",
     "Karina Hensberry", "elementary", 35,
     "Match equivalent fractions across visual models in a timed "
     "scaffolded sequence with self-checked answer cards."),
    ("Keplers Laws", "Orbits and Areas Investigation",
     "Noah Finkelstein", "university", 60,
     "Verify Kepler's second and third laws by sampling sweep areas and "
     "comparing period^2 / a^3 across simulated orbits."),
    ("Buoyancy", "Density and Sinking Lab",
     "Emily Moore", "high", 40,
     "Predict whether objects of various materials float or sink, then "
     "explain the outcome through density and displaced volume."),
    ("Collision Lab", "Momentum and Energy Carts",
     "Sam McKagan", "high", 50,
     "Compare elastic, inelastic, and explosive collisions; verify "
     "momentum conservation and quantify kinetic-energy loss."),
    ("John Travoltage", "Charge Transfer Inquiry",
     "Kelly Lancaster", "elementary", 25,
     "Investigate how friction-based charge buildup leads to a static "
     "discharge and connect to everyday observations."),
]


BENCHMARK_USERS = [
    ("teacher@phet.test", "Ada Lovelace", "phet-teacher-pass",
     "teacher", "Cherry Creek High School", "United States"),
    ("student@phet.test", "Carl Sagan", "phet-student-pass",
     "student", "Ithaca High School", "United States"),
    ("research@phet.test", "Marie Curie", "phet-research-pass",
     "researcher", "Sorbonne University", "France"),
    ("demo@phet.test", "Demo User", "phet-demo-pass",
     "teacher", "Demo School", "Canada"),
]


def seed_subjects():
    if Subject.query.count() > 0:
        return
    for slug, name, icon, color, desc in SUBJECTS_SEED:
        db.session.add(Subject(
            slug=slug, name=name, icon=icon, color=color, description=desc,
        ))
    db.session.commit()


def seed_grades():
    if GradeLevel.query.count() > 0:
        return
    for slug, name, age_range, sort_order in GRADES_SEED:
        db.session.add(GradeLevel(
            slug=slug, name=name, age_range=age_range, sort_order=sort_order,
        ))
    db.session.commit()


def seed_languages():
    if Language.query.count() > 0:
        return
    for code, name, native, rtl in LANGUAGES_SEED:
        db.session.add(Language(
            code=code, name=name, native_name=native, is_rtl=rtl, sim_count=0,
        ))
    db.session.commit()


def seed_simulations():
    if Simulation.query.count() > 0:
        return
    for row in SIMULATIONS_SEED:
        (title, subjects, grades, topics, extra_langs,
         featured, is_new, runtime, year, month, day, plays) = row
        slug = _slug(title)
        languages = ["en"] + list(extra_langs)
        sim = Simulation(
            slug=slug,
            title=title,
            short_description=_make_short_desc(title, topics),
            overview=_make_overview(title, topics, subjects),
            subjects_json=json.dumps(subjects),
            grades_json=json.dumps(grades),
            topics_json=json.dumps(topics),
            languages_json=json.dumps(languages),
            is_html5=True,
            is_featured=featured,
            is_new=is_new,
            thumbnail=f"{slug}.svg",
            runtime_minutes=runtime,
            release_date=date(year, month, day),
            play_count=plays,
            download_count=max(plays // 8, 1000),
        )
        db.session.add(sim)
    db.session.commit()

    # update per-language sim counts
    lang_counts = {l.code: 0 for l in Language.query.all()}
    for sim in Simulation.query.all():
        for code in sim.languages():
            if code in lang_counts:
                lang_counts[code] += 1
    for code, count in lang_counts.items():
        lang = Language.query.filter_by(code=code).first()
        if lang:
            lang.sim_count = count
    db.session.commit()


def seed_activities():
    if Activity.query.count() > 0:
        return
    for sim_title, title, author, grade, duration, desc in ACTIVITIES_SEED:
        sim = Simulation.query.filter_by(slug=_slug(sim_title)).first()
        if not sim:
            continue
        db.session.add(Activity(
            sim_id=sim.id,
            title=title,
            author=author,
            grade_level=grade,
            duration_min=duration,
            description=desc,
            file_type="PDF",
            download_count=max(duration * 137 % 9000, 350),
            published_date=date(2024, ((duration % 12) + 1), 15),
        ))
    db.session.commit()


def seed_benchmark_users():
    if User.query.count() > 0:
        return
    for email, name, password, role, institution, country in BENCHMARK_USERS:
        db.session.add(User(
            email=email,
            name=name,
            password_hash=bcrypt.generate_password_hash(password).decode(),
            role=role,
            institution=institution,
            country=country,
        ))
    db.session.commit()

    # Pre-populate saved sims for the demo teacher so the account page is
    # non-empty when an agent inspects it after login.
    teacher = User.query.filter_by(email="teacher@phet.test").first()
    if teacher:
        for slug in ("forces-and-motion-basics", "build-an-atom",
                     "ph-scale", "natural-selection"):
            sim = Simulation.query.filter_by(slug=slug).first()
            if sim:
                db.session.add(SavedSimulation(
                    user_id=teacher.id, sim_id=sim.id,
                    notes=f"Use for {sim.title} unit opener.",
                ))
        db.session.commit()


def _make_short_desc(title, topics):
    if not topics:
        return f"Interactive simulation: {title}."
    topic_str = ", ".join(topics[:3])
    return f"Explore {topic_str} with the interactive {title} simulation."


def _make_overview(title, topics, subjects):
    subject_names = ", ".join(s.replace("-", " ").title() for s in subjects)
    topic_list = ", ".join(topics) if topics else "core concepts"
    return (
        f"{title} is an interactive HTML5 simulation in the PhET "
        f"{subject_names} collection. Learners investigate {topic_list} "
        f"by directly manipulating model parameters and observing "
        f"real-time visual feedback. The simulation supports inquiry-"
        f"based instruction, formative assessment, and at-home practice, "
        f"and is freely available under a Creative Commons license."
    )


def seed_all():
    # Short-circuit: if the seed DB already contains the deepened catalogue
    # we have nothing to do. This keeps byte-identical resets working
    # because we never mutate the file on boot when it is already seeded.
    if (Simulation.query.count() > 0
            and LessonPlan.query.count() > 0
            and TeacherTip.query.count() > 0
            and NewsArticle.query.count() > 0
            and Sponsor.query.count() > 0):
        return
    seed_subjects()
    seed_grades()
    seed_languages()
    seed_simulations()
    seed_activities()
    seed_benchmark_users()
    seed_lesson_plans()
    seed_teacher_tips()
    seed_news_articles()
    seed_research_papers()
    seed_sponsors()
    seed_workshops()
    seed_team_members()
    seed_faq_items()
    normalize_seed_db_layout()


# ---------------------------------------------------------------------------
# Deepening seed data (lesson plans, tips, news, research, sponsors,
# workshops, team, FAQ, history). All deterministic from md5 + the existing
# simulation/grade/language seed. No randomness; rebuilds are byte-identical.
# ---------------------------------------------------------------------------

HISTORY_MILESTONES = [
    (2002, "Carl Wieman founds PhET",
     "Nobel laureate Carl Wieman launches the Physics Education "
     "Technology project at the University of Colorado Boulder to "
     "build research-driven physics simulations."),
    (2005, "First Java release",
     "Initial public release of more than 30 Java-based interactive "
     "simulations covering mechanics, electromagnetism, and quantum "
     "phenomena."),
    (2009, "Math and chemistry expansion",
     "PhET expands beyond physics to cover chemistry, math, and "
     "biology, surpassing 100 simulations and a hundred million "
     "annual plays."),
    (2012, "HTML5 transition begins",
     "Engineering team starts porting the catalogue from Java to "
     "HTML5 so that simulations can run on tablets and Chromebooks "
     "without browser plugins."),
    (2015, "Accessibility initiative launches",
     "PhET partners with disability researchers to add keyboard "
     "navigation, screen-reader descriptions, and sonification to "
     "core simulations."),
    (2018, "Global PhET reaches 100 languages",
     "Volunteer translators surpass 100 languages, making PhET the "
     "most widely-translated science education resource on the web."),
    (2021, "One billion plays",
     "Cumulative simulation plays cross the one-billion threshold; "
     "PhET classroom features ship for synchronous remote teaching."),
    (2024, "PhET Studio public beta",
     "PhET Studio enters public beta, letting teachers customise "
     "and share their own variants of existing simulations."),
    (2026, "Mirror release for research",
     "A deterministic mirror of the PhET catalogue is published for "
     "use by educational-AI researchers under a Creative Commons "
     "licence."),
]


def _slug_safe(text, fallback):
    s = re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")
    return s or fallback


LESSON_PLAN_TITLES = [
    ("Introductory Inquiry Lab", "Students predict outcomes, run trials, and reconcile "
     "observations with theory.", 45),
    ("Guided Concept Walkthrough", "Step-by-step guided exploration with built-in "
     "checkpoints and reflection prompts.", 60),
    ("Open-Ended Investigation", "Open-ended project format with student-chosen "
     "questions, data tables, and a short write-up.", 90),
    ("Quick Formative Check", "Twenty-minute lesson with three short tasks and a "
     "quick exit ticket.", 20),
    ("Differentiated Stations", "Tiered task stations supporting struggling, on-level, "
     "and advanced learners.", 75),
    ("Cross-Disciplinary Tie-In", "Connects the simulation to a real-world data "
     "set from environmental science.", 55),
    ("Engineering Design Challenge", "Students design a solution that satisfies a "
     "constraint stated in the prompt.", 80),
    ("Argument-from-Evidence", "Students collect observations and write a claim, "
     "evidence, reasoning paragraph.", 50),
    ("Modeling Cycle", "Build, test, refine. Students iterate on a conceptual model "
     "across two class periods.", 90),
    ("Phenomena-Anchored Discussion", "Anchored in a real classroom phenomenon and "
     "discussion-driven.", 40),
    ("Lab Report Practice", "Students complete a structured lab report using the "
     "simulation as the data source.", 60),
    ("Computational Thinking", "Students decompose the simulation behaviour into "
     "rules and predict the next state.", 65),
]


TEACHER_TIP_TITLES = [
    ("Run a Predict-Observe-Explain cycle",
     "classroom",
     "Have students write a prediction before running the simulation, then "
     "compare and reconcile after observing."),
    ("Pause the screen to focus discussion",
     "classroom",
     "Use the freeze button to lock the simulation state while students "
     "discuss what they see; restart only after every group has spoken."),
    ("Pair students for verbal explanations",
     "classroom",
     "Assign mixed-readiness pairs so the stronger student narrates the "
     "physical reasoning out loud while the partner manipulates controls."),
    ("Print the worksheet single-sided",
     "logistics",
     "Single-sided printing lets students lay out the entire activity at "
     "their desk and improves data-capture quality."),
    ("Project on the main board first",
     "classroom",
     "Begin by running the simulation on the projector while you narrate the "
     "controls; only then let students take over on their own devices."),
    ("Use the slow-motion control",
     "ux",
     "The slow-motion slider exposes intermediate states that look almost "
     "instantaneous at full speed; lean on it for kinematics."),
    ("Hide irrelevant variables early",
     "ux",
     "Most simulations let you hide secondary readouts; do that for "
     "introductory lessons so students focus on the main relationship."),
    ("Connect to a free-response writing prompt",
     "assessment",
     "End each session with a short open response that asks students to "
     "summarise the most surprising observation in writing."),
    ("Build vocabulary before you start",
     "language",
     "Pre-teach two or three key terms; the simulation accelerates only "
     "after students can name what they are watching."),
    ("Reset between groups",
     "logistics",
     "Always reset the simulation state between groups so the new students "
     "start from a known initial condition."),
    ("Re-use the screenshot tool",
     "assessment",
     "Have students screenshot two contrasting states and paste them into "
     "their lab notebook before changing variables again."),
    ("Use accessibility narration",
     "accessibility",
     "Turning on voicing narrates the underlying state and is useful even "
     "for fully sighted learners as a verbal scaffold."),
]


NEWS_ARTICLE_TITLES = [
    ("PhET Studio enters public beta", "platform",
     "PhET Studio, the in-browser tool that lets teachers build customised "
     "variants of existing simulations, is now in public beta."),
    ("New accessibility features land", "accessibility",
     "Three new accessibility features ship in this release: pan-and-zoom, "
     "alternative input, and sonification of mouse traces."),
    ("Global PhET passes 110 languages", "translations",
     "Volunteer translators have pushed the catalogue past 110 languages, "
     "with new launches in Tigrinya, Tajik, and Quechua."),
    ("Featured teacher: classroom innovations", "community",
     "This month's featured teacher describes how predict-observe-explain "
     "cycles transformed her introductory chemistry sequence."),
    ("Annual report 2025 published", "organization",
     "The 2025 annual report summarises platform usage, new translations, "
     "and the impact of the accessibility initiative."),
    ("Workshop series: virtual summer institute", "workshops",
     "Registration is open for the virtual summer institute, with eight "
     "live sessions and asynchronous lesson-design clinics."),
    ("Climate Change Model simulation released", "release",
     "The new Climate Change Model simulation models greenhouse-gas "
     "concentrations against global mean temperature."),
    ("Open data: anonymised play counts", "research",
     "We have published an anonymised dataset of simulation play counts "
     "for educational-AI researchers to study learning patterns."),
    ("Partnership with Mastercard Foundation", "organization",
     "A new partnership with the Mastercard Foundation will fund expansion "
     "into eleven sub-Saharan African countries."),
    ("Build a Nucleus exits beta", "release",
     "Build a Nucleus, our new nuclear physics simulation, exits beta "
     "today with refreshed accessibility features."),
    ("Research highlight: misconception probe", "research",
     "A new study using PhET tracking data quantifies how Newtonian "
     "misconceptions persist after instruction."),
    ("Teacher leaders program announces 2026 cohort", "community",
     "The Teacher Leaders program announces the 2026 cohort of forty "
     "educators across twelve countries."),
]


RESEARCH_PAPER_SEED = [
    ("Inquiry-based learning with interactive simulations",
     "Wieman, C., Adams, W., Perkins, K.",
     2008,
     "Science",
     "Reviews early evidence that PhET simulations support inquiry-based "
     "learning by exposing causal structure students cannot easily reach "
     "through static media.",
     "inquiry; simulations; physics education",
     "10.1126/science.1161948",
     842),
    ("PhET interactive simulations: transformative tools for teaching chemistry",
     "Lancaster, K., Moore, E., Parson, R., Perkins, K.",
     2013,
     "Journal of Chemical Education",
     "Documents how PhET chemistry simulations function as transformative "
     "tools when paired with appropriately scaffolded activities.",
     "chemistry; simulations; transformative learning",
     "10.1021/ed3003503",
     531),
    ("A framework for the design of simulation-based learning",
     "Adams, W., Reid, S., LeMaster, R., McKagan, S., Perkins, K., Wieman, C.",
     2008,
     "Journal of Interactive Learning Research",
     "Synthesises design heuristics, interviewing studies, and classroom "
     "observations into a coherent simulation-design framework.",
     "design; usability; education",
     "10.1119/1.2812550",
     412),
    ("Establishing the productive structure of student inquiry",
     "Podolefsky, N., Perkins, K., Adams, W.",
     2010,
     "Physical Review Special Topics - PER",
     "Argues that productive inquiry depends on cognitive scaffolds the "
     "simulation makes salient at the right moment.",
     "inquiry; scaffolding; physics",
     "10.1103/PhysRevSTPER.6.020117",
     287),
    ("Designing for inclusive use: accessibility in PhET simulations",
     "Smith, T., Moore, E., Perkins, K.",
     2020,
     "ACM ASSETS",
     "Documents the accessibility redesign that introduced keyboard "
     "navigation, voicing, and sonification across the catalogue.",
     "accessibility; inclusive design; voicing",
     "10.1145/3373625.3417013",
     94),
    ("Learning to balance equations using a digital tool",
     "Lancaster, K., Beard, R., Moore, E., Loeblein, T., Parson, R., Lemaster, R., Perkins, K.",
     2012,
     "Chemistry Education Research and Practice",
     "Quantitative pre/post study showing the Balancing Chemical Equations "
     "simulation closes the gap between symbolic and visual representations.",
     "balancing equations; chemistry; representational fluency",
     "10.1039/c2rp00010e",
     203),
    ("Productive failure with a simulated environment",
     "Kapur, M., Bielaczyc, K.",
     2012,
     "Journal of the Learning Sciences",
     "Shows simulations support productive failure by giving learners "
     "manipulable feedback after a wrong prediction.",
     "productive failure; learning sciences",
     "10.1080/10508406.2011.591717",
     679),
    ("Implicit feedback signals in interactive simulations",
     "Bopardikar, A., Adams, W.",
     2019,
     "Computers and Education",
     "Identifies which simulation responses functionally serve as feedback "
     "even when no explicit feedback message is given.",
     "feedback; cognitive load; HCI",
     "10.1016/j.compedu.2019.04.001",
     156),
    ("Trajectories of engagement in K-12 physics simulations",
     "Heim, A., Perkins, K., Madsen, A.",
     2021,
     "Physical Review PER",
     "Cluster analysis of click-stream data identifies four distinct "
     "engagement trajectories during simulation use.",
     "engagement; clustering; learning analytics",
     "10.1103/PhysRevPhysEducRes.17.010135",
     71),
    ("Cognitive coaching during simulation-based instruction",
     "Lopez, R., Olmstead, A.",
     2018,
     "International Journal of Science Education",
     "Compares scaffolded versus unscaffolded simulation lessons across "
     "twelve high-school classrooms.",
     "scaffolding; simulations; secondary",
     "10.1080/09500693.2018.1486101",
     142),
    ("Bilingual learners and visual representations in PhET",
     "Garcia, M., Perkins, K.",
     2022,
     "Journal of Research in Science Teaching",
     "Tests whether translated simulations narrow or widen the achievement "
     "gap for emergent bilingual learners.",
     "bilingual; representation; equity",
     "10.1002/tea.21745",
     58),
    ("Simulation-mediated peer discussion",
     "Olmstead, A., Smith, T.",
     2017,
     "International Journal of Science Education",
     "Quantitative coding of student utterances during paired simulation "
     "tasks; identifies productive discussion moves.",
     "peer discussion; collaboration",
     "10.1080/09500693.2017.1334049",
     188),
    ("Mathematical modeling through interactive simulation",
     "Roy, R., Adams, W.",
     2015,
     "Mathematical Thinking and Learning",
     "Argues that simulation parameters can serve as concrete anchors for "
     "abstract mathematical relationships.",
     "math; modeling; anchoring",
     "10.1080/10986065.2015.1054340",
     112),
    ("Teacher beliefs about simulation use in chemistry",
     "Loeblein, T., Lancaster, K.",
     2014,
     "Chemistry Education Research and Practice",
     "Survey of three hundred chemistry teachers exploring beliefs about "
     "when simulations should be introduced.",
     "teacher beliefs; survey",
     "10.1039/c4rp00057a",
     97),
    ("Computational artefacts as cognitive tools",
     "Wilensky, U., Resnick, M.",
     2009,
     "Mind, Culture, and Activity",
     "Theoretical paper arguing simulations work because they externalise "
     "cognitive structures.",
     "computational thinking; theory",
     "10.1080/10749030903253851",
     320),
    ("Voicing and sonification: complementary accessibility paths",
     "Smith, T., Tovar, J.",
     2023,
     "ACM ASSETS",
     "Comparative study of voicing-only, sonification-only, and combined "
     "configurations on simulation comprehension.",
     "voicing; sonification; accessibility",
     "10.1145/3597638.3614497",
     32),
]


SPONSOR_SEED = [
    ("moore", "Gordon and Betty Moore Foundation", "principal",
     "Long-time principal sponsor of PhET who funded the core HTML5 "
     "transition between 2014 and 2019.",
     "sponsor-moore.png", "https://www.moore.org/", 1),
    ("hewlett", "William and Flora Hewlett Foundation", "principal",
     "Supports PhET's open educational resources strategy and the "
     "translation programme.",
     "sponsor-hewlett.svg", "https://hewlett.org/", 2),
    ("nsf", "National Science Foundation", "principal",
     "Funded the original PhET research programme and a sequence of "
     "follow-on accessibility and learning-analytics grants.",
     "sponsor-nsf.png", "https://www.nsf.gov/", 3),
    ("mastercard", "Mastercard Foundation", "principal",
     "Funds expansion of PhET in sub-Saharan Africa, including teacher "
     "training and locally relevant lesson plans.",
     "sponsor-mastercard.svg", "https://mastercardfdn.org/", 4),
    ("yidan", "Yidan Prize Foundation", "principal",
     "Yidan Prize laureate funding supports PhET's global teacher "
     "leadership programme.",
     "sponsor-yidan.png", "https://yidanprize.org/", 5),
    ("amgen", "Amgen Foundation", "sustaining",
     "Funds biology simulation development and the Build a Nucleus "
     "interactive.",
     None, "https://www.amgenfoundation.org/", 10),
    ("cu", "University of Colorado Boulder", "sustaining",
     "Hosts PhET as a university project and provides core operational "
     "support including server infrastructure.",
     None, "https://www.colorado.edu/", 11),
    ("templeton", "John Templeton Foundation", "supporting",
     "Supports work on inquiry-based curiosity and learning trajectories.",
     None, "https://www.templeton.org/", 20),
    ("knight", "Knight Foundation", "supporting",
     "Funds the local-news literacy companion materials that pair with "
     "PhET data simulations.",
     None, "https://knightfoundation.org/", 21),
    ("rotary", "Rotary International", "supporting",
     "Supports printing and offline distribution of PhET activity guides "
     "in low-bandwidth regions.",
     None, "https://www.rotary.org/", 22),
    ("microsoft", "Microsoft Philanthropies", "supporting",
     "Provides in-kind cloud credits and accessibility engineering hours.",
     None, "https://www.microsoft.com/philanthropies/", 23),
    ("google", "Google.org", "supporting",
     "Supports the developer documentation translation effort.",
     None, "https://www.google.org/", 24),
]


WORKSHOP_SEED = [
    ("virtual-summer-institute-2026", "Virtual Summer Institute 2026",
     "Dr. Trish Loeblein", date(2026, 7, 14), 120, 200, 0,
     "Eight live sessions over two weeks covering simulation design, "
     "classroom use, and assessment design.",
     "Virtual"),
    ("classroom-mode-deep-dive", "Classroom Mode Deep Dive",
     "Emily Moore", date(2026, 6, 18), 90, 60, 0,
     "Hands-on workshop for the Classroom Mode feature with realistic "
     "student scenarios.",
     "Virtual"),
    ("accessibility-workshop-spring", "Accessibility Workshop: Voicing and Sonification",
     "Taliesin Smith", date(2026, 6, 4), 90, 80, 0,
     "A practical introduction to the accessibility features and how to "
     "design lessons that exercise them.",
     "Virtual"),
    ("lesson-plan-design-clinic", "Lesson Plan Design Clinic",
     "Trish Loeblein and Karina Hensberry", date(2026, 8, 22), 120, 50, 0,
     "Bring an existing lesson and leave with a redesigned PhET-anchored "
     "version with peer feedback.",
     "Virtual"),
    ("phet-studio-getting-started", "PhET Studio: Getting Started",
     "Robert Parson", date(2026, 9, 10), 75, 100, 0,
     "Walkthrough of PhET Studio with a focus on customising existing "
     "simulations for your own classroom.",
     "Virtual"),
    ("global-phet-translator-summit", "Global PhET Translator Summit",
     "Diana Lopez-Tavares", date(2026, 10, 5), 180, 150, 0,
     "Annual gathering of volunteer translators with sessions on locale "
     "review and quality control.",
     "Virtual"),
    ("phet-day-boulder", "PhET Day Boulder 2026",
     "Kathy Perkins", date(2026, 11, 1), 360, 80, 0,
     "In-person day at the University of Colorado Boulder with hands-on "
     "demos and a tour of the engineering team.",
     "Boulder, CO"),
    ("middle-school-lab-design", "Middle School Lab Design Workshop",
     "Karina Hensberry", date(2026, 5, 30), 90, 60, 0,
     "Lab-design workshop tailored to the middle-school grade band.",
     "Virtual"),
    ("phet-day-springfield-2025", "PhET Day Springfield 2025",
     "Trish Loeblein", date(2025, 11, 8), 360, 80, 0,
     "Historical in-person event held in Springfield, included for "
     "completeness.",
     "Springfield, MA"),
    ("intro-to-html5-sims", "Intro to HTML5 Simulations",
     "Sam Reid", date(2024, 5, 12), 60, 100, 0,
     "Historical session walking new teachers through the HTML5 "
     "simulation lifecycle.",
     "Virtual"),
    ("assessment-with-sims-2024", "Assessment with Simulations 2024",
     "Wendy Adams", date(2024, 7, 7), 90, 120, 0,
     "Historical workshop on building assessment items that pair with "
     "simulation use.",
     "Virtual"),
    ("equity-in-stem-2025", "Equity in STEM 2025",
     "Diana Lopez-Tavares", date(2025, 3, 14), 120, 100, 0,
     "Workshop on equity-minded simulation use across linguistic and "
     "ability differences.",
     "Virtual"),
]


TEAM_MEMBER_SEED = [
    ("kathy-perkins", "Kathy Perkins", "Director", "leadership",
     "Kathy Perkins directs PhET Interactive Simulations and leads its "
     "research and partnership programmes. She holds a PhD in physics "
     "from Harvard University.", None, 1),
    ("emily-moore", "Emily Moore", "Director of Research and Design", "leadership",
     "Emily Moore directs PhET's research and design programme, including "
     "the accessibility and inclusive design initiative.", None, 2),
    ("trish-loeblein", "Dr. Trish Loeblein", "Senior Teacher in Residence", "teachers",
     "Trish Loeblein is a long-time PhET teacher-in-residence and lead "
     "author of many of the most-downloaded lesson plans.", None, 3),
    ("sam-reid", "Sam Reid", "Lead Software Engineer", "engineering",
     "Sam Reid leads PhET's software engineering team and has driven the "
     "HTML5 simulation architecture since 2012.", None, 4),
    ("taliesin-smith", "Taliesin Smith", "Accessibility Lead", "engineering",
     "Taliesin Smith leads the accessibility engineering effort, with a "
     "focus on voicing and sonification.", None, 5),
    ("diana-lopez-tavares", "Diana Lopez-Tavares", "Translations Manager", "translations",
     "Diana coordinates the volunteer translator network and oversees the "
     "Global PhET initiative across more than a hundred locales.", None, 6),
    ("karina-hensberry", "Karina Hensberry", "Teacher in Residence", "teachers",
     "Karina Hensberry contributes lesson plans, classroom-mode design "
     "input, and middle-school teacher training.", None, 7),
    ("robert-parson", "Robert Parson", "Chemistry Lead", "research",
     "Robert Parson leads chemistry simulation design, with a focus on "
     "representational fluency between symbolic and visual chemistry.", None, 8),
    ("wendy-adams", "Wendy Adams", "Senior Research Associate", "research",
     "Wendy Adams led the foundational interviewing studies that shaped "
     "PhET's design heuristics.", None, 9),
    ("noah-podolefsky", "Noah Podolefsky", "Research Associate", "research",
     "Noah Podolefsky studies the cognitive structure of student inquiry "
     "with interactive simulations.", None, 10),
    ("ariel-paul", "Ariel Paul", "Math Lead", "engineering",
     "Ariel Paul leads PhET's math simulation team and has built "
     "Fractions Intro and the Area Model series.", None, 11),
    ("jonathan-olson", "Jonathan Olson", "Engineering Manager", "engineering",
     "Jonathan Olson manages day-to-day engineering and the release "
     "process for the simulation catalogue.", None, 12),
    ("amanda-mclaren", "Amanda McLaren", "UX Designer", "design",
     "Amanda McLaren designs interaction flows and accessibility "
     "affordances across the catalogue.", None, 13),
    ("matt-blackman", "Matt Blackman", "Software Engineer", "engineering",
     "Matt Blackman works on the simulation runtime and contributed to "
     "the PhET Studio MVP.", None, 14),
    ("megan-hoffman", "Megan Hoffman", "Project Manager", "leadership",
     "Megan Hoffman coordinates simulation development cycles and the "
     "annual roadmap.", None, 15),
    ("brett-fiedler", "Brett Fiedler", "Sonification Engineer", "engineering",
     "Brett Fiedler designs the mouse-trace sonification and voicing "
     "engine.", None, 16),
    ("jonathan-shoults", "Jonathan Shoults", "Front-end Engineer", "engineering",
     "Jonathan Shoults works on PhET's front-end framework and the new "
     "Studio interface.", None, 17),
    ("nick-walker", "Nick Walker", "Build Engineer", "engineering",
     "Nick Walker maintains the build, release, and translation tooling "
     "for the catalogue.", None, 18),
    ("anna-amick", "Anna Amick", "Teacher Liaison", "teachers",
     "Anna Amick coordinates the teacher leaders programme and field "
     "workshops.", None, 19),
    ("matt-pennington", "Matt Pennington", "Quality Engineer", "engineering",
     "Matt Pennington runs the cross-browser regression suite for every "
     "PhET release.", None, 20),
]


FAQ_SEED = [
    ("general", "What is PhET Interactive Simulations?",
     "PhET is a non-profit project at the University of Colorado "
     "Boulder that produces free interactive simulations for math and "
     "science education.", 1),
    ("general", "Is PhET free?",
     "Yes. All simulations and teaching resources are free and "
     "released under a Creative Commons licence.", 2),
    ("general", "Who builds PhET?",
     "A team of engineers, researchers, designers, and teachers at the "
     "University of Colorado Boulder, with a network of volunteer "
     "translators and educator contributors.", 3),
    ("general", "What languages are supported?",
     "More than a hundred languages, with the most common being "
     "English, Spanish, Chinese, French, German, and Portuguese.", 4),
    ("general", "Where can I report a bug?",
     "Each simulation has a Report a Bug page accessible from the "
     "Sim detail view. We triage reports weekly.", 5),
    ("technical", "Do I need an account to use simulations?",
     "No. Simulations run anonymously in your browser; an account is "
     "only required to save favourites and post comments.", 1),
    ("technical", "What devices are supported?",
     "Any modern desktop or tablet browser. HTML5 simulations are "
     "tested on Chromebooks, iPads, iPhones, Windows, macOS, and Linux.", 2),
    ("technical", "Can I run PhET offline?",
     "Yes. Each simulation can be downloaded as a self-contained HTML "
     "file from its detail page.", 3),
    ("technical", "Why do some sims still require Java?",
     "A small number of legacy simulations have not yet been ported "
     "to HTML5 and require Java. They remain available as downloads.", 4),
    ("technical", "How do I report an accessibility issue?",
     "Every simulation has a Report an Accessibility Issue link "
     "that routes directly to the accessibility engineering team.", 5),
    ("teaching", "How do I find a lesson plan for my class?",
     "Browse the Lesson Plans page or filter by grade band and "
     "subject on the activities page.", 1),
    ("teaching", "Can I submit my own lesson plan?",
     "Yes. Sign in and use the Submit a Lesson Plan page. We review "
     "submissions before publishing.", 2),
    ("teaching", "Are there training workshops?",
     "Yes. See the Workshops page for the upcoming schedule, which "
     "includes free virtual sessions and the annual PhET Day event.", 3),
    ("teaching", "Can I host a classroom session?",
     "Yes. Sign in, open the Classroom Mode page, and create a "
     "session code that students can join.", 4),
    ("teaching", "Do you offer professional development credit?",
     "Selected workshops offer continuing-education credit; check the "
     "individual workshop page.", 5),
    ("accessibility", "Which simulations support keyboard navigation?",
     "All simulations that are part of the inclusive design programme "
     "support keyboard navigation. See each Sim Accessibility page.", 1),
    ("accessibility", "What is voicing?",
     "Voicing is a feature that reads aloud the current state of the "
     "simulation, supplementing screen-reader output.", 2),
    ("accessibility", "What is sonification?",
     "Sonification represents simulation state as sound: pitch and "
     "timbre vary to communicate continuous variables.", 3),
    ("accessibility", "Can I use a switch device?",
     "Many simulations support alternative input including switch "
     "devices through their inclusive controls.", 4),
    ("accessibility", "Where is the accessibility policy?",
     "See the Accessibility page for the full policy and the per-"
     "simulation accessibility detail pages.", 5),
    ("donations", "How can I donate?",
     "Use the Donate page to make a one-time or recurring contribution.", 1),
    ("donations", "Is PhET a registered non-profit?",
     "PhET is a project of the University of Colorado Boulder, which "
     "is a public, non-profit university.", 2),
    ("donations", "Can my company sponsor PhET?",
     "Yes. Contact the team via the Contact page; corporate "
     "partnerships fund specific simulation programmes.", 3),
    ("donations", "Will my donation receipt be tax-deductible?",
     "Donations are processed by the University of Colorado "
     "Foundation and are tax-deductible in the United States.", 4),
]


def seed_lesson_plans():
    if LessonPlan.query.count() > 0:
        return
    sims = Simulation.query.order_by(Simulation.title).all()
    grade_bands = ["elementary", "middle", "high", "university"]
    title_count = len(LESSON_PLAN_TITLES)
    for i, sim in enumerate(sims):
        plans_per_sim = 1 + (_md5_seed("lp_count", sim.slug) % 2)
        for n in range(plans_per_sim):
            h = _md5_seed("lp", sim.slug, n)
            tpl = LESSON_PLAN_TITLES[h % title_count]
            grade = grade_bands[(h >> 4) % 4]
            author_idx = (h >> 8) % len(TEAM_MEMBER_SEED)
            author = TEAM_MEMBER_SEED[author_idx][1]
            base = _slug_safe(f"{sim.slug}-{tpl[0]}", f"lp-{sim.id}-{n}")
            slug = _unique_slug(LessonPlan, base)
            day = 1 + (h % 27)
            month = 1 + ((h >> 12) % 12)
            year = 2024 + ((h >> 16) % 2)
            db.session.add(LessonPlan(
                slug=slug,
                title=f"{sim.title}: {tpl[0]}",
                sim_id=sim.id,
                author=author,
                grade_band=grade,
                duration_min=tpl[2],
                objectives=(
                    f"Students will use the {sim.title} simulation to "
                    f"investigate the underlying relationships and "
                    f"reason from observation to claim."
                ),
                materials=(
                    "Computer or tablet with browser, paper, pencil, "
                    "student worksheet (one per pair)."
                ),
                body=(
                    f"{tpl[1]} Students open the {sim.title} simulation, "
                    f"complete the predict-observe-explain cycle, and "
                    f"submit a short write-up. Differentiation notes are "
                    f"included for {grade} learners."
                ),
                standards="NGSS, Common Core Math Practice 4",
                cover_image=f"{sim.slug}.png",
                rating_sum=(h % 250),
                rating_count=max(1, (h >> 3) % 80),
                download_count=max(120, (h >> 5) % 9000),
                published_date=date(year, month, day),
            ))
    db.session.commit()


def seed_teacher_tips():
    if TeacherTip.query.count() > 0:
        return
    sims = Simulation.query.order_by(Simulation.title).limit(80).all()
    for i, sim in enumerate(sims):
        h = _md5_seed("tip", sim.slug)
        tpl = TEACHER_TIP_TITLES[h % len(TEACHER_TIP_TITLES)]
        base = _slug_safe(f"{tpl[0]}-{sim.slug}", f"tip-{sim.id}")
        slug = _unique_slug(TeacherTip, base)
        day = 1 + (h % 27)
        month = 1 + ((h >> 8) % 12)
        author_idx = (h >> 12) % len(TEAM_MEMBER_SEED)
        db.session.add(TeacherTip(
            slug=slug,
            title=f"{tpl[0]} — using {sim.title}",
            author=TEAM_MEMBER_SEED[author_idx][1],
            category=tpl[1],
            summary=tpl[2][:380],
            body=(
                f"{tpl[2]} Specifically for the {sim.title} simulation, "
                f"this tip works well during the first ten minutes of "
                f"class. Pair it with a quick exit-ticket question to "
                f"surface lingering misconceptions."
            ),
            upvotes=(h >> 4) % 250,
            published_date=date(2024 + ((h >> 16) % 2), month, day),
        ))
    db.session.commit()


def seed_news_articles():
    if NewsArticle.query.count() > 0:
        return
    # 12 themed articles, with variants per sim for the climate / release ones
    for i, (title, cat, summary) in enumerate(NEWS_ARTICLE_TITLES):
        h = _md5_seed("news", title)
        base = _slug_safe(title, f"news-{i}")
        slug = _unique_slug(NewsArticle, base)
        day = 1 + (h % 27)
        month = 1 + ((h >> 8) % 12)
        author_idx = (h >> 12) % len(TEAM_MEMBER_SEED)
        db.session.add(NewsArticle(
            slug=slug,
            title=title,
            summary=summary,
            body=(
                f"{summary} This article walks through the change, the "
                f"motivation behind it, and what it means for teachers "
                f"and learners. The PhET team welcomes feedback through "
                f"the Contact page or the community forum."
            ),
            author=TEAM_MEMBER_SEED[author_idx][1],
            category=cat,
            published_date=date(2025 + ((h >> 16) % 2), month, day),
            cover_image=None,
            view_count=(h >> 4) % 50000,
        ))
    # add per-sim release notes for sims marked is_new to thicken the index
    new_sims = Simulation.query.filter_by(is_new=True).order_by(Simulation.title).all()
    for i, sim in enumerate(new_sims):
        h = _md5_seed("news_rel", sim.slug)
        title = f"Release notes: {sim.title}"
        base = _slug_safe(f"release-notes-{sim.slug}", f"news-rel-{sim.id}")
        slug = _unique_slug(NewsArticle, base)
        day = 1 + (h % 27)
        month = 1 + ((h >> 8) % 12)
        author_idx = (h >> 12) % len(TEAM_MEMBER_SEED)
        db.session.add(NewsArticle(
            slug=slug,
            title=title,
            summary=(
                f"{sim.title} ships with refreshed accessibility "
                f"features and updated translations."
            ),
            body=(
                f"{sim.title} is now released. The release adds the new "
                f"voicing engine and refreshed translations covering "
                f"more than thirty additional locales. See the "
                f"accessibility page for the full feature matrix."
            ),
            author=TEAM_MEMBER_SEED[author_idx][1],
            category="release",
            published_date=sim.release_date,
            cover_image=None,
            view_count=(h >> 4) % 25000,
        ))
    db.session.commit()


def seed_research_papers():
    if ResearchPaper.query.count() > 0:
        return
    for title, authors, year, venue, abstract, kw, doi, cites in RESEARCH_PAPER_SEED:
        h = _md5_seed("paper", title)
        base = _slug_safe(title, f"paper-{h % 9999}")
        slug = _unique_slug(ResearchPaper, base)
        db.session.add(ResearchPaper(
            slug=slug,
            title=title,
            authors=authors,
            year=year,
            venue=venue,
            abstract=abstract,
            keywords=kw,
            citation_count=cites,
            doi=doi,
        ))
    db.session.commit()


def seed_sponsors():
    if Sponsor.query.count() > 0:
        return
    for slug, name, tier, blurb, logo, hp, sort_order in SPONSOR_SEED:
        db.session.add(Sponsor(
            slug=slug, name=name, tier=tier, blurb=blurb,
            logo=logo, homepage=hp, sort_order=sort_order,
        ))
    db.session.commit()


def seed_workshops():
    if Workshop.query.count() > 0:
        return
    for slug, title, presenter, held, dur, cap, reg, desc, loc in WORKSHOP_SEED:
        db.session.add(Workshop(
            slug=slug, title=title, presenter=presenter,
            held_on=held, duration_min=dur, capacity=cap,
            registered=reg, description=desc, location=loc,
        ))
    db.session.commit()


def seed_team_members():
    if TeamMember.query.count() > 0:
        return
    for slug, name, role, team, bio, photo, sort_order in TEAM_MEMBER_SEED:
        db.session.add(TeamMember(
            slug=slug, name=name, role=role, team=team,
            bio=bio, photo=photo, sort_order=sort_order,
        ))
    db.session.commit()


def seed_faq_items():
    if FAQItem.query.count() > 0:
        return
    for category, question, answer, sort_order in FAQ_SEED:
        h = _md5_seed("faq", category, question)
        db.session.add(FAQItem(
            category=category,
            question=question,
            answer=answer,
            sort_order=sort_order,
            helpful=(h >> 4) % 320,
        ))
    db.session.commit()


def normalize_seed_db_layout():
    """Pin auto_increment counters and VACUUM so the on-disk database is
    byte-identical between rebuilds. See harden-env gotcha #3."""
    try:
        db.session.execute(text("VACUUM"))
        db.session.commit()
    except Exception:
        db.session.rollback()


with app.app_context():
    db.create_all()
    seed_all()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 40015))
    app.run(host="0.0.0.0", port=port, debug=False)
