"""Mayo Clinic mirror — Flask app for the WebHarbor benchmark.

Routes cover:
- Home + nav
- Diseases & Conditions: A-Z index + detail
- Symptoms A-Z + detail + multi-step Symptom Checker wizard
- Tests & Procedures: A-Z + detail
- Drugs & Supplements: A-Z + detail
- Departments & Doctors with faceted Find-a-Doctor search
- Clinical Trials directory + detail
- Healthy Lifestyle hub + article detail
- Patient Stories
- News articles
- Request Appointment (multi-step)
- Patient Portal stub + Login/Register
- Search across diseases / procedures / drugs / doctors
- About / Locations / Careers / Education
- Cancer Center hub + per-cancer-type pages
- Body System browse landing
- Glossary A-Z
- Patient & Visitor info hub
- Refer-a-patient / second opinion / international patient forms
- Career application form
- Donation form
- Per-campus detail pages
"""
import os
import re
import string
import hashlib
from datetime import datetime, date, timedelta
from functools import wraps

from flask import (
    Flask, render_template, request, redirect, url_for, flash, jsonify,
    abort, session, Response,
)
from flask_sqlalchemy import SQLAlchemy
from flask_login import (
    LoginManager, UserMixin, login_user, logout_user, login_required, current_user,
)
from flask_bcrypt import Bcrypt

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
os.makedirs(os.path.join(BASE_DIR, "instance"), exist_ok=True)

app = Flask(__name__, instance_path=os.path.join(BASE_DIR, "instance"))
app.url_map.strict_slashes = False
app.config["SECRET_KEY"] = "mayo_clinic-dev-secret-please-change"
app.config["SQLALCHEMY_DATABASE_URI"] = (
    "sqlite:///" + os.path.join(BASE_DIR, "instance", "mayo_clinic.db")
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = "login"

MIRROR_REFERENCE_DATE = datetime(2026, 5, 27)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
STOP_WORDS = {'the','a','an','in','on','at','to','for','of','and','or','is','it','by','with','what','where','who','how','find','tell','me'}


def tokens(q):
    return [t.lower() for t in re.split(r"\W+", q or "") if t and t.lower() not in STOP_WORDS and len(t) > 1]


def scored_search(query, items, fields):
    toks = tokens(query)
    if not toks:
        return list(items)
    results = []
    for item in items:
        text = " ".join((getattr(item, f, "") or "") for f in fields).lower()
        score = sum(1 for t in toks if t in text)
        if score > 0:
            results.append((item, score))
    results.sort(key=lambda x: -x[1])
    return [r[0] for r in results]


def slugify(text):
    t = (text or "").lower().strip()
    t = re.sub(r"[^a-z0-9]+", "-", t)
    return t.strip("-")


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    display_name = db.Column(db.String(120), nullable=False, default="Patient")
    password_hash = db.Column(db.String(255), nullable=False)
    date_of_birth = db.Column(db.String(20), default="")
    phone = db.Column(db.String(40), default="")
    address = db.Column(db.String(255), default="")
    preferred_location = db.Column(db.String(40), default="Rochester")
    created_at = db.Column(db.DateTime, default=lambda: MIRROR_REFERENCE_DATE)


class Department(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(80), unique=True, nullable=False)
    name = db.Column(db.String(160), nullable=False)
    description = db.Column(db.Text, default="")
    locations = db.Column(db.String(255), default="")  # comma-joined
    focus_areas = db.Column(db.Text, default="")  # comma-joined


class Doctor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(140), unique=True, nullable=False)
    name = db.Column(db.String(160), nullable=False)
    credentials = db.Column(db.String(40), default="M.D.")
    specialty = db.Column(db.String(160), nullable=False)
    dept_id = db.Column(db.Integer, db.ForeignKey("department.id"))
    dept_slug = db.Column(db.String(80), default="")
    locations = db.Column(db.String(255), default="")
    languages = db.Column(db.String(255), default="English")
    education = db.Column(db.Text, default="")  # newline-joined
    focus_areas = db.Column(db.Text, default="")  # comma-joined
    research_interests = db.Column(db.Text, default="")
    bio = db.Column(db.Text, default="")
    accepts_appointments = db.Column(db.Boolean, default=True)
    department = db.relationship("Department", backref="doctors")


class Condition(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(140), unique=True, nullable=False)
    name = db.Column(db.String(200), nullable=False)
    primary_dept_slug = db.Column(db.String(80), default="")
    summary = db.Column(db.Text, default="")
    overview = db.Column(db.Text, default="")
    symptoms = db.Column(db.Text, default="")
    causes = db.Column(db.Text, default="")
    risk_factors = db.Column(db.Text, default="")
    complications = db.Column(db.Text, default="")
    prevention = db.Column(db.Text, default="")
    diagnosis = db.Column(db.Text, default="")
    treatment = db.Column(db.Text, default="")
    lifestyle = db.Column(db.Text, default="")
    alternative = db.Column(db.Text, default="")
    preparing = db.Column(db.Text, default="")
    references_text = db.Column(db.Text, default="")
    related_procedures = db.Column(db.String(500), default="")  # comma slugs
    related_drugs = db.Column(db.String(500), default="")


class Procedure(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(140), unique=True, nullable=False)
    name = db.Column(db.String(200), nullable=False)
    dept_slug = db.Column(db.String(80), default="")
    category = db.Column(db.String(40), default="procedure")
    summary = db.Column(db.Text, default="")
    why_done = db.Column(db.Text, default="")
    how_to_prepare = db.Column(db.Text, default="")
    what_you_can_expect = db.Column(db.Text, default="")
    results = db.Column(db.Text, default="")
    risks = db.Column(db.Text, default="")


class Drug(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(140), unique=True, nullable=False)
    name = db.Column(db.String(200), nullable=False)
    kind = db.Column(db.String(40), default="prescription")  # prescription / otc / supplement
    route = db.Column(db.String(120), default="Oral")
    treats = db.Column(db.String(500), default="")
    description = db.Column(db.Text, default="")
    dosage = db.Column(db.Text, default="")
    side_effects = db.Column(db.Text, default="")
    warnings = db.Column(db.Text, default="")
    interactions = db.Column(db.Text, default="")


class Symptom(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(140), unique=True, nullable=False)
    name = db.Column(db.String(160), nullable=False)
    region = db.Column(db.String(40), default="general")
    demographic = db.Column(db.String(20), default="both")
    description = db.Column(db.Text, default="")
    when_to_see_doctor = db.Column(db.Text, default="")
    causes = db.Column(db.Text, default="")


