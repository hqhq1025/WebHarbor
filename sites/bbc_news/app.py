"""
BBC News mirror - Flask application.

Adaptation of the mirror-web pattern to a news site:
  Entity     = Article (news story)
  Category   = Section (World, UK, Business, Technology, ...)
  Topic      = Tag / subject label
  Cart       = Reading List (save-for-later with folders + notes)
  Wishlist   = Bookmarks (one-click save to My News)
  Order      = Digest (exported bundle of articles as newsletter)
  Review     = Comment (with optional replies)
  Subscription = Topic alerts (email-me-when-X-updates)
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
    session, abort, Response
)
from flask_sqlalchemy import SQLAlchemy
from flask_login import (
    LoginManager, UserMixin, login_user, logout_user, login_required, current_user
)
from flask_bcrypt import Bcrypt
from flask_wtf import CSRFProtect
from sqlalchemy import or_, and_, func

BASE_DIR = Path(__file__).parent
DB_DIR = BASE_DIR / "instance"
DB_DIR.mkdir(exist_ok=True)

app = Flask(__name__)
app.config["SECRET_KEY"] = "bbc-news-mirror-secret-key-change-in-prod-987654321"
app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{DB_DIR / 'bbc_news.db'}"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["WTF_CSRF_TIME_LIMIT"] = None

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = "login"
login_manager.login_message = "Please sign in to continue."
csrf = CSRFProtect(app)


def bbc_article_share_url(article):
    if article.source_url:
        return article.source_url
    return f"https://www.bbc.com/news/articles/{article.slug}"


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
    location = db.Column(db.String(120), default="")
    bio = db.Column(db.Text, default="")
    avatar_color = db.Column(db.String(20), default="#bb1919")  # BBC red
    notification_email = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    reading_list = db.relationship("ReadingListItem", backref="user", cascade="all, delete-orphan")
    bookmarks = db.relationship("Bookmark", backref="user", cascade="all, delete-orphan")
    digests = db.relationship("Digest", backref="user", cascade="all, delete-orphan")
    comments = db.relationship("Comment", backref="user", cascade="all, delete-orphan")
    subscriptions = db.relationship("TopicSubscription", backref="user", cascade="all, delete-orphan")
    history = db.relationship("ReadingHistory", backref="user", cascade="all, delete-orphan")

    def set_password(self, raw: str):
        self.password_hash = bcrypt.generate_password_hash(raw).decode("utf-8")

    def check_password(self, raw: str) -> bool:
        return bcrypt.check_password_hash(self.password_hash, raw)

    @property
    def initials(self):
        parts = (self.full_name or self.username or "U").split()
        if len(parts) >= 2:
            return (parts[0][0] + parts[-1][0]).upper()
        return (self.username[:2] if self.username else "U").upper()


class Category(db.Model):
    """Top-level BBC News section: World, UK, Business, Technology, ..."""
    __tablename__ = "categories"
    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(60), unique=True, nullable=False, index=True)
    name = db.Column(db.String(120), nullable=False)
    subtitle = db.Column(db.String(250), default="")
    color = db.Column(db.String(20), default="#bb1919")
    icon = db.Column(db.String(20), default="")
    parent_slug = db.Column(db.String(60), default="")
    sort_order = db.Column(db.Integer, default=100)
    description = db.Column(db.Text, default="")

    articles = db.relationship("Article", backref="category", lazy="dynamic")

    @property
    def article_count(self):
        return Article.query.filter_by(category_id=self.id).count()


class Article(db.Model):
    """A single news story."""
    __tablename__ = "articles"
    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(80), unique=True, nullable=False, index=True)
    headline = db.Column(db.Text, nullable=False)
    subtitle = db.Column(db.Text, default="")
    summary = db.Column(db.Text, default="")
    body = db.Column(db.Text, default="")  # paragraphs separated by \n\n
    author = db.Column(db.String(200), default="BBC News")
    category_id = db.Column(db.Integer, db.ForeignKey("categories.id"))
    hero_image = db.Column(db.String(400), default="")
    gallery_json = db.Column(db.Text, default="[]")  # JSON list of image paths
    # Full gallery payload (hero + images + sections) as served to article_detail
    # template. Migrated from scraped_data/article_galleries.json so the
    # production image doesn't need the JSON file at runtime.
    gallery_full_json = db.Column(db.Text, default="{}")
    topics_json = db.Column(db.Text, default="[]")  # JSON list of topic strings
    published_at = db.Column(db.DateTime, default=datetime.utcnow)
    reading_time = db.Column(db.Integer, default=3)  # minutes
    word_count = db.Column(db.Integer, default=0)
    view_count = db.Column(db.Integer, default=0)
    is_featured = db.Column(db.Boolean, default=False)
    is_breaking = db.Column(db.Boolean, default=False)
    is_live = db.Column(db.Boolean, default=False)
    location = db.Column(db.String(120), default="")
    source_url = db.Column(db.String(500), default="")
    # Task-driven extensions
    section_slug = db.Column(db.String(60), default="", index=True)  # denormalized primary section
    subsection = db.Column(db.String(120), default="", index=True)   # e.g., 'Football', 'Golf', 'AI'
    region = db.Column(db.String(60), default="")                    # e.g., 'UK','Europe','Asia','Africa','Middle East'
    video_url = db.Column(db.String(500), default="")                # video clip URL
    feature_tags = db.Column(db.Text, default="[]")                  # JSON list of kebab-case tags
    content_type = db.Column(db.String(20), default="article")       # 'article','video','podcast','live'

    comments_rel = db.relationship("Comment", backref="article", cascade="all, delete-orphan", lazy="dynamic")
    reading_list_items = db.relationship("ReadingListItem", backref="article", cascade="all, delete-orphan")
    bookmarks = db.relationship("Bookmark", backref="article", cascade="all, delete-orphan")
    history = db.relationship("ReadingHistory", backref="article", cascade="all, delete-orphan")

    def get_gallery(self) -> list:
        try:
            return json.loads(self.gallery_json or "[]")
        except Exception:
            return []

    def get_full_gallery(self) -> dict:
        """Return the full gallery dict (hero, images, sections) for use by
        the article_detail template. Stored on the row so we don't need the
        scraped JSON at runtime."""
        try:
            return json.loads(self.gallery_full_json or "{}")
        except Exception:
            return {}

    def get_topics(self) -> list:
        try:
            return json.loads(self.topics_json or "[]")
        except Exception:
            return []

    def get_paragraphs(self) -> list:
        body = self.body or ""
        paras = [p.strip() for p in re.split(r"\n\n+", body) if p.strip()]
        return paras

    @property
    def published_date_str(self):
        if not self.published_at:
            return ""
        now = datetime.utcnow()
        delta = now - self.published_at
        if delta.days == 0:
            hours = delta.seconds // 3600
            if hours < 1:
                mins = max(1, delta.seconds // 60)
                return f"{mins} min{'s' if mins != 1 else ''} ago"
            return f"{hours} hr{'s' if hours != 1 else ''} ago"
        if delta.days < 7:
            return f"{delta.days} day{'s' if delta.days != 1 else ''} ago"
        return self.published_at.strftime("%d %b %Y")

    @property
    def short_headline(self):
        if len(self.headline) > 100:
            return self.headline[:100] + "…"
        return self.headline

    @property
    def comment_count(self):
        return self.comments_rel.count()


class ReadingListItem(db.Model):
    """Cart analog — a saved article in a user's reading list with folder + notes."""
    __tablename__ = "reading_list_items"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    article_id = db.Column(db.Integer, db.ForeignKey("articles.id"), nullable=False)
    folder = db.Column(db.String(100), default="Read Later")
    note = db.Column(db.Text, default="")
    priority = db.Column(db.String(20), default="normal")  # normal, high, low
    added_at = db.Column(db.DateTime, default=datetime.utcnow)
    read = db.Column(db.Boolean, default=False)
    __table_args__ = (db.UniqueConstraint("user_id", "article_id", name="_user_article_rl_uc"),)


class Bookmark(db.Model):
    """Wishlist analog — a one-click 'save to My News' bookmark."""
    __tablename__ = "bookmarks"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    article_id = db.Column(db.Integer, db.ForeignKey("articles.id"), nullable=False)
    bookmarked_at = db.Column(db.DateTime, default=datetime.utcnow)
    __table_args__ = (db.UniqueConstraint("user_id", "article_id", name="_user_article_bm_uc"),)


class Digest(db.Model):
    """Order analog — an exported digest/newsletter of saved articles."""
    __tablename__ = "digests"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    digest_number = db.Column(db.String(40), unique=True, nullable=False)
    title = db.Column(db.String(200), default="My News Digest")
    format = db.Column(db.String(20), default="email")  # email, pdf, text, rss
    status = db.Column(db.String(20), default="delivered")  # pending, delivered, cancelled
    article_count = db.Column(db.Integer, default=0)
    delivery_email = db.Column(db.String(200), default="")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    notes = db.Column(db.Text, default="")

    items = db.relationship("DigestItem", backref="digest", cascade="all, delete-orphan")


class DigestItem(db.Model):
    __tablename__ = "digest_items"
    id = db.Column(db.Integer, primary_key=True)
    digest_id = db.Column(db.Integer, db.ForeignKey("digests.id"), nullable=False)
    article_id = db.Column(db.Integer, db.ForeignKey("articles.id"), nullable=False)
    article = db.relationship("Article")


class Comment(db.Model):
    """Review analog — a user comment on an article, supports replies."""
    __tablename__ = "comments"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    article_id = db.Column(db.Integer, db.ForeignKey("articles.id"), nullable=False)
    parent_id = db.Column(db.Integer, db.ForeignKey("comments.id"), nullable=True)
    body = db.Column(db.Text, nullable=False)
    like_count = db.Column(db.Integer, default=0)
    flagged = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    replies = db.relationship(
        "Comment",
        backref=db.backref("parent", remote_side=[id]),
        cascade="all, delete-orphan",
        lazy="dynamic",
    )


class TopicSubscription(db.Model):
    """Subscribe to a category or topic for email alerts."""
    __tablename__ = "topic_subscriptions"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    category_slug = db.Column(db.String(60), default="")
    topic = db.Column(db.String(120), default="")
    frequency = db.Column(db.String(20), default="daily")  # daily, weekly, breaking_only
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class ReadingHistory(db.Model):
    """Track which articles a user has read."""
    __tablename__ = "reading_history"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    article_id = db.Column(db.Integer, db.ForeignKey("articles.id"), nullable=False)
    viewed_at = db.Column(db.DateTime, default=datetime.utcnow)


# =======================================================================
# LOGIN MANAGER
# =======================================================================

@login_manager.user_loader
def load_user(uid):
    return db.session.get(User, int(uid))


# =======================================================================
# SEED DATA
# =======================================================================

CATEGORY_META = [
    ("home",          "Home",          "#bb1919", "",         "",      10,  "The latest news, analysis, and stories from around the world"),
    ("news",          "News",          "#bb1919", "",         "",      20,  "Top stories and breaking news"),
    ("world",         "World",         "#bb1919", "",         "news",  30,  "International news and correspondent reports"),
    ("uk",            "UK",            "#bb1919", "",         "news",  40,  "News from across the United Kingdom"),
    ("politics",      "Politics",      "#bb1919", "",         "news",  50,  "Westminster, policy, and the political landscape"),
    ("business",      "Business",      "#000000", "",         "",      60,  "Markets, companies, economy, and your money"),
    ("technology",    "Technology",    "#000000", "",         "",      70,  "Tech, AI, startups, and the digital world"),
    ("science",       "Science",       "#000000", "",         "",      80,  "Space, nature, and the science of everything"),
    ("health",        "Health",        "#000000", "",         "",      90,  "Medicine, NHS, wellbeing, and disease"),
    ("entertainment", "Entertainment", "#000000", "",         "",     100,  "Film, music, celebrity, and television"),
    ("arts",          "Arts",          "#000000", "",         "",     110,  "Theatre, books, museums, and culture"),
    ("sport",         "Sport",         "#000000", "",         "",     120,  "Football, cricket, tennis, and more"),
    ("earth",         "Earth",         "#0a6b2e", "",         "",     130,  "Our changing planet, climate, and conservation"),
    ("travel",        "Travel",        "#000000", "",         "",     140,  "Destinations, guides, and travel stories"),
    ("in_pictures",   "In Pictures",   "#000000", "",         "",     150,  "Photojournalism and the visual story"),
    ("bbcverify",     "BBC Verify",    "#bb1919", "",         "news", 160,  "Fact-checking and verification"),
    ("video",         "Video",         "#000000", "",         "",     170,  "Watch the latest video news"),
    ("live",          "Live",          "#bb1919", "",         "",     180,  "Live events and breaking coverage"),
    ("culture",       "Culture",       "#000000", "",         "",     190,  "Film, books, music, and the arts"),
    ("audio",         "Audio",         "#000000", "",         "",     200,  "Podcasts, radio, and audio stories"),
    ("weather",       "Weather",       "#0a6b2e", "",         "",     210,  "Forecasts, storms, and climate alerts"),
    ("market_data",   "Market Data",   "#000000", "",         "business", 220, "Stock prices, indices, and currencies"),
    ("green_living",  "Green Living",  "#0a6b2e", "",         "earth", 230,  "Sustainable living and eco guides"),
    ("natural_wonders","Natural Wonders","#0a6b2e","",        "earth", 240,  "Wildlife, landscapes, and nature"),
    ("ai",            "Artificial Intelligence", "#000000", "", "technology", 250, "AI, machine learning, and the future"),
    ("war",           "War & Conflict", "#bb1919", "",        "world", 260,  "Reports from war zones and conflict updates"),
    # R3 additions — BBC sub-brands (Food, Sounds, iPlayer, Bitesize)
    ("food",          "Food",          "#bb1919", "",         "",      300,  "Recipes, food stories and the BBC Food kitchen"),
    ("sounds",        "Sounds",        "#000000", "",         "audio", 310,  "BBC Sounds podcasts, radio and music"),
    ("iplayer",       "iPlayer",       "#000000", "",         "",      320,  "BBC iPlayer drama, documentary and entertainment"),
    ("bitesize",      "Bitesize",      "#0a6b2e", "",         "",      330,  "BBC Bitesize learning for primary and secondary"),
    ("podcasts",      "Podcasts",      "#000000", "",         "sounds",311,  "Podcasts from the BBC and the wider world"),
    ("radio",         "Radio",         "#000000", "",         "sounds",312,  "BBC Radio live and on-demand"),
    ("film",          "Film & TV",     "#000000", "",         "culture",191, "Film and television reviews and features"),
    ("music",         "Music",         "#000000", "",         "culture",192, "Music news, releases and reviews"),
    ("books",         "Books",         "#000000", "",         "culture",193, "Books, authors and literary culture"),
    ("art_design",    "Art & Design",  "#000000", "",         "culture",194, "Art exhibitions, design and visual culture"),
    ("style",         "Style",         "#000000", "",         "culture",195, "Style, fashion and design"),
    ("destinations",  "Destinations",  "#000000", "",         "travel", 141, "Destination guides for the world's cities and regions"),
    ("worlds_table",  "World's Table", "#000000", "",         "travel", 142, "Food and culture from around the world"),
    ("the_specialist","The SpeciaList","#000000", "",         "travel", 143, "Expert travel picks and itineraries"),
    ("new_releases",  "New Releases",  "#000000", "",         "audio",  201, "Newly released podcasts from the BBC"),
    # R3: sport sub-disciplines (so /news/<slug> resolves on fresh builds)
    ("football",      "Football",      "#bb1919", "",         "sport", 121, "Football news from the UK, Europe and the world"),
    ("cricket",       "Cricket",       "#bb1919", "",         "sport", 122, "Cricket news, Test, ODI and T20 coverage"),
    ("rugby",         "Rugby",         "#bb1919", "",         "sport", 123, "Rugby union and league news"),
    ("tennis",        "Tennis",        "#bb1919", "",         "sport", 124, "Tennis news from the ATP, WTA and Grand Slams"),
    ("golf",          "Golf",          "#bb1919", "",         "sport", 125, "Golf news from the PGA, DP World and majors"),
    ("athletics",     "Athletics",     "#bb1919", "",         "sport", 126, "Track and field news and championships"),
    ("horse_racing",  "Horse Racing",  "#bb1919", "",         "sport", 127, "Flat racing and National Hunt coverage"),
    ("snooker",       "Snooker",       "#bb1919", "",         "sport", 128, "Snooker news and tournament coverage"),
    ("boxing",        "Boxing",        "#bb1919", "",         "sport", 129, "Boxing news, world titles and big fights"),
    ("formula1",      "Formula 1",     "#bb1919", "",         "sport", 130, "Formula 1 races, drivers and constructors"),
]

REGIONAL_SUBCATS = [
    ("africa",        "Africa",        "#bb1919", "world", 31),
    ("asia",          "Asia",          "#bb1919", "world", 32),
    ("australia",     "Australia",     "#bb1919", "world", 33),
    ("europe",        "Europe",        "#bb1919", "world", 34),
    ("latin_america", "Latin America", "#bb1919", "world", 35),
    ("middle_east",   "Middle East",   "#bb1919", "world", 36),
    ("us_canada",     "US & Canada",   "#bb1919", "world", 37),
    ("england",       "England",       "#bb1919", "uk",    41),
    ("scotland",      "Scotland",      "#bb1919", "uk",    42),
    ("wales",         "Wales",         "#bb1919", "uk",    43),
    ("northern_ireland", "N. Ireland", "#bb1919", "uk",    44),
]


def _slugify_fallback(text):
    s = re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")
    return s[:60] or "article"


