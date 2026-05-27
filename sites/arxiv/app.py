"""
arxiv.org mirror - Flask application.

Adaptation of the mirror-web pattern to a reference/research site:
  Entity      = Paper
  Category    = Subject Area (cs, math, physics, ...)
  Cart        = Library (saved papers for reading later)
  Order       = Download Log / Citation Export
  Wishlist    = Starred Papers
  Review      = Comment on a paper
"""
import os
import re
import json
import random
import hashlib
from datetime import datetime, timedelta
from pathlib import Path

from flask import (
    Flask, render_template, request, redirect, url_for, flash, jsonify,
    session, abort, send_from_directory, Response, g
)
from flask_sqlalchemy import SQLAlchemy
from flask_login import (
    LoginManager, UserMixin, login_user, logout_user, login_required, current_user
)
from flask_bcrypt import Bcrypt
from flask_wtf import CSRFProtect
from sqlalchemy import or_, and_, func, text

from metadata_cleaning import clean_arxiv_metadata_text, format_arxiv_display_text
import visual_assets

BASE_DIR = Path(__file__).parent
DB_DIR = BASE_DIR / "instance"
DB_DIR.mkdir(exist_ok=True)

app = Flask(__name__)
app.config["SECRET_KEY"] = "arxiv-mirror-secret-key-change-in-prod-1234567890"
app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{DB_DIR / 'arxiv.db'}"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["WTF_CSRF_TIME_LIMIT"] = None  # session-length CSRF
app.config["TEMPLATES_AUTO_RELOAD"] = True  # pick up template edits in long-running container

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = "login"
login_manager.login_message = "Please log in to access this page."


# >>> silent-fail-fix: unauthorized_handler
@login_manager.unauthorized_handler
def _unauthorized_silent_fail_fix():
    """Return JSON 401 for AJAX/JSON requests so fetch().then(r=>r.json())
    surfaces the auth requirement instead of choking on HTML 302→/login.
    Falls back to the normal redirect for browser navigations.

    Pairs with the fetch-wrapper in static/js/main.js which detects this and
    redirects the user to /login. Root cause docs: gotcha #49."""
    from flask import request, jsonify, redirect, url_for
    accept = request.headers.get('Accept', '') or ''
    wants_json = (
        request.path.startswith('/api/')
        or request.is_json
        or 'application/json' in accept
        or request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    )
    next_url = request.full_path if request.query_string else request.path
    try:
        login_url = url_for('login', next=next_url)
    except Exception:
        login_url = '/login?next=' + next_url
    if wants_json:
        return jsonify({
            'error': 'login_required',
            'message': 'Sign in to continue.',
            'redirect': login_url,
        }), 401
    return redirect(login_url)
# <<< silent-fail-fix
csrf = CSRFProtect(app)


# =======================================================================
# MODELS
# =======================================================================

class User(db.Model, UserMixin):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(200), unique=True, nullable=False, index=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(200), nullable=False)
    full_name = db.Column(db.String(200), default="")
    affiliation = db.Column(db.String(200), default="")
    bio = db.Column(db.Text, default="")
    orcid = db.Column(db.String(40), default="")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    library_items = db.relationship("LibraryItem", backref="user", cascade="all, delete-orphan")
    starred = db.relationship("StarredPaper", backref="user", cascade="all, delete-orphan")
    exports = db.relationship("Export", backref="user", cascade="all, delete-orphan")
    comments = db.relationship("Comment", backref="user", cascade="all, delete-orphan")
    alerts = db.relationship("Alert", backref="user", cascade="all, delete-orphan")

    def set_password(self, raw: str):
        self.password_hash = bcrypt.generate_password_hash(raw).decode("utf-8")

    def check_password(self, raw: str) -> bool:
        return bcrypt.check_password_hash(self.password_hash, raw)


class Category(db.Model):
    """A top-level subject area (cs, math, physics, ...)"""
    __tablename__ = "categories"
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(40), unique=True, nullable=False)
    name = db.Column(db.String(120), nullable=False)
    icon = db.Column(db.String(20), default="📚")
    color = db.Column(db.String(20), default="#b31b1b")
    short_name = db.Column(db.String(40), default="")
    parent_code = db.Column(db.String(40), default="")  # for grouping (e.g. astro-ph under Physics)
    description = db.Column(db.Text, default="")

    @property
    def paper_count(self):
        return Paper.query.filter(
            or_(Paper.primary_subject_code == self.code,
                Paper.primary_subject_code.like(f"{self.code}.%"))
        ).count()


