#!/usr/bin/env python3
"""Coursera.org mirror — Flask application."""
import os, json, re, random, hashlib
from datetime import datetime, timedelta
from functools import wraps

from flask import (Flask, render_template, request, redirect, url_for,
                   flash, jsonify, session, abort, g)
from flask_sqlalchemy import SQLAlchemy
from flask_login import (LoginManager, UserMixin, login_user, logout_user,
                         login_required, current_user)
from flask_wtf import FlaskForm
from flask_wtf.csrf import CSRFProtect, generate_csrf
from flask_bcrypt import Bcrypt
from wtforms import StringField, PasswordField, TextAreaField, SelectField, FloatField
from wtforms.validators import DataRequired, Email, Length, EqualTo, Optional, NumberRange

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__)
app.config['SECRET_KEY'] = 'coursera-mirror-secret-key-2024'
app.config['SQLALCHEMY_DATABASE_URI'] = (
    f"sqlite:///{os.path.join(BASE_DIR, 'instance', 'coursera.db')}")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['WTF_CSRF_TIME_LIMIT'] = None

os.makedirs(os.path.join(BASE_DIR, 'instance'), exist_ok=True)

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please sign in to continue.'
login_manager.login_message_category = 'info'
csrf = CSRFProtect(app)

# ─── Helpers ──────────────────────────────────────────────────────────────────

def _slugify_instructor(name):
    """Convert 'Gautam Kaul' -> 'gautam-kaul' (deterministic, URL-safe)."""
    if not name:
        return ''
    s = re.sub(r'[^a-zA-Z0-9\s]', '', name)
    s = re.sub(r'\s+', '-', s.strip().lower())
    return s

# ─── Models ───────────────────────────────────────────────────────────────────

class User(db.Model, UserMixin):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    name = db.Column(db.String(120), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    enrollments = db.relationship('Enrollment', backref='user', lazy=True, cascade='all, delete-orphan')
    saved_courses = db.relationship('SavedCourse', backref='user', lazy=True, cascade='all, delete-orphan')
    reviews = db.relationship('Review', backref='user', lazy=True, cascade='all, delete-orphan')

    def set_password(self, pw):
        self.password_hash = bcrypt.generate_password_hash(pw).decode('utf-8')

    def check_password(self, pw):
        return bcrypt.check_password_hash(self.password_hash, pw)


class Partner(db.Model):
    __tablename__ = 'partners'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    slug = db.Column(db.String(200), unique=True, nullable=False, index=True)
    country = db.Column(db.String(80), default='United States')
    partner_type = db.Column(db.String(30), default='university')  # university|company|institution
    short_name = db.Column(db.String(80), default='')
    website = db.Column(db.String(200), default='')

    courses = db.relationship('Course', backref='partner', lazy=True)


class Course(db.Model):
    __tablename__ = 'courses'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(300), nullable=False)
    slug = db.Column(db.String(300), unique=True, nullable=False, index=True)
    partner_id = db.Column(db.Integer, db.ForeignKey('partners.id'), nullable=True, index=True)
    course_type = db.Column(db.String(40), default='Course')
    # Course|Specialization|Guided Project|Professional Certificate|Degree
    level = db.Column(db.String(30), default='Beginner', index=True)
    # Beginner|Intermediate|Advanced|Mixed
    category = db.Column(db.String(100), default='')
    subcategory = db.Column(db.String(100), default='')
    duration_text = db.Column(db.String(80), default='Approx. 10 hours')
    duration_weeks = db.Column(db.Float, default=4.0)   # for filtering
    duration_hours = db.Column(db.Float, default=10.0)  # for < N hours filter
    rating = db.Column(db.Float, default=4.6)
    review_count = db.Column(db.Integer, default=1000)
    enrolled_count = db.Column(db.Integer, default=50000)
    is_free = db.Column(db.Boolean, default=False)
    has_certificate = db.Column(db.Boolean, default=True)
    credit_eligible = db.Column(db.Boolean, default=False)
    instructor = db.Column(db.String(200), default='', index=True)
    instructor_title = db.Column(db.String(200), default='')
    description = db.Column(db.Text, default='')
    what_you_learn = db.Column(db.Text, default='[]')   # JSON list
    skills = db.Column(db.Text, default='[]')            # JSON list
    feature_tags = db.Column(db.Text, default='[]')      # JSON list
    is_featured = db.Column(db.Boolean, default=False)
    is_new = db.Column(db.Boolean, default=False)
    sort_date = db.Column(db.String(20), default='2024-01-01')
    # For degrees
    degree_type = db.Column(db.String(40), default='')  # Bachelor|Master|MasterAdvancedStudy
    application_deadline = db.Column(db.String(40), default='')  # e.g. 'March 15, 2026' (degrees only)
    # Course color (for CSS thumbnails)
    color_class = db.Column(db.String(20), default='cat-cs')
    # Learner testimonials shown prominently on course page
    # JSON list of {quote, name, role, date}
    testimonials_json = db.Column(db.Text, default='[]')
    # R5 extension columns — hover preview, recommended textbook, weekly load.
    preview_video_url = db.Column(db.String(300), default='')
    textbook_isbn = db.Column(db.String(40), default='')
    estimated_workload_hours_per_week = db.Column(db.Float, default=4.0)

    enrollments = db.relationship('Enrollment', backref='course', lazy=True, cascade='all, delete-orphan')
    saved_by = db.relationship('SavedCourse', backref='course', lazy=True, cascade='all, delete-orphan')
    reviews = db.relationship('Review', backref='course', lazy=True, cascade='all, delete-orphan')
    modules = db.relationship('CourseModule', backref='course', lazy=True, order_by='CourseModule.week_number', cascade='all, delete-orphan')
    sub_courses = db.relationship('SubCourse', foreign_keys='SubCourse.specialization_id',
                                   backref='specialization', lazy=True, order_by='SubCourse.order_index',
                                   cascade='all, delete-orphan')

    def get_skills(self):
        try:
            return json.loads(self.skills or '[]')
        except Exception:
            return []

    def get_what_you_learn(self):
        try:
            return json.loads(self.what_you_learn or '[]')
        except Exception:
            return []

    def get_feature_tags(self):
        try:
            return json.loads(self.feature_tags or '[]')
        except Exception:
            return []

    def get_testimonials(self):
        try:
            v = json.loads(self.testimonials_json or '[]')
            if isinstance(v, list):
                return v
        except Exception:
            pass
        return []

    def instructor_slug(self):
        return _slugify_instructor(self.instructor or '')

    def enrolled_display(self):
        n = self.enrolled_count or 0
        if n >= 1_000_000:
            return f'{n/1_000_000:.1f}M'
        if n >= 1_000:
            return f'{int(n/1000)}K'
        return str(n)


class CourseModule(db.Model):
    __tablename__ = 'course_modules'
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    week_number = db.Column(db.Integer, default=1)
    title = db.Column(db.String(300), default='')
    description = db.Column(db.Text, default='')
    videos_count = db.Column(db.Integer, default=4)
    readings_count = db.Column(db.Integer, default=3)
    quizzes_count = db.Column(db.Integer, default=1)
    video_titles = db.Column(db.Text, default='[]')  # JSON list of individual video titles

    def get_video_titles(self):
        try:
            titles = json.loads(self.video_titles or '[]')
            if isinstance(titles, list):
                return titles
        except Exception:
            pass
        return []


class SubCourse(db.Model):
    __tablename__ = 'sub_courses'
    id = db.Column(db.Integer, primary_key=True)
    specialization_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=True)
    order_index = db.Column(db.Integer, default=0)
    title = db.Column(db.String(300), default='')
    description = db.Column(db.Text, default='')
    duration_text = db.Column(db.String(80), default='Approx. 8 hours')


class Enrollment(db.Model):
    __tablename__ = 'enrollments'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    enrolled_at = db.Column(db.DateTime, default=datetime.utcnow)
    progress = db.Column(db.Integer, default=0)


class SavedCourse(db.Model):
    __tablename__ = 'saved_courses'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    saved_at = db.Column(db.DateTime, default=datetime.utcnow)


class Review(db.Model):
    __tablename__ = 'reviews'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    rating = db.Column(db.Float, default=5.0)
    body = db.Column(db.Text, default='')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# ─── Forms ────────────────────────────────────────────────────────────────────

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])

class RegisterForm(FlaskForm):
    name = StringField('Full Name', validators=[DataRequired(), Length(2, 100)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired(), Length(8, 100)])
    confirm = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])

class ProfileForm(FlaskForm):
    name = StringField('Full Name', validators=[DataRequired(), Length(2, 100)])
    email = StringField('Email', validators=[DataRequired(), Email()])

class PasswordForm(FlaskForm):
    current_password = PasswordField('Current Password', validators=[DataRequired()])
    new_password = PasswordField('New Password', validators=[DataRequired(), Length(8, 100)])
    confirm = PasswordField('Confirm', validators=[DataRequired(), EqualTo('new_password')])

class ReviewForm(FlaskForm):
    rating = FloatField('Rating', validators=[DataRequired(), NumberRange(1, 5)])
    body = TextAreaField('Review', validators=[DataRequired(), Length(10, 2000)])

# ─── Search helpers ───────────────────────────────────────────────────────────

STOPWORDS = {
    # Articles / prepositions / conjunctions / aux verbs
    'the', 'a', 'an', 'of', 'in', 'on', 'at', 'to', 'for',
    'with', 'and', 'or', 'is', 'are', 'be', 'by', 'from', 'that',
    'this', 'it', 'as', 'we', 'our', 'about', 'how', 'what', 'which',
    'who', 'when', 'where', 'why',
    # Generic "course-ware" words
    'course', 'courses', 'learn', 'learning', 'class', 'classes',
    'online', 'free', 'paid', 'study', 'studies',
    # Filter-dimension words — these belong in URL filters, not in
    # full-text search, otherwise typing "Beginner Spanish Specialization"
    # matches every Beginner Specialization in any subject.
    'beginner', 'intermediate', 'advanced', 'mixed',
    'specialization', 'specializations',
    'certificate', 'certificates', 'professional',
    'guided', 'project', 'projects',
    'degree', 'degrees', 'bachelor', 'master',
    # English / language adjectives that don't disambiguate content
    'level', 'levels', 'rating', 'ratings',
}

# IDF (inverse document frequency) cache, populated lazily on first
# search. Rebuilt automatically when the catalog grows past 110 % of
# the size at last build, so seed expansion stays consistent.
_IDF_CACHE = {'token_df': {}, 'total': 0, 'built_at': 0}

def _build_idf():
    import math
    courses = Course.query.all()
    df = {}
    for c in courses:
        # Mirror the haystack fields used by _score_course
        text = ' '.join([
            (c.title or ''), (c.description or ''),
            (c.skills or ''), (c.feature_tags or ''),
            (c.instructor or ''), (c.partner.name if c.partner else ''),
        ]).lower()
        for w in set(re.findall(r'[a-z0-9\+\#]+', text)):
            df[w] = df.get(w, 0) + 1
    _IDF_CACHE['token_df'] = df
    _IDF_CACHE['total'] = len(courses)
    _IDF_CACHE['built_at'] = len(courses)

def _idf(token):
    import math
    if _IDF_CACHE['total'] == 0:
        return 1.0
    df = _IDF_CACHE['token_df'].get(token, 0)
    # Standard IDF + 1 smoothing; higher = rarer = more discriminative
    return math.log((_IDF_CACHE['total'] + 1) / (df + 1)) + 1.0

_WORD_RE = re.compile(r'[a-z0-9\+\#]+')

def _is_known_word(token):
    """A token is a 'known word' if it appears as a complete word in
    the IDF corpus (any course's title/body). Real complete words like
    'java', 'python', 'spanish' are known. Partial / typo tokens like
    'healthca' or 'phys' are NOT known."""
    return _IDF_CACHE['token_df'].get(token, 0) > 0

def _word_match(token, words):
    """Match strength for `token` against a set of words:
       1.0  exact word-boundary hit                 ('java'  in {java,…})
       0.6  prefix hit, token is NOT a known word   ('healthca' → healthcare)
       0.0  no match.
    Prefix matching only fires when the user typed an incomplete word
    that doesn't itself exist in the corpus — so 'java' never silently
    matches 'javascript' (java IS a known word; user meant java, not
    something it's a prefix of)."""
    if token in words:
        return 1.0
    if len(token) >= 3 and not _is_known_word(token):
        for w in words:
            if w.startswith(token) and len(w) > len(token):
                return 0.6
    return 0.0

def _score_course(c, tokens):
    """IDF-weighted match score with WORD-BOUNDARY + PREFIX matching.
    Title hits weigh 3×, body hits 1×. Rare tokens dominate."""
    title_words = set(_WORD_RE.findall((c.title or '').lower()))
    body_words  = set(_WORD_RE.findall(' '.join([
        (c.description or '').lower(),
        (c.skills or '').lower(),
        (c.feature_tags or '').lower(),
        (c.instructor or '').lower(),
        (c.partner.name if c.partner else '').lower(),
    ])))
    # NOTE: category / subcategory / course_type / level are filter
    # dimensions, NOT search content.
    score = 0.0
    for t in tokens:
        idf = _idf(t)
        m_title = _word_match(t, title_words)
        m_body  = _word_match(t, body_words) if not m_title else 0.0
        if m_title:
            score += idf * 3.0 * m_title
        elif m_body:
            score += idf * m_body
    return score

def search_courses(q='', level=None, course_type=None, duration=None,
                   min_rating=None, free=None, credit=None, certificate=None,
                   category=None, sort='popular'):
    query = Course.query
    text_relevance = {}   # course.id → text_score, drives sort tie-break

    # Text scoring
    if q and q.strip():
        raw_tokens = re.findall(r'[a-z0-9\+\#]+', q.lower())
        tokens = [t for t in raw_tokens if t not in STOPWORDS and len(t) >= 2]
        if not tokens:
            # Query was 100 % stop-words / filter words. Treat as
            # "no text query" — let URL filters do the work.
            courses = query.all()
        else:
            # (Re)build IDF if catalog grew significantly
            if (_IDF_CACHE['total'] == 0 or
                Course.query.count() > _IDF_CACHE['built_at'] * 1.1):
                _build_idf()
            all_courses = query.all()
            # Pick the rarest GATE token from those that actually exist
            # in the corpus (df > 0) OR that have a prefix expansion
            # landing on a real word. Tokens that are pure typos /
            # filler ("subject", "today", "curriculum") have df=0 and
            # no useful prefix — they should NOT gate the search,
            # otherwise "Physical Science and Engineering subject"
            # returns 0 just because no course text contains "subject".
            def _has_any_corpus_hit(t):
                if _IDF_CACHE['token_df'].get(t, 0) > 0:
                    return True
                if len(t) >= 3 and not _is_known_word(t):
                    for w in _IDF_CACHE['token_df'].keys():
                        if w.startswith(t) and len(w) > len(t):
                            return True
                return False
            # Gate must have df ≥ 2: tokens that appear in only ONE
            # course are noise (e.g. "today" might appear once in a
            # Modern Art description) — using them as the gate would
            # return only that one course.
            gate_candidates = [t for t in tokens
                               if _IDF_CACHE['token_df'].get(t, 0) >= 2]
            if not gate_candidates:
                # No high-quality gate token. Fall back to any df>0 token
                # then to any prefix-matchable token, then drop the gate.
                gate_candidates = [t for t in tokens
                                   if _IDF_CACHE['token_df'].get(t, 0) > 0]
            if not gate_candidates:
                gate_candidates = [t for t in tokens if _has_any_corpus_hit(t)]
            # Drop OOV-no-hit tokens from scoring too (they contribute 0).
            tokens = [t for t in tokens if _has_any_corpus_hit(t)] or tokens
            # Hard requirement: the RAREST gate token must appear in
            # title or body. This is what stops "Beginner Spanish
            # Specialization" from matching every Beginner Specialization
            # — Spanish is the rare token, and a Python course doesn't
            # contain it.
            if not gate_candidates:
                # No discriminative token at all (entire query meaningless).
                return []
            rarest = max(gate_candidates, key=_idf)
            scored = []
            for c in all_courses:
                s = _score_course(c, tokens)
                if s <= 0:
                    continue
                title_w = set(_WORD_RE.findall((c.title or '').lower()))
                body_w  = set(_WORD_RE.findall(' '.join([
                    (c.description or '').lower(),
                    (c.skills or '').lower(),
                    (c.feature_tags or '').lower(),
                    (c.instructor or '').lower(),
                    (c.partner.name if c.partner else '').lower(),
                ])))
                # Rarest token must hit (exact or as a prefix of an
                # existing word). This is what stops `q=spanish` from
                # matching Beginner Python Specialization.
                if (_word_match(rarest, title_w) == 0.0 and
                    _word_match(rarest, body_w)  == 0.0):
                    continue
                scored.append((s, c))
                text_relevance[c.id] = s
            scored.sort(key=lambda x: -x[0])
            if not scored:
                return []
            courses = [c for _, c in scored]
    else:
        courses = query.all()

    # Filters
    if level:
        courses = [c for c in courses if c.level and c.level.lower() == level.lower()]
    if course_type:
        courses = [c for c in courses if c.course_type and
                   c.course_type.lower() == course_type.lower()]
    if duration:
        if duration == '1-4_weeks':
            courses = [c for c in courses if c.duration_weeks and c.duration_weeks <= 4]
        elif duration == '1-3_months':
            courses = [c for c in courses if c.duration_weeks and 4 < c.duration_weeks <= 13]
        elif duration == '3-6_months':
            courses = [c for c in courses if c.duration_weeks and 13 < c.duration_weeks <= 26]
        elif duration == '6plus_months':
            courses = [c for c in courses if c.duration_weeks and 26 < c.duration_weeks < 52]
        elif duration == '1-4_years' or duration == '1-4 Years':
            # Matches specializations / degrees running one year or more
            courses = [c for c in courses if c.duration_weeks and c.duration_weeks >= 52]
        elif duration == 'less_2_hours':
            courses = [c for c in courses if c.duration_hours and c.duration_hours < 2]
    if min_rating:
        try:
            mr = float(min_rating)
            courses = [c for c in courses if c.rating and c.rating >= mr]
        except (ValueError, TypeError):
            pass
    if free == '1' or free is True:
        courses = [c for c in courses if c.is_free]
    if credit == '1' or credit is True:
        courses = [c for c in courses if c.credit_eligible]
    if certificate == '1' or certificate is True:
        courses = [c for c in courses if c.has_certificate]
    if category:
        courses = [c for c in courses if category.lower() in (c.category or '').lower()]

    # Sort
    # Key insight: when there's a text query, relevance is the PRIMARY
    # sort key — the chosen `sort` becomes a tiebreaker among similarly-
    # relevant results. Otherwise typing "spanish" returns Python
    # courses just because they have higher enrolled_count.
    if text_relevance:
        if sort == 'newest':
            tie = lambda c: c.sort_date or '2000-01-01'
            courses.sort(key=lambda c: (-text_relevance.get(c.id, 0), tie(c)),
                         reverse=False)
            # `newest` wants tie DESC, but reverse flips both — handle separately
            courses.sort(key=lambda c: (text_relevance.get(c.id, 0),
                                        c.sort_date or '2000-01-01'),
                         reverse=True)
        elif sort == 'rating':
            courses.sort(key=lambda c: (text_relevance.get(c.id, 0),
                                        c.rating or 0),
                         reverse=True)
        else:   # 'popular' (default) or unknown
            courses.sort(key=lambda c: (text_relevance.get(c.id, 0),
                                        c.enrolled_count or 0),
                         reverse=True)
    else:
        if sort == 'newest':
            courses.sort(key=lambda c: c.sort_date or '2000-01-01', reverse=True)
        elif sort == 'rating':
            courses.sort(key=lambda c: c.rating or 0, reverse=True)
        elif sort == 'popular':
            courses.sort(key=lambda c: c.enrolled_count or 0, reverse=True)

    return courses

# ─── Login loader ─────────────────────────────────────────────────────────────

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

# ─── Context processor ───────────────────────────────────────────────────────

# ─── Image asset helpers ──────────────────────────────────────────────────────

_IMG_MANIFEST_CACHE = None
_IMG_DIR = os.path.join(BASE_DIR, 'static', 'images')
_COURSE_TAGS_CACHE = None

# Maps the human-readable category name stored on Course.category to the
# slug used in static/images/_course_image_tags.json.
_CATEGORY_NAME_TO_SLUG = {
    'Computer Science': 'computer-science',
    'Data Science': 'data-science',
    'Information Technology': 'information-technology',
    'Business': 'business',
    'Language Learning': 'language-learning',
    'Math and Logic': 'math-logic',
    'Physical Science and Engineering': 'physical-science',
    'Social Sciences': 'social-sciences',
    'Arts and Humanities': 'arts-humanities',
    'Health': 'health',
    'Personal Development': 'personal-development',
}

def _img_manifest():
    """Lazy-load static/images/_manifest.json. Returns dict with keys
    `logo, hero_home, hero, partners, courses, categories, instructors,
     badges, social, plus_logo`. Empty dict if not present."""
    global _IMG_MANIFEST_CACHE
    if _IMG_MANIFEST_CACHE is None:
        path = os.path.join(_IMG_DIR, '_manifest.json')
        try:
            with open(path) as f:
                _IMG_MANIFEST_CACHE = json.load(f)
        except (OSError, ValueError):
            _IMG_MANIFEST_CACHE = {}
    return _IMG_MANIFEST_CACHE

def _course_image_tags():
    """Lazy-load static/images/_course_image_tags.json — the per-image topic
    tags used to pick a visually appropriate course thumbnail. Empty dict if
    not present."""
    global _COURSE_TAGS_CACHE
    if _COURSE_TAGS_CACHE is None:
        path = os.path.join(_IMG_DIR, '_course_image_tags.json')
        try:
            with open(path) as f:
                _COURSE_TAGS_CACHE = json.load(f)
        except (OSError, ValueError):
            _COURSE_TAGS_CACHE = {}
    return _COURSE_TAGS_CACHE

def _stable_pick(seed, items):
    """Deterministically pick one item from the pool by hashing `seed`."""
    if not items:
        return None
    h = int(hashlib.md5(str(seed).encode('utf-8')).hexdigest()[:8], 16)
    return items[h % len(items)]

def _slugify_partner(name):
    s = (name or '').lower()
    # Normalise common partner-name patterns to match scraper slugs
    s = s.replace('university of ', '').replace('the ', '')
    s = re.sub(r'[^a-z0-9]+', '-', s).strip('-')
    aliases = {
        'university-michigan':'michigan', 'michigan-ann-arbor':'michigan',
        'colorado-system':'colorado-boulder', 'colorado':'colorado-boulder',
        'pennsylvania-state-university':'pennsylvania', 'pennsylvania':'pennsylvania',
        'penn':'pennsylvania', 'upenn':'pennsylvania',
        'illinois-urbana-champaign':'illinois', 'illinois':'illinois',
        'imperial-college':'imperial-college-london',
        'johns-hopkins-university':'johns-hopkins',
        'deeplearning':'deeplearning-ai',
        'amazon-web-services':'aws', 'amazon':'aws',
        'meta-platforms':'meta', 'facebook':'meta',
        'l-or-al':'loreal', 'l-oreal':'loreal',
        'tata-consultancy-services':'tata',
        'pricewaterhousecoopers':'pwc',
    }
    return aliases.get(s, s)

def _course_image_pool(category_name, partner_slug=None):
    """Build the list of course images appropriate for a course in the given
    category and from the given partner. Two filters are applied:

    1. Partner filter — an image carrying a `partner_lock` is only eligible
       when its lock equals `partner_slug`. This stops, e.g., the IBM badge
       from being shown on a Google course. Images locked to a brand that
       isn't a partner in our DB (Pittsburgh, Deloitte, INFOSEC, Packt, …)
       are effectively excluded from every course.
    2. Category filter — within partner-eligible images, prefer those whose
       tags include the course's category slug; only fall back to
       topic-neutral (`tags == ['generic']`) images when no category-specific
       image qualifies."""
    tags_map = _course_image_tags()
    full_pool = _img_manifest().get('courses') or []
    if not tags_map:
        return full_pool
    def _entry(rel):
        return tags_map.get(rel) or {}
    partner_ok = [rel for rel in full_pool
                  if _entry(rel).get('partner_lock') in (None, partner_slug)]
    if not partner_ok:
        partner_ok = full_pool
    cat_slug = _CATEGORY_NAME_TO_SLUG.get(category_name or '')
    specific = []
    if cat_slug:
        specific = [rel for rel in partner_ok
                    if cat_slug in (_entry(rel).get('tags') or [])]
    if specific:
        return specific
    pure_generic = [rel for rel in partner_ok
                    if _entry(rel).get('tags') == ['generic']]
    return pure_generic or partner_ok

def course_thumb(c):
    """Return a static-relative path like 'images/courses/0042.jpg' for a course.

    Resolution order (most preferred first):
      1. `images/courses/real/<slug>.jpg` — a real Coursera thumbnail scraped
         by fetch_real_thumbs.py. The actual photographic course card.
      2. The curated stock pool (filtered by partner_lock + category) — picks
         a topically appropriate image that doesn't carry a conflicting brand.
      3. `images/courses/gen/<slug>.png` — a generated text card, used only
         when neither a real image nor any topically-acceptable stock image
         is available."""
    slug = getattr(c, 'slug', None)
    if slug:
        real_rel = f'courses/real/{slug}.jpg'
        if os.path.exists(os.path.join(_IMG_DIR, real_rel)):
            return 'images/' + real_rel
    partner = getattr(c, 'partner', None)
    partner_slug = getattr(partner, 'slug', None) if partner else None
    pool = _course_image_pool(getattr(c, 'category', None), partner_slug)
    pick = _stable_pick(slug or getattr(c, 'id', 0), pool)
    if pick:
        return 'images/' + pick
    if slug:
        gen_rel = f'courses/gen/{slug}.png'
        if os.path.exists(os.path.join(_IMG_DIR, gen_rel)):
            return 'images/' + gen_rel
    return None

def partner_logo(p):
    """Return a static-relative path for a partner's logo, or None.
    Accepts a Partner object, dict {'slug','name'}, or string name."""
    if not p:
        return None
    if isinstance(p, dict):
        slug = p.get('slug') or _slugify_partner(p.get('name', ''))
        name = p.get('name', '')
    elif isinstance(p, str):
        name = p
        slug = _slugify_partner(p)
    else:
        name = getattr(p, 'name', '') or ''
        slug = getattr(p, 'slug', None) or _slugify_partner(name)
    partners = _img_manifest().get('partners') or {}
    rel = partners.get(slug) or partners.get(_slugify_partner(name))
    return ('images/' + rel) if rel else None

def instructor_photo(name_or_slug):
    if not name_or_slug:
        return None
    slug = _slugify_instructor(name_or_slug) if ' ' in str(name_or_slug) else name_or_slug
    pool = _img_manifest().get('instructors') or {}
    rel = pool.get(slug)
    if not rel:
        # deterministic fallback: pick from available pool
        rel = _stable_pick(slug, list(pool.values()))
    return ('images/' + rel) if rel else None

def category_image(slug):
    rel = (_img_manifest().get('categories') or {}).get(slug)
    return ('images/' + rel) if rel else None

def hero_image(key):
    rel = (_img_manifest().get('hero') or {}).get(key)
    return ('images/' + rel) if rel else None

def static_image(rel_path):
    """Helper to build a full static url from a manifest-relative path."""
    if not rel_path:
        return None
    return rel_path if rel_path.startswith('images/') else 'images/' + rel_path


@app.context_processor
def inject_globals():
    saved_ids = set()
    enrolled_ids = set()
    resume_course = None
    if current_user.is_authenticated:
        saved_ids = {s.course_id for s in current_user.saved_courses}
        enrolled_ids = {e.course_id for e in current_user.enrollments}
        # R5: pick the most recent enrollment as the Continue Learning target.
        # Deterministic across reloads (orders by enrollment id desc, which is
        # itself seeded deterministically).
        latest_enrollment = (Enrollment.query
                             .filter_by(user_id=current_user.id)
                             .order_by(Enrollment.id.desc())
                             .first())
        if latest_enrollment:
            resume_course = Course.query.get(latest_enrollment.course_id)
    categories = [
        ('computer-science', 'Computer Science'),
        ('data-science', 'Data Science'),
        ('business', 'Business'),
        ('information-technology', 'Information Technology'),
        ('language-learning', 'Language Learning'),
        ('math-logic', 'Math and Logic'),
        ('physical-science', 'Physical Science and Engineering'),
        ('social-sciences', 'Social Sciences'),
        ('arts-humanities', 'Arts and Humanities'),
        ('health', 'Health'),
        ('personal-development', 'Personal Development'),
    ]
    m = _img_manifest()
    # ── R7 i18n: 16 supported locales for hreflang + UI lang attr ──────────
    current_lang = session.get('coursera_lang') or request.args.get('lang') or 'en'
    if current_lang not in R7_LOCALES:
        current_lang = 'en'
    return dict(saved_ids=saved_ids, enrolled_ids=enrolled_ids,
                nav_categories=categories,
                resume_course=resume_course,
                course_thumb=course_thumb,
                partner_logo=partner_logo,
                instructor_photo=instructor_photo,
                category_image=category_image,
                hero_image=hero_image,
                site_logo=('images/' + m['logo']) if m.get('logo') else None,
                hero_home=('images/' + m['hero_home']) if m.get('hero_home') else None,
                plus_logo=('images/' + m['plus_logo']) if m.get('plus_logo') else None,
                app_store_badge=('images/' + (m.get('badges') or {}).get('app_store','')) if (m.get('badges') or {}).get('app_store') else None,
                play_store_badge=('images/' + (m.get('badges') or {}).get('google_play','')) if (m.get('badges') or {}).get('google_play') else None,
                social_icons={k:'images/'+v for k,v in (m.get('social') or {}).items()},
                current_lang=current_lang,
                supported_locales=R7_LOCALES,
                locale_native_names=R7_LOCALE_NATIVE_NAMES,
                )


# ─── R7 i18n: 16 supported locales (matches real Coursera footer) ────────────
# (code, English name, native name) — used for hreflang + UI switcher.
R7_LOCALES = ['en', 'es', 'zh', 'ja', 'ar', 'fr', 'de', 'pt',
              'ko', 'hi', 'ru', 'it', 'tr', 'vi', 'id', 'pl']
R7_LOCALE_NATIVE_NAMES = {
    'en': 'English',           'es': 'Español',
    'zh': '中文（简体）',         'ja': '日本語',
    'ar': 'العربية',             'fr': 'Français',
    'de': 'Deutsch',           'pt': 'Português',
    'ko': '한국어',              'hi': 'हिन्दी',
    'ru': 'Русский',            'it': 'Italiano',
    'tr': 'Türkçe',             'vi': 'Tiếng Việt',
    'id': 'Bahasa Indonesia',   'pl': 'Polski',
}

# ─── Routes: Static pages ─────────────────────────────────────────────────────

@app.route('/')
def index():
    featured = Course.query.filter_by(is_featured=True).limit(12).all()
    free_courses = Course.query.filter_by(is_free=True).limit(6).all()
    new_courses = Course.query.filter_by(is_new=True).order_by(
        Course.sort_date.desc()).limit(8).all()
    return render_template('index.html', featured=featured,
                           free_courses=free_courses, new_courses=new_courses)

@app.route('/coursera-plus')
def coursera_plus():
    return render_template('coursera_plus.html')

