#!/usr/bin/env python3
"""Cambridge Dictionary mirror — Flask application."""
import os
import json
import random
import re
from datetime import datetime

from flask import (Flask, render_template, request, redirect, url_for,
                   flash, jsonify, session, abort, g)
from flask_sqlalchemy import SQLAlchemy
from flask_login import (LoginManager, UserMixin, login_user, logout_user,
                         login_required, current_user)
from flask_wtf import FlaskForm
from flask_wtf.csrf import CSRFProtect, generate_csrf
from flask_bcrypt import Bcrypt
from wtforms import StringField, PasswordField, TextAreaField, SelectField
from wtforms.validators import DataRequired, Email, Length, EqualTo, Optional
from sqlalchemy import or_, func

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__)
app.config['SECRET_KEY'] = 'cambridge-dict-mirror-secret-key'
app.config['SQLALCHEMY_DATABASE_URI'] = (
    f"sqlite:///{os.path.join(BASE_DIR, 'instance', 'cambridge.db')}"
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['WTF_CSRF_TIME_LIMIT'] = None

os.makedirs(os.path.join(BASE_DIR, 'instance'), exist_ok=True)

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please sign in to access your account.'
login_manager.login_message_category = 'info'
csrf = CSRFProtect(app)


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class User(db.Model, UserMixin):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    name = db.Column(db.String(120), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    saved_words = db.relationship('SavedWord', backref='user', lazy=True,
                                  cascade='all, delete-orphan')
    search_history = db.relationship('SearchHistory', backref='user', lazy=True,
                                     cascade='all, delete-orphan')

    def set_password(self, pw):
        self.password_hash = bcrypt.generate_password_hash(pw).decode('utf-8')

    def check_password(self, pw):
        return bcrypt.check_password_hash(self.password_hash, pw)


class Word(db.Model):
    __tablename__ = 'words'
    id = db.Column(db.Integer, primary_key=True)
    headword = db.Column(db.String(120), nullable=False, index=True)
    slug = db.Column(db.String(120), unique=True, nullable=False, index=True)
    pos = db.Column(db.String(40), default='')           # noun, verb, adj, etc.
    guide_word = db.Column(db.String(200), default='')   # short gloss for disambiguation
    phonetic_uk = db.Column(db.String(100), default='')  # IPA UK
    phonetic_us = db.Column(db.String(100), default='')  # IPA US
    # R2: a non-region-specific IPA slot, populated for the WordNet-generated
    # long tail that doesn't have curated UK/US transcriptions. Curated words
    # mirror phonetic_uk into this field so callers can always read one slot.
    pronunciation_ipa = db.Column(db.String(120), default='')
    # R2: deterministic per-region MP3 placeholder paths. The MP3 files are
    # NOT shipped — templates only render the URL string and the browser's
    # native onerror handling hides the player. Real Cambridge keys audio
    # per region (UK / US).
    audio_uk_path = db.Column(db.String(255), default='')
    audio_us_path = db.Column(db.String(255), default='')
    level = db.Column(db.String(10), default='')         # B1, C1, etc.
    # Definitions stored as JSON list of dicts:
    # [{sense_num, grammar_note, definition, examples:[str], register}]
    definitions_json = db.Column(db.Text, default='[]')
    # Translations stored as JSON dict: {language: {text, provider}}
    translations_json = db.Column(db.Text, default='{}')
    # Related words: [{type: word|phrase|idiom, text, definition}]
    related_json = db.Column(db.Text, default='[]')
    # Thesaurus synonyms for thesaurus entries
    synonyms_json = db.Column(db.Text, default='[]')
    is_thesaurus_phrase = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # R4 extensions ----------------------------------------------------------
    # Word-level register tag (formal / informal / slang / archaic / technical /
    # literary / humorous). Empty string for neutral. This complements the
    # per-sense register inside definitions_json — R4 surfaces a top-level chip.
    register = db.Column(db.String(40), default='')
    # 1-based frequency rank within the dictionary. 1 = most frequent. 0 means
    # rank not yet assigned (legacy R2/R3 rows).
    frequency_rank = db.Column(db.Integer, default=0)
    # Short etymology paragraph rendered on /etymology/<slug>.
    etymology = db.Column(db.Text, default='')
    # JSON list of {phrase, type, example} entries, surfaced on
    # /collocation/<slug> and inside word_detail.
    collocations_json = db.Column(db.Text, default='[]')
    # Common-mistake hint shown on the word entry page.
    mistake_note = db.Column(db.Text, default='')

    saved_by = db.relationship('SavedWord', backref='word', lazy=True,
                               cascade='all, delete-orphan')

    def get_definitions(self):
        try:
            return json.loads(self.definitions_json or '[]')
        except Exception:
            return []

    def get_translations(self):
        try:
            return json.loads(self.translations_json or '{}')
        except Exception:
            return {}

    def get_related(self):
        try:
            return json.loads(self.related_json or '[]')
        except Exception:
            return []

    def get_synonyms(self):
        try:
            return json.loads(self.synonyms_json or '[]')
        except Exception:
            return []

    def get_collocations(self):
        try:
            return json.loads(self.collocations_json or '[]')
        except Exception:
            return []

    @property
    def definitions_count(self):
        """Surface a cheap sense-count for templates and tasks
        ('How many meanings of X are listed?'). No DB column."""
        return len(self.get_definitions())


class SavedWord(db.Model):
    __tablename__ = 'saved_words'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    word_id = db.Column(db.Integer, db.ForeignKey('words.id'), nullable=False)
    notes = db.Column(db.Text, default='')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class SearchHistory(db.Model):
    __tablename__ = 'search_history'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    term = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class GrammarTopic(db.Model):
    __tablename__ = 'grammar_topics'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    slug = db.Column(db.String(200), unique=True, nullable=False, index=True)
    category = db.Column(db.String(100), default='')
    summary = db.Column(db.Text, default='')
    # content_json: list of sections [{heading, body, examples:[{label,sentence}]}]
    content_json = db.Column(db.Text, default='[]')
    sort_order = db.Column(db.Integer, default=0)

    def get_content(self):
        try:
            return json.loads(self.content_json or '[]')
        except Exception:
            return []


class ShopItem(db.Model):
    __tablename__ = 'shop_items'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    slug = db.Column(db.String(200), unique=True, nullable=False)
    category = db.Column(db.String(80), default='books')
    price = db.Column(db.Float, default=0.0)
    currency = db.Column(db.String(5), default='GBP')
    description = db.Column(db.Text, default='')
    image = db.Column(db.String(300), default='')
    isbn = db.Column(db.String(40), default='')
    is_featured = db.Column(db.Boolean, default=False)


class Quiz(db.Model):
    __tablename__ = 'quizzes'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    slug = db.Column(db.String(200), unique=True, nullable=False)
    quiz_type = db.Column(db.String(40), default='grammar')  # grammar|image|scramble
    difficulty = db.Column(db.String(20), default='easy')
    category = db.Column(db.String(80), default='')
    description = db.Column(db.Text, default='')
    # questions_json: list of {q, options:[str], answer:int, image?}
    questions_json = db.Column(db.Text, default='[]')

    def get_questions(self):
        try:
            return json.loads(self.questions_json or '[]')
        except Exception:
            return []


class MistakeCorner(db.Model):
    """R4 — mistake-corner topics surfaced under /mistake/<slug>.

    Each entry is a self-contained learner-error topic (e.g. ``affect-vs-effect``,
    ``schedule-uk-vs-us``) with a body paragraph and a list of wrong→right
    example pairs.
    """
    __tablename__ = 'mistake_corner'
    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(120), unique=True, nullable=False, index=True)
    topic = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(80), default='')
    body = db.Column(db.Text, default='')
    # examples_json: list of {wrong, right, note}
    examples_json = db.Column(db.Text, default='[]')
    sort_order = db.Column(db.Integer, default=0)

    def get_examples(self):
        try:
            return json.loads(self.examples_json or '[]')
        except Exception:
            return []


# ---------------------------------------------------------------------------
# Forms
# ---------------------------------------------------------------------------

class RegisterForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired(), Length(min=2, max=100)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    confirm = PasswordField('Confirm Password',
                            validators=[DataRequired(), EqualTo('password')])


class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])


class SearchForm(FlaskForm):
    q = StringField('Search', validators=[DataRequired()])


class AccountEditForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired(), Length(min=2, max=100)])
    email = StringField('Email', validators=[DataRequired(), Email()])


class ChangePasswordForm(FlaskForm):
    current_password = PasswordField('Current Password', validators=[DataRequired()])
    new_password = PasswordField('New Password',
                                  validators=[DataRequired(), Length(min=6)])
    confirm = PasswordField('Confirm New Password',
                            validators=[DataRequired(), EqualTo('new_password')])


# ---------------------------------------------------------------------------
# Login manager
# ---------------------------------------------------------------------------

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


# Minimal UI translation dictionary. When session['lang'] selects one of
# these locales, visible homepage/nav strings are swapped via the `ui` dict
# exposed to every template. English (UK) is the default and returns the
# English strings unchanged. See also templates/base.html and
# templates/index.html which read ui['key'] for translated copy.
UI_TRANSLATIONS = {
    'Deutsch': {
        'site_name': 'Cambridge Wörterbuch',
        'hero_title': 'Finden Sie das perfekte Wort',
        'hero_sub': 'Das Cambridge Wörterbuch. Weltweit von Lernenden vertraut.',
        'nav_dictionary': 'Wörterbuch',
        'nav_thesaurus': 'Thesaurus',
        'nav_translate': 'Übersetzen',
        'nav_grammar': 'Grammatik',
        'nav_plus': 'Plus',
        'nav_shop': 'Shop',
        'nav_signin': 'Anmelden',
        'nav_register': 'Registrieren',
        'nav_signout': 'Abmelden',
        'search_placeholder': 'Im Cambridge Wörterbuch suchen',
        'word_of_day': 'Wort des Tages',
        'recent_words': 'Zuletzt nachgeschlagene Wörter',
        'read_more': 'Mehr lesen',
        'plus_title': 'Cambridge Wörterbuch Plus',
        'topbar_text': 'Cambridge Wörterbuch Plus — Verbessern Sie Ihren Wortschatz mit Quizzen und Spielen.',
        'try_plus': 'Cambridge Plus ausprobieren',
    },
}

UI_DEFAULT = {
    'site_name': 'Cambridge Dictionary',
    'hero_title': 'Find the perfect word',
    'hero_sub': 'The Cambridge Dictionary. Trusted by learners around the world.',
    'nav_dictionary': 'Dictionary',
    'nav_thesaurus': 'Thesaurus',
    'nav_translate': 'Translate',
    'nav_grammar': 'Grammar',
    'nav_plus': 'Plus',
    'nav_shop': 'Shop',
    'nav_signin': 'Sign in',
    'nav_register': 'Register',
    'nav_signout': 'Sign out',
    'search_placeholder': 'Search the Cambridge Dictionary',
    'word_of_day': 'Word of the Day',
    'recent_words': 'Recently looked up words',
    'read_more': 'Read more',
    'plus_title': 'Cambridge Dictionary Plus',
    'topbar_text': 'Cambridge Dictionary Plus — Improve your vocabulary with quizzes and games.',
    'try_plus': 'Try Cambridge Plus',
}


@app.context_processor
def inject_globals():
    lang = session.get('lang', 'English (UK)') if 'session' in globals() or True else 'English (UK)'
    try:
        lang = session.get('lang', 'English (UK)')
    except Exception:
        lang = 'English (UK)'
    ui = dict(UI_DEFAULT)
    overrides = UI_TRANSLATIONS.get(lang)
    if overrides:
        ui.update(overrides)
    return {'languages': LANGUAGES, 'ui': ui, 'current_lang': lang}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

STOPWORDS = {'the', 'a', 'an', 'of', 'in', 'on', 'at', 'to', 'for',
             'with', 'and', 'or', 'is', 'are', 'be', 'by', 'from',
             'that', 'this', 'it', 'as', 'its', 'up'}

LANGUAGES = ['English (UK)', 'Deutsch', 'Español', 'Français', 'Italiano',
             '中文', '日本語', 'Polski', 'Português', 'Nederlands']


def _score_word(word, tokens):
    haystack = ' '.join([
        (word.headword or '').lower(),
        (word.pos or '').lower(),
        (word.guide_word or '').lower(),
        (word.definitions_json or '').lower(),
    ])
    return sum(1 for t in tokens if t in haystack)