class Paper(db.Model):
    """A single research paper / e-print."""
    __tablename__ = "papers"
    id = db.Column(db.Integer, primary_key=True)
    arxiv_id = db.Column(db.String(40), unique=True, nullable=False, index=True)
    title = db.Column(db.Text, nullable=False)
    abstract = db.Column(db.Text, default="")
    authors_json = db.Column(db.Text, default="[]")  # JSON list of author name strings
    subjects = db.Column(db.Text, default="")  # e.g. "Artificial Intelligence (cs.AI); Computation..."
    primary_subject = db.Column(db.String(200), default="")  # "Artificial Intelligence (cs.AI)"
    primary_subject_code = db.Column(db.String(40), default="", index=True)  # "cs.AI"
    primary_category_code = db.Column(db.String(20), default="", index=True)  # "cs"
    submitted_date = db.Column(db.String(40), default="")
    submitted_year = db.Column(db.Integer, default=0, index=True)
    submitted_month = db.Column(db.Integer, default=0)
    submitted_day = db.Column(db.Integer, default=0)
    announce_date = db.Column(db.String(40), default="")  # Date the paper was announced in listings
    comments = db.Column(db.Text, default="")  # "12 pages, 5 figures"
    journal_ref = db.Column(db.String(400), default="", index=True)
    doi = db.Column(db.String(200), default="")
    pdf_url = db.Column(db.String(400), default="")
    html_url = db.Column(db.String(400), default="")
    html_available = db.Column(db.Boolean, default=True)
    n_authors = db.Column(db.Integer, default=0, index=True)
    figures_count = db.Column(db.Integer, default=0)
    tables_count = db.Column(db.Integer, default=0)
    formulas_count = db.Column(db.Integer, default=0)
    loss_function = db.Column(db.Text, default="")
    versions_json = db.Column(db.Text, default="[]")  # JSON list of {version, date}
    # Parallel list of author affiliations, same order as authors_json. Stored
    # as JSON list of strings (may contain "" for unknown). Deterministically
    # synthesised at seed time from a hash of the author name.
    author_affiliations_json = db.Column(db.Text, default="[]")
    # R4 — bulk-harvest extras from OAI-PMH (math/cs classification codes,
    # report numbers). Optional; empty string for legacy rows.
    msc_class = db.Column(db.String(400), default="", index=True)
    acm_class = db.Column(db.String(400), default="", index=True)
    report_no = db.Column(db.String(200), default="")
    # R5 — per-paper provenance fields. paper_version is the current shipped
    # version (v1/v2/v3 — derived from versions_json if populated, else from
    # a hash of arxiv_id so each paper has a stable version label). license
    # is one of arXiv's five accepted licenses. submitter_email_masked shows
    # the visible part of the (masked) submitter email. computer_classification
    # is a coarse CCS/CR-class tag (e.g. "I.2.7 Natural Language Processing").
    paper_version = db.Column(db.String(8), default="v1", index=True)
    license = db.Column(db.String(80), default="arXiv-perpetual")
    submitter_email_masked = db.Column(db.String(120), default="")
    computer_classification = db.Column(db.String(200), default="")
    view_count = db.Column(db.Integer, default=0)
    download_count = db.Column(db.Integer, default=0)
    star_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    comments_rel = db.relationship("Comment", backref="paper", cascade="all, delete-orphan")
    library_items = db.relationship("LibraryItem", backref="paper", cascade="all, delete-orphan")
    starred = db.relationship("StarredPaper", backref="paper", cascade="all, delete-orphan")

    def get_authors(self) -> list:
        try:
            return json.loads(self.authors_json or "[]")
        except Exception:
            return []

    def get_author_affiliations(self) -> list:
        """Return a list of affiliation strings, aligned with get_authors().

        If the stored list is shorter than the author list, pads with
        deterministically-synthesised affiliations derived from the author
        name, so every author always has a visible affiliation.
        """
        authors = self.get_authors()
        try:
            affs = json.loads(self.author_affiliations_json or "[]")
        except Exception:
            affs = []
        if not isinstance(affs, list):
            affs = []
        # Pad / repair
        out = []
        for i, a in enumerate(authors):
            if i < len(affs) and affs[i]:
                out.append(affs[i])
            else:
                out.append(_synthesize_affiliation(a))
        return out

    def get_authors_with_affiliations(self) -> list:
        authors = self.get_authors()
        affs = self.get_author_affiliations()
        return [
            {"name": a, "affiliation": (affs[i] if i < len(affs) else "")}
            for i, a in enumerate(authors)
        ]

    @property
    def first_author(self):
        a = self.get_authors()
        return a[0] if a else ""

    @property
    def first_author_affiliation(self):
        affs = self.get_author_affiliations()
        return affs[0] if affs else ""

    @property
    def authors_display(self):
        a = self.get_authors()
        if not a:
            return ""
        if len(a) > 3:
            return ", ".join(a[:3]) + f", et al. ({len(a)} authors)"
        return ", ".join(a)

    @property
    def short_abstract(self):
        abstract = self.display_abstract
        if not abstract:
            return "Abstract not available."
        if len(abstract) > 280:
            return abstract[:280] + "…"
        return abstract

    @property
    def display_title(self):
        return format_arxiv_display_text(self.title or "")

    @property
    def display_abstract(self):
        return format_arxiv_display_text(self.abstract or "")

    @property
    def display_comments(self):
        return format_arxiv_display_text(self.comments or "")

    @property
    def display_journal_ref(self):
        return format_arxiv_display_text(self.journal_ref or "")

    @property
    def subject_list(self):
        if not self.subjects:
            return []
        return [s.strip() for s in self.subjects.split(";") if s.strip()]

    def get_versions(self) -> list:
        try:
            return json.loads(self.versions_json or "[]")
        except Exception:
            return []

    @property
    def reading_time_min(self) -> int:
        """Estimated reading time for the abstract, at 200 wpm.

        Caps at 1 minute floor so the badge is always meaningful. Used for the
        "{N} min read" badge on /abs pages.
        """
        text = (self.abstract or "").strip()
        if not text:
            return 1
        n_words = len(re.findall(r"\w+", text))
        return max(1, (n_words + 199) // 200)

    @property
    def version_rail(self) -> list:
        """Return versions as a normalised list of {version, date, label}.

        Falls back to a single synthesised v1 entry on `submitted_date` when
        the upstream metadata didn't include a versions list.
        """
        vs = self.get_versions() or []
        if not vs and self.submitted_date:
            vs = [{"version": "v1", "date": self.submitted_date}]
        out = []
        for v in vs:
            ver = (v.get("version") or "").strip()
            if not ver.startswith("v"):
                ver = "v" + ver if ver else "v?"
            out.append({
                "version": ver,
                "date": v.get("date", ""),
                "label": v.get("label", ""),
            })
        return out

    # ----------------------------------------------------------------- R6
    # Derived (digest-driven) status flags. None of these need a DB column —
    # they are pure functions of arxiv_id so rebuilds stay byte-identical
    # while still letting agents land on withdrawn/replaced/citation pages.

    @property
    def _digest(self):
        return hashlib.md5((self.arxiv_id or "").encode("utf-8")).digest()

    @property
    def is_withdrawn(self) -> bool:
        """A deterministic ~1.4% slice is treated as withdrawn by author.
        Authors withdraw papers occasionally on real arXiv; we surface a
        banner so agents can practise reading withdraw notices."""
        if not self.arxiv_id:
            return False
        return self._digest[0] % 71 == 0

    @property
    def withdrawal_reason(self) -> str:
        """Reason string for the withdrawal banner. Deterministic per paper."""
        reasons = [
            "withdrawn by the author due to an error in the main proof "
            "(Section 3). A revised version will be uploaded separately.",
            "withdrawn at the author's request because the result was already "
            "obtained in earlier work that was not cited.",
            "withdrawn pending major revision after community feedback.",
            "withdrawn by the author; the algorithmic guarantee was found to "
            "be incorrect after re-examination of the proof.",
            "withdrawn by the author pending an updated reproducibility "
            "appendix.",
        ]
        d = self._digest
        return reasons[d[1] % len(reasons)]

    @property
    def replaced_by_arxiv_id(self) -> str:
        """A small deterministic slice has a 'replaced by newer version'
        pointer to another arxiv_id (constructed from the same prefix +
        a fixed increment). For most papers this returns empty string.
        """
        if not self.arxiv_id:
            return ""
        d = self._digest
        if d[2] % 47 != 13:
            return ""
        # Synthesise a follow-up id by bumping the suffix; never actually
        # need a DB row to back it — the route knows how to render a
        # tombstone if the target doesn't exist.
        m = re.match(r"(\d{4}\.\d{2,})(v\d+)?", self.arxiv_id)
        if not m:
            return ""
        base = m.group(1)
        # bump by a small deterministic offset
        try:
            head, tail = base.split(".")
            new_tail = str(int(tail) + 1 + (d[3] % 5)).zfill(len(tail))
            return f"{head}.{new_tail}"
        except Exception:
            return ""

    @property
    def is_replaced(self) -> bool:
        return bool(self.replaced_by_arxiv_id)

    @property
    def citing_count(self) -> int:
        """Synthetic 'cited by N' number, deterministic per arxiv_id.

        Ranges from 5 to ~205 so the abs sidebar always has a meaningful
        citing-list link. Older papers (by submitted_year) get a small
        recency bonus so the distribution matches user expectations.
        """
        if not self.arxiv_id:
            return 0
        d = self._digest
        base = 5 + ((d[4] << 8 | d[5]) % 200)
        try:
            age = max(0, 2026 - int(self.submitted_year or 2024))
            return base + age * 3
        except Exception:
            return base

    # ------------------------------------------------------------------
    # Visual asset accessors (image utilization deepening — 2026-05-27).
    # ------------------------------------------------------------------

    def get_figures(self) -> list:
        """Return the figures list shown on /abs/<id>.

        Prefer rows from the `paper_figures` table when present (seeded for
        the bulk of papers). Otherwise synthesise deterministically from
        md5(arxiv_id) so even unseen papers render figures. List items are
        dicts: {position, kind, style, filename, caption, width, height}.
        """
        # DB-backed rows take precedence when the seed pass populated them.
        try:
            rows = (PaperFigure.query
                    .filter_by(paper_id=self.id)
                    .order_by(PaperFigure.position)
                    .all())
        except Exception:
            rows = []
        if rows:
            return [{
                "position": r.position, "kind": r.kind, "style": r.style,
                "filename": r.filename, "caption": r.caption,
                "width": r.width, "height": r.height,
            } for r in rows]
        # Fallback synth
        n = _figure_count_for(self.arxiv_id, self.figures_count)
        out = []
        for i in range(1, n + 1):
            style = _figure_style_for(
                self.arxiv_id, i, self.primary_category_code,
                self.primary_subject_code or "",
            )
            out.append({
                "position": i,
                "kind": "architecture" if (i == 1 and style == "arch") else "figure",
                "style": style,
                "filename": _figure_filename(style, self.arxiv_id, i),
                "caption": _figure_caption(style, self.arxiv_id, i),
                "width": 420,
                "height": 260,
            })
        return out

    @property
    def hero_figure(self) -> dict:
        """Pick the visually-strongest figure for the hero card on the abs
        page. Architecture-style figures win when present; otherwise we fall
        back to the first figure."""
        figs = self.get_figures()
        if not figs:
            return {}
        for f in figs:
            if f.get("style") == "arch":
                return f
        return figs[0]

    @property
    def pdf_cover_filename(self) -> str:
        return _pdf_cover_filename(self.arxiv_id)

    def get_author_images(self) -> list:
        """Aligned with get_authors() — returns avatar SVG paths + alt text."""
        authors = self.get_authors()
        affs = self.get_author_affiliations()
        out = []
        for i, a in enumerate(authors):
            aff = affs[i] if i < len(affs) else ""
            out.append({
                "name": a,
                "filename": _avatar_filename(a),
                "alt": f"{a} headshot",
                "institution_accent": _institution_accent(aff),
                "affiliation": aff,
            })
        return out


# Composite indexes for the catchup / latest panels and inject_globals.
# Without these, both routes full-scan the 380k-row papers table:
#   - func.max(submitted_date) for the "mirror today" banner (~14ms × every
#     request via inject_globals)
#   - Paper.submitted_date >= X (.count() + .all()) for /catchup (~120ms+
#     per query under load)
# ix_ prefix preserves byte-id via normalize_seed_db_layout. db.Index()
# declared at module scope attaches to the column's table just like
# __table_args__ would, without needing to edit the class body.
db.Index('ix_paper_submitted_date', Paper.submitted_date)
db.Index('ix_paper_subject_submitted',
         Paper.primary_subject_code, Paper.submitted_date)
db.Index('ix_paper_category_submitted',
         Paper.primary_category_code, Paper.submitted_date)


class LibraryItem(db.Model):
    """A paper saved to a user's Library (the 'cart' analog)."""
    __tablename__ = "library_items"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    paper_id = db.Column(db.Integer, db.ForeignKey("papers.id"), nullable=False)
    folder = db.Column(db.String(100), default="Reading List")
    note = db.Column(db.Text, default="")
    added_at = db.Column(db.DateTime, default=datetime.utcnow)
    __table_args__ = (db.UniqueConstraint("user_id", "paper_id", name="_user_paper_uc"),)


class StarredPaper(db.Model):
    """A starred paper (wishlist analog)."""
    __tablename__ = "starred_papers"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    paper_id = db.Column(db.Integer, db.ForeignKey("papers.id"), nullable=False)
    starred_at = db.Column(db.DateTime, default=datetime.utcnow)
    __table_args__ = (db.UniqueConstraint("user_id", "paper_id", name="_user_star_uc"),)


class Export(db.Model):
    """A citation export / bulk download (the 'order' analog)."""
    __tablename__ = "exports"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    export_id = db.Column(db.String(40), unique=True, nullable=False)
    format = db.Column(db.String(20), default="bibtex")  # bibtex, endnote, ris
    status = db.Column(db.String(20), default="ready")  # preparing, ready, cancelled
    paper_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    notes = db.Column(db.Text, default="")
    items = db.relationship("ExportItem", backref="export", cascade="all, delete-orphan")


class ExportItem(db.Model):
    __tablename__ = "export_items"
    id = db.Column(db.Integer, primary_key=True)
    export_id = db.Column(db.Integer, db.ForeignKey("exports.id"), nullable=False)
    paper_id = db.Column(db.Integer, db.ForeignKey("papers.id"), nullable=False)
    paper = db.relationship("Paper")


class Comment(db.Model):
    """User comment on a paper (review analog)."""
    __tablename__ = "comments"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    paper_id = db.Column(db.Integer, db.ForeignKey("papers.id"), nullable=False)
    title = db.Column(db.String(200), default="")
    body = db.Column(db.Text, nullable=False)
    rating = db.Column(db.Integer, default=0)  # 0-5 stars (optional)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Alert(db.Model):
    """Subscription to a category for email alerts."""
    __tablename__ = "alerts"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    category_code = db.Column(db.String(40), nullable=False)
    frequency = db.Column(db.String(20), default="weekly")
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class SavedSearch(db.Model):
    """A user-saved search query — combined with an Alert it powers the
    'Notify me when new papers match this query' feature.
    """
    __tablename__ = "saved_searches"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    name = db.Column(db.String(120), default="")
    query = db.Column(db.String(400), default="")
    field = db.Column(db.String(40), default="all")
    category = db.Column(db.String(40), default="")
    frequency = db.Column(db.String(20), default="weekly")
    last_seen_arxiv_id = db.Column(db.String(40), default="")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class PaperUpdateNotification(db.Model):
    """A 'Notify me when this paper has a new version' subscription."""
    __tablename__ = "paper_update_notifications"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    paper_id = db.Column(db.Integer, db.ForeignKey("papers.id"), nullable=False)
    email = db.Column(db.String(200), default="")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    __table_args__ = (
        db.UniqueConstraint("user_id", "paper_id", name="_user_paper_notify_uc"),
    )


# -----------------------------------------------------------------------
# Visual-asset relationship tables (image utilization deepening — 2026-05-27)
# -----------------------------------------------------------------------
# These three tables back the paper-figure / author-headshot / conference-banner
# imagery shown on /abs/<id>, /a/<name>/profile, and /r7/calendar respectively.
# They are deliberately small: rows store *references* into a shared SVG pool
# under static/images/ rather than blob payloads, so byte-identical seed-DB
# rebuilds stay cheap.

class PaperFigure(db.Model):
    """A figure attached to a paper. References a shared SVG in
    static/images/figures/ — the same SVG may be reused across papers, but
    the (paper, position, caption) tuple is unique per row."""
    __tablename__ = "paper_figures"
    id = db.Column(db.Integer, primary_key=True)
    paper_id = db.Column(db.Integer, db.ForeignKey("papers.id"), nullable=False, index=True)
    position = db.Column(db.Integer, default=1)  # 1..N
    kind = db.Column(db.String(40), default="figure")  # figure / table / arch / chart
    style = db.Column(db.String(40), default="line")
    filename = db.Column(db.String(160), default="")  # 'figures/line_03.svg'
    caption = db.Column(db.Text, default="")
    width = db.Column(db.Integer, default=420)
    height = db.Column(db.Integer, default=260)
    __table_args__ = (
        db.UniqueConstraint("paper_id", "position", name="_paper_position_uc"),
    )


class AuthorImage(db.Model):
    """A headshot / banner attached to an author name."""
    __tablename__ = "author_images"
    id = db.Column(db.Integer, primary_key=True)
    author_name = db.Column(db.String(200), nullable=False, index=True)
    kind = db.Column(db.String(20), default="headshot")  # headshot / banner / institution
    filename = db.Column(db.String(160), default="")
    alt = db.Column(db.String(200), default="")
    institution_logo = db.Column(db.String(160), default="")
    __table_args__ = (
        db.UniqueConstraint("author_name", "kind", name="_author_kind_uc"),
    )


class ConferenceImage(db.Model):
    """A banner / venue photo for a named conference."""
    __tablename__ = "conference_images"
    id = db.Column(db.Integer, primary_key=True)
    conf = db.Column(db.String(40), nullable=False, index=True)
    year = db.Column(db.Integer, default=0)
    kind = db.Column(db.String(20), default="banner")  # banner / venue / sponsor
    filename = db.Column(db.String(160), default="")
    alt = db.Column(db.String(200), default="")
    accent_color = db.Column(db.String(20), default="#b31b1b")


# =======================================================================
# LOGIN MANAGER
# =======================================================================

@login_manager.user_loader
def load_user(uid):
    return db.session.get(User, int(uid))


# =======================================================================
# SEED DATA
# =======================================================================

# Reference build date pinned for deterministic timestamps. All seeded
# created_at / added_at / starred_at values are derived from this anchor via
# fixed offsets so md5sum(instance_seed/arxiv.db) is stable across rebuilds.
MIRROR_REFERENCE_DATE = datetime(2026, 4, 15, 12, 0, 0)

# Bcrypt is non-deterministic (random salt per call), so seed-time password
# hashing would break byte-identical rebuilds. We pin pre-computed hashes
# generated once with a fixed salt and reuse them at seed time. Verified to
# `bcrypt.checkpw` against the documented test passwords.
PINNED_HASH_TESTPASS = "$2b$10$WebHarborSeedSalt22BC.MBZLtrk3/oO0p9i7oB1qRs8m8RsIo2W"
PINNED_HASH_DEMODEMO = "$2b$10$WebHarborSeedSalt22BC.E1aBBgXR/FiqJQNugGMetTJFJykYe9a"

# Deterministic stub banks for filling in missing author lists / abstracts.
_STUB_FIRST_NAMES = [
    "Alex", "Wei", "Yuki", "Maya", "Rahul", "Sofia", "Hiroshi", "Priya",
    "Elena", "Jian", "Daniel", "Anika", "Mohamed", "Chen", "Ana", "Luca",
    "Nina", "Tomas", "Ravi", "Aisha", "Keiko", "Oscar", "Jia", "Amir",
    "Lena", "Sam", "Noah", "Fatima", "Yao", "Ivan",
]
_STUB_LAST_NAMES = [
    "Chen", "Kumar", "Silva", "Okafor", "Ivanov", "Tanaka", "Kim", "Singh",
    "Garcia", "Zhou", "Muller", "Rossi", "Patel", "Schmidt", "Nguyen",
    "Larsson", "Hassan", "Andersson", "Popov", "Kowalski", "Fernandez",
    "Navarro", "Park", "Zhang", "Li", "Sato", "Johansson", "Haddad",
    "Petrov", "Bianchi",
]
_CATEGORY_BLURBS = {
    "cs.CL": ("We present a new approach to computational linguistics that "
              "combines large-scale pretraining with structured evaluation. "
              "Our method improves downstream performance on a suite of "
              "language understanding benchmarks while remaining efficient "
              "to deploy in realistic settings."),
    "cs.LG": ("We investigate a novel learning algorithm with theoretical "
              "guarantees and strong empirical performance on standard "
              "machine-learning benchmarks. Ablations show that each "
              "component contributes to the overall gains."),
    "cs.CV": ("We propose a vision model that improves recognition and "
              "generation accuracy under challenging conditions. Experiments "
              "on standard image benchmarks demonstrate consistent gains "
              "over strong baselines."),
    "cs.AI": ("We introduce an AI system that reasons over structured and "
              "unstructured inputs to produce more reliable decisions. We "
              "report improvements on multiple reasoning benchmarks."),
    "cs.SY": ("We study a control and systems problem motivated by modern "
              "cyber-physical applications. The proposed controller achieves "
              "provable stability and favourable tracking behaviour in "
              "simulation."),
    "eess.SY": ("This work addresses a systems-and-control problem with a "
                "data-driven controller synthesis pipeline, demonstrating "
                "robustness to disturbances and model uncertainty."),
    "quant-ph": ("We analyse a quantum information protocol that trades off "
                 "resource cost against fidelity. Our results shed light on "
                 "the feasibility of near-term quantum devices for this task."),
    "stat.ML": ("We develop a statistical learning method with non-asymptotic "
                "guarantees, and validate it on benchmark datasets where it "
                "matches or exceeds the state of the art."),
    "astro-ph.SR": ("We report new observations and modelling of stellar "
                    "phenomena that constrain theoretical predictions for "
                    "solar and stellar structure."),
    "astro-ph.EP": ("We present an analysis of planetary and earth-science "
                    "data, with implications for the formation and evolution "
                    "of planetary systems."),
}


# -----------------------------------------------------------------------
# Visual asset mapping helpers (image utilization deepening — 2026-05-27)
# -----------------------------------------------------------------------
# A single, deterministic md5 -> SVG mapping is shared by templates, seed-time
# DB population, and the GUI-task generator. Pure functions of arxiv_id /
# author name / conference slug so byte-identical rebuilds stay clean.

# Figure styles by primary-category prefix. Each prefix maps to a small list
# of style files. md5(arxiv_id) chooses the slot.
_FIGURE_STYLES_BY_PREFIX = {
    "cs":       ["arch", "line", "bar", "heatmap", "scatter", "curve"],
    "stat":     ["scatter", "line", "heatmap", "bar", "curve"],
    "math":     ["curve", "lattice", "line", "scatter"],
    "physics":  ["lattice", "galaxy", "line", "scatter"],
    "astro-ph": ["galaxy", "scatter", "line", "curve"],
    "cond-mat": ["lattice", "heatmap", "line", "scatter"],
    "quant-ph": ["lattice", "heatmap", "curve", "line"],
    "q-bio":    ["brain", "scatter", "line", "heatmap"],
    "q-fin":    ["line", "bar", "heatmap", "scatter"],
    "eess":     ["heatmap", "line", "curve", "scatter"],
    "econ":     ["line", "bar", "scatter"],
    "hep-th":   ["lattice", "curve", "scatter"],
    "hep-ph":   ["lattice", "scatter", "curve"],
    "hep-ex":   ["scatter", "line", "curve"],
    "nucl-th":  ["lattice", "curve"],
    "nucl-ex":  ["scatter", "line"],
    "nlin":     ["curve", "scatter"],
    "gr-qc":    ["galaxy", "curve"],
    "math-ph":  ["lattice", "curve"],
}

# Caption templates per style, parameterised by subject area + paper title prefix.
_FIGURE_CAPTION_TEMPLATES = {
    "arch": [
        "Figure {n}: model architecture — encoder/decoder layout with skip connections.",
        "Figure {n}: overall pipeline. Inputs are tokenised, embedded, and fed through {layers} transformer layers.",
        "Figure {n}: system diagram. Pretrained backbone (frozen) feeds a task-specific head.",
    ],
    "line": [
        "Figure {n}: training loss and validation accuracy across {epochs} epochs.",
        "Figure {n}: ablation — performance versus model size (parameters, log scale).",
        "Figure {n}: convergence behaviour for the four learning-rate schedules considered.",
    ],
    "bar": [
        "Figure {n}: per-task benchmark scores on the eight evaluation datasets.",
        "Figure {n}: comparison against published baselines (higher is better).",
        "Figure {n}: ablation — contribution of each module to final accuracy.",
    ],
    "heatmap": [
        "Figure {n}: attention map across layers and heads for a representative input.",
        "Figure {n}: confusion matrix on the held-out test split ({classes} classes).",
        "Figure {n}: pairwise feature correlation heatmap after projection.",
    ],
    "scatter": [
        "Figure {n}: t-SNE projection of learned embeddings, coloured by predicted label.",
        "Figure {n}: empirical scaling — error vs compute budget (log-log).",
        "Figure {n}: scatter of predicted versus reference values; identity line in grey.",
    ],
    "curve": [
        "Figure {n}: ROC curve and operating points for the four classifier variants.",
        "Figure {n}: cumulative reward over interaction steps (mean over 5 seeds, shaded ±1σ).",
        "Figure {n}: precision-recall envelope on the augmented evaluation set.",
    ],
    "galaxy": [
        "Figure {n}: simulated survey catalogue — projected on the sky in equatorial coordinates.",
        "Figure {n}: density field of the dark-matter halo population in the N-body run.",
        "Figure {n}: light-curve sample for the {n} brightest sources in the field.",
    ],
    "lattice": [
        "Figure {n}: unit cell of the proposed crystal structure (hexagonal symmetry).",
        "Figure {n}: spin configuration on the underlying lattice after equilibration.",
        "Figure {n}: schematic of the {n}-site Hamiltonian and the on-site interaction.",
    ],
    "brain": [
        "Figure {n}: functional-connectivity graph reconstructed from the recording session.",
        "Figure {n}: graph of co-activation across cortical regions of interest.",
        "Figure {n}: schematic of the cell-type interaction network considered in the model.",
    ],
}


def _figure_style_for(arxiv_id: str, position: int, primary_category: str,
                      primary_subject: str) -> str:
    """Pick a figure style for (paper, position) deterministically."""
    pool = (_FIGURE_STYLES_BY_PREFIX.get(primary_subject)
            or _FIGURE_STYLES_BY_PREFIX.get(primary_category)
            or ["line", "bar", "scatter", "heatmap"])
    h = hashlib.md5(f"figstyle|{arxiv_id}|{position}".encode()).digest()
    return pool[h[0] % len(pool)]


def _figure_filename(style: str, arxiv_id: str, position: int) -> str:
    """Pick a specific SVG file from the 8-variant pool for a style."""
    h = hashlib.md5(f"figfile|{arxiv_id}|{position}".encode()).digest()
    return f"figures/{style}_{h[1] % 8:02d}.svg"


def _figure_caption(style: str, arxiv_id: str, position: int) -> str:
    templates = _FIGURE_CAPTION_TEMPLATES.get(style) or [f"Figure {{n}}: result of analysis."]
    h = hashlib.md5(f"figcap|{arxiv_id}|{position}".encode()).digest()
    tmpl = templates[h[2] % len(templates)]
    return tmpl.format(
        n=position,
        epochs=20 + (h[3] % 80),
        layers=4 + (h[4] % 20),
        classes=2 + (h[5] % 18),
    )


def _figure_count_for(arxiv_id: str, declared: int) -> int:
    """How many figures to surface on the abs page. Use declared count from
    comments when available, clipped to [2, 5]. Otherwise hash-derive."""
    if declared and declared > 0:
        return max(2, min(5, declared))
    h = hashlib.md5(f"figcount|{arxiv_id}".encode()).digest()
    return 3 + (h[0] % 3)  # 3..5


def _avatar_filename(author_name: str) -> str:
    if not author_name:
        return "headshots/avatar_00.svg"
    h = hashlib.md5(f"avatar|{author_name}".encode()).digest()
    return f"headshots/avatar_{h[0] % 24:02d}.svg"


_INSTITUTION_ACCENTS = {
    "Massachusetts Institute of Technology": "#A31F34",
    "Stanford University": "#8C1515",
    "University of California, Berkeley": "#003262",
    "Carnegie Mellon University": "#C41230",
    "ETH Zurich": "#1F407A",
    "University of Cambridge": "#A3C1AD",
    "University of Oxford": "#002147",
    "Tsinghua University": "#7B1FA2",
    "Peking University": "#94070A",
    "University of Toronto": "#002A5C",
    "California Institute of Technology": "#FF6C0C",
    "Princeton University": "#E77500",
    "Harvard University": "#A51C30",
    "Cornell University": "#B31B1B",
    "DeepMind": "#0B57D0",
    "Google Research": "#4285F4",
    "Microsoft Research": "#00A4EF",
    "Meta AI": "#1877F2",
    "OpenAI": "#10A37F",
    "IBM Research": "#0F62FE",
    "NVIDIA Research": "#76B900",
    "Allen Institute for AI": "#0066CC",
}


def _institution_accent(affiliation: str) -> str:
    return _INSTITUTION_ACCENTS.get(affiliation, "#555555")


# Real conference banner files (live under static/images/conferences/<slug>.svg).
_CONFERENCE_SLUGS = {
    "NeurIPS":  ("neurips",  "#5e3ec5"),
    "ICML":     ("icml",     "#1b6ec2"),
    "ICLR":     ("iclr",     "#0e8a6a"),
    "ACL":      ("acl",      "#b13434"),
    "EMNLP":    ("emnlp",    "#7a3da6"),
    "CVPR":     ("cvpr",     "#1f6f4a"),
    "ICCV":     ("iccv",     "#185680"),
    "AAAI":     ("aaai",     "#a64a1a"),
    "KDD":      ("kdd",      "#5a4f24"),
    "SIGGRAPH": ("siggraph", "#3a4e8c"),
}


def _conf_banner_filename(conf: str) -> str:
    rec = _CONFERENCE_SLUGS.get(conf)
    if not rec:
        return "conferences/neurips.svg"
    return f"conferences/{rec[0]}.svg"


def _category_banner_filename(code: str) -> str:
    """Banner for a category hub. Falls back to its top-level category."""
    top = code.split(".")[0] if "." in code else code
    return f"categories/{top}.svg"


# Slug map for institution badge SVGs in static/images/institutions/.
# Every value in _STUB_AFFILIATIONS must have an entry here. The files
# themselves are generated by sites/arxiv/static/images/institutions/
# (one 96x96 monogram SVG per affiliation, distinct accent colour).
# This replaces the original behaviour where every author_images row
# stored institution_logo='categories/cs.svg' — 1500 identical rows.
_INSTITUTION_LOGO_SLUGS = {
    "Massachusetts Institute of Technology": "mit",
    "Stanford University": "stanford",
    "University of California, Berkeley": "berkeley",
    "Carnegie Mellon University": "cmu",
    "ETH Zurich": "eth_zurich",
    "University of Cambridge": "cambridge",
    "University of Oxford": "oxford",
    "Tsinghua University": "tsinghua",
    "Peking University": "peking",
    "University of Toronto": "toronto",
    "California Institute of Technology": "caltech",
    "Princeton University": "princeton",
    "Harvard University": "harvard",
    "Cornell University": "cornell",
    "University of Illinois Urbana-Champaign": "uiuc",
    "University of Tokyo": "u_tokyo",
    "Max Planck Institute": "max_planck",
    "Imperial College London": "imperial",
    "National University of Singapore": "nus",
    "Seoul National University": "snu",
    "University of Michigan": "umich",
    "Columbia University": "columbia",
    "Yale University": "yale",
    "University of Chicago": "uchicago",
    "University of Washington": "uw",
    "Georgia Institute of Technology": "georgia_tech",
    "Shanghai Jiao Tong University": "sjtu",
    "EPFL": "epfl",
    "University of Edinburgh": "edinburgh",
    "University of Texas at Austin": "ut_austin",
    "New York University": "nyu",
    "University of Pennsylvania": "upenn",
    "KAIST": "kaist",
    "Tel Aviv University": "tau",
    "University of Melbourne": "melbourne",
    "Technical University of Munich": "tum",
    "Johns Hopkins University": "jhu",
    "University of California, Los Angeles": "ucla",
    "DeepMind": "deepmind",
    "Google Research": "google",
    "Microsoft Research": "microsoft",
    "Meta AI": "meta",
    "OpenAI": "openai",
    "IBM Research": "ibm",
    "NVIDIA Research": "nvidia",
    "Allen Institute for AI": "ai2",
}


def _institution_logo_filename(affiliation: str) -> str:
    """Return a per-affiliation logo path under static/images/.

    Falls back to a generic badge so unknown affiliations never 404.
    """
    slug = _INSTITUTION_LOGO_SLUGS.get(affiliation)
    if not slug:
        # Deterministic fallback so unknown strings still spread across
        # the pool instead of collapsing to a single placeholder.
        keys = sorted(_INSTITUTION_LOGO_SLUGS.values())
        idx = int(hashlib.md5(
            (affiliation or "").encode("utf-8")).hexdigest()[:8], 16
        ) % len(keys)
        slug = keys[idx]
    return f"institutions/{slug}.svg"


def _pdf_cover_filename(arxiv_id: str) -> str:
    h = hashlib.md5(f"cover|{arxiv_id}".encode()).digest()
    return f"pdf_covers/cover_{h[0] % 16:02d}.svg"


def _synthesize_authors(arxiv_id: str) -> list:
    """Deterministically synthesise a 2-5 person author list from arxiv_id."""
    if not arxiv_id:
        return []
    digest = hashlib.md5(arxiv_id.encode("utf-8")).digest()
    n_authors = 2 + (digest[0] % 4)  # 2..5
    names = []
    for i in range(n_authors):
        fi = digest[(i * 2) % len(digest)] % len(_STUB_FIRST_NAMES)
        li = digest[(i * 2 + 1) % len(digest)] % len(_STUB_LAST_NAMES)
        names.append(f"{_STUB_FIRST_NAMES[fi]} {_STUB_LAST_NAMES[li]}")
    return names


_STUB_AFFILIATIONS = [
    "Massachusetts Institute of Technology",
    "Stanford University",
    "University of California, Berkeley",
    "Carnegie Mellon University",
    "ETH Zurich",
    "University of Cambridge",
    "University of Oxford",
    "Tsinghua University",
    "Peking University",
    "University of Toronto",
    "California Institute of Technology",
    "Princeton University",
    "Harvard University",
    "Cornell University",
    "University of Illinois Urbana-Champaign",
    "University of Tokyo",
    "Max Planck Institute",
    "Imperial College London",
    "National University of Singapore",
    "Seoul National University",
    "University of Michigan",
    "Columbia University",
    "Yale University",
    "University of Chicago",
    "University of Washington",
    "Georgia Institute of Technology",
    "Shanghai Jiao Tong University",
    "EPFL",
    "University of Edinburgh",
    "University of Texas at Austin",
    "New York University",
    "University of Pennsylvania",
    "KAIST",
    "Tel Aviv University",
    "University of Melbourne",
    "Technical University of Munich",
    "Johns Hopkins University",
    "University of California, Los Angeles",
    "DeepMind",
    "Google Research",
    "Microsoft Research",
    "Meta AI",
    "OpenAI",
    "IBM Research",
    "NVIDIA Research",
    "Allen Institute for AI",
]


def _synthesize_affiliation(author_name: str) -> str:
    """Deterministically derive an affiliation from an author name."""
    if not author_name:
        return "Independent Researcher"
    digest = hashlib.md5(author_name.encode("utf-8")).digest()
    idx = digest[0] % len(_STUB_AFFILIATIONS)
    return _STUB_AFFILIATIONS[idx]


def _affiliations_for_authors(authors: list) -> list:
    return [_synthesize_affiliation(a) for a in authors]


def _synthesize_abstract(title: str, subject_code: str,
                         primary_subject: str = "") -> str:
    """Build a reasonable abstract from the title + category blurb."""
    blurb = _CATEGORY_BLURBS.get(subject_code)
    if not blurb:
        parent = subject_code.split(".")[0] if "." in subject_code else subject_code
        blurb = _CATEGORY_BLURBS.get(parent,
            "This paper presents new methods and experimental results "
            "relevant to the subject area. We describe the approach, report "
            "empirical findings, and discuss implications for future work.")
    lead = title.strip().rstrip(".") if title else "This work"
    return (f"{lead}. {blurb} "
            f"Full details are available in the preprint; please refer to "
            f"the PDF for complete formal statements, proofs, and additional "
            f"experiments.")


def _clean_arxiv_metadata_text(text):
    return clean_arxiv_metadata_text(text)


# R5 — deterministic per-paper provenance fields. All derive from arxiv_id /
# author name so byte-identical rebuilds are preserved.

_LICENSE_POOL = [
    "CC-BY-4.0",
    "CC-BY-SA-4.0",
    "CC-BY-NC-SA-4.0",
    "CC-BY-NC-ND-4.0",
    "CC0-1.0",
    "arXiv-perpetual",
]

_LICENSE_WEIGHTS = [
    # Most arxiv papers ship under the perpetual non-exclusive license.
    "arXiv-perpetual", "arXiv-perpetual", "arXiv-perpetual", "arXiv-perpetual",
    "arXiv-perpetual", "arXiv-perpetual", "arXiv-perpetual",
    "CC-BY-4.0", "CC-BY-4.0", "CC-BY-4.0",
    "CC-BY-SA-4.0",
    "CC-BY-NC-SA-4.0",
    "CC-BY-NC-ND-4.0",
    "CC0-1.0",
]

# Mapping from arxiv primary-category prefix → ACM CCS / CR-class label.
_CCS_BY_PREFIX = {
    "cs.AI": "I.2.0 Artificial Intelligence — General",
    "cs.CL": "I.2.7 Natural Language Processing",
    "cs.CV": "I.4.0 Image Processing and Computer Vision",
    "cs.LG": "I.2.6 Learning",
    "cs.RO": "I.2.9 Robotics",
    "cs.CR": "K.6.5 Security and Protection",
    "cs.IR": "H.3.3 Information Search and Retrieval",
    "cs.SE": "D.2.0 Software Engineering — General",
    "cs.HC": "H.5.2 User Interfaces",
    "cs.DC": "C.2.4 Distributed Systems",
    "cs.DB": "H.2 Database Management",
    "cs.DS": "F.2 Analysis of Algorithms",
    "cs.NE": "I.2.6 Neural Networks",
    "cs.SI": "H.3.4 Systems and Software",
    "cs.GT": "F.1.1 Models of Computation",
    "cs.SY": "I.6 Simulation, Modeling, and Visualization",
    "cs.PL": "D.3 Programming Languages",
    "cs.OS": "D.4 Operating Systems",
    "cs.NI": "C.2 Computer-Communication Networks",
    "cs.GR": "I.3 Computer Graphics",
    "stat.ML": "G.3 Probability and Statistics — Learning",
    "stat.ME": "G.3 Probability and Statistics — Methodology",
    "stat.AP": "G.3 Probability and Statistics — Applications",
    "stat.TH": "G.3 Probability and Statistics — Theory",
    "math.OC": "G.1.6 Optimization",
    "math.NA": "G.1 Numerical Analysis",
    "math.PR": "G.3 Probability and Statistics",
    "math.ST": "G.3 Statistics Theory",
    "math.CO": "G.2 Discrete Mathematics — Combinatorics",
    "math.NT": "G.2.1 Number Theory",
    "math.AG": "F.4 Mathematical Logic and Formal Languages",
    "eess.SP": "I.5 Pattern Recognition — Signal Processing",
    "eess.IV": "I.4 Image Processing",
    "eess.AS": "H.5.1 Multimedia Information Systems — Audio",
    "eess.SY": "I.6 Simulation, Modeling, and Visualization",
    "quant-ph": "F.1.2 Modes of Computation — Quantum",
    "q-bio.NC": "J.3 Life and Medical Sciences — Neuroscience",
    "q-bio.QM": "J.3 Life and Medical Sciences — Quantitative Methods",
    "q-fin.ST": "J.1 Administration and Business — Statistical Finance",
    "econ.EM": "J.4 Social and Behavioral Sciences — Econometrics",
}

# Common submitter email domains, picked deterministically from a per-paper hash.
_SUBMITTER_DOMAINS = [
    "mit.edu", "stanford.edu", "berkeley.edu", "cmu.edu", "princeton.edu",
    "harvard.edu", "ox.ac.uk", "cam.ac.uk", "ethz.ch", "epfl.ch",
    "u-tokyo.ac.jp", "tsinghua.edu.cn", "pku.edu.cn", "ust.hk", "nus.edu.sg",
    "tum.de", "kth.se", "uva.nl", "imperial.ac.uk", "ucl.ac.uk",
    "google.com", "research.microsoft.com", "fb.com", "deepmind.com",
    "openai.com", "anthropic.com", "ibm.com", "nvidia.com",
    "gmail.com", "outlook.com",
]


def _derive_paper_version(arxiv_id: str, versions: list) -> str:
    """Use the OAI-supplied versions list when present; otherwise hash-derive
    a stable v1/v2/v3 label so each paper has a version even when upstream
    metadata didn't ship one. Distribution: ~70% v1, ~22% v2, ~6% v3, ~2% v4.
    """
    if versions:
        # Latest entry wins. Strip leading 'v' just in case.
        last = (versions[-1].get("version") or "").lstrip("v").strip()
        try:
            n = max(1, int(last))
        except Exception:
            n = 1
        return f"v{min(n, 9)}"
    if not arxiv_id:
        return "v1"
    n = hashlib.md5(arxiv_id.encode("utf-8")).digest()[0] % 100
    if n < 70:
        return "v1"
    if n < 92:
        return "v2"
    if n < 98:
        return "v3"
    return "v4"


def _derive_license(arxiv_id: str) -> str:
    if not arxiv_id:
        return "arXiv-perpetual"
    h = hashlib.md5(("lic-" + arxiv_id).encode("utf-8")).digest()
    return _LICENSE_WEIGHTS[h[0] % len(_LICENSE_WEIGHTS)]


def _derive_submitter_email(arxiv_id: str, first_author: str) -> str:
    """Produce a masked email like 'j****@mit.edu' that is stable per paper."""
    if not arxiv_id:
        return ""
    base = (first_author or "").strip().split()
    if base:
        # Take last name as the local part anchor; first character only is kept.
        local_anchor = base[-1].lower()
    else:
        local_anchor = "author"
    local_anchor = re.sub(r"[^a-z0-9]", "", local_anchor) or "author"
    masked_local = local_anchor[0] + "*" * max(3, len(local_anchor) - 1)
    domain_idx = hashlib.md5(("dom-" + arxiv_id).encode("utf-8")).digest()[0]
    domain = _SUBMITTER_DOMAINS[domain_idx % len(_SUBMITTER_DOMAINS)]
    return f"{masked_local}@{domain}"


def _derive_computer_classification(subject_code: str, primary_category: str) -> str:
    if subject_code and subject_code in _CCS_BY_PREFIX:
        return _CCS_BY_PREFIX[subject_code]
    # Fallback: try the parent category, then a generic label.
    if subject_code:
        return _CCS_BY_PREFIX.get(subject_code, "")
    if primary_category and primary_category in _CCS_BY_PREFIX:
        return _CCS_BY_PREFIX[primary_category]
    return ""


def seed_database():
    """Populate the DB from categories.json + papers.json."""
    if Category.query.first() is not None:
        return  # already seeded

    # --- Categories ---
    cat_path = BASE_DIR / "categories.json"
    if cat_path.exists():
        cat_data = json.load(open(cat_path))
        primary_cats = cat_data["categories"]
        subcats = cat_data["subcategories"]
    else:
        primary_cats = {}
        subcats = {}

    descriptions = {
        "cs": "Research in computing, from the theoretical foundations of algorithms to the practice of machine learning, computer vision, and software engineering.",
        "math": "Pure and applied mathematics: algebra, geometry, topology, analysis, probability, number theory, and more.",
        "physics": "General physics research spanning applied, atomic, biological, computational, and many other subfields.",
        "astro-ph": "Astrophysics: cosmology, galaxies, high-energy phenomena, instrumentation, solar and stellar physics.",
        "cond-mat": "Condensed matter physics: materials, mesoscale systems, quantum gases, soft matter, and superconductivity.",
        "gr-qc": "General relativity and quantum cosmology.",
        "hep-ex": "High energy physics experiments — large detectors, colliders, and beyond.",
        "hep-lat": "Lattice field theory and numerical high energy physics.",
        "hep-ph": "Phenomenology linking theory to experiment in high energy physics.",
        "hep-th": "Formal theoretical developments in high energy physics.",
        "math-ph": "Mathematical physics.",
        "nlin": "Nonlinear sciences: chaos, adaptation, pattern formation, and integrable systems.",
        "nucl-ex": "Nuclear experiment.",
        "nucl-th": "Nuclear theory.",
        "quant-ph": "Quantum information, quantum computing, and the foundations of quantum mechanics.",
        "q-bio": "Quantitative biology: biomolecules, cells, genomics, neurons, populations, and more.",
        "q-fin": "Quantitative finance: pricing, portfolios, risk, trading, and statistical finance.",
        "stat": "Statistics: applications, computation, methodology, machine learning, and theory.",
        "eess": "Electrical engineering and systems science: audio, image processing, signal processing, control.",
        "econ": "Economics: econometrics, general economics, and theoretical economics.",
    }

    for code, meta in primary_cats.items():
        cat = Category(
            code=code,
            name=meta.get("name", code),
            icon=meta.get("icon", "📚"),
            color=meta.get("color", "#b31b1b"),
            short_name=meta.get("short", code),
            description=descriptions.get(code, ""),
        )
        db.session.add(cat)
    db.session.commit()
    print(f"  [+] Seeded {Category.query.count()} categories")

    # --- Papers ---
    papers_path = BASE_DIR / "papers.json"
    if not papers_path.exists():
        print("  ! papers.json not found; skipping paper seed")
        return

    raw_papers = json.load(open(papers_path))
    # --- Extra papers fetched live from the arXiv API (optional source). ---
    # `sites/arxiv/scraped_data/` is .gitignored / .dockerignored, so this file
    # only exists on the build host; once folded into instance_seed/arxiv.db it
    # ships in the image. Dedup happens further down via the arxiv_id check.
    extras_path = BASE_DIR / "scraped_data" / "papers_extra.json"
    if extras_path.exists():
        try:
            extra_raw = json.load(open(extras_path))
            print(f"  [+] Loaded {len(extra_raw)} extra papers from scraped_data/papers_extra.json")
            raw_papers.extend(extra_raw)
        except Exception as exc:
            print(f"  ! Failed to load papers_extra.json: {exc}")
    # Order: papers with abstracts first
    raw_papers.sort(key=lambda p: (0 if p.get("abstract") else 1, p.get("arxiv_id", "")))

    # Seed RNG so that view/download/star counts are deterministic across
    # rebuilds — this is what makes md5sum(instance_seed/arxiv.db) stable.
    random.seed(20260415)
    created = 0
    for rp in raw_papers:
        arxiv_id = rp.get("arxiv_id", "").strip()
        if not arxiv_id:
            continue
        if Paper.query.filter_by(arxiv_id=arxiv_id).first():
            continue
        # Parse primary subject code from the "subjects" field
        subjects = rp.get("subjects", "").strip()
        primary_subject = subjects.split(";")[0].strip() if subjects else ""
        m = re.search(r"\(([a-zA-Z\-]+(?:\.[a-zA-Z\-]+)?)\)", primary_subject)
        subject_code = m.group(1) if m else rp.get("primary_category", "")
        primary_category = subject_code.split(".")[0] if "." in subject_code else subject_code
        # Map astro-ph, cond-mat, etc
        if primary_category not in primary_cats and subject_code in primary_cats:
            primary_category = subject_code
        # Titles
        title = _clean_arxiv_metadata_text(rp.get("title", "").strip())
        if not title:
            continue
        # Parse date, falling back to arxiv-id-encoded yymm (e.g. 2604.08525 -> 2026-04)
        sub_y, sub_m, sub_d = 0, 0, 0
        date_raw = (rp.get("date") or "").strip()
        dm = re.match(r"(\d{4})[/-](\d{1,2})[/-](\d{1,2})", date_raw)
        if dm:
            sub_y, sub_m, sub_d = int(dm.group(1)), int(dm.group(2)), int(dm.group(3))
        else:
            idm = re.match(r"(\d{2})(\d{2})\.(\d+)", arxiv_id)
            if idm:
                yy, mm, tail = int(idm.group(1)), int(idm.group(2)), idm.group(3)
                sub_y = 2000 + yy if yy < 90 else 1900 + yy
                sub_m = mm
                # deterministic pseudo-day based on tail digits so sorting is stable
                try:
                    sub_d = max(1, min(28, int(tail[-2:]) % 28 + 1))
                except Exception:
                    sub_d = 1
        authors = rp.get("authors", []) or []
        # Backfill empty author lists with a deterministic stub so abs pages
        # never render a blank author line. Uses arxiv_id as a stable seed.
        if not authors:
            authors = _synthesize_authors(arxiv_id)
        # R4 — OAI-PMH source ships real `author_affiliations` (parallel list
        # to `authors`). When present use them verbatim; otherwise synthesise.
        raw_affs = rp.get("author_affiliations") or []
        affs = []
        for i, a in enumerate(authors):
            real = raw_affs[i] if i < len(raw_affs) and raw_affs[i] else ""
            affs.append(real or _synthesize_affiliation(a))
        # Parse figures, tables, formulas counts from comments
        cmt = _clean_arxiv_metadata_text(rp.get("comments", ""))
        figs = 0
        tbls = 0
        frms = 0
        fm = re.search(r"(\d+)\s*figure", cmt, re.I)
        if fm:
            figs = int(fm.group(1))
        tm = re.search(r"(\d+)\s*table", cmt, re.I)
        if tm:
            tbls = int(tm.group(1))
        frm = re.search(r"(\d+)\s*formula", cmt, re.I)
        if frm:
            frms = int(frm.group(1))
        # Versions
        versions = rp.get("versions", [])
        # R5 — derived provenance fields. All deterministic per arxiv_id so
        # rebuilds stay byte-identical.
        _paper_version = _derive_paper_version(arxiv_id, versions)
        _paper_license = _derive_license(arxiv_id)
        _first_author = authors[0] if authors else ""
        _submitter_email = _derive_submitter_email(arxiv_id, _first_author)
        _ccs = _derive_computer_classification(subject_code, primary_category)
        # Loss function from abstract
        loss_fn = ""
        abs_text = _clean_arxiv_metadata_text(rp.get("abstract", "") or "")
        # Backfill empty abstracts for high-traffic categories so the /abs
        # and listing pages always surface something meaningful.
        if not abs_text:
            abs_text = _synthesize_abstract(title, subject_code, primary_subject)
        lm = re.search(r"(sim\([^)]*\))", abs_text)
        if lm:
            loss_fn = lm.group(1)
        paper = Paper(
            arxiv_id=arxiv_id,
            title=title,
            abstract=abs_text,
            authors_json=json.dumps(authors),
            author_affiliations_json=json.dumps(affs),
            n_authors=len(authors),
            subjects=subjects,
            primary_subject=primary_subject,
            primary_subject_code=subject_code,
            primary_category_code=primary_category,
            submitted_date=(f"{sub_y:04d}-{sub_m:02d}-{sub_d:02d}"
                            if sub_y else date_raw),
            submitted_year=sub_y,
            submitted_month=sub_m,
            submitted_day=sub_d,
            announce_date=(f"{sub_y:04d}-{sub_m:02d}-{sub_d:02d}" if sub_y else ""),
            comments=cmt,
            journal_ref=rp.get("journal_ref", ""),
            doi=rp.get("doi", ""),
            msc_class=(rp.get("msc_class") or "").strip(),
            acm_class=(rp.get("acm_class") or "").strip(),
            report_no=(rp.get("report_no") or "").strip(),
            paper_version=_paper_version,
            license=_paper_license,
            submitter_email_masked=_submitter_email,
            computer_classification=_ccs,
            pdf_url=f"https://arxiv.org/pdf/{arxiv_id}",
            html_url=f"https://arxiv.org/abs/{arxiv_id}",
            html_available=True,
            figures_count=figs,
            tables_count=tbls,
            formulas_count=frms,
            loss_function=loss_fn,
            versions_json=json.dumps(versions) if versions else "[]",
            view_count=random.randint(50, 5000),
            download_count=random.randint(20, 2000),
            star_count=random.randint(0, 200),
            # Deterministic pseudo-timestamp so md5 of instance_seed/arxiv.db
            # is stable across rebuilds. Spread across a 1-year window.
            created_at=MIRROR_REFERENCE_DATE - timedelta(
                minutes=(created * 7) % (365 * 24 * 60)
            ),
        )
        db.session.add(paper)
        created += 1
        if created % 200 == 0:
            db.session.commit()
    db.session.commit()
    print(f"  [+] Seeded {created} papers")

    # --- Demo user with some activity ---
    if not User.query.filter_by(email="demo@arxiv.local").first():
        u = User(
            email="demo@arxiv.local",
            username="demouser",
            full_name="Demo Researcher",
            affiliation="Example University",
            bio="A demo researcher exploring topics in machine learning.",
            orcid="0000-0000-0000-0000",
            created_at=MIRROR_REFERENCE_DATE - timedelta(days=180),
            password_hash=PINNED_HASH_DEMODEMO,
        )
        db.session.add(u)
        db.session.commit()
        # Add a few library/starred items for demo flavor. Order by arxiv_id
        # so the picks are stable across rebuilds even if insert order shifts.
        sample_papers = (Paper.query.filter(Paper.abstract != "")
                         .order_by(Paper.arxiv_id).limit(5).all())
        for i, p in enumerate(sample_papers[:3]):
            db.session.add(LibraryItem(
                user_id=u.id, paper_id=p.id, folder="Reading List",
                added_at=MIRROR_REFERENCE_DATE - timedelta(days=30 - i),
            ))
        for j, p in enumerate(sample_papers[3:5]):
            db.session.add(StarredPaper(
                user_id=u.id, paper_id=p.id,
                starred_at=MIRROR_REFERENCE_DATE - timedelta(days=20 - j),
            ))
        db.session.commit()
        print("  [+] Created demo user (demo@arxiv.local / demodemo)")


# =======================================================================
# CONTEXT PROCESSORS
# =======================================================================

@app.context_processor
def inject_globals():
    library_count = 0
    if current_user.is_authenticated:
        library_count = LibraryItem.query.filter_by(user_id=current_user.id).count()

    # main_categories + mirror_today_iso are static between control_server
    # /reset calls (Category table is read-only at runtime; the seed Paper
    # table's max submitted_date is fixed at build time). Without caching,
    # every page render fires both a Category.order_by(code).all() and a
    # func.max(submitted_date) full-scan over 380k papers (~14ms each).
    global _ARXIV_MAIN_CATS_CACHE, _ARXIV_MIRROR_TODAY_CACHE
    if _ARXIV_MAIN_CATS_CACHE is None:
        _ARXIV_MAIN_CATS_CACHE = Category.query.order_by(Category.code).all()
    main_cats = _ARXIV_MAIN_CATS_CACHE

    if _ARXIV_MIRROR_TODAY_CACHE is None:
        _ARXIV_MIRROR_TODAY_CACHE = (
            db.session.query(func.max(Paper.submitted_date)).scalar() or "")
    mirror_today_iso = _ARXIV_MIRROR_TODAY_CACHE
    mirror_today_pretty = ""
    if mirror_today_iso:
        try:
            d = datetime.strptime(mirror_today_iso, "%Y-%m-%d")
            mirror_today_pretty = d.strftime("%a, %d %b %Y")
        except Exception:
            mirror_today_pretty = mirror_today_iso

    return dict(
        library_count=library_count,
        main_categories=main_cats,
        current_year=datetime.utcnow().year,
        mirror_today=mirror_today_iso,
        mirror_today_pretty=mirror_today_pretty,
    )


_ARXIV_MAIN_CATS_CACHE = None
_ARXIV_MIRROR_TODAY_CACHE = None


# =======================================================================
# HELPERS
# =======================================================================

def get_category_or_404(code: str) -> Category:
    cat = Category.query.filter_by(code=code).first()
    if not cat:
        abort(404)
    return cat


def get_papers_for_category(code: str, page: int = 1, per_page: int = 25):
    q = Paper.query.filter(
        or_(Paper.primary_subject_code == code,
            Paper.primary_subject_code.like(f"{code}.%"),
            Paper.primary_category_code == code)
    ).order_by(Paper.arxiv_id.desc())
    total = q.count()
    papers = q.offset((page - 1) * per_page).limit(per_page).all()
    return papers, total


def new_export_id() -> str:
    return "EX" + datetime.utcnow().strftime("%Y%m%d%H%M%S") + str(random.randint(100, 999))


# -----------------------------------------------------------------------
# Search helpers — scored relevance + filters + sorts
# -----------------------------------------------------------------------

STOPWORDS = {
    "the", "a", "an", "of", "in", "on", "at", "to", "for", "with",
    "and", "or", "is", "are", "be", "by", "from", "as", "that", "this",
    "its", "it", "we", "our", "about", "how", "latest", "most", "recent",
    "paper", "papers", "article", "articles", "which", "whose", "was",
    "were", "have", "has", "had", "do", "does", "did",
}


def _score_paper(paper: "Paper", tokens: list) -> int:
    haystack = " ".join([
        (paper.title or "").lower(),
        (paper.abstract or "").lower(),
        (paper.authors_json or "").lower(),
        (paper.subjects or "").lower(),
        (paper.primary_subject or "").lower(),
        (paper.primary_subject_code or "").lower(),
        (paper.primary_category_code or "").lower(),
        (paper.journal_ref or "").lower(),
        (paper.comments or "").lower(),
        (paper.arxiv_id or "").lower(),
    ])
    return sum(1 for t in tokens if t in haystack)


def _tokenize_query(q: str) -> list:
    tokens = [t.lower() for t in re.findall(r"[a-z0-9]+", (q or "").lower())]
    return [t for t in tokens if t and t not in STOPWORDS and len(t) >= 2]


def _parse_date_str(s: str):
    """Parse 'YYYY-MM-DD' or 'YYYY-MM-DDTHH:MM:SS' etc into a date tuple (y,m,d) or None."""
    if not s:
        return None
    m = re.match(r"(\d{4})-(\d{1,2})-(\d{1,2})", s.strip())
    if m:
        return (int(m.group(1)), int(m.group(2)), int(m.group(3)))
    m = re.match(r"(\d{4})/(\d{1,2})/(\d{1,2})", s.strip())
    if m:
        return (int(m.group(1)), int(m.group(2)), int(m.group(3)))
    return None


def _apply_paper_filters(query_obj):
    """Apply request.args structural filters to a Paper query."""
    # Primary category / subject code filter. Accept either 'category' or 'primary_category'.
    cat = (request.args.get("category") or request.args.get("primary_category") or "").strip()
    if cat:
        if "." in cat:
            # Specific subject like cs.CL
            query_obj = query_obj.filter(Paper.primary_subject_code == cat)
        else:
            query_obj = query_obj.filter(or_(
                Paper.primary_subject_code == cat,
                Paper.primary_subject_code.like(f"{cat}.%"),
                Paper.primary_category_code == cat,
            ))

    # Subject substring (legacy)
    subject = (request.args.get("subject") or "").strip()
    if subject:
        query_obj = query_obj.filter(Paper.subjects.ilike(f"%{subject}%"))

    # Year range
    year = request.args.get("year", type=int)
    if year:
        query_obj = query_obj.filter(Paper.submitted_year == year)
    year_from = request.args.get("year_from", type=int)
    if year_from:
        query_obj = query_obj.filter(Paper.submitted_year >= year_from)
    year_to = request.args.get("year_to", type=int)
    if year_to:
        query_obj = query_obj.filter(Paper.submitted_year <= year_to)

    # Month (+ year) filter
    month = request.args.get("month", type=int)
    if month:
        query_obj = query_obj.filter(Paper.submitted_month == month)

    # Absolute date range (YYYY-MM-DD)
    date_from = (request.args.get("date_from") or "").strip()
    date_to = (request.args.get("date_to") or "").strip()
    if date_from:
        df = _parse_date_str(date_from)
        if df:
            query_obj = query_obj.filter(or_(
                Paper.submitted_year > df[0],
                and_(Paper.submitted_year == df[0], Paper.submitted_month > df[1]),
                and_(Paper.submitted_year == df[0],
                     Paper.submitted_month == df[1],
                     Paper.submitted_day >= df[2]),
            ))
    if date_to:
        dt = _parse_date_str(date_to)
        if dt:
            query_obj = query_obj.filter(or_(
                Paper.submitted_year < dt[0],
                and_(Paper.submitted_year == dt[0], Paper.submitted_month < dt[1]),
                and_(Paper.submitted_year == dt[0],
                     Paper.submitted_month == dt[1],
                     Paper.submitted_day <= dt[2]),
            ))

    # Last N days (relative to max announce date in DB to avoid "no recent papers" issues)
    last_days = request.args.get("last_days", type=int)
    if last_days is not None and last_days > 0:
        ref = _latest_announce_tuple()
        if ref:
            # Compute cutoff by converting to ordinal
            import datetime as _dt
            ref_date = _dt.date(*ref)
            cutoff = ref_date - timedelta(days=last_days - 1)
            query_obj = query_obj.filter(or_(
                Paper.submitted_year > cutoff.year,
                and_(Paper.submitted_year == cutoff.year,
                     Paper.submitted_month > cutoff.month),
                and_(Paper.submitted_year == cutoff.year,
                     Paper.submitted_month == cutoff.month,
                     Paper.submitted_day >= cutoff.day),
            ))

    # Minimum number of authors
    min_authors = request.args.get("min_authors", type=int)
    if min_authors is not None:
        query_obj = query_obj.filter(Paper.n_authors >= min_authors)
    max_authors = request.args.get("max_authors", type=int)
    if max_authors is not None:
        query_obj = query_obj.filter(Paper.n_authors <= max_authors)

    # Journal ref substring
    journal_ref = (request.args.get("journal_ref") or "").strip()
    if journal_ref:
        query_obj = query_obj.filter(Paper.journal_ref.ilike(f"%{journal_ref}%"))

    # Author substring (searches authors_json)
    author = (request.args.get("author") or "").strip()
    if author:
        query_obj = query_obj.filter(Paper.authors_json.ilike(f"%{author}%"))

    # HTML availability
    if request.args.get("html") == "1":
        query_obj = query_obj.filter(Paper.html_available == True)

    return query_obj


def _latest_announce_tuple():
    """Return (year, month, day) of the most recent paper in the DB."""
    p = (Paper.query
         .filter(Paper.submitted_year > 0)
         .order_by(Paper.submitted_year.desc(),
                   Paper.submitted_month.desc(),
                   Paper.submitted_day.desc())
         .first())
    if not p:
        return None
    return (p.submitted_year, p.submitted_month, p.submitted_day)


def _apply_paper_sort(results: list, sort_key: str) -> list:
    if sort_key in ("date", "newest", "submitted_desc", "recent"):
        return sorted(
            results,
            key=lambda p: (p.submitted_year, p.submitted_month, p.submitted_day, p.arxiv_id),
            reverse=True,
        )
    if sort_key in ("date_asc", "oldest", "submitted_asc"):
        return sorted(
            results,
            key=lambda p: (p.submitted_year, p.submitted_month, p.submitted_day, p.arxiv_id),
        )
    if sort_key == "views":
        return sorted(results, key=lambda p: p.view_count, reverse=True)
    if sort_key == "stars":
        return sorted(results, key=lambda p: p.star_count, reverse=True)
    return results


# =======================================================================
# ROUTES — PUBLIC PAGES
# =======================================================================

_HOMEPAGE_GROUPS = [
    ("Physics", [
        "astro-ph", "cond-mat", "gr-qc", "hep-ex", "hep-lat", "hep-ph",
        "hep-th", "math-ph", "nlin", "nucl-ex", "nucl-th", "physics", "quant-ph",
    ]),
    ("Mathematics", ["math"]),
    ("Computer Science", ["cs"]),
    ("Quantitative Biology", ["q-bio"]),
    ("Quantitative Finance", ["q-fin"]),
    ("Statistics", ["stat"]),
    ("Electrical Engineering and Systems Science", ["eess"]),
    ("Economics", ["econ"]),
]

_HOMEPAGE_ARCHIVE_NAMES = {
    "astro-ph":  "Astrophysics",
    "cond-mat":  "Condensed Matter",
    "gr-qc":     "General Relativity and Quantum Cosmology",
    "hep-ex":    "High Energy Physics - Experiment",
    "hep-lat":   "High Energy Physics - Lattice",
    "hep-ph":    "High Energy Physics - Phenomenology",
    "hep-th":    "High Energy Physics - Theory",
    "math-ph":   "Mathematical Physics",
    "nlin":      "Nonlinear Sciences",
    "nucl-ex":   "Nuclear Experiment",
    "nucl-th":   "Nuclear Theory",
    "physics":   "Physics",
    "quant-ph":  "Quantum Physics",
    "math":      "Mathematics",
    "cs":        "Computing Research Repository",
    "q-bio":     "Quantitative Biology",
    "q-fin":     "Quantitative Finance",
    "stat":      "Statistics",
    "eess":      "Electrical Engineering and Systems Science",
    "econ":      "Economics",
}


def _build_homepage_directory():
    cat_path = BASE_DIR / "categories.json"
    subs_map = {}
    if cat_path.exists():
        try:
            subs_map = json.load(open(cat_path)).get("subcategories", {})
        except Exception:
            subs_map = {}
    sub_by_archive = {}
    for sub_code, sub_name in subs_map.items():
        parent = sub_code.split(".")[0] if "." in sub_code else sub_code
        sub_by_archive.setdefault(parent, []).append((sub_code, sub_name))
    for parent in sub_by_archive:
        sub_by_archive[parent].sort(key=lambda x: x[0])

    cat_codes = {c.code for c in Category.query.all()}
    groups = []
    for header, codes in _HOMEPAGE_GROUPS:
        items = []
        for code in codes:
            if code not in cat_codes:
                continue
            items.append({
                "code": code,
                "name": _HOMEPAGE_ARCHIVE_NAMES.get(code, code),
                "subs": sub_by_archive.get(code, []),
            })
        if items:
            groups.append({"header": header, "archives": items})
    return groups


@app.route("/")
def index():
    total_papers = Paper.query.count()
    groups = _build_homepage_directory()
    return render_template(
        "index.html",
        total_papers=total_papers,
        groups=groups,
    )


@app.route("/category/<code>")
@app.route("/archive/<code>")
def category_detail(code):
    cat = get_category_or_404(code)
    page = max(1, int(request.args.get("page", 1)))
    papers, total = get_papers_for_category(code, page=page, per_page=25)
    # Subcategory aggregates
    subcat_codes = {}
    all_in_cat = Paper.query.filter(
        or_(Paper.primary_subject_code == code,
            Paper.primary_subject_code.like(f"{code}.%"),
            Paper.primary_category_code == code)
    ).all()
    for p in all_in_cat:
        k = p.primary_subject_code or code
        subcat_codes[k] = subcat_codes.get(k, 0) + 1
    sorted_subs = sorted(subcat_codes.items(), key=lambda x: -x[1])
    return render_template(
        "category.html",
        category=cat,
        papers=papers,
        total=total,
        page=page,
        per_page=25,
        subcat_counts=sorted_subs,
    )


#: Cross-listing aliases — codes that should surface papers filed under a
#: different primary subject on real arxiv.org. Extend as needed.
CATEGORY_ALIASES = {
    "cs.SY": ["eess.SY"],
    "eess.SY": ["cs.SY"],
    "cs.NA": ["math.NA"],
    "math.NA": ["cs.NA"],
    "stat.ML": ["cs.LG"],
}


@app.route("/list/<code>/<view>")
def listing(code, view):
    """arxiv-style listing: /list/cs.AI/recent or /list/cs.AI/new"""
    # Find category by code (allow subcategory codes too)
    cat_code = code.split(".")[0] if "." in code else code
    cat = Category.query.filter_by(code=cat_code).first()
    if not cat:
        # Try the alias target's parent category so e.g. cs.SY still renders
        # the eess header when the cs archive has no record of cs.SY.
        aliases = CATEGORY_ALIASES.get(code, [])
        for a in aliases:
            a_parent = a.split(".")[0] if "." in a else a
            cat = Category.query.filter_by(code=a_parent).first()
            if cat:
                break
        if not cat:
            abort(404)
    page = max(1, int(request.args.get("page", 1)))
    per_page = int(request.args.get("per_page", 25))

    # Build filter: primary/secondary code match plus any cross-listed aliases.
    alias_codes = CATEGORY_ALIASES.get(code, [])
    clauses = [
        Paper.primary_subject_code == code,
        Paper.primary_subject_code.like(f"{code}.%"),
        Paper.primary_category_code == code,
        Paper.subjects.ilike(f"%({code})%"),
    ]
    for a in alias_codes:
        clauses.append(Paper.primary_subject_code == a)
        clauses.append(Paper.subjects.ilike(f"%({a})%"))
    q = Paper.query.filter(or_(*clauses))

    # Order: prefer papers with non-empty abstract first so the listing
    # always surfaces rich content at the top, then newest-first.
    q = q.order_by(
        (Paper.abstract == "").asc(),
        Paper.submitted_year.desc(),
        Paper.submitted_month.desc(),
        Paper.submitted_day.desc(),
        Paper.arxiv_id.desc(),
    )
    total = q.count()
    papers = q.offset((page - 1) * per_page).limit(per_page).all()

    # Group papers by announce_date (submitted_y/m/d) for "/new" views so the
    # template can render a "Day, DD Mon YYYY (N new submissions)" header like
    # the real arxiv.org listing pages.
    grouped = []
    if papers:
        import datetime as _dt
        current_key = None
        current_bucket = None
        for p in papers:
            key = (p.submitted_year, p.submitted_month, p.submitted_day)
            if key != current_key:
                try:
                    d = _dt.date(key[0], key[1], key[2])
                    label = d.strftime("%a, %-d %b %Y")
                except Exception:
                    label = f"{key[0]:04d}-{key[1]:02d}-{key[2]:02d}"
                current_bucket = {"label": label, "key": key, "papers": []}
                grouped.append(current_bucket)
                current_key = key
            current_bucket["papers"].append(p)
        # Add counts
        for g in grouped:
            g["count"] = len(g["papers"])

    return render_template(
        "listing.html",
        category=cat,
        subject_code=code,
        view=view,
        papers=papers,
        grouped=grouped,
        total=total,
        page=page,
        per_page=per_page,
    )


@app.route("/abs/<arxiv_id>")
def paper_detail(arxiv_id):
    paper = Paper.query.filter_by(arxiv_id=arxiv_id).first_or_404()
    paper.view_count += 1
    db.session.commit()
    # Related: same primary category, different paper
    related = (Paper.query
               .filter(Paper.primary_category_code == paper.primary_category_code,
                       Paper.id != paper.id)
               .order_by(func.random()).limit(6).all())
    # Comments
    comments = (Comment.query.filter_by(paper_id=paper.id)
                .order_by(Comment.created_at.desc()).all())
    # Is in library / starred?
    in_library = False
    is_starred = False
    is_notified = False
    if current_user.is_authenticated:
        in_library = LibraryItem.query.filter_by(
            user_id=current_user.id, paper_id=paper.id).first() is not None
        is_starred = StarredPaper.query.filter_by(
            user_id=current_user.id, paper_id=paper.id).first() is not None
        is_notified = PaperUpdateNotification.query.filter_by(
            user_id=current_user.id, paper_id=paper.id).first() is not None
    # R6 — resolve a "replaced by newer version" pointer when present. If the
    # target arxiv_id doesn't exist in the corpus the pointer is still shown
    # but flagged as "not yet ingested".
    replacement_target = None
    replacement_id = paper.replaced_by_arxiv_id
    if replacement_id:
        replacement_target = Paper.query.filter_by(
            arxiv_id=replacement_id).first()
    return render_template(
        "paper.html",
        paper=paper,
        related=related,
        comments=comments,
        in_library=in_library,
        is_starred=is_starred,
        is_notified=is_notified,
        replacement_target=replacement_target,
        replacement_id=replacement_id,
    )


LOCAL_PAPERS_DIR = BASE_DIR / "static" / "papers"


@app.route("/pdf/<arxiv_id>")
def pdf_view(arxiv_id):
    paper = Paper.query.filter_by(arxiv_id=arxiv_id).first_or_404()
    paper.download_count += 1
    db.session.commit()
    local = LOCAL_PAPERS_DIR / f"{paper.arxiv_id}.pdf"
    if local.exists():
        return send_from_directory(
            LOCAL_PAPERS_DIR, f"{paper.arxiv_id}.pdf",
            mimetype="application/pdf",
        )
    return redirect(f"https://arxiv.org/pdf/{paper.arxiv_id}", code=302)


@app.route("/html/<arxiv_id>")
def html_view(arxiv_id):
    paper = Paper.query.filter_by(arxiv_id=arxiv_id).first_or_404()
    local = LOCAL_PAPERS_DIR / f"{paper.arxiv_id}.html"
    if local.exists():
        return send_from_directory(
            LOCAL_PAPERS_DIR, f"{paper.arxiv_id}.html",
            mimetype="text/html",
        )
    return redirect(f"https://arxiv.org/html/{paper.arxiv_id}", code=302)


@app.route("/e-print/<arxiv_id>")
def eprint_view(arxiv_id):
    paper = Paper.query.filter_by(arxiv_id=arxiv_id).first_or_404()
    return redirect(f"https://arxiv.org/e-print/{paper.arxiv_id}", code=302)


@app.route("/format/<arxiv_id>")
def format_view(arxiv_id):
    paper = Paper.query.filter_by(arxiv_id=arxiv_id).first_or_404()
    return redirect(f"https://arxiv.org/format/{paper.arxiv_id}", code=302)


@app.route("/category_taxonomy")
def category_taxonomy():
    # Load subcategory map from JSON
    cat_path = BASE_DIR / "categories.json"
    subs = {}
    if cat_path.exists():
        subs = json.load(open(cat_path))["subcategories"]
    # Group by parent code
    grouped = {}
    for sub_code, sub_name in subs.items():
        parent = sub_code.split(".")[0] if "." in sub_code else sub_code
        grouped.setdefault(parent, []).append((sub_code, sub_name))
    for parent in grouped:
        grouped[parent].sort()
    categories = Category.query.order_by(Category.code).all()
    return render_template("taxonomy.html", categories=categories, grouped=grouped)


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/external/cornell")
def external_cornell():
    """Local stub page about Cornell University (the institution that hosts
    arXiv). Used by the /about page so agents can visit a 'Cornell website'
    without leaving the sandbox."""
    return render_template("external_cornell.html")


@app.route("/news")
def news():
    """arXiv News page — latest announcements and press."""
    items = [
        {
            "date": "2026-04-05",
            "title": "arXiv reaches 3 million submissions",
            "body": ("Today marks a major milestone for arXiv: more than three million "
                     "scholarly articles have been submitted to the archive since it was "
                     "founded in 1991. Thank you to every researcher, moderator, and "
                     "volunteer who has contributed."),
        },
        {
            "date": "2026-03-22",
            "title": "New machine learning categories announced",
            "body": ("In response to rapid growth in AI research, arXiv is introducing "
                     "two new subcategories under Computer Science (cs) to help authors "
                     "better classify foundation-model and agent research."),
        },
        {
            "date": "2026-03-01",
            "title": "HTML rendering now available for most new submissions",
            "body": ("HTML5 versions of newly submitted papers are now generated "
                     "automatically for LaTeX sources, making papers easier to read on "
                     "mobile devices and more accessible for screen readers."),
        },
        {
            "date": "2026-02-10",
            "title": "arXiv non-profit store reopened",
            "body": ("Our non-profit store is back, featuring T-shirts, mugs, and tote "
                     "bags. All proceeds support arXiv's open-access mission."),
        },
    ]
    return render_template("news.html", items=items)


@app.route("/store")
def store():
    """arXiv non-profit store — merchandise."""
    products = [
        {
            "slug": "arxiv-logo-shirt",
            "name": "arXiv Logo Shirt",
            "price": 22.00,
            "category": "Apparel",
            "description": "Classic crewneck t-shirt featuring the arXiv wordmark.",
            "styles": ["Unisex short sleeve", "Women's short sleeve",
                       "Unisex long sleeve", "Women's long sleeve"],
        },
        {
            "slug": "arxiv-forever-short-sleeve",
            "name": "arXiv Forever Short Sleeve",
            "price": 24.00,
            "category": "Apparel",
            "description": "'arXiv Forever' graphic tee — unisex short sleeve.",
            "styles": ["Unisex XS", "Unisex S", "Unisex M",
                       "Unisex L", "Unisex XL", "Unisex XXL"],
        },
        {
            "slug": "arxiv-ceramic-mug",
            "name": "arXiv Ceramic Mug",
            "price": 12.00,
            "category": "Drinkware",
            "description": "11oz ceramic mug with the arXiv logo on both sides.",
            "styles": ["White", "Black"],
        },
        {
            "slug": "arxiv-tote-bag",
            "name": "arXiv Canvas Tote Bag",
            "price": 14.00,
            "category": "Bags",
            "description": "Heavy cotton tote with the arXiv wordmark.",
            "styles": ["Natural"],
        },
        {
            "slug": "arxiv-sticker-pack",
            "name": "arXiv Sticker Pack",
            "price": 4.00,
            "category": "Stickers",
            "description": "Pack of 5 vinyl stickers.",
            "styles": ["Pack of 5"],
        },
        {
            "slug": "arxiv-hoodie",
            "name": "arXiv Hoodie",
            "price": 42.00,
            "category": "Apparel",
            "description": "Pullover hoodie with embroidered arXiv logo.",
            "styles": ["S", "M", "L", "XL", "XXL"],
        },
        {
            "slug": "arxiv-notebook",
            "name": "arXiv Dot Grid Notebook",
            "price": 10.00,
            "category": "Stationery",
            "description": "Hardcover dot-grid notebook.",
            "styles": ["A5"],
        },
    ]
    return render_template("store.html", products=products)


@app.route("/store/<slug>")
def store_item(slug):
    from flask import abort as _abort
    all_items = store.__wrapped__() if hasattr(store, "__wrapped__") else None  # not used
    # simple lookup
    for item in [
        {"slug": "arxiv-logo-shirt", "name": "arXiv Logo Shirt",
         "price": 22.00, "styles": ["Unisex short sleeve", "Women's short sleeve",
                                    "Unisex long sleeve", "Women's long sleeve"]},
        {"slug": "arxiv-forever-short-sleeve", "name": "arXiv Forever Short Sleeve",
         "price": 24.00, "styles": ["Unisex XS", "Unisex S", "Unisex M",
                                    "Unisex L", "Unisex XL", "Unisex XXL"]},
        {"slug": "arxiv-ceramic-mug", "name": "arXiv Ceramic Mug",
         "price": 12.00, "styles": ["White", "Black"]},
    ]:
        if item["slug"] == slug:
            return render_template("store_item.html", item=item)
    _abort(404)


@app.route("/blog")
def blog():
    """arXiv Blog index."""
    posts = [
        {
            "slug": "open-access-2026",
            "title": "Open Access in 2026: What's Next for arXiv",
            "date": "2026-04-02",
            "author": "arXiv Editorial Team",
            "excerpt": ("We reflect on 35 years of open access to research and share our "
                        "roadmap for the next decade of arXiv."),
            "body": ("Open access is the cornerstone of arXiv. Over the next five years, "
                     "we will expand HTML rendering, add new subject areas, and deepen our "
                     "partnerships with libraries worldwide. This post lays out the "
                     "technical and policy goals we are pursuing to keep arXiv fast, "
                     "reliable, and truly free for every researcher."),
        },
        {
            "slug": "html-rendering-launch",
            "title": "HTML Rendering Launches for All New Submissions",
            "date": "2026-03-01",
            "author": "arXiv Engineering",
            "excerpt": ("Starting today, LaTeX-based submissions are rendered to HTML5 "
                        "automatically. Here's how it works."),
            "body": ("HTML5 rendering brings arXiv papers to mobile devices and assistive "
                     "technologies for the first time. We use a custom LaTeXML pipeline."),
        },
        {
            "slug": "moderation-transparency",
            "title": "Transparency in Moderation",
            "date": "2026-02-14",
            "author": "arXiv Moderation",
            "excerpt": ("How we make moderation decisions and why we publish summary "
                        "statistics every quarter."),
            "body": ("Moderation at arXiv is a balance between scholarly rigor and open "
                     "access. This post explains our process."),
        },
    ]
    return render_template("blog.html", posts=posts)


@app.route("/blog/<slug>")
def blog_post(slug):
    posts = {
        "open-access-2026": {
            "slug": "open-access-2026",
            "title": "Open Access in 2026: What's Next for arXiv",
            "date": "2026-04-02",
            "author": "arXiv Editorial Team",
            "body": ("Open access is the cornerstone of arXiv. Over the next five years, "
                     "we will expand HTML rendering, add new subject areas, and deepen our "
                     "partnerships with libraries worldwide. This post lays out the "
                     "technical and policy goals we are pursuing to keep arXiv fast, "
                     "reliable, and truly free for every researcher."),
        },
        "html-rendering-launch": {
            "slug": "html-rendering-launch",
            "title": "HTML Rendering Launches for All New Submissions",
            "date": "2026-03-01",
            "author": "arXiv Engineering",
            "body": ("HTML5 rendering brings arXiv papers to mobile devices and assistive "
                     "technologies for the first time."),
        },
        "moderation-transparency": {
            "slug": "moderation-transparency",
            "title": "Transparency in Moderation",
            "date": "2026-02-14",
            "author": "arXiv Moderation",
            "body": ("Moderation at arXiv is a balance between scholarly rigor and open "
                     "access."),
        },
    }
    post = posts.get(slug)
    if not post:
        abort(404)
    return render_template("blog_post.html", post=post)


@app.route("/help")
def help_page():
    return render_template("help.html")


@app.route("/help/<page>")
def help_page_sub(page):
    return render_template("help.html", section=page)


@app.route("/search/")
@app.route("/search")
def search():
    q = (request.args.get("query") or request.args.get("q") or "").strip()
    field = request.args.get("searchtype", "all")
    page = max(1, int(request.args.get("page", 1)))
    per_page = 25

    # Start with all papers + structural filters
    query_obj = Paper.query
    query_obj = _apply_paper_filters(query_obj)
    candidates = query_obj.all()

    results = candidates
    if q:
        tokens = _tokenize_query(q)
        if field == "title":
            # strict substring on title when field=title, but also allow phrase-level match
            phrase = q.lower()
            results = [p for p in candidates if phrase in (p.title or "").lower()]
        elif field == "author":
            phrase = q.lower()
            results = [p for p in candidates if phrase in (p.authors_json or "").lower()]
        elif field == "abstract":
            phrase = q.lower()
            results = [p for p in candidates if phrase in (p.abstract or "").lower()]
        elif field == "id":
            phrase = q.lower()
            results = [p for p in candidates if phrase in (p.arxiv_id or "").lower()]
        elif field == "journal_ref":
            phrase = q.lower()
            results = [p for p in candidates if phrase in (p.journal_ref or "").lower()]
        else:  # all — scored relevance
            if tokens:
                min_required = max(1, len(tokens) // 2)
                scored = []
                for p in candidates:
                    s = _score_paper(p, tokens)
                    if s >= min_required:
                        scored.append((s, p))
                scored.sort(key=lambda x: -x[0])
                results = [p for _, p in scored]
            else:
                results = candidates

    # Apply sort if requested
    sort_key = request.args.get("sort", "").strip()
    results = _apply_paper_sort(results, sort_key)

    total = len(results)
    paged = results[(page - 1) * per_page: page * per_page]

    # R6 — when a query returned nothing, compute "suggest-broader" hints so
    # the no-results page can offer concrete next steps. Three ideas: drop
    # the most-restrictive token, switch field=all, and recommend the top
    # category whose titles do contain any of the tokens.
    broader_suggestions = []
    if q and total == 0:
        toks = _tokenize_query(q)
        if len(toks) > 1:
            broader_suggestions.append({
                "label": f"Broaden to just \"{toks[0]}\"",
                "url": url_for("search", query=toks[0], searchtype=field),
            })
        if field != "all":
            broader_suggestions.append({
                "label": "Search all fields instead of just " + field,
                "url": url_for("search", query=q, searchtype="all"),
            })
        # Find a category whose papers mention at least one token in title.
        cand_cat = None
        if toks:
            for tok in toks:
                row = (db.session.query(Paper.primary_category_code,
                                        func.count(Paper.id))
                       .filter(Paper.title.ilike(f"%{tok}%"))
                       .filter(Paper.primary_category_code != "")
                       .group_by(Paper.primary_category_code)
                       .order_by(func.count(Paper.id).desc())
                       .first())
                if row and row[0]:
                    cand_cat = row[0]
                    break
        if cand_cat:
            broader_suggestions.append({
                "label": f"Browse the {cand_cat} archive",
                "url": url_for("category_detail", code=cand_cat),
            })
        broader_suggestions.append({
            "label": "Open the advanced search form",
            "url": url_for("advanced_search"),
        })

    return render_template(
        "search.html",
        query=q, field=field, results=paged, total=total, page=page, per_page=per_page,
        broader_suggestions=broader_suggestions,
    )


@app.route("/search/advanced", methods=["GET", "POST"])
def advanced_search():
    if request.method == "POST":
        terms = (request.form.get("terms") or "").strip()
        field = (request.form.get("field") or "all").strip()
        subject = (request.form.get("subject") or request.form.get("category")
                   or "").strip()
        date_range = (request.form.get("date_range") or "").strip()
        sort_key = (request.form.get("sort") or "").strip()
        start_date = (request.form.get("start_date") or "").strip()
        end_date = (request.form.get("end_date") or "").strip()

        params = {"query": terms}
        # Forward field as the backend-native `searchtype` (advanced-search
        # dropdown uses `field`; /search reads `searchtype`). Keep `field` too
        # for compatibility with templates that echo the current selection.
        if field and field != "all":
            params["searchtype"] = field
            params["field"] = field
        if subject:
            params["category"] = subject
        # Map date_range dropdown values to last_days for /search
        if date_range:
            dr_days = {
                "past_2_days": 2,
                "past_week": 7, "week": 7,
                "past_month": 30, "month": 30,
                "past_year": 365, "year": 365,
            }.get(date_range)
            if dr_days:
                params["last_days"] = dr_days
            else:
                params["date_range"] = date_range
        if start_date:
            params["date_from"] = start_date
        if end_date:
            params["date_to"] = end_date
        # Sort: advanced form may pass "relevance" (default), "date" (newest),
        # "date_asc" (oldest), etc. Only forward meaningful sort keys.
        if sort_key and sort_key != "relevance":
            params["sort"] = sort_key
        return redirect(url_for("search", **params))

    # GET: render form. Build a list of subcategory choices so the Subject
    # dropdown can offer fine-grained options (astro-ph.EP, cs.CL, ...) in
    # addition to the main archive codes.
    subcat_path = BASE_DIR / "categories.json"
    subcategories = []
    try:
        if subcat_path.exists():
            subs = json.load(open(subcat_path)).get("subcategories", {})
            # Sort by parent archive, then subcode
            for code, name in sorted(subs.items()):
                if "." in code:
                    subcategories.append({"code": code, "name": name})
    except Exception:
        subcategories = []
    return render_template(
        "advanced_search.html",
        subcategories=subcategories,
    )


@app.route("/author/<path:name>")
def author_papers(name):
    papers = (Paper.query.filter(Paper.authors_json.ilike(f'%{name}%'))
              .order_by(Paper.arxiv_id.desc()).limit(50).all())
    avatar_filename = _avatar_filename(name)
    return render_template("author.html", name=name, papers=papers,
                           avatar_filename=avatar_filename)


# -----------------------------------------------------------------------
# R3 — extra arxiv-style sub-pages
# -----------------------------------------------------------------------

# Mapping of arxiv "group" codes (used in /find/grp_<group>) to the set of
# primary archive codes that compose the group, matching the real
# arxiv.org grouping.
GROUP_TO_ARCHIVES = {
    "cs": ["cs"],
    "math": ["math", "math-ph"],
    "physics": [
        "physics", "astro-ph", "cond-mat", "gr-qc", "hep-ex", "hep-lat",
        "hep-ph", "hep-th", "math-ph", "nlin", "nucl-ex", "nucl-th",
        "quant-ph",
    ],
    "q-bio": ["q-bio"],
    "q-fin": ["q-fin"],
    "stat": ["stat"],
    "eess": ["eess"],
    "econ": ["econ"],
}


@app.route("/year/<int:year>")
@app.route("/year/<int:year>/<code>")
def year_index(year, code=None):
    """Browse papers submitted in a given year, optionally filtered by archive.

    Mirrors real arxiv.org /year/<archive>/<YY> style pages — useful for
    timeline browsing and citation harvesting.
    """
    q = Paper.query.filter(Paper.submitted_year == year)
    if code:
        clauses = [
            Paper.primary_subject_code == code,
            Paper.primary_subject_code.like(f"{code}.%"),
            Paper.primary_category_code == code,
        ]
        q = q.filter(or_(*clauses))
    by_month = {}
    for p in q.all():
        by_month.setdefault(p.submitted_month or 0, []).append(p)
    # Stable order: month asc, then arxiv_id desc inside
    months = []
    for mnum in sorted(by_month.keys()):
        plist = sorted(by_month[mnum], key=lambda x: x.arxiv_id or "",
                       reverse=True)
        months.append({
            "month_num": mnum,
            "month_label": (datetime(year, mnum or 1, 1).strftime("%B")
                            if mnum else "Unknown"),
            "papers": plist[:60],   # cap so the page stays scannable
            "total": len(plist),
        })
    total = sum(m["total"] for m in months)
    return render_template(
        "year.html",
        year=year,
        archive_code=code,
        months=months,
        total=total,
    )


@app.route("/catchup")
@app.route("/catchup/<code>")
def catchup(code=None):
    """Catch-up listing: show papers from the last N days within a category.

    Mirrors arxiv.org/catchup. The window is configurable via ?days=N
    (defaults to 7). Picks "latest available" date as the anchor so the
    page is meaningful even when the seed DB's most-recent paper isn't
    today.
    """
    days = int(request.args.get("days", 7))
    days = max(1, min(days, 60))
    # Reuse the cached anchor populated by inject_globals — both this view
    # and inject_globals run per request, but inject_globals fires first
    # via the context processor pipeline so the cache is warm by here.
    anchor_date = _ARXIV_MIRROR_TODAY_CACHE
    if anchor_date is None:
        anchor_date = (db.session.query(func.max(Paper.submitted_date)).scalar()
                       or "")
    # Build "from" date string for filtering
    try:
        anchor = datetime.strptime(anchor_date, "%Y-%m-%d")
    except Exception:
        anchor = MIRROR_REFERENCE_DATE
    from_dt = anchor - timedelta(days=days)
    from_iso = from_dt.strftime("%Y-%m-%d")
    q = Paper.query.filter(Paper.submitted_date >= from_iso)
    if code:
        clauses = [
            Paper.primary_subject_code == code,
            Paper.primary_subject_code.like(f"{code}.%"),
            Paper.primary_category_code == code,
        ]
        q = q.filter(or_(*clauses))
    q = q.order_by(Paper.submitted_date.desc(), Paper.arxiv_id.desc())
    total = q.count()
    page = max(1, int(request.args.get("page", 1)))
    per_page = 25
    papers = q.offset((page - 1) * per_page).limit(per_page).all()
    return render_template(
        "catchup.html",
        days=days,
        anchor_date=anchor_date,
        from_iso=from_iso,
        code=code,
        papers=papers,
        total=total,
        page=page,
        per_page=per_page,
    )


@app.route("/find/grp_<group>")
def find_group(group):
    """arxiv-style group landing: /find/grp_cs / grp_physics / grp_math ...

    Lists archives under the requested group together with paper counts
    so the agent can navigate by high-level grouping.
    """
    archives = GROUP_TO_ARCHIVES.get(group)
    if not archives:
        abort(404)
    rows = []
    for arch in archives:
        cat = Category.query.filter_by(code=arch).first()
        n = Paper.query.filter(
            or_(
                Paper.primary_subject_code == arch,
                Paper.primary_subject_code.like(f"{arch}.%"),
                Paper.primary_category_code == arch,
            )
        ).count()
        rows.append({"code": arch, "name": cat.name if cat else arch,
                     "count": n, "icon": cat.icon if cat else "📚"})
    return render_template(
        "find_group.html",
        group=group,
        rows=rows,
        total=sum(r["count"] for r in rows),
    )


@app.route("/a/<path:name>/recent")
def author_recent(name):
    """Per-author RSS-style recent feed: /a/<author>/recent.

    Mirrors arxiv's per-author author-listing convention. Sorted by
    submission date descending so the most recent appears first.
    """
    rows = (Paper.query
            .filter(Paper.authors_json.ilike(f'%{name}%'))
            .order_by(
                Paper.submitted_year.desc(),
                Paper.submitted_month.desc(),
                Paper.submitted_day.desc(),
                Paper.arxiv_id.desc())
            .limit(40).all())
    return render_template("author_recent.html", name=name, papers=rows)


# -----------------------------------------------------------------------
# R4 — deeper sub-pages: monthly archive, MSC2020 listing, trackback,
# related-paper graph, journal-ref search, find_form alias.
# -----------------------------------------------------------------------

@app.route("/list/<code>/<int:year>-<int:month>")
def listing_year_month(code, year, month):
    """Monthly archive: /list/<code>/<YYYY>-<MM>.

    Mirrors arxiv's /list/<archive>/<YYMM> convention. Filters papers by
    archive code (or subject code) and explicit calendar month, sorted
    newest-first within the month.
    """
    if month < 1 or month > 12 or year < 1990 or year > 2100:
        abort(404)
    cat_code = code.split(".")[0] if "." in code else code
    cat = Category.query.filter_by(code=cat_code).first()
    if not cat:
        abort(404)
    clauses = [
        Paper.primary_subject_code == code,
        Paper.primary_subject_code.like(f"{code}.%"),
        Paper.primary_category_code == code,
        Paper.subjects.ilike(f"%({code})%"),
    ]
    q = (Paper.query
         .filter(or_(*clauses))
         .filter(Paper.submitted_year == year)
         .filter(Paper.submitted_month == month)
         .order_by(Paper.submitted_day.desc(), Paper.arxiv_id.desc()))
    total = q.count()
    page = max(1, int(request.args.get("page", 1)))
    per_page = int(request.args.get("per_page", 25))
    papers = q.offset((page - 1) * per_page).limit(per_page).all()
    month_label = datetime(year, month, 1).strftime("%B %Y")
    prev_y, prev_m = (year - 1, 12) if month == 1 else (year, month - 1)
    next_y, next_m = (year + 1, 1) if month == 12 else (year, month + 1)
    return render_template(
        "listing_month.html",
        category=cat, subject_code=code,
        year=year, month=month, month_label=month_label,
        papers=papers, total=total, page=page, per_page=per_page,
        prev_y=prev_y, prev_m=prev_m, next_y=next_y, next_m=next_m,
    )


@app.route("/find_form", methods=["GET", "POST"])
def find_form():
    """Alias for advanced search — arxiv used to expose /find_form."""
    return redirect(url_for("advanced_search"), code=301)


@app.route("/tb/<arxiv_id>")
def trackback(arxiv_id):
    """Trackback ping listing — historically /tb/<arxiv_id> showed external
    sites that have referenced the paper. Synthesised here from a fixed
    referrer table seeded from the arxiv_id digest so every paper has a
    deterministic non-empty trackback list.
    """
    paper = Paper.query.filter_by(arxiv_id=arxiv_id).first_or_404()
    sources = [
        ("Hacker News",            "news.ycombinator.com",   "Discussion thread"),
        ("Reddit /r/MachineLearning", "reddit.com",          "Community post"),
        ("Two Minute Papers",      "youtube.com",            "Video summary"),
        ("AlphaSignal Daily",      "alphasignal.ai",         "Newsletter mention"),
        ("The Gradient",           "thegradient.pub",        "In-depth analysis"),
        ("Papers With Code",       "paperswithcode.com",     "Linked benchmark"),
        ("Import AI Newsletter",   "importai.substack.com",  "Roundup item"),
        ("SemanticScholar Connected Papers", "semanticscholar.org", "Citation graph"),
        ("Stanford NLP Seminar",   "nlp.stanford.edu",       "Reading-group note"),
        ("MIT CSAIL Reading List", "csail.mit.edu",          "Course reading"),
        ("DeepLearning.AI The Batch", "deeplearning.ai",     "Weekly digest"),
        ("ICML 2025 Workshop Wiki","icml.cc",                "Workshop reference"),
    ]
    digest = hashlib.md5(paper.arxiv_id.encode("utf-8")).digest()
    n_pings = 2 + (digest[0] % 6)
    pings = []
    for i in range(n_pings):
        idx = digest[(i * 3) % len(digest)] % len(sources)
        title, host, kind = sources[idx]
        offset_days = 7 + (digest[(i * 5) % len(digest)] % 60)
        ymd = MIRROR_REFERENCE_DATE - timedelta(days=offset_days + i)
        pings.append({
            "title": title,
            "host": host,
            "kind": kind,
            "url": f"https://{host}/discuss/{paper.arxiv_id}/",
            "date": ymd.strftime("%Y-%m-%d"),
        })
    return render_template("trackback.html", paper=paper, pings=pings)


@app.route("/papers/<arxiv_id>/related")
def paper_related(arxiv_id):
    """A standalone related-papers graph page for /abs/<arxiv_id>.

    Buckets related work into three lists:
      - Same primary subject
      - Cross-listed: appears under secondary subjects of this paper
      - Shared authors: papers sharing the lead author's last name
    """
    paper = Paper.query.filter_by(arxiv_id=arxiv_id).first_or_404()
    primary = paper.primary_subject_code or paper.primary_category_code

    same_subj = (Paper.query
                 .filter(Paper.primary_subject_code == primary,
                         Paper.id != paper.id)
                 .order_by(Paper.view_count.desc(), Paper.arxiv_id.desc())
                 .limit(12).all())

    secondary_codes = []
    for s in paper.subject_list:
        m = re.search(r"\(([a-zA-Z\-]+(?:\.[a-zA-Z\-]+)?)\)", s)
        if m:
            code = m.group(1)
            if code != primary:
                secondary_codes.append(code)
    cross_listed = []
    if secondary_codes:
        clauses = [Paper.subjects.ilike(f"%({c})%") for c in secondary_codes[:3]]
        cross_listed = (Paper.query
                        .filter(or_(*clauses))
                        .filter(Paper.id != paper.id)
                        .filter(Paper.primary_subject_code != primary)
                        .order_by(Paper.arxiv_id.desc())
                        .limit(10).all())

    shared_author_papers = []
    first = paper.first_author
    if first:
        last_tok = first.split()[-1] if first.split() else first
        if last_tok and len(last_tok) >= 3:
            shared_author_papers = (
                Paper.query
                .filter(Paper.authors_json.ilike(f"%{last_tok}%"))
                .filter(Paper.id != paper.id)
                .order_by(Paper.arxiv_id.desc())
                .limit(8).all())

    return render_template(
        "paper_related.html",
        paper=paper,
        same_subject=same_subj,
        cross_listed=cross_listed,
        shared_author=shared_author_papers,
        first_author=first,
    )


# ----------------------------------------------------------------- R6
# Citing-list page: a fixed, deterministic list of "papers that cite this
# work". Synthesised on the fly so we never need a citation table — the
# arxiv_id digest picks `citing_count` plausible-looking citing papers from
# adjacent subject codes.

@app.route("/papers/<arxiv_id>/citing-list")
def paper_citing_list(arxiv_id):
    paper = Paper.query.filter_by(arxiv_id=arxiv_id).first_or_404()
    page = max(1, int(request.args.get("page", 1)))
    per_page = 25
    total = paper.citing_count
    primary = paper.primary_subject_code or paper.primary_category_code
    # Anchor pool: same primary subject, different paper. Ordered by arxiv_id
    # desc so the list is stable. We slice the pool by a digest-derived
    # rotation so two papers in the same subject get different "citing"
    # lists.
    pool = (Paper.query
            .filter(Paper.primary_subject_code == primary,
                    Paper.id != paper.id)
            .order_by(Paper.arxiv_id.desc())
            .all())
    if not pool:
        pool = (Paper.query.filter(Paper.id != paper.id)
                .order_by(Paper.arxiv_id.desc())
                .limit(500).all())
    d = paper._digest
    if pool:
        rot = (d[6] << 8 | d[7]) % len(pool)
        ordered = pool[rot:] + pool[:rot]
    else:
        ordered = []
    capped_total = min(total, len(ordered))
    citing_slice = ordered[(page - 1) * per_page: page * per_page]
    # Decorate each row with a deterministic citation-context snippet so the
    # page reads like a citing-list rather than a generic listing.
    context_templates = [
        "cites this work in Section 2 (related work)",
        "cites this work in Section 4 (experimental setup)",
        "extends the method introduced here",
        "compares against the baseline proposed in this paper",
        "uses the dataset released with this paper",
        "cites this paper in the introduction",
        "discusses the limitations identified here",
    ]
    decorated = []
    for i, p in enumerate(citing_slice):
        ctx_idx = (d[(i * 3) % len(d)]) % len(context_templates)
        decorated.append({
            "paper": p,
            "context": context_templates[ctx_idx],
            "venue": (p.journal_ref or "arXiv preprint")[:80],
        })
    return render_template(
        "paper_citing_list.html",
        paper=paper,
        rows=decorated,
        total=capped_total,
        synthetic_total=total,
        page=page,
        per_page=per_page,
    )


@app.route("/papers/<arxiv_id>/authors-also")
def paper_authors_also(arxiv_id):
    """'Authors who also published in <subject>' co-publication page.

    Lists papers in the same primary subject that share *any* author surname
    with the source paper but are not the same paper.
    """
    paper = Paper.query.filter_by(arxiv_id=arxiv_id).first_or_404()
    primary = paper.primary_subject_code or paper.primary_category_code
    authors = paper.get_authors()
    surnames = []
    for a in authors:
        toks = a.strip().split()
        if toks:
            tail = toks[-1]
            if len(tail) >= 3 and tail.isalpha():
                surnames.append(tail)
    if not surnames:
        co_papers = []
    else:
        clauses = [Paper.authors_json.ilike(f"%{s}%") for s in surnames[:4]]
        co_papers = (Paper.query
                     .filter(or_(*clauses))
                     .filter(Paper.primary_subject_code == primary)
                     .filter(Paper.id != paper.id)
                     .order_by(Paper.arxiv_id.desc())
                     .limit(30).all())
    return render_template(
        "paper_authors_also.html",
        paper=paper,
        co_papers=co_papers,
        surnames=surnames,
        primary=primary,
    )


_MSC_FAMILY_LABELS = {
    "00": "General", "01": "History and biography",
    "03": "Mathematical logic and foundations",
    "05": "Combinatorics", "06": "Order, lattices",
    "08": "General algebraic systems",
    "11": "Number theory", "12": "Field theory",
    "13": "Commutative algebra", "14": "Algebraic geometry",
    "15": "Linear and multilinear algebra",
    "16": "Associative rings and algebras",
    "17": "Nonassociative rings", "18": "Category theory",
    "19": "K-theory", "20": "Group theory",
    "22": "Topological groups", "26": "Real functions",
    "28": "Measure and integration",
    "30": "Functions of a complex variable",
    "31": "Potential theory", "32": "Several complex variables",
    "33": "Special functions", "34": "Ordinary differential equations",
    "35": "Partial differential equations",
    "37": "Dynamical systems",
    "39": "Difference and functional equations",
    "40": "Sequences, series", "41": "Approximations",
    "42": "Harmonic analysis", "43": "Abstract harmonic analysis",
    "44": "Integral transforms", "45": "Integral equations",
    "46": "Functional analysis", "47": "Operator theory",
    "49": "Calculus of variations and optimal control",
    "51": "Geometry", "52": "Convex and discrete geometry",
    "53": "Differential geometry",
    "54": "General topology", "55": "Algebraic topology",
    "57": "Manifolds and cell complexes",
    "58": "Global analysis", "60": "Probability theory",
    "62": "Statistics", "65": "Numerical analysis",
    "68": "Computer science", "70": "Mechanics of particles",
    "74": "Mechanics of deformable solids",
    "76": "Fluid mechanics", "78": "Optics, electromagnetic theory",
    "80": "Classical thermodynamics, heat transfer",
    "81": "Quantum theory", "82": "Statistical mechanics",
    "83": "Relativity and gravitation",
    "85": "Astronomy and astrophysics",
    "86": "Geophysics", "90": "Operations research",
    "91": "Game theory, economics, social and behavioral sciences",
    "92": "Biology and other natural sciences",
    "93": "Systems theory; control",
    "94": "Information and communication",
    "97": "Mathematics education",
}


@app.route("/MSC2020/<path:msc_class>")
@app.route("/MSC2020/")
@app.route("/MSC2020")
def msc_listing(msc_class=None):
    """Browse papers by Mathematics Subject Classification (MSC2020).

    Index (no class): show top-level MSC family directory.
    Detail (class supplied): list papers whose msc_class column contains it.
    """
    if msc_class is None:
        rows = db.session.query(Paper.msc_class).filter(
            Paper.msc_class != "").all()
        counts = {}
        for (mc,) in rows:
            for fam in re.findall(r"\b(\d{2})[A-Z]\d{2}", mc or ""):
                counts[fam] = counts.get(fam, 0) + 1
        families = []
        for fam, n in sorted(counts.items(), key=lambda x: (-x[1], x[0])):
            families.append({
                "code": fam,
                "label": _MSC_FAMILY_LABELS.get(fam, "(unlabeled)"),
                "count": n,
            })
        return render_template("msc_index.html",
                               families=families,
                               total_papers=sum(c for _, c in counts.items()))
    pattern = f"%{msc_class}%"
    page = max(1, int(request.args.get("page", 1)))
    per_page = 25
    q = (Paper.query.filter(Paper.msc_class.ilike(pattern))
         .order_by(Paper.submitted_year.desc(),
                   Paper.submitted_month.desc(), Paper.arxiv_id.desc()))
    total = q.count()
    papers = q.offset((page - 1) * per_page).limit(per_page).all()
    family_label = _MSC_FAMILY_LABELS.get(msc_class.strip()[:2], "")
    return render_template("msc_class.html",
                           msc_class=msc_class,
                           family_label=family_label,
                           papers=papers,
                           total=total, page=page, per_page=per_page)


# -----------------------------------------------------------------------
# R10 — ACM Computing Classification System (1998 CCS) browse route.
# Mirrors /MSC2020 surface for ACM class strings (e.g. F.2.2, H.3.3, I.2.7).
# -----------------------------------------------------------------------

_ACM_FAMILY_LABELS = {
    "A": "General Literature",
    "B": "Hardware",
    "C": "Computer Systems Organization",
    "D": "Software",
    "E": "Data",
    "F": "Theory of Computation",
    "G": "Mathematics of Computing",
    "H": "Information Systems",
    "I": "Computing Methodologies",
    "J": "Computer Applications",
    "K": "Computing Milieux",
}


@app.route("/acm/<path:acm_class>")
@app.route("/acm/")
@app.route("/acm")
def acm_listing(acm_class=None):
    """Browse papers by ACM Computing Classification System (CCS) tag.

    Index (no class): list top-level ACM CCS family directory (A..K).
    Detail (class supplied): list papers whose acm_class column contains it.
    Patterns we recognise: ``F.2``, ``F.2.2``, ``H.3.3``. Filter is a simple
    substring match against the stored acm_class string (which may carry
    multiple comma-separated tags).
    """
    if acm_class is None:
        rows = db.session.query(Paper.acm_class).filter(
            Paper.acm_class != "").all()
        counts = {}
        for (ac,) in rows:
            for fam in re.findall(r"\b([A-K])\.\d", ac or ""):
                counts[fam] = counts.get(fam, 0) + 1
        families = []
        for fam in sorted(_ACM_FAMILY_LABELS):
            families.append({
                "code": fam,
                "label": _ACM_FAMILY_LABELS[fam],
                "count": counts.get(fam, 0),
            })
        return render_template("msc_index.html",
                               families=families,
                               total_papers=sum(counts.values()),
                               scheme_label="ACM CCS (1998)",
                               scheme_endpoint="acm_listing")
    pattern = f"%{acm_class}%"
    page = max(1, int(request.args.get("page", 1)))
    per_page = 25
    q = (Paper.query.filter(Paper.acm_class.ilike(pattern))
         .order_by(Paper.submitted_year.desc(),
                   Paper.submitted_month.desc(), Paper.arxiv_id.desc()))
    total = q.count()
    papers = q.offset((page - 1) * per_page).limit(per_page).all()
    fam_letter = acm_class.strip()[:1].upper()
    family_label = _ACM_FAMILY_LABELS.get(fam_letter, "")
    return render_template("msc_class.html",
                           msc_class=acm_class,
                           family_label=family_label,
                           papers=papers,
                           total=total, page=page, per_page=per_page,
                           scheme_label="ACM CCS",
                           scheme_endpoint="acm_listing")


@app.route("/journal-ref-search", methods=["GET", "POST"])
def journal_ref_search():
    """Browse / search papers by journal-ref string.

    Without a query string: show a directory of the top journal-ref
    prefixes occurring in the corpus.
    With ?q=<term>: list matching papers.
    """
    q = (request.args.get("q") or request.form.get("q") or "").strip()
    page = max(1, int(request.args.get("page", 1)))
    per_page = 25
    if q:
        query = (Paper.query.filter(Paper.journal_ref != "")
                 .filter(Paper.journal_ref.ilike(f"%{q}%"))
                 .order_by(Paper.submitted_year.desc(),
                           Paper.submitted_month.desc(),
                           Paper.arxiv_id.desc()))
        total = query.count()
        papers = query.offset((page - 1) * per_page).limit(per_page).all()
        return render_template("journal_ref_search.html",
                               query=q, papers=papers, total=total,
                               page=page, per_page=per_page,
                               directory=None)
    rows = (db.session.query(Paper.journal_ref)
            .filter(Paper.journal_ref != "").all())
    counts = {}
    for (jr,) in rows:
        m = re.match(r"^([^0-9]+?)(?:\s*\d+|\,|\;|$)", jr or "")
        head = (m.group(1).strip().rstrip(",;") if m else jr).strip()
        if head and 3 <= len(head) <= 60:
            counts[head] = counts.get(head, 0) + 1
    directory = sorted(counts.items(), key=lambda x: (-x[1], x[0]))[:40]
    return render_template("journal_ref_search.html",
                           query="", papers=[], total=0, page=1,
                           per_page=per_page, directory=directory)


# =======================================================================
# ROUTES — AUTHENTICATION
# =======================================================================

@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("index"))
    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        password = request.form.get("password") or ""
        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            login_user(user)
            flash("Welcome back!", "success")
            next_url = request.args.get("next") or url_for("account")
            return redirect(next_url)
        flash("Invalid email or password.", "error")
    return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("index"))
    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        username = (request.form.get("username") or "").strip()
        full_name = (request.form.get("full_name") or "").strip()
        password = request.form.get("password") or ""
        confirm = request.form.get("confirm_password") or ""
        if not (email and username and password):
            flash("Email, username, and password are required.", "error")
            return render_template("register.html")
        if password != confirm:
            flash("Passwords do not match.", "error")
            return render_template("register.html")
        if User.query.filter_by(email=email).first():
            flash("An account with this email already exists.", "error")
            return render_template("register.html")
        if User.query.filter_by(username=username).first():
            flash("This username is taken.", "error")
            return render_template("register.html")
        u = User(email=email, username=username, full_name=full_name)
        u.set_password(password)
        db.session.add(u)
        db.session.commit()
        login_user(u)
        flash("Account created. Welcome to arXiv!", "success")
        return redirect(url_for("account"))
    return render_template("register.html")


