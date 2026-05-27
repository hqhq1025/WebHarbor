"""Google Search mirror — Flask application.

Adapted from the commerce skeleton to a search/reference engine:
  Product       -> SearchResult / Topic
  Category      -> Vertical (All, Images, Videos, News, Maps, Shopping, Books)
  Cart          -> SearchHistory (recent searches)
  Order         -> Collection (bundle of saved results)
  Wishlist      -> Bookmark (saved result)
  Review        -> ResultFeedback (thumbs up/down + comment)
"""

import os
import json
import hashlib
import random
import re
from datetime import datetime, timedelta
from urllib.parse import urlparse


def hash_int(s):
    """Stable deterministic hash for byte-id seeding (replaces hash() which
    is randomized per process unless PYTHONHASHSEED=0)."""
    return int(hashlib.md5(s.encode('utf-8')).hexdigest()[:8], 16)

from flask import (
    Flask, render_template, request, redirect, url_for, flash,
    jsonify, abort, session, send_from_directory,
)
from flask_sqlalchemy import SQLAlchemy
from flask_login import (
    LoginManager, UserMixin, login_user, logout_user, login_required, current_user,
)
from flask_bcrypt import Bcrypt
from flask_wtf import FlaskForm, CSRFProtect
from wtforms import StringField, PasswordField, TextAreaField, BooleanField, SelectField, IntegerField
from wtforms.validators import DataRequired, Email, Length, EqualTo, Optional
from sqlalchemy import or_, and_, func, desc

HERE = os.path.dirname(os.path.abspath(__file__))

# ---------- app bootstrap ---------------------------------------------------

app = Flask(__name__)
app.config['SECRET_KEY'] = 'google-search-mirror-secret-key-do-not-use-in-prod'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(HERE, 'instance', 'google_search.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
os.makedirs(os.path.join(HERE, 'instance'), exist_ok=True)

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_mgr = LoginManager(app)
login_mgr.login_view = 'login'
login_mgr.login_message = 'Please sign in to continue.'
csrf = CSRFProtect(app)


# ---------- models ----------------------------------------------------------

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(200), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(200), nullable=False)
    name = db.Column(db.String(120), nullable=False, default='')
    avatar_letter = db.Column(db.String(1), default='G')
    safe_search = db.Column(db.String(20), default='moderate')  # off, moderate, strict
    region = db.Column(db.String(30), default='US')
    language = db.Column(db.String(10), default='en')
    results_per_page = db.Column(db.Integer, default=10)
    dark_mode = db.Column(db.Boolean, default=False)
    created = db.Column(db.DateTime, default=datetime.utcnow)

    history = db.relationship('SearchHistory', backref='user', lazy='dynamic',
                              cascade='all, delete-orphan')
    bookmarks = db.relationship('Bookmark', backref='user', lazy='dynamic',
                                cascade='all, delete-orphan')
    collections = db.relationship('Collection', backref='user', lazy='dynamic',
                                  cascade='all, delete-orphan')
    feedback = db.relationship('ResultFeedback', backref='user', lazy='dynamic',
                               cascade='all, delete-orphan')
    alerts = db.relationship('Alert', backref='user', lazy='dynamic',
                             cascade='all, delete-orphan')

    def set_password(self, raw):
        self.password_hash = bcrypt.generate_password_hash(raw).decode('utf-8')

    def check_password(self, raw):
        return bcrypt.check_password_hash(self.password_hash, raw)


class Vertical(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(40), unique=True, nullable=False)
    name = db.Column(db.String(40), nullable=False)
    icon = db.Column(db.String(40), default='search')
    is_default = db.Column(db.Boolean, default=False)
    sort_order = db.Column(db.Integer, default=0)


class Topic(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(120), unique=True, nullable=False, index=True)
    name = db.Column(db.String(200), nullable=False)
    wiki_title = db.Column(db.String(200))
    summary = db.Column(db.Text, default='')
    wiki_url = db.Column(db.String(400))
    hero_image = db.Column(db.String(400))
    images_json = db.Column(db.Text, default='[]')
    result_count = db.Column(db.Integer, default=1000000)
    search_time = db.Column(db.Float, default=0.4)
    knowledge_type = db.Column(db.String(40), default='')  # place, person, planet, software, etc.
    # Phase 9 additions — task-driven SERP completion
    query_text = db.Column(db.String(400), default='', index=True)  # exact WebVoyager query
    task_id = db.Column(db.String(40), default='', index=True)  # e.g. "Google Search--0"
    keywords_json = db.Column(db.Text, default='[]')  # JSON list of searchable keywords
    answer_token = db.Column(db.Text, default='')  # canonical answer string for task verification
    knowledge_panel_json = db.Column(db.Text, default='{}')  # rich panel JSON

    results = db.relationship('SearchResult', backref='topic', lazy='select',
                              cascade='all, delete-orphan', order_by='SearchResult.rank')
    paa_questions = db.relationship('PaaQuestion', backref='topic', lazy='select',
                                    cascade='all, delete-orphan', order_by='PaaQuestion.rank')
    related_queries = db.relationship('RelatedQuery', backref='topic', lazy='select',
                                      cascade='all, delete-orphan', order_by='RelatedQuery.rank')
    knowledge_facts = db.relationship('KnowledgeFact', backref='topic', lazy='select',
                                      cascade='all, delete-orphan', order_by='KnowledgeFact.rank')

    def get_images(self):
        try:
            return json.loads(self.images_json or '[]')
        except Exception:
            return []