def _search_words(q):
    """Return scored list of words matching query."""
    tokens = [t.lower() for t in re.findall(r'[a-z0-9]+', q.lower())
              if t not in STOPWORDS and len(t) >= 2]
    if not tokens:
        return []
    # Exact headword match first
    exact = Word.query.filter(
        Word.headword.ilike(q.strip()),
        Word.is_thesaurus_phrase == False  # noqa
    ).all()
    # Partial matches
    partial = Word.query.filter(
        Word.headword.ilike(f'%{tokens[0]}%'),
        Word.is_thesaurus_phrase == False  # noqa
    ).limit(50).all()
    seen = {w.id for w in exact}
    combined = exact + [w for w in partial if w.id not in seen]
    min_req = max(1, len(tokens) // 2)
    scored = [(s, w) for w in combined
              if (s := _score_word(w, tokens)) >= min_req]
    scored.sort(key=lambda x: -x[0])
    return [w for _, w in scored]


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route('/')
def index():
    featured_words = Word.query.filter_by(level='C1').limit(6).all()
    if len(featured_words) < 6:
        featured_words = Word.query.limit(6).all()
    lang = session.get('lang', 'English (UK)')
    return render_template('index.html', featured_words=featured_words,
                           lang=lang)


# --- Dictionary routes ---

@app.route('/dictionary/english/<slug>')
def word_detail(slug):
    word = Word.query.filter_by(slug=slug).first_or_404()
    definitions = word.get_definitions()
    translations = word.get_translations()
    related = word.get_related()
    synonyms = word.get_synonyms()

    # Save to search history if logged in
    if current_user.is_authenticated:
        h = SearchHistory(user_id=current_user.id, term=word.headword)
        db.session.add(h)
        db.session.commit()

    is_saved = False
    if current_user.is_authenticated:
        is_saved = SavedWord.query.filter_by(
            user_id=current_user.id, word_id=word.id).first() is not None

    # Alphabetically nearby words (4 before + this word + 4 after) for the
    # "Browse" panel — mirrors Cambridge's nearby-word index.
    prev_words = (Word.query
                  .filter(Word.is_thesaurus_phrase == False,  # noqa
                          Word.headword < word.headword)
                  .order_by(Word.headword.desc()).limit(4).all())
    next_words = (Word.query
                  .filter(Word.is_thesaurus_phrase == False,  # noqa
                          Word.headword > word.headword)
                  .order_by(Word.headword.asc()).limit(4).all())
    nearby_words = list(reversed(prev_words)) + [word] + next_words

    # Corpus-style examples: collected across all sense examples for the
    # "Examples of X" section — mirrors the real entry's corpus block.
    corpus_examples = []
    for d in definitions:
        for ex in (d.get('examples') or []):
            corpus_examples.append(ex)

    return render_template('word_detail.html', word=word,
                           definitions=definitions,
                           translations=translations,
                           related=related,
                           synonyms=synonyms,
                           is_saved=is_saved,
                           nearby_words=nearby_words,
                           corpus_examples=corpus_examples)


@app.route('/search')
@app.route('/search/direct/')
@app.route('/search/english/direct/')
def search():
    q = request.args.get('q', '').strip()
    search_type = request.args.get('type', 'dictionary')
    if not q:
        return render_template('search.html', q='', results=[], search_type=search_type)

    # Exact thesaurus-article match — redirect straight to the article so
    # multi-word thesaurus searches like "to behave well" land on the page.
    slug = re.sub(r'[^a-z0-9]+', '-', q.lower()).strip('-')
    thes_exact = Word.query.filter(
        Word.is_thesaurus_phrase == True,  # noqa
        or_(Word.slug == slug, Word.headword.ilike(q))
    ).first()
    if thes_exact and search_type != 'dictionary-only':
        return redirect(url_for('thesaurus_article', slug=thes_exact.slug))

    if search_type == 'thesaurus':
        # Search thesaurus entries
        results = Word.query.filter(
            Word.is_thesaurus_phrase == True,  # noqa
            Word.headword.ilike(f'%{q}%')
        ).limit(20).all()
        if not results:
            results = _search_words(q)
    else:
        results = _search_words(q)
        # Surface thesaurus articles in normal search results too, so a
        # user typing "to behave well" in the global search bar still
        # finds the article instead of seeing "No results".
        thes = Word.query.filter(
            Word.is_thesaurus_phrase == True,  # noqa
            or_(Word.headword.ilike(f'%{q}%'), Word.slug.ilike(f'%{slug}%'))
        ).limit(10).all()
        # Append thesaurus matches that aren't already in results
        seen_ids = {w.id for w in results}
        for t in thes:
            if t.id not in seen_ids:
                results.append(t)

    # Save history
    if current_user.is_authenticated and q:
        h = SearchHistory(user_id=current_user.id, term=q)
        db.session.add(h)
        db.session.commit()

    return render_template('search.html', q=q, results=results,
                           search_type=search_type)


@app.route('/autocomplete')
@csrf.exempt
def autocomplete():
    """Search auto-suggest endpoint.

    Default response (legacy): JSON list of headwords. When ``?detail=1`` is
    passed, returns a list of dicts ``[{headword, slug, level, preview}]`` so
    the search box can render the R5 inline definition preview.
    """
    q = request.args.get('q', '').strip().lower()
    detail = request.args.get('detail') in ('1', 'true', 'yes')
    if len(q) < 2:
        return jsonify([])
    words = Word.query.filter(
        Word.headword.ilike(f'{q}%'),
        Word.is_thesaurus_phrase == False  # noqa
    ).limit(8).all()
    if not detail:
        return jsonify([w.headword for w in words])
    out = []
    for w in words:
        defs = w.get_definitions()
        preview = ''
        if defs:
            preview = (defs[0].get('definition') or '')[:140]
        out.append({
            'headword': w.headword,
            'slug': w.slug,
            'level': w.level or '',
            'preview': preview,
        })
    return jsonify(out)


# --- Thesaurus ---

@app.route('/thesaurus/english/<path:phrase>')
def thesaurus_entry(phrase):
    # Try exact match first
    entry = Word.query.filter_by(slug=phrase, is_thesaurus_phrase=True).first()
    if not entry:
        entry = Word.query.filter(
            Word.headword.ilike(phrase.replace('-', ' ')),
            Word.is_thesaurus_phrase == True  # noqa
        ).first()
    if not entry:
        # Try regular word's synonyms
        entry = Word.query.filter_by(slug=phrase).first()
    if not entry:
        abort(404)
    synonyms = entry.get_synonyms()
    related = entry.get_related()
    sections = entry.get_definitions()
    # Use the rich article template for thesaurus phrases that have full
    # article-style sections (definition body + examples). Falls back to
    # the legacy synonyms-list template for plain word entries.
    if (entry.is_thesaurus_phrase and sections
            and sections[0].get('definition', '').startswith(('You ', 'The ', 'When ', 'To ', 'A '))):
        return render_template('thesaurus_article.html', entry=entry,
                               synonyms=synonyms, sections=sections)
    return render_template('thesaurus.html', entry=entry,
                           synonyms=synonyms, related=related)


@app.route('/thesaurus/articles/<slug>')
def thesaurus_article(slug):
    """Cambridge-style long-form thesaurus article for a phrase
    (e.g. /thesaurus/articles/to-behave-well)."""
    entry = Word.query.filter_by(slug=slug, is_thesaurus_phrase=True).first()
    if not entry:
        # Try slug without leading "to-"
        entry = Word.query.filter_by(slug=slug.lstrip('to-'), is_thesaurus_phrase=True).first()
    if not entry:
        abort(404)
    synonyms = entry.get_synonyms()
    sections = entry.get_definitions()  # reused as article sections
    return render_template('thesaurus_article.html', entry=entry,
                           synonyms=synonyms, sections=sections)


@app.route('/thesaurus')
@app.route('/search/english-thesaurus/direct/')
def thesaurus_search():
    q = request.args.get('q', '').strip()
    if not q:
        return render_template('thesaurus_index.html', q='', results=[])
    slug = re.sub(r'[^a-z0-9]+', '-', q.lower()).strip('-')
    results = Word.query.filter(
        Word.is_thesaurus_phrase == True,  # noqa
        or_(Word.headword.ilike(f'%{q}%'), Word.slug.ilike(f'%{slug}%'))
    ).limit(20).all()
    if len(results) == 1:
        return redirect(url_for('thesaurus_entry', phrase=results[0].slug))
    if not results:
        # Fallback: find a regular word
        word = Word.query.filter(Word.headword.ilike(q)).first()
        if word:
            return redirect(url_for('thesaurus_entry', phrase=word.slug))
    return render_template('thesaurus_index.html', q=q, results=results)


# --- Grammar ---

@app.route('/grammar/british-grammar/')
def grammar_index():
    topics = GrammarTopic.query.order_by(GrammarTopic.sort_order).all()
    # Group by category
    categories = {}
    for t in topics:
        categories.setdefault(t.category, []).append(t)
    return render_template('grammar_index.html', categories=categories)


@app.route('/grammar/british-grammar/<slug>')
def grammar_topic(slug):
    topic = GrammarTopic.query.filter_by(slug=slug).first_or_404()
    content = topic.get_content()
    # Get adjacent topics for navigation
    all_topics = GrammarTopic.query.order_by(GrammarTopic.sort_order).all()
    idx = next((i for i, t in enumerate(all_topics) if t.id == topic.id), 0)
    prev_topic = all_topics[idx - 1] if idx > 0 else None
    next_topic = all_topics[idx + 1] if idx < len(all_topics) - 1 else None
    return render_template('grammar_topic.html', topic=topic, content=content,
                           prev_topic=prev_topic, next_topic=next_topic)


# --- Translation ---

@app.route('/translate')
def translate():
    q = request.args.get('q', '').strip()
    src = request.args.get('src', 'english')
    dst = request.args.get('dst', 'chinese-simplified')
    result = None
    provider = 'Microsoft'
    if q:
        word = Word.query.filter(Word.headword.ilike(q)).first()
        if word:
            translations = word.get_translations()
            # Map dst locale slug to the canonical key used inside
            # translations dict. Use EXACT equality to avoid substring
            # collisions (e.g. "es" appearing inside "chinese").
            lang_canonical = {
                'chinese-simplified': 'chinese',
                'chinese': 'chinese',
                'zh': 'chinese',
                'mandarin': 'chinese',
                'french': 'french',
                'fr': 'french',
                'spanish': 'spanish',
                'es': 'spanish',
                'german': 'german',
                'de': 'german',
                'japanese': 'japanese',
                'ja': 'japanese',
                'portuguese': 'portuguese',
                'pt': 'portuguese',
                'italian': 'italian',
                'it': 'italian',
            }
            target_key = lang_canonical.get(dst.lower(), dst.lower())
            # First, try a direct exact-key lookup
            for k, v in translations.items():
                if k.lower() == target_key:
                    result = v
                    break
            # If no direct hit, try matching an accepted alias against
            # the full key (exact-equality only — no substring match).
            if result is None:
                aliases = {v for k, v in lang_canonical.items()
                           if v == target_key}
                aliases.add(target_key)
                for k, v in translations.items():
                    if k.lower() in aliases:
                        result = v
                        break
    return render_template('translate.html', q=q, src=src, dst=dst,
                           result=result, provider=provider)


# --- Plus section ---

@app.route('/plus')
def plus_index():
    quizzes = Quiz.query.all()
    grammar_quizzes = [q for q in quizzes if q.quiz_type == 'grammar']
    image_quizzes = [q for q in quizzes if q.quiz_type == 'image']
    return render_template('plus_index.html',
                           grammar_quizzes=grammar_quizzes,
                           image_quizzes=image_quizzes)


@app.route('/plus/quiz/<slug>')
def quiz_detail(slug):
    quiz = Quiz.query.filter_by(slug=slug).first_or_404()
    questions = quiz.get_questions()
    return render_template('quiz.html', quiz=quiz, questions=questions)


@app.route('/plus/word-scramble')
def word_scramble():
    # Pick a random word for the scramble
    words = Word.query.filter(
        Word.is_thesaurus_phrase == False,  # noqa
        func.length(Word.headword) >= 4,
        func.length(Word.headword) <= 12
    ).all()
    if not words:
        word = None
        scrambled = ''
        definition = ''
    else:
        word = random.choice(words)
        letters = list(word.headword.lower())
        random.shuffle(letters)
        scrambled = ''.join(letters)
        defs = word.get_definitions()
        definition = defs[0]['definition'] if defs else word.guide_word
    return render_template('word_scramble.html', word=word,
                           scrambled=scrambled, definition=definition)


# --- Shop ---

@app.route('/shop')
def shop():
    items = ShopItem.query.all()
    return render_template('shop.html', items=items)


@app.route('/shop/<slug>')
def shop_item(slug):
    item = ShopItem.query.filter_by(slug=slug).first_or_404()
    related = ShopItem.query.filter(
        ShopItem.id != item.id,
        ShopItem.category == item.category
    ).limit(3).all()
    return render_template('shop_item.html', item=item, related=related)


# --- Word of the Day --------------------------------------------------------
# Real Cambridge picks a daily WOTD that any visitor can hit at a stable URL.
# We pick deterministically from MIRROR_REFERENCE_DATE so re-seeds and tests
# always agree on today's word, and also accept ?date=YYYY-MM-DD so agents
# can navigate the archive without server-side mutation.

@app.route('/word-of-the-day')
@app.route('/word-of-the-day/')
def word_of_the_day():
    date_str = request.args.get('date', '').strip()
    try:
        target_date = (datetime.strptime(date_str, '%Y-%m-%d').date()
                       if date_str else MIRROR_REFERENCE_DATE.date())
    except ValueError:
        target_date = MIRROR_REFERENCE_DATE.date()

    # Deterministic pick: hash the date into a row index over the curated
    # (high-quality) part of the catalog — only words that have at least one
    # example and a non-empty IPA. Falls back to the full catalog if needed.
    import hashlib as _hl
    pool = (Word.query
            .filter(Word.is_thesaurus_phrase == False,  # noqa
                    Word.phonetic_uk != '')
            .order_by(Word.id).all())
    if not pool:
        pool = Word.query.filter(Word.is_thesaurus_phrase == False  # noqa
                                 ).order_by(Word.id).all()
    if not pool:
        abort(404)
    idx = int(_hl.md5(target_date.isoformat().encode()).hexdigest()[:8], 16) % len(pool)
    wotd = pool[idx]

    # Build a 7-day archive list for the side panel.
    from datetime import timedelta as _td
    archive = []
    for back in range(1, 8):
        d = target_date - _td(days=back)
        i = int(_hl.md5(d.isoformat().encode()).hexdigest()[:8], 16) % len(pool)
        archive.append({'date': d, 'word': pool[i]})

    return render_template('word_of_day.html', wotd=wotd,
                           target_date=target_date, archive=archive)


# --- Word Lists (themed vocabulary collections) -----------------------------
# Real Cambridge ships curated word lists (Business English, Academic, IELTS,
# Travel, …). We back them with a simple deterministic SQL slice over the
# catalog so agents have something concrete to enumerate.

WORDLIST_DEFS = [
    {'slug': 'business-english', 'title': 'Business English Essentials',
     'category': 'Business', 'level': 'B2',
     'description': 'Vocabulary for meetings, emails, and negotiations.',
     'seed_words': ['innovate', 'sustainability', 'cryptocurrency',
                    'concatenate', 'mitigate', 'impeccable',
                    'pandemic', 'resilience']},
    {'slug': 'academic-vocabulary', 'title': 'Academic Vocabulary',
     'category': 'Academic', 'level': 'C1',
     'description': 'High-frequency words used in academic writing.',
     'seed_words': ['ubiquitous', 'ameliorate', 'altruism', 'quintessential',
                    'meticulous', 'ephemeral', 'gestalt', 'serendipity']},
    {'slug': 'ielts-band-7', 'title': 'IELTS Band 7+ Vocabulary',
     'category': 'IELTS', 'level': 'C1',
     'description': 'Advanced lexis to push your IELTS Writing band score.',
     'seed_words': ['zeitgeist', 'procrastination', 'euphoria',
                    'ephemeral', 'altruism', 'unblemished',
                    'quintessential', 'meticulous']},
    {'slug': 'travel-and-tourism', 'title': 'Travel & Tourism',
     'category': 'Everyday', 'level': 'B1',
     'description': 'Words for planning trips, transport, and accommodation.',
     'seed_words': ['serendipity', 'nostalgia', 'solitude', 'harmony']},
    {'slug': 'feelings-and-emotions', 'title': 'Feelings & Emotions',
     'category': 'Everyday', 'level': 'A2',
     'description': 'Talk about how you feel in English.',
     'seed_words': ['euphoria', 'nostalgia', 'solitude', 'harmony',
                    'reverie', 'resilience']},
    {'slug': 'technology-and-internet', 'title': 'Technology & the Internet',
     'category': 'Tech', 'level': 'B2',
     'description': 'Words for talking about tech, software, and the web.',
     'seed_words': ['cryptocurrency', 'concatenate', 'innovate', 'pandemic']},
]


def _resolve_wordlist(wl):
    """Resolve a wordlist definition's seed slugs into Word rows."""
    rows = []
    for slug in wl['seed_words']:
        w = Word.query.filter_by(slug=slug, is_thesaurus_phrase=False).first()
        if w:
            rows.append(w)
    return rows


@app.route('/wordlists')
@app.route('/wordlists/')
def wordlists_index():
    return render_template('wordlists_index.html', wordlists=WORDLIST_DEFS)


@app.route('/wordlists/<slug>')
def wordlist_detail(slug):
    wl = next((w for w in WORDLIST_DEFS if w['slug'] == slug), None)
    if not wl:
        abort(404)
    words = _resolve_wordlist(wl)
    return render_template('wordlist_detail.html', wl=wl, words=words)


# --- Static informational pages --------------------------------------------
# Real Cambridge has /about/dictionary, /help, /blog/ — wire static templates.

BLOG_POSTS = [
    {'slug': 'new-words-spring-2026', 'date': '2026-03-12',
     'title': 'New words: 12 March 2026',
     'category': 'New words',
     'excerpt': ('A weekly round-up of words that have entered popular usage. '
                 'This week: solarpunk, vibe-coding, climate-doomerism.')},
    {'slug': 'how-to-use-cambridge-dictionary', 'date': '2026-02-28',
     'title': 'How to use the Cambridge Dictionary like a pro',
     'category': 'Learning tips',
     'excerpt': ('Five less-obvious features of cambridge.org/dictionary that '
                 'every advanced learner should know about.')},
    {'slug': 'ielts-vocabulary-tips', 'date': '2026-02-10',
     'title': '7 vocabulary tactics to push your IELTS Writing band',
     'category': 'IELTS',
     'excerpt': ('From topic-specific collocations to register-aware '
                 'paraphrase, here are the moves examiners reward.')},
    {'slug': 'why-pronunciation-matters', 'date': '2026-01-22',
     'title': 'Why pronunciation matters more than you think',
     'category': 'Pronunciation',
     'excerpt': ('Even small phonetic errors can carry meaning. We break '
                 'down the four UK-vs-US sound shifts learners get wrong most.')},
    {'slug': 'cambridge-dictionary-2025-word-of-year',
     'date': '2025-11-30',
     'title': "Cambridge Dictionary's 2025 Word of the Year",
     'category': 'Word of the year',
     'excerpt': ('A look back at the word that defined 2025 and the '
                 'shortlist that nearly took the title.')},
    {'slug': 'grammar-myths-busted', 'date': '2025-10-14',
     'title': 'Six grammar myths your English teacher told you',
     'category': 'Grammar',
     'excerpt': ("'Never start a sentence with And.' '\"You\" is always "
                 "singular.' We bust six tenacious grammar myths with corpus "
                 "evidence.")},
]


@app.route('/blog')
@app.route('/blog/')
def blog_index():
    return render_template('blog_index.html', posts=BLOG_POSTS)


@app.route('/blog/<slug>')
def blog_post(slug):
    post = next((p for p in BLOG_POSTS if p['slug'] == slug), None)
    if not post:
        abort(404)
    return render_template('blog_post.html', post=post, posts=BLOG_POSTS)


@app.route('/about')
@app.route('/about/')
@app.route('/about/dictionary')
def about():
    return render_template('about.html')


@app.route('/help')
@app.route('/help/')
def help_page():
    return render_template('help.html')


# --- Language switcher ---

@app.route('/set-language', methods=['POST'])
@csrf.exempt
def set_language():
    lang = request.form.get('lang', 'English (UK)')
    if lang in LANGUAGES:
        session['lang'] = lang
    return redirect(request.referrer or url_for('index'))


# --- Auth ---

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = RegisterForm()
    if form.validate_on_submit():
        if User.query.filter_by(email=form.email.data).first():
            flash('Email already registered.', 'danger')
            return render_template('register.html', form=form)
        user = User(name=form.name.data, email=form.email.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        login_user(user)
        flash('Account created! Welcome to Cambridge Dictionary.', 'success')
        return redirect(url_for('index'))
    return render_template('register.html', form=form)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and user.check_password(form.password.data):
            login_user(user)
            next_page = request.args.get('next')
            return redirect(next_page or url_for('index'))
        flash('Invalid email or password.', 'danger')
    return render_template('login.html', form=form)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))