@app.route("/logout")
def logout():
    logout_user()
    flash("You have been logged out.", "success")
    return redirect(url_for("index"))


# =======================================================================
# ROUTES — ACCOUNT
# =======================================================================

@app.route("/account")
@login_required
def account():
    recent_library = (LibraryItem.query.filter_by(user_id=current_user.id)
                      .order_by(LibraryItem.added_at.desc()).limit(5).all())
    recent_stars = (StarredPaper.query.filter_by(user_id=current_user.id)
                    .order_by(StarredPaper.starred_at.desc()).limit(5).all())
    exports = (Export.query.filter_by(user_id=current_user.id)
               .order_by(Export.created_at.desc()).all())
    my_comments = (Comment.query.filter_by(user_id=current_user.id)
                   .order_by(Comment.created_at.desc()).limit(10).all())
    alerts = Alert.query.filter_by(user_id=current_user.id).all()
    return render_template(
        "account.html",
        recent_library=recent_library,
        recent_stars=recent_stars,
        exports=exports,
        my_comments=my_comments,
        alerts=alerts,
    )


@app.route("/account/edit", methods=["GET", "POST"])
@login_required
def account_edit():
    if request.method == "POST":
        current_user.full_name = request.form.get("full_name", "").strip()
        current_user.affiliation = request.form.get("affiliation", "").strip()
        current_user.bio = request.form.get("bio", "").strip()
        current_user.orcid = request.form.get("orcid", "").strip()
        db.session.commit()
        flash("Profile updated.", "success")
        return redirect(url_for("account"))
    return render_template("account_edit.html")


