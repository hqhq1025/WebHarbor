"""TED mirror for WebHarbor (deepened to vanilla-level)."""
import hashlib
import json
import os
import re
import shutil
from datetime import datetime, timedelta
from pathlib import Path

from flask import (Flask, abort, flash, jsonify, redirect, render_template,
                   request, session, url_for)
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text
from werkzeug.security import check_password_hash


def _deterministic_password_hash(password, salt_seed):
    """Byte-deterministic pbkdf2 hash so seed DB is reset-stable.

    werkzeug.generate_password_hash uses a random salt, which breaks the
    byte-identical reset invariant required by WebHarbor.
    """
    fixed_salt = hashlib.sha1(("salt-" + (salt_seed or "")).encode()).hexdigest()[:8]
    derived = hashlib.pbkdf2_hmac(
        "sha256", password.encode(), fixed_salt.encode(), 1000, dklen=32
    ).hex()
    return f"pbkdf2:sha256:1000${fixed_salt}${derived}"


from seed_data import EVENTS, PLAYLISTS, TALKS
from seed_extended import (BLOG_POSTS, CONFERENCES, MEMBERSHIP_TIERS,
                            NEWSLETTERS, PODCASTS, SERIES, SPEAKERS, TED_ED,
                            TEDX_EVENTS, TOPIC_PAGES,
                            build_seed_comments_for_talk)

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "instance" / "ted.db"
SEED_DB_PATH = BASE_DIR / "instance_seed" / "ted.db"

# Fixed reference time for any seed timestamp.
MIRROR_REFERENCE_DATE = datetime(2026, 4, 15, 12, 0, 0)

app = Flask(__name__)
app.config["SECRET_KEY"] = "webharbor-ted-dev-key"
app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{DB_PATH}"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
BASE_DIR.joinpath("instance").mkdir(exist_ok=True)

db = SQLAlchemy(app)


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(160), unique=True, nullable=False)
    display_name = db.Column(db.String(120), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(120), default="Curious learner")
    city = db.Column(db.String(120), default="")
    newsletter_topic = db.Column(db.String(80), default="technology")
    member_tier = db.Column(db.String(40), default="explorer")
    bio = db.Column(db.Text, default="")
    avatar = db.Column(db.String(260), default="")


class Talk(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    source_id = db.Column(db.String(40), unique=True, nullable=False)
    slug = db.Column(db.String(220), unique=True, nullable=False, index=True)
    title = db.Column(db.String(260), nullable=False)
    speaker = db.Column(db.String(180), nullable=False)
    speaker_slug = db.Column(db.String(180), default="", index=True)
    event = db.Column(db.String(120), default="")
    talk_type = db.Column(db.String(80), default="TED Talk")
    duration_seconds = db.Column(db.Integer, default=0)
    published_at = db.Column(db.String(20), default="")
    recorded_on = db.Column(db.String(20), default="")
    views = db.Column(db.Integer, default=0)
    image = db.Column(db.String(260), default="")
    canonical_url = db.Column(db.String(300), default="")
    description = db.Column(db.Text, default="")
    transcript = db.Column(db.Text, default="")
    topics_json = db.Column(db.Text, default="[]")
    recommended_json = db.Column(db.Text, default="[]")

    @property
    def topics(self):
        return json.loads(self.topics_json or "[]")

    @property
    def recommended_for(self):
        return json.loads(self.recommended_json or "[]")

    @property
    def minutes(self):
        return max(1, round((self.duration_seconds or 0) / 60))

    @property
    def views_label(self):
        if self.views >= 1_000_000:
            return f"{self.views / 1_000_000:.1f}M"
        if self.views >= 1000:
            return f"{self.views // 1000}K"
        return str(self.views)


class Speaker(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(180), unique=True, nullable=False, index=True)
    name = db.Column(db.String(180), nullable=False)
    role = db.Column(db.String(120), default="")
    affiliation = db.Column(db.String(180), default="")
    bio = db.Column(db.Text, default="")
    why_listen = db.Column(db.Text, default="")
    photo = db.Column(db.String(260), default="")
    talks_count = db.Column(db.Integer, default=0)
    total_views = db.Column(db.Integer, default=0)
    languages = db.Column(db.String(180), default="English")


class Topic(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(120), unique=True, nullable=False)
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, default="")
    banner = db.Column(db.String(260), default="")
    popular_talk_slug = db.Column(db.String(220), default="")
    talk_count = db.Column(db.Integer, default=0)


class Series(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(120), unique=True, nullable=False)
    name = db.Column(db.String(180), nullable=False)
    tagline = db.Column(db.String(240), default="")
    description = db.Column(db.Text, default="")
    host = db.Column(db.String(180), default="")
    banner = db.Column(db.String(260), default="")
    episode_slugs_json = db.Column(db.Text, default="[]")
    episode_count = db.Column(db.Integer, default=0)


class Podcast(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(120), unique=True, nullable=False)
    name = db.Column(db.String(180), nullable=False)
    host = db.Column(db.String(180), default="")
    publisher = db.Column(db.String(180), default="")
    tagline = db.Column(db.String(240), default="")
    frequency = db.Column(db.String(60), default="")
    rss = db.Column(db.String(260), default="")
    banner = db.Column(db.String(260), default="")
    episode_count = db.Column(db.Integer, default=0)


