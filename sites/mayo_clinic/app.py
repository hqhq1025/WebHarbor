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