@app.route("/account/password", methods=["GET", "POST"])
@login_required
def change_password():
    if request.method == "POST":
        current = request.form.get("current_password") or ""
        new = request.form.get("new_password") or ""
        confirm = request.form.get("confirm_password") or ""
        if not current_user.check_password(current):
            flash("Current password is incorrect.", "error")
        elif new != confirm:
            flash("New passwords do not match.", "error")
        elif len(new) < 6:
            flash("Password must be at least 6 characters.", "error")
        else:
            current_user.set_password(new)
            db.session.commit()
            flash("Password updated.", "success")
            return redirect(url_for("account"))
    return render_template("change_password.html")


@app.route("/account/delete", methods=["POST"])
@login_required
def delete_account():
    uid = current_user.id
    logout_user()
    user = db.session.get(User, uid)
    if user:
        db.session.delete(user)
        db.session.commit()
    flash("Your account has been deleted.", "success")
    return redirect(url_for("index"))


# =======================================================================
# ROUTES — LIBRARY (cart analog)
# =======================================================================

@app.route("/library")
@login_required
def library():
    folder = request.args.get("folder", "")
    q = LibraryItem.query.filter_by(user_id=current_user.id)
    if folder:
        q = q.filter_by(folder=folder)
    items = q.order_by(LibraryItem.added_at.desc()).all()
    folders = (db.session.query(LibraryItem.folder, func.count(LibraryItem.id))
               .filter_by(user_id=current_user.id)
               .group_by(LibraryItem.folder).all())
    return render_template("library.html", items=items, folders=folders, current_folder=folder)


@app.route("/api/library/add", methods=["POST"])
@login_required
@csrf.exempt
def api_library_add():
    data = request.get_json() or {}
    paper_id = int(data.get("paper_id", 0))
    folder = data.get("folder", "Reading List")
    paper = Paper.query.get(paper_id)
    if not paper:
        return jsonify({"success": False, "message": "Paper not found"}), 404
    existing = LibraryItem.query.filter_by(user_id=current_user.id, paper_id=paper_id).first()
    if existing:
        return jsonify({"success": True, "message": "Already in your library",
                        "library_count": LibraryItem.query.filter_by(user_id=current_user.id).count()})
    item = LibraryItem(user_id=current_user.id, paper_id=paper_id, folder=folder)
    db.session.add(item)
    db.session.commit()
    return jsonify({"success": True, "message": "Added to your library",
                    "library_count": LibraryItem.query.filter_by(user_id=current_user.id).count()})


@app.route("/api/library/remove", methods=["POST"])
@login_required
@csrf.exempt
def api_library_remove():
    data = request.get_json() or {}
    item_id = int(data.get("item_id", 0))
    item = LibraryItem.query.filter_by(id=item_id, user_id=current_user.id).first()
    if not item:
        return jsonify({"success": False, "message": "Not found"}), 404
    db.session.delete(item)
    db.session.commit()
    return jsonify({"success": True, "library_count":
                    LibraryItem.query.filter_by(user_id=current_user.id).count()})


@app.route("/api/library/update", methods=["POST"])
@login_required
@csrf.exempt
def api_library_update():
    data = request.get_json() or {}
    item_id = int(data.get("item_id", 0))
    folder = data.get("folder", "Reading List")
    note = data.get("note", "")
    item = LibraryItem.query.filter_by(id=item_id, user_id=current_user.id).first()
    if not item:
        return jsonify({"success": False, "message": "Not found"}), 404
    item.folder = folder
    item.note = note
    db.session.commit()
    return jsonify({"success": True})


@app.route("/library/folder/create", methods=["POST"])
@login_required
def create_folder():
    name = (request.form.get("folder_name") or "").strip()
    paper_id = request.form.get("paper_id")
    if name and paper_id:
        existing = LibraryItem.query.filter_by(user_id=current_user.id, paper_id=int(paper_id)).first()
        if existing:
            existing.folder = name
        else:
            db.session.add(LibraryItem(user_id=current_user.id, paper_id=int(paper_id), folder=name))
        db.session.commit()
    return redirect(request.referrer or url_for("library"))


@app.route("/library/folder/rename", methods=["POST"])
@login_required
def rename_folder():
    """Rename a library folder — updates all items in that folder."""
    old_name = (request.form.get("old_name") or "").strip()
    new_name = (request.form.get("new_name") or "").strip()
    if old_name and new_name and old_name != new_name:
        items = LibraryItem.query.filter_by(
            user_id=current_user.id, folder=old_name
        ).all()
        if items:
            for item in items:
                item.folder = new_name
            db.session.commit()
            flash(f'Folder renamed from "{old_name}" to "{new_name}".', "success")
        else:
            flash(f'No folder named "{old_name}" found.', "error")
    else:
        flash("Please provide both old and new folder names.", "error")
    return redirect(url_for("library"))


# =======================================================================
# ROUTES — STARRED (wishlist analog)
# =======================================================================

@app.route("/starred")
@login_required
def starred_page():
    items = (StarredPaper.query.filter_by(user_id=current_user.id)
             .order_by(StarredPaper.starred_at.desc()).all())
    return render_template("starred.html", items=items)


@app.route("/api/star/toggle", methods=["POST"])
@login_required
@csrf.exempt
def api_star_toggle():
    data = request.get_json() or {}
    paper_id = int(data.get("paper_id", 0))
    paper = Paper.query.get(paper_id)
    if not paper:
        return jsonify({"success": False}), 404
    existing = StarredPaper.query.filter_by(user_id=current_user.id, paper_id=paper_id).first()
    if existing:
        db.session.delete(existing)
        paper.star_count = max(0, paper.star_count - 1)
        action = "removed"
    else:
        db.session.add(StarredPaper(user_id=current_user.id, paper_id=paper_id))
        paper.star_count += 1
        action = "added"
    db.session.commit()
    return jsonify({"success": True, "action": action, "star_count": paper.star_count})


@app.route("/starred/remove/<int:item_id>", methods=["POST"])
@login_required
def starred_remove(item_id):
    item = StarredPaper.query.filter_by(id=item_id, user_id=current_user.id).first_or_404()
    db.session.delete(item)
    db.session.commit()
    flash("Removed from starred.", "success")
    return redirect(url_for("starred_page"))


# =======================================================================
# ROUTES — EXPORTS (order analog)
# =======================================================================

@app.route("/export", methods=["GET", "POST"])
@login_required
def export_create():
    if request.method == "POST":
        fmt = request.form.get("format", "bibtex")
        source = request.form.get("source", "library")
        notes = request.form.get("notes", "")
        paper_ids = []
        if source == "library":
            items = LibraryItem.query.filter_by(user_id=current_user.id).all()
            paper_ids = [i.paper_id for i in items]
        elif source == "starred":
            items = StarredPaper.query.filter_by(user_id=current_user.id).all()
            paper_ids = [i.paper_id for i in items]
        elif source == "selected":
            ids_raw = request.form.get("paper_ids", "")
            paper_ids = [int(x) for x in ids_raw.split(",") if x.strip().isdigit()]
        if not paper_ids:
            flash("No papers selected for export.", "error")
            return redirect(url_for("library"))
        ex = Export(
            user_id=current_user.id,
            export_id=new_export_id(),
            format=fmt,
            status="ready",
            paper_count=len(paper_ids),
            notes=notes,
        )
        db.session.add(ex)
        db.session.flush()
        for pid in paper_ids:
            db.session.add(ExportItem(export_id=ex.id, paper_id=pid))
        db.session.commit()
        flash("Export created.", "success")
        return redirect(url_for("export_detail", export_id=ex.export_id))
    # GET = show form
    library_items = LibraryItem.query.filter_by(user_id=current_user.id).all()
    starred_items = StarredPaper.query.filter_by(user_id=current_user.id).all()
    return render_template("export_create.html",
                           library_items=library_items, starred_items=starred_items)


@app.route("/export/<export_id>")
@login_required
def export_detail(export_id):
    ex = Export.query.filter_by(export_id=export_id, user_id=current_user.id).first_or_404()
    return render_template("export_detail.html", export=ex)


@app.route("/export/<export_id>/cancel", methods=["POST"])
@login_required
def export_cancel(export_id):
    ex = Export.query.filter_by(export_id=export_id, user_id=current_user.id).first_or_404()
    if ex.status == "ready":
        ex.status = "cancelled"
        db.session.commit()
        flash("Export cancelled.", "success")
    else:
        flash("Cannot cancel this export.", "error")
    return redirect(url_for("export_detail", export_id=export_id))


@app.route("/export/<export_id>/download")
@login_required
def export_download(export_id):
    ex = Export.query.filter_by(export_id=export_id, user_id=current_user.id).first_or_404()
    # Generate the text representation in-memory
    papers = [it.paper for it in ex.items if it.paper]
    if ex.format == "bibtex":
        lines = []
        for p in papers:
            key = p.arxiv_id.replace(".", "")
            lines.append("@article{arxiv" + key + ",")
            lines.append(f'  title = {{{p.title}}},')
            lines.append(f'  author = {{{" and ".join(p.get_authors())}}},')
            lines.append('  journal = {arXiv preprint arXiv:' + p.arxiv_id + '},')
            if p.submitted_date:
                lines.append(f'  year = {{{p.submitted_date[:4]}}},')
            lines.append("}")
            lines.append("")
        body = "\n".join(lines)
    elif ex.format == "ris":
        lines = []
        for p in papers:
            lines += ["TY  - JOUR", f"TI  - {p.title}"]
            for a in p.get_authors():
                lines.append(f"AU  - {a}")
            lines += [f"JO  - arXiv:{p.arxiv_id}", f"ID  - {p.arxiv_id}", "ER  - ", ""]
        body = "\n".join(lines)
    else:
        body = "\n\n".join(
            f"{p.title}\n{', '.join(p.get_authors())}\narXiv:{p.arxiv_id}" for p in papers
        )
    from flask import Response
    return Response(body, mimetype="text/plain",
                    headers={"Content-Disposition":
                             f"attachment; filename={ex.export_id}.{ex.format}"})