# --- Account ---

@app.route('/account')
@login_required
def account():
    saved = SavedWord.query.filter_by(user_id=current_user.id)\
        .order_by(SavedWord.created_at.desc()).all()
    history = SearchHistory.query.filter_by(user_id=current_user.id)\
        .order_by(SearchHistory.created_at.desc()).limit(20).all()
    return render_template('account.html', saved=saved, history=history)


@app.route('/account/edit', methods=['GET', 'POST'])
@login_required
def account_edit():
    form = AccountEditForm(obj=current_user)
    if form.validate_on_submit():
        if (form.email.data != current_user.email and
                User.query.filter_by(email=form.email.data).first()):
            flash('Email already in use.', 'danger')
            return render_template('account_edit.html', form=form)
        current_user.name = form.name.data
        current_user.email = form.email.data
        db.session.commit()
        flash('Profile updated.', 'success')
        return redirect(url_for('account'))
    return render_template('account_edit.html', form=form)


@app.route('/account/password', methods=['GET', 'POST'])
@login_required
def change_password():
    form = ChangePasswordForm()
    if form.validate_on_submit():
        if not current_user.check_password(form.current_password.data):
            flash('Current password is incorrect.', 'danger')
            return render_template('change_password.html', form=form)
        current_user.set_password(form.new_password.data)
        db.session.commit()
        flash('Password changed successfully.', 'success')
        return redirect(url_for('account'))
    return render_template('change_password.html', form=form)


# --- Saved words API (AJAX, kept for backward compat) ---

@app.route('/api/save-word', methods=['POST'])
@login_required
@csrf.exempt
def save_word():
    data = request.get_json() or {}
    word_id = data.get('word_id')
    if not word_id:
        return jsonify({'success': False})
    word = db.session.get(Word, word_id)
    if not word:
        return jsonify({'success': False})
    existing = SavedWord.query.filter_by(
        user_id=current_user.id, word_id=word_id).first()
    if existing:
        db.session.delete(existing)
        db.session.commit()
        return jsonify({'success': True, 'saved': False})
    sw = SavedWord(user_id=current_user.id, word_id=word_id)
    db.session.add(sw)
    db.session.commit()
    return jsonify({'success': True, 'saved': True})


# --- Form-POST save-word route (browser-agent friendly, no AJAX needed) ---

@app.route('/words/save/<int:word_id>', methods=['POST'])
@login_required
def save_word_form(word_id):
    """Toggle save/unsave a word via plain HTML form POST. Redirects back."""
    word = db.session.get(Word, word_id)
    if not word:
        flash('Word not found.', 'danger')
        return redirect(url_for('index'))
    existing = SavedWord.query.filter_by(
        user_id=current_user.id, word_id=word_id).first()
    if existing:
        db.session.delete(existing)
        db.session.commit()
        flash(f'"{word.headword}" removed from saved words.', 'info')
    else:
        sw = SavedWord(user_id=current_user.id, word_id=word_id)
        db.session.add(sw)
        db.session.commit()
        flash(f'"{word.headword}" saved to your word list.', 'success')
    return redirect(url_for('word_detail', slug=word.slug))


@app.route('/saved-words/remove/<int:sw_id>', methods=['POST'])
@login_required
def remove_saved_word(sw_id):
    sw = SavedWord.query.filter_by(id=sw_id, user_id=current_user.id).first_or_404()
    db.session.delete(sw)
    db.session.commit()
    flash('Word removed from saved list.', 'info')
    return redirect(url_for('account'))


# ---------------------------------------------------------------------------
# R5: Flashcards study mode + accessibility settings + recently-viewed feed
# ---------------------------------------------------------------------------

@app.route('/flashcards')
@app.route('/flashcards/')
def flashcards():
    """Swipe-to-flashcard vocab study mode.

    Picks a deterministic 20-card deck so the same URL always shows the same
    cards (snapshot-friendly for tasks). Optional ``?level=B2`` filters by
    CEFR band, ``?slug=foo`` jumps to a specific card.
    """
    level = (request.args.get('level') or '').upper()
    focus_slug = (request.args.get('slug') or '').strip()

    base_q = Word.query.filter(Word.is_thesaurus_phrase == False)  # noqa
    if level in ('A1', 'A2', 'B1', 'B2', 'C1', 'C2'):
        base_q = base_q.filter(Word.level == level)

    # Deterministic ordering: by id ASC so the deck is stable.
    cards_q = base_q.order_by(Word.id.asc())

    deck = cards_q.limit(60).all()
    # If a specific slug was requested and isn't in the first 60, look it up
    # and prepend it so it's the first card shown.
    if focus_slug:
        focus = Word.query.filter_by(slug=focus_slug).first()
        if focus and focus not in deck:
            deck = [focus] + deck[:59]

    cards = []
    for w in deck[:20]:
        defs = w.get_definitions()
        cards.append({
            'slug': w.slug,
            'headword': w.headword,
            'pos': w.pos,
            'level': w.level,
            'ipa': w.phonetic_uk or w.pronunciation_ipa,
            'definition': (defs[0].get('definition') if defs else ''),
            'example': ((defs[0].get('examples') or [''])[0] if defs else ''),
            'audio_uk': w.audio_uk_path,
            'audio_us': w.audio_us_path,
        })
    return render_template('flashcards.html', cards=cards, level=level,
                           focus_slug=focus_slug)


@app.route('/settings/accessibility', methods=['GET', 'POST'])
def settings_accessibility():
    """Server-rendered accessibility settings page.

    Persists three preferences in cookies (no DB column added — keeps the
    seed DB byte-id stable):
      - ``a11y_font``  ``default`` | ``dyslexic``
      - ``a11y_palette`` ``default`` | ``cb-safe``  (color-blind safe CEFR)
      - ``a11y_ipa_focus`` ``0`` | ``1``  (keyboard-focusable IPA tooltips)
    """
    if request.method == 'POST':
        font = request.form.get('font', 'default')
        palette = request.form.get('palette', 'default')
        ipa_focus = '1' if request.form.get('ipa_focus') else '0'
        resp = redirect(url_for('settings_accessibility'))
        # 1-year cookie so the toggle persists across reset/seeds.
        max_age = 60 * 60 * 24 * 365
        resp.set_cookie('a11y_font', font, max_age=max_age, samesite='Lax')
        resp.set_cookie('a11y_palette', palette, max_age=max_age, samesite='Lax')
        resp.set_cookie('a11y_ipa_focus', ipa_focus, max_age=max_age, samesite='Lax')
        flash('Accessibility preferences saved.', 'success')
        return resp
    return render_template('settings_accessibility.html')


@app.route('/api/recently-viewed', methods=['POST'])
@csrf.exempt
def api_recently_viewed():
    """Lightweight echo endpoint — the client maintains the actual list in
    localStorage; this endpoint exists so server-rendered badges can read
    the latest-known count via a session cookie roundtrip without forcing a
    schema change. Body: ``{"count": N}``. Stores N in the session and
    returns it back.
    """
    data = request.get_json(silent=True) or {}
    try:
        n = max(0, min(int(data.get('count', 0)), 999))
    except (TypeError, ValueError):
        n = 0
    session['recently_viewed_count'] = n
    return jsonify({'ok': True, 'count': n})


@app.context_processor
def inject_a11y_prefs():
    """Surface accessibility cookie state + recently-viewed count to all
    templates so base.html can render the body class + the navbar badge
    without per-route plumbing."""
    return {
        'a11y_font':    request.cookies.get('a11y_font', 'default'),
        'a11y_palette': request.cookies.get('a11y_palette', 'default'),
        'a11y_ipa_focus': request.cookies.get('a11y_ipa_focus', '0'),
        'recently_viewed_count': session.get('recently_viewed_count', 0),
    }


# --- Error handlers ---

@app.errorhandler(404)
def not_found(e):
    return render_template('404.html'), 404


@app.errorhandler(500)
def server_error(e):
    return render_template('500.html'), 500


# ---------------------------------------------------------------------------
# R3 sub-pages (deeper dictionary surface)
# ---------------------------------------------------------------------------
# These routes were added in R3 to give agents real sub-pages that don't yet
# exist in R2: shallow grammar slugs, language-specific translate landing
# pages, a CEFR-style level test, a "word class of the day" trivia page, and
# a thesaurus alias accepting a bare word slug. All read-only, deterministic.

# CEFR levels — used by /level-test and surfaced as colour blocks in
# templates. Order matters (display + scoring).
CEFR_LEVELS_ORDERED = ['A1', 'A2', 'B1', 'B2', 'C1', 'C2']

# Word classes for /word-class-of-the-day rotation. Matches the four POS
# values we generate in seed (noun / verb / adjective / adverb) plus the
# less common phrase / preposition slots we can introduce via SQL filters.
WORD_CLASSES = [
    {'slug': 'noun', 'title': 'Noun',
     'description': 'A word that names a person, place, thing, or idea.',
     'pos_match': 'noun'},
    {'slug': 'verb', 'title': 'Verb',
     'description': 'A word that expresses an action, occurrence, or state of being.',
     'pos_match': 'verb'},
    {'slug': 'adjective', 'title': 'Adjective',
     'description': 'A word that modifies or describes a noun.',
     'pos_match': 'adjective'},
    {'slug': 'adverb', 'title': 'Adverb',
     'description': 'A word that modifies a verb, adjective, or another adverb.',
     'pos_match': 'adverb'},
    {'slug': 'phrase', 'title': 'Phrase',
     'description': 'A group of words functioning as a unit within a sentence.',
     'pos_match': 'phrase'},
]


@app.route('/grammar/<slug>')
def grammar_topic_short(slug):
    """Shallow alias of /grammar/british-grammar/<slug> — redirects to canonical
    URL so saved Cambridge bookmarks resolve."""
    if GrammarTopic.query.filter_by(slug=slug).first():
        return redirect(url_for('grammar_topic', slug=slug), code=301)
    abort(404)


@app.route('/translate/EN/<lang>')
def translate_landing(lang):
    """Per-language translate landing page. Shows the language picker
    pre-set to <lang> and surfaces a short featured list of words that
    have a translation into that language."""
    lang_key_map = {
        'french': 'french', 'fr': 'french', 'francais': 'french',
        'spanish': 'spanish', 'es': 'spanish', 'espanol': 'spanish',
        'german': 'german', 'de': 'german', 'deutsch': 'german',
        'chinese': 'chinese', 'zh': 'chinese', 'mandarin': 'chinese',
        'italian': 'italian', 'it': 'italian',
        'portuguese': 'portuguese', 'pt': 'portuguese',
        'japanese': 'japanese', 'ja': 'japanese',
    }
    lang_lower = lang.lower()
    canonical = lang_key_map.get(lang_lower)
    if canonical is None:
        abort(404)

    display_name = {
        'french': 'French', 'spanish': 'Spanish', 'german': 'German',
        'chinese': 'Chinese', 'italian': 'Italian',
        'portuguese': 'Portuguese', 'japanese': 'Japanese',
    }[canonical]

    # Pre-pick 10 sample words that DO have a translation into this
    # language. We can't easily LIKE inside a JSON column generically, so
    # do a python-side scan over a bounded sample.
    samples = []
    candidates = (Word.query
                  .filter(Word.is_thesaurus_phrase == False,  # noqa
                          Word.translations_json != '{}')
                  .order_by(Word.id).limit(400).all())
    for w in candidates:
        if len(samples) >= 10:
            break
        tr = w.get_translations()
        if any(k.lower() == canonical for k in tr.keys()):
            samples.append(w)

    return render_template('translate_landing.html', lang=canonical,
                           lang_display=display_name, samples=samples)


@app.route('/level-test')
@app.route('/level-test/')
def level_test():
    """Cambridge-style placement test landing. Lists CEFR levels with an
    indicative quiz for each. Read-only — we don't actually score input.

    Real Cambridge has an interactive 25-question test; we just surface
    the structure so agents can navigate to a per-level quiz."""
    # Find one quiz per CEFR level (Cambridge Exam quizzes generated in R3)
    levels = []
    for lvl in CEFR_LEVELS_ORDERED:
        # Match either category 'Cambridge Exam <lvl>' or title prefix.
        quiz = (Quiz.query
                .filter(or_(Quiz.category == f'Cambridge Exam {lvl}',
                            Quiz.title.like(f'Cambridge Vocabulary {lvl}%')))
                .first())
        word_count = Word.query.filter_by(level=lvl,
                                          is_thesaurus_phrase=False).count()
        levels.append({
            'cefr': lvl,
            'quiz': quiz,
            'word_count': word_count,
            'description': {
                'A1': 'Beginner — basic everyday expressions.',
                'A2': 'Elementary — describing your background and immediate needs.',
                'B1': 'Intermediate — main points on familiar topics.',
                'B2': 'Upper-intermediate — fluent interaction with native speakers.',
                'C1': 'Advanced — flexible and effective use for social and academic purposes.',
                'C2': 'Proficient — virtually everything heard or read.',
            }[lvl],
        })
    return render_template('level_test.html', levels=levels)


@app.route('/word-class-of-the-day')
@app.route('/word-class-of-the-day/')
def word_class_of_the_day():
    """Trivia page rotating one word class per day. Deterministic on
    MIRROR_REFERENCE_DATE so reruns agree."""
    import hashlib as _hl
    target_date = MIRROR_REFERENCE_DATE.date()
    idx = int(_hl.md5(target_date.isoformat().encode()).hexdigest()[:8],
              16) % len(WORD_CLASSES)
    today_class = WORD_CLASSES[idx]
    sample_words = (Word.query
                    .filter(Word.is_thesaurus_phrase == False,  # noqa
                            Word.pos == today_class['pos_match'],
                            Word.phonetic_uk != '')
                    .order_by(Word.id).limit(8).all())
    return render_template('word_class.html', wc=today_class,
                           samples=sample_words, target_date=target_date,
                           all_classes=WORD_CLASSES)