class PodcastEpisode(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    podcast_id = db.Column(db.Integer, db.ForeignKey("podcast.id"), nullable=False)
    slug = db.Column(db.String(220), nullable=False)
    title = db.Column(db.String(260), nullable=False)
    speaker = db.Column(db.String(180), default="")
    duration_seconds = db.Column(db.Integer, default=0)
    published_at = db.Column(db.String(20), default="")
    image = db.Column(db.String(260), default="")
    description = db.Column(db.Text, default="")
    position = db.Column(db.Integer, default=0)


class TedEdLesson(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(220), unique=True, nullable=False)
    title = db.Column(db.String(260), nullable=False)
    educator = db.Column(db.String(180), default="")
    subject = db.Column(db.String(80), default="")
    grade_band = db.Column(db.String(60), default="")
    duration_seconds = db.Column(db.Integer, default=0)
    image = db.Column(db.String(260), default="")
    summary = db.Column(db.Text, default="")
    dig_deeper_json = db.Column(db.Text, default="[]")
    talk_slug = db.Column(db.String(220), default="")


class Conference(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(120), unique=True, nullable=False)
    name = db.Column(db.String(180), nullable=False)
    city = db.Column(db.String(160), default="")
    country = db.Column(db.String(80), default="")
    starts_on = db.Column(db.String(20), default="")
    ends_on = db.Column(db.String(20), default="")
    theme = db.Column(db.String(180), default="")
    track = db.Column(db.String(80), default="")
    capacity = db.Column(db.Integer, default=0)
    status = db.Column(db.String(80), default="")
    summary = db.Column(db.Text, default="")
    banner = db.Column(db.String(260), default="")
    session_slugs_json = db.Column(db.Text, default="[]")
    application_roles_json = db.Column(db.Text, default="[]")


class TedxEvent(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(120), unique=True, nullable=False)
    name = db.Column(db.String(180), nullable=False)
    city = db.Column(db.String(160), default="")
    country = db.Column(db.String(80), default="")
    date = db.Column(db.String(20), default="")
    theme = db.Column(db.String(180), default="")
    organizer = db.Column(db.String(180), default="")
    capacity = db.Column(db.Integer, default=0)
    banner = db.Column(db.String(260), default="")
    feature_talk_slug = db.Column(db.String(220), default="")
    status = db.Column(db.String(80), default="")


class MembershipTier(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(60), unique=True, nullable=False)
    name = db.Column(db.String(80), nullable=False)
    monthly_price = db.Column(db.Integer, default=0)
    annual_price = db.Column(db.Integer, default=0)
    tagline = db.Column(db.String(240), default="")
    perks_json = db.Column(db.Text, default="[]")
    color = db.Column(db.String(20), default="#111")


class Newsletter(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(60), unique=True, nullable=False)
    name = db.Column(db.String(120), nullable=False)
    frequency = db.Column(db.String(40), default="")
    description = db.Column(db.Text, default="")


class BlogPost(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(220), unique=True, nullable=False, index=True)
    title = db.Column(db.String(260), nullable=False)
    author = db.Column(db.String(180), default="")
    bucket = db.Column(db.String(60), default="")
    bucket_slug = db.Column(db.String(60), default="")
    topic = db.Column(db.String(80), default="")
    published_at = db.Column(db.String(20), default="")
    hero = db.Column(db.String(260), default="")
    summary = db.Column(db.Text, default="")
    body = db.Column(db.Text, default="")
    talk_slug = db.Column(db.String(220), default="")
    tags_json = db.Column(db.Text, default="[]")


class SavedTalk(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    talk_id = db.Column(db.Integer, db.ForeignKey("talk.id"), nullable=False)
    saved_at = db.Column(db.DateTime, default=lambda: MIRROR_REFERENCE_DATE)
    note = db.Column(db.String(240), default="")
    talk = db.relationship("Talk")


class TalkNote(db.Model):
    """A standalone user note attached to a talk (separate from saved-talk note)."""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    talk_id = db.Column(db.Integer, db.ForeignKey("talk.id"), nullable=False)
    body = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: MIRROR_REFERENCE_DATE)
    talk = db.relationship("Talk")


class TalkRating(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    talk_id = db.Column(db.Integer, db.ForeignKey("talk.id"), nullable=False)
    value = db.Column(db.Integer, default=0)


class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    talk_id = db.Column(db.Integer, db.ForeignKey("talk.id"), nullable=False)
    body = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: MIRROR_REFERENCE_DATE)
    score = db.Column(db.Integer, default=0)
    parent_id = db.Column(db.Integer, db.ForeignKey("comment.id"), nullable=True)
    author_label = db.Column(db.String(120), default="")
    talk = db.relationship("Talk")


class CommentVote(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    comment_id = db.Column(db.Integer, db.ForeignKey("comment.id"), nullable=False)
    value = db.Column(db.Integer, default=0)


class BlogComment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    post_id = db.Column(db.Integer, db.ForeignKey("blog_post.id"), nullable=False)
    body = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: MIRROR_REFERENCE_DATE)
    author_label = db.Column(db.String(120), default="")


class Playlist(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(120), unique=True, nullable=False)
    title = db.Column(db.String(180), nullable=False)
    description = db.Column(db.Text, default="")
    topic = db.Column(db.String(80), default="")


class PlaylistTalk(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    playlist_id = db.Column(db.Integer, db.ForeignKey("playlist.id"), nullable=False)
    talk_id = db.Column(db.Integer, db.ForeignKey("talk.id"), nullable=False)
    position = db.Column(db.Integer, default=0)
    talk = db.relationship("Talk")


class UserPlaylist(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    slug = db.Column(db.String(120), nullable=False)
    title = db.Column(db.String(180), nullable=False)
    description = db.Column(db.Text, default="")
    is_public = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=lambda: MIRROR_REFERENCE_DATE)


class UserPlaylistTalk(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_playlist_id = db.Column(db.Integer, db.ForeignKey("user_playlist.id"), nullable=False)
    talk_id = db.Column(db.Integer, db.ForeignKey("talk.id"), nullable=False)
    position = db.Column(db.Integer, default=0)
    talk = db.relationship("Talk")


class Event(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(120), unique=True, nullable=False)
    name = db.Column(db.String(180), nullable=False)
    city = db.Column(db.String(120), default="")
    month = db.Column(db.String(40), default="")
    track = db.Column(db.String(80), default="")
    capacity = db.Column(db.Integer, default=0)


class Registration(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    event_id = db.Column(db.Integer, db.ForeignKey("event.id"), nullable=False)
    status = db.Column(db.String(40), default="waitlisted")
    event = db.relationship("Event")


class ConferenceApplication(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    conference_id = db.Column(db.Integer, db.ForeignKey("conference.id"), nullable=False)
    role = db.Column(db.String(60), default="Attendee")
    status = db.Column(db.String(40), default="submitted")
    motivation = db.Column(db.Text, default="")
    submitted_at = db.Column(db.DateTime, default=lambda: MIRROR_REFERENCE_DATE)


class TedxApplication(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    tedx_event_id = db.Column(db.Integer, db.ForeignKey("tedx_event.id"), nullable=False)
    role = db.Column(db.String(60), default="Attendee")
    status = db.Column(db.String(40), default="submitted")
    submitted_at = db.Column(db.DateTime, default=lambda: MIRROR_REFERENCE_DATE)


class MembershipSubscription(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    tier_slug = db.Column(db.String(40), nullable=False)
    billing = db.Column(db.String(20), default="monthly")
    status = db.Column(db.String(40), default="active")
    started_at = db.Column(db.DateTime, default=lambda: MIRROR_REFERENCE_DATE)


class NewsletterSubscription(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    email = db.Column(db.String(160), nullable=False)
    newsletter_slug = db.Column(db.String(60), nullable=False)
    confirmed = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=lambda: MIRROR_REFERENCE_DATE)


class Translation(db.Model):
    """Open Translation Project submission."""
    id = db.Column(db.Integer, primary_key=True)
    talk_id = db.Column(db.Integer, db.ForeignKey("talk.id"), nullable=False)
    language = db.Column(db.String(40), nullable=False)
    translator_user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    status = db.Column(db.String(40), default="draft")  # draft / submitted / reviewed / published
    body = db.Column(db.Text, default="")
    submitted_at = db.Column(db.DateTime, default=lambda: MIRROR_REFERENCE_DATE)
    talk = db.relationship("Talk")


class ShareLog(db.Model):
    """A record of an outbound share action (no actual external call)."""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    talk_id = db.Column(db.Integer, db.ForeignKey("talk.id"), nullable=True)
    blog_post_id = db.Column(db.Integer, db.ForeignKey("blog_post.id"), nullable=True)
    channel = db.Column(db.String(40), nullable=False)
    message = db.Column(db.String(280), default="")
    created_at = db.Column(db.DateTime, default=lambda: MIRROR_REFERENCE_DATE)


class Report(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    target_type = db.Column(db.String(20), nullable=False)  # comment / talk / blog / user
    target_id = db.Column(db.Integer, nullable=False)
    reason = db.Column(db.String(80), default="")
    detail = db.Column(db.Text, default="")
    created_at = db.Column(db.DateTime, default=lambda: MIRROR_REFERENCE_DATE)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

STOP_WORDS = {"the", "a", "an", "and", "or", "of", "to", "for", "in", "on",
              "with", "by", "my", "is", "from", "at", "be"}


def current_user():
    uid = session.get("user_id")
    return db.session.get(User, uid) if uid else None


def require_login():
    if not current_user():
        flash("Please sign in to continue.", "info")
        return redirect(url_for("login", next=request.path))
    return None


def _slugify(text):
    s = re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")
    return s or "untitled"


@app.context_processor
def inject_globals():
    nav_topics = [t.name for t in Topic.query.order_by(Topic.talk_count.desc()).limit(10).all()]
    if not nav_topics:
        nav_topics = sorted({tp for talk in Talk.query.limit(40).all() for tp in talk.topics})[:10]
    return {
        "current_user": current_user(),
        "nav_topics": nav_topics,
        "footer_topics": [t.name for t in Topic.query.order_by(Topic.talk_count.desc()).limit(18).all()],
        "footer_series": Series.query.order_by(Series.slug).limit(6).all(),
        "footer_podcasts": Podcast.query.order_by(Podcast.slug).limit(6).all(),
    }


@app.template_filter("date_label")
def date_label(value):
    try:
        return datetime.strptime(value, "%Y-%m-%d").strftime("%b %d, %Y")
    except Exception:
        return value


@app.template_filter("duration_label")
def duration_label(seconds):
    seconds = int(seconds or 0)
    mins = seconds // 60
    secs = seconds % 60
    return f"{mins}:{secs:02d}"


@app.template_filter("from_json")
def from_json_filter(value):
    try:
        return json.loads(value or "[]")
    except Exception:
        return []


def tokenize(text):
    return [t for t in re.split(r"[^a-z0-9]+", (text or "").lower())
            if len(t) > 1 and t not in STOP_WORDS]


def scored_talks(query, talks):
    tokens = tokenize(query)
    if not tokens:
        return list(talks)
    ranked = []
    for talk in talks:
        text = " ".join([talk.title or "", talk.speaker or "", talk.event or "",
                         talk.description or "", talk.transcript or "",
                         " ".join(talk.topics or [])]).lower()
        score = sum(1 for token in tokens if token in text)
        if score:
            ranked.append((score, talk.views or 0, talk))
    return [talk for _, _, talk in sorted(ranked, key=lambda item: (-item[0], -item[1]))]


# ---------------------------------------------------------------------------
# Seed
# ---------------------------------------------------------------------------

def seed_database():
    if Talk.query.count() > 0:
        return

    talks_by_topic = {}
    talk_by_slug = {}
    for row in TALKS:
        speaker_slug = _slugify(row["speaker"].split(",")[0].strip())
        talk = Talk(
            source_id=row["source_id"],
            slug=row["slug"],
            title=row["title"],
            speaker=row["speaker"],
            speaker_slug=speaker_slug,
            event=row["event"],
            talk_type=row["talk_type"],
            duration_seconds=row["duration_seconds"],
            published_at=row["published_at"],
            recorded_on=row["recorded_on"],
            views=row["views"],
            image=row["image"],
            canonical_url=row["canonical_url"],
            description=row["description"],
            transcript=row["transcript"],
            topics_json=json.dumps(row["topics"]),
            recommended_json=json.dumps(row["recommended_for"]),
        )
        db.session.add(talk)
        db.session.flush()
        talk_by_slug[row["slug"]] = talk
        for topic in row["topics"]:
            talks_by_topic.setdefault(topic.lower(), []).append(talk.id)

    # PLAYLISTS
    for row in PLAYLISTS:
        playlist = Playlist(**row)
        db.session.add(playlist)
        db.session.flush()
        topic_terms = [term.strip().lower() for term in row["topic"].split("|") if term.strip()]
        ids = []
        for term in topic_terms:
            for talk_id in talks_by_topic.get(term, []):
                if talk_id not in ids:
                    ids.append(talk_id)
        ids = ids[:8]
        if len(ids) < 4:
            ids = [talk.id for talk in Talk.query.order_by(Talk.views.desc()).limit(8)]
        for position, talk_id in enumerate(ids, start=1):
            db.session.add(PlaylistTalk(playlist_id=playlist.id, talk_id=talk_id, position=position))

    # EVENTS
    for row in EVENTS:
        db.session.add(Event(**row))

    # SPEAKERS
    for row in SPEAKERS:
        db.session.add(Speaker(**row))

    # TOPIC PAGES
    for row in TOPIC_PAGES:
        db.session.add(Topic(**row))

    # SERIES
    for row in SERIES:
        db.session.add(Series(
            slug=row["slug"], name=row["name"], tagline=row["tagline"],
            description=row["description"], host=row["host"], banner=row["banner"],
            episode_count=row["episode_count"],
            episode_slugs_json=json.dumps(row["episode_slugs"]),
        ))

    # PODCASTS + episodes
    for row in PODCASTS:
        podcast = Podcast(
            slug=row["slug"], name=row["name"], host=row["host"],
            publisher=row["publisher"], tagline=row["tagline"],
            frequency=row["frequency"], rss=row["rss"], banner=row["banner"],
            episode_count=row["episode_count"],
        )
        db.session.add(podcast)
        db.session.flush()
        for i, ep in enumerate(row["episodes"]):
            db.session.add(PodcastEpisode(
                podcast_id=podcast.id, slug=ep["slug"], title=ep["title"],
                speaker=ep["speaker"], duration_seconds=ep["duration_seconds"],
                published_at=ep["published_at"], image=ep["image"],
                description=ep["description"], position=i + 1,
            ))

    # TED-Ed
    for row in TED_ED:
        db.session.add(TedEdLesson(
            slug=row["slug"], title=row["title"], educator=row["educator"],
            subject=row["subject"], grade_band=row["grade_band"],
            duration_seconds=row["duration_seconds"], image=row["image"],
            summary=row["summary"],
            dig_deeper_json=json.dumps(row["dig_deeper"]),
            talk_slug=row["talk_slug"],
        ))

    # CONFERENCES
    for row in CONFERENCES:
        db.session.add(Conference(
            slug=row["slug"], name=row["name"], city=row["city"],
            country=row["country"], starts_on=row["starts_on"],
            ends_on=row["ends_on"], theme=row["theme"], track=row["track"],
            capacity=row["capacity"], status=row["status"], summary=row["summary"],
            banner=row["banner"],
            session_slugs_json=json.dumps(row["session_slugs"]),
            application_roles_json=json.dumps(row["application_roles"]),
        ))

    # TEDX
    for row in TEDX_EVENTS:
        db.session.add(TedxEvent(**row))

    # MEMBERSHIP
    for row in MEMBERSHIP_TIERS:
        db.session.add(MembershipTier(
            slug=row["slug"], name=row["name"],
            monthly_price=row["monthly_price"], annual_price=row["annual_price"],
            tagline=row["tagline"], perks_json=json.dumps(row["perks"]),
            color=row["color"],
        ))

    # NEWSLETTERS
    for row in NEWSLETTERS:
        db.session.add(Newsletter(**row))

    # BLOG POSTS
    for row in BLOG_POSTS:
        db.session.add(BlogPost(
            slug=row["slug"], title=row["title"], author=row["author"],
            bucket=row["bucket"], bucket_slug=row["bucket_slug"],
            topic=row["topic"], published_at=row["published_at"],
            hero=row["hero"], summary=row["summary"], body=row["body"],
            talk_slug=row["talk_slug"],
            tags_json=json.dumps(row["tags"]),
        ))

    db.session.commit()

    # Seeded comments (after talks are flushed)
    talk_slugs = list(talk_by_slug.keys())
    for slug in talk_slugs:
        talk = talk_by_slug[slug]
        related_slug = talk_slugs[(talk.id) % len(talk_slugs)]
        for i, cmt in enumerate(build_seed_comments_for_talk(slug, related_slug)):
            db.session.add(Comment(
                user_id=None, talk_id=talk.id, body=cmt["body"],
                score=cmt["score"], author_label="TED community",
            ))
    db.session.commit()


def seed_users():
    if User.query.filter_by(email="alice.j@test.com").first():
        return
    users = [
        ("alice_j", "alice.j@test.com", "Alice Johnson", "Product manager", "Seattle", "ai"),
        ("bob_c", "bob.c@test.com", "Bob Chen", "Graduate student", "Boston", "science"),
        ("carol_d", "carol.d@test.com", "Carol Davis", "Workshop facilitator", "Austin", "design"),
        ("david_k", "david.k@test.com", "David Kim", "Climate researcher", "San Francisco", "climate"),
        ("emily_r", "emily.r@test.com", "Emily Ramirez", "High school teacher", "Mexico City", "education"),
        ("frank_n", "frank.n@test.com", "Frank Nakamura", "Civic technologist", "Tokyo", "ai"),
    ]
    talks = Talk.query.order_by(Talk.views.desc()).limit(24).all()
    events = Event.query.all()
    conferences = Conference.query.all()
    tiers = MembershipTier.query.all()
    blog_posts = BlogPost.query.order_by(BlogPost.id).limit(40).all()
    newsletters = Newsletter.query.all()

    for index, (username, email, name, role, city, topic) in enumerate(users):
        avatar = talks[index].image if talks else ""
        user = User(
            username=username,
            email=email,
            display_name=name,
            role=role,
            city=city,
            newsletter_topic=topic.lower(),
            member_tier=["explorer", "supporter", "patron", "founder-circle"][index % 4],
            bio=f"{name} — {role} in {city}.",
            avatar=avatar,
            password_hash=_deterministic_password_hash("TestPass123!", email),
        )
        db.session.add(user)
        db.session.flush()

        # Saved talks
        for offset_days, talk in enumerate(talks[index:index + 4]):
            saved_at = MIRROR_REFERENCE_DATE - timedelta(days=index * 7 + offset_days)
            db.session.add(SavedTalk(
                user_id=user.id, talk_id=talk.id,
                note=f"Review for {topic} discussion",
                saved_at=saved_at,
            ))

        # Notes
        for n_offset, talk in enumerate(talks[index:index + 2]):
            db.session.add(TalkNote(
                user_id=user.id, talk_id=talk.id,
                body=f"Quote from minute {3 + n_offset}: this is where the argument turns.",
                created_at=MIRROR_REFERENCE_DATE - timedelta(days=n_offset),
            ))

        # Ratings
        for r_offset, talk in enumerate(talks[index:index + 3]):
            db.session.add(TalkRating(
                user_id=user.id, talk_id=talk.id,
                value=4 + ((index + r_offset) % 2),
            ))

        # Event registration
        if events:
            db.session.add(Registration(
                user_id=user.id, event_id=events[index % len(events)].id,
                status="confirmed",
            ))

        # Conference application
        if conferences:
            conf = conferences[index % len(conferences)]
            db.session.add(ConferenceApplication(
                user_id=user.id, conference_id=conf.id,
                role="Attendee", status="submitted",
                motivation=f"Eager to attend {conf.name} as a {role.lower()}.",
            ))

        # Membership subscription
        tier_slug = ["explorer", "supporter", "patron", "founder-circle"][index % 4]
        db.session.add(MembershipSubscription(
            user_id=user.id, tier_slug=tier_slug,
            billing="annual" if index % 2 else "monthly",
            status="active",
        ))

        # Newsletter subscription
        nls = newsletters[index % len(newsletters)] if newsletters else None
        if nls:
            db.session.add(NewsletterSubscription(
                user_id=user.id, email=email,
                newsletter_slug=nls.slug, confirmed=True,
            ))

        # User playlist
        up = UserPlaylist(
            user_id=user.id,
            slug=f"{username}-favorites",
            title=f"{name.split()[0]}'s favorites",
            description=f"Personal collection curated by {name}.",
            is_public=index % 2 == 0,
            created_at=MIRROR_REFERENCE_DATE - timedelta(days=index * 3),
        )
        db.session.add(up)
        db.session.flush()
        for pos, talk in enumerate(talks[index:index + 5]):
            db.session.add(UserPlaylistTalk(
                user_playlist_id=up.id, talk_id=talk.id, position=pos + 1,
            ))

        # Translation submission
        if talks:
            db.session.add(Translation(
                talk_id=talks[index].id, language=["Spanish", "French", "Mandarin", "Hindi", "Portuguese", "Japanese"][index % 6],
                translator_user_id=user.id, status="submitted",
                body="(translator working transcript)",
            ))

        # Blog comment
        if blog_posts:
            db.session.add(BlogComment(
                user_id=user.id, post_id=blog_posts[index % len(blog_posts)].id,
                body=f"Sharing this with my {role.lower()} cohort tomorrow morning.",
                author_label=name,
            ))

    db.session.commit()


def normalize_seed_db_layout():
    """Re-emit indexes in alpha order + VACUUM so rebuilds match byte-for-byte."""
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


# ---------------------------------------------------------------------------
# Routes — browse
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    featured = Talk.query.order_by(Talk.published_at.desc()).limit(5).all()
    popular = Talk.query.order_by(Talk.views.desc()).limit(8).all()
    playlists = Playlist.query.order_by(Playlist.title).limit(8).all()
    series_rows = Series.query.order_by(Series.slug).limit(4).all()
    podcasts_rows = Podcast.query.order_by(Podcast.slug).limit(4).all()
    blog_rows = BlogPost.query.order_by(BlogPost.id).limit(4).all()
    next_conf = Conference.query.filter(Conference.status.like("%open%") |
                                         Conference.status.like("%Open%")) \
                                 .order_by(Conference.starts_on).first()
    return render_template("index.html", featured=featured, popular=popular,
                           playlists=playlists, series_rows=series_rows,
                           podcasts_rows=podcasts_rows, blog_rows=blog_rows,
                           next_conf=next_conf)


_TALKS_PAGE_SIZE = 24

@app.route("/talks")
def talks():
    topic = request.args.get("topic", "").lower()
    event = request.args.get("event", "")
    max_minutes = request.args.get("max_minutes", type=int)
    sort = request.args.get("sort", "newest")
    page = max(1, request.args.get("page", 1, type=int))
    query = Talk.query
    if event:
        query = query.filter(Talk.event == event)
    if sort == "popular":
        items = query.order_by(Talk.views.desc()).all()
    elif sort == "oldest":
        items = query.order_by(Talk.published_at).all()
    else:
        items = query.order_by(Talk.published_at.desc()).all()
    if topic:
        items = [talk for talk in items if topic in [t.lower() for t in talk.topics]]
    if max_minutes:
        items = [talk for talk in items if talk.minutes <= max_minutes]
    total = len(items)
    n_pages = max(1, (total + _TALKS_PAGE_SIZE - 1) // _TALKS_PAGE_SIZE)
    page = min(page, n_pages)
    start = (page - 1) * _TALKS_PAGE_SIZE
    items = items[start:start + _TALKS_PAGE_SIZE]
    events = [row[0] for row in db.session.query(Talk.event).distinct().order_by(Talk.event).all()]
    return render_template("talks.html", talks=items, topic=topic, event=event,
                           max_minutes=max_minutes, events=events, sort=sort,
                           page=page, n_pages=n_pages, total=total)


@app.route("/search")
def search():
    q = request.args.get("q", "").strip()
    kind = request.args.get("kind", "talks")
    if kind == "speakers":
        items = []
        if q:
            qq = q.lower()
            for s in Speaker.query.order_by(Speaker.name).all():
                if qq in s.name.lower() or qq in s.role.lower() or qq in s.affiliation.lower():
                    items.append(s)
        return render_template("search.html", q=q, kind=kind,
                                speakers=items, talks=[], podcasts=[], blog=[])
    if kind == "podcasts":
        items = []
        if q:
            qq = q.lower()
            for p in Podcast.query.order_by(Podcast.name).all():
                if qq in p.name.lower() or qq in p.tagline.lower() or qq in p.host.lower():
                    items.append(p)
        return render_template("search.html", q=q, kind=kind,
                                speakers=[], talks=[], podcasts=items, blog=[])
    if kind == "blog":
        items = []
        if q:
            qq = q.lower()
            for b in BlogPost.query.order_by(BlogPost.id).all():
                if qq in b.title.lower() or qq in b.summary.lower() or qq in b.body.lower():
                    items.append(b)
        return render_template("search.html", q=q, kind=kind,
                                speakers=[], talks=[], podcasts=[], blog=items)
    talks = scored_talks(q, Talk.query.all()) if q else []
    return render_template("search.html", q=q, kind="talks", talks=talks,
                            speakers=[], podcasts=[], blog=[])


@app.route("/talks/<slug>")
def talk_detail(slug):
    talk = Talk.query.filter_by(slug=slug).first_or_404()
    related = [item for item in scored_talks(" ".join(talk.topics[:2]),
                                              Talk.query.all())
               if item.id != talk.id][:4]
    user = current_user()
    saved = None
    user_rating = None
    if user:
        saved = SavedTalk.query.filter_by(user_id=user.id, talk_id=talk.id).first()
        user_rating = TalkRating.query.filter_by(user_id=user.id, talk_id=talk.id).first()
    avg_rating_row = db.session.query(db.func.avg(TalkRating.value)).filter(
        TalkRating.talk_id == talk.id).scalar()
    avg_rating = round(avg_rating_row or 0, 2)
    rating_count = TalkRating.query.filter_by(talk_id=talk.id).count()
    save_count = SavedTalk.query.filter_by(talk_id=talk.id).count()
    comment_count = Comment.query.filter_by(talk_id=talk.id).count()
    speaker_row = Speaker.query.filter_by(slug=talk.speaker_slug).first()
    return render_template(
        "talk_detail.html", talk=talk, related=related, saved=saved,
        user_rating=user_rating, avg_rating=avg_rating,
        rating_count=rating_count, save_count=save_count,
        comment_count=comment_count, speaker_row=speaker_row,
    )


@app.route("/talks/<slug>/transcript")
def talk_transcript(slug):
    talk = Talk.query.filter_by(slug=slug).first_or_404()
    # Build a multi-language pseudo-transcript banner from existing Translation rows.
    translations = Translation.query.filter_by(talk_id=talk.id).all()
    return render_template("transcript.html", talk=talk, translations=translations)


@app.route("/talks/<slug>/discussion", methods=["GET", "POST"])
def talk_discussion(slug):
    talk = Talk.query.filter_by(slug=slug).first_or_404()
    if request.method == "POST":
        login_redirect = require_login()
        if login_redirect:
            return login_redirect
        body = (request.form.get("body") or "").strip()
        if not body:
            flash("Please write a comment first.", "error")
        else:
            user = current_user()
            db.session.add(Comment(
                user_id=user.id, talk_id=talk.id, body=body,
                score=0, author_label=user.display_name,
            ))
            db.session.commit()
            flash("Comment posted.", "success")
        return redirect(url_for("talk_discussion", slug=slug))
    comments = Comment.query.filter_by(talk_id=talk.id).order_by(
        Comment.score.desc(), Comment.id).all()
    return render_template("discussion.html", talk=talk, comments=comments)


# ---------------------------------------------------------------------------
# Speakers
# ---------------------------------------------------------------------------

@app.route("/speakers")
def speakers_index():
    letter = request.args.get("letter", "").upper()
    q = request.args.get("q", "").strip().lower()
    query = Speaker.query
    items = query.order_by(Speaker.name).all()
    if letter and letter.isalpha():
        items = [s for s in items if s.name[:1].upper() == letter]
    if q:
        items = [s for s in items if q in s.name.lower() or q in (s.role or "").lower()]
    letters = sorted({s.name[:1].upper() for s in Speaker.query.all() if s.name})
    return render_template("speakers_index.html", speakers=items, letter=letter,
                           q=q, letters=letters)


@app.route("/speakers/<slug>")
def speaker_detail(slug):
    speaker = Speaker.query.filter_by(slug=slug).first_or_404()
    talks = Talk.query.filter_by(speaker_slug=slug).order_by(Talk.views.desc()).all()
    return render_template("speaker_detail.html", speaker=speaker, talks=talks)


# ---------------------------------------------------------------------------
# Topics
# ---------------------------------------------------------------------------

@app.route("/topics")
def topics():
    items = Topic.query.order_by(Topic.talk_count.desc(), Topic.name).all()
    return render_template("topics.html", topics=items)


@app.route("/topics/<topic>")
def topic_detail(topic):
    topic_slug = _slugify(topic)
    row = Topic.query.filter_by(slug=topic_slug).first()
    name = row.name.lower() if row else topic.lower()
    talks = [t for t in Talk.query.order_by(Talk.views.desc()).all()
             if name in [x.lower() for x in t.topics]]
    return render_template("topic_detail.html", topic_row=row,
                           topic=name, talks=talks)


# ---------------------------------------------------------------------------
# Playlists
# ---------------------------------------------------------------------------

@app.route("/playlists")
def playlists():
    items = Playlist.query.order_by(Playlist.title).all()
    return render_template("playlists.html", playlists=items)


@app.route("/playlists/<slug>")
def playlist_detail(slug):
    playlist = Playlist.query.filter_by(slug=slug).first_or_404()
    links = PlaylistTalk.query.filter_by(playlist_id=playlist.id).order_by(
        PlaylistTalk.position).all()
    return render_template("playlist_detail.html", playlist=playlist, links=links)


# ---------------------------------------------------------------------------
# Series
# ---------------------------------------------------------------------------

@app.route("/series")
def series_index():
    items = Series.query.order_by(Series.slug).all()
    return render_template("series_index.html", series_rows=items)


@app.route("/series/<slug>")
def series_detail(slug):
    series = Series.query.filter_by(slug=slug).first_or_404()
    episode_slugs = json.loads(series.episode_slugs_json or "[]")
    episodes = [Talk.query.filter_by(slug=s).first() for s in episode_slugs]
    episodes = [e for e in episodes if e]
    return render_template("series_detail.html", series=series, episodes=episodes)


# ---------------------------------------------------------------------------
# Podcasts
# ---------------------------------------------------------------------------

@app.route("/podcasts")
def podcasts_index():
    items = Podcast.query.order_by(Podcast.slug).all()
    return render_template("podcasts_index.html", podcasts=items)


@app.route("/podcasts/<slug>")
def podcast_detail(slug):
    podcast = Podcast.query.filter_by(slug=slug).first_or_404()
    episodes = PodcastEpisode.query.filter_by(podcast_id=podcast.id).order_by(
        PodcastEpisode.position).all()
    return render_template("podcast_detail.html", podcast=podcast, episodes=episodes)


@app.route("/podcasts/<slug>/<episode_slug>")
def podcast_episode(slug, episode_slug):
    podcast = Podcast.query.filter_by(slug=slug).first_or_404()
    episode = PodcastEpisode.query.filter_by(
        podcast_id=podcast.id, slug=episode_slug).first_or_404()
    # Try to attach the originating talk (if the episode mirrors one).
    related_talk = Talk.query.filter_by(slug=episode_slug).first()
    return render_template("podcast_episode.html", podcast=podcast,
                           episode=episode, related_talk=related_talk)


# ---------------------------------------------------------------------------
# TED-Ed
# ---------------------------------------------------------------------------

@app.route("/ted-ed")
def ted_ed_index():
    subject = request.args.get("subject", "")
    grade = request.args.get("grade", "")
    items = TedEdLesson.query.order_by(TedEdLesson.title).all()
    if subject:
        items = [x for x in items if x.subject == subject]
    if grade:
        items = [x for x in items if x.grade_band == grade]
    subjects = sorted({x.subject for x in TedEdLesson.query.all() if x.subject})
    grades = sorted({x.grade_band for x in TedEdLesson.query.all() if x.grade_band})
    return render_template("ted_ed_index.html", lessons=items, subject=subject,
                           grade=grade, subjects=subjects, grades=grades)


@app.route("/ted-ed/<slug>")
def ted_ed_detail(slug):
    lesson = TedEdLesson.query.filter_by(slug=slug).first_or_404()
    related_talk = Talk.query.filter_by(slug=lesson.talk_slug).first()
    return render_template("ted_ed_detail.html", lesson=lesson,
                           related_talk=related_talk)


# ---------------------------------------------------------------------------
# Conferences (flagship + special TED events)
# ---------------------------------------------------------------------------

@app.route("/conferences")
def conferences_index():
    items = Conference.query.order_by(Conference.starts_on).all()
    return render_template("conferences_index.html", conferences=items)


@app.route("/conferences/<slug>")
def conference_detail(slug):
    conf = Conference.query.filter_by(slug=slug).first_or_404()
    session_slugs = json.loads(conf.session_slugs_json or "[]")
    sessions = [Talk.query.filter_by(slug=s).first() for s in session_slugs]
    sessions = [s for s in sessions if s]
    return render_template("conference_detail.html", conf=conf, sessions=sessions)


@app.route("/conferences/<slug>/attend", methods=["GET", "POST"])
def conference_attend(slug):
    conf = Conference.query.filter_by(slug=slug).first_or_404()
    if request.method == "POST":
        login_redirect = require_login()
        if login_redirect:
            return login_redirect
        flash(f"You are on the {conf.name} attend list.", "success")
        return redirect(url_for("conference_attend", slug=slug))
    return render_template("conference_attend.html", conf=conf)


@app.route("/conferences/<slug>/apply", methods=["GET", "POST"])
def conference_apply(slug):
    conf = Conference.query.filter_by(slug=slug).first_or_404()
    if request.method == "POST":
        login_redirect = require_login()
        if login_redirect:
            return login_redirect
        user = current_user()
        role = (request.form.get("role") or "Attendee").strip()
        motivation = (request.form.get("motivation") or "").strip()
        existing = ConferenceApplication.query.filter_by(
            user_id=user.id, conference_id=conf.id).first()
        if not existing:
            db.session.add(ConferenceApplication(
                user_id=user.id, conference_id=conf.id,
                role=role, motivation=motivation, status="submitted",
            ))
            db.session.commit()
            flash(f"Application submitted for {conf.name}.", "success")
        else:
            existing.role = role
            existing.motivation = motivation
            db.session.commit()
            flash(f"Application updated for {conf.name}.", "success")
        return redirect(url_for("conference_apply", slug=slug))
    roles = json.loads(conf.application_roles_json or "[]")
    user = current_user()
    existing = None
    if user:
        existing = ConferenceApplication.query.filter_by(
            user_id=user.id, conference_id=conf.id).first()
    return render_template("conference_apply.html", conf=conf, roles=roles,
                            existing=existing)


# ---------------------------------------------------------------------------
# TEDx
# ---------------------------------------------------------------------------

@app.route("/tedx")
def tedx_index():
    items = TedxEvent.query.order_by(TedxEvent.date).all()
    return render_template("tedx_index.html", events=items)


@app.route("/tedx/event/<slug>", methods=["GET", "POST"])
def tedx_event(slug):
    event = TedxEvent.query.filter_by(slug=slug).first_or_404()
    if request.method == "POST":
        login_redirect = require_login()
        if login_redirect:
            return login_redirect
        user = current_user()
        role = (request.form.get("role") or "Attendee").strip()
        db.session.add(TedxApplication(
            user_id=user.id, tedx_event_id=event.id,
            role=role, status="submitted",
        ))
        db.session.commit()
        flash(f"RSVP saved for {event.name}.", "success")
        return redirect(url_for("tedx_event", slug=slug))
    feature_talk = Talk.query.filter_by(slug=event.feature_talk_slug).first()
    return render_template("tedx_event.html", event=event, feature_talk=feature_talk)


# ---------------------------------------------------------------------------
# Membership
# ---------------------------------------------------------------------------

@app.route("/membership")
def membership_landing():
    tiers = MembershipTier.query.order_by(MembershipTier.monthly_price).all()
    return render_template("membership_landing.html", tiers=tiers)


@app.route("/membership/levels")
def membership_levels():
    tiers = MembershipTier.query.order_by(MembershipTier.monthly_price).all()
    return render_template("membership_levels.html", tiers=tiers)


@app.route("/membership/subscribe", methods=["GET", "POST"])
def membership_subscribe():
    tiers = MembershipTier.query.order_by(MembershipTier.monthly_price).all()
    if request.method == "POST":
        login_redirect = require_login()
        if login_redirect:
            return login_redirect
        user = current_user()
        tier_slug = (request.form.get("tier") or "supporter").strip().lower()
        billing = (request.form.get("billing") or "monthly").strip().lower()
        tier = MembershipTier.query.filter_by(slug=tier_slug).first()
        if not tier:
            flash("Unknown membership tier.", "error")
            return redirect(url_for("membership_subscribe"))
        existing = MembershipSubscription.query.filter_by(
            user_id=user.id).order_by(MembershipSubscription.id.desc()).first()
        if existing:
            existing.tier_slug = tier_slug
            existing.billing = billing
            existing.status = "active"
        else:
            db.session.add(MembershipSubscription(
                user_id=user.id, tier_slug=tier_slug,
                billing=billing, status="active",
            ))
        user.member_tier = tier_slug
        db.session.commit()
        flash(f"Membership upgraded to {tier.name}.", "success")
        return redirect(url_for("account"))
    return render_template("membership_subscribe.html", tiers=tiers)


# ---------------------------------------------------------------------------
# Translate / Open Translation Project
# ---------------------------------------------------------------------------

@app.route("/translate")
def translate_landing():
    languages_count = 119
    submitted = Translation.query.count()
    return render_template("translate_landing.html",
                           languages_count=languages_count,
                           submitted=submitted)


@app.route("/translate/dashboard", methods=["GET", "POST"])
def translate_dashboard():
    login_redirect = require_login()
    if login_redirect:
        return login_redirect
    user = current_user()
    if request.method == "POST":
        talk_slug = (request.form.get("talk_slug") or "").strip()
        language = (request.form.get("language") or "Spanish").strip()
        body = (request.form.get("body") or "").strip()
        talk = Talk.query.filter_by(slug=talk_slug).first()
        if not talk:
            flash("That talk could not be found.", "error")
        else:
            db.session.add(Translation(
                talk_id=talk.id, language=language,
                translator_user_id=user.id, body=body, status="submitted",
            ))
            db.session.commit()
            flash(f"Translation draft submitted for \"{talk.title}\" ({language}).",
                  "success")
        return redirect(url_for("translate_dashboard"))
    submissions = Translation.query.filter_by(translator_user_id=user.id) \
        .order_by(Translation.id.desc()).all()
    suggested = Talk.query.order_by(Talk.views.desc()).limit(8).all()
    languages = ["Spanish", "French", "Mandarin", "Hindi", "Portuguese",
                 "Japanese", "Arabic", "German", "Korean", "Italian",
                 "Russian", "Bengali"]
    return render_template("translate_dashboard.html",
                           submissions=submissions, suggested=suggested,
                           languages=languages)


@app.route("/translate/<int:translation_id>/review", methods=["POST"])
def translate_review(translation_id):
    login_redirect = require_login()
    if login_redirect:
        return login_redirect
    tr = db.session.get(Translation, translation_id) or abort(404)
    decision = (request.form.get("decision") or "reviewed").strip().lower()
    tr.status = "published" if decision == "approve" else "reviewed"
    db.session.commit()
    flash(f"Translation marked {tr.status}.", "success")
    return redirect(url_for("translate_dashboard"))


# ---------------------------------------------------------------------------
# About
# ---------------------------------------------------------------------------

@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/about/our-organization")
def about_org():
    return render_template("about_org.html")


@app.route("/about/programs-initiatives")
def about_programs():
    series_rows = Series.query.all()
    return render_template("about_programs.html", series_rows=series_rows)


# ---------------------------------------------------------------------------
# Blog (TED Ideas)
# ---------------------------------------------------------------------------

@app.route("/blog")
def blog_index():
    bucket = request.args.get("bucket", "")
    items = BlogPost.query.order_by(BlogPost.published_at.desc(), BlogPost.id).all()
    if bucket:
        items = [b for b in items if b.bucket_slug == bucket]
    buckets = sorted({(b.bucket_slug, b.bucket) for b in BlogPost.query.all()})
    return render_template("blog_index.html", posts=items, bucket=bucket,
                           buckets=buckets)


@app.route("/blog/<slug>", methods=["GET", "POST"])
def blog_post(slug):
    post = BlogPost.query.filter_by(slug=slug).first_or_404()
    if request.method == "POST":
        login_redirect = require_login()
        if login_redirect:
            return login_redirect
        user = current_user()
        body = (request.form.get("body") or "").strip()
        if body:
            db.session.add(BlogComment(
                user_id=user.id, post_id=post.id, body=body,
                author_label=user.display_name,
            ))
            db.session.commit()
            flash("Comment posted.", "success")
        return redirect(url_for("blog_post", slug=slug))
    related_talk = Talk.query.filter_by(slug=post.talk_slug).first()
    comments = BlogComment.query.filter_by(post_id=post.id).order_by(BlogComment.id).all()
    return render_template("blog_post.html", post=post, related_talk=related_talk,
                            comments=comments)


# ---------------------------------------------------------------------------
# Newsletter
# ---------------------------------------------------------------------------

@app.route("/newsletter")
def newsletter_index():
    items = Newsletter.query.all()
    return render_template("newsletter_index.html", newsletters=items)


@app.route("/newsletter/subscribe", methods=["GET", "POST"])
def newsletter_subscribe():
    items = Newsletter.query.all()
    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        slug = (request.form.get("newsletter") or "ideas").strip().lower()
        if not email or "@" not in email:
            flash("Please provide a valid email.", "error")
        elif not Newsletter.query.filter_by(slug=slug).first():
            flash("Unknown newsletter.", "error")
        else:
            user = current_user()
            db.session.add(NewsletterSubscription(
                user_id=user.id if user else None,
                email=email, newsletter_slug=slug, confirmed=True,
            ))
            db.session.commit()
            flash(f"Subscribed {email} to {slug}.", "success")
        return redirect(url_for("newsletter_subscribe"))
    return render_template("newsletter_subscribe.html", newsletters=items)


# ---------------------------------------------------------------------------
# Account hub
# ---------------------------------------------------------------------------

@app.route("/myaccount")
def myaccount_redirect():
    return redirect(url_for("account"))


@app.route("/myaccount/saved-talks")
def myaccount_saved():
    login_redirect = require_login()
    if login_redirect:
        return login_redirect
    user = current_user()
    saved = SavedTalk.query.filter_by(user_id=user.id).order_by(
        SavedTalk.saved_at.desc()).all()
    return render_template("account_saved.html", saved=saved)


@app.route("/myaccount/notes", methods=["GET", "POST"])
def myaccount_notes():
    login_redirect = require_login()
    if login_redirect:
        return login_redirect
    user = current_user()
    if request.method == "POST":
        note_id = request.form.get("delete_note_id", type=int)
        if note_id:
            note = db.session.get(TalkNote, note_id)
            if note and note.user_id == user.id:
                db.session.delete(note)
                db.session.commit()
                flash("Note deleted.", "success")
        return redirect(url_for("myaccount_notes"))
    notes = TalkNote.query.filter_by(user_id=user.id).order_by(
        TalkNote.created_at.desc()).all()
    return render_template("account_notes.html", notes=notes)


@app.route("/myaccount/playlists", methods=["GET", "POST"])
def myaccount_playlists():
    login_redirect = require_login()
    if login_redirect:
        return login_redirect
    user = current_user()
    if request.method == "POST":
        title = (request.form.get("title") or "").strip()
        description = (request.form.get("description") or "").strip()
        is_public = bool(request.form.get("is_public"))
        if not title:
            flash("Please give your playlist a title.", "error")
        else:
            slug = _slugify(title)[:120]
            db.session.add(UserPlaylist(
                user_id=user.id, slug=slug, title=title,
                description=description, is_public=is_public,
            ))
            db.session.commit()
            flash(f"Playlist \"{title}\" created.", "success")
        return redirect(url_for("myaccount_playlists"))
    playlists = UserPlaylist.query.filter_by(user_id=user.id).order_by(
        UserPlaylist.created_at.desc()).all()
    return render_template("account_playlists.html", playlists=playlists)


@app.route("/myaccount/playlists/<int:playlist_id>", methods=["GET", "POST"])
def myaccount_playlist_detail(playlist_id):
    login_redirect = require_login()
    if login_redirect:
        return login_redirect
    user = current_user()
    playlist = db.session.get(UserPlaylist, playlist_id) or abort(404)
    if playlist.user_id != user.id:
        abort(403)
    if request.method == "POST":
        action = request.form.get("action", "add")
        if action == "delete-playlist":
            UserPlaylistTalk.query.filter_by(user_playlist_id=playlist.id).delete()
            db.session.delete(playlist)
            db.session.commit()
            flash("Playlist deleted.", "success")
            return redirect(url_for("myaccount_playlists"))
        if action == "remove":
            ut_id = request.form.get("ut_id", type=int)
            if ut_id:
                ut = db.session.get(UserPlaylistTalk, ut_id)
                if ut and ut.user_playlist_id == playlist.id:
                    db.session.delete(ut)
                    db.session.commit()
                    flash("Removed from playlist.", "success")
        else:
            talk_slug = (request.form.get("talk_slug") or "").strip()
            talk = Talk.query.filter_by(slug=talk_slug).first()
            if not talk:
                flash("Talk not found.", "error")
            else:
                pos = UserPlaylistTalk.query.filter_by(
                    user_playlist_id=playlist.id).count() + 1
                db.session.add(UserPlaylistTalk(
                    user_playlist_id=playlist.id, talk_id=talk.id, position=pos,
                ))
                db.session.commit()
                flash(f"Added \"{talk.title}\" to playlist.", "success")
        return redirect(url_for("myaccount_playlist_detail", playlist_id=playlist.id))
    talks = UserPlaylistTalk.query.filter_by(
        user_playlist_id=playlist.id).order_by(UserPlaylistTalk.position).all()
    return render_template("account_playlist_detail.html",
                           playlist=playlist, items=talks)


# ---------------------------------------------------------------------------
# Talk interactions (POST)
# ---------------------------------------------------------------------------

@app.route("/events", methods=["GET", "POST"])
def events():
    if request.method == "POST":
        login_redirect = require_login()
        if login_redirect:
            return login_redirect
        event = Event.query.filter_by(slug=request.form.get("event_slug")).first_or_404()
        user = current_user()
        existing = Registration.query.filter_by(user_id=user.id, event_id=event.id).first()
        if not existing:
            db.session.add(Registration(user_id=user.id, event_id=event.id,
                                        status="waitlisted"))
            db.session.commit()
        flash(f"Registration saved for {event.name}.", "success")
        return redirect(url_for("account"))
    return render_template("events.html",
                           events=Event.query.order_by(Event.month.desc()).all())


@app.route("/save/<slug>", methods=["POST"])
def save_talk(slug):
    login_redirect = require_login()
    if login_redirect:
        return login_redirect
    talk = Talk.query.filter_by(slug=slug).first_or_404()
    user = current_user()
    if not SavedTalk.query.filter_by(user_id=user.id, talk_id=talk.id).first():
        db.session.add(SavedTalk(user_id=user.id, talk_id=talk.id,
                                 note=request.form.get("note", "")))
        db.session.commit()
        flash("Talk saved.", "success")
    return redirect(request.referrer or url_for("talk_detail", slug=slug))


@app.route("/unsave/<int:saved_id>", methods=["POST"])
def unsave_talk(saved_id):
    login_redirect = require_login()
    if login_redirect:
        return login_redirect
    saved = SavedTalk.query.get_or_404(saved_id)
    if saved.user_id != current_user().id:
        abort(403)
    db.session.delete(saved)
    db.session.commit()
    flash("Saved talk removed.", "success")
    return redirect(url_for("myaccount_saved"))


@app.route("/talks/<slug>/note", methods=["POST"])
def talk_note(slug):
    login_redirect = require_login()
    if login_redirect:
        return login_redirect
    talk = Talk.query.filter_by(slug=slug).first_or_404()
    body = (request.form.get("body") or "").strip()
    if not body:
        flash("Please write a note first.", "error")
    else:
        user = current_user()
        db.session.add(TalkNote(user_id=user.id, talk_id=talk.id, body=body))
        db.session.commit()
        flash("Note saved.", "success")
    return redirect(url_for("talk_detail", slug=slug))


@app.route("/talks/<slug>/rate", methods=["POST"])
def talk_rate(slug):
    login_redirect = require_login()
    if login_redirect:
        return login_redirect
    talk = Talk.query.filter_by(slug=slug).first_or_404()
    user = current_user()
    value = request.form.get("value", type=int) or 0
    value = max(1, min(5, value))
    existing = TalkRating.query.filter_by(user_id=user.id, talk_id=talk.id).first()
    if existing:
        existing.value = value
    else:
        db.session.add(TalkRating(user_id=user.id, talk_id=talk.id, value=value))
    db.session.commit()
    flash(f"Rated \"{talk.title}\" {value}/5.", "success")
    return redirect(url_for("talk_detail", slug=slug))


@app.route("/talks/<slug>/share", methods=["POST"])
def talk_share(slug):
    talk = Talk.query.filter_by(slug=slug).first_or_404()
    user = current_user()
    channel = (request.form.get("channel") or "link").strip().lower()
    message = (request.form.get("message") or "").strip()[:280]
    db.session.add(ShareLog(
        user_id=user.id if user else None, talk_id=talk.id,
        channel=channel, message=message,
    ))
    db.session.commit()
    flash(f"Share link copied ({channel}).", "success")
    return redirect(url_for("talk_detail", slug=slug))


@app.route("/talks/<slug>/translate", methods=["POST"])
def talk_translate_submit(slug):
    login_redirect = require_login()
    if login_redirect:
        return login_redirect
    talk = Talk.query.filter_by(slug=slug).first_or_404()
    user = current_user()
    language = (request.form.get("language") or "Spanish").strip()
    body = (request.form.get("body") or "").strip()
    db.session.add(Translation(
        talk_id=talk.id, language=language,
        translator_user_id=user.id, body=body, status="submitted",
    ))
    db.session.commit()
    flash(f"Translation draft submitted ({language}).", "success")
    return redirect(url_for("talk_transcript", slug=slug))


@app.route("/comment/<int:comment_id>/vote", methods=["POST"])
def comment_vote(comment_id):
    login_redirect = require_login()
    if login_redirect:
        return login_redirect
    comment = db.session.get(Comment, comment_id) or abort(404)
    user = current_user()
    direction = request.form.get("direction", "up")
    delta = 1 if direction == "up" else -1
    existing = CommentVote.query.filter_by(user_id=user.id, comment_id=comment.id).first()
    if existing:
        existing.value = delta
    else:
        db.session.add(CommentVote(user_id=user.id, comment_id=comment.id, value=delta))
    comment.score = (comment.score or 0) + delta
    db.session.commit()
    return redirect(url_for("talk_discussion", slug=comment.talk.slug))


@app.route("/comment/<int:comment_id>/report", methods=["POST"])
def comment_report(comment_id):
    comment = db.session.get(Comment, comment_id) or abort(404)
    user = current_user()
    reason = (request.form.get("reason") or "spam").strip().lower()
    detail = (request.form.get("detail") or "").strip()
    db.session.add(Report(
        user_id=user.id if user else None,
        target_type="comment", target_id=comment.id,
        reason=reason, detail=detail,
    ))
    db.session.commit()
    flash("Report submitted.", "success")
    return redirect(url_for("talk_discussion", slug=comment.talk.slug))


@app.route("/blog/<slug>/share", methods=["POST"])
def blog_share(slug):
    post = BlogPost.query.filter_by(slug=slug).first_or_404()
    user = current_user()
    channel = (request.form.get("channel") or "link").strip().lower()
    message = (request.form.get("message") or "").strip()[:280]
    db.session.add(ShareLog(
        user_id=user.id if user else None, blog_post_id=post.id,
        channel=channel, message=message,
    ))
    db.session.commit()
    flash(f"Shared blog post via {channel}.", "success")
    return redirect(url_for("blog_post", slug=slug))


# ---------------------------------------------------------------------------
# Auth + account
# ---------------------------------------------------------------------------

@app.route("/account", methods=["GET", "POST"])
def account():
    login_redirect = require_login()
    if login_redirect:
        return login_redirect
    user = current_user()
    if request.method == "POST":
        user.display_name = request.form.get("display_name", user.display_name).strip() or user.display_name
        user.role = request.form.get("role", user.role).strip() or user.role
        user.city = request.form.get("city", user.city).strip()
        user.newsletter_topic = request.form.get("newsletter_topic", user.newsletter_topic).strip().lower()
        user.bio = request.form.get("bio", user.bio).strip()
        db.session.commit()
        flash("Profile updated.", "success")
        return redirect(url_for("account"))
    saved = SavedTalk.query.filter_by(user_id=user.id).order_by(
        SavedTalk.saved_at.desc()).limit(6).all()
    notes = TalkNote.query.filter_by(user_id=user.id).order_by(
        TalkNote.created_at.desc()).limit(4).all()
    registrations = Registration.query.filter_by(user_id=user.id).all()
    applications = ConferenceApplication.query.filter_by(user_id=user.id).all()
    playlists = UserPlaylist.query.filter_by(user_id=user.id).order_by(
        UserPlaylist.created_at.desc()).all()
    subscription = MembershipSubscription.query.filter_by(
        user_id=user.id).order_by(MembershipSubscription.id.desc()).first()
    tier = None
    if subscription:
        tier = MembershipTier.query.filter_by(slug=subscription.tier_slug).first()
    return render_template("account.html", user=user, saved=saved, notes=notes,
                           registrations=registrations, applications=applications,
                           playlists=playlists, subscription=subscription, tier=tier)


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").lower().strip()
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password_hash, request.form.get("password", "")):
            session["user_id"] = user.id
            flash("Signed in.", "success")
            return redirect(request.args.get("next") or url_for("account"))
        flash("Invalid email or password.", "error")
    return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        email = request.form.get("email", "").lower().strip()
        username = re.sub(r"[^a-z0-9_]+", "", request.form.get("username", "").lower())[:40]
        if User.query.filter((User.email == email) | (User.username == username)).first():
            flash("That email or username already exists.", "error")
        else:
            user = User(
                email=email, username=username,
                display_name=request.form.get("display_name", username).strip() or username,
                password_hash=_deterministic_password_hash(
                    request.form.get("password", "TestPass123!"), email),
            )
            db.session.add(user)
            db.session.commit()
            session["user_id"] = user.id
            flash("Account created.", "success")
            return redirect(url_for("account"))
    return render_template("register.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("Signed out.", "success")
    return redirect(url_for("index"))


# ---------------------------------------------------------------------------
# Tiny API (used internally / by some tasks)
# ---------------------------------------------------------------------------

@app.route("/api/talks/<slug>")
def api_talk(slug):
    talk = Talk.query.filter_by(slug=slug).first_or_404()
    return jsonify({
        "slug": talk.slug,
        "title": talk.title,
        "speaker": talk.speaker,
        "event": talk.event,
        "duration_seconds": talk.duration_seconds,
        "views": talk.views,
        "topics": talk.topics,
    })


@app.route("/_health")
def health():
    return {"ok": True, "site": "ted", "talks": Talk.query.count(),
            "speakers": Speaker.query.count(),
            "conferences": Conference.query.count(),
            "blog_posts": BlogPost.query.count()}


# ---------------------------------------------------------------------------
# Boot
# ---------------------------------------------------------------------------

with app.app_context():
    fresh_seed = not DB_PATH.exists()
    db.create_all()
    seed_database()
    seed_users()
    if fresh_seed:
        normalize_seed_db_layout()
    if not SEED_DB_PATH.exists() and DB_PATH.exists():
        SEED_DB_PATH.parent.mkdir(exist_ok=True)
        shutil.copy2(DB_PATH, SEED_DB_PATH)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 40015))
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