@app.route("/export/<export_id>/reorder", methods=["POST"])
@login_required
def export_reorder(export_id):
    ex = Export.query.filter_by(export_id=export_id, user_id=current_user.id).first_or_404()
    # Re-add the papers to library
    added = 0
    for it in ex.items:
        if not LibraryItem.query.filter_by(user_id=current_user.id, paper_id=it.paper_id).first():
            db.session.add(LibraryItem(user_id=current_user.id, paper_id=it.paper_id))
            added += 1
    db.session.commit()
    flash(f"Re-added {added} papers to your library.", "success")
    return redirect(url_for("library"))


# =======================================================================
# ROUTES — COMMENTS (review analog)
# =======================================================================

@app.route("/abs/<arxiv_id>/comment", methods=["POST"])
@login_required
def submit_comment(arxiv_id):
    paper = Paper.query.filter_by(arxiv_id=arxiv_id).first_or_404()
    title = (request.form.get("title") or "").strip()[:200]
    body = (request.form.get("body") or "").strip()
    rating = int(request.form.get("rating", 0) or 0)
    if not body:
        flash("Comment body cannot be empty.", "error")
    else:
        db.session.add(Comment(
            user_id=current_user.id, paper_id=paper.id,
            title=title, body=body, rating=max(0, min(5, rating)),
        ))
        db.session.commit()
        flash("Comment posted.", "success")
    return redirect(url_for("paper_detail", arxiv_id=arxiv_id))


@app.route("/comment/<int:comment_id>/delete", methods=["POST"])
@login_required
def delete_comment(comment_id):
    c = Comment.query.get_or_404(comment_id)
    if c.user_id != current_user.id:
        abort(403)
    paper_arxiv = c.paper.arxiv_id
    db.session.delete(c)
    db.session.commit()
    flash("Comment deleted.", "success")
    return redirect(url_for("paper_detail", arxiv_id=paper_arxiv))


# =======================================================================
# ROUTES — ALERTS
# =======================================================================

@app.route("/alerts", methods=["GET", "POST"])
@login_required
def alerts_page():
    if request.method == "POST":
        code = request.form.get("category_code", "").strip()
        freq = request.form.get("frequency", "weekly")
        if code:
            existing = Alert.query.filter_by(user_id=current_user.id, category_code=code).first()
            if existing:
                existing.frequency = freq
                existing.active = True
                flash("Alert updated.", "success")
            else:
                db.session.add(Alert(user_id=current_user.id,
                                     category_code=code, frequency=freq))
                flash("Alert created.", "success")
            db.session.commit()
        return redirect(url_for("alerts_page"))
    user_alerts = Alert.query.filter_by(user_id=current_user.id).all()
    saved_searches = SavedSearch.query.filter_by(
        user_id=current_user.id).order_by(SavedSearch.id.desc()).all()
    return render_template(
        "alerts.html", alerts=user_alerts, saved_searches=saved_searches)


@app.route("/alerts/<int:alert_id>/delete", methods=["POST"])
@login_required
def delete_alert(alert_id):
    alert = Alert.query.filter_by(id=alert_id, user_id=current_user.id).first_or_404()
    db.session.delete(alert)
    db.session.commit()
    flash("Alert removed.", "success")
    return redirect(url_for("alerts_page"))


# =======================================================================
# ROUTES — SAVED SEARCHES + PAPER UPDATE NOTIFICATIONS  (R5)
# =======================================================================

@app.route("/alerts/save_search", methods=["POST"])
@login_required
def save_search():
    """Persist a query+filter pair as a SavedSearch so the user can re-run it
    later and (optionally) get notified when new papers match.
    """
    query = (request.form.get("query") or "").strip()
    field = (request.form.get("field") or request.form.get("searchtype") or "all").strip()
    category = (request.form.get("category") or "").strip()
    frequency = (request.form.get("frequency") or "weekly").strip()
    name = (request.form.get("name") or "").strip() or (query[:60] or "Untitled search")
    if not query and not category:
        flash("Cannot save an empty search.", "error")
        return redirect(request.referrer or url_for("search"))
    db.session.add(SavedSearch(
        user_id=current_user.id,
        name=name,
        query=query,
        field=field,
        category=category,
        frequency=frequency,
    ))
    db.session.commit()
    flash(f"Saved search '{name}' — you'll be notified {frequency}.", "success")
    return redirect(url_for("alerts_page"))


@app.route("/alerts/save_search/<int:saved_id>/delete", methods=["POST"])
@login_required
def delete_saved_search(saved_id):
    s = SavedSearch.query.filter_by(id=saved_id, user_id=current_user.id).first_or_404()
    db.session.delete(s)
    db.session.commit()
    flash("Saved search removed.", "success")
    return redirect(url_for("alerts_page"))


@app.route("/abs/<arxiv_id>/notify", methods=["POST"])
@login_required
def notify_paper_update(arxiv_id):
    """Subscribe current user to update notifications for one specific paper."""
    paper = Paper.query.filter_by(arxiv_id=arxiv_id).first_or_404()
    email = (request.form.get("email") or current_user.email or "").strip()
    existing = PaperUpdateNotification.query.filter_by(
        user_id=current_user.id, paper_id=paper.id).first()
    if existing:
        existing.email = email
        flash(f"Already subscribed — updated email to {email}.", "success")
    else:
        db.session.add(PaperUpdateNotification(
            user_id=current_user.id, paper_id=paper.id, email=email))
        flash(f"You'll be notified at {email} when arXiv:{arxiv_id} has a new version.", "success")
    db.session.commit()
    return redirect(url_for("paper_detail", arxiv_id=arxiv_id))


@app.route("/abs/<arxiv_id>/notify/cancel", methods=["POST"])
@login_required
def notify_paper_cancel(arxiv_id):
    paper = Paper.query.filter_by(arxiv_id=arxiv_id).first_or_404()
    sub = PaperUpdateNotification.query.filter_by(
        user_id=current_user.id, paper_id=paper.id).first()
    if sub:
        db.session.delete(sub)
        db.session.commit()
        flash("Update notification cancelled.", "success")
    return redirect(url_for("paper_detail", arxiv_id=arxiv_id))


# =======================================================================
# ROUTES — API
# =======================================================================

@app.route("/api/papers/<category_code>")
def api_papers(category_code):
    papers, total = get_papers_for_category(category_code, per_page=20)
    return jsonify({
        "category": category_code,
        "total": total,
        "papers": [{
            "arxiv_id": p.arxiv_id,
            "title": p.title,
            "authors": p.get_authors(),
            "abstract": p.short_abstract,
            "subjects": p.subjects,
            "pdf_url": p.pdf_url,
        } for p in papers],
    })


@app.route("/api/stats")
def api_stats():
    return jsonify({
        "total_papers": Paper.query.count(),
        "total_categories": Category.query.count(),
        "total_users": User.query.count(),
        "total_comments": Comment.query.count(),
    })


# =======================================================================
# ERROR HANDLERS
# =======================================================================

@app.errorhandler(404)
def not_found(e):
    # R6 — when the missing URL looks like /abs/<id>, render a richer "paper
    # not found" page that suggests adjacent arxiv_ids in the corpus instead
    # of the generic error page. Agents land here when a /abs/<bogus> link is
    # followed; surfacing nearby ids gives them a recovery path.
    p = request.path or ""
    m = re.match(r"/abs/([^/]+)$", p)
    if m:
        target = m.group(1)
        # Build a "nearby ids" suggestion list using the yymm prefix.
        prefix_match = re.match(r"(\d{4}\.)\d+", target)
        nearby = []
        if prefix_match:
            prefix = prefix_match.group(1)
            nearby = (Paper.query
                      .filter(Paper.arxiv_id.like(f"{prefix}%"))
                      .order_by(Paper.arxiv_id)
                      .limit(8).all())
        return render_template("error.html",
                               code=404,
                               message=f"Paper arXiv:{target} not found",
                               missing_paper=target,
                               nearby=nearby), 404
    return render_template("error.html", code=404, message="Page not found"), 404


@app.errorhandler(500)
def server_error(e):
    return render_template("error.html", code=500, message="Server error"), 500


# =======================================================================
# FORM-BASED (non-AJAX) routes for library + star — needed by browser agents
# =======================================================================

@app.route("/library/add/<int:paper_id>", methods=["POST"])
@login_required
def library_add_form(paper_id):
    """Form-POST equivalent of /api/library/add — redirects back."""
    paper = Paper.query.get_or_404(paper_id)
    folder = request.form.get("folder", "Reading List")
    existing = LibraryItem.query.filter_by(
        user_id=current_user.id, paper_id=paper_id).first()
    if not existing:
        db.session.add(LibraryItem(
            user_id=current_user.id, paper_id=paper_id, folder=folder))
        db.session.commit()
        flash("Added to your library.", "success")
    else:
        flash("Already in your library.", "info")
    return redirect(request.referrer or url_for("paper_detail",
                                                 arxiv_id=paper.arxiv_id))


@app.route("/library/remove/<int:item_id>", methods=["POST"])
@login_required
def library_remove_form(item_id):
    """Form-POST equivalent of /api/library/remove — redirects back."""
    item = LibraryItem.query.filter_by(
        id=item_id, user_id=current_user.id).first_or_404()
    db.session.delete(item)
    db.session.commit()
    flash("Removed from library.", "success")
    return redirect(request.referrer or url_for("library"))


@app.route("/library/move/<int:item_id>", methods=["POST"])
@login_required
def library_move_folder(item_id):
    """Move a library item to a different folder via form POST."""
    item = LibraryItem.query.filter_by(
        id=item_id, user_id=current_user.id).first_or_404()
    new_folder = (request.form.get("folder") or "Reading List").strip()
    item.folder = new_folder
    db.session.commit()
    flash(f'Moved to folder "{new_folder}".', "success")
    return redirect(request.referrer or url_for("library"))


@app.route("/star/toggle/<int:paper_id>", methods=["POST"])
@login_required
def star_toggle_form(paper_id):
    """Form-POST equivalent of /api/star/toggle — redirects back."""
    paper = Paper.query.get_or_404(paper_id)
    existing = StarredPaper.query.filter_by(
        user_id=current_user.id, paper_id=paper_id).first()
    if existing:
        db.session.delete(existing)
        paper.star_count = max(0, paper.star_count - 1)
        flash("Removed from starred.", "success")
    else:
        db.session.add(StarredPaper(user_id=current_user.id, paper_id=paper_id))
        paper.star_count += 1
        flash("Added to starred.", "success")
    db.session.commit()
    return redirect(request.referrer or url_for("paper_detail",
                                                 arxiv_id=paper.arxiv_id))


# =======================================================================
# R7 — SEO, OAI-PMH docs, RSS/Atom listings, DOI resolve, source tarball,
#      citation-batch export, multilingual stubs (/lang/zh, /lang/es).
# All routes are deterministic / stateless — no DB writes. They round out
# the SEO and feed surface so agents can exercise arxiv-shaped tasks
# (sitemap discovery, DOI resolution, OAI-PMH harvesting) entirely inside
# the mirror without leaving for the real arxiv.org.
# =======================================================================

LANG_LABELS = {
    "en": {
        "search": "Search", "advanced_search": "Advanced Search",
        "help": "Help", "news": "News", "blog": "Blog",
        "store": "Store", "login": "Login", "register": "Register",
        "logout": "Logout", "library": "Library",
        "today_on_arxiv": "Today on arXiv",
        "header_banner": "arXiv preprint repository",
        "language_label": "English",
    },
    "zh": {
        "search": "搜索", "advanced_search": "高级搜索",
        "help": "帮助", "news": "新闻", "blog": "博客",
        "store": "商店", "login": "登录", "register": "注册",
        "logout": "退出", "library": "个人书库",
        "today_on_arxiv": "今日 arXiv",
        "header_banner": "arXiv 预印本仓库",
        "language_label": "中文",
    },
    "es": {
        "search": "Buscar", "advanced_search": "Búsqueda avanzada",
        "help": "Ayuda", "news": "Noticias", "blog": "Blog",
        "store": "Tienda", "login": "Acceder", "register": "Registrarse",
        "logout": "Salir", "library": "Biblioteca",
        "today_on_arxiv": "Hoy en arXiv",
        "header_banner": "Repositorio de preprints arXiv",
        "language_label": "Español",
    },
}

# WSGI shim: strip /lang/<code>/ prefix early so URL routing sees the
# canonical path. Stores chosen language in environ for the request context
# processor to surface to templates.
_orig_wsgi_app = app.wsgi_app


def _lang_prefix_wsgi(environ, start_response):
    p = environ.get("PATH_INFO", "")
    m = re.match(r"^/lang/(zh|es|en)(/.*)?$", p)
    if m:
        environ["HTTP_X_ARXIV_LANG"] = m.group(1)
        environ["PATH_INFO"] = m.group(2) or "/"
    return _orig_wsgi_app(environ, start_response)


app.wsgi_app = _lang_prefix_wsgi


@app.context_processor
def inject_lang_pref():
    pref = request.environ.get("HTTP_X_ARXIV_LANG", "en")
    if pref not in LANG_LABELS:
        pref = "en"
    return dict(
        lang_pref=pref,
        lang_labels=LANG_LABELS[pref],
        available_languages=[("en", "English"), ("zh", "中文"),
                             ("es", "Español")],
    )


@app.route("/lang/<code>")
@app.route("/lang/<code>/")
def lang_landing(code):
    """Top-level landing for /lang/<code> — the WSGI shim has already
    rewritten PATH_INFO to '/' so we just re-dispatch to the index view.
    This route only fires for paths that come in raw (e.g. via direct
    Flask test client). With the shim, requests to /lang/zh hit index()
    directly."""
    if code not in LANG_LABELS:
        abort(404)
    return redirect(url_for("index"))


# -----------------------------------------------------------------------
# SEO — robots.txt, sitemap index, per-year sitemaps
# -----------------------------------------------------------------------

@app.route("/robots.txt")
def robots_txt():
    body = (
        "User-agent: *\n"
        "Allow: /\n"
        "Disallow: /account\n"
        "Disallow: /library\n"
        "Disallow: /starred\n"
        "Disallow: /export/\n"
        "Disallow: /alerts\n"
        "\n"
        "User-agent: GPTBot\n"
        "Allow: /\n"
        "\n"
        "Sitemap: /sitemap.xml\n"
        "Sitemap: /sitemap-index.xml\n"
    )
    return Response(body, mimetype="text/plain")


def _sitemap_years():
    rows = db.session.query(Paper.submitted_year).distinct().filter(
        Paper.submitted_year > 0).order_by(Paper.submitted_year.desc()).all()
    return [r[0] for r in rows]


@app.route("/sitemap.xml")
@app.route("/sitemap-index.xml")
def sitemap_index():
    years = _sitemap_years()
    root = request.url_root.rstrip("/")
    parts = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    parts.append(f"  <sitemap><loc>{root}/sitemap-static.xml</loc></sitemap>")
    for y in years:
        parts.append(f"  <sitemap><loc>{root}/sitemap-{y}.xml</loc></sitemap>")
    parts.append("</sitemapindex>")
    return Response("\n".join(parts) + "\n", mimetype="application/xml")


@app.route("/sitemap-static.xml")
def sitemap_static():
    root = request.url_root.rstrip("/")
    static_paths = ["/", "/about", "/help", "/news", "/blog", "/store",
                    "/category_taxonomy", "/advanced", "/oai-pmh",
                    "/lang/en", "/lang/zh", "/lang/es"]
    parts = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for sp in static_paths:
        parts.append(f"  <url><loc>{root}{sp}</loc><changefreq>weekly</changefreq><priority>0.7</priority></url>")
    parts.append("</urlset>")
    return Response("\n".join(parts) + "\n", mimetype="application/xml")


@app.route("/sitemap-<int:year>.xml")
def sitemap_year(year):
    root = request.url_root.rstrip("/")
    # Cap at 5000 URLs per sitemap (well under the 50k spec limit) — keeps
    # render fast and predictable. Agents looking up "how many URLs in
    # sitemap-2024.xml" get a stable answer per year.
    rows = (Paper.query.filter_by(submitted_year=year)
            .order_by(Paper.arxiv_id)
            .with_entities(Paper.arxiv_id, Paper.submitted_date)
            .limit(5000).all())
    if not rows:
        abort(404)
    parts = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for aid, sd in rows:
        parts.append(
            f"  <url><loc>{root}/abs/{aid}</loc>"
            f"<lastmod>{sd or year}</lastmod>"
            f"<changefreq>monthly</changefreq><priority>0.5</priority></url>"
        )
    parts.append("</urlset>")
    return Response("\n".join(parts) + "\n", mimetype="application/xml")


# -----------------------------------------------------------------------
# OAI-PMH documentation page (read-only HTML overview — agents land here
# when chasing the OAI-PMH bulk-harvest interface).
# -----------------------------------------------------------------------

@app.route("/oai-pmh")
@app.route("/oai2")
@app.route("/oai")
@app.route("/help/oai")
def oai_pmh_doc():
    sets = [
        ("cs", "Computer Science"), ("math", "Mathematics"),
        ("stat", "Statistics"), ("physics", "Physics"),
        ("astro-ph", "Astrophysics"), ("cond-mat", "Condensed Matter"),
        ("hep-th", "High Energy Physics - Theory"),
        ("hep-ph", "High Energy Physics - Phenomenology"),
        ("hep-ex", "High Energy Physics - Experiment"),
        ("hep-lat", "High Energy Physics - Lattice"),
        ("nucl-th", "Nuclear Theory"), ("nucl-ex", "Nuclear Experiment"),
        ("gr-qc", "General Relativity and Quantum Cosmology"),
        ("math-ph", "Mathematical Physics"),
        ("quant-ph", "Quantum Physics"), ("nlin", "Nonlinear Sciences"),
        ("q-bio", "Quantitative Biology"),
        ("q-fin", "Quantitative Finance"),
        ("eess", "Electrical Engineering and Systems Science"),
        ("econ", "Economics"),
    ]
    total = db.session.query(func.count(Paper.id)).scalar() or 0
    return render_template("oai_pmh.html", sets=sets, paper_total=total)


# -----------------------------------------------------------------------
# DOI resolver — accept either a full DOI (10.xxxx/...) or a URL form.
# Used by tasks like "resolve DOI 10.1109/foo and open the paper".
# -----------------------------------------------------------------------

@app.route("/resolve/doi/<path:doi>")
@app.route("/doi/<path:doi>")
def doi_resolve(doi):
    # Strip optional "doi:" prefix and any URL scheme.
    doi = doi.strip()
    for prefix in ("doi:", "DOI:", "https://doi.org/", "http://doi.org/",
                   "https://dx.doi.org/"):
        if doi.lower().startswith(prefix.lower()):
            doi = doi[len(prefix):]
            break
    p = Paper.query.filter(Paper.doi == doi).first()
    if not p:
        # Try a LIKE fallback for tasks that pass the trailing identifier
        # only (e.g. "1109/foo" instead of "10.1109/foo").
        p = Paper.query.filter(Paper.doi.like(f"%{doi}")).first()
    if not p:
        return render_template("error.html", code=404,
                               message=f"No paper found for DOI '{doi}'"), 404
    return redirect(url_for("paper_detail", arxiv_id=p.arxiv_id), code=302)


# -----------------------------------------------------------------------
# LaTeX source tarball info page — explains the e-print bundle layout.
# -----------------------------------------------------------------------

@app.route("/src/<arxiv_id>")
@app.route("/src/<arxiv_id>/")
def source_tarball(arxiv_id):
    p = Paper.query.filter_by(arxiv_id=arxiv_id).first_or_404()
    # Deterministic tarball metadata derived from arxiv_id hash. No data on
    # disk — this is a stub doc page describing what a real harvest would
    # download.
    digest = hashlib.sha256(arxiv_id.encode()).digest()
    size_kb = 32 + (int.from_bytes(digest[:3], "big") % 1480)  # 32..1512 kb
    file_count = 4 + (digest[3] % 28)                          # 4..31 files
    has_bbl = (digest[4] % 3) != 0
    has_figs = (digest[5] % 5) != 0
    return render_template("source_tarball.html",
                           paper=p, size_kb=size_kb,
                           file_count=file_count,
                           has_bbl=has_bbl, has_figs=has_figs)


# -----------------------------------------------------------------------
# RSS / Atom feeds per category (real arxiv ships these at e.g.
# rss.arxiv.org/rss/cs and export.arxiv.org/api/query?...).
# -----------------------------------------------------------------------

def _feed_papers(code, limit=25):
    return (Paper.query.filter(
        or_(Paper.primary_subject_code == code,
            Paper.primary_subject_code.like(f"{code}.%"),
            Paper.primary_category_code == code))
        .order_by(Paper.arxiv_id.desc())
        .limit(limit).all())


@app.route("/list/<code>/rss")
@app.route("/rss/<code>")
@app.route("/rss/<code>.xml")
def listing_rss(code):
    papers = _feed_papers(code)
    if not papers:
        abort(404)
    root = request.url_root.rstrip("/")
    items = []
    for p in papers:
        title = (p.title or "").replace("&", "&amp;").replace("<", "&lt;")
        desc = (p.short_abstract or "").replace("&", "&amp;").replace("<", "&lt;")
        items.append(
            f"  <item>\n"
            f"    <title>{title}</title>\n"
            f"    <link>{root}/abs/{p.arxiv_id}</link>\n"
            f"    <guid isPermaLink=\"true\">{root}/abs/{p.arxiv_id}</guid>\n"
            f"    <description>{desc}</description>\n"
            f"    <pubDate>{p.submitted_date}</pubDate>\n"
            f"    <category>{p.primary_subject_code}</category>\n"
            f"  </item>"
        )
    body = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<rss version="2.0" xmlns:dc="http://purl.org/dc/elements/1.1/">\n'
        '<channel>\n'
        f"  <title>arXiv {code} latest preprints</title>\n"
        f"  <link>{root}/list/{code}/recent</link>\n"
        f"  <description>Latest {code} submissions to arXiv</description>\n"
        f"  <language>en-us</language>\n"
        + "\n".join(items) +
        "\n</channel>\n</rss>\n"
    )
    return Response(body, mimetype="application/rss+xml")


@app.route("/list/<code>/atom")
@app.route("/atom/<code>")
@app.route("/atom/<code>.xml")
def listing_atom(code):
    papers = _feed_papers(code)
    if not papers:
        abort(404)
    root = request.url_root.rstrip("/")
    entries = []
    for p in papers:
        title = (p.title or "").replace("&", "&amp;").replace("<", "&lt;")
        summ = (p.short_abstract or "").replace("&", "&amp;").replace("<", "&lt;")
        entries.append(
            f"  <entry>\n"
            f"    <title>{title}</title>\n"
            f"    <id>{root}/abs/{p.arxiv_id}</id>\n"
            f"    <link href=\"{root}/abs/{p.arxiv_id}\"/>\n"
            f"    <updated>{p.submitted_date}T00:00:00Z</updated>\n"
            f"    <summary>{summ}</summary>\n"
            f"    <category term=\"{p.primary_subject_code}\"/>\n"
            f"  </entry>"
        )
    body = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<feed xmlns="http://www.w3.org/2005/Atom">\n'
        f"  <title>arXiv {code} latest preprints</title>\n"
        f"  <id>{root}/atom/{code}</id>\n"
        f"  <link href=\"{root}/atom/{code}\" rel=\"self\"/>\n"
        f"  <updated>{papers[0].submitted_date}T00:00:00Z</updated>\n"
        + "\n".join(entries) +
        "\n</feed>\n"
    )
    return Response(body, mimetype="application/atom+xml")


# -----------------------------------------------------------------------
# Citation batch export — download N citations as BibTeX in one shot.
# Distinct from /export which is a UI flow with multiple steps.
# -----------------------------------------------------------------------

@app.route("/citation/batch")
@app.route("/cite/batch")
def citation_batch():
    try:
        count = int(request.args.get("n", "100"))
    except ValueError:
        count = 100
    count = max(1, min(200, count))
    fmt = (request.args.get("format") or "bibtex").lower()
    cat = (request.args.get("cat") or "").strip()
    q = Paper.query.order_by(Paper.arxiv_id.desc())
    if cat:
        q = q.filter(or_(Paper.primary_subject_code == cat,
                         Paper.primary_subject_code.like(f"{cat}.%"),
                         Paper.primary_category_code == cat))
    papers = q.limit(count).all()
    lines = []
    if fmt == "ris":
        for p in papers:
            lines.append("TY  - JOUR")
            lines.append(f"TI  - {p.title}")
            for a in p.get_authors():
                lines.append(f"AU  - {a}")
            lines.append(f"PY  - {p.submitted_year}")
            lines.append(f"UR  - https://arxiv.org/abs/{p.arxiv_id}")
            if p.doi:
                lines.append(f"DO  - {p.doi}")
            lines.append("ER  -")
            lines.append("")
        body = "\n".join(lines)
        mime = "application/x-research-info-systems"
    else:
        for p in papers:
            cite_key = f"arxiv{p.arxiv_id.replace('.', '')}"
            authors_bib = " and ".join(p.get_authors()) or "Anonymous"
            lines.append(f"@article{{{cite_key},")
            lines.append(f"  title = {{{p.title}}},")
            lines.append(f"  author = {{{authors_bib}}},")
            lines.append(f"  year = {{{p.submitted_year}}},")
            lines.append(f"  eprint = {{{p.arxiv_id}}},")
            lines.append("  archivePrefix = {arXiv},")
            if p.primary_subject_code:
                lines.append(f"  primaryClass = {{{p.primary_subject_code}}},")
            if p.doi:
                lines.append(f"  doi = {{{p.doi}}},")
            lines.append(f"  url = {{https://arxiv.org/abs/{p.arxiv_id}}}")
            lines.append("}")
            lines.append("")
        body = "\n".join(lines)
        mime = "application/x-bibtex"
    # Surface the count as a visible header line so agents can read
    # "Exported 100 BibTeX entries" directly from the page.
    body = f"% Exported {len(papers)} {fmt.upper()} entries from arXiv mirror\n\n" + body
    return Response(body, mimetype=mime)


# -----------------------------------------------------------------------
# SEO meta block + JSON-LD ScholarlyArticle helper. The template includes
# the dict via {{ paper_seo_meta(paper) | safe }}; centralising here keeps
# the encoding rules in one place.
# -----------------------------------------------------------------------

def _xml_escape(s):
    return (s or "").replace("&", "&amp;").replace("<", "&lt;") \
                    .replace(">", "&gt;").replace('"', "&quot;")


@app.template_global()
def paper_seo_meta(paper):
    """Return a block of Dublin Core meta tags + JSON-LD ScholarlyArticle
    schema for a single paper. Output is HTML-safe; caller marks |safe."""
    dc_creators = "\n".join(
        f'  <meta name="DC.creator" content="{_xml_escape(a)}">'
        for a in paper.get_authors())
    dc = [
        f'  <meta name="DC.title" content="{_xml_escape(paper.title)}">',
        f'  <meta name="DC.date" content="{_xml_escape(paper.submitted_date)}">',
        f'  <meta name="DC.identifier" content="arXiv:{paper.arxiv_id}">',
        f'  <meta name="DC.identifier.uri" content="https://arxiv.org/abs/{paper.arxiv_id}">',
        f'  <meta name="DC.subject" content="{_xml_escape(paper.primary_subject_code)}">',
        f'  <meta name="DC.publisher" content="arXiv.org">',
        f'  <meta name="DC.rights" content="{_xml_escape(paper.license or "arXiv-perpetual")}">',
        f'  <meta name="DC.language" content="en">',
        f'  <meta name="DC.type" content="Text.Article">',
        f'  <meta name="DC.description" content="{_xml_escape((paper.abstract or "")[:300])}">',
    ]
    if paper.doi:
        dc.append(f'  <meta name="DC.identifier.doi" content="{_xml_escape(paper.doi)}">')
    if paper.journal_ref:
        dc.append(f'  <meta name="DC.source" content="{_xml_escape(paper.journal_ref)}">')
    # Highwire Press citation_* meta (Google Scholar / Semantic Scholar).
    citation = [
        f'  <meta name="citation_title" content="{_xml_escape(paper.title)}">',
        f'  <meta name="citation_arxiv_id" content="{paper.arxiv_id}">',
        f'  <meta name="citation_date" content="{_xml_escape(paper.submitted_date)}">',
        f'  <meta name="citation_online_date" content="{_xml_escape(paper.submitted_date)}">',
        f'  <meta name="citation_pdf_url" content="https://arxiv.org/pdf/{paper.arxiv_id}">',
        f'  <meta name="citation_abstract_html_url" content="https://arxiv.org/abs/{paper.arxiv_id}">',
    ]
    for a in paper.get_authors():
        citation.append(f'  <meta name="citation_author" content="{_xml_escape(a)}">')
    if paper.doi:
        citation.append(f'  <meta name="citation_doi" content="{_xml_escape(paper.doi)}">')
    # JSON-LD ScholarlyArticle (deterministic — sorted keys via json.dumps).
    json_ld = {
        "@context": "https://schema.org",
        "@type": "ScholarlyArticle",
        "headline": paper.title,
        "name": paper.title,
        "identifier": f"arXiv:{paper.arxiv_id}",
        "url": f"https://arxiv.org/abs/{paper.arxiv_id}",
        "datePublished": paper.submitted_date,
        "abstract": (paper.abstract or "")[:1000],
        "author": [{"@type": "Person", "name": a}
                   for a in paper.get_authors()],
        "publisher": {"@type": "Organization", "name": "arXiv",
                      "url": "https://arxiv.org"},
        "keywords": paper.primary_subject_code,
        "inLanguage": "en",
        "license": paper.license or "arXiv-perpetual",
    }
    if paper.doi:
        json_ld["sameAs"] = f"https://doi.org/{paper.doi}"
    blob = json.dumps(json_ld, ensure_ascii=False, sort_keys=True, indent=2)
    return (dc_creators + "\n" + "\n".join(dc) + "\n" + "\n".join(citation)
            + '\n  <script type="application/ld+json">\n' + blob
            + "\n  </script>")


# =======================================================================
# R8 — observability, developer & telemetry endpoints, contextual help
# All responses are deterministic functions of (corpus stats, arxiv_id,
# fixed reference date) so no DB writes are needed and byte-identical
# rebuilds stay intact.
# =======================================================================

# Build-time anchor for /healthz / /api/uptime. Fixed so "uptime" reads
# stable across replays of the same mirror.
SERVICE_BUILD_TS = MIRROR_REFERENCE_DATE.replace(hour=0, minute=0, second=0)


@app.route("/healthz")
@app.route("/health")
def healthz():
    """Cheap liveness probe — returns 200 + JSON when the DB connection
    is reachable. Used by uptime monitors and the /api/uptime page."""
    try:
        n = db.session.query(func.count(Paper.id)).scalar() or 0
        return jsonify({
            "status": "ok",
            "service": "arxiv-mirror",
            "build_date": SERVICE_BUILD_TS.strftime("%Y-%m-%d"),
            "papers": int(n),
            "checks": {"database": "ok", "cache": "ok", "search": "ok"},
        })
    except Exception as exc:
        return jsonify({"status": "degraded", "error": str(exc)}), 503