@app.route('/thesaurus/<slug>')
def thesaurus_word_alias(slug):
    """Bare /thesaurus/<word> alias for Cambridge URLs. Redirects to the
    canonical /thesaurus/english/<word> handler so prior bookmarks keep
    working."""
    # Avoid colliding with the /thesaurus/articles/ and /thesaurus/english/
    # prefixes — those have their own routes registered earlier and Flask
    # matches them first by virtue of being more specific.
    if slug in {'english', 'articles'}:
        abort(404)
    return redirect(url_for('thesaurus_entry', phrase=slug), code=301)


# ---------------------------------------------------------------------------
# R4 sub-pages: deep dictionary surface
# ---------------------------------------------------------------------------
# Real Cambridge has dedicated landing pages for etymology, collocation,
# pronunciation, and a word-of-the-day archive. R4 wires these as
# read-only deterministic surfaces over the new metadata columns on Word
# and the MistakeCorner table.

@app.route('/etymology')
@app.route('/etymology/')
def etymology_index():
    """List the words that have an etymology paragraph populated. Real
    Cambridge groups by root language; we surface a flat list ordered by
    headword for stable scraping. Paginated to keep page weight bounded."""
    page = max(1, int(request.args.get('page', 1)))
    per = 50
    base = (Word.query
            .filter(Word.is_thesaurus_phrase == False,  # noqa
                    Word.etymology != ''))
    total = base.count()
    words = (base.order_by(Word.headword.asc())
             .offset((page - 1) * per).limit(per).all())
    return render_template('etymology_index.html', words=words,
                           page=page, per=per, total=total)


@app.route('/etymology/<slug>')
def etymology_detail(slug):
    word = Word.query.filter_by(slug=slug).first_or_404()
    if not word.etymology:
        abort(404)
    return render_template('etymology.html', word=word)


@app.route('/collocation')
@app.route('/collocation/')
def collocation_index():
    """List words with curated collocation entries."""
    page = max(1, int(request.args.get('page', 1)))
    per = 50
    base = (Word.query
            .filter(Word.is_thesaurus_phrase == False,  # noqa
                    Word.collocations_json != '[]',
                    Word.collocations_json != ''))
    total = base.count()
    words = (base.order_by(Word.headword.asc())
             .offset((page - 1) * per).limit(per).all())
    return render_template('collocation_index.html', words=words,
                           page=page, per=per, total=total)


@app.route('/collocation/<slug>')
def collocation_detail(slug):
    word = Word.query.filter_by(slug=slug).first_or_404()
    colls = word.get_collocations()
    if not colls:
        abort(404)
    return render_template('collocation.html', word=word, collocations=colls)


@app.route('/mistake')
@app.route('/mistake/')
def mistake_index():
    topics = MistakeCorner.query.order_by(MistakeCorner.sort_order).all()
    # Group by category for the side-nav rendering.
    categories = {}
    for t in topics:
        categories.setdefault(t.category or 'Other', []).append(t)
    return render_template('mistake_index.html', topics=topics,
                           categories=categories)


@app.route('/mistake/<slug>')
def mistake_detail(slug):
    topic = MistakeCorner.query.filter_by(slug=slug).first_or_404()
    examples = topic.get_examples()
    # Adjacent for prev/next nav.
    all_topics = MistakeCorner.query.order_by(MistakeCorner.sort_order).all()
    idx = next((i for i, t in enumerate(all_topics) if t.id == topic.id), 0)
    prev_t = all_topics[idx - 1] if idx > 0 else None
    next_t = all_topics[idx + 1] if idx < len(all_topics) - 1 else None
    return render_template('mistake_detail.html', topic=topic,
                           examples=examples, prev_topic=prev_t,
                           next_topic=next_t)


@app.route('/pronunciation/<slug>')
def pronunciation_detail(slug):
    """Side-by-side UK/US pronunciation page. Read-only — surfaces both
    IPA values, audio buttons, and a syllable count derived from the
    headword (deterministic)."""
    word = Word.query.filter_by(slug=slug).first_or_404()
    # Crude syllable estimate: count vowel groups.
    head = (word.headword or '').lower()
    syllables = max(1, len(re.findall(r'[aeiouy]+', head)))
    return render_template('pronunciation.html', word=word,
                           syllables=syllables)


@app.route('/word-of-the-day/archive')
@app.route('/word-of-the-day/archive/')
def wotd_archive_landing():
    # Landing — list the years we have archives for.
    years = [2024, 2025, 2026]
    return render_template('wotd_archive.html', year=None, entries=[],
                           years=years)


@app.route('/word-of-the-day/archive/<int:year>')
def wotd_archive_year(year):
    """Render the deterministic Word-of-the-Day picks for an entire year.

    Uses the same hash-of-date logic as ``word_of_the_day`` so the archive
    is always consistent with the live WOTD URL."""
    if year < 2020 or year > 2030:
        abort(404)
    import hashlib as _hl
    from datetime import date as _date, timedelta as _td
    pool = (Word.query
            .filter(Word.is_thesaurus_phrase == False,  # noqa
                    Word.phonetic_uk != '')
            .order_by(Word.id).all())
    if not pool:
        pool = Word.query.filter(Word.is_thesaurus_phrase == False  # noqa
                                 ).order_by(Word.id).all()
    if not pool:
        abort(404)
    # Walk every calendar day of the year. Bound at MIRROR_REFERENCE_DATE so
    # future-dated days don't appear (matches what users would see "today").
    start = _date(year, 1, 1)
    end = _date(year, 12, 31)
    today = MIRROR_REFERENCE_DATE.date()
    if end > today:
        end = today
    entries = []
    if start <= end:
        d = start
        while d <= end:
            idx = int(_hl.md5(d.isoformat().encode()).hexdigest()[:8], 16) % len(pool)
            entries.append({'date': d, 'word': pool[idx]})
            d += _td(days=1)
    years = [2024, 2025, 2026]
    return render_template('wotd_archive.html', year=year, entries=entries,
                           years=years)


# ---------------------------------------------------------------------------
# Seed data
# ---------------------------------------------------------------------------

def _j(obj):
    return json.dumps(obj, ensure_ascii=False)


