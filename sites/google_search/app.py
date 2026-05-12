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
import random
import re
from datetime import datetime, timedelta
from urllib.parse import urlparse

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
        })

    # Panel visibility: only show for bio / fact-lookup tasks.
    show_panel = should_show_panel(topic, q)

    return render_template(
        template,
        q=q, page=page, vertical=vertical,
        topic=topic, results=annotated,
        paa=paa, related=related, knowledge=knowledge,
        result_count=result_count, search_time=search_time,
        answer_token=answer_token,
        knowledge_panel=knowledge_panel,
        show_panel=show_panel,
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


def seed_benchmark_users():
    """Idempotent: create 4 benchmark users with history, bookmarks, collections, alerts.

    Safe to call multiple times — returns immediately if alice already exists.
    """
    if User.query.filter_by(email='alice.j@test.com').first():
        return  # already seeded

    _PASS = 'TestPass123!'

    # ------------------------------------------------------------------ users
    alice = User(email='alice.j@test.com', name='Alice Johnson',
                 avatar_letter='A', safe_search='moderate', region='US',
                 language='en', results_per_page=10)
    alice.set_password(_PASS)

    bob = User(email='bob.c@test.com', name='Bob Chen',
               avatar_letter='B', safe_search='strict', region='US',
               language='en', results_per_page=20)
    bob.set_password(_PASS)

    carol = User(email='carol.d@test.com', name='Carol Davis',
                 avatar_letter='C', safe_search='off', region='GB',
                 language='en', results_per_page=10)
    carol.set_password(_PASS)

    david = User(email='david.k@test.com', name='David Kim',
                 avatar_letter='D', safe_search='moderate', region='KR',
                 language='en', results_per_page=10)
    david.set_password(_PASS)

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

    now = datetime.utcnow()

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
            result_count=random.randint(100000, 5000000),
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
            result_count=random.randint(50000, 3000000),
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
            result_count=random.randint(200000, 8000000),
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
            result_count=random.randint(100000, 6000000),
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
    print('  Benchmark users seeded: alice, bob, carol, david')


if __name__ == '__main__':
    init_db()
    with app.app_context():
        seed_benchmark_users()
    port = int(os.environ.get('PORT', 28851))
    app.run(host='0.0.0.0', port=port, debug=False)