@app.route("/api/uptime")
def api_uptime():
    """Uptime report — stable per build. The 'window_days' is digest-derived
    from the build date so two builds of the same seed report the same SLA."""
    digest = hashlib.md5(SERVICE_BUILD_TS.isoformat().encode("utf-8")).digest()
    window_days = 30
    # Synth a stable 99.9x percentage and per-day incidents.
    avail_pp = 9990 + (digest[0] % 10)        # 99.90 .. 99.99
    avail_pct = avail_pp / 100.0
    incidents = []
    for i in range(3):
        day = SERVICE_BUILD_TS - timedelta(days=2 + i * 9)
        incidents.append({
            "date": day.strftime("%Y-%m-%d"),
            "duration_min": 2 + (digest[(i + 1) * 2] % 18),
            "summary": [
                "Brief search latency spike",
                "OAI-PMH replication delay",
                "PDF mirror cache warmup",
                "Authentication node rolling restart",
            ][digest[i] % 4],
            "severity": ["info", "minor", "minor"][i],
        })
    return jsonify({
        "service": "arxiv-mirror",
        "window_days": window_days,
        "availability_pct": avail_pct,
        "last_outage": incidents[0]["date"],
        "incidents": incidents,
        "build_date": SERVICE_BUILD_TS.strftime("%Y-%m-%d"),
    })


@app.route("/api/events")
def api_events():
    """Recent platform events feed — deterministic, anchored to the
    most-recent paper submission_date in the corpus. Useful for tasks
    like 'list the most recent platform events' or 'how many security
    advisories in the events feed?'.
    """
    anchor = db.session.query(func.max(Paper.submitted_date)).scalar() or "2026-04-01"
    try:
        anchor_dt = datetime.strptime(anchor, "%Y-%m-%d")
    except Exception:
        anchor_dt = SERVICE_BUILD_TS
    EVENT_BANK = [
        ("submission", "info", "Daily submission window closed"),
        ("submission", "info", "New submissions announced"),
        ("ingest", "info", "Bulk OAI harvest cycle completed"),
        ("ingest", "minor", "Backfill: 2018 metadata reprocessed"),
        ("moderation", "info", "Moderator quorum reached for math.NT batch"),
        ("moderation", "minor", "Cross-list reassignment applied"),
        ("infra", "info", "Search index rebuild finished"),
        ("infra", "minor", "Read-replica failover (no user impact)"),
        ("security", "info", "Quarterly audit completed"),
        ("security", "advisory", "TLS cert rotated on api.* endpoints"),
        ("api", "info", "OAI-PMH endpoint capacity expanded"),
        ("api", "info", "Citation batch export rate-limit raised"),
        ("release", "info", "HTML5 renderer v3.2 deployed"),
        ("release", "info", "Sitemap generator updated"),
        ("policy", "info", "Withdrawal policy clarified in help"),
    ]
    n = max(1, min(40, int(request.args.get("limit", 20))))
    sev = (request.args.get("severity") or "").strip().lower()
    rows = []
    for i in range(n):
        kind, severity, summary = EVENT_BANK[i % len(EVENT_BANK)]
        ts = anchor_dt - timedelta(hours=i * 9, minutes=(i * 13) % 60)
        rows.append({
            "id": f"EV-{ts.strftime('%Y%m%d')}-{i:03d}",
            "ts": ts.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "kind": kind,
            "severity": severity,
            "summary": summary,
        })
    if sev:
        rows = [r for r in rows if r["severity"] == sev]
    return jsonify({"anchor": anchor, "count": len(rows), "events": rows})


@app.route("/api/log")
def api_log():
    """Application access-log tail. Synthesised from a fixed bank +
    arxiv-id rotation so the output is identical across rebuilds.
    Honours ?limit=N (default 25, max 200) and ?status=4xx|5xx|2xx."""
    n = max(1, min(200, int(request.args.get("limit", 25))))
    flt = (request.args.get("status") or "").strip().lower()
    # Stable arxiv-id sample for the URL column.
    sample = (Paper.query.order_by(Paper.arxiv_id)
              .with_entities(Paper.arxiv_id).limit(120).all())
    sample_ids = [r[0] for r in sample] or ["0000.00000"]
    PATH_TPLS = [
        "GET /abs/{aid}", "GET /pdf/{aid}", "GET /list/cs.LG/recent",
        "GET /list/cs.CV/recent", "GET /search?query=quantum",
        "GET /robots.txt", "GET /sitemap.xml", "POST /api/library/add",
        "GET /api/papers/cs", "GET /citation/batch?n=50",
        "GET /cite/batch?n=100&format=ris", "GET /MSC2020/68T",
        "GET /year/2024/cs", "GET /find/grp_cs", "GET /oai-pmh",
        "GET /atom/math.xml", "GET /healthz", "GET /api/uptime",
    ]
    STATUS_POOL = ["200"] * 16 + ["301", "302", "304", "404", "401", "500"]
    lines = []
    for i in range(n):
        aid = sample_ids[i % len(sample_ids)]
        path = PATH_TPLS[i % len(PATH_TPLS)].format(aid=aid)
        status = STATUS_POOL[i % len(STATUS_POOL)]
        ts = SERVICE_BUILD_TS - timedelta(seconds=i * 7 + 2)
        # Deterministic 24-byte request id from arxiv_id + index
        rid = hashlib.sha1(f"{aid}-{i}".encode()).hexdigest()[:16]
        bytes_out = 256 + (hashlib.md5(rid.encode()).digest()[0] * 96)
        lines.append({
            "ts": ts.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "request_id": rid,
            "method_path": path,
            "status": status,
            "bytes": bytes_out,
            "client_ip": f"10.0.{(i * 17) % 256}.{(i * 31) % 256}",
        })
    if flt in {"2xx", "3xx", "4xx", "5xx"}:
        head = flt[0]
        lines = [l for l in lines if l["status"].startswith(head)]
    return jsonify({"count": len(lines), "lines": lines,
                    "service": "arxiv-mirror"})


@app.route("/api/telemetry")
def api_telemetry():
    """Aggregate counters — used for tasks like 'how many papers are
    indexed' / 'how many comments' without scraping pages."""
    return jsonify({
        "papers_total": db.session.query(func.count(Paper.id)).scalar() or 0,
        "papers_with_doi": db.session.query(func.count(Paper.id))
            .filter(Paper.doi != "").scalar() or 0,
        "papers_with_msc": db.session.query(func.count(Paper.id))
            .filter(Paper.msc_class != "").scalar() or 0,
        "comments_total": db.session.query(func.count(Comment.id)).scalar() or 0,
        "library_items_total": db.session.query(func.count(LibraryItem.id)).scalar() or 0,
        "users_total": db.session.query(func.count(User.id)).scalar() or 0,
        "categories_total": db.session.query(func.count(Category.id)).scalar() or 0,
        "build_date": SERVICE_BUILD_TS.strftime("%Y-%m-%d"),
    })


# -----------------------------------------------------------------------
# Developer keys + webhooks. Read-only stubs — tokens & secrets are
# digest-derived per session-less client so /developer/api-key never
# leaks secret material and stays byte-identical across rebuilds.
# -----------------------------------------------------------------------

def _developer_token_for_email(email):
    """Stable per-email token. Format mirrors `arx_live_*` industry style."""
    norm = (email or "anonymous@arxiv.local").strip().lower()
    raw = hashlib.sha256(("arxiv-dev-key|" + norm).encode("utf-8")).hexdigest()
    return "arx_live_" + raw[:32]


@app.route("/developer")
@app.route("/developer/")
def developer_index():
    """Documentation hub for the public API surface."""
    endpoints = [
        ("GET /api/papers/<category>", "List most recent papers in a category"),
        ("GET /api/stats", "Aggregate corpus counts"),
        ("GET /api/telemetry", "Detailed counters including DOI/MSC coverage"),
        ("GET /api/events", "Recent platform events"),
        ("GET /api/uptime", "Service availability snapshot"),
        ("GET /api/log?limit=N", "Recent access log (synthetic)"),
        ("GET /healthz", "Liveness probe"),
        ("POST /webhook/new-paper", "Subscribe a webhook URL for new-paper events"),
        ("GET /oai-pmh", "OAI-PMH bulk harvest documentation"),
        ("GET /cite/batch?n=N", "BibTeX/RIS batch export"),
    ]
    return render_template("developer.html",
                           endpoints=endpoints,
                           sdk_version="2.6.0",
                           build_date=SERVICE_BUILD_TS.strftime("%Y-%m-%d"))


@app.route("/developer/api-key", methods=["GET", "POST"])
@csrf.exempt
def developer_api_key():
    """Stable developer key page. POST issues a fresh-looking response
    but the underlying token is deterministic per email so the page can
    be replayed in tasks like 'open /developer/api-key, log in, copy the
    token'."""
    if current_user.is_authenticated:
        email = current_user.email
    else:
        email = (request.values.get("email") or "").strip().lower()
    token = _developer_token_for_email(email) if email else ""
    sample_curl = (
        "curl -H 'Authorization: Bearer " + (token or "<your-token>") + "' "
        + request.url_root.rstrip('/') + "/api/papers/cs"
    )
    return render_template("developer_api_key.html",
                           email=email, token=token,
                           sample_curl=sample_curl,
                           build_date=SERVICE_BUILD_TS.strftime("%Y-%m-%d"))


@app.route("/webhook/new-paper", methods=["GET", "POST"])
@csrf.exempt
def webhook_new_paper():
    """Display a stable signing secret + last-delivery payload for the
    new-paper webhook. POST also returns the same data — every request
    is deterministic for a given email."""
    email = ((current_user.email if current_user.is_authenticated else None)
             or request.values.get("email") or "").strip().lower()
    secret_seed = "arxiv-webhook|" + (email or "anonymous@arxiv.local")
    signing_secret = "whsec_" + hashlib.sha256(
        secret_seed.encode("utf-8")).hexdigest()[:40]
    latest = (Paper.query.order_by(Paper.submitted_date.desc(),
                                   Paper.arxiv_id.desc())
              .first())
    sample_payload = {
        "event": "new-paper",
        "delivery_id": hashlib.md5(secret_seed.encode()).hexdigest()[:24],
        "occurred_at": SERVICE_BUILD_TS.strftime("%Y-%m-%dT00:00:00Z"),
        "data": {
            "arxiv_id": latest.arxiv_id if latest else None,
            "title": latest.title if latest else None,
            "primary_subject": (latest.primary_subject_code
                                if latest else None),
            "url": (request.url_root.rstrip("/") + f"/abs/{latest.arxiv_id}"
                    if latest else None),
        },
    }
    return render_template(
        "webhook_new_paper.html",
        email=email,
        signing_secret=signing_secret,
        sample_payload=json.dumps(sample_payload, indent=2, sort_keys=True),
        latest=latest,
    )


# -----------------------------------------------------------------------
# Contextual help — hover-text glossary for terms that show up on every
# paper page (affiliations, licenses, MSC class). Served as JSON so the
# UI can fetch & render tooltips without re-shipping a static dict.
# -----------------------------------------------------------------------

CONTEXTUAL_HELP = {
    "affiliation": ("The author's home institution at submission time, "
                    "parsed from the OAI-PMH metadata. arXiv does not "
                    "verify affiliations — they reflect what the "
                    "submitting author entered."),
    "license-arXiv-perpetual": (
        "arXiv perpetual, non-exclusive licence: grants arXiv the right "
        "to distribute the work forever but the copyright stays with the "
        "author. The default for submissions without an explicit Creative "
        "Commons choice."),
    "license-CC-BY-4.0": (
        "Creative Commons Attribution 4.0 — anyone may reuse the work, "
        "including commercially, as long as proper attribution is given."),
    "license-CC-BY-SA-4.0": (
        "Creative Commons Attribution-ShareAlike 4.0 — same as CC-BY-4.0 "
        "but derivative works must use the same licence."),
    "license-CC-BY-NC-SA-4.0": (
        "Creative Commons Attribution-NonCommercial-ShareAlike 4.0 — "
        "non-commercial reuse with attribution and matching licence."),
    "license-CC-BY-NC-ND-4.0": (
        "Creative Commons Attribution-NonCommercial-NoDerivatives 4.0 — "
        "non-commercial reuse only, no derivative works."),
    "license-CC0-1.0": (
        "Creative Commons Zero — the author has released the work into the "
        "public domain to the extent possible by law."),
    "msc-class": ("Mathematics Subject Classification (MSC2020) tag set "
                  "by the author. Two-digit prefix marks the family; the "
                  "letter+digits select a sub-area."),
    "doi": ("Digital Object Identifier — persistent URL for the formally "
            "published version of the paper (typically supplied after "
            "journal acceptance)."),
    "journal-ref": ("Journal reference — citation string for the formally "
                    "published version. Many preprints never get one."),
    "report-no": ("Institutional report number assigned by the lab or "
                  "department that produced the paper."),
    "msc": ("Mathematics Subject Classification family (see "
            "MSC2020 page)."),
    "keyboard-help": ("Keyboard shortcuts available on this page — see "
                     "the floating help panel triggered by '?'."),
}


@app.route("/api/help/<topic>")
def api_help(topic):
    """Return contextual help text for a single hover-help topic.

    Tasks frequently ask the agent to 'open /api/help/license-CC-BY-4.0
    and copy the description' — the JSON output is stable and small.
    """
    topic = (topic or "").strip()
    body = CONTEXTUAL_HELP.get(topic, "")
    return jsonify({"topic": topic, "found": bool(body), "body": body,
                    "topics_available": sorted(CONTEXTUAL_HELP)})


@app.route("/help/keyboard")
def help_keyboard():
    """Documentation page listing the keyboard shortcuts the UI ships."""
    shortcuts = [
        ("j", "Next paper in listing / next result"),
        ("k", "Previous paper in listing / previous result"),
        ("?", "Toggle the keyboard-shortcut help panel"),
        ("Ctrl/Cmd + K", "Open command palette — paste an arxiv_id to jump to /abs/<id>"),
        ("g h", "Go to homepage"),
        ("g l", "Go to your library"),
        ("g s", "Go to advanced search"),
        ("e", "Toggle the abstract collapse on /abs pages"),
        ("/", "Focus the header search input"),
        ("Escape", "Close any open dialog / palette"),
    ]
    return render_template("help_keyboard.html", shortcuts=shortcuts)


# -----------------------------------------------------------------------
# R9 — multi-step submission wizard, endorsement flow, withdraw/replace
# stubs, ORCID-link API, conference-link API.  All routes are stateless
# (no DB writes) and derive every nonce/code/identifier deterministically
# from the input so rebuilds stay byte-identical and replayed tasks always
# observe the same answer.
# -----------------------------------------------------------------------

SUBMIT_WIZARD_STEPS = [
    ("license", "Pick a distribution licence",
     "Select how others may reuse the paper."),
    ("metadata", "Title, authors, abstract",
     "Mandatory fields — the title, author list (in submission order), the abstract, and the primary subject class."),
    ("files", "Upload the source archive",
     "LaTeX source plus figures or a single PDF.  Maximum upload size 50 MB."),
    ("supplementary", "Supplementary material (optional)",
     "Anc-files such as videos, code, data; max 200 MB total across all anc-files."),
    ("preview", "Preview & confirm",
     "Verify the rendered abstract and the parsed metadata before announcement."),
    ("complete", "Announcement scheduled",
     "Your paper is queued for the next announcement window (20:00 EST, Mon-Fri)."),
]


@app.route("/submit", methods=["GET"])
@app.route("/submit/", methods=["GET"])
def submit_wizard_index():
    return redirect(url_for("submit_wizard_step", step="license"), code=302)


@app.route("/submit/<step>", methods=["GET", "POST"])
@csrf.exempt
def submit_wizard_step(step):
    """Multi-step submission wizard.  Each step renders the current
    form, links to the next/prev step, and (on POST) returns the next
    step's URL in the response so an agent can chain through GET-POST-GET
    without ever mutating server state."""
    step = (step or "license").strip().lower()
    known = {s[0] for s in SUBMIT_WIZARD_STEPS}
    if step not in known:
        abort(404)
    order = [s[0] for s in SUBMIT_WIZARD_STEPS]
    idx = order.index(step)
    prev_step = order[idx - 1] if idx > 0 else None
    next_step = order[idx + 1] if idx + 1 < len(order) else None
    title = dict((s[0], s[1]) for s in SUBMIT_WIZARD_STEPS)[step]
    blurb = dict((s[0], s[2]) for s in SUBMIT_WIZARD_STEPS)[step]
    # Deterministic per-step ticket id — useful as a stable answer for
    # tasks like "submit step 3, report the upload ticket".
    ticket = "subm-" + hashlib.sha256(
        ("arxiv-submit-wizard|" + step).encode()
    ).hexdigest()[:12]
    submitted = request.method == "POST"
    return render_template(
        "submit_wizard.html",
        step=step, step_index=idx + 1, step_total=len(order),
        steps=SUBMIT_WIZARD_STEPS, title=title, blurb=blurb,
        prev_step=prev_step, next_step=next_step,
        ticket=ticket, submitted=submitted,
    )


def _endorsement_code_for(email, subject_class):
    seed = "arxiv-endorse|" + (email or "anon").strip().lower() + "|" + (
        subject_class or "cs").strip().lower()
    return "END-" + hashlib.sha256(seed.encode()).hexdigest()[:10].upper()


@app.route("/endorsements")
def endorsements_index():
    """Documentation for the endorsement system."""
    rules = [
        ("Submitting to a new subject class for the first time",
         "Most users need an endorser who has already published 3 papers "
         "in that class within the last 5 years."),
        ("Endorser eligibility",
         "Author of 3+ accepted papers (any subject) and at least one in "
         "the target class within the trailing five-year window."),
        ("Validity",
         "Endorsements stay valid for 5 years from the issue date."),
        ("Single-paper endorsement",
         "Some classes (e.g. cs.AI) auto-endorse if a co-author already "
         "has an active endorsement for that class."),
    ]
    classes = ["cs.AI", "cs.CL", "cs.CV", "cs.LG", "cs.RO", "stat.ML",
               "math.AG", "math.NT", "physics.optics", "quant-ph",
               "hep-th", "astro-ph.CO"]
    return render_template("endorsements.html", rules=rules,
                           classes=classes,
                           contact="endorsement-help@arxiv.local")


@app.route("/endorse-request", methods=["GET", "POST"])
@csrf.exempt
def endorse_request():
    """Form that issues a stable per-(email, class) endorsement code.
    No DB writes — the code is a function of the inputs."""
    email = (request.values.get("email") or "").strip().lower()
    subject = (request.values.get("subject_class") or "").strip()
    note = (request.values.get("note") or "").strip()[:200]
    code = _endorsement_code_for(email, subject) if (email and subject) else ""
    return render_template(
        "endorse_request.html",
        email=email, subject_class=subject, note=note, code=code,
        classes=["cs.AI", "cs.CL", "cs.CV", "cs.LG", "cs.RO", "stat.ML",
                 "math.AG", "math.NT", "physics.optics", "quant-ph",
                 "hep-th", "astro-ph.CO"],
        valid_from=SERVICE_BUILD_TS.strftime("%Y-%m-%d"),
        valid_until=(SERVICE_BUILD_TS + timedelta(days=365 * 5)
                     ).strftime("%Y-%m-%d"),
    )


def _withdraw_ticket_for(arxiv_id):
    return "WDR-" + hashlib.sha256(
        ("arxiv-withdraw|" + (arxiv_id or "")).encode()
    ).hexdigest()[:10].upper()


@app.route("/withdraw/<arxiv_id>", methods=["GET", "POST"])
@csrf.exempt
def withdraw_paper(arxiv_id):
    """Stub for the paper-withdrawal flow.  GET renders the
    confirmation form, POST renders the 'request received' page with a
    stable ticket id."""
    paper = Paper.query.filter_by(arxiv_id=arxiv_id).first()
    if not paper:
        abort(404)
    reason = (request.values.get("reason") or "").strip()[:500]
    submitted = request.method == "POST"
    ticket = _withdraw_ticket_for(arxiv_id) if submitted else ""
    review_lag_days = 1  # arxiv business-day SLA
    return render_template(
        "withdraw_paper.html",
        paper=paper, reason=reason, submitted=submitted, ticket=ticket,
        review_lag_days=review_lag_days,
        announce_at=(SERVICE_BUILD_TS + timedelta(days=review_lag_days)
                     ).strftime("%Y-%m-%d"),
    )


def _replace_ticket_for(arxiv_id):
    return "REPL-" + hashlib.sha256(
        ("arxiv-replace|" + (arxiv_id or "")).encode()
    ).hexdigest()[:10].upper()


@app.route("/replace/<arxiv_id>", methods=["GET", "POST"])
@csrf.exempt
def replace_paper(arxiv_id):
    """Stub for the paper-version-replacement flow.  GET renders the
    upload form (filename, summary of changes), POST shows the queued
    ticket and the next-version id (vN+1)."""
    paper = Paper.query.filter_by(arxiv_id=arxiv_id).first()
    if not paper:
        abort(404)
    summary = (request.values.get("summary") or "").strip()[:500]
    submitted = request.method == "POST"
    ticket = _replace_ticket_for(arxiv_id) if submitted else ""
    try:
        versions = paper.versions if hasattr(paper, "versions") else []
        if isinstance(versions, list) and versions:
            cur = versions[-1].get("version", "v1")
        else:
            cur = "v1"
    except Exception:
        cur = "v1"
    m = re.match(r"v(\d+)", cur or "v1")
    next_version = f"v{int(m.group(1)) + 1}" if m else "v2"
    return render_template(
        "replace_paper.html",
        paper=paper, summary=summary, submitted=submitted, ticket=ticket,
        current_version=cur, next_version=next_version,
        announce_at=(SERVICE_BUILD_TS + timedelta(days=1)
                     ).strftime("%Y-%m-%d"),
    )


@app.route("/api/orcid/link", methods=["GET", "POST"])
@csrf.exempt
def api_orcid_link():
    """Deterministic ORCID-resolution stub.

    Returns JSON describing the link state for a given (email, orcid)
    pair.  The 'verified' flag is a function of the inputs so the same
    request always returns the same answer."""
    email = (request.values.get("email") or "").strip().lower()
    orcid_id = (request.values.get("orcid") or "").strip()
    if not orcid_id:
        seed = hashlib.sha256(("orcid|" + (email or "anon")).encode()).hexdigest()
        digits = re.sub(r"\D", "", seed)[:16].ljust(16, "0")
        orcid_id = f"{digits[:4]}-{digits[4:8]}-{digits[8:12]}-{digits[12:16]}"
    verified = bool(re.match(r"^\d{4}-\d{4}-\d{4}-\d{3}[0-9X]$", orcid_id))
    link_token = "orcid_link_" + hashlib.sha256(
        ("arxiv-orcid|" + email + "|" + orcid_id).encode()
    ).hexdigest()[:24]
    return jsonify({
        "email": email,
        "orcid": orcid_id,
        "verified": verified,
        "link_token": link_token,
        "linked_at": SERVICE_BUILD_TS.strftime("%Y-%m-%dT00:00:00Z"),
        "profile_url": "https://orcid.org/" + orcid_id,
    })


# Static directory of major venues — keeps /api/conference/<conf> stable
# and lets agents discover venue keys from /conferences.
CONFERENCE_DIRECTORY = {
    "neurips":   {"name": "NeurIPS", "field": "Machine Learning",
                  "primary_subject": "cs.LG",
                  "url": "https://neurips.cc/",
                  "deadline_month": "May", "notification_month": "September"},
    "icml":      {"name": "ICML", "field": "Machine Learning",
                  "primary_subject": "cs.LG",
                  "url": "https://icml.cc/",
                  "deadline_month": "January", "notification_month": "May"},
    "iclr":      {"name": "ICLR", "field": "Representation Learning",
                  "primary_subject": "cs.LG",
                  "url": "https://iclr.cc/",
                  "deadline_month": "September", "notification_month": "January"},
    "cvpr":      {"name": "CVPR", "field": "Computer Vision",
                  "primary_subject": "cs.CV",
                  "url": "https://cvpr.thecvf.com/",
                  "deadline_month": "November", "notification_month": "March"},
    "iccv":      {"name": "ICCV", "field": "Computer Vision",
                  "primary_subject": "cs.CV",
                  "url": "https://iccv.thecvf.com/",
                  "deadline_month": "March", "notification_month": "July"},
    "eccv":      {"name": "ECCV", "field": "Computer Vision",
                  "primary_subject": "cs.CV",
                  "url": "https://eccv.ecva.net/",
                  "deadline_month": "March", "notification_month": "July"},
    "acl":       {"name": "ACL", "field": "Computational Linguistics",
                  "primary_subject": "cs.CL",
                  "url": "https://www.aclweb.org/",
                  "deadline_month": "February", "notification_month": "May"},
    "emnlp":     {"name": "EMNLP", "field": "Empirical NLP",
                  "primary_subject": "cs.CL",
                  "url": "https://www.emnlp.org/",
                  "deadline_month": "June", "notification_month": "October"},
    "naacl":     {"name": "NAACL", "field": "NLP — North-American chapter",
                  "primary_subject": "cs.CL",
                  "url": "https://www.naacl.org/",
                  "deadline_month": "December", "notification_month": "March"},
    "aaai":      {"name": "AAAI", "field": "Artificial Intelligence",
                  "primary_subject": "cs.AI",
                  "url": "https://aaai.org/",
                  "deadline_month": "August", "notification_month": "December"},
    "ijcai":     {"name": "IJCAI", "field": "Artificial Intelligence",
                  "primary_subject": "cs.AI",
                  "url": "https://www.ijcai.org/",
                  "deadline_month": "January", "notification_month": "April"},
    "kdd":       {"name": "KDD", "field": "Data Mining",
                  "primary_subject": "cs.LG",
                  "url": "https://www.kdd.org/",
                  "deadline_month": "February", "notification_month": "May"},
    "www":       {"name": "TheWebConf (WWW)", "field": "Web & Information Retrieval",
                  "primary_subject": "cs.IR",
                  "url": "https://www2024.thewebconf.org/",
                  "deadline_month": "October", "notification_month": "January"},
    "sigir":     {"name": "SIGIR", "field": "Information Retrieval",
                  "primary_subject": "cs.IR",
                  "url": "https://sigir.org/",
                  "deadline_month": "January", "notification_month": "April"},
    "uist":      {"name": "UIST", "field": "Human-Computer Interaction",
                  "primary_subject": "cs.HC",
                  "url": "https://uist.acm.org/",
                  "deadline_month": "April", "notification_month": "July"},
    "chi":       {"name": "CHI", "field": "Human-Computer Interaction",
                  "primary_subject": "cs.HC",
                  "url": "https://chi.acm.org/",
                  "deadline_month": "September", "notification_month": "December"},
}


@app.route("/api/conference/<conf>")
def api_conference(conf):
    """Lookup metadata for a known venue + sample related papers from
    the corpus (matched by primary_subject_code)."""
    key = (conf or "").strip().lower()
    info = CONFERENCE_DIRECTORY.get(key)
    if not info:
        return jsonify({
            "conference": key, "found": False,
            "known_conferences": sorted(CONFERENCE_DIRECTORY),
        }), 404
    subj = info["primary_subject"]
    sample_q = (
        Paper.query
        .filter(Paper.primary_subject_code == subj)
        .order_by(Paper.arxiv_id.asc())
        .limit(5)
    )
    samples = [{"arxiv_id": p.arxiv_id, "title": p.title} for p in sample_q]
    return jsonify({
        "conference": key, "found": True,
        "name": info["name"], "field": info["field"],
        "primary_subject": subj,
        "deadline_month": info["deadline_month"],
        "notification_month": info["notification_month"],
        "homepage": info["url"],
        "sample_papers": samples,
        "build_date": SERVICE_BUILD_TS.strftime("%Y-%m-%d"),
    })


@app.route("/conferences")
def conferences_index():
    """HTML directory of every conference /api/conference/<conf> knows."""
    rows = sorted(
        [(k, v["name"], v["field"], v["primary_subject"])
         for k, v in CONFERENCE_DIRECTORY.items()],
        key=lambda r: r[0],
    )
    return render_template("conferences.html", rows=rows)


# =======================================================================
# =======================================================================
# BENCHMARK SEED DATA
# =======================================================================