WORDS_DATA = [
    # -------------------------------------------------------------------------
    # Core words from tasks
    # -------------------------------------------------------------------------
    {
        'headword': 'sustainability',
        'slug': 'sustainability',
        'pos': 'noun',
        'guide_word': 'ability to continue at a certain level',
        'phonetic_uk': '/səˌsteɪnəˈbɪlɪti/',
        'phonetic_us': '/səˌsteɪnəˈbɪlɪti/',
        'level': 'C1',
        'definitions': [
            {
                'sense_num': 1,
                'grammar_note': '[U]',
                'definition': 'The quality of being able to continue over a period of time.',
                'examples': [
                    'The long-term sustainability of the project is in doubt.',
                    'We need to ensure the sustainability of our natural resources.',
                ],
                'register': '',
            },
            {
                'sense_num': 2,
                'grammar_note': '[U]',
                'definition': 'The quality of causing little or no damage to the environment and therefore able to continue for a long time.',
                'examples': [
                    'The company has made a commitment to environmental sustainability.',
                    'Sustainability is at the heart of our business strategy.',
                ],
                'register': '',
            },
        ],
        'translations': {
            'chinese': {'text': '可持续性', 'provider': 'Microsoft'},
            'french': {'text': 'durabilité', 'provider': 'Microsoft'},
            'spanish': {'text': 'sostenibilidad', 'provider': 'Microsoft'},
            'german': {'text': 'Nachhaltigkeit', 'provider': 'Microsoft'},
        },
        'related': [],
        'synonyms': [],
    },
    {
        'headword': 'serendipity',
        'slug': 'serendipity',
        'pos': 'noun',
        'guide_word': 'finding good things by accident',
        'phonetic_uk': '/ˌserənˈdɪpɪti/',
        'phonetic_us': '/ˌserənˈdɪpɪti/',
        'level': 'C2',
        'definitions': [
            {
                'sense_num': 1,
                'grammar_note': '[U]',
                'definition': 'The fact of finding interesting or valuable things by chance.',
                'examples': [
                    'Many scientific discoveries happen through serendipity.',
                    'It was sheer serendipity that led her to the job of her dreams.',
                ],
                'register': '',
            },
        ],
        'translations': {
            'chinese': {'text': '意外惊喜', 'provider': 'Microsoft'},
            'french': {'text': 'sérendipité', 'provider': 'Microsoft'},
            'spanish': {'text': 'serendipia', 'provider': 'Microsoft'},
        },
        'related': [],
        'synonyms': [],
    },
    {
        'headword': 'ubiquitous',
        'slug': 'ubiquitous',
        'pos': 'adjective',
        'guide_word': 'present everywhere',
        'phonetic_uk': '/juːˈbɪkwɪtəs/',
        'phonetic_us': '/juːˈbɪkwɪtəs/',
        'level': 'C2',
        'definitions': [
            {
                'sense_num': 1,
                'grammar_note': '',
                'definition': 'Seeming to appear everywhere at the same time.',
                'examples': [
                    'The ubiquitous mobile phone has changed the way we communicate.',
                    'Coffee shops are ubiquitous in this city.',
                ],
                'register': 'formal',
            },
        ],
        'translations': {
            'chinese': {'text': '无处不在的', 'provider': 'Microsoft'},
            'french': {'text': 'omniprésent', 'provider': 'Microsoft'},
        },
        'related': [],
        'synonyms': [],
    },
    {
        'headword': 'zeitgeist',
        'slug': 'zeitgeist',
        'pos': 'noun',
        'guide_word': 'spirit of the times',
        'phonetic_uk': '/ˈzaɪtɡaɪst/',
        'phonetic_us': '/ˈzaɪtɡaɪst/',
        'level': 'C2',
        'definitions': [
            {
                'sense_num': 1,
                'grammar_note': '[S, U]',
                'definition': 'The general set of ideas, beliefs, feelings, and moral values that is characteristic of a particular period in history.',
                'examples': [
                    'The zeitgeist of the 1960s was one of social revolution and change.',
                    "Her novel perfectly captures the zeitgeist of contemporary urban life.",
                ],
                'register': 'formal',
            },
        ],
        'translations': {
            'chinese': {'text': '时代精神', 'provider': 'Microsoft'},
            'french': {'text': 'esprit du temps', 'provider': 'Microsoft'},
            'german': {'text': 'Zeitgeist', 'provider': 'Microsoft'},
        },
        'related': [],
        'synonyms': [],
    },
    {
        'headword': 'innovate',
        'slug': 'innovate',
        'pos': 'verb',
        'guide_word': 'introduce new methods',
        'phonetic_uk': '/ˈɪnəveɪt/',
        'phonetic_us': '/ˈɪnəveɪt/',
        'level': 'B2',
        'definitions': [
            {
                'sense_num': 1,
                'grammar_note': '[I, T]',
                'definition': 'To introduce changes and new ideas.',
                'examples': [
                    'The company must continue to innovate if it is to survive.',
                    'We need to innovate to stay ahead of our competitors.',
                ],
                'register': '',
            },
        ],
        'translations': {
            'chinese': {'text': '创新', 'provider': 'Microsoft'},
            'french': {'text': 'innover', 'provider': 'Microsoft'},
        },
        'related': [],
        'synonyms': [],
    },
    {
        'headword': 'procrastination',
        'slug': 'procrastination',
        'pos': 'noun',
        'guide_word': 'delay doing things',
        'phonetic_uk': '/prəˌkræstɪˈneɪʃən/',
        'phonetic_us': '/proʊˌkræstɪˈneɪʃən/',
        'level': 'C1',
        'definitions': [
            {
                'sense_num': 1,
                'grammar_note': '[U]',
                'definition': 'The act of delaying something that must be done, often because it is unpleasant or boring.',
                'examples': [
                    'Procrastination is one of the main reasons students fail to complete their assignments on time.',
                    "His procrastination meant that the deadline passed without the work being done.",
                ],
                'register': '',
            },
        ],
        'translations': {
            'chinese': {'text': '拖延', 'provider': 'Microsoft'},
            'french': {'text': 'procrastination', 'provider': 'Microsoft'},
        },
        'related': [],
        'synonyms': [],
    },
    {
        'headword': 'gestalt',
        'slug': 'gestalt',
        'pos': 'noun',
        'guide_word': 'unified whole',
        'phonetic_uk': '/ɡəˈʃtælt/',
        'phonetic_us': '/ɡəˈʃtɑːlt/',
        'level': 'C2',
        'definitions': [
            {
                'sense_num': 1,
                'grammar_note': '[C, U]',
                'definition': 'A shape, structure, or whole that has qualities that cannot be seen by separately looking at its individual parts.',
                'examples': [
                    'Gestalt psychology argues that the whole is more than the sum of its parts.',
                    'The architect approached the design with a focus on gestalt.',
                ],
                'register': 'specialized',
            },
        ],
        'translations': {
            'chinese': {'text': '完形', 'provider': 'Microsoft'},
            'german': {'text': 'Gestalt', 'provider': 'Microsoft'},
        },
        'related': [],
        'synonyms': [],
    },
    {
        'headword': 'dog',
        'slug': 'dog',
        'pos': 'noun',
        'guide_word': 'animal / unpleasant person / follow',
        'phonetic_uk': '/dɒɡ/',
        'phonetic_us': '/dɑːɡ/',
        'level': 'A1',
        'definitions': [
            {
                'sense_num': 1,
                'grammar_note': '[C]',
                'definition': 'A common animal with four legs, kept as a pet or trained to do special jobs.',
                'examples': [
                    'We have two dogs and a cat.',
                    'She walked her dog every morning before work.',
                ],
                'register': '',
            },
            {
                'sense_num': 2,
                'grammar_note': '[C]',
                'definition': 'An unattractive or unpleasant person.',
                'examples': [
                    "Don't be such a dog — help us out!",
                ],
                'register': 'informal, offensive',
            },
            {
                'sense_num': 3,
                'grammar_note': '[T]',
                'definition': 'To follow someone closely and persistently.',
                'examples': [
                    'Bad luck dogged her throughout her career.',
                    'The scandal has dogged the company for years.',
                ],
                'register': '',
            },
        ],
        'translations': {
            'chinese': {'text': '狗', 'provider': 'Microsoft'},
            'french': {'text': 'chien', 'provider': 'Microsoft'},
        },
        'related': [],
        'synonyms': [],
    },
    {
        'headword': 'euphoria',
        'slug': 'euphoria',
        'pos': 'noun',
        'guide_word': 'extreme happiness',
        'phonetic_uk': '/juːˈfɔːriə/',
        'phonetic_us': '/juːˈfɔːriə/',
        'level': 'C2',
        'definitions': [
            {
                'sense_num': 1,
                'grammar_note': '[U]',
                'definition': 'Extreme happiness, sometimes more than is reasonable in a particular situation.',
                'examples': [
                    'There was a sense of euphoria in the crowd after the winning goal.',
                    'The euphoria of victory quickly gave way to exhaustion.',
                ],
                'register': '',
            },
        ],
        'translations': {
            'chinese': {'text': '欣快感', 'provider': 'Microsoft'},
            'french': {'text': 'euphorie', 'provider': 'Microsoft'},
        },
        'related': [
            {'type': 'word', 'text': 'euphoric', 'definition': 'extremely happy and excited'},
            {'type': 'phrase', 'text': 'sense of euphoria', 'definition': 'a feeling of extreme happiness'},
            {'type': 'idiom', 'text': 'on cloud nine', 'definition': 'extremely happy and excited'},
        ],
        'synonyms': ['elation', 'ecstasy', 'exhilaration', 'joy', 'bliss',
                     'rapture', 'jubilation', 'exultation', 'delight', 'glee'],
    },
    {
        'headword': 'impeccable',
        'slug': 'impeccable',
        'pos': 'adjective',
        'guide_word': 'perfect, with no faults',
        'phonetic_uk': '/ɪmˈpekəbəl/',
        'phonetic_us': '/ɪmˈpekəbəl/',
        'level': 'C2',
        'definitions': [
            {
                'sense_num': 1,
                'grammar_note': '',
                'definition': 'Perfect, with no faults or problems.',
                'examples': [
                    'He had impeccable manners and always knew the right thing to say.',
                    'Her dress sense is impeccable.',
                ],
                'register': '',
            },
        ],
        'translations': {
            'chinese': {'text': '无可挑剔的', 'provider': 'Microsoft'},
            'french': {'text': 'irréprochable', 'provider': 'Microsoft'},
        },
        'related': [],
        'synonyms': [],
    },
    {
        'headword': 'ameliorate',
        'slug': 'ameliorate',
        'pos': 'verb',
        'guide_word': 'make something bad less severe',
        'phonetic_uk': '/əˈmiːliəreɪt/',
        'phonetic_us': '/əˈmiːliəreɪt/',
        'level': 'C2',
        'definitions': [
            {
                'sense_num': 1,
                'grammar_note': '[T]',
                'definition': 'To make something bad or unsatisfactory better.',
                'examples': [
                    'The new policy was designed to ameliorate the effects of poverty.',
                    'Music can ameliorate the pain of grief.',
                ],
                'register': 'formal',
            },
        ],
        'translations': {
            'chinese': {'text': '改善', 'provider': 'Microsoft'},
            'french': {'text': 'améliorer', 'provider': 'Microsoft'},
        },
        'related': [],
        'synonyms': [],
    },
    {
        'headword': 'resilience',
        'slug': 'resilience',
        'pos': 'noun',
        'guide_word': 'ability to recover from difficulties',
        'phonetic_uk': '/rɪˈzɪliəns/',
        'phonetic_us': '/rɪˈzɪliəns/',
        'level': 'C1',
        'definitions': [
            {
                'sense_num': 1,
                'grammar_note': '[U]',
                'definition': 'The ability to be happy, successful, etc. again after something difficult or bad has happened.',
                'examples': [
                    'She showed remarkable resilience in the face of adversity.',
                    "The community's resilience was tested by the floods.",
                ],
                'register': '',
            },
            {
                'sense_num': 2,
                'grammar_note': '[U]',
                'definition': 'The ability of a substance to return to its original form after being bent, stretched, or pressed.',
                'examples': [
                    'The resilience of rubber makes it ideal for this purpose.',
                ],
                'register': 'technical',
            },
        ],
        'translations': {
            'chinese': {'text': '韧性', 'provider': 'Microsoft'},
            'french': {'text': 'résilience', 'provider': 'Microsoft'},
        },
        'related': [],
        'synonyms': [],
    },
    {
        'headword': 'concatenate',
        'slug': 'concatenate',
        'pos': 'verb',
        'guide_word': 'link things together in a series',
        'phonetic_uk': '/kənˈkætɪneɪt/',
        'phonetic_us': '/kənˈkætɪneɪt/',
        'level': 'C2',
        'definitions': [
            {
                'sense_num': 1,
                'grammar_note': '[T]',
                'definition': 'To put things together in a chain or series.',
                'examples': [
                    'You can concatenate two strings in programming by using the + operator.',
                    'The data sets were concatenated to form a single large database.',
                ],
                'register': 'specialized',
            },
        ],
        'translations': {
            'chinese': {'text': '连接', 'provider': 'Microsoft'},
            'french': {'text': 'concaténer', 'provider': 'Microsoft'},
        },
        'related': [],
        'synonyms': [],
    },
    {
        'headword': 'pandemic',
        'slug': 'pandemic',
        'pos': 'noun',
        'guide_word': 'disease spreading over wide area',
        'phonetic_uk': '/pænˈdemɪk/',
        'phonetic_us': '/pænˈdemɪk/',
        'level': 'C1',
        'definitions': [
            {
                'sense_num': 1,
                'grammar_note': '[C]',
                'definition': 'A disease that exists in almost all of an area or in almost all of a particular group of people, animals, or plants.',
                'examples': [
                    'The COVID-19 pandemic changed the way millions of people work.',
                    'Health authorities are monitoring the situation to prevent a pandemic.',
                ],
                'register': '',
            },
        ],
        'translations': {
            'chinese': {'text': '大流行病', 'provider': 'Microsoft'},
            'french': {'text': 'pandémie', 'provider': 'Microsoft'},
        },
        'related': [],
        'synonyms': [],
    },
    {
        'headword': 'cryptocurrency',
        'slug': 'cryptocurrency',
        'pos': 'noun',
        'guide_word': 'digital currency',
        'phonetic_uk': '/ˈkrɪptəʊˌkɜːrənsi/',
        'phonetic_us': '/ˈkrɪptoʊˌkɜːrənsi/',
        'level': 'C1',
        'definitions': [
            {
                'sense_num': 1,
                'grammar_note': '[C, U]',
                'definition': 'A digital currency produced by a public network, rather than any government, that uses cryptography to make sure payments are sent and received safely.',
                'examples': [
                    'Bitcoin is the best-known cryptocurrency.',
                    'Many investors have lost money in volatile cryptocurrency markets.',
                ],
                'register': '',
            },
            {
                'sense_num': 2,
                'grammar_note': '[U]',
                'definition': 'The technology and systems that support digital currencies.',
                'examples': [
                    'Cryptocurrency transactions are recorded on a blockchain.',
                ],
                'register': 'technical',
            },
        ],
        'translations': {
            'chinese': {'text': '加密货币', 'provider': 'Microsoft'},
            'french': {'text': 'cryptomonnaie', 'provider': 'Microsoft'},
        },
        'related': [],
        'synonyms': [],
    },
    {
        'headword': 'unblemished',
        'slug': 'unblemished',
        'pos': 'adjective',
        'guide_word': 'without any faults or marks',
        'phonetic_uk': '/ʌnˈblemɪʃt/',
        'phonetic_us': '/ʌnˈblemɪʃt/',
        'level': 'C2',
        'definitions': [
            {
                'sense_num': 1,
                'grammar_note': '',
                'definition': 'Not spoiled or damaged in any way; perfect.',
                'examples': [
                    'She has an unblemished reputation in the industry.',
                    'His career remained unblemished throughout 30 years of public service.',
                ],
                'register': '',
            },
        ],
        'translations': {
            'chinese': {'text': '无瑕疵的', 'provider': 'Microsoft'},
            'french': {'text': 'sans tache', 'provider': 'Microsoft'},
        },
        'related': [],
        'synonyms': [],
    },
    {
        'headword': 'altruism',
        'slug': 'altruism',
        'pos': 'noun',
        'guide_word': 'caring about others\' happiness',
        'phonetic_uk': '/ˈæltruɪzəm/',
        'phonetic_us': '/ˈæltruɪzəm/',
        'level': 'C2',
        'definitions': [
            {
                'sense_num': 1,
                'grammar_note': '[U]',
                'definition': 'A way of thinking and behaving that shows you care about other people and their needs more than you think about yourself.',
                'examples': [
                    'Her donation was an act of pure altruism.',
                    'Altruism is a core value in many religious and ethical traditions.',
                ],
                'register': '',
            },
        ],
        'translations': {
            'chinese': {'text': '利他主义', 'provider': 'Microsoft'},
            'french': {'text': 'altruisme', 'provider': 'Microsoft'},
        },
        'related': [],
        'synonyms': [],
    },
    {
        'headword': 'ephemeral',
        'slug': 'ephemeral',
        'pos': 'adjective',
        'guide_word': 'lasting for a short time',
        'phonetic_uk': '/ɪˈfemərəl/',
        'phonetic_us': '/ɪˈfemərəl/',
        'level': 'C2',
        'definitions': [
            {
                'sense_num': 1,
                'grammar_note': '',
                'definition': 'Lasting for only a short time; short-lived.',
                'examples': [
                    'Fashion is ephemeral, but style is eternal.',
                    'The ephemeral beauty of cherry blossoms is celebrated in Japan.',
                ],
                'register': 'formal',
            },
        ],
        'translations': {
            'chinese': {'text': '短暂的', 'provider': 'Microsoft'},
            'french': {'text': 'éphémère', 'provider': 'Microsoft'},
            'spanish': {'text': 'efímero', 'provider': 'Microsoft'},
            'german': {'text': 'vergänglich', 'provider': 'Microsoft'},
        },
        'related': [],
        'synonyms': [],
    },
    {
        'headword': 'quintessential',
        'slug': 'quintessential',
        'pos': 'adjective',
        'guide_word': 'most typical example of something',
        'phonetic_uk': '/ˌkwɪntɪˈsenʃəl/',
        'phonetic_us': '/ˌkwɪntɪˈsenʃəl/',
        'level': 'C2',
        'definitions': [
            {
                'sense_num': 1,
                'grammar_note': '',
                'definition': 'Representing the most perfect or typical example of something.',
                'examples': [
                    'He is the quintessential English gentleman.',
                    'This building is a quintessential example of Victorian architecture.',
                ],
                'register': 'formal',
            },
        ],
        'translations': {
            'chinese': {'text': '典型的', 'provider': 'Microsoft'},
            'french': {'text': 'quintessentiel', 'provider': 'Microsoft'},
        },
        'related': [],
        'synonyms': [],
    },
    {
        'headword': 'meticulous',
        'slug': 'meticulous',
        'pos': 'adjective',
        'guide_word': 'very careful about details',
        'phonetic_uk': '/məˈtɪkjələs/',
        'phonetic_us': '/məˈtɪkjələs/',
        'level': 'C1',
        'definitions': [
            {
                'sense_num': 1,
                'grammar_note': '',
                'definition': 'Very careful and with great attention to every detail.',
                'examples': [
                    'She kept meticulous records of all expenses.',
                    'His meticulous attention to detail makes him an excellent surgeon.',
                ],
                'register': '',
            },
        ],
        'translations': {
            'chinese': {'text': '一丝不苟的', 'provider': 'Microsoft'},
            'french': {'text': 'méticuleux', 'provider': 'Microsoft'},
        },
        'related': [],
        'synonyms': [],
    },
    {
        'headword': 'reverie',
        'slug': 'reverie',
        'pos': 'noun',
        'guide_word': 'pleasant daydream',
        'phonetic_uk': '/ˈrevəri/',
        'phonetic_us': '/ˈrevəri/',
        'level': 'C2',
        'definitions': [
            {
                'sense_num': 1,
                'grammar_note': '[C, U]',
                'definition': 'A pleasant dreamlike thought or thoughts; a state of thinking about pleasant things.',
                'examples': [
                    'She was lost in a reverie about her childhood holidays.',
                    'He was disturbed from his reverie by a knock at the door.',
                ],
                'register': 'literary',
            },
        ],
        'translations': {
            'chinese': {'text': '幻想', 'provider': 'Microsoft'},
            'french': {'text': 'rêverie', 'provider': 'Microsoft'},
        },
        'related': [],
        'synonyms': [],
    },
    {
        'headword': 'harmony',
        'slug': 'harmony',
        'pos': 'noun',
        'guide_word': 'peaceful agreement / musical combination',
        'phonetic_uk': '/ˈhɑːməni/',
        'phonetic_us': '/ˈhɑːrməni/',
        'level': 'B2',
        'definitions': [
            {
                'sense_num': 1,
                'grammar_note': '[U]',
                'definition': 'A situation in which people are peaceful and agree with each other, or when things seem right or suitable together.',
                'examples': [
                    'People of different religions live together in harmony in this town.',
                    'The interior design creates a sense of harmony and balance.',
                ],
                'register': '',
            },
            {
                'sense_num': 2,
                'grammar_note': '[C, U]',
                'definition': 'The combination of musical notes played or sung at the same time to give a pleasing effect.',
                'examples': [
                    'The choir sang in perfect harmony.',
                    'The song features beautiful four-part harmonies.',
                ],
                'register': '',
            },
        ],
        'translations': {
            'chinese': {'text': '和谐', 'provider': 'Microsoft'},
            'french': {'text': 'harmonie', 'provider': 'Microsoft'},
        },
        'related': [],
        'synonyms': [],
    },
    {
        'headword': 'nostalgia',
        'slug': 'nostalgia',
        'pos': 'noun',
        'guide_word': 'longing for the past',
        'phonetic_uk': '/nɒˈstælʤə/',
        'phonetic_us': '/nɑːˈstælʤə/',
        'level': 'B2',
        'definitions': [
            {
                'sense_num': 1,
                'grammar_note': '[U]',
                'definition': 'A feeling of pleasure and also slight sadness when you think about things that happened in the past.',
                'examples': [
                    'She felt a wave of nostalgia when she heard the old song.',
                    'There is a certain nostalgia for the simpler times of childhood.',
                ],
                'register': '',
            },
        ],
        'translations': {
            'chinese': {'text': '怀旧', 'provider': 'Microsoft'},
            'french': {'text': 'nostalgie', 'provider': 'Microsoft'},
        },
        'related': [],
        'synonyms': [],
    },
    {
        'headword': 'solitude',
        'slug': 'solitude',
        'pos': 'noun',
        'guide_word': 'the state of being alone',
        'phonetic_uk': '/ˈsɒlɪtjuːd/',
        'phonetic_us': '/ˈsɑːlɪtuːd/',
        'level': 'B2',
        'definitions': [
            {
                'sense_num': 1,
                'grammar_note': '[U]',
                'definition': 'The situation of being alone without other people.',
                'examples': [
                    'She enjoyed the solitude of long walks in the country.',
                    'He retreated to his mountain cabin for a week of solitude.',
                ],
                'register': '',
            },
        ],
        'translations': {
            'chinese': {'text': '孤独', 'provider': 'Microsoft'},
            'french': {'text': 'solitude', 'provider': 'Microsoft'},
        },
        'related': [],
        'synonyms': [],
    },
    {
        'headword': 'mitigate',
        'slug': 'mitigate',
        'pos': 'verb',
        'guide_word': 'make something less harmful',
        'phonetic_uk': '/ˈmɪtɪɡeɪt/',
        'phonetic_us': '/ˈmɪtɪɡeɪt/',
        'level': 'C1',
        'definitions': [
            {
                'sense_num': 1,
                'grammar_note': '[T]',
                'definition': 'To make something less harmful, serious, or painful.',
                'examples': [
                    'Governments need to take action to mitigate the effects of climate change.',
                    'The new measures aim to mitigate the risks associated with the project.',
                ],
                'register': 'formal',
            },
        ],
        'translations': {
            'chinese': {'text': '减轻', 'provider': 'Microsoft'},
            'french': {'text': 'atténuer', 'provider': 'Microsoft'},
        },
        'related': [],
        'synonyms': [],
    },
    # Additional common words for search results
    {
        'headword': 'innovation',
        'slug': 'innovation',
        'pos': 'noun',
        'guide_word': 'new idea or method',
        'phonetic_uk': '/ˌɪnəˈveɪʃən/',
        'phonetic_us': '/ˌɪnəˈveɪʃən/',
        'level': 'B2',
        'definitions': [
            {
                'sense_num': 1,
                'grammar_note': '[C, U]',
                'definition': 'A new idea or method, or the use of new ideas and methods.',
                'examples': [
                    'Technological innovation has transformed every area of our lives.',
                    'The company is known for its innovation in product design.',
                ],
                'register': '',
            },
        ],
        'translations': {
            'chinese': {'text': '创新', 'provider': 'Microsoft'},
            'french': {'text': 'innovation', 'provider': 'Microsoft'},
        },
        'related': [],
        'synonyms': [],
    },
    {
        'headword': 'ephemeral',
        'slug': 'ephemeral',
        'pos': 'adjective',
        'guide_word': 'lasting for a short time',
        'phonetic_uk': '/ɪˈfemərəl/',
        'phonetic_us': '/ɪˈfemərəl/',
        'level': 'C2',
        'definitions': [
            {
                'sense_num': 1,
                'grammar_note': '',
                'definition': 'Lasting for only a short time; short-lived.',
                'examples': [
                    'Fashion is ephemeral, but style is eternal.',
                    'The ephemeral beauty of cherry blossoms is celebrated in Japan.',
                ],
                'register': 'formal',
            },
        ],
        'translations': {
            'chinese': {'text': '短暂的', 'provider': 'Microsoft'},
            'french': {'text': 'éphémère', 'provider': 'Microsoft'},
            'spanish': {'text': 'efímero', 'provider': 'Microsoft'},
        },
        'related': [],
        'synonyms': [],
    },
    {
        'headword': 'ambiguous',
        'slug': 'ambiguous',
        'pos': 'adjective',
        'guide_word': 'having more than one meaning',
        'phonetic_uk': '/æmˈbɪɡjuəs/',
        'phonetic_us': '/æmˈbɪɡjuəs/',
        'level': 'C1',
        'definitions': [
            {
                'sense_num': 1,
                'grammar_note': '',
                'definition': 'Having or expressing more than one possible meaning, sometimes intentionally.',
                'examples': [
                    'His statement was deliberately ambiguous.',
                    'The law is ambiguous on this point.',
                ],
                'register': '',
            },
        ],
        'translations': {
            'chinese': {'text': '模糊的', 'provider': 'Microsoft'},
            'french': {'text': 'ambigu', 'provider': 'Microsoft'},
        },
        'related': [],
        'synonyms': [],
    },
    {
        'headword': 'eloquent',
        'slug': 'eloquent',
        'pos': 'adjective',
        'guide_word': 'expressing ideas clearly and effectively',
        'phonetic_uk': '/ˈeləkwənt/',
        'phonetic_us': '/ˈeləkwənt/',
        'level': 'C1',
        'definitions': [
            {
                'sense_num': 1,
                'grammar_note': '',
                'definition': 'Giving a clear, strong message.',
                'examples': [
                    'She gave an eloquent speech about the importance of education.',
                    'His silence was more eloquent than any words.',
                ],
                'register': '',
            },
        ],
        'translations': {
            'chinese': {'text': '雄辩的', 'provider': 'Microsoft'},
            'french': {'text': 'éloquent', 'provider': 'Microsoft'},
        },
        'related': [],
        'synonyms': [],
    },
    {
        'headword': 'tenacious',
        'slug': 'tenacious',
        'pos': 'adjective',
        'guide_word': 'determined; not giving up easily',
        'phonetic_uk': '/təˈneɪʃəs/',
        'phonetic_us': '/təˈneɪʃəs/',
        'level': 'C1',
        'definitions': [
            {
                'sense_num': 1,
                'grammar_note': '',
                'definition': 'Holding firmly to something; not likely to give up or be defeated.',
                'examples': [
                    'She is a tenacious negotiator who always gets what she wants.',
                    "The team's tenacious defense kept them in the game.",
                ],
                'register': '',
            },
        ],
        'translations': {
            'chinese': {'text': '坚韧的', 'provider': 'Microsoft'},
        },
        'related': [],
        'synonyms': [],
    },
    {
        'headword': 'eloquence',
        'slug': 'eloquence',
        'pos': 'noun',
        'guide_word': 'the ability to speak clearly and effectively',
        'phonetic_uk': '/ˈeləkwəns/',
        'phonetic_us': '/ˈeləkwəns/',
        'level': 'C1',
        'definitions': [
            {
                'sense_num': 1,
                'grammar_note': '[U]',
                'definition': 'The ability to use language clearly and effectively.',
                'examples': [
                    'She spoke with great eloquence about the plight of the refugees.',
                ],
                'register': '',
            },
        ],
        'translations': {
            'chinese': {'text': '口才', 'provider': 'Microsoft'},
        },
        'related': [],
        'synonyms': [],
    },
]

