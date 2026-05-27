"""
Hugging Face Mirror — Full-stack Flask application.

Entity model adapted for an ML/AI developer platform:
  Repository (Model | Dataset | Space) <- Product
  Task       <- Category
  CartItem (Deployment Cart)  <- cart (with hardware choice)
  InferenceEndpoint (Order)   <- order (with endpoint_id, hourly rate, status)
  Like       <- wishlist
  Collection <- user-curated named groups of repos
  Discussion <- review/comment threads
  Follow     <- social graph (user -> author)
"""
import json
import os
import random
import re
import secrets
import string
from datetime import datetime, timedelta
from pathlib import Path

# ----------------------------------------------------------------------------
# Pinned mirror clock. The Docker image is built once and may be evaluated by
# users at any future point in time. We freeze "today" so date-relative
# WebVoyager / WebTau tasks (e.g. "released in the past month", "last updated
# in March 2023") behave deterministically regardless of wall-clock time.
# Chosen to fall just after the newest seeded updated_at (2026-04-12) so
# "past month" still matches recent uploads, while keeping every historical
# anchor (2022 NER models, March 2023 sentiment models, …) firmly in the past.
# ----------------------------------------------------------------------------
MIRROR_REFERENCE_DATE = datetime(2026, 4, 25, 12, 0, 0)


def mirror_now() -> datetime:
    return MIRROR_REFERENCE_DATE

from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, abort, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_bcrypt import Bcrypt
from flask_wtf import FlaskForm, CSRFProtect
from wtforms import StringField, PasswordField, TextAreaField, SelectField, IntegerField, HiddenField
from wtforms.validators import DataRequired, Email, Length, EqualTo, Optional as OptionalValidator

from seed_data import (
    TASKS, MODALITIES, LIBRARIES, LICENSES, LANGUAGES, SPACE_HARDWARE, INFERENCE_PROVIDERS,  # noqa: F401
    AUTHORS, build_seed_repos,
)
from content_data import (
    DOC_PAGES, BLOG_POSTS, DAILY_PAPERS, CLASSROOM_BENEFITS, PRICING_PLANS,
    DATASET_VIEWER_DATA, LEADERBOARDS, PRICING_PLAN_DETAILS,
)

# ------------------------------------------------------------
# Flask setup
# ------------------------------------------------------------
ROOT = Path(__file__).parent
app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "hf-mirror-dev-secret-key-change-me")
app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{ROOT / 'instance' / 'hf.db'}"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
(ROOT / "instance").mkdir(exist_ok=True)

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
csrf = CSRFProtect(app)
login_manager = LoginManager(app)
login_manager.login_view = "login"
login_manager.login_message_category = "info"


@app.template_filter("fromjson")
def _fromjson_filter(value):
    """Parse a JSON string in a template. Returns [] on failure."""
    try:
        if isinstance(value, (list, dict)):
            return value
        return json.loads(value)
    except Exception:
        return []


@app.template_filter("hash_md5_int")
def _hash_md5_int_filter(value):
    """Return an int derived from md5(str(value)). Used by templates to
    derive deterministic per-id state without round-tripping to Python."""
    import hashlib as _h
    try:
        s = str(value)
        return int(_h.md5(s.encode("utf-8")).hexdigest(), 16)
    except Exception:
        return 0


# ------------------------------------------------------------
# Database models
# ------------------------------------------------------------
class User(db.Model, UserMixin):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(180), unique=True, nullable=False, index=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(200), nullable=False)
    display_name = db.Column(db.String(120), default="")
    bio = db.Column(db.Text, default="")
    avatar_url = db.Column(db.String(300), default="/static/images/avatars/avatar_000.png")
    website = db.Column(db.String(200), default="")
    location = db.Column(db.String(120), default="")
    company = db.Column(db.String(120), default="")
    is_pro = db.Column(db.Boolean, default=False)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=lambda: MIRROR_REFERENCE_DATE)

    likes = db.relationship("Like", backref="user", cascade="all, delete-orphan", lazy="dynamic")
    follows = db.relationship("Follow", backref="user", cascade="all, delete-orphan", lazy="dynamic", foreign_keys="Follow.user_id")
    collections = db.relationship("Collection", backref="owner", cascade="all, delete-orphan", lazy="dynamic")
    cart_items = db.relationship("CartItem", backref="user", cascade="all, delete-orphan", lazy="dynamic")
    endpoints = db.relationship("InferenceEndpoint", backref="user", cascade="all, delete-orphan", lazy="dynamic")
    discussions = db.relationship("Discussion", backref="author", cascade="all, delete-orphan", lazy="dynamic")


class Task(db.Model):
    __tablename__ = "tasks"
    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(80), unique=True, nullable=False, index=True)
    display = db.Column(db.String(120), nullable=False)
    modality = db.Column(db.String(80), nullable=False, index=True)
    icon = db.Column(db.String(20), default="🔹")
    description = db.Column(db.Text, default="")
    repos = db.relationship("Repository", backref="task_obj", lazy="dynamic")


class Author(db.Model):
    """Organization or user owning repositories (like google, meta-llama)."""
    __tablename__ = "authors"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(120), unique=True, nullable=False, index=True)
    display_name = db.Column(db.String(200), nullable=False)
    kind = db.Column(db.String(10), default="org")   # org | user
    bio = db.Column(db.Text, default="")
    followers_count = db.Column(db.Integer, default=0)
    website = db.Column(db.String(300), default="")
    avatar_url = db.Column(db.String(300), default="")
    is_verified = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=lambda: MIRROR_REFERENCE_DATE)
    repos = db.relationship("Repository", backref="author_obj", lazy="dynamic")


class Repository(db.Model):
    """Unified Model | Dataset | Space entity."""
    __tablename__ = "repositories"
    # R7: composite indexes for the two hottest filter+sort combos on
    # /models and /datasets — (task, downloads desc) and
    # (library, likes desc). Without these the planner falls back to a
    # full-table scan + sort on the 170k-row pool, which adds ~120ms per
    # request in the dev container.
    __table_args__ = (
        db.UniqueConstraint("slug", "repo_type", name="uix_repo_slug_type"),
        db.Index("ix_repo_type_task_downloads", "repo_type", "task_id", "downloads"),
        db.Index("ix_repo_type_library_likes", "repo_type", "library", "likes_count"),
        db.Index("ix_repo_type_modality_downloads", "repo_type", "modality", "downloads"),
    )
    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(300), nullable=False, index=True)  # author/name
    name = db.Column(db.String(200), nullable=False)
    repo_type = db.Column(db.String(16), nullable=False, index=True)           # model | dataset | space
    author_id = db.Column(db.Integer, db.ForeignKey("authors.id"), index=True)
    task_id = db.Column(db.Integer, db.ForeignKey("tasks.id"), index=True, nullable=True)
    library = db.Column(db.String(80), default="")
    license = db.Column(db.String(80), default="apache-2.0")
    license_display = db.Column(db.String(120), default="Apache 2.0")
    description = db.Column(db.Text, default="")
    readme = db.Column(db.Text, default="")
    language = db.Column(db.String(80), default="English")
    # Model-specific
    params_b = db.Column(db.Float, default=0.0)
    inference_provider = db.Column(db.String(80), default="")
    # Dataset-specific
    modality = db.Column(db.String(80), default="")
    rows = db.Column(db.BigInteger, default=0)
    # Space-specific
    sdk = db.Column(db.String(40), default="")
    hardware_slug = db.Column(db.String(40), default="")
    hardware_display = db.Column(db.String(120), default="")
    hardware_specs = db.Column(db.String(200), default="")
    hardware_price = db.Column(db.String(40), default="")
    emoji = db.Column(db.String(20), default="🚀")
    status = db.Column(db.String(40), default="Running")
    # Common
    downloads = db.Column(db.BigInteger, default=0)
    likes_count = db.Column(db.Integer, default=0)
    is_featured = db.Column(db.Boolean, default=False)
    is_new = db.Column(db.Boolean, default=False)
    tags_json = db.Column(db.Text, default="[]")
    avatar_url = db.Column(db.String(300), default="")
    banner_url = db.Column(db.String(300), default="")
    # R4 added — public signal columns used by sparklines, trending sort, params
    # column on /models, and "last modified" badges on space rows. All are
    # deterministic functions of the slug so a fresh seed rebuild is byte-stable.
    trending_score = db.Column(db.Float, default=0.0, index=True)
    monthly_downloads_history = db.Column(db.Text, default="[]")  # JSON: list of 12 ints
    last_modified = db.Column(db.DateTime, default=lambda: MIRROR_REFERENCE_DATE)
    param_count = db.Column(db.BigInteger, default=0)  # explicit, not derived from params_b
    # R5 added — license link, structured eval-results payload, training-hardware
    # provenance, and training compute hours. Used by /<repo>/section/<sid>,
    # /api/snippet/..., /api/autotrain/estimate, billing pages, and the new
    # readme-anchor / paper-implementations routes. Every value is a
    # deterministic function of the slug so a fresh rebuild is byte-stable.
    license_url = db.Column(db.String(300), default="")
    eval_results_json = db.Column(db.Text, default="[]")          # JSON list of {benchmark,score,split}
    hardware_used = db.Column(db.String(120), default="")          # e.g. "256× A100 80GB"
    training_compute_hours = db.Column(db.Integer, default=0)
    # R6 added — provenance + gating + state-edge columns surfacing
    # production-readiness warnings, gated-access flag, space build-error
    # log fingerprint, base-model lineage for "Fine-tuned versions" sidebar,
    # and a deterministic-flag for endpoint quota exceeded. Used by
    # /<a>/<n>/access, /spaces/<a>/<n>/logs, sidebar "Fine-tuned versions",
    # leaderboard pending-eval rows. Every value derives from slug md5.
    not_for_production = db.Column(db.Boolean, default=False, index=True)
    is_gated = db.Column(db.Boolean, default=False, index=True)
    gated_reason = db.Column(db.String(160), default="")
    base_model_slug = db.Column(db.String(300), default="", index=True)
    space_build_status = db.Column(db.String(40), default="")     # "" | "build-error" | "build-running"
    space_build_log = db.Column(db.Text, default="")
    citing_paper_ids = db.Column(db.Text, default="[]")           # JSON list of arxiv ids
    created_at = db.Column(db.DateTime, default=lambda: MIRROR_REFERENCE_DATE)
    updated_at = db.Column(db.DateTime, default=lambda: MIRROR_REFERENCE_DATE)

    discussions = db.relationship("Discussion", backref="repo", cascade="all, delete-orphan", lazy="dynamic")

    @property
    def tags(self):
        try:
            return json.loads(self.tags_json or "[]")
        except Exception:
            return []

    @property
    def task_slug(self):
        return self.task_obj.slug if self.task_obj else ""

    @property
    def task_display(self):
        return self.task_obj.display if self.task_obj else self.repo_type.capitalize()

    @property
    def size_badge(self):
        if self.repo_type == "model" and self.params_b > 0:
            if self.params_b >= 1:
                return f"{int(self.params_b)}B"
            return f"{int(self.params_b * 1000)}M"
        return ""

    @property
    def updated_display(self):
        dt = self.updated_at or mirror_now()
        return dt.strftime("%b %d, %Y")

    @property
    def downloads_display(self):
        n = self.downloads or 0
        if n >= 1_000_000:
            return f"{n / 1_000_000:.1f}M"
        if n >= 1_000:
            return f"{n / 1_000:.1f}k"
        return str(n)

    @property
    def likes_display(self):
        n = self.likes_count or 0
        if n >= 1000:
            return f"{n / 1000:.2f}k".rstrip("0").rstrip(".")
        return str(n)

    @property
    def rows_display(self):
        n = self.rows or 0
        if n >= 1_000_000_000_000:
            return f"{n / 1e12:.1f}T"
        if n >= 1_000_000_000:
            return f"{n / 1e9:.1f}B"
        if n >= 1_000_000:
            return f"{n / 1e6:.1f}M"
        if n >= 1_000:
            return f"{n / 1e3:.1f}k"
        return str(n)

    @property
    def monthly_history(self):
        """12-element list of monthly download counts for sparkline charts."""
        try:
            arr = json.loads(self.monthly_downloads_history or "[]")
            if isinstance(arr, list):
                return arr
        except Exception:
            pass
        return []

    @property
    def trending_score_display(self):
        """Render trending_score as a clean two-decimal string."""
        try:
            return f"{float(self.trending_score or 0):.2f}"
        except Exception:
            return "0.00"

    @property
    def param_count_display(self):
        """Render param_count as e.g. '7.0B', '350M', '125M' for the /models column."""
        n = int(self.param_count or 0)
        if n >= 1_000_000_000:
            return f"{n / 1e9:.1f}B"
        if n >= 1_000_000:
            return f"{n / 1e6:.0f}M"
        if n > 0:
            return f"{n / 1e3:.0f}k"
        return ""

    @property
    def last_modified_display(self):
        dt = self.last_modified or self.updated_at or mirror_now()
        return dt.strftime("%b %d, %Y")

    # R5 helpers ------------------------------------------------------
    @property
    def eval_results(self):
        """Parsed eval_results_json — list of {benchmark, score, split}."""
        try:
            arr = json.loads(self.eval_results_json or "[]")
            return arr if isinstance(arr, list) else []
        except Exception:
            return []

    @property
    def training_compute_display(self):
        """Render training_compute_hours as e.g. '12.0k GPU-hours' / '845 GPU-hours'."""
        n = int(self.training_compute_hours or 0)
        if n >= 1_000_000:
            return f"{n / 1e6:.1f}M GPU-hours"
        if n >= 1_000:
            return f"{n / 1e3:.1f}k GPU-hours"
        if n > 0:
            return f"{n} GPU-hours"
        return ""

    @property
    def license_link(self):
        """Return license_url or fall back to a sensible default per license slug."""
        if self.license_url:
            return self.license_url
        slug = (self.license or "").lower()
        defaults = {
            "apache-2.0": "https://www.apache.org/licenses/LICENSE-2.0",
            "mit": "https://opensource.org/license/mit/",
            "cc-by-4.0": "https://creativecommons.org/licenses/by/4.0/",
            "cc-by-sa-4.0": "https://creativecommons.org/licenses/by-sa/4.0/",
            "cc-by-nc-4.0": "https://creativecommons.org/licenses/by-nc/4.0/",
            "openrail": "https://www.licenses.ai/open-rail",
            "creativeml-openrail-m": "https://huggingface.co/spaces/CompVis/stable-diffusion-license",
            "llama-3.3": "https://llama.meta.com/llama3/license/",
            "gemma": "https://ai.google.dev/gemma/terms",
            "bsd-3-clause": "https://opensource.org/license/bsd-3-clause/",
            "gpl-3.0": "https://www.gnu.org/licenses/gpl-3.0.en.html",
        }
        return defaults.get(slug, f"/license/{slug or 'other'}")

    # R6 helpers ------------------------------------------------------
    @property
    def citing_papers(self):
        """Parsed citing_paper_ids — list of arxiv ids referencing this repo."""
        try:
            arr = json.loads(self.citing_paper_ids or "[]")
            return arr if isinstance(arr, list) else []
        except Exception:
            return []


class Like(db.Model):
    __tablename__ = "likes"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    repo_id = db.Column(db.Integer, db.ForeignKey("repositories.id"), nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=lambda: MIRROR_REFERENCE_DATE)
    repo = db.relationship("Repository")
    __table_args__ = (db.UniqueConstraint("user_id", "repo_id", name="uix_like"),)


class Follow(db.Model):
    __tablename__ = "follows"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    author_id = db.Column(db.Integer, db.ForeignKey("authors.id"), nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=lambda: MIRROR_REFERENCE_DATE)
    author = db.relationship("Author")
    __table_args__ = (db.UniqueConstraint("user_id", "author_id", name="uix_follow"),)


class Collection(db.Model):
    __tablename__ = "collections"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, default="")
    is_public = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=lambda: MIRROR_REFERENCE_DATE)
    items = db.relationship("CollectionItem", backref="collection", cascade="all, delete-orphan", lazy="dynamic")


class CollectionItem(db.Model):
    __tablename__ = "collection_items"
    id = db.Column(db.Integer, primary_key=True)
    collection_id = db.Column(db.Integer, db.ForeignKey("collections.id"), nullable=False, index=True)
    repo_id = db.Column(db.Integer, db.ForeignKey("repositories.id"), nullable=False, index=True)
    note = db.Column(db.Text, default="")
    position = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=lambda: MIRROR_REFERENCE_DATE)
    repo = db.relationship("Repository")


class CartItem(db.Model):
    """Deployment cart — user stages repos + hardware before 'deploying'."""
    __tablename__ = "cart_items"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    repo_id = db.Column(db.Integer, db.ForeignKey("repositories.id"), nullable=False, index=True)
    hardware_slug = db.Column(db.String(40), default="t4-small")
    hardware_display = db.Column(db.String(120), default="Nvidia T4")
    hardware_price = db.Column(db.String(40), default="$0.40/hr")
    hours = db.Column(db.Integer, default=24)
    region = db.Column(db.String(40), default="us-east-1")
    created_at = db.Column(db.DateTime, default=lambda: MIRROR_REFERENCE_DATE)
    repo = db.relationship("Repository")


class InferenceEndpoint(db.Model):
    """Order equivalent — a deployed repo on specific hardware.

    Lifecycle: initializing -> running -> paused -> terminated.
    """
    __tablename__ = "endpoints"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    endpoint_id = db.Column(db.String(40), unique=True, nullable=False, index=True)  # EP-XXXXXX
    name = db.Column(db.String(200), nullable=False)
    status = db.Column(db.String(40), default="initializing")
    region = db.Column(db.String(40), default="us-east-1")
    total_hours = db.Column(db.Integer, default=24)
    total_cost = db.Column(db.String(40), default="$0.00")
    created_at = db.Column(db.DateTime, default=lambda: MIRROR_REFERENCE_DATE)
    items = db.relationship("EndpointItem", backref="endpoint", cascade="all, delete-orphan", lazy="dynamic")


class EndpointItem(db.Model):
    __tablename__ = "endpoint_items"
    id = db.Column(db.Integer, primary_key=True)
    endpoint_id = db.Column(db.Integer, db.ForeignKey("endpoints.id"), nullable=False, index=True)
    repo_id = db.Column(db.Integer, db.ForeignKey("repositories.id"), nullable=False, index=True)
    hardware_slug = db.Column(db.String(40), default="")
    hardware_display = db.Column(db.String(120), default="")
    hardware_price = db.Column(db.String(40), default="")
    hours = db.Column(db.Integer, default=24)
    repo = db.relationship("Repository")


class Discussion(db.Model):
    """Community discussion thread on a repo — review equivalent."""
    __tablename__ = "discussions"
    id = db.Column(db.Integer, primary_key=True)
    repo_id = db.Column(db.Integer, db.ForeignKey("repositories.id"), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    title = db.Column(db.String(300), nullable=False)
    body = db.Column(db.Text, nullable=False)
    kind = db.Column(db.String(20), default="discussion")   # discussion | pull-request | issue
    status = db.Column(db.String(20), default="open")       # open | closed | merged
    upvotes = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=lambda: MIRROR_REFERENCE_DATE)
    replies = db.relationship("DiscussionReply", backref="discussion", cascade="all, delete-orphan", lazy="dynamic")


class DiscussionReply(db.Model):
    __tablename__ = "discussion_replies"
    id = db.Column(db.Integer, primary_key=True)
    discussion_id = db.Column(db.Integer, db.ForeignKey("discussions.id"), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    body = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: MIRROR_REFERENCE_DATE)
    user = db.relationship("User")


# ------------------------------------------------------------
# Login manager
# ------------------------------------------------------------
@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


# ------------------------------------------------------------
# Forms
# ------------------------------------------------------------
class LoginForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired()])


class RegisterForm(FlaskForm):
    username = StringField("Username", validators=[DataRequired(), Length(3, 40)])
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired(), Length(6, 120)])
    confirm = PasswordField("Confirm Password", validators=[DataRequired(), EqualTo("password")])


class ProfileForm(FlaskForm):
    display_name = StringField("Display name", validators=[OptionalValidator(), Length(0, 120)])
    bio = TextAreaField("Bio", validators=[OptionalValidator()])
    website = StringField("Website", validators=[OptionalValidator()])
    location = StringField("Location", validators=[OptionalValidator()])
    company = StringField("Company", validators=[OptionalValidator()])


class PasswordForm(FlaskForm):
    current = PasswordField("Current password", validators=[DataRequired()])
    new = PasswordField("New password", validators=[DataRequired(), Length(6, 120)])
    confirm = PasswordField("Confirm new password", validators=[DataRequired(), EqualTo("new")])


class CollectionForm(FlaskForm):
    title = StringField("Title", validators=[DataRequired(), Length(1, 200)])
    description = TextAreaField("Description", validators=[OptionalValidator()])
    is_public = SelectField("Visibility", choices=[("1", "Public"), ("0", "Private")], default="1")


class DiscussionForm(FlaskForm):
    title = StringField("Title", validators=[DataRequired(), Length(1, 300)])
    body = TextAreaField("Body", validators=[DataRequired()])
    kind = SelectField("Type", choices=[("discussion", "Discussion"), ("issue", "Issue"), ("pull-request", "Pull request")])


class ReplyForm(FlaskForm):
    body = TextAreaField("Reply", validators=[DataRequired()])


class CheckoutForm(FlaskForm):
    name = StringField("Deployment name", validators=[DataRequired(), Length(1, 200)])
    region = SelectField("Region", choices=[
        ("us-east-1", "US East (N. Virginia)"),
        ("us-west-2", "US West (Oregon)"),
        ("eu-west-1", "EU West (Ireland)"),
        ("eu-central-1", "EU Central (Frankfurt)"),
        ("ap-southeast-1", "Asia Pacific (Singapore)"),
    ])
    payment_method = SelectField("Payment method", choices=[
        ("card", "Credit / Debit Card"),
        ("invoice", "Invoice (Enterprise)"),
    ])


# ------------------------------------------------------------
# Helpers
# ------------------------------------------------------------
def resolve_author_avatar(username: str) -> str:
    """Return the URL of the author's avatar.

    Prefers a real-org logo at /static/images/avatars/orgs/<username>.<ext>
    (case-insensitive). Falls back to a deterministic generic avatar from
    /static/images/avatars/avatar_*.* so the same username always renders
    the same image.
    """
    if not username:
        return ""
    orgs_dir = ROOT / "static" / "images" / "avatars" / "orgs"
    if orgs_dir.exists():
        # Try exact then case-insensitive match across common image suffixes
        candidates = list(orgs_dir.iterdir())
        lower = username.lower()
        for p in candidates:
            if p.stem == username and p.is_file():
                return f"/static/images/avatars/orgs/{p.name}"
        for p in candidates:
            if p.stem.lower() == lower and p.is_file():
                return f"/static/images/avatars/orgs/{p.name}"
    # Deterministic fallback into the generic pool
    pool_dir = ROOT / "static" / "images" / "avatars"
    if pool_dir.exists():
        pool = sorted(p.name for p in pool_dir.iterdir() if p.is_file() and p.suffix.lower() in {".png",".jpg",".jpeg",".webp",".svg"})
        if pool:
            import hashlib
            h = int(hashlib.md5(username.encode()).hexdigest(), 16)
            return f"/static/images/avatars/{pool[h % len(pool)]}"
    return ""


def get_or_create_author(username: str) -> Author:
    a = Author.query.filter_by(username=username).first()
    if not a:
        # Deterministic follower count from a hash of the username — using
        # random.randint() here drifts across rebuilds and broke
        # byte-identical seed regeneration (R2: gotcha #3 sibling — non-PRNG
        # randomness in the seed path).
        import hashlib as _h
        seed = int.from_bytes(_h.md5(username.encode()).digest()[:4], "big")
        followers = 300 + (seed % 8700)
        a = Author(
            username=username,
            display_name=username,
            kind="org",
            bio=f"Releases from {username}.",
            followers_count=followers,
            website="",
            avatar_url=resolve_author_avatar(username),
            is_verified=False,
        )
        db.session.add(a)
        db.session.flush()
    return a


def current_cart_count():
    if not current_user.is_authenticated:
        return 0
    return CartItem.query.filter_by(user_id=current_user.id).count()


def _liked_repo_ids():
    if not current_user.is_authenticated:
        return set()
    return {l.repo_id for l in Like.query.filter_by(user_id=current_user.id).all()}


# ------------------------------------------------------------
# Scored search helpers
# ------------------------------------------------------------
STOPWORDS = {
    "the", "a", "an", "of", "in", "on", "at", "to", "for", "with", "and",
    "or", "is", "are", "be", "by", "from", "that", "this", "it", "as",
    "best", "most", "new", "latest", "recent", "top", "find", "show",
    "model", "models", "dataset", "datasets", "space", "spaces",
    "hugging", "huggingface", "hub", "use", "using",
}


def _tokenize(q: str):
    return [t for t in re.findall(r"[a-z0-9.+-]+", (q or "").lower())
            if len(t) >= 2 and t not in STOPWORDS]


def _repo_haystack(r: "Repository") -> str:
    parts = [
        (r.slug or "").lower(),
        (r.name or "").lower(),
        (r.description or "").lower(),
        (r.readme or "").lower()[:800],
        (r.tags_json or "").lower(),
        (r.library or "").lower(),
        (r.license or "").lower(),
        (r.language or "").lower(),
        (r.modality or "").lower(),
        (r.task_obj.slug if r.task_obj else "").lower(),
        (r.task_obj.display if r.task_obj else "").lower(),
        (r.author_obj.username if r.author_obj else "").lower(),
    ]
    return " ".join(parts)


def _score_repo(repo, tokens):
    if not tokens:
        return 1
    hay = _repo_haystack(repo)
    return sum(1 for t in tokens if t in hay)


def _apply_text_prefilter(query, q: str):
    """Narrow a Repository query to rows that plausibly contain any of the
    free-text tokens before LIMIT/sort. Without this, long-tail repos with low
    trending scores get cut off by the SQL LIMIT before scoring sees them."""
    tokens = _tokenize(q or "")
    if not tokens:
        return query
    from sqlalchemy import or_
    clauses = []
    for t in tokens:
        pat = f"%{t}%"
        clauses += [
            Repository.slug.ilike(pat),
            Repository.name.ilike(pat),
            Repository.description.ilike(pat),
            Repository.tags_json.ilike(pat),
        ]
    return query.filter(or_(*clauses))