def seed_benchmark_users():
    """
    Create 4 benchmark users with pre-seeded library items, starred papers,
    and citation exports. Idempotent — check first user before running.
    """
    if User.query.filter_by(email="alice.j@test.com").first():
        return  # already seeded

    # Pin RNG + clock so library/star/export timestamps are deterministic.
    random.seed(20260501)
    NOW = MIRROR_REFERENCE_DATE

    def _get_paper(arxiv_id: str):
        return Paper.query.filter_by(arxiv_id=arxiv_id).first()

    # ------------------------------------------------------------------
    # alice.j — NLP / ML researcher, heavy library user
    # ------------------------------------------------------------------
    alice = User(
        email="alice.j@test.com",
        username="alice_j",
        full_name="Alice Johnson",
        affiliation="MIT CSAIL",
        bio="NLP researcher focused on contrastive learning and sentence embeddings.",
        orcid="0000-0001-0001-0001",
        password_hash=PINNED_HASH_TESTPASS,
        created_at=NOW - timedelta(days=365),
    )
    # password pinned via password_hash=PINNED_HASH_TESTPASS on the User(...) constructor
    db.session.add(alice)
    db.session.flush()

    alice_papers = [
        ("2104.08821", "Research"),   # SimCSE
        ("2011.05864", "Research"),   # Sentence Embeddings
        ("2004.04906", "Reading List"),  # DPR
        ("1905.01969", "Reading List"),  # Poly-encoder
        ("2303.08774", "To Read"),    # GPT-4 Technical Report
        ("2301.12345", "To Read"),    # NN Optimization
        ("2305.23456", "Research"),   # NN Low-Rank
        ("2309.34567", "Research"),   # Stochastic NN Opt
    ]
    for arxiv_id, folder in alice_papers:
        p = _get_paper(arxiv_id)
        if p:
            db.session.add(LibraryItem(
                user_id=alice.id, paper_id=p.id, folder=folder,
                added_at=NOW - timedelta(days=random.randint(1, 30))))

    alice_stars = ["2104.08821", "2011.05864", "2303.08774", "2401.00123"]
    for arxiv_id in alice_stars:
        p = _get_paper(arxiv_id)
        if p:
            db.session.add(StarredPaper(user_id=alice.id, paper_id=p.id,
                                        starred_at=NOW - timedelta(days=random.randint(1, 20))))

    db.session.commit()

    # Alice has a completed BibTeX export of her Research folder papers
    alice_research_ids = [
        _get_paper(aid).id for aid, folder in alice_papers
        if folder == "Research" and _get_paper(aid)
    ]
    if alice_research_ids:
        ex_alice = Export(
            user_id=alice.id,
            export_id="EX" + "20260101120000" + "001",
            format="bibtex",
            status="ready",
            paper_count=len(alice_research_ids),
            notes="Research papers export",
            created_at=NOW - timedelta(days=5),
        )
        db.session.add(ex_alice)
        db.session.flush()
        for pid in alice_research_ids:
            db.session.add(ExportItem(export_id=ex_alice.id, paper_id=pid))
        db.session.commit()

    # ------------------------------------------------------------------
    # bob.c — Computer Vision / Deep Learning, moderate library
    # ------------------------------------------------------------------
    bob = User(
        email="bob.c@test.com",
        username="bob_c",
        full_name="Bob Chen",
        affiliation="Stanford AI Lab",
        bio="Deep learning researcher specializing in computer vision and graph networks.",
        orcid="0000-0002-0002-0002",
        password_hash=PINNED_HASH_TESTPASS,
        created_at=NOW - timedelta(days=365),
    )
    # password pinned via password_hash=PINNED_HASH_TESTPASS on the User(...) constructor
    db.session.add(bob)
    db.session.flush()

    bob_papers = [
        ("2303.11234", "Reading List"),  # Visual Prompting
        ("2304.22345", "Reading List"),  # Panoptic Segmentation
        ("2401.00123", "Favorites"),     # GNN Molecular
        ("2401.00456", "Favorites"),     # Scalable GNN
        ("2401.00789", "Reading List"),  # Temporal GNN
        ("2604.08209", "To Review"),     # OmniJigsaw
    ]
    for arxiv_id, folder in bob_papers:
        p = _get_paper(arxiv_id)
        if p:
            db.session.add(LibraryItem(
                user_id=bob.id, paper_id=p.id, folder=folder,
                added_at=NOW - timedelta(days=random.randint(1, 45))))

    bob_stars = ["2303.11234", "2401.00123", "2401.00456"]
    for arxiv_id in bob_stars:
        p = _get_paper(arxiv_id)
        if p:
            db.session.add(StarredPaper(user_id=bob.id, paper_id=p.id,
                                        starred_at=NOW - timedelta(days=random.randint(1, 15))))

    db.session.commit()

    # Bob has an RIS export of his Favorites
    bob_fav_ids = [
        _get_paper(aid).id for aid, folder in bob_papers
        if folder == "Favorites" and _get_paper(aid)
    ]
    if bob_fav_ids:
        ex_bob = Export(
            user_id=bob.id,
            export_id="EX" + "20260115090000" + "002",
            format="ris",
            status="ready",
            paper_count=len(bob_fav_ids),
            notes="Favorites RIS export",
            created_at=NOW - timedelta(days=10),
        )
        db.session.add(ex_bob)
        db.session.flush()
        for pid in bob_fav_ids:
            db.session.add(ExportItem(export_id=ex_bob.id, paper_id=pid))
        db.session.commit()

    # ------------------------------------------------------------------
    # carol.d — Statistics / ML Theory, focused reader
    # ------------------------------------------------------------------
    carol = User(
        email="carol.d@test.com",
        username="carol_d",
        full_name="Carol Davis",
        affiliation="UC Berkeley Statistics",
        bio="Statistical ML researcher. Interested in Bayesian methods and diffusion models.",
        orcid="0000-0003-0003-0003",
        password_hash=PINNED_HASH_TESTPASS,
        created_at=NOW - timedelta(days=365),
    )
    # password pinned via password_hash=PINNED_HASH_TESTPASS on the User(...) constructor
    db.session.add(carol)
    db.session.flush()

    carol_papers = [
        ("2412.03134", "ML Theory"),   # Diffusion Noise
        ("2602.22486", "ML Theory"),   # Flow Matching
        ("2510.23199", "Reading List"), # Best Arm ID
        ("2512.12911", "Reading List"), # SVD for DNN
        ("2409.19567", "Reading List"), # math.OC paper
        ("2104.08821", "NLP"),          # SimCSE
        ("2011.05864", "NLP"),          # Sentence Embeddings
    ]
    for arxiv_id, folder in carol_papers:
        p = _get_paper(arxiv_id)
        if p:
            db.session.add(LibraryItem(
                user_id=carol.id, paper_id=p.id, folder=folder,
                added_at=NOW - timedelta(days=random.randint(1, 60))))

    carol_stars = ["2412.03134", "2602.22486", "2510.23199"]
    for arxiv_id in carol_stars:
        p = _get_paper(arxiv_id)
        if p:
            db.session.add(StarredPaper(user_id=carol.id, paper_id=p.id,
                                        starred_at=NOW - timedelta(days=random.randint(1, 25))))

    db.session.commit()

    # Carol has two ready exports (ML Theory BibTeX + NLP RIS) for disambiguation
    carol_theory_ids = [
        _get_paper(aid).id for aid, folder in carol_papers
        if folder == "ML Theory" and _get_paper(aid)
    ]
    carol_nlp_ids = [
        _get_paper(aid).id for aid, folder in carol_papers
        if folder == "NLP" and _get_paper(aid)
    ]
    if carol_nlp_ids:
        ex_carol_nlp = Export(
            user_id=carol.id,
            export_id="EX" + "20260110080000" + "003",
            format="ris",
            status="ready",
            paper_count=len(carol_nlp_ids),
            notes="NLP papers RIS",
            created_at=NOW - timedelta(days=15),
        )
        db.session.add(ex_carol_nlp)
        db.session.flush()
        for pid in carol_nlp_ids:
            db.session.add(ExportItem(export_id=ex_carol_nlp.id, paper_id=pid))

    if carol_theory_ids:
        ex_carol_ready = Export(
            user_id=carol.id,
            export_id="EX" + "20260120143000" + "004",
            format="bibtex",
            status="ready",
            paper_count=len(carol_theory_ids),
            notes="ML Theory papers BibTeX",
            created_at=NOW - timedelta(days=3),
        )
        db.session.add(ex_carol_ready)
        db.session.flush()
        for pid in carol_theory_ids:
            db.session.add(ExportItem(export_id=ex_carol_ready.id, paper_id=pid))
    db.session.commit()

    # ------------------------------------------------------------------
    # david.k — Quantum / Physics, small library
    # ------------------------------------------------------------------
    david = User(
        email="david.k@test.com",
        username="david_k",
        full_name="David Kim",
        affiliation="Caltech Physics",
        bio="Quantum information and quantum computing researcher.",
        orcid="0000-0004-0004-0004",
        password_hash=PINNED_HASH_TESTPASS,
        created_at=NOW - timedelta(days=365),
    )
    # password pinned via password_hash=PINNED_HASH_TESTPASS on the User(...) constructor
    db.session.add(david)
    db.session.flush()

    david_papers = [
        ("2312.17719", "Quantum"),    # quant-ph paper
        ("2402.17148", "Quantum"),    # quant-ph paper
        ("2410.19541", "Reading List"),  # quant-ph paper
        ("2303.08774", "Reading List"),  # GPT-4 (cross-domain interest)
        ("2401.00123", "Reading List"),  # GNN Molecular
    ]
    for arxiv_id, folder in david_papers:
        p = _get_paper(arxiv_id)
        if p:
            db.session.add(LibraryItem(
                user_id=david.id, paper_id=p.id, folder=folder,
                added_at=NOW - timedelta(days=random.randint(1, 30))))

    david_stars = ["2312.17719", "2402.17148"]
    for arxiv_id in david_stars:
        p = _get_paper(arxiv_id)
        if p:
            db.session.add(StarredPaper(user_id=david.id, paper_id=p.id,
                                        starred_at=NOW - timedelta(days=random.randint(1, 10))))

    db.session.commit()

    # David has a ready plaintext export of his starred papers
    david_star_ids = [
        _get_paper(aid).id for aid in david_stars if _get_paper(aid)
    ]
    if david_star_ids:
        ex_david = Export(
            user_id=david.id,
            export_id="EX" + "20260201110000" + "005",
            format="endnote",
            status="ready",
            paper_count=len(david_star_ids),
            notes="Starred quantum papers",
            created_at=NOW - timedelta(days=7),
        )
        db.session.add(ex_david)
        db.session.flush()
        for pid in david_star_ids:
            db.session.add(ExportItem(export_id=ex_david.id, paper_id=pid))
        db.session.commit()

    # ------------------------------------------------------------------
    # Alerts for disambiguation tasks
    # ------------------------------------------------------------------
    for u, alerts_list in [
        (alice, [("cs", "daily"), ("math", "weekly")]),
        (bob, [("cs", "daily"), ("physics", "weekly")]),
        (david, [("physics", "daily"), ("math", "weekly")]),
    ]:
        for j, (cat_code, freq) in enumerate(alerts_list):
            db.session.add(Alert(
                user_id=u.id, category_code=cat_code, frequency=freq,
                created_at=NOW - timedelta(days=90 + u.id * 10 + j),
            ))
    db.session.commit()

    print("  [+] Seeded 4 benchmark users (alice/bob/carol/david)")


# =======================================================================
# COMMUNITY COMMENTS + LIBRARY DEPTH
# =======================================================================

# Reference build date — defined near top of file; re-state here for
# context only. All seeded created_at / added_at values use this anchor.

# Academic-style comment templates with {title-keyword} placeholders.
# Phrased to read like real arXiv-style researcher feedback, not generic
# "great paper" filler.
_COMMENT_TEMPLATES = [
    ("Crisp framing", "Section 3 is the cleanest exposition of this problem I've seen in a while — would love to see the proof of Theorem 1 extended to the non-convex case."),
    ("Reproducibility?", "Has anyone managed to reproduce the headline numbers? My runs on a single A100 are about 4 points lower; curious whether it's the LR schedule."),
    ("Connection to prior work", "There seems to be a strong link with the line of work on amortised inference (e.g. Le et al., 2018). A brief comparison in the related work would help."),
    ("Ablation request", "Curious about the effect of removing the auxiliary loss in Section 4.2. The current Table 3 only varies the encoder depth."),
    ("Notation nitpick", "Minor — in eq. (7), the index j is reused for both the attention head and the layer. Cost me ten minutes to disentangle."),
    ("Code release?", "Is there a code release planned? The trick in §3.4 sounds straightforward but the devil tends to be in the bucketed batching."),
    ("Theoretical concern", "The assumption that the noise is sub-Gaussian seems strong for the application domain you cite. Does the bound still hold under heavier tails?"),
    ("Empirical robustness", "Would love to see error bars across seeds. With a baseline this close, single-seed numbers are hard to interpret."),
    ("Excellent figures", "Figures 2 and 5 are really effective at conveying the geometric intuition. I'll be stealing this presentation style for my next paper."),
    ("Extension idea", "Have you thought about combining this with importance sampling? It would address the variance issue raised in the discussion."),
    ("Potential issue", "I think the proof of Lemma 2 implicitly requires the kernel to be Mercer; this should probably be stated explicitly."),
    ("Followup question", "What would change if the loss were replaced by a Wasserstein distance? The current KL formulation might be unnecessarily restrictive."),
    ("Cross-domain relevance", "Coming from a computer vision background, I found §5 surprisingly applicable to optical flow estimation. Have the authors considered that setting?"),
    ("Compute budget", "Out of curiosity, what was the total compute for the experiments? The appendix only reports per-run cost."),
    ("Limitation acknowledged", "Glad to see the failure mode in Figure 8 honestly reported. Many recent papers would have buried this."),
    ("Survey-worthy", "Could become the canonical reference for this subtopic. I've started recommending it to graduate students in my reading group."),
    ("Statistical significance", "With n=3 seeds and overlapping confidence intervals on CIFAR-100, the claim of 'consistent improvement' may be overstated."),
    ("Baseline choice", "The comparison against [Liu 2024] is a strong baseline, but the authors omit the more recent [Chen 2025] which reports better numbers."),
    ("Lovely analysis", "The asymptotic analysis in Appendix B is the highlight of the paper for me. Reminds me of the classical Sieve estimator literature."),
    ("Confusing notation", "The use of \\theta for two different parameter spaces in Sections 3 and 4 was confusing on first read."),
    ("Real-world deployment", "We tried a variant of this approach in production. The big practical issue is calibration drift over a 2-week window."),
    ("Thanks for sharing", "Thanks for posting the v2 with the corrected proof — that helps a lot. Looking forward to the journal version."),
    ("Dataset bias", "I worry the conclusions are dataset-specific. The phenomenon described in §6 disappears on our internal benchmark."),
    ("Suggested baseline", "A simple nearest-neighbour baseline with the same features achieves ~85% of the reported accuracy in our hands; might be worth including."),
    ("Hardware constraints", "Have you tried a quantised version? The memory footprint as currently described is prohibitive for edge deployment."),
    ("Implementation detail", "If anyone is trying to reimplement: gradient clipping is essential, even though it's only mentioned in passing on page 6."),
    ("Conceptual clarity", "This is the first paper that has clarified for me the difference between the two interpretations of the regularisation term. Excellent writing."),
    ("Open question", "Does the analysis extend to non-stationary distributions? That seems the obvious next step."),
    ("Possible bug", "Equation (15) might have a sign error — running the published code I had to flip the gradient to reproduce Table 2."),
    ("Practitioner perspective", "Speaking as a practitioner: the proposed method is roughly 3x slower at inference than the baseline. Worth weighing against the accuracy gains."),
    ("Citation missing", "An earlier formulation of this idea appears in [Goodfellow et al., 2014, Appendix C]. Worth a citation."),
    ("Beautiful proof", "Proof of Proposition 5 is elegant — the use of the duality argument really clarifies why the result holds."),
    ("Empirical questions", "Curious how the method behaves under distribution shift. The IID assumption in §2 might be too strong for many applications."),
    ("Documentation request", "The hyperparameter table in the appendix is a model for how to report experimental details. Thank you."),
    ("Cross-validation", "Did the authors consider k-fold CV instead of a single train/val/test split? With this dataset size, single-split numbers can be noisy."),
    ("Reproducibility kit", "Released a Docker image reproducing the main table at github.com/example/repro — happy to take pull requests."),
    ("Initialisation matters", "We found the proposed method very sensitive to the choice of initialisation. Worth a stability paragraph in the camera-ready."),
    ("Sample efficiency", "The sample-efficiency claim in §7 looks promising. Have you measured the regret bound empirically?"),
    ("Excellent overview", "This paper now sits at the top of my reading list for new students entering the field. Concise yet thorough."),
    ("Energy/efficiency", "Would be valuable to report the energy cost of training. Camera-ready maybe?"),
    # R3 — additional 40 templates so the comment seed has more variety
    # before it starts wrapping around.
    ("Theory vs practice", "The §3 bound is tight in theory but for n ~ 10^4 the constants dominate; the empirical regime is far from asymptotic."),
    ("Choice of metric", "Reporting BLEU alone obscures the fluency drop reviewers flagged at NeurIPS '25. Consider chrF or a human eval."),
    ("Latent space probe", "Did the authors run a linear probe on the learned representations? That would clarify whether the gains are from features or the head."),
    ("Domain transfer", "We tried this on medical imaging and the gains shrink to ~0.6%. Domain-specific pretraining matters more than the architecture here."),
    ("Hyperparameter sensitivity", "Section 6.2 calls the method 'robust' but the search range is narrow. A wider sweep would be more convincing."),
    ("Distillation candidate", "This would make an excellent teacher for distillation — has anyone tried a smaller student variant?"),
    ("Calibration concern", "ECE is not reported. The reliability diagram in our reproduction shows the model is over-confident on tail classes."),
    ("Streaming setting", "Could the algorithm be adapted to a streaming regime? Many real workloads can't afford the full pass."),
    ("Inductive bias", "It looks like the architectural choice in §4 encodes a strong inductive bias toward locality. Worth foregrounding."),
    ("Loss landscape", "The Hessian eigenspectrum plot in Appendix D is gorgeous — would love to see this for the baseline too."),
    ("Annotation quality", "How were the gold labels collected? Some borderline cases in Figure 4 look ambiguous."),
    ("Pretraining cost", "The 4M GPU-hour pretraining budget makes replication hard. Could the authors release the checkpoint?"),
    ("Stability question", "Training stability is mentioned in passing — what fraction of seeds diverged? That number matters for downstream users."),
    ("Length bias", "Models in the family tend to favor longer outputs. Is the length-normalised metric in Table 2 a fair apples-to-apples comparison?"),
    ("Adversarial robustness", "Have you evaluated against PGD-20 or AutoAttack? Clean accuracy alone is not the right gauge."),
    ("Information-theoretic view", "Equation (12) is essentially a rate-distortion bound. A pointer to the Tishby line of work would help readers."),
    ("Tokenizer matters", "Switching the tokenizer from BPE to unigram halved the gap in our hands. Worth an ablation."),
    ("Inference latency", "End-to-end latency on T4 hardware would be useful — many readers don't have an A100 available."),
    ("Privacy implications", "If the model memorises training data as Figure 9 suggests, the privacy implications need discussion."),
    ("Open-vocabulary", "Section 5 hints at an open-vocabulary extension but doesn't fully follow through. Excited for a follow-up."),
    ("Multi-task transfer", "We tried fine-tuning on three downstream tasks and only one transferred. The pretraining objective may be too narrow."),
    ("Curriculum design", "The curriculum schedule in §3.5 looks ad-hoc. A principled annealing schedule might help reproducibility."),
    ("Negative results", "Appreciate that the authors report the failure on the synthetic benchmark — too rare in this venue."),
    ("Symbolic component", "Combining the neural network with the symbolic solver feels promising. Has anyone benchmarked against pure LLM tool use?"),
    ("Pruning angle", "The sparsity pattern in Figure 7 suggests a magnitude-pruning baseline would be competitive."),
    ("Long-context", "Does the method extend beyond the 8k context window? The attention pattern in Appendix C suggests so."),
    ("Continual learning", "How does the model handle continual streams without catastrophic forgetting? §8 only addresses single-pass training."),
    ("Multilingual evaluation", "English-only evaluation makes it hard to claim the result generalises. mC4 or FLORES would be welcome additions."),
    ("Mechanistic interpretation", "The circuit analysis in §6 reminded me of the Anthropic 'IOI circuit' line. Worth a citation."),
    ("Routing collapse", "We observed routing collapse with the same MoE configuration. Did the authors apply auxiliary load balancing?"),
    ("Code quality", "The released repo is unusually clean — typed configs, frozen seeds, deterministic mode. Set the bar for the field."),
    ("Annotation interface", "The interface used to collect annotations is shown in Appendix E. Is it open-sourced anywhere?"),
    ("Fine-grained eval", "The aggregate score hides a 7-point regression on the hardest split. Worth reporting per-bucket numbers."),
    ("Memory wall", "Once batch size > 64 the activation memory explodes. Gradient checkpointing should be mentioned for practitioners."),
    ("Counterfactual probe", "The counterfactual examples in Table 4 are not very natural. Would synthetic edits via LLM rewriting be cleaner?"),
    ("Long-tail performance", "Performance on the rare-class slice (Figure 10) is what I really care about. Could the authors report mean per-class accuracy?"),
    ("Compute-equal comparison", "When normalised by FLOPs, baseline B nearly matches the proposed method. The headline gain is mostly extra compute."),
    ("Annotation noise", "The reported label noise of 3% looks optimistic. We hand-audited 100 examples and saw closer to 9%."),
    ("Encoder/decoder split", "Have you tried freezing the encoder and only fine-tuning the decoder? The §7 study is suggestive."),
    ("Stochastic depth", "Stochastic depth at the values reported in Table 6 is unusual. A sweep would help readers transfer to other backbones."),
]


def _comment_offset_days(idx: int) -> int:
    """Deterministic, evenly spread offsets so comments don't all share a date."""
    # 1..30 days back from reference, but skip the canonical 0
    return (idx * 7 + 3) % 30 + 1


def seed_community_extras():
    """Populate community comments + extra library items so the discussion
    and library surfaces feel populated.

    Gated so a fully-seeded DB skips this entirely (preserves byte-identical
    reset). Uses MIRROR_REFERENCE_DATE for all timestamps.
    """
    if Comment.query.first() is not None:
        return  # already seeded

    users = User.query.order_by(User.id).all()
    if not users:
        return
    # Map by username for stable selection. seed_benchmark_users runs first
    # so we get demouser + alice/bob/carol/david.
    by_name = {u.username: u for u in users}
    commenter_pool = [
        by_name.get(n) for n in
        ("alice_j", "bob_c", "carol_d", "david_k", "demouser")
        if by_name.get(n) is not None
    ]
    if not commenter_pool:
        return

    # ------------------------------------------------------------------
    # Pick papers to host comments. Stable ordering by arxiv_id so the
    # selection doesn't drift across rebuilds.
    # ------------------------------------------------------------------
    candidate_papers = (
        Paper.query
        .filter(Paper.abstract != "")
        .order_by(Paper.arxiv_id)
        .limit(3500)
        .all()
    )
    if not candidate_papers:
        return

    import random as _r
    rng = _r.Random(20260601)

    # R3 — wider coverage: ~250 distinct papers × ~2.2 comments avg
    # → ~550 comments total. Plus reply-style chains (Re: prefix +
    # @user mention) to make threads feel conversational.
    # R5 — push comments past 2000 across ~950 distinct papers (avg ~2.2 per paper).
    n_papers = min(950, len(candidate_papers))
    target_papers = rng.sample(candidate_papers, n_papers)

    comment_idx = 0
    for paper in target_papers:
        # 1-4 comments per paper, biased toward 1-2 (long tail of 3-4
        # produces the visible threads).
        n_comments = rng.choices([1, 1, 2, 2, 2, 3, 3, 4], k=1)[0]
        last_user_id = None
        prev_user_name = None
        prev_title = ""
        for ci in range(n_comments):
            tmpl = _COMMENT_TEMPLATES[comment_idx % len(_COMMENT_TEMPLATES)]
            title, body = tmpl
            # Avoid two consecutive comments from the same user on one paper
            avail = [u for u in commenter_pool if u.id != last_user_id] or commenter_pool
            user = rng.choice(avail)
            offset_days = _comment_offset_days(comment_idx)
            created_at = MIRROR_REFERENCE_DATE - timedelta(
                days=offset_days, hours=(comment_idx * 13) % 24,
                minutes=(comment_idx * 7) % 60,
            )
            # Pull out a short keyword from the paper title to make the body
            # feel tied to its host paper (purely cosmetic; no semantic logic).
            title_words = [w for w in re.split(r"\W+", paper.title or "") if len(w) > 5]
            anchor = title_words[comment_idx % len(title_words)] if title_words else ""
            body_final = body
            title_final = title
            # ci==0 → top-level comment anchored to paper keyword.
            # ci>=1 → reply chain: "Re: <prev title>" + @prev_user mention.
            if ci == 0:
                if anchor:
                    body_final = f"On '{anchor}': {body}"
            else:
                title_final = f"Re: {prev_title}" if prev_title else f"Re: comment"
                body_final = f"@{prev_user_name} {body}"
            rating = rng.choice([0, 0, 0, 3, 4, 4, 5])
            db.session.add(Comment(
                user_id=user.id,
                paper_id=paper.id,
                title=title_final,
                body=body_final,
                rating=rating,
                created_at=created_at,
            ))
            last_user_id = user.id
            prev_user_name = user.username
            prev_title = title
            comment_idx += 1
    db.session.commit()
    n_comments_total = Comment.query.count()
    print(f"  [+] Seeded {n_comments_total} community comments on {n_papers} papers")

    # ------------------------------------------------------------------
    # R3 — library depth: bring library_items from 72 to ~225.
    # Each commenter gets 22-32 additional saves spread across folders so
    # the /library view feels lived-in and large enough to support
    # find-by-folder / find-by-note tasks.
    # ------------------------------------------------------------------
    folder_choices_by_user = {
        "alice_j": ["Reading List", "Research", "To Read", "NLP", "Agents", "Survey"],
        "bob_c":   ["Reading List", "Favorites", "To Review", "Vision", "3D", "Robotics"],
        "carol_d": ["Reading List", "ML Theory", "Diffusion", "Stats", "Optimization"],
        "david_k": ["Reading List", "Quantum", "Physics", "Cross-domain", "Hardware"],
        "demouser": ["Reading List", "Favorites", "To Read", "Reference"],
    }
    # Skip papers users already have so the UniqueConstraint never fires.
    extra_added = 0
    for user in commenter_pool:
        folders = folder_choices_by_user.get(user.username, ["Reading List"])
        existing_pids = {li.paper_id for li in user.library_items}
        # Pull a wider window per user so the picks don't overlap heavily.
        window = 250
        offset = (user.id * 421) % max(1, len(candidate_papers) - window)
        picks = candidate_papers[offset:offset + window]
        rng2 = _r.Random(20260602 + user.id)
        rng2.shuffle(picks)
        want = rng2.randint(160, 195)
        added_for_user = 0
        for paper in picks:
            if added_for_user >= want:
                break
            if paper.id in existing_pids:
                continue
            folder = folders[added_for_user % len(folders)]
            note_idx = (added_for_user + user.id) % 8
            note = [
                "",
                "Re-read for the lit review",
                "Possible related work for current project",
                "Mentioned at last week's reading group",
                "Check the appendix for the proof technique",
                "Recommended by advisor — high priority",
                "Cited in the recent ICLR position paper",
                "Useful for the §3 baseline",
            ][note_idx]
            added_at = MIRROR_REFERENCE_DATE - timedelta(
                days=(added_for_user * 3 + user.id * 11) % 180,
                hours=(added_for_user * 11) % 24,
                minutes=(added_for_user * 13) % 60,
            )
            db.session.add(LibraryItem(
                user_id=user.id,
                paper_id=paper.id,
                folder=folder,
                note=note,
                added_at=added_at,
            ))
            existing_pids.add(paper.id)
            added_for_user += 1
            extra_added += 1
    db.session.commit()
    n_lib = LibraryItem.query.count()
    print(f"  [+] Seeded {extra_added} extra library items (total {n_lib})")

    # ------------------------------------------------------------------
    # R5 — saved searches + paper-update subscriptions across the
    # benchmark users so the /alerts and /abs notify surfaces aren't
    # empty by default. All timestamps anchored to MIRROR_REFERENCE_DATE.
    # ------------------------------------------------------------------
    saved_search_specs = [
        ("alice_j",  "Quantum-inspired transformers", "quantum", "all",      "cs",       "weekly"),
        ("alice_j",  "SimCSE follow-ups",             "contrastive learning sentence embeddings", "all", "cs.CL", "daily"),
        ("alice_j",  "Retrieval-augmented LLMs",      "retrieval augmented generation", "abstract", "cs.CL", "weekly"),
        ("bob_c",    "Visual prompting",              "visual prompting", "title", "cs.CV",     "weekly"),
        ("bob_c",    "3D Gaussian splatting",         "gaussian splatting", "all", "cs.CV",    "daily"),
        ("carol_d",  "Flow matching surveys",         "flow matching", "all", "stat.ML",       "monthly"),
        ("carol_d",  "Diffusion convergence",         "diffusion model convergence", "all", "stat", "weekly"),
        ("david_k",  "Surface code thresholds",       "surface code threshold", "all", "quant-ph", "weekly"),
        ("david_k",  "Quantum error correction",      "quantum error correction", "abstract", "quant-ph", "daily"),
        ("demouser", "ML for healthcare",             "medical imaging", "all", "cs",           "weekly"),
    ]
    ss_added = 0
    for ui, (uname, name, q, field, cat, freq) in enumerate(saved_search_specs):
        u = by_name.get(uname)
        if not u:
            continue
        db.session.add(SavedSearch(
            user_id=u.id,
            name=name,
            query=q,
            field=field,
            category=cat,
            frequency=freq,
            created_at=MIRROR_REFERENCE_DATE - timedelta(days=(ui * 7) % 90 + 3),
        ))
        ss_added += 1
    db.session.commit()
    print(f"  [+] Seeded {ss_added} saved searches")

    # Paper update subscriptions: pin a handful per user to known seed papers
    notify_specs = [
        ("alice_j", "2104.08821"), ("alice_j", "2303.08774"),
        ("alice_j", "2011.05864"),
        ("bob_c",   "2303.11234"), ("bob_c",   "2401.00123"),
        ("bob_c",   "2604.08209"),
        ("carol_d", "2412.03134"), ("carol_d", "2602.22486"),
        ("david_k", "2401.00789"),
        ("demouser","2104.08821"),
    ]
    pun_added = 0
    for ui, (uname, aid) in enumerate(notify_specs):
        u = by_name.get(uname)
        if not u:
            continue
        p = Paper.query.filter_by(arxiv_id=aid).first()
        if not p:
            continue
        existing = PaperUpdateNotification.query.filter_by(
            user_id=u.id, paper_id=p.id).first()
        if existing:
            continue
        db.session.add(PaperUpdateNotification(
            user_id=u.id,
            paper_id=p.id,
            email=u.email,
            created_at=MIRROR_REFERENCE_DATE - timedelta(days=(ui * 5) % 60 + 1),
        ))
        pun_added += 1
    db.session.commit()
    print(f"  [+] Seeded {pun_added} paper-update notifications")

def backfill_paper_gaps():
    """Patch pre-existing Paper rows with empty authors / abstract so the
    /abs, listing, and /list/<code>/new views never render blank content.

    Safe to run every startup: only rewrites rows whose authors_json is
    empty ('[]'/''/None) or whose abstract is empty. No other fields are
    touched.
    """
    try:
        empty_author_rows = Paper.query.filter(
            or_(Paper.authors_json == "[]",
                Paper.authors_json == "",
                Paper.authors_json.is_(None))
        ).all()
        n_auth = 0
        for p in empty_author_rows:
            authors = _synthesize_authors(p.arxiv_id or "")
            if authors:
                p.authors_json = json.dumps(authors)
                p.n_authors = len(authors)
                n_auth += 1
        empty_abs_rows = Paper.query.filter(
            or_(Paper.abstract == "", Paper.abstract.is_(None))
        ).all()
        n_abs = 0
        for p in empty_abs_rows:
            text = _synthesize_abstract(p.title or "",
                                        p.primary_subject_code or "",
                                        p.primary_subject or "")
            if text:
                p.abstract = text
                n_abs += 1
        if n_auth or n_abs:
            db.session.commit()
            print(f"  [+] Backfilled {n_auth} author lists and {n_abs} abstracts")
    except Exception as e:
        db.session.rollback()
        print(f"  ! backfill_paper_gaps failed: {e}")


def normalize_paper_metadata():
    """Normalize known duplicated LaTeX/text fragments in existing DB rows."""
    try:
        changed = 0
        for paper in Paper.query.all():
            for field in ("title", "abstract", "comments"):
                current = getattr(paper, field) or ""
                cleaned = _clean_arxiv_metadata_text(current)
                if cleaned != current:
                    setattr(paper, field, cleaned)
                    changed += 1
        if changed:
            db.session.commit()
            print(f"  [+] Normalized {changed} arXiv metadata fields")
    except Exception as e:
        db.session.rollback()
        print(f"  ! normalize_paper_metadata failed: {e}")


def ensure_affiliation_column():
    """Ensure newer columns exist on older DBs (idempotent migration).

    Covers R3 (author_affiliations_json) plus R4 (msc_class, acm_class,
    report_no) additions to the papers table.
    """
    try:
        from sqlalchemy import text
        cols = db.session.execute(text(
            "PRAGMA table_info(papers)"
        )).fetchall()
        have = {c[1] for c in cols}
        additions = [
            ("author_affiliations_json", "TEXT DEFAULT '[]'"),
            ("msc_class", "VARCHAR(400) DEFAULT ''"),
            ("acm_class", "VARCHAR(400) DEFAULT ''"),
            ("report_no", "VARCHAR(200) DEFAULT ''"),
            ("paper_version", "VARCHAR(8) DEFAULT 'v1'"),
            ("license", "VARCHAR(80) DEFAULT 'arXiv-perpetual'"),
            ("submitter_email_masked", "VARCHAR(120) DEFAULT ''"),
            ("computer_classification", "VARCHAR(200) DEFAULT ''"),
        ]
        added = []
        for col, decl in additions:
            if col not in have:
                db.session.execute(text(
                    f"ALTER TABLE papers ADD COLUMN {col} {decl}"))
                added.append(col)
        if added:
            db.session.commit()
            print(f"  [+] Added papers columns: {', '.join(added)}")
    except Exception as e:
        db.session.rollback()
        print(f"  ! ensure_affiliation_column failed: {e}")


def backfill_affiliations():
    """Populate author_affiliations_json for every paper that lacks it."""
    try:
        rows = Paper.query.filter(
            or_(Paper.author_affiliations_json == "[]",
                Paper.author_affiliations_json == "",
                Paper.author_affiliations_json.is_(None))
        ).all()
        n = 0
        for p in rows:
            authors = p.get_authors()
            if not authors:
                continue
            p.author_affiliations_json = json.dumps(
                _affiliations_for_authors(authors)
            )
            n += 1
        if n:
            db.session.commit()
            print(f"  [+] Backfilled affiliations for {n} papers")
    except Exception as e:
        db.session.rollback()
        print(f"  ! backfill_affiliations failed: {e}")


def backfill_provenance_fields():
    """R5 — populate paper_version / license / submitter_email_masked /
    computer_classification for every paper that still has empty / default
    values. Deterministic; idempotent (no-op once filled).
    """
    try:
        rows = Paper.query.filter(
            or_(Paper.submitter_email_masked == "",
                Paper.submitter_email_masked.is_(None))
        ).all()
        n = 0
        for p in rows:
            authors = p.get_authors()
            first_author = authors[0] if authors else ""
            versions = p.get_versions()
            p.paper_version = _derive_paper_version(p.arxiv_id or "", versions)
            p.license = _derive_license(p.arxiv_id or "")
            p.submitter_email_masked = _derive_submitter_email(
                p.arxiv_id or "", first_author
            )
            p.computer_classification = _derive_computer_classification(
                p.primary_subject_code or "", p.primary_category_code or ""
            )
            n += 1
        if n:
            db.session.commit()
            print(f"  [+] Backfilled R5 provenance for {n} papers")
    except Exception as e:
        db.session.rollback()
        print(f"  ! backfill_provenance_fields failed: {e}")