class SymptomRule(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    symptom_slug = db.Column(db.String(140))
    age_group = db.Column(db.String(20))  # adult / child / any
    duration = db.Column(db.String(20))  # acute / chronic / any
    condition_name = db.Column(db.String(200))
    condition_slug = db.Column(db.String(140))
    urgency = db.Column(db.String(20))  # urgent / routine / self
    note = db.Column(db.Text, default="")
    rank = db.Column(db.Integer, default=0)


class ClinicalTrial(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nct_id = db.Column(db.String(40), unique=True, nullable=False)
    title = db.Column(db.String(400), nullable=False)
    condition_keyword = db.Column(db.String(200), default="")
    phase = db.Column(db.String(40), default="Phase 2")
    status = db.Column(db.String(40), default="Recruiting")
    intervention = db.Column(db.String(400), default="")
    brief_summary = db.Column(db.Text, default="")
    eligibility = db.Column(db.Text, default="")
    locations = db.Column(db.String(255), default="")
    principal_investigator_id = db.Column(db.Integer, db.ForeignKey("doctor.id"))
    principal_investigator = db.relationship("Doctor")


class Article(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(140), unique=True, nullable=False)
    title = db.Column(db.String(300), nullable=False)
    category = db.Column(db.String(80), default="Healthy Lifestyle")
    summary = db.Column(db.Text, default="")
    body = db.Column(db.Text, default="")
    published_date = db.Column(db.String(40), default="")
    kind = db.Column(db.String(20), default="lifestyle")  # lifestyle / news / story


class AppointmentRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    dept_slug = db.Column(db.String(80))
    location = db.Column(db.String(40), default="Rochester")
    preferred_date = db.Column(db.String(40), default="")
    patient_name = db.Column(db.String(200))
    patient_email = db.Column(db.String(200))
    patient_phone = db.Column(db.String(80))
    reason = db.Column(db.Text, default="")
    insurance = db.Column(db.String(120), default="")
    new_or_returning = db.Column(db.String(20), default="new")
    status = db.Column(db.String(20), default="submitted")
    confirmation_code = db.Column(db.String(20))
    created_at = db.Column(db.DateTime, default=lambda: MIRROR_REFERENCE_DATE)


class SavedItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    kind = db.Column(db.String(30))  # condition / procedure / drug / article
    slug = db.Column(db.String(140))
    title = db.Column(db.String(300))
    saved_at = db.Column(db.DateTime, default=lambda: MIRROR_REFERENCE_DATE)


class NewsletterSignup(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(200))
    topic = db.Column(db.String(80), default="general")
    created_at = db.Column(db.DateTime, default=lambda: MIRROR_REFERENCE_DATE)


class ArticleFeedback(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    article_slug = db.Column(db.String(140))
    article_kind = db.Column(db.String(20))  # condition / article / procedure
    helpful = db.Column(db.Boolean, default=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: MIRROR_REFERENCE_DATE)


class GlossaryTerm(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(140), unique=True, nullable=False)
    term = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(80), default="General")
    definition = db.Column(db.Text, default="")


class ReferralRequest(db.Model):
    """Physician-to-physician referral / refer-a-patient."""
    id = db.Column(db.Integer, primary_key=True)
    referring_provider = db.Column(db.String(200))
    referring_clinic = db.Column(db.String(200))
    referring_phone = db.Column(db.String(80))
    referring_email = db.Column(db.String(200))
    npi = db.Column(db.String(40), default="")
    patient_name = db.Column(db.String(200))
    patient_dob = db.Column(db.String(40))
    patient_diagnosis = db.Column(db.String(400))
    requested_department = db.Column(db.String(80))
    requested_location = db.Column(db.String(40))
    notes = db.Column(db.Text, default="")
    urgency = db.Column(db.String(20), default="routine")
    status = db.Column(db.String(40), default="received")
    confirmation_code = db.Column(db.String(40))
    created_at = db.Column(db.DateTime, default=lambda: MIRROR_REFERENCE_DATE)


class SecondOpinion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_name = db.Column(db.String(200))
    patient_email = db.Column(db.String(200))
    patient_phone = db.Column(db.String(80))
    diagnosis = db.Column(db.String(400))
    current_treatment = db.Column(db.Text)
    desired_review = db.Column(db.Text)
    department_slug = db.Column(db.String(80))
    records_attached = db.Column(db.Boolean, default=False)
    confirmation_code = db.Column(db.String(40))
    status = db.Column(db.String(40), default="received")
    created_at = db.Column(db.DateTime, default=lambda: MIRROR_REFERENCE_DATE)


class InternationalInquiry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_name = db.Column(db.String(200))
    patient_email = db.Column(db.String(200))
    patient_phone = db.Column(db.String(80))
    country = db.Column(db.String(100))
    language = db.Column(db.String(80))
    diagnosis = db.Column(db.String(400))
    travel_dates = db.Column(db.String(120))
    accommodation = db.Column(db.Boolean, default=False)
    translation = db.Column(db.Boolean, default=False)
    confirmation_code = db.Column(db.String(40))
    status = db.Column(db.String(40), default="received")
    created_at = db.Column(db.DateTime, default=lambda: MIRROR_REFERENCE_DATE)


class Donation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    donor_name = db.Column(db.String(200))
    donor_email = db.Column(db.String(200))
    amount = db.Column(db.Integer)  # USD whole dollars
    frequency = db.Column(db.String(20), default="one-time")  # one-time / monthly
    fund = db.Column(db.String(80), default="general")
    dedication = db.Column(db.String(200), default="")
    is_anonymous = db.Column(db.Boolean, default=False)
    confirmation_code = db.Column(db.String(40))
    created_at = db.Column(db.DateTime, default=lambda: MIRROR_REFERENCE_DATE)


class JobApplication(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    job_title = db.Column(db.String(200))
    applicant_name = db.Column(db.String(200))
    applicant_email = db.Column(db.String(200))
    applicant_phone = db.Column(db.String(80))
    years_experience = db.Column(db.Integer)
    cover_letter = db.Column(db.Text, default="")
    resume_filename = db.Column(db.String(200), default="")
    location_pref = db.Column(db.String(40), default="")
    available_date = db.Column(db.String(40), default="")
    status = db.Column(db.String(40), default="received")
    confirmation_code = db.Column(db.String(40))
    created_at = db.Column(db.DateTime, default=lambda: MIRROR_REFERENCE_DATE)


class TrialInquiry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    trial_nct_id = db.Column(db.String(40))
    patient_name = db.Column(db.String(200))
    patient_email = db.Column(db.String(200))
    patient_age = db.Column(db.Integer)
    diagnosis_year = db.Column(db.Integer)
    prior_treatments = db.Column(db.Text, default="")
    eligible_screen = db.Column(db.String(20), default="pending")  # eligible / not-eligible / pending
    status = db.Column(db.String(40), default="received")
    confirmation_code = db.Column(db.String(40))
    created_at = db.Column(db.DateTime, default=lambda: MIRROR_REFERENCE_DATE)


class PortalMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    direction = db.Column(db.String(10))  # to_provider / to_patient
    provider_name = db.Column(db.String(200))
    subject = db.Column(db.String(200))
    body = db.Column(db.Text)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=lambda: MIRROR_REFERENCE_DATE)


class PrescriptionRefill(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    drug_slug = db.Column(db.String(140))
    drug_name = db.Column(db.String(200))
    pharmacy = db.Column(db.String(200))
    status = db.Column(db.String(40), default="submitted")
    confirmation_code = db.Column(db.String(40))
    requested_at = db.Column(db.DateTime, default=lambda: MIRROR_REFERENCE_DATE)


class ProviderMessage(db.Model):
    """Patient-portal message sent to a provider (POST handler)."""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    doctor_slug = db.Column(db.String(140))
    subject = db.Column(db.String(200))
    body = db.Column(db.Text)
    confirmation_code = db.Column(db.String(40))
    created_at = db.Column(db.DateTime, default=lambda: MIRROR_REFERENCE_DATE)


class ShareEvent(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    article_slug = db.Column(db.String(140))
    article_kind = db.Column(db.String(20))
    sender_email = db.Column(db.String(200))
    recipient_email = db.Column(db.String(200))
    note = db.Column(db.Text, default="")
    created_at = db.Column(db.DateTime, default=lambda: MIRROR_REFERENCE_DATE)


class GlossaryFeedback(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    term_slug = db.Column(db.String(140))
    suggestion = db.Column(db.Text)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: MIRROR_REFERENCE_DATE)


class ChatMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    session_token = db.Column(db.String(60))
    sender = db.Column(db.String(20))  # patient / mayo
    body = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=lambda: MIRROR_REFERENCE_DATE)


@login_manager.user_loader
def load_user(uid):
    return db.session.get(User, int(uid))


@app.before_request
def auto_login():
    """Always serve as alice — no real auth needed in this benchmark environment."""
    if request.endpoint and request.endpoint.startswith("logout"):
        return
    if not current_user.is_authenticated:
        alice = User.query.filter_by(email="alice.j@test.com").first()
        if alice:
            login_user(alice)


@app.context_processor
def inject_globals():
    return {
        "letters": list(string.ascii_uppercase),
        "now_year": MIRROR_REFERENCE_DATE.year,
        "mirror_date": MIRROR_REFERENCE_DATE.strftime("%B %d, %Y"),
        "all_departments_nav": Department.query.order_by(Department.name).limit(8).all(),
    }


# ---------------------------------------------------------------------------
# Static asset helpers
# ---------------------------------------------------------------------------
def _list_images(subdir):
    """Return a sorted list of image filenames under static/images/<subdir>/."""
    p = os.path.join(BASE_DIR, "static", "images", subdir)
    if not os.path.isdir(p):
        return []
    return sorted(f for f in os.listdir(p)
                  if os.path.isfile(os.path.join(p, f)) and not f.startswith("."))


def deterministic_image(subdir, key):
    """Pick a stable image from subdir for a given string key."""
    items = _list_images(subdir)
    if not items:
        return None
    h = int(hashlib.md5((key or "").encode()).hexdigest(), 16)
    return f"images/{subdir}/{items[h % len(items)]}"


@app.context_processor
def inject_image_helpers():
    return {
        "pick_image": deterministic_image,
        "list_images": _list_images,
    }


# ---------------------------------------------------------------------------
# Public routes
# ---------------------------------------------------------------------------
@app.route("/")
def index():
    featured_conditions = Condition.query.filter(
        Condition.slug.in_(["diabetes-type-2", "heart-attack", "depression", "asthma", "migraine", "alzheimers-disease"])
    ).all()
    featured_articles = Article.query.filter_by(kind="lifestyle").limit(6).all()
    featured_trials = ClinicalTrial.query.limit(3).all()
    latest_news = Article.query.filter_by(kind="news").order_by(Article.id.desc()).limit(4).all()
    return render_template("index.html",
                           featured_conditions=featured_conditions,
                           featured_articles=featured_articles,
                           featured_trials=featured_trials,
                           latest_news=latest_news)


# --- Diseases & Conditions ---
@app.route("/diseases-conditions")
def diseases_index():
    letter = (request.args.get("letter") or "").upper()
    q = Condition.query.order_by(Condition.name)
    if letter and len(letter) == 1 and letter in string.ascii_uppercase:
        q = q.filter(Condition.name.startswith(letter))
    conditions = q.all()
    return render_template("diseases_index.html", conditions=conditions, active_letter=letter)


@app.route("/diseases-conditions/<slug>")
def condition_detail(slug):
    cond = Condition.query.filter_by(slug=slug).first_or_404()
    dept = Department.query.filter_by(slug=cond.primary_dept_slug).first()
    proc_slugs = [s for s in (cond.related_procedures or "").split(",") if s]
    drug_slugs = [s for s in (cond.related_drugs or "").split(",") if s]
    related_procs = Procedure.query.filter(Procedure.slug.in_(proc_slugs)).all()
    related_drugs = Drug.query.filter(Drug.slug.in_(drug_slugs)).all()
    # Doctors who treat this condition: any doctor in primary department
    doctors = Doctor.query.filter_by(dept_slug=cond.primary_dept_slug).limit(6).all()
    related_conditions = Condition.query.filter(
        Condition.primary_dept_slug == cond.primary_dept_slug,
        Condition.id != cond.id,
    ).limit(6).all()
    return render_template("condition_detail.html",
                           cond=cond, dept=dept,
                           related_procs=related_procs, related_drugs=related_drugs,
                           doctors=doctors, related_conditions=related_conditions)


# --- Symptoms ---
@app.route("/symptoms")
def symptoms_index():
    letter = (request.args.get("letter") or "").upper()
    q = Symptom.query.order_by(Symptom.name)
    if letter and len(letter) == 1:
        q = q.filter(Symptom.name.startswith(letter))
    symptoms = q.all()
    return render_template("symptoms_index.html", symptoms=symptoms, active_letter=letter)


@app.route("/symptoms/<slug>")
def symptom_detail(slug):
    sx = Symptom.query.filter_by(slug=slug).first_or_404()
    rules = SymptomRule.query.filter_by(symptom_slug=slug).order_by(SymptomRule.rank).all()
    return render_template("symptom_detail.html", sx=sx, rules=rules)


# --- Symptom Checker wizard (multi-step) ---
@app.route("/symptom-checker", methods=["GET", "POST"])
def symptom_checker():
    region = request.values.get("region")
    symptom = request.values.get("symptom")
    age_group = request.values.get("age_group")
    duration = request.values.get("duration")

    if not region:
        # Step 1: pick body region
        from content_trials import BODY_REGIONS
        return render_template("symptom_checker_step1.html", regions=BODY_REGIONS, step=1)
    if not symptom:
        # Step 2: pick symptom in region
        sx_list = Symptom.query.filter_by(region=region).order_by(Symptom.name).all()
        return render_template("symptom_checker_step2.html", region=region, symptoms=sx_list, step=2)
    if not age_group:
        return render_template("symptom_checker_step3.html",
                               region=region, symptom=symptom, step=3)
    if not duration:
        return render_template("symptom_checker_step4.html",
                               region=region, symptom=symptom, age_group=age_group, step=4)
    # Step 5: results
    rules = SymptomRule.query.filter_by(symptom_slug=symptom, age_group=age_group, duration=duration).order_by(SymptomRule.rank).all()
    if not rules:
        # Fallback: try age_group=adult duration=any
        rules = SymptomRule.query.filter_by(symptom_slug=symptom).order_by(SymptomRule.rank).all()
    # Cross-link to condition pages where possible
    enriched = []
    for r in rules:
        cond = Condition.query.filter_by(slug=r.condition_slug).first()
        enriched.append((r, cond))
    sx = Symptom.query.filter_by(slug=symptom).first()
    return render_template("symptom_checker_results.html",
                           region=region, symptom=symptom, sx=sx,
                           age_group=age_group, duration=duration,
                           results=enriched, step=5)


# --- Tests & Procedures ---
@app.route("/tests-procedures")
def procedures_index():
    letter = (request.args.get("letter") or "").upper()
    category = request.args.get("category", "")
    q = Procedure.query.order_by(Procedure.name)
    if letter:
        q = q.filter(Procedure.name.startswith(letter))
    if category:
        q = q.filter_by(category=category)
    procs = q.all()
    return render_template("procedures_index.html",
                           procedures=procs, active_letter=letter, category=category)


@app.route("/tests-procedures/<slug>")
def procedure_detail(slug):
    proc = Procedure.query.filter_by(slug=slug).first_or_404()
    dept = Department.query.filter_by(slug=proc.dept_slug).first()
    doctors = Doctor.query.filter_by(dept_slug=proc.dept_slug).limit(5).all()
    related = Procedure.query.filter(
        Procedure.dept_slug == proc.dept_slug,
        Procedure.id != proc.id,
    ).limit(6).all()
    # Conditions that link to this procedure
    related_conds = Condition.query.filter(Condition.related_procedures.contains(slug)).limit(6).all()
    return render_template("procedure_detail.html",
                           proc=proc, dept=dept, doctors=doctors,
                           related_procedures=related, related_conditions=related_conds)


# --- Drugs & Supplements ---
@app.route("/drugs-supplements")
def drugs_index():
    letter = (request.args.get("letter") or "").upper()
    kind = request.args.get("kind", "")
    q = Drug.query.order_by(Drug.name)
    if letter:
        q = q.filter(Drug.name.startswith(letter))
    if kind:
        q = q.filter_by(kind=kind)
    drugs = q.all()
    return render_template("drugs_index.html", drugs=drugs, active_letter=letter, kind=kind)


@app.route("/drugs-supplements/<slug>")
def drug_detail(slug):
    d = Drug.query.filter_by(slug=slug).first_or_404()
    related_conds = Condition.query.filter(Condition.related_drugs.contains(slug)).limit(6).all()
    return render_template("drug_detail.html", drug=d, related_conditions=related_conds)


# --- Departments & Doctors ---
@app.route("/departments-centers")
def departments_index():
    location = request.args.get("location", "")
    q = Department.query.order_by(Department.name)
    if location:
        q = q.filter(Department.locations.contains(location))
    depts = q.all()
    return render_template("departments_index.html", departments=depts, location=location)


@app.route("/departments-centers/<slug>")
def department_detail(slug):
    dept = Department.query.filter_by(slug=slug).first_or_404()
    doctors = Doctor.query.filter_by(dept_slug=slug).all()
    # Conditions/procedures handled by this department
    conditions = Condition.query.filter_by(primary_dept_slug=slug).all()
    procedures = Procedure.query.filter_by(dept_slug=slug).limit(15).all()
    trials = ClinicalTrial.query.join(Doctor, ClinicalTrial.principal_investigator_id == Doctor.id).filter(Doctor.dept_slug == slug).all()
    return render_template("department_detail.html",
                           dept=dept, doctors=doctors,
                           conditions=conditions, procedures=procedures, trials=trials)


@app.route("/find-a-doctor", methods=["GET"])
def find_doctor():
    name_q = request.args.get("q", "").strip()
    specialty = request.args.get("specialty", "")
    location = request.args.get("location", "")
    language = request.args.get("language", "")
    q = Doctor.query.order_by(Doctor.name)
    if specialty:
        q = q.filter(Doctor.dept_slug == specialty)
    if location:
        q = q.filter(Doctor.locations.contains(location))
    if language:
        q = q.filter(Doctor.languages.contains(language))
    docs = q.all()
    if name_q:
        docs = scored_search(name_q, docs, ["name", "specialty", "focus_areas"])
    depts = Department.query.order_by(Department.name).all()
    return render_template("find_doctor.html",
                           doctors=docs, departments=depts,
                           q=name_q, specialty=specialty, location=location, language=language,
                           LOCATIONS=["Rochester", "Jacksonville", "Phoenix"],
                           LANGUAGE_LIST=["English","Spanish","French","German","Mandarin","Cantonese","Arabic","Hindi","Vietnamese","Russian","Portuguese","Italian","Korean","Japanese","Tagalog","Polish"])


@app.route("/biographies/<slug>")
def doctor_detail(slug):
    doc = Doctor.query.filter_by(slug=slug).first_or_404()
    dept = Department.query.filter_by(slug=doc.dept_slug).first()
    # Find conditions the doctor treats (via department)
    conds = Condition.query.filter_by(primary_dept_slug=doc.dept_slug).limit(10).all()
    trials = ClinicalTrial.query.filter_by(principal_investigator_id=doc.id).all()
    return render_template("doctor_detail.html",
                           doc=doc, dept=dept, conditions=conds, trials=trials)


# --- Clinical Trials ---
@app.route("/clinical-trials")
def trials_index():
    keyword = request.args.get("q", "").strip()
    status = request.args.get("status", "")
    phase = request.args.get("phase", "")
    location = request.args.get("location", "")
    q = ClinicalTrial.query.order_by(ClinicalTrial.id)
    if status:
        q = q.filter_by(status=status)
    if phase:
        q = q.filter_by(phase=phase)
    if location:
        q = q.filter(ClinicalTrial.locations.contains(location))
    trials = q.all()
    if keyword:
        trials = scored_search(keyword, trials, ["title", "condition_keyword", "intervention", "brief_summary"])
    return render_template("trials_index.html",
                           trials=trials, q=keyword, status=status, phase=phase, location=location)


@app.route("/clinical-trials/<nct_id>")
def trial_detail(nct_id):
    t = ClinicalTrial.query.filter_by(nct_id=nct_id).first_or_404()
    return render_template("trial_detail.html", trial=t)


# --- Healthy Lifestyle ---
@app.route("/healthy-lifestyle")
def lifestyle_index():
    category = request.args.get("category", "")
    q = Article.query.filter_by(kind="lifestyle")
    if category:
        q = q.filter_by(category=category)
    articles = q.order_by(Article.title).all()
    categories = sorted({a.category for a in Article.query.filter_by(kind="lifestyle").all()})
    return render_template("lifestyle_index.html",
                           articles=articles, categories=categories, category=category)


@app.route("/healthy-lifestyle/<slug>")
def lifestyle_detail(slug):
    a = Article.query.filter_by(slug=slug, kind="lifestyle").first_or_404()
    related = Article.query.filter(Article.kind == "lifestyle", Article.category == a.category, Article.id != a.id).limit(4).all()
    return render_template("article_detail.html", article=a, related=related, back_label="Healthy Lifestyle", back_url=url_for("lifestyle_index"))


# --- News ---
@app.route("/news")
def news_index():
    items = Article.query.filter_by(kind="news").order_by(Article.id.desc()).all()
    return render_template("news_index.html", articles=items)


@app.route("/news/<slug>")
def news_detail(slug):
    a = Article.query.filter_by(slug=slug, kind="news").first_or_404()
    related = Article.query.filter(Article.kind == "news", Article.id != a.id).limit(4).all()
    return render_template("article_detail.html", article=a, related=related, back_label="News", back_url=url_for("news_index"))


# --- Patient Stories ---
@app.route("/patient-stories")
def stories_index():
    items = Article.query.filter_by(kind="story").order_by(Article.title).all()
    return render_template("stories_index.html", articles=items)


@app.route("/patient-stories/<slug>")
def story_detail(slug):
    a = Article.query.filter_by(slug=slug, kind="story").first_or_404()
    related = Article.query.filter(Article.kind == "story", Article.id != a.id).limit(4).all()
    return render_template("article_detail.html", article=a, related=related, back_label="Patient Stories", back_url=url_for("stories_index"))


# --- Request Appointment (multi-step) ---
@app.route("/appointments", methods=["GET"])
def appointments_landing():
    depts = Department.query.order_by(Department.name).all()
    return render_template("appointments_landing.html", departments=depts)


@app.route("/appointments/request", methods=["GET", "POST"])
def request_appointment():
    step = int(request.values.get("step", 1))
    sd = session.setdefault("appt_request", {})

    if request.method == "POST":
        # update state
        for k in ("dept", "location", "preferred_date", "patient_name",
                  "patient_email", "patient_phone", "reason", "insurance", "new_or_returning"):
            v = request.form.get(k)
            if v is not None:
                sd[k] = v
        session.modified = True
        next_step = int(request.form.get("next_step", step + 1))
        if next_step >= 5:
            # finalize
            code = "MAYO-" + hashlib.md5(
                (sd.get("patient_email", "") + sd.get("preferred_date", "")).encode()
            ).hexdigest()[:8].upper()
            ar = AppointmentRequest(
                user_id=current_user.id if current_user.is_authenticated else None,
                dept_slug=sd.get("dept", ""),
                location=sd.get("location", "Rochester"),
                preferred_date=sd.get("preferred_date", ""),
                patient_name=sd.get("patient_name", ""),
                patient_email=sd.get("patient_email", ""),
                patient_phone=sd.get("patient_phone", ""),
                reason=sd.get("reason", ""),
                insurance=sd.get("insurance", ""),
                new_or_returning=sd.get("new_or_returning", "new"),
                confirmation_code=code,
            )
            db.session.add(ar)
            db.session.commit()
            confirmation = {"code": code, **sd}
            session.pop("appt_request", None)
            return render_template("appointment_confirmation.html", confirmation=confirmation)
        return redirect(url_for("request_appointment", step=next_step))

    depts = Department.query.order_by(Department.name).all()
    return render_template("appointment_request.html",
                           step=step, state=sd, departments=depts,
                           locations=["Rochester", "Jacksonville", "Phoenix"])


# --- Search ---
@app.route("/search")
def search():
    q = request.args.get("q", "").strip()
    if not q:
        return render_template("search.html", q="", results={})
    conds = scored_search(q, Condition.query.all(), ["name", "summary", "overview"])[:15]
    procs = scored_search(q, Procedure.query.all(), ["name", "summary"])[:15]
    drugs = scored_search(q, Drug.query.all(), ["name", "treats", "description"])[:15]
    docs = scored_search(q, Doctor.query.all(), ["name", "specialty", "focus_areas"])[:15]
    arts = scored_search(q, Article.query.all(), ["title", "summary", "body"])[:10]
    trials = scored_search(q, ClinicalTrial.query.all(), ["title", "condition_keyword", "brief_summary"])[:8]
    results = {"Conditions": conds, "Tests & Procedures": procs, "Drugs & Supplements": drugs,
               "Doctors": docs, "Articles": arts, "Clinical Trials": trials}
    total = sum(len(v) for v in results.values())
    return render_template("search.html", q=q, results=results, total=total)


@app.route("/api/autocomplete")
def autocomplete():
    q = (request.args.get("q") or "").lower().strip()
    if len(q) < 2:
        return jsonify([])
    suggestions = []
    for c in Condition.query.all():
        if q in c.name.lower():
            suggestions.append({"label": c.name, "kind": "Condition", "url": url_for("condition_detail", slug=c.slug)})
            if len(suggestions) >= 10: break
    for d in Drug.query.all():
        if q in d.name.lower() and len(suggestions) < 10:
            suggestions.append({"label": d.name, "kind": "Drug", "url": url_for("drug_detail", slug=d.slug)})
    for p in Procedure.query.all():
        if q in p.name.lower() and len(suggestions) < 12:
            suggestions.append({"label": p.name, "kind": "Procedure", "url": url_for("procedure_detail", slug=p.slug)})
    return jsonify(suggestions[:12])


# --- Static / About pages ---
@app.route("/about-mayo-clinic")
def about():
    return render_template("about.html")


@app.route("/locations")
def locations():
    return render_template("locations.html")


@app.route("/careers")
def careers():
    return render_template("careers.html")


@app.route("/education")
def education():
    return render_template("education.html")


@app.route("/contact")
def contact():
    return render_template("contact.html")


@app.route("/sitemap")
def sitemap():
    return render_template("sitemap.html",
                           cond_count=Condition.query.count(),
                           proc_count=Procedure.query.count(),
                           drug_count=Drug.query.count(),
                           dept_count=Department.query.count(),
                           doc_count=Doctor.query.count(),
                           trial_count=ClinicalTrial.query.count(),
                           article_count=Article.query.count())


# --- Auth & Patient portal ---
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        u = User.query.filter_by(email=email).first()
        if u and bcrypt.check_password_hash(u.password_hash, request.form.get("password", "")):
            login_user(u)
            return redirect(url_for("patient_portal"))
        flash("Invalid credentials. Use any of the seeded benchmark accounts.", "error")
    return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        if User.query.filter_by(email=email).first():
            flash("That email is already registered.", "error")
            return render_template("register.html")
        u = User(
            username=(request.form.get("username") or email.split("@")[0]).strip(),
            email=email,
            display_name=request.form.get("display_name") or "Patient",
            password_hash=bcrypt.generate_password_hash(request.form.get("password", "TestPass123!")).decode(),
        )
        db.session.add(u)
        db.session.commit()
        login_user(u)
        return redirect(url_for("patient_portal"))
    return render_template("register.html")


@app.route("/logout")
def logout():
    logout_user()
    return redirect(url_for("index"))


@app.route("/patient-portal")
def patient_portal():
    if not current_user.is_authenticated:
        return redirect(url_for("login"))
    apps_ = AppointmentRequest.query.filter_by(user_id=current_user.id).order_by(AppointmentRequest.id.desc()).all()
    saved = SavedItem.query.filter_by(user_id=current_user.id).order_by(SavedItem.saved_at.desc()).all()
    return render_template("patient_portal.html", appointments=apps_, saved=saved, user=current_user)


# --- POST interactions ---
@app.route("/save", methods=["POST"])
def save_item():
    if not current_user.is_authenticated:
        return redirect(url_for("login"))
    kind = request.form.get("kind")
    slug = request.form.get("slug")
    title = request.form.get("title", slug)
    existing = SavedItem.query.filter_by(user_id=current_user.id, kind=kind, slug=slug).first()
    if not existing:
        db.session.add(SavedItem(user_id=current_user.id, kind=kind, slug=slug, title=title))
        db.session.commit()
    return redirect(request.form.get("next") or request.referrer or url_for("patient_portal"))


@app.route("/unsave", methods=["POST"])
def unsave_item():
    if not current_user.is_authenticated:
        return redirect(url_for("login"))
    SavedItem.query.filter_by(user_id=current_user.id, kind=request.form.get("kind"), slug=request.form.get("slug")).delete()
    db.session.commit()
    return redirect(request.referrer or url_for("patient_portal"))


@app.route("/newsletter", methods=["POST"])
def newsletter():
    email = request.form.get("email", "").strip()
    topic = request.form.get("topic", "general")
    if email:
        db.session.add(NewsletterSignup(email=email, topic=topic))
        db.session.commit()
        flash("You're subscribed. Watch for our weekly Mayo Clinic newsletter.", "success")
    return redirect(request.referrer or url_for("index"))


@app.route("/feedback", methods=["POST"])
def feedback():
    helpful = request.form.get("helpful", "yes") == "yes"
    db.session.add(ArticleFeedback(
        article_slug=request.form.get("slug"),
        article_kind=request.form.get("kind"),
        helpful=helpful,
        user_id=current_user.id if current_user.is_authenticated else None,
    ))
    db.session.commit()
    flash("Thank you for your feedback.", "success")
    return redirect(request.referrer or url_for("index"))


@app.route("/_health")
def health_endpoint():
    return jsonify({"ok": True, "site": "mayo_clinic",
                    "conditions": Condition.query.count(),
                    "procedures": Procedure.query.count(),
                    "drugs": Drug.query.count(),
                    "doctors": Doctor.query.count(),
                    "trials": ClinicalTrial.query.count(),
                    "departments": Department.query.count(),
                    "articles": Article.query.count()})


# ---------------------------------------------------------------------------
# Patient Care & Health Info hub
# ---------------------------------------------------------------------------
@app.route("/patient-care-health-info")
@app.route("/patient-care")
def patient_care_hub():
    return render_template("patient_care_hub.html",
                           cond_count=Condition.query.count(),
                           proc_count=Procedure.query.count(),
                           drug_count=Drug.query.count(),
                           doc_count=Doctor.query.count())


# --- Body Systems browse ---
from content_extra import (
    GLOSSARY, BODY_SYSTEMS, CANCER_TYPES, LIFESTYLE_HUBS, CAMPUSES,
    CAREERS_POSTINGS, EDUCATION_PROGRAMS, RESEARCH_AREAS,
)  # noqa: E402

BODY_SYS_LOOKUP = {bs[0]: bs for bs in BODY_SYSTEMS}
CANCER_LOOKUP = {ct[0]: ct for ct in CANCER_TYPES}
HUB_LOOKUP = {h[0]: h for h in LIFESTYLE_HUBS}
CAMPUS_LOOKUP = {c["slug"]: c for c in CAMPUSES}


@app.route("/conditions-by-body-system")
def body_systems_index():
    return render_template("body_systems_index.html", body_systems=BODY_SYSTEMS)


@app.route("/conditions-by-body-system/<slug>")
def body_system_detail(slug):
    bs = BODY_SYS_LOOKUP.get(slug)
    if not bs:
        abort(404)
    system_slug, name, desc, dept_slugs, condition_names = bs
    conditions = Condition.query.filter(Condition.name.in_(condition_names)).order_by(Condition.name).all()
    departments = Department.query.filter(Department.slug.in_(dept_slugs)).all()
    doctors = Doctor.query.filter(Doctor.dept_slug.in_(dept_slugs)).limit(12).all()
    procedures = Procedure.query.filter(Procedure.dept_slug.in_(dept_slugs)).limit(20).all()
    return render_template("body_system_detail.html",
                           system_slug=system_slug, name=name, desc=desc,
                           conditions=conditions, departments=departments,
                           doctors=doctors, procedures=procedures)


# --- Cancer Center hub ---
@app.route("/cancer-center")
def cancer_center():
    cancer_dept = Department.query.filter_by(slug="oncology").first()
    radonc_dept = Department.query.filter_by(slug="radiation-oncology").first()
    onco_docs = Doctor.query.filter(Doctor.dept_slug.in_(["oncology", "radiation-oncology", "hematology"])).limit(10).all()
    trials = ClinicalTrial.query.filter(ClinicalTrial.condition_keyword.like("%cancer%")).limit(10).all()
    return render_template("cancer_center.html",
                           cancer_types=CANCER_TYPES, dept=cancer_dept, radonc=radonc_dept,
                           doctors=onco_docs, trials=trials)


@app.route("/cancer-center/<slug>")
def cancer_type_detail(slug):
    ct = CANCER_LOOKUP.get(slug)
    if not ct:
        abort(404)
    short, name, condition_slug, blurb = ct
    cond = Condition.query.filter_by(slug=condition_slug).first()
    related_conditions = Condition.query.filter(Condition.name.like(f"%{name.split()[0]}%")).limit(8).all()
    related_trials = ClinicalTrial.query.filter(
        (ClinicalTrial.title.like(f"%{name.split()[0]}%")) | (ClinicalTrial.condition_keyword.like(f"%{name.split()[0].lower()}%"))
    ).limit(6).all()
    doctors = Doctor.query.filter(Doctor.dept_slug.in_(["oncology", "radiation-oncology", "hematology", "general-surgery"])).limit(8).all()
    related_procedures = Procedure.query.filter(Procedure.name.like(f"%{name.split()[0]}%")).limit(8).all()
    return render_template("cancer_type_detail.html",
                           ct=ct, name=name, blurb=blurb, cond=cond,
                           related_conditions=related_conditions, related_trials=related_trials,
                           doctors=doctors, related_procedures=related_procedures)


# --- Lifestyle sub-hubs ---
@app.route("/healthy-lifestyle-hub/<hub>")
def lifestyle_hub(hub):
    h = HUB_LOOKUP.get(hub)
    if not h:
        abort(404)
    slug, name, blurb = h
    # Map hub slug -> article category name (case-insensitive contains)
    keyword_map = {
        "nutrition": "Nutrition",
        "fitness": "Fitness",
        "stress": "Stress",
        "adult-health": "Adult Health",
        "childrens-health": "Children's Health",
        "womens-health": "Women's Health",
        "mens-health": "Men's Health",
        "healthy-aging": "Healthy Aging",
        "sleep": "Stress",  # sleep articles tagged under Stress
        "weight-loss": "Nutrition",
        "pregnancy": "Women's Health",
        "sexual-health": "Adult Health",
    }
    category = keyword_map.get(slug, name)
    articles = Article.query.filter_by(kind="lifestyle", category=category).all()
    related_hubs = [h2 for h2 in LIFESTYLE_HUBS if h2[0] != slug][:6]
    return render_template("lifestyle_hub.html",
                           hub_slug=slug, hub_name=name, blurb=blurb,
                           articles=articles, hubs=LIFESTYLE_HUBS, related_hubs=related_hubs)


# --- Locations / Campuses ---
@app.route("/locations/<slug>")
def location_detail(slug):
    c = CAMPUS_LOOKUP.get(slug)
    if not c:
        abort(404)
    # Departments + doctors at this campus
    location_name = {"rochester": "Rochester", "jacksonville": "Jacksonville", "phoenix": "Phoenix"}.get(slug, "Rochester")
    dept_count = Department.query.filter(Department.locations.contains(location_name)).count()
    docs = Doctor.query.filter(Doctor.locations.contains(location_name)).limit(15).all()
    return render_template("location_detail.html",
                           c=c, docs=docs, location_name=location_name,
                           dept_count=dept_count, campuses=CAMPUSES)


# --- Glossary ---
@app.route("/glossary")
def glossary_index():
    letter = (request.args.get("letter") or "").upper()
    category = request.args.get("category", "")
    q = GlossaryTerm.query.order_by(GlossaryTerm.term)
    if letter and len(letter) == 1:
        q = q.filter(GlossaryTerm.term.startswith(letter))
    if category:
        q = q.filter_by(category=category)
    terms = q.all()
    categories = sorted({t.category for t in GlossaryTerm.query.all()})
    return render_template("glossary_index.html",
                           terms=terms, categories=categories,
                           active_letter=letter, active_category=category)


@app.route("/glossary/<slug>")
def glossary_detail(slug):
    t = GlossaryTerm.query.filter_by(slug=slug).first_or_404()
    # Related: same category
    related = GlossaryTerm.query.filter(
        GlossaryTerm.category == t.category, GlossaryTerm.id != t.id,
    ).limit(8).all()
    return render_template("glossary_detail.html", term=t, related=related)


# --- Patient & Visitor Info hub + subpages ---
@app.route("/patient-visitor-guide")
def patient_visitor_guide():
    return render_template("patient_visitor_guide.html", campuses=CAMPUSES)


@app.route("/patient-visitor-guide/<topic>")
def patient_visitor_topic(topic):
    topics = {
        "what-to-expect": ("What to Expect at Mayo Clinic", "From check-in to follow-up, here's what your visit looks like."),
        "billing-insurance": ("Billing and Insurance", "Mayo Clinic accepts most insurance plans and Medicare. Financial assistance is available."),
        "financial-assistance": ("Financial Assistance Program", "Mayo Clinic provides charity care and discounted services for eligible patients."),
        "international-patients": ("International Patient Services", "Dedicated coordinators help international patients with scheduling, travel, language, and accommodation."),
        "accommodations": ("Accommodations and Lodging", "On-campus and partner hotels offer patient and family lodging at every Mayo Clinic campus."),
        "dining": ("Dining at Mayo Clinic", "Cafés, cafeterias, and restaurants are available throughout the Mayo Clinic campuses."),
        "parking": ("Parking and Transportation", "Patient parking, valet services, and free shuttle options are available at all campuses."),
        "accessibility": ("Accessibility Services", "Mayo Clinic provides services for patients with disabilities, including wheelchairs, interpreters, and sensory accommodations."),
        "interpreter-services": ("Interpreter Services", "Free interpreter services in more than 100 languages are available 24/7."),
        "support-groups": ("Support Groups", "Patient and family support groups meet across all Mayo Clinic campuses and online."),
    }
    t = topics.get(topic)
    if not t:
        abort(404)
    title, blurb = t
    return render_template("patient_visitor_topic.html",
                           topic_slug=topic, title=title, blurb=blurb,
                           topics=list(topics.items()))


# --- Research & Education hub ---
@app.route("/research-education")
def research_education():
    return render_template("research_education.html",
                           programs=EDUCATION_PROGRAMS,
                           research_areas=RESEARCH_AREAS)


@app.route("/research-education/<slug>")
def education_program_detail(slug):
    # Match by slugified name
    for prog in EDUCATION_PROGRAMS:
        if slugify(prog[0]) == slug:
            return render_template("education_program_detail.html",
                                   program=prog, all_programs=EDUCATION_PROGRAMS)
    abort(404)


# --- Newsroom (extended) ---
@app.route("/newsroom")
def newsroom():
    items = Article.query.filter_by(kind="news").order_by(Article.id.desc()).all()
    return render_template("newsroom.html", articles=items)


# --- Refer-a-Patient (physician portal) ---
@app.route("/refer-a-patient", methods=["GET", "POST"])
def refer_a_patient():
    depts = Department.query.order_by(Department.name).all()
    if request.method == "POST":
        code = "REF-" + hashlib.md5(
            (request.form.get("patient_name", "") + request.form.get("referring_email", "")).encode()
        ).hexdigest()[:8].upper()
        rr = ReferralRequest(
            referring_provider=request.form.get("referring_provider", ""),
            referring_clinic=request.form.get("referring_clinic", ""),
            referring_phone=request.form.get("referring_phone", ""),
            referring_email=request.form.get("referring_email", ""),
            npi=request.form.get("npi", ""),
            patient_name=request.form.get("patient_name", ""),
            patient_dob=request.form.get("patient_dob", ""),
            patient_diagnosis=request.form.get("patient_diagnosis", ""),
            requested_department=request.form.get("requested_department", ""),
            requested_location=request.form.get("requested_location", "Rochester"),
            notes=request.form.get("notes", ""),
            urgency=request.form.get("urgency", "routine"),
            confirmation_code=code,
        )
        db.session.add(rr)
        db.session.commit()
        flash(f"Referral submitted. Confirmation: {code}. A Mayo Clinic coordinator will contact you within one business day.", "success")
        return render_template("refer_a_patient.html", departments=depts, success_code=code)
    return render_template("refer_a_patient.html", departments=depts)


# --- Second Opinion ---
@app.route("/second-opinion", methods=["GET", "POST"])
def second_opinion():
    depts = Department.query.order_by(Department.name).all()
    if request.method == "POST":
        code = "SO-" + hashlib.md5(
            (request.form.get("patient_email", "") + request.form.get("diagnosis", "")).encode()
        ).hexdigest()[:8].upper()
        so = SecondOpinion(
            patient_name=request.form.get("patient_name", ""),
            patient_email=request.form.get("patient_email", ""),
            patient_phone=request.form.get("patient_phone", ""),
            diagnosis=request.form.get("diagnosis", ""),
            current_treatment=request.form.get("current_treatment", ""),
            desired_review=request.form.get("desired_review", ""),
            department_slug=request.form.get("department_slug", ""),
            records_attached=(request.form.get("records_attached") == "yes"),
            confirmation_code=code,
        )
        db.session.add(so)
        db.session.commit()
        flash(f"Second opinion request received. Confirmation: {code}.", "success")
        return render_template("second_opinion.html", departments=depts, success_code=code)
    return render_template("second_opinion.html", departments=depts)


# --- International Patient Inquiry ---
@app.route("/international-services", methods=["GET", "POST"])
def international_services():
    if request.method == "POST":
        code = "INT-" + hashlib.md5(
            (request.form.get("patient_email", "") + request.form.get("country", "")).encode()
        ).hexdigest()[:8].upper()
        ii = InternationalInquiry(
            patient_name=request.form.get("patient_name", ""),
            patient_email=request.form.get("patient_email", ""),
            patient_phone=request.form.get("patient_phone", ""),
            country=request.form.get("country", ""),
            language=request.form.get("language", ""),
            diagnosis=request.form.get("diagnosis", ""),
            travel_dates=request.form.get("travel_dates", ""),
            accommodation=(request.form.get("accommodation") == "yes"),
            translation=(request.form.get("translation") == "yes"),
            confirmation_code=code,
        )
        db.session.add(ii)
        db.session.commit()
        flash(f"International inquiry received. Confirmation: {code}. A coordinator will contact you within 48 hours.", "success")
        return render_template("international_services.html", success_code=code)
    return render_template("international_services.html")


# --- Giving / Donate ---
@app.route("/giving", methods=["GET"])
def giving():
    return render_template("giving.html")


@app.route("/giving/donate", methods=["GET", "POST"])
def donate():
    funds = [
        ("general", "Greatest Need"),
        ("cancer", "Cancer Research"),
        ("heart", "Cardiovascular Research"),
        ("neuroscience", "Neuroscience Research"),
        ("transplant", "Transplant Programs"),
        ("childrens", "Children's Center"),
        ("rare-diseases", "Rare Diseases"),
        ("alzheimer", "Alzheimer's Disease"),
        ("nursing", "Nursing Education"),
        ("alix-school", "Mayo Clinic Alix School of Medicine"),
    ]
    if request.method == "POST":
        try:
            amount = int(request.form.get("amount", "0").replace(",", "").replace("$", ""))
        except ValueError:
            amount = 0
        code = "GIFT-" + hashlib.md5(
            (request.form.get("donor_email", "") + str(amount)).encode()
        ).hexdigest()[:8].upper()
        d = Donation(
            donor_name=request.form.get("donor_name", "Anonymous"),
            donor_email=request.form.get("donor_email", ""),
            amount=amount,
            frequency=request.form.get("frequency", "one-time"),
            fund=request.form.get("fund", "general"),
            dedication=request.form.get("dedication", ""),
            is_anonymous=(request.form.get("is_anonymous") == "yes"),
            confirmation_code=code,
        )
        db.session.add(d)
        db.session.commit()
        flash(f"Thank you for your gift of ${amount:,}. Confirmation: {code}.", "success")
        return render_template("donate.html", funds=funds, success_code=code, donation=d)
    return render_template("donate.html", funds=funds)


# --- Careers ---
@app.route("/careers/jobs")
def careers_jobs():
    category = request.args.get("category", "")
    location = request.args.get("location", "")
    keyword = (request.args.get("q") or "").strip().lower()
    rows = list(CAREERS_POSTINGS)
    if category:
        rows = [r for r in rows if r[1] == category]
    if location:
        rows = [r for r in rows if r[2] == location]
    if keyword:
        rows = [r for r in rows if keyword in r[0].lower()]
    categories = sorted({r[1] for r in CAREERS_POSTINGS})
    locations_set = sorted({r[2] for r in CAREERS_POSTINGS})
    return render_template("careers_jobs.html", rows=rows,
                           categories=categories, locations=locations_set,
                           category=category, location=location, q=keyword)


@app.route("/careers/job/<int:idx>")
def career_job_detail(idx):
    if idx < 0 or idx >= len(CAREERS_POSTINGS):
        abort(404)
    job = CAREERS_POSTINGS[idx]
    return render_template("career_job_detail.html", job=job, idx=idx)


@app.route("/careers/apply", methods=["GET", "POST"])
def career_apply():
    job_title = request.values.get("job") or request.form.get("job_title", "")
    if request.method == "POST":
        code = "APP-" + hashlib.md5(
            (request.form.get("applicant_email", "") + (job_title or "")).encode()
        ).hexdigest()[:8].upper()
        try:
            years = int(request.form.get("years_experience", "0"))
        except ValueError:
            years = 0
        ja = JobApplication(
            job_title=job_title,
            applicant_name=request.form.get("applicant_name", ""),
            applicant_email=request.form.get("applicant_email", ""),
            applicant_phone=request.form.get("applicant_phone", ""),
            years_experience=years,
            cover_letter=request.form.get("cover_letter", ""),
            resume_filename=request.form.get("resume_filename", "uploaded_resume.pdf"),
            location_pref=request.form.get("location_pref", ""),
            available_date=request.form.get("available_date", ""),
            confirmation_code=code,
        )
        db.session.add(ja)
        db.session.commit()
        flash(f"Application submitted. Confirmation: {code}.", "success")
        return render_template("career_apply.html", job_title=job_title, success_code=code)
    return render_template("career_apply.html", job_title=job_title)


# --- Clinical trial pre-screening / inquiry ---
@app.route("/clinical-trials/<nct_id>/inquire", methods=["GET", "POST"])
def trial_inquire(nct_id):
    trial = ClinicalTrial.query.filter_by(nct_id=nct_id).first_or_404()
    if request.method == "POST":
        code = "TRIAL-" + hashlib.md5(
            (nct_id + request.form.get("patient_email", "")).encode()
        ).hexdigest()[:8].upper()
        try:
            age = int(request.form.get("patient_age", "0"))
            yr = int(request.form.get("diagnosis_year", "0"))
        except ValueError:
            age, yr = 0, 0
        # Simple eligibility: must be 18-80, diagnosed within last 5 yrs
        eligible = "eligible" if 18 <= age <= 80 and yr >= 2020 else "not-eligible"
        ti = TrialInquiry(
            trial_nct_id=nct_id,
            patient_name=request.form.get("patient_name", ""),
            patient_email=request.form.get("patient_email", ""),
            patient_age=age,
            diagnosis_year=yr,
            prior_treatments=request.form.get("prior_treatments", ""),
            eligible_screen=eligible,
            confirmation_code=code,
        )
        db.session.add(ti)
        db.session.commit()
        return render_template("trial_inquire.html", trial=trial, success_code=code, eligible=eligible)
    return render_template("trial_inquire.html", trial=trial)


# --- A-Z site index ---
@app.route("/site-index")
def site_index():
    letter = (request.args.get("letter") or "").upper()
    # Combine conditions + procedures + drugs + departments + glossary + articles
    entries = []
    for c in Condition.query.all():
        entries.append((c.name, "Condition", url_for("condition_detail", slug=c.slug)))
    for p in Procedure.query.all():
        entries.append((p.name, "Procedure", url_for("procedure_detail", slug=p.slug)))
    for d in Drug.query.all():
        entries.append((d.name, "Drug", url_for("drug_detail", slug=d.slug)))
    for d in Department.query.all():
        entries.append((d.name, "Department", url_for("department_detail", slug=d.slug)))
    for g in GlossaryTerm.query.all():
        entries.append((g.term, "Glossary", url_for("glossary_detail", slug=g.slug)))
    entries.sort(key=lambda x: x[0].upper())
    if letter:
        entries = [e for e in entries if e[0].upper().startswith(letter)]
    return render_template("site_index.html", entries=entries, active_letter=letter)


# --- Symptom Checker body map ---
@app.route("/symptom-checker/body-map")
def body_map():
    # Group symptoms by region
    regions = {}
    for s in Symptom.query.all():
        regions.setdefault(s.region, []).append(s)
    return render_template("body_map.html", regions=regions)


# --- Print-friendly view ---
@app.route("/print/<kind>/<slug>")
def print_view(kind, slug):
    if kind == "condition":
        obj = Condition.query.filter_by(slug=slug).first_or_404()
    elif kind == "procedure":
        obj = Procedure.query.filter_by(slug=slug).first_or_404()
    elif kind == "drug":
        obj = Drug.query.filter_by(slug=slug).first_or_404()
    elif kind == "article":
        obj = Article.query.filter_by(slug=slug).first_or_404()
    elif kind == "glossary":
        obj = GlossaryTerm.query.filter_by(slug=slug).first_or_404()
    else:
        abort(404)
    return render_template("print_view.html", kind=kind, obj=obj)


# --- Find a Doctor advanced ---
@app.route("/find-a-doctor/advanced")
def find_doctor_advanced():
    sub_specialty = request.args.get("sub_specialty", "")
    accepts_new = request.args.get("accepts_new", "")
    telemed = request.args.get("telemed", "")
    name_q = request.args.get("q", "")
    specialty = request.args.get("specialty", "")
    location = request.args.get("location", "")
    language = request.args.get("language", "")
    q = Doctor.query.order_by(Doctor.name)
    if specialty:
        q = q.filter(Doctor.dept_slug == specialty)
    if location:
        q = q.filter(Doctor.locations.contains(location))
    if language:
        q = q.filter(Doctor.languages.contains(language))
    if sub_specialty:
        q = q.filter(Doctor.focus_areas.contains(sub_specialty))
    if accepts_new == "yes":
        q = q.filter(Doctor.accepts_appointments == True)
    docs = q.all()
    if name_q:
        docs = scored_search(name_q, docs, ["name", "specialty", "focus_areas"])
    depts = Department.query.order_by(Department.name).all()
    sub_specs = set()
    for d in Doctor.query.all():
        for f in (d.focus_areas or "").split(","):
            if f.strip():
                sub_specs.add(f.strip())
    return render_template("find_doctor_advanced.html",
                           doctors=docs, departments=depts,
                           q=name_q, specialty=specialty, location=location, language=language,
                           sub_specialty=sub_specialty, accepts_new=accepts_new, telemed=telemed,
                           sub_specs=sorted(sub_specs))


# --- Patient portal extended ---
@app.route("/patient-portal/appointments")
def portal_appointments():
    if not current_user.is_authenticated:
        return redirect(url_for("login"))
    apps_ = AppointmentRequest.query.filter_by(user_id=current_user.id).order_by(AppointmentRequest.id.desc()).all()
    return render_template("portal_appointments.html", appointments=apps_)


@app.route("/patient-portal/messages", methods=["GET", "POST"])
def portal_messages():
    if not current_user.is_authenticated:
        return redirect(url_for("login"))
    if request.method == "POST":
        # Send message to provider
        slug = request.form.get("doctor_slug", "")
        doc = Doctor.query.filter_by(slug=slug).first()
        code = "MSG-" + hashlib.md5(
            (str(current_user.id) + request.form.get("subject", "")).encode()
        ).hexdigest()[:8].upper()
        pm = ProviderMessage(
            user_id=current_user.id,
            doctor_slug=slug,
            subject=request.form.get("subject", ""),
            body=request.form.get("body", ""),
            confirmation_code=code,
        )
        db.session.add(pm)
        db.session.commit()
        flash(f"Message sent to {doc.name if doc else 'provider'}. Confirmation: {code}.", "success")
        return redirect(url_for("portal_messages"))
    sent = ProviderMessage.query.filter_by(user_id=current_user.id).order_by(ProviderMessage.id.desc()).all()
    inbox = PortalMessage.query.filter_by(user_id=current_user.id).order_by(PortalMessage.id.desc()).all()
    docs = Doctor.query.order_by(Doctor.name).limit(50).all()
    return render_template("portal_messages.html", sent=sent, inbox=inbox, doctors=docs)


@app.route("/patient-portal/medications", methods=["GET", "POST"])
def portal_medications():
    if not current_user.is_authenticated:
        return redirect(url_for("login"))
    if request.method == "POST":
        slug = request.form.get("drug_slug", "")
        drug = Drug.query.filter_by(slug=slug).first()
        code = "RX-" + hashlib.md5(
            (str(current_user.id) + slug + request.form.get("pharmacy", "")).encode()
        ).hexdigest()[:8].upper()
        pr = PrescriptionRefill(
            user_id=current_user.id,
            drug_slug=slug,
            drug_name=drug.name if drug else slug,
            pharmacy=request.form.get("pharmacy", "Mayo Clinic Pharmacy"),
            confirmation_code=code,
        )
        db.session.add(pr)
        db.session.commit()
        flash(f"Refill requested. Confirmation: {code}.", "success")
        return redirect(url_for("portal_medications"))
    refills = PrescriptionRefill.query.filter_by(user_id=current_user.id).order_by(PrescriptionRefill.id.desc()).all()
    saved_drugs = SavedItem.query.filter_by(user_id=current_user.id, kind="drug").all()
    return render_template("portal_medications.html", refills=refills, saved_drugs=saved_drugs)


@app.route("/patient-portal/billing")
def portal_billing():
    if not current_user.is_authenticated:
        return redirect(url_for("login"))
    appts = AppointmentRequest.query.filter_by(user_id=current_user.id).all()
    # Synthetic bills from appointments
    bills = []
    for i, a in enumerate(appts, 1):
        bills.append({
            "id": i,
            "date": a.preferred_date,
            "department": a.dept_slug,
            "amount": 480 + (i * 73) % 700,
            "status": "paid" if i % 3 == 0 else "pending",
        })
    return render_template("portal_billing.html", bills=bills)


@app.route("/patient-portal/profile", methods=["GET", "POST"])
def portal_profile():
    if not current_user.is_authenticated:
        return redirect(url_for("login"))
    if request.method == "POST":
        current_user.display_name = request.form.get("display_name", current_user.display_name)
        current_user.date_of_birth = request.form.get("date_of_birth", current_user.date_of_birth)
        current_user.phone = request.form.get("phone", current_user.phone)
        current_user.address = request.form.get("address", current_user.address)
        current_user.preferred_location = request.form.get("preferred_location", current_user.preferred_location)
        db.session.commit()
        flash("Profile updated.", "success")
        return redirect(url_for("portal_profile"))
    return render_template("portal_profile.html", user=current_user)


@app.route("/patient-portal/health-records")
def portal_health_records():
    if not current_user.is_authenticated:
        return redirect(url_for("login"))
    saved_conds = SavedItem.query.filter_by(user_id=current_user.id, kind="condition").all()
    return render_template("portal_health_records.html",
                           conditions=saved_conds, user=current_user)


# --- Share article ---
@app.route("/share", methods=["POST"])
def share_article():
    se = ShareEvent(
        article_slug=request.form.get("slug", ""),
        article_kind=request.form.get("kind", "article"),
        sender_email=request.form.get("sender_email", ""),
        recipient_email=request.form.get("recipient_email", ""),
        note=request.form.get("note", ""),
    )
    db.session.add(se)
    db.session.commit()
    flash(f"Shared with {se.recipient_email}.", "success")
    return redirect(request.referrer or url_for("index"))


# --- Glossary feedback ---
@app.route("/glossary/<slug>/feedback", methods=["POST"])
def glossary_feedback(slug):
    gf = GlossaryFeedback(
        term_slug=slug,
        suggestion=request.form.get("suggestion", ""),
        user_id=current_user.id if current_user.is_authenticated else None,
    )
    db.session.add(gf)
    db.session.commit()
    flash("Thanks — your suggestion has been logged.", "success")
    return redirect(url_for("glossary_detail", slug=slug))


# --- Live chat stub ---
@app.route("/live-chat", methods=["GET", "POST"])
def live_chat():
    token = session.get("chat_token")
    if not token:
        token = hashlib.md5(str(datetime.utcnow()).encode()).hexdigest()[:12]
        session["chat_token"] = token
    if request.method == "POST":
        body = request.form.get("body", "").strip()
        if body:
            db.session.add(ChatMessage(
                user_id=current_user.id if current_user.is_authenticated else None,
                session_token=token, sender="patient", body=body,
            ))
            # Auto-reply
            reply = ("Thank you for contacting Mayo Clinic. A health navigator will respond shortly. "
                     "For medical emergencies, call 911. For appointment requests, please use the Request Appointment form.")
            db.session.add(ChatMessage(
                user_id=current_user.id if current_user.is_authenticated else None,
                session_token=token, sender="mayo", body=reply,
            ))
            db.session.commit()
        return redirect(url_for("live_chat"))
    msgs = ChatMessage.query.filter_by(session_token=token).order_by(ChatMessage.id).all()
    return render_template("live_chat.html", messages=msgs)


# --- About sub-pages ---
@app.route("/about-mayo-clinic/<topic>")
def about_topic(topic):
    pages = {
        "leadership": ("Mayo Clinic Leadership",
                       "President and CEO Gianrico Farrugia, M.D., leads Mayo Clinic together with executive leadership from "
                       "Rochester, Phoenix, and Jacksonville campuses. Mayo Clinic is governed by a Board of Trustees and "
                       "operates as a not-for-profit medical practice and medical research group."),
        "history": ("History of Mayo Clinic",
                    "Mayo Clinic began in 1864 when William Worrall Mayo set up a practice in Rochester, Minnesota. After a "
                    "tornado in 1883, Mother Alfred Moes proposed building a hospital with the Mayo brothers. Saint Marys "
                    "Hospital opened in 1889 and the Mayo Clinic model — multidisciplinary, integrated team-based care — "
                    "grew from there."),
        "accreditation": ("Accreditation and Quality",
                          "Mayo Clinic hospitals are accredited by The Joint Commission and Magnet-recognized for nursing "
                          "excellence. All campuses meet rigorous quality, safety, and patient experience standards."),
        "quality-awards": ("Quality and Awards",
                           "Mayo Clinic has been ranked #1 in the World's Best Hospitals by Newsweek for eight consecutive years and "
                           "consistently appears at the top of U.S. News & World Report's Best Hospitals Honor Roll."),
        "annual-report": ("Annual Report",
                          "Mayo Clinic publishes an annual report covering financial performance, patient outcomes, research "
                          "highlights, and community impact across the three campuses and Mayo Clinic Health System."),
        "diversity-equity-inclusion": ("Diversity, Equity, and Inclusion",
                                       "Mayo Clinic is committed to creating a welcoming environment for patients, staff, and "
                                       "trainees of all backgrounds. The Office of Health Equity, Inclusion, and Community "
                                       "Engagement leads enterprise-wide initiatives."),
        "research-mission": ("Mayo Clinic Research Mission",
                             "Research at Mayo Clinic spans laboratory discovery, translational science, clinical trials, "
                             "and health services research, with the goal of improving care for every patient we serve."),
        "model-of-care": ("The Mayo Clinic Model of Care",
                          "The Mayo Clinic Model of Care places the patient at the center, brings together a multidisciplinary "
                          "team, and supports clinicians with research and education infrastructure."),
    }
    p = pages.get(topic)
    if not p:
        abort(404)
    title, body = p
    return render_template("about_topic.html",
                           topic_slug=topic, title=title, body=body,
                           topics=list(pages.items()))


# ---------------------------------------------------------------------------
# Seed / bootstrap
# ---------------------------------------------------------------------------
# Defer the seed_data import until after all models are defined; avoid circular
# import by binding via sys.modules so seed_data can reach back to us.
import sys as _sys
_sys.modules.setdefault('app', _sys.modules[__name__])
from seed_data import seed_database, seed_benchmark_users  # noqa: E402

with app.app_context():
    db.create_all()
    seed_database()
    seed_benchmark_users()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