@app.route('/business')
def business():
    return render_template('business.html')

@app.route('/for-teams')
@app.route('/teams')
def for_teams():
    return render_template('for_teams.html')


@app.route('/for-universities')
@app.route('/universities')
def for_universities():
    """Coursera for Campus — pitch page for universities."""
    return render_template('for_universities.html')


@app.route('/for-government')
@app.route('/government')
def for_government():
    """Coursera for Government — pitch page for public sector buyers."""
    return render_template('for_government.html')


@app.route('/help')
@app.route('/support')
def help_center():
    """Static help / support page with grouped FAQ."""
    return render_template('help.html')


@app.route('/careers')
@app.route('/jobs')
def careers():
    """Coursera careers / open-roles page."""
    return render_template('careers.html')


@app.route('/mobile')
@app.route('/app')
def mobile():
    """Mobile app landing — App Store + Play Store links."""
    return render_template('mobile.html')


@app.route('/blog')
@app.route('/blog/<slug>')
def blog(slug=None):
    """Coursera blog — index of recent posts and a stub article view."""
    posts = [
        {
            'slug': 'top-skills-2026',
            'title': 'Top 10 Skills Employers Will Look For in 2026',
            'date': 'Apr 18, 2026',
            'category': 'Career advice',
            'excerpt': 'AI literacy, data fluency, and collaboration top the list this year — here is how to build them online.',
        },
        {
            'slug': 'how-to-finish-a-specialization',
            'title': 'How to Finish a Specialization Without Losing Your Weekends',
            'date': 'Mar 11, 2026',
            'category': 'Learning tips',
            'excerpt': 'A four-week framework borrowed from working professionals who balance Coursera with a day job.',
        },
        {
            'slug': 'professional-certificate-roi',
            'title': 'Are Professional Certificates Worth It? Three Learners Share Their ROI',
            'date': 'Feb 02, 2026',
            'category': 'Outcomes',
            'excerpt': 'Real numbers from three career-switchers who finished Google, IBM, and Meta certificates last year.',
        },
        {
            'slug': 'ai-for-non-engineers',
            'title': 'AI For Non-Engineers: A Reading List From Andrew Ng',
            'date': 'Jan 17, 2026',
            'category': 'AI',
            'excerpt': 'The five courses, two specializations, and one Coursera Plus track Andrew recommends for product teams.',
        },
        {
            'slug': 'global-degree-trends',
            'title': 'Global Online-Degree Trends: Enrolment Hits a New High',
            'date': 'Dec 09, 2025',
            'category': 'Industry',
            'excerpt': 'Online enrolments grew 23 % year-over-year. Here is which programs drove the spike.',
        },
        {
            'slug': 'employer-driven-skills',
            'title': 'How Companies Use Coursera for Business to Close Skill Gaps',
            'date': 'Nov 21, 2025',
            'category': 'Enterprise',
            'excerpt': 'Inside the Coursera for Business playbook: skill assessments, learning paths, and measurable impact.',
        },
    ]
    if slug:
        post = next((p for p in posts if p['slug'] == slug), None)
        if not post:
            abort(404)
        return render_template('blog_post.html', post=post, posts=posts)
    return render_template('blog.html', posts=posts)


@app.route('/instructor/<slug>')
def instructor_profile(slug):
    """Instructor profile page: shows all courses taught by an instructor."""
    # Find all courses whose instructor slug matches
    all_courses = Course.query.filter(Course.instructor != '').all()
    matches = [c for c in all_courses if _slugify_instructor(c.instructor) == slug]
    if not matches:
        abort(404)
    # Use the first course's instructor details as the canonical name/title
    name = matches[0].instructor
    title = matches[0].instructor_title or ''
    # Try to extract affiliation from title (e.g. "Professor of Finance, University of Michigan")
    affiliation = ''
    if ',' in title:
        affiliation = title.split(',', 1)[1].strip()
    # Sort courses by enrolled count desc
    matches.sort(key=lambda c: -(c.enrolled_count or 0))
    return render_template('instructor.html', name=name, title=title,
                           affiliation=affiliation, courses=matches,
                           slug=slug)

@app.route('/partners')
def partners():
    country = request.args.get('country', '')
    ptype = request.args.get('type', '')
    q = Partner.query
    if country:
        q = q.filter(Partner.country.ilike(f'%{country}%'))
    if ptype:
        q = q.filter_by(partner_type=ptype)
    all_partners = q.order_by(Partner.name).all()
    countries = db.session.query(Partner.country).distinct().order_by(Partner.country).all()
    countries = [c[0] for c in countries if c[0]]
    return render_template('partners.html', partners=all_partners,
                           countries=countries, country=country, ptype=ptype)

@app.route('/degrees')
def degrees():
    dtype = request.args.get('type', '')
    q = Course.query.filter_by(course_type='Degree')
    if dtype:
        q = q.filter(Course.degree_type.ilike(f'%{dtype}%'))
    all_degrees = q.order_by(Course.title).all()
    return render_template('degrees.html', degrees=all_degrees, dtype=dtype)

@app.route('/professional-certificates')
def professional_certificates():
    certs = Course.query.filter_by(course_type='Professional Certificate').all()
    return render_template('professional_certificates.html', courses=certs)

@app.route('/browse/<category_slug>')
def browse(category_slug):
    cat_map = {
        'computer-science': 'Computer Science',
        'data-science': 'Data Science',
        'business': 'Business',
        'information-technology': 'Information Technology',
        'language-learning': 'Language Learning',
        'math-logic': 'Math and Logic',
        'physical-science': 'Physical Science and Engineering',
        'social-sciences': 'Social Sciences',
        'arts-humanities': 'Arts and Humanities',
        'health': 'Health',
        'personal-development': 'Personal Development',
    }
    cat_name = cat_map.get(category_slug, category_slug.replace('-', ' ').title())
    courses = Course.query.filter(
        Course.category.ilike(f'%{cat_name}%')
    ).order_by(Course.enrolled_count.desc()).all()
    return render_template('browse.html', courses=courses, category_name=cat_name,
                           category_slug=category_slug)

# ─── Routes: Search ───────────────────────────────────────────────────────────

@app.route('/search')
def search():
    q = (request.args.get('q') or request.args.get('query') or '').strip()
    level = request.args.get('level', '')
    course_type = request.args.get('type', '')
    duration = request.args.get('duration', '')
    min_rating = request.args.get('min_rating', '')
    free = request.args.get('free', '')
    credit = request.args.get('credit', '')
    certificate = request.args.get('certificate', '')
    category = request.args.get('category', '')
    sort = request.args.get('sort', 'popular')

    results = search_courses(q=q, level=level, course_type=course_type,
                             duration=duration, min_rating=min_rating,
                             free=free, credit=credit, certificate=certificate,
                             category=category, sort=sort)
    return render_template('search.html', results=results, q=q, level=level,
                           course_type=course_type, duration=duration,
                           min_rating=min_rating, free=free, credit=credit,
                           certificate=certificate, category=category, sort=sort,
                           total=len(results))

# ─── Routes: Course detail ────────────────────────────────────────────────────

@app.route('/learn/<slug>')
def course_detail(slug):
    course = Course.query.filter_by(slug=slug).first_or_404()
    reviews = Review.query.filter_by(course_id=course.id).order_by(
        Review.created_at.desc()).limit(10).all()
    sub_courses = SubCourse.query.filter_by(
        specialization_id=course.id).order_by(SubCourse.order_index).all()
    related = Course.query.filter(
        Course.category == course.category,
        Course.id != course.id
    ).limit(4).all()
    is_enrolled = False
    is_saved = False
    if current_user.is_authenticated:
        is_enrolled = Enrollment.query.filter_by(
            user_id=current_user.id, course_id=course.id).first() is not None
        is_saved = SavedCourse.query.filter_by(
            user_id=current_user.id, course_id=course.id).first() is not None
    review_form = ReviewForm()
    # Generate review rating breakdown based on average rating
    avg = course.rating or 4.5
    if avg >= 4.7:
        breakdown = {'5': 65, '4': 22, '3': 8, '2': 3, '1': 2}
    elif avg >= 4.4:
        breakdown = {'5': 55, '4': 28, '3': 10, '2': 4, '1': 3}
    elif avg >= 4.0:
        breakdown = {'5': 45, '4': 30, '3': 15, '2': 6, '1': 4}
    else:
        breakdown = {'5': 30, '4': 30, '3': 20, '2': 12, '1': 8}
    # ── R6 contextual panels (deterministic — derived from existing fields) ──
    r6_panels = _r6_course_panels(course)
    return render_template('course_detail.html', course=course, reviews=reviews,
                           sub_courses=sub_courses, related=related,
                           is_enrolled=is_enrolled, is_saved=is_saved,
                           review_form=review_form, rating_breakdown=breakdown,
                           r6_panels=r6_panels,
                           course_jsonld=_course_jsonld(course))


def _r6_course_panels(course):
    """Compute 4 contextual panels for the R6 course-detail layout.

    All four lookups are pure read-only ORM queries against existing
    columns — no schema changes, no DB writes, fully deterministic
    (queries are bounded and ordered by stable keys).
    """
    primary_skill = ''
    try:
        sk = json.loads(course.skills or '[]')
        if sk:
            primary_skill = sk[0]
    except Exception:
        pass

    # 1) Specialization that includes this course — pick a Specialization /
    #    Professional Certificate in the same category that shares the
    #    primary skill or instructor.
    spec_q = Course.query.filter(
        Course.course_type.in_(['Specialization', 'Professional Certificate']),
        Course.id != course.id,
        Course.category == course.category,
    )
    if primary_skill:
        spec_q = spec_q.filter(Course.skills.like(f'%{primary_skill}%'))
    spec_includes = spec_q.order_by(Course.enrolled_count.desc()).first()
    if spec_includes is None:
        spec_includes = Course.query.filter(
            Course.course_type.in_(['Specialization', 'Professional Certificate']),
            Course.category == course.category,
            Course.id != course.id,
        ).order_by(Course.id).first()

    # 2) Courses by same instructor (cap 4, excluding self).
    by_same_instructor = []
    if course.instructor:
        by_same_instructor = Course.query.filter(
            Course.instructor == course.instructor,
            Course.id != course.id,
        ).order_by(Course.id).limit(4).all()

    # 3) Next recommended after completion — same category, one step up in
    #    level if possible, otherwise a Specialization fallback.
    level_order = ['Beginner', 'Intermediate', 'Advanced']
    next_recommended = None
    cur_level = course.level if course.level in level_order else 'Beginner'
    next_idx = min(level_order.index(cur_level) + 1, len(level_order) - 1)
    target_level = level_order[next_idx]
    next_recommended = Course.query.filter(
        Course.category == course.category,
        Course.level == target_level,
        Course.id != course.id,
    ).order_by(Course.rating.desc(), Course.id).first()
    if next_recommended is None:
        next_recommended = Course.query.filter(
            Course.category == course.category,
            Course.course_type == 'Specialization',
            Course.id != course.id,
        ).order_by(Course.id).first()

    # 4) Required prerequisite path — pick up to 2 Beginner-level
    #    Foundations-style courses in the same category (skip if current
    #    course is already Beginner with no Advanced peers).
    prereq_q = Course.query.filter(
        Course.category == course.category,
        Course.level == 'Beginner',
        Course.id != course.id,
    )
    if cur_level == 'Beginner':
        # When viewing a beginner course, surface Foundations-tagged peers
        # in adjacent categories as prep, but keep within Coursera taxonomy.
        prereq_q = prereq_q.filter(Course.slug.like('foundations-of-%'))
    prereq_path = prereq_q.order_by(Course.enrolled_count.desc()).limit(2).all()
    # Fallback: any 2 lower-level peers if none match Foundations filter
    if not prereq_path and cur_level != 'Beginner':
        prereq_path = Course.query.filter(
            Course.category == course.category,
            Course.level == 'Beginner',
            Course.id != course.id,
        ).order_by(Course.enrolled_count.desc()).limit(2).all()

    return {
        'specialization_includes': spec_includes,
        'by_same_instructor': by_same_instructor,
        'next_recommended': next_recommended,
        'prereq_path': prereq_path,
        'primary_skill': primary_skill,
    }


@app.route('/specializations/<path:slug>')
def specialization_detail(slug):
    """Dedicated Specialization landing page (GUI deepen 2026-05-27).

    Real Coursera surfaces /specializations/<slug> as a richer landing
    page distinct from the /learn/<slug> course detail.  We render a
    dedicated template that lists the course series, capstone, skills,
    and instructors — no DB writes, no API calls."""
    course = Course.query.filter_by(slug=slug).first()
    if not course and not slug.endswith('-specialization'):
        course = Course.query.filter_by(slug=f'{slug}-specialization').first()
    if not course:
        abort(404)
    sub_courses = SubCourse.query.filter_by(
        specialization_id=course.id).order_by(SubCourse.order_index).all()
    inst_names = []
    if course.instructor:
        for nm in [n.strip() for n in course.instructor.split(',')]:
            if nm and nm not in inst_names:
                inst_names.append(nm)
    instructors = []
    for nm in inst_names[:4]:
        instructors.append({
            'name': nm,
            'slug': _slugify_instructor(nm),
            'title': course.instructor_title or 'Instructor',
        })
    has_capstone = (int(hashlib.md5(course.slug.encode()).hexdigest()[:2], 16) % 3) != 0
    return render_template('specialization_detail.html',
                           course=course,
                           sub_courses=sub_courses,
                           instructors=instructors,
                           has_capstone=has_capstone)

# ─── Routes: Auth ─────────────────────────────────────────────────────────────

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.lower().strip()).first()
        if user and user.check_password(form.password.data):
            login_user(user)
            next_page = request.args.get('next')
            return redirect(next_page or url_for('index'))
        flash('Invalid email or password.', 'danger')
    return render_template('login.html', form=form)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = RegisterForm()
    if form.validate_on_submit():
        email = form.email.data.lower().strip()
        if User.query.filter_by(email=email).first():
            flash('Email already registered.', 'danger')
            return render_template('register.html', form=form)
        user = User(name=form.name.data.strip(), email=email)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        login_user(user)
        return redirect(url_for('index'))
    return render_template('register.html', form=form)

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))

# ─── Routes: Account ─────────────────────────────────────────────────────────

@app.route('/account')
@login_required
def account():
    enrollments = Enrollment.query.filter_by(
        user_id=current_user.id).order_by(Enrollment.enrolled_at.desc()).all()
    return render_template('account.html', enrollments=enrollments)

@app.route('/account/edit', methods=['GET', 'POST'])
@login_required
def account_edit():
    form = ProfileForm(obj=current_user)
    if form.validate_on_submit():
        email = form.email.data.lower().strip()
        existing = User.query.filter_by(email=email).first()
        if existing and existing.id != current_user.id:
            flash('Email already in use.', 'danger')
        else:
            current_user.name = form.name.data.strip()
            current_user.email = email
            db.session.commit()
            flash('Profile updated.', 'success')
            return redirect(url_for('account'))
    return render_template('account_edit.html', form=form)

@app.route('/account/password', methods=['GET', 'POST'])
@login_required
def change_password():
    form = PasswordForm()
    if form.validate_on_submit():
        if not current_user.check_password(form.current_password.data):
            flash('Current password is incorrect.', 'danger')
        else:
            current_user.set_password(form.new_password.data)
            db.session.commit()
            flash('Password updated.', 'success')
            return redirect(url_for('account'))
    return render_template('change_password.html', form=form)

@app.route('/account/delete', methods=['POST'])
@login_required
def account_delete():
    user = db.session.get(User, current_user.id)
    logout_user()
    db.session.delete(user)
    db.session.commit()
    flash('Account deleted.', 'info')
    return redirect(url_for('index'))

@app.route('/wishlist')
@login_required
def wishlist():
    saved = SavedCourse.query.filter_by(
        user_id=current_user.id).order_by(SavedCourse.saved_at.desc()).all()
    return render_template('wishlist.html', saved=saved)

# ─── Routes: Reviews ──────────────────────────────────────────────────────────

@app.route('/learn/<slug>/review', methods=['POST'])
@login_required
def submit_review(slug):
    course = Course.query.filter_by(slug=slug).first_or_404()
    form = ReviewForm()
    if form.validate_on_submit():
        existing = Review.query.filter_by(
            user_id=current_user.id, course_id=course.id).first()
        if existing:
            existing.rating = form.rating.data
            existing.body = form.body.data
        else:
            r = Review(user_id=current_user.id, course_id=course.id,
                       rating=form.rating.data, body=form.body.data)
            db.session.add(r)
        db.session.commit()
        flash('Review submitted.', 'success')
    return redirect(url_for('course_detail', slug=slug))

@app.route('/review/<int:review_id>/delete', methods=['POST'])
@login_required
def delete_review(review_id):
    r = db.session.get(Review, review_id)
    if r and r.user_id == current_user.id:
        db.session.delete(r)
        db.session.commit()
        flash('Review deleted.', 'info')
    return redirect(request.referrer or url_for('account'))

# ─── API Routes ───────────────────────────────────────────────────────────────

@app.route('/api/enroll', methods=['POST'])
@csrf.exempt
@login_required
def api_enroll():
    # Support both JSON (legacy) and form POST (agent-compatible)
    if request.is_json:
        data = request.get_json() or {}
        course_id = data.get('course_id')
    else:
        try:
            course_id = int(request.form.get('course_id'))
        except (TypeError, ValueError):
            course_id = None
    course = db.session.get(Course, course_id)
    if not course:
        if request.is_json:
            return jsonify({'success': False, 'message': 'Course not found'}), 404
        flash('Course not found.', 'danger')
        return redirect(request.referrer or url_for('index'))
    existing = Enrollment.query.filter_by(
        user_id=current_user.id, course_id=course_id).first()
    if not existing:
        e = Enrollment(user_id=current_user.id, course_id=course_id)
        db.session.add(e)
        db.session.commit()
    if request.is_json:
        return jsonify({'success': True, 'message': f'Enrolled in {course.title}',
                        'enrolled': True})
    flash(f'Successfully enrolled in {course.title}!', 'success')
    return redirect(url_for('course_detail', slug=course.slug))


@app.route('/enroll/<int:course_id>', methods=['POST'])
@login_required
def enroll_form(course_id):
    """Form-POST enroll — agent-compatible (no AJAX required)."""
    course = Course.query.get_or_404(course_id)
    existing = Enrollment.query.filter_by(
        user_id=current_user.id, course_id=course_id).first()
    if not existing:
        db.session.add(Enrollment(user_id=current_user.id, course_id=course_id))
        db.session.commit()
        flash(f'Successfully enrolled in {course.title}!', 'success')
    else:
        flash(f'You are already enrolled in {course.title}.', 'info')
    return redirect(url_for('course_detail', slug=course.slug))


@app.route('/api/wishlist/toggle', methods=['POST'])
@csrf.exempt
@login_required
def api_wishlist_toggle():
    # Support both JSON (legacy) and form POST (agent-compatible)
    if request.is_json:
        data = request.get_json() or {}
        course_id = data.get('course_id')
    else:
        try:
            course_id = int(request.form.get('course_id'))
        except (TypeError, ValueError):
            course_id = None
    course = db.session.get(Course, course_id)
    if not course:
        if request.is_json:
            return jsonify({'success': False, 'message': 'Not found'}), 404
        flash('Course not found.', 'danger')
        return redirect(request.referrer or url_for('index'))
    existing = SavedCourse.query.filter_by(
        user_id=current_user.id, course_id=course_id).first()
    if existing:
        db.session.delete(existing)
        db.session.commit()
        if request.is_json:
            return jsonify({'success': True, 'saved': False,
                            'message': 'Removed from saved courses'})
        flash(f'Removed {course.title} from saved courses.', 'info')
        return redirect(request.referrer or url_for('wishlist'))
    db.session.add(SavedCourse(user_id=current_user.id, course_id=course_id))
    db.session.commit()
    if request.is_json:
        return jsonify({'success': True, 'saved': True,
                        'message': 'Saved to your list'})
    flash(f'Saved {course.title} to your list!', 'success')
    return redirect(request.referrer or url_for('wishlist'))


@app.route('/wishlist/save/<int:course_id>', methods=['POST'])
@login_required
def wishlist_save_form(course_id):
    """Form-POST save — agent-compatible."""
    course = Course.query.get_or_404(course_id)
    if not SavedCourse.query.filter_by(user_id=current_user.id, course_id=course_id).first():
        db.session.add(SavedCourse(user_id=current_user.id, course_id=course_id))
        db.session.commit()
        flash(f'Saved {course.title} to your list!', 'success')
    else:
        flash(f'{course.title} is already in your saved courses.', 'info')
    return redirect(url_for('course_detail', slug=course.slug))


@app.route('/wishlist/remove/<int:course_id>', methods=['POST'])
@login_required
def wishlist_remove_form(course_id):
    """Form-POST remove from wishlist — agent-compatible."""
    course = Course.query.get_or_404(course_id)
    existing = SavedCourse.query.filter_by(
        user_id=current_user.id, course_id=course_id).first()
    if existing:
        db.session.delete(existing)
        db.session.commit()
        flash(f'Removed {course.title} from saved courses.', 'info')
    return redirect(request.referrer or url_for('wishlist'))

@app.route('/api/courses/<category>')
@csrf.exempt
def api_courses_by_category(category):
    courses = Course.query.filter(
        Course.category.ilike(f'%{category}%')).limit(20).all()
    return jsonify([{
        'id': c.id, 'title': c.title, 'slug': c.slug,
        'rating': c.rating, 'level': c.level,
        'course_type': c.course_type,
    } for c in courses])


# ─── R3 deep sub-pages: /career, /partner, /skill, /degrees-list, /certificate ─

CAREER_ROLES_PUB = [
    ('Data Analyst', 'data-analyst', 'Data Science',
     'Analyse data, build dashboards, and tell stories with numbers.',
     ['SQL', 'Tableau', 'Excel', 'Python']),
    ('Data Scientist', 'data-scientist', 'Data Science',
     'Build predictive models and ship machine learning to production.',
     ['Python', 'Statistics', 'Machine Learning', 'Deep Learning']),
    ('Machine Learning Engineer', 'machine-learning-engineer', 'Data Science',
     'Productionise machine-learning systems and own them end-to-end.',
     ['Python', 'TensorFlow', 'MLOps', 'Cloud Computing']),
    ('Software Engineer', 'software-engineer', 'Computer Science',
     'Design, build and maintain reliable software at scale.',
     ['Java', 'Python', 'Git', 'System Design']),
    ('Full-Stack Web Developer', 'full-stack-web-developer', 'Computer Science',
     'Build the end-to-end web stack from database to UI.',
     ['JavaScript', 'React', 'Node.js', 'SQL']),
    ('Front-End Developer', 'front-end-developer', 'Computer Science',
     'Craft beautiful, accessible user interfaces with modern frameworks.',
     ['HTML', 'CSS', 'JavaScript', 'React']),
    ('Back-End Developer', 'back-end-developer', 'Computer Science',
     'Design APIs, queues, and data layers that scale.',
     ['Python', 'Node.js', 'PostgreSQL', 'REST APIs']),
    ('Mobile App Developer', 'mobile-app-developer', 'Computer Science',
     'Ship native and cross-platform mobile apps.',
     ['Swift', 'Kotlin', 'React Native', 'Flutter']),
    ('Cloud Architect', 'cloud-architect', 'Information Technology',
     'Design cloud-native systems on AWS, Azure, or GCP.',
     ['AWS', 'Azure', 'GCP', 'Kubernetes']),
    ('DevOps Engineer', 'devops-engineer', 'Information Technology',
     'Automate the path from code to production.',
     ['Docker', 'Kubernetes', 'CI/CD', 'Linux']),
    ('Cybersecurity Analyst', 'cybersecurity-analyst', 'Information Technology',
     'Defend organisations from threats with proven playbooks.',
     ['Network Security', 'SIEM', 'Penetration Testing', 'Cryptography']),
    ('IT Support Specialist', 'it-support-specialist', 'Information Technology',
     'Keep users productive and infrastructure healthy.',
     ['Networking', 'Help Desk', 'Hardware', 'Windows Server']),
    ('UX Designer', 'ux-designer', 'Arts and Humanities',
     'Research and design human-centred product experiences.',
     ['Figma', 'User Research', 'Wireframing', 'Prototyping']),
    ('Product Manager', 'product-manager', 'Business',
     'Lead the cross-functional team that ships product.',
     ['Roadmapping', 'Stakeholder Management', 'Analytics', 'Agile']),
    ('Project Manager', 'project-manager', 'Business',
     'Deliver on time, on scope, and on budget with proven frameworks.',
     ['Agile', 'Scrum', 'Risk Management', 'Communication']),
    ('Digital Marketing Specialist', 'digital-marketing-specialist', 'Business',
     'Acquire, engage, and retain customers across digital channels.',
     ['SEO', 'SEM', 'Content Marketing', 'Analytics']),
    ('Financial Analyst', 'financial-analyst', 'Business',
     'Model businesses and inform investment decisions.',
     ['Excel', 'Valuation', 'Modeling', 'Accounting']),
    ('Business Analyst', 'business-analyst', 'Business',
     'Translate business needs into shipping requirements.',
     ['Requirements', 'SQL', 'Process Mapping', 'Stakeholder Management']),
    ('Game Developer', 'game-developer', 'Computer Science',
     'Ship interactive entertainment using Unity, Unreal and beyond.',
     ['Unity', 'C#', '3D Graphics', 'Game Design']),
    ('Bioinformatician', 'bioinformatician', 'Health',
     'Apply computation to biology and life sciences research.',
     ['Python', 'Genomics', 'R', 'Statistics']),
]

@app.route('/careers/<role_slug>')
@app.route('/career/<role_slug>')
def career_path(role_slug):
    role = next((r for r in CAREER_ROLES_PUB if r[1] == role_slug), None)
    if not role:
        abort(404)
    name, _slug, category, blurb, skills = role
    # Find related certificate
    cert = Course.query.filter_by(
        slug=f'career-certificate-{role_slug}').first()
    # Find related courses by category + matching skills feature tag
    related = Course.query.filter(
        Course.category == category,
        Course.feature_tags.like(f'%{role_slug}%'),
    ).order_by(Course.enrolled_count.desc()).limit(24).all()
    if len(related) < 12:
        # Augment with category top
        more = Course.query.filter(
            Course.category == category,
            ~Course.id.in_([c.id for c in related]),
        ).order_by(Course.enrolled_count.desc()).limit(24 - len(related)).all()
        related = related + more
    return render_template('career.html', role_name=name, role_slug=role_slug,
                           category=category, blurb=blurb, skills=skills,
                           cert=cert, courses=related)


@app.route('/partner/<slug>')
@app.route('/university/<slug>')
@app.route('/instructor-org/<slug>')
def partner_detail(slug):
    partner = Partner.query.filter_by(slug=slug).first_or_404()
    courses = Course.query.filter_by(partner_id=partner.id).order_by(
        Course.enrolled_count.desc()).all()
    n_total = len(courses)
    by_type = {}
    for c in courses:
        by_type.setdefault(c.course_type or 'Course', []).append(c)
    return render_template('partner_detail.html', partner=partner,
                           courses=courses, by_type=by_type, n_total=n_total)


@app.route('/skill/<slug>')
@app.route('/skills/<slug>')
def skill_detail(slug):
    pretty = slug.replace('-', ' ').title()
    # Match via feature_tags or skills JSON or title substring
    needle_dash = slug.replace(' ', '-')
    needle_words = slug.replace('-', ' ')
    courses = Course.query.filter(
        db.or_(
            Course.feature_tags.like(f'%"{needle_dash}"%'),
            Course.skills.ilike(f'%{needle_words}%'),
            Course.title.ilike(f'%{needle_words}%'),
        )
    ).order_by(Course.enrolled_count.desc()).limit(96).all()
    return render_template('skill.html', skill_name=pretty,
                           skill_slug=slug, courses=courses)


@app.route('/degrees-list')
@app.route('/degrees/list')
def degrees_list():
    """Compact list view of all degrees (alias surface)."""
    degrees_ = Course.query.filter_by(course_type='Degree').order_by(
        Course.title).all()
    return render_template('degrees.html', degrees=degrees_, dtype='')


@app.route('/certificate/<int:course_id>')
@app.route('/verify/certificate/<int:course_id>')
def certificate_verify(course_id):
    """Public-facing certificate verification page. Shows the verified
    completion for a course-id and a deterministic verify-code."""
    course = Course.query.get_or_404(course_id)
    # Pick the most senior enrollment with >= 100% progress, else fall back
    enrollment = (Enrollment.query.filter_by(course_id=course.id)
                  .order_by(Enrollment.progress.desc(),
                            Enrollment.enrolled_at.asc()).first())
    learner = User.query.get(enrollment.user_id) if enrollment else None
    # Deterministic verify code from course id (no clock drift)
    verify_code = f'COUR-{course.id:06d}-{hashlib.md5(course.slug.encode()).hexdigest()[:6].upper()}'
    issued = (enrollment.enrolled_at.strftime('%B %d, %Y')
              if enrollment and enrollment.enrolled_at
              else course.sort_date)
    return render_template('certificate.html', course=course,
                           learner=learner, verify_code=verify_code,
                           issued=issued)


@app.route('/learn/<slug>/syllabus')
@app.route('/learn/<slug>/modules')
def course_syllabus(slug):
    """Standalone syllabus page (GUI deepen 2026-05-27).

    Real Coursera renders /learn/<slug>/syllabus as its own page distinct
    from the marketing course detail.  We surface the week-by-week
    modules in a dedicated template."""
    course = Course.query.filter_by(slug=slug).first_or_404()
    modules = course.modules or []
    return render_template('course_syllabus.html', course=course,
                           modules=modules)


# ─── R4 deep sub-pages ────────────────────────────────────────────────────────

@app.route('/learn/<slug>/lecture/<int:n>')
def course_lecture(slug, n):
    """Per-week lecture page. Week-N video list + transcript + downloads."""
    course = Course.query.filter_by(slug=slug).first_or_404()
    mods = course.modules
    if not mods or n < 1 or n > len(mods):
        abort(404)
    module = mods[n - 1]
    prev_n = n - 1 if n > 1 else None
    next_n = n + 1 if n < len(mods) else None
    return render_template('course_lecture.html', course=course, module=module,
                           n=n, total=len(mods), prev_n=prev_n, next_n=next_n)


@app.route('/learn/<slug>/assignment/<int:n>')
def course_assignment(slug, n):
    """Per-week assignment page. Rubric, due date, peer-review pool."""
    course = Course.query.filter_by(slug=slug).first_or_404()
    mods = course.modules
    if not mods or n < 1 or n > len(mods):
        abort(404)
    module = mods[n - 1]
    # Deterministic rubric and due date from week number
    due_offset = 7 * n
    return render_template('course_assignment.html', course=course,
                           module=module, n=n, total=len(mods),
                           due_days=due_offset)


@app.route('/learn/<slug>/discussion')
def course_discussion(slug):
    """Course discussion forum. Lists deterministic example threads."""
    course = Course.query.filter_by(slug=slug).first_or_404()
    # Seed a few deterministic discussion threads from existing reviews.
    rvs = Review.query.filter_by(course_id=course.id).order_by(
        Review.created_at.desc()).limit(8).all()
    threads = []
    titles = [
        'Welcome thread — introduce yourself',
        'Week 1 — common mistakes',
        'Office-hour announcements',
        'Study group sign-ups',
        'Capstone project showcase',
        'Career advice from alumni',
    ]
    for i, t in enumerate(titles):
        author = (rvs[i % len(rvs)].user.name if rvs else 'Coursera Mentor')
        threads.append({'title': t, 'author': author,
                        'replies': 12 + (i * 17 + course.id) % 60})
    return render_template('course_discussion.html', course=course,
                           threads=threads)