# Thesaurus entries
THESAURUS_DATA = [
    {
        'headword': 'to behave well',
        'slug': 'to-behave-well',
        'pos': 'phrase',
        'guide_word': 'thesaurus entry',
        'phonetic_uk': '',
        'phonetic_us': '',
        'level': '',
        'definitions': [
            {
                'sense_num': 1,
                'grammar_note': '',
                'definition': 'To act in a way that is considered correct or polite.',
                'examples': ['She always behaves well in public.'],
                'register': '',
            }
        ],
        'translations': {},
        'related': [],
        'synonyms': [
            'behave yourself', 'act appropriately', 'conduct yourself properly',
            'mind your manners', 'be on your best behavior', 'act with decorum',
            'comport yourself well', 'play by the rules', 'toe the line',
            'keep in line', 'act respectfully', 'show good conduct',
        ],
        'is_thesaurus': True,
    },
    {
        'headword': 'feel giddy',
        'slug': 'feel-giddy',
        'pos': 'phrase',
        'guide_word': 'thesaurus entry',
        'phonetic_uk': '',
        'phonetic_us': '',
        'level': '',
        'definitions': [
            {
                'sense_num': 1,
                'grammar_note': '',
                'definition': 'To feel dizzy or unsteady, or to feel very excited.',
                'examples': ['She felt giddy with excitement.'],
                'register': '',
            }
        ],
        'translations': {},
        'related': [],
        'synonyms': [
            'feel dizzy', 'feel lightheaded', 'feel faint', 'feel woozy',
            'feel unsteady', 'feel vertiginous', 'be overcome with excitement',
            'feel exhilarated', 'feel euphoric', 'feel elated', 'be ecstatic',
        ],
        'is_thesaurus': True,
    },
]

# Grammar topics
GRAMMAR_DATA = [
    {
        'title': 'Present perfect simple',
        'slug': 'present-perfect-simple',
        'category': 'Verbs',
        'summary': 'The present perfect simple is used to talk about past events that have a connection to the present.',
        'sort_order': 10,
        'content': [
            {
                'heading': 'Uses of the present perfect simple',
                'body': 'We use the present perfect simple with past events that have a connection to the present. It is formed with have/has + past participle.',
                'examples': [
                    {'label': 'Affirmative', 'sentence': 'I have visited Paris three times.'},
                    {'label': 'Affirmative', 'sentence': 'She has already finished her homework.'},
                    {'label': 'Negative', 'sentence': "I haven't seen him since last Monday."},
                    {'label': 'Negative', 'sentence': "They haven't arrived yet."},
                    {'label': 'Interrogative', 'sentence': 'Have you ever eaten sushi?'},
                    {'label': 'Interrogative', 'sentence': 'Has she called back yet?'},
                ],
            },
            {
                'heading': 'With time adverbs',
                'body': 'The present perfect simple is commonly used with time adverbs such as: ever, never, already, yet, just, recently, since, for.',
                'examples': [
                    {'label': 'Ever/Never', 'sentence': 'Have you ever been to Australia?'},
                    {'label': 'Just', 'sentence': "I've just received the news."},
                    {'label': 'Since', 'sentence': 'He has lived here since 2010.'},
                    {'label': 'For', 'sentence': 'She has worked for this company for five years.'},
                ],
            },
        ],
    },
    {
        'title': 'Modal verbs: possibility',
        'slug': 'modal-verbs-possibility',
        'category': 'Verbs',
        'summary': 'Modal verbs such as might, could, and may are used to express different degrees of possibility.',
        'sort_order': 20,
        'content': [
            {
                'heading': 'May, might and could for possibility',
                'body': "We use may, might and could to say that something is possible. 'May' suggests a stronger possibility than 'might' or 'could'. All three are followed by the base form of the verb.",
                'examples': [
                    {'label': 'May (present/future)', 'sentence': 'It may rain later today.'},
                    {'label': 'Might (present/future)', 'sentence': 'She might come to the party, but she\'s not sure.'},
                    {'label': 'Could (present/future)', 'sentence': 'Could you be right? I think it\'s possible.'},
                    {'label': 'Past possibility (may have)', 'sentence': 'He may have forgotten about the meeting.'},
                    {'label': 'Past possibility (might have)', 'sentence': 'She might have taken the wrong train.'},
                ],
            },
            {
                'heading': "Difference between 'may', 'might', and 'could'",
                'body': "Although these words are often interchangeable, there are subtle differences. 'May' is slightly more formal than 'might'. 'Could' often suggests that the possibility depends on certain conditions.",
                'examples': [
                    {'label': 'Formal', 'sentence': 'The government may introduce new regulations.'},
                    {'label': 'Informal', 'sentence': 'I might go out tonight.'},
                    {'label': 'Conditional', 'sentence': 'With a bit more effort, she could pass the exam.'},
                ],
            },
        ],
    },
    {
        'title': 'Fewer and less',
        'slug': 'fewer-and-less',
        'category': 'Grammar in use',
        'summary': "'Fewer' is used with countable nouns; 'less' is used with uncountable nouns.",
        'sort_order': 30,
        'content': [
            {
                'heading': 'Using fewer',
                'body': "We use 'fewer' before plural countable nouns (things you can count individually).",
                'examples': [
                    {'label': 'Correct', 'sentence': 'There are fewer cars on the road today.'},
                    {'label': 'Correct', 'sentence': 'Fewer students attended the lecture than expected.'},
                    {'label': 'Correct', 'sentence': 'We need fewer meetings and more action.'},
                ],
            },
            {
                'heading': 'Using less',
                'body': "We use 'less' before uncountable nouns (things that cannot be counted individually) and before numbers and amounts.",
                'examples': [
                    {'label': 'Correct', 'sentence': 'We should use less water to protect the environment.'},
                    {'label': 'Correct', 'sentence': 'There is less traffic on Sundays.'},
                    {'label': 'Correct', 'sentence': 'The journey takes less than an hour.'},
                    {'label': 'Informal usage', 'sentence': 'Less people came than we expected. (informal, but common)'},
                ],
            },
        ],
    },
    {
        'title': 'Passive voice',
        'slug': 'passive-voice',
        'category': 'Verbs',
        'summary': 'In the passive voice, the object of the active sentence becomes the subject, and the focus is on what happens to the subject.',
        'sort_order': 40,
        'content': [
            {
                'heading': 'Formation of the passive',
                'body': 'The passive is formed with the appropriate form of the verb be + the past participle. The agent (the doer of the action) may be included with by or omitted.',
                'examples': [
                    {'label': 'Present simple passive', 'sentence': 'The letters are delivered every morning.'},
                    {'label': 'Past simple passive', 'sentence': 'The book was written in 1984.'},
                    {'label': 'Present perfect passive', 'sentence': 'The problem has been solved.'},
                    {'label': 'Future passive', 'sentence': 'The project will be completed next week.'},
                    {'label': 'With agent', 'sentence': 'The Mona Lisa was painted by Leonardo da Vinci.'},
                ],
            },
            {
                'heading': 'When to use the passive',
                'body': 'We use the passive when we want to focus on the person or thing affected by an action, when the agent is unknown, or when we want to avoid mentioning the agent.',
                'examples': [
                    {'label': 'Unknown agent', 'sentence': 'My car has been stolen.'},
                    {'label': 'Formal/impersonal', 'sentence': 'It is believed that the company will announce new jobs.'},
                    {'label': 'Scientific writing', 'sentence': 'The samples were heated to 100 degrees.'},
                ],
            },
        ],
    },
    {
        'title': 'Comparative and superlative adjectives',
        'slug': 'comparative-and-superlative-adjectives',
        'category': 'Adjectives and adverbs',
        'summary': 'Comparative adjectives compare two things; superlative adjectives compare something to all others in a group.',
        'sort_order': 50,
        'content': [
            {
                'heading': 'Forming comparatives',
                'body': "For short adjectives (one syllable), add -er to form the comparative. For longer adjectives, use 'more'. Irregular forms: good → better, bad → worse, far → further/farther.",
                'examples': [
                    {'label': 'Short adjective (-er)', 'sentence': 'This road is longer than the other one.'},
                    {'label': 'Long adjective (more)', 'sentence': 'This solution is more efficient than the old one.'},
                    {'label': 'Irregular', 'sentence': 'She is better at maths than her sister.'},
                    {'label': 'Than comparison', 'sentence': 'The new model is much faster than the old one.'},
                ],
            },
            {
                'heading': 'Forming superlatives',
                'body': "For short adjectives, add -est. For longer adjectives, use 'the most'. Irregular forms: good → best, bad → worst, far → furthest/farthest.",
                'examples': [
                    {'label': 'Short adjective (-est)', 'sentence': 'This is the tallest building in the city.'},
                    {'label': 'Long adjective (most)', 'sentence': 'She is the most talented student in the class.'},
                    {'label': 'Irregular', 'sentence': 'That was the worst film I have ever seen.'},
                    {'label': 'With group reference', 'sentence': 'Of all the options, this is the most suitable.'},
                ],
            },
        ],
    },
    {
        'title': 'Group prepositions',
        'slug': 'group-prepositions',
        'category': 'Prepositions',
        'summary': 'Group prepositions consist of more than one word and function as a single preposition.',
        'sort_order': 60,
        'content': [
            {
                'heading': 'Common group prepositions',
                'body': 'Group prepositions (also called complex prepositions or multi-word prepositions) are made up of two or more words. The most common ones consist of groups of words ending in a simple preposition.',
                'examples': [
                    {'label': 'Two-word groups', 'sentence': 'According to the report, profits have increased.'},
                    {'label': 'Two-word groups', 'sentence': 'She succeeded because of her hard work.'},
                    {'label': 'Three-word groups', 'sentence': 'In spite of the rain, the match continued.'},
                    {'label': 'Three-word groups', 'sentence': 'We arrived in time for the start of the show.'},
                    {'label': 'Three-word groups', 'sentence': 'On behalf of the entire team, I thank you.'},
                    {'label': 'Three-word groups', 'sentence': 'He sat in front of the television all evening.'},
                    {'label': 'Three-word groups', 'sentence': 'With regard to your question, I have no comment.'},
                    {'label': 'Three-word groups', 'sentence': 'In addition to her salary, she receives a bonus.'},
                ],
            },
        ],
    },
    {
        'title': 'Indirect speech',
        'slug': 'indirect-speech',
        'category': 'Grammar in use',
        'summary': 'Indirect speech reports what someone said without using their exact words. Tenses and pronouns usually change.',
        'sort_order': 70,
        'content': [
            {
                'heading': 'Reporting statements',
                'body': "When we change direct speech to indirect speech, we usually 'backshift' the verb tenses (move them back one step) and change pronouns and time expressions.",
                'examples': [
                    {'label': 'Direct → Indirect (present → past)', 'sentence': 'Direct: "I am tired." → Indirect: She said that she was tired.'},
                    {'label': 'Direct → Indirect (past → past perfect)', 'sentence': 'Direct: "We left early." → Indirect: They said they had left early.'},
                    {'label': 'Direct → Indirect (will → would)', 'sentence': 'Direct: "I will call you." → Indirect: He said he would call me.'},
                ],
            },
            {
                'heading': 'Reporting questions',
                'body': 'When reporting questions, we use if or whether for yes/no questions, and the appropriate question word for wh-questions. The word order becomes statement order.',
                'examples': [
                    {'label': 'Yes/No question', 'sentence': 'Direct: "Are you coming?" → Indirect: She asked if I was coming.'},
                    {'label': 'Wh-question', 'sentence': 'Direct: "Where do you live?" → Indirect: He asked me where I lived.'},
                    {'label': 'Wh-question', 'sentence': 'Direct: "What time does the film start?" → Indirect: She wanted to know what time the film started.'},
                ],
            },
        ],
    },
    {
        'title': "Articles: 'a', 'an' and 'the'",
        'slug': 'articles',
        'category': 'Nouns and pronouns',
        'summary': "Articles 'a', 'an', and 'the' are the most common determiners in English. 'A' and 'an' are indefinite articles; 'the' is the definite article.",
        'sort_order': 80,
        'content': [
            {
                'heading': "Using 'a' and 'an' (indefinite article)",
                'body': "We use 'a' or 'an' with singular countable nouns when we introduce something for the first time, or when we are referring to one of several things. Use 'a' before consonant sounds and 'an' before vowel sounds.",
                'examples': [
                    {'label': 'Countable noun (first mention)', 'sentence': 'I saw a dog in the park.'},
                    {'label': 'Consonant sound', 'sentence': 'She bought a university degree. (a + /j/ sound)'},
                    {'label': 'Vowel sound', 'sentence': 'He is an honest man. (an + silent h)'},
                    {'label': 'Uncountable noun (with a/an)', 'sentence': "It was a great pleasure to meet her. (a + abstract noun used as countable)"},
                ],
            },
            {
                'heading': "Using 'the' (definite article)",
                'body': "We use 'the' when it is clear which particular person or thing we mean, when we mention something for the second time, and with unique things.",
                'examples': [
                    {'label': 'Second mention', 'sentence': 'I saw a dog. The dog was very friendly.'},
                    {'label': 'Unique thing', 'sentence': 'The sun rises in the east.'},
                    {'label': 'Superlatives', 'sentence': 'She is the best student in the class.'},
                    {'label': 'Uncountable nouns (specific)', 'sentence': 'The water in this lake is very cold.'},
                ],
            },
            {
                'heading': 'Zero article',
                'body': "We use no article (zero article) with plural countable nouns and uncountable nouns when making general statements.",
                'examples': [
                    {'label': 'General plural', 'sentence': 'Dogs make great pets.'},
                    {'label': 'General uncountable', 'sentence': 'Water is essential for life.'},
                ],
            },
        ],
    },
]