def normalize_seed_db_layout():
    """Re-emit indexes in alpha order + VACUUM so rebuilds are byte-identical.

    SQLAlchemy emits CREATE INDEX from a Python set, which iterates in id()
    order — non-deterministic across processes. That shifts page bytes in
    sqlite_schema even when row data matches. Drop & re-create indexes in a
    stable alphabetic order, then VACUUM to repack pages.

    Gated on a sentinel column-count check: only runs the first time the seed
    DB is built (when the heaviest seed function has just landed rows). On
    warm restarts that find an existing populated DB this is a no-op.
    """
    try:
        conn = db.engine.connect()
        # R7 — composite indexes for the listing-by-category + year hot
        # paths. CREATE INDEX IF NOT EXISTS so a warm restart is a no-op.
        # Drop-and-recreate below resets these in alpha order with all the
        # others, so adding them here doesn't break byte-identical rebuilds.
        for ddl in (
            "CREATE INDEX IF NOT EXISTS ix_papers_cat_year "
            "ON papers(primary_category_code, submitted_year)",
            "CREATE INDEX IF NOT EXISTS ix_papers_subj_year "
            "ON papers(primary_subject_code, submitted_year)",
            "CREATE INDEX IF NOT EXISTS ix_papers_cat_date "
            "ON papers(primary_category_code, submitted_date)",
            "CREATE INDEX IF NOT EXISTS ix_papers_arxiv_id_year "
            "ON papers(arxiv_id, submitted_year)",
        ):
            conn.execute(text(ddl))
        conn.commit()
        idx_rows = conn.execute(text(
            "SELECT name, sql FROM sqlite_master "
            "WHERE type='index' AND name LIKE 'ix_%'"
        )).fetchall()
        # Drop in whatever order, recreate sorted by name.
        for name, _sql in idx_rows:
            conn.execute(text(f"DROP INDEX IF EXISTS {name}"))
        for name, sql in sorted(idx_rows, key=lambda r: r[0]):
            if sql:
                conn.execute(text(sql))
        conn.commit()
        # VACUUM cannot run inside a transaction with SQLAlchemy autobegin.
        # Use a fresh raw connection and isolation_level=None.
        raw = db.engine.raw_connection()
        try:
            raw.isolation_level = None
            cur = raw.cursor()
            cur.execute("VACUUM")
            cur.close()
        finally:
            raw.close()
        print(f"  [+] Normalized seed DB layout ({len(idx_rows)} indexes "
              f"re-emitted, VACUUM done)")
    except Exception as e:
        print(f"  ! normalize_seed_db_layout failed: {e}")


# =======================================================================
# R2-R10 DEEPENING — added 2026-05-27 (depth-from-zero recovery)
# Each round below adds 6+ `rN_` markers + new routes / templates / data
# sources. Routes are byte-deterministic (md5(stable_key) seeding).
# =======================================================================

import hashlib as _r2_hashlib

def _rN_seed(*parts) -> int:
    """Deterministic integer seed from a stable key — never use Python hash()."""
    key = '|'.join(str(p) for p in parts)
    return int(_r2_hashlib.md5(key.encode('utf-8')).hexdigest()[:8], 16)

def _rN_choice(seq, *parts):
    if not seq: return None
    return seq[_rN_seed(*parts) % len(seq)]

# ============================================================
# R2: PDF inline reader + MathJax formula rendering + citation graph
# ============================================================
def r2_pdf_inline_pages(arxiv_id):
    """Synthesize a deterministic number of PDF pages for inline reader."""
    n = 6 + (_rN_seed('r2_pdf', arxiv_id) % 18)  # 6-23 pages
    return [{'page': i+1, 'word_count': 280 + (_rN_seed('r2_pdf_pg', arxiv_id, i) % 320)} for i in range(n)]

def r2_mathjax_formulas(arxiv_id):
    base = ['E=mc^2', '\\nabla \\cdot E = \\rho/\\epsilon_0', 'P(A|B)=P(B|A)P(A)/P(B)',
            '\\int_0^\\infty e^{-x^2}dx=\\frac{\\sqrt{\\pi}}{2}', 'O(n \\log n)',
            '\\mathcal{L}=-\\log p_\\theta(y|x)', '\\sum_{i=1}^n x_i^2']
    k = 2 + (_rN_seed('r2_formula', arxiv_id) % 4)
    return [_rN_choice(base, 'r2_f', arxiv_id, i) for i in range(k)]

def r2_citation_graph(arxiv_id):
    """Build a tiny ego-graph: {nodes:[{id,label}], edges:[{src,dst}]}."""
    seed = _rN_seed('r2_cg', arxiv_id)
    n_in = 3 + (seed % 5)
    n_out = 2 + ((seed >> 4) % 4)
    nodes = [{'id': arxiv_id, 'label': arxiv_id, 'kind': 'self'}]
    edges = []
    for i in range(n_in):
        nid = f'{arxiv_id}.in{i:02d}'
        nodes.append({'id': nid, 'label': f'cites {arxiv_id} ({i+1})', 'kind': 'in'})
        edges.append({'src': nid, 'dst': arxiv_id})
    for i in range(n_out):
        nid = f'{arxiv_id}.out{i:02d}'
        nodes.append({'id': nid, 'label': f'cited by {arxiv_id} ref {i+1}', 'kind': 'out'})
        edges.append({'src': arxiv_id, 'dst': nid})
    return {'nodes': nodes, 'edges': edges, 'n_in': n_in, 'n_out': n_out}

@app.route('/pdf-inline/<arxiv_id>')
def r2_pdf_inline_view(arxiv_id):
    p = Paper.query.filter_by(arxiv_id=arxiv_id).first_or_404()
    pages = r2_pdf_inline_pages(arxiv_id)
    formulas = r2_mathjax_formulas(arxiv_id)
    return render_template('r2_pdf_inline.html', paper=p, pages=pages, formulas=formulas)

@app.route('/api/r2/citation-graph/<arxiv_id>')
def r2_api_citation_graph(arxiv_id):
    Paper.query.filter_by(arxiv_id=arxiv_id).first_or_404()
    return jsonify(r2_citation_graph(arxiv_id))

@app.route('/api/r2/mathjax/<arxiv_id>')
def r2_api_mathjax(arxiv_id):
    return jsonify({'arxiv_id': arxiv_id, 'formulas': r2_mathjax_formulas(arxiv_id)})

# ============================================================
# R3: Author profile depth — h-index, citation count, ORCID, coauthor graph
# ============================================================
def r3_author_h_index(name):
    return 5 + (_rN_seed('r3_hidx', name) % 40)

def r3_author_citation_count(name):
    return 50 + (_rN_seed('r3_cite', name) % 5000)

def r3_author_orcid(name):
    h = _r2_hashlib.md5(('r3_orcid|' + name).encode()).hexdigest()
    groups = [h[i:i+4] for i in (0, 4, 8, 12)]
    digits = ''.join(str(int(g, 16))[:4].zfill(4) for g in groups)[:16]
    return f'{digits[0:4]}-{digits[4:8]}-{digits[8:12]}-{digits[12:16]}'

def r3_author_coauthor_graph(name):
    seed = _rN_seed('r3_cg', name)
    n = 4 + (seed % 8)
    coauthors = [f'Coauthor {chr(65 + (seed >> (i*2)) % 26)}. {chr(65 + (seed >> (i*3)) % 26)}.' for i in range(n)]
    edges = [{'src': name, 'dst': c, 'weight': 1 + (_rN_seed('r3_w', name, c) % 9)} for c in coauthors]
    return {'nodes': [name] + coauthors, 'edges': edges}

@app.route('/a/<path:name>/profile')
def r3_author_profile(name):
    stats = {
        'h_index': r3_author_h_index(name),
        'citations': r3_author_citation_count(name),
        'orcid': r3_author_orcid(name),
        'coauthor_graph': r3_author_coauthor_graph(name),
    }
    # Visual context: headshot avatar + institution banner + featured papers.
    author_papers = (Paper.query
                     .filter(Paper.authors_json.like(f'%"{name}"%'))
                     .order_by(Paper.submitted_year.desc())
                     .limit(6).all())
    affiliation = _synthesize_affiliation(name)
    visual = {
        "headshot": _avatar_filename(name),
        "institution_banner": _category_banner_filename("cs"),
        "institution_accent": _institution_accent(affiliation),
        "affiliation": affiliation,
        "featured_papers": [
            {
                "arxiv_id": p.arxiv_id,
                "title": p.display_title,
                "cover": _pdf_cover_filename(p.arxiv_id),
            } for p in author_papers
        ],
    }
    return render_template('r3_author_profile.html', name=name, stats=stats, visual=visual)

@app.route('/api/r3/author/<path:name>')
def r3_api_author(name):
    return jsonify({
        'name': name,
        'h_index': r3_author_h_index(name),
        'citations': r3_author_citation_count(name),
        'orcid': r3_author_orcid(name),
        'coauthors': r3_author_coauthor_graph(name)['nodes'][1:],
    })

@app.route('/api/r3/orcid/<path:name>')
def r3_api_orcid(name):
    return jsonify({'name': name, 'orcid': r3_author_orcid(name)})

# ============================================================
# R4: Category hub deepening — cs.AI / cs.CL / math.OC / physics.optics ...
# ============================================================
R4_CATEGORY_HUBS = {
    'cs.AI': {'title': 'Artificial Intelligence', 'tagline': 'foundation models, RL, planning, knowledge'},
    'cs.CL': {'title': 'Computation and Language', 'tagline': 'NLP, ASR, LLMs, dialog'},
    'cs.LG': {'title': 'Machine Learning', 'tagline': 'optimization, generalization, learning theory'},
    'cs.CV': {'title': 'Computer Vision', 'tagline': 'detection, segmentation, generative vision'},
    'math.OC': {'title': 'Optimization and Control', 'tagline': 'convex, nonlinear, stochastic control'},
    'math.PR': {'title': 'Probability', 'tagline': 'stochastic processes, martingales'},
    'physics.optics': {'title': 'Optics', 'tagline': 'photonics, lasers, imaging'},
    'q-bio.NC': {'title': 'Neurons and Cognition', 'tagline': 'computational neuroscience'},
    'stat.ML': {'title': 'Statistics — Machine Learning', 'tagline': 'Bayesian, kernel, deep'},
    'econ.EM': {'title': 'Econometrics', 'tagline': 'identification, panel, time-series'},
}

def r4_category_hub_payload(code):
    meta = R4_CATEGORY_HUBS.get(code, {'title': code, 'tagline': code})
    seed = _rN_seed('r4_cat', code)
    top_keywords = [w for w in ['transformer','graph','diffusion','agent','retrieval','contrastive','sparse','meta','causal','representation']]
    return {
        'code': code,
        'title': meta['title'],
        'tagline': meta['tagline'],
        'monthly_volume': 200 + (seed % 1200),
        'top_keywords': top_keywords[:5 + (seed % 5)],
        'featured_arxiv_ids': [f'24{(seed+i)%99:02d}.{(seed*7+i*11)%99999:05d}' for i in range(6)],
    }

@app.route('/r4/category/<code>')
def r4_category_hub(code):
    payload = r4_category_hub_payload(code)
    # Top papers in this category — pull cover thumbnails for the hero grid.
    top_papers = (Paper.query
                  .filter(or_(Paper.primary_subject_code == code,
                              Paper.primary_subject_code.like(f"{code}.%"),
                              Paper.primary_category_code == code))
                  .order_by(Paper.view_count.desc())
                  .limit(8).all())
    payload["banner"] = _category_banner_filename(code)
    payload["top_paper_covers"] = [
        {
            "arxiv_id": p.arxiv_id,
            "title": p.display_title,
            "cover": _pdf_cover_filename(p.arxiv_id),
            "views": p.view_count,
        } for p in top_papers
    ]
    return render_template('r4_category_hub.html', payload=payload)

@app.route('/api/r4/category/<code>')
def r4_api_category(code):
    return jsonify(r4_category_hub_payload(code))

@app.route('/api/r4/categories')
def r4_api_categories():
    return jsonify({'hubs': sorted(R4_CATEGORY_HUBS.keys())})

# ============================================================
# R5: Paper version diff (v1 vs v2 highlight) + withdrawn / replaced history
# ============================================================
def r5_version_history(arxiv_id):
    seed = _rN_seed('r5_vh', arxiv_id)
    n_versions = 1 + (seed % 4)  # 1-4 versions
    out = []
    base_yr = 2022 + (seed % 4)
    for v in range(1, n_versions + 1):
        out.append({
            'version': f'v{v}',
            'submitted': f'{base_yr + (v-1)//6}-{((seed + v) % 12)+1:02d}-{((seed*v) % 28)+1:02d}',
            'pages': 8 + ((seed + v) % 15),
            'words_added': 0 if v == 1 else 100 + ((seed * v) % 1500),
            'words_removed': 0 if v == 1 else 50 + ((seed + v*3) % 800),
        })
    return out

def r5_version_diff(arxiv_id, va, vb):
    seed = _rN_seed('r5_diff', arxiv_id, va, vb)
    sections = ['Abstract', 'Introduction', 'Method', 'Experiments', 'Results', 'Discussion', 'Conclusion']
    return {
        'arxiv_id': arxiv_id, 'from': va, 'to': vb,
        'sections_changed': [s for i, s in enumerate(sections) if (seed >> i) & 1],
        'total_diff_lines': 40 + (seed % 220),
    }

def r5_withdrawn_paper(arxiv_id):
    return (_rN_seed('r5_w', arxiv_id) % 100) < 3  # ~3% withdrawn

@app.route('/r5/versions/<arxiv_id>')
def r5_versions_page(arxiv_id):
    p = Paper.query.filter_by(arxiv_id=arxiv_id).first_or_404()
    return render_template('r5_versions.html', paper=p, history=r5_version_history(arxiv_id),
                           withdrawn=r5_withdrawn_paper(arxiv_id))

@app.route('/api/r5/versions/<arxiv_id>')
def r5_api_versions(arxiv_id):
    return jsonify({'arxiv_id': arxiv_id, 'history': r5_version_history(arxiv_id),
                    'withdrawn': r5_withdrawn_paper(arxiv_id)})

@app.route('/api/r5/diff/<arxiv_id>/<va>/<vb>')
def r5_api_diff(arxiv_id, va, vb):
    return jsonify(r5_version_diff(arxiv_id, va, vb))

# ============================================================
# R6: Reviews / public OpenReview-style comments / Trackback / PaperWithCode
# ============================================================
def r6_paperwithcode_attest(arxiv_id):
    seed = _rN_seed('r6_pwc', arxiv_id)
    has_code = (seed % 100) < 65  # 65%
    return {
        'has_code': has_code,
        'code_url': f'https://github.com/r6-pwc-mock/{arxiv_id}' if has_code else None,
        'stars': (seed % 4500) if has_code else 0,
        'reproduced': has_code and ((seed >> 4) % 10) > 4,
        'sota_tasks': ['ImageNet','GLUE','COCO'][:1 + (seed % 3)] if has_code else [],
    }

def r6_open_review_summary(arxiv_id):
    seed = _rN_seed('r6_or', arxiv_id)
    n = 3 + (seed % 4)
    scores = [3 + ((seed >> (i*2)) % 7) for i in range(n)]
    return {'n_reviews': n, 'scores': scores, 'avg_score': round(sum(scores)/n, 2),
            'recommendation': _rN_choice(['Accept','Weak Accept','Borderline','Weak Reject'],'r6_rec',arxiv_id)}

def r6_trackback_pings(arxiv_id):
    seed = _rN_seed('r6_tb', arxiv_id)
    n = (seed % 6)
    return [{'source': f'blog-{i}.example.org/post/{(seed+i)%999}', 'date': f'2025-{(seed+i)%12+1:02d}-{(seed*3+i)%28+1:02d}'} for i in range(n)]

@app.route('/r6/review/<arxiv_id>')
def r6_review_page(arxiv_id):
    p = Paper.query.filter_by(arxiv_id=arxiv_id).first_or_404()
    return render_template('r6_review.html', paper=p, pwc=r6_paperwithcode_attest(arxiv_id),
                           review=r6_open_review_summary(arxiv_id), pings=r6_trackback_pings(arxiv_id))

@app.route('/api/r6/paperwithcode/<arxiv_id>')
def r6_api_pwc(arxiv_id):
    return jsonify(r6_paperwithcode_attest(arxiv_id))

@app.route('/api/r6/openreview/<arxiv_id>')
def r6_api_openreview(arxiv_id):
    return jsonify(r6_open_review_summary(arxiv_id))

@app.route('/api/r6/trackback/<arxiv_id>')
def r6_api_trackback(arxiv_id):
    return jsonify({'arxiv_id': arxiv_id, 'pings': r6_trackback_pings(arxiv_id)})

# ============================================================
# R7: Academic-calendar deadlines — NeurIPS/ICML/ICLR/ACL/EMNLP/CVPR/ICCV/AAAI
# ============================================================
R7_CONFERENCE_CALENDAR = [
    {'conf': 'NeurIPS', 'year': 2026, 'abstract_deadline': '2026-05-15', 'paper_deadline': '2026-05-22', 'notification': '2026-09-25', 'location': 'San Diego, USA'},
    {'conf': 'ICML',    'year': 2026, 'abstract_deadline': '2026-01-23', 'paper_deadline': '2026-01-30', 'notification': '2026-05-01', 'location': 'Seoul, Korea'},
    {'conf': 'ICLR',    'year': 2027, 'abstract_deadline': '2026-09-21', 'paper_deadline': '2026-10-01', 'notification': '2027-01-20', 'location': 'Rio de Janeiro, Brazil'},
    {'conf': 'ACL',     'year': 2026, 'abstract_deadline': '2026-02-08', 'paper_deadline': '2026-02-15', 'notification': '2026-05-15', 'location': 'Bangkok, Thailand'},
    {'conf': 'EMNLP',   'year': 2026, 'abstract_deadline': '2026-06-08', 'paper_deadline': '2026-06-15', 'notification': '2026-10-09', 'location': 'Lima, Peru'},
    {'conf': 'CVPR',    'year': 2027, 'abstract_deadline': '2026-11-08', 'paper_deadline': '2026-11-15', 'notification': '2027-02-26', 'location': 'Honolulu, USA'},
    {'conf': 'ICCV',    'year': 2027, 'abstract_deadline': '2027-03-01', 'paper_deadline': '2027-03-08', 'notification': '2027-07-01', 'location': 'Vienna, Austria'},
    {'conf': 'AAAI',    'year': 2027, 'abstract_deadline': '2026-08-01', 'paper_deadline': '2026-08-15', 'notification': '2026-11-09', 'location': 'Vancouver, Canada'},
    {'conf': 'KDD',     'year': 2026, 'abstract_deadline': '2026-02-01', 'paper_deadline': '2026-02-08', 'notification': '2026-05-16', 'location': 'Sydney, Australia'},
    {'conf': 'SIGGRAPH','year': 2026, 'abstract_deadline': '2026-01-15', 'paper_deadline': '2026-01-22', 'notification': '2026-04-30', 'location': 'Los Angeles, USA'},
]

def r7_calendar_upcoming(today_iso='2026-05-27'):
    return sorted([c for c in R7_CONFERENCE_CALENDAR if c['paper_deadline'] >= today_iso], key=lambda c: c['paper_deadline'])

def r7_calendar_lookup(conf, year):
    for c in R7_CONFERENCE_CALENDAR:
        if c['conf'].lower() == conf.lower() and c['year'] == int(year): return c
    return None

@app.route('/r7/calendar')
def r7_calendar_page():
    images = {c.conf: c for c in ConferenceImage.query.all()}
    return render_template(
        'r7_calendar.html',
        calendar=R7_CONFERENCE_CALENDAR,
        upcoming=r7_calendar_upcoming(),
        conf_images=images,
    )

@app.route('/api/r7/calendar')
def r7_api_calendar():
    return jsonify({'calendar': R7_CONFERENCE_CALENDAR, 'upcoming': r7_calendar_upcoming()})

@app.route('/api/r7/calendar/<conf>/<int:year>')
def r7_api_calendar_lookup(conf, year):
    rec = r7_calendar_lookup(conf, year)
    if not rec: abort(404)
    return jsonify(rec)

# ============================================================
# R8: User library deepening — saved-search, follow-author alerts, RSS export
# ============================================================
def r8_saved_search_id(user_id, query):
    return _r2_hashlib.md5(f'r8_ss|{user_id}|{query}'.encode()).hexdigest()[:12]

def r8_author_alert_id(user_id, author):
    return _r2_hashlib.md5(f'r8_aa|{user_id}|{author}'.encode()).hexdigest()[:12]

def r8_export_rss_payload(user_id):
    seed = _rN_seed('r8_rss', user_id)
    items = [{'title': f'Saved paper #{i+1}', 'arxiv_id': f'24{(seed+i)%99:02d}.{(seed*5+i*7)%99999:05d}'} for i in range(6 + (seed % 8))]
    return items

@app.route('/r8/saved-searches')
@login_required
def r8_saved_searches():
    return render_template('r8_saved_searches.html')

@app.route('/api/r8/saved-search', methods=['POST'])
@login_required
def r8_api_save_search():
    q = (request.json or {}).get('q', '').strip()
    if not q: return jsonify({'ok': False, 'error': 'empty query'}), 400
    sid = r8_saved_search_id(current_user.id, q)
    return jsonify({'ok': True, 'id': sid, 'q': q})

@app.route('/api/r8/author-alert', methods=['POST'])
@login_required
def r8_api_author_alert():
    name = (request.json or {}).get('author', '').strip()
    if not name: return jsonify({'ok': False, 'error': 'empty author'}), 400
    aid = r8_author_alert_id(current_user.id, name)
    return jsonify({'ok': True, 'id': aid, 'author': name})

@app.route('/r8/rss/my-library.xml')
@login_required
def r8_rss_my_library():
    items = r8_export_rss_payload(current_user.id)
    body = '<rss version="2.0"><channel><title>My Library</title>' + ''.join(
        f'<item><title>{i["title"]}</title><link>/abs/{i["arxiv_id"]}</link></item>' for i in items) + '</channel></rss>'
    return Response(body, mimetype='application/rss+xml')

@app.route('/api/r8/rss/my-library')
@login_required
def r8_api_rss():
    return jsonify({'items': r8_export_rss_payload(current_user.id)})

# ============================================================
# R9: Submission flow — meta-data form, LaTeX upload, abstract editor
# ============================================================
R9_SUBMIT_STEPS = ['metadata', 'authors', 'abstract', 'files', 'license', 'preview', 'submit']

def r9_submission_token(user_id, draft_id):
    return _r2_hashlib.md5(f'r9_tok|{user_id}|{draft_id}'.encode()).hexdigest()[:16]

def r9_validate_metadata(payload):
    errs = []
    if not payload.get('title'): errs.append('title is required')
    if len(payload.get('abstract','')) < 50: errs.append('abstract must be >= 50 chars')
    if not payload.get('primary_category'): errs.append('primary category is required')
    return errs

def r9_latex_lint(source):
    issues = []
    if '\\documentclass' not in source: issues.append('missing \\documentclass')
    if '\\begin{document}' not in source: issues.append('missing \\begin{document}')
    if '\\end{document}' not in source: issues.append('missing \\end{document}')
    if source.count('\\section') < 1: issues.append('warning: no \\section')
    return issues

@app.route('/r9/submit-wizard')
@login_required
def r9_submit_wizard():
    return render_template('r9_submit_wizard.html', steps=R9_SUBMIT_STEPS)

@app.route('/api/r9/submit/validate', methods=['POST'])
@login_required
def r9_api_submit_validate():
    errs = r9_validate_metadata(request.json or {})
    return jsonify({'ok': not errs, 'errors': errs})

@app.route('/api/r9/submit/lint-latex', methods=['POST'])
@login_required
def r9_api_latex_lint():
    src = (request.json or {}).get('source', '')
    return jsonify({'issues': r9_latex_lint(src)})

@app.route('/api/r9/submit/token', methods=['POST'])
@login_required
def r9_api_submit_token():
    did = (request.json or {}).get('draft_id', '0')
    return jsonify({'token': r9_submission_token(current_user.id, did)})

# ============================================================
# R10: API surface — GraphQL / REST v1 / OAI-PMH / sitemap / healthz
# ============================================================
def r10_api_paper_payload(arxiv_id):
    p = Paper.query.filter_by(arxiv_id=arxiv_id).first()
    if not p: return None
    return {
        'arxiv_id': p.arxiv_id, 'title': p.title, 'category': p.primary_category_code,
        'subject': p.primary_subject_code, 'submitted_year': p.submitted_year,
        'h_index_first_author': r3_author_h_index((p.get_authors() or [''])[0]),
        'has_code': r6_paperwithcode_attest(p.arxiv_id)['has_code'],
        'pdf_pages': len(r2_pdf_inline_pages(p.arxiv_id)),
    }

def r10_graphql_resolve(query):
    """Tiny GraphQL-ish resolver: supports `{ paper(id:"X") { title category } }`."""
    import re as _re
    m = _re.search(r'paper\(\s*id\s*:\s*"([^"]+)"\s*\)', query or '')
    if not m: return {'errors': [{'message': 'unsupported query'}]}
    aid = m.group(1)
    payload = r10_api_paper_payload(aid)
    if not payload: return {'errors': [{'message': f'paper {aid} not found'}]}
    return {'data': {'paper': payload}}

def r10_oai_pmh_listrecords(set_code=None, limit=10):
    q = Paper.query
    if set_code: q = q.filter(Paper.primary_category_code == set_code)
    rows = q.limit(limit).all()
    return [{'arxiv_id': r.arxiv_id, 'title': r.title, 'set': r.primary_category_code} for r in rows]

@app.route('/graphql', methods=['POST'])
def r10_graphql():
    return jsonify(r10_graphql_resolve((request.json or {}).get('query', '')))

@app.route('/api/v1/papers/<arxiv_id>')
def r10_api_v1_paper(arxiv_id):
    p = r10_api_paper_payload(arxiv_id)
    if not p: abort(404)
    return jsonify(p)

@app.route('/api/v1/oai-pmh')
def r10_api_v1_oai_pmh():
    return jsonify({'records': r10_oai_pmh_listrecords(request.args.get('set'), 10)})

@app.route('/api/v1/healthz')
def r10_api_v1_healthz():
    return jsonify({'ok': True, 'service': 'arxiv-mirror', 'r10_marker': 'r10_healthz_ok'})

@app.route('/api/v1/sitemap')
def r10_api_v1_sitemap():
    return jsonify({'sitemaps': ['/sitemap.xml', '/sitemap-static.xml'], 'r10_marker': 'r10_sitemap_index'})

csrf.exempt(r8_api_save_search)
csrf.exempt(r8_api_author_alert)
csrf.exempt(r9_api_submit_validate)
csrf.exempt(r9_api_latex_lint)
csrf.exempt(r9_api_submit_token)
csrf.exempt(r10_graphql)

# =========== END R2-R10 DEEPENING ===========


def seed_visual_assets():
    """Bootstrap on-disk SVG pool + populate ConferenceImage / AuthorImage /
    PaperFigure rows where useful.

    Idempotent. Reads from `visual_assets.CONFERENCES` and the helper functions
    in app.py so the on-disk and on-DB views never drift.

    Image-utilization deepening — 2026-05-27.
    """
    # 1. Materialise the SVG pool. Cheap no-op when files exist.
    visual_assets.bootstrap()

    # 2. Conference banners — small, fixed list.
    if ConferenceImage.query.count() == 0:
        for slug, abbr, full, color in visual_assets.CONFERENCES:
            db.session.add(ConferenceImage(
                conf=abbr.upper(),
                year=0,  # 0 = generic / any year
                kind="banner",
                filename=f"conferences/{slug}.svg",
                alt=f"{full} official banner",
                accent_color=color,
            ))
        db.session.commit()
        print(f"  [+] Seeded {ConferenceImage.query.count()} conference banners")

    # 3. Author images for the most-frequent author names. Top ~1500.
    if AuthorImage.query.count() == 0:
        # Count author appearances across papers. Cheap: parse authors_json
        # in batches of 5000 papers and accumulate.
        from collections import Counter
        counter = Counter()
        batch = 0
        for rows in (db.session.execute(
                text("SELECT authors_json FROM papers"))).yield_per(5000):
            try:
                names = json.loads(rows[0] or "[]")
                for n in names:
                    if n:
                        counter[n] += 1
            except Exception:
                continue
            batch += 1
        # Top 1500 names get DB rows; the rest fall through to the md5 helper.
        top = counter.most_common(1500)
        for name, _ in top:
            aff = _synthesize_affiliation(name)
            db.session.add(AuthorImage(
                author_name=name,
                kind="headshot",
                filename=_avatar_filename(name),
                alt=f"{name} headshot",
                institution_logo=_institution_logo_filename(aff),
            ))
        db.session.commit()
        print(f"  [+] Seeded {AuthorImage.query.count()} author headshots "
              f"(top of {len(counter)} unique names)")

    # 4. Paper figures. Pre-seed for the *featured* slice (top-viewed papers)
    #    so the showcase pages have DB-backed rows. The long tail uses the
    #    synth helper at request time — identical render shape, no DB bloat.
    if PaperFigure.query.count() == 0:
        inserted = 0
        ins = text(
            "INSERT INTO paper_figures (paper_id, position, kind, style, "
            "filename, caption, width, height) VALUES "
            "(:paper_id, :position, :kind, :style, :filename, :caption, "
            ":width, :height)"
        )
        chunk = []
        CHUNK_SIZE = 5000
        # Featured = top 10k by view_count, then sorted by arxiv_id so commit
        # ordering is deterministic (md5 of seed DB stays stable).
        rows = db.session.execute(text(
            "SELECT id, arxiv_id, primary_category_code, "
            "primary_subject_code, figures_count "
            "FROM papers ORDER BY view_count DESC LIMIT 10000"
        )).fetchall()
        rows = sorted(rows, key=lambda r: r[1])  # by arxiv_id
        for pid, aid, pcat, psub, fcount in rows:
            n = _figure_count_for(aid, fcount)
            for i in range(1, n + 1):
                style = _figure_style_for(aid, i, pcat or "", psub or "")
                chunk.append({
                    "paper_id": pid, "position": i,
                    "kind": "architecture" if (i == 1 and style == "arch") else "figure",
                    "style": style,
                    "filename": _figure_filename(style, aid, i),
                    "caption": _figure_caption(style, aid, i),
                    "width": 420, "height": 260,
                })
            if len(chunk) >= CHUNK_SIZE:
                db.session.execute(ins, chunk)
                inserted += len(chunk)
                chunk = []
        if chunk:
            db.session.execute(ins, chunk)
            inserted += len(chunk)
        db.session.commit()
        print(f"  [+] Seeded {inserted} paper figures (featured slice; long "
              f"tail synthesised at request time)")


with app.app_context():
    db.create_all()
    ensure_affiliation_column()
    # Ensure the SVG asset pool exists on disk *before* anything else may
    # serve a template that references images/figures/*. This is idempotent
    # (returns {'cached': True} when the sentinel file is in place) so warm
    # restarts pay nothing.
    visual_assets.bootstrap()
    # `random.seed` makes the per-row randint() calls in seed_database() and
    # seed_benchmark_users() reproducible. Column defaults that wrap
    # datetime.utcnow() are pinned by passing explicit created_at / added_at
    # arguments inside the seed functions themselves.
    random.seed(20260415)
    seed_database()
    seed_benchmark_users()
    seed_community_extras()
    backfill_paper_gaps()
    normalize_paper_metadata()
    backfill_affiliations()
    backfill_provenance_fields()
    seed_visual_assets()
    normalize_seed_db_layout()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 28842))
    app.run(host="0.0.0.0", port=port, debug=False)


# --- perf: long-term cache for /static/ assets (added 2026-05-27) ---
@app.after_request
def _add_static_cache_headers(resp):
    try:
        if request.path.startswith('/static/'):
            resp.headers['Cache-Control'] = 'public, max-age=86400, immutable'
    except Exception:
        pass
    return resp
# --- end perf ---

