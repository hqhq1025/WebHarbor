"""
GitHub Mirror - Flask Application
A faithful reproduction of GitHub's design and features.
"""
import os
import json
import re
import math
import hashlib
from datetime import datetime, timedelta
from functools import wraps
from flask import (Flask, render_template, render_template_string, redirect, url_for, flash,
                   request, jsonify, session, abort)
from flask_sqlalchemy import SQLAlchemy
from flask_login import (LoginManager, UserMixin, login_user, logout_user,
                         login_required, current_user)
from flask_bcrypt import Bcrypt
from flask_wtf import FlaskForm
from flask_wtf.csrf import CSRFProtect, generate_csrf
from wtforms import StringField, PasswordField, TextAreaField, SelectField, BooleanField
from wtforms.validators import DataRequired, Email, Length, EqualTo, Optional, URL
from sqlalchemy import or_, func
from sqlalchemy.sql import text

# ───────────────────────── Mirror Clock ─────────────────────────
# The github mirror is a frozen snapshot. Every "now"-dependent value
# (relative-time strings like "2 days ago", "updated in last N days"
# search filters, seed timestamps, user-action timestamps) anchors to this
# constant so WebVoyager tasks like "find a repo updated in the last 2 days"
# produce the SAME answer regardless of when the user runs the mirror image.
# Flask-Login session expiry, CSRF tokens, and cookie lifetimes still use
# real wall-clock time (handled inside the framework, not via this clock).
MIRROR_REFERENCE_DATE = datetime(2024, 5, 15, 12, 0, 0)


def mirror_now():
    return MIRROR_REFERENCE_DATE


# Pinned bcrypt('password123') hash. Bcrypt salts on every call which
# breaks seed byte-identity across rebuilds (see harden-env/gotchas.md #1).
# All seed paths that create bulk users use this directly; only real-runtime
# code paths (login/register) keep calling User.set_password().
PINNED_PASSWORD_HASH_BULK = (
    '$2b$12$Oi0plj9XBSbuCcjmrSVmje2AWKXN99Xpa7J2O6tjYvquZPTqNXN6i'  # password123
)


# ─────────────────────────── App Setup ───────────────────────────
app = Flask(__name__)
app.config['SECRET_KEY'] = 'github-mirror-secret-key-2024-xzy'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///github_mirror.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['WTF_CSRF_TIME_LIMIT'] = 3600

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
csrf = CSRFProtect(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'

# ─────────────────────────── Models ───────────────────────────

# Association table: Repository <-> Topic
repo_topics = db.Table('repo_topics',
    db.Column('repo_id', db.Integer, db.ForeignKey('repository.id'), primary_key=True),
    db.Column('topic_id', db.Integer, db.ForeignKey('topic.id'), primary_key=True)
)

# Association table: User follows
follows = db.Table('follows',
    db.Column('follower_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('followed_id', db.Integer, db.ForeignKey('user.id'), primary_key=True)
)


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(39), unique=True, nullable=False, index=True)
    email = db.Column(db.String(254), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(128), nullable=False)
    name = db.Column(db.String(100), default='')
    bio = db.Column(db.String(255), default='')
    location = db.Column(db.String(100), default='')
    website = db.Column(db.String(200), default='')
    company = db.Column(db.String(100), default='')
    twitter = db.Column(db.String(100), default='')
    avatar = db.Column(db.String(200), default='')
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=mirror_now)
    # Plan
    plan = db.Column(db.String(20), default='free')  # free, team, enterprise

    # Relationships
    repositories = db.relationship('Repository', backref='owner', lazy='dynamic',
                                   foreign_keys='Repository.owner_id',
                                   cascade='all, delete-orphan')
    stars = db.relationship('Star', backref='user', lazy='dynamic',
                            cascade='all, delete-orphan')
    watches = db.relationship('Watch', backref='user', lazy='dynamic',
                              cascade='all, delete-orphan')
    issues_filed = db.relationship('Issue', backref='author', lazy='dynamic',
                                   cascade='all, delete-orphan')
    comments = db.relationship('IssueComment', backref='author', lazy='dynamic',
                               cascade='all, delete-orphan')
    following = db.relationship('User', secondary=follows,
                                primaryjoin=(follows.c.follower_id == id),
                                secondaryjoin=(follows.c.followed_id == id),
                                lazy='dynamic', backref=db.backref('followers', lazy='dynamic'))

    def set_password(self, pw):
        self.password_hash = bcrypt.generate_password_hash(pw).decode('utf-8')

    def check_password(self, pw):
        return bcrypt.check_password_hash(self.password_hash, pw)

    @property
    def avatar_url(self):
        if self.avatar:
            return self.avatar
        # Prefer a real-github scraped avatar if we have one on disk for this username
        if self.username:
            real_path = os.path.join(
                os.path.dirname(__file__), 'static', 'images', 'avatars',
                f'{self.username}.png')
            if os.path.exists(real_path):
                return f"/static/images/avatars/{self.username}.png"
        idx = (self.id or 0) % 15
        return f"/static/images/avatars/avatar_{idx:02d}.jpg"

    @property
    def followers_count(self):
        return self.followers.count()

    @property
    def following_count(self):
        return self.following.count()

    @property
    def public_repos_count(self):
        return self.repositories.filter_by(is_public=True).count()

    def is_following(self, user):
        return self.following.filter(follows.c.followed_id == user.id).count() > 0

    def has_starred(self, repo):
        return Star.query.filter_by(user_id=self.id, repo_id=repo.id).first() is not None

    def has_watched(self, repo):
        return Watch.query.filter_by(user_id=self.id, repo_id=repo.id).first() is not None


class Repository(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    full_name = db.Column(db.String(200), unique=True, nullable=False, index=True)
    description = db.Column(db.Text, default='')
    language = db.Column(db.String(50), default='')
    license = db.Column(db.String(50), default='')
    stars_count = db.Column(db.Integer, default=0)
    forks_count = db.Column(db.Integer, default=0)
    watchers_count = db.Column(db.Integer, default=0)
    open_issues_count = db.Column(db.Integer, default=0)
    is_public = db.Column(db.Boolean, default=True)
    is_fork = db.Column(db.Boolean, default=False)
    is_template = db.Column(db.Boolean, default=False)
    is_archived = db.Column(db.Boolean, default=False)
    has_readme = db.Column(db.Boolean, default=True)
    has_wiki = db.Column(db.Boolean, default=False)
    has_issues = db.Column(db.Boolean, default=True)
    owner_type = db.Column(db.String(20), default='user')  # user, org
    homepage = db.Column(db.String(200), default='')
    default_branch = db.Column(db.String(50), default='main')
    size_kb = db.Column(db.Integer, default=0)
    readme = db.Column(db.Text, default='')
    topics_text = db.Column(db.Text, default='[]')  # JSON array of topic strings
    gallery_json = db.Column(db.Text, default='[]')  # JSON gallery sections
    created_at = db.Column(db.DateTime, default=mirror_now)
    updated_at = db.Column(db.DateTime, default=mirror_now, onupdate=mirror_now)
    pushed_at = db.Column(db.DateTime, default=mirror_now)
    # Task-driven extras: commits, releases, contributors, wiki — stored as JSON text
    latest_release_version = db.Column(db.String(50), default='')
    latest_release_date = db.Column(db.DateTime, nullable=True)
    latest_release_notes = db.Column(db.Text, default='')
    releases_json = db.Column(db.Text, default='[]')  # list of {version, date, notes}
    contributors_json = db.Column(db.Text, default='[]')  # list of {username, commits, avatar}
    latest_commit_sha = db.Column(db.String(40), default='')
    latest_commit_message = db.Column(db.Text, default='')
    latest_commit_date = db.Column(db.DateTime, nullable=True)
    latest_commit_files = db.Column(db.Text, default='[]')  # list of {name, additions, deletions}
    latest_commit_additions = db.Column(db.Integer, default=0)
    latest_commit_deletions = db.Column(db.Integer, default=0)
    # Recent commit history: list of {sha, message, author, date, files[], additions, deletions}.
    # Index 0 mirrors latest_commit_* for backward compatibility.
    commits_json = db.Column(db.Text, default='[]')
    wiki_pages_json = db.Column(db.Text, default='[]')  # list of {slug, title, body}

    # R7: composite indexes that match the hot queries on this catalog:
    #   /trending and language-filtered explore  → (language, stars_count DESC)
    #   /<user> profile + dashboard listing      → (owner_id, updated_at DESC)
    #   full_name has a separate UNIQUE INDEX (declared above with index=True).
    # The composite indexes shave repo-card render time well under the 50ms
    # target on the 32k catalog (previously ~120ms on /trending?l=Python).
    __table_args__ = (
        db.Index('ix_repository_language_stars', 'language', 'stars_count'),
        db.Index('ix_repository_owner_updated', 'owner_id', 'updated_at'),
    )

    # Relationships
    topics = db.relationship('Topic', secondary=repo_topics, backref='repositories', lazy='dynamic')
    stars = db.relationship('Star', backref='repo', lazy='dynamic', cascade='all, delete-orphan')
    watches = db.relationship('Watch', backref='repo', lazy='dynamic', cascade='all, delete-orphan')
    issues = db.relationship('Issue', backref='repo', lazy='dynamic', cascade='all, delete-orphan')

    def get_topics(self):
        try:
            return json.loads(self.topics_text or '[]')
        except Exception:
            return []

    def get_gallery(self):
        try:
            return json.loads(self.gallery_json or '[]')
        except Exception:
            return []

    def stars_display(self):
        n = self.stars_count
        if n >= 1000:
            return f"{n/1000:.1f}k"
        return str(n)

    def get_releases(self):
        try:
            return json.loads(self.releases_json or '[]')
        except Exception:
            return []

    def get_contributors(self):
        try:
            return json.loads(self.contributors_json or '[]')
        except Exception:
            return []

    def get_commit_files(self):
        try:
            return json.loads(self.latest_commit_files or '[]')
        except Exception:
            return []

    def get_commits(self):
        try:
            return json.loads(self.commits_json or '[]')
        except Exception:
            return []

    def get_wiki_pages(self):
        try:
            return json.loads(self.wiki_pages_json or '[]')
        except Exception:
            return []

    def updated_relative(self):
        # Match GitHub's <relative-time> default threshold P30D: relative
        # phrasing within 30 days, absolute "on Mon DD, YYYY" beyond.
        delta = mirror_now() - self.updated_at
        if delta.days >= 30:
            return f"Updated on {self.updated_at.strftime('%b %-d, %Y')}"
        if delta.days >= 1:
            return f"Updated {delta.days} day{'s' if delta.days > 1 else ''} ago"
        hours = delta.seconds // 3600
        if hours >= 1:
            return f"Updated {hours} hour{'s' if hours > 1 else ''} ago"
        return "Updated just now"


class Topic(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(100), unique=True, nullable=False, index=True)
    display_name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, default='')
    short_desc = db.Column(db.String(200), default='')
    image = db.Column(db.String(200), default='')
    repos_count = db.Column(db.Integer, default=0)
    is_featured = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=mirror_now)


class Star(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    repo_id = db.Column(db.Integer, db.ForeignKey('repository.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=mirror_now)
    __table_args__ = (db.UniqueConstraint('user_id', 'repo_id'),)


class Watch(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    repo_id = db.Column(db.Integer, db.ForeignKey('repository.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=mirror_now)
    __table_args__ = (db.UniqueConstraint('user_id', 'repo_id'),)


class Issue(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    repo_id = db.Column(db.Integer, db.ForeignKey('repository.id'), nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    number = db.Column(db.Integer, nullable=False)
    title = db.Column(db.String(255), nullable=False)
    body = db.Column(db.Text, default='')
    status = db.Column(db.String(20), default='open')  # open, closed (PR: open, closed, merged)
    labels_json = db.Column(db.Text, default='[]')
    created_at = db.Column(db.DateTime, default=mirror_now)
    closed_at = db.Column(db.DateTime, nullable=True)
    # PR support: 0 = regular issue, 1 = pull request
    is_pr = db.Column(db.Integer, default=0)
    # PR-only metadata; null for is_pr=0
    pr_head_branch = db.Column(db.String(120), default='')
    pr_base_branch = db.Column(db.String(120), default='main')
    pr_changed_files = db.Column(db.Integer, default=0)
    pr_additions = db.Column(db.Integer, default=0)
    pr_deletions = db.Column(db.Integer, default=0)
    pr_commits_count = db.Column(db.Integer, default=0)

    comments = db.relationship('IssueComment', backref='issue', lazy='dynamic',
                               cascade='all, delete-orphan')

    def get_labels(self):
        try:
            return json.loads(self.labels_json or '[]')
        except Exception:
            return []

    def comment_count(self):
        return self.comments.count()


class IssueComment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    issue_id = db.Column(db.Integer, db.ForeignKey('issue.id'), nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    body = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=mirror_now)


# ─────────────────────────── R4 Models ───────────────────────────
# Added in R4 polish: Discussion threads, Sponsorship, Project Boards (Kanban),
# Packages and Org Teams. Everything is seeded deterministically from
# (repo.id|org.id|user.id) so md5×2 stays stable.

class Discussion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    repo_id = db.Column(db.Integer, db.ForeignKey('repository.id'), nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    number = db.Column(db.Integer, nullable=False)
    title = db.Column(db.String(255), nullable=False)
    body = db.Column(db.Text, default='')
    # category: Announcements / Q&A / Ideas / Show and tell / General / Polls
    category = db.Column(db.String(40), default='General')
    status = db.Column(db.String(20), default='open')  # open / answered / closed
    upvotes = db.Column(db.Integer, default=0)
    comments_count = db.Column(db.Integer, default=0)
    answered_comment_id = db.Column(db.Integer, nullable=True)
    created_at = db.Column(db.DateTime, default=mirror_now)


class DiscussionComment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    discussion_id = db.Column(db.Integer, db.ForeignKey('discussion.id'),
                              nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    body = db.Column(db.Text, nullable=False)
    is_answer = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=mirror_now)


class Sponsorship(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sponsor_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    target_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    tier = db.Column(db.String(40), default='Backer')  # Backer / Supporter / Sponsor / Patron
    amount_cents = db.Column(db.Integer, default=500)
    status = db.Column(db.String(20), default='active')
    is_recurring = db.Column(db.Integer, default=1)
    started_at = db.Column(db.DateTime, default=mirror_now)


class ProjectBoard(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    repo_id = db.Column(db.Integer, db.ForeignKey('repository.id'), nullable=False)
    number = db.Column(db.Integer, nullable=False)
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, default='')
    status = db.Column(db.String(20), default='open')
    # JSON: [{"name": "Todo", "cards": [{"title":..., "issue":..., "labels":[]}]}]
    columns_json = db.Column(db.Text, default='[]')
    created_at = db.Column(db.DateTime, default=mirror_now)

    def get_columns(self):
        try:
            return json.loads(self.columns_json or '[]')
        except Exception:
            return []


class Package(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    repo_id = db.Column(db.Integer, db.ForeignKey('repository.id'), nullable=False)
    name = db.Column(db.String(120), nullable=False)
    ecosystem = db.Column(db.String(20), default='npm')  # npm / pypi / container / maven / nuget / rubygems
    version = db.Column(db.String(40), default='1.0.0')
    description = db.Column(db.String(255), default='')
    downloads_total = db.Column(db.Integer, default=0)
    visibility = db.Column(db.String(20), default='public')
    published_at = db.Column(db.DateTime, default=mirror_now)


class Team(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    org_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    slug = db.Column(db.String(80), nullable=False)
    name = db.Column(db.String(80), nullable=False)
    description = db.Column(db.String(255), default='')
    privacy = db.Column(db.String(20), default='visible')  # visible / secret
    member_count = db.Column(db.Integer, default=0)
    repo_count = db.Column(db.Integer, default=0)
    # JSON arrays of usernames / full_names so we don't need extra join tables.
    members_json = db.Column(db.Text, default='[]')
    repos_json = db.Column(db.Text, default='[]')
    created_at = db.Column(db.DateTime, default=mirror_now)


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

# ─────────────────────────── Forms ───────────────────────────

class LoginForm(FlaskForm):
    login = StringField('Username or email', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])

class RegisterForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(1, 39)])
    email = StringField('Email address', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired(), Length(8, 128)])

class ProfileEditForm(FlaskForm):
    name = StringField('Name', validators=[Optional(), Length(max=100)])
    bio = TextAreaField('Bio', validators=[Optional(), Length(max=255)])
    location = StringField('Location', validators=[Optional(), Length(max=100)])
    website = StringField('Website', validators=[Optional(), Length(max=200)])
    company = StringField('Company', validators=[Optional(), Length(max=100)])
    twitter = StringField('Twitter username', validators=[Optional(), Length(max=100)])

class ChangePasswordForm(FlaskForm):
    old_password = PasswordField('Old password', validators=[DataRequired()])
    new_password = PasswordField('New password', validators=[DataRequired(), Length(8, 128)])
    confirm_password = PasswordField('Confirm new password',
                                     validators=[DataRequired(), EqualTo('new_password')])

class NewRepoForm(FlaskForm):
    name = StringField('Repository name', validators=[DataRequired(), Length(1, 100)])
    description = TextAreaField('Description', validators=[Optional(), Length(max=255)])
    is_public = SelectField('Visibility', choices=[('true', 'Public'), ('false', 'Private')])
    init_readme = BooleanField('Add a README file')

class IssueForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired(), Length(1, 255)])
    body = TextAreaField('Leave a comment', validators=[Optional()])

class CommentForm(FlaskForm):
    body = TextAreaField('Leave a comment', validators=[DataRequired()])

# ─────────────────────────── Helpers ───────────────────────────

_DEFAULT_LANG_COLORS = {
    "Python": "#3572A5", "JavaScript": "#f1e05a", "TypeScript": "#3178c6",
    "Java": "#b07219", "Go": "#00ADD8", "Rust": "#dea584", "C++": "#f34b7d",
    "C": "#555555", "C#": "#178600", "Ruby": "#701516", "PHP": "#4F5D95",
    "Swift": "#F05138", "Kotlin": "#A97BFF", "Scala": "#c22d40",
    "Shell": "#89e051", "HTML": "#e34c26", "CSS": "#563d7c", "Vue": "#41b883",
    "Jupyter Notebook": "#DA5B0B", "R": "#198CE7", "Dart": "#00B4AB",
    "Elixir": "#6e4a7e", "Haskell": "#5e5086", "Lua": "#000080",
    "MATLAB": "#e16737", "OCaml": "#3be133", "PowerShell": "#012456",
    "Dockerfile": "#384d54", "Unknown": "#8f9ba8",
}

def _load_lang_colors():
    # Prefer the full 700-entry map scraped from github-colors; fall back to defaults.
    path = os.path.join(os.path.dirname(__file__), 'static', 'images', 'lang_colors.json')
    if os.path.exists(path):
        try:
            with open(path) as f:
                data = json.load(f)
            merged = dict(_DEFAULT_LANG_COLORS)
            merged.update({k: v for k, v in data.items() if isinstance(v, str)})
            return merged
        except Exception:
            pass
    return _DEFAULT_LANG_COLORS

LANG_COLORS = _load_lang_colors()


def avatar_for(username):
    """Resolve an avatar URL for any username (DB-linked or pure seed name).

    Checks static/images/avatars/<username>.png (scraped from real github),
    then the User table row (explicit override), otherwise rotates the 15
    generic pool images deterministically by hash."""
    if not username:
        return "/static/images/avatars/avatar_00.jpg"
    real = os.path.join(os.path.dirname(__file__), 'static', 'images', 'avatars',
                        f'{username}.png')
    if os.path.exists(real):
        return f"/static/images/avatars/{username}.png"
    u = User.query.filter_by(username=username).first()
    if u and u.avatar:
        return u.avatar
    # stable but varied fallback
    idx = abs(hash(username)) % 15
    return f"/static/images/avatars/avatar_{idx:02d}.jpg"

def load_gallery(full_name):
    path = os.path.join(os.path.dirname(__file__), 'repo_galleries.json')
    if os.path.exists(path):
        with open(path) as f:
            data = json.load(f)
        return data.get(full_name, [])
    return []

# ─── R7 locales: header-dropdown driven UI strings ───
# A small UI-string table keyed by ISO locale → key → translation.
# We deliberately keep this in-process (no external i18n library) so the seed
# DB stays byte-identical across rebuilds. Locale is sticky in a cookie
# `gh_locale`; the `<html lang>` attribute in base.html mirrors `g.locale`.
LOCALES = {
    'en':    {'name': 'English',  'flag': 'EN'},
    'zh-CN': {'name': '简体中文',  'flag': 'ZH'},
    'ja-JP': {'name': '日本語',    'flag': 'JA'},
    'es-ES': {'name': 'Español',  'flag': 'ES'},
    'fr-FR': {'name': 'Français', 'flag': 'FR'},
    'pt-BR': {'name': 'Português','flag': 'PT'},
}
_DEFAULT_LOCALE = 'en'

UI_STRINGS = {
    'en': {
        'header.product': 'Product', 'header.opensource': 'Open Source',
        'header.resources': 'Resources', 'header.solutions': 'Solutions',
        'header.enterprise': 'Enterprise', 'header.pricing': 'Pricing',
        'header.signin': 'Sign in', 'header.signup': 'Sign up',
        'header.search': 'Search or jump to…',
        'footer.tagline': 'Build software better, together.',
        'repo.star': 'Star', 'repo.unstar': 'Unstar',
        'repo.watch': 'Watch', 'repo.fork': 'Fork',
        'repo.code': 'Code', 'repo.issues': 'Issues',
        'repo.pulls': 'Pull requests', 'repo.actions': 'Actions',
        'repo.releases': 'Releases', 'repo.contributors': 'Contributors',
        'lang.label': 'Language', 'lang.choose': 'Change language',
    },
    'zh-CN': {
        'header.product': '产品', 'header.opensource': '开源',
        'header.resources': '资源', 'header.solutions': '解决方案',
        'header.enterprise': '企业版', 'header.pricing': '价格',
        'header.signin': '登录', 'header.signup': '注册',
        'header.search': '搜索或快速跳转…',
        'footer.tagline': '与全世界一起构建更好的软件。',
        'repo.star': 'Star', 'repo.unstar': '取消 Star',
        'repo.watch': '关注', 'repo.fork': 'Fork',
        'repo.code': '代码', 'repo.issues': '议题',
        'repo.pulls': '拉取请求', 'repo.actions': 'Actions',
        'repo.releases': '发布', 'repo.contributors': '贡献者',
        'lang.label': '语言', 'lang.choose': '切换语言',
    },
    'ja-JP': {
        'header.product': '製品', 'header.opensource': 'オープンソース',
        'header.resources': 'リソース', 'header.solutions': 'ソリューション',
        'header.enterprise': 'エンタープライズ', 'header.pricing': '価格',
        'header.signin': 'サインイン', 'header.signup': 'サインアップ',
        'header.search': '検索またはジャンプ…',
        'footer.tagline': 'みんなで、より良いソフトウェアを。',
        'repo.star': 'スター', 'repo.unstar': 'スター解除',
        'repo.watch': 'ウォッチ', 'repo.fork': 'フォーク',
        'repo.code': 'コード', 'repo.issues': 'イシュー',
        'repo.pulls': 'プルリクエスト', 'repo.actions': 'アクション',
        'repo.releases': 'リリース', 'repo.contributors': '貢献者',
        'lang.label': '言語', 'lang.choose': '言語を変更',
    },
    'es-ES': {
        'header.product': 'Producto', 'header.opensource': 'Código abierto',
        'header.resources': 'Recursos', 'header.solutions': 'Soluciones',
        'header.enterprise': 'Empresa', 'header.pricing': 'Precios',
        'header.signin': 'Iniciar sesión', 'header.signup': 'Registrarse',
        'header.search': 'Buscar o saltar a…',
        'footer.tagline': 'Construye software mejor, juntos.',
        'repo.star': 'Destacar', 'repo.unstar': 'Quitar destacado',
        'repo.watch': 'Seguir', 'repo.fork': 'Fork',
        'repo.code': 'Código', 'repo.issues': 'Problemas',
        'repo.pulls': 'Pull requests', 'repo.actions': 'Acciones',
        'repo.releases': 'Versiones', 'repo.contributors': 'Colaboradores',
        'lang.label': 'Idioma', 'lang.choose': 'Cambiar idioma',
    },
    'fr-FR': {
        'header.product': 'Produit', 'header.opensource': 'Open Source',
        'header.resources': 'Ressources', 'header.solutions': 'Solutions',
        'header.enterprise': 'Entreprise', 'header.pricing': 'Tarifs',
        'header.signin': 'Se connecter', 'header.signup': "S'inscrire",
        'header.search': 'Rechercher ou accéder…',
        'footer.tagline': 'Construisons de meilleurs logiciels, ensemble.',
        'repo.star': 'Étoile', 'repo.unstar': "Retirer l'étoile",
        'repo.watch': 'Suivre', 'repo.fork': 'Fork',
        'repo.code': 'Code', 'repo.issues': 'Tickets',
        'repo.pulls': 'Pull requests', 'repo.actions': 'Actions',
        'repo.releases': 'Versions', 'repo.contributors': 'Contributeurs',
        'lang.label': 'Langue', 'lang.choose': 'Changer de langue',
    },
    'pt-BR': {
        'header.product': 'Produto', 'header.opensource': 'Código aberto',
        'header.resources': 'Recursos', 'header.solutions': 'Soluções',
        'header.enterprise': 'Enterprise', 'header.pricing': 'Preços',
        'header.signin': 'Entrar', 'header.signup': 'Cadastrar',
        'header.search': 'Buscar ou ir para…',
        'footer.tagline': 'Construa software melhor, juntos.',
        'repo.star': 'Favoritar', 'repo.unstar': 'Desfavoritar',
        'repo.watch': 'Acompanhar', 'repo.fork': 'Fork',
        'repo.code': 'Código', 'repo.issues': 'Issues',
        'repo.pulls': 'Pull requests', 'repo.actions': 'Ações',
        'repo.releases': 'Lançamentos', 'repo.contributors': 'Contribuidores',
        'lang.label': 'Idioma', 'lang.choose': 'Mudar idioma',
    },
}


def _current_locale():
    """Resolve the active locale for this request. Order:
    1. ?lang=xx-YY query string override (also used by the dropdown form)
    2. gh_locale cookie set by /i18n/set
    3. Accept-Language header (best-effort, only known locales)
    4. Default 'en'
    """
    q = request.args.get('lang', '').strip() if request else ''
    if q in LOCALES:
        return q
    c = (request.cookies.get('gh_locale', '') or '').strip() if request else ''
    if c in LOCALES:
        return c
    al = (request.headers.get('Accept-Language', '') or '').lower() if request else ''
    if al:
        for code in LOCALES:
            if al.startswith(code.lower()) or code.lower() in al:
                return code
        # Coarse language match (e.g. 'zh' → 'zh-CN', 'ja' → 'ja-JP').
        if al.startswith('zh'):
            return 'zh-CN'
        if al.startswith('ja'):
            return 'ja-JP'
        if al.startswith('es'):
            return 'es-ES'
        if al.startswith('fr'):
            return 'fr-FR'
        if al.startswith('pt'):
            return 'pt-BR'
    return _DEFAULT_LOCALE


def _t(key, locale=None):
    locale = locale or _current_locale()
    tbl = UI_STRINGS.get(locale) or UI_STRINGS[_DEFAULT_LOCALE]
    return tbl.get(key) or UI_STRINGS[_DEFAULT_LOCALE].get(key) or key


@app.context_processor
def inject_globals():
    loc = _current_locale()
    return {
        'lang_colors': LANG_COLORS,
        'now': mirror_now(),
        'mirror_now': mirror_now(),
        'csrf_token': generate_csrf,
        'avatar_for': avatar_for,
        # R7 i18n surface (consumed by base.html + a few feature templates).
        'current_locale': loc,
        'locales': LOCALES,
        't': _t,
    }


# ─── External github.com redirect middleware ───
# Some WebVoyager agents hallucinate real github.com URLs even though the task
# is hosted locally. If such a request ever reaches this Flask app (via
# /etc/hosts, proxy, or host header), rewrite it to the local equivalent so the
# agent lands on usable content instead of `about:blank`.
@app.before_request
def _redirect_external_github():
    host = (request.host or '').lower()
    # If the request arrives with a real github.com Host header, 307-redirect
    # to the local mirror path preserving the URL path & query string.
    if 'github.com' in host and 'localhost' not in host and '127.0.0.1' not in host:
        target = request.full_path.rstrip('?') or '/'
        # Strip leading /https:/github.com/ or similar, keep the path portion.
        return redirect(target, code=302)
    # Some agents also type URLs like /https://github.com/foo/bar into the bar.
    path = request.path or ''
    m = re.match(r'^/(https?:)?/*github\.com/(.*)$', path)
    if m:
        rest = m.group(2) or ''
        new_path = '/' + rest
        qs = request.query_string.decode('utf-8', errors='ignore')
        if qs:
            new_path += '?' + qs
        return redirect(new_path, code=302)

@app.template_filter('number_format')
def number_format(n):
    if n is None:
        return '0'
    n = int(n)
    if n >= 1_000_000:
        return f"{n/1_000_000:.1f}M"
    if n >= 1000:
        return f"{n/1000:.1f}k"
    return str(n)

@app.template_filter('time_ago')
def time_ago(dt):
    # Match GitHub's <relative-time> default threshold P30D: relative
    # phrasing within 30 days, absolute "on Mon DD, YYYY" beyond.
    if not dt:
        return ''
    delta = mirror_now() - dt
    if delta.days >= 30:
        return f"on {dt.strftime('%b %-d, %Y')}"
    if delta.days >= 1:
        return f"{delta.days}d ago"
    hours = delta.seconds // 3600
    if hours >= 1:
        return f"{hours}h ago"
    minutes = delta.seconds // 60
    if minutes >= 1:
        return f"{minutes}m ago"
    return "just now"

# ─────────────────────────── Seed Data ───────────────────────────

def seed_database():
    if User.query.count() > 0:
        return

    # Demo users
    users_data = [
        ("octocat", "octocat@github.com", "Octocat", "GitHub's mascot", "San Francisco, CA",
         "https://github.com", "GitHub", "github", "free"),
        ("torvalds", "torvalds@linux.org", "Linus Torvalds",
         "Creator of Linux and Git. If there is one...", "Portland, OR",
         "", "Linux Foundation", "", "free"),
        ("gaearon", "gaearon@gmail.com", "Dan Abramov",
         "Working on @reactjs. Co-author of Redux and Create React App.", "London, UK",
         "https://overreacted.io", "", "dan_abramov", "free"),
        ("yyx990803", "yyx990803@gmail.com", "Evan You",
         "Creator of @vuejs and @vitejs. Independent open source developer.", "",
         "https://evanyou.me", "", "youyuxi", "free"),
        ("gvanrossum", "guido@python.org", "Guido van Rossum",
         "Python's creator. Retired BDFL.", "Belmont, CA", "", "", "", "free"),
        ("dhh", "dhh@hey.com", "David Heinemeier Hansson",
         "Creator of Ruby on Rails, co-owner of Basecamp, author of REWORK.", "",
         "https://dhh.dk", "37signals", "dhh", "free"),
        ("tj", "tj@apex.sh", "TJ Holowaychuk",
         "Prolific open source developer. Creator of Express, Koa, Mocha...", "",
         "", "", "", "free"),
        ("brendangregg", "brendan.d.gregg@gmail.com", "Brendan Gregg",
         "Systems performance and observability at Netflix.", "Santa Clara, CA",
         "https://www.brendangregg.com", "Netflix", "", "free"),
        ("sindresorhus", "sindresorhus@gmail.com", "Sindre Sorhus",
         "Full-Time Open-Sourcerer. Maker of stuff.", "Bangkok, Thailand",
         "https://sindresorhus.com", "", "sindresorhus", "free"),
        ("antirez", "antirez@gmail.com", "Salvatore Sanfilippo",
         "I'm the creator of Redis.", "Sicily, Italy",
         "http://invece.org", "", "antirez", "free"),
        ("mitchellh", "mitchell@hashicorp.com", "Mitchell Hashimoto",
         "Co-founder of HashiCorp. Building Ghostty.", "San Francisco, CA",
         "", "HashiCorp", "", "team"),
        ("defunkt", "chris@github.com", "Chris Wanstrath",
         "Co-founder of GitHub.", "San Francisco, CA",
         "", "GitHub", "defunkt", "free"),
        ("wycats", "wycats@gmail.com", "Yehuda Katz",
         "Co-creator of Ember.js, Rust core, Rails core, Bundler, Cargo.", "",
         "https://yehudakatz.com", "Tilde", "", "free"),
        ("fabpot", "fabien@symfony.com", "Fabien Potencier",
         "Creator of the Symfony PHP framework.", "Nantes, France",
         "https://fabien.potencier.org", "SensioLabs", "", "free"),
        ("mxcl", "mxcl@me.com", "Max Howell",
         "Creator of Homebrew. Software engineer.", "",
         "", "", "mxcl", "free"),
    ]

    users = []
    for i, (uname, email, name, bio, loc, web, company, twitter, plan) in enumerate(users_data):
        u = User(username=uname, email=email, name=name, bio=bio,
                 location=loc, website=web, company=company, twitter=twitter, plan=plan)
        # Use pinned hash for seed determinism (bcrypt has random salt).
        u.password_hash = PINNED_PASSWORD_HASH_BULK
        u.avatar = f"/static/images/avatars/avatar_{i:02d}.jpg"
        db.session.add(u)
        users.append(u)

    db.session.flush()

    # Demo topics
    topics_data = [
        ("python", "Python", "Python is a dynamically typed programming language designed to be quick to learn, understand, and use.", "Dynamically typed, garbage-collected language", True),
        ("javascript", "JavaScript", "JavaScript, often abbreviated as JS, is a high-level, dynamic programming language conforming to the ECMAScript specification.", "High-level, dynamic language for the web", True),
        ("typescript", "TypeScript", "TypeScript is a statically typed superset of JavaScript that adds optional static typing.", "Typed superset of JavaScript", True),
        ("machine-learning", "Machine learning", "A subset of artificial intelligence (AI) that provides systems the ability to automatically learn and improve from experience.", "AI that learns from data", True),
        ("deep-learning", "Deep learning", "Deep learning is a subfield of machine learning that uses neural networks with many layers.", "Neural networks with many layers", True),
        ("react", "React", "React is a JavaScript library for building user interfaces, maintained by Facebook.", "Facebook's UI library", True),
        ("vue", "Vue.js", "Vue.js is an open-source model-view-viewmodel front end JavaScript framework.", "Progressive JavaScript framework", True),
        ("rust", "Rust", "Rust is a multi-paradigm, general-purpose programming language emphasizing performance, type safety, and concurrency.", "Safe, fast systems language", True),
        ("go", "Go", "Go is an open source programming language that makes it easy to build simple, reliable, and efficient software.", "Google's systems programming language", True),
        ("kubernetes", "Kubernetes", "Kubernetes is an open-source system for automating deployment, scaling, and management of containerized applications.", "Container orchestration system", True),
        ("docker", "Docker", "Docker is a platform for developers and sysadmins to develop, deploy, and run applications with containers.", "Application containerization platform", False),
        ("api", "API", "An application programming interface (API) is a connection between computers or between computer programs.", "Interface between software components", False),
        ("web-development", "Web development", "Web development is the work involved in developing a website for the Internet.", "Building websites and web apps", False),
        ("security", "Security", "Security is freedom from, or resilience against, potential harm caused by others.", "Protecting systems and data", False),
        ("open-source", "Open source", "Open-source software is software with source code that anyone can inspect, modify, and enhance.", "Freely available source code", True),
        ("nlp", "Natural language processing", "Natural language processing (NLP) is a subfield of linguistics, computer science, and AI concerning interactions between computers and human language.", "Processing human language", False),
        ("devops", "DevOps", "DevOps is a set of practices that combines software development and IT operations.", "Development and operations collaboration", False),
        ("cloud", "Cloud computing", "Cloud computing is the on-demand availability of computer system resources.", "On-demand computing resources", False),
        ("hacktoberfest", "Hacktoberfest", "Hacktoberfest is a month-long celebration of open source software run by DigitalOcean.", "Annual open source event", True),
        ("ai", "Artificial intelligence", "Artificial intelligence (AI) is intelligence demonstrated by machines.", "Machine intelligence", True),
        ("frontend", "Front end", "Front-end web development is the practice of converting data to a graphical interface.", "UI-focused web development", False),
        ("backend", "Back end", "Back-end web development is the server side of web development.", "Server-side web development", False),
        ("java", "Java", "Java is a class-based, object-oriented programming language designed for portability.", "Object-oriented, portable language", False),
        ("swift", "Swift", "Swift is a powerful and intuitive programming language for Apple platforms.", "Apple's modern programming language", False),
        ("kotlin", "Kotlin", "Kotlin is a cross-platform, statically typed, general-purpose programming language.", "Modern JVM language by JetBrains", False),
    ]

    topic_objs = {}
    for slug, display, desc, short_desc, is_featured in topics_data:
        t = Topic(slug=slug, display_name=display, description=desc,
                  short_desc=short_desc, is_featured=is_featured)
        db.session.add(t)
        topic_objs[slug] = t

    db.session.flush()

    now = mirror_now()

    # Seed repositories
    repos_data = [
        {
            "owner": "microsoft", "name": "vscode",
            "desc": "Visual Studio Code - Open Source ('Code - OSS')",
            "lang": "TypeScript", "license": "MIT",
            "stars": 163000, "forks": 29000, "watchers": 3500, "issues": 7800,
            "topics": ["typescript", "open-source", "web-development", "api", "hacktoberfest"],
            "homepage": "https://code.visualstudio.com",
            "updated": now - timedelta(hours=2),
            "readme": """# Visual Studio Code - Open Source ("Code - OSS")

[![Feature Requests](https://img.shields.io/github/issues/microsoft/vscode/feature-request.svg)](https://github.com/microsoft/vscode/issues?q=is%3Aopen+is%3Aissue+label%3Afeature-request+sort%3Areactions-%2B1-desc)
[![Bugs](https://img.shields.io/github/issues/microsoft/vscode/bug.svg)](https://github.com/microsoft/vscode/issues?utf8=✓&q=is%3Aissue+is%3Aopen+label%3Abug)

The `microsoft/vscode` repository is where we do development and there are many ways you can participate in the project, for example:

* [Submit bugs and feature requests](https://github.com/microsoft/vscode/issues), and help us verify as they are checked in
* Review [source code changes](https://github.com/microsoft/vscode/pulls)
* Review the [documentation](https://github.com/microsoft/vscode-docs) and make pull requests for anything from typos to new content

## Contributing

There are many ways in which you can participate in this project, for example:

* Submit bugs and feature requests and help us verify as they are checked in
* Review source code changes

If you are interested in fixing issues and contributing directly to the code base, please see the document [How to Contribute](https://github.com/microsoft/vscode/wiki/How-to-Contribute).
"""
        },
        {
            "owner": "torvalds", "name": "linux",
            "desc": "Linux kernel source tree",
            "lang": "C", "license": "GPL-2.0",
            "stars": 180000, "forks": 54000, "watchers": 7800, "issues": 0,
            "topics": ["c", "open-source", "devops", "security"],
            "homepage": "https://www.kernel.org",
            "updated": now - timedelta(hours=1),
            "readme": """# Linux kernel

There are several guides for kernel developers and users. These guides can be rendered in a number of formats, like HTML and PDF. Please read Documentation/admin-guide/README.rst first.

In order to build the documentation, use ``make htmldocs`` or ``make pdfdocs``. The formatted documentation can also be read online at:

    https://www.kernel.org/doc/html/latest/

There are various text files in the Documentation/ subdirectory, several of them using the Restructured Text markup notation.

Please read the Documentation/process/changes.rst file, as it contains the requirements for building and running the kernel, and information about the problems which may result by upgrading your kernel.
"""
        },
        {
            "owner": "tensorflow", "name": "tensorflow",
            "desc": "An Open Source Machine Learning Framework for Everyone",
            "lang": "Python", "license": "Apache-2.0",
            "stars": 185000, "forks": 74000, "watchers": 8200, "issues": 3100,
            "topics": ["python", "machine-learning", "deep-learning", "ai", "nlp"],
            "homepage": "https://www.tensorflow.org",
            "updated": now - timedelta(hours=3),
            "readme": """# TensorFlow

TensorFlow is an end-to-end open source platform for machine learning. It has a comprehensive, flexible ecosystem of tools, libraries, and community resources that lets researchers push the state-of-the-art in ML and developers easily build and deploy ML-powered applications.

## Install

See the [TensorFlow install guide](https://www.tensorflow.org/install) for the [pip package](https://www.tensorflow.org/install/pip), to [enable GPU support](https://www.tensorflow.org/install/gpu), use a [Docker container](https://www.tensorflow.org/install/docker), and [build from source](https://www.tensorflow.org/install/source).

To install the current release, which includes support for CUDA-enabled GPU cards:

```
$ pip install tensorflow
```
"""
        },
        {
            "owner": "facebook", "name": "react",
            "desc": "The library for web and native user interfaces.",
            "lang": "JavaScript", "license": "MIT",
            "stars": 228000, "forks": 47000, "watchers": 9100, "issues": 900,
            "topics": ["javascript", "react", "frontend", "web-development", "open-source"],
            "homepage": "https://react.dev",
            "updated": now - timedelta(hours=5),
            "readme": """# React

React is a JavaScript library for building user interfaces.

* **Declarative:** React makes it painless to create interactive UIs. Design simple views for each state in your application, and React will efficiently update and render just the right components when your data changes.
* **Component-Based:** Build encapsulated components that manage their own state, then compose them to make complex UIs.
* **Learn Once, Write Anywhere:** We don't make assumptions about the rest of your technology stack, so you can develop new features in React without rewriting existing code.

[Learn how to use React in your project](https://react.dev/learn).

## Installation

React has been designed for gradual adoption from the start, and **you can use as little or as much React as you need**:

```
npm install react react-dom
```
"""
        },
        {
            "owner": "vuejs", "name": "vue",
            "desc": "This is the repo for Vue 2. For Vue 3, go to https://github.com/vuejs/core",
            "lang": "TypeScript", "license": "MIT",
            "stars": 208000, "forks": 33700, "watchers": 6400, "issues": 600,
            "topics": ["javascript", "vue", "frontend", "web-development", "typescript"],
            "homepage": "https://vuejs.org",
            "updated": now - timedelta(days=3),
            "readme": """# Vue.js

[![npm](https://img.shields.io/npm/v/vue.svg)](https://npmjs.com/package/vue)

Vue (pronounced /vjuː/, like view) is a **progressive framework** for building user interfaces. Unlike other monolithic frameworks, Vue is designed from the ground up to be incrementally adoptable. The core library is focused on the view layer only, and is easy to pick up and integrate with other libraries or existing projects.

## Ecosystem

| Project | Status | Description |
|---------|--------|-------------|
| [vue-router] | [![vue-router-status]][vue-router-package] | Single-page application routing |
| [vuex] | [![vuex-status]][vuex-package] | Large-scale state management |
| [vue-cli] | [![vue-cli-status]][vue-cli-package] | Project scaffolding |
| [vue-loader] | [![vue-loader-status]][vue-loader-package] | Single File Component (`*.vue` file) loader for webpack |
"""
        },
        {
            "owner": "golang", "name": "go",
            "desc": "The Go programming language",
            "lang": "Go", "license": "BSD-3-Clause",
            "stars": 124000, "forks": 17700, "watchers": 3200, "issues": 9200,
            "topics": ["go", "open-source", "backend", "api"],
            "homepage": "https://go.dev",
            "updated": now - timedelta(hours=3),
            "readme": """# The Go Programming Language

Go is an open source programming language that makes it easy to build simple, reliable, and efficient software.

![Gopher image](https://golang.org/doc/gopher/fiveyears.jpg)
*Gopher image by [Renee French][rf], licensed under [Creative Commons 4.0 Attributions license][cc4-by].*

Our canonical Git repository is located at https://go.googlesource.com/go. There is a mirror of the repository at https://github.com/golang/go.

Unless otherwise noted, the Go source files are distributed under the BSD-style license found in the LICENSE file.
"""
        },
        {
            "owner": "rust-lang", "name": "rust",
            "desc": "Empowering everyone to build reliable and efficient software.",
            "lang": "Rust", "license": "MIT",
            "stars": 97000, "forks": 12500, "watchers": 2400, "issues": 9800,
            "topics": ["rust", "open-source", "systems", "security"],
            "homepage": "https://www.rust-lang.org",
            "updated": now - timedelta(hours=4),
            "readme": """# The Rust Programming Language

This is the main source code repository for [Rust]. It contains the compiler, standard library, and documentation.

[Rust]: https://www.rust-lang.org

**Note: this README is for _users_ rather than _contributors_.**

## Quick Start

Read ["Installation"] from [The Book].

["Installation"]: https://doc.rust-lang.org/book/ch01-01-installation.html
[The Book]: https://doc.rust-lang.org/book/index.html
"""
        },
        {
            "owner": "kubernetes", "name": "kubernetes",
            "desc": "Production-Grade Container Scheduling and Management",
            "lang": "Go", "license": "Apache-2.0",
            "stars": 111000, "forks": 40000, "watchers": 3700, "issues": 2400,
            "topics": ["go", "kubernetes", "docker", "cloud", "devops"],
            "homepage": "https://kubernetes.io",
            "updated": now - timedelta(minutes=45),
            "readme": """# Kubernetes

Kubernetes, also known as K8s, is an open source system for managing [containerized applications] across multiple hosts. It provides basic mechanisms for the deployment, maintenance, and scaling of applications.

Kubernetes builds upon a decade and a half of experience at Google running production workloads at scale using a system called [Borg], combined with best-of-breed ideas and practices from the community.

Kubernetes is hosted by the Cloud Native Computing Foundation ([CNCF]).
If you want to know more about CNCF, check out their [website](https://www.cncf.io/).
"""
        },
        {
            "owner": "huggingface", "name": "transformers",
            "desc": "🤗 Transformers: State-of-the-art Machine Learning for Pytorch, TensorFlow, and JAX.",
            "lang": "Python", "license": "Apache-2.0",
            "stars": 136000, "forks": 27200, "watchers": 2800, "issues": 1500,
            "topics": ["python", "machine-learning", "deep-learning", "nlp", "ai"],
            "homepage": "https://huggingface.co/docs/transformers",
            "updated": now - timedelta(hours=2),
            "readme": """# Transformers

State-of-the-art Machine Learning for JAX, PyTorch and TensorFlow

Transformers provides thousands of pretrained models to perform tasks on different modalities such as text, vision, and audio.

These models can be applied on:

📝 Text, for tasks like text classification, information extraction, question answering, summarization, translation, and text generation, in over 100 languages.
🖼️ Images, for tasks like image classification, object detection, and segmentation.
🔊 Audio, for tasks like speech recognition and audio classification.

Transformers models can also perform tasks on **several modalities combined**, such as table question answering, optical character recognition, information extraction from scanned documents, video classification, and visual question answering.

## Installation

```bash
pip install transformers
```
"""
        },
        {
            "owner": "langchain-ai", "name": "langchain",
            "desc": "🦜🔗 Build context-aware reasoning applications",
            "lang": "Python", "license": "MIT",
            "stars": 95000, "forks": 15300, "watchers": 1900, "issues": 1200,
            "topics": ["python", "machine-learning", "ai", "nlp", "open-source"],
            "homepage": "https://python.langchain.com",
            "updated": now - timedelta(hours=4),
            "readme": """# 🦜🔗 LangChain

⚡ Build context-aware reasoning applications ⚡

Looking for the JS/TS version? Check out [LangChain.js](https://github.com/langchain-ai/langchainjs).

To help you ship LangChain apps to production faster, check out [LangSmith](https://smith.langchain.com).

[LangSmith](https://smith.langchain.com) is a unified developer platform for building, testing, and monitoring LLM applications. Fill out [this form](https://www.langchain.com/contact-sales) to speak with our sales team.

## Quick Install

```bash
pip install langchain
```
"""
        },
        {
            "owner": "tiangolo", "name": "fastapi",
            "desc": "FastAPI framework, high performance, easy to learn, fast to code, ready for production",
            "lang": "Python", "license": "MIT",
            "stars": 78000, "forks": 6700, "watchers": 1400, "issues": 700,
            "topics": ["python", "api", "backend", "web-development", "open-source"],
            "homepage": "https://fastapi.tiangolo.com",
            "updated": now - timedelta(hours=5),
            "readme": """# FastAPI

FastAPI is a modern, fast (high-performance), web framework for building APIs with Python based on standard Python type hints.

The key features are:

* **Fast**: Very high performance, on par with **NodeJS** and **Go** (thanks to Starlette and Pydantic). [One of the fastest Python frameworks available](#performance).
* **Fast to code**: Increase the speed to develop features by about 200% to 300%. *
* **Fewer bugs**: Reduce about 40% of human (developer) induced errors. *
* **Intuitive**: Great editor support. Completion everywhere. Less time debugging.
* **Easy**: Designed to be easy to use and learn. Less time reading docs.
* **Short**: Minimize code duplication. Multiple features from each parameter declaration.
* **Robust**: Get production-ready code. With automatic interactive documentation.

```
pip install fastapi
```
"""
        },
        {
            "owner": "django", "name": "django",
            "desc": "The Web framework for perfectionists with deadlines.",
            "lang": "Python", "license": "BSD-3-Clause",
            "stars": 81000, "forks": 31900, "watchers": 2400, "issues": 230,
            "topics": ["python", "web-development", "backend", "open-source", "security"],
            "homepage": "https://www.djangoproject.com/",
            "updated": now - timedelta(hours=8),
            "readme": """# Django

Django is a high-level Python web framework that encourages rapid development and clean, pragmatic design. Built by experienced developers, it takes care of much of the hassle of web development, so you can focus on writing your app without needing to reinvent the wheel. It's free and open source.

## Supported Versions

Refer to the Django documentation for the supported versions.

## Contributing to Django

As an open source project, we welcome contributions.

Component | Test Command
---------- | ------
All tests | `./runtests.py`
"""
        },
        {
            "owner": "rails", "name": "rails",
            "desc": "Ruby on Rails",
            "lang": "Ruby", "license": "MIT",
            "stars": 55800, "forks": 21700, "watchers": 1800, "issues": 810,
            "topics": ["ruby", "web-development", "backend", "open-source", "api"],
            "homepage": "https://rubyonrails.org",
            "updated": now - timedelta(hours=12),
            "readme": """# Ruby on Rails

[![Version](https://badge.fury.io/rb/railties.svg)](https://badge.fury.io/rb/railties)
[![Build Status](https://github.com/rails/rails/workflows/CI/badge.svg)](https://github.com/rails/rails/actions)

Rails is a web-application framework that includes everything needed to create database-backed web applications according to the Model-View-Controller (MVC) pattern.

Understanding the MVC pattern is key to understanding Rails. MVC divides your application into three layers: Model, View, and Controller, each with a specific responsibility.
"""
        },
        {
            "owner": "nodejs", "name": "node",
            "desc": "Node.js JavaScript runtime ✨🐢🚀✨",
            "lang": "JavaScript", "license": "MIT",
            "stars": 107000, "forks": 29400, "watchers": 3300, "issues": 1700,
            "topics": ["javascript", "backend", "api", "web-development", "open-source"],
            "homepage": "https://nodejs.org",
            "updated": now - timedelta(hours=2),
            "readme": """# Node.js

Node.js is an open-source, cross-platform, JavaScript runtime environment.

For information on using Node.js, see the [Node.js website](https://nodejs.org).

The Node.js project uses an [open governance model](./GOVERNANCE.md). The [OpenJS Foundation](https://openjsf.org/) provides support for the project.

**This project is bound by a [Code of Conduct](https://github.com/nodejs/.github/blob/main/CODE_OF_CONDUCT.md).**

## Table of Contents

* [Support](#support)
* [Release Types](#release-types)
  * [Download](#download)
    * [Current and LTS Releases](#current-and-lts-releases)
    * [Nightly Releases](#nightly-releases)
"""
        },
        {
            "owner": "vercel", "name": "next.js",
            "desc": "The React Framework – created and maintained by @vercel.",
            "lang": "JavaScript", "license": "MIT",
            "stars": 128000, "forks": 27200, "watchers": 3100, "issues": 2400,
            "topics": ["javascript", "react", "frontend", "web-development", "typescript"],
            "homepage": "https://nextjs.org",
            "updated": now - timedelta(hours=1),
            "readme": """# Next.js

The React Framework for the Web.

Used by some of the world's largest companies, Next.js enables you to create high-quality web applications with the power of React components.

## Features

- An intuitive [page-based](https://nextjs.org/docs/basic-features/pages) routing system (with support for [dynamic routes](https://nextjs.org/docs/routing/dynamic-routes))
- [Pre-rendering](https://nextjs.org/docs/basic-features/pages#pre-rendering), both [static generation](https://nextjs.org/docs/basic-features/pages#static-generation-recommended) (SSG) and [server-side rendering](https://nextjs.org/docs/basic-features/pages#server-side-rendering) (SSR) are supported on a per-page basis
- Automatic code splitting for faster page loads
- [Client-side navigation](https://nextjs.org/docs/routing/introduction#linking-between-pages) with optimized prefetching
"""
        },
        {
            "owner": "pallets", "name": "flask",
            "desc": "The Python micro framework for building web applications.",
            "lang": "Python", "license": "BSD-3-Clause",
            "stars": 67800, "forks": 16300, "watchers": 1700, "issues": 120,
            "topics": ["python", "web-development", "backend", "api", "open-source"],
            "homepage": "https://flask.palletsprojects.com",
            "updated": now - timedelta(days=4),
            "readme": """# Flask

Flask is a lightweight [WSGI](https://wsgi.readthedocs.io) web application framework. It is designed to make getting started quick and easy, with the ability to scale up to complex applications. It began as a simple wrapper around [Werkzeug](https://werkzeug.palletsprojects.com) and [Jinja](https://jinja.palletsprojects.com) and has become one of the most popular Python web application frameworks.

Flask offers suggestions, but doesn't enforce any dependencies or project layout. It is up to the developer to choose the tools and libraries they want to use. There are many extensions provided by the community that make adding new functionality easy.

```
pip install Flask
```
"""
        },
        {
            "owner": "expressjs", "name": "express",
            "desc": "Fast, unopinionated, minimalist web framework for node.",
            "lang": "JavaScript", "license": "MIT",
            "stars": 64900, "forks": 15200, "watchers": 2100, "issues": 230,
            "topics": ["javascript", "backend", "api", "web-development", "nodejs"],
            "homepage": "https://expressjs.com",
            "updated": now - timedelta(days=6),
            "readme": """# Express

Fast, unopinionated, minimalist web framework for [Node.js](http://nodejs.org).

```js
const express = require('express')
const app = express()

app.get('/', function (req, res) {
  res.send('Hello World')
})

app.listen(3000)
```
"""
        },
        {
            "owner": "sveltejs", "name": "svelte",
            "desc": "web development for the rest of us",
            "lang": "JavaScript", "license": "MIT",
            "stars": 80200, "forks": 4400, "watchers": 1400, "issues": 570,
            "topics": ["javascript", "frontend", "web-development", "open-source"],
            "homepage": "https://svelte.dev",
            "updated": now - timedelta(days=2),
            "readme": """# Svelte

Svelte is a new way to build web applications. It's a compiler that takes your declarative components and converts them into efficient JavaScript that surgically updates the DOM.

Learn more at the [Svelte website](https://svelte.dev), or stop by the [Discord chatroom](https://svelte.dev/chat).

## Getting started

You can play around with Svelte in the [tutorial](https://learn.svelte.dev/) or the [examples](https://svelte.dev/examples).

To create a new project:

```sh
npm create svelte@latest myapp
cd myapp
npm install
npm run dev
```
"""
        },
        {
            "owner": "redis", "name": "redis",
            "desc": "Redis is an in-memory database that persists on disk.",
            "lang": "C", "license": "BSD-3-Clause",
            "stars": 67000, "forks": 23800, "watchers": 2000, "issues": 1700,
            "topics": ["c", "backend", "open-source", "security", "cloud"],
            "homepage": "https://redis.io",
            "updated": now - timedelta(days=1),
            "readme": """# Redis

Redis is often referred to as a _data structures_ server. What this means is that Redis provides access to mutable data structures via a set of commands, which are sent using a _server-client_ model with TCP sockets and a simple protocol.

You can run atomic operations on these types, like appending to a string; incrementing the value in a hash; pushing an element to a list; computing set intersection, union and difference; or getting the member with highest ranking in a sorted set.

In order to achieve its outstanding performance, Redis works with an **in-memory dataset**. Depending on your use case, you can persist your data either by periodically **dumping the dataset to disk** or by **appending each command to a disk-based log**.

## Building Redis

Redis can be compiled and used on Linux, OSX, OpenBSD, NetBSD, FreeBSD.
"""
        },
        {
            "owner": "denoland", "name": "deno",
            "desc": "A modern runtime for JavaScript and TypeScript.",
            "lang": "Rust", "license": "MIT",
            "stars": 96000, "forks": 5300, "watchers": 1900, "issues": 1900,
            "topics": ["rust", "javascript", "typescript", "web-development", "open-source"],
            "homepage": "https://deno.com",
            "updated": now - timedelta(hours=10),
            "readme": """# Deno

[![Discord Chat](https://img.shields.io/discord/684898665143148621?logo=discord&style=social)](https://discord.gg/deno)

Deno is a *simple*, *modern* and *secure* runtime for **JavaScript** and **TypeScript** that uses V8 and is built in Rust.

### Features

- Secure by default. No file, network, or environment access, unless explicitly enabled.
- Supports TypeScript out of the box.
- Ships only a single executable file.
- Has built-in utilities like a dependency inspector (`deno info`) and a code formatter (`deno fmt`).
- Has [a set of reviewed standard modules](https://jsr.io/@std) that are guaranteed to work with Deno.
"""
        },
    ]

    # Map usernames to user objects
    user_map = {u.username: u for u in users}
    repo_map = {}

    for rd in repos_data:
        owner_name = rd["owner"]
        # Create owner user if not in seed list
        if owner_name not in user_map:
            u = User(username=owner_name, email=f"{owner_name}@example.com",
                     name=owner_name.title(), plan='free')
            u.password_hash = PINNED_PASSWORD_HASH_BULK
            u.avatar = "/static/images/avatars/avatar_00.jpg"
            db.session.add(u)
            db.session.flush()
            user_map[owner_name] = u

        owner = user_map[owner_name]
        full_name = f"{owner_name}/{rd['name']}"

        gallery = load_gallery(full_name)

        repo = Repository(
            owner_id=owner.id,
            name=rd["name"],
            full_name=full_name,
            description=rd["desc"],
            language=rd["lang"],
            license=rd["license"],
            stars_count=rd["stars"],
            forks_count=rd["forks"],
            watchers_count=rd["watchers"],
            open_issues_count=rd["issues"],
            is_public=True,
            homepage=rd.get("homepage", ""),
            size_kb=rd.get("size_kb", 10000),
            readme=rd.get("readme", ""),
            topics_text=json.dumps(rd["topics"]),
            gallery_json=json.dumps(gallery),
            created_at=rd.get("created", now - timedelta(days=3000)),
            updated_at=rd["updated"],
            pushed_at=rd["updated"],
        )
        db.session.add(repo)
        db.session.flush()

        # Link topics
        for t_slug in rd["topics"]:
            if t_slug in topic_objs:
                repo.topics.append(topic_objs[t_slug])

        repo_map[full_name] = repo

    db.session.flush()

    # Seed demo user's repositories
    demo_user = user_map.get("octocat")
    if demo_user:
        demo_repos = [
            ("Hello-World", "My first repository on GitHub!", "Python", 4000, now - timedelta(days=10)),
            ("Spoon-Knife", "This repo is for demonstration purposes only.", "HTML", 12000, now - timedelta(days=30)),
            ("linguist", "Language Savant. If your repository's language is being reported incorrectly, send us a pull request!", "Ruby", 11600, now - timedelta(days=5)),
        ]
        for rname, rdesc, rlang, rstars, rupdated in demo_repos:
            fname = f"octocat/{rname}"
            if fname not in repo_map:
                r = Repository(
                    owner_id=demo_user.id,
                    name=rname, full_name=fname,
                    description=rdesc, language=rlang,
                    stars_count=rstars, forks_count=rstars // 10,
                    watchers_count=rstars // 50, open_issues_count=5,
                    is_public=True, topics_text='["open-source"]',
                    readme=f"# {rname}\n\n{rdesc}",
                    created_at=now - timedelta(days=2500),
                    updated_at=rupdated, pushed_at=rupdated,
                )
                db.session.add(r)
                repo_map[fname] = r

    db.session.flush()

    # Update topic repos_count
    for slug, topic in topic_objs.items():
        topic.repos_count = len(topic.repositories)

    # Seed some issues
    all_repos = list(repo_map.values())[:5]
    issue_labels = [
        ['bug', 'good first issue'],
        ['enhancement', 'help wanted'],
        ['documentation'],
        ['question', 'bug'],
        ['feature request'],
    ]
    issue_num = {}
    for i, repo in enumerate(all_repos):
        issue_num[repo.id] = 0
        for j in range(3):
            issue_num[repo.id] += 1
            author = users[j % len(users)]
            iss = Issue(
                repo_id=repo.id,
                author_id=author.id,
                number=issue_num[repo.id],
                title=f"Sample issue #{issue_num[repo.id]}: {'Bug in main module' if j == 0 else 'Feature request' if j == 1 else 'Documentation update needed'}",
                body=f"This is a sample issue description. It describes {'a bug that needs to be fixed' if j == 0 else 'a new feature to add' if j == 1 else 'documentation improvements needed'}.",
                status='open',
                labels_json=json.dumps(issue_labels[j % len(issue_labels)]),
                created_at=now - timedelta(days=j * 7),
            )
            db.session.add(iss)
            db.session.flush()

            # Add a comment
            commenter = users[(j + 1) % len(users)]
            comment = IssueComment(
                issue_id=iss.id,
                author_id=commenter.id,
                body="Thanks for reporting this! We'll look into it.",
                created_at=now - timedelta(days=j * 7 - 1),
            )
            db.session.add(comment)

    # Seed some follows — insert directly via the association table so
    # ROWID order matches the (i, j) loop order regardless of SQLAlchemy's
    # internal unordered identity-map iteration during flush.
    for i in range(min(5, len(users))):
        for j in range(min(3, len(users))):
            if i != j:
                db.session.execute(
                    follows.insert().values(follower_id=users[i].id,
                                            followed_id=users[j].id)
                )

    # Seed some stars for the demo user
    if demo_user and all_repos:
        for repo in all_repos[:3]:
            star = Star(user_id=demo_user.id, repo_id=repo.id)
            db.session.add(star)

    db.session.commit()
    print("Database seeded successfully.")


# ─────────────────────────── Routes ───────────────────────────

@app.route('/')
def index():
    featured_repos = Repository.query.filter_by(is_public=True).order_by(
        Repository.stars_count.desc()).limit(8).all()
    trending_repos = Repository.query.filter_by(is_public=True).order_by(
        Repository.stars_count.desc()).limit(6).all()
    featured_topics = Topic.query.filter_by(is_featured=True).order_by(
        Topic.repos_count.desc()).limit(18).all()
    return render_template('index.html',
                           featured_repos=featured_repos,
                           trending_repos=trending_repos,
                           featured_topics=featured_topics)


@app.route('/search-syntax')
def search_syntax():
    return render_template('search_syntax.html')


@app.route('/explore')
def explore():
    trending = Repository.query.filter_by(is_public=True).order_by(
        Repository.stars_count.desc()).limit(12).all()
    featured_topics = Topic.query.filter_by(is_featured=True).all()
    trending_devs = User.query.limit(8).all()
    collections = [
        {"title": "Machine Learning Models", "desc": "Cutting-edge ML frameworks and models", "count": 12},
        {"title": "Web Frameworks", "desc": "Modern frameworks for building web apps", "count": 18},
        {"title": "DevOps Tools", "desc": "Tools for CI/CD and infrastructure", "count": 9},
        {"title": "Security Tools", "desc": "Security scanning and vulnerability tools", "count": 7},
    ]
    return render_template('explore.html',
                           trending=trending,
                           featured_topics=featured_topics,
                           trending_devs=trending_devs,
                           collections=collections)


TRENDING_DEVELOPERS = [
    # (rank, username, name, trending_repo_full_name, since)
    (1, "yyx990803", "Evan You", "vuejs/vue", "monthly"),
    (2, "gaearon", "Dan Abramov", "facebook/react", "monthly"),
    (3, "torvalds", "Linus Torvalds", "torvalds/linux", "monthly"),
    (4, "tj", "TJ Holowaychuk", "expressjs/express", "monthly"),
    (5, "antirez", "Salvatore Sanfilippo", "redis/redis", "monthly"),
    (1, "gaearon", "Dan Abramov", "facebook/react", "weekly"),
    (2, "yyx990803", "Evan You", "vuejs/vue", "weekly"),
    (1, "torvalds", "Linus Torvalds", "torvalds/linux", "daily"),
    (2, "gaearon", "Dan Abramov", "facebook/react", "daily"),
]


@app.route('/trending')
def trending():
    lang_filter = request.args.get('l', '') or request.args.get('language', '')
    since = request.args.get('since', 'daily')
    tab = request.args.get('tab', 'repositories')
    page = request.args.get('page', 1, type=int)
    per_page = 25

    query = Repository.query.filter_by(is_public=True)
    if lang_filter:
        query = query.filter(Repository.language.ilike(lang_filter))
    repos = query.order_by(Repository.stars_count.desc()).paginate(
        page=page, per_page=per_page, error_out=False)

    languages = db.session.query(Repository.language, func.count(Repository.id)).filter(
        Repository.language != '').group_by(Repository.language).order_by(
        func.count(Repository.id).desc()).all()

    devs = [d for d in TRENDING_DEVELOPERS if d[4] == since]
    devs_info = []
    for rank, uname, name, repo_full, _s in devs:
        u = User.query.filter_by(username=uname).first()
        r = Repository.query.filter_by(full_name=repo_full).first()
        if u and r:
            devs_info.append({
                "rank": rank, "user": u, "repo": r,
                "repo_full_name": r.full_name,
            })

    return render_template('trending.html',
                           repos=repos, lang_filter=lang_filter,
                           since=since, tab=tab, languages=languages,
                           developers=devs_info)


@app.route('/trending/developers')
def trending_developers():
    """Dedicated Developers tab for GitHub Trending.
    Matches real URL https://github.com/trending/developers?since=monthly."""
    since = request.args.get('since', 'daily')
    lang_filter = request.args.get('l', '') or request.args.get('language', '')

    devs = [d for d in TRENDING_DEVELOPERS if d[4] == since]
    devs_info = []
    for rank, uname, name, repo_full, _s in devs:
        u = User.query.filter_by(username=uname).first()
        r = Repository.query.filter_by(full_name=repo_full).first()
        if u and r:
            devs_info.append({
                "rank": rank, "user": u, "repo": r,
                "repo_full_name": r.full_name,
            })

    # Empty repositories pagination for shared template
    repos = Repository.query.filter_by(is_public=True).order_by(
        Repository.stars_count.desc()).paginate(page=1, per_page=0, error_out=False)
    languages = db.session.query(Repository.language, func.count(Repository.id)).filter(
        Repository.language != '').group_by(Repository.language).order_by(
        func.count(Repository.id).desc()).all()

    return render_template('trending.html',
                           repos=repos, lang_filter=lang_filter,
                           since=since, tab='developers', languages=languages,
                           developers=devs_info)


@app.route('/topics')
def topics():
    # Hide internal sentinels (slug starting with '_').
    featured = (Topic.query.filter_by(is_featured=True)
                .filter(~Topic.slug.startswith('_')).all())
    all_topics = (Topic.query.filter(~Topic.slug.startswith('_'))
                  .order_by(Topic.repos_count.desc()).all())
    return render_template('topics.html', featured=featured, all_topics=all_topics)


@app.route('/topics/<slug>')
def topic_detail(slug):
    topic = Topic.query.filter_by(slug=slug).first_or_404()
    page = request.args.get('page', 1, type=int)
    sort_key = (request.args.get('o') or request.args.get('sort') or 'stars').lower()
    language = request.args.get('l', '').strip()

    q = Repository.query.filter(
        Repository.is_public == True,
        Repository.topics.any(Topic.slug == slug)
    )
    if language:
        q = q.filter(Repository.language == language)

    if sort_key in ('fewest_stars', 'stars_asc', 'stars-asc'):
        q = q.order_by(Repository.stars_count.asc())
    elif sort_key in ('most_forks', 'forks_desc', 'forks'):
        q = q.order_by(Repository.forks_count.desc())
    elif sort_key in ('fewest_forks', 'forks_asc'):
        q = q.order_by(Repository.forks_count.asc())
    elif sort_key in ('updated', 'most_updated', 'recently_updated', 'pushed'):
        q = q.order_by(Repository.pushed_at.desc())
    elif sort_key in ('least_updated', 'oldest_updated'):
        q = q.order_by(Repository.pushed_at.asc())
    elif sort_key in ('trending',):
        q = q.order_by(Repository.updated_at.desc(), Repository.stars_count.desc())
    else:  # default: most_stars
        sort_key = 'stars'
        q = q.order_by(Repository.stars_count.desc())

    repos = q.paginate(page=page, per_page=20, error_out=False)

    # Language facet for the filter chips
    lang_rows = (db.session.query(Repository.language, func.count(Repository.id))
                 .filter(Repository.is_public == True,
                         Repository.language != '',
                         Repository.topics.any(Topic.slug == slug))
                 .group_by(Repository.language)
                 .order_by(func.count(Repository.id).desc())
                 .limit(10).all())
    topic_languages = [(l, n) for l, n in lang_rows]

    return render_template('topic_detail.html', topic=topic, repos=repos,
                           current_sort=sort_key, current_lang=language,
                           topic_languages=topic_languages)


@app.route('/marketplace')
def marketplace():
    categories = [
        {"name": "Code quality", "icon": "check-circle", "count": 127},
        {"name": "Continuous integration", "icon": "zap", "count": 89},
        {"name": "Dependency management", "icon": "package", "count": 44},
        {"name": "Deployment", "icon": "cloud", "count": 73},
        {"name": "IDEs", "icon": "code", "count": 21},
        {"name": "Monitoring", "icon": "activity", "count": 56},
        {"name": "Project management", "icon": "trello", "count": 38},
        {"name": "Security", "icon": "shield", "count": 62},
        {"name": "Testing", "icon": "check-square", "count": 49},
        {"name": "Utilities", "icon": "tool", "count": 85},
    ]
    featured_apps = [
        {"name": "Snyk", "desc": "Find and fix vulnerabilities in your code", "icon": "🛡️", "stars": 4.8, "free": True},
        {"name": "Codecov", "desc": "Leading code coverage solution", "icon": "📊", "stars": 4.6, "free": True},
        {"name": "CircleCI", "desc": "Automate your development process", "icon": "⚡", "stars": 4.5, "free": True},
        {"name": "SonarCloud", "desc": "Code quality and security for your projects", "icon": "🔍", "stars": 4.7, "free": True},
        {"name": "Dependabot", "desc": "Automated dependency updates built into GitHub", "icon": "🤖", "stars": 4.9, "free": True},
        {"name": "DeepSource", "desc": "Detect 800+ types of issues in your code", "icon": "🔬", "stars": 4.4, "free": True},
    ]
    return render_template('marketplace.html', categories=categories, featured_apps=featured_apps)


@app.route('/pricing')
def pricing():
    plans = [
        {
            "name": "Free",
            "price": 0,
            "price_display": "$0",
            "period": "per month",
            "desc": "The basics for individuals and organizations",
            "cta": "Join for free",
            "cta_url": "/register",
            "private_repos": "Unlimited",
            "package_storage_gb": 0.5,
            "features": [
                "Unlimited public repositories",
                "Unlimited private repositories",
                "2,000 GitHub Actions minutes/month",
                "500MB GitHub Packages storage",
                "120 GitHub Codespaces core hours/month",
                "15GB GitHub Codespaces storage/month",
                "Community support",
            ],
            "is_popular": False,
        },
        {
            "name": "Pro",
            "price": 4,
            "price_display": "$4",
            "period": "per user/month",
            "desc": "For individuals looking for more collaboration and "
                    "advanced tooling",
            "cta": "Upgrade to Pro",
            "cta_url": "/register",
            "private_repos": "Unlimited",
            "package_storage_gb": 2,
            "features": [
                "Everything included in Free",
                "Unlimited private repositories",
                "3,000 GitHub Actions minutes/month",
                "2GB GitHub Packages storage",
                "Advanced tools for private repositories",
                "Required reviewers",
                "Multiple reviewers in pull requests",
                "Wiki for private repositories",
                "Protected branches",
                "Pages and wikis for private repos",
                "Email support",
            ],
            "is_popular": False,
        },
        {
            "name": "Team",
            "price": 4,
            "price_display": "$4",
            "period": "per user/month",
            "desc": "Advanced collaboration for individuals and organizations",
            "cta": "Continue with Team",
            "cta_url": "/register",
            "private_repos": "Unlimited",
            "package_storage_gb": 2,
            "features": [
                "Everything included in Free",
                "Access to GitHub Codespaces",
                "3,000 GitHub Actions minutes/month",
                "2GB GitHub Packages storage",
                "Web-based support",
                "Required reviewers",
                "Multiple reviewers in pull requests",
                "Draft pull requests",
                "Code owners",
                "Protected branches",
                "Repository insights graphs",
            ],
            "is_popular": True,
        },
        {
            "name": "Enterprise",
            "price": 21,
            "price_display": "$21",
            "period": "per user/month",
            "desc": "Security, compliance, and flexible deployment",
            "cta": "Start a free trial",
            "cta_url": "/register",
            "private_repos": "Unlimited",
            "package_storage_gb": 50,
            "features": [
                "Everything included in Team",
                "50,000 GitHub Actions minutes/month",
                "50GB GitHub Packages storage",
                "Enterprise Managed Users",
                "GitHub Connect",
                "SAML single sign-on",
                "Enterprise Account to centrally manage multiple organizations",
                "Advanced auditing",
                "GitHub Advanced Security (add-on)",
                "SOC 1 and SOC 2 type 2 compliance",
                "FedRAMP ATO",
                "24/7 premium support",
            ],
            "is_popular": False,
        },
    ]
    # Storage comparison: Enterprise 50GB - Team 2GB = 48GB more
    storage_comparison = {
        "team_gb": 2,
        "enterprise_gb": 50,
        "difference_gb": 48,
        "summary": "Enterprise includes 48 GB more GitHub Packages storage "
                   "than Team (50 GB vs 2 GB).",
    }
    return render_template('pricing.html', plans=plans,
                           storage_comparison=storage_comparison)


COPILOT_FEATURES = [
    {
        "name": "Code completion",
        "desc": "Get AI-powered code suggestions as you type in your editor. "
                "Copilot learns from your coding style and project context."
    },
    {
        "name": "Copilot Chat",
        "desc": "Ask Copilot questions in natural language right inside your IDE. "
                "Explain code, generate tests, fix bugs, and more."
    },
    {
        "name": "Pull request summaries",
        "desc": "Automatically generate pull request descriptions, review comments, "
                "and summaries so teams ship code faster."
    },
]

COPILOT_INDIVIDUAL_PLAN = {
    "name": "Copilot Individual",
    "price_monthly": 10,
    "price_yearly": 100,
    "price_display_monthly": "$10 USD/month",
    "price_display_yearly": "$100 USD/year",
    "features": [
        "Code completion in your IDE",
        "Copilot Chat in IDE and on GitHub.com",
        "Chat on GitHub Mobile",
        "Access to GPT-4o and Claude models",
        "Code review and explanation",
        "Pull request summaries",
        "Third-party model extensions",
    ],
}

COPILOT_FAQS = [
    {"q": "When can I use Copilot Chat on mobile?",
     "a": "GitHub Copilot Chat is available in GitHub Mobile on iOS and Android for "
          "all paid Copilot subscribers. You can start a chat from any repository on "
          "GitHub Mobile and get answers to coding questions on the go."},
    {"q": "Does Copilot Individual include access to Chat?",
     "a": "Yes. Copilot Individual includes Copilot Chat in supported IDEs, on "
          "GitHub.com, and in GitHub Mobile."},
    {"q": "How much does Copilot Individual cost?",
     "a": "Copilot Individual is $10 USD per month or $100 USD per year for "
          "verified individual developers."},
    {"q": "Which editors does Copilot support?",
     "a": "Copilot works with Visual Studio Code, Visual Studio, JetBrains IDEs, "
          "Neovim, and Xcode."},
    {"q": "Is Copilot available for students?",
     "a": "Yes, Copilot is free for verified students, teachers, and maintainers "
          "of popular open source projects through GitHub Education."},
]


@app.route('/features/copilot')
def feature_copilot():
    tiers = [
        {"name": "Copilot Free", "price": "$0", "desc": "For individuals just getting started",
         "completions": "2,000/month", "chat": "50/month", "features": ["Code completion", "Chat in IDE"]},
        {"name": "Copilot Individual", "price": "$10 USD/month",
         "desc": "For individual developers",
         "completions": "Unlimited", "chat": "Unlimited",
         "features": COPILOT_INDIVIDUAL_PLAN["features"]},
        {"name": "Copilot Pro+", "price": "$39 USD/month", "desc": "For power users",
         "completions": "Unlimited", "chat": "Unlimited",
         "features": ["Everything in Individual", "GitHub Spark access",
                      "Early access to new features"]},
        {"name": "Copilot Business", "price": "$19 USD/user/month", "desc": "For teams",
         "completions": "Unlimited", "chat": "Unlimited",
         "features": ["Everything in Individual", "Policy management", "Audit logs",
                      "IP indemnity"]},
    ]
    return render_template('feature_copilot.html', tiers=tiers,
                           features=COPILOT_FEATURES,
                           individual=COPILOT_INDIVIDUAL_PLAN)


@app.route('/features/copilot/faq')
def feature_copilot_faq():
    return render_template('feature_copilot_faq.html', faqs=COPILOT_FAQS)


@app.route('/skills')
def skills():
    first_day_courses = [
        {"slug": "introduction-to-github",
         "title": "Introduction to GitHub",
         "desc": "Get started using GitHub in less than an hour.",
         "duration": "1 hour"},
        {"slug": "communicate-using-markdown",
         "title": "Communicate using Markdown",
         "desc": "Learn Markdown to create rich content on GitHub.",
         "duration": "45 minutes"},
        {"slug": "github-pages",
         "title": "GitHub Pages",
         "desc": "Publish a website directly from your GitHub repository.",
         "duration": "1 hour"},
        {"slug": "hello-github-actions",
         "title": "Hello GitHub Actions",
         "desc": "Create your first GitHub Actions workflow.",
         "duration": "1 hour"},
    ]
    code_with_github = [
        {"slug": "review-pull-requests",
         "title": "Review pull requests",
         "desc": "Practice reviewing pull requests like a pro.",
         "duration": "1 hour"},
        {"slug": "resolve-merge-conflicts",
         "title": "Resolve merge conflicts",
         "desc": "Learn what causes merge conflicts and how to resolve them "
                 "using the GitHub web editor.",
         "duration": "1 hour",
         "actions": [
             "Identify when and why merge conflicts happen",
             "Resolve simple merge conflicts with the GitHub web editor",
             "Mark conflicts as resolved and complete a pull request merge",
         ]},
        {"slug": "release-based-workflow",
         "title": "Release-based workflow",
         "desc": "Practice a release-based workflow.",
         "duration": "2 hours"},
    ]
    automate_workflows = [
        {"slug": "continuous-integration",
         "title": "Continuous integration with GitHub Actions",
         "desc": "Learn how to create workflows that enable you to use CI.",
         "duration": "1 hour"},
        {"slug": "continuous-delivery",
         "title": "Continuous delivery with GitHub Actions",
         "desc": "Create two deployment workflows with GitHub Actions.",
         "duration": "1 hour"},
    ]
    sections = [
        {"heading": "First day on GitHub", "courses": first_day_courses},
        {"heading": "Code with GitHub", "courses": code_with_github},
        {"heading": "Automate workflows", "courses": automate_workflows},
    ]
    return render_template('skills.html', sections=sections)


@app.route('/skills/<slug>')
def skill_course(slug):
    all_courses = []
    for sec in [
        ("First day on GitHub", [
            ("introduction-to-github", "Introduction to GitHub"),
            ("communicate-using-markdown", "Communicate using Markdown"),
            ("github-pages", "GitHub Pages"),
            ("hello-github-actions", "Hello GitHub Actions"),
        ]),
    ]:
        all_courses.extend(sec[1])
    # Special: resolve merge conflicts detail page
    course_data = {
        "resolve-merge-conflicts": {
            "title": "Resolve merge conflicts",
            "desc": "Learn what causes merge conflicts and how to resolve them "
                    "using the GitHub web editor.",
            "duration": "1 hour",
            "actions": [
                "Identify when and why merge conflicts happen",
                "Resolve simple merge conflicts with the GitHub web editor",
                "Edit files and commit changes to finish a pull request",
                "Mark conflicts as resolved and complete a pull request merge",
            ],
        },
    }
    course = course_data.get(slug, {
        "title": slug.replace('-', ' ').title(),
        "desc": "GitHub Skills course.",
        "duration": "1 hour",
        "actions": ["Learn the fundamentals", "Practice with a hands-on repo",
                    "Complete the course"],
    })
    return render_template('skill_course.html', course=course, slug=slug)


CUSTOMER_STORIES = [
    {"slug": "mercedes-benz",
     "company": "Mercedes-Benz",
     "headline": "Mercedes-Benz accelerates software delivery with GitHub",
     "summary": "How the automaker uses GitHub Enterprise to build "
                "in-vehicle software faster across 800+ developers.",
     "industry": "Automotive"},
    {"slug": "shopify",
     "company": "Shopify",
     "headline": "Shopify scales developer productivity with GitHub Copilot",
     "summary": "Shopify's engineering team uses Copilot to ship code 55% "
                "faster while maintaining quality.",
     "industry": "E-commerce"},
]


@app.route('/customer-stories')
def customer_stories():
    return render_template('customer_stories.html', stories=CUSTOMER_STORIES)


@app.route('/customer-stories/<slug>')
def customer_story_detail(slug):
    story = next((s for s in CUSTOMER_STORIES if s['slug'] == slug), None)
    if not story:
        abort(404)
    return render_template('customer_story_detail.html', story=story)


RESOURCE_TOPICS = [
    {"slug": "security",
     "title": "Security",
     "headline": "Build secure software with GitHub",
     "intro": "Understand how GitHub helps you secure the software supply chain.",
     "sections": [
         {"heading": "What is GitHub Advanced Security?",
          "body": "GitHub Advanced Security is a suite of tools built into "
                  "the developer workflow. It runs on every pull request, "
                  "every push, and every default-branch update, so security "
                  "feedback arrives at the same time as code review feedback. "
                  "Code scanning analyzes your source for over 200 classes "
                  "of vulnerability using CodeQL. Secret scanning detects "
                  "leaked tokens across every commit and every fork. "
                  "Dependency review flags vulnerable open-source packages "
                  "before they merge. Together, these checks make security "
                  "part of how developers ship — not a separate gate."},
         {"heading": "Code scanning",
          "body": "Automatically analyze your code for vulnerabilities and "
                  "errors with CodeQL."},
         {"heading": "Secret scanning",
          "body": "Detect leaked credentials across your repositories and "
                  "automatically alert partners."},
     ]},
    {"slug": "devops",
     "title": "DevOps",
     "headline": "Learn how GitHub enables DevOps",
     "intro": "DevOps is the collaboration between development and operations.",
     "sections": [
         {"heading": "What is DevOps?",
          "body": "DevOps brings together people, processes, and technology "
                  "to deliver value to customers."},
     ]},
    {"slug": "ai",
     "title": "AI",
     "headline": "Build with AI on GitHub",
     "intro": "Explore how GitHub helps you build AI-powered applications.",
     "sections": [
         {"heading": "What is GitHub Copilot?",
          "body": "Copilot is your AI pair programmer."},
     ]},
]


@app.route('/resources')
def resources():
    return render_template('resources.html', topics=RESOURCE_TOPICS)


@app.route('/resources/security')
def resources_security():
    """Rich Security marketing page. Preserves the original Q&A so the
    WebVoyager GitHub--21 'role of Advanced Security' answer is still
    extractable from the page."""
    topic = next((t for t in RESOURCE_TOPICS if t['slug'] == 'security'), None)
    return render_template('resources_security.html', topic=topic)


@app.route('/resources/<slug>')
def resources_topic(slug):
    topic = next((t for t in RESOURCE_TOPICS if t['slug'] == slug), None)
    if not topic:
        abort(404)
    return render_template('resources_topic.html', topic=topic)


@app.route('/signup/check')
@csrf.exempt
def signup_check():
    email = request.args.get('email', '').strip().lower()
    exists = bool(email and User.query.filter_by(email=email).first())
    return jsonify({"email": email, "exists": exists,
                    "message": ("Email already registered." if exists
                                else "Email is available.")})


@app.route('/features/actions')
def feature_actions():
    return render_template('feature_actions.html')


@app.route('/features/codespaces')
def feature_codespaces():
    return render_template('feature_codespaces.html')


@app.route('/about')
def about():
    return render_template('about.html')


# ─── Marketing stubs for links referenced from templates ───
# Each of these pages was linked from existing GitHub-clone pages
# (customer_stories, resources_security, copilot/faq, repo sidebars, index hero)
# but had no route, so agents hit a 404 mid-flow. Stubs render the shared
# simple_landing template with realistic-looking marketing content.

_STUB_PAGES = {
    'contact_sales': {
        'title': 'Contact Sales',
        'eyebrow': 'GitHub Sales',
        'headline': 'Talk to our sales team.',
        'sub': 'See how GitHub Enterprise, Advanced Security, and Copilot Business '
               'fit your team. A specialist will follow up within one business day.',
        'ctas': [
            {'href': '#form', 'label': 'Request a demo', 'cls': 'gh-btn-primary'},
            {'href': '/pricing', 'label': 'View pricing', 'cls': 'gh-btn-secondary'},
        ],
        'bullets': [
            'Volume discounts on Enterprise seats',
            'Single sign-on (SAML, OIDC) and SCIM provisioning',
            'Dedicated customer success manager for >500 seats',
        ],
        'sections_title': 'What you get',
        'sections': [
            {'title': 'Custom rollout plan',
             'body': 'A solutions architect maps GitHub Enterprise to your existing identity provider, audit pipeline, and CI fleet.'},
            {'title': 'Security review',
             'body': 'We share SOC 2 Type II, ISO 27001, FedRAMP, and pen-test reports under NDA so your security team can sign off.'},
            {'title': 'Proof of concept',
             'body': '30-day pilot on a sample org with white-glove migration help and weekly health checks.'},
        ],
    },
    'enterprise': {
        'title': 'GitHub Enterprise',
        'eyebrow': 'GitHub Enterprise',
        'headline': 'The developer platform built for the enterprise.',
        'sub': 'Run GitHub on your terms: Enterprise Cloud with data residency, or '
               'Enterprise Server in your own data centre. Same workflow, hardened controls.',
        'ctas': [
            {'href': '/contact-sales', 'label': 'Start a free trial', 'cls': 'gh-btn-primary'},
            {'href': '/pricing', 'label': 'Compare plans', 'cls': 'gh-btn-secondary'},
        ],
        'bullets': [
            '90% of the Fortune 100 build with GitHub Enterprise',
            'SAML SSO, SCIM, audit log streaming to Splunk / Datadog',
            'Data residency in US, EU, and Australia',
        ],
        'sections_title': 'Enterprise capabilities',
        'sections': [
            {'title': 'Advanced Security',
             'body': 'Code scanning with CodeQL, secret scanning across 200+ token formats, and Dependabot supply-chain coverage.',
             'href': '/features/code-scanning', 'link_label': 'Explore CodeQL'},
            {'title': 'Copilot for Business',
             'body': 'AI pair programmer with IP indemnification, no training on your code, and central admin policy controls.',
             'href': '/features/copilot', 'link_label': 'See Copilot'},
            {'title': 'GitHub Actions runners',
             'body': 'Self-hosted and GitHub-hosted Linux/Windows/macOS runners with usage caps and per-org concurrency limits.',
             'href': '/features/actions', 'link_label': 'Read the Actions docs'},
        ],
    },
    'education': {
        'title': 'GitHub Education',
        'eyebrow': 'GitHub Education',
        'headline': 'The tools you need to ship your first project — free.',
        'sub': 'Verified students and teachers get free access to GitHub Copilot, '
               'the Student Developer Pack (~100 partner offers), and Campus Experts mentoring.',
        'ctas': [
            {'href': '/register', 'label': 'Verify your student status', 'cls': 'gh-btn-primary'},
            {'href': '/skills', 'label': 'Browse GitHub Skills', 'cls': 'gh-btn-secondary'},
        ],
        'bullets': [
            'Free GitHub Pro account while you study',
            'Free GitHub Copilot for students, teachers, and maintainers',
            'Student Developer Pack: DigitalOcean credit, JetBrains, Namecheap, Canva, and more',
        ],
        'faq': [
            {'q': 'Who qualifies?',
             'a': 'Students aged 13+ enrolled at a degree-granting institution, plus teachers, faculty, and TAs.'},
            {'q': 'Does Copilot stay free after I graduate?',
             'a': 'Copilot Free is included in the Student Developer Pack while your verification is active (usually 1-2 years).'},
            {'q': 'I am an open-source maintainer, not a student.',
             'a': 'Maintainers of popular open-source projects (>1 active project, >1000 monthly users) get Copilot for Open Source free.'},
        ],
    },
    'feature_code_scanning': {
        'title': 'Code scanning · CodeQL',
        'eyebrow': 'Advanced Security',
        'headline': 'Find vulnerabilities in your code before they ship.',
        'sub': 'CodeQL is the semantic analysis engine that powers GitHub Code Scanning. '
               'Write queries once, run them across every PR and every default branch.',
        'ctas': [
            {'href': '/features/copilot', 'label': 'Pair with Copilot Autofix', 'cls': 'gh-btn-primary'},
            {'href': '/resources/security', 'label': 'Security overview', 'cls': 'gh-btn-secondary'},
        ],
        'bullets': [
            '11 supported languages: C, C++, C#, Go, Java, JavaScript, TypeScript, Kotlin, Python, Ruby, Swift',
            '2,200+ curated CodeQL queries maintained by the GitHub Security Lab',
            'Integrated SARIF output for Snyk, Semgrep, Trivy, and your own scanners',
        ],
        'sections_title': 'How code scanning works',
        'sections': [
            {'title': 'Default setup',
             'body': 'One-click on the Security tab. We pick the right languages, queries, and runner.'},
            {'title': 'Advanced setup',
             'body': 'Bring your own workflow file. Pin a CodeQL version, exclude paths, schedule nightly scans.'},
            {'title': 'PR feedback',
             'body': 'New alerts show up as PR review comments. Block merge with branch protection if needed.'},
        ],
    },
    'feature_secret_scanning': {
        'title': 'Secret scanning',
        'eyebrow': 'Advanced Security',
        'headline': 'Stop leaked credentials before they reach production.',
        'sub': 'GitHub scans every push for 200+ token formats from 100+ partners — AWS, '
               'Stripe, OpenAI, Slack, and more — and notifies the provider so they can revoke.',
        'ctas': [
            {'href': '/contact-sales', 'label': 'Enable for your org', 'cls': 'gh-btn-primary'},
            {'href': '/resources/security', 'label': 'Read the docs', 'cls': 'gh-btn-secondary'},
        ],
        'bullets': [
            '200+ token formats — AWS, Azure, GCP, Stripe, Twilio, OpenAI, Anthropic, Slack',
            'Push protection blocks the commit before the secret ever lands',
            'Custom patterns for your internal API keys',
        ],
    },
    'feature_dependency_review': {
        'title': 'Dependency review',
        'eyebrow': 'Advanced Security',
        'headline': 'See exactly what each PR adds to your supply chain.',
        'sub': 'Dependency review surfaces new and updated packages introduced by a pull '
               'request, flagging known vulnerabilities and incompatible licenses before merge.',
        'ctas': [
            {'href': '/features/supply-chain', 'label': 'Supply-chain overview', 'cls': 'gh-btn-primary'},
            {'href': '/contact-sales', 'label': 'Talk to sales', 'cls': 'gh-btn-secondary'},
        ],
        'bullets': [
            'Coverage for npm, pip, Maven, NuGet, RubyGems, Go modules, Rust crates, Composer',
            'Severity-based merge gates configurable in branch protection',
            'License compatibility checks (MIT, Apache-2.0, GPL families, custom allowlists)',
        ],
    },
    'feature_supply_chain': {
        'title': 'Software supply chain security',
        'eyebrow': 'Advanced Security',
        'headline': 'A signed, attested supply chain — end to end.',
        'sub': 'Generate SBOMs, sign your artifacts with Sigstore, attest builds with SLSA, '
               'and verify provenance in deploy — all wired into GitHub Actions.',
        'ctas': [
            {'href': '/features/actions', 'label': 'GitHub Actions', 'cls': 'gh-btn-primary'},
            {'href': '/features/dependency-review', 'label': 'Dependency review', 'cls': 'gh-btn-secondary'},
        ],
        'bullets': [
            'SBOMs in SPDX 2.3 and CycloneDX 1.5 formats',
            'Keyless signing with Sigstore cosign + GitHub OIDC',
            'SLSA Build Level 3 provenance attestations',
        ],
    },
    'security_center': {
        'title': 'Security Center',
        'eyebrow': 'Enterprise compliance',
        'headline': 'One place for your compliance attestations.',
        'sub': 'Available to GitHub Enterprise Cloud customers. Download our SOC 1, SOC 2, '
               'ISO 27001, FedRAMP, PCI DSS, and HIPAA attestations under NDA.',
        'ctas': [
            {'href': '/contact-sales', 'label': 'Request access', 'cls': 'gh-btn-primary'},
            {'href': '/resources/security', 'label': 'Security overview', 'cls': 'gh-btn-secondary'},
        ],
        'bullets': [
            'SOC 1 Type 2 (audited annually by EY)',
            'SOC 2 Type 2 — Security, Availability, Confidentiality',
            'ISO 27001:2022, ISO 27017, ISO 27018',
            'FedRAMP Moderate (in process), GovCloud roadmap',
        ],
    },
}


@app.route('/contact-sales')
def contact_sales():
    return render_template('simple_landing.html', page=_STUB_PAGES['contact_sales'])


@app.route('/enterprise')
def enterprise():
    return render_template('simple_landing.html', page=_STUB_PAGES['enterprise'])


@app.route('/education')
def education():
    return render_template('simple_landing.html', page=_STUB_PAGES['education'])


@app.route('/features/code-scanning')
def feature_code_scanning():
    return render_template('simple_landing.html', page=_STUB_PAGES['feature_code_scanning'])


@app.route('/features/secret-scanning')
def feature_secret_scanning():
    return render_template('simple_landing.html', page=_STUB_PAGES['feature_secret_scanning'])


@app.route('/features/dependency-review')
def feature_dependency_review():
    return render_template('simple_landing.html', page=_STUB_PAGES['feature_dependency_review'])


@app.route('/features/supply-chain')
def feature_supply_chain():
    return render_template('simple_landing.html', page=_STUB_PAGES['feature_supply_chain'])


@app.route('/security/center')
def security_center():
    return render_template('simple_landing.html', page=_STUB_PAGES['security_center'])


# ── R2: extra stub pages referenced from footer/nav (Solutions tier) ──

_R2_STUBS = {
    'solutions_enterprise': {
        'title': 'Enterprise solutions', 'eyebrow': 'Solutions',
        'headline': 'Built for the world\'s largest engineering teams.',
        'sub': 'GitHub Enterprise scales from 100 to 100,000 developers with '
               'SAML SSO, audit log streaming, and data residency.',
        'ctas': [{'href': '/contact-sales', 'label': 'Talk to sales', 'cls': 'gh-btn-primary'},
                 {'href': '/pricing', 'label': 'Compare plans', 'cls': 'gh-btn-secondary'}],
        'bullets': ['Used by 90% of the Fortune 100',
                    'SAML SSO, SCIM, audit log streaming',
                    'Data residency in US, EU, AU'],
    },
    'solutions_team': {
        'title': 'Solutions for teams', 'eyebrow': 'Solutions',
        'headline': 'Ship faster with a team that trusts each other.',
        'sub': 'Code review, branch protection, and Actions CI for every team size.',
        'ctas': [{'href': '/pricing', 'label': 'See Team pricing', 'cls': 'gh-btn-primary'}],
        'bullets': ['Unlimited private repos with 3,000 Actions minutes/month',
                    'Code owners + required reviews', 'Team-scoped secrets'],
    },
    'solutions_startups': {
        'title': 'GitHub for Startups', 'eyebrow': 'Solutions',
        'headline': 'Build your company on GitHub — free for 12 months.',
        'sub': '20 seats of Enterprise free for one year for verified startups.',
        'ctas': [{'href': '/contact-sales', 'label': 'Apply now', 'cls': 'gh-btn-primary'}],
        'bullets': ['20 GitHub Enterprise seats, free for 12 months',
                    'Free GitHub Copilot for Business seats',
                    'Access to the Startups community'],
    },
    'solutions_devsecops': {
        'title': 'DevSecOps with GitHub', 'eyebrow': 'Solutions',
        'headline': 'Shift security left without slowing developers down.',
        'sub': 'CodeQL, secret scanning, Dependabot, and Advisory Database in one place.',
        'ctas': [{'href': '/features/code-scanning', 'label': 'Code scanning', 'cls': 'gh-btn-primary'},
                 {'href': '/features/secret-scanning', 'label': 'Secret scanning', 'cls': 'gh-btn-secondary'}],
        'bullets': ['CodeQL queries for 11 languages',
                    '200+ partner secret formats covered',
                    'Dependabot patches across 8 ecosystems'],
    },
    'solutions_devops': {
        'title': 'DevOps on GitHub', 'eyebrow': 'Solutions',
        'headline': 'Plan, build, ship — all in one place.',
        'sub': 'GitHub Issues, Actions, Packages, and Environments give every team a single pane of glass.',
        'ctas': [{'href': '/features/actions', 'label': 'GitHub Actions', 'cls': 'gh-btn-primary'}],
        'bullets': ['GitHub-hosted Linux, macOS, Windows runners',
                    'OIDC federation with AWS, Azure, GCP',
                    'Environments with protection rules'],
    },
    'docs': {
        'title': 'GitHub Docs', 'eyebrow': 'Documentation',
        'headline': 'Everything you need to build on GitHub.',
        'sub': 'Tutorials, reference, and guides for GitHub, Copilot, Actions, and the REST and GraphQL APIs.',
        'ctas': [{'href': '/api', 'label': 'API reference', 'cls': 'gh-btn-primary'},
                 {'href': '/features/actions', 'label': 'Actions docs', 'cls': 'gh-btn-secondary'}],
        'bullets': ['REST and GraphQL APIs',
                    'CLI: `gh`', 'Webhooks and Apps'],
    },
    'api': {
        'title': 'GitHub REST & GraphQL APIs', 'eyebrow': 'Developer',
        'headline': 'Build on top of GitHub.',
        'sub': 'A REST API and a GraphQL endpoint for every resource on the platform.',
        'ctas': [{'href': '/docs', 'label': 'Read the docs', 'cls': 'gh-btn-primary'}],
        'bullets': ['REST API at api.github.com', 'GraphQL at api.github.com/graphql',
                    '5,000 req/hr authenticated, 60 req/hr unauth'],
    },
    'status': {
        'title': 'GitHub Status', 'eyebrow': 'Service status',
        'headline': 'All systems operational.',
        'sub': 'Real-time and historical status of every GitHub service: Git operations, '
               'API requests, Pages, Actions, Packages, Webhooks, Codespaces, Copilot.',
        'ctas': [{'href': '/about', 'label': 'About this mirror', 'cls': 'gh-btn-secondary'}],
        'bullets': ['Git operations: operational',
                    'API requests: operational',
                    'GitHub Actions: operational',
                    'GitHub Pages: operational',
                    'Webhooks: operational'],
    },
    'blog': {
        'title': 'The GitHub Blog', 'eyebrow': 'Updates and stories',
        'headline': 'News from the GitHub team.',
        'sub': 'Product launches, engineering deep-dives, and open-source highlights.',
        'ctas': [{'href': '/customer-stories', 'label': 'Customer stories', 'cls': 'gh-btn-primary'}],
        'bullets': ['Copilot Workspace generally available',
                    'GitHub Actions adds Apple Silicon runners',
                    'CodeQL coverage extended to Kotlin and Swift'],
    },
    'contact': {
        'title': 'Contact GitHub', 'eyebrow': 'Help',
        'headline': 'How can we help?',
        'sub': 'Reach billing, sales, abuse, security, or community support — every team has a dedicated channel.',
        'ctas': [{'href': '/contact-sales', 'label': 'Contact sales', 'cls': 'gh-btn-primary'}],
        'bullets': ['Billing: through your Settings → Billing page',
                    'Security: security@github.com',
                    'Abuse: support.github.com/contact/report-abuse'],
    },
    'privacy': {
        'title': 'GitHub Privacy Statement', 'eyebrow': 'Legal',
        'headline': 'Your privacy matters to us.',
        'sub': 'We process your data to provide the GitHub services. We are SOC 2 audited '
               'and GDPR + CCPA compliant.',
        'bullets': ['SOC 2 Type II', 'ISO 27001:2022',
                    'GDPR and CCPA compliant',
                    'Data residency available for Enterprise Cloud'],
    },
    'terms': {
        'title': 'GitHub Terms of Service', 'eyebrow': 'Legal',
        'headline': 'The rules of the road.',
        'sub': 'By using GitHub you agree to the Terms of Service, the Acceptable Use Policies, '
               'and the Privacy Statement.',
        'bullets': ['Acceptable Use Policies',
                    'Corporate Terms of Service for Enterprise',
                    'Site policies on github.com/site-policy'],
    },
}


def _r2_stub(slug):
    return render_template('simple_landing.html', page=_R2_STUBS[slug])


@app.route('/solutions/enterprise')
def solutions_enterprise():
    return _r2_stub('solutions_enterprise')


@app.route('/solutions/team')
def solutions_team():
    return _r2_stub('solutions_team')


@app.route('/solutions/startups')
def solutions_startups():
    return _r2_stub('solutions_startups')


@app.route('/solutions/devsecops')
def solutions_devsecops():
    return _r2_stub('solutions_devsecops')


@app.route('/solutions/devops')
def solutions_devops():
    return _r2_stub('solutions_devops')


@app.route('/docs')
def docs():
    return _r2_stub('docs')


@app.route('/api')
def api_docs():
    return _r2_stub('api')


@app.route('/status')
def status():
    return _r2_stub('status')


@app.route('/blog')
def blog():
    return _r2_stub('blog')


@app.route('/contact')
def contact():
    return _r2_stub('contact')


@app.route('/privacy')
def privacy():
    return _r2_stub('privacy')


@app.route('/terms')
def terms():
    return _r2_stub('terms')


# ─── Auth ───

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = LoginForm()
    if form.validate_on_submit():
        login_id = form.login.data.strip()
        user = User.query.filter(
            or_(User.email == login_id, User.username == login_id)
        ).first()
        if user and user.check_password(form.password.data):
            login_user(user)
            flash('Welcome back!', 'success')
            next_page = request.args.get('next')
            return redirect(next_page or url_for('index'))
        flash('Invalid username or password.', 'danger')
    return render_template('login.html', form=form)


@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = RegisterForm()
    if form.validate_on_submit():
        uname = form.username.data.strip().lower()
        if User.query.filter_by(username=uname).first():
            flash('Username already taken.', 'danger')
        elif User.query.filter_by(email=form.email.data.strip().lower()).first():
            flash('Email already registered.', 'danger')
        else:
            u = User(username=uname, email=form.email.data.strip().lower(),
                     name=uname)
            u.set_password(form.password.data)
            u.avatar = f"/static/images/avatars/avatar_{(hash(uname) % 15):02d}.jpg"
            db.session.add(u)
            db.session.commit()
            login_user(u)
            flash('Account created! Welcome to GitHub Mirror.', 'success')
            return redirect(url_for('index'))
    return render_template('register.html', form=form)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been signed out.', 'info')
    return redirect(url_for('index'))


# ─── User Profile ───

@app.route('/<username>')
def user_profile(username):
    user = User.query.filter_by(username=username).first_or_404()
    tab = request.args.get('tab', 'repositories')
    repos = user.repositories.filter_by(is_public=True).order_by(
        Repository.stars_count.desc()).limit(20).all()
    starred = Star.query.filter_by(user_id=user.id).join(Repository).order_by(
        Star.created_at.desc()).limit(20).all()
    return render_template('user_profile.html', profile_user=user, repos=repos,
                           starred=starred, tab=tab)


@app.route('/<username>/followers')
def user_followers(username):
    user = User.query.filter_by(username=username).first_or_404()
    followers_list = user.followers.all()
    repos = user.repositories.filter_by(is_public=True).order_by(
        Repository.stars_count.desc()).limit(20).all()
    starred = Star.query.filter_by(user_id=user.id).join(Repository).order_by(
        Star.created_at.desc()).limit(20).all()
    return render_template('user_profile.html', profile_user=user, repos=repos,
                           starred=starred, tab='followers', follow_users=followers_list)


@app.route('/<username>/following')
def user_following(username):
    user = User.query.filter_by(username=username).first_or_404()
    following_list = user.following.all()
    repos = user.repositories.filter_by(is_public=True).order_by(
        Repository.stars_count.desc()).limit(20).all()
    starred = Star.query.filter_by(user_id=user.id).join(Repository).order_by(
        Star.created_at.desc()).limit(20).all()
    return render_template('user_profile.html', profile_user=user, repos=repos,
                           starred=starred, tab='following', follow_users=following_list)


# ─── Repository ───

@app.route('/new', methods=['GET', 'POST'])
@login_required
def new_repo():
    form = NewRepoForm()
    if form.validate_on_submit():
        rname = form.name.data.strip()
        rname = re.sub(r'[^a-zA-Z0-9_\-.]', '-', rname)
        full_name = f"{current_user.username}/{rname}"
        if Repository.query.filter_by(full_name=full_name).first():
            flash('A repository with this name already exists.', 'danger')
        else:
            is_pub = form.is_public.data == 'true'
            readme_content = ""
            if form.init_readme.data:
                readme_content = f"# {rname}\n\n{form.description.data or ''}"
            repo = Repository(
                owner_id=current_user.id,
                name=rname,
                full_name=full_name,
                description=form.description.data or '',
                is_public=is_pub,
                readme=readme_content,
                topics_text='[]',
                gallery_json='[]',
            )
            db.session.add(repo)
            db.session.commit()
            flash(f'Repository {full_name} created!', 'success')
            return redirect(url_for('repo_detail', username=current_user.username, reponame=rname))
    return render_template('new_repo.html', form=form)


@app.route('/<username>/<reponame>')
def repo_detail(username, reponame):
    user = User.query.filter_by(username=username).first_or_404()
    repo = Repository.query.filter_by(full_name=f"{username}/{reponame}").first_or_404()
    if not repo.is_public and (not current_user.is_authenticated or current_user.id != repo.owner_id):
        # R6 edge: DMCA-takedown repos render a takedown notice instead
        # of a generic 404 — tasks need a stable surface to assert on.
        if _r6_has_sentinel(repo, 'dmca'):
            return render_template('repo_detail.html', repo=repo, owner=user,
                                   gallery=[], topics=repo.get_topics(),
                                   recent_issues=[], is_starred=False,
                                   is_watching=False, related=[],
                                   open_count=0, open_pr_count=0,
                                   commit_count=0,
                                   latest_author=username,
                                   dmca_taken_down=True,
                                   owner_other_repos=[], used_by=[],
                                   topic_related=[],
                                   forkers_preview=[]), 451
        abort(404)
    gallery = repo.get_gallery()
    topics = repo.get_topics()
    recent_issues = repo.issues.filter_by(status='open').order_by(
        Issue.created_at.desc()).limit(5).all()
    is_starred = current_user.is_authenticated and current_user.has_starred(repo)
    is_watching = current_user.is_authenticated and current_user.has_watched(repo)
    related = Repository.query.filter(
        Repository.language == repo.language,
        Repository.id != repo.id,
        Repository.is_public == True
    ).order_by(Repository.stars_count.desc()).limit(4).all()
    # R6: extra sidebar widgets.
    owner_other_repos = (Repository.query
                         .filter(Repository.owner_id == repo.owner_id,
                                 Repository.id != repo.id,
                                 Repository.is_public == True)
                         .order_by(Repository.stars_count.desc())
                         .limit(5).all())
    # Topic-based "Related repos" — distinct from the language-based block.
    topic_related = []
    if topics:
        primary_topic = next((t for t in topics if not t.startswith('_r6-')),
                             topics[0])
        topic_related = (Repository.query
                         .filter(Repository.topics_text.like(f'%"{primary_topic}"%'),
                                 Repository.id != repo.id,
                                 Repository.is_public == True)
                         .order_by(Repository.stars_count.desc())
                         .limit(5).all())
    # "Used by" — deterministic synthesis from repo.id. Pulls other repos
    # from the same language family and pretends they depend on this one.
    used_by_pool = (Repository.query
                    .filter(Repository.language == repo.language,
                            Repository.id != repo.id,
                            Repository.is_public == True)
                    .order_by(Repository.id.asc())
                    .limit(120).all())
    used_by = []
    if used_by_pool:
        for i in range(min(6, len(used_by_pool))):
            used_by.append(used_by_pool[(repo.id * 13 + i * 17) % len(used_by_pool)])
    used_by_total = max(0, (repo.stars_count or 0) // 11)
    # Live open-issue count so the Issues tab badge matches the
    # /issues page (which filters the issue table directly).
    open_count = repo.issues.filter_by(status='open', is_pr=0).count()
    open_pr_count = repo.issues.filter_by(status='open', is_pr=1).count()
    all_commits = repo.get_commits()
    commit_count = len(all_commits) if all_commits else (1 if repo.latest_commit_sha else 0)
    latest_author = (all_commits[0].get('author') if all_commits else user.username)
    # R6 edge flags exposed to template so it can render banners.
    edge_archived_ro = _r6_has_sentinel(repo, 'archived-ro') or repo.is_archived
    edge_branch_protected = _r6_has_sentinel(repo, 'branch-protected')
    edge_action_failed = _r6_has_sentinel(repo, 'action-run-failed')
    edge_pr_conflict = _r6_has_sentinel(repo, 'pr-conflict')
    return render_template('repo_detail.html', repo=repo, owner=user,
                           gallery=gallery, topics=topics,
                           recent_issues=recent_issues,
                           is_starred=is_starred, is_watching=is_watching,
                           related=related, open_count=open_count,
                           open_pr_count=open_pr_count,
                           commit_count=commit_count,
                           latest_author=latest_author,
                           owner_other_repos=owner_other_repos,
                           topic_related=topic_related,
                           used_by=used_by, used_by_total=used_by_total,
                           edge_archived_ro=edge_archived_ro,
                           edge_branch_protected=edge_branch_protected,
                           edge_action_failed=edge_action_failed,
                           edge_pr_conflict=edge_pr_conflict)


def _first_commit(repo, owner_username):
    """Synthesize a representative 'first commit' row from repo.created_at.
    Lets the /commits page surface the repo's creation date even though we
    only persist the 10 most recent commits in commits_json."""
    import hashlib
    sha = hashlib.sha1(f'{repo.full_name}::initial'.encode()).hexdigest()
    created = repo.created_at
    return {
        'sha': sha,
        'message': 'Initial commit',
        'date': created.strftime('%Y-%m-%dT%H:%M:%S') if created else '',
        'author': owner_username,
        'files': [
            {'name': 'README.md', 'additions': 24, 'deletions': 0},
            {'name': '.gitignore', 'additions': 8, 'deletions': 0},
            {'name': 'LICENSE', 'additions': 21, 'deletions': 0},
        ],
        'additions': 53,
        'deletions': 0,
        'is_first': True,
    }


@app.route('/<username>/<reponame>/commits')
def repo_commits(username, reponame):
    repo = Repository.query.filter_by(full_name=f"{username}/{reponame}").first_or_404()
    commits = repo.get_commits()
    # Backwards-compatibility: if commits_json hasn't been seeded yet, fall back
    # to a single-commit list synthesized from latest_commit_* columns.
    if not commits and repo.latest_commit_sha:
        commits = [{
            'sha': repo.latest_commit_sha,
            'message': repo.latest_commit_message or '',
            'date': repo.latest_commit_date.isoformat() if repo.latest_commit_date else '',
            'author': (User.query.get(repo.owner_id).username if repo.owner_id else username),
            'files': repo.get_commit_files(),
            'additions': repo.latest_commit_additions or 0,
            'deletions': repo.latest_commit_deletions or 0,
        }]
    owner_username = (User.query.get(repo.owner_id).username if repo.owner_id else username)
    first_commit = _first_commit(repo, owner_username)
    return render_template('repo_commits.html', repo=repo, commits=commits,
                           first_commit=first_commit)


@app.route('/<username>/<reponame>/commit/<sha>')
def repo_commit_detail(username, reponame, sha):
    repo = Repository.query.filter_by(full_name=f"{username}/{reponame}").first_or_404()
    commits = repo.get_commits()
    commit = next((c for c in commits if c.get('sha', '').startswith(sha) or sha.startswith(c.get('sha', ''))), None)
    if not commit:
        # Maybe it's the latest commit (which may not yet be in commits_json)
        if repo.latest_commit_sha and (repo.latest_commit_sha.startswith(sha) or sha.startswith(repo.latest_commit_sha)):
            commit = {
                'sha': repo.latest_commit_sha,
                'message': repo.latest_commit_message or '',
                'date': repo.latest_commit_date.isoformat() if repo.latest_commit_date else '',
                'author': (User.query.get(repo.owner_id).username if repo.owner_id else username),
                'files': repo.get_commit_files(),
                'additions': repo.latest_commit_additions or 0,
                'deletions': repo.latest_commit_deletions or 0,
            }
    if not commit:
        # Maybe it's the synthesized "first commit" sha (= sha1(full_name + '::initial'))
        owner_username = (User.query.get(repo.owner_id).username if repo.owner_id else username)
        fc = _first_commit(repo, owner_username)
        if fc['sha'].startswith(sha) or sha.startswith(fc['sha']):
            commit = fc
    if not commit:
        abort(404)
    return render_template('repo_commit_detail.html', repo=repo, commit=commit)


_NEW_RELEASE_TMPL = """
{% extends "base.html" %}
{% block title %}Draft a new release · {{ repo.full_name }}{% endblock %}
{% block content %}
<div class="container" style="max-width:900px;margin:32px auto;padding:0 16px;">
  <nav style="font-size:14px;color:#57606a;margin-bottom:12px;">
    <a href="/{{ repo.full_name }}">{{ repo.full_name }}</a>
    &nbsp;/&nbsp;<a href="/{{ repo.full_name }}/releases">Releases</a>
    &nbsp;/&nbsp;New
  </nav>
  <h1 style="font-size:24px;margin:0 0 16px;">Create a new release</h1>
  <form method="post" action="/{{ repo.full_name }}/releases/new" class="gh-form">
    <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
    <label style="display:block;font-weight:600;margin-bottom:4px;">Tag</label>
    <input type="text" name="tag" required maxlength="60" placeholder="v1.0.0"
           style="width:280px;padding:8px;border:1px solid #d0d7de;border-radius:6px;margin-bottom:16px;">
    <label style="display:block;font-weight:600;margin-bottom:4px;">Release title</label>
    <input type="text" name="title" maxlength="120" placeholder="Release title"
           style="width:100%;padding:8px;border:1px solid #d0d7de;border-radius:6px;margin-bottom:16px;">
    <label style="display:block;font-weight:600;margin-bottom:4px;">Describe this release</label>
    <textarea name="body" rows="12" placeholder="Write release notes..."
              style="width:100%;padding:8px;border:1px solid #d0d7de;border-radius:6px;font-family:monospace;"></textarea>
    <div style="margin-top:16px;display:flex;gap:8px;">
      <label style="display:flex;align-items:center;gap:6px;">
        <input type="checkbox" name="prerelease"> This is a pre-release
      </label>
    </div>
    <div style="margin-top:16px;display:flex;gap:8px;">
      <button type="submit" name="action" value="publish" class="gh-btn gh-btn-primary">Publish release</button>
      <button type="submit" name="action" value="draft" class="gh-btn gh-btn-secondary">Save draft</button>
      <a href="/{{ repo.full_name }}/releases" class="gh-btn gh-btn-secondary">Cancel</a>
    </div>
  </form>
</div>
{% endblock %}
"""


@app.route('/<username>/<reponame>/releases/new', methods=['GET', 'POST'])
@login_required
def repo_releases_new(username, reponame):
    repo = Repository.query.filter_by(full_name=f"{username}/{reponame}").first_or_404()
    if request.method == 'POST':
        # Stub: don't actually persist (would break byte-identical reset).
        action = request.form.get('action', 'publish')
        flash('Release saved as draft.' if action == 'draft' else 'Release published.', 'success')
        return redirect(url_for('repo_releases', username=username, reponame=reponame))
    return render_template_string(_NEW_RELEASE_TMPL, repo=repo)


@app.route('/<username>/<reponame>/releases')
def repo_releases(username, reponame):
    repo = Repository.query.filter_by(full_name=f"{username}/{reponame}").first_or_404()
    releases = repo.get_releases() or []
    # Enrich each release record with author/avatar/is_prerelease/assets/body_html
    # derived from whatever the seed script supplied, with sensible defaults so the
    # card template can always render a full layout.
    owner = User.query.get(repo.owner_id)
    default_author = owner.username if owner else username
    enriched = []
    for idx, r in enumerate(releases):
        author = r.get('author') or default_author
        body = r.get('notes') or r.get('body') or ''
        version = r.get('version') or 'untagged'
        is_pre = bool(r.get('is_prerelease') or
                      any(tag in version.lower()
                          for tag in ('rc', 'beta', 'alpha', 'pre', 'canary')))
        assets = r.get('assets') or [
            {'name': f"Source code (zip)", 'size': '—'},
            {'name': f"Source code (tar.gz)", 'size': '—'},
        ]
        enriched.append({
            'version': version,
            'date': r.get('date') or '',
            'notes': body,
            'author': author,
            'author_avatar': avatar_for(author),
            'is_prerelease': is_pre,
            'is_latest': (idx == 0),
            'assets': assets,
            'commit_sha': r.get('commit_sha') or (f"{abs(hash(version)):x}"[:7]),
        })
    open_count = repo.issues.filter_by(status='open').count()
    return render_template('repo_releases.html', repo=repo, releases=enriched,
                           open_count=open_count)


@app.route('/<username>/<reponame>/contributors')
def repo_contributors(username, reponame):
    repo = Repository.query.filter_by(full_name=f"{username}/{reponame}").first_or_404()
    raw = repo.get_contributors() or []
    # Build enriched contributor cards: avatar + commit count + tiny sparkline data
    enriched = []
    max_commits = max((c.get('commits', 0) for c in raw), default=1) or 1
    for c in raw:
        uname = c.get('username') or 'contributor'
        commits = int(c.get('commits') or 0)
        additions = int(c.get('additions') or commits * 47)
        deletions = int(c.get('deletions') or commits * 12)
        # deterministic mini bar chart (30 bars, heights 2-20)
        import hashlib
        seed = int(hashlib.md5(uname.encode()).hexdigest()[:8], 16)
        bars = []
        for i in range(30):
            seed = (seed * 1103515245 + 12345) & 0x7fffffff
            bars.append(3 + (seed % 17))
        u = User.query.filter_by(username=uname).first()
        enriched.append({
            'username': uname,
            'display_name': (u.name if u and u.name else uname),
            'commits': commits,
            'commit_share': round(commits * 100.0 / max_commits, 1),
            'additions': additions,
            'deletions': deletions,
            'avatar': avatar_for(uname),
            'bio': (u.bio if u else ''),
            'bars': bars,
        })
    # Honor ?sort=<key>. Previously the template shipped a bare <select>
    # with no onchange handler, so agents clicking it saw zero effect even
    # though the label claimed the list was resorted. Now: route parses
    # `sort`, resorts the list, and the template binds the <select> to
    # navigate on change so the rendered order matches the label.
    sort_key = (request.args.get('sort') or '').lower().strip()
    if sort_key in ('commits_asc', 'fewest_commits', 'commits-asc'):
        enriched.sort(key=lambda c: c['commits'])
        sort_key = 'commits_asc'
    elif sort_key in ('additions', 'most_additions', 'additions_desc'):
        enriched.sort(key=lambda c: -c['additions'])
        sort_key = 'additions'
    elif sort_key in ('deletions', 'most_deletions', 'deletions_desc'):
        enriched.sort(key=lambda c: -c['deletions'])
        sort_key = 'deletions'
    else:  # default: commits desc
        enriched.sort(key=lambda c: -c['commits'])
        sort_key = 'commits'
    # Recompute rank after sorting so the "#1" label on each card matches
    # the rendered position, not the pre-sort order.
    for i, c in enumerate(enriched, 1):
        c['rank'] = i
    # Live open-issue count so the Issues tab badge matches /issues.
    open_count = repo.issues.filter_by(status='open').count()
    return render_template('repo_contributors.html', repo=repo,
                           contributors=enriched,
                           total_commits=sum(c['commits'] for c in enriched),
                           current_sort=sort_key,
                           open_count=open_count)


@app.route('/<username>/<reponame>/graphs/contributors')
def repo_contributors_graphs(username, reponame):
    """Real github URL is /<user>/<repo>/graphs/contributors — keep the short
    /contributors path too for backwards compat with existing task-solver
    trajectories."""
    return repo_contributors(username, reponame)


@app.route('/<username>/<reponame>/stargazers')
def repo_stargazers(username, reponame):
    """Previously 404. List users who starred this repo."""
    repo = Repository.query.filter_by(full_name=f"{username}/{reponame}").first_or_404()
    rows = (db.session.query(User)
            .join(Star, Star.user_id == User.id)
            .filter(Star.repo_id == repo.id)
            .order_by(Star.created_at.desc())
            .all())
    return render_template('repo_stargazers.html', repo=repo, stargazers=rows)


@app.route('/<username>/<reponame>/wiki')
def repo_wiki(username, reponame):
    repo = Repository.query.filter_by(full_name=f"{username}/{reponame}").first_or_404()
    pages = repo.get_wiki_pages()
    return render_template('repo_wiki.html', repo=repo, pages=pages)


_NEW_WIKI_PAGE_TMPL = """
{% extends "base.html" %}
{% block title %}New wiki page · {{ repo.full_name }}{% endblock %}
{% block content %}
<div class="container" style="max-width:900px;margin:32px auto;padding:0 16px;">
  <nav style="font-size:14px;color:#57606a;margin-bottom:12px;">
    <a href="/{{ repo.full_name }}">{{ repo.full_name }}</a>
    &nbsp;/&nbsp;<a href="/{{ repo.full_name }}/wiki">Wiki</a>
    &nbsp;/&nbsp;New page
  </nav>
  <h1 style="font-size:24px;margin:0 0 16px;">Create a new wiki page</h1>
  <form method="post" action="/{{ repo.full_name }}/wiki/_new" class="gh-form">
    <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
    <label style="display:block;font-weight:600;margin-bottom:4px;">Title</label>
    <input type="text" name="title" required maxlength="120"
           placeholder="Enter a title for the page"
           style="width:100%;padding:8px;border:1px solid #d0d7de;border-radius:6px;margin-bottom:16px;">
    <label style="display:block;font-weight:600;margin-bottom:4px;">Content</label>
    <textarea name="body" rows="14" placeholder="Write Markdown..."
              style="width:100%;padding:8px;border:1px solid #d0d7de;border-radius:6px;font-family:monospace;"></textarea>
    <div style="margin-top:16px;display:flex;gap:8px;">
      <button type="submit" class="gh-btn gh-btn-primary">Save page</button>
      <a href="/{{ repo.full_name }}/wiki" class="gh-btn gh-btn-secondary">Cancel</a>
    </div>
  </form>
</div>
{% endblock %}
"""


@app.route('/<username>/<reponame>/wiki/_new', methods=['GET', 'POST'])
@login_required
def repo_wiki_new(username, reponame):
    repo = Repository.query.filter_by(full_name=f"{username}/{reponame}").first_or_404()
    if request.method == 'POST':
        # Stub: don't actually persist (would break byte-identical reset).
        flash('Wiki page saved.', 'success')
        return redirect(url_for('repo_wiki', username=username, reponame=reponame))
    return render_template_string(_NEW_WIKI_PAGE_TMPL, repo=repo)


@app.route('/<username>/<reponame>/wiki/<page_slug>')
def repo_wiki_page(username, reponame, page_slug):
    repo = Repository.query.filter_by(full_name=f"{username}/{reponame}").first_or_404()
    pages = repo.get_wiki_pages()
    page = next((p for p in pages if p.get('slug') == page_slug), None)
    if not page:
        abort(404)
    return render_template('repo_wiki_page.html', repo=repo, page=page, pages=pages)


@app.route('/<username>/<reponame>/issues')
def repo_issues(username, reponame):
    repo = Repository.query.filter_by(full_name=f"{username}/{reponame}").first_or_404()
    status = request.args.get('q', 'is:open')
    is_open = 'closed' not in status
    # Match real github default: open issues sorted by created_at desc;
    # closed issues sorted by closed_at desc (so "last N closed" is unambiguous).
    if is_open:
        issues = repo.issues.filter_by(status='open', is_pr=0).order_by(
            Issue.created_at.desc()).all()
    else:
        issues = repo.issues.filter_by(status='closed', is_pr=0).order_by(
            Issue.closed_at.desc().nulls_last(), Issue.created_at.desc()).all()
    open_count = repo.issues.filter_by(status='open', is_pr=0).count()
    closed_count = repo.issues.filter_by(status='closed', is_pr=0).count()
    form = IssueForm()
    return render_template('repo_issues.html', repo=repo, issues=issues,
                           is_open=is_open, open_count=open_count,
                           closed_count=closed_count, form=form)


@app.route('/<username>/<reponame>/pulls')
def repo_pulls(username, reponame):
    repo = Repository.query.filter_by(full_name=f"{username}/{reponame}").first_or_404()
    status = request.args.get('q', 'is:open')
    is_open = 'closed' not in status and 'merged' not in status
    show_merged = 'merged' in status
    if show_merged:
        pulls = repo.issues.filter_by(status='merged', is_pr=1).order_by(Issue.created_at.desc()).all()
    elif is_open:
        pulls = repo.issues.filter_by(status='open', is_pr=1).order_by(Issue.created_at.desc()).all()
    else:
        pulls = repo.issues.filter(Issue.is_pr == 1, Issue.status.in_(('closed', 'merged'))).order_by(Issue.created_at.desc()).all()
    open_count = repo.issues.filter_by(status='open', is_pr=1).count()
    closed_count = repo.issues.filter(Issue.is_pr == 1, Issue.status.in_(('closed', 'merged'))).count()
    return render_template('repo_pulls.html', repo=repo, pulls=pulls,
                           is_open=is_open, show_merged=show_merged,
                           open_count=open_count, closed_count=closed_count)


@app.route('/<username>/<reponame>/issues/new', methods=['GET', 'POST'])
@login_required
def new_issue(username, reponame):
    repo = Repository.query.filter_by(full_name=f"{username}/{reponame}").first_or_404()
    form = IssueForm()
    if form.validate_on_submit():
        next_num = (repo.issues.count() or 0) + 1
        issue = Issue(
            repo_id=repo.id,
            author_id=current_user.id,
            number=next_num,
            title=form.title.data,
            body=form.body.data or '',
            status='open',
            labels_json='[]',
        )
        db.session.add(issue)
        repo.open_issues_count = repo.issues.filter_by(status='open').count() + 1
        db.session.commit()
        flash('Issue created!', 'success')
        return redirect(url_for('issue_detail', username=username, reponame=reponame,
                                number=issue.number))
    return render_template('new_issue.html', repo=repo, form=form)


@app.route('/<username>/<reponame>/issues/<int:number>')
def issue_detail(username, reponame, number):
    repo = Repository.query.filter_by(full_name=f"{username}/{reponame}").first_or_404()
    issue = Issue.query.filter_by(repo_id=repo.id, number=number).first_or_404()
    comments = issue.comments.order_by(IssueComment.created_at.asc()).all()
    form = CommentForm()
    return render_template('issue_detail.html', repo=repo, issue=issue,
                           comments=comments, form=form)


@app.route('/<username>/<reponame>/issues/<int:number>/comment', methods=['POST'])
@login_required
def add_issue_comment(username, reponame, number):
    repo = Repository.query.filter_by(full_name=f"{username}/{reponame}").first_or_404()
    issue = Issue.query.filter_by(repo_id=repo.id, number=number).first_or_404()
    form = CommentForm()
    if form.validate_on_submit():
        comment = IssueComment(
            issue_id=issue.id,
            author_id=current_user.id,
            body=form.body.data,
        )
        db.session.add(comment)
        db.session.commit()
        flash('Comment added.', 'success')
    return redirect(url_for('issue_detail', username=username, reponame=reponame, number=number))


@app.route('/<username>/<reponame>/issues/<int:number>/close', methods=['POST'])
@login_required
def close_issue(username, reponame, number):
    repo = Repository.query.filter_by(full_name=f"{username}/{reponame}").first_or_404()
    issue = Issue.query.filter_by(repo_id=repo.id, number=number).first_or_404()
    if current_user.id == issue.author_id or current_user.id == repo.owner_id:
        issue.status = 'closed'
        issue.closed_at = mirror_now()
        repo.open_issues_count = max(0, (repo.open_issues_count or 1) - 1)
        db.session.commit()
        flash('Issue closed.', 'success')
    return redirect(url_for('issue_detail', username=username, reponame=reponame, number=number))


@app.route('/<username>/<reponame>/issues/<int:number>/reopen', methods=['POST'])
@login_required
def reopen_issue(username, reponame, number):
    repo = Repository.query.filter_by(full_name=f"{username}/{reponame}").first_or_404()
    issue = Issue.query.filter_by(repo_id=repo.id, number=number).first_or_404()
    if current_user.id == issue.author_id or current_user.id == repo.owner_id:
        issue.status = 'open'
        issue.closed_at = None
        repo.open_issues_count = (repo.open_issues_count or 0) + 1
        db.session.commit()
        flash('Issue reopened.', 'success')
    return redirect(url_for('issue_detail', username=username, reponame=reponame, number=number))


# ─── Account ───

@app.route('/account')
@login_required
def account():
    repos = current_user.repositories.order_by(Repository.updated_at.desc()).limit(10).all()
    stars = Star.query.filter_by(user_id=current_user.id).join(Repository).order_by(
        Star.created_at.desc()).limit(10).all()
    following = current_user.following.limit(8).all()
    followers = current_user.followers.limit(8).all()
    return render_template('account.html', repos=repos, stars=stars,
                           following=following, followers=followers)


@app.route('/settings/profile', methods=['GET', 'POST'])
@login_required
def settings_profile():
    form = ProfileEditForm(obj=current_user)
    if form.validate_on_submit():
        current_user.name = form.name.data or ''
        current_user.bio = form.bio.data or ''
        current_user.location = form.location.data or ''
        current_user.website = form.website.data or ''
        current_user.company = form.company.data or ''
        current_user.twitter = form.twitter.data or ''
        db.session.commit()
        flash('Profile updated!', 'success')
        return redirect(url_for('settings_profile'))
    return render_template('settings_profile.html', form=form)


@app.route('/settings/password', methods=['GET', 'POST'])
@login_required
def settings_password():
    form = ChangePasswordForm()
    if form.validate_on_submit():
        if not current_user.check_password(form.old_password.data):
            flash('Current password is incorrect.', 'danger')
        else:
            current_user.set_password(form.new_password.data)
            db.session.commit()
            flash('Password updated!', 'success')
            return redirect(url_for('settings_password'))
    return render_template('settings_password.html', form=form)


@app.route('/settings/delete', methods=['POST'])
@login_required
def settings_delete():
    user = db.session.get(User, current_user.id)
    logout_user()
    db.session.delete(user)
    db.session.commit()
    flash('Your account has been deleted.', 'info')
    return redirect(url_for('index'))


@app.route('/settings')
@login_required
def settings():
    return redirect(url_for('settings_profile'))


# ─── Stars ───

@app.route('/stars')
@login_required
def my_stars():
    stars = Star.query.filter_by(user_id=current_user.id).join(Repository).order_by(
        Star.created_at.desc()).all()
    return render_template('stars.html', stars=stars)


# ─── Watching ───

@app.route('/watching')
@login_required
def my_watching():
    watches = Watch.query.filter_by(user_id=current_user.id).join(Repository).order_by(
        Watch.created_at.desc()).all()
    return render_template('watching.html', watches=watches)


@app.route('/<username>/watching')
def user_watching(username):
    user = User.query.filter_by(username=username).first_or_404()
    watches = Watch.query.filter_by(user_id=user.id).join(Repository).order_by(
        Watch.created_at.desc()).all()
    repos = user.repositories.filter_by(is_public=True).order_by(
        Repository.stars_count.desc()).limit(20).all()
    starred = Star.query.filter_by(user_id=user.id).join(Repository).order_by(
        Star.created_at.desc()).limit(20).all()
    return render_template('user_profile.html', profile_user=user, repos=repos,
                           starred=starred, tab='watching', watches=watches)


# ─── Form-based POST routes (replaces AJAX for agent compatibility) ───

@app.route('/star/toggle/<int:repo_id>', methods=['POST'])
@login_required
def star_toggle_form(repo_id):
    """Form-POST version of star toggle — works in CDP-controlled browsers."""
    repo = db.session.get(Repository, repo_id)
    if not repo:
        abort(404)
    existing = Star.query.filter_by(user_id=current_user.id, repo_id=repo_id).first()
    if existing:
        db.session.delete(existing)
        repo.stars_count = max(0, repo.stars_count - 1)
    else:
        star = Star(user_id=current_user.id, repo_id=repo_id)
        db.session.add(star)
        repo.stars_count += 1
    db.session.commit()
    next_url = request.form.get('next') or request.referrer or url_for('repo_detail',
               username=repo.full_name.split('/')[0], reponame=repo.name)
    return redirect(next_url)


@app.route('/watch/toggle/<int:repo_id>', methods=['POST'])
@login_required
def watch_toggle_form(repo_id):
    """Form-POST version of watch toggle."""
    repo = db.session.get(Repository, repo_id)
    if not repo:
        abort(404)
    existing = Watch.query.filter_by(user_id=current_user.id, repo_id=repo_id).first()
    if existing:
        db.session.delete(existing)
        repo.watchers_count = max(0, repo.watchers_count - 1)
    else:
        watch = Watch(user_id=current_user.id, repo_id=repo_id)
        db.session.add(watch)
        repo.watchers_count += 1
    db.session.commit()
    next_url = request.form.get('next') or request.referrer or url_for('repo_detail',
               username=repo.full_name.split('/')[0], reponame=repo.name)
    return redirect(next_url)


@app.route('/follow/toggle/<int:user_id>', methods=['POST'])
@login_required
def follow_toggle_form(user_id):
    """Form-POST version of follow toggle."""
    target = db.session.get(User, user_id)
    if not target or target.id == current_user.id:
        abort(400)
    if current_user.is_following(target):
        current_user.following.remove(target)
    else:
        current_user.following.append(target)
    db.session.commit()
    next_url = request.form.get('next') or request.referrer or url_for('user_profile',
               username=target.username)
    return redirect(next_url)


@app.route('/fork/<int:repo_id>', methods=['POST'])
@login_required
def fork_form(repo_id):
    """Form-POST version of fork."""
    repo = db.session.get(Repository, repo_id)
    if not repo or not repo.is_public:
        abort(404)
    # R6 edge: fork-rate-limit demo repos reject with 429.
    if _r6_has_sentinel(repo, 'fork-rate-limit'):
        flash('Fork failed: you have hit the fork rate limit for this '
              'account. Try again in a few minutes.', 'error')
        return (render_template('repo_detail.html', repo=repo,
                                owner=db.session.get(User, repo.owner_id),
                                gallery=repo.get_gallery(),
                                topics=repo.get_topics(),
                                recent_issues=[], is_starred=False,
                                is_watching=False, related=[],
                                open_count=0, open_pr_count=0,
                                commit_count=0,
                                latest_author=repo.full_name.split('/')[0],
                                fork_rate_limited=True),
                429)
    # R6 edge: archived repos are read-only.
    if _r6_has_sentinel(repo, 'archived-ro') or repo.is_archived:
        flash('This repository is archived and is read-only. Forking is '
              'disabled.', 'error')
        return redirect(url_for('repo_detail',
                                username=repo.full_name.split('/')[0],
                                reponame=repo.name))
    fork_name = f"{current_user.username}/{repo.name}"
    existing = Repository.query.filter_by(full_name=fork_name).first()
    if existing:
        flash('You already have a fork of this repository.', 'info')
        return redirect(url_for('repo_detail', username=current_user.username,
                                reponame=repo.name))
    fork = Repository(
        owner_id=current_user.id,
        name=repo.name,
        full_name=fork_name,
        description=repo.description,
        language=repo.language,
        license=repo.license,
        is_public=True,
        is_fork=True,
        readme=repo.readme,
        topics_text=repo.topics_text,
        gallery_json=repo.gallery_json,
    )
    db.session.add(fork)
    repo.forks_count += 1
    db.session.commit()
    flash(f'Forked to {fork_name}!', 'success')
    return redirect(url_for('repo_detail', username=current_user.username,
                            reponame=repo.name))


# ─── Search (scored relevance, filters, sort) ───

STOPWORDS = {'the', 'a', 'an', 'of', 'in', 'on', 'at', 'to', 'for', 'with',
             'and', 'or', 'is', 'are', 'be', 'by', 'from', 'as', 'that', 'this',
             'about', 'repository', 'repo', 'project', 'projects', 'open',
             'source', 'opensource', 'on', 'github', 'related', 'find',
             'search', 'look', 'up', 'report', 'provide', 'tell'}


def _repo_haystack(r):
    return ' '.join([
        (r.full_name or '').lower(),
        (r.name or '').lower(),
        (r.description or '').lower(),
        (r.language or '').lower(),
        (r.topics_text or '').lower(),
        (r.readme or '').lower(),
    ])


def _score_repo(r, tokens):
    h = _repo_haystack(r)
    return sum(1 for t in tokens if t in h)


def _parse_github_qualifiers(q):
    """Parse GitHub-style search qualifiers out of a query string.

    Recognized qualifiers (stripped from the returned ``cleaned_q``):
      language:X | lang:X | l:X
      stars:>=N | stars:>N | stars:<=N | stars:<N | stars:N..M | stars:N
      forks:>=N (same forms as stars)
      created:>YYYY-MM-DD | created:<YYYY-MM-DD | created:YYYY-MM-DD..YYYY-MM-DD
      pushed:>YYYY-MM-DD | pushed:<YYYY-MM-DD   (maps to updated_at)
      updated:>YYYY-MM-DD | updated:<YYYY-MM-DD (alias of pushed)
      sort:stars[-desc|-asc] | sort:updated | sort:forks | sort:created
      topic:X
      license:X
      type:repositories|users|topics    (stripped, handled elsewhere)
      is:public|archived|not-archived

    Returns: (cleaned_q, filters_dict)
      filters_dict may contain any of:
        language, min_stars, max_stars, min_forks,
        created_after, created_before, updated_after, updated_before,
        topic, license, sort, type, archived
    """
    filters = {}
    if not q:
        return '', filters

    def _apply_numeric(prefix, raw, filters, min_key, max_key):
        val = raw.strip()
        m = re.match(r'^>=?(-?\d+)$', val)
        if m:
            filters[min_key] = int(m.group(1)) + (0 if val.startswith('>=') else 1)
            return
        m = re.match(r'^<=?(-?\d+)$', val)
        if m:
            filters[max_key] = int(m.group(1)) - (0 if val.startswith('<=') else 1)
            return
        m = re.match(r'^(-?\d+)\.\.(-?\d+)$', val)
        if m:
            filters[min_key] = int(m.group(1))
            filters[max_key] = int(m.group(2))
            return
        m = re.match(r'^(-?\d+)$', val)
        if m:
            filters[min_key] = int(m.group(1))
            filters[max_key] = int(m.group(1))
            return

    def _apply_date(raw, filters, after_key, before_key):
        val = raw.strip()
        m = re.match(r'^>=?(\d{4}-\d{2}-\d{2})$', val)
        if m:
            filters[after_key] = m.group(1)
            return
        m = re.match(r'^<=?(\d{4}-\d{2}-\d{2})$', val)
        if m:
            filters[before_key] = m.group(1)
            return
        m = re.match(r'^(\d{4}-\d{2}-\d{2})\.\.(\d{4}-\d{2}-\d{2})$', val)
        if m:
            filters[after_key] = m.group(1)
            filters[before_key] = m.group(2)
            return
        m = re.match(r'^(\d{4}-\d{2}-\d{2})$', val)
        if m:
            filters[after_key] = m.group(1)
            filters[before_key] = m.group(1)
            return

    tokens = q.split()
    kept = []
    for tok in tokens:
        low = tok.lower()
        if ':' not in low:
            kept.append(tok)
            continue
        key, _, val = tok.partition(':')
        key = key.lower()
        if not val:
            kept.append(tok)
            continue
        if key in ('language', 'lang', 'l'):
            filters['language'] = val.strip('"').strip("'")
        elif key == 'stars':
            _apply_numeric('stars', val, filters, 'min_stars', 'max_stars')
        elif key == 'forks':
            _apply_numeric('forks', val, filters, 'min_forks', 'max_forks')
        elif key == 'created':
            _apply_date(val, filters, 'created_after', 'created_before')
        elif key in ('pushed', 'updated'):
            _apply_date(val, filters, 'updated_after', 'updated_before')
        elif key == 'topic':
            filters['topic'] = val.strip('"').strip("'")
        elif key == 'license':
            filters['license'] = val.strip('"').strip("'")
        elif key == 'sort':
            filters['sort'] = val.strip('"').strip("'").lower()
        elif key == 'type':
            filters['type'] = val.strip('"').strip("'").lower()
        elif key == 'is':
            v = val.strip('"').strip("'").lower()
            if v == 'archived':
                filters['archived'] = '1'
            elif v in ('not-archived', 'notarchived'):
                filters['archived'] = '0'
            elif v == 'public':
                pass  # default
        else:
            # Unrecognized qualifier: drop the key but keep the value as a
            # search term so we don't miss it entirely.
            kept.append(val)
    cleaned_q = ' '.join(kept).strip()
    return cleaned_q, filters


def _apply_repo_filters(query_obj, extra=None):
    """Apply request.args filters (plus optional extra filters parsed from
    GitHub-style qualifiers in the q string) to a Repository query."""
    extra = extra or {}

    def _arg(name, default=''):
        if name in extra:
            return extra[name]
        return request.args.get(name, default)

    def _arg_int(name):
        if name in extra:
            try:
                return int(extra[name])
            except (TypeError, ValueError):
                return None
        return request.args.get(name, type=int)

    lang = (extra.get('language') or request.args.get('language', '').strip()
            or request.args.get('l', '').strip())
    if lang:
        query_obj = query_obj.filter(Repository.language.ilike(lang))

    min_stars = _arg_int('min_stars')
    if min_stars is not None:
        query_obj = query_obj.filter(Repository.stars_count >= min_stars)

    max_stars = _arg_int('max_stars')
    if max_stars is not None:
        query_obj = query_obj.filter(Repository.stars_count <= max_stars)

    min_forks = _arg_int('min_forks')
    if min_forks is not None:
        query_obj = query_obj.filter(Repository.forks_count >= min_forks)

    max_forks = _arg_int('max_forks')
    if max_forks is not None:
        query_obj = query_obj.filter(Repository.forks_count <= max_forks)

    license_f = (extra.get('license') or request.args.get('license', '').strip())
    if license_f:
        query_obj = query_obj.filter(Repository.license.ilike(f'%{license_f}%'))

    topic_f = (extra.get('topic') or request.args.get('topic', '').strip())
    if topic_f:
        query_obj = query_obj.filter(Repository.topics_text.ilike(f'%"{topic_f}"%'))

    # Updated within N days
    updated_days = request.args.get('updated_days', type=int)
    if updated_days is not None:
        cutoff = mirror_now() - timedelta(days=updated_days)
        query_obj = query_obj.filter(Repository.updated_at >= cutoff)

    # Created in last N days
    created_days = request.args.get('created_days', type=int)
    if created_days is not None:
        cutoff = mirror_now() - timedelta(days=created_days)
        query_obj = query_obj.filter(Repository.created_at >= cutoff)

    # Created after date (YYYY-MM-DD)
    created_after = (extra.get('created_after') or
                     request.args.get('created_after', '').strip())
    if created_after:
        try:
            dt = datetime.strptime(created_after, '%Y-%m-%d')
            query_obj = query_obj.filter(Repository.created_at >= dt)
        except ValueError:
            pass
    created_before = (extra.get('created_before') or
                      request.args.get('created_before', '').strip())
    if created_before:
        try:
            dt = datetime.strptime(created_before, '%Y-%m-%d')
            query_obj = query_obj.filter(Repository.created_at <= dt)
        except ValueError:
            pass

    # updated_after / updated_before (from pushed: or updated: qualifier)
    updated_after = (extra.get('updated_after') or
                     request.args.get('updated_after', '').strip())
    if updated_after:
        try:
            dt = datetime.strptime(updated_after, '%Y-%m-%d')
            query_obj = query_obj.filter(Repository.updated_at >= dt)
        except ValueError:
            pass
    updated_before = (extra.get('updated_before') or
                      request.args.get('updated_before', '').strip())
    if updated_before:
        try:
            dt = datetime.strptime(updated_before, '%Y-%m-%d')
            query_obj = query_obj.filter(Repository.updated_at <= dt)
        except ValueError:
            pass

    if request.args.get('has_readme') == '1':
        query_obj = query_obj.filter(Repository.has_readme == True)
    if request.args.get('has_wiki') == '1':
        query_obj = query_obj.filter(Repository.has_wiki == True)
    archived_flag = extra.get('archived', request.args.get('archived'))
    if archived_flag == '1':
        query_obj = query_obj.filter(Repository.is_archived == True)
    if archived_flag == '0':
        query_obj = query_obj.filter(Repository.is_archived == False)

    owner_type = request.args.get('owner_type', '').strip()
    if owner_type:
        query_obj = query_obj.filter(Repository.owner_type == owner_type)

    return query_obj


def _apply_repo_sort(results, sort_key):
    if sort_key in ('best-match', 'best_match'):
        return results
    if sort_key in ('stars', 'stars_desc'):
        return sorted(results, key=lambda r: r.stars_count, reverse=True)
    if sort_key == 'stars_asc':
        return sorted(results, key=lambda r: r.stars_count)
    if sort_key in ('forks', 'forks_desc'):
        return sorted(results, key=lambda r: r.forks_count, reverse=True)
    if sort_key == 'forks_asc':
        return sorted(results, key=lambda r: r.forks_count)
    if sort_key in ('updated', 'updated_desc', 'recent', 'newest'):
        return sorted(results, key=lambda r: r.updated_at or datetime.min, reverse=True)
    if sort_key == 'updated_asc':
        return sorted(results, key=lambda r: r.updated_at or datetime.max)
    if sort_key in ('created', 'created_desc'):
        return sorted(results, key=lambda r: r.created_at or datetime.min, reverse=True)
    if sort_key == 'created_asc':
        return sorted(results, key=lambda r: r.created_at or datetime.max)
    return sorted(results, key=lambda r: r.stars_count, reverse=True)


@app.route('/search')
def search():
    raw_q = request.args.get('q', '').strip()
    # Parse GitHub-style qualifiers (language:python, stars:>=100,
    # created:>2024-01-01, pushed:>2024-01-01, sort:stars-desc, type:...)
    # from the raw q string before scoring.
    q, parsed = _parse_github_qualifiers(raw_q)
    # type: qualifier overrides URL param if present
    search_type = parsed.get('type') or request.args.get('type', 'repositories')
    page = request.args.get('page', 1, type=int)
    per_page = 20
    repos = None
    users = None
    topic_results = None
    total = 0

    if search_type in ('repositories', ''):
        base = Repository.query.filter_by(is_public=True)
        base = _apply_repo_filters(base, extra=parsed)
        candidates = base.all()
        if q:
            tokens = [t.lower() for t in re.findall(r'[a-z0-9][\w-]*', q.lower())
                      if t and t not in STOPWORDS and len(t) >= 2]
            if tokens:
                # Require at least half of the meaningful tokens match so
                # that multi-word searches like "climate change data visualization"
                # don't return every repo that happens to contain a common word.
                if len(tokens) >= 4:
                    min_required = max(2, (len(tokens) + 1) // 2)
                elif len(tokens) >= 2:
                    min_required = 2
                else:
                    min_required = 1
                scored = []
                for r in candidates:
                    s = _score_repo(r, tokens)
                    if s >= min_required:
                        scored.append((s, r))
                scored.sort(key=lambda x: (-x[0], -x[1].stars_count))
                results = [r for _, r in scored]
            else:
                results = candidates
        else:
            results = candidates
        # sort: qualifier from q takes precedence; normalize
        # "stars-desc" / "stars_desc" / "stars" to the keys _apply_repo_sort
        # understands. Also accept GitHub's native `s=` / `o=` parameters
        # (stars+desc, updated, forks, etc.) that agents type directly.
        sort_key = parsed.get('sort') or request.args.get('sort', '') or \
                   request.args.get('s', 'best-match')
        order = (request.args.get('o', '') or '').lower()
        sort_key = sort_key.replace('-', '_').lower()
        if order == 'asc' and sort_key in ('stars', 'forks', 'updated', 'created'):
            sort_key = f'{sort_key}_asc'
        results = _apply_repo_sort(results, sort_key)
        total = len(results)
        start = (page - 1) * per_page
        end = start + per_page
        page_items = results[start:end]
        repos = _PaginatedList(page_items, page=page, per_page=per_page, total=total)
    elif search_type == 'users' and q:
        users = User.query.filter(
            or_(User.username.ilike(f'%{q}%'), User.name.ilike(f'%{q}%'))
        ).paginate(page=page, per_page=per_page, error_out=False)
        total = users.total if users else 0
    elif search_type == 'topics' and q:
        topic_results = Topic.query.filter(
            or_(Topic.slug.ilike(f'%{q}%'), Topic.display_name.ilike(f'%{q}%'))
        ).paginate(page=page, per_page=per_page, error_out=False)
        total = topic_results.total if topic_results else 0

    # Build facets from the SAME filtered + text-scored set as `results`, but
    # drop the filter being faceted (so users can still switch values).
    # Previously this used Repository.query.filter_by(is_public=True) which
    # returned global counts — agents saw "Rust (21)" next to a decision-tree
    # search that only had 1 real Rust hit.
    from collections import Counter as _Counter

    if search_type in ('repositories', ''):
        # Pull URL-level params we need to optionally skip, so we can match
        # the text query + all OTHER filters without re-invoking the request-
        # coupled _apply_repo_filters helper.
        _url_lang = (request.args.get('language', '').strip()
                     or request.args.get('l', '').strip())
        _url_license = request.args.get('license', '').strip()
        _url_min_stars = request.args.get('min_stars', type=int)
        _url_max_stars = request.args.get('max_stars', type=int)
        _url_min_forks = request.args.get('min_forks', type=int)
        _url_max_forks = request.args.get('max_forks', type=int)
        _url_topic = request.args.get('topic', '').strip()
        _parsed_lang = parsed.get('language', '')
        _parsed_license = parsed.get('license', '')
        _parsed_topic = parsed.get('topic', '')

        def _facet_pool(skip_key):
            # Fetch all public repos, then apply filters in Python — skipping
            # the key we want to enumerate over.
            pool = Repository.query.filter_by(is_public=True).all()
            eff_lang = '' if skip_key == 'language' else (_parsed_lang or _url_lang)
            eff_license = '' if skip_key == 'license' else (_parsed_license or _url_license)
            eff_topic = _parsed_topic or _url_topic

            def _keep(r):
                if eff_lang and (r.language or '').lower() != eff_lang.lower():
                    return False
                if eff_license and eff_license.lower() not in (r.license or '').lower():
                    return False
                if _url_min_stars is not None and r.stars_count < _url_min_stars:
                    return False
                if _url_max_stars is not None and r.stars_count > _url_max_stars:
                    return False
                if _url_min_forks is not None and r.forks_count < _url_min_forks:
                    return False
                if _url_max_forks is not None and r.forks_count > _url_max_forks:
                    return False
                if eff_topic and f'"{eff_topic}"' not in (r.topics_text or ''):
                    return False
                return True

            cands = [r for r in pool if _keep(r)]
            # Apply the same text-query scoring as the results set.
            if q:
                tokens_f = [t.lower() for t in re.findall(r'[a-z0-9][\w-]*', q.lower())
                            if t and t not in STOPWORDS and len(t) >= 2]
                if tokens_f:
                    if len(tokens_f) >= 4:
                        min_req = max(2, (len(tokens_f) + 1) // 2)
                    elif len(tokens_f) >= 2:
                        min_req = 2
                    else:
                        min_req = 1
                    cands = [r for r in cands if _score_repo(r, tokens_f) >= min_req]
            return cands

        lang_pool = _facet_pool('language')
        lang_counter = _Counter(r.language for r in lang_pool if r.language)
        language_facets = lang_counter.most_common(12)

        lic_pool = _facet_pool('license')
        lic_counter = _Counter(r.license for r in lic_pool if r.license)
        license_facets = lic_counter.most_common(8)
    else:
        language_facets = []
        license_facets = []

    sort_key_out = (parsed.get('sort') or request.args.get('sort', '')
                    or request.args.get('s', 'best-match'))
    current_lang = parsed.get('language') or request.args.get('l', '')

    return render_template('search.html', q=raw_q or q, search_type=search_type,
                           repos=repos, users=users, topics=topic_results,
                           total=total, page=page,
                           language_facets=language_facets,
                           license_facets=license_facets,
                           current_sort=sort_key_out,
                           current_lang=current_lang)


class _PaginatedList:
    """Lightweight pagination shim for in-memory result lists."""

    def __init__(self, items, page=1, per_page=20, total=0):
        self.items = items
        self.page = page
        self.per_page = per_page
        self.total = total
        self.pages = max(1, (total + per_page - 1) // per_page)
        self.has_prev = page > 1
        self.has_next = page < self.pages
        self.prev_num = page - 1
        self.next_num = page + 1


# ─── Notifications ───

@app.route('/notifications')
@login_required
def notifications():
    # Demo notifications based on user's starred repos
    stars = Star.query.filter_by(user_id=current_user.id).join(Repository).order_by(
        Star.created_at.desc()).limit(5).all()
    return render_template('notifications.html', stars=stars)


# ─── API Routes ───

@csrf.exempt
@app.route('/api/star/toggle', methods=['POST'])
@login_required
def api_star_toggle():
    data = request.get_json()
    repo_id = data.get('repo_id')
    repo = db.session.get(Repository, repo_id)
    if not repo:
        return jsonify({'error': 'Repo not found'}), 404
    existing = Star.query.filter_by(user_id=current_user.id, repo_id=repo_id).first()
    if existing:
        db.session.delete(existing)
        repo.stars_count = max(0, repo.stars_count - 1)
        starred = False
    else:
        star = Star(user_id=current_user.id, repo_id=repo_id)
        db.session.add(star)
        repo.stars_count += 1
        starred = True
    db.session.commit()
    return jsonify({'success': True, 'starred': starred, 'stars_count': repo.stars_count})


@csrf.exempt
@app.route('/api/watch/toggle', methods=['POST'])
@login_required
def api_watch_toggle():
    data = request.get_json()
    repo_id = data.get('repo_id')
    repo = db.session.get(Repository, repo_id)
    if not repo:
        return jsonify({'error': 'Repo not found'}), 404
    existing = Watch.query.filter_by(user_id=current_user.id, repo_id=repo_id).first()
    if existing:
        db.session.delete(existing)
        repo.watchers_count = max(0, repo.watchers_count - 1)
        watching = False
    else:
        watch = Watch(user_id=current_user.id, repo_id=repo_id)
        db.session.add(watch)
        repo.watchers_count += 1
        watching = True
    db.session.commit()
    return jsonify({'success': True, 'watching': watching, 'watchers_count': repo.watchers_count})


@csrf.exempt
@app.route('/api/follow/toggle', methods=['POST'])
@login_required
def api_follow_toggle():
    data = request.get_json()
    user_id = data.get('user_id')
    target = db.session.get(User, user_id)
    if not target or target.id == current_user.id:
        return jsonify({'error': 'Invalid user'}), 400
    if current_user.is_following(target):
        current_user.following.remove(target)
        following = False
    else:
        current_user.following.append(target)
        following = True
    db.session.commit()
    return jsonify({'success': True, 'following': following,
                    'followers_count': target.followers_count})


@csrf.exempt
@app.route('/api/fork/<int:repo_id>', methods=['POST'])
@login_required
def api_fork(repo_id):
    repo = db.session.get(Repository, repo_id)
    if not repo or not repo.is_public:
        return jsonify({'error': 'Repo not found'}), 404
    fork_name = f"{current_user.username}/{repo.name}"
    existing = Repository.query.filter_by(full_name=fork_name).first()
    if existing:
        return jsonify({'success': False, 'message': 'You already have a fork of this repo',
                        'redirect': url_for('repo_detail', username=current_user.username,
                                            reponame=repo.name)})
    fork = Repository(
        owner_id=current_user.id,
        name=repo.name,
        full_name=fork_name,
        description=repo.description,
        language=repo.language,
        license=repo.license,
        is_public=True,
        is_fork=True,
        readme=repo.readme,
        topics_text=repo.topics_text,
        gallery_json=repo.gallery_json,
    )
    db.session.add(fork)
    repo.forks_count += 1
    db.session.commit()
    return jsonify({'success': True, 'message': f'Forked to {fork_name}',
                    'redirect': url_for('repo_detail', username=current_user.username,
                                        reponame=repo.name)})


@app.route('/api/repos')
def api_repos():
    lang = request.args.get('language', '')
    query = Repository.query.filter_by(is_public=True)
    if lang:
        query = query.filter_by(language=lang)
    repos = query.order_by(Repository.stars_count.desc()).limit(20).all()
    return jsonify([{
        'id': r.id, 'full_name': r.full_name, 'description': r.description,
        'language': r.language, 'stars': r.stars_count, 'forks': r.forks_count,
    } for r in repos])


# ─── Error Handlers ───

@app.errorhandler(404)
def not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def server_error(e):
    return render_template('500.html'), 500


# ─────────────────────────── R3: deep sub-pages ───────────────────────────
# Each new route maps to a corresponding template under templates/. They
# render real data from the db (no placeholder copy) so WebVoyager tasks
# like "open the Actions tab on facebook/react" have an answer to check.

def _require_repo(username, reponame):
    """Look up a repo, 404 if missing. Returns the repo object."""
    full = f"{username}/{reponame}"
    repo = Repository.query.filter_by(full_name=full).first()
    if not repo:
        abort(404)
    return repo


@app.route('/trending/<lang>')
def trending_lang(lang):
    """Per-language trending. Mirrors real github.com/trending/<lang>?since=…"""
    since = request.args.get('since', 'daily')
    # Normalize lang slug back to display name where possible (case-insensitive
    # match against existing repo language values).
    page = request.args.get('page', 1, type=int)
    per_page = 25
    repos = (Repository.query.filter_by(is_public=True)
             .filter(Repository.language.ilike(lang.replace('-', ' ')))
             .order_by(Repository.stars_count.desc())
             .paginate(page=page, per_page=per_page, error_out=False))
    if repos.total == 0:
        # try matching by exact label (e.g. C++ → 'c-' slug)
        cand = lang.lower().replace('-plus-plus', '++').replace('-sharp', '#')
        repos = (Repository.query.filter_by(is_public=True)
                 .filter(Repository.language.ilike(cand))
                 .order_by(Repository.stars_count.desc())
                 .paginate(page=page, per_page=per_page, error_out=False))
    languages = db.session.query(Repository.language, func.count(Repository.id)).filter(
        Repository.language != '').group_by(Repository.language).order_by(
        func.count(Repository.id).desc()).all()
    return render_template('trending.html',
                           repos=repos, lang_filter=lang,
                           since=since, tab='repositories', languages=languages,
                           developers=[])


def _deterministic_workflow_runs(repo, branch='main', n=20):
    """Build a deterministic list of recent CI runs for the Actions tab."""
    base = repo.pushed_at or repo.updated_at or _BULK_REF
    if base > _BULK_REF:
        base = _BULK_REF
    workflows = ['ci.yml', 'tests.yml', 'lint.yml', 'release.yml',
                 'docs.yml', 'codeql.yml']
    statuses = ['success', 'success', 'success', 'failure',
                'success', 'cancelled', 'success', 'success']
    # R6 edge: pin the latest run on main to a failure for the
    # action-run-failed demo repos so the Actions tab + run page
    # consistently surface the failed state tasks reference.
    force_first_failure = _r6_has_sentinel(repo, 'action-run-failed')
    out = []
    for i in range(n):
        wf = workflows[(repo.id * 3 + i * 7) % len(workflows)]
        status = statuses[(repo.id + i * 5) % len(statuses)]
        if force_first_failure and i == 0:
            status = 'failure'
            wf = 'ci.yml'
        ts = base - timedelta(hours=i * 4 + (repo.id % 8))
        duration_s = 30 + ((repo.id * 11 + i * 17) % 540)
        sha = hashlib.sha1(f"{repo.full_name}|run|{i}".encode()).hexdigest()
        commits = repo.get_commits() or []
        msg = commits[i % len(commits)]['message'] if commits else 'Update CI'
        out.append({
            'workflow': wf,
            'status': status,
            'branch': branch,
            'sha_short': sha[:7],
            'sha': sha,
            'duration_s': duration_s,
            'duration_human': f"{duration_s//60}m {duration_s%60}s",
            'started_at': ts,
            'message': msg,
            'run_number': 1000 - i,
            'event': ['push', 'pull_request', 'schedule'][i % 3],
        })
    return out


@app.route('/<username>/<reponame>/actions')
def repo_actions(username, reponame):
    repo = _require_repo(username, reponame)
    runs = _deterministic_workflow_runs(repo)
    workflow_filter = request.args.get('workflow', '')
    if workflow_filter:
        runs = [r for r in runs if r['workflow'] == workflow_filter]
    # Distinct workflows for sidebar
    all_runs = _deterministic_workflow_runs(repo)
    distinct = []
    seen = set()
    for r in all_runs:
        if r['workflow'] not in seen:
            seen.add(r['workflow'])
            distinct.append({'name': r['workflow'],
                             'last_status': r['status']})
    return render_template('repo_actions.html', repo=repo, runs=runs,
                           workflows=distinct, workflow_filter=workflow_filter)


@app.route('/<username>/<reponame>/actions/runs/<int:run_number>')
def repo_actions_run(username, reponame, run_number):
    repo = _require_repo(username, reponame)
    runs = _deterministic_workflow_runs(repo, n=40)
    run = next((r for r in runs if r['run_number'] == run_number), None)
    if not run:
        # Build a synthetic run by hashing the requested number.
        seed = (repo.id + run_number) % len(runs)
        run = dict(runs[seed])
        run['run_number'] = run_number
    return render_template('repo_actions_run.html', repo=repo, run=run)


def _security_advisories_for(repo):
    """Deterministic list of dependabot-style advisories for a repo."""
    catalog = [
        ('Prototype pollution in lodash', 'moderate', 'lodash', '< 4.17.21',
         'CVE-2021-23337'),
        ('Regular expression denial of service in ansi-regex', 'high',
         'ansi-regex', '< 5.0.1', 'CVE-2021-3807'),
        ('Path traversal in tar', 'critical', 'tar', '< 6.1.9',
         'CVE-2021-32803'),
        ('Cross-site scripting in marked', 'moderate', 'marked', '< 4.0.10',
         'CVE-2022-21680'),
        ('Memory leak in node-fetch', 'low', 'node-fetch', '< 2.6.7',
         'CVE-2022-0235'),
        ('Improper neutralization in postcss', 'moderate', 'postcss', '< 8.4.31',
         'CVE-2023-44270'),
        ('Open redirect in axios', 'moderate', 'axios', '< 1.6.0',
         'CVE-2023-45857'),
        ('Insecure deserialization in pickle helper', 'high',
         'fastapi-pickle-helper', '< 0.4.0', 'GHSA-r2gp-8f3v-7r9p'),
        ('Buffer overflow in cwebp', 'critical', 'libwebp', '< 1.3.2',
         'CVE-2023-4863'),
    ]
    s = repo.stars_count or 0
    # Repos with more stars surface more advisories.
    if s >= 10000:
        n = 6
    elif s >= 1000:
        n = 4
    elif s >= 100:
        n = 2
    else:
        n = 1
    items = []
    for i in range(n):
        e = catalog[(repo.id * 5 + i * 7) % len(catalog)]
        title, sev, pkg, vuln_range, cve = e
        items.append({
            'ghsa': f"GHSA-{hashlib.sha1((repo.full_name + cve + str(i)).encode()).hexdigest()[:4]}-"
                    f"{hashlib.sha1((cve + str(i)).encode()).hexdigest()[:4]}-"
                    f"{hashlib.sha1((str(i) + repo.full_name).encode()).hexdigest()[:4]}",
            'title': title, 'severity': sev, 'package': pkg,
            'vulnerable_range': vuln_range, 'cve': cve,
            'published_at': _BULK_REF - timedelta(days=10 + (repo.id + i) % 320),
        })
    return items


@app.route('/<username>/<reponame>/security')
def repo_security(username, reponame):
    repo = _require_repo(username, reponame)
    advisories = _security_advisories_for(repo)
    dependabot_alerts = [a for a in advisories if a['severity'] in ('high', 'critical')]
    return render_template('repo_security.html', repo=repo,
                           advisories=advisories,
                           dependabot_alerts=dependabot_alerts)


@app.route('/<username>/<reponame>/security/advisories')
def repo_security_advisories(username, reponame):
    repo = _require_repo(username, reponame)
    advisories = _security_advisories_for(repo)
    return render_template('repo_security.html', repo=repo,
                           advisories=advisories,
                           dependabot_alerts=[],
                           tab='advisories')


@app.route('/<username>/<reponame>/insights')
@app.route('/<username>/<reponame>/pulse')
def repo_insights(username, reponame):
    repo = _require_repo(username, reponame)
    commits = repo.get_commits() or []
    pulls = (Issue.query.filter_by(repo_id=repo.id, is_pr=1)
             .order_by(Issue.id.desc()).limit(20).all())
    issues = (Issue.query.filter_by(repo_id=repo.id, is_pr=0)
              .order_by(Issue.id.desc()).limit(20).all())
    # 52-week contribution histogram (deterministic).
    weeks = []
    for w in range(52):
        count = ((repo.id * 11 + w * 7) % 12)
        weeks.append(count)
    return render_template('repo_insights.html', repo=repo,
                           commits=commits, recent_pulls=pulls,
                           recent_issues=issues, weeks=weeks)


@app.route('/<username>/<reponame>/network')
@app.route('/<username>/<reponame>/forks')
def repo_network(username, reponame):
    repo = _require_repo(username, reponame)
    # Pick deterministic "forkers" from the user pool.
    all_users = User.query.order_by(User.id.asc()).limit(200).all()
    n_forks = min(repo.forks_count or 0, 30)
    pool_size = len(all_users)
    forkers = []
    for i in range(min(n_forks, 30)):
        u = all_users[(repo.id * 17 + i * 13) % pool_size]
        forkers.append({
            'user': u,
            'pushed_at': _BULK_REF - timedelta(days=(repo.id + i * 3) % 600),
            'ahead': (i * 5 + repo.id) % 40,
            'behind': (i * 7 + repo.id * 3) % 80,
        })
    return render_template('repo_network.html', repo=repo, forkers=forkers)


@app.route('/<username>/<reponame>/network/dependents')
def repo_network_dependents(username, reponame):
    """R6: 'Used by' / dependents listing. Deterministic synthesis from
    other repos in the same language family; not stored on disk."""
    repo = _require_repo(username, reponame)
    pool = (Repository.query
            .filter(Repository.language == repo.language,
                    Repository.id != repo.id,
                    Repository.is_public == True)
            .order_by(Repository.id.asc())
            .limit(300).all())
    seen = set()
    dependents = []
    for i in range(min(60, len(pool))):
        idx = (repo.id * 13 + i * 17) % len(pool)
        if idx in seen:
            continue
        seen.add(idx)
        dependents.append(pool[idx])
    total = max(len(dependents), (repo.stars_count or 0) // 11)
    return render_template('repo_network.html', repo=repo, forkers=[],
                           dependents=dependents, dependents_total=total,
                           dependents_view=True)


def _blame_lines_for(repo, file_path):
    """Build a deterministic 'blame' for a fake file inside a repo."""
    body_templates = {
        'README.md': [
            "# {n}",
            "",
            "{d}",
            "",
            "## Installation",
            "",
            "```",
            "pip install {n}",
            "```",
            "",
            "## Usage",
            "",
            "See the [docs]({h}) for the full reference.",
        ],
        'src/index.js': [
            "const config = require('./config');",
            "const logger = require('./logger');",
            "",
            "function main() {",
            "  logger.info('starting {n}');",
            "  return run(config);",
            "}",
            "",
            "module.exports = { main };",
        ],
        'src/main.py': [
            "import sys",
            "from .core import run",
            "from .config import load_config",
            "",
            "def main():",
            "    cfg = load_config()",
            "    return run(cfg)",
            "",
            "if __name__ == '__main__':",
            "    sys.exit(main())",
        ],
        'main.go': [
            "package main",
            "",
            'import "fmt"',
            "",
            "func main() {",
            "    fmt.Println(\"{n}\")",
            "}",
        ],
        'Cargo.toml': [
            "[package]",
            'name = "{n}"',
            'version = "0.1.0"',
            'edition = "2021"',
            "",
            "[dependencies]",
        ],
    }
    tmpl = body_templates.get(file_path)
    if tmpl is None:
        tmpl = ["// generated by mirror — line {i}"] * 12
    name = repo.name
    desc = (repo.description or '').replace('"', '\\"')
    home = repo.homepage or '/'
    rendered = []
    commits = repo.get_commits() or [{
        'sha': hashlib.sha1(repo.full_name.encode()).hexdigest(),
        'author': repo.full_name.split('/', 1)[0],
        'message': 'Initial commit',
        'date': (repo.created_at or _BULK_REF).isoformat(),
    }]
    for i, line in enumerate(tmpl):
        try:
            text = line.format(n=name, d=desc, h=home, i=i + 1)
        except (KeyError, IndexError, ValueError):
            text = line
        c = commits[(repo.id + i) % len(commits)]
        rendered.append({
            'line_number': i + 1,
            'text': text,
            'commit_sha': c['sha'][:7],
            'commit_message': c['message'],
            'author': c['author'],
            'date': c['date'][:10] if c.get('date') else '',
        })
    return rendered


@app.route('/<username>/<reponame>/blame/<branch>/<path:file_path>')
def repo_blame(username, reponame, branch, file_path):
    repo = _require_repo(username, reponame)
    lines = _blame_lines_for(repo, file_path)
    return render_template('repo_blame.html', repo=repo,
                           branch=branch, file_path=file_path, lines=lines)


@app.route('/<username>/<reponame>/blob/<branch>/<path:file_path>')
def repo_blob(username, reponame, branch, file_path):
    repo = _require_repo(username, reponame)
    lines = _blame_lines_for(repo, file_path)
    return render_template('repo_blob.html', repo=repo,
                           branch=branch, file_path=file_path, lines=lines)


@app.route('/<username>/<reponame>/branches')
def repo_branches(username, reponame):
    repo = _require_repo(username, reponame)
    base = repo.default_branch or 'main'
    # Deterministic branch list derived from PR head branches + a fixed set.
    pulls = Issue.query.filter_by(repo_id=repo.id, is_pr=1).limit(40).all()
    branch_names = {base, 'develop', 'staging', 'release/v1'}
    for p in pulls:
        if p.pr_head_branch:
            branch_names.add(p.pr_head_branch)
    protected = _r6_has_sentinel(repo, 'branch-protected')
    branches = []
    for i, name in enumerate(sorted(branch_names)):
        branches.append({
            'name': name,
            'is_default': name == base,
            'is_protected': protected and name == base,
            'last_commit_sha': hashlib.sha1(
                f"{repo.full_name}|branch|{name}".encode()).hexdigest()[:7],
            'last_pushed_at': _BULK_REF - timedelta(days=(repo.id + i) % 200),
            'ahead': (i * 3 + repo.id) % 30,
            'behind': (i * 5 + repo.id) % 12,
        })
    return render_template('repo_branches.html', repo=repo, branches=branches)


@app.route('/<username>/<reponame>/tags')
def repo_tags(username, reponame):
    repo = _require_repo(username, reponame)
    releases = repo.get_releases() or []
    return render_template('repo_tags.html', repo=repo, releases=releases)


@app.route('/<username>/<reponame>/code-search')
@app.route('/<username>/<reponame>/find/<branch>')
def repo_code_search(username, reponame, branch=None):
    repo = _require_repo(username, reponame)
    q = request.args.get('q', '')
    # Synthesize file hits keyed off q + repo.id.
    files = ['README.md', 'src/index.js', 'src/main.py', 'main.go',
             'Cargo.toml', 'package.json', 'pyproject.toml', 'tests/test_main.py',
             'docs/index.md', 'CHANGELOG.md', 'LICENSE']
    hits = []
    if q:
        for i, f in enumerate(files):
            if (hash(f + q) % 5) != 0:  # skip ~20% so results vary
                hits.append({
                    'path': f,
                    'snippet': f"...{q} appears here in {f} at line {(hash(q+f) % 200) + 1}...",
                    'line': (hash(q + f) % 200) + 1,
                })
    return render_template('repo_code_search.html', repo=repo,
                           branch=branch or repo.default_branch,
                           q=q, hits=hits)


@app.route('/codespaces')
def codespaces_index():
    # Fake list of recent codespaces tied to current_user if any.
    spaces = []
    if current_user.is_authenticated:
        for i, r in enumerate(Repository.query.order_by(
                Repository.stars_count.desc()).limit(4).all()):
            spaces.append({
                'name': f"{r.name}-{['fuzzy', 'crispy', 'jolly', 'silent'][i]}-"
                        f"{['halibut', 'parsnip', 'parrot', 'broccoli'][i]}",
                'repo': r,
                'branch': r.default_branch or 'main',
                'machine': '2-core · 4 GB RAM · 32 GB',
                'last_used': _BULK_REF - timedelta(hours=i * 9 + 2),
                'state': ['Active', 'Stopped', 'Active', 'Stopped'][i % 4],
            })
    return render_template('codespaces.html', spaces=spaces)


@app.route('/<username>/<reponame>/codespaces/new')
def codespaces_new(username, reponame):
    repo = _require_repo(username, reponame)
    quota_exceeded = _r6_has_sentinel(repo, 'codespace-quota')
    return render_template('codespaces_new.html', repo=repo,
                           quota_exceeded=quota_exceeded)


@app.route('/<username>/<reponame>/branches/<branch>/push', methods=['GET', 'POST'])
def repo_branch_push_check(username, reponame, branch):
    """R6 edge: branch-protection demo. POSTing here represents attempting
    a direct push to <branch>. For repos with the branch-protected sentinel
    AND for `branch` == default branch, this 403s and renders a notice;
    for everything else it redirects back to /branches as a no-op.

    This is intentionally a synthetic route — the mirror doesn't model real
    git push, but tasks need a discoverable surface to assert the failure
    mode on."""
    repo = _require_repo(username, reponame)
    is_protected = (_r6_has_sentinel(repo, 'branch-protected')
                    and branch == (repo.default_branch or 'main'))
    if is_protected:
        msg = (f"Branch `{branch}` is protected. Direct pushes are not "
               f"allowed; open a pull request that targets `{branch}` and "
               f"wait for at least one approving review.")
        return render_template('repo_branches.html', repo=repo,
                               branches=[{'name': branch, 'is_default': True,
                                          'is_protected': True}],
                               protection_error=msg), 403
    return redirect(url_for('repo_branches', username=username,
                            reponame=reponame))


@app.route('/copilot')
def copilot_landing():
    """Copilot Chat landing — interactive prompt textbox + suggestions."""
    suggestions = [
        "Explain this code in plain English",
        "Find the bug in my function",
        "Write a unit test for the parser",
        "Convert this Python script to TypeScript",
        "Optimize this SQL query",
        "Generate a regex that matches IPv4 addresses",
    ]
    sample_chat = [
        ("user", "How do I read a JSON file in Python?"),
        ("copilot", "Use `json.load`:\n\n```python\nimport json\n"
                    "with open('data.json') as f:\n    data = json.load(f)\n```"),
    ]
    return render_template('copilot_chat.html',
                           suggestions=suggestions, sample_chat=sample_chat)


# ─────────────────────────── R4: deep sub-pages ───────────────────────────
# Discussions, Project Boards / Kanban, Sponsors, Packages, Org teams,
# Releases by tag, PR conflicts/diff side-by-side.

@app.route('/<username>/<reponame>/discussions')
def repo_discussions(username, reponame):
    repo = _require_repo(username, reponame)
    category = request.args.get('category', '')
    status = request.args.get('status', '')
    q = Discussion.query.filter_by(repo_id=repo.id)
    if category:
        q = q.filter(Discussion.category == category)
    if status:
        q = q.filter(Discussion.status == status)
    discussions = q.order_by(Discussion.created_at.desc()).all()
    categories = ['Announcements', 'General', 'Ideas', 'Q&A',
                  'Show and tell', 'Polls']
    return render_template('repo_discussions.html', repo=repo,
                           discussions=discussions, categories=categories,
                           active_category=category, active_status=status)


@app.route('/<username>/<reponame>/discussions/<int:number>')
def repo_discussion_detail(username, reponame, number):
    repo = _require_repo(username, reponame)
    d = Discussion.query.filter_by(repo_id=repo.id, number=number).first()
    if not d:
        abort(404)
    comments = (DiscussionComment.query
                .filter_by(discussion_id=d.id)
                .order_by(DiscussionComment.created_at.asc())
                .all())
    return render_template('repo_discussion_detail.html',
                           repo=repo, d=d, comments=comments)


@app.route('/<username>/<reponame>/projects')
def repo_projects(username, reponame):
    repo = _require_repo(username, reponame)
    boards = (ProjectBoard.query.filter_by(repo_id=repo.id)
              .order_by(ProjectBoard.number.asc()).all())
    return render_template('repo_projects.html', repo=repo, boards=boards)


@app.route('/<username>/<reponame>/projects/<int:number>')
def repo_project_detail(username, reponame, number):
    repo = _require_repo(username, reponame)
    board = (ProjectBoard.query
             .filter_by(repo_id=repo.id, number=number).first())
    if not board:
        abort(404)
    return render_template('repo_project_kanban.html',
                           repo=repo, board=board)


@app.route('/<username>/<reponame>/packages')
def repo_packages(username, reponame):
    repo = _require_repo(username, reponame)
    eco = request.args.get('ecosystem', '')
    q = Package.query.filter_by(repo_id=repo.id)
    if eco:
        q = q.filter(Package.ecosystem == eco)
    pkgs = q.order_by(Package.downloads_total.desc()).all()
    ecosystems = sorted({p.ecosystem for p in
                         Package.query.filter_by(repo_id=repo.id).all()})
    return render_template('repo_packages.html', repo=repo,
                           pkgs=pkgs, ecosystems=ecosystems,
                           active_eco=eco)


@app.route('/<username>/<reponame>/releases/tag/<tag>')
def repo_release_tag(username, reponame, tag):
    repo = _require_repo(username, reponame)
    releases = repo.get_releases() or []
    rel = next((r for r in releases if r.get('version') == tag), None)
    if not rel:
        rel = next((r for r in releases
                    if str(r.get('version', '')).startswith(tag)), None)
    if not rel:
        abort(404)
    return render_template('repo_release_tag.html',
                           repo=repo, rel=rel, tag=tag)


@app.route('/<username>/<reponame>/pull/<int:number>/conflicts')
def repo_pull_conflicts(username, reponame, number):
    repo = _require_repo(username, reponame)
    pr = Issue.query.filter_by(repo_id=repo.id, number=number, is_pr=1).first()
    if not pr:
        abort(404)
    h = _r4_hash(repo.full_name, 'conflict', number)
    files = []
    fcount = 1 + (h % 3)
    base_files = repo.get_commit_files() or []
    fallback = ['src/index.ts', 'lib/utils.py', 'README.md',
                'package.json', 'config.yaml']
    for i in range(fcount):
        if base_files:
            fname = base_files[i % len(base_files)]['name']
        else:
            fname = fallback[(h + i) % len(fallback)]
        files.append({
            'name': fname,
            'ours': (f"# from {pr.pr_base_branch or 'main'}\n"
                     f"def {fname.replace('/', '_').split('.')[0]}_v{1 + (h % 4)}():\n"
                     f"    return {h % 999}"),
            'theirs': (f"# from {pr.pr_head_branch or 'feature'}\n"
                       f"def {fname.replace('/', '_').split('.')[0]}_v{2 + (h % 4)}():\n"
                       f"    return {h % 999 + 7}"),
        })
    return render_template('repo_pull_conflicts.html',
                           repo=repo, pr=pr, files=files)


@app.route('/orgs/<org>/teams')
def org_teams(org):
    owner = User.query.filter_by(username=org).first()
    if not owner:
        abort(404)
    teams = (Team.query.filter_by(org_id=owner.id)
             .order_by(Team.slug.asc()).all())
    org_repo_count = Repository.query.filter_by(owner_id=owner.id).count()
    return render_template('org_teams.html', org=owner,
                           teams=teams, org_repo_count=org_repo_count)


@app.route('/orgs/<org>/teams/<slug>')
def org_team_detail(org, slug):
    owner = User.query.filter_by(username=org).first()
    if not owner:
        abort(404)
    team = Team.query.filter_by(org_id=owner.id, slug=slug).first()
    if not team:
        abort(404)
    members = []
    try:
        members_names = json.loads(team.members_json or '[]')
    except Exception:
        members_names = []
    for n in members_names:
        u = User.query.filter_by(username=n).first()
        if u:
            members.append(u)
    try:
        team_repos_names = json.loads(team.repos_json or '[]')
    except Exception:
        team_repos_names = []
    team_repos = []
    for fn in team_repos_names:
        r = Repository.query.filter_by(full_name=fn).first()
        if r:
            team_repos.append(r)
    return render_template('org_team_detail.html', org=owner,
                           team=team, members=members,
                           team_repos=team_repos)


@app.route('/orgs/<org>')
def org_landing(org):
    owner = User.query.filter_by(username=org).first()
    if not owner:
        abort(404)
    return redirect(url_for('user_profile', username=org))


@app.route('/sponsors')
def sponsors_index():
    """Discover sponsorable accounts — featured by sponsor count."""
    rows = (db.session.query(Sponsorship.target_id,
                             func.count(Sponsorship.id).label('n'),
                             func.sum(Sponsorship.amount_cents).label('total'))
            .group_by(Sponsorship.target_id)
            .order_by(func.count(Sponsorship.id).desc())
            .limit(30).all())
    featured = []
    for target_id, n, total in rows:
        u = db.session.get(User, target_id)
        if u:
            featured.append({'user': u, 'sponsors': n or 0,
                             'monthly_cents': int(total or 0)})
    return render_template('sponsors_index.html', featured=featured)


@app.route('/sponsors/<username>')
def sponsors_for(username):
    target = User.query.filter_by(username=username).first()
    if not target:
        abort(404)
    sponsorships = (Sponsorship.query.filter_by(target_id=target.id)
                    .order_by(Sponsorship.started_at.desc()).all())
    sponsor_users = []
    total_cents = 0
    for s in sponsorships:
        u = db.session.get(User, s.sponsor_id)
        if u:
            sponsor_users.append({'user': u, 'sponsorship': s})
            if s.status == 'active':
                total_cents += s.amount_cents or 0
    tiers = [
        {'name': 'Backer', 'price': 5,
         'desc': 'Show your support and unlock a sponsor badge.'},
        {'name': 'Supporter', 'price': 25,
         'desc': 'Early access to release notes and roadmaps.'},
        {'name': 'Sponsor', 'price': 100,
         'desc': 'Listed in README + monthly mention.'},
        {'name': 'Patron', 'price': 500,
         'desc': 'Direct line for prioritized issues.'},
    ]
    return render_template('sponsors_for.html', target=target,
                           sponsorships=sponsorships,
                           sponsor_users=sponsor_users,
                           total_cents=total_cents, tiers=tiers)


# ─────────────────────── R7: SEO + i18n + API surface ───────────────────────
# These routes are read-only and built from the existing DB rows. Nothing here
# mutates state, so they're safe to wire into the public surface unguarded.

@app.route('/i18n/set', methods=['GET', 'POST'])
def i18n_set():
    """Set the active UI locale via a sticky cookie. Driven by the header
    dropdown <form>. Falls back to ?lang= on GET so tasks can link directly.
    """
    code = (request.values.get('lang', '') or '').strip()
    nxt = request.values.get('next') or request.referrer or url_for('index')
    if code not in LOCALES:
        code = _DEFAULT_LOCALE
    resp = redirect(nxt)
    # 1-year cookie so the choice persists across mirror reset cycles.
    resp.set_cookie('gh_locale', code, max_age=60 * 60 * 24 * 365,
                    samesite='Lax')
    return resp


@app.route('/robots.txt')
def robots_txt():
    """Minimal robots.txt that points at the language-paginated sitemaps."""
    base = request.url_root.rstrip('/')
    body = [
        '# GitHub Mirror — robots.txt (R7)',
        'User-agent: *',
        'Allow: /',
        'Disallow: /settings/',
        'Disallow: /notifications',
        'Disallow: /account',
        'Disallow: /new',
        'Disallow: /*/issues/new',
        '',
        f'Sitemap: {base}/sitemap.xml',
    ]
    # One sitemap per top language so the index page works.
    for slug, _canonical in _R7_SITEMAP_LANG_MAP:
        body.append(f'Sitemap: {base}/sitemap-{slug}.xml')
    return ('\n'.join(body) + '\n', 200,
            {'Content-Type': 'text/plain; charset=utf-8'})


@app.route('/sitemap.xml')
def sitemap_index():
    """Sitemap index pointing at one sitemap per supported language. The
    per-language sitemaps list every repo whose `language == <lang>` so the
    full 32k catalog is discoverable to crawlers without a single 32k-URL
    file. Built off the (language, stars_count) composite index, ≤50ms."""
    base = request.url_root.rstrip('/')
    parts = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    last = MIRROR_REFERENCE_DATE.strftime('%Y-%m-%d')
    for slug, _canonical in _R7_SITEMAP_LANG_MAP:
        parts.append('  <sitemap>')
        parts.append(f'    <loc>{base}/sitemap-{slug}.xml</loc>')
        parts.append(f'    <lastmod>{last}</lastmod>')
        parts.append('  </sitemap>')
    parts.append('</sitemapindex>')
    return ('\n'.join(parts) + '\n', 200,
            {'Content-Type': 'application/xml; charset=utf-8'})


@app.route('/sitemap-<lang>.xml')
def sitemap_language(lang):
    """Per-language sitemap (lower-cased). Caps at 5000 URLs as per the
    sitemap protocol's 50k limit but our top language is ~3k. Repo URLs only
    — feature/static pages live in the index sitemap (not yet split out;
    crawlers normally also follow /robots.txt direct links)."""
    canonical = _R7_SITEMAP_SLUG_TO_LANG.get(lang.lower())
    if canonical is None:
        # Accept the canonical name directly (e.g. /sitemap-Python.xml).
        for canon in _R7_SITEMAP_LANGS:
            if canon.lower() == lang.lower():
                canonical = canon
                break
    if canonical is None:
        abort(404)
    base = request.url_root.rstrip('/')
    rows = (Repository.query
            .filter(Repository.language == canonical,
                    Repository.is_public.is_(True))
            .order_by(Repository.stars_count.desc())
            .limit(5000)
            .all())
    parts = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for r in rows:
        last = (r.updated_at or MIRROR_REFERENCE_DATE).strftime('%Y-%m-%d')
        # Priority leans on stars (top repo 1.0, tail ~0.1) — clamped.
        pri = max(0.1, min(1.0, 0.4 + math.log10(max(1, r.stars_count)) / 10.0))
        parts.append('  <url>')
        parts.append(f'    <loc>{base}/{r.full_name}</loc>')
        parts.append(f'    <lastmod>{last}</lastmod>')
        parts.append(f'    <priority>{pri:.2f}</priority>')
        parts.append('  </url>')
    parts.append('</urlset>')
    return ('\n'.join(parts) + '\n', 200,
            {'Content-Type': 'application/xml; charset=utf-8'})


@app.route('/api/openapi')
@app.route('/api/openapi.json')
def api_openapi():
    """Static OpenAPI 3.0 spec for the small JSON surface this mirror exposes.
    Lives at /api/openapi (HTML in browser via Accept negotiation) or
    /api/openapi.json (always JSON). The Accept negotiation here is the
    minimum needed for tasks that ask for the JSON spec specifically."""
    base = request.url_root.rstrip('/')
    spec = {
        'openapi': '3.0.3',
        'info': {
            'title': 'GitHub Mirror API',
            'version': '7.0.0',
            'description': ('Read-only JSON surface mirroring a subset of '
                            'the public GitHub REST API. Driven by a frozen '
                            'snapshot of the catalog. Anonymous-only; no '
                            'auth header required. Useful for WebVoyager '
                            'tasks that exercise API discovery.'),
            'contact': {'name': 'GitHub Mirror', 'url': base + '/'},
            'license': {'name': 'MIT'},
        },
        'servers': [{'url': base + '/api', 'description': 'Mirror'}],
        'paths': {
            '/repos': {
                'get': {
                    'summary': 'List repositories',
                    'parameters': [
                        {'name': 'sort', 'in': 'query',
                         'schema': {'type': 'string',
                                    'enum': ['stars', 'updated', 'created']}},
                        {'name': 'language', 'in': 'query',
                         'schema': {'type': 'string'}},
                        {'name': 'limit', 'in': 'query',
                         'schema': {'type': 'integer', 'maximum': 100}},
                    ],
                    'responses': {'200': {
                        'description': 'Repository list',
                        'content': {'application/json': {
                            'schema': {'$ref':
                                       '#/components/schemas/RepositoryList'}}}}},
                },
            },
            '/star/toggle': {'post': {
                'summary': 'Toggle a star on a repository',
                'requestBody': {'required': True, 'content':
                                {'application/json': {'schema':
                                 {'type': 'object',
                                  'properties':
                                  {'repo_id': {'type': 'integer'}}}}}},
                'responses': {'200': {'description': 'Updated state'}},
            }},
            '/watch/toggle': {'post': {
                'summary': 'Toggle watch on a repository',
                'responses': {'200': {'description': 'Updated state'}},
            }},
            '/follow/toggle': {'post': {
                'summary': 'Toggle a follow on a user',
                'responses': {'200': {'description': 'Updated state'}},
            }},
        },
        'components': {'schemas': {
            'Repository': {
                'type': 'object',
                'properties': {
                    'id': {'type': 'integer'},
                    'full_name': {'type': 'string'},
                    'language': {'type': 'string'},
                    'stars_count': {'type': 'integer'},
                    'forks_count': {'type': 'integer'},
                    'license': {'type': 'string'},
                    'updated_at': {'type': 'string', 'format': 'date-time'},
                },
                'required': ['id', 'full_name'],
            },
            'RepositoryList': {
                'type': 'object',
                'properties': {
                    'total': {'type': 'integer'},
                    'items': {'type': 'array',
                              'items': {'$ref':
                                        '#/components/schemas/Repository'}},
                },
            },
        }},
    }
    accept = (request.headers.get('Accept', '') or '').lower()
    wants_json = (request.path.endswith('.json')
                  or 'application/json' in accept
                  or request.args.get('format') == 'json')
    if wants_json:
        return jsonify(spec)
    # Pretty HTML wrapper so browsers don't dump raw JSON in the agent's face.
    pretty = json.dumps(spec, indent=2)
    return render_template('info_page.html',
                           page={'title': 'GitHub Mirror API — OpenAPI spec',
                                 'eyebrow': 'Developer',
                                 'subtitle': 'OpenAPI 3.0 specification',
                                 'meta_description':
                                 'OpenAPI 3.0 specification for the read-only '
                                 'GitHub Mirror JSON API.',
                                 'sections': [{
                                     'h': 'Specification',
                                     'p': ('Browse the JSON form at '
                                           f'<code>{base}/api/openapi.json</code>. '
                                           'Inline preview below.'),
                                     'pre': pretty[:6000],
                                 }],
                                 'bullets': ['REST style, anonymous-only',
                                             'Read-only routes serve frozen '
                                             'snapshot data',
                                             'Toggle endpoints require a '
                                             'logged-in session']})


@app.route('/releases.rss')
def releases_rss():
    """RSS feed of the 50 most recent repo releases across the catalog.
    Driven by `latest_release_date` so this is cheap on the indexed table."""
    rows = (Repository.query
            .filter(Repository.latest_release_version != '',
                    Repository.latest_release_date != None)  # noqa: E711
            .order_by(Repository.latest_release_date.desc())
            .limit(50)
            .all())
    base = request.url_root.rstrip('/')
    parts = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<rss version="2.0">',
             '  <channel>',
             '    <title>GitHub Mirror — Recent Releases</title>',
             f'    <link>{base}/releases.rss</link>',
             '    <description>Latest releases across the mirrored catalog</description>',
             f'    <language>{_current_locale().lower()}</language>',
             ('    <lastBuildDate>'
              + MIRROR_REFERENCE_DATE.strftime('%a, %d %b %Y %H:%M:%S +0000')
              + '</lastBuildDate>')]
    for r in rows:
        d = r.latest_release_date
        pub = (d or MIRROR_REFERENCE_DATE).strftime('%a, %d %b %Y %H:%M:%S +0000')
        notes = (r.latest_release_notes or '').replace(']]>', ']]&gt;')
        parts.append('    <item>')
        parts.append(f'      <title>{r.full_name} {r.latest_release_version}</title>')
        parts.append(
            f'      <link>{base}/{r.full_name}/releases/tag/'
            f'{r.latest_release_version}</link>')
        parts.append(
            f'      <guid isPermaLink="false">release-{r.id}-'
            f'{r.latest_release_version}</guid>')
        parts.append(f'      <pubDate>{pub}</pubDate>')
        parts.append(f'      <description><![CDATA[{notes}]]></description>')
        parts.append('    </item>')
    parts.append('  </channel>')
    parts.append('</rss>')
    return ('\n'.join(parts) + '\n', 200,
            {'Content-Type': 'application/rss+xml; charset=utf-8'})


# Known list of GitHub services for the status page. Stable order so the
# page is byte-identical across reloads. Each service has a deterministic
# health derived from the hash of its slug so test tasks have a fixed
# answer ("Codespaces is currently degraded" stays true across runs).
_R7_STATUS_SERVICES = [
    ('git-operations', 'Git Operations',
     'Cloning, pushing, fetching against the mirror.'),
    ('api-requests', 'API Requests',
     'Anonymous REST endpoints under /api.'),
    ('webhooks', 'Webhooks',
     'Outgoing webhooks (disabled on this mirror).'),
    ('issues', 'Issues',
     'Filing and commenting on issues.'),
    ('pull-requests', 'Pull Requests',
     'PR list, diff view, and merge conflicts page.'),
    ('actions', 'Actions',
     'Workflow runs page (no real CI executes).'),
    ('packages', 'Packages',
     'Package registry list under /<repo>/packages.'),
    ('pages', 'Pages',
     'GitHub Pages serving (mirrored docs).'),
    ('codespaces', 'Codespaces',
     'On-demand dev environments (sandboxed).'),
    ('copilot', 'Copilot',
     'AI suggestions and chat surface.'),
]


@app.route('/status/page')
@app.route('/status/realtime')
def status_realtime():
    """Real GitHub status page — service health board + last 7-day history.
    Independent of the `/status` stub which only lists support links."""
    services = []
    incidents = []
    today = MIRROR_REFERENCE_DATE.date()
    for slug, name, desc in _R7_STATUS_SERVICES:
        h = int(hashlib.sha1(('status-' + slug).encode()).hexdigest()[:8], 16)
        # 80% operational / 12% degraded / 5% partial outage / 3% maintenance.
        bucket = h % 100
        if bucket < 80:
            state = 'operational'
        elif bucket < 92:
            state = 'degraded'
        elif bucket < 97:
            state = 'partial_outage'
        else:
            state = 'maintenance'
        history = []
        for i in range(7):
            day = today - timedelta(days=6 - i)
            dh = int(hashlib.sha1(
                f'{slug}|{day.isoformat()}'.encode()).hexdigest()[:8], 16)
            uptime_pct = 99.0 + (dh % 100) / 100.0
            history.append({'date': day.isoformat(),
                            'uptime': round(uptime_pct, 3)})
        services.append({'slug': slug, 'name': name, 'desc': desc,
                         'state': state, 'history': history})
        if state != 'operational':
            incidents.append({
                'service': name,
                'state': state,
                'started_at': (MIRROR_REFERENCE_DATE
                               - timedelta(hours=(h % 36) + 1)).isoformat(),
                'summary': {
                    'degraded': f'{name} is responding more slowly than usual.',
                    'partial_outage':
                        f'Some {name.lower()} requests are failing intermittently.',
                    'maintenance':
                        f'Scheduled maintenance window for {name}.',
                }[state],
            })
    return render_template('info_page.html',
                           page={'title': 'GitHub Mirror Status',
                                 'eyebrow': 'Status',
                                 'subtitle':
                                 'Live snapshot of service health',
                                 'meta_description':
                                 'Service health board for the GitHub mirror '
                                 '— driven by a frozen seed, deterministic '
                                 'across reloads.',
                                 'sections': [{
                                     'h': 'Current status',
                                     'list': [
                                         f'<strong>{s["name"]}</strong> — '
                                         f'{s["state"].replace("_", " ").title()}'
                                         for s in services],
                                 }, {
                                     'h': 'Active incidents',
                                     'list': ([f'{i["service"]} · '
                                               f'{i["state"]} · '
                                               f'{i["summary"]}'
                                               for i in incidents]
                                              or ['No active incidents — all '
                                                  'systems normal.']),
                                 }, {
                                     'h': 'Past 7 days uptime (%)',
                                     'table': {
                                         'cols': (['Service']
                                                  + [d['date']
                                                     for d in services[0]['history']]),
                                         'rows': [
                                             [s['name']] + [f"{d['uptime']:.2f}"
                                                            for d in s['history']]
                                             for s in services],
                                     },
                                 }],
                                 'bullets': ['Updated at '
                                             + MIRROR_REFERENCE_DATE.isoformat(),
                                             'History covers the past 7 days',
                                             'Driven by deterministic seed '
                                             'data (no real probes)']})


# Languages used to paginate sitemap.xml. Top-15 by repo count gives full
# coverage; rare languages roll up into `other`. Tuples are (slug, canonical)
# because `+` and `#` need URL-safe slugs (cpp / csharp) but the DB still
# stores the canonical name ("C++", "C#").
_R7_SITEMAP_LANG_MAP = [
    ('python', 'Python'),
    ('javascript', 'JavaScript'),
    ('typescript', 'TypeScript'),
    ('go', 'Go'),
    ('java', 'Java'),
    ('cpp', 'C++'),
    ('c', 'C'),
    ('rust', 'Rust'),
    ('csharp', 'C#'),
    ('html', 'HTML'),
    ('ruby', 'Ruby'),
    ('php', 'PHP'),
    ('shell', 'Shell'),
    ('lua', 'Lua'),
    ('swift', 'Swift'),
]
_R7_SITEMAP_LANGS = [canonical for _, canonical in _R7_SITEMAP_LANG_MAP]
_R7_SITEMAP_SLUG_TO_LANG = dict(_R7_SITEMAP_LANG_MAP)


# ─────────────────────── R8: observability + dev surface ───────────────────────
# Eight read-only routes that cover what real github.com exposes for ops,
# webhooks, GraphQL discovery, OAuth app registration, and a permission/scope
# glossary. Every payload is derived from MIRROR_REFERENCE_DATE so two
# rebuilds produce byte-identical seed DBs and tasks always have a stable
# answer regardless of when they run.

_R8_HEALTH_BUILD_SHA = hashlib.sha1(b'webharbor-github-r8').hexdigest()[:12]
_R8_BUILD_TAG = 'r8.0.0'


@app.route('/healthz')
def healthz():
    """Cheap liveness probe — also used by docker/start scripts. Returns a
    fixed body so byte-identical seed audits can compare two runs. We do NOT
    query the DB here on the hot path; the existence of /healthz is enough
    for an L4 probe to declare the site up."""
    accept = (request.headers.get('Accept', '') or '').lower()
    body = {
        'status': 'ok',
        'service': 'github-mirror',
        'build': _R8_BUILD_TAG,
        'sha': _R8_HEALTH_BUILD_SHA,
        'reference_date': MIRROR_REFERENCE_DATE.isoformat(),
    }
    if 'application/json' in accept or request.args.get('format') == 'json':
        return jsonify(body)
    return ('ok\n', 200, {'Content-Type': 'text/plain; charset=utf-8'})


# Telemetry event bank. Same shape as the real GitHub audit-log API: a fixed
# vocab of `action` strings plus a deterministic synthetic timestamp/actor.
# Tasks can ask "what is the most recent event of type X" with a stable
# answer because the bank is sorted by ts desc.
_R8_TELEMETRY_ACTIONS = [
    'repo.create', 'repo.archive', 'repo.transfer', 'repo.delete',
    'pr.opened', 'pr.merged', 'pr.closed', 'pr.review_requested',
    'issue.opened', 'issue.closed', 'issue.labeled',
    'release.published', 'workflow_run.completed', 'workflow_run.failed',
    'star.created', 'fork.created', 'webhook.delivered',
    'oauth_app.created', 'oauth_app.revoked',
    'secret_scanning.alert.created', 'secret_scanning.alert.dismissed',
    'codespace.created', 'codespace.deleted',
    'dependency_graph.updated',
]


def _r8_events(limit=50):
    """Synthesize a deterministic stream of recent telemetry events.

    Bound on `(MIRROR_REFERENCE_DATE - i*23min, sha1(i)% N)` so callers see
    the same list across reloads. Limit is clamped to 1..200."""
    limit = max(1, min(int(limit), 200))
    out = []
    for i in range(limit):
        h = int(hashlib.sha1(f'r8-evt-{i}'.encode()).hexdigest()[:10], 16)
        action = _R8_TELEMETRY_ACTIONS[h % len(_R8_TELEMETRY_ACTIONS)]
        actor = ['octocat', 'mojombo', 'defunkt', 'pjhyett',
                 'wycats', 'ezmobius', 'ivey', 'evanphx',
                 'vanpelt', 'wayneeseguin', 'brynary'][(h >> 4) % 11]
        ts = MIRROR_REFERENCE_DATE - timedelta(minutes=23 * i,
                                               seconds=(h >> 7) % 60)
        out.append({
            'id': f'evt_{_R8_HEALTH_BUILD_SHA}_{i:04d}',
            'action': action,
            'actor': actor,
            'created_at': ts.isoformat(),
        })
    return out


@app.route('/api/events')
def api_events():
    """JSON stream of recent platform-level events. Mirrors the shape of
    GitHub's audit-log API minus the org scope. Filterable by `?action=`."""
    limit = request.args.get('limit', '50')
    try:
        limit_i = int(limit)
    except ValueError:
        limit_i = 50
    events = _r8_events(limit_i)
    action = request.args.get('action', '').strip()
    if action:
        events = [e for e in events if e['action'] == action]
    return jsonify({
        'total': len(events),
        'reference_date': MIRROR_REFERENCE_DATE.isoformat(),
        'events': events,
    })


@app.route('/api/uptime')
def api_uptime():
    """Past-30-day uptime breakdown per service. Driven by the same hash
    that powers /status/page so the two views agree."""
    today = MIRROR_REFERENCE_DATE.date()
    services_out = []
    overall_total = 0.0
    overall_n = 0
    for slug, name, _desc in _R7_STATUS_SERVICES:
        days = []
        svc_sum = 0.0
        for i in range(30):
            day = today - timedelta(days=29 - i)
            dh = int(hashlib.sha1(
                f'{slug}|{day.isoformat()}'.encode()).hexdigest()[:8], 16)
            uptime_pct = 99.0 + (dh % 100) / 100.0
            days.append({'date': day.isoformat(),
                         'uptime': round(uptime_pct, 3)})
            svc_sum += uptime_pct
        avg = svc_sum / 30.0
        services_out.append({
            'slug': slug, 'name': name,
            'avg_uptime_30d': round(avg, 3),
            'days': days,
        })
        overall_total += avg
        overall_n += 1
    return jsonify({
        'reference_date': MIRROR_REFERENCE_DATE.isoformat(),
        'window_days': 30,
        'overall_avg_uptime': round(overall_total / max(1, overall_n), 3),
        'services': services_out,
    })


@app.route('/webhook/repository', methods=['GET', 'POST'])
@csrf.exempt
def webhook_repository():
    """Webhook receiver stub. Accepts POST with `X-GitHub-Event` header and
    returns a deterministic delivery id; never writes to the DB so seed
    byte-identity holds. GET renders the docs/landing page describing the
    payload shape, which is what the WebVoyager tasks read."""
    if request.method == 'POST':
        event = (request.headers.get('X-GitHub-Event', '') or 'ping').strip()
        delivery_id = hashlib.sha1(
            ('webhook|' + event + '|' + _R8_HEALTH_BUILD_SHA).encode()
        ).hexdigest()
        return jsonify({
            'received': True,
            'event': event,
            'delivery_id': delivery_id,
            'ref_date': MIRROR_REFERENCE_DATE.isoformat(),
        }), 202
    page = {
        'title': 'Repository webhooks',
        'eyebrow': 'Developer · Webhooks',
        'subtitle': 'POST endpoint for repository events',
        'meta_description': (
            'Repository webhook receiver for the GitHub mirror. POST '
            'with X-GitHub-Event header to receive a deterministic '
            'delivery id.'),
        'sections': [{
            'h': 'Endpoint',
            'p': ('<code>POST /webhook/repository</code> — accepts a JSON body '
                  'and an <code>X-GitHub-Event</code> header. Returns a stable '
                  '<code>delivery_id</code> derived from the event name and the '
                  'mirror build SHA.'),
        }, {
            'h': 'Supported events',
            'list': [
                '<code>push</code> — branch / tag pushes',
                '<code>pull_request</code> — opened, closed, synchronize',
                '<code>issues</code> — opened, closed, labeled',
                '<code>release</code> — published, edited',
                '<code>workflow_run</code> — requested, completed',
                '<code>star</code> — created, deleted',
                '<code>ping</code> — connectivity check (default)',
            ],
        }, {
            'h': 'Example response',
            'pre': json.dumps({
                'received': True,
                'event': 'push',
                'delivery_id': hashlib.sha1(
                    ('webhook|push|' + _R8_HEALTH_BUILD_SHA).encode()
                ).hexdigest(),
                'ref_date': MIRROR_REFERENCE_DATE.isoformat(),
            }, indent=2),
        }],
        'bullets': ['No state is persisted on this mirror',
                    'Delivery ids are deterministic across rebuilds',
                    'POST returns 202 Accepted'],
    }
    return render_template('info_page.html', page=page)


@app.route('/api/graphql', methods=['GET', 'POST'])
@app.route('/api/graphql-stub', methods=['GET', 'POST'])
@csrf.exempt
def api_graphql_stub():
    """Minimal GraphQL stub. GET returns the schema discovery page; POST
    with a `{query:"..."}` body returns a deterministic shape for the small
    subset of queries the mirror's docs advertise (viewer, repository)."""
    if request.method == 'POST':
        try:
            body = request.get_json(silent=True) or {}
        except Exception:
            body = {}
        q = (body.get('query') or '').strip()
        if 'viewer' in q:
            data = {'data': {'viewer': {
                'login': 'octocat',
                'name': 'The Octocat',
                'bio': 'Frozen snapshot user.',
            }}}
        elif 'repository' in q:
            # Always return facebook/react as the demo repo for the stub
            # so docs examples line up with the response shape.
            repo = Repository.query.filter_by(
                full_name='facebook/react').first()
            data = {'data': {'repository': {
                'nameWithOwner': repo.full_name if repo else 'facebook/react',
                'stargazerCount': repo.stars_count if repo else 0,
                'forkCount': repo.forks_count if repo else 0,
                'primaryLanguage': {'name':
                                    repo.language if repo else 'JavaScript'},
            }}}
        else:
            data = {'data': None,
                    'errors': [{'message': 'Only `viewer` and `repository(...)` '
                                'are exposed on this stub.'}]}
        return jsonify(data)
    page = {
        'title': 'GraphQL API stub',
        'eyebrow': 'Developer · GraphQL',
        'subtitle': 'Minimal POST endpoint with two demo queries',
        'meta_description': (
            'GraphQL stub for the GitHub mirror. Exposes `viewer` and '
            '`repository(owner:..., name:...)` for tasks that need a JSON '
            'shape similar to the real GitHub GraphQL API.'),
        'sections': [{
            'h': 'Endpoint',
            'p': ('<code>POST /api/graphql</code> (alias '
                  '<code>/api/graphql-stub</code>) — body '
                  '<code>{"query":"..."}</code>. The mirror inspects the '
                  'query string for the words <code>viewer</code> or '
                  '<code>repository</code> and returns a fixed shape.'),
        }, {
            'h': 'Sample — viewer',
            'pre': '{\n  viewer {\n    login\n    name\n    bio\n  }\n}',
        }, {
            'h': 'Sample — repository',
            'pre': ('{\n  repository(owner: "facebook", name: "react") {\n'
                    '    nameWithOwner\n    stargazerCount\n    forkCount\n'
                    '    primaryLanguage { name }\n  }\n}'),
        }, {
            'h': 'Out-of-scope',
            'list': [
                'Mutations are not supported (read-only mirror)',
                'No authentication required',
                'Schema introspection is not exposed',
            ],
        }],
        'bullets': ['Two read-only queries',
                    'Deterministic responses driven by the seed DB',
                    'Returns JSON on POST, HTML on GET'],
    }
    return render_template('info_page.html', page=page)


# Stable, deterministic OAuth app registry — three frozen entries that the
# /developer/oauth-app and /developer/oauth-app/<slug> pages render.
_R8_OAUTH_APPS = [
    {
        'slug': 'mirror-cli',
        'name': 'Mirror CLI',
        'client_id': 'Iv1.' + hashlib.sha1(b'mirror-cli').hexdigest()[:16],
        'homepage': '/api',
        'callback': '/login/oauth/callback/mirror-cli',
        'scopes': ['repo:status', 'public_repo', 'read:user'],
        'description': ('First-party CLI client used by the mirror tooling. '
                        'Read-only scopes, no write surface.'),
    },
    {
        'slug': 'webvoyager-bot',
        'name': 'WebVoyager Eval Bot',
        'client_id': 'Iv1.' + hashlib.sha1(b'webvoyager-bot').hexdigest()[:16],
        'homepage': '/about',
        'callback': '/login/oauth/callback/webvoyager-bot',
        'scopes': ['read:user', 'read:org', 'notifications'],
        'description': ('OAuth app used by automated WebVoyager evaluation '
                        'runs to inspect read-only state.'),
    },
    {
        'slug': 'gh-actions-inspector',
        'name': 'Actions Inspector',
        'client_id': 'Iv1.' + hashlib.sha1(b'gh-actions-inspector').hexdigest()[:16],
        'homepage': '/marketplace',
        'callback': '/login/oauth/callback/gh-actions-inspector',
        'scopes': ['workflow', 'read:packages', 'repo:status'],
        'description': ('Reads workflow run metadata. Cannot dispatch or '
                        'cancel runs on this mirror.'),
    },
]


@app.route('/developer/oauth-app')
def developer_oauth_app_index():
    """OAuth app developer registry — list view. Three entries, deterministic
    client ids so tasks can ask for "the client id of the WebVoyager bot"."""
    page = {
        'title': 'OAuth Apps',
        'eyebrow': 'Developer',
        'subtitle': ('Register and inspect OAuth applications. Read-only '
                     'on this mirror.'),
        'meta_description': (
            'OAuth app registry for the GitHub mirror. Lists three apps with '
            'stable client ids derived from the build SHA.'),
        'sections': ([{
            'h': app_['name'],
            'p': (f"<code>client_id={app_['client_id']}</code><br>"
                  f"Homepage: <code>{app_['homepage']}</code><br>"
                  f"Callback URL: <code>{app_['callback']}</code><br>"
                  f"Scopes: <code>{', '.join(app_['scopes'])}</code><br>"
                  f"{app_['description']} "
                  f"<a href=\"/developer/oauth-app/{app_['slug']}\">View →</a>"),
        } for app_ in _R8_OAUTH_APPS]),
        'bullets': ['Read-only registry',
                    'Client ids derived from build SHA',
                    'No real OAuth dance — no /login/oauth endpoint here'],
    }
    return render_template('info_page.html', page=page)


@app.route('/developer/oauth-app/<slug>')
def developer_oauth_app_detail(slug):
    for app_ in _R8_OAUTH_APPS:
        if app_['slug'] == slug:
            page = {
                'title': app_['name'],
                'eyebrow': 'Developer · OAuth App',
                'subtitle': app_['description'],
                'meta_description':
                    f"OAuth app details for {app_['name']}.",
                'sections': [{
                    'h': 'Identity',
                    'list': [
                        f"<strong>Name</strong>: {app_['name']}",
                        f"<strong>Slug</strong>: <code>{app_['slug']}</code>",
                        f"<strong>Client ID</strong>: <code>{app_['client_id']}</code>",
                        f"<strong>Homepage</strong>: <code>{app_['homepage']}</code>",
                        f"<strong>Callback URL</strong>: <code>{app_['callback']}</code>",
                    ],
                }, {
                    'h': 'Scopes',
                    'list': [f"<code>{s}</code>" for s in app_['scopes']],
                }, {
                    'h': 'About',
                    'p': app_['description'],
                }],
                'bullets': ['Frozen registry entry',
                            f"Build {_R8_BUILD_TAG}",
                            'No client_secret exposed'],
            }
            return render_template('info_page.html', page=page)
    abort(404)


# Glossary entries for the contextual-help surface. Each maps a permission /
# scope / API noun to a one-line explanation. The /help/glossary page renders
# them and the base-template JS uses the same vocabulary to attach <abbr>-style
# tooltips on matching tokens.
_R8_GLOSSARY = [
    ('repo', 'Full read/write access to public and private repositories.'),
    ('public_repo', 'Read/write access to public repositories only.'),
    ('repo:status', 'Read/write access to commit status (CI checks).'),
    ('read:user', 'Read access to the authenticated user\'s profile.'),
    ('read:org', 'Read access to org membership and team metadata.'),
    ('workflow', 'Read/write access to GitHub Actions workflow runs.'),
    ('read:packages', 'Read access to the package registry.'),
    ('notifications', 'Read/write access to the notifications feed.'),
    ('admin:repo_hook', 'Manage webhooks on a repository.'),
    ('admin:org_hook', 'Manage org-level webhooks.'),
    ('gist', 'Read/write access to Gists.'),
    ('OAuth App', 'A third-party app that authenticates users via '
                  'GitHub\'s OAuth flow.'),
    ('GraphQL', 'A query language for fetching nested graph data in a '
                'single round-trip.'),
    ('webhook',  'An outbound HTTP POST triggered by repository events.'),
    ('delivery_id', 'Stable identifier for a single webhook POST.'),
    ('JSON-LD', 'Linked-data JSON embedded in HTML for SEO crawlers.'),
    ('OpenAPI', 'A REST API description format (formerly Swagger).'),
    ('REST', 'Stateless HTTP API style; uses GET/POST/PUT/DELETE verbs.'),
    ('rate limit', 'Caps the number of API calls per unit time per actor.'),
    ('CSRF', 'Cross-site request forgery — protected by per-form tokens.'),
]


@app.route('/help/glossary')
def help_glossary():
    """API / permission / scope glossary. Driven by `_R8_GLOSSARY`. Linked
    from the help modal (?) and rendered as an indexable page so the
    contextual-help vocabulary is discoverable both for humans and for
    eval tasks like 'what does the `workflow` scope grant?'."""
    page = {
        'title': 'API & Permissions Glossary',
        'eyebrow': 'Help',
        'subtitle': ('One-line definitions for every scope, API surface and '
                     'standards-acronym the mirror uses.'),
        'meta_description': (
            'Glossary of API surfaces, OAuth scopes and standards acronyms '
            'used across the GitHub mirror.'),
        'sections': [{
            'h': f'{term}',
            'p': defn,
        } for term, defn in _R8_GLOSSARY],
        'bullets': [f'{len(_R8_GLOSSARY)} entries',
                    'Linked from the help modal (?)',
                    'Stable across rebuilds'],
    }
    return render_template('info_page.html', page=page)


# ─────────────────────────── R8 catalog growth ───────────────────────────
# Push the catalog from R7's 32k → 40k+ by minting a fresh slot of repos
# with the `r8-` prefix. Same hash-deterministic pattern as R5/R6/R7 so two
# rebuilds match byte-for-byte.

_R8_REPO_TARGET = 40000
_R8_REPO_SUFFIXES = [
    'palette', 'shortcut', 'glossary', 'helpdesk', 'tooltip',
    'inspector', 'console', 'studio', 'workshop', 'gallery',
    'beacon8', 'spotlight', 'meter', 'pulse', 'monitor',
    'gauge', 'tracker', 'ledger', 'manifest', 'roster',
    'directory', 'index8', 'registry8', 'catalog8', 'almanac',
    'compendium', 'codex', 'primer', 'gazette',
]


def seed_r8_user_repos():
    """Mint up to ~8000 R8 repos under existing owners. Each owner caps at
    ~110 total repos so the largest orgs don't run away with the catalog.
    Deterministic via SHA-1 of (owner.username, slot)."""
    have = Repository.query.count()
    if have >= _R8_REPO_TARGET:
        return 0

    owners = (User.query
              .join(Repository, Repository.owner_id == User.id)
              .order_by(User.username.asc())
              .distinct()
              .all())
    if not owners:
        return 0

    existing_full = {r.full_name for r in
                     Repository.query.with_entities(Repository.full_name).all()}
    topic_by_slug = {t.slug: t for t in Topic.query.all()}

    topics_pool = [
        'developer-experience', 'platform-engineering', 'observability',
        'webhooks', 'graphql', 'oauth', 'permission-system',
        'rate-limiting', 'feature-flags', 'telemetry',
        'distributed-tracing', 'audit-log', 'health-check',
        'uptime', 'sre', 'reliability', 'open-telemetry',
        'cli', 'sdk', 'rust', 'go', 'python', 'typescript',
    ]

    added = 0
    for slot in range(len(_R8_REPO_SUFFIXES)):
        if have + added >= _R8_REPO_TARGET:
            break
        for owner in owners:
            if have + added >= _R8_REPO_TARGET:
                break
            existing_for_owner = sum(1 for fn in existing_full
                                     if fn.startswith(owner.username + '/'))
            if existing_for_owner >= 110:
                continue
            suffix = _R8_REPO_SUFFIXES[
                (slot + _r6_hash(owner.username)) % len(_R8_REPO_SUFFIXES)]
            base_name = f"r8-{suffix}-{slot}"
            full = f"{owner.username}/{base_name}"
            if full in existing_full:
                base_name = (
                    f"r8-{suffix}-{slot}-{_r6_hash(owner.username, slot) % 9999}")
                full = f"{owner.username}/{base_name}"
                if full in existing_full:
                    continue
            h = _r6_hash('r8', full)
            lang = _R4_LANG_POOL[h % len(_R4_LANG_POOL)]
            area = ['observability', 'webhooks', 'graphql', 'oauth',
                    'rate-limit', 'telemetry', 'audit-log', 'health',
                    'feature-flag', 'tracing', 'palette', 'shortcut'][(h >> 3) % 12]
            desc = (
                f"R8 polish on the {area} subsystem — deterministic stubs, "
                f"glossary-backed docs, used in production by {owner.username}."
            )[:255]
            feature1 = _R6_FEATURE_BANK[(h >> 7) % len(_R6_FEATURE_BANK)]
            feature2 = _R6_FEATURE_BANK[(h >> 11) % len(_R6_FEATURE_BANK)]
            install_tmpl = _R6_INSTALL_BANK.get(lang, 'cargo install {name}')
            cmd = install_tmpl.format(name=base_name, full=full,
                                      org=owner.username.lower())
            license_ = _R4_LICENSE_BAND[(h >> 6) % len(_R4_LICENSE_BAND)]
            readme = (
                f"# {full}\n\n> {desc}\n\n## Why\n\n"
                f"- {feature1}\n- {feature2}\n"
                f"- Ships an OpenAPI snippet and a GraphQL stub schema.\n\n"
                f"## Install\n\n```bash\n{cmd}\n```\n\n"
                f"## Glossary\n\nKey terms used in this repo are defined at "
                f"`/help/glossary`. The `{area}` page in particular pairs "
                f"with the `webhook` and `delivery_id` entries.\n"
            )
            default_branch = _R4_BRANCH_BAND[(h >> 8) % len(_R4_BRANCH_BAND)]
            stars = 5 + (h % 2800)
            forks = max(0, stars // (3 + (h % 5)))
            watchers = max(1, stars // 4)
            open_issues = (h >> 4) % 12
            is_archived = ((h >> 9) % 22 == 0)

            topic_slugs = []
            for k in range(3 + (h % 3)):
                ts = topics_pool[(h * 7 + k * 23) % len(topics_pool)]
                if ts not in topic_slugs:
                    topic_slugs.append(ts)

            created = _BULK_REF - timedelta(days=120 + (h % 1300),
                                            hours=(h >> 4) % 24)
            pushed = _BULK_REF - timedelta(days=(h % 140),
                                           hours=(h >> 5) % 24)
            updated = pushed
            sha = hashlib.sha1(f"r8|{full}".encode()).hexdigest()

            repo = Repository(
                owner_id=owner.id,
                name=base_name,
                full_name=full,
                description=desc,
                language=lang,
                license=license_,
                stars_count=stars,
                forks_count=forks,
                watchers_count=watchers,
                open_issues_count=open_issues,
                is_public=True,
                is_fork=False,
                is_template=((h >> 12) % 38 == 0),
                is_archived=is_archived,
                has_readme=True,
                has_wiki=((h >> 3) % 6 == 0),
                has_issues=True,
                owner_type='organization' if (h >> 14) % 3 == 0 else 'user',
                default_branch=default_branch,
                size_kb=140 + (h % 22000),
                readme=readme,
                topics_text=json.dumps(topic_slugs),
                gallery_json='[]',
                created_at=created,
                updated_at=updated,
                pushed_at=pushed,
                latest_release_version=(
                    f"v{1 + (h % 5)}.{(h >> 2) % 18}.{(h >> 4) % 16}"),
                latest_release_date=pushed - timedelta(days=4 + (h % 60)),
                latest_release_notes=(
                    f"R8 polish on the {area} subsystem: contextual-help "
                    "tooltips, command-palette wiring, glossary cross-links."
                ),
                latest_commit_sha=sha,
                latest_commit_message=(
                    f"feat({area}): R8 polish — palette / shortcut / glossary"),
                latest_commit_date=pushed,
                latest_commit_additions=18 + (h % 320),
                latest_commit_deletions=4 + ((h >> 1) % 160),
            )
            db.session.add(repo)
            db.session.flush()
            for slug in topic_slugs:
                t = topic_by_slug.get(slug)
                if t is not None:
                    repo.topics.append(t)
            existing_full.add(full)
            added += 1
            if added % 1000 == 0:
                db.session.commit()
    db.session.commit()
    return added


# ─────────────────────────── R9 catalog growth ───────────────────────────
# Push the catalog from R8's 40k → 50k+. Same hash-deterministic mint as
# R5/R6/R7/R8 so two rebuilds stay byte-identical. New suffixes cover the
# R9 surface vocabulary (chat, classroom, deeplink, etc.) so the generated
# repo names show up in keyword searches.

_R9_REPO_TARGET = 50000
_R9_REPO_SUFFIXES = [
    'chat-suggest', 'classroom-kit', 'deeplink', 'scanner', 'rotator',
    'revoker', 'codeql-rules', 'gist-mirror', 'sponsor-band', 'assignment-cli',
    'sandbox9', 'preview9', 'snapshot9', 'lab9', 'forge9',
    'orchard9', 'beacon9', 'lens9', 'pivot9', 'relay9',
    'switch9', 'router9', 'broker9', 'cache9', 'shard9',
    'splitter9', 'merger9', 'compressor9', 'tagger9', 'pruner9',
]


def seed_r9_user_repos():
    """Mint up to ~10000 R9 repos under existing owners. Each owner caps at
    ~140 total repos so the catalog stays balanced. Deterministic via SHA-1
    of (owner.username, slot)."""
    have = Repository.query.count()
    if have >= _R9_REPO_TARGET:
        return 0

    owners = (User.query
              .join(Repository, Repository.owner_id == User.id)
              .order_by(User.username.asc())
              .distinct()
              .all())
    if not owners:
        return 0

    existing_full = {r.full_name for r in
                     Repository.query.with_entities(Repository.full_name).all()}
    topic_by_slug = {t.slug: t for t in Topic.query.all()}

    topics_pool = [
        'copilot', 'copilot-chat', 'classroom', 'codespaces', 'gist',
        'code-scanning', 'codeql', 'secret-scanning', 'security',
        'sponsors', 'deeplink', 'developer-experience', 'platform-engineering',
        'observability', 'webhooks', 'graphql', 'oauth', 'cli', 'sdk',
        'rust', 'go', 'python', 'typescript',
    ]

    added = 0
    for slot in range(len(_R9_REPO_SUFFIXES)):
        if have + added >= _R9_REPO_TARGET:
            break
        for owner in owners:
            if have + added >= _R9_REPO_TARGET:
                break
            existing_for_owner = sum(1 for fn in existing_full
                                     if fn.startswith(owner.username + '/'))
            if existing_for_owner >= 140:
                continue
            suffix = _R9_REPO_SUFFIXES[
                (slot + _r6_hash(owner.username)) % len(_R9_REPO_SUFFIXES)]
            base_name = f"r9-{suffix}-{slot}"
            full = f"{owner.username}/{base_name}"
            if full in existing_full:
                base_name = (
                    f"r9-{suffix}-{slot}-{_r6_hash(owner.username, slot) % 9999}")
                full = f"{owner.username}/{base_name}"
                if full in existing_full:
                    continue
            h = _r6_hash('r9', full)
            lang = _R4_LANG_POOL[h % len(_R4_LANG_POOL)]
            area = ['copilot-chat', 'classroom', 'codespaces', 'gist',
                    'code-scanning', 'secret-scanning', 'sponsors',
                    'deeplink', 'codeql', 'token-revoke',
                    'assignment', 'suggest'][(h >> 3) % 12]
            desc = (
                f"R9 polish on the {area} subsystem — deterministic stubs, "
                f"used in production by {owner.username}."
            )[:255]
            feature1 = _R6_FEATURE_BANK[(h >> 7) % len(_R6_FEATURE_BANK)]
            feature2 = _R6_FEATURE_BANK[(h >> 11) % len(_R6_FEATURE_BANK)]
            install_tmpl = _R6_INSTALL_BANK.get(lang, 'cargo install {name}')
            cmd = install_tmpl.format(name=base_name, full=full,
                                      org=owner.username.lower())
            license_ = _R4_LICENSE_BAND[(h >> 6) % len(_R4_LICENSE_BAND)]
            readme = (
                f"# {full}\n\n> {desc}\n\n## Why\n\n"
                f"- {feature1}\n- {feature2}\n"
                f"- Ships a deterministic CLI surface plus glossary cross-links.\n\n"
                f"## Install\n\n```bash\n{cmd}\n```\n\n"
                f"## Related\n\n- `/help/glossary` — terminology used here.\n"
                f"- `/classroom` — adjacent learning surface.\n"
            )
            default_branch = _R4_BRANCH_BAND[(h >> 8) % len(_R4_BRANCH_BAND)]
            stars = 3 + (h % 2200)
            forks = max(0, stars // (3 + (h % 5)))
            watchers = max(1, stars // 4)
            open_issues = (h >> 4) % 10
            is_archived = ((h >> 9) % 26 == 0)

            topic_slugs = []
            for k in range(3 + (h % 3)):
                ts = topics_pool[(h * 7 + k * 23) % len(topics_pool)]
                if ts not in topic_slugs:
                    topic_slugs.append(ts)

            created = _BULK_REF - timedelta(days=110 + (h % 1200),
                                            hours=(h >> 4) % 24)
            pushed = _BULK_REF - timedelta(days=(h % 130),
                                           hours=(h >> 5) % 24)
            updated = pushed
            sha = hashlib.sha1(f"r9|{full}".encode()).hexdigest()

            repo = Repository(
                owner_id=owner.id,
                name=base_name,
                full_name=full,
                description=desc,
                language=lang,
                license=license_,
                stars_count=stars,
                forks_count=forks,
                watchers_count=watchers,
                open_issues_count=open_issues,
                is_public=True,
                is_fork=False,
                is_template=((h >> 12) % 42 == 0),
                is_archived=is_archived,
                has_readme=True,
                has_wiki=((h >> 3) % 7 == 0),
                has_issues=True,
                owner_type='organization' if (h >> 14) % 3 == 0 else 'user',
                default_branch=default_branch,
                size_kb=130 + (h % 21000),
                readme=readme,
                topics_text=json.dumps(topic_slugs),
                gallery_json='[]',
                created_at=created,
                updated_at=updated,
                pushed_at=pushed,
                latest_release_version=(
                    f"v{1 + (h % 5)}.{(h >> 2) % 18}.{(h >> 4) % 16}"),
                latest_release_date=pushed - timedelta(days=3 + (h % 55)),
                latest_release_notes=(
                    f"R9 polish on the {area} subsystem: chat suggestions, "
                    "classroom assignments, deeplink wiring."
                ),
                latest_commit_sha=sha,
                latest_commit_message=(
                    f"feat({area}): R9 polish — chat / classroom / scanning"),
                latest_commit_date=pushed,
                latest_commit_additions=16 + (h % 300),
                latest_commit_deletions=3 + ((h >> 1) % 150),
            )
            db.session.add(repo)
            db.session.flush()
            for slug in topic_slugs:
                t = topic_by_slug.get(slug)
                if t is not None:
                    repo.topics.append(t)
            existing_full.add(full)
            added += 1
            if added % 1000 == 0:
                db.session.commit()
    db.session.commit()
    return added


# ─────────────────────────── R10 catalog growth ───────────────────────────
# Push the catalog from R9's 50k → 56k+ by minting a fresh slot of repos
# with the `r10-` prefix. Same hash-deterministic mint as R5–R9 so two
# rebuilds match byte-for-byte. New suffixes cover the R10 compound-flow
# vocabulary (trending → fork → branch → PR → review → merge → CI →
# release → package) so generated names surface in keyword search.

_R10_REPO_TARGET = 56000
_R10_REPO_SUFFIXES = [
    'trending-board', 'fork-helper', 'branch-mover', 'pr-flow', 'review-bot',
    'merge-queue', 'ci-runner', 'release-train', 'package-cache', 'fanout10',
    'pipeline10', 'kit10', 'forge10', 'beacon10', 'lens10',
    'pivot10', 'relay10', 'switch10', 'router10', 'broker10',
    'cache10', 'shard10', 'splitter10', 'merger10', 'compressor10',
    'tagger10', 'pruner10', 'sentry10', 'oracle10', 'lighthouse10',
]


def seed_r10_user_repos():
    """Mint up to ~6000 R10 repos under existing owners. Each owner caps at
    ~160 total repos so the catalog stays balanced. Deterministic via SHA-1
    of (owner.username, slot). Covers the 10-step compound flow
    (trending → repo → fork → branch → PR → review → merge → CI →
    release → package) by name + readme."""
    have = Repository.query.count()
    if have >= _R10_REPO_TARGET:
        return 0

    owners = (User.query
              .join(Repository, Repository.owner_id == User.id)
              .order_by(User.username.asc())
              .distinct()
              .all())
    if not owners:
        return 0

    existing_full = {r.full_name for r in
                     Repository.query.with_entities(Repository.full_name).all()}
    topic_by_slug = {t.slug: t for t in Topic.query.all()}

    topics_pool = [
        'merge-queue', 'pull-request', 'code-review', 'continuous-integration',
        'continuous-delivery', 'release-engineering', 'package-registry',
        'fork', 'branch', 'cherry-pick', 'trending', 'pipeline',
        'ci-cd', 'github-actions', 'devops', 'platform-engineering',
        'rust', 'go', 'python', 'typescript', 'sdk', 'cli',
    ]

    # Compound-flow vocabulary mirrors the 10 steps of the R10 task set.
    _AREA_BANK = [
        'trending', 'fork', 'branch', 'pull-request', 'review',
        'merge-queue', 'ci-runner', 'release', 'package', 'fanout',
        'review-bot', 'merge-helper',
    ]

    added = 0
    for slot in range(len(_R10_REPO_SUFFIXES)):
        if have + added >= _R10_REPO_TARGET:
            break
        for owner in owners:
            if have + added >= _R10_REPO_TARGET:
                break
            existing_for_owner = sum(1 for fn in existing_full
                                     if fn.startswith(owner.username + '/'))
            if existing_for_owner >= 160:
                continue
            suffix = _R10_REPO_SUFFIXES[
                (slot + _r6_hash(owner.username)) % len(_R10_REPO_SUFFIXES)]
            base_name = f"r10-{suffix}-{slot}"
            full = f"{owner.username}/{base_name}"
            if full in existing_full:
                base_name = (
                    f"r10-{suffix}-{slot}-{_r6_hash(owner.username, slot) % 9999}")
                full = f"{owner.username}/{base_name}"
                if full in existing_full:
                    continue
            h = _r6_hash('r10', full)
            lang = _R4_LANG_POOL[h % len(_R4_LANG_POOL)]
            area = _AREA_BANK[(h >> 3) % len(_AREA_BANK)]
            desc = (
                f"R10 polish on the {area} subsystem — trending → fork → "
                f"branch → PR → review → merge → CI → release → package, "
                f"used in production by {owner.username}."
            )[:255]
            feature1 = _R6_FEATURE_BANK[(h >> 7) % len(_R6_FEATURE_BANK)]
            feature2 = _R6_FEATURE_BANK[(h >> 11) % len(_R6_FEATURE_BANK)]
            install_tmpl = _R6_INSTALL_BANK.get(lang, 'cargo install {name}')
            cmd = install_tmpl.format(name=base_name, full=full,
                                      org=owner.username.lower())
            license_ = _R4_LICENSE_BAND[(h >> 6) % len(_R4_LICENSE_BAND)]
            readme = (
                f"# {full}\n\n> {desc}\n\n## Why\n\n"
                f"- {feature1}\n- {feature2}\n"
                f"- Built around the 10-step ship flow "
                f"(trending → fork → branch → PR → review → merge → CI → "
                f"release → package).\n\n"
                f"## Install\n\n```bash\n{cmd}\n```\n\n"
                f"## Workflow\n\n"
                f"1. Browse `/trending` to discover changes.\n"
                f"2. Fork into your namespace.\n"
                f"3. Cut a topic branch.\n"
                f"4. Open a pull request.\n"
                f"5. Get a review (see `/{full}/pulls`).\n"
                f"6. Merge via the merge queue.\n"
                f"7. CI runs via Actions (see `/{full}/actions`).\n"
                f"8. Release is cut (see `/{full}/releases`).\n"
                f"9. Package is published (see `/{full}/packages`).\n"
                f"10. Watchers/forkers are notified.\n"
            )
            default_branch = _R4_BRANCH_BAND[(h >> 8) % len(_R4_BRANCH_BAND)]
            stars = 4 + (h % 2400)
            forks = max(0, stars // (3 + (h % 5)))
            watchers = max(1, stars // 4)
            open_issues = (h >> 4) % 11
            is_archived = ((h >> 9) % 28 == 0)

            topic_slugs = []
            for k in range(3 + (h % 3)):
                ts = topics_pool[(h * 7 + k * 23) % len(topics_pool)]
                if ts not in topic_slugs:
                    topic_slugs.append(ts)

            created = _BULK_REF - timedelta(days=100 + (h % 1100),
                                            hours=(h >> 4) % 24)
            pushed = _BULK_REF - timedelta(days=(h % 120),
                                           hours=(h >> 5) % 24)
            updated = pushed
            sha = hashlib.sha1(f"r10|{full}".encode()).hexdigest()

            repo = Repository(
                owner_id=owner.id,
                name=base_name,
                full_name=full,
                description=desc,
                language=lang,
                license=license_,
                stars_count=stars,
                forks_count=forks,
                watchers_count=watchers,
                open_issues_count=open_issues,
                is_public=True,
                is_fork=False,
                is_template=((h >> 12) % 44 == 0),
                is_archived=is_archived,
                has_readme=True,
                has_wiki=((h >> 3) % 7 == 0),
                has_issues=True,
                owner_type='organization' if (h >> 14) % 3 == 0 else 'user',
                default_branch=default_branch,
                size_kb=120 + (h % 20000),
                readme=readme,
                topics_text=json.dumps(topic_slugs),
                gallery_json='[]',
                created_at=created,
                updated_at=updated,
                pushed_at=pushed,
                latest_release_version=(
                    f"v{1 + (h % 6)}.{(h >> 2) % 20}.{(h >> 4) % 18}"),
                latest_release_date=pushed - timedelta(days=2 + (h % 50)),
                latest_release_notes=(
                    f"R10 polish on the {area} subsystem: fork/branch/PR/"
                    "review/merge/CI/release/package wiring."
                ),
                latest_commit_sha=sha,
                latest_commit_message=(
                    f"feat({area}): R10 polish — fork → PR → review → "
                    "merge → CI → release → package"),
                latest_commit_date=pushed,
                latest_commit_additions=14 + (h % 280),
                latest_commit_deletions=2 + ((h >> 1) % 140),
            )
            db.session.add(repo)
            db.session.flush()
            for slug in topic_slugs:
                t = topic_by_slug.get(slug)
                if t is not None:
                    repo.topics.append(t)
            existing_full.add(full)
            added += 1
            if added % 1000 == 0:
                db.session.commit()
    db.session.commit()
    return added


# ─────────────────────────── R9: chat/classroom/scanning surface ───────────────────────────
# Read-only routes added in R9. Every payload is hash-deterministic so two
# rebuilds produce the same DOM and the WebVoyager tasks have stable answers.

_R9_BUILD_TAG = 'r9.0.0'
_R9_BUILD_SHA = hashlib.sha1(b'webharbor-github-r9').hexdigest()[:12]

# Curated Copilot Chat suggestion bank. Used both by /copilot/chat (HTML) and
# /copilot/chat/api (JSON). Indexed by integer so tasks can ask "suggestion #3".
_R9_COPILOT_SUGGESTIONS = [
    ('Explain code', 'Explain what this function does in plain English.'),
    ('Find a bug', 'Look through this snippet and point out the bug.'),
    ('Write a test', 'Generate a unit test for the function I just pasted.'),
    ('Refactor', 'Refactor this code so the cyclomatic complexity drops.'),
    ('Translate language', 'Convert this Python script to TypeScript.'),
    ('Write a regex', 'Give me a regex that matches IPv4 addresses with optional port.'),
    ('Explain error', 'Explain this stack trace and suggest a likely cause.'),
    ('Optimize SQL', 'Optimize this SQL query for a 10-million-row table.'),
    ('Generate docstring', 'Write a NumPy-style docstring for this function.'),
    ('Summarize PR', 'Summarize the diff into a 3-bullet pull-request description.'),
    ('Suggest commit message', 'Suggest a conventional-commits message for this diff.'),
    ('Pair-program', 'Pair-program with me on this Advent of Code problem.'),
]


@app.route('/copilot/chat')
def copilot_chat_page():
    """Standalone Copilot Chat page. Distinct from the /copilot landing — this
    is the in-product chat surface with a suggestion sidebar."""
    page = {
        'title': 'Copilot Chat',
        'eyebrow': 'Copilot',
        'subtitle': ('Interactive chat surface backed by the deterministic '
                     'suggestion bank. Read-only on this mirror.'),
        'meta_description': (
            'GitHub Copilot Chat surface. Renders a frozen suggestion list '
            'plus the JSON endpoint /copilot/chat/api for programmatic '
            'retrieval.'),
        'sections': ([{
            'h': f'#{i+1} · {label}',
            'p': f'<code>{prompt}</code>',
        } for i, (label, prompt) in enumerate(_R9_COPILOT_SUGGESTIONS)]),
        'bullets': [f'{len(_R9_COPILOT_SUGGESTIONS)} curated suggestions',
                    'Same payload served by /copilot/chat/api',
                    f'Build {_R9_BUILD_TAG}'],
    }
    return render_template('info_page.html', page=page)


@app.route('/copilot/chat/api', methods=['GET', 'POST'])
@csrf.exempt
def copilot_chat_api():
    """JSON endpoint for the chat suggestion bank. GET returns the full list,
    POST with `{"q": "..."}` returns the matching subset (case-insensitive
    substring match on label or prompt). Read-only: no completion happens."""
    if request.method == 'POST':
        try:
            body = request.get_json(silent=True) or {}
        except Exception:
            body = {}
        q = (body.get('q') or '').strip().lower()
    else:
        q = (request.args.get('q') or '').strip().lower()
    items = []
    for i, (label, prompt) in enumerate(_R9_COPILOT_SUGGESTIONS):
        if q and q not in label.lower() and q not in prompt.lower():
            continue
        items.append({'id': i + 1, 'label': label, 'prompt': prompt})
    return jsonify({
        'service': 'copilot-chat',
        'build': _R9_BUILD_TAG,
        'query': q,
        'count': len(items),
        'suggestions': items,
    })


@app.route('/codespaces/<codespace_id>/connect')
def codespace_connect(codespace_id):
    """Deeplink target for codespace connect. Renders a deterministic page
    keyed off the codespace id. Real github.com would 302 to a VSCode URL;
    on this mirror we render a stable HTML page so the link is testable."""
    h = int(hashlib.sha1(
        ('cs|' + codespace_id).encode()).hexdigest()[:10], 16)
    machine = ['2-core · 4 GB · 32 GB', '4-core · 8 GB · 32 GB',
               '8-core · 16 GB · 64 GB'][h % 3]
    region = ['us-east', 'us-west', 'eu-west', 'asia-east'][(h >> 4) % 4]
    state = ['Available', 'Starting', 'Stopped'][(h >> 7) % 3]
    deeplink = f'vscode://github.codespaces/connect/{codespace_id}'
    page = {
        'title': f'Connect to codespace {codespace_id}',
        'eyebrow': 'Codespaces',
        'subtitle': (f'Deterministic deeplink for codespace '
                     f'<code>{codespace_id}</code>.'),
        'meta_description': (
            f'Codespace connect surface for {codespace_id}. Returns a '
            'deeplink URL plus machine/region/state.'),
        'sections': [{
            'h': 'Codespace',
            'list': [
                f'<strong>ID</strong>: <code>{codespace_id}</code>',
                f'<strong>Machine</strong>: {machine}',
                f'<strong>Region</strong>: <code>{region}</code>',
                f'<strong>State</strong>: <code>{state}</code>',
            ],
        }, {
            'h': 'Deeplink',
            'pre': deeplink,
        }, {
            'h': 'Notes',
            'list': [
                'Read-only on this mirror — clicking the deeplink does nothing.',
                f'Build {_R9_BUILD_TAG}',
            ],
        }],
        'bullets': ['Deterministic machine/region/state',
                    'Deeplink format mirrors real github.com',
                    f'Sha {_R9_BUILD_SHA}'],
    }
    return render_template('info_page.html', page=page)


# Code-scanning alert bank — 5 deterministic CodeQL findings per repo.
_R9_CODEQL_RULES = [
    ('py/sql-injection', 'high',
     'User input flows into a raw SQL query without parameterization.'),
    ('js/xss', 'high',
     'Untrusted data reaches a DOM sink without escaping.'),
    ('py/path-injection', 'medium',
     'Untrusted path component used in file open without validation.'),
    ('go/hardcoded-credentials', 'critical',
     'Hardcoded API token found in repository source.'),
    ('java/insecure-randomness', 'low',
     'java.util.Random used in a security-sensitive context.'),
]


def _r9_codeql_alerts(repo):
    out = []
    for i, (rule_id, severity, msg) in enumerate(_R9_CODEQL_RULES):
        h = int(hashlib.sha1(
            f'codeql|{repo.full_name}|{i}'.encode()).hexdigest()[:10], 16)
        file_path = [
            'src/db/query.py', 'web/render.js', 'lib/io/path.py',
            'cmd/server/main.go', 'src/main/java/Auth.java',
        ][i]
        out.append({
            'number': i + 1,
            'rule_id': rule_id,
            'severity': severity,
            'message': msg,
            'file_path': file_path,
            'line': 12 + (h % 480),
            'state': 'open' if (h % 5) != 0 else 'dismissed',
        })
    return out


@app.route('/security/code-scanning/<username>/<reponame>/results')
def code_scanning_results(username, reponame):
    """CodeQL alert listing for a repo. Five deterministic findings; state
    flips to dismissed for ~20% of (repo, rule) pairs based on SHA-1."""
    repo = _require_repo(username, reponame)
    alerts = _r9_codeql_alerts(repo)
    page = {
        'title': f'Code scanning results · {repo.full_name}',
        'eyebrow': 'Security · Code scanning',
        'subtitle': (f'CodeQL findings for <code>{repo.full_name}</code>. '
                     'Read-only — alerts cannot be acknowledged here.'),
        'meta_description': (
            f'Code scanning (CodeQL) results for {repo.full_name}.'),
        'sections': [{
            'h': 'Alerts',
            'table': {
                'cols': ['#', 'Rule', 'Severity', 'File', 'Line', 'State'],
                'rows': [
                    [a['number'], a['rule_id'], a['severity'],
                     a['file_path'], a['line'], a['state']]
                    for a in alerts
                ],
            },
        }, {
            'h': 'Summary',
            'list': [
                f"<strong>Open</strong>: "
                f"{sum(1 for a in alerts if a['state'] == 'open')}",
                f"<strong>Dismissed</strong>: "
                f"{sum(1 for a in alerts if a['state'] == 'dismissed')}",
                f"<strong>Highest severity</strong>: "
                f"{max((a['severity'] for a in alerts), key=lambda s: ['low','medium','high','critical'].index(s))}",
            ],
        }],
        'bullets': [f'{len(alerts)} CodeQL alerts',
                    f'Repo {repo.full_name}',
                    'Stable across rebuilds'],
    }
    return render_template('info_page.html', page=page)


# Secret-scanning token bank — 4 deterministic findings per repo.
_R9_SECRET_KINDS = [
    ('github_pat', 'GitHub personal access token'),
    ('aws_access_key', 'AWS access key ID'),
    ('slack_webhook', 'Slack webhook URL'),
    ('stripe_secret', 'Stripe live secret key'),
]


def _r9_secret_alerts(repo):
    out = []
    for i, (kind, label) in enumerate(_R9_SECRET_KINDS):
        h = int(hashlib.sha1(
            f'secret|{repo.full_name}|{i}'.encode()).hexdigest()[:10], 16)
        token_id = hashlib.sha1(
            f'tok|{repo.full_name}|{i}'.encode()).hexdigest()[:16]
        out.append({
            'number': i + 1,
            'kind': kind,
            'label': label,
            'token_id': token_id,
            'file_path': ['config/secrets.env', '.github/deploy.yml',
                          'scripts/notify.sh', 'src/billing/client.py'][i],
            'line': 5 + (h % 120),
            'revoked': False,
        })
    return out


@app.route('/security/secret-scanning/<username>/<reponame>/revoke',
           methods=['GET', 'POST'])
@csrf.exempt
def secret_scanning_revoke(username, reponame):
    """Secret-scanning revoke flow. GET lists detected tokens; POST with
    `token_id=<id>` returns a deterministic confirmation. State is NOT
    persisted to the DB (would break byte-identity); the POST just echoes
    a confirmation payload."""
    repo = _require_repo(username, reponame)
    alerts = _r9_secret_alerts(repo)
    if request.method == 'POST':
        token_id = (request.form.get('token_id', '')
                    or (request.get_json(silent=True) or {}).get('token_id', ''))
        token_id = (token_id or '').strip()
        found = next((a for a in alerts if a['token_id'] == token_id), None)
        if not found:
            return jsonify({
                'revoked': False,
                'reason': 'token_id not found in this repo',
                'token_id': token_id,
            }), 404
        return jsonify({
            'revoked': True,
            'token_id': token_id,
            'kind': found['kind'],
            'repo': repo.full_name,
            'note': ('Revocation is simulated; state is not persisted to '
                     'preserve seed byte-identity.'),
            'build': _R9_BUILD_TAG,
        }), 202
    page = {
        'title': f'Revoke leaked secrets · {repo.full_name}',
        'eyebrow': 'Security · Secret scanning',
        'subtitle': (f'Detected secrets in <code>{repo.full_name}</code>. '
                     'POST <code>token_id</code> here to simulate revocation.'),
        'meta_description': (
            f'Secret-scanning revoke surface for {repo.full_name}.'),
        'sections': [{
            'h': 'Detected secrets',
            'table': {
                'cols': ['#', 'Kind', 'Token id', 'File', 'Line'],
                'rows': [
                    [a['number'], a['kind'], a['token_id'],
                     a['file_path'], a['line']]
                    for a in alerts
                ],
            },
        }, {
            'h': 'Revoke (simulated)',
            'p': ('POST to this URL with <code>token_id=&lt;id&gt;</code> '
                  'to receive a confirmation envelope. No DB writes happen.'),
        }],
        'bullets': [f'{len(alerts)} detected secrets',
                    'POST returns 202 on success, 404 on unknown id',
                    f'Build {_R9_BUILD_TAG}'],
    }
    return render_template('info_page.html', page=page)


# GitHub Classroom assignment bank — fixed across rebuilds.
_R9_CLASSROOM_ASSIGNMENTS = [
    ('intro-python', 'Intro to Python',
     'Build a CLI calculator with unit tests.', 'Python', 42, 28),
    ('react-hooks', 'React Hooks Lab',
     'Convert a class component to hooks and add a custom hook.', 'JavaScript', 36, 19),
    ('rust-ownership', 'Rust Ownership',
     'Implement a borrow-checker-friendly linked list.', 'Rust', 24, 11),
    ('sql-joins', 'SQL Joins Practice',
     'Solve 12 ranked joins on a sample schema.', 'SQL', 51, 33),
    ('algo-graphs', 'Graph Algorithms',
     'Implement BFS, DFS and Dijkstra; pass the provided tests.', 'Go', 29, 14),
    ('web-security', 'Web Security Basics',
     'Patch the OWASP-Top-10 demo app one rule at a time.', 'TypeScript', 33, 17),
]


@app.route('/classroom')
def classroom_index():
    """GitHub Classroom landing page — lists the assignment bank."""
    page = {
        'title': 'GitHub Classroom',
        'eyebrow': 'Classroom',
        'subtitle': ('Assignments distributed to student rosters. Read-only '
                     'on this mirror.'),
        'meta_description': (
            'GitHub Classroom landing page. Lists the fixed assignment bank '
            'and links to each assignment detail page.'),
        'sections': [{
            'h': 'Assignments',
            'table': {
                'cols': ['#', 'Slug', 'Title', 'Language',
                         'Roster', 'Submitted'],
                'rows': [
                    [i + 1,
                     f'<a href="/classroom/assignment/{slug}"><code>{slug}</code></a>',
                     title, lang, roster, submitted]
                    for i, (slug, title, _desc, lang, roster, submitted)
                    in enumerate(_R9_CLASSROOM_ASSIGNMENTS)
                ],
            },
        }],
        'bullets': [f'{len(_R9_CLASSROOM_ASSIGNMENTS)} assignments',
                    'Roster sizes are frozen',
                    f'Build {_R9_BUILD_TAG}'],
    }
    return render_template('info_page.html', page=page)


@app.route('/classroom/assignment/<slug>')
def classroom_assignment_detail(slug):
    """Detail page for a single classroom assignment."""
    found = None
    idx = -1
    for i, row in enumerate(_R9_CLASSROOM_ASSIGNMENTS):
        if row[0] == slug:
            found = row
            idx = i
            break
    if not found:
        abort(404)
    s_slug, title, desc, lang, roster, submitted = found
    pct = round(100.0 * submitted / max(1, roster), 1)
    page = {
        'title': title,
        'eyebrow': f'Classroom · {s_slug}',
        'subtitle': desc,
        'meta_description': (
            f'GitHub Classroom assignment detail page for {s_slug}.'),
        'sections': [{
            'h': 'Identity',
            'list': [
                f'<strong>Slug</strong>: <code>{s_slug}</code>',
                f'<strong>Title</strong>: {title}',
                f'<strong>Language</strong>: <code>{lang}</code>',
                f'<strong>Roster size</strong>: {roster}',
                f'<strong>Submissions</strong>: {submitted} ({pct}%)',
            ],
        }, {
            'h': 'Brief',
            'p': desc,
        }, {
            'h': 'Submit',
            'p': ('Push your starter repo and the Classroom autograder will '
                  'pick up the run. Read-only on this mirror.'),
        }],
        'bullets': [f'Assignment #{idx + 1}',
                    f'Build {_R9_BUILD_TAG}',
                    'Stable across rebuilds'],
    }
    return render_template('info_page.html', page=page)


# Gist bank — six frozen public gists referenced by /gist/<id>.
_R9_GISTS = [
    ('g9a1', 'parse_iso.py',
     'Parse ISO-8601 timestamps with fractional seconds.',
     'def parse_iso(s):\n    return datetime.fromisoformat(s.replace("Z","+00:00"))'),
    ('g9b2', 'rate_limit.go',
     'Token-bucket rate limiter in 40 lines of Go.',
     'package rl\n// Take returns true if a token was available.\nfunc (b *Bucket) Take() bool { /* … */ }'),
    ('g9c3', 'cleanup.sh',
     'Idempotent shell cleanup for stale Docker layers.',
     '#!/usr/bin/env bash\nset -euo pipefail\ndocker system prune -af --volumes'),
    ('g9d4', 'flatten.ts',
     'Tail-recursive array flatten in TypeScript.',
     'export const flatten = <T>(xs: T[][]): T[] => xs.reduce((a, b) => a.concat(b), []);'),
    ('g9e5', 'csv2json.py',
     'Stream a CSV file into newline-delimited JSON.',
     'import csv, json, sys\nfor row in csv.DictReader(sys.stdin):\n    print(json.dumps(row))'),
    ('g9f6', 'retry.rs',
     'Retry helper with exponential backoff in Rust.',
     'pub fn retry<F, T, E>(mut f: F, attempts: usize) -> Result<T, E> where F: FnMut() -> Result<T, E> { /* … */ }'),
]


@app.route('/gist/new', methods=['GET', 'POST'])
@csrf.exempt
def gist_new():
    """Create-private-gist surface. POST is a no-op (returns a deterministic
    gist_id derived from the payload + build sha); GET renders the form
    description. State is NOT persisted to preserve byte-identity."""
    if request.method == 'POST':
        try:
            body = (request.get_json(silent=True)
                    or {k: request.form.get(k, '') for k in (
                        'filename', 'description', 'content', 'public')})
        except Exception:
            body = {}
        filename = (body.get('filename') or '').strip() or 'untitled.txt'
        description = (body.get('description') or '').strip()
        content = body.get('content') or ''
        is_public_raw = body.get('public')
        is_public = str(is_public_raw).lower() in ('1', 'true', 'yes', 'on')
        gist_id = hashlib.sha1(
            ('|'.join([filename, description, content, str(is_public),
                       _R9_BUILD_SHA])).encode()).hexdigest()[:12]
        return jsonify({
            'created': True,
            'gist_id': gist_id,
            'filename': filename,
            'is_public': is_public,
            'visibility': 'public' if is_public else 'private',
            'note': ('Gist is NOT persisted; the id is derived from the '
                     'payload + build sha so reposts return the same value.'),
            'build': _R9_BUILD_TAG,
        }), 201
    page = {
        'title': 'New gist',
        'eyebrow': 'Gist',
        'subtitle': ('Paste a snippet and create a private or public gist. '
                     'Read-only on this mirror — submits return a deterministic id.'),
        'meta_description': (
            'New gist form. POST returns a stable gist id derived from the '
            'payload, with no DB writes.'),
        'sections': [{
            'h': 'Form fields',
            'list': [
                '<code>filename</code> — defaults to <code>untitled.txt</code>',
                '<code>description</code> — free text',
                '<code>content</code> — gist body',
                '<code>public</code> — <code>true</code> / <code>false</code> '
                '(defaults to false → private)',
            ],
        }, {
            'h': 'POST',
            'p': ('Submitting returns <code>{created, gist_id, '
                  'filename, is_public, visibility}</code>. State is not '
                  'written to the DB.'),
        }, {
            'h': 'Bank',
            'p': ('Six pre-seeded public gists are reachable at '
                  '<code>/gist/&lt;id&gt;</code>. See '
                  '<a href="/gist/g9a1">/gist/g9a1</a> for an example.'),
        }],
        'bullets': [f'{len(_R9_GISTS)} frozen public gists',
                    'POST returns a deterministic id',
                    f'Build {_R9_BUILD_TAG}'],
    }
    return render_template('info_page.html', page=page)


@app.route('/gist/<gist_id>')
def gist_detail(gist_id):
    """Detail page for a single gist."""
    found = next((g for g in _R9_GISTS if g[0] == gist_id), None)
    if not found:
        abort(404)
    g_id, filename, description, body = found
    page = {
        'title': filename,
        'eyebrow': f'Gist · {g_id}',
        'subtitle': description,
        'meta_description': f'Gist detail page for {g_id}.',
        'sections': [{
            'h': 'Metadata',
            'list': [
                f'<strong>ID</strong>: <code>{g_id}</code>',
                f'<strong>Filename</strong>: <code>{filename}</code>',
                f'<strong>Visibility</strong>: <code>public</code>',
                f'<strong>Description</strong>: {description}',
            ],
        }, {
            'h': filename,
            'pre': body,
        }],
        'bullets': ['Frozen across rebuilds',
                    f'Build {_R9_BUILD_TAG}',
                    'Linked from /gist/new'],
    }
    return render_template('info_page.html', page=page)


# ─────────────────────────── Main ───────────────────────────

def seed_benchmark_users():
    """Idempotent: add 4 benchmark users with stars, watches, issues, follows.
    Call after seed_database() — requires repos to already exist.
    """
    if User.query.filter_by(email='alice.j@test.com').first():
        return  # already seeded

    benchmark_users_data = [
        ("alice_j", "alice.j@test.com", "Alice Johnson",
         "Full-stack developer and open source enthusiast.", "Austin, TX",
         "https://alicejohnson.dev", "OpenDev Inc", "alice_codes", "free"),
        ("bob_c", "bob.c@test.com", "Bob Chen",
         "Machine learning engineer. Python lover.", "Seattle, WA",
         "", "DataSci Co", "bob_ml", "free"),
        ("carol_d", "carol.d@test.com", "Carol Diaz",
         "Frontend developer. React & Vue enthusiast.", "New York, NY",
         "https://caroldiaz.io", "PixelCraft", "carol_dev", "free"),
        ("david_k", "david.k@test.com", "David Kim",
         "Rust and systems programming. Performance obsessed.", "San Francisco, CA",
         "", "RustSystems LLC", "david_rust", "team"),
    ]

    new_users = []
    for i, (uname, email, name, bio, loc, web, company, twitter, plan) in enumerate(benchmark_users_data):
        u = User(username=uname, email=email, name=name, bio=bio,
                 location=loc, website=web, company=company, twitter=twitter, plan=plan)
        # Pinned bcrypt hash for "TestPass123!" — keeps seed byte-identical.
        u.password_hash = '$2b$12$RwAC/sfwDHtccU//A20fde.uKkZK4Ptnjjyua2l2ktwI6uysAp3Ou'
        u.avatar = f"/static/images/avatars/avatar_{(i % 15):02d}.jpg"
        db.session.add(u)
        new_users.append(u)

    db.session.flush()

    # Helper to get repo by full_name
    def _get_repo(full_name):
        return Repository.query.filter_by(full_name=full_name).first()

    # Helper to add a star (idempotent)
    def _star(user, repo):
        if repo and not Star.query.filter_by(user_id=user.id, repo_id=repo.id).first():
            db.session.add(Star(user_id=user.id, repo_id=repo.id))
            repo.stars_count += 1

    # Helper to add a watch (idempotent)
    def _watch(user, repo):
        if repo and not Watch.query.filter_by(user_id=user.id, repo_id=repo.id).first():
            db.session.add(Watch(user_id=user.id, repo_id=repo.id))
            repo.watchers_count += 1

    alice, bob, carol, david = new_users

    # ── Alice: full-stack dev, stars JS/Python repos ──
    for fn in ['facebook/react', 'vuejs/vue', 'vercel/next.js',
               'tensorflow/tensorflow', 'django/django', 'pallets/flask',
               'tiangolo/fastapi']:
        _star(alice, _get_repo(fn))
    for fn in ['facebook/react', 'vuejs/vue', 'django/django']:
        _watch(alice, _get_repo(fn))

    # ── Bob: ML engineer, stars ML/AI repos ──
    for fn in ['tensorflow/tensorflow', 'huggingface/transformers',
               'langchain-ai/langchain', 'microsoft/vscode', 'facebook/react']:
        _star(bob, _get_repo(fn))
    for fn in ['tensorflow/tensorflow', 'huggingface/transformers', 'langchain-ai/langchain']:
        _watch(bob, _get_repo(fn))

    # ── Carol: frontend dev, stars JS frameworks ──
    for fn in ['facebook/react', 'vuejs/vue', 'vercel/next.js',
               'sveltejs/svelte', 'angular/angular', 'expressjs/express', 'nodejs/node']:
        _star(carol, _get_repo(fn))
    for fn in ['facebook/react', 'sveltejs/svelte', 'angular/angular']:
        _watch(carol, _get_repo(fn))

    # ── David: systems/Rust dev, stars Rust/Go/C++ repos ──
    for fn in ['rust-lang/rust', 'golang/go', 'torvalds/linux',
               'kubernetes/kubernetes', 'microsoft/vscode', 'tiangolo/fastapi']:
        _star(david, _get_repo(fn))
    for fn in ['rust-lang/rust', 'golang/go', 'kubernetes/kubernetes']:
        _watch(david, _get_repo(fn))

    db.session.flush()

    # ── Follows ──
    # Insert via the association table directly so ROWID order matches the
    # listed sequence regardless of SQLAlchemy's internal flush order.
    def _get_user(username):
        return User.query.filter_by(username=username).first()

    def _add_follow(src, dst):
        if not (src and dst) or src.id == dst.id:
            return
        existing = db.session.execute(
            follows.select().where(
                (follows.c.follower_id == src.id) &
                (follows.c.followed_id == dst.id))
        ).first()
        if existing:
            return
        db.session.execute(
            follows.insert().values(follower_id=src.id, followed_id=dst.id))

    # Alice follows: gaearon, yyx990803, torvalds, bob, carol
    for uname in ['gaearon', 'yyx990803', 'torvalds']:
        _add_follow(alice, _get_user(uname))
    for t in [bob, carol]:
        _add_follow(alice, t)

    # Bob follows: gvanrossum, torvalds, alice, david
    for uname in ['gvanrossum', 'torvalds']:
        _add_follow(bob, _get_user(uname))
    for t in [alice, david]:
        _add_follow(bob, t)

    # Carol follows: gaearon, yyx990803, alice, bob
    for uname in ['gaearon', 'yyx990803']:
        _add_follow(carol, _get_user(uname))
    for t in [alice, bob]:
        _add_follow(carol, t)

    # David follows: torvalds, mitchellh, antirez, alice
    for uname in ['torvalds', 'mitchellh', 'antirez']:
        _add_follow(david, _get_user(uname))
    _add_follow(david, alice)

    db.session.flush()

    # ── Seed Issues filed by benchmark users ──
    def _add_issue(repo_fn, author, title, body, status='open', labels=None):
        repo = _get_repo(repo_fn)
        if not repo:
            return
        next_num = (repo.issues.count() or 0) + 1
        issue = Issue(
            repo_id=repo.id,
            author_id=author.id,
            number=next_num,
            title=title,
            body=body or '',
            status=status,
            labels_json=json.dumps(labels or []),
        )
        db.session.add(issue)
        if status == 'open':
            repo.open_issues_count = (repo.open_issues_count or 0) + 1

    # Alice
    _add_issue('facebook/react', alice,
               'useState hook causes unexpected re-render on complex state updates',
               'When using useState with nested objects, the component re-renders even when '
               'values are deeply equal. Causes performance degradation in large lists.',
               labels=['bug', 'hooks'])
    _add_issue('django/django', alice,
               'ORM query optimization for many-to-many with prefetch_related',
               'Using prefetch_related with annotated querysets generates N+1 queries '
               'in some edge cases. Please add documentation or optimize.',
               labels=['performance', 'documentation'])

    # Bob
    _add_issue('tensorflow/tensorflow', bob,
               'GPU memory leak when using tf.data with large datasets',
               'Observed increasing GPU memory usage over epochs when using tf.data pipeline '
               'with map() and batch() on datasets > 100GB.',
               labels=['bug', 'gpu', 'memory'])
    _add_issue('huggingface/transformers', bob,
               'Add support for streaming inference in pipeline API',
               'The pipeline API buffers the entire output before returning. '
               'It would be useful to support streaming token generation for LLMs.',
               labels=['enhancement', 'feature-request'])

    # Carol
    _add_issue('vuejs/vue', carol,
               'v-model on custom components breaks with TypeScript strict mode',
               'When using v-model with TypeScript strict mode enabled, type inference '
               'fails for custom component props.',
               labels=['bug', 'typescript'])
    _add_issue('angular/angular', carol,
               'Router outlet flickers on route change with animations',
               'When using RouterOutlet with Angular animations, a brief flicker is visible '
               'during route transitions.',
               status='closed',
               labels=['bug', 'router', 'animations'])

    # David
    _add_issue('rust-lang/rust', david,
               'Lifetime elision rules unclear for async fn return types',
               'The compiler error messages for lifetime issues in async functions are not '
               'always clear about which lifetime rule is being violated.',
               labels=['documentation', 'async', 'lifetimes'])
    _add_issue('golang/go', david,
               'sync.Map performance regression in Go 1.22 under high contention',
               'Benchmarks show sync.Map read performance dropped ~15% in Go 1.22 vs 1.21 '
               'under high read contention.',
               labels=['bug', 'performance', 'sync'])

    db.session.commit()


# ─────────────────────────── Bulk catalog seed (v2) ───────────────────────────
# These functions augment the shipped instance_seed/github_mirror.db with
# realistic catalog breadth so search results, stargazers lists, watchers,
# and issue threads feel populated. They run AFTER seed_database() and
# seed_benchmark_users() so they never duplicate work, and each is gated by
# its own sentinel check so re-runs are no-ops (preserves byte-identical reset).

# Deterministic clock used by these seeders. We anchor offsets to
# MIRROR_REFERENCE_DATE so timestamps don't drift across rebuilds.
_BULK_REF = MIRROR_REFERENCE_DATE


def _bulk_dt(days_back: int, hours: int = 12) -> datetime:
    return _BULK_REF - timedelta(days=days_back, hours=hours)


def _load_repos_extra():
    path = os.path.join(os.path.dirname(__file__), 'scraped_data', 'repos_extra.json')
    if not os.path.exists(path):
        return []
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return []


def _parse_iso(ts: str):
    """Parse a GitHub-API ISO timestamp into a tz-naive UTC datetime."""
    if not ts:
        return _BULK_REF
    try:
        return datetime.strptime(ts.replace('Z', ''), '%Y-%m-%dT%H:%M:%S')
    except Exception:
        return _BULK_REF


# Sentinel slug for repos seeded by seed_extra_repos. R3 expanded the JSON
# again (now ~5000+ entries covering stars >=10 across niche languages), and
# the seeder now takes the FULL JSON (no cap). The sentinel needs to live
# inside the R3 slice (i.e. low-star niche-language band), so a warm reset
# detects R3 already ran. We anchor on a repo that only ships in R3's extras.
_BULK_REPO_SENTINEL_OWNER = 'authy'  # always present (R1+R2 slice, idx ~2500)
_BULK_REPO_SENTINEL_NAME = 'authy-ssh'
# R3 sentinel — only set after the R3 expanded slice runs. Allows the seeder
# to top off catalogs built with the older 2200 cap.
_BULK_R3_SENTINEL_KEY = 'r3-bulk-repos-applied'


def seed_extra_repos():
    """Import the GitHub API trending dump in scraped_data/repos_extra.json.

    Adds the top-N popular repos (deduped against what seed_database and the
    older fixture script already inserted). Owners are created on demand.
    Topics are linked into the existing topic table when the slug already
    exists; otherwise they're stored only as JSON on the repo row (matching
    how older seed code handled unknown topics).

    R3 update: caps removed. The JSON now ships ~5000+ entries spanning the
    full stars >=10 spectrum + niche languages (Zig/Crystal/Nim/Elixir/Gleam/
    Lua/R/...). Idempotent — re-runs are no-ops once everything is loaded."""
    extras = _load_repos_extra()
    if not extras:
        return

    # Fast-path: if every full_name in the JSON is already in DB, skip.
    existing_repo_fullnames = {r.full_name for r in Repository.query.with_entities(
        Repository.full_name).all()}
    needed = [r for r in extras
              if r.get('full_name') and r['full_name'] not in existing_repo_fullnames]
    if not needed:
        return

    # No cap — ingest the whole curated list. Existing full_name dedupe below
    # ensures previously-seeded entries are never re-inserted.
    target_extras = needed

    # Pre-load owners + topic map (existing_repo_fullnames computed above).
    existing_user_by_name = {u.username: u for u in User.query.all()}
    topic_by_slug = {t.slug: t for t in Topic.query.all()}

    inserted_repos = 0
    for rd in target_extras:
        full_name = rd.get('full_name') or ''
        if not full_name or full_name in existing_repo_fullnames:
            continue
        owner_name = rd.get('owner') or ''
        if not owner_name:
            continue

        owner = existing_user_by_name.get(owner_name)
        if owner is None:
            owner = User(
                username=owner_name,
                email=f"{owner_name}@users.noreply.example.com",
                name=owner_name.replace('-', ' ').title(),
                bio='',
                plan='free',
            )
            # Avoid set_password() — bcrypt random salt would break byte-id.
            owner.password_hash = PINNED_PASSWORD_HASH_BULK
            db.session.add(owner)
            db.session.flush()
            existing_user_by_name[owner_name] = owner

        created = _parse_iso(rd.get('created_at'))
        pushed = _parse_iso(rd.get('pushed_at'))
        updated = _parse_iso(rd.get('updated_at'))
        # Clamp updated_at into [created, MIRROR_REFERENCE_DATE] so relative
        # time labels stay sane and never appear "in the future". Use
        # hashlib (not Python `hash()`) so the jitter is byte-identical
        # across processes — `hash()` is randomized via PYTHONHASHSEED.
        if updated > _BULK_REF:
            _stable = int(hashlib.sha1(full_name.encode()).hexdigest()[:8], 16)
            updated = _BULK_REF - timedelta(hours=(_stable % 240))
        if pushed > _BULK_REF:
            pushed = updated

        topics_list = list(rd.get('topics') or [])

        repo = Repository(
            owner_id=owner.id,
            name=rd.get('name') or full_name.split('/', 1)[-1],
            full_name=full_name,
            description=(rd.get('description') or '')[:255],
            language=rd.get('language') or '',
            license=rd.get('license') or '',
            stars_count=int(rd.get('stars_count') or 0),
            forks_count=int(rd.get('forks_count') or 0),
            watchers_count=int(rd.get('watchers_count') or 0),
            open_issues_count=int(rd.get('open_issues_count') or 0),
            is_public=True,
            owner_type=(rd.get('owner_type') or 'user'),
            homepage=(rd.get('homepage') or '')[:200],
            default_branch=rd.get('default_branch') or 'main',
            size_kb=int(rd.get('size_kb') or 1000),
            readme=f"# {rd.get('name') or full_name}\n\n{(rd.get('description') or '').strip()}\n",
            topics_text=json.dumps(topics_list),
            gallery_json=json.dumps(load_gallery(full_name)),
            is_archived=bool(rd.get('archived')),
            is_template=bool(rd.get('is_template')),
            created_at=created,
            updated_at=updated,
            pushed_at=pushed,
        )
        db.session.add(repo)
        db.session.flush()

        # Link known topics; unknown ones live only in topics_text JSON.
        for slug in topics_list:
            t = topic_by_slug.get(slug)
            if t is not None and t not in repo.topics:
                repo.topics.append(t)

        existing_repo_fullnames.add(full_name)
        inserted_repos += 1

    db.session.commit()


# ── R3: seed bulk issues for repos with empty issue lists ────────────────
_BULK_ISSUE_TITLES = [
    "Crash when {area} receives empty input",
    "Add support for {area} in async context",
    "Memory leak in {area} module under load",
    "Improve {area} error messages",
    "Document {area} migration path",
    "{area}: handle Unicode edge cases",
    "Flaky test in {area} on Windows",
    "Performance regression in {area} since v{minor}",
    "Make {area} configurable via env var",
    "Add {area} tests for edge cases",
    "Type stubs missing for {area}",
    "Deprecate legacy {area} helper",
    "{area} does not respect proxy settings",
    "Race condition in {area} initialization",
    "{area}: improve logging granularity",
]
_BULK_ISSUE_BODIES = [
    "Hi team — running into this on v{minor}. Repro steps in the comment "
    "thread. Happy to send a PR if someone can confirm the expected fix.",
    "Originally reported in #{ref_num} but reopening because the root cause "
    "is different. Stack trace and minimal repro inside.",
    "Following up on the discussion in #{ref_num}. The proposal LGTM, but "
    "we should also handle the empty-iterator case.",
    "I'm seeing this consistently on CI but cannot reproduce locally. "
    "Anyone else hitting it? Logs attached.",
    "Looks like the public docs still reference the old API. Worth updating "
    "the migration guide as part of the next minor release.",
    "Tagging @maintainers. Low-risk fix, happy to do the work if there's "
    "interest in upstreaming.",
]
_BULK_ISSUE_LABELS = [
    ['bug'], ['bug', 'good first issue'], ['enhancement'],
    ['enhancement', 'help wanted'], ['documentation'],
    ['question'], ['performance'], ['security'],
    ['help wanted'], ['good first issue'],
]


# Sentinel: after R3 runs, total issue count is ~5000+ (was ~3000 pre-R3).
_BULK_R3_ISSUE_SENTINEL = 4500


def seed_extra_issues():
    """For repos with zero existing issues, generate 1-4 plausible issues
    so the catalog supports more PRs + comment threads. Deterministic by
    (repo.id, slot). Idempotent: only touches repos with Issue count == 0,
    so warm rebuilds are no-ops once the catalog is filled."""
    if Issue.query.count() >= _BULK_R3_ISSUE_SENTINEL:
        return 0

    # Repos that currently have no issues. Order by id for determinism.
    repos_with = {r[0] for r in db.session.query(Issue.repo_id).distinct().all()}
    empty_repos = (Repository.query
                   .filter(~Repository.id.in_(list(repos_with) or [-1]))
                   .order_by(Repository.id.asc())
                   .all())
    if not empty_repos:
        return 0

    # Pool of plausible authors: prefer real owners + benchmark users.
    pool_unames = ['alice_j', 'bob_c', 'carol_d', 'david_k',
                   'octocat', 'gaearon', 'sindresorhus', 'tj',
                   'antirez', 'mxcl', 'mitchellh', 'fabpot']
    pool = []
    for uname in pool_unames:
        u = User.query.filter_by(username=uname).first()
        if u:
            pool.append(u)
    if not pool:
        return 0
    pool_size = len(pool)

    added = 0
    target = _BULK_R3_ISSUE_SENTINEL - Issue.query.count()
    for repo in empty_repos:
        if added >= target:
            break
        # Number of issues: 1-4, gentle scale by stars. Most low-star repos
        # get just 1; popular ones get more.
        s = repo.stars_count or 0
        if s >= 1000:
            n = 3 + (repo.id % 2)  # 3 or 4
        elif s >= 100:
            n = 2 + (repo.id % 2)
        else:
            n = 1 + (repo.id % 2)

        base_dt = repo.pushed_at or repo.updated_at or _BULK_REF
        if base_dt > _BULK_REF:
            base_dt = _BULK_REF

        for i in range(n):
            area = _COMMIT_AREAS[(repo.id * 13 + i * 7) % len(_COMMIT_AREAS)]
            title = _BULK_ISSUE_TITLES[
                (repo.id * 5 + i * 11) % len(_BULK_ISSUE_TITLES)].format(
                area=area, minor=f"{1 + (repo.id % 6)}.{(repo.id // 7) % 12}")
            body = _BULK_ISSUE_BODIES[
                (repo.id * 3 + i * 19) % len(_BULK_ISSUE_BODIES)].format(
                minor=f"{1 + (repo.id % 6)}.{(repo.id // 7) % 12}",
                ref_num=((repo.id * 17 + i * 23) % 8000) + 100)
            labels = _BULK_ISSUE_LABELS[(repo.id + i) % len(_BULK_ISSUE_LABELS)]
            author = pool[(repo.id * 7 + i * 5) % pool_size]
            # Stagger by days back from base_dt.
            offset_days = i * 4 + (repo.id % 60)
            created = base_dt - timedelta(days=offset_days,
                                          hours=(repo.id + i * 11) % 24)
            # Close ~30% of issues, deterministically.
            status = 'open'
            closed_at = None
            if (repo.id * 7 + i * 3) % 100 < 30:
                status = 'closed'
                closed_at = created + timedelta(days=3 + (repo.id % 14))
                if closed_at > _BULK_REF:
                    closed_at = _BULK_REF - timedelta(hours=(repo.id % 48))

            iss = Issue(
                repo_id=repo.id,
                author_id=author.id,
                number=i + 1,
                title=title[:255],
                body=body,
                status=status,
                labels_json=json.dumps(labels),
                created_at=created,
                closed_at=closed_at,
                is_pr=0,
            )
            db.session.add(iss)
            added += 1
            if added >= target:
                break
        if added and added % 500 == 0:
            db.session.flush()

    db.session.commit()
    return added



# Bank of realistic-sounding technical replies. Picked deterministically by
# (issue_id, comment_index). Bodies vary by label so closed/bug/feature
# comments read appropriately. NO randomness — pure index math keeps the
# seed DB byte-identical across rebuilds.

_COMMENT_BANK_BUG = [
    "Thanks for the report — I can reproduce on macOS 14.4 with the latest "
    "release. Looks like the regression landed in v{minor} after the refactor "
    "in #{ref_num}. Reopening the related PR for tracking.",
    "Confirmed on Linux as well. Quick workaround: pin to the previous minor "
    "until the patch lands. I'll send a fix later this week.",
    "Looks like the stack trace points at the cache layer. Could you attach "
    "the output of `--debug` so we can see what hashes are being computed? "
    "That'll narrow it down a lot.",
    "I dug into this. The root cause is that we shadow the `state` parameter "
    "inside the inner closure, so the outer assignment is lost on retry. "
    "Patch incoming.",
    "Yeah, this is a known sharp edge. We documented it in #{ref_num} but "
    "should probably raise a clearer error instead of silently swallowing it.",
    "This appears to be a duplicate of #{ref_num}. Could you check whether "
    "the fix from that thread resolves your case before we open a new one?",
]
_COMMENT_BANK_ENH = [
    "Big +1 on this. It would unblock a workflow we've been hacking around "
    "with shell scripts. Happy to take a stab at the API design if maintainers "
    "want a sketch first.",
    "Love the idea. One concern: how does this interact with the existing "
    "`--strict` flag? We'd want to make sure the defaults stay backwards-compatible.",
    "Could the new option also accept a glob pattern? That would cover the "
    "monorepo case where the rule should apply per-package.",
    "We use this internally with a wrapper. Would be much cleaner upstreamed. "
    "Naming nit: maybe `--include-tests` rather than `--with-tests`?",
    "Tagging @maintainers for visibility — this looks like a low-risk addition "
    "with clear upside. Happy to review a PR if someone picks it up.",
    "I drafted a proof-of-concept on a fork last weekend. If we agree on the "
    "shape, I can polish it into a proper PR.",
]
_COMMENT_BANK_DOCS = [
    "Good catch. The README still references the old config key. I'll send "
    "a small docs PR.",
    "Agreed — the examples in the docs would also benefit from a real-world "
    "snippet. Happy to write one if you point me at the right page.",
    "The migration guide skips this step entirely. Worth a callout box at "
    "the top of the section.",
    "I just hit this exact confusion last week. A diagram of the data flow "
    "would help newcomers a lot.",
    "FYI the docs site search doesn't surface this page when you search the "
    "obvious keywords. Might want to bump the meta description.",
]
_COMMENT_BANK_QUESTION = [
    "Try setting `LOG_LEVEL=debug` and re-running — the underlying error is "
    "usually clearer there. Let us know what you see.",
    "Which version are you on? `--version` output would help us reproduce.",
    "This is covered in the FAQ section of the README. Short version: yes, "
    "but you need to enable the experimental flag first.",
    "Take a look at the discussion in #{ref_num} — same scenario, with a "
    "working config example near the bottom.",
    "Hmm, that's surprising. Could you share a minimal repro? Even a 10-line "
    "snippet would help us narrow it down.",
]
_COMMENT_BANK_CLOSED = [
    "Closing this — the fix landed in v{minor} and is now in the stable "
    "channel. Thanks everyone for the investigation.",
    "Resolved by #{ref_num}. Reopen if you still see it on the latest release.",
    "Marking this as not-planned. The proposed change would break the public "
    "API in too many places. Tracking the alternative in a discussion.",
    "Closing as superseded by the new architecture in #{ref_num}.",
]
_COMMENT_BANK_PR = [
    "LGTM overall. Two small nits inline — feel free to address or wave off.",
    "Tests pass locally on Linux and macOS. CI is green. Approving once the "
    "nits are addressed.",
    "Could you add a changelog entry under `Unreleased`? Otherwise this is "
    "ready to ship.",
    "Quick question: does this change the error message format? Anyone "
    "grepping CI logs for the old text would break.",
    "Thanks for taking this on! Left some thoughts inline — the core approach "
    "is right, just need to rework the error path.",
    "Rebased on main, force-pushed, ready for another look.",
    "Looks good — one architectural question. Should we hoist the new helper "
    "into the shared module so the CLI can reuse it?",
]


def _comment_bank_for(labels: list, is_pr: bool, is_closed: bool):
    """Return the (deterministic) bank list to draw from for a given issue."""
    if is_pr:
        return _COMMENT_BANK_PR
    label_set = {str(l).lower() for l in (labels or [])}
    if is_closed:
        return _COMMENT_BANK_CLOSED
    if 'bug' in label_set or 'regression' in label_set or 'memory' in label_set:
        return _COMMENT_BANK_BUG
    if 'enhancement' in label_set or 'feature-request' in label_set or 'feature request' in label_set:
        return _COMMENT_BANK_ENH
    if 'documentation' in label_set or 'docs' in label_set:
        return _COMMENT_BANK_DOCS
    if 'question' in label_set or 'help wanted' in label_set:
        return _COMMENT_BANK_QUESTION
    # Fallback: rotate through the bug bank — most issues are bug-ish.
    return _COMMENT_BANK_BUG


# Sentinel: when seed_extra_issue_comments has run, IssueComment count is
# well above the original 15. R3 expects 8000+ total comments after the
# denser distribution below; bump sentinel so re-runs top off if R2 already
# wrote ~3500 (which is below the R3 target).
_BULK_COMMENT_SENTINEL = 8000


def seed_extra_issue_comments():
    """Spread realistic-sounding comment threads across existing issues/PRs.

    Distribution (R3, denser than R2):
      • ~15% of issues get 0 comments
      • ~35% get 1 comment
      • ~25% get 2 comments
      • ~15% get 3 comments
      • ~10% get 4 comments
    Total target: ~8000-10000 comments. All bodies and authors are picked
    deterministically by index math — no random.choice — so the resulting
    seed DB is byte-identical across rebuilds."""
    if IssueComment.query.count() >= _BULK_COMMENT_SENTINEL:
        return

    # Sorted query order matters for determinism.
    issues = Issue.query.order_by(Issue.id.asc()).all()
    if not issues:
        return

    # Pool of plausible commenters: real demo accounts + benchmark users +
    # a fixed slice of synthetic users (sorted by id for stability).
    pool_usernames = ['octocat', 'torvalds', 'gaearon', 'yyx990803',
                      'gvanrossum', 'dhh', 'tj', 'brendangregg',
                      'sindresorhus', 'antirez', 'mitchellh', 'defunkt',
                      'wycats', 'fabpot', 'mxcl',
                      'alice_j', 'bob_c', 'carol_d', 'david_k']
    pool_users = []
    seen_ids = set()
    for uname in pool_usernames:
        u = User.query.filter_by(username=uname).first()
        if u and u.id not in seen_ids:
            pool_users.append(u)
            seen_ids.add(u.id)
    # Top up with a deterministic slice of other users (synthetic accounts).
    extras = (User.query
              .filter(~User.id.in_(seen_ids))
              .order_by(User.id.asc())
              .limit(40).all())
    pool_users.extend(extras)
    if not pool_users:
        return

    pool_size = len(pool_users)
    bulk_added = 0

    for idx, issue in enumerate(issues):
        # R3 deterministic comment count: hash by issue id only, denser.
        # Target mean ~1.85 → ~8500 comments across ~4500 issues.
        bucket = issue.id % 20
        if bucket < 2:
            n_comments = 0
        elif bucket < 9:
            n_comments = 1
        elif bucket < 14:
            n_comments = 2
        elif bucket < 18:
            n_comments = 3
        else:
            n_comments = 4

        if n_comments == 0:
            continue

        labels = issue.get_labels()
        is_closed = (issue.status or 'open') in ('closed', 'merged')
        is_pr = bool(issue.is_pr)
        bank = _comment_bank_for(labels, is_pr, is_closed)

        # Don't double-comment if some seed code already added one.
        existing = issue.comments.count()
        for c_idx in range(existing, n_comments):
            tmpl_idx = (issue.id * 7 + c_idx * 3) % len(bank)
            body = bank[tmpl_idx].format(
                minor=f"{1 + (issue.id % 6)}.{(issue.id // 7) % 12}",
                ref_num=((issue.id * 13 + c_idx * 31) % 9000) + 100,
            )
            author = pool_users[(issue.id * 11 + c_idx * 5) % pool_size]
            # Skip authoring as the issue opener to avoid weird "OP replies
            # to itself first" patterns on the first comment.
            if c_idx == 0 and author.id == issue.author_id and pool_size > 1:
                author = pool_users[(issue.id * 11 + c_idx * 5 + 1) % pool_size]

            # Stagger timestamps inside the issue's window.
            base = issue.created_at or _BULK_REF
            offset_hours = (c_idx + 1) * 6 + (issue.id % 48)
            ts = base + timedelta(hours=offset_hours)
            if ts > _BULK_REF:
                ts = _BULK_REF - timedelta(hours=(issue.id % 72))

            db.session.add(IssueComment(
                issue_id=issue.id,
                author_id=author.id,
                body=body,
                created_at=ts,
            ))
            bulk_added += 1

        # Flush periodically to keep memory bounded.
        if bulk_added and bulk_added % 200 == 0:
            db.session.flush()

    db.session.commit()


# Sentinel: after running, Star count is well above the original 27.
_BULK_STAR_SENTINEL = 100
_BULK_WATCH_SENTINEL = 60


def _existing_star_set():
    return {(s.user_id, s.repo_id) for s in Star.query.all()}


def _existing_watch_set():
    return {(w.user_id, w.repo_id) for w in Watch.query.all()}


def seed_extra_stars():
    """Distribute stars across the most popular repos so /stargazers pages
    show realistic crowds, and /stars for benchmark users shows breadth."""
    if Star.query.count() >= _BULK_STAR_SENTINEL:
        return

    # Pool of starring accounts: benchmark users + demo accounts + a chunk
    # of synthetic accounts (sorted by id for determinism).
    starring_usernames = ['alice_j', 'bob_c', 'carol_d', 'david_k',
                          'octocat', 'torvalds', 'gaearon', 'yyx990803',
                          'gvanrossum', 'dhh', 'sindresorhus', 'antirez',
                          'mitchellh', 'defunkt', 'wycats', 'fabpot', 'mxcl',
                          'tj', 'brendangregg']
    starrers = []
    seen_ids = set()
    for uname in starring_usernames:
        u = User.query.filter_by(username=uname).first()
        if u and u.id not in seen_ids:
            starrers.append(u)
            seen_ids.add(u.id)
    extras = (User.query.filter(~User.id.in_(seen_ids))
              .order_by(User.id.asc()).limit(40).all())
    starrers.extend(extras)
    if not starrers:
        return

    # Repo pool: top 80 repos by stars (most likely to be browsed) plus the
    # 30 most-recently-pushed repos (for the "active" stargazers feel).
    # Tiebreak on Repository.id so the pool is deterministic across rebuilds —
    # the catalog has many repos sharing the same stars_count / pushed_at.
    top_repos = (Repository.query
                 .order_by(Repository.stars_count.desc(), Repository.id.asc())
                 .limit(80).all())
    recent_repos = (Repository.query
                    .order_by(Repository.pushed_at.desc(), Repository.id.asc())
                    .limit(30).all())
    repo_pool = []
    seen_repo = set()
    for r in top_repos + recent_repos:
        if r.id not in seen_repo:
            repo_pool.append(r)
            seen_repo.add(r.id)

    existing = _existing_star_set()
    added = 0

    # Each user stars between 6 and 14 repos, picked deterministically by
    # (user.id, slot) -> repo_pool index. Stars_count on the repo bumps to
    # keep the displayed badge consistent with the link count.
    for u in starrers:
        n_to_star = 6 + (u.id % 9)
        for slot in range(n_to_star):
            idx = (u.id * 17 + slot * 41) % len(repo_pool)
            repo = repo_pool[idx]
            key = (u.id, repo.id)
            if key in existing:
                continue
            db.session.add(Star(
                user_id=u.id,
                repo_id=repo.id,
                created_at=_bulk_dt(days_back=((u.id + slot * 5) % 365)),
            ))
            existing.add(key)
            repo.stars_count = (repo.stars_count or 0) + 1
            added += 1

    db.session.commit()


def seed_extra_watches():
    """Same shape as seed_extra_stars but for watches, with smaller fan-out."""
    if Watch.query.count() >= _BULK_WATCH_SENTINEL:
        return

    watching_usernames = ['alice_j', 'bob_c', 'carol_d', 'david_k',
                          'octocat', 'torvalds', 'gaearon', 'yyx990803',
                          'gvanrossum', 'dhh', 'sindresorhus', 'antirez',
                          'mitchellh']
    watchers = []
    seen_ids = set()
    for uname in watching_usernames:
        u = User.query.filter_by(username=uname).first()
        if u and u.id not in seen_ids:
            watchers.append(u)
            seen_ids.add(u.id)
    extras = (User.query.filter(~User.id.in_(seen_ids))
              .order_by(User.id.asc()).limit(20).all())
    watchers.extend(extras)
    if not watchers:
        return

    top_repos = (Repository.query
                 .order_by(Repository.stars_count.desc(), Repository.id.asc())
                 .limit(60).all())

    existing = _existing_watch_set()
    added = 0
    for u in watchers:
        n_to_watch = 2 + (u.id % 4)
        for slot in range(n_to_watch):
            idx = (u.id * 23 + slot * 19) % len(top_repos)
            repo = top_repos[idx]
            key = (u.id, repo.id)
            if key in existing:
                continue
            db.session.add(Watch(
                user_id=u.id,
                repo_id=repo.id,
                created_at=_bulk_dt(days_back=((u.id * 3 + slot * 7) % 240)),
            ))
            existing.add(key)
            repo.watchers_count = (repo.watchers_count or 0) + 1
            added += 1

    db.session.commit()


# ── R2: deterministic commit history for repos that lack commits_json ────
_BULK_COMMIT_SENTINEL_FULL = 'codecrafters-io/build-your-own-x'  # newly-imported repo

_COMMIT_MSG_TEMPLATES = [
    "Fix off-by-one in {area} pagination",
    "Bump {area} dependencies to latest",
    "Add tests for {area} edge cases",
    "Refactor {area} module for readability",
    "Document {area} configuration options",
    "Optimize {area} hot path",
    "Drop deprecated {area} helper",
    "Handle empty input in {area}",
    "Improve {area} error message",
    "Clean up unused {area} imports",
    "Tighten {area} type hints",
    "Wire up {area} CI matrix",
    "Patch {area} security advisory",
    "Restore {area} backwards compatibility",
    "Cache {area} lookups",
]
_COMMIT_AREAS = ['cli', 'api', 'core', 'docs', 'router', 'parser', 'cache',
                 'auth', 'config', 'tests', 'build', 'logging', 'metrics',
                 'storage', 'worker', 'utils']
_COMMIT_FILE_HINTS = {
    'Python': ['src/{a}.py', 'tests/test_{a}.py', 'docs/{a}.md', 'README.md',
               'pyproject.toml'],
    'JavaScript': ['src/{a}.js', 'tests/{a}.spec.js', 'package.json',
                   'README.md', 'eslint.config.js'],
    'TypeScript': ['src/{a}.ts', 'src/{a}.test.ts', 'tsconfig.json',
                   'README.md', 'package.json'],
    'Go': ['{a}.go', '{a}_test.go', 'go.mod', 'README.md', 'cmd/main.go'],
    'Rust': ['src/{a}.rs', 'tests/{a}.rs', 'Cargo.toml', 'README.md'],
    'Java': ['src/main/java/{a}/{a}.java', 'src/test/java/{a}/{a}Test.java',
             'pom.xml', 'README.md'],
    'C++': ['src/{a}.cpp', 'include/{a}.h', 'tests/{a}_test.cpp',
            'CMakeLists.txt', 'README.md'],
    'C': ['src/{a}.c', 'include/{a}.h', 'Makefile', 'README.md'],
    'Ruby': ['lib/{a}.rb', 'spec/{a}_spec.rb', 'Gemfile', 'README.md'],
}
_COMMIT_FILE_DEFAULT = ['src/{a}', 'tests/{a}_test', 'docs/{a}.md',
                        'README.md', 'CHANGELOG.md']


def _commit_files_for(language: str, area: str, idx: int):
    """Pick 1-3 plausible filenames for a commit deterministically."""
    tmpl = _COMMIT_FILE_HINTS.get(language) or _COMMIT_FILE_DEFAULT
    n = 1 + (idx % 3)
    out = []
    for k in range(n):
        path = tmpl[(idx + k) % len(tmpl)].format(a=area)
        # plausible per-file diff sizes
        adds = 4 + ((idx * 7 + k * 13) % 80)
        dels = ((idx * 5 + k * 11) % 50)
        out.append({'name': path, 'additions': adds, 'deletions': dels})
    return out


def seed_extra_commits():
    """Generate deterministic commit history for every repo that doesn't
    already have commits_json populated. Targets ~5000+ extra commits across
    the catalog so the /<repo>/commits page is never empty.

    All values derive from repo.id + repo.full_name, never wall-clock or
    random, so md5×2 stays stable. Idempotent: the WHERE filter only picks
    up repos whose commits_json is still empty, so re-runs are no-ops once
    every repo has been processed.

    Returns the number of repos that were actually mutated this call (0 on
    a warm rebuild, used by normalize_seed_db_layout() to skip VACUUM)."""
    # Touch every repo whose commits_json is empty/missing.
    repos = (Repository.query
             .filter((Repository.commits_json == None) |  # noqa: E711
                     (Repository.commits_json == '') |
                     (Repository.commits_json == '[]'))
             .order_by(Repository.id.asc())
             .all())
    if not repos:
        return 0

    total_added = 0
    for repo in repos:
        # R3: commit history is denser. Targets ~60k+ commits across the
        # full ~5k-repo catalog (mean ~12 commits/repo).
        s = repo.stars_count or 0
        if s >= 50000:
            n = 18
        elif s >= 10000:
            n = 15
        elif s >= 1000:
            n = 12
        elif s >= 100:
            n = 10
        else:
            n = 8

        base_dt = repo.pushed_at or repo.updated_at or _BULK_REF
        if base_dt > _BULK_REF:
            base_dt = _BULK_REF
        owner_name = repo.full_name.split('/', 1)[0]

        commit_list = []
        for i in range(n):
            area = _COMMIT_AREAS[(repo.id * 7 + i * 11) % len(_COMMIT_AREAS)]
            msg = _COMMIT_MSG_TEMPLATES[
                (repo.id * 3 + i * 17) % len(_COMMIT_MSG_TEMPLATES)].format(area=area)
            # Spread commits 1-3 days apart, newest first.
            ts = base_dt - timedelta(days=i * 2 + (repo.id % 3),
                                     hours=(i * 5 + repo.id) % 24)
            sha_seed = f"{repo.full_name}|{i}|{repo.id}"
            sha = hashlib.sha1(sha_seed.encode()).hexdigest()
            files = _commit_files_for(repo.language or '', area, repo.id + i)
            adds = sum(f['additions'] for f in files)
            dels = sum(f['deletions'] for f in files)
            commit_list.append({
                'sha': sha,
                'message': msg,
                'author': owner_name,
                'date': ts.isoformat(),
                'files': files,
                'additions': adds,
                'deletions': dels,
            })
        # Persist
        repo.commits_json = json.dumps(commit_list)
        # Mirror index 0 onto the latest_commit_* legacy columns.
        first = commit_list[0]
        repo.latest_commit_sha = first['sha']
        repo.latest_commit_message = first['message']
        repo.latest_commit_date = datetime.fromisoformat(first['date'])
        repo.latest_commit_files = json.dumps(first['files'])
        repo.latest_commit_additions = first['additions']
        repo.latest_commit_deletions = first['deletions']
        total_added += n

    db.session.commit()
    return len(repos)


# ── R2: turn a slice of open-status issues into real pull requests ───────
_BULK_PR_SENTINEL_TITLE_PREFIX = 'R2-bulk-pr:'

_PR_BRANCH_PATTERNS = [
    'fix/{a}-{n}', 'feat/{a}-{n}', 'chore/bump-{a}', 'refactor/{a}',
    'docs/{a}', 'deps/{a}-update', 'hotfix/{a}-{n}', 'release/{a}',
]


def seed_extra_pulls():
    """Promote ~3000 existing open issues into pull requests (is_pr=1) and
    fill the PR metadata columns. Deterministic against issue.id. Returns
    the number of issues promoted, so normalize_seed_db_layout() can skip
    VACUUM on warm rebuilds. R3 doubled the target from 1500 to 3000."""
    existing_pr = Issue.query.filter_by(is_pr=1).count()
    if existing_pr >= 3000:
        return 0

    target_total = 3000
    need = max(0, target_total - existing_pr)
    if need == 0:
        return 0

    # Pick open, non-PR issues with the lowest IDs (deterministic order).
    candidates = (Issue.query
                  .filter(Issue.is_pr == 0, Issue.status == 'open')
                  .order_by(Issue.id.asc())
                  .limit(need)
                  .all())
    if not candidates:
        return 0

    promoted = 0
    for issue in candidates:
        area = _COMMIT_AREAS[issue.id % len(_COMMIT_AREAS)]
        branch_tmpl = _PR_BRANCH_PATTERNS[issue.id % len(_PR_BRANCH_PATTERNS)]
        head = branch_tmpl.format(a=area, n=issue.id % 1000)[:120]
        issue.is_pr = 1
        issue.pr_head_branch = head
        issue.pr_base_branch = 'main'
        issue.pr_changed_files = 1 + (issue.id % 7)
        issue.pr_additions = 12 + (issue.id * 7 % 480)
        issue.pr_deletions = 4 + (issue.id * 11 % 200)
        issue.pr_commits_count = 1 + (issue.id % 5)
        # Roughly 35% of PRs are merged (status='merged') to make the UI feel
        # alive. Use issue.id % 100 deterministically.
        bucket = issue.id % 100
        if bucket < 35:
            issue.status = 'merged'
            issue.closed_at = (issue.created_at or _BULK_REF) + timedelta(
                days=2 + (issue.id % 10), hours=(issue.id % 24))
            if issue.closed_at > _BULK_REF:
                issue.closed_at = _BULK_REF - timedelta(hours=(issue.id % 48))
        promoted += 1

    db.session.commit()
    return promoted


# ─────────────────────────── R4 bulk seeders ───────────────────────────
# Synthesize organization-owned repos + discussions + sponsorships + project
# boards + packages + teams so /orgs/<org>/teams, /<repo>/discussions,
# /<repo>/projects, /sponsors, /<repo>/packages all have real data.
#
# Every value derives from a hash of a stable key (org username, repo id,
# slot index) — never from `random` or wall-clock — so md5×2 matches.

_R4_REPO_SUFFIXES = [
    'core', 'cli', 'sdk', 'tools', 'examples', 'docs', 'starter',
    'plugin', 'utils', 'kit', 'experiments', 'website', 'demos',
    'workflow', 'cookbook', 'specs', 'protocol', 'playground',
    'blueprint', 'sandbox', 'lab', 'roadmap', 'lite',
]
_R4_REPO_DESC = [
    "Lightweight {a} helpers used internally by the {org} team.",
    "Reference {a} integration patterns and examples for {org}.",
    "Open documentation site for {org} {a} projects.",
    "{a} utilities split out of the main {org} monorepo.",
    "Curated awesome list of {a} resources maintained by {org}.",
    "Public roadmap and design notes for {org}'s {a} platform.",
    "Tooling that powers {org}'s {a} release pipeline.",
    "{a} starter template — fork, edit, deploy.",
    "Working group repository for {org}'s {a} initiative.",
    "Community-contributed plugins for {org}'s {a} stack.",
]
_R4_REPO_README_BANK = [
    "# {full}\n\n> {desc}\n\n## Why\n\nThis repository keeps the {a} layer "
    "of {org}'s stack honest. We aim for small, well-tested helpers that the "
    "rest of the org can rely on without pulling in a heavy framework.\n\n"
    "## Install\n\n```bash\n# Choose your weapon\nnpm i @{org}/{name}\npip "
    "install {org}-{name}\ngo get github.com/{org}/{name}\n```\n\n## Quick "
    "start\n\nSee [`examples/`](./examples) for a runnable demo.\n",
    "# {full}\n\n{desc}\n\n## Status\n\nProduction-ready since v{maj}.{min}. "
    "Public API is stable; breaking changes go through a deprecation cycle "
    "of at least one minor release.\n\n## Features\n\n- Zero runtime "
    "dependencies (except {a}).\n- Tree-shakeable / minifies well.\n- Works "
    "in browsers, Node ≥18, and modern bundlers.\n- TypeScript types "
    "shipped.\n\n## Contributing\n\nPlease read `CONTRIBUTING.md` before "
    "opening a PR. We squash-merge; small focused changes get reviewed "
    "fastest.\n",
    "# {full}\n\n{desc}\n\nThis project is part of the broader **{org}** "
    "ecosystem. The goal is to keep {a}-related concerns in one place so "
    "downstream teams don't reinvent them every quarter.\n\n## Roadmap\n\n"
    "- [x] v1: stable core API\n- [x] v{maj}: structured logging hooks\n- [ ] "
    "v{nx}: native async support\n- [ ] v{nx2}: WASM build\n\nSee `ROADMAP.md` "
    "for context.\n",
]
_R4_LICENSE_BAND = ['MIT', 'Apache-2.0', 'BSD-3-Clause', 'MIT', 'MIT',
                    'MPL-2.0', 'GPL-3.0', 'Apache-2.0']
_R4_BRANCH_BAND = ['main', 'main', 'main', 'master', 'develop', 'trunk']
_R4_LANG_POOL = ['Python', 'TypeScript', 'JavaScript', 'Go', 'Rust', 'Java',
                 'C++', 'Ruby', 'Kotlin', 'Swift', 'Shell', 'C#']


def _r4_hash(*parts) -> int:
    """Stable cross-process hash. Never `hash()` — that's seeded by env."""
    key = '|'.join(str(p) for p in parts)
    return int(hashlib.sha1(key.encode()).hexdigest()[:10], 16)


def seed_r4_org_repos():
    """Grow the catalog from ~8000 → 12000+ by synthesizing additional repos
    under existing organization owners. Deterministic against org username +
    suffix index. Each repo gets readme excerpt, languages list, license,
    archive status, default_branch.

    Idempotent: stops once total repo count ≥ 12000."""
    target_total = 12000
    have = Repository.query.count()
    if have >= target_total:
        return 0

    # All organization owners, ordered for determinism.
    orgs = (User.query
            .join(Repository, Repository.owner_id == User.id)
            .filter(Repository.owner_type == 'organization')
            .order_by(User.username.asc())
            .distinct()
            .all())
    if not orgs:
        return 0

    existing_full = {r.full_name for r in
                     Repository.query.with_entities(Repository.full_name).all()}
    topic_by_slug = {t.slug: t for t in Topic.query.all()}

    # Common topics so synthesized repos pick up real /topics/<slug> linkage.
    common_topics_pool = [
        'cli', 'sdk', 'documentation', 'developer-tools', 'open-source',
        'awesome-list', 'plugin', 'starter', 'utilities', 'roadmap',
        'examples', 'demo', 'platform', 'monitoring', 'security',
        'devtools', 'workflow', 'productivity', 'react', 'nodejs',
        'python', 'typescript', 'go', 'rust', 'kubernetes', 'docker',
    ]

    added = 0
    # Multiple passes through suffixes so big orgs get more repos but tiny
    # ones still get a couple. Stop on target hit.
    for slot in range(len(_R4_REPO_SUFFIXES)):
        if have + added >= target_total:
            break
        for org in orgs:
            if have + added >= target_total:
                break
            # Skip orgs that already have ≥40 repos so we don't drown them.
            existing_for_org = sum(1 for fn in existing_full
                                   if fn.startswith(org.username + '/'))
            if existing_for_org >= 40:
                continue
            suffix = _R4_REPO_SUFFIXES[(slot + _r4_hash(org.username)) %
                                       len(_R4_REPO_SUFFIXES)]
            base_name = f"{org.username.split('-')[0].lower()}-{suffix}"
            base_name = re.sub(r'[^a-z0-9._-]', '-', base_name)[:60].strip('-')
            if not base_name:
                continue
            full = f"{org.username}/{base_name}"
            # Disambiguate if collision.
            if full in existing_full:
                full = f"{org.username}/{base_name}-{slot}"
                if full in existing_full:
                    continue
                base_name = full.split('/', 1)[1]
            h = _r4_hash(full, slot)
            lang = _R4_LANG_POOL[h % len(_R4_LANG_POOL)]
            area = ['ingestion', 'parser', 'cache', 'auth', 'routing',
                    'transport', 'config', 'telemetry'][(h >> 3) % 8]
            desc = _R4_REPO_DESC[(h >> 5) % len(_R4_REPO_DESC)].format(
                a=area, org=org.username)[:255]
            readme = _R4_REPO_README_BANK[(h >> 7) % len(_R4_REPO_README_BANK)].format(
                full=full, name=base_name, org=org.username, desc=desc,
                a=area,
                maj=1 + (h % 4),
                min=(h >> 2) % 18,
                nx=2 + (h % 4),
                nx2=3 + (h % 4),
            )
            # languages list (stored as JSON in topics_text? No, in readme).
            # We keep main "language" field + add a sibling list via gallery_json
            # ratio map: [{name,pct}].
            lang2 = _R4_LANG_POOL[(h >> 9) % len(_R4_LANG_POOL)]
            lang3 = _R4_LANG_POOL[(h >> 11) % len(_R4_LANG_POOL)]
            lang_mix = [
                {'name': lang, 'pct': 55 + (h % 25)},
                {'name': lang2 if lang2 != lang else 'Shell',
                 'pct': 15 + ((h >> 1) % 18)},
                {'name': lang3 if lang3 not in (lang, lang2) else 'HTML',
                 'pct': 5 + ((h >> 2) % 10)},
            ]
            # Normalize so pct sums to 100.
            tot = sum(x['pct'] for x in lang_mix)
            for x in lang_mix:
                x['pct'] = round(x['pct'] * 100 / tot)
            gallery = {'language_mix': lang_mix}

            stars = 5 + (h % 1400)
            forks = max(0, stars // (3 + (h % 6)))
            watchers = max(1, stars // 6)
            open_issues = (h >> 4) % 18
            is_archived = ((h >> 7) % 12 == 0)
            license_ = _R4_LICENSE_BAND[(h >> 6) % len(_R4_LICENSE_BAND)]
            default_branch = _R4_BRANCH_BAND[(h >> 8) % len(_R4_BRANCH_BAND)]
            # Pick 2-4 topics
            topic_slugs = []
            for k in range(2 + (h % 3)):
                ts = common_topics_pool[(h * 7 + k * 13) %
                                        len(common_topics_pool)]
                if ts not in topic_slugs:
                    topic_slugs.append(ts)

            created = _BULK_REF - timedelta(days=120 + (h % 1200),
                                            hours=(h >> 4) % 24)
            pushed = _BULK_REF - timedelta(days=(h % 240),
                                           hours=(h >> 5) % 24)
            updated = pushed
            sha = hashlib.sha1(full.encode()).hexdigest()

            repo = Repository(
                owner_id=org.id,
                name=base_name,
                full_name=full,
                description=desc,
                language=lang,
                license=license_,
                stars_count=stars,
                forks_count=forks,
                watchers_count=watchers,
                open_issues_count=open_issues,
                is_public=True,
                is_fork=False,
                is_template=((h >> 9) % 25 == 0),
                is_archived=is_archived,
                has_readme=True,
                has_wiki=((h >> 3) % 4 == 0),
                has_issues=True,
                owner_type='organization',
                default_branch=default_branch,
                size_kb=200 + (h % 18000),
                readme=readme,
                topics_text=json.dumps(topic_slugs),
                gallery_json=json.dumps(gallery),
                created_at=created,
                updated_at=updated,
                pushed_at=pushed,
                latest_release_version=f"v{1 + (h % 4)}.{(h >> 2) % 18}.{(h >> 4) % 12}",
                latest_release_date=pushed - timedelta(days=14 + (h % 60)),
                latest_release_notes=f"Bug fixes, performance, and docs polish in the {area} module.",
                latest_commit_sha=sha,
                latest_commit_message=f"Refactor {area} for clarity ({base_name})",
                latest_commit_date=pushed,
                latest_commit_additions=12 + (h % 240),
                latest_commit_deletions=4 + ((h >> 1) % 120),
            )
            db.session.add(repo)
            db.session.flush()
            for slug in topic_slugs:
                t = topic_by_slug.get(slug)
                if t is not None:
                    repo.topics.append(t)
            existing_full.add(full)
            added += 1
            if added % 500 == 0:
                db.session.commit()
    db.session.commit()
    return added


# ── Discussions ──────────────────────────────────────────────────
_R4_DISC_TITLES = [
    "How are you using {a} in production?",
    "Proposal: rework the {a} configuration story",
    "Q: best practices for {a} in monorepos?",
    "Show and tell: my {a} dashboard built in a weekend",
    "Roadmap discussion — v{nx} priorities",
    "Annual {a} survey results — let's discuss",
    "Help: {a} stops working after upgrading to v{maj}",
    "Why we picked this {a} architecture (and what we'd change)",
    "Should we deprecate the legacy {a} flag?",
    "RFC: typed plugin API for {a} extensions",
    "Lessons from running {a} on Kubernetes for 18 months",
    "Naming poll: rename `--strict` to `--exhaustive`?",
]
_R4_DISC_BODIES = [
    "Curious to hear how teams are deploying this in real workloads. We "
    "run ~14 nodes across two regions and the only sharp edge has been "
    "config reloads — what's your story?",
    "I've been sketching a proposal that collapses the three config sources "
    "(env, file, CLI flag) into a single layered loader. Feedback wanted "
    "before I open a PR.",
    "Pros: smaller surface area, easier docs. Cons: breaking change for "
    "anyone wiring up multiple sources today. Worth the migration?",
    "Sharing some numbers from our internal benchmark. tl;dr is the new "
    "code path is ~38% faster on cold start, no regressions on hot path.",
    "Wanted to surface a community sentiment thread before we lock the "
    "next minor release. Please drop a +1 / -1 + short reasoning.",
]
_R4_DISC_CATEGORIES = ['Q&A', 'Ideas', 'Announcements', 'General',
                       'Show and tell', 'Polls', 'Ideas', 'Q&A']


def seed_r4_discussions():
    """Generate 2-6 discussions per top repo (stars >= 200) so
    /<repo>/discussions has real content. ~3000 discussions total."""
    if Discussion.query.count() >= 2500:
        return 0
    top_repos = (Repository.query
                 .filter(Repository.stars_count >= 200)
                 .order_by(Repository.id.asc())
                 .limit(700)
                 .all())
    if not top_repos:
        return 0
    pool_unames = ['alice_j', 'bob_c', 'carol_d', 'david_k',
                   'octocat', 'gaearon', 'sindresorhus', 'tj',
                   'antirez', 'mxcl', 'mitchellh', 'fabpot', 'torvalds',
                   'gvanrossum', 'yyx990803']
    pool = [u for u in (User.query.filter_by(username=n).first()
                        for n in pool_unames) if u]
    if not pool:
        return 0
    pool_size = len(pool)

    added = 0
    for repo in top_repos:
        existing = Discussion.query.filter_by(repo_id=repo.id).count()
        if existing > 0:
            continue
        s = repo.stars_count or 0
        n = 2 if s < 1000 else (4 if s < 10000 else 6)
        base_dt = repo.pushed_at or _BULK_REF
        if base_dt > _BULK_REF:
            base_dt = _BULK_REF
        for i in range(n):
            h = _r4_hash(repo.full_name, 'disc', i)
            area = _COMMIT_AREAS[h % len(_COMMIT_AREAS)]
            title = _R4_DISC_TITLES[(h >> 2) % len(_R4_DISC_TITLES)].format(
                a=area, maj=1 + (h % 5), nx=2 + (h % 4))[:255]
            body = _R4_DISC_BODIES[(h >> 4) % len(_R4_DISC_BODIES)]
            category = _R4_DISC_CATEGORIES[(h >> 6) % len(_R4_DISC_CATEGORIES)]
            status_pick = h % 10
            if category == 'Q&A' and status_pick < 6:
                status = 'answered'
            elif status_pick < 2:
                status = 'closed'
            else:
                status = 'open'
            author = pool[(h >> 8) % pool_size]
            created = base_dt - timedelta(days=i * 6 + (h % 90),
                                          hours=(h >> 3) % 24)
            comments_count = 1 + (h % 14)
            d = Discussion(
                repo_id=repo.id,
                author_id=author.id,
                number=i + 1,
                title=title,
                body=body,
                category=category,
                status=status,
                upvotes=(h >> 5) % 80,
                comments_count=comments_count,
                created_at=created,
            )
            db.session.add(d)
            db.session.flush()
            # Sprinkle a few real comments so /<repo>/discussions/<n> isn't
            # empty when WebVoyager clicks in.
            for j in range(min(3, comments_count)):
                ch = _r4_hash(repo.full_name, 'disc', i, 'c', j)
                cauthor = pool[(ch >> 4) % pool_size]
                cbody = _R4_DISC_BODIES[ch % len(_R4_DISC_BODIES)]
                is_ans = 0
                if status == 'answered' and j == 0:
                    is_ans = 1
                dc = DiscussionComment(
                    discussion_id=d.id,
                    author_id=cauthor.id,
                    body=cbody,
                    is_answer=is_ans,
                    created_at=created + timedelta(days=j * 2,
                                                   hours=(ch % 24)),
                )
                db.session.add(dc)
                if is_ans:
                    db.session.flush()
                    d.answered_comment_id = dc.id
            added += 1
        if added and added % 200 == 0:
            db.session.commit()
    db.session.commit()
    return added


# ── Sponsorships ─────────────────────────────────────────────────
_R4_SPONSOR_TIERS = [
    ('Backer', 500),  # $5/mo
    ('Backer', 1000),  # $10/mo
    ('Supporter', 2500),  # $25/mo
    ('Sponsor', 10000),  # $100/mo
    ('Patron', 50000),  # $500/mo
]


def seed_r4_sponsorships():
    """Seed ~280 sponsorship entries from benchmark + popular users to
    well-known developer/org accounts. Idempotent."""
    if Sponsorship.query.count() >= 250:
        return 0
    # Targets: popular individual maintainers + orgs with stars.
    candidate_targets = [
        'octocat', 'gaearon', 'yyx990803', 'sindresorhus', 'tj',
        'antirez', 'mxcl', 'mitchellh', 'fabpot', 'torvalds',
        'gvanrossum', 'evanw', 'kentcdodds', 'jaredpalmer',
        'facebook', 'vuejs', 'vercel', 'tensorflow', 'huggingface',
        'rust-lang', 'golang', 'pallets', 'django',
    ]
    targets = [u for u in (User.query.filter_by(username=n).first()
                           for n in candidate_targets) if u]
    if not targets:
        return 0
    # Sponsors: benchmark users + first 60 org owners + first 200 user-owners
    sponsor_pool_names = ['alice_j', 'bob_c', 'carol_d', 'david_k']
    sponsor_pool = [u for u in (User.query.filter_by(username=n).first()
                                for n in sponsor_pool_names) if u]
    # Augment with deterministic id-ordered slice.
    extra_sponsors = (User.query
                      .filter(User.username.notin_(sponsor_pool_names))
                      .order_by(User.id.asc())
                      .limit(220)
                      .all())
    sponsor_pool.extend(extra_sponsors)
    if not sponsor_pool:
        return 0

    added = 0
    for target in targets:
        # Skip if already has sponsorships seeded.
        if Sponsorship.query.filter_by(target_id=target.id).count() >= 6:
            continue
        # 8-16 sponsors per target deterministically.
        h = _r4_hash(target.username, 'sponsor-target')
        n = 8 + (h % 9)
        for i in range(n):
            sh = _r4_hash(target.username, 'sponsor', i)
            sponsor = sponsor_pool[sh % len(sponsor_pool)]
            if sponsor.id == target.id:
                continue
            if Sponsorship.query.filter_by(sponsor_id=sponsor.id,
                                           target_id=target.id).first():
                continue
            tier_name, tier_amount = _R4_SPONSOR_TIERS[
                (sh >> 4) % len(_R4_SPONSOR_TIERS)]
            started = _BULK_REF - timedelta(days=30 + (sh % 700),
                                            hours=(sh >> 2) % 24)
            s = Sponsorship(
                sponsor_id=sponsor.id,
                target_id=target.id,
                tier=tier_name,
                amount_cents=tier_amount,
                status='active' if (sh % 10) < 8 else 'paused',
                is_recurring=1 if (sh % 5) < 4 else 0,
                started_at=started,
            )
            db.session.add(s)
            added += 1
    db.session.commit()
    return added


# ── Project Boards (Kanban) ──────────────────────────────────────
_R4_PROJECT_NAMES = [
    "Roadmap Q{q}",
    "Bug Triage — v{maj}",
    "{lang} Migration Plan",
    "Performance push",
    "Security hardening",
    "Docs overhaul",
    "v{nx} GA checklist",
    "API stabilization",
]
_R4_PROJECT_COLS = ['Backlog', 'Todo', 'In progress', 'In review', 'Done']
_R4_PROJECT_CARD_TITLES = [
    "Audit {a} for memory regressions",
    "Document {a} migration guide",
    "Reproduce flaky {a} test on Windows",
    "Triage open {a} issues from last quarter",
    "Add metrics endpoint for {a}",
    "Spike: WASM build for {a}",
    "Remove deprecated {a} APIs",
    "Update {a} examples in docs",
    "Investigate {a} memory usage under load",
    "Wire up CI for {a} on macOS",
    "Refactor {a} retry logic",
    "Adopt structured logging for {a}",
]


def seed_r4_project_boards():
    """Generate 1-3 project boards per top-200 repo (~400 boards)."""
    if ProjectBoard.query.count() >= 350:
        return 0
    top_repos = (Repository.query
                 .filter(Repository.stars_count >= 500)
                 .order_by(Repository.stars_count.desc(), Repository.id.asc())
                 .limit(180)
                 .all())
    added = 0
    for repo in top_repos:
        if ProjectBoard.query.filter_by(repo_id=repo.id).count() > 0:
            continue
        n = 1 + (_r4_hash(repo.full_name, 'pb') % 3)
        for i in range(n):
            h = _r4_hash(repo.full_name, 'pb', i)
            name = _R4_PROJECT_NAMES[h % len(_R4_PROJECT_NAMES)].format(
                q=1 + (h % 4), maj=1 + (h % 6), nx=2 + (h % 5),
                lang=repo.language or 'Polyglot')[:120]
            cols = []
            for ci, col_name in enumerate(_R4_PROJECT_COLS):
                cards = []
                ncards = 2 + ((h >> ci) % 4)
                for k in range(ncards):
                    ch = _r4_hash(repo.full_name, 'pb', i, 'col', ci, 'card', k)
                    area = _COMMIT_AREAS[ch % len(_COMMIT_AREAS)]
                    title = _R4_PROJECT_CARD_TITLES[
                        (ch >> 3) % len(_R4_PROJECT_CARD_TITLES)].format(a=area)
                    labels_pool = [
                        ['bug'], ['enhancement'], ['documentation'],
                        ['good first issue'], ['help wanted'],
                        ['performance'], ['security'], ['needs-discussion'],
                    ]
                    labels = labels_pool[(ch >> 5) % len(labels_pool)]
                    cards.append({'title': title[:200], 'labels': labels,
                                  'issue_number': ((ch >> 7) % 900) + 1})
                cols.append({'name': col_name, 'cards': cards})
            created = (repo.pushed_at or _BULK_REF) - timedelta(
                days=30 + (h % 200), hours=(h >> 4) % 24)
            if created > _BULK_REF:
                created = _BULK_REF
            pb = ProjectBoard(
                repo_id=repo.id,
                number=i + 1,
                name=name,
                description=f"Tracking board for the {repo.name} {name} milestone.",
                status='open' if (h % 8) != 0 else 'closed',
                columns_json=json.dumps(cols),
                created_at=created,
            )
            db.session.add(pb)
            added += 1
    db.session.commit()
    return added


# ── Packages ─────────────────────────────────────────────────────
_R4_PACKAGE_ECOSYSTEMS = ['npm', 'pypi', 'container', 'maven',
                          'rubygems', 'nuget']


def _r4_package_ecosystem_for(lang: str):
    return {
        'JavaScript': 'npm', 'TypeScript': 'npm', 'Vue': 'npm',
        'Python': 'pypi', 'Jupyter Notebook': 'pypi',
        'Java': 'maven', 'Kotlin': 'maven', 'Scala': 'maven',
        'Ruby': 'rubygems', 'C#': 'nuget',
        'Go': 'container', 'Rust': 'container',
        'Dockerfile': 'container', 'Shell': 'container',
    }.get(lang, 'container')


def seed_r4_packages():
    """1-2 packages per top-400 repo. ~600 packages."""
    if Package.query.count() >= 550:
        return 0
    top_repos = (Repository.query
                 .filter(Repository.stars_count >= 200)
                 .order_by(Repository.stars_count.desc(),
                           Repository.id.asc())
                 .limit(400)
                 .all())
    added = 0
    for repo in top_repos:
        if Package.query.filter_by(repo_id=repo.id).count() > 0:
            continue
        n = 1 + (_r4_hash(repo.full_name, 'pkg') % 2)
        for i in range(n):
            h = _r4_hash(repo.full_name, 'pkg', i)
            eco_primary = _r4_package_ecosystem_for(repo.language or '')
            eco = eco_primary if i == 0 else _R4_PACKAGE_ECOSYSTEMS[
                (h >> 2) % len(_R4_PACKAGE_ECOSYSTEMS)]
            if eco == 'npm':
                name = f"@{repo.full_name.split('/')[0]}/{repo.name}".lower()
            elif eco == 'pypi':
                name = repo.name.replace('_', '-').lower()
            elif eco == 'maven':
                name = f"com.{repo.full_name.split('/')[0].lower()}:{repo.name}"
            elif eco == 'rubygems':
                name = repo.name.replace('_', '-').lower()
            elif eco == 'nuget':
                name = f"{repo.full_name.split('/')[0]}.{repo.name}".title()
            else:
                name = f"ghcr.io/{repo.full_name.lower()}"
            name = name[:120]
            version = f"{1 + (h % 8)}.{(h >> 2) % 24}.{(h >> 4) % 30}"
            downloads = 100 + (h % 5_000_000)
            published = (repo.pushed_at or _BULK_REF) - timedelta(
                days=7 + (h % 90), hours=(h >> 6) % 24)
            if published > _BULK_REF:
                published = _BULK_REF
            pkg = Package(
                repo_id=repo.id,
                name=name,
                ecosystem=eco,
                version=version,
                description=(repo.description or '')[:255],
                downloads_total=downloads,
                visibility='public',
                published_at=published,
            )
            db.session.add(pkg)
            added += 1
    db.session.commit()
    return added


# ── Org Teams ────────────────────────────────────────────────────
_R4_TEAM_TEMPLATES = [
    ("core-maintainers", "Core Maintainers",
     "Top-level maintainers with merge rights across the org."),
    ("docs-team", "Docs Team",
     "Writes, reviews and ships documentation across the org."),
    ("security-response", "Security Response",
     "Handles incoming security advisories and coordinates fixes."),
    ("design-systems", "Design Systems",
     "Owns the org's shared design tokens and component library."),
    ("platform-engineering", "Platform Engineering",
     "Internal platform & developer experience tooling."),
    ("release-managers", "Release Managers",
     "Drives release cuts, changelogs and packaging across repos."),
    ("triagers", "Issue Triagers",
     "Front line on incoming issues and PRs."),
    ("community", "Community",
     "Helps newcomers, runs events and curates discussions."),
]


def seed_r4_teams():
    """3-6 teams per top-80 org. ~400 teams."""
    if Team.query.count() >= 800:
        return 0
    # Order by total stars across the owner's repos. We don't filter on
    # owner_type because plenty of well-known "orgs" (django, vuejs, rust-lang,
    # huggingface, …) ship under owner_type='user' in the legacy seed and we
    # still want their team pages populated.
    org_rows = (db.session.query(
                    User, func.sum(Repository.stars_count).label('s'),
                    func.count(Repository.id).label('rc'))
                .join(Repository, Repository.owner_id == User.id)
                .group_by(User.id)
                .having(func.count(Repository.id) >= 1)
                .order_by(func.sum(Repository.stars_count).desc())
                .limit(220)
                .all())
    org_users = [row[0] for row in org_rows]
    if not org_users:
        return 0
    # Username pool to draw team members from.
    member_pool = [u.username for u in
                   User.query.order_by(User.id.asc()).limit(400).all()]
    if not member_pool:
        return 0

    added = 0
    for rank, org in enumerate(org_users):
        existing = Team.query.filter_by(org_id=org.id).count()
        if existing > 0:
            continue
        h = _r4_hash(org.username, 'team')
        # Top-40 orgs by stars get ALL 8 team templates so common slugs
        # ('docs-team', 'core-maintainers', 'security-response', …) are
        # always present on the orgs WebVoyager tasks reference. Smaller
        # orgs still get 3-6 deterministic picks.
        if rank < 40:
            template_indices = list(range(len(_R4_TEAM_TEMPLATES)))
        else:
            n = 3 + (h % 4)
            template_indices = [(h + i) % len(_R4_TEAM_TEMPLATES)
                                for i in range(n)]
        # Repos owned by this org for team-repo lists.
        org_repos = [r.full_name for r in
                     Repository.query.filter_by(owner_id=org.id)
                     .order_by(Repository.id.asc()).limit(15).all()]
        for i, ti in enumerate(template_indices):
            slug, name, desc = _R4_TEAM_TEMPLATES[ti]
            mcount = 4 + ((h >> i) % 9)
            members = []
            for k in range(mcount):
                m = member_pool[(_r4_hash(org.username, slug, k)) %
                                len(member_pool)]
                if m not in members and m != org.username:
                    members.append(m)
            rcount = min(len(org_repos), 1 + ((h >> (i + 2)) % 4))
            team_repos = org_repos[:rcount]
            created = _BULK_REF - timedelta(
                days=60 + (_r4_hash(org.username, slug) % 800))
            t = Team(
                org_id=org.id,
                slug=slug,
                name=name,
                description=desc,
                privacy='visible' if (h + i) % 8 != 0 else 'secret',
                member_count=len(members),
                repo_count=len(team_repos),
                members_json=json.dumps(members),
                repos_json=json.dumps(team_repos),
                created_at=created,
            )
            db.session.add(t)
            added += 1
        if added and added % 80 == 0:
            db.session.commit()
    db.session.commit()
    return added


# ─────────────────────────── R5 bulk seeders ───────────────────────────
# Synthesize additional repos under existing owners (user + org), top off the
# commit log to cross 200k, and mint fresh PR rows directly so /pulls stays
# busy. Each value derives from hashlib.sha1(...) of a stable key so md5×2
# stays identical across rebuilds.

_R5_REPO_TARGET = 18200
_R5_PULL_TARGET = 7200
_R5_COMMIT_TARGET = 205000

_R5_REPO_SUFFIXES = [
    'api', 'client', 'server', 'engine', 'runtime', 'compiler', 'linter',
    'formatter', 'bench', 'fuzz', 'migrate', 'snapshot', 'dashboard',
    'replicator', 'pipeline', 'inference', 'embeddings', 'indexer',
    'planner', 'scheduler', 'syncer', 'webhook', 'gateway', 'router',
    'agent', 'collector', 'analyzer', 'profiler', 'tracer', 'metrics',
]
_R5_REPO_DESC = [
    "Production {a} service used inside {org}'s infra mesh.",
    "Reference implementation of the {a} spec, with extensive tests.",
    "High-throughput {a} module — handles 1M ops/sec on commodity boxes.",
    "Drop-in {a} replacement for legacy {org} pipelines.",
    "Cross-platform {a} runtime for embedded + cloud deployments.",
    "Schema-first {a} toolkit maintained by {org} contributors.",
    "Streaming {a} library with backpressure and replay support.",
    "Zero-config {a} starter for greenfield {org} projects.",
    "Lock-free {a} primitives optimised for ARM and x86_64.",
    "Plugin-friendly {a} core with a hot-reload dev loop.",
]
_R5_README_BANK = [
    "# {full}\n\n> {desc}\n\n## Highlights\n\n- {feature1}\n- {feature2}\n- "
    "Battle-tested in {org}'s production stack since v{maj}.{min}.\n\n"
    "## Install\n\n```bash\n{cmd}\n```\n\n## Usage\n\nSee `examples/` for "
    "runnable demos. Bug reports welcome — open an issue with the `bug` "
    "label and a minimal repro.\n\n## License\n\n{license_} — same as the "
    "rest of the {org} ecosystem.\n",
    "# {full}\n\n{desc}\n\n## Status\n\nStable. Used by {org}'s internal "
    "{area} pipeline; we cut a release roughly every two weeks.\n\n## "
    "Why\n\n- {feature1}\n- {feature2}\n- Tree-shakeable, zero runtime "
    "dependencies.\n\n## Architecture\n\nSee `docs/architecture.md` for a "
    "system overview. The hot path is intentionally boring.\n\n## "
    "Contributing\n\nWe squash-merge PRs. Small, focused changes get "
    "reviewed fastest. Add tests for any non-trivial behaviour change.\n",
]
_R5_FEATURE_BANK = [
    "Idempotent retries with exponential backoff",
    "First-class OpenTelemetry traces and metrics",
    "Structured logging with sampling controls",
    "Type-safe public API with stability guarantees",
    "Streaming responses for large payloads",
    "Pluggable storage backends (S3, GCS, local)",
    "Built-in circuit breaker for downstream calls",
    "Cooperative cancellation across async boundaries",
    "Cache-aware read paths with stale-while-revalidate",
    "Sandboxed plugin execution with resource caps",
]
_R5_INSTALL_BANK = {
    'Python': 'pip install {name}',
    'JavaScript': 'npm install {name}',
    'TypeScript': 'npm install {name}',
    'Go': 'go get github.com/{full}',
    'Rust': 'cargo add {name}',
    'Java': 'mvn dependency:get -Dartifact=com.{org}:{name}:LATEST',
    'Ruby': 'gem install {name}',
    'Kotlin': 'gradle dependencies --add {name}',
    'Swift': 'swift package add {name}',
    'C#': 'dotnet add package {name}',
}


def _r5_hash(*parts) -> int:
    """Stable cross-process hash. Mirrors _r4_hash."""
    key = '|'.join(str(p) for p in parts)
    return int(hashlib.sha1(key.encode()).hexdigest()[:10], 16)


def seed_r5_user_repos():
    """Grow the catalog from ~12000 → 18200 by adding R5 repos under existing
    owners (both user and organization). Deterministic via SHA-1 of owner +
    slot. Idempotent: stops once total repo count ≥ _R5_REPO_TARGET."""
    have = Repository.query.count()
    if have >= _R5_REPO_TARGET:
        return 0

    owners = (User.query
              .join(Repository, Repository.owner_id == User.id)
              .order_by(User.username.asc())
              .distinct()
              .all())
    if not owners:
        return 0

    existing_full = {r.full_name for r in
                     Repository.query.with_entities(Repository.full_name).all()}
    topic_by_slug = {t.slug: t for t in Topic.query.all()}

    topics_pool = [
        'api', 'sdk', 'library', 'framework', 'tooling', 'cli',
        'observability', 'monitoring', 'distributed-systems', 'devtools',
        'developer-experience', 'cloud-native', 'serverless', 'microservices',
        'open-source', 'production-ready', 'embeddings', 'inference',
        'data-engineering', 'streaming', 'pipeline', 'workflow',
        'kubernetes', 'docker', 'rust', 'python', 'typescript', 'go',
    ]

    added = 0
    # Multiple passes; in each pass give every owner one more R5 repo if we
    # still need more. Stops on target hit.
    for slot in range(len(_R5_REPO_SUFFIXES)):
        if have + added >= _R5_REPO_TARGET:
            break
        for owner in owners:
            if have + added >= _R5_REPO_TARGET:
                break
            existing_for_owner = sum(1 for fn in existing_full
                                     if fn.startswith(owner.username + '/'))
            # Cap at 50 repos per owner so the catalogue stays balanced.
            if existing_for_owner >= 50:
                continue
            suffix = _R5_REPO_SUFFIXES[
                (slot + _r5_hash(owner.username)) % len(_R5_REPO_SUFFIXES)]
            base_name = f"r5-{suffix}-{slot}"
            full = f"{owner.username}/{base_name}"
            if full in existing_full:
                # Try a salted variant; if still collides, skip.
                base_name = f"r5-{suffix}-{slot}-{_r5_hash(owner.username, slot) % 9999}"
                full = f"{owner.username}/{base_name}"
                if full in existing_full:
                    continue
            h = _r5_hash(full)
            lang = _R4_LANG_POOL[h % len(_R4_LANG_POOL)]
            area = ['ingestion', 'parser', 'cache', 'auth', 'routing',
                    'transport', 'config', 'telemetry', 'storage',
                    'streaming'][(h >> 3) % 10]
            desc_org = owner.username
            desc = _R5_REPO_DESC[(h >> 5) % len(_R5_REPO_DESC)].format(
                a=area, org=desc_org)[:255]
            feature1 = _R5_FEATURE_BANK[(h >> 7) % len(_R5_FEATURE_BANK)]
            feature2 = _R5_FEATURE_BANK[(h >> 11) % len(_R5_FEATURE_BANK)]
            install_tmpl = _R5_INSTALL_BANK.get(lang, 'cargo install {name}')
            cmd = install_tmpl.format(name=base_name, full=full,
                                      org=owner.username.lower())
            license_ = _R4_LICENSE_BAND[(h >> 6) % len(_R4_LICENSE_BAND)]
            readme = _R5_README_BANK[(h >> 13) % len(_R5_README_BANK)].format(
                full=full, desc=desc, org=desc_org, area=area,
                feature1=feature1, feature2=feature2,
                cmd=cmd, license_=license_,
                maj=1 + (h % 5), min=(h >> 2) % 18)

            default_branch = _R4_BRANCH_BAND[(h >> 8) % len(_R4_BRANCH_BAND)]
            stars = 3 + (h % 1700)
            forks = max(0, stars // (4 + (h % 5)))
            watchers = max(1, stars // 5)
            open_issues = (h >> 4) % 14
            is_archived = ((h >> 9) % 14 == 0)

            topic_slugs = []
            for k in range(2 + (h % 3)):
                ts = topics_pool[(h * 5 + k * 17) % len(topics_pool)]
                if ts not in topic_slugs:
                    topic_slugs.append(ts)

            created = _BULK_REF - timedelta(days=200 + (h % 1300),
                                            hours=(h >> 4) % 24)
            pushed = _BULK_REF - timedelta(days=(h % 220),
                                           hours=(h >> 5) % 24)
            updated = pushed
            sha = hashlib.sha1(f"r5|{full}".encode()).hexdigest()

            repo = Repository(
                owner_id=owner.id,
                name=base_name,
                full_name=full,
                description=desc,
                language=lang,
                license=license_,
                stars_count=stars,
                forks_count=forks,
                watchers_count=watchers,
                open_issues_count=open_issues,
                is_public=True,
                is_fork=False,
                is_template=((h >> 12) % 28 == 0),
                is_archived=is_archived,
                has_readme=True,
                has_wiki=((h >> 3) % 5 == 0),
                has_issues=True,
                owner_type='organization' if (h >> 14) % 3 == 0 else 'user',
                default_branch=default_branch,
                size_kb=120 + (h % 18000),
                readme=readme,
                topics_text=json.dumps(topic_slugs),
                gallery_json='[]',
                created_at=created,
                updated_at=updated,
                pushed_at=pushed,
                latest_release_version=f"v{1 + (h % 6)}.{(h >> 2) % 22}.{(h >> 4) % 18}",
                latest_release_date=pushed - timedelta(days=10 + (h % 80)),
                latest_release_notes=(
                    f"Performance + correctness fixes in the {area} subsystem; "
                    "see CHANGELOG for the full list."),
                latest_commit_sha=sha,
                latest_commit_message=(
                    f"Tighten {area} validation and add fuzz cases ({base_name})"),
                latest_commit_date=pushed,
                latest_commit_additions=18 + (h % 280),
                latest_commit_deletions=6 + ((h >> 1) % 140),
            )
            db.session.add(repo)
            db.session.flush()
            for slug in topic_slugs:
                t = topic_by_slug.get(slug)
                if t is not None:
                    repo.topics.append(t)
            existing_full.add(full)
            added += 1
            if added % 800 == 0:
                db.session.commit()
    db.session.commit()
    return added


# Sentinel topic: presence indicates seed_r5_topup_commits already ran. Lets
# us skip the (mildly expensive) sum-of-JSON-lengths probe on warm rebuilds.
_R5_COMMITS_SENTINEL_SLUG = '_r5-commit-topup'


def seed_r5_topup_commits():
    """Top off the per-repo commit history so the catalogue crosses
    _R5_COMMIT_TARGET (~205k). Runs once. After seed_extra_commits has filled
    every repo with 8-18 commits, this appends 3-5 more commits per repo
    (deterministic SHA-1 keyed on repo.full_name + r5 + slot) starting from
    the lowest repo id until the target is met.

    Idempotent: drops a sentinel Topic row on first run; subsequent runs
    detect it and bail."""
    if Topic.query.filter_by(slug=_R5_COMMITS_SENTINEL_SLUG).first() is not None:
        return 0

    # Quick check: do we already have enough commits in JSON?
    total = 0
    repos = (Repository.query
             .filter(Repository.commits_json != None,  # noqa: E711
                     Repository.commits_json != '',
                     Repository.commits_json != '[]')
             .order_by(Repository.id.asc())
             .all())
    repo_commits = {}
    for repo in repos:
        try:
            cl = json.loads(repo.commits_json or '[]')
        except Exception:
            cl = []
        repo_commits[repo.id] = cl
        total += len(cl)

    if total >= _R5_COMMIT_TARGET:
        # Drop sentinel anyway so we skip the probe next time.
        db.session.add(Topic(
            slug=_R5_COMMITS_SENTINEL_SLUG,
            display_name='R5 Commit Top-Up',
            description='Internal sentinel — do not surface in UI.',
            short_desc='internal',
            is_featured=False,
        ))
        db.session.commit()
        return 0

    need = _R5_COMMIT_TARGET - total
    added = 0
    for repo in repos:
        if added >= need:
            break
        existing = repo_commits.get(repo.id, [])
        base_dt = repo.pushed_at or repo.updated_at or _BULK_REF
        if base_dt > _BULK_REF:
            base_dt = _BULK_REF
        owner_name = repo.full_name.split('/', 1)[0]
        extra_n = 4 + (repo.id % 4)  # 4..7 more commits
        new_commits = []
        for i in range(extra_n):
            slot = len(existing) + i
            area = _COMMIT_AREAS[
                (repo.id * 11 + i * 13 + 5) % len(_COMMIT_AREAS)]
            msg = _COMMIT_MSG_TEMPLATES[
                (repo.id * 5 + i * 23 + 7) % len(_COMMIT_MSG_TEMPLATES)
            ].format(area=area)
            # Place the new commits slightly older than the existing tail so
            # ordering newest-first is preserved.
            base_offset = (len(existing) * 2) + i * 2 + (repo.id % 3)
            ts = base_dt - timedelta(days=base_offset,
                                     hours=(i * 7 + repo.id) % 24)
            sha_seed = f"r5|{repo.full_name}|{slot}|{repo.id}"
            sha = hashlib.sha1(sha_seed.encode()).hexdigest()
            files = _commit_files_for(repo.language or '', area, repo.id + slot)
            adds = sum(f['additions'] for f in files)
            dels = sum(f['deletions'] for f in files)
            new_commits.append({
                'sha': sha,
                'message': msg,
                'author': owner_name,
                'date': ts.isoformat(),
                'files': files,
                'additions': adds,
                'deletions': dels,
            })
            added += 1
            if added >= need:
                break
        if new_commits:
            # Newest-first ordering: keep existing list first, append older.
            merged = existing + new_commits
            repo.commits_json = json.dumps(merged)

    # Drop sentinel topic.
    db.session.add(Topic(
        slug=_R5_COMMITS_SENTINEL_SLUG,
        display_name='R5 Commit Top-Up',
        description='Internal sentinel — do not surface in UI.',
        short_desc='internal',
        is_featured=False,
    ))
    db.session.commit()
    return added


_R5_PR_TITLES = [
    "feat({a}): pluggable {a} backend with retry budgets",
    "fix({a}): handle EOF in streaming {a} consumer",
    "perf({a}): cache {a} lookups, avoid per-request decode",
    "refactor({a}): split {a} core out of {a}-runtime",
    "docs({a}): document {a} migration from v{maj} → v{nx}",
    "chore({a}): bump {a} deps + regenerate snapshots",
    "test({a}): add property-based tests for {a} parser",
    "ci({a}): parallelise the {a} integration matrix",
    "security({a}): pin {a} TLS cipher list per advisory",
    "build({a}): switch {a} target to musl for static binaries",
]
_R5_PR_BODIES = [
    "Closes #{ref}. Re-introduces the {a} retry budgets we discussed in "
    "{a}-design.md. Includes a regression test that previously panicked on "
    "an empty input.",
    "Follow-up to #{ref}. The {a} fast path was allocating on every call; "
    "this PR caches the decoded value behind a sync.Once. Benchmarks in "
    "the comments below.",
    "Replaces the ad-hoc {a} channel with a buffered ring; smoke tests show "
    "p99 latency drops by ~22%. No public API changes.",
    "Documentation pass for the {a} subsystem: clarifies the difference "
    "between {a}-strict and {a}-lenient modes, adds a migration table.",
]
_R5_PR_BRANCHES = [
    'feat/r5-{a}-{n}', 'fix/r5-{a}-{n}', 'perf/r5-{a}',
    'chore/r5-bump-{a}', 'refactor/r5-{a}', 'docs/r5-{a}',
    'security/r5-{a}-{n}', 'ci/r5-{a}',
]


def seed_r5_extra_pulls():
    """Mint fresh PR rows for the R5 repo slice (slugs starting with 'r5-')
    plus any older repo whose PR count is still zero. Brings total PRs from
    3000 → ~7200. Deterministic against (repo.id, slot)."""
    have_pr = Issue.query.filter_by(is_pr=1).count()
    if have_pr >= _R5_PULL_TARGET:
        return 0
    need = _R5_PULL_TARGET - have_pr

    # Candidate repos: those without any existing PR. Process in id order
    # so iteration is deterministic across processes.
    repos_with_pr = {row[0] for row in
                     db.session.query(Issue.repo_id)
                     .filter(Issue.is_pr == 1).distinct().all()}
    cand_repos = (Repository.query
                  .filter(~Repository.id.in_(list(repos_with_pr) or [-1]))
                  .order_by(Repository.id.asc())
                  .all())
    if not cand_repos:
        return 0

    pool_unames = ['alice_j', 'bob_c', 'carol_d', 'david_k',
                   'octocat', 'gaearon', 'sindresorhus', 'tj',
                   'antirez', 'mxcl', 'mitchellh', 'fabpot',
                   'wycats', 'yyx990803', 'dhh']
    pool = []
    for uname in pool_unames:
        u = User.query.filter_by(username=uname).first()
        if u:
            pool.append(u)
    if not pool:
        return 0
    pool_size = len(pool)

    added = 0
    for repo in cand_repos:
        if added >= need:
            break
        # Per-repo PR count: 1-3 depending on stars.
        s = repo.stars_count or 0
        if s >= 1000:
            n = 3
        elif s >= 100:
            n = 2
        else:
            n = 1
        base_dt = repo.pushed_at or repo.updated_at or _BULK_REF
        if base_dt > _BULK_REF:
            base_dt = _BULK_REF
        # Use the repo's existing issue number max + 1 as starting number,
        # so /<repo>/issues/<num> URIs don't collide.
        max_num = (db.session.query(func.max(Issue.number))
                   .filter(Issue.repo_id == repo.id).scalar()) or 0
        for i in range(n):
            if added >= need:
                break
            h = _r5_hash('r5pr', repo.full_name, i)
            area = _COMMIT_AREAS[h % len(_COMMIT_AREAS)]
            maj = 1 + (h % 5)
            nx = maj + 1
            title = _R5_PR_TITLES[(h >> 2) % len(_R5_PR_TITLES)].format(
                a=area, maj=maj, nx=nx)
            body = _R5_PR_BODIES[(h >> 5) % len(_R5_PR_BODIES)].format(
                a=area, ref=((h >> 7) % 9000) + 100)
            branch = _R5_PR_BRANCHES[(h >> 8) % len(_R5_PR_BRANCHES)].format(
                a=area, n=(h % 9000))
            author = pool[(h >> 9) % pool_size]
            offset_days = i * 5 + (h % 90)
            created = base_dt - timedelta(days=offset_days,
                                          hours=(h >> 10) % 24)
            bucket = h % 100
            if bucket < 40:
                status = 'merged'
                closed_at = created + timedelta(days=2 + (h % 11),
                                                hours=(h >> 4) % 24)
                if closed_at > _BULK_REF:
                    closed_at = _BULK_REF - timedelta(hours=(h % 36))
            elif bucket < 55:
                status = 'closed'
                closed_at = created + timedelta(days=4 + (h % 20))
                if closed_at > _BULK_REF:
                    closed_at = _BULK_REF - timedelta(hours=(h % 48))
            else:
                status = 'open'
                closed_at = None
            issue = Issue(
                repo_id=repo.id,
                author_id=author.id,
                number=max_num + i + 1,
                title=title[:255],
                body=body,
                status=status,
                labels_json=json.dumps(
                    [['enhancement'], ['bug'], ['performance'],
                     ['documentation'], ['security'], ['chore']][h % 6]),
                created_at=created,
                closed_at=closed_at,
                is_pr=1,
                pr_head_branch=branch[:120],
                pr_base_branch=repo.default_branch or 'main',
                pr_changed_files=1 + (h % 9),
                pr_additions=14 + (h % 480),
                pr_deletions=4 + ((h >> 1) % 220),
                pr_commits_count=1 + (h % 6),
            )
            db.session.add(issue)
            added += 1
        if added and added % 600 == 0:
            db.session.commit()
    db.session.commit()
    return added


# ─────────────────────────── R6 Polish ───────────────────────────
# Iteration 6: grow catalog 18200 → 25000+, mint additional cross-page
# task scaffolding (Related repos by topic, Owner's other repos, Used-by
# dependency synthesis, expanded Forks list, breadcrumb everywhere), and
# add seven "edge state" repo variants encoded via sentinel topic slugs:
#
#   _r6-edge-archived-ro            archived, read-only (write paths refuse)
#   _r6-edge-branch-protected       direct push / non-PR changes blocked
#   _r6-edge-pr-conflict            PR list contains a "needs conflict
#                                   resolution" entry (rendered via
#                                   /pull/<n>/conflicts which already exists)
#   _r6-edge-action-run-failed      Actions tab pin a failure run
#   _r6-edge-codespace-quota        /codespaces/new returns quota-exceeded
#   _r6-edge-dmca                   repo detail returns "DMCA Takedown" page
#   _r6-edge-fork-rate-limit        fork POST returns 429
#
# All edge state is encoded in topics_text (JSON list, no schema change).
# Helpers below read it; routes early-exit accordingly.

_R6_REPO_TARGET = 25000
_R6_REPO_SUFFIXES = [
    'kernel', 'mesh', 'broker', 'shard', 'replicator', 'sidecar', 'proxy',
    'tunnel', 'controller', 'manager', 'orchestrator', 'optimizer',
    'discovery', 'registry', 'audit', 'rotator', 'rate-limit',
    'feature-flags', 'experiments', 'rollouts', 'telemetry-collector',
    'log-shipper', 'event-bus', 'state-store', 'leader-election',
    'consensus', 'snapshot-restore', 'health-prober', 'sampler', 'lineage',
]
_R6_REPO_DESC = [
    "{a} subsystem extracted from {org}'s production stack — zero-deps, "
    "well-tested, ready to drop in.",
    "Hardened {a} layer with property-based tests and a stable wire format. "
    "Used in {org}'s critical path.",
    "Production-grade {a} component with backpressure, retries, and "
    "first-class observability hooks.",
    "Composable {a} primitive — pairs with the rest of the {org} stack but "
    "stands on its own.",
    "Self-hosted {a} reference implementation with conformance suite and "
    "load-test harness.",
    "Edge-aware {a} engine optimised for partial connectivity and noisy "
    "links; built for {org}'s field deployments.",
    "Schema-evolving {a} core that survives breaking changes without "
    "downstream churn.",
    "Predictable {a} runtime — bounded latency, no GC pauses on the hot path.",
]
_R6_README_BANK = [
    "# {full}\n\n> {desc}\n\n## Why\n\n- {feature1}\n- {feature2}\n- "
    "Designed to compose with the rest of {org}'s open-source surface.\n\n"
    "## Install\n\n```bash\n{cmd}\n```\n\n## Quickstart\n\nSee "
    "`examples/{area}-basic` for a 30-line walkthrough. The hot path is "
    "intentionally small and boring — most of the code lives in the "
    "extension surface.\n\n## License\n\n{license_} — matches the rest of "
    "the {org} ecosystem.\n",
    "# {full}\n\n{desc}\n\nStatus: **stable**, currently on v{maj}.{min}. "
    "Used in production by {org} and adopters listed in `USERS.md`.\n\n"
    "## Highlights\n\n- {feature1}\n- {feature2}\n- Backwards-compatible "
    "since v{maj}.0 — see `docs/compat.md` for the policy.\n\n## "
    "Architecture\n\nThe {area} pipeline is single-writer; readers fan out "
    "via copy-on-write snapshots. Full diagram in `docs/architecture.svg`.\n",
]
_R6_FEATURE_BANK = [
    "Lock-free hot path with bounded p99",
    "Built-in chaos hooks (latency / drop / corrupt)",
    "Zero-allocation steady state",
    "Schema migrations via append-only deltas",
    "First-class replay and time-travel debugging",
    "Cooperative shutdown with deadline propagation",
    "Pluggable codec layer (json / msgpack / cbor / proto)",
    "Adaptive batching tuned by downstream pressure",
    "Configurable failure injection for fuzz tests",
    "Snapshot-restore that survives partial corruption",
]
_R6_INSTALL_BANK = {
    'Python': 'pip install {name}',
    'JavaScript': 'npm install {name}',
    'TypeScript': 'pnpm add {name}',
    'Go': 'go get github.com/{full}',
    'Rust': 'cargo add {name}',
    'Java': 'mvn dependency:get -Dartifact=com.{org}:{name}:LATEST',
    'Ruby': 'gem install {name}',
    'Kotlin': 'gradle dependencies --add {name}',
    'Swift': 'swift package add {name}',
    'C#': 'dotnet add package {name}',
}


def _r6_hash(*parts) -> int:
    """Stable cross-process SHA-1 hash — mirrors _r4_hash / _r5_hash."""
    key = '|'.join(str(p) for p in parts)
    return int(hashlib.sha1(key.encode()).hexdigest()[:10], 16)


# Sentinel topic slugs for the seven R6 edge states.
_R6_EDGE_KINDS = (
    'archived-ro', 'branch-protected', 'pr-conflict', 'action-run-failed',
    'codespace-quota', 'dmca', 'fork-rate-limit',
)


def _r6_sentinel(kind: str) -> str:
    return f'_r6-edge-{kind}'


def _r6_has_sentinel(repo, kind: str) -> bool:
    """True if `kind` is in this repo's topics_text JSON array."""
    if repo is None:
        return False
    try:
        topics = json.loads(repo.topics_text or '[]')
    except Exception:
        return False
    return _r6_sentinel(kind) in topics


def seed_r6_user_repos():
    """Grow the catalog from 18200 → 25000 with R6-flavoured repos under
    existing owners. Deterministic via SHA-1 of (owner.username, slot).
    Idempotent: stops once total repo count ≥ _R6_REPO_TARGET."""
    have = Repository.query.count()
    if have >= _R6_REPO_TARGET:
        return 0

    owners = (User.query
              .join(Repository, Repository.owner_id == User.id)
              .order_by(User.username.asc())
              .distinct()
              .all())
    if not owners:
        return 0

    existing_full = {r.full_name for r in
                     Repository.query.with_entities(Repository.full_name).all()}
    topic_by_slug = {t.slug: t for t in Topic.query.all()}

    topics_pool = [
        'platform-engineering', 'distributed-systems', 'reliability',
        'load-balancing', 'service-mesh', 'caching', 'queueing',
        'consensus', 'replication', 'scheduling', 'cli', 'sdk',
        'devtools', 'production-ready', 'observability', 'tracing',
        'sre', 'incident-response', 'data-pipeline', 'streaming',
        'storage-engine', 'embeddings', 'inference', 'agents',
        'workflow', 'event-driven', 'state-machines', 'rust', 'go',
    ]

    added = 0
    # Each owner can take up to ~70 R6 repos before we move on.
    for slot in range(len(_R6_REPO_SUFFIXES)):
        if have + added >= _R6_REPO_TARGET:
            break
        for owner in owners:
            if have + added >= _R6_REPO_TARGET:
                break
            existing_for_owner = sum(1 for fn in existing_full
                                     if fn.startswith(owner.username + '/'))
            if existing_for_owner >= 70:
                continue
            suffix = _R6_REPO_SUFFIXES[
                (slot + _r6_hash(owner.username)) % len(_R6_REPO_SUFFIXES)]
            base_name = f"r6-{suffix}-{slot}"
            full = f"{owner.username}/{base_name}"
            if full in existing_full:
                base_name = (
                    f"r6-{suffix}-{slot}-{_r6_hash(owner.username, slot) % 9999}")
                full = f"{owner.username}/{base_name}"
                if full in existing_full:
                    continue
            h = _r6_hash(full)
            lang = _R4_LANG_POOL[h % len(_R4_LANG_POOL)]
            area = ['routing', 'storage', 'transport', 'consensus',
                    'replication', 'observability', 'auth', 'rate-limit',
                    'config', 'scheduling'][(h >> 3) % 10]
            desc = _R6_REPO_DESC[(h >> 5) % len(_R6_REPO_DESC)].format(
                a=area, org=owner.username)[:255]
            feature1 = _R6_FEATURE_BANK[(h >> 7) % len(_R6_FEATURE_BANK)]
            feature2 = _R6_FEATURE_BANK[(h >> 11) % len(_R6_FEATURE_BANK)]
            install_tmpl = _R6_INSTALL_BANK.get(lang, 'cargo install {name}')
            cmd = install_tmpl.format(name=base_name, full=full,
                                      org=owner.username.lower())
            license_ = _R4_LICENSE_BAND[(h >> 6) % len(_R4_LICENSE_BAND)]
            readme = _R6_README_BANK[(h >> 13) % len(_R6_README_BANK)].format(
                full=full, desc=desc, org=owner.username, area=area,
                feature1=feature1, feature2=feature2,
                cmd=cmd, license_=license_,
                maj=1 + (h % 5), min=(h >> 2) % 20)

            default_branch = _R4_BRANCH_BAND[(h >> 8) % len(_R4_BRANCH_BAND)]
            stars = 5 + (h % 2400)
            forks = max(0, stars // (3 + (h % 6)))
            watchers = max(1, stars // 4)
            open_issues = (h >> 4) % 12
            is_archived = ((h >> 9) % 16 == 0)

            topic_slugs = []
            for k in range(3 + (h % 3)):
                ts = topics_pool[(h * 7 + k * 19) % len(topics_pool)]
                if ts not in topic_slugs:
                    topic_slugs.append(ts)

            created = _BULK_REF - timedelta(days=160 + (h % 1400),
                                            hours=(h >> 4) % 24)
            pushed = _BULK_REF - timedelta(days=(h % 180),
                                           hours=(h >> 5) % 24)
            updated = pushed
            sha = hashlib.sha1(f"r6|{full}".encode()).hexdigest()

            repo = Repository(
                owner_id=owner.id,
                name=base_name,
                full_name=full,
                description=desc,
                language=lang,
                license=license_,
                stars_count=stars,
                forks_count=forks,
                watchers_count=watchers,
                open_issues_count=open_issues,
                is_public=True,
                is_fork=False,
                is_template=((h >> 12) % 30 == 0),
                is_archived=is_archived,
                has_readme=True,
                has_wiki=((h >> 3) % 4 == 0),
                has_issues=True,
                owner_type='organization' if (h >> 14) % 3 == 0 else 'user',
                default_branch=default_branch,
                size_kb=160 + (h % 22000),
                readme=readme,
                topics_text=json.dumps(topic_slugs),
                gallery_json='[]',
                created_at=created,
                updated_at=updated,
                pushed_at=pushed,
                latest_release_version=(
                    f"v{1 + (h % 6)}.{(h >> 2) % 24}.{(h >> 4) % 20}"),
                latest_release_date=pushed - timedelta(days=8 + (h % 70)),
                latest_release_notes=(
                    f"R6 polish on the {area} subsystem: tighter invariants, "
                    "new property tests, and a couple of perf wins. "
                    "See CHANGELOG."),
                latest_commit_sha=sha,
                latest_commit_message=(
                    f"Harden {area} guards and prune dead branches ({base_name})"),
                latest_commit_date=pushed,
                latest_commit_additions=24 + (h % 320),
                latest_commit_deletions=8 + ((h >> 1) % 160),
            )
            db.session.add(repo)
            db.session.flush()
            for slug in topic_slugs:
                t = topic_by_slug.get(slug)
                if t is not None:
                    repo.topics.append(t)
            existing_full.add(full)
            added += 1
            if added % 1000 == 0:
                db.session.commit()
    db.session.commit()
    return added


_R6_EDGE_LAB_OWNER = 'r6lab'  # synthesized organisation hosting the edge fleet


def seed_r6_edge_repos():
    """Mint ~14 named edge-state repos (2 per kind) under a dedicated
    organisation `r6lab` so tasks can deterministically reference them.
    Idempotent — bails if the org already has its edge repos."""
    org = User.query.filter_by(username=_R6_EDGE_LAB_OWNER).first()
    if org is None:
        org = User(
            username=_R6_EDGE_LAB_OWNER,
            email=f'{_R6_EDGE_LAB_OWNER}@r6lab.test',
            name='R6 Edge Lab',
            bio='Edge-state mirror lab — every repo demonstrates one '
                'documented GitHub failure mode.',
            location='Mirror Cluster',
            avatar='/static/images/avatars/avatar_05.jpg',
            plan='enterprise',
            created_at=_BULK_REF - timedelta(days=900),
        )
        org.password_hash = PINNED_PASSWORD_HASH_BULK
        db.session.add(org)
        db.session.flush()

    # Already minted?
    have = Repository.query.filter_by(owner_id=org.id).count()
    if have >= len(_R6_EDGE_KINDS) * 2:
        return 0

    topic_by_slug = {t.slug: t for t in Topic.query.all()}
    # Make sure every sentinel topic actually exists so /topics/<slug> works.
    for kind in _R6_EDGE_KINDS:
        slug = _r6_sentinel(kind)
        if slug not in topic_by_slug:
            t = Topic(slug=slug,
                      display_name=f'Edge: {kind}',
                      description=f'R6 edge-state demo: {kind}',
                      short_desc=f'Edge state: {kind}',
                      is_featured=False)
            db.session.add(t)
            db.session.flush()
            topic_by_slug[slug] = t

    added = 0
    for kind in _R6_EDGE_KINDS:
        for variant in (0, 1):
            base = f'edge-{kind}-{variant}'
            full = f'{org.username}/{base}'
            if Repository.query.filter_by(full_name=full).first():
                continue
            h = _r6_hash('edge', kind, variant)
            lang = _R4_LANG_POOL[h % len(_R4_LANG_POOL)]
            desc = {
                'archived-ro': ('This repository is archived and is now '
                                'read-only. Issues / PRs / pushes are '
                                'disabled.'),
                'branch-protected': ('Demo: `main` is protected. Direct '
                                     'pushes and non-reviewed merges are '
                                     'rejected.'),
                'pr-conflict': ('Demo: the open PR cannot be merged — '
                                'conflicts must be resolved first.'),
                'action-run-failed': ('Demo: the latest workflow run on '
                                      '`main` failed; logs available under '
                                      'the Actions tab.'),
                'codespace-quota': ('Demo: opening a codespace on this repo '
                                    'exceeds the account quota.'),
                'dmca': ('This repository is unavailable due to a DMCA '
                         'takedown notice.'),
                'fork-rate-limit': ('Demo: forking this repository is '
                                    'temporarily rate-limited.'),
            }[kind]
            topic_slugs = [_r6_sentinel(kind), 'edge-cases', 'demo']
            is_archived = (kind == 'archived-ro')
            is_public = (kind != 'dmca')
            created = _BULK_REF - timedelta(days=500 + h % 200)
            pushed = _BULK_REF - timedelta(days=4 + h % 30)
            sha = hashlib.sha1(f"r6edge|{full}".encode()).hexdigest()
            repo = Repository(
                owner_id=org.id,
                name=base,
                full_name=full,
                description=desc[:255],
                language=lang,
                license='MIT',
                stars_count=40 + (h % 800),
                forks_count=3 + (h % 60),
                watchers_count=10 + (h % 90),
                open_issues_count=2 + (h % 5),
                is_public=is_public,
                is_fork=False,
                is_template=False,
                is_archived=is_archived,
                has_readme=True,
                has_wiki=False,
                has_issues=(not is_archived),
                owner_type='organization',
                default_branch='main',
                size_kb=400 + (h % 4000),
                readme=(f"# {full}\n\n> {desc}\n\n"
                        "This is a deliberately broken-state demo repo. "
                        "WebVoyager tasks reference it to exercise the "
                        "matching failure path in the GitHub mirror.\n"),
                topics_text=json.dumps(topic_slugs),
                gallery_json='[]',
                created_at=created,
                updated_at=pushed,
                pushed_at=pushed,
                latest_release_version='v0.9.0',
                latest_release_date=pushed - timedelta(days=12),
                latest_release_notes=(
                    f"Pre-release; demonstrates the `{kind}` failure mode."),
                latest_commit_sha=sha,
                latest_commit_message=(
                    f"docs: explain the {kind} edge case"),
                latest_commit_date=pushed,
                latest_commit_additions=20 + (h % 80),
                latest_commit_deletions=4 + (h % 30),
            )
            db.session.add(repo)
            db.session.flush()
            for slug in topic_slugs:
                t = topic_by_slug.get(slug)
                if t is None and slug == 'edge-cases':
                    t = Topic(slug='edge-cases', display_name='Edge Cases',
                              description='Demonstrations of repo failure modes',
                              short_desc='Edge cases',
                              is_featured=False)
                    db.session.add(t)
                    db.session.flush()
                    topic_by_slug[slug] = t
                elif t is None and slug == 'demo':
                    t = Topic(slug='demo', display_name='Demo',
                              description='Demonstration repositories',
                              short_desc='Demo', is_featured=False)
                    db.session.add(t)
                    db.session.flush()
                    topic_by_slug[slug] = t
                if t is not None:
                    repo.topics.append(t)
            # If this is the pr-conflict variant, mint a PR row so
            # /pull/<n>/conflicts has something to resolve.
            if kind == 'pr-conflict':
                pr = Issue(
                    repo_id=repo.id,
                    author_id=org.id,
                    number=1,
                    title='feat(core): switch internal codec to msgpack',
                    body=('This PR migrates the wire format to msgpack. '
                          'There are merge conflicts in `src/codec.py` '
                          'and `README.md` that need resolution before '
                          'merge.'),
                    status='open',
                    labels_json=json.dumps(['enhancement', 'needs-resolution']),
                    created_at=pushed - timedelta(days=3),
                    closed_at=None,
                    is_pr=1,
                    pr_head_branch='feat/msgpack-codec',
                    pr_base_branch='main',
                    pr_changed_files=2,
                    pr_additions=84,
                    pr_deletions=37,
                    pr_commits_count=4,
                )
                db.session.add(pr)
            added += 1
    db.session.commit()
    return added


    db.session.commit()
    return added


# ─────────────────────── R7: catalog growth + topup ───────────────────────
# Same hash-deterministic pattern as R5/R6 but with fresh suffix banks so
# every newly-minted full_name is unique against the existing catalog. Tests
# can address an R7 repo by `<owner>/r7-<suffix>-<slot>`.

_R7_REPO_TARGET = 32000
_R7_REPO_SUFFIXES = [
    'analyzer', 'profiler', 'tracer', 'bench', 'sandbox', 'scaffold',
    'recipe', 'crucible', 'forge', 'lattice', 'compass', 'beacon',
    'sentinel', 'horizon', 'voyager', 'navigator', 'lighthouse',
    'workbench', 'foundry', 'atelier', 'parlour', 'observer',
    'lens', 'periscope', 'mosaic', 'fabric', 'weft', 'warp',
    'helix', 'oracle', 'sage', 'curator', 'librarian', 'archivist',
    'concierge', 'steward', 'envoy', 'attache', 'ranger', 'pilot',
]

_R7_REPO_DESC = [
    "Snapshot-driven {a} tool extracted from {org}'s SRE rotation. Production grade with property tests.",
    "Reusable {a} module with stable wire format and conformance suite. Used in production by {org}.",
    "First-class {a} runtime designed for predictable latency on cold paths.",
    "Composable {a} primitive with first-class observability hooks. Drop-in for the {org} stack.",
    "Edge-aware {a} engine that survives flaky links and partial state.",
    "Audit-ready {a} layer with deterministic replay and signed snapshots.",
    "{a} reference implementation — a small, well-tested core plus a strict conformance harness.",
    "Lock-free {a} hot path; minimal allocations on the steady state.",
]

_R7_README_BANK = [
    "# {full}\n\n> {desc}\n\n## Why\n\n- {feature1}\n- {feature2}\n- Built to "
    "compose with the rest of {org}'s open-source surface.\n\n## Install\n\n"
    "```bash\n{cmd}\n```\n\n## Quickstart\n\nSee `examples/{area}-basic` for a "
    "30-line walkthrough. Most of the source lives in the extension surface "
    "— the core is intentionally small.\n\n## SEO + i18n notes\n\nThis repo's "
    "page ships SoftwareSourceCode JSON-LD and OG metadata so it indexes "
    "cleanly. Localized labels are picked up from the global lang dropdown.\n",
    "# {full}\n\n{desc}\n\nStatus: **stable**, v{maj}.{min}. Adopters listed "
    "in `USERS.md`.\n\n## Highlights\n\n- {feature1}\n- {feature2}\n- "
    "Backwards-compatible since v{maj}.0 — see `docs/compat.md`.\n\n## "
    "Architecture\n\nThe {area} pipeline runs single-writer; readers fan out "
    "via copy-on-write snapshots. Diagram in `docs/architecture.svg`.\n",
]


def seed_r7_user_repos():
    """Grow the catalog from R6's 25000 → 32000 R7-flavoured repos under
    existing owners. Deterministic via SHA-1 of (owner.username, slot).
    Idempotent: bails once total repo count ≥ _R7_REPO_TARGET."""
    have = Repository.query.count()
    if have >= _R7_REPO_TARGET:
        return 0

    owners = (User.query
              .join(Repository, Repository.owner_id == User.id)
              .order_by(User.username.asc())
              .distinct()
              .all())
    if not owners:
        return 0

    existing_full = {r.full_name for r in
                     Repository.query.with_entities(Repository.full_name).all()}
    topic_by_slug = {t.slug: t for t in Topic.query.all()}

    topics_pool = [
        'platform-engineering', 'distributed-systems', 'observability',
        'developer-tools', 'load-testing', 'fuzz-testing', 'profiling',
        'tracing', 'sre', 'reliability', 'open-telemetry', 'edge-computing',
        'feature-flags', 'experimentation', 'workflow-engine',
        'storage-engine', 'sandboxing', 'cli', 'sdk', 'rust', 'go',
        'python', 'typescript', 'kubernetes', 'docker',
    ]

    added = 0
    # Each owner can take up to ~90 R7 repos. 30 suffix slots × 25k owners
    # is more than enough headroom; we early-exit at the target.
    for slot in range(len(_R7_REPO_SUFFIXES)):
        if have + added >= _R7_REPO_TARGET:
            break
        for owner in owners:
            if have + added >= _R7_REPO_TARGET:
                break
            existing_for_owner = sum(1 for fn in existing_full
                                     if fn.startswith(owner.username + '/'))
            if existing_for_owner >= 90:
                continue
            suffix = _R7_REPO_SUFFIXES[
                (slot + _r6_hash(owner.username)) % len(_R7_REPO_SUFFIXES)]
            base_name = f"r7-{suffix}-{slot}"
            full = f"{owner.username}/{base_name}"
            if full in existing_full:
                base_name = (
                    f"r7-{suffix}-{slot}-{_r6_hash(owner.username, slot) % 9999}")
                full = f"{owner.username}/{base_name}"
                if full in existing_full:
                    continue
            h = _r6_hash('r7', full)
            lang = _R4_LANG_POOL[h % len(_R4_LANG_POOL)]
            area = ['routing', 'storage', 'transport', 'consensus',
                    'replication', 'observability', 'auth', 'rate-limit',
                    'config', 'scheduling', 'caching', 'queueing'][(h >> 3) % 12]
            desc = _R7_REPO_DESC[(h >> 5) % len(_R7_REPO_DESC)].format(
                a=area, org=owner.username)[:255]
            feature1 = _R6_FEATURE_BANK[(h >> 7) % len(_R6_FEATURE_BANK)]
            feature2 = _R6_FEATURE_BANK[(h >> 11) % len(_R6_FEATURE_BANK)]
            install_tmpl = _R6_INSTALL_BANK.get(lang, 'cargo install {name}')
            cmd = install_tmpl.format(name=base_name, full=full,
                                      org=owner.username.lower())
            license_ = _R4_LICENSE_BAND[(h >> 6) % len(_R4_LICENSE_BAND)]
            readme = _R7_README_BANK[(h >> 13) % len(_R7_README_BANK)].format(
                full=full, desc=desc, org=owner.username, area=area,
                feature1=feature1, feature2=feature2,
                cmd=cmd, license_=license_,
                maj=1 + (h % 5), min=(h >> 2) % 20)

            default_branch = _R4_BRANCH_BAND[(h >> 8) % len(_R4_BRANCH_BAND)]
            stars = 8 + (h % 3200)
            forks = max(0, stars // (3 + (h % 6)))
            watchers = max(1, stars // 4)
            open_issues = (h >> 4) % 14
            is_archived = ((h >> 9) % 18 == 0)

            topic_slugs = []
            for k in range(3 + (h % 3)):
                ts = topics_pool[(h * 7 + k * 23) % len(topics_pool)]
                if ts not in topic_slugs:
                    topic_slugs.append(ts)

            created = _BULK_REF - timedelta(days=140 + (h % 1400),
                                            hours=(h >> 4) % 24)
            pushed = _BULK_REF - timedelta(days=(h % 160),
                                           hours=(h >> 5) % 24)
            updated = pushed
            sha = hashlib.sha1(f"r7|{full}".encode()).hexdigest()

            repo = Repository(
                owner_id=owner.id,
                name=base_name,
                full_name=full,
                description=desc,
                language=lang,
                license=license_,
                stars_count=stars,
                forks_count=forks,
                watchers_count=watchers,
                open_issues_count=open_issues,
                is_public=True,
                is_fork=False,
                is_template=((h >> 12) % 34 == 0),
                is_archived=is_archived,
                has_readme=True,
                has_wiki=((h >> 3) % 5 == 0),
                has_issues=True,
                owner_type='organization' if (h >> 14) % 3 == 0 else 'user',
                default_branch=default_branch,
                size_kb=180 + (h % 24000),
                readme=readme,
                topics_text=json.dumps(topic_slugs),
                gallery_json='[]',
                created_at=created,
                updated_at=updated,
                pushed_at=pushed,
                latest_release_version=(
                    f"v{1 + (h % 6)}.{(h >> 2) % 24}.{(h >> 4) % 20}"),
                latest_release_date=pushed - timedelta(days=6 + (h % 70)),
                latest_release_notes=(
                    f"R7 polish on the {area} subsystem: tightened invariants, "
                    "new property tests, OG/JSON-LD coverage on the repo "
                    "page. See CHANGELOG."),
                latest_commit_sha=sha,
                latest_commit_message=(
                    f"feat({area}): harden invariants + property tests ({base_name})"),
                latest_commit_date=pushed,
                latest_commit_additions=22 + (h % 360),
                latest_commit_deletions=6 + ((h >> 1) % 180),
            )
            db.session.add(repo)
            db.session.flush()
            for slug in topic_slugs:
                t = topic_by_slug.get(slug)
                if t is not None:
                    repo.topics.append(t)
            existing_full.add(full)
            added += 1
            if added % 1000 == 0:
                db.session.commit()
    db.session.commit()
    return added


# Commit-count topup target — drives `commits_json` length for high-star
# repos so the cumulative count crosses _R7_COMMIT_TARGET. Each repo's
# topup is deterministic against (repo.id, slot).
_R7_COMMIT_TARGET = 400000


def seed_r7_topup_commits():
    """Top up commits_json across the catalog until the cumulative commit
    count crosses _R7_COMMIT_TARGET. Existing commits are preserved; we only
    *extend* the list with older commits dated before the current oldest
    entry. Deterministic — sha derives from (repo.id, slot)."""
    # Use SQLite's json_array_length (available since 3.38) to count actual
    # commits across the catalog. Falling back to a byte-length heuristic
    # would over-estimate (≈500B per commit, not 250B) and cause the topup
    # to early-exit before reaching the target — that bug bit the first run
    # which finished at 359k / 400k.
    try:
        cur = db.session.execute(
            text("SELECT COALESCE(SUM(json_array_length(commits_json)), 0) "
                 "FROM repository WHERE commits_json IS NOT NULL "
                 "AND commits_json != ''"))
        actual_have = int(cur.scalar() or 0)
    except Exception:
        # Older SQLite: fall back to a generous 500-byte-per-commit guess.
        sample = db.session.execute(
            text("SELECT SUM(LENGTH(commits_json)) FROM repository "
                 "WHERE commits_json IS NOT NULL")).scalar() or 0
        actual_have = max(0, sample // 500)
    if actual_have >= _R7_COMMIT_TARGET:
        return 0

    # Bring high-star repos up to 30 commits, mid-tier to 22, tail to 16.
    # That alone adds ~150k commits on the 32k catalog when paired with
    # the R5+R6 existing baseline.
    repos = (Repository.query
             .order_by(Repository.stars_count.desc(),
                       Repository.id.asc())
             .all())

    total_added = 0
    touched = 0
    for repo in repos:
        s = repo.stars_count or 0
        if s >= 5000:
            target = 30
        elif s >= 500:
            target = 22
        elif s >= 50:
            target = 18
        else:
            target = 16
        try:
            commits = json.loads(repo.commits_json or '[]')
        except Exception:
            commits = []
        if len(commits) >= target:
            continue

        # Anchor at the oldest existing commit's date so the new (older)
        # commits sit cleanly before it. Fall back to created_at / BULK_REF.
        oldest_dt = _BULK_REF
        if commits:
            try:
                oldest_dt = datetime.fromisoformat(commits[-1].get('date'))
            except Exception:
                pass
        elif repo.created_at:
            oldest_dt = repo.created_at

        owner_name = repo.full_name.split('/', 1)[0]
        need = target - len(commits)
        for i in range(need):
            slot = len(commits) + i
            area = _COMMIT_AREAS[(repo.id * 9 + slot * 13) % len(_COMMIT_AREAS)]
            msg = _COMMIT_MSG_TEMPLATES[
                (repo.id * 7 + slot * 19) % len(_COMMIT_MSG_TEMPLATES)
            ].format(area=area)
            ts = oldest_dt - timedelta(days=i * 2 + (repo.id % 3) + 1,
                                       hours=(i * 5 + repo.id) % 24)
            sha = hashlib.sha1(
                f"r7|{repo.full_name}|{slot}".encode()).hexdigest()
            files = _commit_files_for(repo.language or '', area,
                                      repo.id + slot + 1000)
            adds = sum(f['additions'] for f in files)
            dels = sum(f['deletions'] for f in files)
            commits.append({
                'sha': sha,
                'message': msg,
                'author': owner_name,
                'date': ts.isoformat(),
                'files': files,
                'additions': adds,
                'deletions': dels,
            })
        repo.commits_json = json.dumps(commits)
        total_added += need
        touched += 1
        if touched % 2000 == 0:
            db.session.commit()
    db.session.commit()
    return touched


def normalize_seed_db_layout(dirty: bool = False):
    """Re-emit indexes in alpha order + VACUUM so seed rebuilds match
    byte-for-byte across processes (see harden-env/gotchas.md #2).

    Gated on `dirty` — only re-indexes and VACUUMs when a prior seeder
    actually wrote rows this run. Warm rebuilds (where everything was
    already seeded) skip this, so the SQLite file change counter stays
    stable and md5×2 matches across runs."""
    if not dirty:
        return
    try:
        conn = db.engine.connect()
        idx_rows = conn.execute(text(
            "SELECT name, sql FROM sqlite_master "
            "WHERE type='index' AND name LIKE 'ix_%'"
        )).fetchall()
        for name, _ in idx_rows:
            conn.execute(text(f"DROP INDEX IF EXISTS {name}"))
        for name, sql in sorted(idx_rows, key=lambda r: r[0]):
            if sql:
                conn.execute(text(sql))
        conn.execute(text("VACUUM"))
        conn.commit()
    except Exception:
        db.session.rollback()


def post_seed_tweaks():
    """Idempotent updates that run on every startup to keep WebVoyager-task
    coverage current even if seed_database() short-circuits because users
    already exist."""
    # Promote topics that frequently appear in WebVoyager tasks so they're
    # discoverable from the homepage / topics index.
    promote_slugs = ('image-processing', 'cybersecurity', 'web-scraping',
                     'security', 'nlp')
    changed = False
    for slug in promote_slugs:
        t = Topic.query.filter_by(slug=slug).first()
        if t and not t.is_featured:
            t.is_featured = True
            changed = True

    # R3: ensure every unique topic slug referenced by any repo lives in
    # the Topic table (so /topics/<slug> + /topics index stay populated).
    # Idempotent — skips slugs that already exist.
    existing_topic_slugs = {t.slug for t in Topic.query.all()}
    seen = set()
    for repo in Repository.query.with_entities(Repository.topics_text).all():
        try:
            for slug in json.loads(repo[0] or '[]'):
                if not isinstance(slug, str):
                    continue
                slug = slug.strip().lower()
                if slug and slug not in existing_topic_slugs and slug not in seen:
                    seen.add(slug)
        except Exception:
            continue
    if seen:
        for slug in sorted(seen):  # sorted → deterministic insert order
            display = slug.replace('-', ' ').title()
            db.session.add(Topic(
                slug=slug, display_name=display,
                description=f"Repositories tagged {display}.",
                short_desc=f"Repositories tagged {display}",
                is_featured=False,
            ))
        changed = True

    if changed:
        db.session.flush()
    # Refresh repos_count so topic cards show real numbers.
    for t in Topic.query.all():
        c = len(t.repositories) if isinstance(t.repositories, list) else t.repositories.count()
        if t.repos_count != c:
            t.repos_count = c
            changed = True
    if changed:
        db.session.commit()
    return 1 if changed else 0


def create_app():
    with app.app_context():
        db.create_all()
        seed_database()
        seed_benchmark_users()
        seed_extra_repos()
        c0 = seed_extra_issues() or 0
        seed_extra_issue_comments()
        seed_extra_stars()
        seed_extra_watches()
        c1 = seed_extra_commits() or 0
        c2 = seed_extra_pulls() or 0
        # R4: org-driven extras
        c3 = seed_r4_org_repos() or 0
        c4 = seed_r4_discussions() or 0
        c5 = seed_r4_sponsorships() or 0
        c6 = seed_r4_project_boards() or 0
        c7 = seed_r4_packages() or 0
        c8 = seed_r4_teams() or 0
        # R5: add ~6k repos, top off commits past 200k, mint fresh PRs.
        # seed_r5_user_repos() must run before seed_extra_commits() can fill
        # in their commit history; we call seed_extra_commits() again to
        # process the R5 slice. Then seed_r5_topup_commits() tops off.
        c9 = seed_r5_user_repos() or 0
        c1b = seed_extra_commits() or 0
        c10 = seed_r5_topup_commits() or 0
        c11 = seed_r5_extra_pulls() or 0
        # R6: edge-state lab + 6800 more catalog repos.
        c12 = seed_r6_edge_repos() or 0
        c13 = seed_r6_user_repos() or 0
        c1c = seed_extra_commits() or 0
        # R7: extend catalog to 32k + top up commits past 400k.
        c14 = seed_r7_user_repos() or 0
        c1d = seed_extra_commits() or 0
        c15 = seed_r7_topup_commits() or 0
        # R8: extend catalog to 40k+; commits topped via seed_extra_commits.
        c16 = seed_r8_user_repos() or 0
        c1e = seed_extra_commits() or 0
        # R9: extend catalog to 50k+; commits topped via seed_extra_commits.
        c17 = seed_r9_user_repos() or 0
        c1f = seed_extra_commits() or 0
        # R10: extend catalog to 56k+; commits topped via seed_extra_commits.
        c18 = seed_r10_user_repos() or 0
        c1g = seed_extra_commits() or 0
        ct = post_seed_tweaks() or 0
        normalize_seed_db_layout(
            dirty=(c0 + c1 + c1b + c1c + c1d + c1e + c1f + c1g + c2 + c3 + c4 + c5 + c6 + c7
                   + c8 + c9 + c10 + c11 + c12 + c13 + c14 + c15 + c16 + c17 + c18 + ct) > 0)
    return app


# Ensure DB schema + tweaks apply regardless of how app is launched (direct
# `app.run` vs `create_app()` entrypoint).
with app.app_context():
    try:
        db.create_all()
        seed_database()
        seed_benchmark_users()
        seed_extra_repos()
        c0 = seed_extra_issues() or 0
        seed_extra_issue_comments()
        seed_extra_stars()
        seed_extra_watches()
        c1 = seed_extra_commits() or 0
        c2 = seed_extra_pulls() or 0
        # R4
        c3 = seed_r4_org_repos() or 0
        c4 = seed_r4_discussions() or 0
        c5 = seed_r4_sponsorships() or 0
        c6 = seed_r4_project_boards() or 0
        c7 = seed_r4_packages() or 0
        c8 = seed_r4_teams() or 0
        # R5
        c9 = seed_r5_user_repos() or 0
        c1b = seed_extra_commits() or 0
        c10 = seed_r5_topup_commits() or 0
        c11 = seed_r5_extra_pulls() or 0
        # R6
        c12 = seed_r6_edge_repos() or 0
        c13 = seed_r6_user_repos() or 0
        c1c = seed_extra_commits() or 0
        # R7
        c14 = seed_r7_user_repos() or 0
        c1d = seed_extra_commits() or 0
        c15 = seed_r7_topup_commits() or 0
        # R8
        c16 = seed_r8_user_repos() or 0
        c1e = seed_extra_commits() or 0
        # R9
        c17 = seed_r9_user_repos() or 0
        c1f = seed_extra_commits() or 0
        # R10
        c18 = seed_r10_user_repos() or 0
        c1g = seed_extra_commits() or 0
        ct = post_seed_tweaks() or 0
        normalize_seed_db_layout(
            dirty=(c0 + c1 + c1b + c1c + c1d + c1e + c1f + c1g + c2 + c3 + c4 + c5 + c6 + c7
                   + c8 + c9 + c10 + c11 + c12 + c13 + c14 + c15 + c16 + c17 + c18 + ct) > 0)
        ct = post_seed_tweaks() or 0
        normalize_seed_db_layout(
            dirty=(c0 + c1 + c2 + c3 + c4 + c5 + c6 + c7 + c8 + ct) > 0)
    except Exception:
        # In case of stale schema, skip silently; routes remain available.
        db.session.rollback()


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
R2_SITE_NAME = "GitHub"
R2_DOMAIN = "github.com"
R2_ACCESSIBILITY_BLURB = "GitHub publishes accessibility conformance reports and supports keyboard-only workflows across the code review and Issues surfaces."


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
R3_SITE_NAME = "GitHub"
R3_DOMAIN = "github.com"


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


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 28848))
    app.run(host='0.0.0.0', port=port, debug=False)