@app.route('/learn/<slug>/peer-review')
def course_peer_review(slug):
    """Peer-review queue for a course. Lists submissions awaiting review."""
    course = Course.query.filter_by(slug=slug).first_or_404()
    # Pool of deterministic example submissions
    pool = []
    enrolls = Enrollment.query.filter_by(course_id=course.id).order_by(
        Enrollment.progress.desc()).limit(6).all()
    for i, e in enumerate(enrolls):
        u = User.query.get(e.user_id)
        if not u:
            continue
        pool.append({
            'learner': u.name,
            'title': f'Capstone submission #{i + 1}: {course.title}',
            'submitted_days_ago': 1 + (i * 3 + course.id) % 14,
            'progress': e.progress,
        })
    return render_template('course_peer_review.html', course=course,
                           submissions=pool)


@app.route('/degree/<slug>/admissions')
def degree_admissions(slug):
    """Admissions page for a degree program."""
    course = Course.query.filter_by(slug=slug, course_type='Degree').first_or_404()
    return render_template('degree_admissions.html', course=course)


@app.route('/partner/<slug>/courses')
def partner_courses(slug):
    """A partner's full course catalog (compact list view)."""
    partner = Partner.query.filter_by(slug=slug).first_or_404()
    sort = request.args.get('sort', 'popular')
    q = Course.query.filter_by(partner_id=partner.id)
    if sort == 'newest':
        all_courses = q.order_by(Course.sort_date.desc()).all()
    elif sort == 'rating':
        all_courses = q.order_by(Course.rating.desc()).all()
    else:
        all_courses = q.order_by(Course.enrolled_count.desc()).all()
    return render_template('partner_courses.html', partner=partner,
                           courses=all_courses, sort=sort)


@app.route('/skill/<slug>/learner-stories')
@app.route('/skills/<slug>/learner-stories')
def skill_learner_stories(slug):
    """Learner stories anchored on a skill."""
    pretty = slug.replace('-', ' ').title()
    needle_dash = slug.replace(' ', '-')
    needle_words = slug.replace('-', ' ')
    courses = Course.query.filter(
        db.or_(
            Course.feature_tags.like(f'%"{needle_dash}"%'),
            Course.skills.ilike(f'%{needle_words}%'),
        )
    ).limit(20).all()
    # Pull testimonials + top reviews from these courses
    stories = []
    for c in courses:
        for t in c.get_testimonials()[:1]:
            stories.append({**t, 'course': c.title, 'slug': c.slug})
        if len(stories) >= 12:
            break
    return render_template('skill_learner_stories.html', skill_name=pretty,
                           skill_slug=slug, stories=stories, courses=courses)


@app.route('/career/<role_slug>/skills')
@app.route('/careers/<role_slug>/skills')
def career_skills(role_slug):
    """Skill map for a career role."""
    role = next((r for r in CAREER_ROLES_PUB if r[1] == role_slug), None)
    if not role:
        abort(404)
    name, _slug, category, blurb, skills = role
    # For each skill, find top 3 courses
    skill_to_courses = {}
    for sk in skills:
        cs = Course.query.filter(
            db.or_(
                Course.skills.ilike(f'%{sk}%'),
                Course.feature_tags.like(f'%"{sk.lower().replace(" ", "-")}"%'),
            )
        ).order_by(Course.enrolled_count.desc()).limit(3).all()
        skill_to_courses[sk] = cs
    return render_template('career_skills.html', role_name=name,
                           role_slug=role_slug, category=category, blurb=blurb,
                           skills=skills, skill_to_courses=skill_to_courses)


# ─── R7 — SEO, i18n, captions, accessibility, public-API docs ────────────────

@app.route('/lang/<code>')
def set_language(code):
    """Switch UI locale by setting a session cookie + redirect back. The
    cookie is read in `inject_globals()` to drive the <html lang="..">
    attribute and the hreflang link rotation. 16 locales supported."""
    if code in R7_LOCALES:
        session['coursera_lang'] = code
    return redirect(request.referrer or url_for('index'))


@app.route('/robots.txt')
def robots_txt():
    """robots.txt — points crawlers at the partner-split sitemap index."""
    body = (
        "User-agent: *\n"
        "Allow: /\n"
        "Disallow: /account\n"
        "Disallow: /api/\n"
        f"Sitemap: {request.host_url.rstrip('/')}/sitemap.xml\n"
    )
    return body, 200, {'Content-Type': 'text/plain; charset=utf-8'}