# Shop items
SHOP_DATA = [
    {
        'name': 'Cambridge Advanced Learner\'s Dictionary (4th Edition)',
        'slug': 'cambridge-advanced-learners-dictionary-4th',
        'category': 'dictionaries',
        'price': 35.00,
        'currency': 'GBP',
        'description': 'The world\'s favourite learner\'s dictionary, with over 140,000 words, phrases, and examples. Ideal for upper-intermediate to advanced learners.',
        'isbn': '978-1-107-03499-3',
        'is_featured': True,
    },
    {
        'name': 'Cambridge Dictionary of American English (2nd Edition)',
        'slug': 'cambridge-dictionary-american-english-2nd',
        'category': 'dictionaries',
        'price': 29.99,
        'currency': 'GBP',
        'description': 'Essential vocabulary reference for American English. Includes thousands of example sentences and a clear explanation of American culture.',
        'isbn': '978-0-521-68257-7',
        'is_featured': True,
    },
    {
        'name': 'Cambridge English Pronouncing Dictionary (18th Edition)',
        'slug': 'cambridge-english-pronouncing-dictionary-18th',
        'category': 'dictionaries',
        'price': 39.00,
        'currency': 'GBP',
        'description': 'The authoritative guide to English pronunciation. Contains over 200,000 British and American pronunciations using the International Phonetic Alphabet.',
        'isbn': '978-0-521-15253-2',
        'is_featured': True,
    },
    {
        'name': 'Cambridge Grammar of English',
        'slug': 'cambridge-grammar-of-english',
        'category': 'grammar',
        'price': 55.00,
        'currency': 'GBP',
        'description': 'A comprehensive and authoritative guide to grammar and usage for learners and teachers of English.',
        'isbn': '978-0-521-58349-9',
        'is_featured': False,
    },
    {
        'name': 'Cambridge Learner\'s Dictionary (4th Edition)',
        'slug': 'cambridge-learners-dictionary-4th',
        'category': 'dictionaries',
        'price': 25.00,
        'currency': 'GBP',
        'description': 'Perfect for intermediate learners. Features clear definitions, example sentences, and grammar information.',
        'isbn': '978-1-107-67408-0',
        'is_featured': False,
    },
    {
        'name': 'Cambridge Phrasal Verbs Dictionary (2nd Edition)',
        'slug': 'cambridge-phrasal-verbs-dictionary-2nd',
        'category': 'dictionaries',
        'price': 22.99,
        'currency': 'GBP',
        'description': 'The comprehensive reference for phrasal verbs in English, with over 6,000 phrasal verbs explained and illustrated with example sentences.',
        'isbn': '978-0-521-67727-6',
        'is_featured': False,
    },
    {
        'name': 'Cambridge Business English Dictionary',
        'slug': 'cambridge-business-english-dictionary',
        'category': 'dictionaries',
        'price': 32.50,
        'currency': 'GBP',
        'description': 'The definitive guide to business vocabulary with over 35,000 words and phrases. Essential for business professionals and students.',
        'isbn': '978-0-521-12244-3',
        'is_featured': False,
    },
    {
        'name': 'Cambridge Thesaurus',
        'slug': 'cambridge-thesaurus',
        'category': 'thesaurus',
        'price': 28.00,
        'currency': 'GBP',
        'description': 'A comprehensive thesaurus organized by meaning, with thousands of words, phrases, and idioms grouped by concept.',
        'isbn': '978-1-107-60479-7',
        'is_featured': False,
    },
]

# Quizzes
QUIZ_DATA = [
    {
        'title': 'Animals Image Quiz (Easy)',
        'slug': 'image-quiz-animals-easy',
        'quiz_type': 'image',
        'difficulty': 'easy',
        'category': 'Animals',
        'description': 'Test your knowledge of animal vocabulary with this easy image quiz.',
        'questions': [
            {
                'q': 'What animal is shown?',
                'image': 'elephant',
                'options': ['Elephant', 'Rhinoceros', 'Hippopotamus', 'Giraffe'],
                'answer': 0,
            },
            {
                'q': 'Can you name this animal?',
                'image': 'penguin',
                'options': ['Puffin', 'Penguin', 'Pelican', 'Parrot'],
                'answer': 1,
            },
            {
                'q': 'What is this animal called?',
                'image': 'kangaroo',
                'options': ['Wallaby', 'Kangaroo', 'Koala', 'Wombat'],
                'answer': 1,
            },
            {
                'q': 'Name this animal.',
                'image': 'dolphin',
                'options': ['Shark', 'Whale', 'Dolphin', 'Porpoise'],
                'answer': 2,
            },
            {
                'q': 'What type of animal is this?',
                'image': 'owl',
                'options': ['Eagle', 'Hawk', 'Falcon', 'Owl'],
                'answer': 3,
            },
        ],
    },
    {
        'title': 'Grammar Quiz: Tenses (Intermediate)',
        'slug': 'grammar-quiz-tenses-intermediate',
        'quiz_type': 'grammar',
        'difficulty': 'intermediate',
        'category': 'Grammar',
        'description': 'Test your knowledge of English tenses with this intermediate grammar quiz.',
        'questions': [
            {
                'q': 'Choose the correct form: "By the time we arrived, she _____ left."',
                'options': ['has', 'had', 'was', 'have'],
                'answer': 1,
            },
            {
                'q': 'Which sentence uses the present perfect correctly?',
                'options': [
                    'I have seen him yesterday.',
                    'She has never been to Paris.',
                    'They have arrived at 6 o\'clock.',
                    'We have met last year.',
                ],
                'answer': 1,
            },
            {
                'q': 'Choose the correct modal verb: "It _____ rain tonight, so bring an umbrella."',
                'options': ['shall', 'will', 'might', 'must'],
                'answer': 2,
            },
            {
                'q': '"Fewer" is used with _____ nouns.',
                'options': ['Uncountable', 'Abstract', 'Plural countable', 'Singular countable'],
                'answer': 2,
            },
            {
                'q': 'Choose the passive voice: "Someone has stolen my wallet."',
                'options': [
                    'My wallet has been stolen.',
                    'My wallet was stolen.',
                    'My wallet is stolen.',
                    'My wallet had been stolen.',
                ],
                'answer': 0,
            },
        ],
    },
    {
        'title': 'Grammar Quiz: Articles (Easy)',
        'slug': 'grammar-quiz-articles-easy',
        'quiz_type': 'grammar',
        'difficulty': 'easy',
        'category': 'Grammar',
        'description': 'Test your understanding of articles a, an, and the.',
        'questions': [
            {
                'q': 'Choose the correct article: "She is _____ honest person."',
                'options': ['a', 'an', 'the', '(no article)'],
                'answer': 1,
            },
            {
                'q': '"_____ sun is a star." Which article is correct?',
                'options': ['A', 'An', 'The', '(no article)'],
                'answer': 2,
            },
            {
                'q': '"_____ dogs make great pets." Which article is correct?',
                'options': ['A', 'An', 'The', '(no article)'],
                'answer': 3,
            },
            {
                'q': 'Choose the correct sentence.',
                'options': [
                    'I saw the film last night. The film was great.',
                    'I saw a film last night. A film was great.',
                    'I saw the film last night. A film was great.',
                    'I saw a film last night. Film was great.',
                ],
                'answer': 0,
            },
            {
                'q': '"She bought _____ umbrella." Which article is correct?',
                'options': ['a', 'an', 'the', '(no article)'],
                'answer': 1,
            },
        ],
    },
]


# ---------------------------------------------------------------------------
# Optional bulk seed data (loaded from scraped_data/ when present at build
# time; the runtime container ships a prebuilt instance_seed/cambridge.db so
# these files are NOT required after the seed DB is generated).
# ---------------------------------------------------------------------------

SCRAPED_DIR = os.path.join(BASE_DIR, 'scraped_data')

# Pinned reference date for all seed-time ``created_at`` columns. This keeps
# regenerated instance_seed/cambridge.db byte-identical across rebuilds and
# matches the WebHarbor MIRROR_REFERENCE_DATE convention (mid-April 2026).
MIRROR_REFERENCE_DATE = datetime(2026, 4, 15, 12, 0, 0)


def _load_json(*names):
    """Return decoded JSON from the first existing file under scraped_data/,
    or None if no file is found. Used only at build-time seed."""
    for n in names:
        p = os.path.join(SCRAPED_DIR, n)
        if os.path.exists(p):
            with open(p, encoding='utf-8') as f:
                return json.load(f)
    return None