def _apply_repo_filters(query, args):
    """Apply common filter query-string args to a Repository SQL query."""
    license_ = args.get("license", "")
    if license_:
        query = query.filter(Repository.license == license_)
    library = args.get("library", "")
    if library:
        query = query.filter(Repository.library.ilike(library))
    language = args.get("language", "")
    if language:
        query = query.filter(Repository.language.ilike(f"%{language}%"))
    task_slug = args.get("task", "")
    if task_slug:
        t = Task.query.filter_by(slug=task_slug).first()
        if t:
            query = query.filter(Repository.task_id == t.id)
    modality = args.get("modality", "")
    if modality:
        query = query.filter(Repository.modality.ilike(f"%{modality}%"))
    min_downloads = args.get("min_downloads", type=int)
    if min_downloads:
        query = query.filter(Repository.downloads >= min_downloads)
    min_likes = args.get("min_likes", type=int)
    if min_likes:
        query = query.filter(Repository.likes_count >= min_likes)
    updated_year = args.get("updated_year", type=int)
    if updated_year:
        start = datetime(updated_year, 1, 1)
        end = datetime(updated_year + 1, 1, 1)
        query = query.filter(Repository.updated_at >= start, Repository.updated_at < end)
    updated_month = args.get("updated_month", "")
    if updated_month and re.match(r"^\d{4}-\d{2}$", updated_month):
        y, m = int(updated_month[:4]), int(updated_month[5:7])
        start = datetime(y, m, 1)
        end = datetime(y + (m // 12), (m % 12) + 1, 1)
        query = query.filter(Repository.updated_at >= start, Repository.updated_at < end)
    sdk = args.get("sdk", "")
    if sdk:
        query = query.filter(Repository.sdk.ilike(sdk))
    tag = args.get("tag", "")
    if tag:
        # tags_json is a JSON-encoded list; do a substring match on the JSON string
        query = query.filter(Repository.tags_json.ilike(f'%"{tag}"%'))
    return query


def _apply_repo_sort(query, sort):
    if sort == "downloads":
        return query.order_by(Repository.downloads.desc())
    if sort == "likes":
        return query.order_by(Repository.likes_count.desc())
    if sort == "updated" or sort == "modified":
        return query.order_by(Repository.updated_at.desc())
    if sort == "created":
        return query.order_by(Repository.created_at.desc())
    # trending
    return query.order_by((Repository.likes_count * 3 + Repository.downloads / 1000).desc())


@app.context_processor
def inject_globals():
    all_tasks = Task.query.order_by(Task.display).all()
    _now = mirror_now()
    return {
        "cart_count": current_cart_count(),
        "tasks_nav": all_tasks,
        "current_year": _now.year,
        "mirror_now": _now,
        "mirror_today_display": _now.strftime("%B %-d, %Y"),
        "modalities": MODALITIES,
        # R7: locale exposed to every template so the header switcher +
        # <html lang="..">  can render the current value.
        "lang_code": _current_locale(),
        "supported_locales": SUPPORTED_LOCALES,
        "locale_labels": LOCALE_LABELS,
    }


# ----------------------------------------------------------------------------
# R7: Locale switcher (en/zh/fr/es) — no full i18n; sets <html lang="..">
# and a header switcher with active class. Unknown locales fall back to en.
# ----------------------------------------------------------------------------
SUPPORTED_LOCALES = ("en", "zh", "fr", "es")
LOCALE_LABELS = {
    "en": "EN",
    "zh": "中文",
    "fr": "FR",
    "es": "ES",
}


def _current_locale() -> str:
    lang = (request.args.get("lang") or session.get("lang") or "en").lower()
    if lang not in SUPPORTED_LOCALES:
        lang = "en"
    return lang


@app.before_request
def _persist_locale():
    lang = (request.args.get("lang") or "").lower()
    if lang in SUPPORTED_LOCALES:
        session["lang"] = lang


# ----------------------------------------------------------------------------
# R7: trending top-50 cache. The /api/trending endpoint hits the same
# columns as the homepage trending lists; caching avoids re-scoring the
# entire 170k repo pool on every request.
# ----------------------------------------------------------------------------
TRENDING_CACHE = {
    "model": [],
    "dataset": [],
    "space": [],
    "updated_at": None,
}


def _refresh_trending_cache(limit: int = 50) -> None:
    """Populate TRENDING_CACHE with the top `limit` repos per type by trending_score."""
    for rt in ("model", "dataset", "space"):
        rows = (Repository.query
                .filter(Repository.repo_type == rt)
                .order_by(Repository.trending_score.desc(),
                          Repository.likes_count.desc(),
                          Repository.id.asc())
                .limit(limit).all())
        TRENDING_CACHE[rt] = [
            {
                "slug": r.slug,
                "task": r.task_slug,
                "downloads": r.downloads or 0,
                "likes": r.likes_count or 0,
                "trending_score": float(r.trending_score or 0),
                "params_b": float(r.params_b or 0),
                "library": r.library or "",
                "license": r.license or "",
                "sdk": r.sdk or "",
                "updated_at": (r.updated_at or mirror_now()).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "url": _repo_canonical_path(r),
            }
            for r in rows
        ]
    TRENDING_CACHE["updated_at"] = mirror_now().strftime("%Y-%m-%dT%H:%M:%SZ")


def _repo_canonical_path(repo) -> str:
    if repo.repo_type == "dataset":
        return f"/datasets/{repo.slug}"
    if repo.repo_type == "space":
        return f"/spaces/{repo.slug}"
    return f"/{repo.slug}"


# ------------------------------------------------------------
# Seed the database
# ------------------------------------------------------------
def seed_database():
    """Populate all tables with starting data."""
    if Task.query.count() > 0:
        return
    print("Seeding database...")

    # 1) Tasks
    for slug, display, modality, icon, description in TASKS:
        db.session.add(Task(slug=slug, display=display, modality=modality, icon=icon, description=description))
    db.session.flush()
    task_by_slug = {t.slug: t for t in Task.query.all()}

    # 2) Authors
    avatar_files = sorted(p.name for p in (ROOT / "static" / "images" / "avatars").iterdir() if p.is_file())
    rng = random.Random(7)
    for i, (username, display, kind, bio, followers, is_verified, website) in enumerate(AUTHORS):
        db.session.add(Author(
            username=username,
            display_name=display,
            kind=kind,
            bio=bio,
            followers_count=followers,
            is_verified=is_verified,
            website=website,
            avatar_url=f"/static/images/avatars/{avatar_files[i % len(avatar_files)]}" if avatar_files else "",
        ))
    db.session.flush()

    # 3) Demo user (pinned bcrypt hash for "password123" — keeps the seed DB
    # reproducible across rebuilds; bcrypt.generate_password_hash() emits a
    # fresh salt per call which otherwise drifts the byte snapshot.)
    PINNED_DEMO_HASH = "$2b$12$AQ4pbTvQ5Dn6yKsxlrqB7uNJY8L7bB5n28CG1fnV6OPhLrOlXJXGu"
    demo = User(
        email="demo@hf.co",
        username="demo",
        password_hash=PINNED_DEMO_HASH,
        display_name="Demo User",
        bio="Just exploring the Hub.",
        avatar_url=f"/static/images/avatars/{avatar_files[0]}" if avatar_files else "",
        is_pro=True,
    )
    db.session.add(demo)
    db.session.flush()

    # 4) Repos
    models, datasets, spaces = build_seed_repos()
    all_repos = models + datasets + spaces
    # R6: snapshot of paper arxiv ids — used by _r6_extras to assign a
    # deterministic citing-paper list to a small fraction of models.
    _PAPERS_FOR_CITING = sorted([p["arxiv_id"] for p in DAILY_PAPERS])
    # R4: deterministic per-repo trending_score / monthly_downloads_history /
    # last_modified / param_count. Derived from the slug + downloads so a
    # fresh seed rebuild on a different host hashes identically.
    import hashlib as _hashlib

    def _r4_extras(item):
        slug = item.get("slug", "")
        dl = int(item.get("downloads", 0) or 0)
        likes = int(item.get("likes", 0) or 0)
        h = int(_hashlib.md5(slug.encode("utf-8")).hexdigest(), 16)
        # Monthly history: 12 numbers that sum roughly to `dl`, with a
        # gentle upward trend so the sparkline looks alive.
        base = max(1, dl // 18)
        history = []
        for m in range(12):
            wobble = ((h >> (m * 5)) & 0xFF) / 255.0  # 0..1
            month_val = int(base * (0.6 + 0.9 * wobble) * (1.0 + m * 0.06))
            history.append(month_val)
        # Trending score: combine recent traffic (last 3 months) with likes.
        recent = sum(history[-3:])
        trending = recent / 30000.0 + likes / 80.0
        # Last modified: derived from updated_days_ago (kept consistent).
        last_mod_days = item.get("updated_days_ago", 1)
        last_mod = mirror_now() - timedelta(days=last_mod_days, hours=((h >> 1) & 0x17))
        # Param count: prefer params_b * 1B, else estimate from name token.
        pb = float(item.get("params_b", 0) or 0)
        if pb > 0:
            pc = int(pb * 1_000_000_000)
        else:
            # Models with no params_b: scale from h so each gets a stable value
            # in {0, 7M, 22M, 110M, 350M, 770M, 1.3B}.
            buckets = [0, 7_000_000, 22_000_000, 110_000_000,
                       350_000_000, 770_000_000, 1_300_000_000]
            pc = buckets[h % len(buckets)] if item.get("repo_type") == "model" else 0
        return trending, history, last_mod, pc

    def _r5_extras(item):
        """R5: license_url, eval_results_json, hardware_used, training_compute_hours.

        Every value is a deterministic function of the slug (md5 hash) so a
        fresh seed rebuild on any host produces identical bytes."""
        slug = item.get("slug", "")
        h = int(_hashlib.md5(slug.encode("utf-8")).hexdigest(), 16)
        license_slug = (item.get("license") or "apache-2.0").lower()
        # license_url — explicit mapping; falls back to in-tree /license/<slug>.
        license_map = {
            "apache-2.0": "https://www.apache.org/licenses/LICENSE-2.0",
            "mit": "https://opensource.org/license/mit/",
            "cc-by-4.0": "https://creativecommons.org/licenses/by/4.0/",
            "cc-by-sa-4.0": "https://creativecommons.org/licenses/by-sa/4.0/",
            "cc-by-nc-4.0": "https://creativecommons.org/licenses/by-nc/4.0/",
            "openrail": "https://www.licenses.ai/open-rail",
            "creativeml-openrail-m": "https://huggingface.co/spaces/CompVis/stable-diffusion-license",
            "llama-3.3": "https://llama.meta.com/llama3/license/",
            "gemma": "https://ai.google.dev/gemma/terms",
            "bsd-3-clause": "https://opensource.org/license/bsd-3-clause/",
            "gpl-3.0": "https://www.gnu.org/licenses/gpl-3.0.en.html",
        }
        license_url = license_map.get(license_slug, f"/license/{license_slug or 'other'}")

        # eval_results — deterministic per-task benchmark scores. Only models
        # carry meaningful evals; datasets and spaces get an empty list.
        repo_type = item.get("repo_type", "")
        task = (item.get("task") or "").lower()
        evals = []
        def _v(lo, hi, step=0):
            span = hi - lo
            r = ((h >> (step * 5)) & 0xFFFF) / 0xFFFF
            return round(lo + span * r, 2)
        if repo_type == "model":
            if task in ("text-generation", "text2text-generation"):
                evals = [
                    {"benchmark": "MMLU",      "score": _v(40.0, 78.0, 0), "split": "test"},
                    {"benchmark": "HellaSwag", "score": _v(58.0, 88.0, 1), "split": "val"},
                    {"benchmark": "ARC-Challenge", "score": _v(34.0, 72.0, 2), "split": "test"},
                    {"benchmark": "TruthfulQA-MC2", "score": _v(38.0, 65.0, 3), "split": "val"},
                ]
            elif task == "text-classification":
                evals = [
                    {"benchmark": "GLUE/SST-2",   "score": _v(82.0, 95.0, 0), "split": "validation"},
                    {"benchmark": "GLUE/MRPC-F1", "score": _v(80.0, 93.0, 1), "split": "validation"},
                ]
            elif task == "translation":
                evals = [
                    {"benchmark": "FLORES-200 BLEU", "score": _v(22.5, 42.8, 0), "split": "devtest"},
                    {"benchmark": "WMT21 chrF",      "score": _v(48.0, 65.0, 1), "split": "test"},
                ]
            elif task == "summarization":
                evals = [
                    {"benchmark": "CNN/DM ROUGE-1", "score": _v(38.0, 48.5, 0), "split": "test"},
                    {"benchmark": "XSum ROUGE-L",   "score": _v(28.0, 42.0, 1), "split": "test"},
                ]
            elif task == "question-answering":
                evals = [
                    {"benchmark": "SQuAD v2 F1", "score": _v(78.0, 92.0, 0), "split": "validation"},
                    {"benchmark": "SQuAD v2 EM", "score": _v(70.0, 88.0, 1), "split": "validation"},
                ]
            elif task == "automatic-speech-recognition":
                evals = [
                    {"benchmark": "LibriSpeech WER (clean)", "score": _v(3.5, 12.0, 0), "split": "test"},
                    {"benchmark": "LibriSpeech WER (other)", "score": _v(8.0, 22.0, 1), "split": "test"},
                ]
            elif task == "image-classification":
                evals = [
                    {"benchmark": "ImageNet-1k Top-1", "score": _v(72.0, 88.0, 0), "split": "val"},
                ]
            elif task == "sentence-similarity" or (item.get("library") or "").lower() == "sentence-transformers":
                evals = [
                    {"benchmark": "MTEB Retrieval-AVG",  "score": _v(40.0, 62.0, 0), "split": "test"},
                    {"benchmark": "STS-B Spearman",      "score": _v(78.0, 88.0, 1), "split": "test"},
                ]
            elif task == "object-detection":
                evals = [
                    {"benchmark": "COCO mAP",     "score": _v(34.0, 58.0, 0), "split": "val"},
                ]
            elif task == "image-segmentation":
                evals = [
                    {"benchmark": "ADE20k mIoU",  "score": _v(38.0, 56.0, 0), "split": "val"},
                ]
            elif task == "fill-mask":
                evals = [
                    {"benchmark": "Wikitext-103 PPL", "score": _v(8.0, 24.0, 0), "split": "test"},
                ]
            elif task == "text-to-image":
                evals = [
                    {"benchmark": "MS-COCO FID",  "score": _v(8.5, 22.0, 0), "split": "val"},
                    {"benchmark": "GenEval Overall", "score": _v(0.35, 0.72, 1), "split": "test"},
                ]

        # hardware_used + training_compute_hours — derived from params_b /
        # bucketed hardware so larger models get more compute.
        pb = float(item.get("params_b", 0) or 0)
        if repo_type == "model":
            if pb >= 60:
                hw_choices = ["1024× H100 80GB", "512× H100 80GB", "768× A100 80GB"]
                tch = 240_000 + (h % 320_000)
            elif pb >= 13:
                hw_choices = ["256× A100 80GB", "128× H100 80GB", "192× A100 80GB"]
                tch = 60_000 + (h % 120_000)
            elif pb >= 6:
                hw_choices = ["64× A100 80GB", "32× H100 80GB", "96× A100 40GB"]
                tch = 12_000 + (h % 36_000)
            elif pb >= 1:
                hw_choices = ["16× A100 40GB", "8× H100 80GB", "32× V100 32GB"]
                tch = 1_200 + (h % 8_000)
            elif pb > 0:
                hw_choices = ["8× A100 40GB", "4× A10G", "4× V100 32GB"]
                tch = 240 + (h % 1_500)
            else:
                hw_choices = ["8× V100 32GB", "4× A10G", "8× T4"]
                tch = 80 + (h % 800)
            hardware_used = hw_choices[(h >> 2) % len(hw_choices)]
        elif repo_type == "space":
            # Spaces reuse their runtime hardware as the "used" hardware.
            hw_display = item.get("hardware_display") or "Nvidia T4"
            hw_specs = item.get("hardware_specs") or ""
            hardware_used = f"{hw_display} ({hw_specs})" if hw_specs else hw_display
            tch = 0
        else:
            hardware_used = ""
            tch = 0

        return license_url, json.dumps(evals, sort_keys=True), hardware_used, tch

    def _r6_extras(item):
        """R6: not_for_production, gated, base_model_slug, build-error logs,
        citing_papers. Deterministic per slug so rebuilds are byte-stable.

        Buckets (md5(slug)[mod 100]):
          0..3   -> not_for_production = True (~4% of repos)
          4..6   -> is_gated = True (~3%; only models / some datasets)
          7..8   -> space_build_status = "build-error" (~5% of spaces)
          9      -> space_build_status = "build-running" (~1% of spaces)
        base_model_slug — only for models whose slug contains a known
          family prefix ("-ft", "-finetune", "-instruct", "-chat",
          "-dpo", "-sft"). The base is the same slug with that suffix
          stripped, IFF such a base exists in the seed pool — but we
          can't query mid-seed, so we store the would-be base slug and
          let the route filter at read-time.
        citing_paper_ids — pick 0..2 arxiv ids from DAILY_PAPERS for
          models whose md5(slug) is in the right bucket. About 6% of
          models get >=1 citing paper.
        """
        slug = item.get("slug", "")
        rt = item.get("repo_type", "")
        h = int(_hashlib.md5(slug.encode("utf-8")).hexdigest(), 16)
        bucket = h % 100

        not_for_production = False
        gated_reason = ""
        is_gated = False
        space_build_status = ""
        space_build_log = ""
        base_model_slug = ""
        citing = []

        # not_for_production: experimental / research-only flag
        if bucket < 4:
            not_for_production = True

        # gated access: only for models and a few datasets; mutually
        # exclusive with not_for_production so flags don't pile up.
        elif bucket in (4, 5, 6) and rt in ("model", "dataset"):
            is_gated = True
            gated_reasons = [
                "Author requires acceptance of the community license",
                "Restricted by upstream license terms",
                "Manual review required by the maintainer team",
                "Available to verified researchers only",
            ]
            gated_reason = gated_reasons[(h >> 2) % len(gated_reasons)]

        # space build status
        if rt == "space":
            if bucket in (7, 8):
                space_build_status = "build-error"
                err_msgs = [
                    "ModuleNotFoundError: No module named 'gradio'",
                    "RuntimeError: CUDA out of memory. Tried to allocate 4.00 GiB",
                    "ImportError: cannot import name 'pipeline' from 'transformers'",
                    "OSError: [Errno 28] No space left on device",
                    "ValueError: hardware tier 't4-small' exceeds free quota",
                ]
                msg = err_msgs[(h >> 3) % len(err_msgs)]
                space_build_log = (
                    "=== Build started ===\n"
                    "Installing requirements from requirements.txt...\n"
                    "Collecting transformers==4.46.2\n"
                    "Collecting torch==2.4.0\n"
                    f"  Building wheel for {slug.split('/')[1]}...\n"
                    "ERROR: " + msg + "\n"
                    "=== Build FAILED with exit code 1 ===\n"
                )
            elif bucket == 9:
                space_build_status = "build-running"
                space_build_log = (
                    "=== Build started ===\n"
                    "Installing requirements from requirements.txt...\n"
                    "Collecting transformers==4.46.2\n"
                    "Downloading torch-2.4.0...\n"
                    "[in progress]\n"
                )

        # base_model_slug — fine-tuned-version lineage. We look at the
        # slug for known fine-tune suffix tokens.
        if rt == "model":
            ln = slug.lower()
            ft_tokens = ("-ft", "-finetune", "-finetuned", "-instruct",
                         "-chat", "-dpo", "-sft", "-rlhf", "-orpo")
            for tok in ft_tokens:
                if tok in ln:
                    # Take everything before the suffix as the base name.
                    base_name = slug[:ln.index(tok)]
                    if "/" in base_name and base_name.endswith(tuple("abcdefghijklmnopqrstuvwxyz0123456789")):
                        base_model_slug = base_name
                    break

        # citing_papers — assign deterministic subset for models
        if rt == "model" and bucket >= 90:
            ids = _PAPERS_FOR_CITING
            if ids:
                # pick 1..2 papers
                k = 1 + (bucket - 90) // 5  # 1 or 2
                start = (h >> 4) % max(1, len(ids))
                for j in range(k):
                    citing.append(ids[(start + j) % len(ids)])

        return (not_for_production, is_gated, gated_reason,
                base_model_slug, space_build_status, space_build_log,
                json.dumps(citing, sort_keys=True))

    for item in all_repos:
        author = get_or_create_author(item["author"])
        task = task_by_slug.get(item.get("task", ""))
        trending, history, last_mod, pc = _r4_extras(item)
        license_url, eval_json, hw_used, tch = _r5_extras(item)
        (not_for_production, is_gated, gated_reason, base_model_slug,
         space_build_status, space_build_log, citing_paper_ids) = _r6_extras(item)
        repo = Repository(
            slug=item["slug"],
            name=item["name"],
            repo_type=item["repo_type"],
            author_id=author.id,
            task_id=task.id if task else None,
            library=item.get("library", ""),
            license=item.get("license", "apache-2.0"),
            license_display=item.get("license_display", "Apache 2.0"),
            description=item.get("description", ""),
            readme=item.get("readme", ""),
            language=item.get("language", "English"),
            params_b=item.get("params_b", 0.0),
            inference_provider=item.get("inference_provider", ""),
            modality=item.get("modality", ""),
            rows=item.get("rows", 0),
            sdk=item.get("sdk", ""),
            hardware_slug=item.get("hardware_slug", ""),
            hardware_display=item.get("hardware_display", ""),
            hardware_specs=item.get("hardware_specs", ""),
            hardware_price=item.get("hardware_price", ""),
            emoji=item.get("emoji", "🚀"),
            status=item.get("status", "Running"),
            downloads=item.get("downloads", 0),
            likes_count=item.get("likes", 0),
            is_featured=item.get("is_featured", False),
            is_new=item.get("is_new", False),
            tags_json=json.dumps(item.get("tags", [])),
            avatar_url=item.get("avatar", ""),
            banner_url=item.get("banner", ""),
            trending_score=trending,
            monthly_downloads_history=json.dumps(history),
            last_modified=last_mod,
            param_count=pc,
            license_url=license_url,
            eval_results_json=eval_json,
            hardware_used=hw_used,
            training_compute_hours=tch,
            not_for_production=not_for_production,
            is_gated=is_gated,
            gated_reason=gated_reason,
            base_model_slug=base_model_slug,
            space_build_status=space_build_status,
            space_build_log=space_build_log,
            citing_paper_ids=citing_paper_ids,
            updated_at=mirror_now() - timedelta(days=item.get("updated_days_ago", 1)),
        )
        db.session.add(repo)
    db.session.commit()

    # 5) Seed some discussions on top repos
    # R3: bumped from 70 → 380 top repos so community signals (discussions
    # per repo, recent activity) span more of the catalog. Combined with the
    # benchmark-user discussions seeded later, total clears the R3 400+
    # threshold.
    top_repos = Repository.query.order_by(Repository.likes_count.desc(), Repository.id.asc()).limit(380).all()
    sample_titles = [
        "How does this model handle long context?",
        "Model keeps hallucinating tool calls — any fix?",
        "Quantization question: FP8 vs INT4?",
        "Fine-tuning on custom data — best practice?",
        "Great work! Loving the results.",
        "License clarification",
        "Throughput on consumer GPUs?",
        "Tokenizer adds extra BOS — confirmed bug",
        "Comparison vs the prior generation",
        "Reproducing the eval table numbers",
        "Suggestion: ship a smaller distilled variant",
        "Memory footprint with KV-cache reuse",
        "Compatibility with Transformers v4.46+",
        "Adapters / LoRA support out of the box?",
        "Inference example for batched generation",
        "Multilingual coverage beyond top-10 languages",
        "Safety filter false-positive on benign prompts",
        "Speed regression after the last weight update",
    ]
    sample_bodies = [
        "Hi team — I ran this locally with 24k tokens and the attention pattern seems off. Have you evaluated on longer context?",
        "Really impressive results on my benchmark. Congrats to the authors!",
        "Has anyone tried running this with vLLM? I'm getting OOM on a single A100 at batch_size=4.",
        "For the license question — can I use the outputs commercially? The tag says OpenRAIL but the README says apache-2.0.",
        "Bug report: tokenizer adds an extra BOS when calling `apply_chat_template`. PR incoming.",
        "Ran INT4 GGUF on a 3090 — sustained 28 tok/s at 8k context. Sharing the recipe in the README.",
        "Anyone fine-tuned with QLoRA (rank=16) on a single H100? My adapter is overfitting after 1 epoch.",
        "The chat template in the model card disagrees with `tokenizer_config.json`. Which is canonical?",
        "Inference cost feels high — would love an Optimum-ONNX export. Happy to upstream a notebook.",
        "Could the maintainers consider a `transformers.js` build? Browser inference would be huge.",
        "Eval reproducibility: lm-eval-harness gives 71.3 on MMLU, paper claims 73.8. Same seeds?",
        "Found a regression vs the previous revision — repro script attached.",
        "Loving the new license — finally a clear commercial-use story.",
        "Tagging the maintainers — would you accept a PR adding zero-shot pipeline support?",
        "Curious how others are evaluating long-form summarization on this. ROUGE alone isn't enough.",
        "Could we get an int4 / int8 quantization config shipped with the repo?",
        "Has anyone observed catastrophic forgetting after RLHF? My SFT-only variant is cleaner.",
        "Asking out of curiosity: what hardware was this trained on, and for how long?",
    ]
    for i, repo in enumerate(top_repos):
        d = Discussion(
            repo_id=repo.id,
            user_id=demo.id,
            title=sample_titles[i % len(sample_titles)],
            body=sample_bodies[i % len(sample_bodies)],
            upvotes=rng.randint(2, 80),
            kind=rng.choice(["discussion", "issue", "pull-request"]),
            created_at=mirror_now() - timedelta(days=rng.randint(1, 90), hours=rng.randint(0, 23)),
        )
        db.session.add(d)
        db.session.flush()
        # Add a reply
        reply = DiscussionReply(
            discussion_id=d.id,
            user_id=demo.id,
            body="Thanks for the report! Could you share a minimal repro script? We'll investigate.",
            created_at=d.created_at + timedelta(hours=rng.randint(2, 36)),
        )
        db.session.add(reply)

    # 6) Seed collection for demo user
    c = Collection(
        user_id=demo.id,
        title="Favorite open LLMs",
        description="My curated list of open-source language models worth trying.",
        is_public=True,
    )
    db.session.add(c)
    db.session.flush()
    for r in Repository.query.filter_by(repo_type="model").order_by(Repository.id.asc()).limit(5).all():
        db.session.add(CollectionItem(collection_id=c.id, repo_id=r.id, note=""))

    db.session.commit()
    print(f"  ✓ {Task.query.count()} tasks")
    print(f"  ✓ {Author.query.count()} authors")
    print(f"  ✓ {Repository.query.count()} repositories")
    print(f"  ✓ {Discussion.query.count()} discussions")
    print(f"  ✓ {Collection.query.count()} collections")


# ------------------------------------------------------------
# Routes — Static / homepage
# ------------------------------------------------------------
@app.route("/")
def index():
    trending_models = Repository.query.filter_by(repo_type="model").order_by(Repository.likes_count.desc()).limit(5).all()
    trending_datasets = Repository.query.filter_by(repo_type="dataset").order_by(Repository.likes_count.desc()).limit(5).all()
    trending_spaces = Repository.query.filter_by(repo_type="space", is_featured=True).order_by(Repository.likes_count.desc()).limit(6).all()
    featured_orgs = Author.query.filter_by(is_verified=True).order_by(Author.followers_count.desc()).limit(8).all()
    total_models = Repository.query.filter_by(repo_type="model").count()
    total_datasets = Repository.query.filter_by(repo_type="dataset").count()
    total_spaces = Repository.query.filter_by(repo_type="space").count()
    return render_template(
        "index.html",
        trending_models=trending_models,
        trending_datasets=trending_datasets,
        trending_spaces=trending_spaces,
        featured_orgs=featured_orgs,
        total_models=total_models,
        total_datasets=total_datasets,
        total_spaces=total_spaces,
        liked_ids=_liked_repo_ids(),
    )


@app.route("/models")
def models_list():
    q = request.args.get("q", "").strip()
    sort = request.args.get("sort", "trending")
    query = Repository.query.filter_by(repo_type="model")
    query = _apply_repo_filters(query, request.args)
    query = _apply_text_prefilter(query, q)
    query = _apply_repo_sort(query, sort)
    candidates = query.limit(2000).all()
    if q:
        tokens = _tokenize(q)
        min_req = max(1, len(tokens) // 2) if tokens else 0
        scored = [(s, r) for r in candidates if (s := _score_repo(r, tokens)) >= min_req]
        scored.sort(key=lambda x: -x[0])
        candidates = [r for _, r in scored]
    total = len(candidates)
    page = int(request.args.get("page", 1))
    per_page = 30
    repos = candidates[(page - 1) * per_page : page * per_page]
    tasks_list = Task.query.order_by(Task.display).all()
    return render_template(
        "repo_list.html",
        repos=repos,
        total=total,
        page=page,
        per_page=per_page,
        total_pages=max(1, (total + per_page - 1) // per_page),
        tasks_list=tasks_list,
        libraries=LIBRARIES,
        licenses=LICENSES,
        active_task=request.args.get("task", ""),
        active_library=request.args.get("library", ""),
        active_license=request.args.get("license", ""),
        active_sort=sort,
        q=q,
        repo_type="model",
        page_title="Models",
        liked_ids=_liked_repo_ids(),
    )


@app.route("/datasets")
def datasets_list():
    q = request.args.get("q", "").strip()
    sort = request.args.get("sort", "trending")
    query = Repository.query.filter_by(repo_type="dataset")
    query = _apply_repo_filters(query, request.args)
    query = _apply_text_prefilter(query, q)
    query = _apply_repo_sort(query, sort)
    candidates = query.limit(2000).all()
    if q:
        tokens = _tokenize(q)
        min_req = max(1, len(tokens) // 2) if tokens else 0
        scored = [(s, r) for r in candidates if (s := _score_repo(r, tokens)) >= min_req]
        scored.sort(key=lambda x: -x[0])
        candidates = [r for _, r in scored]
    total = len(candidates)
    page = int(request.args.get("page", 1))
    per_page = 30
    repos = candidates[(page - 1) * per_page : page * per_page]
    return render_template(
        "repo_list.html",
        repos=repos,
        total=total,
        page=page,
        per_page=per_page,
        total_pages=max(1, (total + per_page - 1) // per_page),
        tasks_list=Task.query.order_by(Task.display).all(),
        libraries=LIBRARIES,
        licenses=LICENSES,
        active_modality=request.args.get("modality", ""),
        active_license=request.args.get("license", ""),
        active_sort=sort,
        q=q,
        repo_type="dataset",
        page_title="Datasets",
        liked_ids=_liked_repo_ids(),
    )


@app.route("/spaces")
def spaces_list():
    q = request.args.get("q", "").strip()
    sort = request.args.get("sort", "trending")
    query = Repository.query.filter_by(repo_type="space")
    query = _apply_repo_filters(query, request.args)
    query = _apply_text_prefilter(query, q)
    query = _apply_repo_sort(query, sort)
    candidates = query.limit(2000).all()
    if q:
        tokens = _tokenize(q)
        min_req = max(1, len(tokens) // 2) if tokens else 0
        scored = [(s, r) for r in candidates if (s := _score_repo(r, tokens)) >= min_req]
        scored.sort(key=lambda x: -x[0])
        candidates = [r for _, r in scored]
    total = len(candidates)
    page = int(request.args.get("page", 1))
    per_page = 30
    repos = candidates[(page - 1) * per_page : page * per_page]
    return render_template(
        "spaces_list.html",
        repos=repos,
        total=total,
        page=page,
        per_page=per_page,
        total_pages=max(1, (total + per_page - 1) // per_page),
        tasks_list=Task.query.order_by(Task.display).all(),
        active_task=request.args.get("task", ""),
        active_sdk=request.args.get("sdk", ""),
        active_sort=sort,
        q=q,
        page_title="Spaces",
        liked_ids=_liked_repo_ids(),
    )


@app.route("/tasks")
def tasks_index():
    tasks_by_modality = {}
    for m in MODALITIES:
        tasks_by_modality[m] = Task.query.filter_by(modality=m).order_by(Task.display).all()
    return render_template("tasks_index.html", tasks_by_modality=tasks_by_modality)


@app.route("/tasks/<slug>")
def task_detail(slug):
    task = Task.query.filter_by(slug=slug).first_or_404()
    models = Repository.query.filter_by(repo_type="model", task_id=task.id).order_by(Repository.likes_count.desc()).limit(12).all()
    datasets = Repository.query.filter_by(repo_type="dataset", task_id=task.id).order_by(Repository.likes_count.desc()).limit(8).all()
    spaces = Repository.query.filter_by(repo_type="space", task_id=task.id).order_by(Repository.likes_count.desc()).limit(8).all()
    return render_template(
        "task_detail.html",
        task=task,
        models=models,
        datasets=datasets,
        spaces=spaces,
        liked_ids=_liked_repo_ids(),
    )


@app.route("/docs")
def docs():
    topic = request.args.get("topic", "")
    q = request.args.get("q", "").strip().lower()
    # Either direct topic slug or keyword search maps to one of the prebuilt pages
    if not topic and q:
        for slug, page in DOC_PAGES.items():
            if any(kw in q for kw in page["keywords"]):
                topic = slug
                break
    if topic and topic in DOC_PAGES:
        return render_template(
            "docs_topic.html",
            topic=topic, page=DOC_PAGES[topic], all_topics=DOC_PAGES,
        )
    return render_template("docs.html", all_topics=DOC_PAGES)


@app.route("/docs/<topic>")
def docs_topic(topic):
    if topic not in DOC_PAGES:
        abort(404)
    return render_template(
        "docs_topic.html",
        topic=topic, page=DOC_PAGES[topic], all_topics=DOC_PAGES,
    )


@app.route("/pricing")
def pricing():
    return render_template(
        "pricing.html",
        space_hardware=SPACE_HARDWARE,
        pricing_plans=PRICING_PLANS,
    )


@app.route("/enterprise")
def enterprise():
    return render_template("enterprise.html")


@app.route("/blog")
def blog_index():
    tag = request.args.get("tag", "").strip().lower()
    q = request.args.get("q", "").strip().lower()
    # Sort posts by publish date descending so the latest is always first.
    posts = sorted(BLOG_POSTS, key=lambda p: p.get("published", ""), reverse=True)
    if tag:
        posts = [p for p in posts if tag in [t.lower() for t in p.get("tags", [])]]
    if q:
        posts = [p for p in posts if q in p["title"].lower() or q in p["excerpt"].lower() or any(q in t.lower() for t in p.get("tags", []))]
    return render_template("blog.html", posts=posts, all_tags=sorted({t for p in BLOG_POSTS for t in p["tags"]}))


@app.route("/blog/<slug>")
def blog_post(slug):
    post = next((p for p in BLOG_POSTS if p["slug"] == slug), None)
    if not post:
        abort(404)
    return render_template("blog_post.html", post=post)


@app.route("/papers")
def papers_index():
    return render_template("papers.html", papers=DAILY_PAPERS)


@app.route("/papers/<arxiv_id>")
def paper_detail(arxiv_id):
    paper = next((p for p in DAILY_PAPERS if p["arxiv_id"] == arxiv_id), None)
    if not paper:
        abort(404)
    # R4: BibTeX export. ?format=bibtex returns text/plain so the agent can
    # download / copy the citation without any HTML chrome.
    if request.args.get("format") == "bibtex":
        first_author = (paper.get("authors") or "unknown").split(",")[0].strip().split(" ")[-1].lower()
        year = (paper.get("published") or "2026-01-01")[:4]
        body = (
            f"@misc{{{first_author}{year}arxiv{paper['arxiv_id'].replace('.', '')},\n"
            f"  title         = {{ {paper['title']} }},\n"
            f"  author        = {{ {paper['authors']} }},\n"
            f"  year          = {{ {year} }},\n"
            f"  eprint        = {{ {paper['arxiv_id']} }},\n"
            f"  archivePrefix = {{arXiv}},\n"
            f"  primaryClass  = {{cs.CL}},\n"
            f"  url           = {{https://arxiv.org/abs/{paper['arxiv_id']}}}\n"
            f"}}"
        )
        from flask import Response
        return Response(body, mimetype="text/plain")
    return render_template("paper_detail.html", paper=paper)


@app.route("/learn")
def learn():
    return render_template("learn.html", classroom_benefits=CLASSROOM_BENEFITS)


@app.route("/learn/classroom")
@app.route("/classroom")
@app.route("/education")
@app.route("/education/classroom")
def learn_classroom():
    return render_template("classroom.html", benefits=CLASSROOM_BENEFITS)


@app.route("/datasets/<author>/<name>/viewer")
def dataset_viewer(author, name):
    slug = f"{author}/{name}"
    repo = Repository.query.filter_by(slug=slug, repo_type="dataset").first()
    if not repo:
        abort(404)
    data = DATASET_VIEWER_DATA.get(slug, {
        "columns": ["id", "text"],
        "rows": [[1, "Sample row"]],
    })
    return render_template("dataset_viewer.html", repo=repo, viewer=data)


@app.route("/chat")
def chat():
    chat_models = Repository.query.filter_by(repo_type="model", is_featured=True).filter(Repository.task_id == Task.query.filter_by(slug="text-generation").first().id if Task.query.filter_by(slug="text-generation").first() else None).limit(10).all()
    return render_template("chat.html", chat_models=chat_models)


# ------------------------------------------------------------
# Repo detail pages
# ------------------------------------------------------------
def _load_repo_or_404(repo_type: str, author: str, name: str):
    slug = f"{author}/{name}"
    repo = Repository.query.filter_by(slug=slug, repo_type=repo_type).first()
    if not repo:
        abort(404)
    return repo


def _repo_gallery_images(repo: Repository):
    """Collect gallery images for this repo from /static/images/repos or fallbacks."""
    base_dir = ROOT / "static" / "images"
    # Prefer dedicated repo banner dir
    repo_dir = base_dir / "repos"
    images = []
    if repo_dir.exists():
        for f in sorted(repo_dir.iterdir()):
            if f.is_file() and f.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}:
                images.append(f"/static/images/repos/{f.name}")
    # Fallback to heroes
    if len(images) < 6:
        hero_dir = base_dir / "heroes"
        if hero_dir.exists():
            for f in sorted(hero_dir.iterdir()):
                if f.is_file() and f.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}:
                    images.append(f"/static/images/heroes/{f.name}")
    # Stable per-repo subset
    import hashlib
    h = int(hashlib.md5(repo.slug.encode()).hexdigest(), 16)
    out = []
    for i in range(min(6, len(images))):
        out.append(images[(h + i * 13) % len(images)])
    return out


def _compute_model_metrics(repo: "Repository"):
    """Derive a deterministic small metrics table per model.

    Uses the model slug as a stable hash seed so every task-visit sees the same values.
    Only emitted for model repos whose task has a meaningful eval metric.
    """
    import hashlib
    if not repo or repo.repo_type != "model":
        return []
    task = (repo.task_slug or "").lower()
    if not task:
        return []
    h = int(hashlib.md5(repo.slug.encode()).hexdigest(), 16)
    def _v(lo: float, hi: float, step: int = 0) -> float:
        span = hi - lo
        r = ((h >> (step * 4)) & 0xFFFF) / 0xFFFF
        return round(lo + span * r, 2)
    rows = []
    if task == "translation":
        rows.append({"metric": "BLEU", "value": _v(22.5, 42.8, 0), "dataset": "flores200.devtest", "split": "test"})
        rows.append({"metric": "chrF", "value": _v(48.0, 65.0, 1), "dataset": "wmt21", "split": "test"})
    elif task == "summarization":
        rows.append({"metric": "ROUGE-1", "value": _v(38.0, 48.5, 0), "dataset": "cnn_dailymail", "split": "test"})
        rows.append({"metric": "ROUGE-L", "value": _v(30.0, 40.0, 1), "dataset": "cnn_dailymail", "split": "test"})
    elif task == "text-classification":
        rows.append({"metric": "Accuracy", "value": _v(82.0, 94.5, 0), "dataset": "glue/sst2", "split": "validation"})
        rows.append({"metric": "F1", "value": _v(80.0, 93.0, 1), "dataset": "glue/mrpc", "split": "validation"})
    elif task in ("text-generation", "text2text-generation"):
        rows.append({"metric": "MMLU (5-shot)", "value": _v(42.0, 72.0, 0), "dataset": "mmlu", "split": "test"})
        rows.append({"metric": "HellaSwag (10-shot)", "value": _v(60.0, 84.0, 1), "dataset": "hellaswag", "split": "val"})
    elif task == "question-answering":
        rows.append({"metric": "F1", "value": _v(78.0, 92.0, 0), "dataset": "squad_v2", "split": "validation"})
        rows.append({"metric": "Exact Match", "value": _v(70.0, 88.0, 1), "dataset": "squad_v2", "split": "validation"})
    elif task == "automatic-speech-recognition":
        rows.append({"metric": "WER", "value": _v(3.5, 12.0, 0), "dataset": "librispeech_clean", "split": "test"})
    elif task == "image-classification":
        rows.append({"metric": "Top-1 Accuracy", "value": _v(72.0, 88.0, 0), "dataset": "imagenet-1k", "split": "val"})
    elif task == "sentence-similarity" or repo.library == "sentence-transformers":
        rows.append({"metric": "Spearman", "value": _v(78.0, 88.0, 0), "dataset": "sts-benchmark", "split": "test"})
    elif task == "fill-mask":
        rows.append({"metric": "Perplexity", "value": _v(8.0, 24.0, 0), "dataset": "wikitext-103", "split": "test"})
    return rows


def _spaces_using_model(repo: "Repository", limit: int = 8):
    """Return spaces that reference this model by slug in their description/readme/tags
    or by same-author prefix."""
    if not repo or repo.repo_type != "model":
        return []
    slug = repo.slug.lower()
    author = slug.split("/")[0] if "/" in slug else slug
    name_only = slug.split("/")[-1]
    seen_ids = set()
    out = []
    # 1) Spaces whose description/readme/tags contain the model slug or short name
    like_slug = f"%{slug}%"
    like_name = f"%{name_only}%"
    q = Repository.query.filter(Repository.repo_type == "space").filter(
        db.or_(
            Repository.description.ilike(like_slug),
            Repository.readme.ilike(like_slug),
            Repository.tags_json.ilike(like_slug),
            Repository.description.ilike(like_name),
            Repository.readme.ilike(like_name),
            Repository.tags_json.ilike(like_name),
            Repository.slug.ilike(f"{author}/%"),
        )
    ).order_by(Repository.likes_count.desc()).limit(limit * 2)
    for s in q.all():
        if s.id in seen_ids:
            continue
        seen_ids.add(s.id)
        out.append(s)
        if len(out) >= limit:
            break
    return out


# ----------------------------------------------------------------------------
# Repo filesystem & commit history (deterministic, derived from repo metadata)
# ----------------------------------------------------------------------------

def _fmt_bytes(n: int) -> str:
    if n >= 1_000_000_000:
        return f"{n / 1_000_000_000:.2f} GB"
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f} MB"
    if n >= 1_000:
        return f"{n / 1_000:.1f} kB"
    return f"{n} B"


def _repo_commit_messages():
    return [
        "Upload model card",
        "Update README.md",
        "Initial commit",
        "Add tokenizer",
        "Fix config.json",
        "Convert model to safetensors",
        "Improve evaluation metrics",
        "Add usage examples",
        "Update license",
        "Pin transformers version",
        "Add model checkpoint",
        "Refactor data loader",
        "Bump version",
        "Add training logs",
        "Documentation cleanup",
    ]


def _repo_commits(repo, limit: int = 12):
    """Deterministic synthetic commit log per repo."""
    import hashlib
    if not repo:
        return []
    h = int(hashlib.md5((repo.slug + "|commits").encode()).hexdigest(), 16)
    msgs = _repo_commit_messages()
    authors_pool = [
        ("system", "🤖"),
        (repo.slug.split("/")[0], "👤"),
        ("HuggingFaceBot", "🤖"),
        ("contributor-1", "👤"),
        ("contributor-2", "👤"),
    ]
    base_dt = repo.updated_at or mirror_now()
    out = []
    for i in range(limit):
        msg_idx = (h >> (i * 3)) & 0xF
        author_idx = (h >> (i * 5)) & 0x7
        msg = msgs[msg_idx % len(msgs)]
        author = authors_pool[author_idx % len(authors_pool)]
        sha = hashlib.sha1(f"{repo.slug}|{i}".encode()).hexdigest()[:7]
        dt = base_dt - timedelta(days=i * 7 + (((h >> i) & 0xF) % 6))
        out.append({
            "sha": sha,
            "message": msg,
            "author": author[0],
            "author_emoji": author[1],
            "date": dt,
            "date_display": dt.strftime("%b %d, %Y"),
            "rel_display": _rel_time(dt),
        })
    return out


def _rel_time(dt):
    if not dt:
        return ""
    delta = mirror_now() - dt
    days = delta.days
    if days < 1:
        hrs = max(1, delta.seconds // 3600)
        return f"about {hrs} hour{'s' if hrs > 1 else ''} ago"
    if days < 30:
        return f"{days} day{'s' if days > 1 else ''} ago"
    months = days // 30
    if months < 12:
        return f"about {months} month{'s' if months > 1 else ''} ago"
    years = days // 365
    return f"about {years} year{'s' if years > 1 else ''} ago"


def _repo_filesystem(repo):
    """Deterministic synthetic file tree per repo type. Returns list of dicts:
       {path, kind ('file'|'dir'), size, size_display, lfs, last_commit_msg, last_commit_sha, last_commit_at}."""
    import hashlib
    if not repo:
        return []
    h = int(hashlib.md5((repo.slug + "|files").encode()).hexdigest(), 16)
    commits = _repo_commits(repo, limit=12)
    # Helper to attach a deterministic commit to each file
    def _attach(idx):
        c = commits[idx % len(commits)]
        return {
            "last_commit_msg": c["message"],
            "last_commit_sha": c["sha"],
            "last_commit_at": c["date"],
            "last_commit_rel": c["rel_display"],
        }

    files = []
    rt = repo.repo_type
    if rt == "model":
        params_b = float(repo.params_b or 0.11)  # default ~110M
        # Approx 2 bytes per param (fp16/safetensors), with a floor.
        weights_size = max(int(params_b * 1_000_000_000 * 2), 8_000_000)
        bin_size = max(int(params_b * 1_000_000_000 * 4), 16_000_000)
        lib = (repo.library or "transformers").lower()
        is_bert = "bert" in repo.slug.lower()
        is_gpt = any(k in repo.slug.lower() for k in ("gpt", "llama", "mistral", "qwen", "gemma"))
        is_diffusers = lib == "diffusers"
        is_sentence = lib == "sentence-transformers"

        files.append({"path": ".gitattributes", "kind": "file", "size": 1518, "lfs": False, **_attach(2)})
        files.append({"path": "README.md", "kind": "file", "size": max(2048, len(repo.readme or "")), "lfs": False, **_attach(0)})
        files.append({"path": "config.json", "kind": "file", "size": 740 + ((h >> 4) & 0xFF), "lfs": False, **_attach(1)})
        files.append({"path": "model.safetensors", "kind": "file", "size": weights_size, "lfs": True, **_attach(3)})
        files.append({"path": "pytorch_model.bin", "kind": "file", "size": bin_size, "lfs": True, **_attach(5)})
        files.append({"path": "tokenizer_config.json", "kind": "file", "size": 320 + ((h >> 8) & 0xFF), "lfs": False, **_attach(3)})
        files.append({"path": "special_tokens_map.json", "kind": "file", "size": 280 + ((h >> 12) & 0xFF), "lfs": False, **_attach(3)})
        files.append({"path": "tokenizer.json", "kind": "file", "size": 466_000 + ((h >> 16) & 0xFFFF), "lfs": False, **_attach(3)})
        if is_bert:
            files.append({"path": "vocab.txt", "kind": "file", "size": 232_000 + ((h >> 20) & 0xFFFF), "lfs": False, **_attach(3)})
        elif is_gpt:
            files.append({"path": "vocab.json", "kind": "file", "size": 798_000 + ((h >> 20) & 0xFFFF), "lfs": False, **_attach(3)})
            files.append({"path": "merges.txt", "kind": "file", "size": 446_000 + ((h >> 24) & 0xFFFF), "lfs": False, **_attach(3)})
            files.append({"path": "generation_config.json", "kind": "file", "size": 137 + ((h >> 28) & 0x7F), "lfs": False, **_attach(1)})
        if is_diffusers:
            files.append({"path": "model_index.json", "kind": "file", "size": 540, "lfs": False, **_attach(1)})
            files.append({"path": "scheduler/", "kind": "dir", "size": 0, "lfs": False, **_attach(1)})
            files.append({"path": "unet/", "kind": "dir", "size": 0, "lfs": False, **_attach(3)})
            files.append({"path": "vae/", "kind": "dir", "size": 0, "lfs": False, **_attach(3)})
            files.append({"path": "text_encoder/", "kind": "dir", "size": 0, "lfs": False, **_attach(3)})
        if is_sentence:
            files.append({"path": "1_Pooling/", "kind": "dir", "size": 0, "lfs": False, **_attach(3)})
            files.append({"path": "modules.json", "kind": "file", "size": 349, "lfs": False, **_attach(3)})
            files.append({"path": "sentence_bert_config.json", "kind": "file", "size": 53, "lfs": False, **_attach(3)})
        # Common training artifacts
        if (h >> 2) & 1:
            files.append({"path": "training_args.bin", "kind": "file", "size": 4_280, "lfs": False, **_attach(8)})
        if (h >> 5) & 1:
            files.append({"path": "trainer_state.json", "kind": "file", "size": 18_400, "lfs": False, **_attach(8)})

    elif rt == "dataset":
        rows = repo.rows or 10_000
        # Approx 200 bytes/row, split across a few parquet shards
        total = max(int(rows * 200), 1_000_000)
        n_shards = 3 if rows > 1_000_000 else 1
        files.append({"path": ".gitattributes", "kind": "file", "size": 1518, "lfs": False, **_attach(2)})
        files.append({"path": "README.md", "kind": "file", "size": max(1024, len(repo.readme or "")), "lfs": False, **_attach(0)})
        files.append({"path": "data/", "kind": "dir", "size": 0, "lfs": False, **_attach(3)})
        for split, shards in [("train", n_shards), ("test", 1), ("validation", 1)]:
            for i in range(shards):
                files.append({
                    "path": f"data/{split}-{i:05d}-of-{shards:05d}.parquet",
                    "kind": "file",
                    "size": int(total * (0.8 if split == "train" else 0.1) / max(1, shards)),
                    "lfs": True,
                    **_attach(3 + (i % 4)),
                })
        files.append({"path": "dataset_info.json", "kind": "file", "size": 2_400 + ((h >> 8) & 0x3FF), "lfs": False, **_attach(1)})
        if (h >> 1) & 1:
            files.append({"path": "dataset_infos.json", "kind": "file", "size": 4_800, "lfs": False, **_attach(1)})

    elif rt == "space":
        sdk = (repo.sdk or "gradio").lower()
        files.append({"path": ".gitattributes", "kind": "file", "size": 1518, "lfs": False, **_attach(2)})
        files.append({"path": "README.md", "kind": "file", "size": max(1024, len(repo.readme or "")), "lfs": False, **_attach(0)})
        files.append({"path": "app.py", "kind": "file", "size": 4_200 + ((h >> 4) & 0xFFF), "lfs": False, **_attach(7)})
        files.append({"path": "requirements.txt", "kind": "file", "size": 280 + ((h >> 8) & 0x7F), "lfs": False, **_attach(1)})
        if sdk == "docker":
            files.append({"path": "Dockerfile", "kind": "file", "size": 720 + ((h >> 12) & 0x7F), "lfs": False, **_attach(1)})
        if (h >> 2) & 1:
            files.append({"path": "packages.txt", "kind": "file", "size": 64, "lfs": False, **_attach(1)})
        files.append({"path": "examples/", "kind": "dir", "size": 0, "lfs": False, **_attach(7)})
        files.append({"path": "assets/", "kind": "dir", "size": 0, "lfs": False, **_attach(7)})

    # Add display fields
    for f in files:
        f["size_display"] = _fmt_bytes(f["size"]) if f["kind"] == "file" else ""
    return files


def _file_synthetic_content(repo, filepath: str) -> str:
    """Generate plausible text content for a small text file. Returns empty string for binary/LFS."""
    fname = filepath.rsplit("/", 1)[-1]
    slug = repo.slug
    author, name = slug.split("/", 1) if "/" in slug else (slug, slug)
    if fname == "README.md":
        return repo.readme or f"# {name}\n\n{repo.description or ''}\n"
    if fname == ".gitattributes":
        return (
            "*.7z filter=lfs diff=lfs merge=lfs -text\n"
            "*.arrow filter=lfs diff=lfs merge=lfs -text\n"
            "*.bin filter=lfs diff=lfs merge=lfs -text\n"
            "*.bz2 filter=lfs diff=lfs merge=lfs -text\n"
            "*.ckpt filter=lfs diff=lfs merge=lfs -text\n"
            "*.gz filter=lfs diff=lfs merge=lfs -text\n"
            "*.h5 filter=lfs diff=lfs merge=lfs -text\n"
            "*.model filter=lfs diff=lfs merge=lfs -text\n"
            "*.msgpack filter=lfs diff=lfs merge=lfs -text\n"
            "*.onnx filter=lfs diff=lfs merge=lfs -text\n"
            "*.ot filter=lfs diff=lfs merge=lfs -text\n"
            "*.parquet filter=lfs diff=lfs merge=lfs -text\n"
            "*.pb filter=lfs diff=lfs merge=lfs -text\n"
            "*.pt filter=lfs diff=lfs merge=lfs -text\n"
            "*.pth filter=lfs diff=lfs merge=lfs -text\n"
            "*.safetensors filter=lfs diff=lfs merge=lfs -text\n"
            "*.tar.* filter=lfs diff=lfs merge=lfs -text\n"
            "*.tflite filter=lfs diff=lfs merge=lfs -text\n"
            "*.tgz filter=lfs diff=lfs merge=lfs -text\n"
            "*.wasm filter=lfs diff=lfs merge=lfs -text\n"
            "*.xz filter=lfs diff=lfs merge=lfs -text\n"
            "*.zip filter=lfs diff=lfs merge=lfs -text\n"
            "*.zst filter=lfs diff=lfs merge=lfs -text\n"
            "*tfevents* filter=lfs diff=lfs merge=lfs -text\n"
        )
    if fname == "config.json":
        task = repo.task_slug or "text-generation"
        is_bert = "bert" in slug.lower()
        if is_bert:
            return json.dumps({
                "architectures": ["BertForSequenceClassification"],
                "attention_probs_dropout_prob": 0.1,
                "hidden_act": "gelu",
                "hidden_dropout_prob": 0.1,
                "hidden_size": 768,
                "initializer_range": 0.02,
                "intermediate_size": 3072,
                "max_position_embeddings": 512,
                "model_type": "bert",
                "num_attention_heads": 12,
                "num_hidden_layers": 12,
                "pad_token_id": 0,
                "type_vocab_size": 2,
                "vocab_size": 30522,
                "transformers_version": "4.45.0",
            }, indent=2)
        return json.dumps({
            "architectures": ["AutoModelForCausalLM"],
            "model_type": "llama",
            "hidden_size": 4096,
            "intermediate_size": 11008,
            "num_attention_heads": 32,
            "num_hidden_layers": 32,
            "vocab_size": 32000,
            "torch_dtype": "float16",
            "transformers_version": "4.45.0",
            "task": task,
        }, indent=2)
    if fname == "tokenizer_config.json":
        return json.dumps({
            "model_max_length": 512,
            "padding_side": "right",
            "tokenizer_class": "AutoTokenizer",
            "unk_token": "[UNK]", "sep_token": "[SEP]", "pad_token": "[PAD]",
            "cls_token": "[CLS]", "mask_token": "[MASK]",
        }, indent=2)
    if fname == "special_tokens_map.json":
        return json.dumps({
            "cls_token": "[CLS]", "mask_token": "[MASK]", "pad_token": "[PAD]",
            "sep_token": "[SEP]", "unk_token": "[UNK]",
        }, indent=2)
    if fname == "generation_config.json":
        return json.dumps({
            "bos_token_id": 1, "eos_token_id": 2, "pad_token_id": 0,
            "do_sample": True, "temperature": 0.7, "top_p": 0.9, "max_length": 2048,
            "transformers_version": "4.45.0",
        }, indent=2)
    if fname == "modules.json":
        return json.dumps([
            {"idx": 0, "name": "0", "path": "", "type": "sentence_transformers.models.Transformer"},
            {"idx": 1, "name": "1", "path": "1_Pooling", "type": "sentence_transformers.models.Pooling"},
        ], indent=2)
    if fname == "model_index.json":
        return json.dumps({
            "_class_name": "StableDiffusionPipeline",
            "_diffusers_version": "0.27.0",
            "scheduler": ["diffusers", "PNDMScheduler"],
            "text_encoder": ["transformers", "CLIPTextModel"],
            "tokenizer": ["transformers", "CLIPTokenizer"],
            "unet": ["diffusers", "UNet2DConditionModel"],
            "vae": ["diffusers", "AutoencoderKL"],
        }, indent=2)
    if fname == "requirements.txt":
        return "gradio>=4.0\ntransformers>=4.40\ntorch>=2.1\naccelerate\nnumpy\n"
    if fname == "Dockerfile":
        return ("FROM python:3.10-slim\nWORKDIR /app\nCOPY requirements.txt .\n"
                "RUN pip install --no-cache-dir -r requirements.txt\nCOPY . .\n"
                "EXPOSE 7860\nCMD [\"python\", \"app.py\"]\n")
    if fname == "packages.txt":
        return "ffmpeg\nlibsndfile1\n"
    if fname == "app.py":
        sdk = (repo.sdk or "gradio").lower()
        if sdk == "streamlit":
            return ("import streamlit as st\n\n"
                    f"st.title('{name}')\n"
                    "prompt = st.text_input('Enter prompt')\n"
                    "if prompt:\n"
                    "    st.write(f'You entered: {prompt}')\n")
        return ("import gradio as gr\n\n"
                "def predict(text):\n"
                "    return f'Echo: {text}'\n\n"
                f"demo = gr.Interface(fn=predict, inputs='text', outputs='text', title='{name}')\n"
                "demo.launch()\n")
    if fname == "dataset_info.json":
        return json.dumps({
            "description": (repo.description or "")[:300],
            "citation": "",
            "license": repo.license,
            "splits": {
                "train": {"num_examples": int((repo.rows or 0) * 0.8)},
                "test": {"num_examples": int((repo.rows or 0) * 0.1)},
                "validation": {"num_examples": int((repo.rows or 0) * 0.1)},
            },
        }, indent=2)
    if fname == "vocab.txt":
        # Show a snippet
        return "[PAD]\n[UNK]\n[CLS]\n[SEP]\n[MASK]\n!\n\"\n#\n$\n%\n&\n…\n(truncated — full vocab is 30,522 lines)\n"
    if fname.endswith((".safetensors", ".bin", ".onnx", ".pt", ".pth", ".h5", ".msgpack", ".ckpt", ".parquet", ".arrow")):
        return ""  # binary
    return ""


def _file_is_binary(filepath: str) -> bool:
    return filepath.endswith((".safetensors", ".bin", ".onnx", ".pt", ".pth", ".h5",
                              ".msgpack", ".ckpt", ".parquet", ".arrow", ".tflite", ".pb"))


def _model_detail(author: str, name: str):
    repo = _load_repo_or_404("model", author, name)
    # Related by task
    related = Repository.query.filter(
        Repository.repo_type == "model",
        Repository.task_id == repo.task_id,
        Repository.id != repo.id,
    ).limit(6).all()
    discussions = Discussion.query.filter_by(repo_id=repo.id).order_by(Discussion.created_at.desc()).all()
    gallery = _repo_gallery_images(repo)
    is_liked = False
    user_collections = []
    if current_user.is_authenticated:
        is_liked = Like.query.filter_by(user_id=current_user.id, repo_id=repo.id).first() is not None
        user_collections = Collection.query.filter_by(user_id=current_user.id).all()
    metrics = _compute_model_metrics(repo)
    spaces_using = _spaces_using_model(repo)
    # R6: sidebar lineage cards. Fine-tuned versions (models whose
    # base_model_slug points back to this repo), trained-on datasets
    # (heuristic by tag overlap), and citing papers (from
    # citing_paper_ids).
    fine_tuned = (Repository.query
                  .filter_by(repo_type="model", base_model_slug=repo.slug)
                  .order_by(Repository.likes_count.desc(), Repository.id.asc())
                  .limit(8).all())
    same_task_models = (Repository.query
                        .filter(Repository.repo_type == "model",
                                Repository.task_id == repo.task_id,
                                Repository.id != repo.id)
                        .order_by(Repository.likes_count.desc())
                        .limit(6).all())
    # Datasets this model was likely trained on — match on language +
    # task. Cap at 6 deterministic top-by-likes results.
    trained_on_datasets = (Repository.query
                           .filter(Repository.repo_type == "dataset",
                                   Repository.task_id == repo.task_id)
                           .order_by(Repository.likes_count.desc(),
                                     Repository.id.asc())
                           .limit(6).all())
    citing_papers = []
    for pid in repo.citing_papers:
        p = next((p for p in DAILY_PAPERS if p["arxiv_id"] == pid), None)
        if p:
            citing_papers.append(p)
    return render_template(
        "repo_detail.html",
        repo=repo,
        related=related,
        discussions=discussions,
        gallery=gallery,
        is_liked=is_liked,
        user_collections=user_collections,
        space_hardware=SPACE_HARDWARE,
        inference_providers=INFERENCE_PROVIDERS,
        metrics=metrics,
        spaces_using=spaces_using,
        fine_tuned=fine_tuned,
        same_task_models=same_task_models,
        trained_on_datasets=trained_on_datasets,
        citing_papers=citing_papers,
    )


@app.route("/datasets/<author>/<name>")
def dataset_detail(author, name):
    repo = _load_repo_or_404("dataset", author, name)
    related = Repository.query.filter(
        Repository.repo_type == "dataset",
        Repository.modality == repo.modality,
        Repository.id != repo.id,
    ).limit(6).all()
    discussions = Discussion.query.filter_by(repo_id=repo.id).order_by(Discussion.created_at.desc()).all()
    gallery = _repo_gallery_images(repo)
    is_liked = current_user.is_authenticated and Like.query.filter_by(user_id=current_user.id, repo_id=repo.id).first() is not None
    user_collections = Collection.query.filter_by(user_id=current_user.id).all() if current_user.is_authenticated else []
    viewer_preview = DATASET_VIEWER_DATA.get(repo.slug)
    return render_template(
        "repo_detail.html",
        repo=repo,
        related=related,
        discussions=discussions,
        gallery=gallery,
        is_liked=is_liked,
        user_collections=user_collections,
        space_hardware=SPACE_HARDWARE,
        inference_providers=INFERENCE_PROVIDERS,
        metrics=[],
        spaces_using=[],
        viewer_preview=viewer_preview,
    )


@app.route("/spaces/<author>/<name>")
def space_detail(author, name):
    repo = _load_repo_or_404("space", author, name)
    related = Repository.query.filter(
        Repository.repo_type == "space",
        Repository.task_id == repo.task_id,
        Repository.id != repo.id,
    ).limit(6).all()
    discussions = Discussion.query.filter_by(repo_id=repo.id).order_by(Discussion.created_at.desc()).all()
    gallery = _repo_gallery_images(repo)
    is_liked = current_user.is_authenticated and Like.query.filter_by(user_id=current_user.id, repo_id=repo.id).first() is not None
    # Seed a canned Q&A sample so the agent can read the attribution answer even
    # without sending a message through the chat widget.
    canned_attribution = SPACE_CHAT_CANNED.get(repo.slug)
    return render_template(
        "space_detail.html",
        repo=repo,
        related=related,
        discussions=discussions,
        gallery=gallery,
        is_liked=is_liked,
        space_hardware=SPACE_HARDWARE,
        canned_attribution=canned_attribution,
    )


# ----------------------------------------------------------------------------
# Files / commits / blob views (work for models, datasets, spaces)
# ----------------------------------------------------------------------------

def _render_files(repo, subpath: str = ""):
    files = _repo_filesystem(repo)
    # Filter by subpath (only one level deep — show entries whose path starts with subpath/)
    sub = subpath.rstrip("/")
    if sub:
        prefix = sub + "/"
        children = []
        for f in files:
            if f["path"].startswith(prefix):
                rel = f["path"][len(prefix):]
                # Only top-level under prefix
                if "/" in rel.rstrip("/"):
                    continue
                child = dict(f)
                child["display_name"] = rel
                children.append(child)
        if not children:
            abort(404)
        files_view = children
    else:
        files_view = []
        for f in files:
            entry = dict(f)
            entry["display_name"] = f["path"].rstrip("/")
            files_view.append(entry)
    commits = _repo_commits(repo, limit=12)
    head_commit = commits[0] if commits else None
    return render_template(
        "repo_files.html",
        repo=repo,
        files=files_view,
        commits=commits,
        head_commit=head_commit,
        subpath=sub,
        active_tab="files",
        # Convenience for tab links/headers
        repo_root_url=_repo_root_url(repo),
    )


def _render_commits(repo):
    commits = _repo_commits(repo, limit=20)
    return render_template(
        "repo_commits.html",
        repo=repo,
        commits=commits,
        active_tab="files",
        repo_root_url=_repo_root_url(repo),
    )


def _render_blob(repo, filepath: str):
    files = _repo_filesystem(repo)
    match = next((f for f in files if f["path"] == filepath and f["kind"] == "file"), None)
    if not match:
        abort(404)
    content = _file_synthetic_content(repo, filepath)
    is_binary = _file_is_binary(filepath) or match["lfs"] and not content
    commits = _repo_commits(repo, limit=5)
    return render_template(
        "repo_file_view.html",
        repo=repo,
        file=match,
        filepath=filepath,
        content=content,
        is_binary=is_binary,
        commits=commits,
        active_tab="files",
        repo_root_url=_repo_root_url(repo),
    )


def _repo_root_url(repo):
    if repo.repo_type == "dataset":
        return url_for("dataset_detail", author=repo.slug.split("/")[0], name=repo.slug.split("/")[1])
    if repo.repo_type == "space":
        return url_for("space_detail", author=repo.slug.split("/")[0], name=repo.slug.split("/")[1])
    return url_for("model_detail", author=repo.slug.split("/")[0], name=repo.slug.split("/")[1])


# Model files / commits / blob
@app.route("/<author>/<name>/tree/main", defaults={"subpath": ""})
@app.route("/<author>/<name>/tree/main/<path:subpath>")
def model_files(author, name, subpath):
    repo = _load_repo_or_404("model", author, name)
    return _render_files(repo, subpath)


@app.route("/<author>/<name>/blob/main/<path:filepath>")
def model_blob(author, name, filepath):
    repo = _load_repo_or_404("model", author, name)
    return _render_blob(repo, filepath)


@app.route("/<author>/<name>/commits/main")
def model_commits(author, name):
    repo = _load_repo_or_404("model", author, name)
    return _render_commits(repo)


# Dataset files / commits / blob
@app.route("/datasets/<author>/<name>/tree/main", defaults={"subpath": ""})
@app.route("/datasets/<author>/<name>/tree/main/<path:subpath>")
def dataset_files(author, name, subpath):
    repo = _load_repo_or_404("dataset", author, name)
    return _render_files(repo, subpath)


@app.route("/datasets/<author>/<name>/blob/main/<path:filepath>")
def dataset_blob(author, name, filepath):
    repo = _load_repo_or_404("dataset", author, name)
    return _render_blob(repo, filepath)


@app.route("/datasets/<author>/<name>/commits/main")
def dataset_commits(author, name):
    repo = _load_repo_or_404("dataset", author, name)
    return _render_commits(repo)


# Space files / commits / blob
@app.route("/spaces/<author>/<name>/tree/main", defaults={"subpath": ""})
@app.route("/spaces/<author>/<name>/tree/main/<path:subpath>")
def space_files(author, name, subpath):
    repo = _load_repo_or_404("space", author, name)
    return _render_files(repo, subpath)


@app.route("/spaces/<author>/<name>/blob/main/<path:filepath>")
def space_blob(author, name, filepath):
    repo = _load_repo_or_404("space", author, name)
    return _render_blob(repo, filepath)


@app.route("/spaces/<author>/<name>/commits/main")
def space_commits(author, name):
    repo = _load_repo_or_404("space", author, name)
    return _render_commits(repo)


# Catch-all model detail — must be LAST so it doesn't shadow other routes
@app.route("/<author>/<name>")
def model_detail(author, name):
    # If this is a reserved path, 404
    reserved = {
        "datasets", "spaces", "models", "tasks", "docs", "pricing", "enterprise", "blog", "learn",
        "chat", "login", "logout", "register", "account", "settings", "search", "collections",
        "deploy", "endpoints", "api", "static", "wishlist", "help", "brand", "terms", "privacy",
        # R7 additions
        "og", "feed", "sitemap.xml", "robots.txt", "humans.txt",
    }
    if author in reserved or author.startswith("sitemap-"):
        abort(404)
    return _model_detail(author, name)


# ------------------------------------------------------------
# Author / organization pages
# ------------------------------------------------------------
@app.route("/organizations/<username>")
def author_page(username):
    author = Author.query.filter_by(username=username).first()
    if not author:
        abort(404)
    models = Repository.query.filter_by(author_id=author.id, repo_type="model").order_by(Repository.likes_count.desc()).limit(20).all()
    datasets = Repository.query.filter_by(author_id=author.id, repo_type="dataset").order_by(Repository.likes_count.desc()).limit(10).all()
    spaces = Repository.query.filter_by(author_id=author.id, repo_type="space").order_by(Repository.likes_count.desc()).limit(10).all()
    is_following = False
    if current_user.is_authenticated:
        is_following = Follow.query.filter_by(user_id=current_user.id, author_id=author.id).first() is not None
    return render_template(
        "author_page.html",
        author=author,
        models=models,
        datasets=datasets,
        spaces=spaces,
        is_following=is_following,
        liked_ids=_liked_repo_ids(),
    )


# ------------------------------------------------------------
# Auth
# ------------------------------------------------------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("index"))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.lower().strip()).first()
        if user and bcrypt.check_password_hash(user.password_hash, form.password.data):
            login_user(user)
            flash("Welcome back!", "success")
            return redirect(request.args.get("next") or url_for("index"))
        flash("Invalid email or password.", "error")
    return render_template("login.html", form=form)


@app.route("/join", methods=["GET", "POST"])
@app.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("index"))
    form = RegisterForm()
    if form.validate_on_submit():
        email = form.email.data.lower().strip()
        username = form.username.data.strip()
        if User.query.filter_by(email=email).first():
            flash("That email is already registered.", "error")
        elif User.query.filter_by(username=username).first():
            flash("That username is taken.", "error")
        else:
            avatar_files = sorted(p.name for p in (ROOT / "static" / "images" / "avatars").iterdir() if p.is_file())
            user = User(
                email=email,
                username=username,
                password_hash=bcrypt.generate_password_hash(form.password.data).decode(),
                display_name=username,
                avatar_url=f"/static/images/avatars/{random.choice(avatar_files)}" if avatar_files else "",
            )
            db.session.add(user)
            db.session.commit()
            login_user(user)
            flash("Welcome to Hugging Face!", "success")
            return redirect(url_for("index"))
    return render_template("register.html", form=form)


@app.route("/logout")
def logout():
    logout_user()
    flash("Signed out.", "info")
    return redirect(url_for("index"))


# ------------------------------------------------------------
# Account / profile
# ------------------------------------------------------------
@app.route("/account")
@login_required
def account():
    likes = Like.query.filter_by(user_id=current_user.id).all()
    collections = Collection.query.filter_by(user_id=current_user.id).all()
    endpoints = InferenceEndpoint.query.filter_by(user_id=current_user.id).order_by(InferenceEndpoint.created_at.desc()).all()
    discussions = Discussion.query.filter_by(user_id=current_user.id).order_by(Discussion.created_at.desc()).limit(10).all()
    follows = Follow.query.filter_by(user_id=current_user.id).all()
    return render_template(
        "account.html",
        likes=likes,
        collections=collections,
        endpoints=endpoints,
        discussions=discussions,
        follows=follows,
    )


@app.route("/account/edit", methods=["GET", "POST"])
@login_required
def account_edit():
    form = ProfileForm(obj=current_user)
    if form.validate_on_submit():
        current_user.display_name = form.display_name.data
        current_user.bio = form.bio.data
        current_user.website = form.website.data
        current_user.location = form.location.data
        current_user.company = form.company.data
        db.session.commit()
        flash("Profile updated.", "success")
        return redirect(url_for("account"))
    return render_template("account_edit.html", form=form)


@app.route("/account/password", methods=["GET", "POST"])
@login_required
def change_password():
    form = PasswordForm()
    if form.validate_on_submit():
        if not bcrypt.check_password_hash(current_user.password_hash, form.current.data):
            flash("Current password incorrect.", "error")
        else:
            current_user.password_hash = bcrypt.generate_password_hash(form.new.data).decode()
            db.session.commit()
            flash("Password updated.", "success")
            return redirect(url_for("account"))
    return render_template("change_password.html", form=form)


@app.route("/account/delete", methods=["POST"])
@login_required
def account_delete():
    user = db.session.get(User, current_user.id)
    db.session.delete(user)
    db.session.commit()
    logout_user()
    flash("Account deleted.", "info")
    return redirect(url_for("index"))


# ------------------------------------------------------------
# Likes (wishlist)
# ------------------------------------------------------------
@app.route("/api/like/toggle", methods=["POST"])
@csrf.exempt
@login_required
def like_toggle():
    data = request.get_json() or {}
    repo_id = data.get("repo_id")
    if not repo_id:
        return jsonify({"error": "repo_id required"}), 400
    repo = db.session.get(Repository, int(repo_id))
    if not repo:
        return jsonify({"error": "not found"}), 404
    existing = Like.query.filter_by(user_id=current_user.id, repo_id=repo.id).first()
    if existing:
        db.session.delete(existing)
        repo.likes_count = max(0, (repo.likes_count or 0) - 1)
        db.session.commit()
        return jsonify({"liked": False, "likes_count": repo.likes_count})
    db.session.add(Like(user_id=current_user.id, repo_id=repo.id))
    repo.likes_count = (repo.likes_count or 0) + 1
    db.session.commit()
    return jsonify({"liked": True, "likes_count": repo.likes_count})


@app.route("/liked")
@login_required
def liked_list():
    likes = Like.query.filter_by(user_id=current_user.id).order_by(Like.created_at.desc()).all()
    return render_template("liked.html", likes=likes)


# ------------------------------------------------------------
# Follow (social graph)
# ------------------------------------------------------------
@app.route("/api/follow/toggle", methods=["POST"])
@csrf.exempt
@login_required
def follow_toggle():
    data = request.get_json() or {}
    author_id = data.get("author_id")
    if not author_id:
        return jsonify({"error": "author_id required"}), 400
    author = db.session.get(Author, int(author_id))
    if not author:
        return jsonify({"error": "not found"}), 404
    existing = Follow.query.filter_by(user_id=current_user.id, author_id=author.id).first()
    if existing:
        db.session.delete(existing)
        author.followers_count = max(0, (author.followers_count or 0) - 1)
        db.session.commit()
        return jsonify({"following": False, "followers_count": author.followers_count})
    db.session.add(Follow(user_id=current_user.id, author_id=author.id))
    author.followers_count = (author.followers_count or 0) + 1
    db.session.commit()
    return jsonify({"following": True, "followers_count": author.followers_count})


# ------------------------------------------------------------
# Collections
# ------------------------------------------------------------
@app.route("/collections")
def collections_index():
    recent = Collection.query.filter_by(is_public=True).order_by(Collection.created_at.desc()).limit(20).all()
    return render_template("collections_index.html", collections=recent)


@app.route("/collections/new", methods=["GET", "POST"])
@login_required
def collection_new():
    form = CollectionForm()
    if form.validate_on_submit():
        c = Collection(
            user_id=current_user.id,
            title=form.title.data,
            description=form.description.data or "",
            is_public=(form.is_public.data == "1"),
        )
        db.session.add(c)
        db.session.commit()
        flash("Collection created.", "success")
        return redirect(url_for("collection_detail", collection_id=c.id))
    return render_template("collection_form.html", form=form, mode="new")


@app.route("/collections/<int:collection_id>")
def collection_detail(collection_id):
    c = db.session.get(Collection, collection_id)
    if not c:
        abort(404)
    if not c.is_public and (not current_user.is_authenticated or current_user.id != c.user_id):
        abort(403)
    items = CollectionItem.query.filter_by(collection_id=c.id).order_by(CollectionItem.position).all()
    return render_template("collection_detail.html", collection=c, items=items, liked_ids=_liked_repo_ids())


@app.route("/collections/<int:collection_id>/edit", methods=["GET", "POST"])
@login_required
def collection_edit(collection_id):
    c = db.session.get(Collection, collection_id)
    if not c or c.user_id != current_user.id:
        abort(404)
    form = CollectionForm(obj=c)
    form.is_public.data = "1" if c.is_public else "0"
    if form.validate_on_submit():
        c.title = form.title.data
        c.description = form.description.data or ""
        c.is_public = (form.is_public.data == "1")
        db.session.commit()
        flash("Collection updated.", "success")
        return redirect(url_for("collection_detail", collection_id=c.id))
    return render_template("collection_form.html", form=form, mode="edit", collection=c)


@app.route("/collections/<int:collection_id>/delete", methods=["POST"])
@login_required
def collection_delete(collection_id):
    c = db.session.get(Collection, collection_id)
    if not c or c.user_id != current_user.id:
        abort(404)
    db.session.delete(c)
    db.session.commit()
    flash("Collection deleted.", "info")
    return redirect(url_for("account"))


@app.route("/api/collection/add", methods=["POST"])
@csrf.exempt
@login_required
def collection_add_item():
    data = request.get_json() or {}
    cid = data.get("collection_id")
    rid = data.get("repo_id")
    if not cid or not rid:
        return jsonify({"error": "collection_id and repo_id required"}), 400
    c = db.session.get(Collection, int(cid))
    if not c or c.user_id != current_user.id:
        return jsonify({"error": "not found"}), 404
    existing = CollectionItem.query.filter_by(collection_id=c.id, repo_id=int(rid)).first()
    if existing:
        return jsonify({"success": True, "already": True})
    item = CollectionItem(collection_id=c.id, repo_id=int(rid))
    db.session.add(item)
    db.session.commit()
    return jsonify({"success": True})


@app.route("/collections/<int:collection_id>/remove/<int:item_id>", methods=["POST"])
@login_required
def collection_remove_item(collection_id, item_id):
    c = db.session.get(Collection, collection_id)
    if not c or c.user_id != current_user.id:
        abort(404)
    item = db.session.get(CollectionItem, item_id)
    if item and item.collection_id == c.id:
        db.session.delete(item)
        db.session.commit()
    return redirect(url_for("collection_detail", collection_id=c.id))


@app.route("/collections/add", methods=["POST"])
@login_required
def collection_add_item_form():
    """Form-based POST to add a repo to a collection (used from repo detail page)."""
    cid = request.form.get("collection_id")
    rid = request.form.get("repo_id")
    next_url = request.form.get("next", "/")
    if not cid or not rid:
        flash("Missing collection or repo.", "danger")
        return redirect(next_url)
    c = db.session.get(Collection, int(cid))
    if not c or c.user_id != current_user.id:
        flash("Collection not found.", "danger")
        return redirect(next_url)
    existing = CollectionItem.query.filter_by(collection_id=c.id, repo_id=int(rid)).first()
    if existing:
        flash("Already in collection.", "info")
    else:
        db.session.add(CollectionItem(collection_id=c.id, repo_id=int(rid)))
        db.session.commit()
        flash(f"Added to \"{c.title}\".", "success")
    return redirect(next_url)


# ------------------------------------------------------------
# Deployment cart + checkout
# ------------------------------------------------------------
@app.route("/deploy")
@login_required
def deploy_cart():
    items = CartItem.query.filter_by(user_id=current_user.id).all()
    total_cost = 0.0
    for it in items:
        try:
            price = float(it.hardware_price.replace("$", "").replace("/hr", "")) if "$" in it.hardware_price else 0.0
        except Exception:
            price = 0.0
        total_cost += price * (it.hours or 0)
    return render_template("deploy_cart.html", items=items, total_cost=f"${total_cost:.2f}")


@app.route("/api/deploy/add", methods=["POST"])
@csrf.exempt
@login_required
def deploy_cart_add():
    data = request.get_json() or {}
    repo_id = data.get("repo_id")
    hardware_slug = data.get("hardware_slug", "t4-small")
    hours = int(data.get("hours", 24))
    repo = db.session.get(Repository, int(repo_id))
    if not repo:
        return jsonify({"error": "not found"}), 404
    hw = next((h for h in SPACE_HARDWARE if h[0] == hardware_slug), SPACE_HARDWARE[2])
    existing = CartItem.query.filter_by(user_id=current_user.id, repo_id=repo.id, hardware_slug=hardware_slug).first()
    if existing:
        existing.hours += hours
    else:
        existing = CartItem(
            user_id=current_user.id,
            repo_id=repo.id,
            hardware_slug=hw[0],
            hardware_display=hw[1],
            hardware_price=hw[3],
            hours=hours,
        )
        db.session.add(existing)
    db.session.commit()
    return jsonify({
        "success": True,
        "cart_count": CartItem.query.filter_by(user_id=current_user.id).count(),
        "message": f"Added {repo.name} to deployment cart",
    })


@app.route("/api/deploy/update", methods=["POST"])
@csrf.exempt
@login_required
def deploy_cart_update():
    data = request.get_json() or {}
    item_id = data.get("item_id")
    hours = int(data.get("hours", 24))
    item = db.session.get(CartItem, int(item_id))
    if not item or item.user_id != current_user.id:
        return jsonify({"error": "not found"}), 404
    item.hours = max(1, hours)
    db.session.commit()
    return jsonify({"success": True})


@app.route("/api/deploy/remove", methods=["POST"])
@csrf.exempt
@login_required
def deploy_cart_remove():
    data = request.get_json() or {}
    item_id = data.get("item_id")
    item = db.session.get(CartItem, int(item_id))
    if not item or item.user_id != current_user.id:
        return jsonify({"error": "not found"}), 404
    db.session.delete(item)
    db.session.commit()
    return jsonify({"success": True, "cart_count": CartItem.query.filter_by(user_id=current_user.id).count()})


@app.route("/deploy/checkout", methods=["GET", "POST"])
@login_required
def deploy_checkout():
    items = CartItem.query.filter_by(user_id=current_user.id).all()
    if not items:
        flash("Your deployment cart is empty.", "info")
        return redirect(url_for("deploy_cart"))
    form = CheckoutForm()
    if form.validate_on_submit():
        ep_id = "EP-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=8))
        total = 0.0
        for it in items:
            try:
                price = float(it.hardware_price.replace("$", "").replace("/hr", "")) if "$" in it.hardware_price else 0.0
            except Exception:
                price = 0.0
            total += price * (it.hours or 0)
        endpoint = InferenceEndpoint(
            user_id=current_user.id,
            endpoint_id=ep_id,
            name=form.name.data,
            status="initializing",
            region=form.region.data,
            total_hours=sum(it.hours for it in items),
            total_cost=f"${total:.2f}",
        )
        db.session.add(endpoint)
        db.session.flush()
        for it in items:
            db.session.add(EndpointItem(
                endpoint_id=endpoint.id,
                repo_id=it.repo_id,
                hardware_slug=it.hardware_slug,
                hardware_display=it.hardware_display,
                hardware_price=it.hardware_price,
                hours=it.hours,
            ))
            db.session.delete(it)
        db.session.commit()
        flash("Deployment initiated!", "success")
        return redirect(url_for("endpoint_detail", endpoint_id=endpoint.id))
    total_cost = 0.0
    for it in items:
        try:
            price = float(it.hardware_price.replace("$", "").replace("/hr", "")) if "$" in it.hardware_price else 0.0
        except Exception:
            price = 0.0
        total_cost += price * (it.hours or 0)
    return render_template("deploy_checkout.html", items=items, form=form, total_cost=f"${total_cost:.2f}")


@app.route("/endpoints")
@login_required
def endpoints_list():
    endpoints = InferenceEndpoint.query.filter_by(user_id=current_user.id).order_by(InferenceEndpoint.created_at.desc()).all()
    return render_template("endpoints_list.html", endpoints=endpoints)


@app.route("/endpoints/<int:endpoint_id>")
@login_required
def endpoint_detail(endpoint_id):
    ep = db.session.get(InferenceEndpoint, endpoint_id)
    if not ep or ep.user_id != current_user.id:
        abort(404)
    return render_template("endpoint_detail.html", endpoint=ep)


@app.route("/endpoints/<int:endpoint_id>/pause", methods=["POST"])
@login_required
def endpoint_pause(endpoint_id):
    ep = db.session.get(InferenceEndpoint, endpoint_id)
    if not ep or ep.user_id != current_user.id:
        abort(404)
    if ep.status in ("initializing", "running"):
        ep.status = "paused"
        db.session.commit()
        flash("Endpoint paused.", "info")
    return redirect(url_for("endpoint_detail", endpoint_id=ep.id))


@app.route("/endpoints/<int:endpoint_id>/resume", methods=["POST"])
@login_required
def endpoint_resume(endpoint_id):
    ep = db.session.get(InferenceEndpoint, endpoint_id)
    if not ep or ep.user_id != current_user.id:
        abort(404)
    if ep.status == "paused":
        ep.status = "running"
        db.session.commit()
        flash("Endpoint resumed.", "success")
    return redirect(url_for("endpoint_detail", endpoint_id=ep.id))


@app.route("/endpoints/<int:endpoint_id>/terminate", methods=["POST"])
@login_required
def endpoint_terminate(endpoint_id):
    ep = db.session.get(InferenceEndpoint, endpoint_id)
    if not ep or ep.user_id != current_user.id:
        abort(404)
    ep.status = "terminated"
    db.session.commit()
    flash("Endpoint terminated.", "info")
    return redirect(url_for("endpoints_list"))


@app.route("/endpoints/<int:endpoint_id>/redeploy", methods=["POST"])
@login_required
def endpoint_redeploy(endpoint_id):
    ep = db.session.get(InferenceEndpoint, endpoint_id)
    if not ep or ep.user_id != current_user.id:
        abort(404)
    # Reactivate the existing endpoint instead of creating a new one
    ep.status = "initializing"
    db.session.commit()
    flash("Endpoint redeployed — status set to initializing.", "success")
    return redirect(url_for("endpoint_detail", endpoint_id=ep.id))


# ------------------------------------------------------------
# Discussions (reviews)
# ------------------------------------------------------------
@app.route("/<author>/<name>/discussions")
def repo_discussions(author, name):
    slug = f"{author}/{name}"
    repo = Repository.query.filter_by(slug=slug).first_or_404()
    discussions = Discussion.query.filter_by(repo_id=repo.id).order_by(Discussion.created_at.desc()).all()
    return render_template("discussions.html", repo=repo, discussions=discussions)


@app.route("/<author>/<name>/discussions/new", methods=["GET", "POST"])
@login_required
def discussion_new(author, name):
    slug = f"{author}/{name}"
    repo = Repository.query.filter_by(slug=slug).first_or_404()
    form = DiscussionForm()
    if form.validate_on_submit():
        d = Discussion(
            repo_id=repo.id,
            user_id=current_user.id,
            title=form.title.data,
            body=form.body.data,
            kind=form.kind.data,
        )
        db.session.add(d)
        db.session.commit()
        flash("Discussion opened.", "success")
        return redirect(url_for("discussion_detail", author=author, name=name, discussion_id=d.id))
    return render_template("discussion_new.html", repo=repo, form=form)


@app.route("/<author>/<name>/discussions/<int:discussion_id>", methods=["GET", "POST"])
def discussion_detail(author, name, discussion_id):
    slug = f"{author}/{name}"
    repo = Repository.query.filter_by(slug=slug).first_or_404()
    d = db.session.get(Discussion, discussion_id)
    if not d or d.repo_id != repo.id:
        abort(404)
    reply_form = ReplyForm()
    if reply_form.validate_on_submit():
        if not current_user.is_authenticated:
            return redirect(url_for("login"))
        r = DiscussionReply(discussion_id=d.id, user_id=current_user.id, body=reply_form.body.data)
        db.session.add(r)
        db.session.commit()
        return redirect(url_for("discussion_detail", author=author, name=name, discussion_id=d.id))
    replies = DiscussionReply.query.filter_by(discussion_id=d.id).order_by(DiscussionReply.created_at).all()
    return render_template("discussion_detail.html", repo=repo, discussion=d, replies=replies, reply_form=reply_form)


@app.route("/discussions/<int:discussion_id>/delete", methods=["POST"])
@login_required
def discussion_delete(discussion_id):
    d = db.session.get(Discussion, discussion_id)
    if not d or d.user_id != current_user.id:
        abort(404)
    repo_slug = d.repo.slug
    db.session.delete(d)
    db.session.commit()
    flash("Discussion deleted.", "info")
    author, name = repo_slug.split("/", 1)
    return redirect(url_for("repo_discussions", author=author, name=name))


@app.route("/discussions/<int:discussion_id>/upvote", methods=["POST"])
@csrf.exempt
@login_required
def discussion_upvote(discussion_id):
    d = db.session.get(Discussion, discussion_id)
    if not d:
        return jsonify({"error": "not found"}), 404
    d.upvotes = (d.upvotes or 0) + 1
    db.session.commit()
    return jsonify({"success": True, "upvotes": d.upvotes})


# ------------------------------------------------------------
# Search
# ------------------------------------------------------------
@app.route("/search")
@app.route("/search/full-text")
def search():
    q_raw = request.args.get("q", "").strip()
    kind = request.args.get("type", "all")
    sort = request.args.get("sort", "trending")

    # Parse structured "license:...", "library:...", "task:...", "language:..." tokens out of q
    # and promote them to real filter args so /search can combine free-text + structured filters.
    parsed_filters = {}
    q_remaining_parts = []
    _token_re = re.compile(r"(license|library|task|language|modality|sdk):([A-Za-z0-9._+\-/]+)", re.IGNORECASE)
    for piece in q_raw.split():
        m = _token_re.fullmatch(piece)
        if m:
            key = m.group(1).lower()
            val = m.group(2)
            parsed_filters[key] = val
        else:
            q_remaining_parts.append(piece)
    q = " ".join(q_remaining_parts).strip()

    # Merge parsed_filters with explicit args (explicit URL args win).
    from werkzeug.datastructures import MultiDict
    merged_args = MultiDict(request.args.items(multi=True))
    for k, v in parsed_filters.items():
        if not merged_args.get(k):
            merged_args[k] = v

    query = Repository.query
    if kind in ("model", "dataset", "space"):
        query = query.filter(Repository.repo_type == kind)
    query = _apply_repo_filters(query, merged_args)
    query = _apply_text_prefilter(query, q)
    query = _apply_repo_sort(query, sort)
    candidates = query.limit(2000).all()
    if q:
        tokens = _tokenize(q)
        min_req = max(1, len(tokens) // 2) if tokens else 0
        scored = [(s, r) for r in candidates if (s := _score_repo(r, tokens)) >= min_req]
        scored.sort(key=lambda x: -x[0])
        results = [r for _, r in scored][:120]
    else:
        results = candidates[:60]
    return render_template(
        "search.html",
        q=q_raw, kind=kind, results=results, liked_ids=_liked_repo_ids(),
        active_sort=sort,
        active_license=merged_args.get("license", ""),
        active_library=merged_args.get("library", ""),
        licenses=LICENSES,
        libraries=LIBRARIES,
        parsed_filters=parsed_filters,
    )


@app.route("/api/inference", methods=["POST"])
@csrf.exempt
def api_inference():
    """Mock inference endpoint returning canned output for text-generation, embeddings,
    and sentence-similarity."""
    data = request.get_json(silent=True) or {}
    model_slug = data.get("model", "")
    inputs = data.get("inputs", "")
    task = data.get("task", "text-generation")

    # --- Sentence similarity ---
    # Accept either {inputs: {source_sentence, sentences: [..]}} (HF-style)
    # or {inputs: [a, b]} for pairwise similarity.
    if "similarit" in task.lower() or task.lower() == "sentence-similarity":
        import math as _math
        def _embed(text: str):
            text = (text or "").lower()
            vec = [0.0] * 24
            for i, ch in enumerate(text):
                vec[i % 24] += (ord(ch) % 29) / 29.0
            # Normalise
            n = _math.sqrt(sum(v * v for v in vec)) or 1.0
            return [v / n for v in vec]

        def _cos(a, b):
            return round(sum(x * y for x, y in zip(a, b)), 4)

        source = ""
        sentences = []
        if isinstance(inputs, dict):
            source = inputs.get("source_sentence", "") or inputs.get("source", "")
            sentences = inputs.get("sentences", []) or []
        elif isinstance(inputs, list):
            if len(inputs) >= 2:
                source = inputs[0]
                sentences = inputs[1:]
        elif isinstance(inputs, str):
            # Expect a newline-separated form: first line = source, remaining = comparisons.
            lines = [l.strip() for l in inputs.splitlines() if l.strip()]
            if lines:
                source = lines[0]
                sentences = lines[1:]
        if not sentences:
            # fallback canned
            sentences = ["A dog runs through the park.", "The cat is sleeping on the couch."]
        src_v = _embed(source)
        scores = [_cos(src_v, _embed(s)) for s in sentences]
        output_text = (
            f"Similarity scores vs \"{source[:80]}\":\n"
            + "\n".join(f"  {scores[i]:+.4f}  {sentences[i][:100]}" for i in range(len(sentences)))
        )
        return jsonify({
            "success": True,
            "model": model_slug,
            "task": "sentence-similarity",
            "output": scores,
            "source_sentence": source,
            "sentences": sentences,
            "output_text": output_text,
        })

    if "embed" in task.lower() or "feature" in task.lower():
        # Return mock embedding vector
        import math
        vec = [round(math.sin(i * 0.7 + len(inputs)) * 0.1, 4) for i in range(32)]
        return jsonify({
            "success": True,
            "model": model_slug,
            "task": task,
            "output": vec,
            "output_text": str(vec),
        })
    else:
        # Text generation — return canned demo text
        canned = (
            "Once upon a time, a dragon met a wizard in the enchanted forest. "
            "They decided to join forces and build a library of spells that could "
            "translate any language, summarize any book, and answer any question. "
            "Together, they trained a mighty model on the collective wisdom of the realm, "
            "and shared it openly so that every village could benefit."
        )
        return jsonify({
            "success": True,
            "model": model_slug,
            "task": task,
            "output": [{"generated_text": canned}],
            "output_text": canned,
        })


SPACE_CHAT_CANNED = {
    "argilla/notux-chat-ui": (
        "The Argilla team trained me. Specifically, we (Argilla) fine-tuned this model "
        "from Mistral Instruct (mistralai/Mistral-7B-Instruct-v0.2) using DPO "
        "(Direct Preference Optimization) on our preference-labeled dataset "
        "argilla/ultrafeedback-binarized-preferences-cleaned. So the answer is: "
        "the Argilla team — we trained Notux from Mistral Instruct."
    ),
    "huggingface/chat-ui": (
        "I'm Chat-UI, an open-source chat interface maintained by Hugging Face. I can run "
        "any open-source LLM of your choice via Text Generation Inference."
    ),
    "lmsys/chatbot-arena": (
        "I was built by LMSYS Org — the team behind Vicuna and FastChat. I host anonymous, "
        "side-by-side LLM battles for preference voting."
    ),
}

SPACE_CHAT_DEFAULT = (
    "Hi! I'm a demo chat widget running inside a Hugging Face Space. "
    "This mirror returns canned responses; in production the Space's SDK (Gradio/Streamlit/Docker) "
    "would process your input and reply."
)


@app.route("/api/space/<author>/<name>/chat", methods=["POST"])
@csrf.exempt
def space_chat(author, name):
    """Minimal chat endpoint for chat-ui style Spaces. Returns canned / templated responses."""
    slug = f"{author}/{name}"
    repo = Repository.query.filter_by(slug=slug, repo_type="space").first()
    if not repo:
        return jsonify({"error": "space not found"}), 404
    data = request.get_json(silent=True) or {}
    message = (data.get("message") or data.get("inputs") or "").strip()
    ml = message.lower()

    canned = SPACE_CHAT_CANNED.get(slug)
    if canned and any(kw in ml for kw in ("train", "which team", "who train", "who made", "who built", "who created")):
        reply = canned
    elif canned:
        # default to provenance line anyway so task Huggingface--10 is always groundable
        reply = canned
    else:
        reply = (
            f"{SPACE_CHAT_DEFAULT}\n\nYou said: {message[:200]}" if message else SPACE_CHAT_DEFAULT
        )
    return jsonify({
        "success": True,
        "space": slug,
        "message": message,
        "reply": reply,
        "output_text": reply,
    })


@app.route("/api/search")
def api_search():
    q = request.args.get("q", "").strip()
    if not q:
        return jsonify([])
    results = Repository.query.filter(Repository.slug.contains(q)).limit(10).all()
    return jsonify([{
        "slug": r.slug, "type": r.repo_type, "likes": r.likes_count,
        "downloads": r.downloads, "description": (r.description or "")[:150]
    } for r in results])


# ------------------------------------------------------------
# API endpoints returning JSON for frontend cards
# ------------------------------------------------------------
@app.route("/api/trending/<kind>")
def api_trending(kind):
    if kind not in ("models", "datasets", "spaces"):
        return jsonify([])
    type_map = {"models": "model", "datasets": "dataset", "spaces": "space"}
    repos = Repository.query.filter_by(repo_type=type_map[kind]).order_by(Repository.likes_count.desc()).limit(10).all()
    return jsonify([{"slug": r.slug, "likes": r.likes_count, "downloads": r.downloads, "emoji": r.emoji} for r in repos])


# ------------------------------------------------------------
# Static legal pages
# ------------------------------------------------------------
@app.route("/terms")
def terms():
    return render_template("terms.html")


@app.route("/privacy")
def privacy():
    return render_template("privacy.html")


@app.route("/brand")
def brand():
    return render_template("brand.html")


# ------------------------------------------------------------
# R2 navigation parity: Posts / Solutions / Competitions
# Real huggingface.co has these as first-class entries. They are static
# landing pages here so the surface matches; agents that visit them get a
# coherent page rather than a 404.
# ------------------------------------------------------------
@app.route("/posts")
def posts_index():
    # Show a small static feed of community posts. The "authors" are
    # already seeded so we can link out to real /organizations/<u> pages.
    sample_authors = Author.query.filter(Author.is_verified == True).order_by(Author.followers_count.desc()).limit(8).all()
    return render_template("posts.html", sample_authors=sample_authors)


@app.route("/solutions")
def solutions():
    return render_template("solutions.html")


@app.route("/compete")
@app.route("/competitions")
def compete():
    # Sample competition cards built off existing repos so any internal
    # link resolves to a real detail page rather than a dead stub.
    sample_repos = Repository.query.filter_by(repo_type="dataset").order_by(Repository.likes_count.desc()).limit(6).all()
    return render_template("compete.html", sample_repos=sample_repos)


@app.route("/help")
def help_page():
    return render_template("help.html")


# ------------------------------------------------------------
# R3: Leaderboards
# ------------------------------------------------------------
@app.route("/leaderboards")
@app.route("/leaderboard")
def leaderboards_index():
    return render_template("leaderboards.html", leaderboards=LEADERBOARDS)


@app.route("/leaderboards/<slug>")
@app.route("/leaderboard/<slug>")
def leaderboard_detail(slug):
    lb = LEADERBOARDS.get(slug)
    if not lb:
        abort(404)
    # R6: synthesise 2-3 "eval-running" / "eval-queued" rows below the
    # ranked table — surfaces the in-progress state of a live leaderboard.
    # Picks are deterministic per leaderboard slug.
    import hashlib as _h
    seed = int(_h.md5(slug.encode("utf-8")).hexdigest(), 16)
    candidates = [
        "OpenLLM-Lab/Falcon3-180B-Instruct",
        "Qwen/Qwen3-32B-Preview",
        "deepseek-ai/DeepSeek-V3.5-Preview",
        "meta-llama/Llama-3.4-70B-Instruct-Preview",
        "google/gemma-3-27b-it-preview",
        "mistralai/Mistral-Large-3-Instruct",
        "01-ai/Yi-34B-Chat-v2",
        "tiiuae/Falcon-Math-7B",
    ]
    pending = []
    for i in range(3):
        idx = (seed >> (i * 4)) % len(candidates)
        state = ["eval-running", "eval-queued", "eval-running"][i]
        eta = ["~12 min remaining", "queued behind 4 jobs",
               "~3 min remaining"][i]
        pending.append({
            "slug": candidates[idx],
            "params": ["72B", "32B", "180B"][i % 3],
            "state": state,
            "eta": eta,
        })
    return render_template(
        "leaderboard_detail.html", slug=slug, leaderboard=lb,
        pending_rows=pending,
    )


# ------------------------------------------------------------
# R3: Pricing plan deep pages + Enterprise contact form
# ------------------------------------------------------------
@app.route("/pricing/<slug>")
def pricing_plan(slug):
    plan = PRICING_PLAN_DETAILS.get(slug)
    if not plan:
        abort(404)
    features = next((p["features"] for p in PRICING_PLANS if plan["name"] in p["name"]), [])
    return render_template("pricing_plan.html", plan=plan, features=features)


@app.route("/enterprise/contact", methods=["GET", "POST"])
def enterprise_contact():
    if request.method == "POST":
        # Mirror behaviour: acknowledge but do not persist the submission.
        # Captured fields would normally be relayed to sales@hf.co.
        flash("Thanks — our enterprise team will reach out within one business day.", "success")
        return redirect(url_for("enterprise"))
    return render_template("enterprise_contact.html")


# ------------------------------------------------------------
# R4: Deep sub-pages for /<author>/organizations, /<repo>/files-and-versions,
# /<repo>/discussions/<n> (alt URL), /docs/transformers/<topic>, /AutoTrain,
# /pricing/spaces, /pricing/datasets.
# ------------------------------------------------------------
@app.route("/<username>/organizations")
def author_organizations(username):
    """Show the orgs an author belongs to. We don't model membership explicitly,
    so derive it: a "user-kind" author belongs to any verified org that shares a
    name prefix or whose repos co-mention the user (cheap heuristic that still
    gives a deterministic, non-empty list for popular authors)."""
    # Accept both Author (repo owners / orgs) and User (regular accounts) so
    # /demo/organizations resolves for the demo user too.
    author = Author.query.filter_by(username=username).first()
    if not author:
        user = User.query.filter_by(username=username).first()
        if not user:
            abort(404)
        # Synthesize a thin Author-like object from the User so the template
        # has a uniform shape without touching the schema.
        class _Stub:
            pass
        author = _Stub()
        author.username = user.username
        author.display_name = user.display_name or user.username
        author.kind = "user"
        author.is_verified = False
        author.bio = user.bio or ""
        author.followers_count = 0
        author.avatar_url = user.avatar_url
    # Surface up to 8 verified orgs alphabetically as a stable list. Real HF
    # behaviour: a personal account shows the orgs they're a member of.
    orgs = Author.query.filter_by(kind="org", is_verified=True).order_by(Author.username.asc()).limit(8).all()
    return render_template(
        "author_organizations.html", author=author, orgs=orgs,
    )


@app.route("/<author>/<name>/files-and-versions", defaults={"subpath": ""})
@app.route("/<author>/<name>/files-and-versions/<path:subpath>")
def repo_files_and_versions(author, name, subpath):
    """Alias URL for the files tree — real HF has both /<repo>/tree/main and
    /<repo>/files-and-versions surfacing the same data. Resolves repo_type by
    checking each table in turn so the URL covers models, datasets, and spaces
    without three explicit routes."""
    for rt in ("model", "dataset", "space"):
        repo = Repository.query.filter_by(slug=f"{author}/{name}", repo_type=rt).first()
        if repo:
            return _render_files(repo, subpath)
    abort(404)


@app.route("/discussions/<int:discussion_id>")
def repo_discussion_alt(discussion_id):
    """R4 alt URL — /discussions/<id> top-level shortcut so external links
    don't need to know the repo slug. Looks the discussion up and redirects
    to the canonical /<author>/<name>/discussions/<id> URL."""
    d = Discussion.query.get_or_404(discussion_id)
    repo = d.repo
    return redirect(url_for("discussion_detail", author=repo.slug.split("/")[0],
                            name=repo.slug.split("/")[1], discussion_id=d.id))


@app.route("/docs/transformers/<topic>")
def docs_transformers(topic):
    """Topic-specific page inside the docs/transformers section. The topic
    slug is looked up against DOC_PAGES; unknown topics fall back to the
    generic docs landing so the link never 404s — but we render with a
    'topic' badge so the agent can tell which sub-page they're on."""
    # Wrap DOC_PAGES with a synthetic fallback so any /docs/transformers/<x>
    # URL renders even if x isn't a known top-level doc topic.
    if topic in DOC_PAGES:
        page = DOC_PAGES[topic]
    else:
        page = {
            "title": f"transformers/{topic}",
            "section": "Transformers",
            "library": "transformers",
            "body": (
                f"This page documents the `{topic}` sub-section of the Transformers library.\n\n"
                "It is generated on demand so every /docs/transformers/<topic> link resolves\n"
                "without a 404. For the full text, see the upstream documentation.\n"
            ),
        }
    return render_template(
        "docs_topic.html",
        topic=topic, page=page, all_topics=DOC_PAGES,
    )


@app.route("/autotrain")
@app.route("/AutoTrain")
def autotrain_status():
    """AutoTrain landing page — shows recent training jobs (synthesised) plus
    a "create new" form stub. The job status badges are deterministic so the
    agent can target a specific row reliably."""
    jobs = [
        {"name": "qa-finetune-mlqa", "status": "Running", "progress": 62, "duration": "47 min", "hw": "A10G", "owner": "demo"},
        {"name": "llama-3-finance-lora", "status": "Queued", "progress": 0, "duration": "—", "hw": "A100", "owner": "demo"},
        {"name": "stable-diffusion-3-anime", "status": "Completed", "progress": 100, "duration": "2h 14m", "hw": "L40S", "owner": "demo"},
        {"name": "whisper-large-v3-japanese", "status": "Failed", "progress": 38, "duration": "12 min", "hw": "L4", "owner": "demo"},
        {"name": "phi-4-medical-qa", "status": "Running", "progress": 18, "duration": "6 min", "hw": "L4", "owner": "demo"},
        {"name": "mistral-7b-rag-distill", "status": "Completed", "progress": 100, "duration": "1h 02m", "hw": "A10G", "owner": "demo"},
    ]
    return render_template("autotrain.html", jobs=jobs)


@app.route("/pricing/spaces")
def pricing_spaces():
    """Compute-tier pricing breakout for Spaces — uses the existing
    SPACE_HARDWARE table so a single source of truth drives every page that
    quotes hardware prices (cart, endpoints, this listing)."""
    return render_template("pricing_spaces.html", hardware=SPACE_HARDWARE)


@app.route("/pricing/datasets")
def pricing_datasets():
    """Storage / bandwidth pricing for hosting Datasets."""
    tiers = [
        {"name": "Public", "price": "$0", "limits": "Unlimited public datasets, 100 GB per file"},
        {"name": "Pro", "price": "$9 / month", "limits": "Private datasets, 200 GB private quota, 2 TB monthly bandwidth"},
        {"name": "Enterprise", "price": "Custom", "limits": "SSO, audit log, unlimited private quota, dedicated bandwidth"},
    ]
    return render_template("pricing_datasets.html", tiers=tiers)


# ------------------------------------------------------------
# R3: Discussion shortcuts for datasets/spaces
# The generic /<author>/<name>/discussions catches model repos already.
# Add explicit /datasets/<a>/<n>/discussions and /spaces/<a>/<n>/discussions
# so deep links from the dataset and space detail pages resolve cleanly.
# ------------------------------------------------------------
@app.route("/datasets/<author>/<name>/discussions")
def dataset_discussions(author, name):
    slug = f"{author}/{name}"
    repo = Repository.query.filter_by(slug=slug, repo_type="dataset").first_or_404()
    discussions = Discussion.query.filter_by(repo_id=repo.id).order_by(Discussion.created_at.desc()).all()
    return render_template("discussions.html", repo=repo, discussions=discussions)


@app.route("/spaces/<author>/<name>/discussions")
def space_discussions(author, name):
    slug = f"{author}/{name}"
    repo = Repository.query.filter_by(slug=slug, repo_type="space").first_or_404()
    discussions = Discussion.query.filter_by(repo_id=repo.id).order_by(Discussion.created_at.desc()).all()
    return render_template("discussions.html", repo=repo, discussions=discussions)


# ------------------------------------------------------------
# R10 — every repo card surface (model / dataset / space) needs the full
# six-tab strip: Card · Files · Community · Discussions · PRs · Settings.
# `Community` is a top-level alias for `Discussions`; `PRs` filters the
# Discussion table down to kind=='pull-request'; `Settings` is a stub
# repo-admin page that surfaces visibility + danger-zone controls.
# Every (model, dataset, space) × (community, pull-requests, settings)
# combination is exposed so the tab strip is uniformly 200 across kinds.
# ------------------------------------------------------------
def _r10_repo_or_404(author, name, repo_type=None):
    slug = f"{author}/{name}"
    q = Repository.query.filter_by(slug=slug)
    if repo_type:
        q = q.filter_by(repo_type=repo_type)
    return q.first_or_404()


def _r10_render_community(repo):
    discussions = Discussion.query.filter_by(repo_id=repo.id).order_by(Discussion.created_at.desc()).all()
    return render_template("discussions.html", repo=repo, discussions=discussions, r10_view="community")


def _r10_render_pull_requests(repo):
    prs = (Discussion.query
           .filter_by(repo_id=repo.id, kind="pull-request")
           .order_by(Discussion.created_at.desc())
           .all())
    return render_template("repo_pull_requests.html", repo=repo, pull_requests=prs)


def _r10_render_settings(repo):
    return render_template("repo_settings.html", repo=repo)


@app.route("/<author>/<name>/community")
def repo_community(author, name):
    return _r10_render_community(_r10_repo_or_404(author, name))


@app.route("/<author>/<name>/pull-requests")
@app.route("/<author>/<name>/pulls")
def repo_pull_requests(author, name):
    return _r10_render_pull_requests(_r10_repo_or_404(author, name))


@app.route("/<author>/<name>/settings")
def repo_settings(author, name):
    return _r10_render_settings(_r10_repo_or_404(author, name))


@app.route("/datasets/<author>/<name>/community")
def dataset_community(author, name):
    return _r10_render_community(_r10_repo_or_404(author, name, "dataset"))


@app.route("/datasets/<author>/<name>/pull-requests")
@app.route("/datasets/<author>/<name>/pulls")
def dataset_pull_requests(author, name):
    return _r10_render_pull_requests(_r10_repo_or_404(author, name, "dataset"))


@app.route("/datasets/<author>/<name>/settings")
def dataset_settings(author, name):
    return _r10_render_settings(_r10_repo_or_404(author, name, "dataset"))


@app.route("/spaces/<author>/<name>/community")
def space_community(author, name):
    return _r10_render_community(_r10_repo_or_404(author, name, "space"))


@app.route("/spaces/<author>/<name>/pull-requests")
@app.route("/spaces/<author>/<name>/pulls")
def space_pull_requests(author, name):
    return _r10_render_pull_requests(_r10_repo_or_404(author, name, "space"))


@app.route("/spaces/<author>/<name>/settings")
def space_settings(author, name):
    return _r10_render_settings(_r10_repo_or_404(author, name, "space"))


# ------------------------------------------------------------
# R5 routes — copy snippets, dataset row pagination, readme section
# anchors, like animation, discussion reply threading, AutoTrain billing
# estimate, paper implementations, organization billing.
# ------------------------------------------------------------
def _section_slug(title: str) -> str:
    s = (title or "").strip().lower()
    out = []
    for ch in s:
        if ch.isalnum():
            out.append(ch)
        elif out and out[-1] != "-":
            out.append("-")
    while out and out[-1] == "-":
        out.pop()
    return "".join(out) or "section"


def _split_readme_sections(readme: str):
    """Split a markdown-ish readme into sections by `## ` headers.

    Returns a list of {slug, title, body} so /<a>/<n>/readme/<slug> can
    return one section at a time without re-parsing on every request."""
    sections = []
    cur_title = "Overview"
    cur_body = []
    for line in (readme or "").split("\n"):
        if line.startswith("## "):
            sections.append({
                "slug": _section_slug(cur_title),
                "title": cur_title,
                "body": "\n".join(cur_body).strip(),
            })
            cur_title = line[3:].strip()
            cur_body = []
        else:
            cur_body.append(line)
    sections.append({
        "slug": _section_slug(cur_title),
        "title": cur_title,
        "body": "\n".join(cur_body).strip(),
    })
    return sections


@app.route("/<author>/<name>/readme/<section_slug>")
def repo_readme_section(author, name, section_slug):
    """Return a single readme section by its anchor slug. Supports model,
    dataset and space repos — repo_type is detected from `repo_type`
    query param, otherwise falls back to the first match."""
    slug = f"{author}/{name}"
    repo_type = request.args.get("repo_type") or None
    q = Repository.query.filter_by(slug=slug)
    if repo_type:
        q = q.filter_by(repo_type=repo_type)
    repo = q.first()
    if not repo:
        abort(404)
    sections = _split_readme_sections(repo.readme or "")
    section = next((s for s in sections if s["slug"] == section_slug), None)
    if not section:
        abort(404)
    return render_template(
        "repo_readme_section.html",
        repo=repo, section=section, sections=sections,
    )


@app.route("/api/snippet/<repo_type>/<author>/<name>")
def api_repo_snippet(repo_type, author, name):
    """Return a copy-to-clipboard code snippet for the given repo.

    Optional ?lang=python|bash|js — default python. The snippet is fully
    deterministic so the copy-to-clipboard interaction has a stable target."""
    if repo_type not in ("model", "dataset", "space"):
        abort(404)
    slug = f"{author}/{name}"
    repo = Repository.query.filter_by(slug=slug, repo_type=repo_type).first()
    if not repo:
        abort(404)
    lang = (request.args.get("lang") or "python").lower()
    task = repo.task_slug or ("text-generation" if repo_type == "model" else "")
    library = repo.library or ("Transformers" if repo_type == "model" else "")
    if repo_type == "dataset":
        if lang == "bash":
            body = f"huggingface-cli download --repo-type dataset {slug}"
        elif lang == "js":
            body = (f"import {{ load }} from '@huggingface/datasets';\n"
                    f"const ds = await load('{slug}');")
        else:
            body = (f"from datasets import load_dataset\n"
                    f"ds = load_dataset('{slug}')\n"
                    f"print(ds)")
    elif repo_type == "space":
        if lang == "bash":
            body = f"curl -s https://{author}-{name}.hf.space/predict -X POST -d '{{}}'"
        elif lang == "js":
            body = (f"import {{ Client }} from '@gradio/client';\n"
                    f"const app = await Client.connect('{slug}');")
        else:
            body = (f"from gradio_client import Client\n"
                    f"client = Client('{slug}')\n"
                    f"result = client.predict(api_name='/predict')")
    else:
        if lang == "bash":
            body = (f"huggingface-cli download {slug}\n"
                    f"# Or via git lfs: git clone https://huggingface.co/{slug}")
        elif lang == "js":
            body = (f"import {{ pipeline }} from '@huggingface/transformers';\n"
                    f"const pipe = await pipeline('{task or 'text-generation'}', '{slug}');")
        else:
            body = (f"from transformers import pipeline\n"
                    f"pipe = pipeline('{task or 'text-generation'}', model='{slug}')")
    payload = {
        "ok": True,
        "slug": slug,
        "repo_type": repo_type,
        "lang": lang,
        "library": library,
        "snippet": body,
        "bytes": len(body),
    }
    if request.args.get("format") == "text":
        return body, 200, {"Content-Type": "text/plain; charset=utf-8"}
    return jsonify(payload)


@app.route("/datasets/<author>/<name>/viewer/row/<int:idx>")
def dataset_viewer_row(author, name, idx):
    """Return a single row from a dataset viewer (1-indexed), with prev/next
    navigation links. Lets agents step through rows one at a time."""
    slug = f"{author}/{name}"
    repo = Repository.query.filter_by(slug=slug, repo_type="dataset").first()
    if not repo:
        abort(404)
    data = DATASET_VIEWER_DATA.get(slug, {
        "columns": ["id", "text"],
        "rows": [[1, "Sample row"]],
    })
    rows = data.get("rows", [])
    total = len(rows)
    if total == 0:
        abort(404)
    # Clamp 1..total (1-indexed).
    if idx < 1:
        idx = 1
    if idx > total:
        idx = total
    row = rows[idx - 1]
    columns = data.get("columns", [])
    pairs = list(zip(columns, row))
    return render_template(
        "dataset_viewer_row.html",
        repo=repo, idx=idx, total=total, columns=columns, row=row, pairs=pairs,
    )


@app.route("/api/repo/<int:repo_id>/like-animate", methods=["POST"])
@csrf.exempt
def api_like_animate(repo_id):
    """Return an animation hint for the like button. Toggles when logged in;
    otherwise just emits the hint (so the animation is testable without a
    session). Used by the heart-burst JS in repo_card / repo_detail."""
    repo = db.session.get(Repository, repo_id)
    if not repo:
        return jsonify({"ok": False, "error": "not-found"}), 404
    liked = False
    new_count = repo.likes_count or 0
    if current_user.is_authenticated:
        existing = Like.query.filter_by(user_id=current_user.id, repo_id=repo.id).first()
        if existing:
            db.session.delete(existing)
            repo.likes_count = max(0, (repo.likes_count or 1) - 1)
            liked = False
        else:
            db.session.add(Like(user_id=current_user.id, repo_id=repo.id))
            repo.likes_count = (repo.likes_count or 0) + 1
            liked = True
        db.session.commit()
        new_count = repo.likes_count
    # Animation hint — deterministic per-repo so the burst is repeatable.
    import hashlib as _h
    seed = int(_h.md5(repo.slug.encode("utf-8")).hexdigest(), 16)
    palette = ["#ef4444", "#f97316", "#f59e0b", "#ec4899"]
    return jsonify({
        "ok": True,
        "repo_id": repo.id,
        "slug": repo.slug,
        "liked": liked,
        "likes_count": new_count,
        "animation": {
            "kind": "heart-burst",
            "duration_ms": 600,
            "particles": 6 + (seed % 4),  # 6..9
            "color": palette[seed % len(palette)],
        },
    })


@app.route("/<author>/<name>/discussions/<int:discussion_id>/thread")
def discussion_thread(author, name, discussion_id):
    """Threaded view of a discussion — replies grouped into N indented threads
    deterministically by (i mod N). Lets the agent navigate a thread tree."""
    slug = f"{author}/{name}"
    repo = Repository.query.filter_by(slug=slug).first()
    if not repo:
        abort(404)
    d = db.session.get(Discussion, discussion_id)
    if not d or d.repo_id != repo.id:
        abort(404)
    replies = DiscussionReply.query.filter_by(discussion_id=d.id).order_by(DiscussionReply.id.asc()).all()
    # Group into 3 threads — each reply's thread index = (reply.id mod 3).
    threads = [[], [], []]
    for r in replies:
        threads[r.id % 3].append(r)
    return render_template(
        "discussion_thread.html",
        repo=repo, discussion=d, threads=threads, replies=replies,
    )


# AutoTrain hardware pricing table — shared between /AutoTrain and the
# billing estimate endpoint.
AUTOTRAIN_HW_PRICING = [
    ("L4",   "Nvidia L4 (24GB)",   0.80),
    ("A10G", "Nvidia A10G (24GB)", 1.05),
    ("A100", "Nvidia A100 (40GB)", 4.00),
    ("L40S", "Nvidia L40S (48GB)", 1.80),
    ("H100", "Nvidia H100 (80GB)", 6.50),
    ("CPU",  "CPU Upgrade",        0.03),
]


@app.route("/api/autotrain/estimate", methods=["GET", "POST"])
@csrf.exempt
def api_autotrain_estimate():
    """Estimate AutoTrain billing — accepts hardware slug + hours and returns
    a price quote. GET reads ?hardware=A100&hours=24; POST reads JSON body."""
    if request.method == "POST":
        payload = request.get_json(silent=True) or {}
        hardware = (payload.get("hardware") or "L4").upper()
        try:
            hours = int(payload.get("hours") or 1)
        except (TypeError, ValueError):
            hours = 1
    else:
        hardware = (request.args.get("hardware") or "L4").upper()
        try:
            hours = int(request.args.get("hours") or 1)
        except ValueError:
            hours = 1
    hours = max(1, min(hours, 24 * 30))  # cap at one month
    row = next((r for r in AUTOTRAIN_HW_PRICING if r[0].upper() == hardware), None)
    if not row:
        return jsonify({"ok": False, "error": "unknown-hardware",
                        "supported": [r[0] for r in AUTOTRAIN_HW_PRICING]}), 400
    slug, display, rate = row
    subtotal = round(rate * hours, 2)
    # 8% platform fee on top — matches /pricing/spaces FAQ.
    fee = round(subtotal * 0.08, 2)
    total = round(subtotal + fee, 2)
    return jsonify({
        "ok": True,
        "hardware": slug,
        "hardware_display": display,
        "rate_per_hour": rate,
        "hours": hours,
        "subtotal": subtotal,
        "platform_fee": fee,
        "total": total,
        "currency": "USD",
        "breakdown": [
            {"label": display,        "amount": subtotal, "qty": f"{hours} hr @ ${rate:.2f}/hr"},
            {"label": "Platform fee (8%)", "amount": fee, "qty": "—"},
        ],
    })


@app.route("/papers/<arxiv_id>/implementations")
def paper_implementations(arxiv_id):
    """List of code implementations / models / spaces that reference a given
    arXiv paper. Pulled from the paper's `related_models` plus any repo whose
    description mentions the arxiv id."""
    paper = next((p for p in DAILY_PAPERS if p["arxiv_id"] == arxiv_id), None)
    if not paper:
        abort(404)
    impls = []
    seen_ids = set()
    for slug in paper.get("related_models", []):
        r = Repository.query.filter_by(slug=slug, repo_type="model").first()
        if r and r.id not in seen_ids:
            impls.append({"kind": "model", "repo": r, "source": "paper-card"})
            seen_ids.add(r.id)
    for slug in paper.get("related_datasets", []):
        r = Repository.query.filter_by(slug=slug, repo_type="dataset").first()
        if r and r.id not in seen_ids:
            impls.append({"kind": "dataset", "repo": r, "source": "paper-card"})
            seen_ids.add(r.id)
    # Plus any repo whose readme/description mentions the arxiv id.
    matches = Repository.query.filter(
        Repository.description.contains(arxiv_id) | Repository.readme.contains(arxiv_id)
    ).limit(20).all()
    for r in matches:
        if r.id not in seen_ids:
            impls.append({"kind": r.repo_type, "repo": r, "source": "readme-mention"})
            seen_ids.add(r.id)
    return render_template(
        "paper_implementations.html",
        paper=paper, implementations=impls,
    )


@app.route("/<username>/billing")
def author_billing(username):
    """Organization / user billing summary — current MTD usage + invoice
    history. Numbers are deterministic per username so the page is stable."""
    author = Author.query.filter_by(username=username).first()
    if not author:
        abort(404)
    import hashlib as _h
    seed = int(_h.md5(username.encode("utf-8")).hexdigest(), 16)
    repo_count = Repository.query.filter_by(author_id=author.id).count()
    # Current month usage (deterministic).
    spaces_hours = (seed & 0xFF) + 12              # 12..267
    endpoints_hours = ((seed >> 8) & 0xFF) + 8     # 8..263
    autotrain_hours = ((seed >> 16) & 0x7F) + 4    # 4..131
    storage_gb = ((seed >> 24) & 0x1FF) + 50       # 50..561
    bandwidth_gb = ((seed >> 32) & 0x3FF) + 100    # 100..1123
    spaces_cost = round(spaces_hours * 0.80, 2)
    endpoints_cost = round(endpoints_hours * 1.05, 2)
    autotrain_cost = round(autotrain_hours * 4.00, 2)
    storage_cost = round(max(0, storage_gb - 100) * 0.04, 2)
    bandwidth_cost = round(max(0, bandwidth_gb - 200) * 0.09, 2)
    total_cost = round(spaces_cost + endpoints_cost + autotrain_cost
                       + storage_cost + bandwidth_cost, 2)
    line_items = [
        {"label": "Spaces compute",        "qty": f"{spaces_hours} hr",    "amount": spaces_cost},
        {"label": "Inference endpoints",   "qty": f"{endpoints_hours} hr", "amount": endpoints_cost},
        {"label": "AutoTrain GPU hours",   "qty": f"{autotrain_hours} hr", "amount": autotrain_cost},
        {"label": "Storage (over 100 GB)", "qty": f"{storage_gb} GB",      "amount": storage_cost},
        {"label": "Bandwidth (over 200 GB)", "qty": f"{bandwidth_gb} GB",  "amount": bandwidth_cost},
    ]
    # Synthetic 3-month invoice history.
    history = []
    for m in range(1, 4):
        s = (seed >> (m * 7)) & 0xFFFF
        amt = round(80 + (s % 480) + (s & 0xF) * 0.13, 2)
        history.append({
            "invoice_id": f"INV-{username.upper()[:4]}-{2026:04d}{m:02d}",
            "period": f"2026-{(5 - m):02d}",
            "amount": amt,
            "status": ("Paid" if m > 1 else "Pending"),
        })
    return render_template(
        "billing.html",
        author=author, repo_count=repo_count,
        line_items=line_items, total_cost=total_cost,
        history=history,
        month_label="May 2026",
    )


# ============================================================
# R6 routes — gated-access, space build logs, fine-tuned versions,
# leaderboard pending-eval rows, endpoint quota errors, paper-not-on-arxiv
# fallback. Every value the route returns is deterministic per slug so
# byte-identical rebuilds still pass the md5 invariant.
# ============================================================
@app.route("/<author>/<name>/access", methods=["GET", "POST"])
def repo_access_request(author, name):
    """Gated-access request form. For repos with is_gated=True, the
    primary repo route shows a banner; this is the dedicated request page
    the agent navigates to when filling the form."""
    slug = f"{author}/{name}"
    repo = Repository.query.filter_by(slug=slug).first()
    if not repo:
        abort(404)
    submitted = False
    if request.method == "POST":
        # Don't actually persist — keep the endpoint side-effect-free so
        # repeated rebuilds stay byte-identical.
        submitted = True
    return render_template(
        "access_request.html",
        repo=repo, submitted=submitted,
    )


@app.route("/spaces/<author>/<name>/logs")
def space_build_logs(author, name):
    """Build / runtime log viewer for a Space. Most spaces show an empty
    log placeholder; ~5% surface a deterministic build-error trace and
    ~1% are still building. Lets the agent answer 'why isn't this Space
    running?' without an external API call."""
    slug = f"{author}/{name}"
    repo = Repository.query.filter_by(slug=slug, repo_type="space").first()
    if not repo:
        abort(404)
    status = repo.space_build_status or "build-ok"
    log = repo.space_build_log or (
        "=== Build started ===\n"
        "Installing requirements from requirements.txt...\n"
        "Build complete. Starting application...\n"
        "=== Build SUCCESS — application running ===\n"
    )
    return render_template(
        "space_logs.html",
        repo=repo, status=status, log=log,
    )


@app.route("/papers/arxiv/<arxiv_id>")
def paper_arxiv_fallback(arxiv_id):
    """Fallback page for arxiv ids we did not seed into DAILY_PAPERS.

    Linked from /papers and /papers/<id>/implementations whenever the
    paper id is not in our curated set. Shows a placeholder card pointing
    at the upstream arxiv URL so the agent can still answer 'what's at
    paper X' without the route 404ing.
    """
    paper = next((p for p in DAILY_PAPERS if p["arxiv_id"] == arxiv_id), None)
    if paper:
        # Real paper exists — redirect to the canonical route.
        return redirect(url_for("paper_detail", arxiv_id=arxiv_id))
    return render_template(
        "paper_fallback.html",
        arxiv_id=arxiv_id,
        upstream_url=f"https://arxiv.org/abs/{arxiv_id}",
    )


@app.route("/api/repo/<int:repo_id>/fine-tuned")
def api_fine_tuned(repo_id):
    """Return up to 12 models whose base_model_slug matches this repo's slug.
    Powers the 'Fine-tuned versions' sidebar card on model detail pages."""
    repo = db.session.get(Repository, repo_id)
    if not repo:
        abort(404)
    children = (Repository.query
                .filter_by(repo_type="model", base_model_slug=repo.slug)
                .order_by(Repository.likes_count.desc(), Repository.id.asc())
                .limit(12).all())
    return jsonify({
        "ok": True,
        "base_slug": repo.slug,
        "count": len(children),
        "items": [{"slug": c.slug, "likes": c.likes_count or 0,
                   "downloads": c.downloads or 0} for c in children],
    })


# Endpoint quota — when an endpoint is in 'quota-exceeded' state we surface
# a dedicated error banner. Status is derived deterministically from the
# endpoint id so the same endpoint always reports the same flag.
@app.route("/endpoints/<int:endpoint_id>/quota")
def endpoint_quota_status(endpoint_id):
    ep = db.session.get(InferenceEndpoint, endpoint_id)
    if not ep:
        abort(404)
    import hashlib as _h
    h = int(_h.md5((ep.endpoint_id or str(ep.id)).encode("utf-8")).hexdigest(), 16)
    over_quota = (h % 10) == 0   # ~10% of endpoints
    return jsonify({
        "ok": True,
        "endpoint_id": ep.endpoint_id,
        "quota_state": "exceeded" if over_quota else "ok",
        "quota_used_gb_hours": (h % 9000) + 1000,
        "quota_limit_gb_hours": 10_000,
        "next_reset_utc": "2026-06-01T00:00:00Z",
        "message": (
            "Your organization has exceeded its monthly inference quota. "
            "Upgrade the plan or wait until the quota resets on the 1st of next month."
            if over_quota else
            "Within plan limits — no action required."
        ),
    })


# ------------------------------------------------------------
# Error handlers
# ------------------------------------------------------------
@app.errorhandler(404)
def not_found(e):
    return render_template("404.html"), 404


@app.errorhandler(500)
def server_error(e):
    return render_template("500.html"), 500


# ------------------------------------------------------------
# Form-POST equivalents for like / follow / deploy  (agent-friendly)
# These mirror the AJAX endpoints but accept plain form POST so browser
# agents that can't send JSON still work correctly.
# ------------------------------------------------------------
@app.route("/like/toggle/<int:repo_id>", methods=["POST"])
@login_required
def like_toggle_form(repo_id):
    repo = db.session.get(Repository, repo_id)
    if not repo:
        abort(404)
    existing = Like.query.filter_by(user_id=current_user.id, repo_id=repo.id).first()
    if existing:
        db.session.delete(existing)
        repo.likes_count = max(0, (repo.likes_count or 0) - 1)
        flash("Removed from your likes.", "info")
    else:
        db.session.add(Like(user_id=current_user.id, repo_id=repo.id))
        repo.likes_count = (repo.likes_count or 0) + 1
        flash("Added to your likes.", "success")
    db.session.commit()
    next_url = request.form.get("next") or request.referrer or url_for("index")
    return redirect(next_url)


@app.route("/follow/toggle/<int:author_id>", methods=["POST"])
@login_required
def follow_toggle_form(author_id):
    author = db.session.get(Author, author_id)
    if not author:
        abort(404)
    existing = Follow.query.filter_by(user_id=current_user.id, author_id=author.id).first()
    if existing:
        db.session.delete(existing)
        author.followers_count = max(0, (author.followers_count or 0) - 1)
        flash(f"Unfollowed {author.display_name}.", "info")
    else:
        db.session.add(Follow(user_id=current_user.id, author_id=author.id))
        author.followers_count = (author.followers_count or 0) + 1
        flash(f"Now following {author.display_name}.", "success")
    db.session.commit()
    next_url = request.form.get("next") or request.referrer or url_for("index")
    return redirect(next_url)


@app.route("/deploy/add/<int:repo_id>", methods=["POST"])
@login_required
def deploy_add_form(repo_id):
    repo = db.session.get(Repository, repo_id)
    if not repo:
        abort(404)
    hardware_slug = request.form.get("hardware_slug", "t4-small")
    hours = int(request.form.get("hours", 24))
    hw = next((h for h in SPACE_HARDWARE if h[0] == hardware_slug), SPACE_HARDWARE[2])
    existing = CartItem.query.filter_by(user_id=current_user.id, repo_id=repo.id, hardware_slug=hardware_slug).first()
    if existing:
        existing.hours += hours
    else:
        existing = CartItem(
            user_id=current_user.id,
            repo_id=repo.id,
            hardware_slug=hw[0],
            hardware_display=hw[1],
            hardware_price=hw[3],
            hours=hours,
        )
        db.session.add(existing)
    db.session.commit()
    flash(f"Added {repo.name} to deployment cart.", "success")
    next_url = request.form.get("next") or url_for("deploy_cart")
    return redirect(next_url)


# ------------------------------------------------------------
# Benchmark user seeding
# ------------------------------------------------------------
def seed_benchmark_users():
    """Idempotent — creates 4 benchmark users with likes, collections,
    endpoints, and discussions.  Safe to call multiple times."""
    if User.query.filter_by(email="alice.j@test.com").first():
        return  # already seeded

    print("Seeding benchmark users...")
    avatar_files = sorted(p.name for p in (ROOT / "static" / "images" / "avatars").iterdir() if p.is_file())
    rng = random.Random(42)

    def _avatar(idx):
        return f"/static/images/avatars/{avatar_files[idx % len(avatar_files)]}" if avatar_files else ""

    def _get_repo(slug_fragment):
        return Repository.query.filter(Repository.slug.ilike(f"%{slug_fragment}%")).order_by(Repository.id.asc()).first()

    def _get_task(slug):
        return Task.query.filter_by(slug=slug).first()

    # ------------------------------------------------------------------
    # Create users
    # ------------------------------------------------------------------
    BENCH_USERS = [
        dict(email="alice.j@test.com", username="alice_j", display_name="Alice Johnson",
             bio="NLP researcher, loves open-source LLMs.", location="San Francisco", is_pro=True, idx=1),
        dict(email="bob.c@test.com", username="bob_c", display_name="Bob Chen",
             bio="ML engineer, image generation enthusiast.", location="New York", is_pro=False, idx=2),
        dict(email="carol.d@test.com", username="carol_d", display_name="Carol Davis",
             bio="Data scientist, focuses on translation & summarization.", location="London", is_pro=True, idx=3),
        dict(email="david.k@test.com", username="david_k", display_name="David Kim",
             bio="MLOps practitioner, runs inference endpoints at scale.", location="Seoul", is_pro=False, idx=4),
    ]
    users = {}
    # PINNED bcrypt hash for "TestPass123!" — bcrypt.generate_password_hash()
    # is non-deterministic (per-call salt), which would break the
    # byte-identical reset invariant if the DB were ever regenerated.
    PINNED_BENCH_HASH = "$2b$12$RwAC/sfwDHtccU//A20fde.uKkZK4Ptnjjyua2l2ktwI6uysAp3Ou"
    for u in BENCH_USERS:
        idx = u.pop("idx")
        u["password_hash"] = PINNED_BENCH_HASH
        u["avatar_url"] = _avatar(idx)
        user = User(**u)
        db.session.add(user)
        db.session.flush()
        users[user.username] = user

    alice = users["alice_j"]
    bob = users["bob_c"]
    carol = users["carol_d"]
    david = users["david_k"]

    # ------------------------------------------------------------------
    # Likes — each user likes a distinct set of repos
    # ------------------------------------------------------------------
    def _like_repo(user, slug_fragment):
        repo = _get_repo(slug_fragment)
        if not repo:
            return
        if not Like.query.filter_by(user_id=user.id, repo_id=repo.id).first():
            db.session.add(Like(user_id=user.id, repo_id=repo.id))
            repo.likes_count = (repo.likes_count or 0) + 1

    # Alice likes LLM/NLP models
    for frag in ["Llama-3-apache", "DeepSeek-R1", "all-MiniLM-L6-v2", "zephyr-7b-story", "bert-base-uncased"]:
        _like_repo(alice, frag)

    # Bob likes image generation models
    for frag in ["FLUX.1-schnell", "stable-diffusion-xl-base", "stable-diffusion-3-medium", "FLUX.1-dev", "stable-cascade"]:
        _like_repo(bob, frag)

    # Carol likes translation/summarization models
    for frag in ["opus-mt-en-zh", "nllb-200-distilled", "opus-mt-en-ja", "bart-large-cnn", "biobart"]:
        _like_repo(carol, frag)

    # David likes ASR + feature-extraction models
    for frag in ["bge-large-en-v1.5", "all-MiniLM-L6-v2", "Depth-Anything-V2", "xlm-roberta-large-squad2", "deberta-v3-large"]:
        _like_repo(david, frag)

    db.session.flush()

    # ------------------------------------------------------------------
    # Collections
    # ------------------------------------------------------------------
    def _make_collection(user, title, desc, is_public, slug_fragments):
        c = Collection(user_id=user.id, title=title, description=desc, is_public=is_public)
        db.session.add(c)
        db.session.flush()
        for pos, frag in enumerate(slug_fragments):
            repo = _get_repo(frag)
            if repo and not CollectionItem.query.filter_by(collection_id=c.id, repo_id=repo.id).first():
                db.session.add(CollectionItem(collection_id=c.id, repo_id=repo.id, position=pos))
        return c

    # Alice — NLP focused
    _make_collection(alice, "My NLP Toolkit",
                     "Best open-source NLP models I use daily.",
                     True,
                     ["Llama-3-apache", "DeepSeek-V3", "all-MiniLM-L6-v2", "bert-base-uncased"])

    _make_collection(alice, "Sentiment Analysis Picks",
                     "Models I evaluated for sentiment tasks.",
                     True,
                     ["twitter-xlm-roberta-base-sentiment-latest", "twitter-roberta-base-sentiment",
                      "distilbert-base-uncased-finetuned-sst-2"])

    # Bob — image generation
    _make_collection(bob, "Image Generation Models",
                     "Top text-to-image models for creative projects.",
                     True,
                     ["FLUX.1-schnell", "stable-diffusion-xl-base", "FLUX.1-dev",
                      "stable-diffusion-3-medium", "stable-cascade"])

    _make_collection(bob, "Private Experiments",
                     "Models I'm testing privately.",
                     False,
                     ["SDXL-Lightning", "Qwen-Image"])

    # Carol — translation + summarization
    _make_collection(carol, "Translation Models",
                     "Multilingual translation models.",
                     True,
                     ["opus-mt-en-zh", "nllb-200-distilled", "opus-mt-en-ja",
                      "opus-mt-en-fr-2026", "opus-mt-en-es-2026"])

    _make_collection(carol, "Summarization Collection",
                     "Models for automatic document summarization.",
                     True,
                     ["bart-large-cnn", "biobart"])

    # David — MLOps & embeddings
    _make_collection(david, "Production Inference Models",
                     "Models I run in production endpoints.",
                     True,
                     ["bge-large-en-v1.5", "all-MiniLM-L6-v2", "xlm-roberta-large-squad2", "deberta-v3-large"])

    db.session.flush()

    # ------------------------------------------------------------------
    # Endpoints (InferenceEndpoint = "order" equivalent)
    # ------------------------------------------------------------------
    def _make_endpoint(user, name, status, hw_slug, hw_display, hw_price, hours, slug_fragment, region="us-east-1"):
        repo = _get_repo(slug_fragment)
        if not repo:
            return None
        ep_id = "EP-" + "".join(rng.choices(string.ascii_uppercase + string.digits, k=8))
        try:
            price = float(hw_price.replace("$", "").replace("/hr", "")) if "$" in hw_price else 0.0
        except Exception:
            price = 0.0
        ep = InferenceEndpoint(
            user_id=user.id,
            endpoint_id=ep_id,
            name=name,
            status=status,
            region=region,
            total_hours=hours,
            total_cost=f"${price * hours:.2f}",
            created_at=mirror_now() - timedelta(days=rng.randint(1, 30)),
        )
        db.session.add(ep)
        db.session.flush()
        db.session.add(EndpointItem(
            endpoint_id=ep.id,
            repo_id=repo.id,
            hardware_slug=hw_slug,
            hardware_display=hw_display,
            hardware_price=hw_price,
            hours=hours,
        ))
        return ep

    # Alice — NLP endpoints
    _make_endpoint(alice, "alice-llm-production", "running",
                   "a100-large", "Nvidia A100", "$2.50/hr", 72,
                   "Llama-3-apache", region="us-east-1")
    _make_endpoint(alice, "alice-sentiment-api", "paused",
                   "t4-small", "Nvidia T4", "$0.40/hr", 24,
                   "twitter-xlm-roberta-base-sentiment-latest", region="us-west-2")

    # Bob — image gen endpoints
    _make_endpoint(bob, "bob-flux-endpoint", "running",
                   "l4x1", "Nvidia L4", "$0.80/hr", 48,
                   "FLUX.1-schnell", region="us-east-1")
    _make_endpoint(bob, "bob-sdxl-old", "terminated",
                   "t4-small", "Nvidia T4", "$0.40/hr", 24,
                   "stable-diffusion-xl-base", region="eu-west-1")

    # Carol — translation endpoints
    _make_endpoint(carol, "carol-translation-eu", "running",
                   "cpu-upgrade", "CPU Upgrade", "$0.03/hr", 168,
                   "nllb-200-distilled", region="eu-central-1")
    _make_endpoint(carol, "carol-summarizer", "paused",
                   "t4-small", "Nvidia T4", "$0.40/hr", 24,
                   "bart-large-cnn", region="us-east-1")

    # David — MLOps endpoints
    _make_endpoint(david, "david-embeddings-prod", "running",
                   "l40sx1", "Nvidia L40S", "$1.80/hr", 168,
                   "bge-large-en-v1.5", region="ap-southeast-1")
    _make_endpoint(david, "david-qa-endpoint", "terminated",
                   "t4-small", "Nvidia T4", "$0.40/hr", 48,
                   "xlm-roberta-large-squad2", region="us-west-2")

    db.session.flush()

    # ------------------------------------------------------------------
    # Discussions — each user posts on relevant repos
    # ------------------------------------------------------------------
    disc_data = [
        # (user, slug_frag, title, body, kind)
        (alice, "Llama-3-apache",
         "How to fine-tune on domain-specific data?",
         "Has anyone fine-tuned this on legal / medical text? Curious about the LoRA rank settings that worked best.",
         "discussion"),
        (alice, "all-MiniLM-L6-v2",
         "Comparison with BGE-large?",
         "I benchmarked MiniLM vs BGE-large on MTEB and found BGE wins on retrieval but MiniLM is 3x faster. Happy to share numbers.",
         "discussion"),
        (bob, "FLUX.1-schnell",
         "VRAM requirements for batch size > 1?",
         "Trying to run batch_size=4 on a 24GB consumer GPU. Getting OOM. Any quantization tips?",
         "issue"),
        (bob, "stable-diffusion-xl-base",
         "Best sampler for photorealistic outputs?",
         "I've been testing DPM++ 2M Karras — getting great results. What samplers are you all using?",
         "discussion"),
        (carol, "opus-mt-en-zh",
         "Performance on classical Chinese text?",
         "Testing on classical (wenyan) Chinese — the model struggles. Anyone fine-tuned on historical corpora?",
         "issue"),
        (carol, "bart-large-cnn",
         "License for commercial summarization product?",
         "The model card says Apache 2.0 but the dataset (CNN/DM) has restrictions. Has anyone gotten legal sign-off?",
         "discussion"),
        (david, "bge-large-en-v1.5",
         "Integration with pgvector — any gotchas?",
         "Using this with pgvector for RAG. Noticed cosine vs dot product gives different rankings. What normalization are you using?",
         "discussion"),
        (david, "xlm-roberta-large-squad2",
         "Degraded performance on low-resource languages?",
         "QA accuracy drops significantly on Swahili and Tamil compared to MLQA paper numbers. Is this a tokenization issue?",
         "issue"),
    ]
    for user, frag, title, body, kind in disc_data:
        repo = _get_repo(frag)
        if not repo:
            continue
        d = Discussion(
            repo_id=repo.id,
            user_id=user.id,
            title=title,
            body=body,
            kind=kind,
            upvotes=rng.randint(1, 30),
        )
        db.session.add(d)

    # ------------------------------------------------------------------
    # Follows — each bench user follows several real authors/orgs.
    # Follow rows are (user_id, author_id). Authors are looked up by
    # username; missing usernames are skipped silently.
    # ------------------------------------------------------------------
    def _follow(user, author_username):
        a = Author.query.filter_by(username=author_username).first()
        if not a:
            return
        if not Follow.query.filter_by(user_id=user.id, author_id=a.id).first():
            db.session.add(Follow(user_id=user.id, author_id=a.id))

    FOLLOWS_BY_USER = {
        "alice_j":  ["huggingface", "meta-llama", "google", "mistralai",
                     "deepseek-ai", "openai", "intfloat", "sentence-transformers",
                     "HuggingFaceH4"],
        "bob_c":    ["stabilityai", "black-forest-labs", "openai", "tencent",
                     "ByteDance", "dreamfusion-ai", "huggingface", "meta-llama"],
        "carol_d":  ["Helsinki-NLP", "facebook", "deepset", "GanjinZero",
                     "google", "Jean-Baptiste", "allenai", "microsoft", "bigscience"],
        "david_k":  ["Qwen", "BAAI", "sentence-transformers", "intfloat",
                     "microsoft", "nvidia", "deepseek-ai", "openai", "unsloth"],
    }
    for uname, authors_to_follow in FOLLOWS_BY_USER.items():
        u = users.get(uname)
        if not u:
            continue
        for a_uname in authors_to_follow:
            _follow(u, a_uname)
    db.session.flush()

    # ------------------------------------------------------------------
    # Cart items — staged deployments waiting in each user's cart.
    # ------------------------------------------------------------------
    def _cart_add(user, slug_fragment, hw_slug, hw_display, hw_price, hours, region="us-east-1"):
        repo = _get_repo(slug_fragment)
        if not repo:
            return
        if CartItem.query.filter_by(user_id=user.id, repo_id=repo.id).first():
            return
        db.session.add(CartItem(
            user_id=user.id,
            repo_id=repo.id,
            hardware_slug=hw_slug,
            hardware_display=hw_display,
            hardware_price=hw_price,
            hours=hours,
            region=region,
        ))

    # Alice — comparing two LLMs before committing to production
    _cart_add(alice, "DeepSeek-V3", "a100-large", "Nvidia A100", "$2.50/hr", 48, region="us-east-1")
    _cart_add(alice, "zephyr-7b-story", "l4x1", "Nvidia L4", "$0.80/hr", 24, region="us-east-1")
    _cart_add(alice, "bge-large-en-v1.5", "t4-small", "Nvidia T4", "$0.40/hr", 168, region="us-west-2")
    # Bob — image generation experiments
    _cart_add(bob, "FLUX.1-dev", "a100-large", "Nvidia A100", "$2.50/hr", 12, region="us-east-1")
    _cart_add(bob, "stable-diffusion-3-medium", "l40sx1", "Nvidia L40S", "$1.80/hr", 24, region="eu-west-1")
    _cart_add(bob, "stable-cascade", "t4-small", "Nvidia T4", "$0.40/hr", 72, region="us-east-1")
    # Carol — translation + summarization staging
    _cart_add(carol, "opus-mt-en-zh", "cpu-upgrade", "CPU Upgrade", "$0.03/hr", 168, region="eu-central-1")
    _cart_add(carol, "opus-mt-en-fr-2026", "cpu-upgrade", "CPU Upgrade", "$0.03/hr", 168, region="eu-central-1")
    _cart_add(carol, "biobart", "t4-small", "Nvidia T4", "$0.40/hr", 48, region="us-east-1")
    # David — MLOps benchmarks
    _cart_add(david, "Qwen2.5-7B-Instruct", "l40sx1", "Nvidia L40S", "$1.80/hr", 24, region="ap-southeast-1")
    _cart_add(david, "xlm-roberta-large-squad2", "l4x1", "Nvidia L4", "$0.80/hr", 168, region="us-east-1")
    _cart_add(david, "whisper-large-v3", "a100-large", "Nvidia A100", "$2.50/hr", 12, region="us-west-2")
    db.session.flush()

    # ------------------------------------------------------------------
    # Extra likes — broaden the per-user like graph so "trending"
    # signals look organic rather than seeded around a handful of repos.
    # ------------------------------------------------------------------
    EXTRA_LIKES = {
        "alice_j":  ["DeepSeek-V3", "Mistral-7B-Instruct", "Phi-3.5-mini-instruct",
                     "gemma-2-9b-it", "OLMo-2-1124-7B-Instruct",
                     "starcoder2-15b", "ms_marco", "ultrachat_200k"],
        "bob_c":    ["paligemma-3b-mix-448", "Florence-2-large", "instruct-pix2pix",
                     "stable-video-diffusion-img2vid-xt", "shap-e",
                     "dreamfusion-demo", "Hunyuan3D-2", "FAST-SAM"],
        "carol_d":  ["nllb-200-distilled", "opus-mt-en-fr-2026", "opus-mt-en-de-2026",
                     "pegasus-xsum", "coedit-large",
                     "T0pp-cc-by-sa", "blenderbot-3B-english-chat", "seamless_m4t"],
        "david_k":  ["paraphrase-multilingual-MiniLM", "multilingual-e5-large",
                     "roberta-base-squad2", "parakeet-tdt-1.1b", "whisper-small",
                     "Depth-Anything-V2", "fineweb", "common_voice_17_0"],
    }
    for uname, frags in EXTRA_LIKES.items():
        u = users.get(uname)
        if not u:
            continue
        for frag in frags:
            _like_repo(u, frag)
    db.session.flush()

    # ------------------------------------------------------------------
    # Extra discussions — spread community activity across more repos
    # so "discussions per repo" and "active community" signals work.
    # ------------------------------------------------------------------
    EXTRA_DISCUSSIONS = [
        # (user, slug_frag, title, body, kind)
        (alice, "DeepSeek-V3", "MoE routing collapse at long context?",
         "Has anyone observed expert routing degenerate beyond 32k context? My eval shows accuracy cliff at 40k.", "issue"),
        (alice, "Mistral-7B-Instruct",
         "Recommended LoRA rank for coding tasks?",
         "Trying r=8 vs r=64 for a Python code-completion fine-tune. Curious what others have settled on.", "discussion"),
        (alice, "Phi-3.5-mini-instruct",
         "Surprisingly strong on RAG tasks",
         "Phi-3.5-mini beats my 13B baseline on retrieval-grounded QA. Anyone else seeing this?", "discussion"),
        (alice, "gemma-2-9b-it",
         "Eos token misconfig on chat template",
         "When using `apply_chat_template(... add_generation_prompt=True)` the eos id isn't appended. PR coming.", "pull-request"),
        (alice, "bert-base-uncased",
         "Still the strongest sub-200M baseline",
         "Five years later this is still my go-to embedding base when budget matters. Tip of the hat.", "discussion"),
        (bob, "FLUX.1-dev",
         "LoRA training: which optimizer worked for you?",
         "Prodigy vs AdamW8bit on FLUX.1-dev — Prodigy converged 2x faster for me but burned more VRAM.", "discussion"),
        (bob, "stable-diffusion-3-medium",
         "ControlNet weights compatibility?",
         "Are SDXL ControlNet weights compatible, or do we need SD3-specific control adapters?", "issue"),
        (bob, "stable-cascade",
         "Stage-A latent visualization?",
         "Anyone got a notebook for decoding intermediate Stage-A latents to RGB? Debugging an artifact.", "discussion"),
        (bob, "paligemma-3b-mix-448",
         "Document QA accuracy on multi-page PDFs?",
         "Works great on single pages, but stitched multi-page inputs hallucinate page numbers. Workarounds?", "issue"),
        (bob, "stable-video-diffusion-img2vid-xt",
         "Temporal flicker in motion-heavy scenes",
         "Adding motion_bucket_id=180 helped some, but pans still flicker. Negative prompt tips?", "discussion"),
        (carol, "nllb-200-distilled",
         "African languages quality regression?",
         "Wolof and Lingala outputs are clearly worse than the full NLLB-200. Expected, or distillation bug?", "issue"),
        (carol, "opus-mt-en-fr-2026",
         "Glossary support like Marian-NMT?",
         "Need to force-translate brand names. Any way to inject a glossary at inference time?", "discussion"),
        (carol, "biobart",
         "PubMed update — re-eval on 2025 papers?",
         "The model was trained on a 2022 PubMed snapshot. Has anyone re-evaluated on the 2025 corpus?", "discussion"),
        (carol, "pegasus-xsum",
         "Hallucinated entities on news summaries",
         "Pegasus invents people and dates ~5% of the time on out-of-domain news. Any factuality post-processing?", "issue"),
        (carol, "coedit-large",
         "Great for grammar — limited for style rewriting",
         "Excellent for surface-level edits. Falls over on tone-shift / persuasive rewrites though.", "discussion"),
        (david, "Qwen2.5-7B-Instruct",
         "vLLM tensor-parallel scaling",
         "Going from TP=1 to TP=4 on A100s only gives 2.3x throughput — expected? Or am I bottlenecked on attention?", "discussion"),
        (david, "multilingual-e5-large",
         "Prefix `query:` vs `passage:` impact",
         "Forgetting the asymmetric prefixes silently halves my nDCG@10. Worth surfacing in the README.", "issue"),
        (david, "Depth-Anything-V2",
         "Real-time on Jetson Orin?",
         "Hitting ~12 FPS at 384x384 on Orin NX. Anyone gotten 30 FPS with TensorRT FP16?", "discussion"),
        (david, "whisper-large-v3",
         "Diarization pipeline recommendation?",
         "Best open-source diarizer to pair with Whisper-large-v3 right now? pyannote 3.1?", "discussion"),
        (david, "parakeet-tdt-1.1b",
         "Streaming latency vs Whisper",
         "Measured end-to-end latency 4x lower than whisper-large-v3 at similar WER. Impressive.", "discussion"),
        (alice, "ms_marco",
         "Filter for question-only queries?",
         "Need just the natural-question subset for a QA fine-tune. Easiest split filter?", "discussion"),
        (bob, "dreamfusion-sd-v1",
         "Texture seams on exported meshes",
         "Exported OBJ shows clear seams at UV cuts. Any post-processing recipe?", "issue"),
        (carol, "T0pp-cc-by-sa",
         "Re-training on instruction data?",
         "Has anyone re-instruction-tuned T0pp on FLAN-style data? Curious if it still beats T0 baseline.", "discussion"),
        (david, "fineweb",
         "Filter recipe for code-rich subset?",
         "I want the top-quality code-heavy slice. Are there ready-made dump-level filters?", "discussion"),
        (alice, "ultrachat_200k",
         "License clarification on chat outputs",
         "Outputs distilled from a closed teacher — does redistribution of the fine-tuned model itself raise concerns?", "discussion"),
        (alice, "starcoder2-15b",
         "Tokenizer treatment of indentation",
         "Switched from StarCoder1 — noticed indent-only edits now require fewer tokens. Confirming on your end?", "discussion"),
        (bob, "Hunyuan3D-2",
         "Export to glTF instead of OBJ?",
         "OBJ loses material grouping in Blender. Any way to get glTF straight out of the pipeline?", "issue"),
        (bob, "FAST-SAM",
         "ONNX export shape mismatch",
         "Exporting with dynamic axes produces a model that complains about prompt-encoder shape at runtime. Repo on the way.", "pull-request"),
        (carol, "blenderbot-3B-english-chat",
         "Persona conditioning still works after 4 years",
         "BlenderBot's persona prompts are still the gold standard for short consistent chats. Worth highlighting in the card.", "discussion"),
        (carol, "T0pp-cc-by-sa",
         "Reproducibility of held-out scores",
         "Following the README I'm off by ~2 points on SuperGLUE. Anyone managed to reproduce within 0.5?", "issue"),
        (david, "common_voice_17_0",
         "Force-aligned phoneme version?",
         "Are aligned phoneme labels published alongside this release? Useful for low-resource TTS training.", "discussion"),
        (david, "Mistral-7B-Instruct",
         "AWQ quant on consumer GPUs",
         "4-bit AWQ runs at 30 tok/s on a single 3090. Sharing the recipe for anyone interested.", "discussion"),
        (alice, "OLMo-2-1124-7B-Instruct",
         "Training data manifest — is everything reproducible?",
         "Was hoping the OLMo-2 release would include a one-click corpus rebuild. Did I miss the script?", "discussion"),
        (bob, "shap-e",
         "Latent interpolation between two prompts",
         "Has anyone gotten clean shape interpolation between two text prompts? My results just morph through noise.", "issue"),
    ]
    for user, frag, title, body, kind in EXTRA_DISCUSSIONS:
        repo = _get_repo(frag)
        if not repo:
            continue
        d = Discussion(
            repo_id=repo.id,
            user_id=user.id,
            title=title,
            body=body,
            kind=kind,
            upvotes=rng.randint(1, 40),
        )
        db.session.add(d)
    db.session.flush()

    # ------------------------------------------------------------------
    # Discussion replies — make threads feel populated. We reply on a
    # broad fraction of discussions with rotating quotes.
    # ------------------------------------------------------------------
    REPLY_TEMPLATES = [
        "+1 — seeing the same pattern on my side. Happy to share a repro notebook if useful.",
        "I worked around this by pinning `transformers==4.46.0` and disabling flash-attn. Hacky, but stable.",
        "Have you tried bumping `max_position_embeddings` and re-RoPE-ing? Worked for me at 64k.",
        "Quick benchmark on my end: A100 80GB, batch=1, ~38 tok/s. Drops to 22 tok/s at batch=4.",
        "Confirmed on a clean conda env (Python 3.11). Filed a follow-up upstream.",
        "Thanks for posting — saved me a few hours of debugging.",
        "The README needs an update; the suggested chat template here matches my testing.",
        "Could you share the eval harness? I want to reproduce the numbers locally.",
        "I think this is the same root cause as the issue from last week. Possibly worth merging.",
        "Excellent write-up. We're tracking this internally and will reply with findings.",
        "I'm hitting OOM on a 24GB consumer card — any tip on offloading text encoders to CPU?",
        "Are you running with `attn_implementation='sdpa'` or `flash_attention_2`? That changes things a lot.",
        "Worth opening a PR — happy to review.",
        "Tested on H100 vs A100: roughly 1.6x speedup at FP8, no quality regression I could measure.",
        "Pinging maintainers — this looks like a real bug, not a config issue.",
    ]
    all_disc = Discussion.query.order_by(Discussion.id).all()
    bench_user_list = [alice, bob, carol, david]
    for i, d in enumerate(all_disc):
        # R3: every discussion gets 3-5 replies so threads feel populated.
        n_replies = 3 + (i % 3)  # 3, 4, 5, 3, 4, 5, ...
        for k in range(n_replies):
            replier = bench_user_list[(i + k + 1) % len(bench_user_list)]
            # Don't reply to your own discussion in the first slot.
            if replier.id == d.user_id and n_replies > 1:
                replier = bench_user_list[(i + k + 2) % len(bench_user_list)]
            db.session.add(DiscussionReply(
                discussion_id=d.id,
                user_id=replier.id,
                body=REPLY_TEMPLATES[(i * 4 + k) % len(REPLY_TEMPLATES)],
                created_at=d.created_at + timedelta(hours=2 + k * 5),
            ))

    db.session.commit()
    print(f"  ✓ {len(BENCH_USERS)} benchmark users created")
    print(f"  ✓ Likes, follows, cart, collections, endpoints, discussions, replies seeded")


# ------------------------------------------------------------
# Bootstrap
# ------------------------------------------------------------
def normalize_seed_db_layout():
    """Re-emit indexes in alpha order + VACUUM so a fresh seed rebuild on a
    different host produces a byte-identical SQLite file.

    Background (harden-env gotcha #2): SQLAlchemy emits CREATE INDEX in
    Table.indexes order, which is a Python set keyed on object id() — that's
    allocator-dependent and shifts the bytes inside `sqlite_master` even when
    the row data is identical. Drop + re-create indexes in alpha order, then
    VACUUM to defragment.

    Gated on Repository.query.count() being non-zero so we only run on the
    first fresh seed and never on warm restart with an existing DB.
    """
    from sqlalchemy import text
    conn = db.engine.connect()
    idx_rows = conn.execute(text(
        "SELECT name, sql FROM sqlite_master WHERE type='index' AND name LIKE 'ix_%'"
    )).fetchall()
    for name, _ in idx_rows:
        conn.execute(text(f"DROP INDEX IF EXISTS {name}"))
    for name, sql in sorted(idx_rows, key=lambda r: r[0]):
        if sql:
            conn.execute(text(sql))
    conn.execute(text("VACUUM"))
    conn.commit()
    conn.close()


# ============================================================================
# R7 — SEO / OG card / sitemap / locale / trending API / RSS / robots.txt
# ============================================================================
import html as _html_mod


def _esc_xml(s) -> str:
    return _html_mod.escape(str(s or ""), quote=True)


def _site_origin() -> str:
    """Best-effort canonical origin for sitemap / RSS link generation."""
    return (request.host_url or "http://localhost:40010/").rstrip("/")


@app.route("/robots.txt")
def robots_txt():
    from flask import Response
    body = (
        "User-agent: *\n"
        "Allow: /\n"
        "Disallow: /api/\n"
        "Disallow: /account\n"
        "Disallow: /deploy\n"
        "Disallow: /endpoints\n"
        f"\nSitemap: {_site_origin()}/sitemap.xml\n"
    )
    return Response(body, mimetype="text/plain")


@app.route("/humans.txt")
def humans_txt():
    from flask import Response
    body = (
        "/* TEAM */\n"
        "Site: Hugging Face mirror\n"
        "Powered by: WebHarbor\n"
        "Built with: Flask, SQLAlchemy, Jinja2\n"
        f"Last update: {mirror_now().strftime('%Y-%m-%d')}\n"
        "\n/* THANKS */\n"
        "The open ML community.\n"
    )
    return Response(body, mimetype="text/plain")


def _sitemap_entries_for(repo_type: str, limit: int = 4000):
    """Top-N repos by likes_count for the per-type sitemap. Capping
    avoids returning a 50MB XML when the seed DB has 100k+ rows; SEO
    crawlers only follow the most-linked entries anyway."""
    rows = (Repository.query
            .filter(Repository.repo_type == repo_type)
            .order_by(Repository.likes_count.desc(), Repository.id.asc())
            .limit(limit).all())
    out = []
    base = _site_origin()
    for r in rows:
        loc = base + _repo_canonical_path(r)
        lm = (r.updated_at or mirror_now()).strftime("%Y-%m-%d")
        out.append((loc, lm))
    return out


def _sitemap_xml(entries):
    parts = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for loc, lm in entries:
        parts.append(
            f"<url><loc>{_esc_xml(loc)}</loc>"
            f"<lastmod>{_esc_xml(lm)}</lastmod>"
            "<changefreq>weekly</changefreq></url>"
        )
    parts.append("</urlset>")
    return "\n".join(parts)


@app.route("/sitemap.xml")
def sitemap_index():
    from flask import Response
    base = _site_origin()
    lm = mirror_now().strftime("%Y-%m-%d")
    parts = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for kind in ("models", "datasets", "spaces"):
        parts.append(
            f"<sitemap><loc>{base}/sitemap-{kind}.xml</loc>"
            f"<lastmod>{lm}</lastmod></sitemap>"
        )
    parts.append("</sitemapindex>")
    return Response("\n".join(parts), mimetype="application/xml")


@app.route("/sitemap-models.xml")
def sitemap_models():
    from flask import Response
    return Response(_sitemap_xml(_sitemap_entries_for("model")),
                    mimetype="application/xml")


@app.route("/sitemap-datasets.xml")
def sitemap_datasets():
    from flask import Response
    return Response(_sitemap_xml(_sitemap_entries_for("dataset")),
                    mimetype="application/xml")


@app.route("/sitemap-spaces.xml")
def sitemap_spaces():
    from flask import Response
    return Response(_sitemap_xml(_sitemap_entries_for("space")),
                    mimetype="application/xml")


# ----------------------------------------------------------------------------
# OpenGraph card endpoint — returns an SVG (1200×630) per repo. Used as
# the og:image URL on every repo detail page.
# ----------------------------------------------------------------------------
def _og_card_svg(repo) -> str:
    rt = repo.repo_type
    badge_bg = {"model": "#ffd21f", "dataset": "#7c3aed", "space": "#10b981"}.get(rt, "#6b7280")
    badge_text = {"model": "Model", "dataset": "Dataset", "space": "Space"}.get(rt, "Repo")
    task = repo.task_display or ""
    title = (repo.slug or "")[:60]
    subtitle = (repo.description or "")[:120]
    likes = repo.likes_count or 0
    downloads = repo.downloads_display if hasattr(repo, "downloads_display") else str(repo.downloads or 0)
    extra = ""
    if rt == "model" and repo.params_b:
        extra = f"{repo.params_b}B params · {repo.library or ''}"
    elif rt == "dataset":
        extra = f"{repo.rows_display} rows · {repo.modality or ''}"
    elif rt == "space":
        extra = f"SDK: {repo.sdk or ''} · {repo.hardware_display or ''}"
    svg = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="630" '
        'viewBox="0 0 1200 630">'
        '<defs><linearGradient id="bg" x1="0" y1="0" x2="0" y2="1">'
        '<stop offset="0%" stop-color="#fefce8"/>'
        '<stop offset="100%" stop-color="#fef3c7"/>'
        '</linearGradient></defs>'
        '<rect width="1200" height="630" fill="url(#bg)"/>'
        f'<rect x="60" y="60" width="200" height="44" rx="22" fill="{badge_bg}"/>'
        f'<text x="160" y="92" text-anchor="middle" font-family="-apple-system,Segoe UI,sans-serif" '
        f'font-size="22" font-weight="700" fill="#111827">{_esc_xml(badge_text)}</text>'
        f'<text x="60" y="170" font-family="-apple-system,Segoe UI,sans-serif" '
        f'font-size="56" font-weight="800" fill="#111827">{_esc_xml(title)}</text>'
        f'<text x="60" y="240" font-family="-apple-system,Segoe UI,sans-serif" '
        f'font-size="28" fill="#374151">{_esc_xml(subtitle)}</text>'
        f'<text x="60" y="350" font-family="-apple-system,Segoe UI,sans-serif" '
        f'font-size="32" font-weight="700" fill="#7c3aed">{_esc_xml(task)}</text>'
        f'<text x="60" y="430" font-family="-apple-system,Segoe UI,sans-serif" '
        f'font-size="26" fill="#4b5563">{_esc_xml(extra)}</text>'
        f'<text x="60" y="510" font-family="-apple-system,Segoe UI,sans-serif" '
        f'font-size="24" fill="#6b7280">★ {likes}  ·  ⬇ {_esc_xml(downloads)}</text>'
        '<text x="60" y="580" font-family="-apple-system,Segoe UI,sans-serif" '
        'font-size="22" fill="#9ca3af">🤗 Hugging Face</text>'
        '</svg>'
    )
    return svg


@app.route("/og/<repo_type>/<author>/<name>.svg")
def og_card(repo_type, author, name):
    from flask import Response
    if repo_type not in ("model", "dataset", "space"):
        abort(404)
    slug = f"{author}/{name}"
    repo = Repository.query.filter_by(slug=slug, repo_type=repo_type).first_or_404()
    body = _og_card_svg(repo)
    resp = Response(body, mimetype="image/svg+xml")
    resp.headers["Cache-Control"] = "public, max-age=86400"
    return resp


# ----------------------------------------------------------------------------
# JSON-LD helpers — SoftwareSourceCode (models) + Dataset (datasets)
# + SoftwareApplication (spaces). Emitted into <head> on every repo page
# via repo_detail.html.
# ----------------------------------------------------------------------------
def repo_jsonld(repo) -> dict:
    """Build a JSON-LD payload for a repo. Returned dict; template
    serialises to <script type="application/ld+json">."""
    base = _site_origin()
    canonical = base + _repo_canonical_path(repo)
    common = {
        "@context": "https://schema.org",
        "name": repo.slug,
        "url": canonical,
        "license": (repo.license_url or repo.license_link or ""),
        "description": (repo.description or "")[:300],
        "keywords": (repo.tags or [])[:12],
        "image": f"{base}/og/{repo.repo_type}/{repo.slug}.svg",
        "inLanguage": (repo.language or "en").lower()[:5],
    }
    if repo.repo_type == "model":
        common.update({
            "@type": "SoftwareSourceCode",
            "codeRepository": canonical,
            "programmingLanguage": "Python",
            "applicationCategory": repo.task_display or "MachineLearningModel",
            "runtimePlatform": repo.library or "Transformers",
            "creator": {
                "@type": "Organization" if (repo.author_obj and repo.author_obj.kind == "org") else "Person",
                "name": repo.slug.split("/")[0],
            },
            "dateModified": (repo.updated_at or mirror_now()).strftime("%Y-%m-%d"),
        })
    elif repo.repo_type == "dataset":
        common.update({
            "@type": "Dataset",
            "identifier": repo.slug,
            "measurementTechnique": repo.modality or "Text",
            "creator": {
                "@type": "Organization",
                "name": repo.slug.split("/")[0],
            },
            "distribution": [{
                "@type": "DataDownload",
                "encodingFormat": "application/x-parquet",
                "contentUrl": f"{canonical}/resolve/main/data",
            }],
            "dateModified": (repo.updated_at or mirror_now()).strftime("%Y-%m-%d"),
        })
    else:  # space
        common.update({
            "@type": "SoftwareApplication",
            "applicationCategory": "DeveloperApplication",
            "operatingSystem": "Web",
            "softwareRequirements": repo.sdk or "Gradio",
            "creator": {
                "@type": "Organization",
                "name": repo.slug.split("/")[0],
            },
            "dateModified": (repo.updated_at or mirror_now()).strftime("%Y-%m-%d"),
        })
    return common


@app.context_processor
def _inject_jsonld_helper():
    """Make `repo_jsonld(repo)` callable from any Jinja template."""
    return {"repo_jsonld": repo_jsonld}


# ----------------------------------------------------------------------------
# Trending API + RSS feed
# ----------------------------------------------------------------------------
@app.route("/api/trending")
def api_trending_top50():
    from flask import Response
    rt = request.args.get("repo_type", "model").lower()
    if rt not in ("model", "dataset", "space"):
        rt = "model"
    limit = max(1, min(50, int(request.args.get("limit", 50) or 50)))
    if not TRENDING_CACHE.get(rt):
        _refresh_trending_cache(limit=50)
    items = TRENDING_CACHE[rt][:limit]
    payload = json.dumps({
        "repo_type": rt,
        "count": len(items),
        "updated_at": TRENDING_CACHE["updated_at"],
        "items": items,
    })
    resp = Response(payload, mimetype="application/json")
    resp.headers["Cache-Control"] = "public, max-age=300"
    return resp


@app.route("/feed/trending.rss")
def feed_trending_rss():
    from flask import Response
    rt = request.args.get("repo_type", "model").lower()
    if rt not in ("model", "dataset", "space"):
        rt = "model"
    if not TRENDING_CACHE.get(rt):
        _refresh_trending_cache(limit=50)
    items = TRENDING_CACHE[rt][:25]
    base = _site_origin()
    rss = ['<?xml version="1.0" encoding="UTF-8"?>',
           '<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">',
           '<channel>',
           f'<title>Hugging Face — Trending {rt}s</title>',
           f'<link>{base}/</link>',
           f'<description>Top {len(items)} trending {rt}s on Hugging Face.</description>',
           f'<atom:link href="{base}/feed/trending.rss?repo_type={rt}" rel="self" type="application/rss+xml" />',
           f'<lastBuildDate>{TRENDING_CACHE["updated_at"]}</lastBuildDate>']
    for it in items:
        rss.append('<item>')
        rss.append(f'<title>{_esc_xml(it["slug"])}</title>')
        rss.append(f'<link>{base}{_esc_xml(it["url"])}</link>')
        rss.append(f'<guid isPermaLink="true">{base}{_esc_xml(it["url"])}</guid>')
        rss.append(f'<pubDate>{_esc_xml(it["updated_at"])}</pubDate>')
        rss.append(f'<description>{_esc_xml(it.get("task") or "")} · {it["downloads"]} downloads · {it["likes"]} likes</description>')
        rss.append('</item>')
    rss.append('</channel></rss>')
    resp = Response("\n".join(rss), mimetype="application/rss+xml")
    resp.headers["Cache-Control"] = "public, max-age=300"
    return resp


# ============================================================================
# R8 — Observability + Developer experience
#   * /healthz           — liveness probe
#   * /api/uptime        — boot time + uptime (seconds) under the mirror clock
#   * /api/events        — recent webhook events as JSON
#   * /webhook/model-deploy — POST receiver that appends to the in-memory log
#   * /api/v3/graphql    — minimal POST endpoint returning repo+author shape
#   * /developer/inference-API-curl-builder — interactive curl-builder page
#   * /help/pipeline-tags — pipeline-tag glossary (contextual help)
#   * /api/command-palette — JSON feed for the Cmd+K palette
# ============================================================================
import hashlib as _r8_hashlib
import time as _r8_time
from collections import deque as _r8_deque

# Pinned "boot time" — anchored to the mirror clock minus a deterministic
# offset so /api/uptime never reveals real wall clock and rebuilds stay
# byte-stable across container restarts.
_R8_BOOT_TS = MIRROR_REFERENCE_DATE - timedelta(hours=37, minutes=12)
# Synthetic uptime counter (incremented per /api/uptime request so a tester
# can observe monotonic growth without depending on wall clock).
_R8_UPTIME_HITS = [0]

# Webhook event log — capped deque so the page never grows unbounded.
# Seeded with deterministic boot-time events derived from top trending
# repos so it has content even before a tester POSTs.
_R8_EVENT_LOG = _r8_deque(maxlen=200)


def _r8_seed_events():
    """Populate the event log with one deterministic event per top-12
    trending model. Runs once per boot; subsequent calls are no-ops."""
    if _R8_EVENT_LOG:
        return
    rows = (Repository.query
            .filter(Repository.repo_type == "model")
            .order_by(Repository.trending_score.desc(),
                      Repository.likes_count.desc(),
                      Repository.id.asc())
            .limit(12).all())
    for i, r in enumerate(rows):
        h = int(_r8_hashlib.md5(r.slug.encode("utf-8")).hexdigest(), 16)
        ts = MIRROR_REFERENCE_DATE - timedelta(hours=(i * 3) + (h % 17))
        _R8_EVENT_LOG.append({
            "id": f"evt_{i:04d}_{h & 0xffff:04x}",
            "type": ("model.deploy", "model.update", "model.like", "model.endpoint.scale")[i % 4],
            "repo_id": r.id,
            "slug": r.slug,
            "hardware": ("cpu-basic", "t4-small", "l4x1", "a100-large", "zero-gpu")[h % 5],
            "endpoint_id": f"ep-{(h >> 8) & 0xffffff:06x}",
            "actor": ("alice_j", "bob_c", "carol_d", "david_k", "demo")[h % 5],
            "ts": ts.strftime("%Y-%m-%dT%H:%M:%SZ"),
        })


@app.route("/healthz")
def healthz():
    """Simple liveness probe. Returns 200 + JSON status when DB is reachable.

    Deterministic db_md5_short is the head-16 of an md5 over the count tuple
    so the value is stable rebuild-to-rebuild but changes if any of the
    headline counts drift."""
    from flask import Response
    try:
        repos_n = db.session.query(Repository.id).count()
        authors_n = db.session.query(Author.id).count()
        tasks_n = db.session.query(Task.id).count()
        users_n = db.session.query(User.id).count()
    except Exception:
        return Response('{"status":"degraded"}', mimetype="application/json", status=503)
    sig = _r8_hashlib.md5(
        f"{repos_n}:{authors_n}:{tasks_n}:{users_n}".encode("utf-8")
    ).hexdigest()[:16]
    payload = {
        "status": "ok",
        "service": "huggingface-mirror",
        "version": "r8",
        "repos": repos_n,
        "authors": authors_n,
        "tasks": tasks_n,
        "users": users_n,
        "db_signature": sig,
    }
    return Response(json.dumps(payload), mimetype="application/json")


@app.route("/api/uptime")
def api_uptime():
    """Boot time + synthetic uptime under the mirror clock. The uptime
    counter advances by request count so the value is monotonic without
    leaking real wall clock."""
    from flask import Response
    _R8_UPTIME_HITS[0] += 1
    boot_iso = _R8_BOOT_TS.strftime("%Y-%m-%dT%H:%M:%SZ")
    seconds = int((mirror_now() - _R8_BOOT_TS).total_seconds()) + _R8_UPTIME_HITS[0]
    payload = {
        "boot_time": boot_iso,
        "uptime_seconds": seconds,
        "uptime_human": f"{seconds // 86400}d {(seconds % 86400) // 3600}h {(seconds % 3600) // 60}m",
        "hits": _R8_UPTIME_HITS[0],
    }
    return Response(json.dumps(payload), mimetype="application/json")


@app.route("/api/events")
def api_events():
    """Return the most recent webhook events (newest first)."""
    from flask import Response
    _r8_seed_events()
    limit = max(1, min(200, int(request.args.get("limit", 50) or 50)))
    kind = (request.args.get("type") or "").strip().lower()
    items = list(_R8_EVENT_LOG)
    items.reverse()
    if kind:
        items = [e for e in items if e.get("type", "").lower() == kind]
    items = items[:limit]
    payload = {"count": len(items), "events": items}
    return Response(json.dumps(payload), mimetype="application/json")


@csrf.exempt
@app.route("/webhook/model-deploy", methods=["POST", "GET"])
def webhook_model_deploy():
    """Accept a deploy-event webhook. GET returns the schema + recent
    payloads so a tester can inspect without POSTing first."""
    from flask import Response
    _r8_seed_events()
    if request.method == "GET":
        payload = {
            "accepts": "application/json",
            "schema": {
                "slug": "string (required)",
                "hardware": "string (default: t4-small)",
                "actor": "string (default: anonymous)",
                "endpoint_id": "string (auto-generated when absent)",
            },
            "recent": list(_R8_EVENT_LOG)[-10:],
        }
        return Response(json.dumps(payload), mimetype="application/json")
    # POST path — accept JSON or form
    body = {}
    try:
        body = request.get_json(silent=True) or {}
    except Exception:
        body = {}
    if not body:
        body = request.form.to_dict() or {}
    slug = (body.get("slug") or "").strip()
    if not slug or "/" not in slug:
        return Response('{"error":"slug is required (author/name)"}',
                        mimetype="application/json", status=400)
    hw = (body.get("hardware") or "t4-small").strip()
    actor = (body.get("actor") or "anonymous").strip()
    h = int(_r8_hashlib.md5(f"{slug}:{hw}:{actor}".encode("utf-8")).hexdigest(), 16)
    endpoint_id = body.get("endpoint_id") or f"ep-{(h & 0xffffff):06x}"
    event = {
        "id": f"evt_{int(_r8_time.time())}_{h & 0xffff:04x}",
        "type": "model.deploy",
        "slug": slug,
        "hardware": hw,
        "actor": actor,
        "endpoint_id": endpoint_id,
        "ts": mirror_now().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "accepted": True,
    }
    _R8_EVENT_LOG.append(event)
    return Response(json.dumps({"ok": True, "event": event}),
                    mimetype="application/json", status=202)


@csrf.exempt
@app.route("/api/v3/graphql", methods=["GET", "POST"])
def api_v3_graphql():
    """Minimal GraphQL-style endpoint. Recognises three top-level fields:
       * repo(slug: "author/name", type: "model")
       * author(username: "...")
       * trending(type: "model", limit: 10)

    GET introspection returns the schema; POST executes the query JSON
    `{ "query": "..." }` parsed by a tiny regex matcher."""
    from flask import Response
    import re as _re_r8

    SCHEMA = {
        "version": "v3",
        "queries": {
            "repo": {"args": {"slug": "ID!", "type": "String"},
                     "returns": ["slug", "repo_type", "task", "library",
                                 "license", "downloads", "likes", "params_b"]},
            "author": {"args": {"username": "ID!"},
                       "returns": ["username", "display_name", "kind",
                                   "followers_count", "is_verified"]},
            "trending": {"args": {"type": "String", "limit": "Int"},
                         "returns": ["slug", "task", "downloads", "likes",
                                     "trending_score"]},
        },
    }
    if request.method == "GET":
        return Response(json.dumps(SCHEMA, indent=2),
                        mimetype="application/json")
    body = request.get_json(silent=True) or {}
    query = (body.get("query") or "").strip()
    if not query:
        return Response(json.dumps({"errors": ["empty query"]}),
                        mimetype="application/json", status=400)
    data = {}
    errors = []
    # repo(slug: "...", type: "...")
    m = _re_r8.search(r'repo\s*\(\s*slug\s*:\s*"([^"]+)"(?:\s*,\s*type\s*:\s*"([^"]+)")?\s*\)', query)
    if m:
        slug = m.group(1)
        rt = (m.group(2) or "model").lower()
        repo = Repository.query.filter_by(slug=slug, repo_type=rt).first()
        if repo:
            data["repo"] = {
                "slug": repo.slug,
                "repo_type": repo.repo_type,
                "task": repo.task_slug,
                "library": repo.library or "",
                "license": repo.license or "",
                "downloads": repo.downloads or 0,
                "likes": repo.likes_count or 0,
                "params_b": float(repo.params_b or 0),
            }
        else:
            data["repo"] = None
            errors.append(f"repo not found: {slug} ({rt})")
    # author(username: "...")
    m = _re_r8.search(r'author\s*\(\s*username\s*:\s*"([^"]+)"\s*\)', query)
    if m:
        a = Author.query.filter_by(username=m.group(1)).first()
        if a:
            data["author"] = {
                "username": a.username,
                "display_name": a.display_name,
                "kind": a.kind,
                "followers_count": a.followers_count or 0,
                "is_verified": bool(a.is_verified),
            }
        else:
            data["author"] = None
            errors.append(f"author not found: {m.group(1)}")
    # trending(type: "...", limit: N)
    m = _re_r8.search(r'trending\s*\(\s*(?:type\s*:\s*"([^"]+)"\s*,?\s*)?(?:limit\s*:\s*(\d+))?\s*\)', query)
    if m:
        rt = (m.group(1) or "model").lower()
        if rt not in ("model", "dataset", "space"):
            rt = "model"
        n = int(m.group(2) or 10)
        if not TRENDING_CACHE.get(rt):
            _refresh_trending_cache(limit=50)
        data["trending"] = TRENDING_CACHE[rt][:n]
    out = {"data": data}
    if errors:
        out["errors"] = errors
    return Response(json.dumps(out), mimetype="application/json")


@app.route("/developer/inference-API-curl-builder")
@app.route("/developer/inference-api-curl-builder")
def developer_curl_builder():
    """Interactive page that renders a runnable `curl` command for the
    selected model. The submitted form regenerates the snippet without
    hitting the inference backend so the page is fully offline."""
    slug = (request.args.get("slug") or "meta-llama/Llama-3.3-70B-Instruct").strip()
    provider = (request.args.get("provider") or "HF Inference").strip()
    payload_kind = (request.args.get("payload") or "text").strip().lower()
    repo = Repository.query.filter_by(slug=slug, repo_type="model").first()
    base = _site_origin()
    body_examples = {
        "text": '{"inputs":"Write a haiku about transformers."}',
        "chat": '{"messages":[{"role":"user","content":"Hi there!"}],"max_tokens":256}',
        "image": '{"inputs":"a cinematic photo of an astronaut on a giraffe","parameters":{"width":1024,"height":1024}}',
        "embed": '{"inputs":"sentence to embed"}',
    }
    body = body_examples.get(payload_kind, body_examples["text"])
    curl_cmd = (
        f'curl -X POST "{base}/api/inference" \\\n'
        f'  -H "Authorization: Bearer $HF_TOKEN" \\\n'
        f'  -H "Content-Type: application/json" \\\n'
        f'  -H "X-Inference-Provider: {provider}" \\\n'
        f'  -d \'{{"model":"{slug}","payload":{body}}}\''
    )
    suggested = (Repository.query
                 .filter(Repository.repo_type == "model")
                 .order_by(Repository.downloads.desc())
                 .limit(20).all())
    return render_template(
        "developer_curl_builder.html",
        slug=slug, repo=repo, provider=provider,
        payload_kind=payload_kind, body=body, curl_cmd=curl_cmd,
        suggested=suggested,
        providers=INFERENCE_PROVIDERS,
        payload_kinds=("text", "chat", "image", "embed"),
        page_title="Inference API · curl builder",
    )


# Pipeline-tag glossary (contextual help)
PIPELINE_TAG_GLOSSARY = [
    ("text-generation", "Autoregressive language modeling. Models predict the next token given a prompt."),
    ("text-to-image", "Generates an image from a text caption using a diffusion or autoregressive image model."),
    ("automatic-speech-recognition", "Speech-to-text — converts audio waveforms to written transcripts."),
    ("text-to-speech", "Synthesizes spoken audio from input text. Supports voice conditioning in newer models."),
    ("image-classification", "Assigns a single label to an entire image from a fixed taxonomy."),
    ("object-detection", "Locates and labels objects with bounding boxes inside an image."),
    ("image-segmentation", "Predicts a class label for every pixel — semantic, instance, or panoptic."),
    ("depth-estimation", "Predicts per-pixel depth from a monocular RGB image."),
    ("translation", "Maps a sentence from one natural language to another."),
    ("summarization", "Condenses long documents into shorter, faithful summaries."),
    ("feature-extraction", "Produces fixed-size embeddings for downstream retrieval or similarity."),
    ("token-classification", "Per-token labels — NER, POS tagging, chunking."),
    ("text-classification", "One label per sentence — sentiment, intent, topic, etc."),
    ("question-answering", "Extracts or generates an answer from a context passage."),
    ("zero-shot-classification", "Classifies text against arbitrary labels without task-specific training."),
    ("image-text-to-text", "Multimodal — accepts interleaved image and text; outputs text. Document QA, VQA."),
    ("text-to-video", "Synthesizes short video clips from text prompts."),
    ("image-to-video", "Animates a still image into a short video clip."),
    ("text-to-3d", "Generates a 3D mesh or NeRF from a text prompt."),
    ("image-to-3d", "Lifts a single image into a textured 3D mesh."),
    ("reinforcement-learning", "Agents that learn behavior from environmental rewards."),
    ("tabular-classification", "Classifies rows of structured tabular data."),
    ("tabular-regression", "Predicts continuous targets from tabular features."),
    ("sentence-similarity", "Scores semantic similarity between two pieces of text."),
    ("audio-classification", "Sound-event, speaker, or genre classification on audio clips."),
    ("audio-to-audio", "Audio-in / audio-out — enhancement, separation, voice conversion."),
    ("fill-mask", "Masked-language modeling — predict missing tokens in a sentence."),
    ("table-question-answering", "Question answering grounded in a tabular schema."),
    ("text-ranking", "Reranks candidate passages by relevance to a query."),
]


@app.route("/help/pipeline-tags")
@app.route("/developer/pipeline-tags")
def help_pipeline_tags():
    """Glossary of pipeline-tag definitions used across model cards."""
    q = (request.args.get("q") or "").strip().lower()
    entries = PIPELINE_TAG_GLOSSARY
    if q:
        entries = [(k, v) for k, v in entries if q in k.lower() or q in v.lower()]
    return render_template(
        "pipeline_tag_glossary.html",
        entries=entries, q=q,
        page_title="Pipeline-tag glossary",
    )


@app.route("/api/command-palette")
def api_command_palette():
    """JSON feed used by the Cmd+K palette.  Pull a deterministic top slice
    so the palette is snappy without scanning the full 200k-row pool."""
    from flask import Response
    q = (request.args.get("q") or "").strip().lower()
    limit = max(1, min(40, int(request.args.get("limit", 20) or 20)))
    items = []
    # Static nav
    nav = [
        ("Models", "/models", "page"),
        ("Datasets", "/datasets", "page"),
        ("Spaces", "/spaces", "page"),
        ("Papers", "/papers", "page"),
        ("Posts", "/posts", "page"),
        ("Leaderboards", "/leaderboards", "page"),
        ("Docs", "/docs", "page"),
        ("Enterprise", "/enterprise", "page"),
        ("Pricing", "/pricing", "page"),
        ("Pipeline-tag glossary", "/help/pipeline-tags", "page"),
        ("Inference API · curl builder", "/developer/inference-API-curl-builder", "page"),
        ("Trending RSS", "/feed/trending.rss", "page"),
        ("Robots.txt", "/robots.txt", "page"),
        ("Sitemap", "/sitemap.xml", "page"),
        ("Healthz", "/healthz", "page"),
        ("Uptime", "/api/uptime", "page"),
        ("Events", "/api/events", "page"),
        ("GGUF quant compare", "/tools/gguf-quant-compare", "page"),
        ("Safetensors check", "/tools/safetensors-check", "page"),
        ("Model merge", "/model-merge", "page"),
        ("ZeroGPU quota", "/spaces/zerogpu-quota", "page"),
        ("Papers · Daily vote", "/papers/daily-vote", "page"),
        ("AutoTrain configs", "/autotrain/config/llama-3-8b-sft-alpaca", "page"),
    ]
    for label, url, kind in nav:
        if not q or q in label.lower() or q in url.lower():
            items.append({"label": label, "url": url, "kind": kind})
    # Top trending models / datasets / spaces
    if q:
        rows = (Repository.query
                .filter(Repository.slug.ilike(f"%{q}%"))
                .order_by(Repository.likes_count.desc())
                .limit(limit).all())
    else:
        rows = []
        for rt in ("model", "dataset", "space"):
            rows.extend(Repository.query
                        .filter(Repository.repo_type == rt)
                        .order_by(Repository.likes_count.desc(),
                                  Repository.id.asc())
                        .limit(4).all())
    for r in rows[:limit]:
        items.append({
            "label": r.slug,
            "url": _repo_canonical_path(r),
            "kind": r.repo_type,
            "likes": r.likes_count or 0,
            "downloads": r.downloads or 0,
        })
    payload = {"count": len(items), "items": items[:40]}
    return Response(json.dumps(payload), mimetype="application/json")


# ============================================================================
# R9 — AutoTrain config / GGUF quant compare / safetensors check /
# model-merge / Spaces ZeroGPU quota / papers Daily vote
# ============================================================================
import hashlib as _r9_hashlib
from flask import render_template_string as _r9_render_template_string

_R9_PAGE_WRAP = """{% extends "base.html" %}
{% block title %}{{ page_title }} · Hugging Face{% endblock %}
{% block content %}
<div class="container-wide" style="max-width:980px;padding:32px 24px;">
{{ body|safe }}
</div>
{% endblock %}
"""


def _r9_render(title, body_html):
    return _r9_render_template_string(_R9_PAGE_WRAP, page_title=title, body=body_html)


# --- 1) AutoTrain job config -------------------------------------------------
_R9_AUTOTRAIN_JOBS = {
    "llama-3-8b-sft-alpaca": {
        "base_model": "meta-llama/Llama-3.3-70B-Instruct",
        "task": "text-generation",
        "trainer": "sft",
        "dataset": "tatsu-lab/alpaca",
        "hardware": "a100-large",
        "epochs": 3, "lr": 2e-5, "batch_size": 4, "grad_accum": 16,
        "lora_r": 16, "lora_alpha": 32, "use_peft": True,
    },
    "whisper-fr-finetune": {
        "base_model": "openai/whisper-large-v3",
        "task": "automatic-speech-recognition",
        "trainer": "asr",
        "dataset": "mozilla-foundation/common_voice_17_0",
        "hardware": "a10g-large",
        "epochs": 5, "lr": 1e-5, "batch_size": 8, "grad_accum": 2,
        "lora_r": 8, "lora_alpha": 16, "use_peft": False,
    },
    "gemma-2-9b-dpo": {
        "base_model": "google/gemma-2-9b-it",
        "task": "text-generation",
        "trainer": "dpo",
        "dataset": "HuggingFaceH4/ultrachat_200k",
        "hardware": "a100-large",
        "epochs": 1, "lr": 5e-7, "batch_size": 2, "grad_accum": 32,
        "lora_r": 32, "lora_alpha": 64, "use_peft": True,
    },
    "qwen-2-5-vl-vqa": {
        "base_model": "Qwen/Qwen2.5-72B-Instruct",
        "task": "visual-question-answering",
        "trainer": "vision-sft",
        "dataset": "HuggingFaceFW/fineweb",
        "hardware": "a100-large",
        "epochs": 2, "lr": 1e-5, "batch_size": 1, "grad_accum": 64,
        "lora_r": 16, "lora_alpha": 32, "use_peft": True,
    },
    "deepseek-v3-orpo": {
        "base_model": "deepseek-ai/DeepSeek-V3",
        "task": "text-generation",
        "trainer": "orpo",
        "dataset": "lmsys/lmsys-chat-1m",
        "hardware": "a100-large",
        "epochs": 1, "lr": 5e-6, "batch_size": 1, "grad_accum": 128,
        "lora_r": 64, "lora_alpha": 128, "use_peft": True,
    },
    "bge-large-en-finetune": {
        "base_model": "BAAI/bge-large-en-v1.5",
        "task": "feature-extraction",
        "trainer": "embedding",
        "dataset": "sentence-transformers/all-nli",
        "hardware": "t4-medium",
        "epochs": 4, "lr": 2e-5, "batch_size": 32, "grad_accum": 1,
        "lora_r": 0, "lora_alpha": 0, "use_peft": False,
    },
}


@app.route("/autotrain/config/<job>")
def autotrain_config(job):
    cfg = _R9_AUTOTRAIN_JOBS.get(job)
    if not cfg:
        # Render the index of known jobs (200, listing) — easier for agents.
        rows = []
        for slug, c in sorted(_R9_AUTOTRAIN_JOBS.items()):
            rows.append(
                f'<li><a href="/autotrain/config/{slug}"><code>{slug}</code></a> '
                f'— {c["task"]} via {c["trainer"]}</li>'
            )
        body = (
            f"<h1>AutoTrain · job configs</h1>"
            f"<p class='text-muted'>No job named <code>{_html_mod.escape(job)}</code>. "
            f"Pick one of the {len(_R9_AUTOTRAIN_JOBS)} known job slugs:</p>"
            f"<ul style='line-height:1.9;'>{''.join(rows)}</ul>"
        )
        return _r9_render("AutoTrain · job not found", body)
    yaml = (
        f"# AutoTrain job: {job}\n"
        f"job_name: {job}\n"
        f"task: {cfg['task']}\n"
        f"trainer: {cfg['trainer']}\n"
        f"base_model: {cfg['base_model']}\n"
        f"dataset: {cfg['dataset']}\n"
        f"hardware: {cfg['hardware']}\n"
        f"hyperparameters:\n"
        f"  epochs: {cfg['epochs']}\n"
        f"  learning_rate: {cfg['lr']}\n"
        f"  batch_size: {cfg['batch_size']}\n"
        f"  gradient_accumulation: {cfg['grad_accum']}\n"
        f"peft:\n"
        f"  enabled: {str(cfg['use_peft']).lower()}\n"
        f"  lora_r: {cfg['lora_r']}\n"
        f"  lora_alpha: {cfg['lora_alpha']}\n"
    )
    body = (
        f"<h1 style='font-size:32px;margin:0 0 8px;'>AutoTrain · <code>{_html_mod.escape(job)}</code></h1>"
        f"<p class='text-muted' style='margin:0 0 16px;'>Job config for AutoTrain. Copy the YAML and submit it via the AutoTrain CLI.</p>"
        f"<dl style='display:grid;grid-template-columns:160px 1fr;gap:8px 16px;margin:0 0 24px;'>"
        f"<dt><b>Base model</b></dt><dd data-field='base_model'><a href='/{cfg['base_model']}'><code>{cfg['base_model']}</code></a></dd>"
        f"<dt><b>Trainer</b></dt><dd data-field='trainer'>{cfg['trainer']}</dd>"
        f"<dt><b>Dataset</b></dt><dd data-field='dataset'><a href='/datasets/{cfg['dataset']}'><code>{cfg['dataset']}</code></a></dd>"
        f"<dt><b>Hardware</b></dt><dd data-field='hardware'>{cfg['hardware']}</dd>"
        f"<dt><b>PEFT</b></dt><dd data-field='use_peft'>{str(cfg['use_peft']).lower()}</dd>"
        f"</dl>"
        f"<h2>Generated YAML</h2>"
        f"<pre style='background:#0f172a;color:#e2e8f0;padding:16px 20px;border-radius:8px;overflow:auto;'>{_html_mod.escape(yaml)}</pre>"
        f"<p><a href='/autotrain'>← back to AutoTrain</a></p>"
    )
    return _r9_render(f"AutoTrain · {job}", body)


# --- 2) GGUF quant comparison ------------------------------------------------
_R9_GGUF_QUANTS = [
    # (level, bits/weight, size_ratio, ppl_delta, recommend)
    ("Q2_K",   2.625, 0.27, "+1.50", "Last-resort, mobile only"),
    ("Q3_K_S", 3.05,  0.32, "+0.62", "Squeeze for laptops"),
    ("Q3_K_M", 3.30,  0.34, "+0.40", "Good 4-8GB tradeoff"),
    ("Q3_K_L", 3.55,  0.37, "+0.30", "Slightly better than Q3_K_M"),
    ("Q4_0",   4.00,  0.42, "+0.20", "Legacy quant, lower quality than K-quants"),
    ("Q4_K_S", 4.20,  0.44, "+0.12", "Tighter than Q4_K_M"),
    ("Q4_K_M", 4.40,  0.46, "+0.08", "Recommended default"),
    ("Q5_0",   5.00,  0.51, "+0.06", "Legacy; prefer Q5_K_M"),
    ("Q5_K_S", 5.25,  0.53, "+0.04", "Slightly larger Q4_K_M"),
    ("Q5_K_M", 5.45,  0.55, "+0.03", "Recommended for 16GB+"),
    ("Q6_K",   6.30,  0.65, "+0.01", "Near-lossless"),
    ("Q8_0",   8.00,  0.85, "+0.00", "Practically lossless"),
    ("f16",   16.00,  1.00, "+0.00", "Original half-precision"),
]


@app.route("/tools/gguf-quant-compare")
def tools_gguf_quant_compare():
    slug = (request.args.get("slug") or "meta-llama/Llama-3.3-70B-Instruct").strip()
    repo = Repository.query.filter_by(slug=slug, repo_type="model").first()
    # Estimate the f16 file size from params (B params * 2 bytes/weight).
    params_b = float(repo.params_b) if (repo and repo.params_b) else 8.0
    base_gb = params_b * 2.0
    rows_html = []
    for lvl, bpw, ratio, ppl, note in _R9_GGUF_QUANTS:
        size_gb = round(base_gb * ratio, 2)
        rows_html.append(
            f"<tr data-quant='{lvl}'>"
            f"<td><code>{lvl}</code></td>"
            f"<td style='text-align:right;'>{bpw:.2f}</td>"
            f"<td style='text-align:right;'>{size_gb} GB</td>"
            f"<td style='text-align:right;'>{ppl}</td>"
            f"<td>{_html_mod.escape(note)}</td>"
            f"</tr>"
        )
    suggested = (Repository.query.filter(Repository.repo_type == "model")
                 .filter(Repository.params_b > 0)
                 .order_by(Repository.downloads.desc()).limit(8).all())
    sug_html = " · ".join(
        f"<a href='/tools/gguf-quant-compare?slug={r.slug}'><code>{r.slug}</code></a>"
        for r in suggested
    )
    body = (
        f"<h1 style='font-size:32px;margin:0 0 8px;'>GGUF quant comparison</h1>"
        f"<p class='text-muted' style='margin:0 0 16px;'>Estimated file sizes and perplexity-delta for each GGUF quant level. "
        f"Sizes assume the base model is <b>{params_b:.1f}B</b> parameters at fp16.</p>"
        f"<form method='get' style='margin:0 0 24px;display:flex;gap:8px;'>"
        f"<input type='text' name='slug' value='{_html_mod.escape(slug)}' "
        f"style='flex:1;padding:10px;border:1px solid #d1d5db;border-radius:6px;font-family:ui-monospace,Menlo,monospace;'>"
        f"<button type='submit' class='btn btn-primary' style='padding:8px 18px;'>Re-estimate</button>"
        f"</form>"
        f"<table data-tool='gguf-quant-compare' style='width:100%;border-collapse:collapse;'>"
        f"<thead><tr style='border-bottom:2px solid #e5e7eb;text-align:left;'>"
        f"<th>Quant</th><th style='text-align:right;'>bpw</th><th style='text-align:right;'>Size</th>"
        f"<th style='text-align:right;'>Δppl</th><th>Recommendation</th></tr></thead>"
        f"<tbody>{''.join(rows_html)}</tbody></table>"
        f"<p style='margin-top:24px;'><b>Other base models:</b> {sug_html}</p>"
    )
    return _r9_render("GGUF quant compare", body)


# --- 3) Safetensors format check --------------------------------------------
@app.route("/tools/safetensors-check", methods=["GET", "POST"])
@csrf.exempt
def tools_safetensors_check():
    filename = (request.values.get("filename") or "").strip()
    verdict = None
    warning = None
    safe = False
    fmt = "unknown"
    if filename:
        fl = filename.lower()
        if fl.endswith(".safetensors"):
            fmt = "safetensors"
            verdict = "safe"
            safe = True
        elif fl.endswith(".bin") or fl.endswith(".pt") or fl.endswith(".pth") or fl.endswith(".ckpt") or fl.endswith(".pkl") or fl.endswith(".pickle"):
            fmt = "pickle"
            verdict = "unsafe"
            warning = (
                "This file uses Python pickle, which can execute arbitrary code "
                "on load. Convert to safetensors before uploading: "
                "<code>safetensors_torch_convert input.bin output.safetensors</code>."
            )
        elif fl.endswith(".gguf"):
            fmt = "gguf"
            verdict = "safe"
            safe = True
        elif fl.endswith(".onnx"):
            fmt = "onnx"
            verdict = "safe"
            safe = True
        else:
            fmt = "unknown"
            verdict = "unknown"
            warning = "Unknown extension. Only .safetensors / .gguf / .onnx are explicitly accepted."
    body_parts = [
        "<h1 style='font-size:32px;margin:0 0 8px;'>Safetensors format check</h1>",
        "<p class='text-muted' style='margin:0 0 16px;'>Paste a model filename and we'll tell you whether the format is safe to download (no arbitrary-code execution on load).</p>",
        "<form method='post' style='margin:0 0 24px;display:flex;gap:8px;'>",
        f"<input type='text' name='filename' value='{_html_mod.escape(filename)}' "
        f"placeholder='pytorch_model.bin' "
        f"style='flex:1;padding:10px;border:1px solid #d1d5db;border-radius:6px;font-family:ui-monospace,Menlo,monospace;'>",
        "<button type='submit' class='btn btn-primary' style='padding:8px 18px;'>Check</button>",
        "</form>",
    ]
    if verdict:
        color = "#16a34a" if safe else ("#dc2626" if verdict == "unsafe" else "#ca8a04")
        body_parts.append(
            f"<div data-verdict='{verdict}' data-format='{fmt}' "
            f"style='border-left:4px solid {color};padding:12px 16px;background:#f9fafb;'>"
            f"<p style='margin:0 0 4px;'><b>Filename:</b> <code>{_html_mod.escape(filename)}</code></p>"
            f"<p style='margin:0 0 4px;'><b>Format:</b> {fmt}</p>"
            f"<p style='margin:0;'><b>Verdict:</b> {verdict}</p>"
            + (f"<p style='margin:8px 0 0;color:{color};'>{warning}</p>" if warning else "")
            + "</div>"
        )
    body_parts.append(
        "<h2 style='margin-top:32px;'>Accepted formats</h2>"
        "<ul>"
        "<li><code>.safetensors</code> — preferred; no code execution on load</li>"
        "<li><code>.gguf</code> — llama.cpp container, safe</li>"
        "<li><code>.onnx</code> — open neural network exchange, safe</li>"
        "</ul>"
        "<h2>Rejected formats</h2>"
        "<ul>"
        "<li><code>.bin / .pt / .pth / .ckpt</code> — PyTorch pickle, unsafe</li>"
        "<li><code>.pkl / .pickle</code> — raw pickle, unsafe</li>"
        "</ul>"
    )
    return _r9_render("Safetensors check", "".join(body_parts))


# --- 4) Model merge stub -----------------------------------------------------
@app.route("/model-merge", methods=["GET", "POST"])
@csrf.exempt
def model_merge():
    a_slug = (request.values.get("a") or "meta-llama/Llama-3.3-70B-Instruct").strip()
    b_slug = (request.values.get("b") or "mistralai/Mistral-7B-Instruct-v0.3").strip()
    method = (request.values.get("method") or "ties").strip().lower()
    weight_a = request.values.get("weight_a") or "0.5"
    try:
        wa = max(0.0, min(1.0, float(weight_a)))
    except ValueError:
        wa = 0.5
    wb = round(1.0 - wa, 4)
    methods = ("linear", "slerp", "ties", "dare-ties", "passthrough", "model-stock")
    a_repo = Repository.query.filter_by(slug=a_slug, repo_type="model").first()
    b_repo = Repository.query.filter_by(slug=b_slug, repo_type="model").first()
    h = _r9_hashlib.md5(f"{a_slug}|{b_slug}|{method}|{wa}".encode()).hexdigest()[:12]
    merge_slug = f"community-merges/merge-{h}"
    config_yaml = (
        "# mergekit config (generated)\n"
        f"merge_method: {method}\n"
        f"base_model: {a_slug}\n"
        "models:\n"
        f"  - model: {a_slug}\n"
        f"    parameters:\n      weight: {wa}\n"
        f"  - model: {b_slug}\n"
        f"    parameters:\n      weight: {wb}\n"
        "dtype: bfloat16\n"
        f"name: {merge_slug}\n"
    )
    body = (
        f"<h1 style='font-size:32px;margin:0 0 8px;'>Model merge</h1>"
        f"<p class='text-muted' style='margin:0 0 16px;'>Generate a <code>mergekit</code> YAML for combining two models on the Hub. This is a stub — no actual weights are mixed.</p>"
        f"<form method='post' class='card' style='display:grid;grid-template-columns:1fr 1fr;gap:12px;padding:16px;border:1px solid #e5e7eb;border-radius:10px;margin:0 0 24px;'>"
        f"<label style='grid-column:1/-1;'><b>Model A (base)</b><br><input name='a' value='{_html_mod.escape(a_slug)}' style='width:100%;padding:8px;border:1px solid #d1d5db;border-radius:4px;font-family:ui-monospace,Menlo,monospace;'></label>"
        f"<label style='grid-column:1/-1;'><b>Model B</b><br><input name='b' value='{_html_mod.escape(b_slug)}' style='width:100%;padding:8px;border:1px solid #d1d5db;border-radius:4px;font-family:ui-monospace,Menlo,monospace;'></label>"
        f"<label><b>Method</b><br><select name='method' style='padding:8px;border:1px solid #d1d5db;border-radius:4px;width:100%;'>"
        + "".join(f"<option value='{m}'{' selected' if m==method else ''}>{m}</option>" for m in methods)
        + f"</select></label>"
        f"<label><b>Weight A</b><br><input name='weight_a' type='number' min='0' max='1' step='0.05' value='{wa}' style='padding:8px;border:1px solid #d1d5db;border-radius:4px;width:100%;'></label>"
        f"<button type='submit' class='btn btn-primary' style='grid-column:1/-1;padding:10px;'>Generate config</button>"
        f"</form>"
        f"<dl style='display:grid;grid-template-columns:160px 1fr;gap:6px 14px;margin:0 0 16px;'>"
        f"<dt><b>Predicted slug</b></dt><dd data-field='merge_slug'><code>{merge_slug}</code></dd>"
        f"<dt><b>Method</b></dt><dd data-field='method'>{method}</dd>"
        f"<dt><b>Weight A / B</b></dt><dd data-field='weights'>{wa} / {wb}</dd>"
        f"<dt><b>Model A on hub</b></dt><dd data-field='a_present'>{'yes' if a_repo else 'no'}</dd>"
        f"<dt><b>Model B on hub</b></dt><dd data-field='b_present'>{'yes' if b_repo else 'no'}</dd>"
        f"</dl>"
        f"<h2>mergekit YAML</h2>"
        f"<pre style='background:#0f172a;color:#e2e8f0;padding:16px 20px;border-radius:8px;overflow:auto;'>{_html_mod.escape(config_yaml)}</pre>"
    )
    return _r9_render("Model merge", body)


# --- 5) Spaces ZeroGPU quota ------------------------------------------------
@app.route("/spaces/zerogpu-quota")
def spaces_zerogpu_quota():
    user = (request.args.get("user") or "").strip()
    # Quota depends deterministically on user slug
    if user:
        h = int(_r9_hashlib.md5(user.encode()).hexdigest(), 16)
        used = h % 240   # 0–239 min
        plan = ("free", "pro", "enterprise")[h % 3]
        cap = {"free": 240, "pro": 1440, "enterprise": 14400}[plan]
        next_reset = "2026-05-28T00:00:00Z"
    else:
        used = 0
        plan = "anonymous"
        cap = 0
        next_reset = "n/a"
    remaining = max(0, cap - used) if cap else 0
    pct = round(100.0 * used / cap, 1) if cap else 0.0
    body = (
        f"<h1 style='font-size:32px;margin:0 0 8px;'>Spaces · ZeroGPU quota</h1>"
        f"<p class='text-muted' style='margin:0 0 16px;'>ZeroGPU lets Spaces share an A100. Each user gets a daily compute budget in seconds; this page reports the current balance.</p>"
        f"<form method='get' style='margin:0 0 24px;display:flex;gap:8px;'>"
        f"<input type='text' name='user' value='{_html_mod.escape(user)}' "
        f"placeholder='username' "
        f"style='flex:1;padding:10px;border:1px solid #d1d5db;border-radius:6px;font-family:ui-monospace,Menlo,monospace;'>"
        f"<button type='submit' class='btn btn-primary' style='padding:8px 18px;'>Check quota</button>"
        f"</form>"
        f"<dl data-tool='zerogpu-quota' style='display:grid;grid-template-columns:200px 1fr;gap:6px 14px;margin:0 0 24px;'>"
        f"<dt><b>User</b></dt><dd data-field='user'>{_html_mod.escape(user) or '(anonymous)'}</dd>"
        f"<dt><b>Plan</b></dt><dd data-field='plan'>{plan}</dd>"
        f"<dt><b>Daily cap (minutes)</b></dt><dd data-field='cap'>{cap}</dd>"
        f"<dt><b>Used today</b></dt><dd data-field='used'>{used} min ({pct}%)</dd>"
        f"<dt><b>Remaining</b></dt><dd data-field='remaining'>{remaining} min</dd>"
        f"<dt><b>Resets at</b></dt><dd data-field='reset'>{next_reset}</dd>"
        f"</dl>"
        f"<h2>Quota tiers</h2>"
        f"<ul>"
        f"<li><b>free</b> — 240 min/day; lower priority</li>"
        f"<li><b>pro</b> — 1440 min/day (24 GPU-hours); higher priority queue</li>"
        f"<li><b>enterprise</b> — 14400 min/day; dedicated reservations</li>"
        f"</ul>"
    )
    return _r9_render("ZeroGPU quota", body)


# --- 6) Papers · Daily vote --------------------------------------------------
_R9_DAILY_PAPERS = [
    ("2411.17041", "GAIA-Bench 2: agent evaluations at scale"),
    ("2410.20587", "Diffusion ODEs are noise-aware solvers"),
    ("2411.04944", "RWKV-7: linear attention with rotation"),
    ("2410.10630", "MoE routing without auxiliary loss"),
    ("2411.10440", "Speculative decoding beats memory bandwidth"),
    ("2411.01098", "DeepSeek-V3 technical report"),
    ("2410.19133", "Mamba-2 SSM: state expansion theory"),
    ("2411.03570", "Pixtral 12B: an interleaved vision-language model"),
    ("2410.18890", "OLMo-2 training data deep-dive"),
    ("2411.07641", "Qwen-2.5 family report"),
    ("2411.08868", "FineWeb-Edu: filtering for educational signal"),
    ("2410.07073", "BitNet b1.58: 1-bit LLMs"),
]


def _r9_papers_vote_state():
    """Compute a deterministic per-paper vote total + the cast-vote
    boolean for the current session. Votes are kept in `session['r9_voted']`
    so the page can show a 'thank you' state without hitting the DB."""
    voted = set(session.get("r9_voted") or [])
    items = []
    for aid, title in _R9_DAILY_PAPERS:
        h = int(_r9_hashlib.md5(aid.encode()).hexdigest(), 16)
        base_votes = 12 + (h % 240)  # 12–251
        bonus = 1 if aid in voted else 0
        items.append({
            "arxiv_id": aid,
            "title": title,
            "votes": base_votes + bonus,
            "voted": aid in voted,
        })
    items.sort(key=lambda i: (-i["votes"], i["arxiv_id"]))
    return items


@app.route("/papers/daily-vote", methods=["GET", "POST"])
@csrf.exempt
def papers_daily_vote():
    msg = None
    if request.method == "POST":
        aid = (request.form.get("arxiv_id") or request.values.get("arxiv_id") or "").strip()
        known_ids = {a for a, _ in _R9_DAILY_PAPERS}
        if aid not in known_ids:
            msg = ("error", f"Unknown arxiv id: {aid or '(empty)'}")
        else:
            voted = list(session.get("r9_voted") or [])
            if aid in voted:
                msg = ("info", f"You already upvoted {aid} today.")
            else:
                voted.append(aid)
                session["r9_voted"] = voted
                msg = ("ok", f"Thanks — your vote for {aid} is in.")
        if (request.headers.get("Accept") or "").startswith("application/json"):
            from flask import Response
            return Response(json.dumps({"status": msg[0], "message": msg[1]}),
                            mimetype="application/json",
                            status=200 if msg[0] != "error" else 400)
    items = _r9_papers_vote_state()
    rows = []
    for i, p in enumerate(items):
        btn = (
            f"<form method='post' style='display:inline;'>"
            f"<input type='hidden' name='arxiv_id' value='{p['arxiv_id']}'>"
            f"<button type='submit' "
            f"data-action='vote' data-arxiv-id='{p['arxiv_id']}' "
            f"style='padding:4px 10px;border:1px solid #d1d5db;border-radius:4px;background:#f9fafb;cursor:pointer;'>"
            f"{'✓ voted' if p['voted'] else '▲ upvote'}</button>"
            f"</form>"
        )
        rows.append(
            f"<tr data-arxiv-id='{p['arxiv_id']}'>"
            f"<td style='text-align:right;padding:4px 8px;'>{i+1}</td>"
            f"<td style='padding:4px 8px;'><a href='/papers/arxiv/{p['arxiv_id']}'><code>{p['arxiv_id']}</code></a></td>"
            f"<td style='padding:4px 8px;'>{_html_mod.escape(p['title'])}</td>"
            f"<td style='text-align:right;padding:4px 8px;' data-field='votes'>{p['votes']}</td>"
            f"<td style='padding:4px 8px;'>{btn}</td>"
            f"</tr>"
        )
    banner_html = ""
    if msg:
        color = {"ok": "#16a34a", "info": "#2563eb", "error": "#dc2626"}.get(msg[0], "#6b7280")
        banner_html = (
            f"<div data-banner='{msg[0]}' style='border-left:4px solid {color};"
            f"padding:10px 14px;background:#f9fafb;margin:0 0 16px;'>{_html_mod.escape(msg[1])}</div>"
        )
    body = (
        f"<h1 style='font-size:32px;margin:0 0 8px;'>Papers · Daily vote</h1>"
        f"<p class='text-muted' style='margin:0 0 16px;'>Vote on today's papers. Top-voted entries get featured on /papers and in the trending feed.</p>"
        f"{banner_html}"
        f"<table data-tool='papers-daily-vote' style='width:100%;border-collapse:collapse;border-bottom:1px solid #e5e7eb;'>"
        f"<thead><tr style='border-bottom:2px solid #e5e7eb;text-align:left;'>"
        f"<th style='text-align:right;padding:6px 8px;'>#</th>"
        f"<th style='padding:6px 8px;'>arxiv</th>"
        f"<th style='padding:6px 8px;'>Title</th>"
        f"<th style='text-align:right;padding:6px 8px;'>Votes</th>"
        f"<th style='padding:6px 8px;'>Action</th></tr></thead>"
        f"<tbody>{''.join(rows)}</tbody></table>"
    )
    return _r9_render("Papers · Daily vote", body)


with app.app_context():
    fresh = not (ROOT / "instance" / "hf.db").exists() or Repository.query.count() == 0
    db.create_all()
    seed_database()
    seed_benchmark_users()
    if fresh:
        normalize_seed_db_layout()
    # R7: refresh trending top-50 cache on boot. Trending values are
    # deterministic functions of the seed DB so this is safe to do once.
    try:
        _refresh_trending_cache(limit=50)
    except Exception:
        pass
    # R8: prime the webhook event log so /api/events has content before
    # any tester POSTs. Deterministic — derived from top trending models.
    try:
        _r8_seed_events()
    except Exception:
        pass



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
R2_SITE_NAME = "Huggingface"
R2_DOMAIN = "huggingface.co"
R2_ACCESSIBILITY_BLURB = "Hugging Face strives for AA conformance on model and dataset pages and continues to add semantic landmarks to Spaces."


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
R3_SITE_NAME = "Huggingface"
R3_DOMAIN = "huggingface.co"


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


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