class SearchResult(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    topic_id = db.Column(db.Integer, db.ForeignKey('topic.id'), nullable=False, index=True)
    title = db.Column(db.String(400), nullable=False)
    url = db.Column(db.String(600), nullable=False)
    display_url = db.Column(db.String(200))
    snippet = db.Column(db.Text)
    source = db.Column(db.String(40))  # wikipedia, youtube, etc.
    source_type = db.Column(db.String(20), default='web')  # web, news, image, video
    rank = db.Column(db.Integer, default=0)
    image = db.Column(db.String(400))
    # R4 enrichment: SERP card metadata
    result_type = db.Column(db.String(20), default='organic')  # organic, featured, ad
    breadcrumb = db.Column(db.String(300), default='')         # en.wikipedia.org › wiki › <Topic>
    favicon = db.Column(db.String(300), default='')            # favicon URL

    feedback = db.relationship('ResultFeedback', backref='result', lazy='dynamic',
                               cascade='all, delete-orphan')
    bookmarks = db.relationship('Bookmark', backref='result', lazy='dynamic',
                                cascade='all, delete-orphan')


class PaaQuestion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    topic_id = db.Column(db.Integer, db.ForeignKey('topic.id'), nullable=False, index=True)
    question = db.Column(db.String(400), nullable=False)
    answer = db.Column(db.Text, default='')
    rank = db.Column(db.Integer, default=0)


class RelatedQuery(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    topic_id = db.Column(db.Integer, db.ForeignKey('topic.id'), nullable=False, index=True)
    term = db.Column(db.String(200), nullable=False)
    rank = db.Column(db.Integer, default=0)


class KnowledgeFact(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    topic_id = db.Column(db.Integer, db.ForeignKey('topic.id'), nullable=False, index=True)
    key = db.Column(db.String(80), nullable=False)
    value = db.Column(db.String(500), nullable=False)
    rank = db.Column(db.Integer, default=0)


class SearchHistory(db.Model):
    """Recent searches — the 'cart' equivalent for a search engine."""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    q = db.Column(db.String(400), nullable=False)
    vertical = db.Column(db.String(40), default='all')
    searched_at = db.Column(db.DateTime, default=datetime.utcnow)
    result_count = db.Column(db.Integer, default=0)


class Bookmark(db.Model):
    """Saved search result — the 'wishlist' equivalent."""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    result_id = db.Column(db.Integer, db.ForeignKey('search_result.id'), nullable=True)
    # For manual bookmarks
    title = db.Column(db.String(400), nullable=False)
    url = db.Column(db.String(600), nullable=False)
    snippet = db.Column(db.Text, default='')
    note = db.Column(db.Text, default='')
    collection_id = db.Column(db.Integer, db.ForeignKey('collection.id'), nullable=True, index=True)
    created = db.Column(db.DateTime, default=datetime.utcnow)


class Collection(db.Model):
    """A bundle of bookmarks — the 'order' equivalent.
    Users create collections to organize their saved results (like folders).
    """
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, default='')
    color = db.Column(db.String(10), default='#4285F4')
    is_public = db.Column(db.Boolean, default=False)
    created = db.Column(db.DateTime, default=datetime.utcnow)

    bookmarks = db.relationship('Bookmark', backref='collection', lazy='dynamic')


class ResultFeedback(db.Model):
    """Thumbs up/down + optional comment — the 'review' equivalent for results."""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    result_id = db.Column(db.Integer, db.ForeignKey('search_result.id'), nullable=False, index=True)
    rating = db.Column(db.String(10), default='helpful')  # helpful, not_helpful, spam
    comment = db.Column(db.Text, default='')
    created = db.Column(db.DateTime, default=datetime.utcnow)


class Alert(db.Model):
    """Google Alerts — notify on new results for a query."""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    term = db.Column(db.String(200), nullable=False)
    frequency = db.Column(db.String(20), default='daily')  # as_it_happens, daily, weekly
    sources = db.Column(db.String(80), default='automatic')  # automatic, news, blogs, etc.
    region = db.Column(db.String(30), default='any')
    created = db.Column(db.DateTime, default=datetime.utcnow)
    active = db.Column(db.Boolean, default=True)


class Doodle(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(80), unique=True, nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, default='')
    published = db.Column(db.DateTime, default=datetime.utcnow)
    image_url = db.Column(db.String(400))


class GoogleApp(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(40), nullable=False)
    icon = db.Column(db.String(40), default='search')
    color = db.Column(db.String(10), default='#4285F4')
    url = db.Column(db.String(200), default='/')


class TrendingTerm(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    term = db.Column(db.String(200), nullable=False)
    rank = db.Column(db.Integer, default=0)
    volume = db.Column(db.Integer, default=1000)
    trend_direction = db.Column(db.String(10), default='up')


@login_mgr.user_loader
def load_user(uid):
    return db.session.get(User, int(uid))


# ---------- forms -----------------------------------------------------------

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember = BooleanField('Remember me')


class RegisterForm(FlaskForm):
    name = StringField('Full name', validators=[DataRequired(), Length(min=2, max=80)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    confirm = PasswordField('Confirm password', validators=[DataRequired(), EqualTo('password')])


class AccountEditForm(FlaskForm):
    name = StringField('Full name', validators=[DataRequired(), Length(min=2, max=80)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    safe_search = SelectField('SafeSearch',
                              choices=[('off', 'Off'), ('moderate', 'Moderate'), ('strict', 'Strict')])
    region = StringField('Region')
    language = StringField('Language')
    results_per_page = IntegerField('Results per page')
    dark_mode = BooleanField('Dark mode')


class ChangePasswordForm(FlaskForm):
    current = PasswordField('Current password', validators=[DataRequired()])
    new = PasswordField('New password', validators=[DataRequired(), Length(min=6)])
    confirm = PasswordField('Confirm new password', validators=[DataRequired(), EqualTo('new')])


class CollectionForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired(), Length(min=1, max=120)])
    description = TextAreaField('Description')
    color = StringField('Color', default='#4285F4')
    is_public = BooleanField('Public')


class BookmarkForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired(), Length(max=400)])
    url = StringField('URL', validators=[DataRequired(), Length(max=600)])
    snippet = TextAreaField('Snippet')
    note = TextAreaField('Personal note')
    collection_id = SelectField('Collection', coerce=int)


class AlertForm(FlaskForm):
    term = StringField('Query', validators=[DataRequired(), Length(max=200)])
    frequency = SelectField('Frequency', choices=[('as_it_happens', 'As-it-happens'),
                                                  ('daily', 'At most once a day'),
                                                  ('weekly', 'At most once a week')])
    sources = SelectField('Sources', choices=[('automatic', 'Automatic'), ('news', 'News'),
                                              ('blogs', 'Blogs'), ('video', 'Video'),
                                              ('books', 'Books'), ('discussions', 'Discussions'),
                                              ('finance', 'Finance')])
    region = StringField('Region', default='any')


class FeedbackForm(FlaskForm):
    rating = SelectField('Rating', choices=[('helpful', 'Helpful'), ('not_helpful', 'Not helpful'), ('spam', 'Spam')])
    comment = TextAreaField('Comment', validators=[Optional(), Length(max=1000)])


# ---------- context helpers -------------------------------------------------

@app.context_processor
def inject_globals():
    from flask_wtf.csrf import generate_csrf
    trending = TrendingTerm.query.order_by(TrendingTerm.rank).limit(10).all()
    apps = GoogleApp.query.all()
    return {
        'nav_verticals': Vertical.query.order_by(Vertical.sort_order).all(),
        'trending_terms': trending,
        'google_apps': apps,
        'current_year': datetime.utcnow().year,
        'csrf_token_value': generate_csrf(),
    }


def fmt_count(n):
    if n is None:
        return '0'
    return f'{n:,}'

app.jinja_env.filters['fmt_count'] = fmt_count


def _answer_leak_tokens(answer_token: str):
    """Extract 'leak' substrings from an answer_token: long words/numbers/dates
    that would literally give the answer away."""
    if not answer_token:
        return []
    tokens = set()
    for m in re.findall(r"\d{1,3}(?:[,.]\d{3})+|\d+\.\d+|\d+", answer_token):
        if len(m) >= 2:
            tokens.add(m.lower())
    months = ('january','february','march','april','may','june','july','august',
              'september','october','november','december')
    for mo in months:
        if mo in answer_token.lower():
            tokens.add(mo)
    # Proper nouns (consecutive Capitalised words)
    for m in re.findall(r"[A-Z][a-zA-Z]{3,}(?:\s+[A-Z][a-zA-Z]+){0,3}", answer_token):
        if len(m) >= 5:
            tokens.add(m.lower())
    # Units that often appear in single-value answers
    for unit in ('meters', 'feet', 'ft', 'km', 'mph', 'seconds'):
        if unit in answer_token.lower():
            tokens.add(unit)
    return [t for t in tokens if len(t) >= 2]


def fact_leaks_answer(fact, answer_token):
    """Return True when a KnowledgeFact.value substring-matches the answer."""
    try:
        val = (fact.value or '').lower()
        key = (fact.key or '').lower()
    except Exception:
        return False
    if not answer_token:
        return False
    answer_low = answer_token.lower()
    # Direct containment
    if val and val in answer_low:
        return True
    if answer_low and answer_low[:60] in val:
        return True
    # Leak-token overlap: numeric or named tokens shared between fact.value and answer
    leak_tokens = _answer_leak_tokens(answer_token)
    hits = 0
    for t in leak_tokens:
        if len(t) >= 3 and t in val:
            hits += 1
    # Require 2+ distinct leak tokens before flagging, to avoid false positives
    # like "James Gunn" matching a director name on an unrelated fact
    if hits >= 2:
        return True
    # Single very-specific leak (e.g. "5,895 m" for Kilimanjaro)
    for t in leak_tokens:
        if ',' in t or '.' in t:
            if t in val:
                return True
    # Key-based heuristic: "initial release" / "record" / "elevation" fields
    # are typically the answer field in these tasks, drop them
    if key in {'initial release', 'release', 'elevation', 'record',
               'distance', 'population', 'founded', 'height'}:
        if any(t in val for t in leak_tokens):
            return True
    return False


app.jinja_env.tests['fact_leaks_answer'] = fact_leaks_answer
app.jinja_env.filters['fact_leaks_answer'] = fact_leaks_answer


def summary_for_panel(summary: str, answer_token: str, max_chars: int = 240) -> str:
    """Trim summary to first 1-2 sentences with any answer-leaking sentence removed."""
    if not summary:
        return ''
    sents = re.split(r'(?<=[.!?])\s+', summary.strip())
    out = []
    leak_tokens = _answer_leak_tokens(answer_token)
    for s in sents:
        s_low = s.lower()
        if any(t in s_low for t in leak_tokens) and leak_tokens:
            continue
        out.append(s)
        if sum(len(x) for x in out) >= max_chars:
            break
    joined = ' '.join(out).strip()
    if len(joined) > max_chars:
        joined = joined[:max_chars].rsplit(' ', 1)[0] + '...'
    return joined or (summary[:80] + '...')


app.jinja_env.filters['summary_for_panel'] = summary_for_panel


def fmt_time_ago(dt):
    if not dt:
        return ''
    delta = datetime.utcnow() - dt
    if delta.days > 365:
        return f'{delta.days // 365}y ago'
    if delta.days > 30:
        return f'{delta.days // 30}mo ago'
    if delta.days > 0:
        return f'{delta.days}d ago'
    if delta.seconds > 3600:
        return f'{delta.seconds // 3600}h ago'
    if delta.seconds > 60:
        return f'{delta.seconds // 60}m ago'
    return 'just now'

app.jinja_env.filters['time_ago'] = fmt_time_ago


# ---------- search helpers --------------------------------------------------

STOPWORDS = {
    'the', 'a', 'an', 'of', 'in', 'on', 'at', 'to', 'for', 'with',
    'and', 'or', 'is', 'are', 'be', 'by', 'from', 'as', 'that', 'this',
    'find', 'show', 'tell', 'me', 'what', 'who', 'when', 'where', 'how',
    'search', 'google', 'please', 'get', 'look', 'up', 'about', 'has',
    'have', 'had', 'do', 'does', 'did', 'was', 'were', 'been', 'being',
    'it', 'its', 'his', 'her', 'their', 'they', 'them', 'i', 'you', 'we',
    'my', 'your', 'our', 'if', 'then', 'than', 'there', 'here', 'so',
    'also', 'list', 'give', 'brief', 'current', 'latest', 'most', 'out',
}


def _tokenize(text):
    if not text:
        return []
    return [t for t in re.findall(r'[a-z0-9]+', text.lower())
            if t not in STOPWORDS and len(t) >= 2]


def _score_topic(topic, tokens):
    """Score a topic against search tokens.

    Returns a tuple (primary, secondary) where primary = tokens matched in
    the core fields (query_text, name, wiki_title, keywords) and secondary
    counts matches in summary/answer. This prevents an off-topic topic from
    winning just because its long answer_token happens to mention a keyword.
    """
    if not tokens:
        return (0, 0)
    try:
        keywords = json.loads(topic.keywords_json or '[]')
    except Exception:
        keywords = []
    core = ' '.join([
        (topic.query_text or '').lower(),
        (topic.name or '').lower(),
        (topic.wiki_title or '').lower(),
        ' '.join(str(k).lower() for k in keywords),
    ])
    aux = ' '.join([
        (topic.summary or '').lower(),
        (topic.answer_token or '').lower(),
    ])
    primary = sum(1 for t in set(tokens) if t in core)
    secondary = sum(1 for t in set(tokens) if t in aux)
    return (primary, secondary)


def competing_topics(q, exclude_id=None, limit=4):
    """Return topics that compete with a query (second-best matches).

    Used to inject sibling/distractor SERP cards when the query is partial.
    """
    if not q:
        return []
    tokens = _tokenize(q.lower())
    if not tokens:
        return []
    scored = []
    for cand in Topic.query.all():
        if exclude_id is not None and cand.id == exclude_id:
            continue
        primary, secondary = _score_topic(cand, tokens)
        if primary >= max(1, len(tokens) // 2):
            scored.append((primary, secondary, cand))
    # sort by primary desc, secondary desc
    scored.sort(key=lambda x: (-x[0], -x[1]))
    return [c for _, _, c in scored[:limit]]


def find_topic(q):
    """Find the best matching topic for a query string.

    1. Exact query_text match (case-insensitive)
    2. Scored relevance against name/keywords/summary/answer with stopword filter
    3. Fallback slug/name contains
    """
    if not q:
        return None
    q_norm = q.strip().lower()

    # 1. Exact query_text match
    t = Topic.query.filter(func.lower(Topic.query_text) == q_norm).first()
    if t:
        return t

    # 2. Scored relevance
    tokens = _tokenize(q_norm)
    if tokens:
        min_required = max(1, len(tokens) // 2)
        best = None
        best_primary = 0
        best_total = 0
        for cand in Topic.query.all():
            primary, secondary = _score_topic(cand, tokens)
            total = primary + secondary
            # Require at least min_required tokens total, prefer core matches
            if total >= min_required and (
                primary > best_primary
                or (primary == best_primary and total > best_total)
            ):
                best = cand
                best_primary = primary
                best_total = total
        if best:
            return best

    # 3. Fallback — slug / substring
    slug = re.sub(r'[^a-z0-9]+', '_', q_norm).strip('_')
    t = Topic.query.filter_by(slug=slug).first()
    if t:
        return t
    t = Topic.query.filter(func.lower(Topic.name).like(f'%{q_norm}%')).first()
    if t:
        return t
    t = Topic.query.filter(func.lower(Topic.summary).like(f'%{q_norm}%')).first()
    if t:
        return t
    words = [w for w in re.split(r'\s+', q_norm) if len(w) > 2]
    if words:
        for w in words:
            t = Topic.query.filter(or_(
                func.lower(Topic.name).like(f'%{w}%'),
                func.lower(Topic.slug).like(f'%{w}%'),
            )).first()
            if t:
                return t
    return None


def filter_results_by_query(results, tokens, vertical='all'):
    """Dynamic filtering of a list of SearchResult against query tokens.

    Used as a fallback when an exact-query SERP isn't seeded: we take the
    topic's full result list and re-rank by token overlap in title+snippet.
    """
    if not tokens:
        filtered = list(results)
    else:
        scored = []
        for r in results:
            hay = f'{(r.title or "").lower()} {(r.snippet or "").lower()} {(r.source or "").lower()}'
            s = sum(1 for t in set(tokens) if t in hay)
            scored.append((s, r))
        scored.sort(key=lambda x: (-x[0], x[1].rank))
        filtered = [r for _, r in scored]
    if vertical and vertical != 'all':
        filtered = [r for r in filtered
                    if (r.source_type or 'web') == vertical or vertical == 'all']
    return filtered


# ---------- routes: static pages --------------------------------------------

@app.route('/')
def index():
    doodle = Doodle.query.order_by(desc(Doodle.published)).first()
    return render_template('index.html', doodle=doodle)


@app.route('/search')
def search():
    q = (request.args.get('q') or '').strip()
    vertical = (request.args.get('tbm') or 'all').strip()
    page = max(1, int(request.args.get('page', 1)))

    if not q:
        return redirect(url_for('index'))

    # Log history if logged in
    if current_user.is_authenticated:
        # Don't duplicate an exact query within the last 60s
        recent = SearchHistory.query.filter_by(user_id=current_user.id, q=q).order_by(
            desc(SearchHistory.searched_at)
        ).first()
        if not recent or (datetime.utcnow() - recent.searched_at).seconds > 60:
            db.session.add(SearchHistory(
                user_id=current_user.id,
                q=q,
                vertical=vertical,
                result_count=8,
            ))
            db.session.commit()

    topic = find_topic(q)
    results = []
    paa = []
    related = []
    knowledge = None
    result_count = random.randint(100_000, 10_000_000)
    search_time = round(random.uniform(0.24, 0.88), 2)
    answer_token = ''
    knowledge_panel = {}

    if topic:
        tokens = _tokenize(q)
        exact = (topic.query_text or '').strip().lower() == q.strip().lower()
        if exact or not tokens:
            results = list(topic.results)
        else:
            # Dynamic filter on stored entries
            results = filter_results_by_query(list(topic.results), tokens, vertical)
            if not results:
                results = list(topic.results)
        paa = topic.paa_questions
        related = topic.related_queries
        knowledge = topic
        result_count = topic.result_count
        search_time = topic.search_time
        answer_token = topic.answer_token or ''
        try:
            knowledge_panel = json.loads(topic.knowledge_panel_json or '{}')
        except Exception:
            knowledge_panel = {}
        # Inject distractor SERP cards from competing topics when query is
        # partial / ambiguous — this prevents the SERP from trivially handing
        # out the answer in a single topic's first result.
        if not exact and tokens:
            competitors = competing_topics(q, exclude_id=topic.id, limit=4)
            if competitors:
                # Take up to 2 top results from each competitor
                distractor_cards = []
                for c in competitors:
                    for r in list(c.results)[:2]:
                        distractor_cards.append(r)
                # Interleave: keep first 2 gold results at top, then alternate
                gold_top = results[:2]
                gold_rest = results[2:]
                merged = list(gold_top)
                # Weave: 1 distractor, 1 gold, 1 distractor, 1 gold...
                i = j = 0
                while i < len(distractor_cards) or j < len(gold_rest):
                    if i < len(distractor_cards):
                        merged.append(distractor_cards[i]); i += 1
                    if j < len(gold_rest):
                        merged.append(gold_rest[j]); j += 1
                results = merged

    template = 'search.html'
    if vertical == 'images':
        template = 'search_images.html'
    elif vertical == 'videos':
        template = 'search_videos.html'
    elif vertical == 'news':
        template = 'search_news.html'
    elif vertical == 'maps':
        template = 'search_maps.html'
    elif vertical == 'shopping':
        template = 'search_shopping.html'
    elif vertical == 'books':
        template = 'search_books.html'
    elif vertical == 'finance':
        template = 'search_finance.html'

    # Attach per-result external-cache link so the template can link each card
    # to its `/external/<host>/<path>` snapshot when available. Falls back to
    # the internal /topic/ route when no scraped snapshot exists (Plan B).
    annotated = []
    for r in results:
        ext_path = external_path_for(r.url)
        annotated.append({
            'id': r.id,
            'title': r.title,
            'url': r.url,
            'display_url': r.display_url,
            'snippet': r.snippet,
            'source': r.source,
            'source_type': r.source_type,
            'rank': r.rank,
            'image': r.image,
            'topic': r.topic,
            'external_path': ext_path,
            'result_type': getattr(r, 'result_type', 'organic') or 'organic',
            'breadcrumb': getattr(r, 'breadcrumb', '') or '',
            'favicon': getattr(r, 'favicon', '') or '',
        })

    # Panel visibility: only show for bio / fact-lookup tasks.
    show_panel = should_show_panel(topic, q)

    # Pagination: 10 results per page (Google default). Always show 10 page
    # links if total results suggest it — synthetic but matches real Google.
    per_page = 10
    total_pages = max(1, min(10, (len(annotated) + per_page - 1) // per_page))
    if total_pages == 1 and topic:
        # Topic-anchored SERPs always show 10 page tabs so paginate tasks are
        # navigable even when the local mirror only has 8 real results.
        total_pages = 10
    page_results = annotated[(page - 1) * per_page : page * per_page]
    has_prev = page > 1
    has_next = page < total_pages

    return render_template(
        template,
        q=q, page=page, vertical=vertical,
        topic=topic, results=page_results, all_results=annotated,
        paa=paa, related=related, knowledge=knowledge,
        result_count=result_count, search_time=search_time,
        answer_token=answer_token,
        knowledge_panel=knowledge_panel,
        show_panel=show_panel,
        total_pages=total_pages, has_prev=has_prev, has_next=has_next, per_page=per_page,
    )


@app.route('/lucky')
def feeling_lucky():
    q = (request.args.get('q') or '').strip()
    if not q:
        return redirect(url_for('index'))
    topic = find_topic(q)
    if topic:
        return redirect(url_for('topic_detail', slug=topic.slug))
    # Random topic
    t = Topic.query.order_by(func.random()).first()
    if t:
        return redirect(url_for('topic_detail', slug=t.slug))
    return redirect(url_for('index'))


@app.route('/topic/<slug>')
def topic_detail(slug):
    topic = Topic.query.filter_by(slug=slug).first_or_404()
    related_topics = Topic.query.filter(Topic.id != topic.id).order_by(func.random()).limit(6).all()
    return render_template('topic_detail.html', topic=topic, related_topics=related_topics)


_EXT_INDEX_CACHE = None

def _load_external_index():
    """Lazy-load a {sha: url} index covering all cached snapshots on disk."""
    global _EXT_INDEX_CACHE
    if _EXT_INDEX_CACHE is not None:
        return _EXT_INDEX_CACHE
    cache_dir = os.path.join(app.static_folder, 'external_cache')
    idx = {}
    if os.path.isdir(cache_dir):
        for fn in os.listdir(cache_dir):
            if not fn.endswith('.json'):
                continue
            try:
                with open(os.path.join(cache_dir, fn), 'r', encoding='utf-8') as f:
                    m = json.load(f)
                sha = fn[:-5]  # strip .json
                u = m.get('url')
                if u:
                    idx[sha] = u
            except Exception:
                continue
    _EXT_INDEX_CACHE = idx
    return idx


def _find_cache_for_path(cached_path: str, query_string: str = ''):
    """Given an incoming /external/<path> request, locate the matching cache file.

    Flask URL-decodes the path (so `%E2%80%93` becomes `–` etc.) which breaks a
    naive re-hash. We fix this by scanning the on-disk index for any cached url
    whose `netloc+path` or decoded form matches. The optional `query_string`
    argument is folded into hash candidates and used to disambiguate index hits
    when multiple cached entries share the same netloc+path (e.g.
    `trends.google.com/trends/explore?geo=US-NY` vs `?geo=US-OH&q=columbus`).
    """
    from hashlib import sha256
    from urllib.parse import unquote, quote

    suffix = ('?' + query_string) if query_string else ''

    # First try: direct hash of https:// + cached_path + ?query
    for scheme in ('https://', 'http://'):
        cand = scheme + cached_path + suffix
        h = sha256(cand.encode('utf-8')).hexdigest()[:40]
        base = os.path.join(app.static_folder, 'external_cache', h)
        if os.path.exists(base + '.html'):
            return h, cand

    # Second try: re-encode path back to %xx form and hash
    # The cached sha is from the percent-encoded version (as scraped) so we
    # try quoting the decoded path.
    enc = quote(cached_path, safe="/:@?=&%#+")
    for scheme in ('https://', 'http://'):
        cand = scheme + enc + suffix
        h = sha256(cand.encode('utf-8')).hexdigest()[:40]
        base = os.path.join(app.static_folder, 'external_cache', h)
        if os.path.exists(base + '.html'):
            return h, cand

    # Third try: legacy lookup ignoring the query string entirely (handles
    # links generated before this fix landed).
    if suffix:
        legacy_sha, legacy_url = _find_cache_for_path(cached_path, '')
        if legacy_sha:
            return legacy_sha, legacy_url

    # Fourth try: scan the index for a URL whose netloc+path matches either
    # encoded-or-decoded variant. Prefer entries whose query string matches
    # exactly; fall back to the first netloc+path match.
    idx = _load_external_index()
    target_variants = {
        cached_path,
        unquote(cached_path),
        quote(cached_path, safe="/:@?=&%#+"),
    }
    fallback = None
    for sha, u in idx.items():
        p = urlparse(u)
        np = (p.netloc + p.path).lstrip('/')
        if np in target_variants or unquote(np) in target_variants:
            if p.query == query_string:
                return sha, u
            if fallback is None:
                fallback = (sha, u)
    if fallback:
        return fallback
    return None, None


@app.route('/external/<path:cached_path>')
def external_view(cached_path):
    """Serve a cached snapshot of a real upstream page.

    `cached_path` looks like `en.wikipedia.org/wiki/Guardians_of_the_Galaxy_Vol._3`.
    We hash the canonical URL to look up the cached HTML + metadata on disk.
    """
    qs = request.query_string.decode('utf-8') if request.query_string else ''
    sha, canonical = _find_cache_for_path(cached_path, qs)
    if not sha:
        abort(404)
    base = os.path.join(app.static_folder, 'external_cache', sha)
    html_path = base + '.html'
    meta_path = base + '.json'
    if not os.path.exists(html_path) or not os.path.exists(meta_path):
        abort(404)
    with open(html_path, 'r', encoding='utf-8') as f:
        body = f.read()
    with open(meta_path, 'r', encoding='utf-8') as f:
        meta = json.load(f)
    return render_template('external_view.html', body=body, meta=meta, original_url=canonical)


def external_path_for(url: str) -> str:
    """Return the `/external/<host>/<path>` route for a scraped upstream URL,
    or None if no cached snapshot exists on disk."""
    from hashlib import sha256
    if not url:
        return None
    h = sha256(url.encode('utf-8')).hexdigest()[:40]
    base = os.path.join(app.static_folder, 'external_cache', h)
    if not os.path.exists(base + '.html'):
        return None
    p = urlparse(url)
    out = '/external/' + (p.netloc + p.path).lstrip('/')
    if p.query:
        out += '?' + p.query
    return out


def should_show_panel(topic, query: str) -> bool:
    """Decide whether to surface the right-side knowledge panel for a task.

    Real Google hides the panel for list / news / comparison queries and shows
    it for single-entity fact lookups (bios, release dates, measurements)."""
    if topic is None:
        return False
    q = (query or '').lower()
    hide_markers = [
        'latest news', 'most popular', 'top 5', 'top 3', 'top 10', 'top-10',
        'top n', 'compare', 'comparison', 'differences between',
        'list', 'list of', 'tell me about', 'most played', 'upcoming',
        'trending', 'browse', 'discover which', 'explain the major',
        'article that explains', 'top-3', 'top-5',
    ]
    for m in hide_markers:
        if m in q:
            return False
    show_markers = [
        'bio', 'biography', 'release date', 'height', 'elevation',
        'population', 'area', 'distance', 'world record', 'born',
        'how tall', 'how high', 'how many', 'how old', 'what year',
        'which year', 'what is the name', 'what is the', 'who is',
    ]
    for m in show_markers:
        if m in q:
            return True
    # Default behavior: show only for obvious single-entity types
    ktype = (topic.knowledge_type or '').lower()
    if ktype in ('person', 'place', 'movie', 'geography', 'measurement', 'fact'):
        return True
    return False


@app.route('/url')
def url_redirect():
    """Same-origin Google-style /url?q=<ext>&topic=<slug> redirect.

    The sandboxed browser cannot load public internet URLs, so instead of
    opening the external page we synthesize a cached summary for the agent.
    If `topic` is present (or resolvable from `q`), we render topic_detail
    for that topic. Otherwise we fall back to a /search?q=<q>."""
    ext = (request.args.get('q') or '').strip()
    slug = (request.args.get('topic') or '').strip()
    topic = None
    if slug:
        topic = Topic.query.filter_by(slug=slug).first()
    if topic is None and ext:
        # Try to resolve by matching a stored SearchResult url
        sr = SearchResult.query.filter_by(url=ext).first()
        if sr is not None:
            topic = sr.topic
    if topic is not None:
        related_topics = Topic.query.filter(Topic.id != topic.id).order_by(func.random()).limit(6).all()
        return render_template('topic_detail.html', topic=topic, related_topics=related_topics)
    if ext:
        return redirect(url_for('search', q=ext))
    return redirect(url_for('index'))


@app.route('/trending')
def trending():
    terms = TrendingTerm.query.order_by(TrendingTerm.rank).all()
    return render_template('trending.html', terms=terms)


@app.route('/doodles')
def doodles():
    dlist = Doodle.query.order_by(desc(Doodle.published)).all()
    return render_template('doodles.html', doodles=dlist)


@app.route('/doodle/<slug>')
def doodle_detail(slug):
    d = Doodle.query.filter_by(slug=slug).first_or_404()
    return render_template('doodle_detail.html', doodle=d)


@app.route('/advanced')
def advanced_search():
    return render_template('advanced.html')


# --- R4 deep sub-pages ----------------------------------------------------

@app.route('/webhp')
def webhp():
    """Homepage shortcut variant — kept for /webhp link compatibility."""
    return redirect(url_for('index'))


@app.route('/imghp')
def imghp():
    """Images homepage — same UI as /search?tbm=images for a stock query."""
    return render_template('imghp.html')


@app.route('/videohp')
def videohp():
    """Videos homepage."""
    return render_template('videohp.html')


@app.route('/search/snapshot')
@app.route('/search/snapshot/<slug>')
def search_snapshot(slug=None):
    """AI Overview / Search Generative Experience snapshot.

    Surfaces the answer_token + knowledge_panel as a synthesized AI-style
    summary, citing the topic's top results.
    """
    q = (request.args.get('q') or '').strip()
    topic = None
    if slug:
        topic = Topic.query.filter_by(slug=slug).first()
    if topic is None and q:
        topic = find_topic(q)
    return render_template('search_snapshot.html', topic=topic, q=q)


@app.route('/preferences/region', methods=['GET', 'POST'])
def preferences_region():
    """Region picker — Google's 'Search results region' setting."""
    saved = False
    if request.method == 'POST':
        region = request.form.get('region', 'US')[:30]
        if current_user.is_authenticated:
            current_user.region = region
            db.session.commit()
        else:
            session['region'] = region
        saved = True
    return render_template('preferences_region.html', saved=saved)


@app.route('/preferences/languages', methods=['GET', 'POST'])
def preferences_languages():
    """Languages picker — controls UI language + result language preferences."""
    saved = False
    if request.method == 'POST':
        lang = request.form.get('language', 'en')[:10]
        if current_user.is_authenticated:
            current_user.language = lang
            db.session.commit()
        else:
            session['language'] = lang
        saved = True
    return render_template('preferences_languages.html', saved=saved)


_HELP_TOPICS = {
    'basics': ('Search basics', 'Get more out of Google Search by learning the fundamentals of how queries work.'),
    'operators': ('Search operators', 'Use operators like site:, intitle:, intext:, "exact phrase", and minus terms.'),
    'images': ('Search Images', 'Find images, reverse-image search with Google Lens, and filter by colour or licence.'),
    'safesearch': ('SafeSearch', 'Filter explicit content from Search results across every Google product.'),
    'voice': ('Voice Search', 'Speak your query — works on Chrome, Android, and iOS.'),
    'shortcuts': ('Search shortcuts', 'Tips for calculator, conversions, weather, dictionary, and other inline answers.'),
    'discover': ('Discover feed', 'Personalised content card stream that learns from your interests.'),
    'history': ('Search history', 'View, delete, or pause your saved search activity at any time.'),
    'autocomplete': ('Autocomplete predictions', 'How predictions are generated and how to remove inappropriate ones.'),
    'languages': ('Languages on Search', 'Change your Google Search interface and content language.'),
}


@app.route('/search/help')
def search_help_index():
    return render_template('search_help_index.html', topics=_HELP_TOPICS)


@app.route('/search/help/<topic>')
def search_help(topic):
    if topic not in _HELP_TOPICS:
        abort(404)
    title, body = _HELP_TOPICS[topic]
    return render_template('search_help.html',
                           help_topic=topic, help_title=title, help_body=body,
                           topics=_HELP_TOPICS)


_SUPPORT_ANSWERS = {
    134479: ('How Search works',
             'When you type a query into Google Search, our systems look across hundreds of billions of pages in the Search index and return the most relevant, useful results.'),
    181196: ('Manage your activity controls',
             'You can view, manage, and delete the activity that Google saves to your Google Account at any time.'),
    9637484: ('Refine web searches',
             'Operators include site:, related:, intext:, intitle:, AROUND(n), filetype:, and the OR operator (in caps) for alternation.'),
    173733:  ('Remove personal information from Google',
              'Submit a request and Google reviews material that may violate one of our removal policies.'),
    9132983: ('Sign in to your Google Account',
              'Use any Google product by signing in once. Your account follows you across Search, Maps, Gmail, and more.'),
    9657411: ('SafeSearch settings',
              'SafeSearch helps you filter explicit content like nudity and violence from your Google Search results.'),
    9134408: ('Trending searches',
              'Trends shows the relative popularity of search terms over time and across regions.'),
    9627632: ('Search by image with Lens',
              'Identify objects, landmarks, plants, and animals using your camera or any image saved on your device.'),
    9645136: ('Browsing and search activity on Chrome',
              'Customise what Chrome saves about your activity, including browsing history and downloads.'),
    142949:  ('Search settings overview',
              'Adjust language, region, results-per-page, and SafeSearch from a single dashboard.'),
}


@app.route('/support/answer/<int:answer_id>')
def support_answer(answer_id):
    if answer_id not in _SUPPORT_ANSWERS:
        abort(404)
    title, body = _SUPPORT_ANSWERS[answer_id]
    return render_template('support_answer.html',
                           answer_id=answer_id,
                           answer_title=title, answer_body=body)


@app.route('/about')
def about():
    return render_template('about.html')


@app.route('/how_search_works')
def how_search_works():
    return render_template('how_search_works.html')


@app.route('/privacy')
def privacy():
    return render_template('privacy.html')


@app.route('/terms')
def terms():
    return render_template('terms.html')


@app.route('/settings', methods=['GET', 'POST'])
@app.route('/preferences', methods=['GET', 'POST'])
@login_required
def settings():
    if request.method == 'POST':
        safe_search = request.form.get('safe_search', 'moderate')
        region = request.form.get('region', 'US')
        language = request.form.get('language', 'en')
        results_per_page = int(request.form.get('results_per_page', 10))
        dark_mode = request.form.get('dark_mode') == 'on'

        current_user.safe_search = safe_search
        current_user.region = region
        current_user.language = language
        current_user.results_per_page = results_per_page
        current_user.dark_mode = dark_mode
        db.session.commit()
        flash('Settings saved successfully.')
        return redirect(url_for('settings'))
    return render_template('settings.html')


@app.route('/advertising')
def advertising():
    return render_template('advertising.html')


@app.route('/business')
def business():
    return render_template('business.html')


# --- Google App stubs (one template, rendered per app) ---

@app.route('/gmail')
def gmail():
    return render_template('app_gmail.html')


@app.route('/drive')
def drive():
    return render_template('app_drive.html')


@app.route('/calendar')
def calendar():
    return render_template('app_calendar.html')


@app.route('/maps')
def maps():
    return render_template('app_maps.html')


@app.route('/youtube')
def youtube():
    return render_template('app_youtube.html')


@app.route('/translate')
def translate():
    return render_template('app_translate.html')


@app.route('/scholar')
def scholar():
    return render_template('app_scholar.html')


@app.route('/news')
def news():
    return render_template('app_news.html')


# --- Additional app-launcher stubs ---------------------------------------
# The Google apps grid links to /meet, /docs, /sheets etc. — without these
# routes every click out of the launcher hits a 404. Each renders the
# shared `app_placeholder.html` template parameterised by name/color.

_APP_STUBS = [
    ('meet',     'Google Meet',     '#00897b', 'Premium video meetings for everyone. Stay in touch with HD video calls.'),
    ('chat',     'Google Chat',     '#34a853', 'Streamlined messaging for teams that supercharges collaboration.'),
    ('docs',     'Google Docs',     '#4285f4', 'Create and edit documents online, for free. Built-in collaboration tools.'),
    ('sheets',   'Google Sheets',   '#0f9d58', 'Online spreadsheets with built-in formulas, pivot tables, and conditional formatting.'),
    ('slides',   'Google Slides',   '#f4b400', 'Create and edit beautiful presentations directly in your browser.'),
    ('photos',   'Google Photos',   '#4285f4', 'Your photos and videos, organised and easy to find.'),
    ('contacts', 'Google Contacts', '#4285f4', 'Sync, back up, and organise your contacts across every device.'),
    ('keep',     'Google Keep',     '#f4b400', 'Capture, edit, and share notes from anywhere on any device.'),
    ('books',    'Google Books',    '#4285f4', 'Search the full text of millions of books from libraries and publishers worldwide.'),
    ('shopping', 'Google Shopping', '#4285f4', 'Search, compare, and shop for products across thousands of retailers.'),
    ('finance',  'Google Finance',  '#34a853', 'Real-time quotes, financial news, and personalised watchlists.'),
    ('earth',    'Google Earth',    '#4285f4', 'Explore the world from above with high-resolution satellite imagery.'),
    ('arts',     'Arts & Culture',  '#ea4335', 'Discover artworks, collections, and stories from over 2,000 museums.'),
    ('lens',     'Google Lens',     '#4285f4', 'Search what you see — translate text, identify plants, and learn more.'),
    ('play',     'Google Play',     '#f4b400', 'Apps, games, movies, books, and more — all in one place.'),
]


def _make_app_stub(slug, name, color, desc):
    def view():
        return render_template('app_placeholder.html',
                               app_name=name, app_color=color, app_desc=desc)
    view.__name__ = slug  # endpoint name = slug, e.g. url_for('meet')
    return view


for _slug, _name, _color, _desc in _APP_STUBS:
    app.add_url_rule(f'/{_slug}', _slug,
                     _make_app_stub(_slug, _name, _color, _desc))


# ---------- routes: auth ----------------------------------------------------

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('account'))
    form = LoginForm()
    if form.validate_on_submit():
        u = User.query.filter_by(email=form.email.data.lower()).first()
        if u and u.check_password(form.password.data):
            login_user(u, remember=bool(form.remember.data))
            flash('Welcome back!', 'success')
            nxt = request.args.get('next')
            return redirect(nxt or url_for('account'))
        flash('Invalid email or password', 'error')
    return render_template('login.html', form=form)


@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('account'))
    form = RegisterForm()
    if form.validate_on_submit():
        if User.query.filter_by(email=form.email.data.lower()).first():
            flash('An account with that email already exists', 'error')
        else:
            u = User(
                email=form.email.data.lower(),
                name=form.name.data,
                avatar_letter=form.name.data[0].upper() if form.name.data else 'G',
            )
            u.set_password(form.password.data)
            db.session.add(u)
            db.session.commit()
            login_user(u)
            flash('Account created!', 'success')
            return redirect(url_for('account'))
    return render_template('register.html', form=form)


@app.route('/logout')
def logout():
    logout_user()
    flash('Signed out.', 'success')
    return redirect(url_for('index'))


# ---------- routes: account -------------------------------------------------

@app.route('/account')
@login_required
def account():
    history = current_user.history.order_by(desc(SearchHistory.searched_at)).limit(20).all()
    collections = current_user.collections.order_by(desc(Collection.created)).all()
    bookmarks = current_user.bookmarks.order_by(desc(Bookmark.created)).limit(12).all()
    alerts = current_user.alerts.order_by(desc(Alert.created)).limit(8).all()
    stats = {
        'searches': current_user.history.count(),
        'bookmarks': current_user.bookmarks.count(),
        'collections': current_user.collections.count(),
        'alerts': current_user.alerts.filter_by(active=True).count(),
    }
    return render_template('account.html', history=history, collections=collections,
                           bookmarks=bookmarks, alerts=alerts, stats=stats)


@app.route('/account/edit', methods=['GET', 'POST'])
@login_required
def account_edit():
    form = AccountEditForm(obj=current_user)
    if form.validate_on_submit():
        current_user.name = form.name.data
        current_user.email = form.email.data.lower()
        current_user.safe_search = form.safe_search.data
        current_user.region = form.region.data
        current_user.language = form.language.data
        current_user.results_per_page = form.results_per_page.data or 10
        current_user.dark_mode = form.dark_mode.data
        current_user.avatar_letter = form.name.data[0].upper() if form.name.data else 'G'
        db.session.commit()
        flash('Profile updated', 'success')
        return redirect(url_for('account'))
    return render_template('account_edit.html', form=form)


@app.route('/account/password', methods=['GET', 'POST'])
@login_required
def change_password():
    form = ChangePasswordForm()
    if form.validate_on_submit():
        if not current_user.check_password(form.current.data):
            flash('Current password is incorrect', 'error')
        else:
            current_user.set_password(form.new.data)
            db.session.commit()
            flash('Password updated', 'success')
            return redirect(url_for('account'))
    return render_template('change_password.html', form=form)


@app.route('/account/delete', methods=['POST'])
@login_required
def account_delete():
    u = db.session.get(User, current_user.id)
    logout_user()
    if u:
        db.session.delete(u)
        db.session.commit()
    flash('Your account has been deleted.', 'success')
    return redirect(url_for('index'))


# ---------- routes: history -------------------------------------------------

@app.route('/history')
@login_required
def history():
    items = current_user.history.order_by(desc(SearchHistory.searched_at)).all()
    return render_template('history.html', items=items)


@app.route('/history/clear', methods=['POST'])
@login_required
def history_clear():
    current_user.history.delete()
    db.session.commit()
    flash('Search history cleared', 'success')
    return redirect(url_for('history'))


@app.route('/history/delete/<int:hid>', methods=['POST'])
@login_required
def history_delete(hid):
    h = SearchHistory.query.filter_by(id=hid, user_id=current_user.id).first_or_404()
    db.session.delete(h)
    db.session.commit()
    return redirect(url_for('history'))


# ---------- routes: bookmarks -----------------------------------------------

@app.route('/bookmarks')
@login_required
def bookmarks():
    col_id = request.args.get('collection', type=int)
    q = current_user.bookmarks
    if col_id:
        q = q.filter_by(collection_id=col_id)
    items = q.order_by(desc(Bookmark.created)).all()
    collections = current_user.collections.order_by(Collection.name).all()
    active = Collection.query.get(col_id) if col_id else None
    return render_template('bookmarks.html', items=items, collections=collections, active=active)


@app.route('/bookmarks/add', methods=['GET', 'POST'])
@login_required
def bookmark_add():
    form = BookmarkForm()
    form.collection_id.choices = [(0, '(No collection)')] + \
        [(c.id, c.name) for c in current_user.collections.all()]
    # Prefill from query args
    if request.method == 'GET':
        form.title.data = request.args.get('title', '')
        form.url.data = request.args.get('url', '')
        form.snippet.data = request.args.get('snippet', '')
    if form.validate_on_submit():
        bm = Bookmark(
            user_id=current_user.id,
            title=form.title.data,
            url=form.url.data,
            snippet=form.snippet.data,
            note=form.note.data,
            collection_id=form.collection_id.data or None,
        )
        db.session.add(bm)
        db.session.commit()
        flash('Bookmark added', 'success')
        return redirect(url_for('bookmarks'))
    return render_template('bookmark_add.html', form=form)


@app.route('/bookmark/<int:bid>/delete', methods=['POST'])
@login_required
def bookmark_delete(bid):
    bm = Bookmark.query.filter_by(id=bid, user_id=current_user.id).first_or_404()
    db.session.delete(bm)
    db.session.commit()
    flash('Bookmark removed', 'success')
    return redirect(url_for('bookmarks'))


@app.route('/api/bookmark/toggle', methods=['POST'])
@csrf.exempt
@login_required
def api_bookmark_toggle():
    """AJAX endpoint (kept for backward compat). Accepts JSON or form data."""
    data = request.get_json(silent=True) or request.form
    result_id = data.get('result_id')
    if not result_id:
        return jsonify({'error': 'result_id required'}), 400
    try:
        result_id = int(result_id)
    except (ValueError, TypeError):
        return jsonify({'error': 'invalid result_id'}), 400
    r = db.session.get(SearchResult, result_id)
    if not r:
        return jsonify({'error': 'not found'}), 404
    existing = Bookmark.query.filter_by(user_id=current_user.id, result_id=result_id).first()
    if existing:
        db.session.delete(existing)
        db.session.commit()
        return jsonify({'saved': False, 'count': current_user.bookmarks.count()})
    bm = Bookmark(
        user_id=current_user.id,
        result_id=result_id,
        title=r.title,
        url=r.url,
        snippet=r.snippet or '',
    )
    db.session.add(bm)
    db.session.commit()
    return jsonify({'saved': True, 'count': current_user.bookmarks.count()})


@app.route('/bookmark/save/<int:result_id>', methods=['POST'])
@login_required
def bookmark_save_form(result_id):
    """Form-POST version of bookmark toggle — works without JavaScript."""
    r = db.session.get(SearchResult, result_id)
    if not r:
        abort(404)
    existing = Bookmark.query.filter_by(user_id=current_user.id, result_id=result_id).first()
    if existing:
        db.session.delete(existing)
        db.session.commit()
        flash('Bookmark removed', 'success')
    else:
        bm = Bookmark(
            user_id=current_user.id,
            result_id=result_id,
            title=r.title,
            url=r.url,
            snippet=r.snippet or '',
        )
        db.session.add(bm)
        db.session.commit()
        flash('Result saved to bookmarks', 'success')
    return redirect(request.referrer or url_for('bookmarks'))


# ---------- routes: collections ---------------------------------------------

@app.route('/collections')
@login_required
def collections():
    items = current_user.collections.order_by(desc(Collection.created)).all()
    return render_template('collections.html', items=items)


@app.route('/collections/new', methods=['GET', 'POST'])
@login_required
def collection_new():
    form = CollectionForm()
    if form.validate_on_submit():
        c = Collection(
            user_id=current_user.id,
            name=form.name.data,
            description=form.description.data,
            color=form.color.data or '#4285F4',
            is_public=bool(form.is_public.data),
        )
        db.session.add(c)
        db.session.commit()
        flash('Collection created', 'success')
        return redirect(url_for('collections'))
    return render_template('collection_form.html', form=form, title='New collection')


@app.route('/collection/<int:cid>')
@login_required
def collection_detail(cid):
    c = Collection.query.filter_by(id=cid, user_id=current_user.id).first_or_404()
    items = c.bookmarks.order_by(desc(Bookmark.created)).all()
    return render_template('collection_detail.html', collection=c, items=items)


@app.route('/collection/<int:cid>/edit', methods=['GET', 'POST'])
@login_required
def collection_edit(cid):
    c = Collection.query.filter_by(id=cid, user_id=current_user.id).first_or_404()
    form = CollectionForm(obj=c)
    if form.validate_on_submit():
        c.name = form.name.data
        c.description = form.description.data
        c.color = form.color.data or '#4285F4'
        c.is_public = bool(form.is_public.data)
        db.session.commit()
        flash('Collection updated', 'success')
        return redirect(url_for('collection_detail', cid=cid))
    return render_template('collection_form.html', form=form, title='Edit collection')


@app.route('/collection/<int:cid>/delete', methods=['POST'])
@login_required
def collection_delete(cid):
    c = Collection.query.filter_by(id=cid, user_id=current_user.id).first_or_404()
    # Orphan its bookmarks (don't delete them)
    for bm in c.bookmarks.all():
        bm.collection_id = None
    db.session.delete(c)
    db.session.commit()
    flash('Collection deleted', 'success')
    return redirect(url_for('collections'))


# ---------- routes: alerts --------------------------------------------------

@app.route('/alerts')
@login_required
def alerts():
    items = current_user.alerts.order_by(desc(Alert.created)).all()
    return render_template('alerts.html', items=items)


@app.route('/alerts/new', methods=['GET', 'POST'])
@login_required
def alert_new():
    form = AlertForm()
    form.term.data = form.term.data or request.args.get('q', '')
    if form.validate_on_submit():
        a = Alert(
            user_id=current_user.id,
            term=form.term.data,
            frequency=form.frequency.data,
            sources=form.sources.data,
            region=form.region.data,
        )
        db.session.add(a)
        db.session.commit()
        flash('Alert created', 'success')
        return redirect(url_for('alerts'))
    return render_template('alert_new.html', form=form)


@app.route('/alert/<int:aid>/toggle', methods=['POST'])
@login_required
def alert_toggle(aid):
    a = Alert.query.filter_by(id=aid, user_id=current_user.id).first_or_404()
    a.active = not a.active
    db.session.commit()
    return redirect(url_for('alerts'))


@app.route('/alert/<int:aid>/delete', methods=['POST'])
@login_required
def alert_delete(aid):
    a = Alert.query.filter_by(id=aid, user_id=current_user.id).first_or_404()
    db.session.delete(a)
    db.session.commit()
    flash('Alert removed', 'success')
    return redirect(url_for('alerts'))


@app.route('/alert/<int:aid>/update', methods=['POST'])
@login_required
def alert_update(aid):
    a = Alert.query.filter_by(id=aid, user_id=current_user.id).first_or_404()
    freq = request.form.get('frequency', '').strip()
    if freq in ('as_it_happens', 'daily', 'weekly'):
        a.frequency = freq
        db.session.commit()
        flash('Alert frequency updated', 'success')
    else:
        flash('Invalid frequency', 'error')
    return redirect(url_for('alerts'))


# ---------- routes: feedback ------------------------------------------------

@app.route('/result/<int:rid>/feedback', methods=['POST'])
@login_required
def result_feedback(rid):
    r = SearchResult.query.get_or_404(rid)
    rating = request.form.get('rating', 'helpful')
    comment = request.form.get('comment', '')
    fb = ResultFeedback(
        user_id=current_user.id,
        result_id=rid,
        rating=rating,
        comment=comment,
    )
    db.session.add(fb)
    db.session.commit()
    flash('Feedback submitted. Thank you!', 'success')
    return redirect(request.referrer or url_for('topic_detail', slug=r.topic.slug))


@app.route('/feedback/<int:fid>/delete', methods=['POST'])
@login_required
def feedback_delete(fid):
    fb = ResultFeedback.query.filter_by(id=fid, user_id=current_user.id).first_or_404()
    db.session.delete(fb)
    db.session.commit()
    return redirect(request.referrer or url_for('account'))


# ---------- routes: API -----------------------------------------------------

@app.route('/api/history/add', methods=['POST'])
@csrf.exempt
@login_required
def api_history_add():
    """AJAX endpoint (kept for backward compat). Accepts JSON or form data."""
    data = request.get_json(silent=True) or request.form
    query = (data.get('q') or '').strip()
    if not query:
        return jsonify({'error': 'q required'}), 400
    h = SearchHistory(user_id=current_user.id, q=query)
    db.session.add(h)
    db.session.commit()
    return jsonify({'success': True, 'count': current_user.history.count()})


@app.route('/history/add', methods=['POST'])
@login_required
def history_add_form():
    """Form-POST version of history add — works without JavaScript."""
    query = (request.form.get('q') or '').strip()
    if query:
        # Don't duplicate an exact query within the last 60s
        recent = SearchHistory.query.filter_by(user_id=current_user.id, q=query).order_by(
            desc(SearchHistory.searched_at)
        ).first()
        if not recent or (datetime.utcnow() - recent.searched_at).seconds > 60:
            db.session.add(SearchHistory(user_id=current_user.id, q=query))
            db.session.commit()
    return redirect(request.referrer or url_for('history'))


@app.route('/api/topics')
@csrf.exempt
def api_topics():
    q = request.args.get('q', '').strip().lower()
    query = Topic.query
    if q:
        query = query.filter(func.lower(Topic.name).like(f'%{q}%'))
    topics = query.limit(20).all()
    return jsonify([
        {'slug': t.slug, 'name': t.name, 'summary': (t.summary or '')[:200], 'hero': t.hero_image}
        for t in topics
    ])


@app.route('/api/suggestions')
@csrf.exempt
def api_suggestions():
    """R5: autocomplete payload — history (when logged in) + topic matches
    + trending fallback + naive spelling-correction hint.

    Deterministic ordering keyed off the query string so identical queries
    produce identical responses (helps recording / replay).
    """
    q = request.args.get('q', '').strip()
    qlow = q.lower()
    limit = max(1, min(int(request.args.get('limit', 10)), 20))

    history_terms = []
    if current_user.is_authenticated and qlow:
        hist = (SearchHistory.query
                .filter_by(user_id=current_user.id)
                .filter(func.lower(SearchHistory.q).like(f'{qlow}%'))
                .order_by(desc(SearchHistory.searched_at))
                .limit(5).all())
        history_terms = [{'kind': 'history', 'text': h.q} for h in hist]

    topic_terms = []
    if qlow:
        topics = (Topic.query
                  .filter(func.lower(Topic.name).like(f'%{qlow}%'))
                  .limit(limit).all())
        topic_terms = [{'kind': 'topic', 'text': t.name, 'slug': t.slug} for t in topics]

    related_terms = []
    if qlow:
        rqs = (RelatedQuery.query
               .filter(func.lower(RelatedQuery.term).like(f'%{qlow}%'))
               .order_by(RelatedQuery.rank)
               .limit(limit).all())
        related_terms = [{'kind': 'related', 'text': rq.term} for rq in rqs]

    trending = []
    if not qlow:
        tr = TrendingTerm.query.order_by(TrendingTerm.rank).limit(limit).all()
        trending = [{'kind': 'trending', 'text': t.term} for t in tr]

    # Naive spelling-correct: when no topic_terms match, look for the
    # closest topic by trigram-ish overlap. Deterministic.
    spelling = None
    if qlow and not topic_terms and len(qlow) >= 4:
        # cheap: any topic whose lowercased name shares the first 3 chars
        cand = (Topic.query
                .filter(func.lower(Topic.name).like(f'{qlow[:3]}%'))
                .limit(5).all())
        if cand:
            # pick the one with the smallest length-difference (stable tiebreak by slug)
            best = min(cand, key=lambda c: (abs(len(c.name) - len(q)), c.slug))
            if best.name.lower() != qlow:
                spelling = {'kind': 'spelling', 'text': best.name,
                            'original': q}

    # Merge: history first, then topic, then related; cap by limit.
    merged = []
    seen = set()
    for grp in (history_terms, topic_terms, related_terms, trending):
        for item in grp:
            key = item['text'].lower()
            if key in seen:
                continue
            seen.add(key)
            merged.append(item)
            if len(merged) >= limit:
                break
        if len(merged) >= limit:
            break

    return jsonify({
        'query': q,
        'suggestions': merged,
        'spelling': spelling,
    })


# ---------- R6 edge-case routes --------------------------------------------
# Each one renders a small dedicated template so the agent gets a real
# page (HTTP 200) rather than a silent 404 when navigating from a SERP
# notice / safe-search prompt / voice modal etc.

@app.route('/sorry/index')
def safesearch_required():
    """Google's classic 'sorry' interstitial — query flagged as needing
    safe-search confirmation. Returns 200 with an explicit page so the
    agent can read the explanation and pick a continuation.
    """
    cont = request.args.get('continue') or url_for('index')
    q = request.args.get('q') or ''
    reason = request.args.get('reason', 'safesearch')
    return render_template('safesearch_required.html',
                           continue_url=cont, q=q, reason=reason)


@app.route('/dmca/notice/<int:notice_id>')
def dmca_notice(notice_id):
    """DMCA takedown notice page — describes a removed result. Notice
    fields are derived deterministically from the URL id so tasks can
    target a specific complainant/title."""
    # Deterministic synthesis — same id always renders the same record.
    titles = [
        'The Complete History of Modern Photography (2019 ed.)',
        'Hidden Cuisines: A Chef\'s Atlas (2021)',
        'Architectural Marvels of the 20th Century',
        'Field Guide to North American Mammals',
        'The Definitive Encyclopaedia of Mythology',
    ]
    complainants = [
        'Atlas Heritage Press, LLC',
        'Northwoods Publishing Group',
        'Skybridge Editorial Services',
        'Beacon House Publishers',
        'Meridian University Press',
    ]
    idx = notice_id % len(titles)
    notice = {
        'id': notice_id,
        'title': titles[idx],
        'complainant': complainants[idx],
        'filed_on': '2026-03-14',
        'urls_removed': 1 + (notice_id % 4),
        'jurisdiction': 'United States (17 U.S.C. § 512)',
    }
    return render_template('dmca_notice.html', notice=notice)


@app.route('/search/disambiguate')
def disambiguate():
    """Multiple-meaning disambiguation page. Looks up topics whose
    `name` field overlaps the requested title and renders a list with
    knowledge-card thumbnails for each candidate."""
    title = (request.args.get('title') or '').strip()
    if not title:
        return redirect(url_for('index'))
    matches = (Topic.query
               .filter(func.lower(Topic.name).like(f'%{title.lower()}%'))
               .order_by(Topic.id)
               .limit(8).all())
    return render_template('disambiguate.html', title=title, matches=matches)


@app.route('/trending/region/<region_code>')
def trending_region(region_code):
    """Trending-by-region page. Some regions are flagged as restricted;
    a banner explains the local-law restriction without revealing the
    underlying terms."""
    restricted = {'CN', 'IR', 'KP', 'SY', 'RU'}
    code = (region_code or '').upper()
    is_restricted = code in restricted
    terms = []
    if not is_restricted:
        # Deterministic slice keyed off region code so re-renders match.
        all_terms = TrendingTerm.query.order_by(TrendingTerm.rank).all()
        if all_terms:
            start = (sum(ord(c) for c in code) % max(1, len(all_terms) - 12))
            terms = all_terms[start:start + 12]
    return render_template('trending_region.html',
                           region_code=code,
                           is_restricted=is_restricted,
                           terms=terms)


# ---------- R7: SEO, locale, performance, accessibility, takeout ----------
# Added in iteration 7/10.  Routes are stateless so byte-id reset is
# unaffected (no extra rows are written by any /r7/* endpoint).

import time as _R7_time

# Locale list lifted from seed_data so we don't duplicate the source of truth.
try:
    from seed_data import TOP_LOCALES as _R7_LOCALES
except Exception:  # pragma: no cover — seed_data must be importable
    _R7_LOCALES = []


def _r7_canonical_root(req):
    """Return scheme://host with no trailing slash for use in sitemap / JSON-LD."""
    return f"{req.scheme}://{req.host}"


@app.context_processor
def _r7_locale_inject():
    """Surface hl/gl + locale list to every template so the header picker
    and JSON-LD blocks can render without per-route plumbing."""
    hl = (request.args.get('hl') or session.get('hl')
          or (current_user.language if current_user.is_authenticated else None)
          or 'en')
    gl = (request.args.get('gl') or session.get('gl')
          or (current_user.region if current_user.is_authenticated else None)
          or 'US')
    hl = (hl or 'en')[:8]
    gl = (gl or 'US')[:4]
    if request.args.get('hl'):
        session['hl'] = hl
    if request.args.get('gl'):
        session['gl'] = gl
    rtl = any(L[0] == hl and L[4] for L in _R7_LOCALES)
    return {
        'hl': hl,
        'gl': gl,
        'locale_rtl': rtl,
        'top_locales': _R7_LOCALES,
        'canonical_root': _r7_canonical_root(request),
    }


@app.before_request
def _r7_render_timer():
    """Capture per-request wall-clock for the X-Render-Time header + the
    /performance dashboard."""
    from flask import g
    g._r7_t0 = _R7_time.perf_counter()


@app.after_request
def _r7_render_timer_after(resp):
    from flask import g
    t0 = getattr(g, '_r7_t0', None)
    if t0 is not None:
        elapsed_ms = (_R7_time.perf_counter() - t0) * 1000.0
        resp.headers['X-Render-Time-Ms'] = f'{elapsed_ms:.2f}'
    if request.path in ('/sitemap.xml', '/sitemap-trending.xml',
                        '/sitemap-topics.xml', '/sitemap-doodles.xml',
                        '/opensearch.xml', '/robots.txt'):
        resp.headers['Cache-Control'] = 'public, max-age=3600'
    return resp


@app.route('/robots.txt')
def r7_robots():
    body = (
        "User-agent: *\n"
        "Allow: /search\n"
        "Disallow: /account\n"
        "Disallow: /history\n"
        "Disallow: /bookmarks\n"
        "Disallow: /collection\n"
        "Disallow: /takeout\n"
        f"Sitemap: {_r7_canonical_root(request)}/sitemap.xml\n"
    )
    return body, 200, {'Content-Type': 'text/plain; charset=utf-8'}


@app.route('/opensearch.xml')
def r7_opensearch():
    """OpenSearch description doc. Real Google ships an equivalent
    referenced from <link rel='search'> on every page."""
    root = _r7_canonical_root(request)
    body = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<OpenSearchDescription xmlns="http://a9.com/-/spec/opensearch/1.1/">\n'
        '  <ShortName>Google</ShortName>\n'
        '  <Description>Search the web with Google.</Description>\n'
        '  <InputEncoding>UTF-8</InputEncoding>\n'
        f'  <Url type="text/html" template="{root}/search?q={{searchTerms}}"/>\n'
        f'  <Url type="application/x-suggestions+json" template="{root}/api/suggestions?q={{searchTerms}}"/>\n'
        '  <Language>en-US</Language>\n'
        f'  <SearchForm>{root}/</SearchForm>\n'
        '</OpenSearchDescription>\n'
    )
    return body, 200, {'Content-Type': 'application/opensearchdescription+xml; charset=utf-8'}


@app.route('/sitemap.xml')
def r7_sitemap_index():
    """Sitemap index — points at per-section sitemaps."""
    root = _r7_canonical_root(request)
    body = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f'  <sitemap><loc>{root}/sitemap-trending.xml</loc></sitemap>\n'
        f'  <sitemap><loc>{root}/sitemap-topics.xml</loc></sitemap>\n'
        f'  <sitemap><loc>{root}/sitemap-doodles.xml</loc></sitemap>\n'
        '</sitemapindex>\n'
    )
    return body, 200, {'Content-Type': 'application/xml; charset=utf-8'}


@app.route('/sitemap-trending.xml')
def r7_sitemap_trending():
    root = _r7_canonical_root(request)
    parts = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    terms = TrendingTerm.query.order_by(TrendingTerm.rank).all()
    parts.append(f'<url><loc>{root}/trending</loc><changefreq>hourly</changefreq><priority>0.8</priority></url>')
    for t in terms:
        q = (t.term or '').replace(' ', '+')
        parts.append(
            f'<url><loc>{root}/search?q={q}</loc><changefreq>hourly</changefreq><priority>0.6</priority></url>'
        )
    parts.append('</urlset>')
    return '\n'.join(parts), 200, {'Content-Type': 'application/xml; charset=utf-8'}


@app.route('/sitemap-topics.xml')
def r7_sitemap_topics():
    root = _r7_canonical_root(request)
    parts = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    topics = Topic.query.order_by(Topic.id).limit(5000).all()
    for t in topics:
        parts.append(
            f'<url><loc>{root}/topic/{t.slug}</loc><changefreq>weekly</changefreq><priority>0.5</priority></url>'
        )
    parts.append('</urlset>')
    return '\n'.join(parts), 200, {'Content-Type': 'application/xml; charset=utf-8'}


@app.route('/sitemap-doodles.xml')
def r7_sitemap_doodles():
    root = _r7_canonical_root(request)
    parts = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    dlist = Doodle.query.order_by(desc(Doodle.published)).all()
    for d in dlist:
        when = (d.published or datetime(2026, 1, 1)).strftime('%Y-%m-%d')
        parts.append(
            f'<url><loc>{root}/doodle/{d.slug}</loc><lastmod>{when}</lastmod><changefreq>monthly</changefreq><priority>0.4</priority></url>'
        )
    parts.append('</urlset>')
    return '\n'.join(parts), 200, {'Content-Type': 'application/xml; charset=utf-8'}


@app.route('/locales')
@app.route('/preferences/locales')
def r7_locales():
    """50+-locale picker. Lists every (hl, gl) pair as a query-string link
    that re-enters /search?... with the language chip applied."""
    by_hl = {}
    for hl, gl, label, native, rtl in _R7_LOCALES:
        by_hl.setdefault(hl, []).append({'gl': gl, 'label': label, 'native': native, 'rtl': rtl})
    return render_template(
        'r7_locales.html',
        locales=_R7_LOCALES,
        by_hl=sorted(by_hl.items()),
    )


@app.route('/search/syntax')
@app.route('/search/operators')
def r7_search_syntax():
    """Advanced query-syntax help (site:, intitle:, OR, minus, filetype:,
    before:, after:, AROUND(N), define:, ...)."""
    operators = [
        ('site:', 'Restrict results to a single domain', 'climate change site:nytimes.com'),
        ('intitle:', 'Word must appear in the page title', 'intitle:"machine learning"'),
        ('intext:', 'Word must appear in the page body', 'intext:transformer architecture'),
        ('inurl:', 'Word must appear in the URL', 'inurl:wiki gravity'),
        ('"…"', 'Match an exact phrase verbatim', '"to be or not to be"'),
        ('OR', 'Match either of two terms', 'Python OR JavaScript'),
        ('-', 'Exclude a term', 'jaguar -car'),
        ('*', 'Wildcard inside an exact phrase', '"the * theory of relativity"'),
        ('filetype:', 'Restrict to a file extension', 'filetype:pdf annual report'),
        ('related:', 'Find pages similar to a given URL', 'related:nytimes.com'),
        ('cache:', 'Show the cached snapshot of a page', 'cache:wikipedia.org/wiki/Sun'),
        ('AROUND(N)', 'Two terms within N words of each other', 'Tesla AROUND(3) Musk'),
        ('before:', 'Only pages published before a date', 'recession before:2020-01-01'),
        ('after:', 'Only pages published after a date', 'AI breakthroughs after:2024-01-01'),
        ('define:', 'Definition of a word', 'define:serendipity'),
        ('weather', 'Current weather inline answer', 'weather Paris'),
        ('time', 'Current local time inline answer', 'time Tokyo'),
        ('… in …', 'Unit / currency conversion', '25 USD in EUR'),
    ]
    return render_template('r7_search_syntax.html', operators=operators)


@app.route('/accessibility')
@app.route('/accessibility/keyboard')
def r7_accessibility():
    """Keyboard-navigation reference + WCAG statement."""
    shortcuts = [
        ('Tab', 'Move focus to the next search result'),
        ('Shift + Tab', 'Move focus to the previous search result'),
        ('J', 'Jump to the next result (Vimium-style)'),
        ('K', 'Jump to the previous result'),
        ('Enter', 'Open the focused result'),
        ('/', 'Focus the search box'),
        ('Esc', 'Close the autocomplete dropdown'),
        ('Ctrl + Enter', 'Open the result in a new tab'),
        ('Alt + Left', 'Go back to previous page'),
        ('Alt + Right', 'Go forward'),
        ('?', 'Open the keyboard-shortcut overlay'),
        ('Cmd + K', 'Open the Command palette (jump to any vertical/page)'),
        ('Ctrl + K', 'Open the Command palette (Windows / Linux variant)'),
        ('G then T', 'Jump to Trending searches'),
        ('G then D', 'Jump to the Doodles archive'),
        ('G then H', 'Jump to your Search history'),
        ('G then S', 'Jump to Settings'),
        ('G then P', 'Jump to the Command palette'),
        ('G then ?', 'Jump to the syntax glossary (/help/syntax-glossary)'),
    ]
    return render_template('r7_accessibility.html', shortcuts=shortcuts)


@app.route('/performance')
def r7_performance():
    """SERP-render performance dashboard. Shows per-endpoint render-time
    budgets captured by the before_request / after_request hooks."""
    samples = [
        {'path': '/search', 'render_ms': 8.4,
         'note': 'topic-hit, 11 results, knowledge panel'},
        {'path': '/search', 'render_ms': 14.2,
         'note': 'topic-miss, fallback render'},
        {'path': '/topic/<slug>', 'render_ms': 11.6,
         'note': 'topic detail w/ 40+ results'},
        {'path': '/trending', 'render_ms': 4.1,
         'note': 'static list of 208 terms'},
        {'path': '/doodles', 'render_ms': 3.8,
         'note': 'doodle archive (90 rows, paginated)'},
        {'path': '/sitemap-topics.xml', 'render_ms': 22.7,
         'note': '5000-URL sitemap, cached 1h'},
    ]
    return render_template('r7_performance.html', samples=samples)


@app.route('/takeout')
@app.route('/takeout/search-history')
@login_required
def r7_takeout_search_history():
    """Google Takeout — export the signed-in user's search history as JSON
    or CSV (the My Activity format)."""
    fmt = (request.args.get('format') or '').lower()
    rows = SearchHistory.query.filter_by(user_id=current_user.id).order_by(
        desc(SearchHistory.searched_at)
    ).all()
    payload = {
        'product': 'Google Search',
        'export_user': current_user.email,
        'export_user_name': current_user.name,
        'exported_at': datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'),
        'item_count': len(rows),
        'items': [{
            'query': r.q,
            'vertical': r.vertical,
            'searched_at': r.searched_at.strftime('%Y-%m-%dT%H:%M:%SZ'),
            'result_count': r.result_count,
        } for r in rows],
    }
    if fmt == 'json':
        body = json.dumps(payload, indent=2, ensure_ascii=False)
        return body, 200, {
            'Content-Type': 'application/json; charset=utf-8',
            'Content-Disposition': 'attachment; filename="search-history.json"',
        }
    if fmt == 'csv':
        lines = ['searched_at,query,vertical,result_count']
        for it in payload['items']:
            q = (it['query'] or '').replace('"', '""')
            lines.append(f'{it["searched_at"]},"{q}",{it["vertical"]},{it["result_count"]}')
        return '\n'.join(lines), 200, {
            'Content-Type': 'text/csv; charset=utf-8',
            'Content-Disposition': 'attachment; filename="search-history.csv"',
        }
    return render_template('r7_takeout.html', payload=payload)


@app.route('/voice/error/no-mic')
def voice_no_mic():
    """Voice-search modal triggered without microphone permission. The
    agent navigating to /voice without mic access should land here so it
    can confirm the failure mode."""
    return render_template('voice_no_mic.html')


@app.route('/search/zero-results')
def zero_results():
    """Explicit 'zero results found' page with three suggested alternative
    queries derived deterministically from the input string. Reachable
    when the SERP determines no topic match (the /search route also
    inlines a zero-state, but this one is its own URL for cross-page
    chains)."""
    q = (request.args.get('q') or '').strip()
    if not q:
        return redirect(url_for('index'))
    # Pick three deterministic alternatives from existing topic names.
    rng = random.Random(sum(ord(c) for c in q) or 1)
    pool = Topic.query.order_by(Topic.id).limit(80).all()
    alts = []
    if pool:
        sample = rng.sample(pool, min(3, len(pool)))
        alts = [{'q': t.name, 'snippet': (t.summary or '')[:160]} for t in sample]
    return render_template('zero_results.html', q=q, alts=alts)


# ---------- R8 polish: observability + command palette + glossary + dev -----

# Pinned mirror-build identity for byte-id determinism. Updated in lockstep
# with seed_data.MIRROR_REFERENCE_DATE so /healthz and /api/uptime never
# reveal wall-clock time on a fresh /reset.
_R8_BUILD = {
    'version': '8.0.0',
    'build_id': 'gsearch-r8-2026-05-12',
    'build_date': '2026-05-12T12:00:00Z',
    'commit': 'a7c4e9d',
    'env': 'mirror',
}


def _r8_table_counts():
    """Cached row counts for the observability endpoints. Bypassing the
    ORM so the response is cheap even on cold pages."""
    from sqlalchemy import text
    out = {}
    with db.engine.connect() as c:
        for tbl in ('topic', 'search_result', 'paa_question', 'knowledge_fact',
                    'related_query', 'trending_term', 'doodle', 'google_app',
                    'vertical', 'user'):
            try:
                out[tbl] = c.execute(text(f'SELECT COUNT(*) FROM {tbl}')).scalar()
            except Exception:
                out[tbl] = None
    return out


@app.route('/healthz')
def r8_healthz():
    """Liveness probe — returns JSON status of the mirror process + DB.

    Always returns HTTP 200 when the request landed; downstream consumers
    inspect the `status` field. Deterministic by design — no wall-clock
    fields, no per-request randomness."""
    counts = _r8_table_counts()
    db_ok = all(v is not None for v in counts.values())
    body = {
        'status': 'ok' if db_ok else 'degraded',
        'service': 'google-search-mirror',
        'version': _R8_BUILD['version'],
        'build_id': _R8_BUILD['build_id'],
        'build_date': _R8_BUILD['build_date'],
        'checks': {
            'db': 'ok' if db_ok else 'fail',
            'templates': 'ok',
            'static': 'ok',
        },
        'row_counts': counts,
    }
    return jsonify(body)


@app.route('/api/uptime')
def r8_api_uptime():
    """Mirror uptime / build identity. Wall-clock is pinned to the build
    date so byte-id reset never observes time drift."""
    return jsonify({
        'service': 'google-search-mirror',
        'version': _R8_BUILD['version'],
        'build_id': _R8_BUILD['build_id'],
        'build_date': _R8_BUILD['build_date'],
        'commit': _R8_BUILD['commit'],
        'env': _R8_BUILD['env'],
        'reset_endpoint': '/reset',
        'reference_date': '2026-05-12T12:00:00Z',
    })


# Pinned canonical events stream — surfaced from a static array so the
# /api/events response is byte-identical across container restarts.
_R8_EVENTS = [
    {'ts': '2026-05-12T11:58:04Z', 'level': 'info',  'event': 'seed.start',
     'detail': 'building seed DB from source'},
    {'ts': '2026-05-12T11:59:11Z', 'level': 'info',  'event': 'seed.r4.done',
     'detail': '+5 deep results per topic at rank>=10'},
    {'ts': '2026-05-12T11:59:22Z', 'level': 'info',  'event': 'seed.r5.done',
     'detail': '+6 results / +3 PAA / +4 KFs per topic at rank>=20'},
    {'ts': '2026-05-12T11:59:33Z', 'level': 'info',  'event': 'seed.r6.done',
     'detail': '+5 results / +2 PAA / +1 KF per topic at rank>=30'},
    {'ts': '2026-05-12T11:59:44Z', 'level': 'info',  'event': 'seed.r7.done',
     'detail': '+11 deep results / +5 KFs per topic at rank>=40'},
    {'ts': '2026-05-12T11:59:55Z', 'level': 'info',  'event': 'seed.r8.done',
     'detail': '+15 deep results / +4 KFs per topic at rank>=60'},
    {'ts': '2026-05-12T12:00:00Z', 'level': 'info',  'event': 'app.ready',
     'detail': 'mirror accepting requests on /search'},
    {'ts': '2026-05-12T12:00:01Z', 'level': 'info',  'event': 'index.vacuum',
     'detail': 'normalize_seed_db_layout VACUUM complete'},
]


@app.route('/api/events')
def r8_api_events():
    """Append-only event stream (filtered)."""
    level = (request.args.get('level') or '').lower().strip()
    evt = (request.args.get('event') or '').lower().strip()
    items = list(_R8_EVENTS)
    if level:
        items = [e for e in items if e['level'] == level]
    if evt:
        items = [e for e in items if evt in e['event']]
    return jsonify({'items': items, 'count': len(items),
                    'service': 'google-search-mirror'})


@app.route('/api/v3/graphql', methods=['GET', 'POST'])
@app.route('/api/v3-graphql', methods=['GET', 'POST'])
@csrf.exempt
def r8_api_v3_graphql():
    """Mirror's GraphQL-style endpoint.

    GET — returns the schema introspection summary.
    POST — accepts {"query": "...", "variables": {...}} and returns a
    deterministic projection of Topic/SearchResult fields.

    The runtime parser only supports a handful of fields (topic, search,
    trending) but mimics the GraphQL response shape so agents can be
    scripted against a stable mock."""
    if request.method == 'GET':
        return jsonify({
            'service': 'google-search-mirror',
            'graphql_version': '3.0',
            'endpoint': '/api/v3/graphql',
            'methods': ['GET', 'POST'],
            'schema': {
                'Query': {
                    'topic(slug: String!)':
                        'Topic by slug — { slug, name, summary, result_count, results { title, url, rank } }',
                    'search(q: String!, limit: Int = 10)':
                        'Top-N SearchResults — { topic { slug, name }, results { title, url, snippet, rank } }',
                    'trending(limit: Int = 25)':
                        'Trending terms — { term, rank, volume, trend_direction }',
                    'verticals':
                        'Available verticals — { slug, name, sort_order }',
                },
                'Topic': {'slug': 'String', 'name': 'String', 'summary': 'String',
                          'result_count': 'Int', 'results': '[SearchResult]'},
                'SearchResult': {'title': 'String', 'url': 'String', 'snippet': 'String',
                                 'display_url': 'String', 'rank': 'Int'},
                'TrendingTerm': {'term': 'String', 'rank': 'Int', 'volume': 'Int',
                                 'trend_direction': 'String'},
            },
            'example': {
                'POST_body': {'query': 'query { trending(limit: 3) { term rank } }'},
            },
        })

    # POST
    try:
        body = request.get_json(silent=True) or {}
    except Exception:
        body = {}
    query = (body.get('query') or request.values.get('query') or '').strip()
    variables = body.get('variables') or {}

    data = {}
    errors = []

    if not query:
        errors.append({'message': 'missing query field'})
    else:
        ql = query.lower()
        if 'trending' in ql:
            limit = int(variables.get('limit') or 25)
            rows = TrendingTerm.query.order_by(TrendingTerm.rank).limit(limit).all()
            data['trending'] = [{'term': r.term, 'rank': r.rank,
                                 'volume': r.volume, 'trend_direction': r.trend_direction}
                                for r in rows]
        if 'topic(' in ql or 'topic ' in ql or 'topic{' in ql:
            slug = (variables.get('slug') or '').strip()
            if not slug:
                # Try to extract slug:"xxx" inline
                m = re.search(r'slug\s*:\s*"([^"]+)"', query)
                if m:
                    slug = m.group(1)
            if slug:
                t = Topic.query.filter_by(slug=slug).first()
                if t:
                    data['topic'] = {
                        'slug': t.slug, 'name': t.name, 'summary': t.summary,
                        'result_count': t.result_count,
                        'results': [{'title': r.title, 'url': r.url, 'rank': r.rank}
                                    for r in sorted(t.results, key=lambda r: r.rank)[:5]],
                    }
                else:
                    errors.append({'message': f'topic not found: {slug}'})
            else:
                errors.append({'message': 'missing slug variable for topic'})
        if 'search(' in ql or 'search ' in ql:
            q = (variables.get('q') or '').strip()
            if not q:
                m = re.search(r'q\s*:\s*"([^"]+)"', query)
                if m:
                    q = m.group(1)
            limit = int(variables.get('limit') or 10)
            if q:
                t = find_topic(q)
                if t:
                    res = sorted(t.results, key=lambda r: r.rank)[:limit]
                    data['search'] = {
                        'topic': {'slug': t.slug, 'name': t.name},
                        'results': [{'title': r.title, 'url': r.url,
                                     'snippet': r.snippet, 'rank': r.rank}
                                    for r in res],
                    }
                else:
                    data['search'] = {'topic': None, 'results': []}
            else:
                errors.append({'message': 'missing q variable for search'})
        if 'verticals' in ql:
            data['verticals'] = [{'slug': v.slug, 'name': v.name, 'sort_order': v.sort_order}
                                 for v in Vertical.query.order_by(Vertical.sort_order).all()]

    return jsonify({'data': data, 'errors': errors if errors else None})


# Canonical, deterministic recent SERP-change events for the alert webhook.
# Same ordering on every reset because they're a static array.
_R8_SERP_CHANGE_EVENTS = [
    {'change_id': 'serp-001', 'topic_slug': 'chatgpt',
     'kind': 'rank_shift', 'old_rank': 2, 'new_rank': 1,
     'observed_at': '2026-05-11T08:00:00Z',
     'note': 'OpenAI homepage took the top organic slot from Wikipedia'},
    {'change_id': 'serp-002', 'topic_slug': 'climate_change',
     'kind': 'panel_added', 'panel': 'knowledge',
     'observed_at': '2026-05-11T09:15:00Z',
     'note': 'Knowledge panel added for IPCC AR6'},
    {'change_id': 'serp-003', 'topic_slug': 'paris',
     'kind': 'new_result', 'rank': 4,
     'observed_at': '2026-05-11T10:42:00Z',
     'note': 'Time Out Paris article entered top 5'},
    {'change_id': 'serp-004', 'topic_slug': 'nvidia_h100',
     'kind': 'rank_shift', 'old_rank': 4, 'new_rank': 2,
     'observed_at': '2026-05-12T03:00:00Z',
     'note': 'NVIDIA datasheet jumped above third-party reviews'},
    {'change_id': 'serp-005', 'topic_slug': 'tokyo',
     'kind': 'panel_updated', 'panel': 'travel_advisory',
     'observed_at': '2026-05-12T06:00:00Z',
     'note': 'Travel advisory band changed to level 1'},
]


@app.route('/webhook/serp-change-alert', methods=['GET', 'POST'])
@csrf.exempt
def r8_serp_change_webhook():
    """Public webhook endpoint that streams pinned SERP-change events.

    GET — return recent events filtered by ?topic= and/or ?kind=.
    POST — accept a JSON subscription body and echo the validated config
    plus the same events list, so an agent can verify the round-trip.

    Wall-clock-free: every event is pinned to the build-reference date so
    byte-id reset is preserved."""
    topic_q = (request.args.get('topic') or '').strip().lower()
    kind_q = (request.args.get('kind') or '').strip().lower()
    items = list(_R8_SERP_CHANGE_EVENTS)
    if topic_q:
        items = [e for e in items if topic_q in e['topic_slug']]
    if kind_q:
        items = [e for e in items if e['kind'] == kind_q]

    if request.method == 'POST':
        body = request.get_json(silent=True) or {}
        callback = (body.get('callback_url') or '').strip()
        topics = body.get('topics') or []
        kinds = body.get('kinds') or []
        return jsonify({
            'subscription': {
                'callback_url': callback,
                'topics': list(topics) if isinstance(topics, list) else [],
                'kinds':  list(kinds)  if isinstance(kinds,  list) else [],
                'status': 'accepted' if callback else 'rejected',
            },
            'events': items,
            'event_count': len(items),
            'service': 'google-search-mirror',
        })

    return jsonify({
        'endpoint': '/webhook/serp-change-alert',
        'methods': ['GET', 'POST'],
        'events': items,
        'event_count': len(items),
        'docs': '/developer/custom-search-engine-builder',
    })


@app.route('/developer/custom-search-engine-builder', methods=['GET', 'POST'])
def r8_developer_cse_builder():
    """Programmable search-engine builder.

    GET — render a small form that previews the resulting JSON config.
    POST — accept the form, render the same page with the saved config
    summary plus a downloadable JSON snippet.

    The "save" is in-process only — no DB writes — so byte-id reset stays
    intact across rebuilds."""
    saved = None
    cse_id = ''
    verts = [v.slug for v in Vertical.query.order_by(Vertical.sort_order).all()]
    if request.method == 'POST':
        name = (request.form.get('name') or 'My Custom Engine').strip()
        sites = [s.strip() for s in (request.form.get('sites') or '').split(',') if s.strip()]
        vertical = (request.form.get('vertical') or 'all').strip()
        safe_search = (request.form.get('safe_search') or 'moderate').strip()
        # Deterministic CSE id from inputs
        cse_id = 'cse-' + hashlib.md5(
            (name + '|' + ','.join(sorted(sites)) + '|' + vertical).encode('utf-8')
        ).hexdigest()[:12]
        saved = {
            'name': name,
            'sites': sites,
            'vertical': vertical if vertical in verts else 'all',
            'safe_search': safe_search if safe_search in ('off', 'moderate', 'strict') else 'moderate',
            'cse_id': cse_id,
            'embed_snippet': f'<script async src="/cse.js?cx={cse_id}"></script>',
            'endpoint': f'/api/v3/graphql?cx={cse_id}',
        }
    return render_template('r8_developer_cse.html',
                           verts=verts, saved=saved, cse_id=cse_id)


# Per-operator glossary used by /help/syntax-glossary and reused below.
_R8_SYNTAX_GLOSSARY = [
    {'op': 'site:',     'name': 'Domain restriction',
     'desc': 'Limit results to a single domain or subdomain.',
     'pairs_well_with': ['intitle:', 'after:'],
     'example': 'climate change site:nytimes.com',
     'gotcha': 'site:.gov restricts to all U.S. government domains; site:gov does not.'},
    {'op': 'intitle:',  'name': 'Title match',
     'desc': 'The word(s) must appear in the page <title> element.',
     'pairs_well_with': ['site:', 'OR'],
     'example': 'intitle:"machine learning" survey',
     'gotcha': 'Quote multi-word operands or the operator only binds to the first token.'},
    {'op': 'intext:',   'name': 'Body match',
     'desc': 'The term must appear in the body of the page, not just metadata.',
     'pairs_well_with': ['site:'],
     'example': 'intext:transformer architecture',
     'gotcha': 'Body matching is slower than title matching at scale.'},
    {'op': 'inurl:',    'name': 'URL match',
     'desc': 'The term must appear in the URL path or query string.',
     'pairs_well_with': ['site:'],
     'example': 'inurl:wiki gravity',
     'gotcha': 'Punctuation in URLs (.html, /docs) is dropped before matching.'},
    {'op': 'filetype:', 'name': 'File extension',
     'desc': 'Restrict to a single file extension (pdf, doc, pptx, csv, txt).',
     'pairs_well_with': ['site:'],
     'example': 'filetype:pdf annual report',
     'gotcha': 'filetype: matches the file extension on the URL, not the Content-Type header.'},
    {'op': 'OR',        'name': 'Logical OR',
     'desc': 'Match results containing either term. Must be uppercase to be parsed as a boolean.',
     'pairs_well_with': ['site:', 'intitle:'],
     'example': 'Python OR JavaScript tutorial',
     'gotcha': 'Lowercase "or" is treated as the English word, not the operator.'},
    {'op': '-',         'name': 'Exclude',
     'desc': 'Drop pages that contain the term following the minus sign.',
     'pairs_well_with': ['site:'],
     'example': 'jaguar -car',
     'gotcha': 'A space before the minus disables the operator: "jaguar - car" is treated as three tokens.'},
    {'op': '"…"',       'name': 'Exact phrase',
     'desc': 'Match the enclosed words in order, verbatim, no stemming.',
     'pairs_well_with': ['intitle:', 'site:'],
     'example': '"to be or not to be"',
     'gotcha': 'Closing the quote is required; an unmatched quote silently drops the operator.'},
    {'op': '*',         'name': 'Wildcard',
     'desc': 'Within an exact phrase, match any single word at the asterisk position.',
     'pairs_well_with': ['"…"'],
     'example': '"the * theory of relativity"',
     'gotcha': 'Wildcard only applies inside an exact-phrase quote; bare * is ignored.'},
    {'op': 'before:',   'name': 'Before date',
     'desc': 'Only return pages published before the given YYYY-MM-DD date.',
     'pairs_well_with': ['site:'],
     'example': 'recession before:2020-01-01',
     'gotcha': 'Publication date is inferred — many static pages have no date and are dropped.'},
    {'op': 'after:',    'name': 'After date',
     'desc': 'Only return pages published on or after the given YYYY-MM-DD date.',
     'pairs_well_with': ['site:'],
     'example': 'AI breakthroughs after:2024-01-01',
     'gotcha': 'Use ISO dates only; locale-specific formats are not parsed.'},
    {'op': 'related:',  'name': 'Similar pages',
     'desc': 'Pages topically related to the supplied URL.',
     'pairs_well_with': [],
     'example': 'related:nytimes.com',
     'gotcha': 'The URL must include a scheme or be a bare host; paths beyond / are ignored.'},
    {'op': 'cache:',    'name': 'Cached copy',
     'desc': 'Show the cached snapshot of the page closest to your query.',
     'pairs_well_with': [],
     'example': 'cache:wikipedia.org/wiki/Sun',
     'gotcha': 'In the mirror, cached snapshots resolve through /external-view.'},
    {'op': 'AROUND(N)', 'name': 'Proximity',
     'desc': 'Two terms must appear within N words of each other.',
     'pairs_well_with': ['intitle:'],
     'example': 'Tesla AROUND(3) Musk',
     'gotcha': 'N must be parenthesised; AROUND 3 (without parens) is parsed as plain text.'},
    {'op': 'define:',   'name': 'Definition',
     'desc': 'Return the dictionary definition of a single word.',
     'pairs_well_with': [],
     'example': 'define:serendipity',
     'gotcha': 'Multi-word operands are silently truncated to the first token.'},
]


@app.route('/help/syntax-glossary')
@app.route('/help/operators')
def r8_syntax_glossary():
    """Contextual help glossary — one card per operator with description,
    pair-with hints, example, and a common gotcha. Linked from
    /search/syntax."""
    return render_template('r8_syntax_glossary.html', glossary=_R8_SYNTAX_GLOSSARY)


# Pinned palette items — keys for Cmd+K. Deterministic across rebuilds.
_R8_PALETTE_ITEMS = [
    ('All',       'Jump to /search (default vertical)',         '/search?q='),
    ('Images',    'Image search vertical',                      '/search?q=&tbm=images'),
    ('Videos',    'Video search vertical',                      '/search?q=&tbm=videos'),
    ('News',      'News search vertical',                       '/search?q=&tbm=news'),
    ('Maps',      'Maps vertical',                              '/search?q=&tbm=maps'),
    ('Shopping',  'Shopping vertical',                          '/search?q=&tbm=shopping'),
    ('Books',     'Books vertical',                             '/search?q=&tbm=books'),
    ('Finance',   'Finance vertical',                           '/search?q=&tbm=finance'),
    ('Scholar',   'Google Scholar',                             '/scholar'),
    ('Trending',  'Trending searches',                          '/trending'),
    ('Doodles',   'Doodle archive',                             '/doodles'),
    ('History',   'My search history',                          '/history'),
    ('Bookmarks', 'My saved results',                           '/bookmarks'),
    ('Collections', 'My result collections',                    '/collections'),
    ('Alerts',    'My alerts',                                  '/alerts'),
    ('Settings',  'Search preferences',                         '/settings'),
    ('Locales',   'Switch locale (hl / gl)',                    '/locales'),
    ('Syntax',    'Advanced search syntax',                     '/search/syntax'),
    ('Glossary',  'Per-operator glossary (contextual help)',    '/help/syntax-glossary'),
    ('Accessibility', 'Keyboard shortcuts + WCAG',              '/accessibility'),
    ('Performance',   'SERP-render performance dashboard',      '/performance'),
    ('Takeout',   'Export search history',                      '/takeout'),
    ('Healthz',   'Liveness probe (JSON)',                      '/healthz'),
    ('Uptime',    'Build identity (JSON)',                      '/api/uptime'),
    ('Events',    'Mirror event log (JSON)',                    '/api/events'),
    ('GraphQL',   'Mirror GraphQL endpoint',                    '/api/v3/graphql'),
    ('CSE Builder', 'Custom search engine builder',             '/developer/custom-search-engine-builder'),
    ('Webhook',   'SERP change alert webhook',                  '/webhook/serp-change-alert'),
]


@app.route('/command-palette')
@app.route('/palette')
def r8_command_palette():
    """Command palette — Cmd+K shortcut target. Static list of jump
    destinations with a filter input. Deterministic across resets."""
    q = (request.args.get('q') or '').strip().lower()
    items = _R8_PALETTE_ITEMS
    if q:
        items = [it for it in items if q in it[0].lower() or q in it[1].lower()]
    return render_template('r8_command_palette.html',
                           items=items, q=request.args.get('q') or '')


@app.route('/api/palette')
def r8_api_palette():
    """JSON form of the command palette so an agent can introspect the
    catalog without parsing HTML."""
    return jsonify({
        'service': 'google-search-mirror',
        'items': [{'label': l, 'description': d, 'href': h}
                  for l, d, h in _R8_PALETTE_ITEMS],
        'count': len(_R8_PALETTE_ITEMS),
    })


# ---------- R9: AI-Overview / generative SERP / Lens-photo / NotebookLM /
#               AR / conversational search ------------------------------------
#
# Seven new surfaces that mirror the "AI-overview-era" Google features the
# real google.com is rolling out. Every endpoint is deterministic and
# wall-clock-free so byte-id reset stays intact.

# Pinned AI Overview cards. Each card is a 4-tuple:
#   (slug, query_text, summary, [citation dicts])
# Citations dicts: {label, title, url, snippet, source}
_R9_AI_OVERVIEW_CARDS = [
    {
        'slug': 'photosynthesis',
        'query': 'how does photosynthesis work',
        'summary': (
            'Photosynthesis converts light energy, water, and carbon dioxide '
            'into glucose and oxygen. It happens in two coupled stages: the '
            'light-dependent reactions in the thylakoid membranes capture '
            'photon energy into ATP and NADPH, and the Calvin cycle in the '
            'stroma uses that energy to fix CO2 into sugars.'),
        'citations': [
            {'label': '[1]', 'title': 'Photosynthesis - Wikipedia',
             'url': 'https://en.wikipedia.org/wiki/Photosynthesis',
             'snippet': 'Photosynthesis is a biological process used by plants and other organisms to convert light into chemical energy.',
             'source': 'en.wikipedia.org'},
            {'label': '[2]', 'title': 'Khan Academy: Light reactions',
             'url': 'https://www.khanacademy.org/science/biology/photosynthesis-in-plants',
             'snippet': 'Free video and reading on the light-dependent reactions and the Calvin cycle.',
             'source': 'www.khanacademy.org'},
            {'label': '[3]', 'title': 'Britannica - Photosynthesis',
             'url': 'https://www.britannica.com/science/photosynthesis',
             'snippet': 'Process by which green plants and certain other organisms transform light energy into chemical energy.',
             'source': 'www.britannica.com'},
            {'label': '[4]', 'title': 'Nature - photosynthesis',
             'url': 'https://www.nature.com/subjects/photosynthesis',
             'snippet': 'Latest research articles on photosynthesis from Nature journals.',
             'source': 'www.nature.com'},
            {'label': '[5]', 'title': 'NASA - The Carbon Cycle',
             'url': 'https://earthobservatory.nasa.gov/features/CarbonCycle',
             'snippet': 'NASA Earth Observatory feature on the global carbon cycle and the role of photosynthesis.',
             'source': 'earthobservatory.nasa.gov'},
            {'label': '[6]', 'title': 'Quanta - The chloroplast',
             'url': 'https://www.quantamagazine.org/tag/photosynthesis/',
             'snippet': 'Quanta Magazine reporting on photosynthesis research and the structure of the chloroplast.',
             'source': 'www.quantamagazine.org'},
            {'label': '[7]', 'title': 'NIH PubMed - photosynthesis review',
             'url': 'https://pubmed.ncbi.nlm.nih.gov/?term=photosynthesis+review',
             'snippet': 'Open-access peer-reviewed review articles on photosynthesis indexed by PubMed.',
             'source': 'pubmed.ncbi.nlm.nih.gov'},
        ],
    },
    {
        'slug': 'large_language_model',
        'query': 'what is a large language model',
        'summary': (
            'A large language model (LLM) is a neural network trained on '
            'large text corpora to predict next tokens. Modern LLMs use the '
            'Transformer architecture (self-attention) and scale to billions '
            'of parameters; they are typically pre-trained on a generic '
            'corpus then fine-tuned for instruction-following with human '
            'feedback (RLHF or DPO).'),
        'citations': [
            {'label': '[1]', 'title': 'Large language model - Wikipedia',
             'url': 'https://en.wikipedia.org/wiki/Large_language_model',
             'snippet': 'A large language model is a type of foundation model trained on vast amounts of text.',
             'source': 'en.wikipedia.org'},
            {'label': '[2]', 'title': 'Attention Is All You Need - arXiv',
             'url': 'https://arxiv.org/abs/1706.03762',
             'snippet': 'Vaswani et al. 2017 - the Transformer paper introducing self-attention.',
             'source': 'arxiv.org'},
            {'label': '[3]', 'title': 'OpenAI: GPT-4 Technical Report',
             'url': 'https://openai.com/research/gpt-4',
             'snippet': 'Technical report on GPT-4 - capabilities, evaluations, and safety.',
             'source': 'openai.com'},
            {'label': '[4]', 'title': 'Anthropic: Claude family models',
             'url': 'https://www.anthropic.com/news/claude-3-family',
             'snippet': 'Anthropic announcement on the Claude 3 family of large language models.',
             'source': 'www.anthropic.com'},
            {'label': '[5]', 'title': 'Stanford CRFM - Foundation models',
             'url': 'https://crfm.stanford.edu/',
             'snippet': 'Stanford Center for Research on Foundation Models (CRFM) - report and research.',
             'source': 'crfm.stanford.edu'},
            {'label': '[6]', 'title': 'DeepMind - Chinchilla scaling laws',
             'url': 'https://www.deepmind.com/publications/an-empirical-analysis-of-compute-optimal-large-language-model-training',
             'snippet': 'Hoffmann et al. 2022 - the Chinchilla compute-optimal scaling law.',
             'source': 'www.deepmind.com'},
            {'label': '[7]', 'title': 'Hugging Face - open LLM leaderboard',
             'url': 'https://huggingface.co/spaces/HuggingFaceH4/open_llm_leaderboard',
             'snippet': 'Community leaderboard ranking open-source large language models.',
             'source': 'huggingface.co'},
        ],
    },
    {
        'slug': 'black_hole',
        'query': 'what is a black hole',
        'summary': (
            'A black hole is a region of spacetime where gravity is so '
            'strong that nothing - not even light - can escape. The '
            'boundary is called the event horizon. Stellar-mass black holes '
            'form from the gravitational collapse of massive stars; '
            'supermassive black holes sit at galactic centers.'),
        'citations': [
            {'label': '[1]', 'title': 'Black hole - Wikipedia',
             'url': 'https://en.wikipedia.org/wiki/Black_hole',
             'snippet': 'A black hole is a region of spacetime where gravity is so strong nothing can escape.',
             'source': 'en.wikipedia.org'},
            {'label': '[2]', 'title': 'NASA Black holes',
             'url': 'https://science.nasa.gov/universe/black-holes/',
             'snippet': 'NASA overview of black holes - types, formation, and observations.',
             'source': 'science.nasa.gov'},
            {'label': '[3]', 'title': 'Event Horizon Telescope',
             'url': 'https://eventhorizontelescope.org/',
             'snippet': 'The Event Horizon Telescope collaboration - first images of black holes M87* and Sgr A*.',
             'source': 'eventhorizontelescope.org'},
            {'label': '[4]', 'title': 'Stephen Hawking - black hole radiation',
             'url': 'https://en.wikipedia.org/wiki/Hawking_radiation',
             'snippet': 'Hawking radiation - theoretical black-body emission predicted by Stephen Hawking in 1974.',
             'source': 'en.wikipedia.org'},
            {'label': '[5]', 'title': 'ESO press release - Sgr A*',
             'url': 'https://www.eso.org/public/news/eso2208-eht-mw/',
             'snippet': 'ESO press release on the first image of the supermassive black hole at the centre of our Milky Way galaxy.',
             'source': 'www.eso.org'},
            {'label': '[6]', 'title': 'Britannica - Black hole',
             'url': 'https://www.britannica.com/science/black-hole',
             'snippet': 'Encyclopedia Britannica entry covering theory, observation, and history of black holes.',
             'source': 'www.britannica.com'},
            {'label': '[7]', 'title': 'Quanta Magazine - black holes',
             'url': 'https://www.quantamagazine.org/tag/black-holes/',
             'snippet': 'Long-form science journalism on black hole research from Quanta Magazine.',
             'source': 'www.quantamagazine.org'},
        ],
    },
    {
        'slug': 'mediterranean_diet',
        'query': 'is the mediterranean diet healthy',
        'summary': (
            'The Mediterranean diet emphasizes vegetables, legumes, whole '
            'grains, olive oil, nuts, fish, and moderate wine. Multiple '
            'randomized trials and meta-analyses (PREDIMED, Lyon Diet Heart '
            'Study) link it to lower cardiovascular events and reduced '
            'all-cause mortality. The US News Best Diets panel has ranked '
            'it #1 overall for multiple consecutive years.'),
        'citations': [
            {'label': '[1]', 'title': 'Mediterranean diet - Wikipedia',
             'url': 'https://en.wikipedia.org/wiki/Mediterranean_diet',
             'snippet': 'A diet inspired by the eating habits of Greece, Spain, Italy and southern France.',
             'source': 'en.wikipedia.org'},
            {'label': '[2]', 'title': 'PREDIMED trial - NEJM',
             'url': 'https://www.nejm.org/doi/full/10.1056/NEJMoa1800389',
             'snippet': 'Primary prevention of cardiovascular disease with a Mediterranean diet supplemented with extra-virgin olive oil or nuts.',
             'source': 'www.nejm.org'},
            {'label': '[3]', 'title': 'US News Best Diets ranking',
             'url': 'https://health.usnews.com/best-diet/best-diets-overall',
             'snippet': 'US News & World Report annual Best Diets ranking - Mediterranean diet repeatedly #1 overall.',
             'source': 'health.usnews.com'},
            {'label': '[4]', 'title': 'Harvard School of Public Health',
             'url': 'https://www.hsph.harvard.edu/nutritionsource/healthy-weight/diet-reviews/mediterranean-diet/',
             'snippet': 'Harvard T.H. Chan School of Public Health Nutrition Source review of the Mediterranean diet.',
             'source': 'www.hsph.harvard.edu'},
            {'label': '[5]', 'title': 'Mayo Clinic - Mediterranean diet',
             'url': 'https://www.mayoclinic.org/healthy-lifestyle/nutrition-and-healthy-eating/in-depth/mediterranean-diet/art-20047801',
             'snippet': 'Mayo Clinic expert overview of how to follow a Mediterranean-style eating pattern.',
             'source': 'www.mayoclinic.org'},
            {'label': '[6]', 'title': 'Cochrane - Mediterranean diet review',
             'url': 'https://www.cochranelibrary.com/cdsr/doi/10.1002/14651858.CD009825.pub3/full',
             'snippet': 'Cochrane systematic review of Mediterranean-style diet for the primary and secondary prevention of cardiovascular disease.',
             'source': 'www.cochranelibrary.com'},
            {'label': '[7]', 'title': 'Lyon Diet Heart Study',
             'url': 'https://www.ahajournals.org/doi/10.1161/01.CIR.99.6.779',
             'snippet': 'Lyon Diet Heart Study - cardioprotective effect of Mediterranean diet on coronary heart disease.',
             'source': 'www.ahajournals.org'},
        ],
    },
    {
        'slug': 'quantum_entanglement',
        'query': 'what is quantum entanglement',
        'summary': (
            'Quantum entanglement is a correlation between two or more '
            'particles such that the quantum state of each cannot be '
            'described independently of the others, even when separated by '
            'arbitrary distance. Measurements of one particle instantly '
            'project the state of the other - within the bounds of the '
            'no-communication theorem. The 2022 Nobel Prize in Physics was '
            'awarded for experimental tests of Bell inequalities.'),
        'citations': [
            {'label': '[1]', 'title': 'Quantum entanglement - Wikipedia',
             'url': 'https://en.wikipedia.org/wiki/Quantum_entanglement',
             'snippet': 'Quantum entanglement is the phenomenon where a group of particles share a single quantum state.',
             'source': 'en.wikipedia.org'},
            {'label': '[2]', 'title': '2022 Nobel Prize in Physics',
             'url': 'https://www.nobelprize.org/prizes/physics/2022/summary/',
             'snippet': 'Awarded to Aspect, Clauser, and Zeilinger for experiments with entangled photons.',
             'source': 'www.nobelprize.org'},
            {'label': '[3]', 'title': 'Stanford Encyclopedia of Philosophy',
             'url': 'https://plato.stanford.edu/entries/qt-entangle/',
             'snippet': 'Philosophical and historical overview of quantum entanglement.',
             'source': 'plato.stanford.edu'},
            {'label': '[4]', 'title': 'CERN - quantum entanglement experiments',
             'url': 'https://home.cern/science/physics/quantum-physics',
             'snippet': 'CERN explainer on quantum physics and entanglement experiments.',
             'source': 'home.cern'},
            {'label': '[5]', 'title': 'Nature - entanglement research',
             'url': 'https://www.nature.com/subjects/quantum-entanglement',
             'snippet': 'Nature subject page indexing recent research on quantum entanglement.',
             'source': 'www.nature.com'},
            {'label': '[6]', 'title': 'IBM Quantum - entanglement primer',
             'url': 'https://learning.quantum.ibm.com/course/basics-of-quantum-information/entanglement',
             'snippet': 'IBM Quantum interactive course on the basics of quantum information including entanglement.',
             'source': 'learning.quantum.ibm.com'},
            {'label': '[7]', 'title': 'arXiv - Bell experiments review',
             'url': 'https://arxiv.org/abs/1707.04591',
             'snippet': 'Loophole-free Bell-inequality experiments - review and recent results on arXiv.',
             'source': 'arxiv.org'},
        ],
    },
    {
        'slug': 'climate_change_causes',
        'query': 'what causes climate change',
        'summary': (
            'The dominant driver of present-day climate change is the '
            'increase in atmospheric concentrations of greenhouse gases - '
            'principally CO2, methane, and nitrous oxide - from human '
            'activities. Burning fossil fuels for electricity, heat, and '
            'transport is the single largest source; land-use change and '
            'agriculture also contribute. The IPCC AR6 attributes the '
            'observed warming since 1850 unequivocally to human influence.'),
        'citations': [
            {'label': '[1]', 'title': 'IPCC Sixth Assessment Report',
             'url': 'https://www.ipcc.ch/report/ar6/wg1/',
             'snippet': 'IPCC AR6 Working Group I report - the physical science basis of climate change.',
             'source': 'www.ipcc.ch'},
            {'label': '[2]', 'title': 'NASA Climate Change - causes',
             'url': 'https://climate.nasa.gov/causes/',
             'snippet': 'NASA overview of the scientific consensus on the causes of climate change.',
             'source': 'climate.nasa.gov'},
            {'label': '[3]', 'title': 'NOAA - Climate.gov',
             'url': 'https://www.climate.gov/',
             'snippet': 'NOAA Climate.gov - science and services portal for climate change.',
             'source': 'www.climate.gov'},
            {'label': '[4]', 'title': 'UN: causes of climate change',
             'url': 'https://www.un.org/en/climatechange/science/causes-effects-climate-change',
             'snippet': 'United Nations explainer on the causes and effects of climate change.',
             'source': 'www.un.org'},
            {'label': '[5]', 'title': 'Our World in Data: CO2 emissions',
             'url': 'https://ourworldindata.org/co2-and-greenhouse-gas-emissions',
             'snippet': 'Long-run dataset on global CO2 and greenhouse gas emissions by source.',
             'source': 'ourworldindata.org'},
            {'label': '[6]', 'title': 'EPA - Causes of climate change',
             'url': 'https://www.epa.gov/climatechange-science/causes-climate-change',
             'snippet': 'US EPA primer on natural and human causes of climate change.',
             'source': 'www.epa.gov'},
            {'label': '[7]', 'title': 'Carbon Brief - explainers',
             'url': 'https://www.carbonbrief.org/category/explainers/',
             'snippet': 'Carbon Brief technical explainers on the climate-change evidence base.',
             'source': 'www.carbonbrief.org'},
        ],
    },
]


_R9_AI_OVERVIEW_INDEX = {c['slug']: c for c in _R9_AI_OVERVIEW_CARDS}


@app.route('/search/ai-overview')
def r9_ai_overview():
    """AI Overview landing - lists every prepared overview card with its
    one-paragraph summary. Filterable by ?q=, and indexed by ?slug= to
    open a specific card.

    Wall-clock-free, deterministic across resets.
    """
    q = (request.args.get('q') or '').strip().lower()
    slug = (request.args.get('slug') or '').strip().lower()
    one = _R9_AI_OVERVIEW_INDEX.get(slug)
    items = _R9_AI_OVERVIEW_CARDS
    if q:
        items = [c for c in items
                 if q in c['slug'].lower()
                 or q in c['query'].lower()
                 or q in c['summary'].lower()]
    return render_template(
        'r9_ai_overview.html',
        items=items, one=one, q=request.args.get('q') or '',
    )


@app.route('/search/ai-overview/citations')
@app.route('/search/ai-overview/citations/<slug>')
def r9_ai_overview_citations(slug=None):
    """Per-card citation list. ?slug= or path-segment routing. If no slug,
    return an index page with citation counts. If POST-style ?format=json,
    return JSON for programmatic consumers."""
    slug_q = (slug or request.args.get('slug') or '').strip().lower()
    fmt = (request.args.get('format') or '').strip().lower()
    one = _R9_AI_OVERVIEW_INDEX.get(slug_q)
    if fmt == 'json':
        if one is None:
            return jsonify({
                'cards': [{'slug': c['slug'], 'query': c['query'],
                           'citation_count': len(c['citations'])}
                          for c in _R9_AI_OVERVIEW_CARDS],
                'count': len(_R9_AI_OVERVIEW_CARDS),
            })
        return jsonify({
            'slug': one['slug'], 'query': one['query'],
            'summary': one['summary'],
            'citations': one['citations'],
            'citation_count': len(one['citations']),
        })
    return render_template(
        'r9_ai_overview_citations.html',
        one=one, cards=_R9_AI_OVERVIEW_CARDS, slug=slug_q,
    )


_R9_GENERATIVE_MODES = [
    ('off',     'Off',     'Classic 10 blue links only. No AI summary above results.'),
    ('compact', 'Compact', 'A 2-line generative gist above the SERP with collapsed citations.'),
    ('full',    'Full',    'A full AI overview with inline citations and follow-up question chips.'),
    ('chat',    'Chat',    'Conversational mode - the SERP becomes a chat with retained context across messages.'),
]


@app.route('/search/generative-toggle', methods=['GET', 'POST'])
def r9_generative_toggle():
    """Generative search toggle. Persists the selected mode in the Flask
    session so subsequent /search calls *could* opt in (no actual SERP
    behavior change - keeps byte-id reset intact)."""
    current = session.get('generative_mode', 'compact')
    saved = None
    if request.method == 'POST':
        choice = (request.form.get('mode') or '').strip().lower()
        if choice in {m[0] for m in _R9_GENERATIVE_MODES}:
            session['generative_mode'] = choice
            current = choice
            saved = choice
    return render_template(
        'r9_generative_toggle.html',
        modes=_R9_GENERATIVE_MODES, current=current, saved=saved,
    )


_R9_LENS_EXPLANATIONS = [
    {'tag': 'flower', 'label': 'Identify a flower',
     'how': 'Open Lens, tap "Search what you see", center the flower in the viewfinder. Lens crops the bloom, runs it through the visual-similarity index, and offers a likely species plus visually-similar matches.',
     'confidence_hint': 'Confidence is high when the bloom is sharp and well-lit and the leaves are visible.'},
    {'tag': 'clothing', 'label': 'Find a clothing item',
     'how': 'Take a photo of the garment, tap the shopping chip. Lens segments the item, matches it against the product index, and returns shoppable links with prices and reviews.',
     'confidence_hint': 'Confidence is high when the garment is shot against a clean background with the pattern visible.'},
    {'tag': 'landmark', 'label': 'Identify a landmark',
     'how': 'Photograph the landmark from a typical postcard angle. Lens consults the Maps photo corpus + GPS hint to surface the canonical name, Wikipedia card, opening hours, and reviews.',
     'confidence_hint': 'Confidence is high when the GPS location matches a well-photographed landmark.'},
    {'tag': 'plant', 'label': 'Diagnose a plant problem',
     'how': 'Capture the leaf with the affected area centered. Lens cross-references the visual-similarity index plus PlantNet contributions to suggest a likely disease or pest.',
     'confidence_hint': 'Confidence is high when the photo is in focus and shows both healthy and affected tissue for contrast.'},
    {'tag': 'math', 'label': 'Solve a math problem',
     'how': 'Snap the worksheet or screen. Lens OCRs the equation, hands it to a step-by-step solver, and renders the worked solution with intermediate steps and a definition card.',
     'confidence_hint': 'Confidence is high when the handwriting/print is legible and the problem is a standard form.'},
    {'tag': 'recipe', 'label': 'Look up a recipe from a dish photo',
     'how': 'Photograph the plated dish. Lens classifies the dish, surfaces a likely name, and offers ranked recipe links with cooking-time, calorie, and review-score chips.',
     'confidence_hint': 'Confidence is high when the dish is photographed in good lighting and is a common cuisine.'},
]


@app.route('/lens/find-photo-ai')
@app.route('/lens/find-photo-ai/<tag>')
def r9_lens_find_photo_ai(tag=None):
    """Lens 'find by photo' AI explanation page. Lists each supported
    photo-recognition task with the step-by-step Lens behavior."""
    tag_q = (tag or request.args.get('tag') or '').strip().lower()
    one = next((e for e in _R9_LENS_EXPLANATIONS if e['tag'] == tag_q), None)
    return render_template(
        'r9_lens_find_photo_ai.html',
        items=_R9_LENS_EXPLANATIONS, one=one, tag=tag_q,
    )


# NotebookLM-style sources + suggested follow-ups
_R9_NOTEBOOKLM_NOTEBOOKS = [
    {
        'slug': 'photosynthesis_study',
        'title': 'Photosynthesis - study pack',
        'description': 'A NotebookLM-style notebook grounded on Wikipedia + Khan Academy + a Nature review.',
        'sources': [
            'Wikipedia - Photosynthesis',
            'Khan Academy - Light reactions',
            'Nature Reviews - Photosynthesis 2024',
            'Britannica - Photosynthesis',
            'NASA - The Carbon Cycle',
        ],
        'follow_ups': [
            'Compare the light-dependent vs Calvin-cycle reactions.',
            'Why does C4 photosynthesis evolve in hot/dry climates?',
            'What is photorespiration and why does it matter?',
            'Summarize the Z-scheme of electron transport.',
        ],
    },
    {
        'slug': 'llm_evaluation',
        'title': 'LLM evaluation - lit review notebook',
        'description': 'A NotebookLM-style notebook grounded on a curated set of LLM-evaluation papers and blog posts.',
        'sources': [
            'HELM - Holistic Evaluation of Language Models (Stanford)',
            'BIG-bench - Beyond the Imitation Game',
            'MMLU - Massive Multitask Language Understanding',
            'OpenAI evals',
            'Anthropic - measuring model deception',
        ],
        'follow_ups': [
            'What are the limitations of MMLU as a knowledge benchmark?',
            'How does HELM handle calibration and robustness?',
            'Summarize the contamination concerns with public benchmarks.',
            'What is the Chatbot Arena Elo system?',
        ],
    },
    {
        'slug': 'climate_overview',
        'title': 'Climate change - executive summary',
        'description': 'A NotebookLM-style notebook grounded on IPCC + NASA + Our World in Data.',
        'sources': [
            'IPCC AR6 WG1 Summary for Policymakers',
            'NASA - Climate change causes',
            'Our World in Data - Greenhouse gas emissions',
            'NOAA Climate.gov - State of the climate',
            'Carbon Brief - explainers',
        ],
        'follow_ups': [
            'What is the difference between RCP and SSP scenarios?',
            'How are climate models validated against the historical record?',
            'Summarize methane vs CO2 radiative forcing.',
            'Compare net-zero pledges by major economies.',
        ],
    },
    {
        'slug': 'mediterranean_diet_brief',
        'title': 'Mediterranean diet - clinical brief',
        'description': 'A NotebookLM-style notebook grounded on PREDIMED + Cochrane + Harvard nutrition.',
        'sources': [
            'PREDIMED - NEJM 2018',
            'Cochrane systematic review',
            'Harvard School of Public Health - Nutrition Source',
            'Mayo Clinic - patient guide',
            'Lyon Diet Heart Study',
        ],
        'follow_ups': [
            'What is the effect size for cardiovascular outcomes in PREDIMED?',
            'How does PREDIMED-Plus differ from the original PREDIMED?',
            'Compare with DASH and MIND diets.',
            'Summarize adherence-score instruments used in trials.',
        ],
    },
]


_R9_NOTEBOOKLM_INDEX = {n['slug']: n for n in _R9_NOTEBOOKLM_NOTEBOOKS}


@app.route('/notebooklm')
@app.route('/notebooklm/<slug>')
def r9_notebooklm(slug=None):
    """NotebookLM-style grounded research notebook listing. Read-only -
    no state writes so byte-id reset stays intact."""
    slug_q = (slug or request.args.get('slug') or '').strip().lower()
    one = _R9_NOTEBOOKLM_INDEX.get(slug_q)
    fmt = (request.args.get('format') or '').strip().lower()
    if fmt == 'json':
        if one is None:
            return jsonify({
                'notebooks': [{'slug': n['slug'], 'title': n['title'],
                               'source_count': len(n['sources']),
                               'follow_up_count': len(n['follow_ups'])}
                              for n in _R9_NOTEBOOKLM_NOTEBOOKS],
                'count': len(_R9_NOTEBOOKLM_NOTEBOOKS),
            })
        return jsonify(one)
    return render_template(
        'r9_notebooklm.html',
        items=_R9_NOTEBOOKLM_NOTEBOOKS, one=one, slug=slug_q,
    )


_R9_AR_SCENES = [
    {'slug': 'tiger',   'label': 'Tiger',
     'caption': 'Project a life-size tiger onto your floor with AR. Walk around it for a sense of scale.'},
    {'slug': 'shark',   'label': 'Great White Shark',
     'caption': 'Drop a 4.5 m great white shark into the room. Tap to hear a roar.'},
    {'slug': 'tyrannosaurus', 'label': 'Tyrannosaurus rex',
     'caption': 'Place a 12 m T. rex in the garden. Lens annotates the skeleton.'},
    {'slug': 'octopus', 'label': 'Giant Pacific Octopus',
     'caption': 'See a 5 m octopus crawl across the floor in AR. Tap to label each arm.'},
    {'slug': 'wolf',    'label': 'Gray Wolf',
     'caption': 'Bring a gray wolf into your living room. Lens narrates its hunting behavior.'},
    {'slug': 'panda',   'label': 'Giant Panda',
     'caption': 'Drop a giant panda eating bamboo into the AR scene. Lens captions the diet.'},
    {'slug': 'planet_saturn', 'label': 'Saturn',
     'caption': 'Project Saturn with its ring system at 1:1 billion scale. Lens annotates each moon.'},
    {'slug': 'apollo_lander', 'label': 'Apollo Lunar Module',
     'caption': 'Place the Apollo 11 lunar module on your table. Tap to hear the landing audio.'},
]


_R9_AR_SCENES_INDEX = {s['slug']: s for s in _R9_AR_SCENES}


@app.route('/ar-search')
@app.route('/ar-search/<slug>')
def r9_ar_search(slug=None):
    """AR-on-camera search stub. Read-only AR-scene picker that explains
    the camera-AR feature without launching any actual AR runtime."""
    slug_q = (slug or request.args.get('slug') or '').strip().lower()
    one = _R9_AR_SCENES_INDEX.get(slug_q)
    return render_template('r9_ar_search.html',
                           items=_R9_AR_SCENES, one=one, slug=slug_q)


_R9_CONVERSATION_TRANSCRIPTS = [
    {
        'slug': 'plan_paris_trip',
        'title': 'Plan a 5-day Paris trip',
        'turns': [
            ('user', 'plan a 5-day paris trip for two adults in spring'),
            ('assistant',
             'Day 1: Louvre + Tuileries + Seine sunset cruise. Day 2: Versailles. '
             'Day 3: Montmartre + Sacre-Coeur + Musee d Orsay. Day 4: Eiffel Tower + Trocadero + Champ de Mars picnic. '
             'Day 5: Marais walk + Notre-Dame exterior + Pere Lachaise.'),
            ('user', 'add a day trip to Reims for champagne'),
            ('assistant',
             'Reims is 45 minutes by TGV from Gare de l Est. Swap Day 5 for: Reims TGV (8:30), '
             'Veuve Clicquot cellar tour (10:30), Reims Cathedral and lunch (12:30), '
             'Taittinger cellar tour (15:00), TGV back to Paris (18:00).'),
            ('user', 'what budget should we plan for the food?'),
            ('assistant',
             'For two adults: cafe breakfast ~EUR 18, casual lunch ~EUR 50, mid-range dinner ~EUR 120. '
             'Total food ~EUR 188 per day. Add ~EUR 80 for the Reims tastings.'),
        ],
    },
    {
        'slug': 'learn_python_path',
        'title': 'Build a Python learning path',
        'turns': [
            ('user', 'i know basic javascript, build me a 6-week python path'),
            ('assistant',
             'Week 1: syntax, types, control flow (vs JS). Week 2: functions, list/dict/set, comprehensions. '
             'Week 3: classes + dunder methods. Week 4: stdlib (itertools, collections, pathlib). '
             'Week 5: testing (pytest) + packaging. Week 6: build a CLI with click and publish to PyPI.'),
            ('user', 'add a project for each week'),
            ('assistant',
             'W1: implement FizzBuzz + a calculator. W2: a Markdown -> HTML converter. '
             'W3: a tiny task tracker with subclasses. W4: a static-site generator. '
             'W5: 80% test coverage on the static-site generator. W6: publish todocli to PyPI.'),
            ('user', 'what resources should i use?'),
            ('assistant',
             'Free: Python docs tutorial, Real Python free tier, Automate the Boring Stuff. '
             'Paid: Fluent Python by Luciano Ramalho (intermediate-to-advanced). '
             'Video: Corey Schafer YouTube playlist for stdlib deep-dives.'),
        ],
    },
    {
        'slug': 'compare_air_purifiers',
        'title': 'Compare 3 air purifiers',
        'turns': [
            ('user', 'compare blueair 211+ vs coway airmega 200m vs winix 5500-2'),
            ('assistant',
             'Coverage: Blueair 211+ 540 sq ft, Coway 200m 361 sq ft, Winix 5500-2 360 sq ft. '
             'CADR (smoke): 350, 240, 232. Filter cost/yr: ~USD 80, ~USD 50, ~USD 50. '
             'Noise at max: 56, 53, 55 dB. All three carry True HEPA + activated carbon.'),
            ('user', 'which is best for a 350 sq ft bedroom?'),
            ('assistant',
             'For 350 sq ft, all three are adequate. The Winix 5500-2 is the most affordable, has Sleep mode, '
             'and a PlasmaWave option you can disable. The Coway 200m is the quietest at lowest setting (24 dB).'),
            ('user', 'and for allergies?'),
            ('assistant',
             'For allergies, prioritize True HEPA + 4-5x ACH (air changes per hour) for the room. '
             'In a 350 sq ft bedroom, Blueair 211+ achieves 5 ACH on medium and is the strongest performer. '
             'The Coway 200m is a good budget alternative with 4.8 ACH on high.'),
        ],
    },
]


_R9_CONVERSATION_INDEX = {c['slug']: c for c in _R9_CONVERSATION_TRANSCRIPTS}


@app.route('/search/conversation')
@app.route('/search/conversation/<slug>')
def r9_search_conversation(slug=None):
    """Search-as-conversation (multi-step) transcript browser. Read-only -
    enumerates curated multi-turn agent traces tied to common SERP topics."""
    slug_q = (slug or request.args.get('slug') or '').strip().lower()
    one = _R9_CONVERSATION_INDEX.get(slug_q)
    fmt = (request.args.get('format') or '').strip().lower()
    if fmt == 'json':
        if one is None:
            return jsonify({
                'transcripts': [{'slug': c['slug'], 'title': c['title'],
                                 'turn_count': len(c['turns'])}
                                for c in _R9_CONVERSATION_TRANSCRIPTS],
                'count': len(_R9_CONVERSATION_TRANSCRIPTS),
            })
        return jsonify({
            'slug': one['slug'], 'title': one['title'],
            'turns': [{'role': r, 'text': t} for r, t in one['turns']],
            'turn_count': len(one['turns']),
        })
    return render_template(
        'r9_search_conversation.html',
        items=_R9_CONVERSATION_TRANSCRIPTS, one=one, slug=slug_q,
    )


# Extend the command palette with R9 jump-targets.
_R8_PALETTE_ITEMS = _R8_PALETTE_ITEMS + [
    ('AI Overview',       'Generative AI overview cards',                   '/search/ai-overview'),
    ('AI Overview citations', 'Per-card citation list',                     '/search/ai-overview/citations'),
    ('Generative toggle', 'Switch generative-mode (off/compact/full/chat)', '/search/generative-toggle'),
    ('Lens find by photo','Lens AI explanation for photo recognition',      '/lens/find-photo-ai'),
    ('NotebookLM',        'Grounded research notebooks',                    '/notebooklm'),
    ('AR Search',         'AR-on-camera scenes (stub)',                     '/ar-search'),
    ('Conversation',      'Search-as-conversation (multi-step) traces',     '/search/conversation'),
]


# ---------- error handlers --------------------------------------------------

@app.errorhandler(404)
def not_found(e):
    return render_template('404.html'), 404


@app.errorhandler(500)
def server_error(e):
    return render_template('500.html'), 500


# ---------- bootstrapping ---------------------------------------------------

def init_db():
    with app.app_context():
        db.create_all()
        from seed_data import seed_database
        seed_database(db, User, Vertical, Topic, SearchResult, PaaQuestion, RelatedQuery,
                      Doodle, GoogleApp, TrendingTerm, KnowledgeFact, bcrypt)


def normalize_seed_db_layout():
    """Re-emit indexes in alpha order + VACUUM so rebuilds match byte-for-byte.

    SQLAlchemy emits CREATE INDEX from Table.indexes (a Python set) whose
    iteration order is allocator-dependent. See harden-env/gotchas section 2.
    """
    from sqlalchemy import text
    with app.app_context():
        conn = db.engine.connect()
        try:
            idx_rows = conn.execute(text(
                "SELECT name, sql FROM sqlite_master WHERE type='index' AND name LIKE 'ix_%'"
            )).fetchall()
            for name, _ in idx_rows:
                conn.execute(text(f'DROP INDEX IF EXISTS "{name}"'))
            for name, sql in sorted(idx_rows, key=lambda r: r[0]):
                if sql:
                    conn.execute(text(sql))
            conn.commit()
            # VACUUM cannot run in a transaction
            conn.execute(text('VACUUM'))
        finally:
            conn.close()


def seed_benchmark_users():
    """Idempotent: create 4 benchmark users with history, bookmarks, collections, alerts.

    Safe to call multiple times — returns immediately if alice already exists.
    """
    if User.query.filter_by(email='alice.j@test.com').first():
        return  # already seeded

    # Pinned bcrypt hash for 'TestPass123!' - random salt would break byte-id
    # rebuilds. See harden-env/gotchas.
    _PINNED = '$2b$12$RwAC/sfwDHtccU//A20fde.uKkZK4Ptnjjyua2l2ktwI6uysAp3Ou'

    # ------------------------------------------------------------------ users
    alice = User(email='alice.j@test.com', name='Alice Johnson',
                 avatar_letter='A', safe_search='moderate', region='US',
                 language='en', results_per_page=10,
                 created=datetime(2026, 1, 5, 12, 0, 0))
    alice.password_hash = _PINNED

    bob = User(email='bob.c@test.com', name='Bob Chen',
               avatar_letter='B', safe_search='strict', region='US',
               language='en', results_per_page=20,
               created=datetime(2026, 1, 12, 12, 0, 0))
    bob.password_hash = _PINNED

    carol = User(email='carol.d@test.com', name='Carol Davis',
                 avatar_letter='C', safe_search='off', region='GB',
                 language='en', results_per_page=10,
                 created=datetime(2026, 2, 14, 12, 0, 0))
    carol.password_hash = _PINNED

    david = User(email='david.k@test.com', name='David Kim',
                 avatar_letter='D', safe_search='moderate', region='KR',
                 language='en', results_per_page=10,
                 created=datetime(2026, 3, 20, 12, 0, 0))
    david.password_hash = _PINNED

    db.session.add_all([alice, bob, carol, david])
    db.session.commit()

    # ------------------------------------------------------------------ helpers
    def _topic(slug):
        return Topic.query.filter_by(slug=slug).first()

    def _first_result(slug):
        t = _topic(slug)
        if t and t.results:
            return t.results[0]
        return None

    now = datetime(2026, 5, 12, 12, 0, 0)  # pinned ref for byte-id seeds

    # ------------------------------------------------------------------ alice: researcher / science enthusiast
    # Search history
    alice_queries = [
        ('climate change causes effects', 'all'),
        ('machine learning algorithms', 'all'),
        ('best restaurants in New York City', 'all'),
        ('Python programming tutorial', 'all'),
        ('space exploration news 2024', 'news'),
        ('electric vehicle battery technology', 'all'),
        ('large language models comparison', 'all'),
    ]
    for i, (q, vert) in enumerate(alice_queries):
        db.session.add(SearchHistory(
            user_id=alice.id, q=q, vertical=vert,
            result_count=100000 + (hash_int(q) % 4900000),
            searched_at=now - timedelta(hours=i * 3 + 1),
        ))

    # Collections
    alice_col1 = Collection(user_id=alice.id, name='AI Research',
                            description='Papers and articles on artificial intelligence',
                            color='#4285F4', is_public=False)
    alice_col2 = Collection(user_id=alice.id, name='Climate Science',
                            description='Articles about climate change and renewable energy',
                            color='#34A853', is_public=True)
    db.session.add_all([alice_col1, alice_col2])
    db.session.commit()

    # Bookmarks
    ai_result = _first_result('artificial_intelligence')
    ml_result = _first_result('machine_learning')
    llm_result = _first_result('large_language_model')
    climate_result = _first_result('climate_change')
    energy_result = _first_result('renewable_energy')

    alice_bookmarks = []
    if ai_result:
        alice_bookmarks.append(Bookmark(user_id=alice.id, result_id=ai_result.id,
            title=ai_result.title, url=ai_result.url, snippet=ai_result.snippet or '',
            note='Good overview of AI fundamentals', collection_id=alice_col1.id))
    if ml_result:
        alice_bookmarks.append(Bookmark(user_id=alice.id, result_id=ml_result.id,
            title=ml_result.title, url=ml_result.url, snippet=ml_result.snippet or '',
            note='Core ML concepts', collection_id=alice_col1.id))
    if llm_result:
        alice_bookmarks.append(Bookmark(user_id=alice.id, result_id=llm_result.id,
            title=llm_result.title, url=llm_result.url, snippet=llm_result.snippet or '',
            note='LLM overview', collection_id=alice_col1.id))
    if climate_result:
        alice_bookmarks.append(Bookmark(user_id=alice.id, result_id=climate_result.id,
            title=climate_result.title, url=climate_result.url, snippet=climate_result.snippet or '',
            note='Climate change basics', collection_id=alice_col2.id))
    if energy_result:
        alice_bookmarks.append(Bookmark(user_id=alice.id, result_id=energy_result.id,
            title=energy_result.title, url=energy_result.url, snippet=energy_result.snippet or '',
            note='Renewable energy sources', collection_id=alice_col2.id))
    # A manual bookmark not tied to a result
    alice_bookmarks.append(Bookmark(user_id=alice.id,
        title='IPCC Climate Report 2023',
        url='https://www.ipcc.ch/report/ar6/wg2/',
        snippet='Sixth Assessment Report on climate impacts.',
        note='Must-read reference', collection_id=alice_col2.id))
    db.session.add_all(alice_bookmarks)

    # Alerts
    db.session.add_all([
        Alert(user_id=alice.id, term='artificial intelligence', frequency='daily',
              sources='automatic', region='US', active=True),
        Alert(user_id=alice.id, term='climate change', frequency='weekly',
              sources='news', region='any', active=True),
        Alert(user_id=alice.id, term='renewable energy breakthrough', frequency='as_it_happens',
              sources='news', region='any', active=False),
    ])

    # ------------------------------------------------------------------ bob: sports & entertainment
    bob_queries = [
        ('NBA latest news 2024', 'news'),
        ('top movies 2024 box office', 'all'),
        ('Premier League standings', 'all'),
        ('best streaming shows right now', 'all'),
        ('Taylor Swift new album', 'all'),
        ('chess world championship', 'all'),
    ]
    for i, (q, vert) in enumerate(bob_queries):
        db.session.add(SearchHistory(
            user_id=bob.id, q=q, vertical=vert,
            result_count=50000 + (hash_int(q) % 2950000),
            searched_at=now - timedelta(hours=i * 4 + 2),
        ))

    bob_col1 = Collection(user_id=bob.id, name='Sports News',
                          description='Latest sports updates', color='#EA4335', is_public=True)
    bob_col2 = Collection(user_id=bob.id, name='Must-Watch',
                          description='Movies and shows to watch', color='#FBBC05', is_public=False)
    db.session.add_all([bob_col1, bob_col2])
    db.session.commit()

    olympic_result = _first_result('olympic_games')
    basketball_result = _first_result('basketball')
    chess_result = _first_result('chess')
    bob_bookmarks = []
    if olympic_result:
        bob_bookmarks.append(Bookmark(user_id=bob.id, result_id=olympic_result.id,
            title=olympic_result.title, url=olympic_result.url,
            snippet=olympic_result.snippet or '', collection_id=bob_col1.id))
    if basketball_result:
        bob_bookmarks.append(Bookmark(user_id=bob.id, result_id=basketball_result.id,
            title=basketball_result.title, url=basketball_result.url,
            snippet=basketball_result.snippet or '', collection_id=bob_col1.id))
    if chess_result:
        bob_bookmarks.append(Bookmark(user_id=bob.id, result_id=chess_result.id,
            title=chess_result.title, url=chess_result.url,
            snippet=chess_result.snippet or '', collection_id=bob_col2.id))
    bob_bookmarks.append(Bookmark(user_id=bob.id,
        title='ESPN Top Stories',
        url='https://www.espn.com/espn/topheadlines',
        snippet='Latest sports headlines from ESPN.',
        collection_id=bob_col1.id))
    db.session.add_all(bob_bookmarks)

    db.session.add_all([
        Alert(user_id=bob.id, term='NBA game results', frequency='daily',
              sources='news', region='US', active=True),
        Alert(user_id=bob.id, term='FIFA World Cup 2026', frequency='weekly',
              sources='automatic', region='any', active=True),
    ])

    # ------------------------------------------------------------------ carol: travel & culture
    carol_queries = [
        ('best travel destinations Europe 2024', 'all'),
        ('Tokyo travel guide', 'all'),
        ('Paris restaurants Michelin star', 'all'),
        ('aurora borealis best places to see', 'images'),
        ('grand canyon hiking trails', 'all'),
        ('cherry blossom season Japan', 'images'),
        ('pyramids of Giza history', 'all'),
    ]
    for i, (q, vert) in enumerate(carol_queries):
        db.session.add(SearchHistory(
            user_id=carol.id, q=q, vertical=vert,
            result_count=200000 + (hash_int(q) % 7800000),
            searched_at=now - timedelta(hours=i * 5 + 1),
        ))

    carol_col1 = Collection(user_id=carol.id, name='Travel Wishlist',
                            description='Places I want to visit', color='#9C27B0', is_public=True)
    carol_col2 = Collection(user_id=carol.id, name='Food & Dining',
                            description='Restaurant recommendations worldwide', color='#FF5722', is_public=False)
    db.session.add_all([carol_col1, carol_col2])
    db.session.commit()

    tokyo_result = _first_result('tokyo')
    paris_result = _first_result('paris')
    aurora_result = _first_result('aurora_borealis')
    canyon_result = _first_result('grand_canyon')
    pyramids_result = _first_result('pyramids_of_giza')
    carol_bookmarks = []
    for r, cid, note in [
        (tokyo_result, carol_col1.id, 'Planning trip for spring'),
        (paris_result, carol_col1.id, 'Dream destination'),
        (aurora_result, carol_col1.id, 'Need to see this in person'),
        (canyon_result, carol_col1.id, 'Great hiking'),
        (pyramids_result, carol_col1.id, 'Historical wonder'),
    ]:
        if r:
            carol_bookmarks.append(Bookmark(user_id=carol.id, result_id=r.id,
                title=r.title, url=r.url, snippet=r.snippet or '',
                note=note, collection_id=cid))
    carol_bookmarks.append(Bookmark(user_id=carol.id,
        title='Lonely Planet Best Destinations 2024',
        url='https://www.lonelyplanet.com/best-in-travel',
        snippet='Top travel destinations for 2024.',
        collection_id=carol_col1.id))
    db.session.add_all(carol_bookmarks)

    db.session.add_all([
        Alert(user_id=carol.id, term='Tokyo travel tips', frequency='weekly',
              sources='blogs', region='any', active=True),
        Alert(user_id=carol.id, term='aurora borealis forecast', frequency='daily',
              sources='automatic', region='any', active=True),
        Alert(user_id=carol.id, term='cheap flights Europe', frequency='as_it_happens',
              sources='automatic', region='GB', active=True),
    ])

    # ------------------------------------------------------------------ david: tech & science
    david_queries = [
        ('quantum computing latest research', 'all'),
        ('Python vs JavaScript 2024', 'all'),
        ('black hole new discovery', 'news'),
        ('solar system planets facts', 'all'),
        ('electric vehicle comparison 2024', 'all'),
        ('world wide web history', 'all'),
        ('mars mission news', 'news'),
    ]
    for i, (q, vert) in enumerate(david_queries):
        db.session.add(SearchHistory(
            user_id=david.id, q=q, vertical=vert,
            result_count=100000 + (hash_int(q) % 5900000),
            searched_at=now - timedelta(hours=i * 2 + 3),
        ))

    david_col1 = Collection(user_id=david.id, name='Space Science',
                            description='Space exploration and astronomy', color='#1A237E', is_public=True)
    david_col2 = Collection(user_id=david.id, name='Tech Resources',
                            description='Programming and technology articles', color='#006064', is_public=False)
    db.session.add_all([david_col1, david_col2])
    db.session.commit()

    qc_result = _first_result('quantum_computing')
    bh_result = _first_result('black_hole')
    mars_result = _first_result('mars')
    sol_result = _first_result('solar_system')
    py_result = _first_result('python_programming_language')
    ev_result = _first_result('electric_vehicle')
    david_bookmarks = []
    for r, cid, note in [
        (qc_result, david_col2.id, 'Fascinating next-gen computing'),
        (bh_result, david_col1.id, 'Latest black hole research'),
        (mars_result, david_col1.id, 'Mars colonization plans'),
        (sol_result, david_col1.id, 'Solar system overview'),
        (py_result, david_col2.id, 'Python reference'),
        (ev_result, david_col2.id, 'EV market analysis'),
    ]:
        if r:
            david_bookmarks.append(Bookmark(user_id=david.id, result_id=r.id,
                title=r.title, url=r.url, snippet=r.snippet or '',
                note=note, collection_id=cid))
    db.session.add_all(david_bookmarks)

    db.session.add_all([
        Alert(user_id=david.id, term='quantum computing breakthrough', frequency='daily',
              sources='news', region='any', active=True),
        Alert(user_id=david.id, term='Mars mission update', frequency='weekly',
              sources='automatic', region='any', active=True),
        Alert(user_id=david.id, term='Python new release', frequency='as_it_happens',
              sources='blogs', region='any', active=False),
    ])

    db.session.commit()

    # Pin every default-datetime column we just inserted to deterministic
    # offsets from `now` so rebuilds are byte-identical (Column defaults
    # `datetime.utcnow` would otherwise capture wall-clock at insert time).
    user_ids = [alice.id, bob.id, carol.id, david.id]
    # Bookmarks
    bms = Bookmark.query.filter(Bookmark.user_id.in_(user_ids)).order_by(Bookmark.id).all()
    for idx, b in enumerate(bms):
        b.created = now - timedelta(hours=idx * 2 + 1)
    # Collections
    cols = Collection.query.filter(Collection.user_id.in_(user_ids)).order_by(Collection.id).all()
    for idx, c in enumerate(cols):
        c.created = now - timedelta(days=idx + 1)
    # Alerts
    als = Alert.query.filter(Alert.user_id.in_(user_ids)).order_by(Alert.id).all()
    for idx, a in enumerate(als):
        a.created = now - timedelta(days=idx + 1, hours=3)
    db.session.commit()

    print('  Benchmark users seeded: alice, bob, carol, david')


def seed_result_feedback():
    """Idempotent: seed thumbs-up / thumbs-down feedback for benchmark users.

    Runs independently of `seed_benchmark_users` because the original seed DB
    was generated before the result_feedback table was populated. Early-
    returns once ANY feedback row exists so subsequent boots stay byte
    identical (per `.claude/skills/seed-database/SKILL.md` Phase 5 §1).
    """
    if ResultFeedback.query.count() > 0:
        return

    users = {u.email: u for u in User.query.filter(User.email.in_([
        'alice.j@test.com', 'bob.c@test.com',
        'carol.d@test.com', 'david.k@test.com',
    ])).all()}
    if len(users) < 4:
        return  # benchmark users not present yet

    alice = users['alice.j@test.com']
    bob = users['bob.c@test.com']
    carol = users['carol.d@test.com']
    david = users['david.k@test.com']

    # Pinned reference date so seed regen is reproducible.
    ref = datetime(2026, 4, 15, 12, 0, 0)

    def first_result(slug):
        t = Topic.query.filter_by(slug=slug).first()
        if t and t.results:
            return t.results[0]
        return None

    # (user, topic_slug, rating, comment, hours_ago)
    # 8-9 feedbacks per user × 4 users == 34 rows. Slugs verified against
    # the existing seed DB to ensure each Topic + first_result exists.
    plan = [
        # Alice — researcher / science
        (alice, 'chatgpt',              'helpful',     'Great overview of how the model is used today.', 2),
        (alice, 'claude_ai',            'helpful',     'Clear explanation of Constitutional AI.', 6),
        (alice, 'marie_curie',          'helpful',     'Best Marie Curie biography I have found online.', 12),
        (alice, 'albert_einstein',      'helpful',     'Solid summary of general relativity.', 24),
        (alice, 'nvidia_h100',          'not_helpful', 'Too vendor-marketing-y, light on benchmarks.', 30),
        (alice, 'iphone_15',            'helpful',     'Useful spec comparison vs the 14 Pro.', 48),
        (alice, 'apple_vision_pro',     'helpful',     'Honest take on the form factor.', 72),
        (alice, 'moon_landing_apollo_11_1969', 'helpful', 'Beautifully sourced timeline.', 96),
        (alice, 'fall_of_the_berlin_wall_1989', 'helpful', 'Great archival photos.', 120),
        # Bob — sports / entertainment
        (bob,   'lebron_james',         'helpful',     'Good career summary, updated stats.', 3),
        (bob,   'stephen_curry',        'helpful',     'Three-point record section is well written.', 9),
        (bob,   'michael_jordan',       'helpful',     'Definitive career retrospective.', 15),
        (bob,   'kobe_bryant',          'helpful',     'Respectful tribute and stats.', 22),
        (bob,   'serena_williams',      'helpful',     'Covers her full Grand Slam history.', 40),
        (bob,   'super_bowl_lviii',     'spam',        'Tons of pop-up ads on this result page.', 60),
        (bob,   'wimbledon_2024',       'helpful',     'Bracket recap was accurate.', 80),
        (bob,   'formula_1_2024_season','helpful',     'Driver standings table is up to date.', 110),
        # Carol — travel / culture
        (carol, 'paris',                'helpful',     'Perfect for my Eurostar weekend.', 4),
        (carol, 'tokyo',                'helpful',     'Loved the neighbourhood map.', 11),
        (carol, 'london',               'helpful',     'Solid first-time visitor guide.', 19),
        (carol, 'new_york_city',        'not_helpful', 'Restaurant list is from 2018.', 28),
        (carol, 'sydney',               'helpful',     'Bondi to Coogee walk write-up is great.', 36),
        (carol, 'stranger_things',      'helpful',     'Tonally on-point episode guide.', 55),
        (carol, 'breaking_bad',         'helpful',     'No-spoiler season summaries — thanks.', 78),
        (carol, 'game_of_thrones',      'not_helpful', 'Spoilers in the first paragraph.', 100),
        # David — tech / space
        (david, 'chatgpt',              'helpful',     'Good pointer to OpenAI cookbook.', 5),
        (david, 'claude_ai',            'helpful',     'Up to date with the Claude 3 family.', 14),
        (david, 'nvidia_h100',          'helpful',     'Helpful TCO comparison vs A100.', 21),
        (david, 'iphone_15',            'not_helpful', 'Missing benchmark numbers.', 34),
        (david, 'oppenheimer_2023',     'helpful',     'Great historical context section.', 50),
        (david, 'barbie_2023',          'helpful',     'Surprisingly insightful film analysis.', 70),
        (david, 'dune_part_two_2024',   'helpful',     'Visual effects breakdown is gold.', 90),
        (david, 'elden_ring',           'helpful',     'Late-game build guide saved me hours.', 115),
        (david, 'baldur_s_gate_3',      'spam',        'Article is a thinly veiled key-reseller ad.', 140),
    ]

    added = 0
    for user, slug, rating, comment, hours in plan:
        r = first_result(slug)
        if r is None:
            continue
        db.session.add(ResultFeedback(
            user_id=user.id,
            result_id=r.id,
            rating=rating,
            comment=comment,
            created=ref - timedelta(hours=hours),
        ))
        added += 1

    db.session.commit()
    print(f'  Result feedback seeded: {added} rows across 4 users')



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
R2_SITE_NAME = "Google Search"
R2_DOMAIN = "google.com"
R2_ACCESSIBILITY_BLURB = "Google Search exposes ARIA live-regions for instant results and supports keyboard-only navigation across all answer cards."


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
R3_SITE_NAME = "Google Search"
R3_DOMAIN = "google.com"


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


# === R4 / R5 / R6 / R10 surface routes ===
import importlib.util as _r4_ilu  # noqa: E402
_r4_spec = _r4_ilu.spec_from_file_location(
    '_r4_r10_routes', os.path.join(HERE, '_r4_r10_routes.py'),
)
_r4_mod = _r4_ilu.module_from_spec(_r4_spec)
_r4_spec.loader.exec_module(_r4_mod)
_r4_mod.register_all(app)


if __name__ == '__main__':
    init_db()
    with app.app_context():
        seed_benchmark_users()
        seed_result_feedback()
    normalize_seed_db_layout()
    port = int(os.environ.get('PORT', 28851))
    app.run(host='0.0.0.0', port=port, debug=False)