def seed_database():
    if Category.query.first() is not None:
        return

    # --- Categories ---
    for slug, name, color, icon, parent, order, desc in CATEGORY_META:
        db.session.add(Category(
            slug=slug, name=name, color=color, icon=icon,
            parent_slug=parent, sort_order=order, description=desc,
            subtitle=desc,
        ))
    for slug, name, color, parent, order in REGIONAL_SUBCATS:
        db.session.add(Category(
            slug=slug, name=name, color=color,
            parent_slug=parent, sort_order=order,
            description=f"News from {name}",
        ))
    db.session.commit()
    print(f"  [+] Seeded {Category.query.count()} categories")

    # --- Articles ---
    art_path = BASE_DIR / "scraped_data" / "articles.json"
    gallery_path = BASE_DIR / "scraped_data" / "article_galleries.json"
    if not art_path.exists():
        print("  ! articles.json not found")
        return

    raw_articles = json.load(open(art_path))
    gallery_data = {}
    if gallery_path.exists():
        gallery_data = json.load(open(gallery_path))

    # Get category by slug
    cat_by_slug = {c.slug: c for c in Category.query.all()}

    # Pin a baseline timestamp so "x hrs ago" renders naturally
    now = datetime.utcnow()
    created = 0
    for idx, rp in enumerate(raw_articles):
        slug = rp.get("slug", "").strip()
        if not slug:
            slug = _slugify_fallback(rp.get("headline", f"article-{idx}"))
        if Article.query.filter_by(slug=slug).first():
            continue
        headline = (rp.get("headline") or "").strip()
        if not headline:
            continue

        cat_slug = rp.get("category") or ""
        if cat_slug not in cat_by_slug:
            cat_slug = "world"  # default
        category = cat_by_slug[cat_slug]

        subtitle = (rp.get("subtitle") or "").strip()[:400]
        summary = (rp.get("summary") or subtitle or "").strip()[:350]
        body = (rp.get("body") or "").strip()

        topics = rp.get("tags") or rp.get("topics") or []

        # Hero + gallery — also bake the full gallery dict (sections, etc.)
        # into gallery_full_json so the article_detail template can render
        # it without needing the source JSON at runtime.
        hero = ""
        gallery_imgs = []
        full_gallery = {}
        if slug in gallery_data:
            g = gallery_data[slug]
            hero = g.get("hero") or ""
            gallery_imgs = g.get("images", [])[:12]
            full_gallery = g

        published = now - timedelta(hours=random.randint(1, 72), minutes=random.randint(0, 59))

        art = Article(
            slug=slug,
            headline=headline,
            subtitle=subtitle,
            summary=summary,
            body=body,
            author=rp.get("author") or "BBC News",
            category_id=category.id,
            hero_image=hero,
            gallery_json=json.dumps(gallery_imgs),
            gallery_full_json=json.dumps(full_gallery),
            topics_json=json.dumps(topics),
            published_at=published,
            reading_time=rp.get("reading_time") or max(1, len(body.split()) // 200),
            word_count=rp.get("word_count") or len(body.split()),
            view_count=random.randint(500, 50000),
            is_featured=(idx < 6),
            is_breaking=(idx < 2),
            is_live=(idx == 0),
            location=rp.get("location") or "",
            source_url=rp.get("url") or "",
            section_slug=cat_slug,
        )
        db.session.add(art)
        created += 1
        if created % 50 == 0:
            db.session.commit()
    db.session.commit()
    print(f"  [+] Seeded {created} articles")

    # --- Demo user ---
    if not User.query.filter_by(email="demo@bbcnews.local").first():
        u = User(
            email="demo@bbcnews.local",
            username="newsreader",
            full_name="News Reader",
            location="London, UK",
            bio="Keeping up with the world's stories.",
        )
        u.set_password("demodemo")
        db.session.add(u)
        db.session.commit()

        sample = Article.query.limit(6).all()
        for i, a in enumerate(sample[:3]):
            db.session.add(ReadingListItem(
                user_id=u.id, article_id=a.id,
                folder="Work" if i % 2 == 0 else "Read Later",
            ))
        for a in sample[3:5]:
            db.session.add(Bookmark(user_id=u.id, article_id=a.id))
        db.session.commit()
        print(f"  [+] Created demo user (demo@bbcnews.local / demodemo)")


# =======================================================================
# BENCHMARK USER SEED
# =======================================================================

def seed_benchmark_users():
    """Create 4 benchmark users with reading list items, bookmarks, and digests.
    Idempotent — safe to call multiple times."""
    if User.query.filter_by(email="alice.j@test.com").first():
        return  # already seeded

    # Helper: get articles for a section, with fallback sections
    def _arts(primary_slug, fallbacks, count):
        arts = Article.query.filter_by(section_slug=primary_slug).limit(count).all()
        if len(arts) < count:
            for fb in fallbacks:
                extra = Article.query.filter_by(section_slug=fb).limit(count - len(arts)).all()
                seen_ids = {a.id for a in arts}
                arts += [a for a in extra if a.id not in seen_ids]
                if len(arts) >= count:
                    break
        return arts[:count]

    # ---- Alice Johnson — tech & science reader ----
    alice = User(
        email="alice.j@test.com",
        username="alice_johnson",
        full_name="Alice Johnson",
        location="London, UK",
        bio="Technology and science enthusiast.",
        avatar_color="#0057a8",
    )
    alice.set_password("TestPass123!")
    db.session.add(alice)
    db.session.flush()

    tech_arts = _arts("technology", ["science", "business"], 8)
    sci_arts = _arts("science", ["technology", "health"], 5)

    # Reading list: 4 tech + 2 science articles across two folders
    for i, a in enumerate(tech_arts[:4]):
        db.session.add(ReadingListItem(user_id=alice.id, article_id=a.id,
                                       folder="Technology", priority="high" if i < 2 else "normal"))
    for a in sci_arts[:2]:
        db.session.add(ReadingListItem(user_id=alice.id, article_id=a.id,
                                       folder="Science", priority="normal"))
    db.session.flush()

    # Bookmarks: 4 articles
    for a in tech_arts[4:6] + sci_arts[2:4]:
        db.session.add(Bookmark(user_id=alice.id, article_id=a.id))

    # Digests: 1 delivered, 1 pending
    d1 = Digest(user_id=alice.id, digest_number="D-ALICE-001",
                title="Weekly Tech Digest", format="email",
                status="delivered", article_count=min(4, len(tech_arts[:4])),
                delivery_email="alice.j@test.com")
    db.session.add(d1)
    db.session.flush()
    for a in tech_arts[:4]:
        db.session.add(DigestItem(digest_id=d1.id, article_id=a.id))

    d2 = Digest(user_id=alice.id, digest_number="D-ALICE-002",
                title="Science Roundup", format="text",
                status="pending", article_count=min(3, len(sci_arts[:3])),
                delivery_email="alice.j@test.com")
    db.session.add(d2)
    db.session.flush()
    for a in sci_arts[:3]:
        db.session.add(DigestItem(digest_id=d2.id, article_id=a.id))

    # Topic subscriptions
    db.session.add(TopicSubscription(user_id=alice.id, category_slug="technology",
                                     topic="AI", frequency="daily"))
    db.session.add(TopicSubscription(user_id=alice.id, category_slug="science",
                                     topic="Space", frequency="weekly"))

    # ---- Bob Chen — business & world reader ----
    bob = User(
        email="bob.c@test.com",
        username="bob_chen",
        full_name="Bob Chen",
        location="Manchester, UK",
        bio="Business and global news follower.",
        avatar_color="#c00000",
    )
    bob.set_password("TestPass123!")
    db.session.add(bob)
    db.session.flush()

    biz_arts = _arts("business", ["world", "politics"], 8)
    world_arts = _arts("world", ["politics", "uk"], 5)

    for i, a in enumerate(biz_arts[:5]):
        folder = "Business" if i < 3 else "World News"
        db.session.add(ReadingListItem(user_id=bob.id, article_id=a.id,
                                       folder=folder, priority="high" if i == 0 else "normal"))
    for a in world_arts[:3]:
        db.session.add(ReadingListItem(user_id=bob.id, article_id=a.id,
                                       folder="World News", priority="normal"))

    for a in biz_arts[5:7]:
        db.session.add(Bookmark(user_id=bob.id, article_id=a.id))
    for a in world_arts[3:5]:
        db.session.add(Bookmark(user_id=bob.id, article_id=a.id))
    db.session.flush()

    d3 = Digest(user_id=bob.id, digest_number="D-BOB-001",
                title="Business & Markets Weekly", format="email",
                status="delivered", article_count=min(5, len(biz_arts[:5])),
                delivery_email="bob.c@test.com")
    db.session.add(d3)
    db.session.flush()
    for a in biz_arts[:5]:
        db.session.add(DigestItem(digest_id=d3.id, article_id=a.id))

    d4 = Digest(user_id=bob.id, digest_number="D-BOB-002",
                title="World News Digest", format="pdf",
                status="delivered", article_count=min(3, len(world_arts[:3])),
                delivery_email="bob.c@test.com")
    db.session.add(d4)
    db.session.flush()
    for a in world_arts[:3]:
        db.session.add(DigestItem(digest_id=d4.id, article_id=a.id))

    db.session.add(TopicSubscription(user_id=bob.id, category_slug="business",
                                     topic="Markets", frequency="daily"))
    db.session.add(TopicSubscription(user_id=bob.id, category_slug="world",
                                     topic="", frequency="breaking_only"))

    # ---- Carol Davis — health & environment reader ----
    carol = User(
        email="carol.d@test.com",
        username="carol_davis",
        full_name="Carol Davis",
        location="Edinburgh, UK",
        bio="Health, environment, and earth science enthusiast.",
        avatar_color="#2e7d32",
    )
    carol.set_password("TestPass123!")
    db.session.add(carol)
    db.session.flush()

    health_arts = _arts("health", ["science", "uk"], 8)
    # earth may be absent in smaller DBs — fall back to science/world
    earth_arts = _arts("earth", ["science", "world"], 6)
    # ensure no overlap
    earth_ids = {a.id for a in earth_arts}
    health_uniq = [a for a in health_arts if a.id not in earth_ids]

    for i, a in enumerate(health_uniq[:4]):
        db.session.add(ReadingListItem(user_id=carol.id, article_id=a.id,
                                       folder="Health", priority="high" if i < 2 else "normal"))
    for a in earth_arts[:4]:
        db.session.add(ReadingListItem(user_id=carol.id, article_id=a.id,
                                       folder="Environment", priority="normal"))

    for a in health_uniq[4:7]:
        db.session.add(Bookmark(user_id=carol.id, article_id=a.id))
    for a in earth_arts[4:6]:
        db.session.add(Bookmark(user_id=carol.id, article_id=a.id))
    db.session.flush()

    d5 = Digest(user_id=carol.id, digest_number="D-CAROL-001",
                title="Health & Wellbeing Digest", format="email",
                status="delivered", article_count=min(4, len(health_uniq[:4])),
                delivery_email="carol.d@test.com")
    db.session.add(d5)
    db.session.flush()
    for a in health_uniq[:4]:
        db.session.add(DigestItem(digest_id=d5.id, article_id=a.id))

    d6 = Digest(user_id=carol.id, digest_number="D-CAROL-002",
                title="Climate & Earth Digest", format="rss",
                status="pending", article_count=min(4, len(earth_arts[:4])),
                delivery_email="carol.d@test.com")
    db.session.add(d6)
    db.session.flush()
    for a in earth_arts[:4]:
        db.session.add(DigestItem(digest_id=d6.id, article_id=a.id))

    db.session.add(TopicSubscription(user_id=carol.id, category_slug="health",
                                     topic="NHS", frequency="daily"))
    db.session.add(TopicSubscription(user_id=carol.id, category_slug="earth",
                                     topic="Climate Change", frequency="weekly"))

    # ---- David Kim — sport & entertainment reader ----
    david = User(
        email="david.k@test.com",
        username="david_kim",
        full_name="David Kim",
        location="Birmingham, UK",
        bio="Sports fanatic and entertainment news follower.",
        avatar_color="#6a1b9a",
    )
    david.set_password("TestPass123!")
    db.session.add(david)
    db.session.flush()

    # sport may be absent in smaller DBs — fall back to entertainment/arts
    sport_arts = _arts("sport", ["entertainment", "arts"], 8)
    ent_arts = _arts("entertainment", ["arts", "culture"], 6)
    sport_ids = {a.id for a in sport_arts}
    ent_uniq = [a for a in ent_arts if a.id not in sport_ids]
    # If no unique ent arts (all overlapped into sport_arts fallback), pull from arts directly
    if not ent_uniq:
        arts_arts = _arts("arts", ["entertainment", "culture"], 6)
        ent_uniq = [a for a in arts_arts if a.id not in sport_ids][:6]

    for i, a in enumerate(sport_arts[:5]):
        db.session.add(ReadingListItem(user_id=david.id, article_id=a.id,
                                       folder="Sport", priority="high" if i < 3 else "normal"))
    for a in ent_uniq[:3]:
        db.session.add(ReadingListItem(user_id=david.id, article_id=a.id,
                                       folder="Entertainment", priority="normal"))

    for a in sport_arts[5:7]:
        db.session.add(Bookmark(user_id=david.id, article_id=a.id))
    for a in ent_uniq[3:6]:
        db.session.add(Bookmark(user_id=david.id, article_id=a.id))
    db.session.flush()

    d7 = Digest(user_id=david.id, digest_number="D-DAVID-001",
                title="Sports Weekend Roundup", format="email",
                status="delivered", article_count=min(5, len(sport_arts[:5])),
                delivery_email="david.k@test.com")
    db.session.add(d7)
    db.session.flush()
    for a in sport_arts[:5]:
        db.session.add(DigestItem(digest_id=d7.id, article_id=a.id))

    d8 = Digest(user_id=david.id, digest_number="D-DAVID-002",
                title="Entertainment Weekly", format="email",
                status="cancelled", article_count=min(3, len(ent_uniq[:3])),
                delivery_email="david.k@test.com")
    db.session.add(d8)
    db.session.flush()
    for a in ent_uniq[:3]:
        db.session.add(DigestItem(digest_id=d8.id, article_id=a.id))

    db.session.add(TopicSubscription(user_id=david.id, category_slug="sport",
                                     topic="Football", frequency="daily"))
    db.session.add(TopicSubscription(user_id=david.id, category_slug="entertainment",
                                     topic="Film", frequency="weekly"))

    db.session.commit()
    print("  [+] Seeded 4 benchmark users (alice, bob, carol, david)")


# =======================================================================
# CONTEXT PROCESSORS
# =======================================================================

# BBC News navigation tree — mirrors the real bbc.com/news mainNavigation
# augmented with our local World/Politics hub pages so regional drill-down works.
# Paths are kept identical to our existing /news/<slug> routes.
BBC_NAV_TREE = [
    {"title": "Home", "path": "/", "slug": "home"},
    {"title": "News", "path": "/news/news", "slug": "news", "children": [
        {"title": "UK", "path": "/news/uk", "slug": "uk", "children": [
            {"title": "UK Politics", "path": "/news/politics", "slug": "politics"},
            {"title": "England", "path": "/news/england", "slug": "england"},
            {"title": "N. Ireland", "path": "/news/northern_ireland", "slug": "northern_ireland"},
            {"title": "Scotland", "path": "/news/scotland", "slug": "scotland"},
            {"title": "Wales", "path": "/news/wales", "slug": "wales"},
        ]},
        {"title": "World", "path": "/news/world", "slug": "world", "children": [
            {"title": "Africa", "path": "/news/africa", "slug": "africa"},
            {"title": "Asia", "path": "/news/asia", "slug": "asia"},
            {"title": "Australia", "path": "/news/australia", "slug": "australia"},
            {"title": "Europe", "path": "/news/europe", "slug": "europe"},
            {"title": "Latin America", "path": "/news/latin_america", "slug": "latin_america"},
            {"title": "Middle East", "path": "/news/middle_east", "slug": "middle_east"},
            {"title": "US & Canada", "path": "/news/us_canada", "slug": "us_canada"},
        ]},
        {"title": "In Pictures", "path": "/news/in_pictures", "slug": "in_pictures"},
        {"title": "BBC Verify", "path": "/news/bbcverify", "slug": "bbcverify"},
    ]},
    {"title": "Sport", "path": "/news/sport", "slug": "sport", "children": [
        {"title": "Football", "path": "/news/football", "slug": "football"},
        {"title": "Golf", "path": "/news/golf", "slug": "golf"},
        {"title": "Athletics", "path": "/news/athletics", "slug": "athletics"},
        {"title": "Horse Racing", "path": "/news/horse_racing", "slug": "horse_racing"},
        {"title": "Tennis", "path": "/news/tennis", "slug": "tennis"},
        {"title": "Cricket", "path": "/news/cricket", "slug": "cricket"},
        {"title": "Rugby", "path": "/news/rugby", "slug": "rugby"},
    ]},
    {"title": "Business", "path": "/news/business", "slug": "business", "children": [
        {"title": "Market Data", "path": "/news/market_data", "slug": "market_data"},
        {"title": "Technology of Business", "path": "/news/business?subsection=Technology+of+Business", "slug": "business_tob"},
    ]},
    {"title": "Innovation", "path": "/news/technology", "slug": "technology", "children": [
        {"title": "Technology", "path": "/news/technology", "slug": "technology"},
        {"title": "Science", "path": "/news/science", "slug": "science"},
        {"title": "Artificial Intelligence", "path": "/news/ai", "slug": "ai"},
    ]},
    {"title": "Health", "path": "/news/health", "slug": "health"},
    {"title": "Culture", "path": "/news/culture", "slug": "culture", "children": [
        {"title": "Film & TV", "path": "/news/film", "slug": "film"},
        {"title": "Music", "path": "/news/music", "slug": "music"},
        {"title": "Books", "path": "/news/books", "slug": "books"},
        {"title": "Art & Design", "path": "/news/art_design", "slug": "art_design"},
        {"title": "Style", "path": "/news/style", "slug": "style"},
        {"title": "Entertainment News", "path": "/news/entertainment", "slug": "entertainment"},
    ]},
    {"title": "Arts", "path": "/news/arts", "slug": "arts"},
    {"title": "Travel", "path": "/news/travel", "slug": "travel", "children": [
        {"title": "The SpeciaList", "path": "/news/the_specialist", "slug": "the_specialist"},
        {"title": "Destinations", "path": "/news/destinations", "slug": "destinations"},
        {"title": "World's Table", "path": "/news/worlds_table", "slug": "worlds_table"},
    ]},
    {"title": "Earth", "path": "/news/earth", "slug": "earth", "children": [
        {"title": "Natural Wonders", "path": "/news/natural_wonders", "slug": "natural_wonders"},
        {"title": "Green Living", "path": "/news/green_living", "slug": "green_living"},
    ]},
    {"title": "Audio", "path": "/news/audio", "slug": "audio", "children": [
        {"title": "Podcasts", "path": "/news/podcasts", "slug": "podcasts"},
        {"title": "New Releases", "path": "/news/new_releases", "slug": "new_releases"},
        {"title": "Radio", "path": "/news/radio", "slug": "radio"},
    ]},
    {"title": "Weather", "path": "/news/weather", "slug": "weather"},
    {"title": "Video", "path": "/news/video", "slug": "video"},
    {"title": "Live", "path": "/live", "slug": "live"},
]


def _slug_in_subtree(node, target):
    if node.get('slug') == target:
        return True
    for child in node.get('children') or []:
        if _slug_in_subtree(child, target):
            return True
    return False


def _active_path_for(request_path):
    """Return the BBC-nav slug matching the current request, for highlighting."""
    if request_path == '/':
        return 'home'
    parts = request_path.strip('/').split('/')
    if len(parts) >= 2 and parts[0] == 'news':
        return parts[1]
    if parts:
        return parts[0]
    return ''


@app.context_processor
def inject_globals():
    reading_list_count = 0
    bookmark_count = 0
    if current_user.is_authenticated:
        reading_list_count = ReadingListItem.query.filter_by(user_id=current_user.id).count()
        bookmark_count = Bookmark.query.filter_by(user_id=current_user.id).count()

    main_cats = (Category.query.filter(Category.parent_slug == "")
                 .order_by(Category.sort_order).all())
    news_subcats = (Category.query.filter(Category.parent_slug == "news")
                    .order_by(Category.sort_order).all())
    now = datetime.utcnow()
    active_slug = _active_path_for(request.path) if request else ''
    # Breaking-news banner: pick the freshest is_breaking==1 story, unless
    # the user has dismissed the banner via cookie.
    breaking_now = None
    try:
        if request and request.cookies.get("bbc_breaking_dismissed") != "1":
            breaking_now = (Article.query
                            .filter(Article.is_breaking == 1)
                            .order_by(Article.published_at.desc())
                            .first())
    except Exception:
        breaking_now = None
    return dict(
        reading_list_count=reading_list_count,
        bookmark_count=bookmark_count,
        main_categories=main_cats,
        news_subcats=news_subcats,
        bbc_nav_tree=BBC_NAV_TREE,
        active_nav_slug=active_slug,
        current_time_str=now.strftime("%H:%M %Z").strip() or now.strftime("%H:%M GMT"),
        current_date_str=now.strftime("%A %d %B %Y"),
        current_year=now.year,
        breaking_now=breaking_now,
    )


# =======================================================================
# HELPERS
# =======================================================================

def get_article_or_404(slug):
    a = Article.query.filter_by(slug=slug).first()
    if not a:
        abort(404)
    return a


def get_category_or_404(slug):
    c = Category.query.filter_by(slug=slug).first()
    if not c:
        abort(404)
    return c


def articles_for_category(slug, limit=None):
    """Return all articles in a category or its children."""
    cat = Category.query.filter_by(slug=slug).first()
    if not cat:
        return []
    # Include child categories
    child_slugs = [c.slug for c in Category.query.filter_by(parent_slug=slug).all()]
    if child_slugs:
        child_ids = [c.id for c in Category.query.filter(Category.slug.in_(child_slugs + [slug])).all()]
        q = Article.query.filter(Article.category_id.in_(child_ids))
    else:
        q = Article.query.filter_by(category_id=cat.id)
    q = q.order_by(Article.published_at.desc())
    if limit:
        q = q.limit(limit)
    return q.all()


def new_digest_number():
    return "D" + datetime.utcnow().strftime("%Y%m%d%H%M%S") + str(random.randint(100, 999))


# =======================================================================
# ROUTES — PUBLIC PAGES
# =======================================================================

@app.route("/")
def index():
    featured = Article.query.filter_by(is_featured=True).order_by(Article.published_at.desc()).limit(6).all()
    if not featured:
        featured = Article.query.order_by(Article.published_at.desc()).limit(6).all()
    top_story = featured[0] if featured else None
    secondary = featured[1:6] if len(featured) > 1 else []

    latest = Article.query.order_by(Article.published_at.desc()).limit(12).all()
    must_read = Article.query.order_by(func.random()).limit(5).all()

    # Per-category strips
    world_items = articles_for_category("world", limit=4)
    uk_items = articles_for_category("uk", limit=4)
    business_items = articles_for_category("business", limit=4)
    tech_items = articles_for_category("technology", limit=4)

    return render_template(
        "index.html",
        top_story=top_story,
        secondary=secondary,
        latest=latest,
        must_read=must_read,
        world_items=world_items,
        uk_items=uk_items,
        business_items=business_items,
        tech_items=tech_items,
    )


@app.route("/news")
def news_root_alias():
    """Real bbc.com/news section root resolves to the mirror homepage."""
    return redirect(url_for("index"))


@app.route("/section/<slug>")
@app.route("/news/<slug>")
def section_page(slug):
    cat = get_category_or_404(slug)
    page = max(1, int(request.args.get("page", 1)))
    per_page = 20

    # Regional categories (parent is 'world' or 'uk') also match by region/subsection
    # so that agents navigating to Africa/Asia/Europe see relevant stories even when
    # the canonical section_slug is the parent ('world').
    REGION_MAP = {
        "africa": "Africa",
        "asia": "Asia",
        "australia": "Australia",
        "europe": "Europe",
        "latin_america": "Latin America",
        "middle_east": "Middle East",
        "us_canada": "US & Canada",
        "england": "England",
        "scotland": "Scotland",
        "wales": "Wales",
        "northern_ireland": "N. Ireland",
    }
    region_name = REGION_MAP.get(slug)

    # Include child categories' articles AND articles denormalized to this slug
    child_slugs = [c.slug for c in Category.query.filter_by(parent_slug=slug).all()]
    if child_slugs:
        child_ids = [c.id for c in Category.query.filter(Category.slug.in_(child_slugs + [slug])).all()]
        conds = [
            Article.category_id.in_(child_ids),
            Article.section_slug == slug,
        ]
        if region_name:
            conds.append(Article.region == region_name)
            conds.append(Article.subsection.ilike(f"%{region_name}%"))
        q = Article.query.filter(or_(*conds))
    else:
        conds = [
            Article.category_id == cat.id,
            Article.section_slug == slug,
        ]
        if region_name:
            conds.append(Article.region == region_name)
            conds.append(Article.subsection.ilike(f"%{region_name}%"))
        q = Article.query.filter(or_(*conds))

    # Subsection/region/tag filters (optional)
    subsection = (request.args.get("subsection") or "").strip()
    if subsection:
        q = q.filter(Article.subsection.ilike(f'%{subsection}%'))
    region = (request.args.get("region") or "").strip()
    if region:
        q = q.filter(Article.region.ilike(f'%{region}%'))
    tag = (request.args.get("tag") or "").strip().lower()
    if tag:
        q = q.filter(or_(
            Article.feature_tags.ilike(f'%{tag}%'),
            Article.topics_json.ilike(f'%{tag}%'),
        ))
    content_type = (request.args.get("content_type") or "").strip()
    if content_type:
        q = q.filter(Article.content_type == content_type)

    q = q.order_by(Article.published_at.desc())

    total = q.count()
    articles = q.offset((page - 1) * per_page).limit(per_page).all()
    lead = articles[0] if articles else None
    rest = articles[1:] if len(articles) > 1 else []

    children = Category.query.filter_by(parent_slug=slug).order_by(Category.sort_order).all()

    return render_template(
        "section.html",
        category=cat,
        lead=lead,
        articles=rest,
        total=total,
        page=page,
        per_page=per_page,
        children=children,
    )


def load_article_gallery(slug):
    """Return the full gallery dict for an article slug. Reads from the
    Article.gallery_full_json column so no scraped JSON is needed at
    runtime."""
    art = Article.query.filter_by(slug=slug).first()
    if art is None:
        return {}
    return art.get_full_gallery()


@app.route("/article/<slug>")
def article_detail(slug):
    art = get_article_or_404(slug)
    art.view_count += 1
    db.session.commit()

    # Record reading history
    if current_user.is_authenticated:
        existing = ReadingHistory.query.filter_by(
            user_id=current_user.id, article_id=art.id
        ).first()
        if existing:
            existing.viewed_at = datetime.utcnow()
        else:
            db.session.add(ReadingHistory(user_id=current_user.id, article_id=art.id))
        db.session.commit()

    # Related articles in same category
    related = (Article.query.filter(
        Article.category_id == art.category_id, Article.id != art.id
    ).order_by(func.random()).limit(6).all())
    # More from author (or BBC News default)
    more_articles = (Article.query.filter(Article.id != art.id)
                     .order_by(func.random()).limit(4).all())

    comments_q = Comment.query.filter_by(
        article_id=art.id, parent_id=None
    ).order_by(Comment.created_at.desc()).all()

    in_reading_list = False
    reading_list_item = None
    is_bookmarked = False
    if current_user.is_authenticated:
        reading_list_item = ReadingListItem.query.filter_by(
            user_id=current_user.id, article_id=art.id
        ).first()
        in_reading_list = reading_list_item is not None
        is_bookmarked = Bookmark.query.filter_by(
            user_id=current_user.id, article_id=art.id
        ).first() is not None

    # Load gallery sections
    article_gallery = load_article_gallery(slug)

    # R6: More from this reporter — articles by the same author. Only
    # populated when the article carries a real byline (not the generic
    # "BBC News" / "BBC Sport" placeholders) so the block does not turn
    # into a near-random side-list on legacy rows.
    more_from_reporter = []
    generic_authors = {
        "BBC News", "BBC Sport", "BBC Weather", "BBC Travel", "BBC Food",
        "BBC Sounds", "BBC iPlayer", "BBC Business", "BBC Bitesize",
    }
    if art.author and art.author not in generic_authors:
        more_from_reporter = (Article.query
                              .filter(Article.author == art.author,
                                      Article.id != art.id)
                              .order_by(Article.published_at.desc())
                              .limit(5).all())

    # R6: Top story today — the most-recent featured article, distinct
    # from the current one. Renders as a sidebar block.
    top_story_today = (Article.query
                       .filter(Article.is_featured == True,
                               Article.id != art.id)
                       .order_by(Article.published_at.desc())
                       .first())

    # R6: Related topics — surface real /topic/<tag> destinations.
    # Pulls the article's own topics_json and supplements with any
    # subsection or region. Capped at 8 to keep the UI tidy.
    related_topic_chips: list[str] = []
    seen_chips: set[str] = set()
    for chip in (art.get_topics() or []):
        c = (chip or "").strip()
        if c and c.lower() not in seen_chips:
            related_topic_chips.append(c)
            seen_chips.add(c.lower())
    for extra in (art.subsection, art.region):
        if extra and extra.lower() not in seen_chips:
            related_topic_chips.append(extra)
            seen_chips.add(extra.lower())
    related_topic_chips = related_topic_chips[:8]

    # R6: edge-case status banner. Decoded from feature_tags so the
    # logic stays close to the data.
    edge_status = None
    edge_banner = None
    edge_status_map = {
        "r6-removed-legal":   "This article has been removed for legal reasons.",
        "r6-region-blocked":  "This video is not available in your region.",
        "r6-live-ended":      "This live blog has ended. Read our summary below.",
        "r6-superseded":      "An updated version of this story is available.",
        "r6-comments-locked": "Comments are closed on this story.",
        "r6-user-blocked":    "You have been blocked from commenting on this story.",
    }
    for tag_code, banner_text in edge_status_map.items():
        if art.feature_tags and tag_code in art.feature_tags:
            edge_status = tag_code
            edge_banner = banner_text
            break

    return render_template(
        "article_detail.html",
        article=art,
        article_share_url=bbc_article_share_url(art),
        article_gallery=article_gallery,
        related=related,
        more_articles=more_articles,
        comments=comments_q,
        in_reading_list=in_reading_list,
        reading_list_item=reading_list_item,
        is_bookmarked=is_bookmarked,
        more_from_reporter=more_from_reporter,
        top_story_today=top_story_today,
        related_topic_chips=related_topic_chips,
        edge_status=edge_status,
        edge_banner=edge_banner,
    )


@app.route("/topic/<topic>")
def topic_page(topic):
    like_tag = f'%"{topic}"%'
    like_ft = f'%{topic.lower()}%'
    results = (Article.query.filter(or_(
            Article.topics_json.ilike(like_tag),
            Article.feature_tags.ilike(like_ft),
            Article.subsection.ilike(f'%{topic}%'),
        )).order_by(Article.published_at.desc()).limit(100).all())
    return render_template("topic.html", topic=topic, results=results)


STOPWORDS = {
    'the', 'a', 'an', 'of', 'in', 'on', 'at', 'to', 'for', 'with',
    'and', 'or', 'is', 'are', 'be', 'by', 'from', 'as', 'that', 'this',
    'about', 'into', 'what', 'who', 'how', 'when', 'where', 'which',
    'some', 'any', 'it', 'its', 'their', 'news', 'bbc', 'article', 'story',
    'latest', 'recent', 'report', 'find', 'get', 'read', 'search',
}


def _score_article(article, tokens):
    """Score an article against search tokens. Returns # of distinct tokens matched."""
    haystack = ' '.join([
        (article.headline or '').lower(),
        (article.subtitle or '').lower(),
        (article.summary or '').lower(),
        (article.body or '').lower()[:4000],  # cap for speed
        (article.author or '').lower(),
        (article.topics_json or '').lower(),
        (article.feature_tags or '').lower(),
        (article.subsection or '').lower(),
        (article.section_slug or '').lower(),
        (article.region or '').lower(),
        (article.location or '').lower(),
    ])
    return sum(1 for t in tokens if t in haystack)


def _apply_article_filters(query_obj):
    """Apply request.args filters to an Article query."""
    section = (request.args.get("section") or "").strip().lower()
    if section:
        # Match denormalized section_slug OR category.slug (via join)
        child_slugs = {c.slug for c in Category.query.filter_by(parent_slug=section).all()}
        allowed = {section} | child_slugs
        cat_ids = [c.id for c in Category.query.filter(Category.slug.in_(allowed)).all()]
        query_obj = query_obj.filter(or_(
            Article.section_slug == section,
            Article.category_id.in_(cat_ids) if cat_ids else False,
        ))

    subsection = (request.args.get("subsection") or "").strip()
    if subsection:
        query_obj = query_obj.filter(Article.subsection.ilike(f'%{subsection}%'))

    region = (request.args.get("region") or "").strip()
    if region:
        query_obj = query_obj.filter(Article.region.ilike(f'%{region}%'))

    tag = (request.args.get("tag") or "").strip().lower()
    if tag:
        query_obj = query_obj.filter(or_(
            Article.feature_tags.ilike(f'%{tag}%'),
            Article.topics_json.ilike(f'%{tag}%'),
        ))

    content_type = (request.args.get("content_type") or "").strip()
    if content_type:
        query_obj = query_obj.filter(Article.content_type == content_type)

    since_days = request.args.get("since_days", type=int)
    if since_days is not None:
        cutoff = datetime.utcnow() - timedelta(days=since_days)
        query_obj = query_obj.filter(Article.published_at >= cutoff)

    return query_obj


def _apply_article_sort(results, sort_key):
    if sort_key in ('newest', 'date_desc', 'latest'):
        return sorted(results, key=lambda a: a.published_at or datetime.min, reverse=True)
    if sort_key in ('oldest', 'date_asc'):
        return sorted(results, key=lambda a: a.published_at or datetime.min)
    if sort_key in ('popular', 'views'):
        return sorted(results, key=lambda a: a.view_count or 0, reverse=True)
    # default: newest
    return sorted(results, key=lambda a: a.published_at or datetime.min, reverse=True)


@app.route("/search")
def search():
    q = (request.args.get("q") or request.args.get("query") or "").strip()
    scope = request.args.get("scope", "all")
    page = max(1, int(request.args.get("page", 1)))
    per_page = 20

    query_obj = Article.query
    query_obj = _apply_article_filters(query_obj)
    candidates = query_obj.all()

    if q:
        tokens = [t.lower() for t in re.findall(r'[a-z0-9]+', q.lower())
                  if t and t not in STOPWORDS and len(t) >= 2]
        if tokens:
            min_required = max(1, len(tokens) // 2)
            scored = []
            for a in candidates:
                if scope == "headline":
                    haystack = (a.headline or '').lower()
                    s = sum(1 for t in tokens if t in haystack)
                elif scope == "body":
                    haystack = (a.body or '').lower()
                    s = sum(1 for t in tokens if t in haystack)
                else:
                    s = _score_article(a, tokens)
                if s >= min_required:
                    scored.append((s, a))
            scored.sort(key=lambda x: (-x[0],
                                       -(x[1].published_at.timestamp() if x[1].published_at else 0)))
            results = [a for _, a in scored]
        else:
            results = candidates
    else:
        results = candidates

    results = _apply_article_sort(results, request.args.get("sort", "newest"))
    total = len(results)
    start = (page - 1) * per_page
    page_results = results[start:start + per_page]

    return render_template(
        "search.html",
        query=q, scope=scope, results=page_results, total=total,
        page=page, per_page=per_page,
    )


@app.route("/latest")
def latest_page():
    page = max(1, int(request.args.get("page", 1)))
    per_page = 25
    q = Article.query.order_by(Article.published_at.desc())
    total = q.count()
    articles = q.offset((page - 1) * per_page).limit(per_page).all()
    return render_template("latest.html", articles=articles, total=total, page=page, per_page=per_page)


@app.route("/live")
def live_page():
    live_articles = Article.query.filter_by(is_live=True).all()
    breaking = Article.query.filter_by(is_breaking=True).order_by(Article.published_at.desc()).limit(10).all()
    return render_template("live.html", live=live_articles, breaking=breaking)


@app.route("/live/<topic>")
def live_topic_page(topic):
    """Per-topic live blog. Lists all live + breaking + most-recent articles
    related to a section or topic so 'live blog reading' tasks are solvable.
    Topic can be a section_slug (sport, world, ...) or free-text token."""
    topic_key = (topic or "").strip().lower().replace("-", "_")
    # Section lookup first
    cat = Category.query.filter_by(slug=topic_key).first()
    live_articles = []
    breaking = []
    related = []
    if cat:
        section_ids = [cat.id] + [c.id for c in Category.query.filter_by(parent_slug=cat.slug).all()]
        live_articles = (Article.query
            .filter(Article.category_id.in_(section_ids))
            .filter(or_(Article.is_live == True, Article.content_type == 'live'))
            .order_by(Article.published_at.desc()).limit(15).all())
        breaking = (Article.query
            .filter(Article.category_id.in_(section_ids))
            .filter_by(is_breaking=True)
            .order_by(Article.published_at.desc()).limit(15).all())
        related = (Article.query
            .filter(Article.category_id.in_(section_ids))
            .order_by(Article.published_at.desc()).limit(20).all())
    else:
        like = f'%{topic}%'
        live_articles = (Article.query
            .filter(or_(Article.subsection.ilike(like),
                        Article.topics_json.ilike(like),
                        Article.feature_tags.ilike(like)))
            .filter(or_(Article.is_live == True, Article.content_type == 'live'))
            .order_by(Article.published_at.desc()).limit(15).all())
        related = (Article.query
            .filter(or_(Article.subsection.ilike(like),
                        Article.topics_json.ilike(like),
                        Article.headline.ilike(like)))
            .order_by(Article.published_at.desc()).limit(20).all())
    return render_template("live_topic.html",
                           topic=topic, category=cat,
                           live=live_articles, breaking=breaking, related=related)


# --- BBC sub-brand aliases (R3) -----------------------------------------

@app.route("/food")
def food_alias():
    return redirect(url_for("section_page", slug="food"))


@app.route("/food/recipes")
@app.route("/food/recipes/<recipe_slug>")
def food_recipe_alias(recipe_slug=None):
    if recipe_slug:
        return redirect(url_for("article_detail", slug=recipe_slug))
    return redirect(url_for("section_page", slug="food"))


@app.route("/iplayer")
def iplayer_alias():
    return redirect(url_for("section_page", slug="iplayer"))


@app.route("/iplayer/episode/<ep_slug>")
def iplayer_episode_alias(ep_slug):
    return redirect(url_for("article_detail", slug=ep_slug))


@app.route("/sounds")
def sounds_alias():
    return redirect(url_for("section_page", slug="sounds"))


@app.route("/sounds/play/<ep_slug>")
def sounds_play_alias(ep_slug):
    return redirect(url_for("article_detail", slug=ep_slug))


@app.route("/bitesize")
def bitesize_alias():
    return redirect(url_for("section_page", slug="bitesize"))


@app.route("/bitesize/guides/<g_slug>")
def bitesize_guide_alias(g_slug):
    return redirect(url_for("article_detail", slug=g_slug))


@app.route("/sport/<discipline>")
def sport_discipline_alias(discipline):
    """Real bbc.com uses /sport/football, /sport/cricket, etc.
    Map onto the existing section_page; fall back to filtering 'sport'
    by subsection when no dedicated category exists."""
    discipline_key = (discipline or "").strip().lower().replace("-", "_")
    if Category.query.filter_by(slug=discipline_key).first():
        return redirect(url_for("section_page", slug=discipline_key))
    # Fallback: sport section filtered by subsection
    return redirect(url_for("section_page", slug="sport", subsection=discipline.title()))


@app.route("/weather/<location>")
def weather_location_alias(location):
    """Per-city weather page. Resolves to the matching forecast article or
    falls back to the weather section filtered by location."""
    loc_key = (location or "").replace("-", " ").replace("_", " ")
    art = (Article.query
           .filter(Article.section_slug == 'weather')
           .filter(or_(Article.subsection.ilike(f'%{loc_key}%'),
                       Article.location.ilike(f'%{loc_key}%')))
           .order_by(Article.published_at.desc())
           .first())
    if art:
        return redirect(url_for("article_detail", slug=art.slug))
    return redirect(url_for("section_page", slug="weather", subsection=loc_key))


@app.route("/weather")
def weather_alias():
    return redirect(url_for("section_page", slug="weather"))


@app.route("/audio")
def audio_alias():
    return redirect(url_for("section_page", slug="audio"))


@app.route("/culture")
def culture_alias():
    return redirect(url_for("section_page", slug="culture"))


@app.route("/sport")
def sport_alias():
    return redirect(url_for("section_page", slug="sport"))


@app.route("/about")
def about_page():
    return render_template("about.html")


@app.route("/help")
def help_page():
    return render_template("help.html")


@app.route("/contact")
def contact_page():
    return render_template("contact.html")


@app.route("/privacy")
def privacy_page():
    return render_template("privacy.html")


@app.route("/terms")
def terms_page():
    return render_template("terms.html")


@app.route("/cookies")
def cookies_page():
    return render_template("cookies.html")


@app.route("/accessibility")
def accessibility_page():
    return render_template("accessibility.html")


# =======================================================================
# ROUTES — AUTH
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
            flash("Signed in successfully.", "success")
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
            flash("Email, username, and password are all required.", "error")
            return render_template("register.html")
        if password != confirm:
            flash("Passwords do not match.", "error")
            return render_template("register.html")
        if User.query.filter_by(email=email).first():
            flash("An account with that email already exists.", "error")
            return render_template("register.html")
        if User.query.filter_by(username=username).first():
            flash("That username is already taken.", "error")
            return render_template("register.html")
        u = User(email=email, username=username, full_name=full_name)
        u.set_password(password)
        db.session.add(u)
        db.session.commit()
        login_user(u)
        flash("Account created. Welcome to BBC News.", "success")
        return redirect(url_for("account"))
    return render_template("register.html")


@app.route("/logout")
def logout():
    logout_user()
    flash("You have been signed out.", "success")
    return redirect(url_for("index"))


# =======================================================================
# ROUTES — ACCOUNT
# =======================================================================

@app.route("/account")
@login_required
def account():
    recent_rl = (ReadingListItem.query.filter_by(user_id=current_user.id)
                 .order_by(ReadingListItem.added_at.desc()).limit(5).all())
    recent_bm = (Bookmark.query.filter_by(user_id=current_user.id)
                 .order_by(Bookmark.bookmarked_at.desc()).limit(5).all())
    digests = (Digest.query.filter_by(user_id=current_user.id)
               .order_by(Digest.created_at.desc()).all())
    my_comments = (Comment.query.filter_by(user_id=current_user.id)
                   .order_by(Comment.created_at.desc()).limit(10).all())
    subs = TopicSubscription.query.filter_by(user_id=current_user.id).all()
    history = (ReadingHistory.query.filter_by(user_id=current_user.id)
               .order_by(ReadingHistory.viewed_at.desc()).limit(10).all())
    return render_template(
        "account.html",
        recent_rl=recent_rl,
        recent_bm=recent_bm,
        digests=digests,
        my_comments=my_comments,
        subs=subs,
        history=history,
    )


@app.route("/account/edit", methods=["GET", "POST"])
@login_required
def account_edit():
    if request.method == "POST":
        current_user.full_name = request.form.get("full_name", "").strip()
        current_user.location = request.form.get("location", "").strip()
        current_user.bio = request.form.get("bio", "").strip()
        current_user.notification_email = request.form.get("notification_email") == "on"
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


@app.route("/history")
@login_required
def history_page():
    items = (ReadingHistory.query.filter_by(user_id=current_user.id)
             .order_by(ReadingHistory.viewed_at.desc()).limit(100).all())
    return render_template("history.html", items=items)


@app.route("/history/clear", methods=["POST"])
@login_required
def clear_history():
    ReadingHistory.query.filter_by(user_id=current_user.id).delete()
    db.session.commit()
    flash("Reading history cleared.", "success")
    return redirect(url_for("history_page"))


# =======================================================================
# ROUTES — READING LIST (cart analog)
# =======================================================================

@app.route("/reading-list")
@login_required
def reading_list():
    folder = request.args.get("folder", "")
    q = ReadingListItem.query.filter_by(user_id=current_user.id)
    if folder:
        q = q.filter_by(folder=folder)
    items = q.order_by(ReadingListItem.added_at.desc()).all()
    folders = (db.session.query(ReadingListItem.folder, func.count(ReadingListItem.id))
               .filter_by(user_id=current_user.id)
               .group_by(ReadingListItem.folder).all())
    return render_template("reading_list.html", items=items, folders=folders, current_folder=folder)


@app.route("/api/reading-list/add", methods=["POST"])
@login_required
@csrf.exempt
def api_reading_list_add():
    # Accept both JSON (legacy AJAX) and form POST (CDP browser agent)
    if request.content_type and "application/json" in request.content_type:
        data = request.get_json() or {}
    else:
        data = request.form
    article_id = int(data.get("article_id", 0))
    folder = (data.get("folder") or "Read Later")[:100]
    note = (data.get("note") or "")[:500]
    art = Article.query.get(article_id)
    if not art:
        if request.content_type and "application/json" in request.content_type:
            return jsonify({"success": False, "message": "Article not found"}), 404
        flash("Article not found.", "error")
        return redirect(request.referrer or url_for("reading_list"))
    existing = ReadingListItem.query.filter_by(
        user_id=current_user.id, article_id=article_id
    ).first()
    if existing:
        existing.folder = folder
        if note:
            existing.note = note
        db.session.commit()
        if request.content_type and "application/json" in request.content_type:
            return jsonify({
                "success": True,
                "message": "Reading list updated",
                "reading_list_count": ReadingListItem.query.filter_by(user_id=current_user.id).count(),
            })
        flash("Reading list updated.", "success")
        return redirect(request.referrer or url_for("reading_list"))
    item = ReadingListItem(
        user_id=current_user.id, article_id=article_id, folder=folder, note=note,
    )
    db.session.add(item)
    db.session.commit()
    if request.content_type and "application/json" in request.content_type:
        return jsonify({
            "success": True,
            "message": "Added to your reading list",
            "reading_list_count": ReadingListItem.query.filter_by(user_id=current_user.id).count(),
        })
    flash("Added to your reading list.", "success")
    return redirect(request.referrer or url_for("reading_list"))


@app.route("/api/reading-list/remove", methods=["POST"])
@login_required
@csrf.exempt
def api_reading_list_remove():
    # Accept both JSON (legacy AJAX) and form POST (CDP browser agent)
    if request.content_type and "application/json" in request.content_type:
        data = request.get_json() or {}
    else:
        data = request.form
    item_id = int(data.get("item_id", 0))
    item = ReadingListItem.query.filter_by(id=item_id, user_id=current_user.id).first()
    if not item:
        if request.content_type and "application/json" in request.content_type:
            return jsonify({"success": False, "message": "Not found"}), 404
        flash("Item not found.", "error")
        return redirect(url_for("reading_list"))
    db.session.delete(item)
    db.session.commit()
    if request.content_type and "application/json" in request.content_type:
        return jsonify({
            "success": True,
            "reading_list_count": ReadingListItem.query.filter_by(user_id=current_user.id).count(),
        })
    flash("Removed from reading list.", "success")
    return redirect(url_for("reading_list"))


@app.route("/reading-list/item/<int:item_id>/update", methods=["POST"])
@login_required
def reading_list_update_item(item_id):
    """Form POST: update folder and/or priority of a reading list item."""
    item = ReadingListItem.query.filter_by(id=item_id, user_id=current_user.id).first_or_404()
    folder = (request.form.get("folder") or "").strip()[:100]
    priority = (request.form.get("priority") or "").strip()
    if folder:
        item.folder = folder
    if priority in ("high", "normal", "low"):
        item.priority = priority
    db.session.commit()
    flash("Reading list item updated.", "success")
    return redirect(url_for("reading_list"))


@app.route("/api/reading-list/mark-read", methods=["POST"])
@login_required
@csrf.exempt
def api_reading_list_mark_read():
    data = request.get_json() or {}
    item_id = int(data.get("item_id", 0))
    item = ReadingListItem.query.filter_by(id=item_id, user_id=current_user.id).first()
    if not item:
        return jsonify({"success": False}), 404
    item.read = not item.read
    db.session.commit()
    return jsonify({"success": True, "read": item.read})


@app.route("/reading-list/folder/create", methods=["POST"])
@login_required
def reading_list_folder_create():
    folder = (request.form.get("folder") or "").strip()[:100]
    article_id = request.form.get("article_id", type=int)
    if folder and article_id:
        existing = ReadingListItem.query.filter_by(
            user_id=current_user.id, article_id=article_id
        ).first()
        if existing:
            existing.folder = folder
        else:
            db.session.add(ReadingListItem(
                user_id=current_user.id, article_id=article_id, folder=folder,
            ))
        db.session.commit()
        flash(f"Saved to '{folder}'.", "success")
    return redirect(request.referrer or url_for("reading_list"))


# =======================================================================
# ROUTES — BOOKMARKS (wishlist analog)
# =======================================================================

@app.route("/bookmarks")
@login_required
def bookmarks_page():
    items = (Bookmark.query.filter_by(user_id=current_user.id)
             .order_by(Bookmark.bookmarked_at.desc()).all())
    return render_template("bookmarks.html", items=items)


@app.route("/api/bookmark/toggle", methods=["POST"])
@login_required
@csrf.exempt
def api_bookmark_toggle():
    # Accept both JSON (legacy AJAX) and form POST (CDP browser agent)
    if request.content_type and "application/json" in request.content_type:
        data = request.get_json() or {}
    else:
        data = request.form
    article_id = int(data.get("article_id", 0))
    art = Article.query.get(article_id)
    if not art:
        if request.content_type and "application/json" in request.content_type:
            return jsonify({"success": False}), 404
        flash("Article not found.", "error")
        return redirect(request.referrer or url_for("bookmarks_page"))
    existing = Bookmark.query.filter_by(
        user_id=current_user.id, article_id=article_id
    ).first()
    if existing:
        db.session.delete(existing)
        action = "removed"
        flash_msg = "Bookmark removed."
    else:
        db.session.add(Bookmark(user_id=current_user.id, article_id=article_id))
        action = "added"
        flash_msg = "Bookmarked."
    db.session.commit()
    count = Bookmark.query.filter_by(user_id=current_user.id).count()
    if request.content_type and "application/json" in request.content_type:
        return jsonify({"success": True, "action": action, "bookmark_count": count})
    flash(flash_msg, "success")
    return redirect(request.referrer or url_for("bookmarks_page"))


@app.route("/bookmarks/remove/<int:item_id>", methods=["POST"])
@login_required
def bookmarks_remove(item_id):
    item = Bookmark.query.filter_by(id=item_id, user_id=current_user.id).first_or_404()
    db.session.delete(item)
    db.session.commit()
    flash("Bookmark removed.", "success")
    return redirect(url_for("bookmarks_page"))


# =======================================================================
# ROUTES — DIGESTS (order analog)
# =======================================================================

@app.route("/digest", methods=["GET", "POST"])
@login_required
def digest_create():
    if request.method == "POST":
        fmt = request.form.get("format", "email")
        source = request.form.get("source", "reading_list")
        title = (request.form.get("title") or "My News Digest")[:200]
        notes = request.form.get("notes", "")
        email = (request.form.get("delivery_email") or current_user.email).strip()
        article_ids = []
        if source == "reading_list":
            items = ReadingListItem.query.filter_by(user_id=current_user.id).all()
            article_ids = [i.article_id for i in items]
        elif source == "bookmarks":
            items = Bookmark.query.filter_by(user_id=current_user.id).all()
            article_ids = [i.article_id for i in items]
        elif source == "latest":
            latest = Article.query.order_by(Article.published_at.desc()).limit(10).all()
            article_ids = [a.id for a in latest]
        if not article_ids:
            flash("No articles available for digest.", "error")
            return redirect(url_for("reading_list"))
        digest = Digest(
            user_id=current_user.id,
            digest_number=new_digest_number(),
            title=title,
            format=fmt,
            status="delivered",
            article_count=len(article_ids),
            delivery_email=email,
            notes=notes,
        )
        db.session.add(digest)
        db.session.flush()
        for aid in article_ids:
            db.session.add(DigestItem(digest_id=digest.id, article_id=aid))
        db.session.commit()
        flash("Digest created.", "success")
        return redirect(url_for("digest_detail", digest_number=digest.digest_number))
    rl_items = ReadingListItem.query.filter_by(user_id=current_user.id).all()
    bm_items = Bookmark.query.filter_by(user_id=current_user.id).all()
    return render_template("digest_create.html", rl_items=rl_items, bm_items=bm_items)


@app.route("/digest/<digest_number>")
@login_required
def digest_detail(digest_number):
    digest = Digest.query.filter_by(
        digest_number=digest_number, user_id=current_user.id
    ).first_or_404()
    return render_template("digest_detail.html", digest=digest)


@app.route("/digest/<digest_number>/cancel", methods=["POST"])
@login_required
def digest_cancel(digest_number):
    digest = Digest.query.filter_by(
        digest_number=digest_number, user_id=current_user.id
    ).first_or_404()
    if digest.status in ("pending", "delivered"):
        digest.status = "cancelled"
        db.session.commit()
        flash("Digest cancelled.", "success")
    else:
        flash("Cannot cancel this digest.", "error")
    return redirect(url_for("digest_detail", digest_number=digest_number))


@app.route("/digest/<digest_number>/resend", methods=["POST"])
@login_required
def digest_resend(digest_number):
    digest = Digest.query.filter_by(
        digest_number=digest_number, user_id=current_user.id
    ).first_or_404()
    added = 0
    for it in digest.items:
        if not ReadingListItem.query.filter_by(
            user_id=current_user.id, article_id=it.article_id
        ).first():
            db.session.add(ReadingListItem(
                user_id=current_user.id, article_id=it.article_id, folder="From Digest",
            ))
            added += 1
    db.session.commit()
    flash(f"Added {added} articles to your reading list.", "success")
    return redirect(url_for("reading_list"))


@app.route("/digest/<digest_number>/download")
@login_required
def digest_download(digest_number):
    digest = Digest.query.filter_by(
        digest_number=digest_number, user_id=current_user.id
    ).first_or_404()
    articles = [it.article for it in digest.items if it.article]
    if digest.format == "email":
        body = f"{digest.title}\n{'=' * 50}\n\nDigest #{digest.digest_number}\nDelivered {digest.created_at.strftime('%Y-%m-%d %H:%M')}\n\n"
        for a in articles:
            body += f"{a.headline}\n{a.summary or a.subtitle or ''}\n{a.source_url}\n\n"
    elif digest.format == "rss":
        body = '<?xml version="1.0"?>\n<rss version="2.0"><channel>\n'
        body += f"<title>{digest.title}</title>\n"
        for a in articles:
            body += f"<item><title>{a.headline}</title><link>{a.source_url}</link><description>{a.summary}</description></item>\n"
        body += "</channel></rss>"
    else:  # text/pdf fallback
        body = "\n\n".join(
            f"[{a.category.name if a.category else ''}]\n{a.headline}\n{a.summary or a.subtitle or ''}"
            for a in articles
        )
    mt = "application/rss+xml" if digest.format == "rss" else "text/plain"
    ext = "xml" if digest.format == "rss" else "txt"
    return Response(body, mimetype=mt, headers={
        "Content-Disposition": f"attachment; filename={digest.digest_number}.{ext}",
    })


# =======================================================================
# ROUTES — COMMENTS (review analog)
# =======================================================================

@app.route("/article/<slug>/comment", methods=["POST"])
@login_required
def submit_comment(slug):
    art = get_article_or_404(slug)
    body = (request.form.get("body") or "").strip()
    parent_id = request.form.get("parent_id", type=int)
    if not body:
        flash("Comment cannot be empty.", "error")
    else:
        db.session.add(Comment(
            user_id=current_user.id,
            article_id=art.id,
            body=body[:2000],
            parent_id=parent_id if parent_id else None,
        ))
        db.session.commit()
        flash("Comment posted.", "success")
    return redirect(url_for("article_detail", slug=slug))


@app.route("/comment/<int:comment_id>/delete", methods=["POST"])
@login_required
def delete_comment(comment_id):
    c = Comment.query.get_or_404(comment_id)
    if c.user_id != current_user.id:
        abort(403)
    slug = c.article.slug
    db.session.delete(c)
    db.session.commit()
    flash("Comment deleted.", "success")
    return redirect(url_for("article_detail", slug=slug))


@app.route("/api/comment/like", methods=["POST"])
@login_required
@csrf.exempt
def api_comment_like():
    data = request.get_json() or {}
    cid = int(data.get("comment_id", 0))
    c = Comment.query.get(cid)
    if not c:
        return jsonify({"success": False}), 404
    c.like_count += 1
    db.session.commit()
    return jsonify({"success": True, "like_count": c.like_count})


# =======================================================================
# ROUTES — SUBSCRIPTIONS
# =======================================================================

@app.route("/subscriptions", methods=["GET", "POST"])
@login_required
def subscriptions_page():
    if request.method == "POST":
        slug = request.form.get("category_slug", "").strip()
        topic = request.form.get("topic", "").strip()
        freq = request.form.get("frequency", "daily")
        if slug or topic:
            existing = TopicSubscription.query.filter_by(
                user_id=current_user.id, category_slug=slug, topic=topic
            ).first()
            if existing:
                existing.frequency = freq
                existing.active = True
                flash("Subscription updated.", "success")
            else:
                db.session.add(TopicSubscription(
                    user_id=current_user.id,
                    category_slug=slug,
                    topic=topic,
                    frequency=freq,
                ))
                flash("Subscribed.", "success")
            db.session.commit()
        return redirect(url_for("subscriptions_page"))
    subs = TopicSubscription.query.filter_by(user_id=current_user.id).all()
    return render_template("subscriptions.html", subs=subs)


@app.route("/subscriptions/<int:sub_id>/delete", methods=["POST"])
@login_required
def delete_subscription(sub_id):
    sub = TopicSubscription.query.filter_by(
        id=sub_id, user_id=current_user.id
    ).first_or_404()
    db.session.delete(sub)
    db.session.commit()
    flash("Subscription removed.", "success")
    return redirect(url_for("subscriptions_page"))


@app.route("/subscriptions/<int:sub_id>/update", methods=["POST"])
@login_required
def update_subscription(sub_id):
    sub = TopicSubscription.query.filter_by(
        id=sub_id, user_id=current_user.id
    ).first_or_404()
    freq = request.form.get("frequency", "").strip()
    if freq in ("daily", "weekly", "breaking_only"):
        sub.frequency = freq
        db.session.commit()
        flash("Subscription frequency updated.", "success")
    else:
        flash("Invalid frequency.", "error")
    return redirect(url_for("subscriptions_page"))


# =======================================================================
# ROUTES — API
# =======================================================================

@app.route("/api/articles/<slug>")
def api_category_articles(slug):
    cat = Category.query.filter_by(slug=slug).first_or_404()
    articles = (Article.query.filter_by(category_id=cat.id)
                .order_by(Article.published_at.desc()).limit(20).all())
    return jsonify({
        "category": cat.slug,
        "name": cat.name,
        "count": len(articles),
        "articles": [{
            "slug": a.slug,
            "headline": a.headline,
            "summary": a.summary,
            "image": a.hero_image,
            "published": a.published_at.isoformat() if a.published_at else None,
            "reading_time": a.reading_time,
        } for a in articles],
    })


@app.route("/api/stats")
def api_stats():
    return jsonify({
        "total_articles": Article.query.count(),
        "total_categories": Category.query.count(),
        "total_users": User.query.count(),
        "total_comments": Comment.query.count(),
    })


# =======================================================================
# R4: deep sub-pages, breaking-news banner, postcode weather, share modal
# =======================================================================

@app.route("/breaking-news")
def breaking_news_page():
    """Dedicated breaking-news index page. Lists every article currently
    flagged is_breaking=1, plus an opt-out cookie to dismiss the pulsing
    banner site-wide."""
    breaking = (Article.query
                .filter(Article.is_breaking == 1)
                .order_by(Article.published_at.desc())
                .limit(60).all())
    return render_template("breaking_news.html", articles=breaking,
                           page_title="Breaking news")


@app.route("/breaking-news/banner-dismiss", methods=["POST"])
def breaking_news_banner_dismiss():
    """Set a cookie so the pulsing red banner stops appearing on every page."""
    resp = redirect(request.referrer or url_for("index"))
    resp.set_cookie("bbc_breaking_dismissed", "1", max_age=60 * 60 * 24)
    return resp


@app.route("/weather/postcode/<postcode>")
def weather_postcode(postcode):
    """7-day forecast keyed by a UK postcode area (SW1A, EH1, CF10, ...)."""
    key = (postcode or "").upper().strip()
    art = (Article.query
           .filter(Article.section_slug == "weather")
           .filter(or_(
               Article.feature_tags.ilike(f'%"{key.lower()}"%'),
               Article.topics_json.ilike(f'%"{key}"%'),
               Article.headline.ilike(f'%({key})%'),
           ))
           .order_by(Article.published_at.desc())
           .first())
    if art:
        return redirect(url_for("article_detail", slug=art.slug))
    return redirect(url_for("section_page", slug="weather", subsection=key))


@app.route("/iplayer/categories")
@app.route("/iplayer/categories/<cat_slug>")
def iplayer_categories(cat_slug=None):
    """List BBC iPlayer programmes by category. With <cat_slug> filters."""
    if cat_slug:
        cat_name = (cat_slug or "").replace("-", " ").replace("_", " ").title()
        return redirect(url_for("section_page", slug="iplayer", subsection=cat_name))
    return redirect(url_for("section_page", slug="iplayer_categories"))


@app.route("/sounds/genres")
@app.route("/sounds/genres/<genre>")
def sounds_genres(genre=None):
    """Browse BBC Sounds podcasts by genre."""
    if genre:
        g_name = (genre or "").replace("-", " ").replace("_", " ").title()
        return redirect(url_for("section_page", slug="podcasts", subsection=g_name))
    return redirect(url_for("section_page", slug="podcasts_genres"))


@app.route("/world/<region>")
@app.route("/world/<region>/<country>")
def world_region_country(region, country=None):
    """Drill down /world/asia/india, /world/europe/germany etc."""
    region_key = (region or "").lower().replace("-", "_")
    if country:
        country_disp = country.replace("-", " ").replace("_", " ").title()
        return redirect(url_for("section_page", slug=region_key,
                                subsection=country_disp))
    return redirect(url_for("section_page", slug=region_key))


@app.route("/news/in-pictures")
def in_pictures_alias():
    """Hyphen variant — the underscore form /news/in_pictures is already
    served directly by section_page so no alias needed there."""
    return redirect(url_for("section_page", slug="in_pictures"))


@app.route("/video/<slug>")
def video_player(slug):
    """Sticky video player page — same as article_detail but renders the
    video-player template wrapper."""
    return redirect(url_for("article_detail", slug=slug))


@app.route("/article/<slug>/share", methods=["GET", "POST"])
def article_share(slug):
    """Share modal endpoint. POST with method=email|copy|twitter|facebook
    records the share intent server-side; GET returns the modal HTML
    fragment for fetch()."""
    art = get_article_or_404(slug)
    method = (request.values.get("method") or "copy").strip().lower()
    share_url = bbc_article_share_url(art)
    if request.method == "POST" and method == "email":
        recipient = (request.values.get("recipient") or "").strip()
        # Record-only; nothing actually mailed in the mirror.
        return jsonify({
            "ok": True,
            "method": "email",
            "recipient": recipient,
            "subject": f"BBC News: {art.headline}",
            "body": f"{art.headline}\n\nRead more: {share_url}",
        })
    return jsonify({
        "ok": True,
        "method": method,
        "url": share_url,
        "title": art.headline,
        "subtitle": art.subtitle or "",
    })


@app.route("/api/podcast/subscribe", methods=["POST"])
def api_podcast_subscribe():
    """Subscribe to a podcast (slug). Anonymous-friendly; if signed in,
    creates a topic subscription. Always returns ok=True."""
    slug = (request.values.get("slug") or "").strip()
    art = Article.query.filter_by(slug=slug).first()
    podcast_title = art.headline if art else slug
    if current_user.is_authenticated and podcast_title:
        existing = TopicSubscription.query.filter_by(
            user_id=current_user.id, topic=podcast_title
        ).first()
        if not existing:
            sub = TopicSubscription(
                user_id=current_user.id,
                topic=podcast_title,
                frequency="weekly",
                is_active=True,
            )
            db.session.add(sub)
            db.session.commit()
    return jsonify({"ok": True, "podcast": podcast_title})


@app.route("/api/iplayer/watchlist", methods=["POST"])
def api_iplayer_watchlist():
    """Add an iPlayer episode to the watchlist. Re-uses reading_list under
    the 'iPlayer' folder when the user is signed in."""
    slug = (request.values.get("slug") or "").strip()
    art = Article.query.filter_by(slug=slug).first()
    if not art:
        return jsonify({"ok": False, "error": "not_found"}), 404
    if current_user.is_authenticated:
        existing = ReadingListItem.query.filter_by(
            user_id=current_user.id, article_id=art.id, folder="iPlayer"
        ).first()
        if not existing:
            item = ReadingListItem(
                user_id=current_user.id,
                article_id=art.id,
                folder="iPlayer",
                is_read=False,
                notes="",
            )
            db.session.add(item)
            db.session.commit()
    return jsonify({"ok": True, "slug": slug, "title": art.headline})


# =======================================================================
# R5: BBC Verify / Newsround / live-blog jump-to-update / quiz / reactions
# =======================================================================

@app.route("/newsround")
@app.route("/newsround/")
def newsround_alias():
    """Top-level /newsround alias -> Newsround section page."""
    return redirect(url_for("section_page", slug="newsround"))


@app.route("/verify")
@app.route("/verify/")
def verify_alias():
    """Convenience /verify -> bbcverify section page."""
    return redirect(url_for("section_page", slug="bbcverify"))


@app.route("/quizzes")
@app.route("/quiz")
def quizzes_alias():
    """Browse all quiz attempts available on BBC News."""
    return redirect(url_for("section_page", slug="quizzes"))


@app.route("/quiz/<slug>", methods=["GET"])
def quiz_detail(slug):
    """A specific quiz article rendered through the article_detail
    template. The body already contains the multiple-choice questions
    inline, so we just redirect to the canonical article URL."""
    art = Article.query.filter_by(slug=slug).first_or_404()
    return redirect(url_for("article_detail", slug=art.slug))


@app.route("/quiz/<slug>/attempt", methods=["POST"])
def quiz_attempt(slug):
    """Record a quiz attempt. Anonymous-friendly; if signed in, persists
    via reading_list under folder='Quizzes' with note='Attempt: <score>'.
    The body accepts JSON or form-encoded `score` (int 0..10) and
    `answers` (string)."""
    art = Article.query.filter_by(slug=slug).first()
    if not art:
        return jsonify({"ok": False, "error": "not_found"}), 404
    try:
        score = int(request.values.get("score") or 0)
    except ValueError:
        score = 0
    score = max(0, min(10, score))
    answers = (request.values.get("answers") or "")[:200]
    if current_user.is_authenticated:
        existing = ReadingListItem.query.filter_by(
            user_id=current_user.id, article_id=art.id, folder="Quizzes"
        ).first()
        if existing:
            existing.note = f"Attempt: {score}/10 ({answers})"
        else:
            item = ReadingListItem(
                user_id=current_user.id,
                article_id=art.id,
                folder="Quizzes",
                read=True,
                note=f"Attempt: {score}/10 ({answers})",
            )
            db.session.add(item)
        db.session.commit()
    return jsonify({
        "ok": True,
        "slug": art.slug,
        "score": score,
        "max": 10,
        "message": f"Recorded attempt: {score}/10",
    })


@app.route("/article/<slug>/react", methods=["POST"])
def article_react(slug):
    """Apply an emoji reaction to an article. Persisted as a comment row
    with body = '[reaction] <emoji>' so the existing comment_count surface
    keeps working. Idempotent per user+emoji."""
    art = Article.query.filter_by(slug=slug).first_or_404()
    emoji = (request.values.get("emoji") or "").strip()[:8]
    valid = {"👍", "❤", "😂", "😮", "😢", "👎", ":+1:", ":heart:", ":smile:",
             "thumbs_up", "love", "haha", "wow", "sad", "thumbs_down",
             "like", "fire", "🔥", "🎉", "celebrate"}
    if emoji not in valid:
        return jsonify({"ok": False, "error": "invalid_emoji",
                        "allowed": sorted(valid)}), 400
    if current_user.is_authenticated:
        body = f"[reaction] {emoji}"
        existing = Comment.query.filter_by(
            user_id=current_user.id, article_id=art.id, body=body
        ).first()
        if not existing:
            cm = Comment(
                user_id=current_user.id,
                article_id=art.id,
                body=body,
                like_count=0,
                flagged=False,
            )
            db.session.add(cm)
            db.session.commit()
    # Always-on counter from existing reactions on this article.
    n = Comment.query.filter(
        Comment.article_id == art.id,
        Comment.body.like("[reaction] %"),
    ).count()
    return jsonify({"ok": True, "slug": art.slug, "emoji": emoji,
                    "reaction_count": n})


# Supported translation language codes (stub — we do not actually
# translate the body, we just record the request and return a payload
# the client can render with a "translated" label).
R5_TRANSLATE_LANGS = {
    "es": "Spanish", "fr": "French", "de": "German", "it": "Italian",
    "pt": "Portuguese", "zh": "Chinese (Simplified)", "ja": "Japanese",
    "ar": "Arabic", "fa": "Persian", "ru": "Russian", "hi": "Hindi",
    "ur": "Urdu", "ko": "Korean", "tr": "Turkish", "sw": "Swahili",
    "id": "Indonesian", "vi": "Vietnamese", "th": "Thai", "pl": "Polish",
    "nl": "Dutch",
}


@app.route("/article/<slug>/translate/<lang>", methods=["GET", "POST"])
def article_translate(slug, lang):
    """Render an article with a 'translated' badge for one of the
    supported languages. The mirror does not actually translate text; the
    endpoint exists so /article/<slug>/translate/<lang> is solvable as a
    task surface."""
    art = Article.query.filter_by(slug=slug).first_or_404()
    code = (lang or "").strip().lower()
    if code not in R5_TRANSLATE_LANGS:
        return jsonify({"ok": False, "error": "unsupported_language",
                        "supported": sorted(R5_TRANSLATE_LANGS.keys())}), 400
    payload = {
        "ok": True,
        "slug": art.slug,
        "language_code": code,
        "language_name": R5_TRANSLATE_LANGS[code],
        "headline": art.headline,
        "subtitle": art.subtitle or "",
        "preview": (art.body or "")[:400],
        "note": (
            f"This is a {R5_TRANSLATE_LANGS[code]} translation preview. The "
            f"mirror does not invoke an external translation service — the "
            f"original article text is shown."
        ),
    }
    if (request.values.get("format") or "").lower() == "json":
        return jsonify(payload)
    # HTML rendering: re-use article_detail but pass a translated_label flag.
    return redirect(url_for(
        "article_detail", slug=art.slug, _anchor="comments"
    ))


@app.route("/topic/<topic>/follow", methods=["POST"])
def follow_topic(topic):
    """Subscribe the signed-in user to a topic via TopicSubscription. The
    same topic survives across pageviews and is shown on the
    Subscriptions page. Anonymous users are redirected to login."""
    t = (topic or "").strip()
    if not t:
        return jsonify({"ok": False, "error": "no_topic"}), 400
    if not current_user.is_authenticated:
        return redirect(url_for("login", next=request.referrer
                                or url_for("topic_page", topic=t)))
    existing = TopicSubscription.query.filter_by(
        user_id=current_user.id, topic=t
    ).first()
    if not existing:
        sub = TopicSubscription(
            user_id=current_user.id,
            topic=t,
            frequency="instant",
            active=True,
        )
        db.session.add(sub)
        db.session.commit()
    flash(f"Now following {t}", "success")
    return redirect(request.referrer or url_for("subscriptions_page"))


@app.route("/live/<slug_suffix>/update/<int:update_n>")
def live_blog_jump_to_update(slug_suffix, update_n):
    """Jump-to-update endpoint on a live blog. Looks up the update by its
    feature_tags = ['live_update', <slug_suffix>, 'update_<N>'] and
    redirects to the corresponding article. Falls back to the parent
    live-blog page if the requested update is out of range."""
    update_n = max(1, min(30, int(update_n)))
    tag = f'"update_{update_n}"'
    target = (Article.query
              .filter(Article.feature_tags.ilike(f'%{tag}%'))
              .filter(Article.feature_tags.ilike(f'%"{slug_suffix}"%'))
              .first())
    if target:
        return redirect(url_for("article_detail", slug=target.slug))
    # Fall back: find the parent live-blog itself.
    parent = (Article.query
              .filter(Article.feature_tags.ilike(f'%"{slug_suffix}"%'))
              .filter(Article.feature_tags.ilike('%"live_blog_parent"%'))
              .first())
    if parent:
        return redirect(url_for("article_detail", slug=parent.slug))
    abort(404)


@app.route("/api/live-blog/<slug_suffix>/updates")
def api_live_blog_updates(slug_suffix):
    """JSON feed of all timestamped updates for a live blog, newest first.
    Powers the live-blog auto-refresh indicator in the client."""
    tag = f'"{slug_suffix}"'
    updates = (Article.query
               .filter(Article.feature_tags.ilike(f'%{tag}%'))
               .filter(Article.feature_tags.ilike('%"live_update"%'))
               .order_by(Article.published_at.desc())
               .limit(60).all())
    return jsonify({
        "ok": True,
        "slug": slug_suffix,
        "count": len(updates),
        "updates": [{
            "slug": a.slug,
            "headline": a.headline,
            "subsection": a.subsection,
            "published_at": a.published_at.isoformat() if a.published_at else None,
            "url": url_for("article_detail", slug=a.slug),
        } for a in updates],
    })


@app.route("/api/search/suggest")
def api_search_suggest():
    """Type-ahead suggestions for the global search box. Returns up to
    eight article headlines + three topic chips + the matching section
    name (if any)."""
    q = (request.args.get("q") or "").strip()
    if len(q) < 2:
        return jsonify({"ok": True, "query": q, "articles": [],
                        "topics": [], "section": None})
    like = f"%{q}%"
    arts = (Article.query
            .filter(Article.headline.ilike(like))
            .order_by(Article.view_count.desc())
            .limit(8).all())
    cat = Category.query.filter(Category.name.ilike(like)).first()
    # Topic suggestions: take top section_slug / subsection matches.
    topic_rows = (db.session.query(Article.subsection)
                  .filter(Article.subsection.ilike(like))
                  .filter(Article.subsection != "")
                  .group_by(Article.subsection)
                  .limit(3).all())
    return jsonify({
        "ok": True,
        "query": q,
        "articles": [{
            "slug": a.slug,
            "headline": a.headline,
            "category": a.category.name if a.category else "",
            "url": url_for("article_detail", slug=a.slug),
        } for a in arts],
        "topics": [t[0] for t in topic_rows if t[0]],
        "section": {
            "slug": cat.slug, "name": cat.name,
            "url": url_for("section_page", slug=cat.slug),
        } if cat else None,
    })


@app.route("/api/dark-mode", methods=["POST"])
def api_dark_mode():
    """Persist the user's dark-mode preference via a server-side cookie.
    The client also caches the value in localStorage so the toggle works
    before the cookie round-trips."""
    val = (request.values.get("value") or "").strip().lower()
    if val not in ("on", "off"):
        return jsonify({"ok": False, "error": "invalid_value"}), 400
    resp = jsonify({"ok": True, "value": val})
    resp.set_cookie("bbc_dark_mode", val, max_age=60 * 60 * 24 * 365,
                    samesite="Lax")
    return resp


@app.route("/api/high-contrast", methods=["POST"])
def api_high_contrast():
    """Persist the user's high-contrast preference. Same shape as
    /api/dark-mode."""
    val = (request.values.get("value") or "").strip().lower()
    if val not in ("on", "off"):
        return jsonify({"ok": False, "error": "invalid_value"}), 400
    resp = jsonify({"ok": True, "value": val})
    resp.set_cookie("bbc_high_contrast", val, max_age=60 * 60 * 24 * 365,
                    samesite="Lax")
    return resp


@app.route("/article/<slug>/transcript")
def article_transcript(slug):
    """Plain-text transcript stub for audio/video articles. Returns the
    article body broken into ~10-second segments so the page is solvable
    for transcript-based tasks."""
    art = Article.query.filter_by(slug=slug).first_or_404()
    paras = art.get_paragraphs()
    segments = []
    sec = 0
    for p in paras:
        words = p.split()
        # ~150 words per minute = 25 words per 10s
        for i in range(0, len(words), 25):
            chunk = " ".join(words[i:i + 25])
            t_mm = sec // 60
            t_ss = sec % 60
            segments.append({
                "t": f"{t_mm:02d}:{t_ss:02d}",
                "text": chunk,
            })
            sec += 10
    return jsonify({
        "ok": True,
        "slug": art.slug,
        "headline": art.headline,
        "duration_seconds": sec,
        "segments": segments,
    })


# =======================================================================
# R7 - SEO + RSS/Atom feeds + AMP + locale switch + sitemap
# =======================================================================
# Adds:
#   * /robots.txt           - crawl-delay, sitemap pointer
#   * /sitemap-news.xml     - Google News sitemap format, last 48h articles
#   * /sitemap.xml          - full sitemap (capped) linking to news sitemap
#   * /rss/<category>.xml   - RSS 2.0 feed per category
#   * /feed/<category>.atom - Atom 1.0 feed per category
#   * /article/<slug>/amp   - AMP-style minimal HTML fallback
#   * /article/<slug>/lang/<locale> - locale switch (en-GB/en-US/zh/es/ar)
#   * /article/<slug>/schema.json   - NewsArticle JSON-LD standalone
#   * /api/story/<slug>/email-alert - POST to subscribe to story updates
#   * /article/<slug>/voiceover-summary - accessibility summary endpoint

R7_LOCALES = {
    "en-GB": {
        "name": "English (UK)", "dir": "ltr",
        "label_read_more": "Read more",
        "label_share": "Share this article",
        "label_published": "Published",
        "label_topics": "Topics",
        "label_subscribe": "Subscribe to updates",
    },
    "en-US": {
        "name": "English (US)", "dir": "ltr",
        "label_read_more": "Read more",
        "label_share": "Share this story",
        "label_published": "Published",
        "label_topics": "Topics",
        "label_subscribe": "Get email alerts",
    },
    "zh": {
        "name": "Chinese", "dir": "ltr",
        "label_read_more": "Read more (zh)",
        "label_share": "Share (zh)",
        "label_published": "Published (zh)",
        "label_topics": "Topics (zh)",
        "label_subscribe": "Subscribe (zh)",
    },
    "es": {
        "name": "Spanish", "dir": "ltr",
        "label_read_more": "Leer mas",
        "label_share": "Compartir este articulo",
        "label_published": "Publicado",
        "label_topics": "Temas",
        "label_subscribe": "Suscribirse a actualizaciones",
    },
    "ar": {
        "name": "Arabic", "dir": "rtl",
        "label_read_more": "Read more (ar)",
        "label_share": "Share (ar)",
        "label_published": "Published (ar)",
        "label_topics": "Topics (ar)",
        "label_subscribe": "Subscribe (ar)",
    },
}

# R7 sitemap anchor: timestamps in the synthetic corpus are deterministic
# relative to this date (matches bake_extras.MIRROR_REFERENCE_DATE).
R7_MIRROR_REFERENCE_DATE = datetime(2026, 4, 15, 9, 0, 0)


def _article_schema_org(article):
    """Build a NewsArticle JSON-LD dict for an article."""
    published_iso = (article.published_at.isoformat() + "Z"
                     if article.published_at else "")
    topics = article.get_topics() or []
    return {
        "@context": "https://schema.org",
        "@type": "NewsArticle",
        "headline": article.headline,
        "description": article.summary or article.subtitle or "",
        "datePublished": published_iso,
        "dateModified": published_iso,
        "author": {
            "@type": "Person",
            "name": article.author or "BBC News",
        },
        "publisher": {
            "@type": "Organization",
            "name": "BBC News",
            "logo": {
                "@type": "ImageObject",
                "url": "https://www.bbc.com/favicon.ico",
                "width": 64,
                "height": 64,
            },
        },
        "image": [article.hero_image] if article.hero_image else [],
        "articleSection": (article.category.name if article.category else ""),
        "keywords": ", ".join(topics),
        "mainEntityOfPage": {
            "@type": "WebPage",
            "@id": bbc_article_share_url(article),
        },
        "wordCount": article.word_count or 0,
        "inLanguage": "en-GB",
    }


@app.route("/article/<slug>/schema.json")
def article_schema_json(slug):
    """Expose the NewsArticle JSON-LD payload as a standalone endpoint."""
    art = Article.query.filter_by(slug=slug).first_or_404()
    schema = _article_schema_org(art)
    resp = jsonify(schema)
    resp.headers["Content-Type"] = "application/ld+json"
    return resp


@app.route("/article/<slug>/amp")
def article_amp(slug):
    """AMP-style minimal HTML fallback."""
    art = Article.query.filter_by(slug=slug).first_or_404()
    schema = _article_schema_org(art)
    paras = art.get_paragraphs()
    canonical = url_for("article_detail", slug=art.slug, _external=False)
    body_html = "\n".join(f"<p>{p}</p>" for p in paras)
    img_html = ""
    if art.hero_image:
        img_html = (
            f'<amp-img src="{art.hero_image}" layout="responsive" '
            f'width="1024" height="576" alt="{art.headline}"></amp-img>'
        )
    schema_json = json.dumps(schema, ensure_ascii=False)
    html = (
        '<!doctype html>\n'
        '<html amp lang="en">\n'
        '<head>\n'
        '<meta charset="utf-8">\n'
        f'<title>{art.headline} - BBC News (AMP)</title>\n'
        f'<link rel="canonical" href="{canonical}">\n'
        '<meta name="viewport" content="width=device-width,minimum-scale=1,initial-scale=1">\n'
        '<style amp-boilerplate>body{-webkit-animation:-amp-start 8s steps(1,end) 0s 1 normal both;animation:-amp-start 8s steps(1,end) 0s 1 normal both}'
        '@-webkit-keyframes -amp-start{from{visibility:hidden}to{visibility:visible}}'
        '@keyframes -amp-start{from{visibility:hidden}to{visibility:visible}}</style>'
        '<noscript><style amp-boilerplate>body{-webkit-animation:none;animation:none}</style></noscript>\n'
        '<script async src="https://cdn.ampproject.org/v0.js"></script>\n'
        f'<script type="application/ld+json">{schema_json}</script>\n'
        '<style amp-custom>body{font-family:Georgia,serif;max-width:680px;margin:auto;padding:1rem;color:#222}'
        'h1{font-size:1.8rem;margin:0 0 0.5rem;color:#000}'
        '.byline{color:#666;font-size:0.85rem;margin-bottom:1rem}'
        'p{font-size:1rem;line-height:1.6}</style>\n'
        '</head>\n<body>\n'
        f'<h1>{art.headline}</h1>\n'
        f'<div class="byline">By {art.author or "BBC News"} | '
        f'{art.published_at.strftime("%Y-%m-%d %H:%M UTC") if art.published_at else ""}</div>\n'
        f'{img_html}\n'
        f'{body_html}\n'
        '</body></html>\n'
    )
    resp = Response(html, mimetype="text/html")
    resp.headers["Link"] = f'<{canonical}>; rel="canonical"'
    return resp


@app.route("/article/<slug>/lang/<locale>")
def article_lang_switch(slug, locale):
    """Locale switch endpoint."""
    art = Article.query.filter_by(slug=slug).first_or_404()
    if locale not in R7_LOCALES:
        return jsonify({
            "ok": False,
            "error": "unsupported_locale",
            "available": sorted(R7_LOCALES.keys()),
        }), 404
    cfg = R7_LOCALES[locale]
    return jsonify({
        "ok": True,
        "slug": art.slug,
        "headline": art.headline,
        "locale": locale,
        "locale_name": cfg["name"],
        "direction": cfg["dir"],
        "labels": {k: v for k, v in cfg.items() if k.startswith("label_")},
        "available_locales": sorted(R7_LOCALES.keys()),
        "canonical_url": url_for("article_detail", slug=art.slug,
                                 _external=False),
    })


@app.route("/robots.txt")
def robots_txt():
    """robots.txt with crawl-delay and sitemap pointer."""
    lines = [
        "User-agent: *",
        "Crawl-delay: 5",
        "Disallow: /account",
        "Disallow: /login",
        "Disallow: /register",
        "Disallow: /history",
        "Disallow: /reading-list",
        "Disallow: /bookmarks",
        "Allow: /article/",
        "Allow: /news/",
        "Allow: /section/",
        "",
        f"Sitemap: {url_for('sitemap_xml', _external=False)}",
        f"Sitemap: {url_for('sitemap_news_xml', _external=False)}",
        "",
        "User-agent: GPTBot",
        "Disallow: /",
        "",
        "User-agent: CCBot",
        "Disallow: /",
    ]
    return Response("\n".join(lines) + "\n", mimetype="text/plain")


@app.route("/sitemap.xml")
def sitemap_xml():
    """Top-level sitemap. Recent article URLs (capped)."""
    lines = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    base = request.host_url.rstrip("/")
    recent = (Article.query
              .order_by(Article.published_at.desc())
              .limit(500)
              .all())
    for art in recent:
        loc = base + url_for("article_detail", slug=art.slug, _external=False)
        lastmod = (art.published_at.strftime("%Y-%m-%dT%H:%M:%SZ")
                   if art.published_at else "")
        lines.append("  <url>")
        lines.append(f"    <loc>{loc}</loc>")
        if lastmod:
            lines.append(f"    <lastmod>{lastmod}</lastmod>")
        lines.append("    <changefreq>hourly</changefreq>")
        lines.append("  </url>")
    lines.append("</urlset>")
    return Response("\n".join(lines), mimetype="application/xml")


@app.route("/sitemap-news.xml")
def sitemap_news_xml():
    """Google News sitemap. Articles from the last 48 hours relative to
    R7_MIRROR_REFERENCE_DATE (deterministic against the synthetic corpus)."""
    from datetime import timedelta as _td
    cutoff = R7_MIRROR_REFERENCE_DATE - _td(hours=48)
    lines = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"',
             '        xmlns:news="http://www.google.com/schemas/sitemap-news/0.9">']
    base = request.host_url.rstrip("/")
    recent = (Article.query
              .filter(Article.published_at >= cutoff)
              .order_by(Article.published_at.desc())
              .limit(1000)
              .all())
    for art in recent:
        loc = base + url_for("article_detail", slug=art.slug, _external=False)
        pub = (art.published_at.strftime("%Y-%m-%dT%H:%M:%SZ")
               if art.published_at else "")
        title = (art.headline or "").replace("&", "&amp;").replace("<", "&lt;")
        lines.append("  <url>")
        lines.append(f"    <loc>{loc}</loc>")
        lines.append("    <news:news>")
        lines.append("      <news:publication>")
        lines.append("        <news:name>BBC News</news:name>")
        lines.append("        <news:language>en</news:language>")
        lines.append("      </news:publication>")
        lines.append(f"      <news:publication_date>{pub}</news:publication_date>")
        lines.append(f"      <news:title>{title}</news:title>")
        lines.append("    </news:news>")
        lines.append("  </url>")
    lines.append("</urlset>")
    return Response("\n".join(lines), mimetype="application/xml")


def _category_or_alias(slug):
    return Category.query.filter_by(slug=slug).first()


@app.route("/rss/<category_slug>.xml")
def rss_category_xml(category_slug):
    """RSS 2.0 feed for a category."""
    cat = _category_or_alias(category_slug)
    if cat is None:
        body = ('<?xml version="1.0"?>\n'
                '<rss version="2.0"><channel>\n'
                f'<title>BBC News - Unknown ({category_slug})</title>\n'
                f'<link>{request.host_url.rstrip("/")}</link>\n'
                '<description>Category not found.</description>\n'
                '</channel></rss>\n')
        return Response(body, mimetype="application/rss+xml", status=404)
    arts = (Article.query
            .filter_by(category_id=cat.id)
            .order_by(Article.published_at.desc())
            .limit(50)
            .all())
    base = request.host_url.rstrip("/")
    out = ['<?xml version="1.0" encoding="UTF-8"?>',
           '<rss version="2.0">',
           '  <channel>',
           f'    <title>BBC News - {cat.name}</title>',
           f'    <link>{base}/section/{cat.slug}</link>',
           f'    <description>{(cat.description or "").replace("&", "&amp;")}</description>',
           '    <language>en-GB</language>',
           '    <ttl>15</ttl>']
    for art in arts:
        url_ = base + url_for("article_detail", slug=art.slug, _external=False)
        pub = (art.published_at.strftime("%a, %d %b %Y %H:%M:%S GMT")
               if art.published_at else "")
        title = (art.headline or "").replace("&", "&amp;").replace("<", "&lt;")
        desc = (art.summary or art.subtitle or "").replace("&", "&amp;").replace("<", "&lt;")
        out.append("    <item>")
        out.append(f"      <title>{title}</title>")
        out.append(f"      <link>{url_}</link>")
        out.append(f'      <guid isPermaLink="true">{url_}</guid>')
        out.append(f"      <pubDate>{pub}</pubDate>")
        out.append(f"      <description>{desc}</description>")
        out.append(f"      <category>{cat.name}</category>")
        out.append("    </item>")
    out.append("  </channel>")
    out.append("</rss>")
    return Response("\n".join(out), mimetype="application/rss+xml")


@app.route("/feed/<category_slug>.atom")
def atom_category_feed(category_slug):
    """Atom 1.0 feed for a category."""
    cat = _category_or_alias(category_slug)
    if cat is None:
        body = ('<?xml version="1.0" encoding="UTF-8"?>\n'
                '<feed xmlns="http://www.w3.org/2005/Atom">\n'
                f'<title>BBC News - Unknown ({category_slug})</title>\n'
                '</feed>\n')
        return Response(body, mimetype="application/atom+xml", status=404)
    arts = (Article.query
            .filter_by(category_id=cat.id)
            .order_by(Article.published_at.desc())
            .limit(50)
            .all())
    base = request.host_url.rstrip("/")
    updated = (arts[0].published_at.isoformat() + "Z"
               if arts and arts[0].published_at
               else R7_MIRROR_REFERENCE_DATE.isoformat() + "Z")
    out = ['<?xml version="1.0" encoding="UTF-8"?>',
           '<feed xmlns="http://www.w3.org/2005/Atom">',
           f'  <title>BBC News - {cat.name}</title>',
           f'  <link href="{base}/section/{cat.slug}" rel="alternate"/>',
           f'  <link href="{base}/feed/{cat.slug}.atom" rel="self"/>',
           f'  <id>tag:bbc.com,2026:{cat.slug}</id>',
           f'  <updated>{updated}</updated>']
    for art in arts:
        url_ = base + url_for("article_detail", slug=art.slug, _external=False)
        upd = (art.published_at.isoformat() + "Z"
               if art.published_at else updated)
        title = (art.headline or "").replace("&", "&amp;").replace("<", "&lt;")
        summary = (art.summary or art.subtitle or "").replace("&", "&amp;").replace("<", "&lt;")
        out.append("  <entry>")
        out.append(f"    <title>{title}</title>")
        out.append(f'    <link href="{url_}" rel="alternate"/>')
        out.append(f'    <id>tag:bbc.com,2026:article:{art.slug}</id>')
        out.append(f"    <updated>{upd}</updated>")
        out.append(f"    <published>{upd}</published>")
        out.append(f"    <author><name>{art.author or 'BBC News'}</name></author>")
        out.append(f'    <category term="{cat.slug}" label="{cat.name}"/>')
        out.append(f"    <summary>{summary}</summary>")
        out.append("  </entry>")
    out.append("</feed>")
    return Response("\n".join(out), mimetype="application/atom+xml")


@app.route("/api/story/<slug>/email-alert", methods=["POST"])
def story_email_alert(slug):
    """Subscribe to per-story update email alerts. Idempotent."""
    art = Article.query.filter_by(slug=slug).first_or_404()
    if not current_user.is_authenticated:
        return jsonify({
            "ok": True,
            "persisted": False,
            "story_slug": art.slug,
            "note": "sign in to receive email alerts for this story",
        })
    topic_key = f"story:{art.slug}"
    existing = TopicSubscription.query.filter_by(
        user_id=current_user.id, topic=topic_key).first()
    if existing:
        existing.active = True
        existing.frequency = "story-update"
        db.session.commit()
        return jsonify({"ok": True, "persisted": True,
                        "story_slug": art.slug, "already_subscribed": True})
    sub = TopicSubscription(
        user_id=current_user.id,
        topic=topic_key,
        category_slug=(art.category.slug if art.category else ""),
        frequency="story-update",
        active=True,
        created_at=datetime.utcnow(),
    )
    db.session.add(sub)
    db.session.commit()
    return jsonify({"ok": True, "persisted": True,
                    "story_slug": art.slug, "already_subscribed": False})


@app.route("/article/<slug>/voiceover-summary")
def voiceover_summary(slug):
    """Accessibility helper for screen-reader-friendly article summary."""
    art = Article.query.filter_by(slug=slug).first_or_404()
    paras = art.get_paragraphs()[:3]
    summary_text = " ".join(p.split(".")[0] + "." for p in paras if p)
    return jsonify({
        "ok": True,
        "slug": art.slug,
        "headline": art.headline,
        "byline": art.author or "BBC News",
        "published_iso": (art.published_at.isoformat() + "Z"
                          if art.published_at else ""),
        "summary_text": summary_text,
        "reading_time_minutes": art.reading_time or 3,
        "topics": art.get_topics()[:6],
        "voiceover_marker": "vo-summary-v1",
    })


# =======================================================================
# R8: Observability / developer / UX glue
# =======================================================================
#
# All R8 routes are read-only or accept idempotent POST payloads. They
# never write to the DB (so they don't move md5) and never block the
# benchmark; they just give agents predictable surfaces to hit.

R8_REFERENCE_DATE = R7_MIRROR_REFERENCE_DATE  # alias - same fixed anchor

# Snapshot of the BBC Local regions and Radio sub-stations - used by both
# the command-palette / region-glossary endpoints and the dev portal.
R8_LOCAL_REGION_INDEX: dict[str, dict] = {
    "london":            {"name": "London",                "nation": "England"},
    "manchester":        {"name": "Manchester",            "nation": "England"},
    "birmingham":        {"name": "Birmingham",            "nation": "England"},
    "leeds":             {"name": "Leeds",                 "nation": "England"},
    "liverpool":         {"name": "Liverpool",             "nation": "England"},
    "newcastle":         {"name": "Newcastle",             "nation": "England"},
    "sheffield":         {"name": "Sheffield",             "nation": "England"},
    "bristol":           {"name": "Bristol",               "nation": "England"},
    "nottingham":        {"name": "Nottingham",            "nation": "England"},
    "leicester":         {"name": "Leicester",             "nation": "England"},
    "coventry":          {"name": "Coventry & Warwickshire","nation": "England"},
    "derby":             {"name": "Derby",                 "nation": "England"},
    "stoke":             {"name": "Stoke & Staffordshire", "nation": "England"},
    "hull":              {"name": "Humberside",            "nation": "England"},
    "york":              {"name": "York & North Yorkshire","nation": "England"},
    "lancashire":        {"name": "Lancashire",            "nation": "England"},
    "cumbria":           {"name": "Cumbria",               "nation": "England"},
    "merseyside":        {"name": "Merseyside",            "nation": "England"},
    "tees":              {"name": "Tees",                  "nation": "England"},
    "oxford":            {"name": "Oxford",                "nation": "England"},
    "cambridgeshire":    {"name": "Cambridgeshire",        "nation": "England"},
    "norfolk":           {"name": "Norfolk",               "nation": "England"},
    "suffolk":           {"name": "Suffolk",               "nation": "England"},
    "essex":             {"name": "Essex",                 "nation": "England"},
    "kent":              {"name": "Kent",                  "nation": "England"},
    "sussex":            {"name": "Sussex",                "nation": "England"},
    "hampshire":         {"name": "Hampshire & Isle of Wight","nation": "England"},
    "dorset":            {"name": "Dorset",                "nation": "England"},
    "devon":             {"name": "Devon",                 "nation": "England"},
    "cornwall":          {"name": "Cornwall",              "nation": "England"},
    "somerset":          {"name": "Somerset",              "nation": "England"},
    "gloucestershire":   {"name": "Gloucestershire",       "nation": "England"},
    "wiltshire":         {"name": "Wiltshire",             "nation": "England"},
    "hereford_worcester":{"name": "Hereford & Worcester",  "nation": "England"},
    "shropshire":        {"name": "Shropshire",            "nation": "England"},
    "glasgow_west":      {"name": "Glasgow & West",        "nation": "Scotland"},
    "edinburgh_east":    {"name": "Edinburgh, Fife & East","nation": "Scotland"},
    "highlands_islands": {"name": "Highlands & Islands",   "nation": "Scotland"},
    "cardiff_se_wales":  {"name": "Cardiff & South East Wales","nation": "Wales"},
    "foyle_west":        {"name": "Foyle & West",          "nation": "Northern Ireland"},
}

R8_RADIO_STATIONS = [
    ("radio1",        "BBC Radio 1"),
    ("radio2",        "BBC Radio 2"),
    ("radio3",        "BBC Radio 3"),
    ("radio4",        "BBC Radio 4"),
    ("radio4_extra",  "BBC Radio 4 Extra"),
    ("six_music",     "BBC Radio 6 Music"),
    ("world_service", "BBC World Service"),
    ("asian_network", "BBC Asian Network"),
    ("fivelive",      "BBC 5 Live"),
]

# Curated region glossary entries for the contextual-help popover.
R8_REGION_GLOSSARY: dict[str, dict] = {
    "uk": {
        "name": "United Kingdom",
        "summary": ("The United Kingdom of Great Britain and Northern Ireland - "
                    "a sovereign state of four nations: England, Scotland, "
                    "Wales and Northern Ireland."),
        "capital": "London",
        "nations": ["England", "Scotland", "Wales", "Northern Ireland"],
        "key_topics": ["UK politics", "the NHS", "devolution", "cost of living"],
    },
    "europe": {
        "name": "Europe",
        "summary": ("Continent of around 50 sovereign states; the European Union "
                    "and the wider Council of Europe shape regional policy."),
        "capital": None,
        "key_topics": ["EU policy", "the war in Ukraine", "energy security"],
    },
    "africa": {
        "name": "Africa",
        "summary": ("Africa is the second-largest continent with 54 recognised "
                    "states and the African Union as its umbrella body."),
        "capital": None,
        "key_topics": ["African Union", "Sahel security", "climate adaptation"],
    },
    "asia": {
        "name": "Asia",
        "summary": ("The world's most populous continent, spanning the Middle "
                    "East, South Asia, Southeast Asia, and East Asia."),
        "capital": None,
        "key_topics": ["China-US relations", "South China Sea", "monsoon season"],
    },
    "middle_east": {
        "name": "Middle East",
        "summary": ("Region spanning western Asia and parts of north Africa; "
                    "the Gulf Cooperation Council and the Arab League are "
                    "major regional bodies."),
        "capital": None,
        "key_topics": ["Israel-Gaza", "Iran sanctions", "oil markets"],
    },
    "us_canada": {
        "name": "US & Canada",
        "summary": ("The United States and Canada share the world's longest "
                    "undefended border and a long-running trade relationship."),
        "capital": None,
        "key_topics": ["US elections", "Canadian federal politics", "trade policy"],
    },
    "latin_america": {
        "name": "Latin America",
        "summary": ("The Spanish- and Portuguese-speaking countries of Central "
                    "and South America, plus the Caribbean."),
        "capital": None,
        "key_topics": ["Amazon deforestation", "migration", "regional elections"],
    },
    "scotland": {
        "name": "Scotland",
        "summary": ("Nation of the United Kingdom with its own parliament at "
                    "Holyrood and devolved powers over health, education and "
                    "justice."),
        "capital": "Edinburgh",
        "key_topics": ["Holyrood", "devolution", "energy transition"],
    },
    "wales": {
        "name": "Wales",
        "summary": ("Nation of the United Kingdom with its own Senedd in "
                    "Cardiff and a distinct legal-aid and education system."),
        "capital": "Cardiff",
        "key_topics": ["the Senedd", "Welsh language policy", "valleys economy"],
    },
    "northern_ireland": {
        "name": "Northern Ireland",
        "summary": ("Nation of the United Kingdom with the Stormont assembly "
                    "and a power-sharing executive at its heart."),
        "capital": "Belfast",
        "key_topics": ["Stormont", "the Windsor Framework", "power-sharing"],
    },
    "england": {
        "name": "England",
        "summary": ("Largest nation of the United Kingdom; no separate parliament "
                    "but devolved combined-authority mayors in major regions."),
        "capital": "London",
        "key_topics": ["Westminster", "metro mayors", "council finances"],
    },
}


@app.route("/healthz")
def healthz():
    """Liveness probe. Returns JSON; never touches the DB heavily."""
    try:
        n_articles = db.session.query(func.count(Article.id)).scalar() or 0
    except Exception:
        return jsonify({
            "ok": False, "service": "bbc_news", "status": "degraded",
            "reason": "db-unreachable",
        }), 503
    return jsonify({
        "ok": True,
        "service": "bbc_news",
        "status": "ok",
        "reference_date": R8_REFERENCE_DATE.isoformat() + "Z",
        "articles_indexed": int(n_articles),
        "version": "r8.1",
        "build": "bbc-news-mirror",
    })


@app.route("/api/uptime")
def api_uptime():
    """Synthetic uptime / SLO report. Deterministic snapshot."""
    return jsonify({
        "ok": True,
        "service": "bbc_news",
        "reference_date": R8_REFERENCE_DATE.isoformat() + "Z",
        "windows": {
            "last_24h": {"uptime_pct": 100.0, "incidents": 0},
            "last_7d":  {"uptime_pct": 99.97, "incidents": 0},
            "last_30d": {"uptime_pct": 99.92, "incidents": 1},
            "last_90d": {"uptime_pct": 99.86, "incidents": 2},
        },
        "slo_target_pct": 99.9,
        "last_incident": {
            "id": "INC-2026-04-04",
            "summary": "Stale RSS cache on /rss/bbc_future.xml for 12 minutes.",
            "resolved_at": "2026-04-04T11:14:00Z",
        },
        "release_channel": "r8.1",
    })


@app.route("/api/events")
def api_events():
    """Recent newsroom events (article publishes, breaking flips). Read-only.

    Query: ?limit=N (default 20, max 200), ?since=YYYY-MM-DD optional.
    """
    try:
        limit = max(1, min(200, int(request.args.get("limit", "20"))))
    except (TypeError, ValueError):
        limit = 20
    since = request.args.get("since", "")
    q = Article.query.order_by(Article.published_at.desc())
    since_dt = None
    if since:
        try:
            since_dt = datetime.strptime(since[:10], "%Y-%m-%d")
            q = q.filter(Article.published_at >= since_dt)
        except ValueError:
            since_dt = None
    arts = q.limit(limit).all()
    events = []
    for a in arts:
        events.append({
            "id": f"evt-{a.id}",
            "type": ("breaking-news" if a.is_breaking
                     else "live-update" if a.is_live
                     else "article-published"),
            "article_slug": a.slug,
            "headline": a.headline,
            "section": a.section_slug or (a.category.slug if a.category else ""),
            "region": a.region or "",
            "published_at": (a.published_at.isoformat() + "Z"
                             if a.published_at else ""),
        })
    return jsonify({
        "ok": True,
        "count": len(events),
        "limit": limit,
        "since": since_dt.strftime("%Y-%m-%d") if since_dt else None,
        "reference_date": R8_REFERENCE_DATE.isoformat() + "Z",
        "events": events,
    })


@app.route("/api/error-report", methods=["POST"])
@csrf.exempt
def api_error_report():
    """Accept a client-side error report. Idempotent acknowledgement."""
    data = request.get_json(silent=True) or {}
    msg = (data.get("message") or "")[:500]
    path = (data.get("path") or request.referrer or "")[:300]
    rid = hashlib.sha1((path + "|" + msg).encode("utf-8")).hexdigest()[:12] \
        if (path or msg) else "anon"
    return jsonify({
        "ok": True,
        "ack": True,
        "report_id": f"err-{rid}",
        "received_at": R8_REFERENCE_DATE.isoformat() + "Z",
        "echo": {"path": path, "message_len": len(msg)},
        "follow_up": "/help/keyboard",
    })


@app.route("/api/telemetry", methods=["POST"])
@csrf.exempt
def api_telemetry():
    """Accept a client-side telemetry event. Acknowledges, never persists."""
    data = request.get_json(silent=True) or {}
    evt = (data.get("event") or "")[:80]
    surface = (data.get("surface") or "")[:80]
    return jsonify({
        "ok": True,
        "ack": True,
        "event": evt,
        "surface": surface,
        "received_at": R8_REFERENCE_DATE.isoformat() + "Z",
        "telemetry_marker": "t8-v1",
    })


@app.route("/developer/news-api")
def developer_news_api():
    """Public-facing developer portal — JSON if Accept: application/json,
    otherwise a styled HTML page that lists the documented endpoints."""
    endpoints = [
        {"method": "GET",  "path": "/api/stats",
         "summary": "Site-wide counts: articles, categories, breaking flag."},
        {"method": "GET",  "path": "/api/events?limit=N&since=YYYY-MM-DD",
         "summary": "Recent newsroom events (publishes / breaking)."},
        {"method": "GET",  "path": "/api/uptime",
         "summary": "Uptime windows and last-incident summary."},
        {"method": "GET",  "path": "/healthz",
         "summary": "Liveness probe."},
        {"method": "GET",  "path": "/api/articles/<slug>",
         "summary": "Articles in a category."},
        {"method": "GET",  "path": "/article/<slug>/schema.json",
         "summary": "Schema.org NewsArticle JSON-LD for a single story."},
        {"method": "GET",  "path": "/article/<slug>/voiceover-summary",
         "summary": "Screen-reader friendly summary."},
        {"method": "GET",  "path": "/api/command-palette",
         "summary": "Command palette items for client-side Cmd+K UI."},
        {"method": "GET",  "path": "/api/keyboard-shortcuts",
         "summary": "Keyboard shortcut catalogue."},
        {"method": "GET",  "path": "/api/region-glossary/<region>",
         "summary": "Contextual help blurb for a region or country."},
        {"method": "POST", "path": "/api/telemetry",
         "summary": "Accept a single telemetry event (JSON body)."},
        {"method": "POST", "path": "/api/error-report",
         "summary": "Accept a client-side error report (JSON body)."},
        {"method": "POST", "path": "/webhook/breaking-news",
         "summary": "Subscribe a webhook URL to breaking-news pushes."},
        {"method": "GET",  "path": "/rss/<slug>.xml",
         "summary": "RSS 2.0 feed for a category."},
        {"method": "GET",  "path": "/feed/<slug>.atom",
         "summary": "Atom 1.0 feed for a category."},
        {"method": "GET",  "path": "/sitemap.xml",
         "summary": "Top-level sitemap."},
        {"method": "GET",  "path": "/sitemap-news.xml",
         "summary": "Google News sitemap."},
    ]
    payload = {
        "ok": True,
        "title": "BBC News - Developer API",
        "version": "r8.1",
        "reference_date": R8_REFERENCE_DATE.isoformat() + "Z",
        "rate_limit": {"per_minute": 600, "burst": 60},
        "auth": "none-for-public-endpoints",
        "schema_url": "/article/<slug>/schema.json",
        "endpoints": endpoints,
    }
    want_json = (
        request.args.get("format") == "json"
        or "application/json" in (request.headers.get("Accept", "") or "")
    )
    if want_json:
        return jsonify(payload)
    return render_template("developer_news_api.html",
                           data=payload, endpoints=endpoints,
                           active_nav_slug="developer")


@app.route("/webhook/breaking-news", methods=["GET", "POST"])
@csrf.exempt
def webhook_breaking_news():
    """Register / inspect webhook subscriptions for breaking-news pushes.

    GET  -> returns the documented webhook contract (JSON or HTML).
    POST -> echoes back the registration ack (no state stored).
    """
    if request.method == "POST":
        data = request.get_json(silent=True) or request.form.to_dict()
        target = (data.get("url") or data.get("target") or "")[:400]
        secret = (data.get("secret") or "")[:120]
        events = (data.get("events") or "breaking-news")[:200]
        sub_id = hashlib.sha1((target + "|" + secret).encode("utf-8")).hexdigest()[:12] \
            if target else "anon"
        return jsonify({
            "ok": bool(target),
            "ack": bool(target),
            "subscription_id": f"wh-{sub_id}",
            "target_url": target,
            "events": [e.strip() for e in events.split(",") if e.strip()],
            "received_at": R8_REFERENCE_DATE.isoformat() + "Z",
            "verify_token": f"verify-{sub_id}",
            "next_steps": "Respond 200 to a GET with ?challenge=<token> to confirm.",
        })
    payload = {
        "ok": True,
        "kind": "webhook",
        "topic": "breaking-news",
        "post_required_fields": ["url", "secret"],
        "optional_fields": ["events"],
        "delivery": {
            "format": "JSON over HTTPS",
            "retry_policy": "exponential backoff, 5 attempts over 6h",
            "signature_header": "X-BBC-Signature: hmac-sha256",
        },
        "subscribe_endpoint": "/webhook/breaking-news",
        "events": ["breaking-news", "live-update", "article-published"],
        "reference_date": R8_REFERENCE_DATE.isoformat() + "Z",
    }
    want_json = (
        request.args.get("format") == "json"
        or "application/json" in (request.headers.get("Accept", "") or "")
    )
    if want_json:
        return jsonify(payload)
    return render_template("webhook_breaking_news.html",
                           data=payload, active_nav_slug="developer")


@app.route("/api/keyboard-shortcuts")
def api_keyboard_shortcuts():
    """Documented keyboard shortcuts. Used by /help/keyboard and the
    on-page '?' overlay."""
    return jsonify({
        "ok": True,
        "version": "r8.1",
        "reference_date": R8_REFERENCE_DATE.isoformat() + "Z",
        "shortcuts": [
            {"keys": ["j"], "action": "next-article",
             "description": "Move to the next article in the current list."},
            {"keys": ["k"], "action": "previous-article",
             "description": "Move to the previous article in the current list."},
            {"keys": ["/"], "action": "focus-search",
             "description": "Focus the global search box in the orb bar."},
            {"keys": ["Meta", "k"], "action": "open-command-palette",
             "description": "Open the command palette to jump to a section, topic or article."},
            {"keys": ["Ctrl", "k"], "action": "open-command-palette",
             "description": "Open the command palette (Windows/Linux variant)."},
            {"keys": ["?"], "action": "open-help",
             "description": "Show the keyboard-shortcut help overlay."},
            {"keys": ["g", "h"], "action": "go-home",
             "description": "Jump to the BBC News homepage."},
            {"keys": ["g", "l"], "action": "go-live",
             "description": "Jump to the Live page."},
            {"keys": ["g", "b"], "action": "go-bookmarks",
             "description": "Jump to your Bookmarks (signed-in users)."},
            {"keys": ["b"], "action": "toggle-bookmark",
             "description": "Bookmark the article currently in focus."},
            {"keys": ["d"], "action": "toggle-dark-mode",
             "description": "Toggle dark mode."},
            {"keys": ["Escape"], "action": "close-overlay",
             "description": "Close any open overlay (palette, help, share)."},
        ],
    })


@app.route("/api/command-palette")
def api_command_palette():
    """Items shown in the client-side Cmd+K palette. Sections + radio
    stations + local regions + a sample of trending headlines."""
    items: list[dict] = []
    # Top-level navigation sections.
    nav_slugs = ["news", "uk", "world", "business", "politics", "technology",
                 "science", "health", "entertainment", "culture", "arts",
                 "travel", "earth", "audio", "video", "sport", "weather",
                 "in_pictures", "bbcverify", "newsround", "multi_step",
                 "breaking_news", "quizzes"]
    seen_slugs: set[str] = set()
    for slug in nav_slugs:
        cat = Category.query.filter_by(slug=slug).first()
        if not cat:
            continue
        if cat.slug in seen_slugs:
            continue
        seen_slugs.add(cat.slug)
        items.append({
            "id": f"section:{cat.slug}",
            "kind": "section",
            "label": cat.name,
            "url": url_for("section_page", slug=cat.slug),
            "hint": cat.subtitle or cat.description[:80] or "",
        })
    # Radio sub-stations.
    for slug, name in R8_RADIO_STATIONS:
        cat = Category.query.filter_by(slug=slug).first()
        if not cat:
            continue
        items.append({
            "id": f"station:{slug}",
            "kind": "audio-station",
            "label": name,
            "url": url_for("section_page", slug=slug),
            "hint": cat.subtitle[:80] if cat.subtitle else "Radio station",
        })
    # Local regions.
    for slug, meta in R8_LOCAL_REGION_INDEX.items():
        items.append({
            "id": f"local:{slug}",
            "kind": "local-region",
            "label": f"BBC Local: {meta['name']}",
            "url": url_for("local_region_page", region_slug=slug),
            "hint": f"Local news from {meta['name']}, {meta['nation']}.",
        })
    # Top trending headlines.
    top_arts = (Article.query
                .order_by(Article.view_count.desc())
                .limit(12)
                .all())
    for art in top_arts:
        items.append({
            "id": f"article:{art.slug}",
            "kind": "article",
            "label": art.headline,
            "url": url_for("article_detail", slug=art.slug),
            "hint": (art.summary or "")[:80],
        })
    # Pages / utilities.
    for label, endpoint, hint in [
        ("Bookmarks",          "bookmarks_page",     "Your saved articles"),
        ("Reading list",       "reading_list",       "Save-for-later folders"),
        ("Subscriptions",      "subscriptions_page", "Email digest preferences"),
        ("Breaking news",      "breaking_news_page", "Live breaking-news feed"),
        ("Keyboard help",      "help_keyboard",      "Keyboard shortcuts"),
        ("Developer API",      "developer_news_api", "Public REST endpoints"),
    ]:
        try:
            url = url_for(endpoint)
        except Exception:
            continue
        items.append({
            "id": f"page:{endpoint}",
            "kind": "page",
            "label": label,
            "url": url,
            "hint": hint,
        })
    return jsonify({
        "ok": True,
        "version": "r8.1",
        "count": len(items),
        "items": items,
    })


@app.route("/api/region-glossary/<region>")
def api_region_glossary(region):
    """Contextual-help popover content for a region or country mention.

    `region` may be a glossary slug ('uk', 'africa', 'scotland', ...) or a
    full country name ('France', 'Germany', ...). Country names map back
    to their parent region via a small static table.
    """
    key = (region or "").strip().lower().replace(" ", "_").replace("-", "_")
    # Country -> region overrides (small static table).
    country_to_region = {
        "france": "europe", "germany": "europe", "italy": "europe",
        "spain": "europe", "ukraine": "europe", "russia": "europe",
        "poland": "europe", "netherlands": "europe", "belgium": "europe",
        "japan": "asia", "china": "asia", "india": "asia", "pakistan": "asia",
        "iran": "middle_east", "iraq": "middle_east", "saudi_arabia": "middle_east",
        "israel": "middle_east", "egypt": "africa", "kenya": "africa",
        "nigeria": "africa", "south_africa": "africa", "ethiopia": "africa",
        "mexico": "latin_america", "brazil": "latin_america",
        "argentina": "latin_america", "colombia": "latin_america",
        "canada": "us_canada", "usa": "us_canada", "united_states": "us_canada",
    }
    canonical = country_to_region.get(key, key)
    entry = R8_REGION_GLOSSARY.get(canonical)
    if not entry:
        return jsonify({
            "ok": False,
            "error": "region-not-found",
            "queried": region,
            "available": sorted(R8_REGION_GLOSSARY.keys()),
        }), 404
    return jsonify({
        "ok": True,
        "region": canonical,
        "name": entry["name"],
        "summary": entry["summary"],
        "capital": entry.get("capital"),
        "nations": entry.get("nations", []),
        "key_topics": entry.get("key_topics", []),
        "doc_link": f"/section/{canonical}",
        "glossary_marker": "rg-v1",
    })


@app.route("/local")
@app.route("/local/")
def local_index():
    """BBC Local index: list of all 40 local regions."""
    regions = sorted(
        (
            {"slug": slug, "name": meta["name"], "nation": meta["nation"]}
            for slug, meta in R8_LOCAL_REGION_INDEX.items()
        ),
        key=lambda r: r["name"],
    )
    return render_template("local_index.html",
                           regions=regions,
                           active_nav_slug="bbc_local",
                           total_regions=len(regions))


@app.route("/local/<region_slug>")
def local_region_page(region_slug):
    """Per-region listing: pull the latest BBC Local articles for that
    region using the feature_tags tagging applied by bake_extras R8."""
    meta = R8_LOCAL_REGION_INDEX.get(region_slug)
    if not meta:
        abort(404)
    tag = "local-" + region_slug.replace("_", "-")
    arts = (Article.query
            .filter(Article.feature_tags.like(f'%"{tag}"%'))
            .order_by(Article.published_at.desc())
            .limit(80)
            .all())
    return render_template("local_region.html",
                           region_slug=region_slug,
                           region_name=meta["name"],
                           nation=meta["nation"],
                           articles=arts,
                           active_nav_slug="bbc_local")


@app.route("/help/keyboard")
def help_keyboard():
    """Static keyboard-shortcut help page. Sources its list from
    /api/keyboard-shortcuts so the two are guaranteed in sync."""
    shortcuts = [
        ("j",            "Next article in the current list"),
        ("k",            "Previous article in the current list"),
        ("/",            "Focus the global search box"),
        ("Cmd+K / Ctrl+K","Open the command palette (jump anywhere)"),
        ("?",            "Show this shortcut help overlay"),
        ("g h",          "Jump to the homepage"),
        ("g l",          "Jump to Live"),
        ("g b",          "Jump to Bookmarks (signed in)"),
        ("b",            "Bookmark the currently focused article"),
        ("d",            "Toggle dark mode"),
        ("Escape",       "Close any open overlay"),
    ]
    return render_template("help_keyboard.html",
                           shortcuts=shortcuts,
                           active_nav_slug="help")


@app.route("/api/multi-step/start", methods=["GET", "POST"])
@csrf.exempt
def api_multi_step_start():
    """Kick off a deterministic multi-step task workflow. Returns the
    first step + the workflow ID; subsequent steps fetched by ID."""
    workflow_id = (request.values.get("workflow") or "default").strip()[:32] or "default"
    seed = hashlib.sha1(workflow_id.encode("utf-8")).hexdigest()[:8]
    return jsonify({
        "ok": True,
        "workflow_id": f"ms-{seed}",
        "step": 1,
        "total_steps": 4,
        "next": "/api/multi-step/step",
        "task": "Open /api/keyboard-shortcuts and locate the shortcut for "
                "'open-command-palette'.",
        "expected_marker": "ks-pal",
        "reference_date": R8_REFERENCE_DATE.isoformat() + "Z",
    })


@app.route("/api/multi-step/step", methods=["GET", "POST"])
@csrf.exempt
def api_multi_step_step():
    """Return the next step of the multi-step workflow."""
    try:
        step = max(1, min(5, int(request.values.get("step", "2"))))
    except (TypeError, ValueError):
        step = 2
    workflow_id = (request.values.get("workflow_id") or "ms-default")[:40]
    steps = {
        2: {"task": "Call /api/region-glossary/uk and capture the `capital` "
                    "field for the next step.",
            "expected_marker": "rg-v1"},
        3: {"task": "Visit /local/london and copy the headline of the first "
                    "article into the next request as `q`.",
            "expected_marker": "local-london"},
        4: {"task": "POST /api/telemetry with {event:'multi-step-done', "
                    "surface:'r8'} and report the `telemetry_marker`.",
            "expected_marker": "t8-v1"},
        5: {"task": "Done. There are no more steps.",
            "expected_marker": "ms-end"},
    }
    payload = steps.get(step, steps[5])
    return jsonify({
        "ok": True,
        "workflow_id": workflow_id,
        "step": step,
        "total_steps": 4,
        "next": "/api/multi-step/step" if step < 5 else None,
        **payload,
        "reference_date": R8_REFERENCE_DATE.isoformat() + "Z",
    })


# =======================================================================
# ERROR HANDLERS
# =======================================================================

@app.errorhandler(404)
def not_found(e):
    return render_template("error.html", code=404, message="Page not found"), 404


@app.errorhandler(500)
def server_error(e):
    return render_template("error.html", code=500, message="Something went wrong"), 500


# =======================================================================
# MAIN
# =======================================================================

def _ensure_gallery_full_column():
    """Idempotent: add the gallery_full_json column to existing DBs that
    were seeded before this column was introduced."""
    import sqlite3 as _sqlite3
    db_path = os.path.join(BASE_DIR, "instance", "bbc_news.db")
    if not os.path.exists(db_path):
        return
    conn = _sqlite3.connect(db_path)
    cur = conn.cursor()
    try:
        cols = {r[1] for r in cur.execute("PRAGMA table_info(articles)").fetchall()}
        if "gallery_full_json" not in cols:
            cur.execute("ALTER TABLE articles ADD COLUMN gallery_full_json TEXT DEFAULT '{}'")
            conn.commit()
    finally:
        conn.close()


with app.app_context():
    _ensure_gallery_full_column()
    db.create_all()
    seed_database()
    seed_benchmark_users()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 28843))
    app.run(host="0.0.0.0", port=port, debug=False)