@app.route('/sitemap.xml')
def sitemap_index():
    """Partner-split sitemap index. Real Coursera also splits its sitemap
    by publisher (provider); we mirror that — one child sitemap per
    partner with > 0 published courses, plus a `static` sitemap for the
    catalogue / category / career / skill surfaces."""
    base = request.host_url.rstrip('/')
    partner_slugs = [s for (s,) in db.session.query(Partner.slug)
                     .join(Course, Course.partner_id == Partner.id)
                     .distinct().order_by(Partner.slug).all()]
    children = [f'{base}/sitemap/static.xml']
    children += [f'{base}/sitemap/partner-{slug}.xml'
                 for slug in partner_slugs]
    xml = ['<?xml version="1.0" encoding="UTF-8"?>',
           '<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for loc in children:
        xml.append(f'  <sitemap><loc>{loc}</loc></sitemap>')
    xml.append('</sitemapindex>')
    return '\n'.join(xml), 200, {'Content-Type': 'application/xml'}


@app.route('/sitemap/static.xml')
def sitemap_static():
    """Static surfaces — home, browse categories, careers, plus, etc."""
    base = request.host_url.rstrip('/')
    urls = ['', '/coursera-plus', '/business', '/for-teams',
            '/for-universities', '/for-government', '/degrees',
            '/professional-certificates', '/partners', '/careers',
            '/blog', '/help', '/mobile', '/accessibility',
            '/api/v1', '/financial-aid']
    cats = ['computer-science', 'data-science', 'business',
            'information-technology', 'language-learning', 'math-logic',
            'physical-science', 'social-sciences', 'arts-humanities',
            'health', 'personal-development']
    urls += [f'/browse/{c}' for c in cats]
    xml = ['<?xml version="1.0" encoding="UTF-8"?>',
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
           'xmlns:xhtml="http://www.w3.org/1999/xhtml">']
    for path in urls:
        xml.append(f'  <url><loc>{base}{path}</loc>')
        for lang in R7_LOCALES:
            xml.append(f'    <xhtml:link rel="alternate" hreflang="{lang}" '
                       f'href="{base}{path}?lang={lang}"/>')
        xml.append('  </url>')
    xml.append('</urlset>')
    return '\n'.join(xml), 200, {'Content-Type': 'application/xml'}


@app.route('/sitemap/partner-<slug>.xml')
def sitemap_partner(slug):
    """Per-partner sitemap. Lists every /learn/<slug> for courses owned
    by this partner, plus the partner page and its /courses index."""
    partner = Partner.query.filter_by(slug=slug).first_or_404()
    base = request.host_url.rstrip('/')
    courses = Course.query.filter_by(partner_id=partner.id).order_by(
        Course.id).all()
    xml = ['<?xml version="1.0" encoding="UTF-8"?>',
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
           'xmlns:xhtml="http://www.w3.org/1999/xhtml">']
    static_paths = [f'/partner/{slug}', f'/partner/{slug}/courses']
    for p in static_paths:
        xml.append(f'  <url><loc>{base}{p}</loc>')
        for lang in R7_LOCALES:
            xml.append(f'    <xhtml:link rel="alternate" hreflang="{lang}" '
                       f'href="{base}{p}?lang={lang}"/>')
        xml.append('  </url>')
    for c in courses:
        xml.append(f'  <url><loc>{base}/learn/{c.slug}</loc>'
                   f'<lastmod>{c.sort_date}</lastmod></url>')
    xml.append('</urlset>')
    return '\n'.join(xml), 200, {'Content-Type': 'application/xml'}


def _course_jsonld(course):
    """Build a schema.org/Course JSON-LD dict for a course. Exposed in
    the template via context — the SEO-Course-schema tasks check for
    `provider`, `courseCode`, `timeRequired`, `educationalCredentialAwarded`
    and `inLanguage` on this object."""
    provider = {
        '@type': ('CollegeOrUniversity'
                  if (course.partner and course.partner.partner_type == 'university')
                  else 'Organization'),
        'name': course.partner.name if course.partner else 'Coursera',
        'sameAs': (f'{request.host_url.rstrip("/")}/partner/'
                   f'{course.partner.slug}' if course.partner else
                   request.host_url.rstrip('/')),
    }
    # ISO-8601 PT for duration_hours.
    duration_iso = f'PT{int(course.duration_hours or 1)}H'
    # courseCode = stable, derived from id — matches /certificate verify code.
    code = f'COUR-{course.id:06d}'
    credential = {
        'Course': 'CompletionCertificate',
        'Specialization': 'Specialization Certificate',
        'Professional Certificate': 'Professional Certificate',
        'Guided Project': 'CompletionCertificate',
        'Degree': course.degree_type or 'Degree',
    }.get(course.course_type, 'CompletionCertificate')
    return {
        '@context': 'https://schema.org',
        '@type': 'Course',
        'name': course.title,
        'description': (course.description or course.title)[:400],
        'provider': provider,
        'courseCode': code,
        'timeRequired': duration_iso,
        'educationalCredentialAwarded': credential,
        'inLanguage': R7_LOCALES,
        'aggregateRating': {
            '@type': 'AggregateRating',
            'ratingValue': course.rating,
            'reviewCount': course.review_count,
        },
        'url': f'{request.host_url.rstrip("/")}/learn/{course.slug}',
    }


@app.route('/learn/<slug>/captions')
@app.route('/learn/<slug>/captions/<int:week>')
def course_captions(slug, week=1):
    """Caption-language picker for a course. Lists all 11 caption tracks
    (en, es, zh, ja, ar, fr, de, pt, ko, hi, ru) for a given lecture week
    — the multilingual-captions tasks check this page renders all 11
    language labels."""
    course = Course.query.filter_by(slug=slug).first_or_404()
    mods = course.modules
    if not mods:
        abort(404)
    week = max(1, min(week, len(mods)))
    module = mods[week - 1]
    caption_langs = [
        ('en', 'English',           'English captions reviewed by native speakers.'),
        ('es', 'Español',           'Subtítulos en español — traducción profesional.'),
        ('zh', '中文（简体）',         '简体中文字幕 — 由专业团队翻译。'),
        ('ja', '日本語',              '日本語字幕 — プロの翻訳者による。'),
        ('ar', 'العربية',             'ترجمة احترافية إلى العربية.'),
        ('fr', 'Français',           'Sous-titres en français — traduction professionnelle.'),
        ('de', 'Deutsch',           'Deutsche Untertitel — von Profis übersetzt.'),
        ('pt', 'Português',         'Legendas em português — tradução profissional.'),
        ('ko', '한국어',              '한국어 자막 — 전문 번역가 검수.'),
        ('hi', 'हिन्दी',                'हिन्दी उपशीर्षक — पेशेवर अनुवाद।'),
        ('ru', 'Русский',            'Русские субтитры — профессиональный перевод.'),
    ]
    return render_template('captions.html', course=course, module=module,
                           week=week, caption_langs=caption_langs)


@app.route('/accessibility')
@app.route('/a11y')
def accessibility_statement():
    """WCAG 2.1 AA accessibility statement + per-feature compliance
    breakdown. Tasks check for the WCAG 2.1 AA badge + the captions /
    keyboard / screen-reader bullets."""
    return render_template('accessibility.html')


@app.route('/api/v1')
@app.route('/api/v1/')
@app.route('/api/v1/docs')
def public_api_docs():
    """Public Coursera-API doc landing page. Lists the 6 public read-only
    endpoints (courses, partners, categories, skills, certificates,
    sitemaps) with auth + rate-limit notes. The API-doc tasks check this
    page exposes the documented endpoints."""
    endpoints = [
        {'method': 'GET', 'path': '/api/v1/courses',
         'desc': 'List published courses. Filter by category, level, partner.',
         'rate_limit': '60 req/min', 'auth': 'public'},
        {'method': 'GET', 'path': '/api/v1/courses/<slug>',
         'desc': 'Fetch a single course by slug, with modules + JSON-LD.',
         'rate_limit': '60 req/min', 'auth': 'public'},
        {'method': 'GET', 'path': '/api/v1/partners',
         'desc': 'List publishing partners (universities, companies, institutions).',
         'rate_limit': '60 req/min', 'auth': 'public'},
        {'method': 'GET', 'path': '/api/v1/categories',
         'desc': 'List the 11 top-level Coursera categories.',
         'rate_limit': '120 req/min', 'auth': 'public'},
        {'method': 'GET', 'path': '/api/v1/skills/<slug>/courses',
         'desc': 'List courses tagged with a skill.',
         'rate_limit': '60 req/min', 'auth': 'public'},
        {'method': 'GET', 'path': '/api/v1/sitemaps',
         'desc': 'List per-partner sitemap URLs.',
         'rate_limit': '30 req/min', 'auth': 'public'},
    ]
    return render_template('coursera_api.html', endpoints=endpoints)


@app.route('/api/v1/categories')
@csrf.exempt
def api_categories():
    """Public read-only endpoint — list of categories."""
    return jsonify([{'slug': s, 'name': n} for (s, n) in [
        ('computer-science', 'Computer Science'),
        ('data-science', 'Data Science'),
        ('business', 'Business'),
        ('information-technology', 'Information Technology'),
        ('language-learning', 'Language Learning'),
        ('math-logic', 'Math and Logic'),
        ('physical-science', 'Physical Science and Engineering'),
        ('social-sciences', 'Social Sciences'),
        ('arts-humanities', 'Arts and Humanities'),
        ('health', 'Health'),
        ('personal-development', 'Personal Development'),
    ]])


@app.route('/api/v1/partners')
@csrf.exempt
def api_partners():
    """Public read-only endpoint — list of partners."""
    rows = Partner.query.order_by(Partner.slug).limit(500).all()
    return jsonify([{
        'slug': p.slug, 'name': p.name, 'country': p.country,
        'type': p.partner_type,
    } for p in rows])


# ─── Error handlers ───────────────────────────────────────────────────────────

@app.errorhandler(404)
def not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def server_error(e):
    return render_template('500.html'), 500


# ─── R8 observability + developer endpoints ──────────────────────────────────
# Lightweight surfaces real Coursera exposes to platform engineers and learning-
# tools integrators. All read-only or in-memory ack so the byte-identical seed
# DB is never mutated by request traffic.

# In-memory event sink — never persisted, reset on every gunicorn worker.
_R8_EVENT_SINK = []


@app.route('/healthz')
@app.route('/health')
@csrf.exempt
def healthz():
    """Kubernetes-style health endpoint. Returns the catalog size + a
    deterministic build identifier so the agent can verify the mirror is up
    and the catalog was seeded. Real Coursera exposes /healthz on every
    backend pod for liveness probing."""
    return jsonify({
        'status': 'ok',
        'service': 'coursera-mirror',
        'build': 'r8-iter8-2026',
        'courses': Course.query.count(),
        'partners': Partner.query.count(),
        'modules': CourseModule.query.count(),
        'commit': 'r8-polish',
    })


@app.route('/api/uptime')
@csrf.exempt
def api_uptime():
    """SLA / uptime status — deterministic figures used by the public
    status-page widget. Returns 99.95% last-30-days, no open incidents."""
    return jsonify({
        'status': 'operational',
        'uptime_30d_pct': 99.95,
        'uptime_90d_pct': 99.93,
        'last_incident': '2026-03-04T08:14:00Z',
        'last_incident_summary': 'Brief search latency in EU-WEST (resolved in 9 min).',
        'components': [
            {'name': 'Catalog API',        'status': 'operational'},
            {'name': 'Learner Web App',    'status': 'operational'},
            {'name': 'Video Streaming',    'status': 'operational'},
            {'name': 'Assignment Grading', 'status': 'operational'},
            {'name': 'Certificate Issuer', 'status': 'operational'},
            {'name': 'Mobile Sync',        'status': 'operational'},
        ],
    })


@app.route('/api/events', methods=['GET', 'POST'])
@csrf.exempt
def api_events():
    """Telemetry beacon — accepts JSON or form POSTs with `event` + payload,
    appends to an in-memory ring buffer (caps at 200), and serves the most
    recent events on GET. Never persisted, so the seed DB invariant holds."""
    if request.method == 'POST':
        if request.is_json:
            data = request.get_json(silent=True) or {}
        else:
            data = {k: v for k, v in request.form.items()}
        evt = {
            'event': str(data.get('event') or 'unknown')[:80],
            'path': str(data.get('path') or request.path)[:200],
            'ts_iso': '2026-05-26T12:00:00Z',  # frozen for byte-id determinism
            'session': str(data.get('session') or 'anon')[:64],
        }
        # Bounded ring buffer
        _R8_EVENT_SINK.append(evt)
        if len(_R8_EVENT_SINK) > 200:
            del _R8_EVENT_SINK[:len(_R8_EVENT_SINK) - 200]
        return jsonify({'accepted': True, 'sink_size': len(_R8_EVENT_SINK)})
    return jsonify({
        'total_received': len(_R8_EVENT_SINK),
        'recent': _R8_EVENT_SINK[-20:],
        'documented_events': [
            'lecture_video_played',
            'lecture_video_paused',
            'lecture_next_module_keystroke',
            'command_palette_open',
            'command_palette_jump',
            'skill_glossary_hover',
            'enrollment_completed',
            'certificate_issued',
        ],
    })


@app.route('/api/lti-callback', methods=['GET', 'POST'])
@csrf.exempt
def api_lti_callback():
    """LTI 1.3 OIDC callback stub. Real LMS integrations land here after the
    auth-redirect. We return a deterministic JWT-shaped payload so platform
    tooling can verify the callback shape without a real signing key."""
    iss = request.values.get('iss', 'https://coursera-mirror.local')
    login_hint = request.values.get('login_hint', 'lti-learner-001')
    target_uri = request.values.get('target_link_uri',
                                    request.host_url.rstrip('/') + '/')
    return jsonify({
        'lti_version': '1.3.0',
        'message_type': 'LtiResourceLinkRequest',
        'iss': iss,
        'aud': 'coursera-mirror-lti',
        'sub': login_hint,
        'target_link_uri': target_uri,
        'deployment_id': 'coursera-r8-deployment',
        'context': {
            'id': 'r8-course-context',
            'title': 'Coursera Mirror LTI Sandbox',
        },
        'resource_link': {
            'id': 'r8-resource-link-001',
            'title': 'Sample course resource link',
        },
        'callback_received': True,
    })


@app.route('/api/v2/graphql', methods=['GET', 'POST'])
@csrf.exempt
def api_v2_graphql():
    """GraphQL v2 stub — schema-introspection-light. Implements three
    queries the public docs list: `courses(first:N)`, `partners(first:N)`,
    `course(slug:"...")`. Anything else is rejected with the canonical
    GraphQL `errors` envelope."""
    if request.method == 'POST':
        body = request.get_json(silent=True) or {}
        query = (body.get('query') or '').strip()
    else:
        query = (request.args.get('query') or '').strip()
    if not query:
        return jsonify({
            'data': None,
            'errors': [{'message': 'No query string supplied.'}],
        }), 400
    # Course-slug lookup
    m = re.search(r'course\s*\(\s*slug\s*:\s*"([^"]+)"\s*\)', query)
    if m:
        c = Course.query.filter_by(slug=m.group(1)).first()
        if not c:
            return jsonify({'data': {'course': None}})
        return jsonify({'data': {'course': {
            'slug': c.slug, 'title': c.title,
            'level': c.level, 'category': c.category,
            'rating': c.rating, 'enrolled': c.enrolled_count,
            'partner': c.partner.name if c.partner else None,
        }}})
    # First-N courses
    m = re.search(r'courses\s*\(\s*first\s*:\s*(\d+)', query)
    if m:
        n = max(1, min(50, int(m.group(1))))
        rows = Course.query.order_by(Course.enrolled_count.desc()).limit(n).all()
        return jsonify({'data': {'courses': [
            {'slug': c.slug, 'title': c.title, 'rating': c.rating}
            for c in rows
        ]}})
    # First-N partners
    m = re.search(r'partners\s*\(\s*first\s*:\s*(\d+)', query)
    if m:
        n = max(1, min(50, int(m.group(1))))
        rows = Partner.query.order_by(Partner.slug).limit(n).all()
        return jsonify({'data': {'partners': [
            {'slug': p.slug, 'name': p.name, 'country': p.country,
             'type': p.partner_type}
            for p in rows
        ]}})
    return jsonify({
        'data': None,
        'errors': [{'message': 'Unsupported query. Try `courses(first:5){slug,title}`.'}],
    }), 400


@app.route('/webhook/enrollment', methods=['GET', 'POST'])
@csrf.exempt
def webhook_enrollment():
    """Enrollment webhook receiver — for integrations that want to be
    notified when a learner enrolls. POST is the canonical method; GET
    returns the documented payload shape + signature header docs."""
    if request.method == 'POST':
        if request.is_json:
            data = request.get_json(silent=True) or {}
        else:
            data = {k: v for k, v in request.form.items()}
        # Deterministic ack id so tasks can assert exact text
        course_slug = str(data.get('course_slug') or 'unknown')
        learner_id  = str(data.get('learner_id') or '0')
        digest = hashlib.md5(
            f'{course_slug}|{learner_id}'.encode()
        ).hexdigest()[:12].upper()
        return jsonify({
            'received': True,
            'ack_id': f'WH-ENROLL-{digest}',
            'course_slug': course_slug,
            'learner_id': learner_id,
            'signature_header': 'X-Coursera-Signature',
            'signature_scheme': 'HMAC-SHA256',
        })
    return jsonify({
        'webhook': 'enrollment',
        'method': 'POST',
        'content_type': 'application/json',
        'signature_header': 'X-Coursera-Signature',
        'signature_scheme': 'HMAC-SHA256',
        'expected_payload': {
            'course_slug': '<string>',
            'learner_id': '<int>',
            'enrolled_at': '<ISO8601>',
            'track': 'audit | paid | plus',
        },
        'documented_events': [
            'enrollment.created',
            'enrollment.completed',
            'enrollment.refunded',
        ],
    })


@app.route('/developer/lti-integration')
@app.route('/developer/lti')
def developer_lti_integration():
    """LTI 1.3 developer-docs landing page — onboarding instructions
    for LMS admins (Canvas / Blackboard / Moodle) to wire Coursera as
    an external tool. Tasks check this page exposes the LTI version
    + the OIDC callback URL."""
    return render_template('developer_lti.html',
                           lti_version='1.3.0',
                           oidc_callback_url='/api/lti-callback',
                           keyset_url='/api/lti/.well-known/jwks.json',
                           launch_url='/api/lti/launch',
                           deep_link_url='/api/lti/deep-link')


# ─── R6 edge-case routes ─────────────────────────────────────────────────────
# Six common "failure / blocked" states a learner can hit on Coursera, each
# rendered with a shared lightweight template so the agent can verify the
# message + the canonical remediation link.

R6_EDGE_CASE_COPY = {
    'deadline-passed': {
        'title': 'Enrollment Deadline Passed',
        'badge': 'Enrollment closed',
        'badge_class': 'edge-bad',
        'lede': (
            'The enrollment window for the current session of '
            '“{course}” closed on the listed application deadline. '
            'New enrollments are paused until the next cohort opens.'
        ),
        'bullets': [
            'Join the waitlist to be notified when the next cohort opens.',
            'Browse self-paced alternatives in {category} that you can start today.',
            'If you previously enrolled, your existing progress is preserved.',
        ],
        'remediation_action': 'Join waitlist',
    },
    'certificate-not-eligible': {
        'title': 'Certificate not yet eligible',
        'badge': 'Graded assignment required',
        'badge_class': 'edge-warn',
        'lede': (
            'You finished all videos in “{course}”, but the shareable '
            'Coursera certificate requires submitting and passing the '
            'graded capstone assignment.'
        ),
        'bullets': [
            'Submit the Week-4 graded assignment to unlock the certificate.',
            'Audit learners need to upgrade to the paid track before submission.',
            'After passing, your certificate ID is auto-issued and verifiable.',
        ],
        'remediation_action': 'Open graded assignment',
    },
    'audit-vs-paid': {
        'title': 'This feature is paid-track only',
        'badge': 'Audit track limit',
        'badge_class': 'edge-warn',
        'lede': (
            '“{course}” is available on the free Audit track, but the '
            'feature you tried to use (graded assignments, peer review, '
            'shareable certificate) is only included on the paid track '
            'or with a Coursera Plus subscription.'
        ),
        'bullets': [
            'Upgrade to the paid track to unlock graded assignments.',
            'Coursera Plus includes this course plus 7,000+ others.',
            'Auditing remains free — you keep access to lectures and readings.',
        ],
        'remediation_action': 'Compare tracks',
    },
    'peer-review-pending': {
        'title': 'Waiting on peer reviewers',
        'badge': '3 reviews needed',
        'badge_class': 'edge-info',
        'lede': (
            'Your submission to “{course}” has been queued for peer '
            'review. Coursera requires three independent reviewers '
            'before a grade is finalized — your queue position is '
            'shown below.'
        ),
        'bullets': [
            'Estimated review time: 5–10 days, depending on cohort size.',
            'Reviewing 3 peers in return moves your submission up the queue.',
            'You can update your submission until the third reviewer locks it.',
        ],
        'remediation_action': 'Review a peer',
    },
}


@app.route('/learn/<slug>/edge/<state>')
def course_edge_case(slug, state):
    """Render one of the per-course edge states (deadline, cert-not-eligible,
    audit-vs-paid, peer-review-pending) for the given course."""
    course = Course.query.filter_by(slug=slug).first_or_404()
    copy = R6_EDGE_CASE_COPY.get(state)
    if not copy:
        from flask import abort
        abort(404)
    lede = copy['lede'].format(course=course.title, category=course.category or 'this category')
    bullets = [b.format(course=course.title, category=course.category or 'this category')
               for b in copy['bullets']]
    queue_position = 1 + (course.id * 7 + len(state)) % 12
    estimated_days = 4 + (course.id * 3 + len(state)) % 8
    return render_template('course_edge_state.html',
                           course=course, state=state, copy=copy,
                           lede=lede, bullets=bullets,
                           queue_position=queue_position,
                           estimated_days=estimated_days)


# Convenience aliases — direct slugs are easier for an agent to compose.
@app.route('/learn/<slug>/deadline-passed')
def course_deadline_passed(slug):
    return course_edge_case(slug, 'deadline-passed')


@app.route('/learn/<slug>/certificate-not-eligible')
def course_cert_not_eligible(slug):
    return course_edge_case(slug, 'certificate-not-eligible')


@app.route('/learn/<slug>/audit-vs-paid')
def course_audit_vs_paid(slug):
    return course_edge_case(slug, 'audit-vs-paid')


@app.route('/learn/<slug>/peer-review-pending')
def course_peer_review_pending(slug):
    return course_edge_case(slug, 'peer-review-pending')


# Profile-level financial-aid edge — a learner's application is reviewed and
# either approved, pending, or rejected. Deterministic outcome keyed on user id.
@app.route('/financial-aid')
@app.route('/financial-aid/<status>')
def financial_aid(status=None):
    """Financial-aid application status page. Without an explicit status,
    derive it deterministically from the current user id (if logged in)
    or from the day-of-year of the seed reference date for anonymous
    viewers — keeps reset/byte identity intact."""
    valid = {'approved', 'pending', 'rejected', 'partial'}
    if status and status not in valid:
        status = None
    if status is None:
        if current_user.is_authenticated:
            keyed = (current_user.id * 11 + 5) % 4
        else:
            keyed = 2  # default to rejected for anon (mirrors the most
            # common task-able failure state without needing login)
        status = ['approved', 'pending', 'partial', 'rejected'][keyed]
    return render_template('financial_aid.html', status=status,
                           reference_date='2026-05-01')


# Partial credit transfer — when one Coursera course gives partial credit
# towards another (e.g. finishing the Foundations course unlocks 20% of
# the Advanced Specialization). Mirrors the "partial-credit-from-other-course"
# scenario in the task brief.
@app.route('/credit-transfer/<int:from_id>/<int:to_id>')
def credit_transfer(from_id, to_id):
    src = Course.query.get_or_404(from_id)
    dst = Course.query.get_or_404(to_id)
    # Deterministic credit percentage keyed on ids — between 10 and 50%.
    pct = 10 + ((from_id * 7 + to_id * 13) % 9) * 5
    transferable = (src.category == dst.category)
    return render_template('credit_transfer.html',
                           src=src, dst=dst, pct=pct,
                           transferable=transferable)


# Completion celebration / LinkedIn-share landing — the last step in the
# canonical "complete the course → share it" navigation chain. Auth not
# required so an agent can verify the share copy without logging in.
@app.route('/learn/<slug>/linkedin-share')
def course_linkedin_share(slug):
    course = Course.query.filter_by(slug=slug).first_or_404()
    return render_template('linkedin_share.html', course=course)


# ─── R9 routes (iter 9/10): Hands-On Labs / Career Academy / Industry Cert / ──
# AI Tutor / Study Groups / Analytics / Capstone Showcase. Read-only,
# deterministic — no migrations, byte-id reset stays intact.

def _r9_courses_by_track(track_tag, limit=120):
    """Return courses tagged with the given R9 track. Deterministic order."""
    rows = (Course.query.filter(Course.feature_tags.like(f'%"{track_tag}"%'))
            .order_by(Course.rating.desc(), Course.id.asc()).limit(limit).all())
    return rows


R9_CAREER_ACADEMY_ROLES = [
    ('software-engineer',  'Software Engineer',   'SWE Career Path',     'Computer Science',          'Software Engineer Academy'),
    ('product-manager',    'Product Manager',     'PM Career Path',      'Business',                  'Product Manager Academy'),
    ('ux-designer',        'UX Designer',         'UX Career Path',      'Arts and Humanities',       'UX Designer Academy'),
    ('data-scientist',     'Data Scientist',      'Data Sci Career',     'Data Science',              'Data Scientist Academy'),
    ('cloud-architect',    'Cloud Architect',     'Cloud Architect',     'Information Technology',    'Cloud Architect Academy'),
    ('cybersecurity-analyst','Cybersecurity Analyst','Cyber Analyst Path','Information Technology',   'Cybersecurity Analyst Academy'),
]

R9_INDUSTRY_CERTS = [
    ('ibm-2026',       'IBM Industry Certificate 2026',       'ibm'),
    ('google-2026',    'Google Industry Certificate 2026',    'google'),
    ('microsoft-2026', 'Microsoft Industry Certificate 2026', 'microsoft'),
    ('aws-2026',       'AWS Industry Certificate 2026',       'aws'),
    ('meta-2026',      'Meta Industry Certificate 2026',      'meta'),
]


@app.route('/labs')
@app.route('/labs/')
def labs_index():
    """Coursera Hands-On Labs hub — sandbox-style 2026 lab courses."""
    courses = _r9_courses_by_track('r9-hands-on-lab', limit=240)
    return render_template('labs_index.html', courses=courses)


@app.route('/labs/<slug>')
def lab_detail(slug):
    """Hands-On Lab detail — surfaces sandbox tools + course payload."""
    course = Course.query.filter_by(slug=slug).first_or_404()
    sandbox_url = f'https://cdn.coursera-mirror.local/sandbox/{course.slug}'
    tools = ['Browser IDE', 'Auto-graded checks', 'Sandbox reset', 'Captioned walkthrough']
    return render_template('lab_detail.html', course=course,
                           sandbox_url=sandbox_url, tools=tools)


@app.route('/career-academy')
@app.route('/career-academy/')
def career_academy_index():
    """Coursera Career Academy hub — six 2026 role tracks."""
    role_cards = []
    for slug, name, primary, category, domain in R9_CAREER_ACADEMY_ROLES:
        # Count matching courses for the role badge.
        n = (Course.query.filter(Course.feature_tags.like(
            '%"r9-career-academy"%')).filter(Course.title.like(f'{domain}%')).count())
        role_cards.append({'slug': slug, 'name': name, 'primary': primary,
                           'category': category, 'count': n,
                           'domain': domain})
    return render_template('career_academy_index.html', roles=role_cards)


@app.route('/career-academy/<role>')
def career_academy_role(role):
    match = next((r for r in R9_CAREER_ACADEMY_ROLES if r[0] == role), None)
    if not match:
        abort(404)
    slug, name, primary, category, domain = match
    rows = (Course.query.filter(Course.feature_tags.like('%"r9-career-academy"%'))
            .filter(Course.title.like(f'{domain}%'))
            .order_by(Course.rating.desc(), Course.id.asc()).limit(60).all())
    return render_template('career_academy_role.html',
                           role_slug=slug, role_name=name,
                           primary=primary, category=category,
                           courses=rows)


@app.route('/certificate/verify/<code>')
def certificate_verify_by_code(code):
    """Verify a Coursera certificate by code: COUR-<courseid>-<md5slug>.
    Falls back to lookup by raw integer id when the agent pastes the
    numeric course-id directly."""
    code = (code or '').strip().upper()
    course = None
    if code.startswith('COUR-'):
        parts = code.split('-')
        if len(parts) >= 3 and parts[1].isdigit():
            cid = int(parts[1])
            cand = Course.query.get(cid)
            if cand and hashlib.md5(cand.slug.encode()).hexdigest()[:6].upper() == parts[2]:
                course = cand
    elif code.isdigit():
        course = Course.query.get(int(code))
    if not course:
        abort(404)
    return certificate_verify(course.id)


@app.route('/coach/ai-tutor', methods=['GET', 'POST'])
@csrf.exempt
def coach_ai_tutor():
    """Mock Coursera AI Coach (Tutor). GET = form; POST = deterministic
    canned answer keyed on the question text — no LLM, no clock, byte-id safe."""
    answer = None
    question = ''
    citations = []
    if request.method == 'POST':
        question = (request.form.get('question') or '').strip()
        if question:
            h = hashlib.sha1(question.lower().encode()).hexdigest()
            buckets = [
                "Great question. Start with the Foundations module — the lab sandbox lets you run the exact pipeline without local setup.",
                "Here's a 3-step plan: (1) skim the syllabus, (2) finish the Hands-On Lab milestone, (3) submit the peer-reviewed capstone.",
                "Coursera AI Coach suggests pairing this concept with the recommended textbook (see ISBN in the syllabus) for spaced practice.",
                "Use the auto-graded sandbox to validate your approach, then post your write-up to the course discussion for peer feedback.",
                "Consider the Industry-Aligned Project track — it maps the skill directly onto a 2026 hiring rubric.",
            ]
            answer = buckets[int(h[:2], 16) % len(buckets)]
            # Cite up to 3 deterministic courses ranked by id stride.
            stride = max(1, Course.query.count() // 1500)
            seed = int(h[2:6], 16)
            ids = [(seed + stride * k) % Course.query.count() + 1 for k in range(3)]
            citations = [c for c in (Course.query.get(i) for i in ids) if c]
    return render_template('coach_ai_tutor.html', question=question,
                           answer=answer, citations=citations)


@app.route('/study-group/create', methods=['GET', 'POST'])
@csrf.exempt
def study_group_create():
    """Study group creation page. GET = form; POST = deterministic
    confirmation. No DB writes (byte-id safe) — only renders confirmation
    with a stable group code derived from the form payload."""
    confirmation = None
    if request.method == 'POST':
        course_slug = (request.form.get('course_slug') or '').strip()
        title       = (request.form.get('title') or '').strip()
        capacity    = (request.form.get('capacity') or '6').strip()
        meeting     = (request.form.get('meeting_time') or '').strip()
        course = Course.query.filter_by(slug=course_slug).first()
        if course and title:
            payload = f'{course_slug}|{title}|{capacity}|{meeting}'.encode()
            group_code = 'SG-' + hashlib.md5(payload).hexdigest()[:8].upper()
            confirmation = dict(group_code=group_code, course=course,
                                title=title, capacity=capacity,
                                meeting=meeting)
    # Surface recent courses to give the form a friendly course picker.
    sample = (Course.query.filter(Course.feature_tags.like('%"r9-hands-on-lab"%'))
              .order_by(Course.rating.desc(), Course.id.asc()).limit(12).all())
    return render_template('study_group_create.html',
                           confirmation=confirmation, sample=sample)


@app.route('/analytics/dashboard')
def analytics_dashboard():
    """Per-learner analytics dashboard. Falls back to a deterministic
    "preview" dataset when not logged in so an agent can land here and
    still see populated charts."""
    if current_user.is_authenticated:
        rows = (Enrollment.query.filter_by(user_id=current_user.id)
                .order_by(Enrollment.enrolled_at.desc()).all())
        enrollments = []
        for e in rows:
            c = Course.query.get(e.course_id)
            if c:
                enrollments.append({'course': c, 'progress': e.progress,
                                    'enrolled_at': e.enrolled_at})
        total = len(enrollments)
        completed = sum(1 for e in enrollments if (e['progress'] or 0) >= 95)
        in_progress = total - completed
        hours = round(sum((e['course'].duration_hours or 0) *
                          ((e['progress'] or 0) / 100.0)
                          for e in enrollments), 1)
        preview = False
    else:
        enrollments = []
        sample = (Course.query.filter(Course.is_featured.is_(True))
                  .order_by(Course.id.asc()).limit(6).all())
        for k, c in enumerate(sample):
            enrollments.append({'course': c, 'progress': 25 + (k * 13) % 75,
                                'enrolled_at': None})
        total = len(enrollments)
        completed = sum(1 for e in enrollments if e['progress'] >= 95)
        in_progress = total - completed
        hours = round(sum((e['course'].duration_hours or 0) *
                          (e['progress'] / 100.0) for e in enrollments), 1)
        preview = True
    return render_template('analytics_dashboard.html',
                           enrollments=enrollments, total=total,
                           completed=completed, in_progress=in_progress,
                           hours=hours, preview=preview)


@app.route('/capstone/showcase')
def capstone_showcase():
    """Top capstone projects across the catalog. Deterministic order."""
    rows = (Course.query.filter(Course.title.like('%Capstone%'))
            .order_by(Course.rating.desc(), Course.review_count.desc(),
                      Course.id.asc()).limit(48).all())
    return render_template('capstone_showcase.html', courses=rows)


@app.route('/peer-mentor/match', methods=['GET', 'POST'])
@csrf.exempt
def peer_mentor_match():
    """Peer-mentor matcher. GET = form; POST = deterministic match
    derived from skill + role. No DB writes."""
    match = None
    if request.method == 'POST':
        skill = (request.form.get('skill') or '').strip()
        role  = (request.form.get('role') or '').strip()
        if skill or role:
            h = hashlib.sha1(f'{skill}|{role}'.lower().encode()).hexdigest()
            mentor_id = int(h[:4], 16) % 999 + 1
            mentor_name = f'Mentor #{mentor_id:03d}'
            # Pick a deterministic course as the mentor's signature class.
            cnt = Course.query.count()
            cid = (int(h[4:8], 16) % cnt) + 1
            sig_course = Course.query.get(cid)
            match = dict(mentor_id=mentor_id, mentor_name=mentor_name,
                         skill=skill, role=role,
                         match_score=80 + int(h[8:10], 16) % 20,
                         sig_course=sig_course)
    return render_template('peer_mentor_match.html', match=match)


@app.route('/bundle/build', methods=['GET', 'POST'])
@csrf.exempt
def bundle_build_personalized():
    """Personalized bundle builder. Takes a goal + level and returns a
    deterministic 4-course bundle drawn from the live catalog."""
    bundle = None
    goal = ''
    level = 'Beginner'
    if request.method == 'POST':
        goal  = (request.form.get('goal') or '').strip()
        level = (request.form.get('level') or 'Beginner').strip()
        if goal:
            h = hashlib.sha1(f'{goal}|{level}'.lower().encode()).hexdigest()
            candidates = (Course.query
                          .filter(Course.level == level)
                          .order_by(Course.rating.desc(), Course.id.asc())
                          .limit(2000).all())
            if candidates:
                step = max(1, len(candidates) // 4)
                seed = int(h[:4], 16) % step
                picks = [candidates[(seed + i * step) % len(candidates)]
                         for i in range(4)]
                total_h = round(sum(c.duration_hours or 0 for c in picks), 1)
                bundle = dict(picks=picks, total_hours=total_h,
                              code='BNDL-' + h[:6].upper(),
                              goal=goal, level=level)
    return render_template('bundle_build.html', bundle=bundle,
                           goal=goal, level=level)


# ─── Seed data ────────────────────────────────────────────────────────────────

CATEGORY_COLORS = {
    'Computer Science': 'cat-cs',
    'Data Science': 'cat-ds',
    'Business': 'cat-biz',
    'Information Technology': 'cat-it',
    'Language Learning': 'cat-lang',
    'Math and Logic': 'cat-math',
    'Physical Science and Engineering': 'cat-eng',
    'Social Sciences': 'cat-soc',
    'Arts and Humanities': 'cat-arts',
    'Health': 'cat-health',
    'Personal Development': 'cat-pd',
}

def _color(cat):
    return CATEGORY_COLORS.get(cat, 'cat-cs')

def seed_database():
    if Partner.query.count() > 0:
        return

    # ── Partners ──────────────────────────────────────────────────────────────
    partners_data = [
        ('Stanford University', 'stanford', 'United States', 'university', 'Stanford'),
        ('Google', 'google', 'United States', 'company', 'Google'),
        ('IBM', 'ibm', 'United States', 'company', 'IBM'),
        ('Yale University', 'yale', 'United States', 'university', 'Yale'),
        ('Duke University', 'duke', 'United States', 'university', 'Duke'),
        ('University of Michigan', 'umich', 'United States', 'university', 'UMich'),
        ('Johns Hopkins University', 'jhu', 'United States', 'university', 'JHU'),
        ('Deeplearning.AI', 'deeplearningai', 'United States', 'company', 'DeepLearning.AI'),
        ('University of Maryland', 'umd', 'United States', 'university', 'UMD'),
        ('Technical University of Munich', 'tum', 'Germany', 'university', 'TUM'),
        ('The Museum of Modern Art', 'moma', 'United States', 'institution', 'MoMA'),
        ('University of Melbourne', 'umelbourne', 'Australia', 'university', 'UMelbourne'),
        ('Macquarie University', 'macquarie', 'Australia', 'university', 'Macquarie'),
        ('University of Sydney', 'usyd', 'Australia', 'university', 'USyd'),
        ('UNSW Sydney', 'unsw', 'Australia', 'university', 'UNSW'),
        ('Deakin University', 'deakin', 'Australia', 'university', 'Deakin'),
        ('Monash University', 'monash', 'Australia', 'university', 'Monash'),
        ('Australian National University', 'anu', 'Australia', 'university', 'ANU'),
        ('University of Illinois Urbana-Champaign', 'uiuc', 'United States', 'university', 'UIUC'),
        ('University of California, Davis', 'ucdavis', 'United States', 'university', 'UC Davis'),
        ('University of California, San Diego', 'ucsd', 'United States', 'university', 'UCSD'),
        ('University of California, Irvine', 'uci', 'United States', 'university', 'UC Irvine'),
        ('Columbia University', 'columbia', 'United States', 'university', 'Columbia'),
        ('Meta', 'meta', 'United States', 'company', 'Meta'),
        ('Microsoft', 'microsoft', 'United States', 'company', 'Microsoft'),
        ('Amazon Web Services', 'aws', 'United States', 'company', 'AWS'),
        ('Salesforce', 'salesforce', 'United States', 'company', 'Salesforce'),
        ('Rice University', 'rice', 'United States', 'university', 'Rice'),
        ('Vanderbilt University', 'vanderbilt', 'United States', 'university', 'Vanderbilt'),
        ('University at Buffalo', 'ubuffalo', 'United States', 'university', 'UBuffalo'),
        ('University of Minnesota', 'umn', 'United States', 'university', 'UMN'),
        ('University of Colorado Boulder', 'cuboulder', 'United States', 'university', 'CU Boulder'),
        ('Georgia Institute of Technology', 'gatech', 'United States', 'university', 'Georgia Tech'),
        ('Arizona State University', 'asu', 'United States', 'university', 'ASU'),
        ('Princeton University', 'princeton', 'United States', 'university', 'Princeton'),
        ('University of Toronto', 'utoronto', 'Canada', 'university', 'UToronto'),
        ('University of Pennsylvania', 'upenn', 'United States', 'university', 'UPenn'),
        ('University of Florida', 'ufl', 'United States', 'university', 'UFL'),
        ('University of London', 'ulondon', 'United Kingdom', 'university', 'ULondon'),
        ('Commonwealth Bank', 'commbank', 'Australia', 'company', 'CommBank'),
        ('PwC', 'pwc', 'Australia', 'company', 'PwC'),
        ('EIT Digital', 'eitdigital', 'Germany', 'institution', 'EIT Digital'),
        ('Macquarie Bank', 'macquariebank', 'Australia', 'company', 'Macquarie Bank'),
        ('University of Western Australia', 'uwa', 'Australia', 'university', 'UWA'),
        ('RMIT University', 'rmit', 'Australia', 'university', 'RMIT'),
        ('University of Queensland', 'uq', 'Australia', 'university', 'UQ'),
        ('University of Adelaide', 'uadelaide', 'Australia', 'university', 'UAdl'),
        ('Atlassian', 'atlassian', 'Australia', 'company', 'Atlassian'),
    ]
    pid = {}
    for name, slug, country, ptype, short in partners_data:
        p = Partner(name=name, slug=slug, country=country,
                    partner_type=ptype, short_name=short)
        db.session.add(p)
        db.session.flush()
        pid[slug] = p.id
    db.session.commit()

    # ── Helper ────────────────────────────────────────────────────────────────
    def add_course(title, slug, partner_slug, course_type, level, category,
                   duration_text, duration_weeks, duration_hours,
                   rating, review_count, enrolled_count,
                   is_free, has_certificate, credit_eligible,
                   instructor, instructor_title, description,
                   skills, what_you_learn, feature_tags,
                   is_featured=False, is_new=False, sort_date='2024-01-01',
                   degree_type='', subcategory=''):
        c = Course(
            title=title, slug=slug,
            partner_id=pid.get(partner_slug),
            course_type=course_type, level=level,
            category=category, subcategory=subcategory,
            duration_text=duration_text,
            duration_weeks=duration_weeks, duration_hours=duration_hours,
            rating=rating, review_count=review_count,
            enrolled_count=enrolled_count,
            is_free=is_free, has_certificate=has_certificate,
            credit_eligible=credit_eligible,
            instructor=instructor, instructor_title=instructor_title,
            description=description,
            skills=json.dumps(skills),
            what_you_learn=json.dumps(what_you_learn),
            feature_tags=json.dumps(feature_tags),
            is_featured=is_featured, is_new=is_new, sort_date=sort_date,
            degree_type=degree_type,
            color_class=_color(category),
        )
        db.session.add(c)
        db.session.flush()
        return c

    def add_modules(course, module_list):
        for w, entry in enumerate(module_list, 1):
            # 5-tuple: (title, desc, vids, reads, quizzes)
            # 6-tuple: (title, desc, vids, reads, quizzes, video_titles_list)
            if len(entry) == 6:
                title, desc, vids, reads, quizzes, vtitles = entry
                vt_json = json.dumps(vtitles)
            else:
                title, desc, vids, reads, quizzes = entry
                vt_json = '[]'
            m = CourseModule(course_id=course.id, week_number=w, title=title,
                             description=desc, videos_count=vids,
                             readings_count=reads, quizzes_count=quizzes,
                             video_titles=vt_json)
            db.session.add(m)

    def add_sub_courses(spec, titles):
        for i, (title, desc, dur) in enumerate(titles):
            s = SubCourse(specialization_id=spec.id, order_index=i+1,
                          title=title, description=desc, duration_text=dur)
            db.session.add(s)

    # ─────────────────────────────────────────────────────────────────────────
    # Task 15: Introduction to Mathematical Thinking (Stanford)
    c = add_course(
        'Introduction to Mathematical Thinking', 'introduction-to-mathematical-thinking',
        'stanford', 'Course', 'Beginner', 'Math and Logic',
        'Approx. 38 hours', 9.5, 38.0, 4.8, 22000, 750000,
        False, True, False,
        'Dr. Keith Devlin', 'Professor, Stanford University',
        'Learn how to think the way mathematicians do — a powerful cognitive process developed over thousands of years.',
        ['Mathematical Thinking', 'Logic', 'Number Theory', 'Proof Writing', 'Abstract Reasoning'],
        ['Understand mathematical proofs', 'Apply logical reasoning', 'Analyse number theory concepts',
         'Write formal mathematical arguments'],
        ['mathematics', 'logic', 'proof', 'number-theory', 'stanford'],
        True, False, '2023-09-01',
    )
    add_modules(c, [
        ('Introductory Material', 'Course orientation and getting started.', 3, 2, 1),
        ('Analysis of Language — The Mathematics of Everyday Language', 'Language, logic, and communication.', 5, 3, 2),
        ('Analysis of Language — Logical Connectives', 'Conjunctions, disjunctions, conditionals.', 4, 2, 1),
        ('What is a Number?', 'Natural numbers, integers, rationals, reals.', 5, 3, 2),
        ('Mathematical Reasoning in the Real World', 'Apply mathematical thinking to real problems.', 4, 3, 1),
        ('Proofs', 'Direct and indirect proofs, induction.', 6, 4, 2),
    ])

    # Task 16: Introduction to Finance: The Basics
    c = add_course(
        'Introduction to Finance: The Basics', 'introduction-to-finance-the-basics',
        'umich', 'Course', 'Beginner', 'Business',
        'Approx. 14 hours', 3.5, 14.0, 4.7, 15000, 300000,
        False, True, False,
        'Gautam Kaul', 'Professor of Finance, University of Michigan',
        'This course is the foundation of Finance. It introduces students to the three fundamental principles of finance.',
        ['Finance', 'Financial Analysis', 'Time Value of Money', 'Net Present Value', 'Risk and Return'],
        ['Understand key finance principles', 'Calculate time value of money', 'Evaluate investment decisions',
         'Understand risk and return tradeoffs'],
        ['finance', 'basics', 'beginner', 'investment', 'npv'],
        True, False, '2023-06-01',
    )
    add_modules(c, [
        ('The Three Pillars of Finance', 'Foundations and principles.', 5, 3, 1),
        ('The Time Value of Money', 'PV, FV, annuities, perpetuities.', 6, 4, 2),
        ('Stocks, Bonds, and Valuation', 'Asset valuation techniques.', 5, 3, 2),
        ('Risk and Return', 'Portfolio theory and the CAPM.', 4, 3, 1),
    ])

    # Task 19: Introduction to Psychology (Yale)
    c = add_course(
        'Introduction to Psychology', 'introduction-to-psychology',
        'yale', 'Course', 'Beginner', 'Social Sciences',
        'Approx. 14 hours', 3.5, 14.0, 4.9, 38000, 1200000,
        True, True, False,
        'Paul Bloom', 'Professor of Psychology, Yale University',
        'What are people most afraid of? What do our dreams mean? Are we natural-born racists? What makes us happy?',
        ['Psychology', 'Cognitive Psychology', 'Social Psychology', 'Behavioral Science', 'Mental Health'],
        ['Understand major psychological theories', 'Analyse human behaviour', 'Evaluate psychological research',
         'Apply psychology to everyday life'],
        ['psychology', 'beginner', 'free', 'yale', 'social-science', 'behaviour', 'cognitive'],
        True, False, '2023-01-01',
    )
    add_modules(c, [
        ('Introduction: What is Psychology?', 'Overview and history.', 4, 2, 1),
        ('Brain', 'Neuroscience and brain function.', 5, 3, 1),
        ('Development', 'Child development and learning.', 4, 2, 1),
        ('Mind', 'Consciousness, memory, and thought.', 5, 3, 2),
        ('Self and Others', 'Social and personality psychology.', 4, 2, 1),
        ('Good Life', 'Happiness and well-being.', 3, 2, 1),
    ])

    # Task 30: Modern Art & Ideas (MoMA)
    c = add_course(
        'Modern Art & Ideas', 'modern-art-ideas',
        'moma', 'Course', 'Beginner', 'Arts and Humanities',
        'Approx. 8 hours', 2.0, 8.0, 4.7, 8000, 200000,
        True, True, False,
        'MoMA Educators', 'The Museum of Modern Art',
        "Explore works in MoMA's collection and learn to interpret and discuss modern and contemporary art.",
        ['Art History', 'Visual Analysis', 'Modern Art', 'Art Criticism', 'Contemporary Art'],
        ['Analyse modern artworks', 'Understand art movements', 'Discuss art with confidence',
         'Explore MoMA collection highlights'],
        ['art', 'modern', 'moma', 'free', 'visual-art', 'museum', 'humanities'],
        False, False, '2023-04-01',
    )
    add_modules(c, [
        ('Looking at Art', 'How to observe and describe artworks.', 3, 2, 1),
        ('Materials and Techniques', 'How artists make art.', 4, 2, 1),
        ('Art in Society', 'Art and its cultural context.', 3, 2, 1),
        ('Themes in Modern Art', 'Identity, environment, abstraction.', 4, 3, 1),
    ])

    # Task 31: Exploring Quantum Physics (UMD)
    c = add_course(
        'Exploring Quantum Physics', 'exploring-quantum-physics',
        'umd', 'Course', 'Intermediate', 'Physical Science and Engineering',
        'Approx. 30 hours', 7.5, 30.0, 4.6, 6500, 150000,
        False, True, True,
        'Charles Clark', 'Professor of Physics, University of Maryland',
        'Explore Schrödinger equation solutions, measurement postulate, wave-particle duality, and basic quantum mechanics.',
        ['Quantum Mechanics', 'Wave Functions', 'Schrödinger Equation', 'Quantum States', 'Physics'],
        ['Solve the Schrödinger equation', 'Understand wave-particle duality',
         'Apply quantum measurement postulate', 'Describe quantum phenomena'],
        ['quantum', 'physics', 'umd', 'intermediate', 'wave-function', 'schrodinger'],
        False, False, '2023-02-01',
    )
    add_modules(c, [
        ('From Classical to Quantum', 'Introduction and historical background.', 4, 3, 1),
        ('The Schrödinger Equation', 'Formulating and solving the equation.', 5, 3, 2),
        ('Wave Functions and Probability', 'Normalisation and expectation values.', 5, 3, 2),
        ('Quantum Measurement', 'The measurement postulate.', 4, 2, 1),
        ('Applications', 'Particle in a box, harmonic oscillator.', 5, 3, 2),
    ])

    # Task 34: Essentials of Global Health (Yale)
    c = add_course(
        'Essentials of Global Health', 'essentials-of-global-health',
        'yale', 'Course', 'Beginner', 'Health',
        'Approx. 33 hours', 8.0, 33.0, 4.8, 25000, 700000,
        False, True, False,
        'Richard Skolnik', 'Lecturer in Global Affairs, Yale University',
        'A comprehensive introduction to global health that examines the key concepts, issues, and challenges.',
        ['Global Health', 'Public Health', 'Health Policy', 'Epidemiology', 'Health Systems'],
        ['Understand global health challenges', 'Analyse health systems worldwide',
         'Evaluate global health interventions', 'Apply health policy concepts'],
        ['global-health', 'public-health', 'yale', 'health-policy', 'beginner'],
        False, False, '2023-05-01',
    )
    add_modules(c, [
        ('Defining and Measuring Global Health', 'Concepts and metrics.', 5, 3, 1),
        ('The Determinants of Health', 'Social and environmental factors.', 4, 3, 1),
        ('Health Systems', 'Structure and function of health systems.', 5, 4, 2),
        ('Communicable Diseases', 'HIV, TB, malaria and more.', 6, 3, 2),
        ('Non-Communicable Diseases', 'Cancer, diabetes, heart disease.', 5, 3, 1),
        ('Health Equity and Policy', 'Addressing disparities.', 4, 3, 1),
    ])

    # Task 39: Space Safety (TUM)
    c = add_course(
        'Space Safety', 'space-safety',
        'tum', 'Course', 'Beginner', 'Physical Science and Engineering',
        'Approx. 15 hours', 4.0, 15.0, 4.5, 3500, 80000,
        False, True, False,
        'Prof. Ulrich Walter', 'Professor of Space Technology, TUM',
        'Learn about space safety issues including space debris, space environment, and astronaut safety.',
        ['Space Safety', 'Space Debris', 'Space Environment', 'Orbital Mechanics', 'Risk Assessment'],
        ['Identify major space safety challenges', 'Understand space debris mitigation',
         'Analyse radiation environments', 'Evaluate astronaut safety protocols'],
        ['space', 'safety', 'tum', 'debris', 'orbital', 'astronaut', 'engineering'],
        False, False, '2024-01-15',
    )
    add_modules(c, [
        ('Introduction to Space Safety',
         'Overview of space safety domain.',
         4, 3, 1,
         ['Welcome to Space Safety',
          'A Short History of Space Mishaps',
          'The Space Environment as a Hazard',
          'Course Roadmap and Assessment Overview']),
        ('Space Debris',
         'Origins, tracking, and mitigation of orbital debris.',
         7, 4, 2,
         ['Where Space Debris Comes From',
          'The Kessler Syndrome Explained',
          'Tracking Debris from the Ground',
          'On-Orbit Conjunction Assessment',
          'Active Debris Removal Concepts',
          'Post-Mission Disposal Guidelines',
          'Future Outlook for Orbital Sustainability']),
        ('Space Weather and Radiation',
         'Solar events, radiation belts.',
         5, 3, 1,
         ['The Sun as a Driver of Space Weather',
          'Solar Wind, CMEs, and Flares',
          'Earth\u2019s Magnetosphere and Radiation Belts',
          'Radiation Effects on Crew and Hardware',
          'Forecasting and Mitigation Strategies']),
        ('Astronaut Safety',
         'Life support and extravehicular activities.',
         5, 3, 2,
         ['Crew Health Risks in Microgravity',
          'Life-Support System Architecture',
          'EVA Operations and Suit Safety',
          'Emergency Procedures and Abort Modes',
          'Long-Duration Mission Considerations']),
    ])

    # Task 25: Relativity for beginners (Stanford)
    c = add_course(
        "Understanding Einstein: The Special Theory of Relativity",
        'understanding-einstein-special-relativity',
        'stanford', 'Course', 'Beginner', 'Physical Science and Engineering',
        'Approx. 18 hours', 4.5, 18.0, 4.8, 14000, 350000,
        False, True, False,
        'Larry Randles Lagerstrom', 'Instructor, Stanford University',
        'In this course we will seek to understand Einstein, especially the Special Theory of Relativity.',
        ['Special Relativity', 'Space-Time', 'Physics', 'Einstein', 'Relativity'],
        ['Understand special relativity', 'Analyse space-time diagrams',
         'Calculate time dilation and length contraction', 'Understand E=mc²'],
        ['relativity', 'einstein', 'physics', 'stanford', 'beginner', 'space-time'],
        False, False, '2023-08-01',
    )
    add_modules(c, [
        ('Introduction and Pre-Requisites', 'Setting the stage.', 3, 2, 1),
        ('The Principle of Relativity', 'Galilean relativity and its limits.', 4, 3, 1),
        ('Special Theory of Relativity', 'Postulates and their consequences.', 5, 4, 2),
        ('Space-Time Diagrams', 'Visualising relativistic effects.', 4, 3, 2),
        ('Time Dilation and Length Contraction', 'Core results.', 5, 3, 1),
        ('Mass-Energy Equivalence', 'E=mc² and applications.', 4, 3, 1),
    ])

    # Task 35: Sustainable Agriculture
    c = add_course(
        'Sustainable Agricultural Land Management', 'sustainable-agricultural-land-management',
        'ufl', 'Course', 'Beginner', 'Physical Science and Engineering',
        'Approx. 12 hours', 4.0, 12.0, 4.6, 5500, 120000,
        False, True, False,
        'Ann Wilkie', 'Professor, University of Florida',
        'Learn sustainable practices for agricultural land management including soil health, water conservation, and agroforestry.',
        ['Sustainable Agriculture', 'Soil Science', 'Water Management', 'Agroforestry', 'Land Use'],
        ['Implement sustainable farming practices', 'Manage soil health',
         'Conserve water in agriculture', 'Apply agroforestry principles'],
        ['sustainable', 'agriculture', 'soil', 'land-management', 'beginner', 'farming'],
        False, False, '2023-11-01',
    )
    add_modules(c, [
        ('Foundations of Sustainable Agriculture', 'Core principles and history.', 4, 3, 1),
        ('Soil Health and Management', 'Soil biology, composting, cover crops.', 5, 3, 2),
        ('Water Conservation', 'Irrigation efficiency and watershed management.', 4, 3, 1),
        ('Agroforestry Systems', 'Integrating trees and crops.', 4, 2, 1),
    ])

    # Task 9/23: AI Ethics (< 20 hours)
    c = add_course(
        'AI, Empathy & Ethics', 'ai-empathy-ethics',
        'ucsc' if 'ucsc' in pid else 'ucsantacruz' if 'ucsantacruz' in pid else 'stanford',
        'Course', 'Beginner', 'Computer Science',
        'Approx. 14 hours', 3.5, 14.0, 4.7, 7500, 180000,
        False, True, False,
        'Kathi Fisler', 'Professor of Computer Science',
        'Explore ethical questions and societal implications of artificial intelligence and machine learning.',
        ['AI Ethics', 'Machine Learning Ethics', 'Bias in AI', 'Fairness', 'Responsible AI'],
        ['Identify ethical issues in AI systems', 'Evaluate fairness in machine learning',
         'Apply ethical frameworks to AI design', 'Analyse bias and discrimination in AI'],
        ['ai-ethics', 'ethics', 'artificial-intelligence', 'bias', 'fairness', 'beginner'],
        False, False, '2024-02-01',
    )

    c2 = add_course(
        'Ethics of Artificial Intelligence', 'ethics-of-artificial-intelligence',
        'princeton', 'Course', 'Beginner', 'Computer Science',
        'Approx. 18 hours', 4.5, 18.0, 4.8, 9200, 220000,
        False, True, False,
        'Sandra Wachter', 'Professor of Technology and Regulation',
        'This course covers ethical considerations of AI including privacy, accountability, transparency, and fairness.',
        ['AI Ethics', 'Privacy', 'Algorithmic Accountability', 'Responsible AI', 'Technology Ethics'],
        ['Understand AI ethical principles', 'Analyse privacy risks',
         'Evaluate accountability mechanisms', 'Design responsible AI systems'],
        ['ai-ethics', 'ethics', 'artificial-intelligence', 'privacy', 'transparency', 'less-20-hours'],
        False, True, '2024-03-01',
    )

    # Task 0: 3D Printing (Beginner, 1-3 months, university)
    c = add_course(
        '3D Printing Revolution', '3d-printing-revolution',
        'uiuc', 'Course', 'Beginner', 'Physical Science and Engineering',
        '1-3 Months', 6.0, 30.0, 4.6, 8000, 180000,
        False, True, False,
        'Vishal Singh', 'Professor, University of Illinois',
        'Understand the technologies, applications, and implications of 3D printing and additive manufacturing.',
        ['3D Printing', 'Additive Manufacturing', 'CAD Design', 'Prototyping', 'Manufacturing'],
        ['Understand 3D printing technologies', 'Design parts for additive manufacturing',
         'Evaluate application domains', 'Analyse industry impact'],
        ['3d-printing', 'additive-manufacturing', 'beginner', 'university', '1-3-months'],
        False, False, '2023-07-01',
    )

    c = add_course(
        '3D Printing Applications', '3d-printing-applications',
        'uci', 'Course', 'Beginner', 'Physical Science and Engineering',
        '1-3 Months', 5.0, 25.0, 4.5, 6000, 120000,
        False, True, False,
        'Timothy Scott', 'Professor, UC Irvine',
        'Explore real-world applications of 3D printing in medicine, aerospace, architecture, and consumer goods.',
        ['3D Printing', 'Bioprinting', 'Aerospace Manufacturing', 'Design for Additive Manufacturing'],
        ['Apply 3D printing to real problems', 'Understand bioprinting', 'Design for manufacturing'],
        ['3d-printing', 'applications', 'beginner', '1-3-months'],
        False, False, '2023-09-01',
    )

    # Task 1: Python (Beginner)
    c = add_course(
        'Python for Everybody', 'python-for-everybody',
        'umich', 'Course', 'Beginner', 'Computer Science',
        'Approx. 19 hours', 4.8, 19.0, 4.8, 450000, 4500000,
        False, True, False,
        'Charles Severance', 'Clinical Professor, University of Michigan',
        'This course aims to teach everyone the basics of programming computers using Python. Built for absolute beginners — no prior coding background needed.',
        ['Python Programming', 'Data Structures', 'Networked Data', 'Databases', 'Visualization'],
        ['Install Python and start programming', 'Write Python functions and loops',
         'Manipulate files and data', 'Use Python for web scraping'],
        ['python', 'programming', 'beginner', 'no-experience', 'basics', 'fundamentals'],
        True, False, '2023-01-01',
    )

    c = add_course(
        'Programming for Everybody (Getting Started with Python)', 'programming-for-everybody',
        'umich', 'Course', 'Beginner', 'Computer Science',
        'Approx. 19 hours', 4.8, 19.0, 4.8, 400000, 3800000,
        True, True, False,
        'Charles Severance', 'Clinical Professor, University of Michigan',
        'This course aims to teach everyone the basics of programming using Python. No prior experience needed.',
        ['Python', 'Programming Basics', 'Variables', 'Conditionals', 'Functions'],
        ['Write basic Python programs', 'Understand variables and expressions',
         'Use conditionals and loops', 'Debug simple programs'],
        ['python', 'beginner', 'no-experience', 'free', 'programming-basics'],
        True, False, '2023-01-01',
    )

    # Task 2: Spanish Specialization (Beginner)
    spec_spanish = add_course(
        'Learn Spanish: Basic Spanish Vocabulary Specialization',
        'learn-spanish-basic-vocabulary-specialization',
        'ucdavis', 'Specialization', 'Beginner', 'Language Learning',
        '3 - 6 Months', 16.0, 70.0, 4.8, 25000, 600000,
        False, True, False,
        'University of California, Davis Instructors', 'UC Davis Language Program',
        'Master basic Spanish vocabulary and grammar through five hands-on courses.',
        ['Spanish', 'Spanish Grammar', 'Spanish Vocabulary', 'Conversational Spanish'],
        ['Communicate in basic Spanish', 'Use essential vocabulary', 'Form simple sentences',
         'Understand Spanish culture'],
        ['spanish', 'specialization', 'beginner', 'language', 'vocabulary'],
        True, False, '2023-03-01',
    )
    add_sub_courses(spec_spanish, [
        ('Spanish Vocabulary: Meeting People', 'Greetings, introductions, and small talk.', 'Approx. 10 hours'),
        ('Spanish Vocabulary: Around Town', 'Directions, transportation, and places.', 'Approx. 10 hours'),
        ('Spanish Vocabulary: At Home', 'Home, family, and daily routines.', 'Approx. 10 hours'),
        ('Spanish Vocabulary: At Work', 'Professional contexts and work vocabulary.', 'Approx. 10 hours'),
        ('Spanish Vocabulary: Nature and Environment', 'Outdoor vocabulary and descriptions.', 'Approx. 10 hours'),
    ])

    # Task 3: Python Data Science (newest sort)
    c = add_course(
        'Python for Data Science, AI & Development', 'python-for-data-science-ai-development',
        'ibm', 'Course', 'Beginner', 'Data Science',
        'Approx. 25 hours', 6.3, 25.0, 4.6, 42000, 1200000,
        False, True, False,
        'Joseph Santarcangelo', 'Data Scientist at IBM',
        'Learn Python for Data Science and AI. No prior programming experience required.',
        ['Python', 'Data Analysis', 'Numpy', 'Pandas', 'Machine Learning'],
        ['Use Python for data science', 'Work with NumPy and Pandas', 'Create visualizations',
         'Apply Python to AI development'],
        ['python', 'data-science', 'ai', 'ibm', 'beginner', 'pandas', 'numpy'],
        False, True, '2024-04-01',
    )

    c = add_course(
        'Python Data Science Fundamentals', 'python-data-science-fundamentals',
        'ibm', 'Course', 'Beginner', 'Data Science',
        'Approx. 18 hours', 4.5, 18.0, 4.7, 18000, 450000,
        False, True, False,
        'Alex Aklson', 'Data Scientist, IBM',
        'Build a strong foundation in Python for data science analysis and visualization.',
        ['Python', 'Data Science', 'Pandas', 'Data Visualization', 'Jupyter'],
        ['Set up Jupyter notebooks', 'Manipulate data with Pandas', 'Create visualizations',
         'Apply statistical methods'],
        ['python', 'data-science', 'fundamentals', 'beginner', 'ibm'],
        False, True, '2024-05-01',
    )

    c = add_course(
        'Applied Data Science with Python Specialization', 'applied-data-science-python',
        'umich', 'Specialization', 'Intermediate', 'Data Science',
        '5 Months', 21.7, 90.0, 4.5, 55000, 800000,
        False, True, False,
        'Christopher Brooks', 'Lecturer, University of Michigan',
        'Gain new skills and applied insights with Python. Includes text mining, social network analysis, and machine learning.',
        ['Python', 'Data Science', 'Machine Learning', 'Text Mining', 'Social Network Analysis'],
        ['Apply Python to data science', 'Build machine learning models', 'Analyse text data',
         'Work with social network data'],
        ['python', 'data-science', 'applied', 'intermediate', 'michigan', 'specialization'],
        False, True, '2024-03-15',
    )

    # Task 4: Business Process Management (rating 4.7)
    c = add_course(
        'Business Process Management', 'business-process-management',
        'uq' if 'uq' in pid else 'vanderbilt',
        'Course', 'Beginner', 'Business',
        'Approx. 17 hours', 4.3, 17.0, 4.7, 12000, 350000,
        False, True, False,
        'Marcello La Rosa', 'Professor, University of Queensland',
        'Business processes are the lifeblood of an organization. Learn how to model, analyze, and improve them.',
        ['Business Process Management', 'Process Modeling', 'BPMN', 'Process Analysis', 'Workflow'],
        ['Model business processes with BPMN', 'Analyze process performance',
         'Improve and optimize workflows', 'Implement process management'],
        ['business-process', 'bpm', 'workflow', 'bpmn', 'beginner', 'management'],
        False, False, '2023-06-15',
    )

    # Task 5: C++ Specialization (Beginner)
    spec_cpp = add_course(
        'Coding for Everyone: C and C++ Specialization', 'coding-everyone-c-cpp',
        'ucsd', 'Specialization', 'Beginner', 'Computer Science',
        '4 Months', 17.4, 70.0, 4.6, 15000, 320000,
        False, True, False,
        'Idil Akin', 'Instructor, UC San Diego',
        'Master the fundamentals of C and C++ programming from scratch. No prior experience needed.',
        ['C Programming', 'C++ Programming', 'Object-Oriented Programming', 'Data Structures'],
        ['Write C programs', 'Use C++ classes and objects', 'Implement data structures',
         'Build real-world applications'],
        ['cpp', 'c-plus-plus', 'c-programming', 'beginner', 'specialization', 'coding'],
        False, False, '2023-07-01',
    )
    add_sub_courses(spec_cpp, [
        ('C for Everyone: Programming Fundamentals', 'Variables, types, control flow.', 'Approx. 14 hours'),
        ('C for Everyone: Structured Programming', 'Functions, arrays, pointers.', 'Approx. 14 hours'),
        ('C++ for C Programmers, Part A', 'Classes, templates, STL.', 'Approx. 16 hours'),
        ('C++ for C Programmers, Part B', 'Advanced OOP and design patterns.', 'Approx. 14 hours'),
    ])

    # Task 6: AI for Healthcare
    c = add_course(
        'AI for Medicine Specialization', 'ai-for-medicine',
        'deeplearningai', 'Specialization', 'Intermediate', 'Health',
        '3 Months', 13.0, 50.0, 4.7, 28000, 450000,
        False, True, False,
        'Andrew Ng', 'Founder, DeepLearning.AI',
        'Apply AI to medicine: diagnose diseases from medical images, predict patient outcomes, and understand medical text.',
        ['Medical AI', 'Computer Vision', 'NLP for Medicine', 'Clinical Data', 'Disease Diagnosis'],
        ['Build AI models for medical imaging', 'Predict patient outcomes',
         'Process clinical text', 'Evaluate medical AI systems'],
        ['ai', 'medicine', 'healthcare', 'deep-learning', 'medical-imaging', 'intermediate'],
        True, False, '2023-05-01',
    )

    c2 = add_course(
        'Artificial Intelligence for Healthcare', 'artificial-intelligence-healthcare',
        'stanford', 'Course', 'Intermediate', 'Health',
        'Approx. 20 hours', 5.0, 20.0, 4.6, 12000, 200000,
        False, True, False,
        'Nigam Shah', 'Professor of Biomedical Informatics, Stanford University',
        'Learn how AI is transforming healthcare including clinical decision support, genomics, and medical imaging.',
        ['Healthcare AI', 'Clinical Informatics', 'Medical Imaging AI', 'Genomics', 'EHR Analytics'],
        ['Apply machine learning to clinical data', 'Understand AI regulations in healthcare',
         'Build clinical NLP models', 'Evaluate AI safety in medicine'],
        ['ai', 'healthcare', 'clinical', 'stanford', 'medical', 'intermediate'],
        False, False, '2023-09-01',
    )
    add_modules(c2, [
        ('Introduction to AI in Healthcare', 'Overview of AI applications in medicine and clinical workflows.', 4, 3, 1),
        ('Medical Imaging with AI', 'Apply deep learning to radiology and pathology images.', 5, 3, 2),
        ('Clinical NLP and EHR Analytics', 'Process clinical notes and electronic health records with NLP.', 4, 3, 1),
        ('AI Ethics and Regulation in Medicine', 'Understand regulations, safety, and ethical considerations.', 3, 2, 1),
    ])

    # Task 7: Reinforcement Learning (Intermediate)
    spec_rl = add_course(
        'Reinforcement Learning Specialization', 'reinforcement-learning-specialization',
        'ualberta' if 'ualberta' in pid else 'umich',
        'Specialization', 'Intermediate', 'Computer Science',
        '4 Months', 17.4, 70.0, 4.7, 18000, 250000,
        False, True, False,
        'Martha White', 'Associate Professor, University of Alberta',
        'Learn the fundamentals of reinforcement learning and how to apply RL to real-world problems.',
        ['Reinforcement Learning', 'Q-Learning', 'Policy Gradient', 'Actor-Critic', 'MDP'],
        ['Implement RL algorithms', 'Solve MDPs', 'Apply policy gradient methods',
         'Build deep RL agents'],
        ['reinforcement-learning', 'rl', 'intermediate', 'q-learning', 'policy-gradient'],
        False, False, '2023-04-01',
    )

    c = add_course(
        'Fundamentals of Reinforcement Learning', 'fundamentals-reinforcement-learning',
        'umich', 'Course', 'Intermediate', 'Computer Science',
        'Approx. 14 hours', 3.5, 14.0, 4.8, 12000, 180000,
        False, True, False,
        'Adam White', 'Assistant Professor, University of Alberta',
        'Explore key principles of reinforcement learning including k-armed bandits, Markov decision processes, and dynamic programming.',
        ['Reinforcement Learning', 'Markov Decision Processes', 'Dynamic Programming', 'Value Functions'],
        ['Understand RL fundamentals', 'Implement k-armed bandit algorithms',
         'Solve MDPs with dynamic programming', 'Apply temporal difference learning'],
        ['reinforcement-learning', 'rl', 'intermediate', 'mdp', 'td-learning'],
        False, False, '2023-06-01',
    )

    # Task 8: R for Data Science (Free)
    c = add_course(
        'R Programming', 'r-programming',
        'jhu', 'Course', 'Beginner', 'Data Science',
        'Approx. 57 hours', 4.0, 57.0, 4.5, 85000, 1200000,
        True, True, False,
        'Roger D. Peng', 'Associate Professor, Johns Hopkins University',
        'In this course you will learn how to program in R and how to use R for effective data analysis.',
        ['R Programming', 'Data Analysis', 'Statistical Computing', 'Data Visualization', 'RStudio'],
        ['Write R programs', 'Manipulate and clean data', 'Create statistical summaries',
         'Build data visualizations'],
        ['r-programming', 'r', 'data-science', 'free', 'beginner', 'statistics', 'r-for-data-science'],
        False, False, '2023-02-01',
    )

    c = add_course(
        'R for Data Science and Machine Learning', 'r-data-science-machine-learning',
        'jhu', 'Course', 'Beginner', 'Data Science',
        'Approx. 20 hours', 5.0, 20.0, 4.6, 22000, 380000,
        True, True, False,
        'Brian Caffo', 'Professor, Johns Hopkins University',
        'Learn R for data science including data manipulation, visualization, and machine learning.',
        ['R', 'Data Science', 'Machine Learning', 'ggplot2', 'caret', 'tidyverse'],
        ['Use tidyverse for data wrangling', 'Build ML models in R',
         'Create publications-quality charts', 'Apply R to real datasets'],
        ['r', 'data-science', 'machine-learning', 'free', 'beginner', 'r-for-data-science', 'ggplot'],
        False, False, '2023-08-01',
    )

    # Task 10: Intro to AI (Beginner)
    c = add_course(
        'AI For Everyone', 'ai-for-everyone',
        'deeplearningai', 'Course', 'Beginner', 'Computer Science',
        'Approx. 6 hours', 1.5, 6.0, 4.8, 95000, 2300000,
        False, True, False,
        'Andrew Ng', 'CEO/Founder Landing AI, Founder deeplearning.ai',
        'AI is not only for engineers. This non-technical course teaches you what AI can and cannot do.',
        ['Artificial Intelligence', 'Machine Learning Strategy', 'AI Ethics', 'AI Projects', 'Deep Learning'],
        ['Understand AI capabilities and limitations', 'Build an AI strategy',
         'Navigate AI ethics', 'Identify AI opportunities in your organization'],
        ['ai', 'artificial-intelligence', 'beginner', 'non-technical', 'deeplearning', 'strategy'],
        True, False, '2023-01-01',
    )

    c = add_course(
        'Introduction to Artificial Intelligence (AI)', 'intro-artificial-intelligence',
        'ibm', 'Course', 'Beginner', 'Computer Science',
        'Approx. 9 hours', 2.3, 9.0, 4.7, 45000, 900000,
        False, True, False,
        'Rav Ahuja', 'Director of Offerings, IBM',
        'A gentle introduction to AI: what it is, why it matters, where it is used.',
        ['Artificial Intelligence', 'Machine Learning Basics', 'Natural Language Processing', 'Computer Vision'],
        ['Define artificial intelligence', 'Explain machine learning basics',
         'Identify AI use cases', 'Understand AI tools and applications'],
        ['ai', 'artificial-intelligence', 'beginner', 'introduction', 'ibm', 'intro'],
        False, False, '2023-03-01',
    )

    # Task 11: Project Management Specialization (university)
    spec_pm = add_course(
        'Engineering Project Management Specialization', 'engineering-project-management-specialization',
        'rice', 'Specialization', 'Beginner', 'Business',
        '5 Months', 21.7, 80.0, 4.7, 12000, 180000,
        False, True, False,
        'Rob Stone', 'Adjunct Professor, Rice University',
        'Learn project management principles and practices for engineering and technical projects.',
        ['Project Management', 'Risk Management', 'Scheduling', 'Stakeholder Management', 'Agile'],
        ['Plan and schedule projects', 'Manage project risks', 'Lead project teams',
         'Apply agile methodologies'],
        ['project-management', 'engineering', 'university', 'specialization', 'agile', 'scheduling'],
        False, False, '2023-05-01',
    )
    add_sub_courses(spec_pm, [
        ('Initiating and Planning Projects', 'Scope, schedule, and budget planning.', 'Approx. 14 hours'),
        ('Budgeting and Scheduling Projects', 'Earned value, scheduling techniques.', 'Approx. 16 hours'),
        ('Managing Project Risks and Changes', 'Risk identification and mitigation.', 'Approx. 14 hours'),
        ('Project Management Project', 'Capstone project applying all skills.', 'Approx. 16 hours'),
    ])

    # Task 12: Java basics (course not specialization)
    c = add_course(
        'Object Oriented Programming in Java', 'object-oriented-programming-java',
        'ucsd', 'Course', 'Beginner', 'Computer Science',
        'Approx. 42 hours', 10.5, 42.0, 4.6, 28000, 600000,
        False, True, False,
        'Leo Porter', 'Associate Teaching Professor, UC San Diego',
        'Learn the fundamentals of object-oriented programming in Java, the world\'s most popular programming language.',
        ['Java', 'Object-Oriented Programming', 'Data Structures', 'Algorithms', 'Classes'],
        ['Write Java programs', 'Create classes and objects', 'Implement interfaces',
         'Use Java collections'],
        ['java', 'object-oriented', 'programming', 'beginner', 'oop', 'basics', 'fundamentals'],
        False, False, '2023-04-01',
    )

    c = add_course(
        'Java Programming Basics', 'java-programming-basics',
        'ucsd', 'Course', 'Beginner', 'Computer Science',
        'Approx. 15 hours', 3.8, 15.0, 4.5, 15000, 320000,
        False, True, False,
        'Christine Alvarado', 'Teaching Professor, UC San Diego',
        'Get started with Java programming: variables, types, expressions, conditions, and loops.',
        ['Java', 'Programming Basics', 'Variables', 'Loops', 'Arrays'],
        ['Write basic Java programs', 'Understand variables and types',
         'Use loops and conditionals', 'Debug Java code'],
        ['java', 'basics', 'beginner', 'programming', 'java-basics'],
        False, False, '2023-06-01',
    )

    # Task 13: Python Specialization (skills)
    spec_py = add_course(
        'Python 3 Programming Specialization', 'python-3-programming-specialization',
        'umich', 'Specialization', 'Beginner', 'Computer Science',
        '5 Months', 21.7, 85.0, 4.8, 68000, 1100000,
        False, True, False,
        'Paul Resnick', 'Associate Professor, University of Michigan',
        'This specialization teaches the fundamentals of programming in Python 3.',
        ['Python', 'Functions', 'Files and Dictionaries', 'Data Collection', 'Classes'],
        ['Write Python 3 programs', 'Use files and dictionaries',
         'Scrape web data', 'Use classes and inheritance'],
        ['python', 'python3', 'specialization', 'beginner', 'programming', 'umich'],
        True, False, '2023-02-01',
    )
    add_sub_courses(spec_py, [
        ('Python Basics', 'Expressions, types, conditionals.', 'Approx. 19 hours'),
        ('Python Functions, Files, and Dictionaries', 'Functions and file I/O.', 'Approx. 19 hours'),
        ('Data Collection and Processing with Python', 'Web APIs and data processing.', 'Approx. 19 hours'),
        ('Python Classes and Inheritance', 'OOP with Python.', 'Approx. 19 hours'),
        ('Python Project: pillow, tesseract, and opencv', 'Image processing project.', 'Approx. 16 hours'),
    ])

    # Task 14: Project Management with Agile modules
    c = add_course(
        'Introduction to Project Management', 'introduction-to-project-management',
        'umelbourne', 'Course', 'Beginner', 'Business',
        'Approx. 10 hours', 2.5, 10.0, 4.7, 35000, 800000,
        False, True, False,
        'Margaret Tan', 'Senior Lecturer, University of Melbourne',
        'Learn the fundamentals of project management including planning, scheduling, risk management, and agile methods.',
        ['Project Management', 'Agile', 'Scrum', 'Risk Management', 'Scheduling'],
        ['Plan a project from start to finish', 'Apply agile methodologies',
         'Manage project risks', 'Use project management tools'],
        ['project-management', 'beginner', 'agile', 'scrum', 'introductory', 'scheduling'],
        False, False, '2023-07-01',
    )
    add_modules(c, [
        ('Introduction to Project Management', 'Overview and frameworks.', 3, 2, 1),
        ('Project Planning and Scheduling', 'WBS, Gantt charts, critical path.', 4, 3, 2),
        ('Agile Project Management', 'Scrum, sprints, and agile practices.', 5, 3, 2),
        ('Risk Management', 'Identifying and mitigating project risks.', 4, 2, 1),
    ])

    # Task 17: Machine Learning (Credit Eligible)
    c = add_course(
        'Machine Learning Specialization', 'machine-learning-specialization',
        'stanford', 'Specialization', 'Beginner', 'Data Science',
        '3 Months', 13.0, 50.0, 4.9, 150000, 2800000,
        False, True, True,
        'Andrew Ng', 'Adjunct Professor, Stanford University',
        'Build ML models with NumPy & scikit-learn, build & train neural networks with TensorFlow.',
        ['Machine Learning', 'Neural Networks', 'Decision Trees', 'Regression', 'Clustering'],
        ['Build supervised learning models', 'Train neural networks', 'Apply unsupervised learning',
         'Use best ML practices'],
        ['machine-learning', 'stanford', 'neural-networks', 'scikit-learn', 'credit-eligible'],
        True, False, '2023-01-01',
    )

    c = add_course(
        'Machine Learning with Python', 'machine-learning-python',
        'ibm', 'Course', 'Intermediate', 'Data Science',
        'Approx. 25 hours', 6.3, 25.0, 4.7, 68000, 950000,
        False, True, True,
        'Saeed Aghabozorgi', 'Senior Data Scientist, IBM',
        'This course dives into the basics of machine learning using Python, including regression, classification, and clustering.',
        ['Machine Learning', 'Python', 'Regression', 'Classification', 'Clustering', 'scikit-learn'],
        ['Apply ML algorithms', 'Build regression models', 'Implement classification',
         'Use scikit-learn'],
        ['machine-learning', 'python', 'ibm', 'intermediate', 'credit-eligible', 'supervised'],
        False, False, '2023-04-01',
    )

    # Task 18: JavaScript (Beginner, Certificate)
    c = add_course(
        'HTML, CSS, and Javascript for Web Developers', 'html-css-javascript-web-developers',
        'jhu', 'Course', 'Beginner', 'Computer Science',
        'Approx. 40 hours', 10.0, 40.0, 4.7, 35000, 750000,
        False, True, False,
        'Yaakov Chaikin', 'Adjunct Professor, Johns Hopkins University',
        'Do you realize that the only functionality of a web application that the user directly interacts with is through the web browser?',
        ['HTML', 'CSS', 'JavaScript', 'Web Development', 'Bootstrap'],
        ['Build web pages with HTML', 'Style with CSS and Bootstrap',
         'Add interactivity with JavaScript', 'Create dynamic web applications'],
        ['javascript', 'html', 'css', 'web-development', 'beginner', 'certificate', 'frontend'],
        False, False, '2023-03-01',
    )

    c = add_course(
        'JavaScript Algorithms and Data Structures', 'javascript-algorithms-data-structures',
        'meta', 'Professional Certificate', 'Beginner', 'Computer Science',
        '6 Months', 26.0, 100.0, 4.8, 22000, 400000,
        False, True, False,
        'Meta Technical Team', 'Meta Instructors',
        'Learn JavaScript programming language including data structures, algorithms, and modern JS features.',
        ['JavaScript', 'ES6', 'Data Structures', 'Algorithms', 'Functional Programming'],
        ['Master JavaScript fundamentals', 'Use ES6+ features',
         'Implement data structures', 'Write efficient algorithms'],
        ['javascript', 'algorithms', 'data-structures', 'beginner', 'meta', 'certificate', 'js'],
        False, False, '2023-06-01',
    )

    # Task 20: Blockchain (Intermediate, 1-4 weeks)
    c = add_course(
        'Blockchain Basics', 'blockchain-basics',
        'ubuffalo', 'Course', 'Intermediate', 'Computer Science',
        '1-4 Weeks', 2.0, 10.0, 4.6, 18000, 350000,
        False, True, False,
        'Bina Ramamurthy', 'Associate Professor, University at Buffalo',
        'A foundational course for understanding the components that make up the Bitcoin, Blockchain technology.',
        ['Blockchain', 'Bitcoin', 'Smart Contracts', 'Ethereum', 'Consensus Mechanisms'],
        ['Understand blockchain technology', 'Explain Bitcoin architecture',
         'Describe smart contracts', 'Analyse consensus mechanisms'],
        ['blockchain', 'basics', 'intermediate', 'bitcoin', 'ethereum', '1-4-weeks', 'technology'],
        False, False, '2023-05-01',
    )

    c = add_course(
        'Blockchain Technology', 'blockchain-technology',
        'ubuffalo', 'Course', 'Intermediate', 'Computer Science',
        '1-4 Weeks', 3.0, 12.0, 4.5, 12000, 200000,
        False, True, False,
        'Bina Ramamurthy', 'Associate Professor, University at Buffalo',
        'Explore the technical underpinnings of blockchain technology and how it enables trustless systems.',
        ['Blockchain Technology', 'Distributed Ledger', 'Cryptography', 'Smart Contracts', 'DApps'],
        ['Explain distributed ledger technology', 'Implement basic smart contracts',
         'Design blockchain solutions', 'Evaluate security tradeoffs'],
        ['blockchain', 'technology', 'intermediate', 'distributed-ledger', '1-4-weeks'],
        False, False, '2023-07-01',
    )

    # Task 21: Digital Marketing (Beginner)
    c = add_course(
        'Fundamentals of Digital Marketing', 'fundamentals-digital-marketing',
        'google', 'Course', 'Beginner', 'Business',
        'Approx. 40 hours', 10.0, 40.0, 4.7, 40000, 900000,
        True, True, False,
        'Google Career Certificates', 'Google',
        'Learn the fundamentals of digital marketing with this free course accredited by IAB Europe.',
        ['Digital Marketing', 'SEO', 'SEM', 'Social Media Marketing', 'Analytics'],
        ['Create a digital marketing strategy', 'Optimize for search engines',
         'Run social media campaigns', 'Use Google Analytics'],
        ['digital-marketing', 'marketing', 'beginner', 'google', 'free', 'seo', 'social-media'],
        False, False, '2023-03-01',
    )

    c = add_course(
        'Digital Marketing Specialization', 'digital-marketing-specialization',
        'uiuc', 'Specialization', 'Beginner', 'Business',
        '8 Months', 34.7, 130.0, 4.7, 30000, 600000,
        False, True, False,
        'Aric Rindfleisch', 'Professor, University of Illinois',
        'The Digital Marketing Specialization from University of Illinois covers digital marketing channels, tools, and strategies.',
        ['Digital Marketing', 'Content Marketing', 'Social Media', 'Email Marketing', 'Marketing Analytics'],
        ['Design a digital marketing strategy', 'Create content campaigns',
         'Manage social media', 'Analyse marketing data'],
        ['digital-marketing', 'specialization', 'beginner', 'uiuc', 'content', 'social-media'],
        False, False, '2023-01-01',
    )

    # Task 22: Human Resource Specialization
    spec_hr = add_course(
        'Human Resource Management: HR for People Managers Specialization',
        'human-resource-management-specialization',
        'umn', 'Specialization', 'Beginner', 'Business',
        '6 Months', 26.0, 100.0, 4.7, 22000, 450000,
        False, True, False,
        'John W. Budd', 'Professor, University of Minnesota',
        'Master human resource management: recruiting, performance management, and compensation.',
        ['Human Resources', 'Talent Acquisition', 'Performance Management', 'Compensation', 'Employee Relations'],
        ['Hire and develop employees', 'Design performance management systems',
         'Create compensation structures', 'Manage employee relations'],
        ['human-resource', 'hr', 'people-management', 'specialization', 'beginner', 'talent', 'recruitment'],
        False, False, '2023-04-01',
    )
    add_sub_courses(spec_hr, [
        ('Preparing to Manage Human Resources', 'Foundations of HR management.', 'Approx. 10 hours'),
        ('Recruiting, Hiring, and Onboarding Employees', 'The full hiring lifecycle.', 'Approx. 10 hours'),
        ('Managing Employee Performance', 'Performance evaluation and improvement.', 'Approx. 10 hours'),
        ('Managing Employee Compensation', 'Salary structures and benefits.', 'Approx. 10 hours'),
        ('Human Resources Management Capstone: HR for People Managers', 'Integrative capstone.', 'Approx. 12 hours'),
    ])

    # Task 24: Sustainability (Physical Science category)
    c = add_course(
        'Sustainable Development and Its Complexity', 'sustainable-development-complexity',
        'toronto' if 'toronto' in pid else 'utoronto',
        'Course', 'Beginner', 'Physical Science and Engineering',
        'Approx. 12 hours', 3.0, 12.0, 4.7, 14000, 300000,
        False, True, False,
        'Lucie Bhatt', 'Professor, University of Toronto',
        'Learn about sustainable development from a systems perspective, covering energy, climate, and social equity.',
        ['Sustainability', 'Sustainable Development', 'Climate Change', 'Systems Thinking', 'SDGs'],
        ['Understand sustainability concepts', 'Analyse complex systems',
         'Apply systems thinking to sustainability', 'Evaluate SDG progress'],
        ['sustainability', 'sustainable-development', 'climate', 'physical-science', 'beginner'],
        False, False, '2023-08-01',
        subcategory='Physical Science and Engineering',
    )

    c = add_course(
        'Sustainability and Development', 'sustainability-and-development',
        'umich', 'Course', 'Beginner', 'Physical Science and Engineering',
        'Approx. 14 hours', 3.5, 14.0, 4.6, 18000, 400000,
        False, True, False,
        'Jonathan Overpeck', 'Professor, University of Michigan',
        'Explore solutions to global sustainability challenges including energy, food, water, and urban systems.',
        ['Sustainability', 'Climate Change', 'Energy Policy', 'Environmental Science', 'SDGs'],
        ['Describe sustainability challenges', 'Evaluate energy solutions',
         'Analyse food and water systems', 'Understand urban sustainability'],
        ['sustainability', 'development', 'environment', 'physical-science', 'beginner', 'climate'],
        False, False, '2023-06-01',
        subcategory='Physical Science and Engineering',
    )
    add_modules(c, [
        ('Foundations of Sustainability', 'Course orientation: defining sustainability, the three pillars (environment, economy, society), and the planetary boundaries framework.', 5, 3, 1),
        ('Measuring Sustainability', 'Carbon footprint, ecological footprint, sustainability indicators, and how to measure progress against the SDGs.', 6, 4, 2),
        ('Energy Systems and Climate', 'Fossil fuels, renewables, and the transition to a low-carbon energy system.', 5, 3, 2),
        ('Food, Water, and Land', 'Agriculture, freshwater scarcity, and sustainable land use practices.', 5, 3, 1),
        ('Urban Sustainability', 'Cities as engines of sustainable development: transport, buildings, and waste systems.', 4, 2, 1),
        ('Pathways to the SDGs', 'Putting it all together: policy levers, finance, and individual action.', 4, 3, 2),
    ])

    # Task 26: Renewable Energy Specialization
    spec_re = add_course(
        'Renewable Energy and Green Building Entrepreneurship Specialization',
        'renewable-energy-green-building-specialization',
        'duke', 'Specialization', 'Beginner', 'Physical Science and Engineering',
        '4 Months', 17.4, 60.0, 4.6, 8500, 120000,
        False, True, False,
        'Bruce Usher', 'Professor, Columbia University',
        'Explore the economics and technology of renewable energy and green building. Ideal for future entrepreneurs.',
        ['Renewable Energy', 'Solar Energy', 'Wind Energy', 'Green Building', 'Energy Entrepreneurship'],
        ['Understand renewable energy technologies', 'Evaluate green building practices',
         'Develop energy business plans', 'Analyse energy markets'],
        ['renewable-energy', 'solar', 'wind', 'green-building', 'specialization', 'entrepreneurship'],
        False, False, '2023-05-01',
    )
    add_sub_courses(spec_re, [
        ('Solar Energy Basics', 'Photovoltaics and solar thermal systems.', 'Approx. 12 hours'),
        ('Wind Energy', 'Wind turbines and wind power systems.', 'Approx. 12 hours'),
        ('Batteries and the Future of Energy Storage', 'Battery technology and storage.', 'Approx. 12 hours'),
        ('Economics of Renewable Energy', 'Market analysis and business models.', 'Approx. 12 hours'),
        ('Renewable Energy Futures', 'Forward-looking survey of grid integration, hydrogen, ocean energy and policy pathways for a 100% renewable future.', 'Approx. 15 hours'),
    ])

    # Task 27: Data Visualization Specialization with project
    spec_dv = add_course(
        'Data Visualization with Tableau Specialization', 'data-visualization-tableau-specialization',
        'ucdavis', 'Specialization', 'Beginner', 'Data Science',
        '5 Months', 21.7, 80.0, 4.6, 18000, 350000,
        False, True, False,
        'Suk Brar', 'Instructor, UC Davis',
        'Learn to create compelling data visualizations with Tableau. Build a portfolio of data visualization projects.',
        ['Tableau', 'Data Visualization', 'Dashboard Design', 'Visual Analytics', 'Storytelling with Data'],
        ['Create Tableau dashboards', 'Design effective visualizations',
         'Tell stories with data', 'Build an analytics portfolio'],
        ['data-visualization', 'tableau', 'specialization', 'beginner', 'dashboard', 'project'],
        False, False, '2023-07-01',
    )
    add_sub_courses(spec_dv, [
        ('Fundamentals of Visualization with Tableau', 'Introduction to Tableau.', 'Approx. 14 hours'),
        ('Essential Design Principles for Tableau', 'Visual design best practices.', 'Approx. 14 hours'),
        ('Visual Analytics with Tableau', 'Advanced analytics features.', 'Approx. 14 hours'),
        ('Creating Dashboards and Storytelling with Tableau', 'Building interactive dashboards.', 'Approx. 14 hours'),
        ('Data Visualization with Tableau Project', 'Capstone project applying all skills.', 'Approx. 14 hours'),
    ])

    # Task 28: Guided Project Astrophysics (Advanced)
    c = add_course(
        'Analyzing Astrophysics Data with Python', 'analyzing-astrophysics-data-python',
        'jhu', 'Guided Project', 'Advanced', 'Physical Science and Engineering',
        'Less Than 2 Hours', 0.5, 1.5, 4.5, 2000, 25000,
        False, False, False,
        'Dr. Nathan Anderson', 'Research Scientist, JHU',
        'In this guided project, you will analyze real astrophysics datasets using Python, matplotlib, and astropy.',
        ['Astrophysics', 'Python', 'astropy', 'Data Analysis', 'matplotlib'],
        ['Load and process astrophysics data', 'Create astronomical plots',
         'Apply statistical methods to observational data', 'Use astropy library'],
        ['astrophysics', 'guided-project', 'advanced', 'python', 'astronomy', 'data-analysis'],
        False, False, '2024-01-01',
    )

    c = add_course(
        'Astrophysics: Exploring Exoplanets', 'astrophysics-exploring-exoplanets',
        'anu', 'Course', 'Intermediate', 'Physical Science and Engineering',
        'Approx. 21 hours', 5.3, 21.0, 4.8, 12000, 200000,
        False, True, False,
        'Paul Francis', 'Research Fellow, ANU',
        'Explore the science of exoplanets — planets outside our solar system.',
        ['Astrophysics', 'Exoplanets', 'Spectroscopy', 'Orbital Mechanics', 'Astronomy'],
        ['Understand exoplanet detection methods', 'Analyse light curves',
         'Calculate orbital parameters', 'Evaluate habitability'],
        ['astrophysics', 'exoplanets', 'astronomy', 'intermediate'],
        False, False, '2023-09-01',
    )

    # Task 32: Data Analysis (Beginner)
    c = add_course(
        'Data Analysis with Python', 'data-analysis-python',
        'ibm', 'Course', 'Beginner', 'Data Science',
        'Approx. 15 hours', 3.8, 15.0, 4.7, 45000, 800000,
        False, True, False,
        'Joseph Santarcangelo', 'Data Scientist, IBM',
        'Learn how to analyze data using Python. Topics include data preparation, simple statistical analysis, data visualization.',
        ['Data Analysis', 'Python', 'Pandas', 'NumPy', 'Matplotlib'],
        ['Load and prepare datasets', 'Perform exploratory data analysis',
         'Create visualizations', 'Build regression models'],
        ['data-analysis', 'python', 'beginner', 'pandas', 'numpy', 'ibm'],
        False, False, '2023-04-01',
    )

    c = add_course(
        'Introduction to Data Analytics', 'introduction-to-data-analytics',
        'ibm', 'Course', 'Beginner', 'Data Science',
        'Approx. 11 hours', 2.8, 11.0, 4.6, 38000, 650000,
        False, True, False,
        'Hima Vasudevan', 'Data Scientist, IBM',
        'Start your journey to become a Data Analyst. Learn about the data analysis process and the role of a data analyst.',
        ['Data Analytics', 'Excel', 'SQL', 'Python', 'Data Visualization'],
        ['Describe the data analysis process', 'Use Excel for data analysis',
         'Write basic SQL queries', 'Create simple visualizations'],
        ['data-analysis', 'analytics', 'beginner', 'introduction', 'ibm', 'excel', 'sql'],
        False, False, '2023-06-01',
    )

    # Task 33: IoT (Beginner, high rating)
    c = add_course(
        'Introduction to the Internet of Things and Embedded Systems',
        'introduction-internet-things-embedded-systems',
        'uci', 'Course', 'Beginner', 'Computer Science',
        'Approx. 15 hours', 3.8, 15.0, 4.6, 22000, 500000,
        False, True, False,
        'Ian Harris', 'Professor, UC Irvine',
        'The Internet of Things (IoT) refers to the connection of everyday objects to the internet.',
        ['Internet of Things', 'Embedded Systems', 'Arduino', 'Sensors', 'Networking'],
        ['Explain IoT concepts', 'Program Arduino microcontrollers',
         'Connect IoT devices to the internet', 'Design IoT systems'],
        ['iot', 'internet-of-things', 'embedded', 'beginner', 'arduino', 'sensors'],
        False, False, '2023-03-01',
    )

    c = add_course(
        'IoT (Internet of Things) Wireless & Cloud Computing Emerging Technologies',
        'iot-wireless-cloud-computing',
        'ubuffalo', 'Course', 'Beginner', 'Computer Science',
        'Approx. 17 hours', 4.3, 17.0, 4.7, 14000, 280000,
        False, True, False,
        'Amanpreet Kapoor', 'Assistant Professor, University at Buffalo',
        'Explore the Internet of Things from wireless communication to cloud computing integration.',
        ['IoT', 'Wireless Communication', 'Cloud Computing', 'Sensors', 'Edge Computing'],
        ['Design IoT architectures', 'Configure wireless IoT protocols',
         'Integrate IoT with cloud platforms', 'Process IoT data'],
        ['iot', 'internet-of-things', 'wireless', 'cloud', 'beginner', 'emerging-technology'],
        False, False, '2023-07-01',
    )

    # Task 36: Degrees (Master of Advanced Study in Engineering)
    c = add_course(
        'Master of Applied Data Science', 'master-applied-data-science',
        'umich', 'Degree', 'Advanced', 'Data Science',
        '12-36 Months', 52.0 * 4, 52.0 * 4 * 10, 4.8, 500, 5000,
        False, False, False,
        'Various Faculty', 'University of Michigan MADS Faculty',
        'The Master of Applied Data Science is a fully online degree from the University of Michigan.',
        ['Data Science', 'Machine Learning', 'Big Data', 'Statistical Modeling', 'Data Engineering'],
        ['Master data science techniques', 'Build production ML systems', 'Lead data science projects'],
        ['degree', 'master', 'data-science', 'online', 'michigan'],
        False, False, '2023-01-01',
        degree_type='Master',
    )

    c = add_course(
        'Master of Computer Science', 'master-computer-science-uiuc',
        'uiuc', 'Degree', 'Advanced', 'Computer Science',
        '12-24 Months', 52.0 * 2, 52.0 * 2 * 10, 4.9, 600, 8000,
        False, False, False,
        'Various Faculty', 'UIUC CS Faculty',
        'Earn a Master of Computer Science from University of Illinois Urbana-Champaign fully online.',
        ['Computer Science', 'Algorithms', 'Machine Learning', 'Distributed Systems', 'Data Engineering'],
        ['Master computer science fundamentals', 'Specialize in CS subfields', 'Complete a capstone project'],
        ['degree', 'master', 'computer-science', 'uiuc', 'online'],
        False, False, '2023-01-01',
        degree_type='Master',
    )

    c = add_course(
        'Master of Advanced Study in Engineering', 'master-advanced-study-engineering-ucberkeley',
        'columbia', 'Degree', 'Advanced', 'Physical Science and Engineering',
        '12-24 Months', 52.0 * 2, 52.0 * 2 * 10, 4.7, 200, 2000,
        False, False, False,
        'Various Faculty', 'Columbia Engineering Faculty',
        'The Master of Science in Engineering program provides advanced training in engineering disciplines.',
        ['Engineering', 'Systems Engineering', 'Project Management', 'Technical Leadership'],
        ['Apply advanced engineering principles', 'Lead engineering teams', 'Complete engineering research'],
        ['degree', 'master', 'engineering', 'advanced-study', 'mas'],
        False, False, '2023-01-01',
        degree_type='MasterAdvancedStudy',
    )
    c.application_deadline = 'May 15, 2026'

    c = add_course(
        'Master of Advanced Study in Engineering Sciences', 'mas-engineering-sciences',
        'rice', 'Degree', 'Advanced', 'Physical Science and Engineering',
        '18-24 Months', 52.0 * 2, 52.0 * 2 * 10, 4.6, 150, 1500,
        False, False, False,
        'Various Faculty', 'Rice University Faculty',
        'Rice University\'s online Master of Advanced Study covers engineering sciences with flexible scheduling.',
        ['Engineering Sciences', 'Applied Mathematics', 'Systems Design', 'Data Analysis'],
        ['Complete advanced engineering coursework', 'Conduct engineering analysis', 'Apply in professional context'],
        ['degree', 'master', 'advanced-study', 'engineering', 'mas', 'rice'],
        False, False, '2023-01-01',
        degree_type='MasterAdvancedStudy',
    )
    c.application_deadline = 'March 31, 2026'

    # Task 41: Bachelor's degrees
    c = add_course(
        'BSc Computer Science', 'bsc-computer-science-ulondon',
        'ulondon', 'Degree', 'Mixed', 'Computer Science',
        '36-72 Months', 52.0 * 6, 52.0 * 6 * 10, 4.7, 3000, 30000,
        False, False, False,
        'Various Faculty', 'University of London Faculty',
        'An internationally recognised online Bachelor\'s degree in Computer Science.',
        ['Computer Science', 'Programming', 'Algorithms', 'Databases', 'Software Engineering'],
        ['Earn a BSc in Computer Science', 'Master programming fundamentals', 'Build software systems'],
        ['degree', 'bachelor', 'computer-science', 'bsc', 'online', 'ulondon'],
        False, False, '2023-01-01',
        degree_type='Bachelor',
    )

    c = add_course(
        'Bachelor of Science in Business Administration', 'bsba-north-texas',
        'asu', 'Degree', 'Mixed', 'Business',
        '48-72 Months', 52.0 * 6, 52.0 * 6 * 10, 4.5, 2000, 15000,
        False, False, False,
        'Various Faculty', 'Arizona State University',
        'Earn a Bachelor\'s of Science in Business Administration from Arizona State University online.',
        ['Business Administration', 'Management', 'Marketing', 'Finance', 'Operations'],
        ['Develop business management skills', 'Understand financial management', 'Lead organisations'],
        ['degree', 'bachelor', 'business', 'bsba', 'asu', 'online'],
        False, False, '2023-01-01',
        degree_type='Bachelor',
    )

    c = add_course(
        'Bachelor of Applied Arts and Sciences', 'baas-utexas',
        'asu', 'Degree', 'Mixed', 'Social Sciences',
        '48-72 Months', 52.0 * 6, 52.0 * 6 * 10, 4.4, 1500, 12000,
        False, False, False,
        'Various Faculty', 'University of North Texas',
        'A flexible Bachelor of Applied Arts and Sciences designed for working adults.',
        ['Liberal Arts', 'Applied Sciences', 'Communication', 'Social Sciences', 'Interdisciplinary'],
        ['Complete a flexible bachelor\'s degree', 'Apply interdisciplinary knowledge', 'Advance your career'],
        ['degree', 'bachelor', 'arts', 'sciences', 'baas', 'online'],
        False, False, '2023-01-01',
        degree_type='Bachelor',
    )

    c = add_course(
        'Bachelor of Science in Data Science', 'bsds-arizona',
        'arizona' if 'arizona' in pid else 'asu',
        'Degree', 'Mixed', 'Data Science',
        '48-72 Months', 52.0 * 6, 52.0 * 6 * 10, 4.6, 1200, 10000,
        False, False, False,
        'Various Faculty', 'Arizona State University',
        'Earn a BS in Data Science to build skills in statistical analysis, programming, and machine learning.',
        ['Data Science', 'Statistics', 'Machine Learning', 'Data Engineering', 'Python'],
        ['Apply data science methods', 'Build ML models', 'Communicate with data'],
        ['degree', 'bachelor', 'data-science', 'bs', 'online', 'asu'],
        False, False, '2023-01-01',
        degree_type='Bachelor',
    )

    # Additional courses for broader category coverage ─────────────────────────

    # Machine Learning (for Task 17 extra results)
    c = add_course(
        'Deep Learning Specialization', 'deep-learning-specialization',
        'deeplearningai', 'Specialization', 'Intermediate', 'Data Science',
        '5 Months', 21.7, 85.0, 4.9, 220000, 3500000,
        False, True, True,
        'Andrew Ng', 'Founder, DeepLearning.AI',
        'Build neural networks and lead successful machine learning projects.',
        ['Deep Learning', 'Neural Networks', 'CNNs', 'RNNs', 'TensorFlow'],
        ['Build deep neural networks', 'Train and optimize models',
         'Apply CNNs to vision tasks', 'Build sequence models'],
        ['deep-learning', 'neural-networks', 'tensorflow', 'credit-eligible', 'intermediate'],
        True, False, '2023-01-01',
    )

    # Coursera Plus featured courses
    for title, slug, partner, cat, level, tags, rating, enrolled, is_feat, is_new, sdate in [
        ('Google Data Analytics Professional Certificate', 'google-data-analytics', 'google',
         'Data Science', 'Beginner', ['data-analytics', 'google', 'certificate', 'spreadsheets'], 4.8, 1200000, True, False, '2023-01-01'),
        ('Google Project Management: Professional Certificate', 'google-project-management', 'google',
         'Business', 'Beginner', ['project-management', 'google', 'certificate', 'agile'], 4.8, 1100000, True, False, '2023-01-01'),
        ('IBM Data Science Professional Certificate', 'ibm-data-science', 'ibm',
         'Data Science', 'Beginner', ['data-science', 'ibm', 'certificate', 'machine-learning'], 4.6, 550000, True, False, '2023-01-01'),
        ('Meta Front-End Developer Professional Certificate', 'meta-front-end-developer', 'meta',
         'Computer Science', 'Beginner', ['front-end', 'react', 'meta', 'certificate', 'javascript'], 4.7, 280000, True, False, '2023-01-01'),
        ('Google UX Design Professional Certificate', 'google-ux-design', 'google',
         'Business', 'Beginner', ['ux-design', 'google', 'design', 'figma'], 4.8, 380000, True, False, '2023-01-01'),
        ('Microsoft Azure Fundamentals AZ-900 Exam Prep', 'microsoft-azure-fundamentals', 'microsoft',
         'Information Technology', 'Beginner', ['azure', 'cloud', 'microsoft', 'certification', 'credit-eligible'], 4.7, 220000, False, True, '2024-03-01'),
        ('AWS Cloud Technical Essentials', 'aws-cloud-technical-essentials', 'aws',
         'Information Technology', 'Beginner', ['aws', 'cloud', 'amazon', 'credit-eligible'], 4.7, 180000, False, True, '2024-02-01'),
        ('Introduction to Generative AI', 'introduction-to-generative-ai', 'google',
         'Computer Science', 'Beginner', ['generative-ai', 'google', 'llm', 'ai', 'free'], 4.6, 850000, True, True, '2024-04-01'),
        ('What is Data Science?', 'what-is-data-science', 'ibm',
         'Data Science', 'Beginner', ['data-science', 'introduction', 'beginner', 'free'], 4.7, 750000, False, False, '2023-01-01'),
        ('The Science of Well-Being', 'the-science-of-well-being', 'yale',
         'Personal Development', 'Beginner', ['well-being', 'happiness', 'yale', 'free', 'psychology'], 4.9, 4000000, True, False, '2023-01-01'),
        ('Learning How to Learn', 'learning-how-to-learn', 'ucsd',
         'Personal Development', 'Beginner', ['learning', 'productivity', 'free', 'memory', 'science-of-learning'], 4.8, 2800000, True, False, '2023-01-01'),
        ('Financial Markets', 'financial-markets', 'yale',
         'Business', 'Beginner', ['finance', 'financial-markets', 'yale', 'stocks', 'bonds', 'free'], 4.8, 1600000, True, False, '2023-01-01'),
    ]:
        is_free_course = 'free' in tags
        add_course(
            title, slug, partner, 'Course', level, cat,
            'Approx. 10 hours', 2.5, 10.0,
            rating, int(rating * 10000), enrolled,
            is_free_course, True, 'credit-eligible' in tags,
            'Course Instructors', partner.title(),
            f'{title} — a popular Coursera course.',
            tags, [f'Gain skills in {t}' for t in tags[:3]], tags,
            is_feat, is_new, sdate,
        )

    db.session.commit()
    print(f"Seeded {Course.query.count()} courses, {Partner.query.count()} partners")


# ─── Benchmark users seed ─────────────────────────────────────────────────────

# Pinned reference date used for byte-identical seed reproducibility.
# Any seed-time `datetime.utcnow()` must be replaced with offsets from this
# so two independent rebuilds produce the same bytes (harden-env gotcha #3).
SEED_REF_DATE = datetime(2025, 11, 1, 12, 0, 0)


def seed_benchmark_users():
    """Idempotent. Creates 4 benchmark users with enrollments, saved courses,
    and reviews. Safe to call multiple times — skips if users already exist.

    Determinism: `random.seed(...)` is pinned and `SEED_REF_DATE` replaces
    `datetime.utcnow()` so every rebuild yields the same DB bytes."""
    if User.query.filter_by(email='alice.j@test.com').first():
        return  # already seeded

    # Pin RNG so progress / date offsets are deterministic across rebuilds.
    random.seed(20251101)

    def _get_course(slug_fragment):
        return Course.query.filter(Course.slug.ilike(f'%{slug_fragment}%')).first()

    def _get_course_title(title_fragment):
        return Course.query.filter(Course.title.ilike(f'%{title_fragment}%')).first()

    # ── User definitions ──────────────────────────────────────────────────────
    users_data = [
        ('Alice Johnson', 'alice.j@test.com', 'TestPass123!'),
        ('Bob Chen', 'bob.c@test.com', 'TestPass123!'),
        ('Carol Davis', 'carol.d@test.com', 'TestPass123!'),
        ('David Kim', 'david.k@test.com', 'TestPass123!'),
    ]
    users = {}
    # Pinned bcrypt hash for "TestPass123!" — required for byte-identical
    # rebuilds. bcrypt.generate_password_hash() mixes a random salt every
    # call, which would shift the users.password_hash bytes per process and
    # break the seed-DB md5 invariant. See harden-env/gotchas.md item #1.
    PINNED_TESTPASS_HASH = (
        '$2b$12$RwAC/sfwDHtccU//A20fde.uKkZK4Ptnjjyua2l2ktwI6uysAp3Ou'
    )
    for name, email, pw in users_data:
        u = User(name=name, email=email,
                 password_hash=PINNED_TESTPASS_HASH,
                 created_at=SEED_REF_DATE - timedelta(days=180))
        db.session.add(u)
        db.session.flush()
        users[email] = u

    # ── Alice: Python + Data Science focus, beginner ──────────────────────────
    alice = users['alice.j@test.com']

    # Enrollments
    alice_enrolled_slugs = [
        'python-for-everybody',
        'python-for-data-science-ai-development',
        'data-analysis-python',
        'introduction-to-data-analytics',
        'machine-learning-specialization',
    ]
    alice_enrolled_ids = []
    for sl in alice_enrolled_slugs:
        c = _get_course(sl)
        if c:
            e = Enrollment(user_id=alice.id, course_id=c.id,
                           progress=random.randint(10, 80),
                           enrolled_at=SEED_REF_DATE - timedelta(days=random.randint(20, 200)))
            db.session.add(e)
            alice_enrolled_ids.append(c.id)

    # Saved courses
    alice_saved_slugs = [
        'deep-learning-specialization',
        'machine-learning-python',
        'python-3-programming-specialization',
        'introduction-generative-ai',
        'supervised-machine',
    ]
    for sl in alice_saved_slugs:
        c = _get_course(sl)
        if c and c.id not in alice_enrolled_ids:
            db.session.add(SavedCourse(user_id=alice.id, course_id=c.id,
                saved_at=SEED_REF_DATE - timedelta(days=random.randint(5, 90))))

    # Reviews for enrolled courses
    alice_reviews = [
        ('python-for-everybody', 5.0, 'Excellent course for beginners. Clear explanations and great exercises.'),
        ('data-analysis-python', 4.5, 'Very practical. The pandas sections were especially useful for my work.'),
        ('machine-learning-specialization', 5.0, 'Andrew Ng is a fantastic teacher. Best ML course available online.'),
    ]
    for slug_frag, rating, body in alice_reviews:
        c = _get_course(slug_frag)
        if c:
            db.session.add(Review(user_id=alice.id, course_id=c.id,
                                  rating=rating, body=body,
                                  created_at=SEED_REF_DATE - timedelta(days=random.randint(10, 90))))

    # ── Bob: Web Dev + JavaScript focus, intermediate ─────────────────────────
    bob = users['bob.c@test.com']

    bob_enrolled_slugs = [
        'html-css-javascript',
        'javascript-algorithms',
        'programming-javascript',
        'meta-front-end',
        'object-oriented-programming-java',
    ]
    bob_enrolled_ids = []
    for sl in bob_enrolled_slugs:
        c = _get_course(sl)
        if c:
            e = Enrollment(user_id=bob.id, course_id=c.id,
                           progress=random.randint(20, 95),
                           enrolled_at=SEED_REF_DATE - timedelta(days=random.randint(20, 200)))
            db.session.add(e)
            bob_enrolled_ids.append(c.id)

    bob_saved_slugs = [
        'react' if _get_course('react') else 'javascript-algorithms',
        'python-for-everybody',
        'introduction-generative-ai',
        'introduction-to-project-management',
        'google-ux-design',
    ]
    for sl in bob_saved_slugs:
        c = _get_course(sl)
        if c and c.id not in bob_enrolled_ids:
            db.session.add(SavedCourse(user_id=bob.id, course_id=c.id,
                saved_at=SEED_REF_DATE - timedelta(days=random.randint(5, 90))))

    bob_reviews = [
        ('html-css-javascript', 4.5, 'Great foundation course. Covers HTML, CSS and JS in a balanced way.'),
        ('meta-front-end', 5.0, 'Meta certificate is well-recognized. The React sections are outstanding.'),
    ]
    for slug_frag, rating, body in bob_reviews:
        c = _get_course(slug_frag)
        if c:
            db.session.add(Review(user_id=bob.id, course_id=c.id,
                                  rating=rating, body=body,
                                  created_at=SEED_REF_DATE - timedelta(days=random.randint(5, 60))))

    # ── Carol: Business + Project Management + HR focus, beginner ────────────
    carol = users['carol.d@test.com']

    carol_enrolled_slugs = [
        'introduction-to-project-management',
        'google-project-management',
        'business-process-management',
        'introduction-to-finance-the-basics',
        'fundamentals-digital-marketing',
    ]
    carol_enrolled_ids = []
    for sl in carol_enrolled_slugs:
        c = _get_course(sl)
        if c:
            e = Enrollment(user_id=carol.id, course_id=c.id,
                           progress=random.randint(30, 100),
                           enrolled_at=SEED_REF_DATE - timedelta(days=random.randint(20, 200)))
            db.session.add(e)
            carol_enrolled_ids.append(c.id)

    carol_saved_slugs = [
        'human-resource-management-specialization',
        'engineering-project-management-specialization',
        'digital-marketing-specialization',
        'google-ux-design',
        'agile-project-management',
    ]
    for sl in carol_saved_slugs:
        c = _get_course(sl)
        if c and c.id not in carol_enrolled_ids:
            db.session.add(SavedCourse(user_id=carol.id, course_id=c.id,
                saved_at=SEED_REF_DATE - timedelta(days=random.randint(5, 90))))

    carol_reviews = [
        ('introduction-to-project-management', 5.0, 'Perfect for aspiring project managers. Great real-world examples.'),
        ('fundamentals-digital-marketing', 4.5, 'Good overview of digital marketing. Free and comprehensive.'),
        ('introduction-to-finance-the-basics', 4.0, 'Solid finance fundamentals. A bit theoretical but well taught.'),
    ]
    for slug_frag, rating, body in carol_reviews:
        c = _get_course(slug_frag)
        if c:
            db.session.add(Review(user_id=carol.id, course_id=c.id,
                                  rating=rating, body=body,
                                  created_at=SEED_REF_DATE - timedelta(days=random.randint(15, 120))))

    # ── David: AI/ML + Advanced topics focus, intermediate/advanced ───────────
    david = users['david.k@test.com']

    david_enrolled_slugs = [
        'machine-learning-specialization',
        'deep-learning-specialization',
        'ai-for-medicine',
        'reinforcement-learning-specialization',
        'machine-learning-python',
    ]
    david_enrolled_ids = []
    for sl in david_enrolled_slugs:
        c = _get_course(sl)
        if c:
            e = Enrollment(user_id=david.id, course_id=c.id,
                           progress=random.randint(40, 100),
                           enrolled_at=SEED_REF_DATE - timedelta(days=random.randint(20, 200)))
            db.session.add(e)
            david_enrolled_ids.append(c.id)

    david_saved_slugs = [
        'artificial-intelligence-healthcare',
        'applied-data-science-python',
        'fundamentals-reinforcement-learning',
        'trustworthy-ai',
        'introduction-generative-ai',
    ]
    for sl in david_saved_slugs:
        c = _get_course(sl)
        if c and c.id not in david_enrolled_ids:
            db.session.add(SavedCourse(user_id=david.id, course_id=c.id,
                saved_at=SEED_REF_DATE - timedelta(days=random.randint(5, 90))))

    david_reviews = [
        ('machine-learning-specialization', 5.0, 'The best ML course I have taken. Andrew Ng explains complex concepts clearly.'),
        ('deep-learning-specialization', 5.0, 'Excellent deep dive into neural networks. Highly recommended for ML practitioners.'),
        ('ai-for-medicine', 4.5, 'Fascinating application of AI. The medical imaging sections are exceptional.'),
        ('reinforcement-learning-specialization', 4.0, 'Challenging but rewarding. Good balance of theory and practice.'),
    ]
    for slug_frag, rating, body in david_reviews:
        c = _get_course(slug_frag)
        if c:
            db.session.add(Review(user_id=david.id, course_id=c.id,
                                  rating=rating, body=body,
                                  created_at=SEED_REF_DATE - timedelta(days=random.randint(5, 180))))

    db.session.commit()
    print(f"Seeded benchmark users: {[u.email for u in users.values()]}")



def run_startup_migrations():
    """Idempotent schema + data migrations run at startup."""
    import sqlite3 as _sqlite3
    db_path = os.path.join(BASE_DIR, 'instance', 'coursera.db')
    if not os.path.exists(db_path):
        return
    conn = _sqlite3.connect(db_path)
    cur = conn.cursor()
    try:
        cols = {r[1] for r in cur.execute("PRAGMA table_info(courses)").fetchall()}
        if 'testimonials_json' not in cols:
            cur.execute("ALTER TABLE courses ADD COLUMN testimonials_json TEXT DEFAULT '[]'")
            conn.commit()
            print("  + courses.testimonials_json")
        # R5: hover-preview video URL, recommended textbook ISBN, weekly load.
        cols = {r[1] for r in cur.execute("PRAGMA table_info(courses)").fetchall()}
        if 'preview_video_url' not in cols:
            cur.execute("ALTER TABLE courses ADD COLUMN preview_video_url VARCHAR(300) DEFAULT ''")
            conn.commit()
            print("  + courses.preview_video_url")
        if 'textbook_isbn' not in cols:
            cur.execute("ALTER TABLE courses ADD COLUMN textbook_isbn VARCHAR(40) DEFAULT ''")
            conn.commit()
            print("  + courses.textbook_isbn")
        if 'estimated_workload_hours_per_week' not in cols:
            cur.execute("ALTER TABLE courses ADD COLUMN estimated_workload_hours_per_week FLOAT DEFAULT 4.0")
            conn.commit()
            print("  + courses.estimated_workload_hours_per_week")
        cols = {r[1] for r in cur.execute("PRAGMA table_info(partners)").fetchall()}
        # country already exists — no-op, defensive check
    finally:
        conn.close()


def seed_testimonials_and_extras():
    """Seed testimonials for priority specializations, add Canva partner,
    and ensure instructor fields are consistent. Idempotent."""
    # Add Canva as an Australian partner if missing
    if not Partner.query.filter_by(slug='canva').first():
        db.session.add(Partner(name='Canva', slug='canva', country='Australia',
                               partner_type='company', short_name='Canva'))
        db.session.commit()

    # Ensure Gautam Kaul teaches more than one course (Task 16).
    # Must run BEFORE the testimonials loop so the loop covers the
    # Kaul course on the FIRST build — otherwise the 2nd build would
    # add testimonials and break byte-identical reset.
    kaul_courses = Course.query.filter(Course.instructor.like('%Gautam Kaul%')).all()
    if len(kaul_courses) < 2:
        umich = Partner.query.filter_by(slug='umich').first()
        new_slug = 'finance-for-non-finance-professionals'
        if not Course.query.filter_by(slug=new_slug).first():
            c2 = Course(
                title='Finance for Non-Finance Professionals',
                slug=new_slug,
                partner_id=umich.id if umich else None,
                course_type='Course',
                level='Beginner',
                category='Business',
                subcategory='Finance',
                duration_text='Approx. 9 hours',
                duration_weeks=2.0, duration_hours=9.0,
                rating=4.7, review_count=9800, enrolled_count=210000,
                is_free=False, has_certificate=True, credit_eligible=False,
                instructor='Gautam Kaul',
                instructor_title='Professor of Finance, University of Michigan',
                description=(
                    'A concise primer for professionals without a finance background. '
                    'Covers core principles of valuation, risk, and capital markets.'),
                skills=json.dumps(['Finance', 'Valuation', 'Risk', 'Capital Markets']),
                what_you_learn=json.dumps([
                    'Explain time value of money',
                    'Assess financial risk',
                    'Interpret corporate finance decisions',
                ]),
                feature_tags=json.dumps(['finance', 'non-finance', 'beginner', 'umich']),
                is_featured=False, is_new=False,
                sort_date='2024-08-01',
                color_class='cat-biz',
                testimonials_json=json.dumps([]),
            )
            db.session.add(c2)
            db.session.flush()
            # Backfill modules so this course matches the rest of the catalog.
            for w, (title, desc, vids, reads, quizzes) in enumerate([
                ('Time Value of Money', 'Discounting, compounding, and the mechanics of valuing future cash flows.', 4, 2, 1),
                ('Risk and Return', 'How risk is priced, the role of diversification, and CAPM intuition.', 4, 2, 1),
                ('Corporate Finance Decisions', 'NPV, IRR, capital budgeting and how firms allocate capital.', 4, 2, 1),
            ], 1):
                db.session.add(CourseModule(course_id=c2.id, week_number=w,
                    title=title, description=desc,
                    videos_count=vids, readings_count=reads, quizzes_count=quizzes,
                    video_titles=json.dumps([f'Lesson {w}.1: {title}', f'Lesson {w}.2: Worked examples'])))
            db.session.commit()
            print("  + added Gautam Kaul second course")

    # Seed testimonials for Specializations (and Professional Certificates)
    # that currently have no testimonials. We synthesize 3 per course using the
    # existing Review rows so everything is self-consistent and on-page.
    targets = Course.query.filter(
        Course.course_type.in_(['Specialization', 'Professional Certificate', 'Course'])
    ).all()
    updated = 0
    for c in targets:
        existing = c.get_testimonials()
        if existing:
            continue
        # Pull up to 3 real reviews from the DB for this course
        rows = Review.query.filter_by(course_id=c.id).order_by(
            Review.rating.desc()).limit(3).all()
        testimonials = []
        for r in rows:
            user = User.query.get(r.user_id)
            if not user:
                continue
            date_str = r.created_at.strftime('%b %Y') if r.created_at else ''
            testimonials.append({
                'quote': r.body,
                'name': user.name,
                'role': 'Learner',
                'date': date_str,
            })
        # If there aren't enough reviews, synthesize based on course title
        if len(testimonials) < 2:
            fallback_names = [
                ('Priya Sharma', 'Software Engineer'),
                ('Marcus Chen', 'Data Analyst'),
                ('Elena Rossi', 'Project Lead'),
            ]
            fallback_quotes = [
                f"{c.title} gave me a clear, practical foundation. I finished the program confident I could apply these skills at work.",
                f"A well-structured {(c.course_type or 'course').lower()}. The assignments in {c.title} pushed me to think, and the instructor feedback was excellent.",
                f"I recommend {c.title} to anyone starting out in {(c.category or 'this field').lower()} — the pace is steady and the examples are real-world.",
            ]
            for i in range(min(3, 3 - len(testimonials))):
                testimonials.append({
                    'quote': fallback_quotes[i],
                    'name': fallback_names[i][0],
                    'role': fallback_names[i][1],
                    'date': ['Nov 2025', 'Oct 2025', 'Sep 2025'][i],
                })
        c.testimonials_json = json.dumps(testimonials[:3])
        updated += 1
    if updated:
        db.session.commit()
        print(f"  + seeded testimonials on {updated} courses")


def _normalize_seed_db_layout():
    """Re-emit indexes in alpha order + VACUUM the SQLite file so two
    independent rebuilds produce byte-identical .db files. Gated on the
    presence of a sentinel pragma so it only runs once (the first build);
    subsequent warm restarts skip it. Sentinel bumped to 4 in R10 because
    seed_v11 backfills modules + missing R5 columns on legacy rows; the new
    backfill alters index page contents so the previous sentinel must miss.
    See harden-env/gotchas.md item #2."""
    from sqlalchemy import text
    conn = db.engine.connect()
    try:
        sentinel = conn.execute(text("PRAGMA user_version")).scalar()
        if sentinel == 4:
            return  # already normalized
        idx_rows = conn.execute(text(
            "SELECT name, sql FROM sqlite_master "
            "WHERE type='index' AND name LIKE 'ix_%'"
        )).fetchall()
        for name, _ in idx_rows:
            conn.execute(text(f"DROP INDEX IF EXISTS {name}"))
        for name, sql in sorted(idx_rows, key=lambda r: r[0]):
            if sql:
                conn.execute(text(sql))
        conn.execute(text("PRAGMA user_version = 4"))
        conn.commit()
        conn.execute(text("VACUUM"))
        conn.commit()
        print("  + normalized index order + VACUUM")
    finally:
        conn.close()


with app.app_context():
    # Schema migration must run BEFORE ORM queries hit the new column.
    # (sqlite `ALTER TABLE ... ADD COLUMN` on an existing DB.)
    # db.create_all() is a no-op for existing tables so run migration first
    # but we need the file to exist. Let create_all build fresh dbs; then
    # migrate; then seed.
    db.create_all()
    run_startup_migrations()
    seed_database()
    seed_benchmark_users()
    # Phase 2 bulk seed extension: extra reviewer users, partners,
    # courses, reviews, enrollments and saves. Idempotent + deterministic.
    # Must run BEFORE seed_testimonials_and_extras so that testimonials
    # cover the v2 courses on the FIRST build (otherwise the second run
    # would add testimonials and break byte-identical reset).
    from seed_extras import seed_v2 as _seed_v2
    _seed_v2(db, {
        'User': User, 'Partner': Partner, 'Course': Course,
        'CourseModule': CourseModule, 'SubCourse': SubCourse,
        'Enrollment': Enrollment, 'SavedCourse': SavedCourse,
        'Review': Review,
    })
    # R2 Phase: expand catalog to 1200+ courses (Advanced / Pro-Cert /
    # Guided-Project / extra Specialization variants + 12 new degrees).
    from seed_extras import seed_v3 as _seed_v3
    _seed_v3(db, {
        'User': User, 'Partner': Partner, 'Course': Course,
        'CourseModule': CourseModule, 'SubCourse': SubCourse,
        'Enrollment': Enrollment, 'SavedCourse': SavedCourse,
        'Review': Review,
    })
    # R3 expansion: ~100 new partners (30+ countries), ~1100 courses
    # (Capstone / Coursera-Plus bundles / Business catalog / Project Network
    # shorts / Career Certificates / Foundations+Advanced+Capstone trios /
    # 10 extra degrees). Must run BEFORE seed_testimonials_and_extras so the
    # testimonials loop covers v4 courses on the FIRST build.
    from seed_extras import seed_v4 as _seed_v4
    _seed_v4(db, {
        'User': User, 'Partner': Partner, 'Course': Course,
        'CourseModule': CourseModule, 'SubCourse': SubCourse,
        'Enrollment': Enrollment, 'SavedCourse': SavedCourse,
        'Review': Review,
    })
    # R4 polish: +60 partners + ~1500 courses (fresh R4 topics × 5 variants,
    # MOOC Classics, industry-specials, career pathways, university intros,
    # research seminars, micro-credentials). Idempotent + deterministic.
    from seed_extras import seed_v5 as _seed_v5
    _seed_v5(db, {
        'User': User, 'Partner': Partner, 'Course': Course,
        'CourseModule': CourseModule, 'SubCourse': SubCourse,
        'Enrollment': Enrollment, 'SavedCourse': SavedCourse,
        'Review': Review,
    })
    # R5 polish: 2024-2025 trending topics (GenAI / LLM / Agentic AI / Quantum
    # / Robotics) × deep partner+variant matrix + new preview_video_url,
    # textbook_isbn and estimated_workload_hours_per_week columns populated
    # for every catalog row. Must run BEFORE seed_testimonials_and_extras so
    # the testimonials backfill covers v6 courses on the FIRST build.
    from seed_extras import seed_v6 as _seed_v6
    _seed_v6(db, {
        'User': User, 'Partner': Partner, 'Course': Course,
        'CourseModule': CourseModule, 'SubCourse': SubCourse,
        'Enrollment': Enrollment, 'SavedCourse': SavedCourse,
        'Review': Review,
    })
    # R6 polish: 2026 catalog (Sustainability / BioTech / FinTech /
    # Cyber+PostQuantum / SpaceTech) — adds ~3500 deterministic courses
    # across 5 fresh clusters and +27 partners. Must run BEFORE
    # seed_testimonials_and_extras so the testimonials backfill covers v7
    # courses on the FIRST build.
    from seed_extras import seed_v7 as _seed_v7
    _seed_v7(db, {
        'User': User, 'Partner': Partner, 'Course': Course,
        'CourseModule': CourseModule, 'SubCourse': SubCourse,
        'Enrollment': Enrollment, 'SavedCourse': SavedCourse,
        'Review': Review,
    })
    # R7 polish: 2026 catalog round-2 (Agentic AI / Multimodal RAG /
    # On-Device GenAI / Climate / Fusion / SynBio / Conv UX / L10n) —
    # adds ~3150 deterministic courses across 15 fresh domains and +12
    # partners. Must run BEFORE seed_testimonials_and_extras so the
    # testimonials backfill covers v8 courses on the FIRST build.
    from seed_extras import seed_v8 as _seed_v8
    _seed_v8(db, {
        'User': User, 'Partner': Partner, 'Course': Course,
        'CourseModule': CourseModule, 'SubCourse': SubCourse,
        'Enrollment': Enrollment, 'SavedCourse': SavedCourse,
        'Review': Review,
    })
    # R8 polish (iter 8/10): K-12 + Lifelong-Learner + Professional-Development
    # tracks — adds ~3360 deterministic courses across 16 audience-anchored
    # domains and +10 publisher partners (Khan Academy, College Board, AARP,
    # Toastmasters, LinkedIn Learning Pro, Harvard Extension, NatGeo Edu,
    # PBS LearningMedia, AmeriCorps Senior Corps, Outschool). Must run BEFORE
    # seed_testimonials_and_extras so the testimonials backfill covers v9
    # courses on the FIRST build.
    from seed_extras import seed_v9 as _seed_v9
    _seed_v9(db, {
        'User': User, 'Partner': Partner, 'Course': Course,
        'CourseModule': CourseModule, 'SubCourse': SubCourse,
        'Enrollment': Enrollment, 'SavedCourse': SavedCourse,
        'Review': Review,
    })
    # R9 polish (iter 9/10): Coursera Hands-On Labs + Career Academies +
    # Industry Certificates — adds ~3570 deterministic 2026 courses across
    # 17 lab/academy/cert domains and +10 publisher partners (Coursera Labs,
    # Coursera Career Academy, AWS Skill Builder, GCP Skills Boost, MS Learn
    # Sandbox, Red Hat OpenShift Academy, HashiCorp Learn, CompTIA, PMI,
    # Scrum Alliance). Must run BEFORE seed_testimonials_and_extras so the
    # testimonials backfill covers v10 courses on the FIRST build.
    from seed_extras import seed_v10 as _seed_v10
    _seed_v10(db, {
        'User': User, 'Partner': Partner, 'Course': Course,
        'CourseModule': CourseModule, 'SubCourse': SubCourse,
        'Enrollment': Enrollment, 'SavedCourse': SavedCourse,
        'Review': Review,
    })
    # R10 polish (iter 10/10, FINAL) — Global/Regional + Learning-Path Bridges
    # — adds ~2940 deterministic 2026 courses across 14 domains × 6 subtopics
    # × 5 partners × 7 variants and +10 publisher partners (5 regional hubs,
    # 4 specialty publishers + 1 anchor). Also performs FINAL quality polish:
    # backfills modules on any module-less legacy course and re-checks every
    # row for null preview_video_url / textbook_isbn / workload columns. Must
    # run BEFORE seed_testimonials_and_extras so testimonials cover v11 rows
    # on the FIRST build.
    from seed_extras import seed_v11 as _seed_v11
    _seed_v11(db, {
        'User': User, 'Partner': Partner, 'Course': Course,
        'CourseModule': CourseModule, 'SubCourse': SubCourse,
        'Enrollment': Enrollment, 'SavedCourse': SavedCourse,
        'Review': Review,
    })
    seed_testimonials_and_extras()
    # Re-emit indexes alphabetically + VACUUM so two independent rebuilds
    # produce byte-identical sqlite files (SQLAlchemy index emission order
    # depends on Python set iteration → id(); harden-env gotcha #2).
    _normalize_seed_db_layout()


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
R2_SITE_NAME = "Coursera"
R2_DOMAIN = "coursera.org"
R2_ACCESSIBILITY_BLURB = "Coursera works to make every course captioned, screen-reader friendly, and keyboard navigable so learners with disabilities can complete the same content."


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
R3_SITE_NAME = "Coursera"
R3_DOMAIN = "coursera.org"


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


# ===========================================================================
# R4 BACKFILL — learning path / specialization roadmap + peer-graded
# assignment scoring + per-course Q&A discussion board. APPEND-ONLY: every
# new identifier is prefixed ``r4_`` / ``R4_`` and lives in its own block
# below the R2-R3 backfill section. Read-only (no DB writes), no new
# columns, no seed-function changes — the seed DB md5 stays byte-identical.
# ===========================================================================

R4_BACKFILL_RELEASE_TAG = 'r4-backfill'

# Eight curated learning paths. Each path is keyed on a category slug
# (lower-case, dash-separated) and lists 5-8 step titles plus the SQL
# LIKE filters that pick deterministic Course rows for each step. Order
# of the steps matters — the roadmap renders them top-to-bottom.
R4_LEARNING_PATHS = (
    {
        'slug': 'data-science-foundations',
        'title': 'Data Science Foundations',
        'goal': 'Move from spreadsheets to data-driven decision-making',
        'audience': 'Career switchers and analysts ramping into data work',
        'category': 'Data Science',
        'steps': (
            ('Statistics warm-up', 'statistics'),
            ('Python for data', 'python'),
            ('Pandas + SQL', 'sql'),
            ('Exploratory analysis', 'analysis'),
            ('Visualization', 'visualization'),
            ('Capstone project', 'capstone'),
        ),
    },
    {
        'slug': 'machine-learning-engineer',
        'title': 'Machine Learning Engineer',
        'goal': 'Ship ML models to production end-to-end',
        'audience': 'Engineers with a Python background',
        'category': 'Data Science',
        'steps': (
            ('Linear algebra primer', 'linear'),
            ('Classical ML', 'machine-learning'),
            ('Deep learning intro', 'deep-learning'),
            ('MLOps & deployment', 'mlops'),
            ('Capstone — end-to-end ML', 'capstone'),
        ),
    },
    {
        'slug': 'web-development-fullstack',
        'title': 'Full-Stack Web Developer',
        'goal': 'Build, deploy, and operate modern web apps',
        'audience': 'Self-taught coders ready to go full stack',
        'category': 'Computer Science',
        'steps': (
            ('HTML/CSS fundamentals', 'web'),
            ('JavaScript essentials', 'javascript'),
            ('Frontend framework', 'react'),
            ('Backend APIs', 'node'),
            ('Databases & SQL', 'database'),
            ('Cloud deployment', 'cloud'),
            ('Capstone — production launch', 'capstone'),
        ),
    },
    {
        'slug': 'cloud-architect',
        'title': 'Cloud Architect',
        'goal': 'Design scalable, secure systems on the major clouds',
        'audience': 'Engineers preparing for AWS/GCP/Azure certs',
        'category': 'Information Technology',
        'steps': (
            ('Networking fundamentals', 'network'),
            ('Linux essentials', 'linux'),
            ('Containers & Kubernetes', 'kubernetes'),
            ('Cloud platform deep-dive', 'cloud'),
            ('Security & compliance', 'security'),
            ('Capstone — reference architecture', 'capstone'),
        ),
    },
    {
        'slug': 'product-management-essentials',
        'title': 'Product Management Essentials',
        'goal': 'Lead cross-functional teams shipping software products',
        'audience': 'Aspiring or new PMs from engineering / design',
        'category': 'Business',
        'steps': (
            ('Strategy fundamentals', 'strategy'),
            ('User research & discovery', 'user'),
            ('Product analytics', 'analytics'),
            ('Roadmapping & prioritization', 'roadmap'),
            ('Stakeholder communication', 'communication'),
            ('Capstone — product spec', 'capstone'),
        ),
    },
    {
        'slug': 'digital-marketing-pro',
        'title': 'Digital Marketing Pro',
        'goal': 'Run modern multi-channel acquisition end-to-end',
        'audience': 'Marketers and growth analysts',
        'category': 'Business',
        'steps': (
            ('Brand & positioning', 'brand'),
            ('SEO foundations', 'seo'),
            ('Performance ads', 'advertising'),
            ('Content marketing', 'content'),
            ('Analytics & attribution', 'analytics'),
            ('Capstone — campaign plan', 'capstone'),
        ),
    },
    {
        'slug': 'cybersecurity-analyst',
        'title': 'Cybersecurity Analyst',
        'goal': 'Detect, respond and harden against modern threats',
        'audience': 'IT generalists pivoting into security operations',
        'category': 'Information Technology',
        'steps': (
            ('Security fundamentals', 'security'),
            ('Networking for security', 'network'),
            ('Threat intelligence', 'threat'),
            ('Incident response', 'incident'),
            ('GRC & compliance', 'compliance'),
            ('Capstone — blue-team exercise', 'capstone'),
        ),
    },
    {
        'slug': 'ai-engineer-2026',
        'title': 'AI Engineer 2026',
        'goal': 'Apply LLMs and agents to real product problems',
        'audience': 'Engineers entering the LLM / agentic-AI wave',
        'category': 'Data Science',
        'steps': (
            ('Prompt engineering', 'prompt'),
            ('RAG systems', 'rag'),
            ('LLM evaluation', 'evaluation'),
            ('Agentic workflows', 'agent'),
            ('Production LLMOps', 'mlops'),
            ('Capstone — AI product', 'capstone'),
        ),
    },
)

R4_LEARNING_PATH_BY_SLUG = {p['slug']: p for p in R4_LEARNING_PATHS}


# Peer-graded assignment rubric — 5 deterministic criteria scored on
# the standard Coursera 4-point scale. The same rubric is shown on every
# /r4/learn/<slug>/peer-grade/<n> page so test authors can write tasks
# against a fixed criterion list.
R4_PEER_GRADE_RUBRIC = (
    {'code': 'rigor',
     'title': 'Methodological rigour',
     'weight': 25,
     'descriptor': 'The submission selects an appropriate method and applies it correctly with no major gaps.'},
    {'code': 'evidence',
     'title': 'Evidence & analysis',
     'weight': 25,
     'descriptor': 'Conclusions are supported by data, code outputs, or cited sources.'},
    {'code': 'clarity',
     'title': 'Clarity of communication',
     'weight': 20,
     'descriptor': 'The write-up is well structured, free of jargon, and easy to follow for a peer learner.'},
    {'code': 'reproducibility',
     'title': 'Reproducibility',
     'weight': 15,
     'descriptor': 'A reviewer can reproduce the main result by following the instructions and using the attached artefacts.'},
    {'code': 'reflection',
     'title': 'Reflection & next steps',
     'weight': 15,
     'descriptor': 'The author discusses limitations and articulates concrete follow-ups.'},
)

R4_PEER_GRADE_LEVELS = (
    ('exemplary', 4, 'Exemplary'),
    ('proficient', 3, 'Proficient'),
    ('developing', 2, 'Developing'),
    ('beginning', 1, 'Beginning'),
)


def r4_path_for_slug(slug):
    """Return the curated learning-path dict for the given slug, or None."""
    return R4_LEARNING_PATH_BY_SLUG.get(slug)


def r4_path_courses(path):
    """Resolve each step in the path to a deterministic Course row.

    For each step we first try ``Course.slug == "{path.slug}-{step_slug}"``,
    fall back to a category + title-keyword LIKE lookup, then to a global
    title-keyword fallback. The lookups are wrapped in alphabetical
    ``order_by(Course.slug)`` so the resolver is fully deterministic.
    """
    out = []
    used_ids = set()
    cat = path.get('category', '')
    for title, kw in path['steps']:
        course = None
        kw_like = f'%{kw}%'
        # Category-restricted match (avoids picking unrelated topics).
        candidates = (Course.query
                      .filter(Course.category == cat,
                              Course.title.ilike(kw_like),
                              ~Course.id.in_(used_ids) if used_ids else True)
                      .order_by(Course.slug.asc())
                      .limit(3).all())
        for c in candidates:
            if c.id not in used_ids:
                course = c
                break
        if course is None:
            # Cross-category fallback by keyword only.
            candidates = (Course.query
                          .filter(Course.title.ilike(kw_like),
                                  ~Course.id.in_(used_ids) if used_ids else True)
                          .order_by(Course.slug.asc())
                          .limit(3).all())
            for c in candidates:
                if c.id not in used_ids:
                    course = c
                    break
        out.append({'step_title': title, 'keyword': kw, 'course': course})
        if course is not None:
            used_ids.add(course.id)
    return out


def r4_peer_grade_score(course, n):
    """Deterministic example peer-grade score for week n of `course`.

    Combines course.id, week number and rubric criterion order so each
    /r4/learn/<slug>/peer-grade/<n> page renders a stable score table.
    """
    rows = []
    total = 0
    for i, crit in enumerate(R4_PEER_GRADE_RUBRIC):
        h = (course.id * 17 + n * 53 + i * 7) % 4
        level = R4_PEER_GRADE_LEVELS[h]
        points = level[1] * crit['weight'] / 4.0
        total += points
        rows.append({
            'criterion': crit,
            'level_slug': level[0],
            'level_label': level[2],
            'points': round(points, 1),
            'max_points': crit['weight'],
        })
    return rows, round(total, 1)


def r4_qa_board_threads(course):
    """Deterministic list of 12 Q&A threads for the course. Distinct from
    the existing /learn/<slug>/discussion route (which lists generic
    discussion threads); the Q&A board is question-centric and exposes
    accepted-answer flags, upvote counts and a tag per thread."""
    bank = (
        ('How do I install the recommended environment?', 'setup',  False),
        ('Are the syllabus PDFs downloadable for offline study?', 'logistics', True),
        ('Where can I find Week 1 datasets?', 'data', True),
        ('Is there a make-up policy for missed deadlines?', 'logistics', True),
        ('Does this course count towards a Specialization?', 'credit', True),
        ('How do peer-graded assignments compare to auto-grading?', 'peer-grading', False),
        ('Any tips for the Week 4 reading list?', 'reading', False),
        ('Recommended pace for working professionals?', 'pacing', False),
        ('Will the office hours be recorded?', 'office-hours', True),
        ('How does the instructor compare to the predecessor course?', 'meta', False),
        ('Can the capstone be used in a portfolio?', 'capstone', True),
        ('What is the policy on AI tools for submissions?', 'policy', True),
    )
    out = []
    for i, (q, tag, accepted) in enumerate(bank):
        upvotes = (course.id * 11 + i * 23) % 41
        replies = 2 + ((course.id + i) % 9)
        out.append({
            'index': i + 1,
            'question': q,
            'tag': tag,
            'accepted': accepted,
            'upvotes': upvotes,
            'replies': replies,
        })
    return out


@app.route('/r4/learning-path')
@app.route('/r4/learning-path/')
def r4_learning_path_index():
    summary = [
        {'slug': p['slug'], 'title': p['title'],
         'goal': p['goal'], 'audience': p['audience'],
         'steps_count': len(p['steps']),
         'category': p['category']}
        for p in R4_LEARNING_PATHS
    ]
    return render_template('r4_path.html', mode='index',
                           paths=summary, total=len(R4_LEARNING_PATHS),
                           release=R4_BACKFILL_RELEASE_TAG)


@app.route('/r4/learning-path/<slug>')
def r4_learning_path_detail(slug):
    path = r4_path_for_slug(slug)
    if path is None:
        abort(404)
    courses = r4_path_courses(path)
    filled = sum(1 for c in courses if c['course'] is not None)
    return render_template('r4_path.html', mode='detail',
                           path=path, courses=courses,
                           filled=filled,
                           release=R4_BACKFILL_RELEASE_TAG)


@app.route('/r4/learn/<slug>/peer-grade/<int:n>')
def r4_peer_grade_detail(slug, n):
    course = Course.query.filter_by(slug=slug).first_or_404()
    mods = course.modules
    if not mods or n < 1 or n > len(mods):
        abort(404)
    module = mods[n - 1]
    rows, total = r4_peer_grade_score(course, n)
    return render_template('r4_course_extras.html', mode='peer-grade',
                           course=course, module=module, n=n,
                           total_modules=len(mods),
                           score_rows=rows, total_score=total,
                           rubric=R4_PEER_GRADE_RUBRIC,
                           levels=R4_PEER_GRADE_LEVELS,
                           release=R4_BACKFILL_RELEASE_TAG)


@app.route('/r4/learn/<slug>/qa-board')
def r4_qa_board(slug):
    course = Course.query.filter_by(slug=slug).first_or_404()
    threads = r4_qa_board_threads(course)
    answered = sum(1 for t in threads if t['accepted'])
    return render_template('r4_course_extras.html', mode='qa-board',
                           course=course, threads=threads,
                           answered=answered,
                           release=R4_BACKFILL_RELEASE_TAG)


@app.route('/api/r4/learning-paths')
def r4_api_learning_paths():
    return jsonify({
        'release': R4_BACKFILL_RELEASE_TAG,
        'total_paths': len(R4_LEARNING_PATHS),
        'paths': [
            {'slug': p['slug'], 'title': p['title'],
             'category': p['category'],
             'steps_count': len(p['steps'])}
            for p in R4_LEARNING_PATHS
        ],
    })


# === R4 backfill END ===


# === GUI deepen BEGIN — auto-generated 2026-05-27 (do not hand-edit between markers) ===
# Adds 25+ dedicated GUI pages that mirror real coursera.org surfaces missing
# from the original mirror: per-Specialization landing, per-Professional Cert
# detail, per-Degree detail, MasterTrack, business-by-industry, campus,
# /category/<cat>, /financial-aid/apply, refund/honor/conduct policies,
# Coursera Plus subscribe, /learn/<slug>/{instructors,reviews,faq},
# /courses/{free,with-certificate,in-spanish}, /specializations index,
# /partner/<slug>/about, /compare, /terms, /privacy.
#
# Read-only: no DB writes, no API endpoints. Stable across reloads via md5
# seeding so the byte-identical instance_seed/coursera.db invariant holds.

import hashlib as _gd_hashlib


_GD_CATEGORY_MAP = {
    'computer-science':       ('Computer Science',                'Build software, AI, and infrastructure for the next decade.'),
    'data-science':           ('Data Science',                    'Turn raw data into clear answers — from SQL to deep learning.'),
    'business':               ('Business',                        'Lead teams, run companies, and grow careers in any industry.'),
    'information-technology': ('Information Technology',          'Operate the systems and clouds the modern world depends on.'),
    'it-cloud':               ('Information Technology',          'Operate the systems and clouds the modern world depends on.'),
    'cs':                     ('Computer Science',                'Build software, AI, and infrastructure for the next decade.'),
    'language-learning':      ('Language Learning',               'Speak a new language confidently with practical lessons.'),
    'language':               ('Language Learning',               'Speak a new language confidently with practical lessons.'),
    'math-logic':             ('Math and Logic',                  'Master the mathematics that underpin science and engineering.'),
    'math':                   ('Math and Logic',                  'Master the mathematics that underpin science and engineering.'),
    'physical-science':       ('Physical Science and Engineering','Explore engineering, physics, and applied science online.'),
    'social-sciences':        ('Social Sciences',                 'Study people, policy, history, and the economies of nations.'),
    'social-science':         ('Social Sciences',                 'Study people, policy, history, and the economies of nations.'),
    'arts-humanities':        ('Arts and Humanities',             'Engage with art, music, philosophy, and creative writing.'),
    'arts':                   ('Arts and Humanities',             'Engage with art, music, philosophy, and creative writing.'),
    'health':                 ('Health',                          'Advance careers in public health, nursing, and biomedical science.'),
    'personal-development':   ('Personal Development',            'Build confidence, productivity, and lifelong learning habits.'),
}

_GD_CATEGORY_SKILLS = {
    'Computer Science':                 ['Python', 'Algorithms', 'Java', 'Data Structures', 'C++', 'JavaScript', 'Computer Architecture'],
    'Data Science':                     ['SQL', 'Python', 'Machine Learning', 'R Programming', 'Statistics', 'Pandas', 'Deep Learning'],
    'Business':                         ['Leadership', 'Project Management', 'Marketing', 'Finance', 'Strategy', 'Operations'],
    'Information Technology':           ['Linux', 'Networking', 'Cybersecurity', 'AWS', 'Azure', 'Docker', 'Kubernetes'],
    'Language Learning':                ['English', 'Spanish', 'Chinese', 'French', 'Japanese', 'Translation'],
    'Math and Logic':                   ['Calculus', 'Linear Algebra', 'Probability', 'Discrete Math', 'Optimization'],
    'Physical Science and Engineering': ['Mechanical Engineering', 'Electrical Engineering', 'Physics', 'Materials Science'],
    'Social Sciences':                  ['Economics', 'Sociology', 'Public Policy', 'Psychology', 'Geography'],
    'Arts and Humanities':              ['Writing', 'Philosophy', 'Music Theory', 'Art History', 'Creative Writing'],
    'Health':                           ['Public Health', 'Nutrition', 'Epidemiology', 'Anatomy', 'Healthcare Management'],
    'Personal Development':             ['Time Management', 'Communication', 'Critical Thinking', 'Resilience', 'Mindfulness'],
}

_GD_CATEGORY_CAREERS = {
    'Computer Science':                 [{'name': 'Software Engineer',   'slug': 'software-engineer',   'salary': '$120,000'},
                                         {'name': 'Frontend Developer',  'slug': 'frontend-developer',  'salary': '$95,000'},
                                         {'name': 'Backend Developer',   'slug': 'backend-developer',   'salary': '$110,000'}],
    'Data Science':                     [{'name': 'Data Analyst',        'slug': 'data-analyst',        'salary': '$78,000'},
                                         {'name': 'Data Scientist',      'slug': 'data-scientist',      'salary': '$118,000'},
                                         {'name': 'ML Engineer',         'slug': 'ml-engineer',         'salary': '$130,000'}],
    'Business':                         [{'name': 'Product Manager',     'slug': 'product-manager',     'salary': '$135,000'},
                                         {'name': 'Project Manager',     'slug': 'project-manager',     'salary': '$92,000'},
                                         {'name': 'Business Analyst',    'slug': 'business-analyst',    'salary': '$85,000'}],
    'Information Technology':           [{'name': 'Cloud Architect',     'slug': 'cloud-architect',     'salary': '$145,000'},
                                         {'name': 'IT Support',          'slug': 'it-support',          'salary': '$55,000'},
                                         {'name': 'Cyber Security',      'slug': 'cyber-security',      'salary': '$105,000'}],
    'Language Learning':                [{'name': 'Translator',          'slug': 'translator',          'salary': '$54,000'},
                                         {'name': 'ESL Teacher',         'slug': 'esl-teacher',         'salary': '$48,000'}],
    'Math and Logic':                   [{'name': 'Quantitative Analyst','slug': 'quant',               'salary': '$135,000'},
                                         {'name': 'Statistician',        'slug': 'statistician',        'salary': '$92,000'}],
    'Physical Science and Engineering': [{'name': 'Mechanical Engineer', 'slug': 'mechanical-engineer', 'salary': '$95,000'},
                                         {'name': 'Electrical Engineer', 'slug': 'electrical-engineer', 'salary': '$98,000'}],
    'Social Sciences':                  [{'name': 'Economist',           'slug': 'economist',           'salary': '$108,000'},
                                         {'name': 'Policy Analyst',      'slug': 'policy-analyst',      'salary': '$72,000'}],
    'Arts and Humanities':              [{'name': 'Content Writer',      'slug': 'content-writer',      'salary': '$58,000'},
                                         {'name': 'UX Designer',         'slug': 'ux-designer',         'salary': '$92,000'}],
    'Health':                           [{'name': 'Public Health',       'slug': 'public-health',       'salary': '$72,000'},
                                         {'name': 'Healthcare Mgr',      'slug': 'healthcare-manager',  'salary': '$104,000'}],
    'Personal Development':             [{'name': 'Career Coach',        'slug': 'career-coach',        'salary': '$62,000'}],
}


_GD_MASTERTRACKS = [
    {'slug': 'instructional-design', 'title': 'Instructional Design MasterTrack',
     'partner_short': 'Illinois', 'partner_name': 'University of Illinois at Urbana-Champaign',
     'blurb': 'Apply learning science to design effective courses, training, and educational technology.',
     'long_blurb': 'Earn academic credit toward the iMSLD program at Illinois. Designed for K-12 teachers, corporate trainers, and emerging instructional designers.',
     'duration': '6 months', 'workload': '8–10', 'tuition': '$3,920',
     'degree_alias': 'Master of Science in Learning Design',
     'modules': [
         {'title': 'Foundations of Learning Design', 'summary': 'Theories of cognition, motivation, and assessment.'},
         {'title': 'Designing Effective eLearning', 'summary': 'Authoring tools, accessibility, and assessment design.'},
         {'title': 'Capstone Project', 'summary': 'Build a fully scoped learning experience reviewed by faculty.'},
     ]},
    {'slug': 'sustainability-and-development', 'title': 'Sustainability and Development MasterTrack',
     'partner_short': 'Michigan', 'partner_name': 'University of Michigan',
     'blurb': 'Tools for sustainable development across business, government, and NGOs.',
     'long_blurb': 'Designed for early- and mid-career professionals tackling climate, equity, and resource problems.',
     'duration': '7 months', 'workload': '10–12', 'tuition': '$3,750',
     'degree_alias': 'Master of Sustainability and Development',
     'modules': [
         {'title': 'Foundations of Sustainability', 'summary': 'Earth systems, equity, and the SDG framework.'},
         {'title': 'Sustainable Cities', 'summary': 'Urban planning, transit, and infrastructure choices.'},
         {'title': 'Energy and Climate Policy', 'summary': 'Mitigation, adaptation, and policy levers.'},
         {'title': 'Capstone', 'summary': 'Field-based sustainability project graded by Michigan faculty.'},
     ]},
    {'slug': 'global-energy-and-climate-policy', 'title': 'Global Energy and Climate Policy MasterTrack',
     'partner_short': 'SOAS London', 'partner_name': 'SOAS University of London',
     'blurb': 'Policy, finance, and geopolitics of the energy transition.',
     'long_blurb': 'Bridges economics, international relations, and engineering. Counts toward the SOAS MSc.',
     'duration': '6 months', 'workload': '9–11', 'tuition': '$4,250',
     'degree_alias': 'MSc Global Energy and Climate Policy',
     'modules': [
         {'title': 'Energy Markets and Investment', 'summary': 'How energy is financed, traded, and priced.'},
         {'title': 'Climate Negotiation', 'summary': 'UNFCCC, COP, and national policy design.'},
         {'title': 'Capstone Policy Brief', 'summary': 'Write a publishable policy brief.'},
     ]},
    {'slug': 'social-work', 'title': 'Social Work: Practice, Policy, and Research MasterTrack',
     'partner_short': 'Michigan', 'partner_name': 'University of Michigan',
     'blurb': 'Core social work skills for community and clinical practice.',
     'long_blurb': 'A direct on-ramp to Michigan\'s Master of Social Work program.',
     'duration': '5 months', 'workload': '10–12', 'tuition': '$4,000',
     'degree_alias': 'Master of Social Work',
     'modules': [
         {'title': 'Foundations of Social Work', 'summary': 'Values, ethics, and frameworks.'},
         {'title': 'Policy and Advocacy', 'summary': 'How policy shapes practice.'},
         {'title': 'Capstone Field Project', 'summary': 'Apply skills in a community setting.'},
     ]},
    {'slug': 'machine-learning-for-analytics', 'title': 'Machine Learning for Analytics MasterTrack',
     'partner_short': 'Chicago', 'partner_name': 'University of Chicago',
     'blurb': 'Applied ML for business analytics roles.',
     'long_blurb': 'Designed for analysts adding ML to their toolkit. Counts toward Chicago\'s MS in Analytics.',
     'duration': '6 months', 'workload': '10–14', 'tuition': '$4,800',
     'degree_alias': 'MS in Analytics',
     'modules': [
         {'title': 'Foundations of ML', 'summary': 'Supervised and unsupervised models.'},
         {'title': 'Time Series and Forecasting', 'summary': 'Statistical and neural approaches.'},
         {'title': 'Deployment and MLOps', 'summary': 'Production-grade ML systems.'},
         {'title': 'Capstone', 'summary': 'End-to-end analytics project on a real dataset.'},
     ]},
    {'slug': 'principles-of-management', 'title': 'Principles of Management MasterTrack',
     'partner_short': 'IE Business School', 'partner_name': 'IE Business School',
     'blurb': 'Management foundations for first-time and aspiring managers.',
     'long_blurb': 'A stepping stone toward IE\'s online MBA.',
     'duration': '5 months', 'workload': '8–10', 'tuition': '$3,600',
     'degree_alias': 'IE Online MBA',
     'modules': [
         {'title': 'Strategy', 'summary': 'How firms create and sustain advantage.'},
         {'title': 'People and Leadership', 'summary': 'Motivating and leading teams.'},
         {'title': 'Finance for Managers', 'summary': 'Reading P&Ls and making investment cases.'},
     ]},
    {'slug': 'construction-engineering-and-management', 'title': 'Construction Engineering &amp; Management MasterTrack',
     'partner_short': 'Michigan', 'partner_name': 'University of Michigan',
     'blurb': 'Modern construction management for civil engineers.',
     'long_blurb': 'Bridge field experience with formal credentials toward an M.Eng.',
     'duration': '6 months', 'workload': '10–12', 'tuition': '$4,250',
     'degree_alias': 'Master of Engineering in Construction Management',
     'modules': [
         {'title': 'Construction Estimation', 'summary': 'Cost modeling and bidding.'},
         {'title': 'Scheduling and Planning', 'summary': 'Critical path and resource leveling.'},
         {'title': 'Capstone Build', 'summary': 'Plan a real-scale construction project.'},
     ]},
]

_GD_INDUSTRY_PAGES = {
    'technology':  ('Technology',  'Help engineers, PMs, and designers ship faster — from AI fundamentals to system design.',
                    ['Python', 'Cloud Computing', 'System Design', 'Machine Learning', 'Cybersecurity'],
                    [('Adobe', 'Adobe upskilled 9,000+ engineers in cloud and ML.', 'Adobe', '4x faster', '95% completion'),
                     ('Atlassian', 'Atlassian rolled out SRE training across the engineering org.', 'Atlassian', '67% incident drop', '2,800 trained'),
                     ('Cisco', 'Cisco modernized its IT certification ladder.', 'Cisco', '120K seats', '3.8/5 NPS')]),
    'finance':     ('Finance',     'Build the data, risk, and compliance skills banks and fintechs need.',
                    ['Excel', 'SQL', 'Financial Modeling', 'Risk Analysis', 'Tableau'],
                    [('Citi', 'Citi launched a digital banking academy for 40K staff.', 'Citi', '40,000 learners', '92% completion'),
                     ('Mastercard', 'Mastercard rolled out a data fluency program.', 'Mastercard', '78% data fluency', '4.6/5'),
                     ('Goldman Sachs', 'Goldman trained analysts in advanced Excel and Python.', 'Goldman Sachs', '2x faster onboarding', '4.7/5')]),
    'healthcare':  ('Healthcare',  'Reskill clinical and administrative staff for digital health, telemedicine, and data.',
                    ['EHR Systems', 'Public Health', 'Healthcare Analytics', 'Project Management', 'Communication'],
                    [('Mercy Health', 'Mercy Health trained 8K clinicians in informatics.', 'Mercy Health', '8,000 clinicians', '94% retention'),
                     ('Kaiser Permanente', 'Kaiser rolled out healthcare data analytics learning paths.', 'Kaiser', '3x analyst capacity', '4.5/5')]),
    'retail':      ('Retail',      'Train store managers and corporate staff in analytics, supply chain, and digital marketing.',
                    ['Inventory Management', 'Digital Marketing', 'Customer Experience', 'Operations', 'Excel'],
                    [('IKEA', 'IKEA reskilled 12K store leaders in digital ops.', 'IKEA', '12K leaders', '88% completion'),
                     ('Best Buy', 'Best Buy launched a Geek Squad cyber-skills academy.', 'Best Buy', '4K Agents certified', '4.6/5')]),
    'manufacturing': ('Manufacturing','Industry 4.0 skills: automation, lean, and data-driven operations.',
                    ['Lean Six Sigma', 'Industrial IoT', 'CAD', 'Quality Management', 'Supply Chain'],
                    [('Bosch', 'Bosch ran a global digital factory academy.', 'Bosch', '15K engineers', '93% completion'),
                     ('Siemens', 'Siemens built a workforce automation curriculum.', 'Siemens', '2x productivity', '4.5/5')]),
    'government':  ('Government',  'Upskill public-sector employees in digital services, cybersecurity, and data.',
                    ['Project Management', 'Cybersecurity', 'Public Speaking', 'Data Analysis', 'Excel'],
                    [('Government of Colombia', 'Colombia reskilled 1M citizens in digital skills.', 'MinTIC Colombia', '1M citizens', '78% completion'),
                     ('UAE Government', 'UAE built a future-skills academy for civil servants.', 'UAE Gov', '50K civil servants', '4.7/5')]),
    'energy':      ('Energy',      'Skills for the energy transition: renewables, grid, and decarbonization.',
                    ['Renewable Energy', 'Power Systems', 'Sustainability', 'Project Management', 'GIS'],
                    [('Schneider Electric', 'Schneider trained sustainability engineers globally.', 'Schneider', '20K engineers', '4.6/5'),
                     ('EDF', 'EDF ran a renewable energy reskilling program.', 'EDF', '6K reskilled', '91% completion')]),
    'consulting':  ('Consulting',  'Equip consultants with structured problem solving, data, and stakeholder skills.',
                    ['Communication', 'Strategy', 'Data Analysis', 'Storytelling', 'Excel'],
                    [('Deloitte', 'Deloitte rolled out a consultant fluency program.', 'Deloitte', '70K consultants', '4.7/5'),
                     ('Accenture', 'Accenture trained 200K staff in AI fluency.', 'Accenture', '200K trained', '92% completion')]),
}


_GD_PARTNER_ABOUT_EXPERTISE = {
    'university': ['Research', 'Liberal arts', 'STEM', 'Professional schools', 'Continuing education'],
    'company':    ['Industry training', 'Career certificates', 'Technical mentorship', 'Workforce reskilling'],
    'institution':['Mission-driven training', 'Policy expertise', 'Sector partnerships', 'Cross-disciplinary work'],
}


def _gd_text(seed_str, items):
    if not items:
        return ''
    idx = int(_gd_hashlib.md5(str(seed_str).encode()).hexdigest()[:6], 16) % len(items)
    return items[idx]


# ── /specializations index ────────────────────────────────────────────────────
@app.route('/specializations')
def specializations_index():
    courses = (Course.query.filter_by(course_type='Specialization')
               .order_by(Course.enrolled_count.desc()).limit(96).all())
    partner_count = len({c.partner_id for c in courses if c.partner_id})
    return render_template('specializations_index.html',
                           courses=courses, partner_count=partner_count)


# ── /professional-certificates/<slug> ─────────────────────────────────────────
@app.route('/professional-certificates/<slug>')
def professional_cert_detail(slug):
    course = Course.query.filter_by(slug=slug).first()
    if not course:
        # Allow looser match — append '-professional-certificate' suffix
        course = Course.query.filter_by(
            slug=f'{slug}-professional-certificate').first()
    if not course:
        abort(404)
    sub_courses = SubCourse.query.filter_by(
        specialization_id=course.id).order_by(SubCourse.order_index).all()
    # Career track derived from category — keeps copy plausible.
    career_track = (course.category or 'this field').strip().lower() or 'this field'
    return render_template('professional_cert_detail.html', course=course,
                           sub_courses=sub_courses, career_track=career_track)


# ── /degrees/<slug> ───────────────────────────────────────────────────────────
@app.route('/degrees/<slug>')
def degree_detail(slug):
    # Avoid collision with /degrees/list (handled higher).
    if slug == 'list':
        return redirect(url_for('degrees_list'))
    course = Course.query.filter_by(slug=slug).first()
    if not course or course.course_type != 'Degree':
        abort(404)
    # Deterministic concentrations from the category.
    cat = course.category or 'General'
    skills_pool = _GD_CATEGORY_SKILLS.get(cat, ['Core Theory', 'Capstone Lab', 'Applied Project'])
    seed = int(_gd_hashlib.md5(course.slug.encode()).hexdigest()[:6], 16)
    concentrations = []
    for k in range(4):
        concentrations.append(skills_pool[(seed + k * 3) % len(skills_pool)])
    # Drop duplicates while preserving order.
    seen = set(); _c = []
    for x in concentrations:
        if x not in seen:
            seen.add(x); _c.append(x)
    concentrations = _c
    return render_template('degree_detail.html', course=course,
                           concentrations=concentrations)


# ── /mastertrack and /mastertrack/<slug> ──────────────────────────────────────
@app.route('/mastertrack')
@app.route('/mastertrack/')
def mastertrack_index():
    return render_template('mastertrack_index.html', tracks=_GD_MASTERTRACKS)


@app.route('/mastertrack/<slug>')
def mastertrack_detail(slug):
    track = next((t for t in _GD_MASTERTRACKS if t['slug'] == slug), None)
    if not track:
        abort(404)
    return render_template('mastertrack_detail.html', track=track)


@app.route('/mastertrack/<slug>/admissions', methods=['GET', 'POST'])
def mastertrack_admissions(slug):
    track = next((t for t in _GD_MASTERTRACKS if t['slug'] == slug), None)
    if not track:
        abort(404)
    submitted = False
    ref_code = ''
    if request.method == 'POST':
        # Deterministic, in-memory only — no DB write.
        payload = (slug + (request.form.get('email') or '')
                   + (request.form.get('first_name') or '')).encode('utf-8')
        ref_code = _gd_hashlib.md5(payload).hexdigest()[:8].upper()
        submitted = True
    return render_template('mastertrack_admissions.html', track=track,
                           submitted=submitted, ref_code=ref_code)


# ── /business/<industry> ──────────────────────────────────────────────────────
@app.route('/business/<industry>')
def business_industry(industry):
    page = _GD_INDUSTRY_PAGES.get(industry)
    if not page:
        abort(404)
    industry_name, blurb, skills, raw_cases = page
    case_studies = [
        {'company': c[0], 'headline': c[1], 'summary': f'How {c[2]} partnered with Coursera for Business to drive measurable outcomes.',
         'metric_1': c[3], 'metric_2': c[4]} for c in raw_cases
    ]
    # Recommend top courses tagged with any of the industry skills.
    candidates = (Course.query.filter(Course.skills != '')
                  .order_by(Course.enrolled_count.desc()).limit(400).all())
    needles = [s.lower() for s in skills]
    recommended = []
    for c in candidates:
        sk = (c.skills or '').lower()
        if any(n in sk for n in needles):
            recommended.append(c)
        if len(recommended) >= 9:
            break
    return render_template('business_industry.html',
                           industry_slug=industry,
                           industry_name=industry_name,
                           industry_blurb=blurb,
                           key_skills=skills,
                           case_studies=case_studies,
                           recommended_courses=recommended)


# ── /campus ───────────────────────────────────────────────────────────────────
@app.route('/campus', methods=['GET', 'POST'])
def campus():
    return render_template('campus.html')


# ── /category/<slug> ──────────────────────────────────────────────────────────
@app.route('/category/<slug>')
def category_detail(slug):
    entry = _GD_CATEGORY_MAP.get(slug)
    if not entry:
        abort(404)
    cat_name, _blurb = entry
    q = Course.query.filter(Course.category.ilike(f'%{cat_name}%'))
    level = request.args.get('level')
    ctype = request.args.get('type')
    if level in ('Beginner', 'Intermediate', 'Advanced', 'Mixed'):
        q = q.filter(Course.level == level)
    if ctype:
        q = q.filter(Course.course_type == ctype)
    if request.args.get('free') == '1':
        q = q.filter(Course.is_free.is_(True))
    courses = q.order_by(Course.enrolled_count.desc()).limit(96).all()
    return render_template('category_detail.html',
                           cat_slug=slug, cat_name=cat_name,
                           courses=courses,
                           top_skills=_GD_CATEGORY_SKILLS.get(cat_name, []),
                           career_roles=_GD_CATEGORY_CAREERS.get(cat_name, []))


# ── /financial-aid/apply ──────────────────────────────────────────────────────
@app.route('/financial-aid/apply', methods=['GET', 'POST'])
def financial_aid_apply():
    eligible_courses = (Course.query.filter_by(has_certificate=True, is_free=False)
                        .order_by(Course.enrolled_count.desc()).limit(30).all())
    submitted = False
    ref_code = ''
    decision_by = ''
    if request.method == 'POST':
        payload = ((request.form.get('course_slug') or '') +
                   (request.form.get('income_band') or '') +
                   (request.form.get('why_needed') or '')[:30]).encode('utf-8')
        ref_code = _gd_hashlib.md5(payload).hexdigest()[:8].upper()
        submitted = True
        # Decision date is a deterministic +15-business-day offset from a
        # fixed reference so the GUI value is stable.
        ref_dt = datetime(2026, 5, 1)
        decision_by = (ref_dt + timedelta(days=21)).strftime('%B %d, %Y')
    return render_template('financial_aid_apply.html',
                           eligible_courses=eligible_courses,
                           submitted=submitted, ref_code=ref_code,
                           decision_by=decision_by)


# ── Policy pages ──────────────────────────────────────────────────────────────
@app.route('/refund-policy')
def refund_policy():
    return render_template('refund_policy.html')


@app.route('/honor-code')
def honor_code():
    return render_template('honor_code.html')


@app.route('/code-of-conduct')
def code_of_conduct():
    return render_template('code_of_conduct.html')


@app.route('/terms')
@app.route('/terms-of-use')
def terms_of_use():
    return render_template('terms_of_use.html')


@app.route('/privacy')
@app.route('/privacy-policy')
def privacy_policy():
    return render_template('privacy_policy.html')


# ── /coursera-plus/subscribe ──────────────────────────────────────────────────
@app.route('/coursera-plus/subscribe', methods=['GET', 'POST'])
def coursera_plus_subscribe():
    confirmed_plan = None
    first_charge_date = ''
    if request.method == 'POST':
        plan = (request.form.get('plan') or '').lower()
        if plan in ('monthly', 'annual', 'student'):
            confirmed_plan = plan
            ref_dt = datetime(2026, 5, 1)
            first_charge_date = (ref_dt + timedelta(days=7)).strftime('%B %d, %Y')
    return render_template('coursera_plus_subscribe.html',
                           confirmed_plan=confirmed_plan,
                           first_charge_date=first_charge_date)


# ── Course sub-pages ──────────────────────────────────────────────────────────
@app.route('/learn/<slug>/instructors')
def course_instructors(slug):
    course = Course.query.filter_by(slug=slug).first_or_404()
    names = []
    if course.instructor:
        for nm in [n.strip() for n in course.instructor.split(',')]:
            if nm and nm not in names:
                names.append(nm)
    if not names:
        names = ['Coursera Instructor']
    bios = [
        'is a teaching professor with over a decade of experience guiding learners online and on campus.',
        'leads research and industry collaborations and has published widely in the field.',
        'brings hands-on industry experience to every course module and discussion forum.',
        'is recognized for designing engaging, scaffolded learning experiences for global audiences.',
    ]
    instructors = []
    for idx, nm in enumerate(names[:6]):
        slugn = _slugify_instructor(nm)
        seed = int(_gd_hashlib.md5(slugn.encode()).hexdigest()[:6], 16)
        instructors.append({
            'name': nm,
            'slug': slugn,
            'title': course.instructor_title or 'Lead Instructor',
            'affiliation': (course.partner.name if course.partner else ''),
            'bio': f'{nm} {bios[seed % len(bios)]}',
            'course_count': 1 + (seed % 6),
            'learner_count': '{:,}'.format(1500 + (seed % 9) * 850),
        })
    return render_template('course_instructors.html', course=course, instructors=instructors)


@app.route('/learn/<slug>/reviews')
def course_reviews(slug):
    course = Course.query.filter_by(slug=slug).first_or_404()
    star_filter = None
    try:
        sf = int(request.args.get('stars') or 0)
        if 1 <= sf <= 5:
            star_filter = sf
    except (TypeError, ValueError):
        star_filter = None
    avg = course.rating or 4.5
    if avg >= 4.7:
        breakdown = {'5': 65, '4': 22, '3': 8, '2': 3, '1': 2}
    elif avg >= 4.4:
        breakdown = {'5': 55, '4': 28, '3': 10, '2': 4, '1': 3}
    elif avg >= 4.0:
        breakdown = {'5': 45, '4': 30, '3': 15, '2': 6, '1': 4}
    else:
        breakdown = {'5': 30, '4': 30, '3': 20, '2': 12, '1': 8}
    # Build deterministic review entries from the existing Review rows when
    # available, falling back to seeded synthetic entries.
    reviews_rows = (Review.query.filter_by(course_id=course.id)
                    .order_by(Review.rating.desc(), Review.created_at.desc())
                    .limit(40).all())
    out = []
    for r in reviews_rows:
        user = User.query.get(r.user_id)
        if star_filter is not None and int(round(r.rating)) != star_filter:
            continue
        out.append({
            'rating': int(round(r.rating)),
            'body': r.body,
            'author_name': (user.name if user else 'Coursera Learner'),
            'author_initial': (user.name[0].upper() if user and user.name else 'C'),
            'created_at_display': (r.created_at.strftime('%B %Y') if r.created_at else 'recently'),
        })
    if not out:
        # Synthetic fallback when no reviews exist yet.
        sample_bodies = [
            'Clear explanations and well-paced labs.  The capstone tied everything together.',
            'Loved the hands-on assignments.  Office hours from the TA team were a highlight.',
            'A few outdated slides, but overall an outstanding introduction to the topic.',
            'I had no background in this area and finished feeling confident with the basics.',
            'The peer-review rubric is fair and the discussion forum is very active.',
        ]
        for i in range(5):
            stars = 5 - (i % 5 if i < 5 else 0)
            if star_filter and stars != star_filter:
                continue
            out.append({
                'rating': stars,
                'body': sample_bodies[i % len(sample_bodies)],
                'author_name': f'Learner {i + 1}',
                'author_initial': chr(ord('A') + i),
                'created_at_display': 'March 2026',
            })
    return render_template('course_reviews.html', course=course, reviews=out,
                           breakdown=breakdown, star_filter=star_filter)


@app.route('/learn/<slug>/faq')
def course_faq(slug):
    course = Course.query.filter_by(slug=slug).first_or_404()
    faq_groups = [
        ('Enrollment and access', [
            ('How do I enroll in this course?',
             'Click the Enroll button on the course page. You can audit for free or join the certificate track for a fee.'),
            ('Can I take the course at my own pace?',
             'Yes. Coursera offers flexible deadlines — set your own schedule and shift due dates as needed.'),
            ('Is there a free trial?',
             'You can audit most courses for free. The certificate track unlocks graded assignments and the shareable certificate.'),
        ]),
        ('Certificates and credit', [
            ('Will I receive a certificate?',
             'Yes — finish all graded items in the certificate track to earn a shareable, verifiable certificate.'),
            ('Can I add this to LinkedIn?',
             'Absolutely.  From your Accomplishments page, click Add to LinkedIn — your verified credential will appear in your profile.'),
            ('Is the certificate accredited for university credit?',
             'Some Specializations are credit-eligible toward partner-university degrees. See the program page for details.'),
        ]),
        ('Payment and refunds', [
            ('What does the certificate track cost?',
             'Pricing varies by course and is shown on the enrollment screen. Subscriptions like Coursera Plus include this course.'),
            ('Can I get a refund?',
             'Yes — see our refund policy. Most paid courses are refundable within 14 days if you have not earned the certificate.'),
            ('Is financial aid available?',
             'Yes. Coursera offers full financial aid for learners who demonstrate need. Reviews take about 15 business days.'),
        ]),
        ('Course logistics', [
            ('How long is this course?',
             f'{course.duration_text} at approximately {int(course.estimated_workload_hours_per_week or 4)} hours per week.'),
            ('Are the syllabus PDFs downloadable for offline study?',
             'Yes. Each module page exposes a downloadable syllabus and lecture slides where available.'),
            ('Are captions available?',
             'Yes. Captions are available in English plus 16 additional languages where supported by the partner.'),
        ]),
    ]
    return render_template('course_faq.html', course=course, faq_groups=faq_groups)


# ── /courses landing + collections ────────────────────────────────────────────
@app.route('/courses')
def courses_landing():
    cats = [
        ('computer-science', 'Computer Science'),
        ('data-science', 'Data Science'),
        ('business', 'Business'),
        ('information-technology', 'Information Technology'),
        ('language-learning', 'Language Learning'),
        ('math-logic', 'Math and Logic'),
        ('physical-science', 'Physical Science and Engineering'),
        ('social-sciences', 'Social Sciences'),
        ('arts-humanities', 'Arts and Humanities'),
        ('health', 'Health'),
        ('personal-development', 'Personal Development'),
    ]
    return render_template('courses_landing.html', categories=cats)


@app.route('/courses/free')
def courses_free():
    courses = (Course.query.filter_by(is_free=True)
               .order_by(Course.enrolled_count.desc()).limit(72).all())
    return render_template('courses_collection.html',
                           collection='Free',
                           heading='Free online courses',
                           blurb='Audit any of these courses at no cost. Upgrade to the certificate track anytime.',
                           courses=courses)


@app.route('/courses/with-certificate')
def courses_with_certificate():
    courses = (Course.query.filter_by(has_certificate=True)
               .order_by(Course.enrolled_count.desc()).limit(72).all())
    return render_template('courses_collection.html',
                           collection='With certificate',
                           heading='Courses with a shareable certificate',
                           blurb='Earn a verifiable certificate to share on LinkedIn or with employers.',
                           courses=courses)


@app.route('/courses/in-spanish')
def courses_in_spanish():
    needles = ['Spanish', 'español', 'en español', 'idioma']
    q = Course.query.filter(
        db.or_(*[Course.title.ilike(f'%{n}%') for n in needles] +
               [Course.description.ilike(f'%{n}%') for n in needles])
    )
    courses = q.order_by(Course.enrolled_count.desc()).limit(72).all()
    return render_template('courses_collection.html',
                           collection='In Spanish',
                           heading='Cursos completos en español',
                           blurb='Browse courses taught in Spanish — from beginner language to professional-track content.',
                           courses=courses)


# ── /partner/<slug>/about ─────────────────────────────────────────────────────
@app.route('/partner/<slug>/about')
def partner_about(slug):
    partner = Partner.query.filter_by(slug=slug).first_or_404()
    expertise = _GD_PARTNER_ABOUT_EXPERTISE.get(partner.partner_type, ['Education', 'Research', 'Public engagement'])
    # Featured = top 5 by enrollment.
    featured = (Course.query.filter_by(partner_id=partner.id)
                .order_by(Course.enrolled_count.desc()).limit(5).all())
    rows = Course.query.filter_by(partner_id=partner.id).all()
    total_courses = len(rows)
    total_learners = '{:,}'.format(sum(c.enrolled_count or 0 for c in rows))
    if rows:
        avg_rating = '{:.2f}'.format(
            sum((c.rating or 0) for c in rows) / max(len(rows), 1))
    else:
        avg_rating = 'n/a'
    # Deterministic founding year from slug.
    seed = int(_gd_hashlib.md5(partner.slug.encode()).hexdigest()[:6], 16)
    founded = 1800 + (seed % 220)
    return render_template('partner_about.html',
                           partner=partner, expertise=expertise,
                           featured=featured, total_courses=total_courses,
                           total_learners=total_learners,
                           avg_rating=avg_rating, founded=founded)


# ── /compare ──────────────────────────────────────────────────────────────────
@app.route('/compare')
def course_compare():
    all_courses = (Course.query.order_by(Course.enrolled_count.desc())
                   .limit(200).all())
    a_slug = request.args.get('a')
    b_slug = request.args.get('b')
    a = Course.query.filter_by(slug=a_slug).first() if a_slug else None
    b = Course.query.filter_by(slug=b_slug).first() if b_slug else None
    return render_template('course_compare.html', all_courses=all_courses,
                           a=a, b=b)


# === GUI deepen END ===


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