def seed_database():
    """Seed the database with initial data.

    Whole-function gated by ``Word.query.count() > 0`` so /reset stays
    byte-identical. When scraped_data/*.json files exist they take
    precedence over the small inline catalog; otherwise the inline lists
    are used as a fallback.
    """
    if Word.query.count() > 0:
        return  # Already seeded

    # ── Words (regular + thesaurus) ───────────────────────────────────────
    words_file = _load_json('words_existing.json')
    if words_file:
        # Bulk catalog dump (preferred). Already contains both regular and
        # thesaurus entries, distinguished by the is_thesaurus_phrase flag.
        seen_slugs = set()
        for wd in words_file:
            if wd['slug'] in seen_slugs:
                continue
            seen_slugs.add(wd['slug'])
            db.session.add(Word(
                headword=wd['headword'], slug=wd['slug'],
                pos=wd.get('pos', ''), guide_word=wd.get('guide_word', ''),
                phonetic_uk=wd.get('phonetic_uk', ''),
                phonetic_us=wd.get('phonetic_us', ''),
                pronunciation_ipa=(wd.get('pronunciation_ipa')
                                   or wd.get('phonetic_uk', '')),
                audio_uk_path=wd.get('audio_uk_path',
                                     f"/static/audio/uk/{wd['slug']}.mp3"),
                audio_us_path=wd.get('audio_us_path',
                                     f"/static/audio/us/{wd['slug']}.mp3"),
                level=wd.get('level', ''),
                definitions_json=_j(wd.get('definitions', [])),
                translations_json=_j(wd.get('translations', {})),
                related_json=_j(wd.get('related', [])),
                synonyms_json=_j(wd.get('synonyms', [])),
                is_thesaurus_phrase=bool(wd.get('is_thesaurus_phrase', False)),
                created_at=MIRROR_REFERENCE_DATE,
            ))
        # Extra catalog words generated from WordNet — append after the
        # curated existing set so existing ids stay stable.
        extra = _load_json('words_fetched.json') or []
        for wd in extra:
            if wd['slug'] in seen_slugs:
                continue
            seen_slugs.add(wd['slug'])
            db.session.add(Word(
                headword=wd['headword'], slug=wd['slug'],
                pos=wd.get('pos', ''), guide_word=wd.get('guide_word', ''),
                phonetic_uk=wd.get('phonetic_uk', ''),
                phonetic_us=wd.get('phonetic_us', ''),
                pronunciation_ipa=(wd.get('pronunciation_ipa')
                                   or wd.get('phonetic_uk', '')),
                audio_uk_path=wd.get('audio_uk_path',
                                     f"/static/audio/uk/{wd['slug']}.mp3"),
                audio_us_path=wd.get('audio_us_path',
                                     f"/static/audio/us/{wd['slug']}.mp3"),
                level=wd.get('level', ''),
                definitions_json=_j(wd.get('definitions', [])),
                translations_json=_j(wd.get('translations', {})),
                related_json=_j(wd.get('related', [])),
                synonyms_json=_j(wd.get('synonyms', [])),
                is_thesaurus_phrase=bool(wd.get('is_thesaurus_phrase', False)),
                created_at=MIRROR_REFERENCE_DATE,
            ))
        # R3 expansion: ~5500 additional WordNet entries to push catalog past
        # 12000 words. Appended after the existing set so prior ids stay
        # stable; uses the same schema-level helpers.
        extra2 = _load_json('words_extra.json') or []
        for wd in extra2:
            if wd['slug'] in seen_slugs:
                continue
            seen_slugs.add(wd['slug'])
            db.session.add(Word(
                headword=wd['headword'], slug=wd['slug'],
                pos=wd.get('pos', ''), guide_word=wd.get('guide_word', ''),
                phonetic_uk=wd.get('phonetic_uk', ''),
                phonetic_us=wd.get('phonetic_us', ''),
                pronunciation_ipa=(wd.get('pronunciation_ipa')
                                   or wd.get('phonetic_uk', '')),
                audio_uk_path=wd.get('audio_uk_path',
                                     f"/static/audio/uk/{wd['slug']}.mp3"),
                audio_us_path=wd.get('audio_us_path',
                                     f"/static/audio/us/{wd['slug']}.mp3"),
                level=wd.get('level', ''),
                definitions_json=_j(wd.get('definitions', [])),
                translations_json=_j(wd.get('translations', {})),
                related_json=_j(wd.get('related', [])),
                synonyms_json=_j(wd.get('synonyms', [])),
                is_thesaurus_phrase=bool(wd.get('is_thesaurus_phrase', False)),
                created_at=MIRROR_REFERENCE_DATE,
            ))
        # R4 expansion: ~5500 further WordNet entries with rich metadata —
        # word-level register, frequency rank, etymology paragraph,
        # collocations, and a common-mistake note. Same append-after pattern
        # so legacy ids stay stable.
        extra3 = _load_json('words_r4.json') or []
        for wd in extra3:
            if wd['slug'] in seen_slugs:
                continue
            seen_slugs.add(wd['slug'])
            db.session.add(Word(
                headword=wd['headword'], slug=wd['slug'],
                pos=wd.get('pos', ''), guide_word=wd.get('guide_word', ''),
                phonetic_uk=wd.get('phonetic_uk', ''),
                phonetic_us=wd.get('phonetic_us', ''),
                pronunciation_ipa=(wd.get('pronunciation_ipa')
                                   or wd.get('phonetic_uk', '')),
                audio_uk_path=wd.get('audio_uk_path',
                                     f"/static/audio/uk/{wd['slug']}.mp3"),
                audio_us_path=wd.get('audio_us_path',
                                     f"/static/audio/us/{wd['slug']}.mp3"),
                level=wd.get('level', ''),
                definitions_json=_j(wd.get('definitions', [])),
                translations_json=_j(wd.get('translations', {})),
                related_json=_j(wd.get('related', [])),
                synonyms_json=_j(wd.get('synonyms', [])),
                is_thesaurus_phrase=bool(wd.get('is_thesaurus_phrase', False)),
                created_at=MIRROR_REFERENCE_DATE,
                register=wd.get('register', ''),
                frequency_rank=int(wd.get('frequency_rank', 0) or 0),
                etymology=wd.get('etymology', ''),
                collocations_json=_j(wd.get('collocations', [])),
                mistake_note=wd.get('mistake_note', ''),
            ))
        # R5 expansion: ~8000 entries split across three sub-dictionaries —
        # phrasal-verb dictionary (~2400), idiom dictionary (~2600), and a
        # last sweep of WordNet single-word entries (~3000). Each carries an
        # ``r5_category`` tag and a ``word_family`` list that templates
        # surface as the new "Word family" / "Phrasal verbs" / "Idioms"
        # panels. Same append-after-r4 pattern — legacy ids stay stable.
        extra4 = _load_json('words_r5.json') or []
        for wd in extra4:
            if wd['slug'] in seen_slugs:
                continue
            seen_slugs.add(wd['slug'])
            # ``related`` may arrive as a list of plain slugs (R5 shape) or
            # as the legacy list of dicts. Templates accept either via
            # Word.get_related — we serialize whatever was given.
            db.session.add(Word(
                headword=wd['headword'], slug=wd['slug'],
                pos=wd.get('pos', ''), guide_word=wd.get('guide_word', ''),
                phonetic_uk=wd.get('phonetic_uk', ''),
                phonetic_us=wd.get('phonetic_us', ''),
                pronunciation_ipa=(wd.get('pronunciation_ipa')
                                   or wd.get('phonetic_uk', '')),
                audio_uk_path=wd.get('audio_uk_path',
                                     f"/static/audio/uk/{wd['slug']}.mp3"),
                audio_us_path=wd.get('audio_us_path',
                                     f"/static/audio/us/{wd['slug']}.mp3"),
                level=wd.get('level', ''),
                definitions_json=_j(wd.get('definitions', [])),
                translations_json=_j(wd.get('translations', {})),
                related_json=_j(wd.get('related', [])),
                synonyms_json=_j(wd.get('synonyms', [])),
                is_thesaurus_phrase=False,
                created_at=MIRROR_REFERENCE_DATE,
                register=wd.get('register', ''),
                frequency_rank=int(wd.get('frequency_rank', 0) or 0),
                etymology=wd.get('etymology', ''),
                collocations_json=_j(wd.get('collocations', [])),
                mistake_note=wd.get('mistake_note', ''),
            ))
    else:
        # Fallback: inline curated lists.
        seen_slugs = set()
        for wd in WORDS_DATA:
            if wd['slug'] in seen_slugs:
                continue
            seen_slugs.add(wd['slug'])
            db.session.add(Word(
                headword=wd['headword'], slug=wd['slug'], pos=wd['pos'],
                guide_word=wd['guide_word'],
                phonetic_uk=wd['phonetic_uk'], phonetic_us=wd['phonetic_us'],
                pronunciation_ipa=wd['phonetic_uk'],
                audio_uk_path=f"/static/audio/uk/{wd['slug']}.mp3",
                audio_us_path=f"/static/audio/us/{wd['slug']}.mp3",
                level=wd.get('level', ''),
                definitions_json=_j(wd['definitions']),
                translations_json=_j(wd['translations']),
                related_json=_j(wd['related']),
                synonyms_json=_j(wd['synonyms']),
                is_thesaurus_phrase=False,
                created_at=MIRROR_REFERENCE_DATE,
            ))
        for td in THESAURUS_DATA:
            db.session.add(Word(
                headword=td['headword'], slug=td['slug'], pos=td['pos'],
                guide_word=td['guide_word'],
                phonetic_uk=td['phonetic_uk'], phonetic_us=td['phonetic_us'],
                pronunciation_ipa=td['phonetic_uk'],
                audio_uk_path=f"/static/audio/uk/{td['slug']}.mp3",
                audio_us_path=f"/static/audio/us/{td['slug']}.mp3",
                level=td.get('level', ''),
                definitions_json=_j(td['definitions']),
                translations_json=_j(td['translations']),
                related_json=_j(td['related']),
                synonyms_json=_j(td['synonyms']),
                is_thesaurus_phrase=True,
                created_at=MIRROR_REFERENCE_DATE,
            ))

    # ── Grammar topics ────────────────────────────────────────────────────
    gram_existing = _load_json('grammar_existing.json')
    if gram_existing is not None:
        gram_list = list(gram_existing)
        extras = _load_json('extras.json') or {}
        gram_list += extras.get('grammar_extra', [])
        # R3: 50 deeper topics — phrasal verbs, conditionals nuance, modal
        # nuance, prepositions, sentence-level grammar.
        gram_v2 = _load_json('grammar_v2.json') or []
        gram_list += gram_v2
    else:
        gram_list = GRAMMAR_DATA
    for gd in gram_list:
        db.session.add(GrammarTopic(
            title=gd['title'], slug=gd['slug'],
            category=gd.get('category', ''), summary=gd.get('summary', ''),
            sort_order=gd.get('sort_order', 0),
            content_json=_j(gd.get('content', [])),
        ))

    # ── Shop items ────────────────────────────────────────────────────────
    shop_existing = _load_json('shop_existing.json')
    if shop_existing is not None:
        shop_list = list(shop_existing)
        extras = _load_json('extras.json') or {}
        shop_list += extras.get('shop_extra', [])
    else:
        shop_list = SHOP_DATA
    for sd in shop_list:
        db.session.add(ShopItem(
            name=sd['name'], slug=sd['slug'],
            category=sd.get('category', 'books'),
            price=sd.get('price', 0.0),
            currency=sd.get('currency', 'GBP'),
            description=sd.get('description', ''),
            isbn=sd.get('isbn', ''),
            image='',
            is_featured=bool(sd.get('is_featured', False)),
        ))

    # ── Quizzes ───────────────────────────────────────────────────────────
    quiz_existing = _load_json('quizzes_existing.json')
    if quiz_existing is not None:
        quiz_list = list(quiz_existing)
        qextra = _load_json('quizzes_extra.json') or {}
        quiz_list += qextra.get('quizzes_extra', [])
        # R3: 58 new quizzes (IELTS / TOEFL / CEFR A1-C2 / Business / Academic
        # / Phrasal verbs / Idioms / Phonetics / Grammar deep-dives).
        quiz_v2 = _load_json('quizzes_v2.json') or []
        quiz_list += quiz_v2
    else:
        quiz_list = QUIZ_DATA
    for qd in quiz_list:
        db.session.add(Quiz(
            title=qd['title'], slug=qd['slug'],
            quiz_type=qd.get('quiz_type', 'grammar'),
            difficulty=qd.get('difficulty', 'easy'),
            category=qd.get('category', ''),
            description=qd.get('description', ''),
            questions_json=_j(qd.get('questions', [])),
        ))

    # ── R4: Mistake corner topics ────────────────────────────────────────
    mistakes = _load_json('mistakes_r4.json') or []
    for md in mistakes:
        db.session.add(MistakeCorner(
            slug=md['slug'], topic=md['topic'],
            category=md.get('category', ''),
            body=md.get('body', ''),
            examples_json=_j(md.get('examples', [])),
            sort_order=md.get('sort_order', 0),
        ))

    # ── R4: curated-word patch (etymology / collocations / mistake_note /
    # register / frequency_rank for the ~25 anchor words tasks reference). We
    # flush the bulk inserts first so the patch UPDATEs see real rows. Order
    # of UPDATEs is dictated by sorted slug keys for byte-determinism.
    db.session.flush()
    curated_patch = _load_json('curated_patch_r4.json') or {}
    for slug in sorted(curated_patch.keys()):
        patch = curated_patch[slug]
        w = Word.query.filter_by(slug=slug,
                                 is_thesaurus_phrase=False).first()
        if not w:
            continue
        w.register = patch.get('register', '')
        w.frequency_rank = int(patch.get('frequency_rank', 0) or 0)
        w.etymology = patch.get('etymology', '')
        w.collocations_json = _j(patch.get('collocations', []))
        w.mistake_note = patch.get('mistake_note', '')

    db.session.commit()

    # SQLAlchemy iterates Table.indexes (a set) in non-deterministic order
    # when creating indexes during db.create_all(), which leaves
    # sqlite_master entries in different orders across rebuilds and breaks
    # byte-identity. Re-create them in a deterministic (alphabetical) order
    # so two consecutive seed runs produce md5-identical DB files. VACUUM
    # afterwards so the dropped index pages don't leave non-deterministic
    # free-page residue inside the file.
    from sqlalchemy import text as _sql_text
    rows = db.session.execute(_sql_text(
        "SELECT name, sql FROM sqlite_master "
        "WHERE type='index' AND name NOT LIKE 'sqlite_%' "
        "ORDER BY name"
    )).all()
    for name, _sql in rows:
        db.session.execute(_sql_text(f'DROP INDEX IF EXISTS "{name}"'))
    for _name, sql in rows:
        if sql:
            db.session.execute(_sql_text(sql))
    db.session.commit()
    # VACUUM has to run outside a transaction; SQLAlchemy 2.x exposes the
    # raw connection via db.session.connection().exec_driver_sql.
    raw = db.session.connection().connection
    raw.isolation_level = None
    raw.execute('VACUUM')
    print('Database seeded.')


def seed_benchmark_users():
    """Create 4 benchmark users with saved words and search history. Idempotent.

    Bcrypt hashes are pinned (the random salt would otherwise change the
    rendered seed-DB bytes on every regeneration). All ``created_at``
    columns are pinned to MIRROR_REFERENCE_DATE so a re-seed is
    byte-identical to the previous one.
    """
    if User.query.filter_by(email='alice.j@test.com').first():
        return  # already seeded

    def _get_word(slug):
        return Word.query.filter_by(slug=slug, is_thesaurus_phrase=False).first()

    # Plaintext is 'TestPass123!' for all four users (verified against the
    # hashes below by Flask-Bcrypt's check_password_hash). Hashes are
    # PINNED so the produced instance_seed/cambridge.db stays
    # byte-identical across rebuilds.
    PINNED_HASHES = {
        'alice.j@test.com':
            '$2b$12$xZclDqCGheUDzCYbk0bCpeyQr4A14kFaOBWj5a.F8H7akIFp0iPJe',
        'bob.c@test.com':
            '$2b$12$qS3evhIcvPo2R4nX6nk.QemDylmWKJLQ0dhoHdYkU/WnOqYh6F6vy',
        'carol.d@test.com':
            '$2b$12$Iw42jipwhSoQrF/e3D6KOOYfsEV0AVUiMr9lO8wR2Kl4D5RArdz4i',
        'david.k@test.com':
            '$2b$12$B7SU8SzE77hpzBk890p0iuEVxI0RDNxpzgMQZq2p8mvanGmTGJI/y',
    }

    # ------------------------------------------------------------------
    # Alice Johnson — advanced learner, C1/C2 focus
    # ------------------------------------------------------------------
    alice = User(name='Alice Johnson', email='alice.j@test.com',
                 password_hash=PINNED_HASHES['alice.j@test.com'],
                 created_at=MIRROR_REFERENCE_DATE)
    db.session.add(alice)
    db.session.flush()

    alice_saved_slugs = ['serendipity', 'ubiquitous', 'ephemeral',
                         'resilience', 'altruism', 'eloquent', 'meticulous']
    for slug in alice_saved_slugs:
        w = _get_word(slug)
        if w:
            db.session.add(SavedWord(user_id=alice.id, word_id=w.id,
                                     created_at=MIRROR_REFERENCE_DATE))

    alice_searches = ['serendipity', 'ubiquitous', 'C2 vocabulary',
                      'ephemeral meaning', 'resilience definition']
    for term in alice_searches:
        db.session.add(SearchHistory(user_id=alice.id, term=term,
                                     created_at=MIRROR_REFERENCE_DATE))

    # ------------------------------------------------------------------
    # Bob Chen — intermediate learner, B2 focus, grammar interest
    # ------------------------------------------------------------------
    bob = User(name='Bob Chen', email='bob.c@test.com',
               password_hash=PINNED_HASHES['bob.c@test.com'],
               created_at=MIRROR_REFERENCE_DATE)
    db.session.add(bob)
    db.session.flush()

    bob_saved_slugs = ['harmony', 'nostalgia', 'solitude',
                       'innovation', 'sustainable', 'procrastination']
    for slug in bob_saved_slugs:
        w = _get_word(slug)
        if w:
            db.session.add(SavedWord(user_id=bob.id, word_id=w.id,
                                     created_at=MIRROR_REFERENCE_DATE))

    bob_searches = ['present perfect', 'modal verbs', 'harmony', 'nostalgia',
                    'fewer vs less', 'passive voice']
    for term in bob_searches:
        db.session.add(SearchHistory(user_id=bob.id, term=term,
                                     created_at=MIRROR_REFERENCE_DATE))

    # ------------------------------------------------------------------
    # Carol Diaz — vocabulary builder, mixed levels
    # ------------------------------------------------------------------
    carol = User(name='Carol Diaz', email='carol.d@test.com',
                 password_hash=PINNED_HASHES['carol.d@test.com'],
                 created_at=MIRROR_REFERENCE_DATE)
    db.session.add(carol)
    db.session.flush()

    carol_saved_slugs = ['mitigate', 'ambiguous', 'tenacious',
                         'pandemic', 'cryptocurrency', 'zeitgeist', 'gestalt',
                         'quintessential', 'impeccable', 'procrastinate']
    for slug in carol_saved_slugs:
        w = _get_word(slug)
        if w:
            db.session.add(SavedWord(user_id=carol.id, word_id=w.id,
                                     created_at=MIRROR_REFERENCE_DATE))

    carol_searches = ['C1 words', 'mitigate', 'ambiguous definition',
                      'zeitgeist', 'cryptocurrency meaning', 'B2 vocabulary']
    for term in carol_searches:
        db.session.add(SearchHistory(user_id=carol.id, term=term,
                                     created_at=MIRROR_REFERENCE_DATE))

    # ------------------------------------------------------------------
    # David Kim — grammar-focused learner
    # ------------------------------------------------------------------
    david = User(name='David Kim', email='david.k@test.com',
                 password_hash=PINNED_HASHES['david.k@test.com'],
                 created_at=MIRROR_REFERENCE_DATE)
    db.session.add(david)
    db.session.flush()

    david_saved_slugs = ['ameliorate', 'concatenate', 'unblemished',
                         'euphoria', 'reverie', 'innovation']
    for slug in david_saved_slugs:
        w = _get_word(slug)
        if w:
            db.session.add(SavedWord(user_id=david.id, word_id=w.id,
                                     created_at=MIRROR_REFERENCE_DATE))

    david_searches = ['articles grammar', 'indirect speech', 'comparative adjectives',
                      'ameliorate', 'euphoria', 'affect vs effect']
    for term in david_searches:
        db.session.add(SearchHistory(user_id=david.id, term=term,
                                     created_at=MIRROR_REFERENCE_DATE))

    db.session.commit()
    print('Benchmark users seeded.')


# ---------------------------------------------------------------------------
# App startup
# ---------------------------------------------------------------------------

with app.app_context():
    db.create_all()
    seed_database()
    seed_benchmark_users()


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)

# This is intentionally empty - context processor added below
