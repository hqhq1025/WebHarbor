#!/usr/bin/env python3
"""ESPN mirror — Flask application with sports data, news, scores, stats."""
import os
import json
import re
import hashlib
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
from wtforms import StringField, PasswordField, TextAreaField
from wtforms.validators import DataRequired, Email, Length, EqualTo, Optional
from sqlalchemy import or_, func

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ─── Mirror clock pin ─────────────────────────────────────────────────────────
# This mirror's content (articles, finalized games, schedules, transactions)
# is frozen in 2024. WebVoyager / WebTau tasks use relative phrases like
# "yesterday", "latest", "past 2 days", "next game", "today's top headline".
# We anchor "today" to a fixed date so those phrases always resolve against
# real data, regardless of wall-clock time when the agent is run.
#
# Picked 2024-04-10 after auditing every date-bearing column AND every
# date-relative WebVoyager task. Rationale:
#
#   yesterday  (anchor − 1d = 2024-04-09):
#     · 2 NBA finalized games (Pacers@Bucks 119-114, Warriors@Nuggets 121-109)
#     · 2 NHL finalized games (Rangers@Bruins 4-2, Oilers@Knights 3-2)
#     · 1 NBA transaction
#   past 2 days  (04-08 / 04-09):  Bucks game, NBA trades / transactions
#   past 3 days  (04-07 / 04-09):  Nuggets game (04-09)
#   past week    (04-03 / 04-09):  5+ NBA transactions
#   latest articles per sport:     04-09 NBA × 4, 04-08 NHL × 1, 04-08 Soccer
#   next scheduled game:           2024-04-14 Nuggets@Lakers (Lakers next)
#   absolute references:           2023-12-25 Christmas Day NBA games (5)
#   season-end framing:            NBA reg season ends mid-April → consistent
#
# No DB row is dated AFTER the anchor except the one intentional 04-14
# scheduled game, so nothing in the seed becomes "from the future."
MIRROR_REFERENCE_DATE = datetime(2024, 4, 10, 12, 0, 0)
MIRROR_REFERENCE_DATE_LABEL = MIRROR_REFERENCE_DATE.strftime('%B %-d, %Y')


def mirror_now() -> datetime:
    """Return the pinned 'now' that all date-relative views use."""
    return MIRROR_REFERENCE_DATE


def mirror_today() -> 'datetime.date':
    """Return the pinned 'today' date."""
    return MIRROR_REFERENCE_DATE.date()


app = Flask(__name__)
app.config['SECRET_KEY'] = 'espn-mirror-secret-key-2024'
app.config['SQLALCHEMY_DATABASE_URI'] = (
    f"sqlite:///{os.path.join(BASE_DIR, 'instance', 'espn.db')}"
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['WTF_CSRF_TIME_LIMIT'] = None

os.makedirs(os.path.join(BASE_DIR, 'instance'), exist_ok=True)

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please sign in to access your ESPN account.'
login_manager.login_message_category = 'info'
csrf = CSRFProtect(app)


# ─── Models ───────────────────────────────────────────────────────────────────

class User(db.Model, UserMixin):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    name = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(30), default='')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_espn_plus = db.Column(db.Boolean, default=False)

    favorites = db.relationship('UserFavorite', backref='user', lazy=True,
                                cascade='all, delete-orphan')

    def set_password(self, pw):
        self.password_hash = bcrypt.generate_password_hash(pw).decode('utf-8')

    def check_password(self, pw):
        return bcrypt.check_password_hash(self.password_hash, pw)

    @property
    def first_name(self):
        return self.name.split()[0] if self.name else ''


class Sport(db.Model):
    __tablename__ = 'sports'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    slug = db.Column(db.String(50), unique=True, nullable=False, index=True)
    display_name = db.Column(db.String(100), default='')
    url_prefix = db.Column(db.String(50), default='')
    nav_order = db.Column(db.Integer, default=99)
    is_active = db.Column(db.Boolean, default=True)


class Conference(db.Model):
    __tablename__ = 'conferences'
    id = db.Column(db.Integer, primary_key=True)
    sport_slug = db.Column(db.String(50), index=True)
    name = db.Column(db.String(100), nullable=False)
    short_name = db.Column(db.String(50), default='')


class Division(db.Model):
    __tablename__ = 'divisions'
    id = db.Column(db.Integer, primary_key=True)
    conference_id = db.Column(db.Integer, db.ForeignKey('conferences.id'))
    sport_slug = db.Column(db.String(50), index=True)
    name = db.Column(db.String(100), nullable=False)


class Team(db.Model):
    __tablename__ = 'teams'
    id = db.Column(db.Integer, primary_key=True)
    sport_slug = db.Column(db.String(50), index=True)
    conference_id = db.Column(db.Integer, db.ForeignKey('conferences.id'), nullable=True)
    division_id = db.Column(db.Integer, db.ForeignKey('divisions.id'), nullable=True)
    name = db.Column(db.String(100), nullable=False)  # "Lakers"
    city = db.Column(db.String(100), default='')
    full_name = db.Column(db.String(150), default='')  # "Los Angeles Lakers"
    slug = db.Column(db.String(80), unique=True, nullable=False, index=True)
    abbreviation = db.Column(db.String(10), default='')
    color_primary = db.Column(db.String(10), default='#552583')
    color_secondary = db.Column(db.String(10), default='#FDB927')
    wins = db.Column(db.Integer, default=0)
    losses = db.Column(db.Integer, default=0)
    ties = db.Column(db.Integer, default=0)
    win_pct = db.Column(db.Float, default=0.0)
    games_back = db.Column(db.Float, default=0.0)
    streak = db.Column(db.String(20), default='W1')
    home_record = db.Column(db.String(10), default='0-0')
    away_record = db.Column(db.String(10), default='0-0')
    division_record = db.Column(db.String(10), default='0-0')
    conference_record = db.Column(db.String(10), default='0-0')
    points_for = db.Column(db.Float, default=0.0)
    points_against = db.Column(db.Float, default=0.0)
    power_index = db.Column(db.Float, default=50.0)
    playoff_odds = db.Column(db.Float, default=50.0)
    standing_rank = db.Column(db.Integer, default=1)
    overtime_losses = db.Column(db.Integer, default=0)  # NHL only

    conference = db.relationship('Conference', backref='teams', lazy=True)
    division = db.relationship('Division', backref='teams', lazy=True)
    players = db.relationship('Player', backref='team', lazy=True)
    home_games = db.relationship('Game', foreign_keys='Game.home_team_id',
                                  backref='home_team', lazy=True)
    away_games = db.relationship('Game', foreign_keys='Game.away_team_id',
                                  backref='away_team', lazy=True)
    transactions = db.relationship('Transaction', backref='team', lazy=True)
    depth_chart = db.relationship('DepthChartEntry', backref='team', lazy=True)


class Player(db.Model):
    __tablename__ = 'players'
    id = db.Column(db.Integer, primary_key=True)
    team_id = db.Column(db.Integer, db.ForeignKey('teams.id'), nullable=True)
    sport_slug = db.Column(db.String(50), index=True)
    name = db.Column(db.String(150), nullable=False)
    slug = db.Column(db.String(200), unique=True, nullable=False, index=True)
    first_name = db.Column(db.String(80), default='')
    last_name = db.Column(db.String(80), default='')
    position = db.Column(db.String(50), default='')
    jersey_number = db.Column(db.String(5), default='')
    height = db.Column(db.String(10), default='')
    weight = db.Column(db.Integer, default=0)
    age = db.Column(db.Integer, default=0)
    nationality = db.Column(db.String(80), default='USA')
    college = db.Column(db.String(100), default='')
    salary = db.Column(db.Float, default=0.0)
    injury_status = db.Column(db.String(50), default='')
    injury_description = db.Column(db.String(200), default='')
    bio = db.Column(db.Text, default='')
    birth_date = db.Column(db.String(20), default='')
    experience = db.Column(db.Integer, default=0)  # years in league

    stats = db.relationship('PlayerStat', backref='player', lazy=True,
                             cascade='all, delete-orphan')
    depth_chart_entries = db.relationship('DepthChartEntry', backref='player', lazy=True)
    game_stats = db.relationship('GamePlayerStat', backref='player', lazy=True)
    transactions_ref = db.relationship('Transaction', backref='player', lazy=True)


class PlayerStat(db.Model):
    __tablename__ = 'player_stats'
    id = db.Column(db.Integer, primary_key=True)
    player_id = db.Column(db.Integer, db.ForeignKey('players.id'), nullable=False)
    season = db.Column(db.String(20), default='2023-24')
    stat_type = db.Column(db.String(20), default='season')  # 'season', 'career'
    games_played = db.Column(db.Integer, default=0)
    games_started = db.Column(db.Integer, default=0)
    # NBA
    points_per_game = db.Column(db.Float, default=0.0)
    rebounds_per_game = db.Column(db.Float, default=0.0)
    assists_per_game = db.Column(db.Float, default=0.0)
    steals_per_game = db.Column(db.Float, default=0.0)
    blocks_per_game = db.Column(db.Float, default=0.0)
    fg_pct = db.Column(db.Float, default=0.0)
    three_pt_pct = db.Column(db.Float, default=0.0)
    ft_pct = db.Column(db.Float, default=0.0)
    minutes_per_game = db.Column(db.Float, default=0.0)
    # Career totals (for career stat_type)
    total_points = db.Column(db.Integer, default=0)
    total_rebounds = db.Column(db.Integer, default=0)
    total_assists = db.Column(db.Integer, default=0)
    total_games = db.Column(db.Integer, default=0)
    # MLB
    batting_avg = db.Column(db.Float, default=0.0)
    home_runs = db.Column(db.Integer, default=0)
    rbi = db.Column(db.Integer, default=0)
    stolen_bases = db.Column(db.Integer, default=0)
    era = db.Column(db.Float, default=0.0)
    strikeouts = db.Column(db.Integer, default=0)
    wins_pitcher = db.Column(db.Integer, default=0)
    # NHL
    goals = db.Column(db.Integer, default=0)
    hockey_assists = db.Column(db.Integer, default=0)
    hockey_points = db.Column(db.Integer, default=0)
    plus_minus = db.Column(db.Integer, default=0)
    penalty_minutes = db.Column(db.Integer, default=0)
    # NFL
    passing_yards = db.Column(db.Integer, default=0)
    passing_tds = db.Column(db.Integer, default=0)
    rushing_yards = db.Column(db.Integer, default=0)
    rushing_tds = db.Column(db.Integer, default=0)
    receiving_yards = db.Column(db.Integer, default=0)
    receiving_tds = db.Column(db.Integer, default=0)
    receptions = db.Column(db.Integer, default=0)
    tackles = db.Column(db.Integer, default=0)
    sacks = db.Column(db.Float, default=0.0)
    # Soccer
    soccer_goals = db.Column(db.Integer, default=0)
    soccer_assists = db.Column(db.Integer, default=0)
    soccer_appearances = db.Column(db.Integer, default=0)
    yellow_cards = db.Column(db.Integer, default=0)
    red_cards = db.Column(db.Integer, default=0)


class Game(db.Model):
    __tablename__ = 'games'
    id = db.Column(db.Integer, primary_key=True)
    sport_slug = db.Column(db.String(50), index=True)
    home_team_id = db.Column(db.Integer, db.ForeignKey('teams.id'))
    away_team_id = db.Column(db.Integer, db.ForeignKey('teams.id'))
    home_score = db.Column(db.Integer, default=0)
    away_score = db.Column(db.Integer, default=0)
    date = db.Column(db.String(20), default='')  # YYYY-MM-DD
    date_display = db.Column(db.String(50), default='')
    time = db.Column(db.String(20), default='7:30 PM ET')
    status = db.Column(db.String(30), default='final')  # 'final', 'scheduled', 'live'
    period = db.Column(db.String(20), default='Final')
    network = db.Column(db.String(50), default='ESPN')
    venue = db.Column(db.String(200), default='')
    recap = db.Column(db.Text, default='')
    ticket_url = db.Column(db.String(500), default='https://www.ticketmaster.com')
    # Leaders stored as JSON
    game_leaders = db.Column(db.Text, default='{}')

    player_stats = db.relationship('GamePlayerStat', backref='game', lazy=True,
                                    cascade='all, delete-orphan')

    def get_leaders(self):
        try:
            return json.loads(self.game_leaders or '{}')
        except Exception:
            return {}


class GamePlayerStat(db.Model):
    __tablename__ = 'game_player_stats'
    id = db.Column(db.Integer, primary_key=True)
    game_id = db.Column(db.Integer, db.ForeignKey('games.id'), nullable=False)
    player_id = db.Column(db.Integer, db.ForeignKey('players.id'), nullable=False)
    team_id = db.Column(db.Integer, db.ForeignKey('teams.id'), nullable=False)
    points = db.Column(db.Integer, default=0)
    rebounds = db.Column(db.Integer, default=0)
    assists = db.Column(db.Integer, default=0)
    steals = db.Column(db.Integer, default=0)
    blocks = db.Column(db.Integer, default=0)
    minutes = db.Column(db.String(10), default='0')

    stat_team = db.relationship('Team', backref='game_player_stats', lazy=True)


class Article(db.Model):
    __tablename__ = 'articles'
    id = db.Column(db.Integer, primary_key=True)
    sport_slug = db.Column(db.String(50), index=True)
    title = db.Column(db.String(500), nullable=False)
    slug = db.Column(db.String(500), unique=True, nullable=False, index=True)
    subtitle = db.Column(db.String(500), default='')
    body = db.Column(db.Text, default='')
    author = db.Column(db.String(100), default='ESPN Staff')
    image = db.Column(db.String(300), default='')
    tags = db.Column(db.Text, default='[]')
    is_headline = db.Column(db.Boolean, default=False)
    is_featured = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    published_date = db.Column(db.String(50), default='')

    def get_tags(self):
        try:
            return json.loads(self.tags or '[]')
        except Exception:
            return []


class Transaction(db.Model):
    __tablename__ = 'transactions'
    id = db.Column(db.Integer, primary_key=True)
    sport_slug = db.Column(db.String(50), index=True)
    team_id = db.Column(db.Integer, db.ForeignKey('teams.id'), nullable=True)
    player_id = db.Column(db.Integer, db.ForeignKey('players.id'), nullable=True)
    description = db.Column(db.Text, nullable=False)
    transaction_type = db.Column(db.String(50), default='trade')
    date = db.Column(db.String(20), default='')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class DepthChartEntry(db.Model):
    __tablename__ = 'depth_chart'
    id = db.Column(db.Integer, primary_key=True)
    team_id = db.Column(db.Integer, db.ForeignKey('teams.id'), nullable=False)
    position = db.Column(db.String(50), default='')
    position_rank = db.Column(db.Integer, default=1)
    player_id = db.Column(db.Integer, db.ForeignKey('players.id'), nullable=False)
    injury_notes = db.Column(db.String(100), default='')


class PowerIndex(db.Model):
    __tablename__ = 'power_index'
    id = db.Column(db.Integer, primary_key=True)
    team_id = db.Column(db.Integer, db.ForeignKey('teams.id'), nullable=False)
    sport_slug = db.Column(db.String(50), index=True)
    season = db.Column(db.String(20), default='2023-24')
    index_value = db.Column(db.Float, default=50.0)
    playoff_odds = db.Column(db.Float, default=50.0)
    avg_point_diff = db.Column(db.Float, default=0.0)
    rank = db.Column(db.Integer, default=1)

    pi_team = db.relationship('Team', backref='power_index_data', lazy=True)


class Recruit(db.Model):
    __tablename__ = 'recruits'
    id = db.Column(db.Integer, primary_key=True)
    sport_slug = db.Column(db.String(50), index=True)
    gender = db.Column(db.String(10), default='M')
    name = db.Column(db.String(150), nullable=False)
    position = db.Column(db.String(50), default='')
    hometown = db.Column(db.String(100), default='')
    committed_to = db.Column(db.String(100), default='')
    stars = db.Column(db.Integer, default=5)
    rank = db.Column(db.Integer, default=1)
    season = db.Column(db.String(20), default='2024-25')
    class_year = db.Column(db.String(10), default='2024')


class UserFavorite(db.Model):
    __tablename__ = 'user_favorites'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    item_type = db.Column(db.String(20), default='team')
    item_id = db.Column(db.Integer, default=0)
    added_at = db.Column(db.DateTime, default=datetime.utcnow)


# ─── R3 Models (betting, awards, draft, podcasts) ────────────────────────────

class BettingOdds(db.Model):
    __tablename__ = 'betting_odds'
    id = db.Column(db.Integer, primary_key=True)
    game_id = db.Column(db.Integer, index=True)
    sport_slug = db.Column(db.String(20), index=True)
    home_moneyline = db.Column(db.Integer, default=0)
    away_moneyline = db.Column(db.Integer, default=0)
    spread_favorite = db.Column(db.String(10), default='')
    spread_line = db.Column(db.Float, default=0.0)
    total = db.Column(db.Float, default=0.0)
    over_odds = db.Column(db.Integer, default=-110)
    under_odds = db.Column(db.Integer, default=-110)
    opened_label = db.Column(db.String(40), default='')
    status = db.Column(db.String(20), default='open')
    sportsbook = db.Column(db.String(40), default='ESPN BET')


class Award(db.Model):
    __tablename__ = 'awards'
    id = db.Column(db.Integer, primary_key=True)
    sport_slug = db.Column(db.String(20), index=True)
    season = db.Column(db.String(20), default='2023-24')
    award_name = db.Column(db.String(80))
    award_slug = db.Column(db.String(80))
    winner_player_id = db.Column(db.Integer)
    winner_team_id = db.Column(db.Integer)
    finalists = db.Column(db.Text, default='[]')
    voting_share = db.Column(db.Float, default=0.0)
    announced_date = db.Column(db.String(20), default='')


class DraftPick(db.Model):
    __tablename__ = 'draft_picks'
    id = db.Column(db.Integer, primary_key=True)
    sport_slug = db.Column(db.String(20), index=True)
    season = db.Column(db.String(20))
    round = db.Column(db.Integer)
    pick = db.Column(db.Integer)
    overall_pick = db.Column(db.Integer)
    team_id = db.Column(db.Integer)
    player_name = db.Column(db.String(150))
    position = db.Column(db.String(20))
    school = db.Column(db.String(120))
    country = db.Column(db.String(60))
    height = db.Column(db.String(10))
    weight = db.Column(db.Integer)
    scout_grade = db.Column(db.Float)
    notes = db.Column(db.String(300))
    is_mock = db.Column(db.Integer, default=1)


class Podcast(db.Model):
    __tablename__ = 'podcasts'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200))
    slug = db.Column(db.String(200), index=True)
    host = db.Column(db.String(200))
    sport_slug = db.Column(db.String(20))
    description = db.Column(db.Text)
    episode_count = db.Column(db.Integer, default=0)
    latest_episode_title = db.Column(db.String(200))
    latest_episode_date = db.Column(db.String(20))
    duration_minutes = db.Column(db.Integer, default=0)


# ─── R4 Models (play-by-play, watchables, parlays) ───────────────────────────

class PlayByPlay(db.Model):
    __tablename__ = 'play_by_play'
    id = db.Column(db.Integer, primary_key=True)
    game_id = db.Column(db.Integer, index=True)
    sport_slug = db.Column(db.String(20), index=True)
    sequence = db.Column(db.Integer, default=0)
    period = db.Column(db.String(10), default='')
    clock = db.Column(db.String(10), default='')
    team_id = db.Column(db.Integer, default=0)
    actor_name = db.Column(db.String(150), default='')
    event_type = db.Column(db.String(30), default='')
    description = db.Column(db.String(300), default='')
    score_home = db.Column(db.Integer, default=0)
    score_away = db.Column(db.Integer, default=0)


class Watchable(db.Model):
    __tablename__ = 'watchables'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200))
    slug = db.Column(db.String(200), index=True)
    kind = db.Column(db.String(40), default='show')
    sport_slug = db.Column(db.String(20), index=True)
    description = db.Column(db.Text)
    is_espn_plus = db.Column(db.Integer, default=1)
    is_live = db.Column(db.Integer, default=0)
    duration_minutes = db.Column(db.Integer, default=0)
    release_date = db.Column(db.String(20))
    host_or_studio = db.Column(db.String(150))


class Parlay(db.Model):
    __tablename__ = 'parlays'
    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(80), index=True)
    title = db.Column(db.String(200))
    leg_count = db.Column(db.Integer, default=0)
    american_odds = db.Column(db.Integer, default=0)
    decimal_odds = db.Column(db.Float, default=0.0)
    legs_json = db.Column(db.Text, default='[]')
    sport_slug = db.Column(db.String(20))
    sportsbook = db.Column(db.String(40))
    is_featured = db.Column(db.Integer, default=0)


# ─── Login ────────────────────────────────────────────────────────────────────

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# ─── Context Processors ───────────────────────────────────────────────────────

@app.context_processor
def inject_globals():
    sports = (Sport.query.filter_by(is_active=True)
              .order_by(Sport.nav_order).all())
    # Defensive: drop any internal marker rows (slug starts with underscore)
    sports = [s for s in sports if not (s.slug or '').startswith('_')]
    return {
        'nav_sports': sports,
        'csrf_token_value': generate_csrf(),
        'today': mirror_today().strftime('%Y-%m-%d'),
        'mirror_today_label': MIRROR_REFERENCE_DATE_LABEL,
        'mirror_today_iso':   mirror_today().strftime('%Y-%m-%d'),
    }


@app.template_filter('from_json_safe')
def _from_json_safe(value):
    """Parse a JSON string in a template; return [] / {} on failure."""
    if not value:
        return []
    try:
        return json.loads(value)
    except (TypeError, ValueError):
        return []


# ─── Forms ────────────────────────────────────────────────────────────────────

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])


class RegisterForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired(), Length(min=2, max=120)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    confirm = PasswordField('Confirm Password',
                            validators=[DataRequired(), EqualTo('password')])


class ProfileForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired()])
    phone = StringField('Phone', validators=[Optional()])


class PasswordForm(FlaskForm):
    current_password = PasswordField('Current Password', validators=[DataRequired()])
    new_password = PasswordField('New Password',
                                 validators=[DataRequired(), Length(min=6)])
    confirm = PasswordField('Confirm', validators=[DataRequired(), EqualTo('new_password')])


# ─── Helpers ──────────────────────────────────────────────────────────────────

STOPWORDS = {'the', 'a', 'an', 'of', 'in', 'on', 'at', 'to', 'for',
             'with', 'and', 'or', 'is', 'are', 'be', 'by', 'from', 'how',
             'many', 'do', 'does', 'what', 'who', 'which', 'all', 'teams',
             'team', 'league', 'players', 'player', 'nba', 'nfl', 'nhl', 'mlb'}


def _score_team(team, tokens):
    haystack = ' '.join([
        (team.full_name or '').lower(),
        (team.name or '').lower(),
        (team.city or '').lower(),
        (team.abbreviation or '').lower(),
        (team.sport_slug or '').lower(),
    ])
    return sum(1 for t in tokens if t in haystack)


def _score_player(player, tokens):
    haystack = ' '.join([
        (player.name or '').lower(),
        (player.first_name or '').lower(),
        (player.last_name or '').lower(),
        (player.position or '').lower(),
        (player.sport_slug or '').lower(),
    ])
    return sum(1 for t in tokens if t in haystack)


def _score_article(article, tokens):
    haystack = ' '.join([
        (article.title or '').lower(),
        (article.subtitle or '').lower(),
        (article.tags or '').lower(),
        (article.sport_slug or '').lower(),
    ])
    return sum(1 for t in tokens if t in haystack)


def get_recent_headlines(sport_slug=None, limit=5):
    q = Article.query.filter_by(is_headline=True)
    if sport_slug:
        q = q.filter_by(sport_slug=sport_slug)
    return q.order_by(Article.created_at.desc()).limit(limit).all()


def get_recent_scores(sport_slug, limit=10):
    return (Game.query
            .filter_by(sport_slug=sport_slug, status='final')
            .order_by(Game.date.desc())
            .limit(limit).all())


def get_upcoming_games(sport_slug, limit=10):
    today = mirror_today().strftime('%Y-%m-%d')
    return (Game.query
            .filter_by(sport_slug=sport_slug, status='scheduled')
            .filter(Game.date >= today)
            .order_by(Game.date)
            .limit(limit).all())


def get_standings(sport_slug):
    conferences = Conference.query.filter_by(sport_slug=sport_slug).all()
    result = []
    for conf in conferences:
        divs = Division.query.filter_by(conference_id=conf.id).all()
        if divs:
            conf_data = {'conference': conf, 'divisions': []}
            for div in divs:
                teams = (Team.query
                         .filter_by(sport_slug=sport_slug, division_id=div.id)
                         .order_by(Team.standing_rank)
                         .all())
                conf_data['divisions'].append({'division': div, 'teams': teams})
            result.append(conf_data)
        else:
            teams = (Team.query
                     .filter_by(sport_slug=sport_slug, conference_id=conf.id)
                     .order_by(Team.standing_rank)
                     .all())
            result.append({'conference': conf, 'divisions': [], 'teams': teams})
    return result


# ─── Routes: Static Pages ─────────────────────────────────────────────────────

@app.route('/')
def index():
    headlines = Article.query.filter_by(is_headline=True).order_by(
        Article.created_at.desc()).limit(8).all()
    featured = Article.query.filter_by(is_featured=True).order_by(
        Article.created_at.desc()).limit(3).all()
    sports_data = {}
    for s in ['nba', 'nfl', 'nhl', 'mlb', 'soccer']:
        sports_data[s] = {
            'scores': get_recent_scores(s, 5),
            'news': Article.query.filter_by(sport_slug=s).order_by(
                Article.created_at.desc()).limit(3).all(),
        }
    return render_template('index.html', headlines=headlines, featured=featured,
                           sports_data=sports_data)


@app.route('/espnplus')
@app.route('/espn-plus')
def espnplus():
    return render_template('espnplus.html')


# ─── Routes: Static Corporate Pages ───────────────────────────────────────────

@app.route('/about')
@app.route('/about/')
@app.route('/about/index.html')
def about():
    return render_template('about.html')


@app.route('/press')
@app.route('/press/')
@app.route('/pressroom')
def press():
    return render_template('press.html')


@app.route('/careers')
@app.route('/careers/')
@app.route('/jobs')
def careers():
    return render_template('careers.html')


@app.route('/watch')
@app.route('/watch/')
def watch():
    sport = Sport.query.filter_by(slug='watch').first()
    featured_articles = Article.query.filter_by(is_featured=True).order_by(
        Article.created_at.desc()).limit(8).all()
    return render_template('watch.html', sport=sport,
                           featured_articles=featured_articles)


# ─── Routes: Favorite (form-based, per ESPN URL convention) ───────────────────

@app.route('/favorite/<team_slug>', methods=['POST', 'GET'])
def favorite_team(team_slug):
    """Toggle a team in the signed-in user's favorites.
    Form POST flow used by team pages (matches espn.com URL shape:
    espn.com/favorite/<team>). Falls back to login redirect when anonymous.
    """
    team = Team.query.filter_by(slug=team_slug).first_or_404()
    if not current_user.is_authenticated:
        flash('Please sign in to add a favorite team.', 'info')
        return redirect(url_for('login'))
    existing = UserFavorite.query.filter_by(
        user_id=current_user.id, item_type='team',
        item_id=team.id).first()
    if existing:
        db.session.delete(existing)
        db.session.commit()
        flash(f'Removed {team.full_name} from favorites.', 'success')
    else:
        fav = UserFavorite(user_id=current_user.id, item_type='team',
                           item_id=team.id)
        db.session.add(fav)
        db.session.commit()
        flash(f'Added {team.full_name} to favorites.', 'success')
    next_url = (request.form.get('next') or request.args.get('next')
                or request.referrer
                or url_for('team_home', sport_slug=team.sport_slug,
                           team_slug=team.slug))
    return redirect(next_url)


# ─── Routes: Sport Sections ───────────────────────────────────────────────────

@app.route('/<sport_slug>/')
@app.route('/<sport_slug>')
def sport_home(sport_slug):
    # Normalize college sport slugs
    slug_map = {
        'college-football': 'ncaaf',
        'mens-college-basketball': 'ncaam',
        'womens-college-basketball': 'ncaaw',
        'ncaa': 'ncaam',
    }
    sport_slug = slug_map.get(sport_slug, sport_slug)
    sport = Sport.query.filter_by(slug=sport_slug).first_or_404()
    headlines = Article.query.filter_by(sport_slug=sport_slug, is_headline=True).order_by(
        Article.created_at.desc()).limit(5).all()
    articles = Article.query.filter_by(sport_slug=sport_slug).order_by(
        Article.created_at.desc()).limit(12).all()
    scores = get_recent_scores(sport_slug, 6)
    upcoming = get_upcoming_games(sport_slug, 6)
    return render_template('sport_home.html', sport=sport,
                           headlines=headlines, articles=articles,
                           scores=scores, upcoming=upcoming)


@app.route('/<sport_slug>/news')
def sport_news(sport_slug):
    slug_map = {'college-football': 'ncaaf', 'mens-college-basketball': 'ncaam',
                'womens-college-basketball': 'ncaaw'}
    sport_slug = slug_map.get(sport_slug, sport_slug)
    sport = Sport.query.filter_by(slug=sport_slug).first_or_404()
    page = request.args.get('page', 1, type=int)
    articles = (Article.query.filter_by(sport_slug=sport_slug)
                .order_by(Article.created_at.desc())
                .paginate(page=page, per_page=20, error_out=False))
    return render_template('sport_news.html', sport=sport, articles=articles)


@app.route('/<sport_slug>/scoreboard')
@app.route('/<sport_slug>/scores')
def scoreboard(sport_slug):
    slug_map = {'college-football': 'ncaaf', 'mens-college-basketball': 'ncaam',
                'womens-college-basketball': 'ncaaw'}
    sport_slug = slug_map.get(sport_slug, sport_slug)
    sport = Sport.query.filter_by(slug=sport_slug).first_or_404()
    date_str = request.args.get('date', '')
    if date_str:
        # Accept YYYYMMDD format
        if len(date_str) == 8:
            try:
                date_obj = datetime.strptime(date_str, '%Y%m%d')
                date_str = date_obj.strftime('%Y-%m-%d')
            except ValueError:
                pass
        games = Game.query.filter_by(sport_slug=sport_slug, date=date_str).all()
        date_display = date_str
    else:
        games = (Game.query.filter_by(sport_slug=sport_slug, status='final')
                 .order_by(Game.date.desc()).limit(15).all())
        date_display = 'Recent'
    upcoming = get_upcoming_games(sport_slug, 5)
    return render_template('scoreboard.html', sport=sport, games=games,
                           upcoming=upcoming, date_display=date_display,
                           date_str=date_str)


@app.route('/scores')
def all_scores():
    date_str = request.args.get('date', '')
    sport_filter = request.args.get('sport', '')
    games_by_sport = {}
    sports = Sport.query.filter_by(is_active=True).all()
    for sp in sports:
        if sport_filter and sp.slug != sport_filter:
            continue
        if date_str:
            if len(date_str) == 8:
                try:
                    date_obj = datetime.strptime(date_str, '%Y%m%d')
                    date_str_q = date_obj.strftime('%Y-%m-%d')
                except ValueError:
                    date_str_q = date_str
            else:
                date_str_q = date_str
            games = Game.query.filter_by(sport_slug=sp.slug, date=date_str_q).all()
        else:
            games = (Game.query.filter_by(sport_slug=sp.slug, status='final')
                     .order_by(Game.date.desc()).limit(5).all())
        if games:
            games_by_sport[sp] = games
    return render_template('all_scores.html', games_by_sport=games_by_sport,
                           date_str=date_str)


@app.route('/<sport_slug>/standings')
def standings(sport_slug):
    slug_map = {'college-football': 'ncaaf', 'mens-college-basketball': 'ncaam',
                'womens-college-basketball': 'ncaaw'}
    sport_slug = slug_map.get(sport_slug, sport_slug)
    sport = Sport.query.filter_by(slug=sport_slug).first_or_404()
    standings_data = get_standings(sport_slug)
    # Flat list for division-less display
    all_teams = Team.query.filter_by(sport_slug=sport_slug).order_by(
        Team.standing_rank).all()
    return render_template('standings.html', sport=sport,
                           standings_data=standings_data, all_teams=all_teams)


@app.route('/<sport_slug>/teams')
def teams_list(sport_slug):
    slug_map = {'college-football': 'ncaaf', 'mens-college-basketball': 'ncaam',
                'womens-college-basketball': 'ncaaw'}
    sport_slug = slug_map.get(sport_slug, sport_slug)
    sport = Sport.query.filter_by(slug=sport_slug).first_or_404()
    conferences = Conference.query.filter_by(sport_slug=sport_slug).all()
    teams_by_conf = {}
    for conf in conferences:
        divs = Division.query.filter_by(conference_id=conf.id).all()
        if divs:
            conf_data = {}
            for div in divs:
                conf_data[div.name] = Team.query.filter_by(
                    sport_slug=sport_slug, division_id=div.id).order_by(
                    Team.full_name).all()
            teams_by_conf[conf.name] = conf_data
        else:
            teams_by_conf[conf.name] = {'All': Team.query.filter_by(
                sport_slug=sport_slug, conference_id=conf.id).order_by(
                Team.full_name).all()}
    all_teams = Team.query.filter_by(sport_slug=sport_slug).order_by(
        Team.full_name).all()
    return render_template('teams_list.html', sport=sport,
                           teams_by_conf=teams_by_conf, all_teams=all_teams)


@app.route('/<sport_slug>/schedule')
def sport_schedule(sport_slug):
    slug_map = {'college-football': 'ncaaf', 'mens-college-basketball': 'ncaam',
                'womens-college-basketball': 'ncaaw'}
    sport_slug = slug_map.get(sport_slug, sport_slug)
    sport = Sport.query.filter_by(slug=sport_slug).first_or_404()
    games = (Game.query.filter_by(sport_slug=sport_slug)
             .order_by(Game.date.desc()).limit(50).all())
    return render_template('schedule.html', sport=sport, games=games)


@app.route('/<sport_slug>/transactions')
def sport_transactions(sport_slug):
    slug_map = {'college-football': 'ncaaf', 'mens-college-basketball': 'ncaam',
                'womens-college-basketball': 'ncaaw'}
    sport_slug = slug_map.get(sport_slug, sport_slug)
    sport = Sport.query.filter_by(slug=sport_slug).first_or_404()
    transactions = (Transaction.query.filter_by(sport_slug=sport_slug)
                    .order_by(Transaction.created_at.desc()).limit(50).all())
    return render_template('transactions.html', sport=sport,
                           transactions=transactions)


@app.route('/nba/bpi')
def nba_bpi():
    sport = Sport.query.filter_by(slug='nba').first_or_404()
    rankings = (PowerIndex.query.filter_by(sport_slug='nba', season='2023-24')
                .order_by(PowerIndex.rank).all())
    return render_template('power_index.html', sport=sport, rankings=rankings,
                           index_name='NBA Basketball Power Index',
                           abbrev='BPI', season='2023-24')


@app.route('/nfl/fpi')
def nfl_fpi():
    sport = Sport.query.filter_by(slug='nfl').first_or_404()
    rankings = (PowerIndex.query.filter_by(sport_slug='nfl', season='2023-24')
                .order_by(PowerIndex.rank).all())
    return render_template('power_index.html', sport=sport, rankings=rankings,
                           index_name='NFL Football Power Index',
                           abbrev='FPI', season='2023-24')


@app.route('/soccer/spi')
def soccer_spi():
    sport = Sport.query.filter_by(slug='soccer').first_or_404()
    rankings = (PowerIndex.query.filter_by(sport_slug='soccer', season='2023-24')
                .order_by(PowerIndex.rank).all())
    return render_template('power_index.html', sport=sport, rankings=rankings,
                           index_name='Soccer Power Index',
                           abbrev='SPI', season='2023-24')


@app.route('/womens-college-basketball/recruiting')
@app.route('/ncaaw/recruiting')
def ncaaw_recruiting():
    sport = Sport.query.filter_by(slug='ncaaw').first_or_404()
    recruits = (Recruit.query.filter_by(sport_slug='ncaaw')
                .order_by(Recruit.rank).all())
    return render_template('recruiting.html', sport=sport, recruits=recruits,
                           gender='Women\'s')


@app.route('/mens-college-basketball/recruiting')
@app.route('/ncaam/recruiting')
def ncaam_recruiting():
    sport = Sport.query.filter_by(slug='ncaam').first_or_404()
    recruits = (Recruit.query.filter_by(sport_slug='ncaam', gender='M')
                .order_by(Recruit.rank).all())
    return render_template('recruiting.html', sport=sport, recruits=recruits,
                           gender='Men\'s')


# ─── Routes: Team Pages ───────────────────────────────────────────────────────

@app.route('/team/<sport_slug>/<team_slug>')
def team_home(sport_slug, team_slug):
    team = Team.query.filter_by(slug=team_slug).first_or_404()
    sport = Sport.query.filter_by(slug=sport_slug).first()
    recent_games = (Game.query.filter(
        (Game.home_team_id == team.id) | (Game.away_team_id == team.id),
        Game.status == 'final'
    ).order_by(Game.date.desc()).limit(5).all())
    upcoming = (Game.query.filter(
        (Game.home_team_id == team.id) | (Game.away_team_id == team.id),
        Game.status == 'scheduled'
    ).order_by(Game.date).limit(3).all())
    news = Article.query.filter(
        Article.tags.ilike(f'%{team.full_name}%')
    ).order_by(Article.created_at.desc()).limit(5).all()
    injuries = Player.query.filter_by(team_id=team.id).filter(
        Player.injury_status != '').all()
    return render_template('team_home.html', team=team, sport=sport,
                           recent_games=recent_games, upcoming=upcoming,
                           news=news, injuries=injuries)


@app.route('/team/<sport_slug>/<team_slug>/roster')
def team_roster(sport_slug, team_slug):
    team = Team.query.filter_by(slug=team_slug).first_or_404()
    sport = Sport.query.filter_by(slug=sport_slug).first()
    players = Player.query.filter_by(team_id=team.id).order_by(
        Player.position, Player.last_name).all()
    return render_template('team_roster.html', team=team, sport=sport,
                           players=players)


@app.route('/team/<sport_slug>/<team_slug>/schedule')
def team_schedule(sport_slug, team_slug):
    team = Team.query.filter_by(slug=team_slug).first_or_404()
    sport = Sport.query.filter_by(slug=sport_slug).first()
    games = (Game.query.filter(
        (Game.home_team_id == team.id) | (Game.away_team_id == team.id)
    ).order_by(Game.date.desc()).limit(40).all())
    next_game = (Game.query.filter(
        (Game.home_team_id == team.id) | (Game.away_team_id == team.id),
        Game.status == 'scheduled'
    ).order_by(Game.date).first())
    return render_template('team_schedule.html', team=team, sport=sport,
                           games=games, next_game=next_game)


@app.route('/team/<sport_slug>/<team_slug>/stats')
def team_stats(sport_slug, team_slug):
    team = Team.query.filter_by(slug=team_slug).first_or_404()
    sport = Sport.query.filter_by(slug=sport_slug).first()
    players = Player.query.filter_by(team_id=team.id).order_by(
        Player.last_name).all()
    player_season_stats = []
    for p in players:
        s = PlayerStat.query.filter_by(player_id=p.id,
                                        season='2023-24',
                                        stat_type='season').first()
        player_season_stats.append((p, s))
    total_gp = len(players)
    return render_template('team_stats.html', team=team, sport=sport,
                           player_season_stats=player_season_stats,
                           total_gp=total_gp)


@app.route('/team/<sport_slug>/<team_slug>/injuries')
def team_injuries(sport_slug, team_slug):
    team = Team.query.filter_by(slug=team_slug).first_or_404()
    sport = Sport.query.filter_by(slug=sport_slug).first()
    players = Player.query.filter_by(team_id=team.id).filter(
        Player.injury_status != '').all()
    return render_template('team_injuries.html', team=team, sport=sport,
                           players=players)


@app.route('/team/<sport_slug>/<team_slug>/transactions')
def team_transactions(sport_slug, team_slug):
    team = Team.query.filter_by(slug=team_slug).first_or_404()
    sport = Sport.query.filter_by(slug=sport_slug).first()
    transactions = (Transaction.query.filter_by(team_id=team.id)
                    .order_by(Transaction.created_at.desc()).limit(30).all())
    return render_template('team_transactions.html', team=team, sport=sport,
                           transactions=transactions)


@app.route('/team/<sport_slug>/<team_slug>/depth-chart')
def team_depth_chart(sport_slug, team_slug):
    team = Team.query.filter_by(slug=team_slug).first_or_404()
    sport = Sport.query.filter_by(slug=sport_slug).first()
    entries = (DepthChartEntry.query.filter_by(team_id=team.id)
               .order_by(DepthChartEntry.position,
                         DepthChartEntry.position_rank).all())
    # Group by position
    by_position = {}
    for entry in entries:
        if entry.position not in by_position:
            by_position[entry.position] = []
        by_position[entry.position].append(entry)
    return render_template('team_depth_chart.html', team=team, sport=sport,
                           by_position=by_position)


# ─── Routes: Player Pages ─────────────────────────────────────────────────────

@app.route('/player/<sport_slug>/<player_slug>')
def player_profile(sport_slug, player_slug):
    player = Player.query.filter_by(slug=player_slug).first_or_404()
    sport = Sport.query.filter_by(slug=sport_slug).first()
    season_stats = PlayerStat.query.filter_by(
        player_id=player.id, season='2023-24', stat_type='season').first()
    career_stats = PlayerStat.query.filter_by(
        player_id=player.id, stat_type='career').first()
    recent_games_stats = (GamePlayerStat.query.filter_by(player_id=player.id)
                          .limit(10).all())
    return render_template('player_profile.html', player=player, sport=sport,
                           season_stats=season_stats, career_stats=career_stats,
                           recent_games_stats=recent_games_stats)


@app.route('/player/<sport_slug>/<player_slug>/gamelog')
def player_gamelog(sport_slug, player_slug):
    player = Player.query.filter_by(slug=player_slug).first_or_404()
    sport = Sport.query.filter_by(slug=sport_slug).first()
    # Order by game date desc so "last N games" reads top-down.
    game_stats = (db.session.query(GamePlayerStat)
                  .join(Game, Game.id == GamePlayerStat.game_id)
                  .filter(GamePlayerStat.player_id == player.id,
                          Game.status == 'final')
                  .order_by(Game.date.desc())
                  .limit(30).all())
    # Build a per-row "opponent / result" view-model so the template can
    # show real game context (needed for soccer, but useful everywhere).
    rows = []
    for gs in game_stats:
        g = Game.query.get(gs.game_id)
        is_home = g and g.home_team_id == player.team_id
        opp = (g.away_team if is_home else g.home_team) if g else None
        team_score = (g.home_score if is_home else g.away_score) if g else None
        opp_score  = (g.away_score if is_home else g.home_score) if g else None
        result = None
        if team_score is not None and opp_score is not None:
            result = 'W' if team_score > opp_score else ('L' if team_score < opp_score else 'D')
        rows.append({
            'gs': gs, 'game': g,
            'opp': opp, 'is_home': is_home,
            'team_score': team_score, 'opp_score': opp_score,
            'result': result,
        })
    return render_template('player_gamelog.html', player=player, sport=sport,
                           game_stats=game_stats, rows=rows)


# ─── Routes: Game Pages ───────────────────────────────────────────────────────

@app.route('/game/<int:game_id>')
def game_detail(game_id):
    game = Game.query.get_or_404(game_id)
    sport = Sport.query.filter_by(slug=game.sport_slug).first()
    home_team = Team.query.get(game.home_team_id)
    away_team = Team.query.get(game.away_team_id)
    home_stats = (GamePlayerStat.query.filter_by(game_id=game.id,
                                                  team_id=home_team.id if home_team else 0)
                  .order_by(GamePlayerStat.points.desc()).all())
    away_stats = (GamePlayerStat.query.filter_by(game_id=game.id,
                                                  team_id=away_team.id if away_team else 0)
                  .order_by(GamePlayerStat.points.desc()).all())
    leaders = game.get_leaders()
    return render_template('game_detail.html', game=game, sport=sport,
                           home_team=home_team, away_team=away_team,
                           home_stats=home_stats, away_stats=away_stats,
                           leaders=leaders)


@app.route('/tickets/<int:game_id>')
def tickets(game_id):
    """Mock ticket-purchase page with deterministic price tiers."""
    game = Game.query.get_or_404(game_id)
    sport = Sport.query.filter_by(slug=game.sport_slug).first()
    home_team = Team.query.get(game.home_team_id)
    away_team = Team.query.get(game.away_team_id)
    # Deterministic tiers by game id so prices are stable across page loads.
    base = 35 + (game.id * 7) % 25
    tiers = [
        {'name': 'Upper Level',     'section': '300-Level',  'price': base},
        {'name': 'Mezzanine',       'section': '200-Level',  'price': base + 45},
        {'name': 'Lower Bowl',      'section': '100-Level',  'price': base + 120},
        {'name': 'Club Level',      'section': 'Club',       'price': base + 240},
        {'name': 'Courtside / Floor','section': 'Floor',     'price': base + 520},
    ]
    return render_template('tickets.html', game=game, sport=sport,
                           home_team=home_team, away_team=away_team,
                           tiers=tiers)


# ─── Routes: Articles ─────────────────────────────────────────────────────────

@app.route('/story/<slug>')
@app.route('/article/<slug>')
def article(slug):
    art = Article.query.filter_by(slug=slug).first_or_404()
    sport = Sport.query.filter_by(slug=art.sport_slug).first()
    related = (Article.query.filter_by(sport_slug=art.sport_slug)
               .filter(Article.id != art.id)
               .order_by(Article.created_at.desc()).limit(4).all())
    return render_template('article.html', article=art, sport=sport,
                           related=related)


# ─── Routes: Search ───────────────────────────────────────────────────────────

@app.route('/search')
@app.route('/search/_/q/<path:espn_query>')
def search(espn_query=''):
    q = (espn_query or request.args.get('q', '')).strip()
    sport_filter = request.args.get('sport', '')
    type_filter = request.args.get('type', '')  # teams, players, articles

    teams = []
    players = []
    articles_list = []

    if q:
        tokens = [t.lower() for t in re.findall(r'[a-z0-9]+', q.lower())
                  if t not in STOPWORDS and len(t) >= 2]
        min_req = max(1, len(tokens) // 2) if tokens else 1

        # Search teams
        if not type_filter or type_filter == 'teams':
            all_teams = Team.query
            if sport_filter:
                all_teams = all_teams.filter_by(sport_slug=sport_filter)
            scored_teams = [(s, t) for t in all_teams.all()
                            if (s := _score_team(t, tokens)) >= min_req]
            scored_teams.sort(key=lambda x: -x[0])
            teams = [t for _, t in scored_teams[:20]]

        # Search players
        if not type_filter or type_filter == 'players':
            all_players = Player.query
            if sport_filter:
                all_players = all_players.filter_by(sport_slug=sport_filter)
            scored_players = [(s, p) for p in all_players.all()
                              if (s := _score_player(p, tokens)) >= min_req]
            scored_players.sort(key=lambda x: -x[0])
            players = [p for _, p in scored_players[:20]]

        # Search articles
        if not type_filter or type_filter == 'articles':
            all_articles = Article.query
            if sport_filter:
                all_articles = all_articles.filter_by(sport_slug=sport_filter)
            scored_articles = [(s, a) for a in all_articles.all()
                               if (s := _score_article(a, tokens)) >= min_req]
            scored_articles.sort(key=lambda x: -x[0])
            articles_list = [a for _, a in scored_articles[:20]]

    sports = Sport.query.filter_by(is_active=True).order_by(Sport.nav_order).all()
    return render_template('search.html', query=q, teams=teams,
                           players=players, articles=articles_list,
                           sports=sports, sport_filter=sport_filter,
                           type_filter=type_filter)


# ─── Routes: Auth ─────────────────────────────────────────────────────────────

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
        flash(f'Welcome to ESPN, {user.first_name}!', 'success')
        return redirect(url_for('index'))
    return render_template('register.html', form=form)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))


# ─── Routes: Account ──────────────────────────────────────────────────────────

@app.route('/account')
@login_required
def account():
    favorites = UserFavorite.query.filter_by(user_id=current_user.id).all()
    fav_teams = []
    fav_players = []
    for fav in favorites:
        if fav.item_type == 'team':
            t = Team.query.get(fav.item_id)
            if t:
                fav_teams.append((fav.id, t))
        elif fav.item_type == 'player':
            p = Player.query.get(fav.item_id)
            if p:
                fav_players.append((fav.id, p))
    return render_template('account.html', fav_teams=fav_teams,
                           fav_players=fav_players)


@app.route('/account/edit', methods=['GET', 'POST'])
@login_required
def account_edit():
    form = ProfileForm(obj=current_user)
    if form.validate_on_submit():
        current_user.name = form.name.data
        current_user.phone = form.phone.data
        db.session.commit()
        flash('Profile updated.', 'success')
        return redirect(url_for('account'))
    return render_template('account_edit.html', form=form)


@app.route('/account/password', methods=['GET', 'POST'])
@login_required
def account_password():
    form = PasswordForm()
    if form.validate_on_submit():
        if not current_user.check_password(form.current_password.data):
            flash('Current password is incorrect.', 'danger')
            return render_template('account_password.html', form=form)
        current_user.set_password(form.new_password.data)
        db.session.commit()
        flash('Password changed successfully.', 'success')
        return redirect(url_for('account'))
    return render_template('account_password.html', form=form)


@app.route('/account/delete', methods=['POST'])
@login_required
def account_delete():
    user = User.query.get(current_user.id)
    logout_user()
    db.session.delete(user)
    db.session.commit()
    flash('Your account has been deleted.', 'info')
    return redirect(url_for('index'))


# ─── Routes: Favorites API ────────────────────────────────────────────────────

@csrf.exempt
@app.route('/api/favorites/toggle', methods=['POST'])
def api_favorite_toggle():
    if not current_user.is_authenticated:
        return jsonify({'success': False, 'message': 'Login required'}), 401
    # Support both JSON (legacy) and form POST
    if request.is_json:
        data = request.get_json() or {}
    else:
        data = request.form
    item_type = data.get('type', 'team')
    item_id = int(data.get('id', 0))
    existing = UserFavorite.query.filter_by(
        user_id=current_user.id, item_type=item_type, item_id=item_id).first()
    if existing:
        db.session.delete(existing)
        db.session.commit()
        action = 'removed'
    else:
        fav = UserFavorite(user_id=current_user.id, item_type=item_type,
                           item_id=item_id)
        db.session.add(fav)
        db.session.commit()
        action = 'added'
    # If form POST, redirect back; if JSON, return JSON
    if not request.is_json:
        next_url = data.get('next') or request.referrer or url_for('account')
        flash(f'{"Added to" if action == "added" else "Removed from"} favorites.', 'success')
        return redirect(next_url)
    return jsonify({'success': True, 'action': action})


# ─── Routes: Stats Leaders ────────────────────────────────────────────────────

@app.route('/nba/stats/leaders')
@app.route('/nba/players')
def nba_stat_leaders():
    sport = Sport.query.filter_by(slug='nba').first_or_404()
    stat = request.args.get('stat', 'points')
    season = request.args.get('season', '2023-24')
    conf_filter = request.args.get('conference', '')

    # Get all NBA player stats
    stats_q = (db.session.query(Player, PlayerStat)
               .join(PlayerStat, Player.id == PlayerStat.player_id)
               .filter(Player.sport_slug == 'nba',
                       PlayerStat.season == season,
                       PlayerStat.stat_type == 'season'))

    if conf_filter:
        stats_q = stats_q.join(Team, Player.team_id == Team.id).join(
            Conference, Team.conference_id == Conference.id).filter(
            Conference.name.ilike(f'%{conf_filter}%'))

    all_stats = stats_q.all()

    sort_map = {
        'points': lambda x: x[1].points_per_game,
        'rebounds': lambda x: x[1].rebounds_per_game,
        'assists': lambda x: x[1].assists_per_game,
        'steals': lambda x: x[1].steals_per_game,
        'blocks': lambda x: x[1].blocks_per_game,
    }
    sort_fn = sort_map.get(stat, sort_map['points'])
    all_stats.sort(key=sort_fn, reverse=True)
    leaders = all_stats[:25]

    return render_template('stat_leaders.html', sport=sport, leaders=leaders,
                           stat=stat, season=season, conf_filter=conf_filter)


@app.route('/nba/statistics')
def nba_statistics():
    return redirect(url_for('nba_stat_leaders'))


# ─── Routes: Stats Pages ──────────────────────────────────────────────────────

@app.route('/<sport_slug>/statistics')
@app.route('/<sport_slug>/stats')
def sport_stats(sport_slug):
    slug_map = {'college-football': 'ncaaf', 'mens-college-basketball': 'ncaam',
                'womens-college-basketball': 'ncaaw'}
    sport_slug = slug_map.get(sport_slug, sport_slug)
    sport = Sport.query.filter_by(slug=sport_slug).first_or_404()
    stat = request.args.get('stat', 'points')
    season = request.args.get('season', '2023-24')
    conf_filter = request.args.get('conference', '').strip()

    stats_q = (db.session.query(Player, PlayerStat)
               .join(PlayerStat, Player.id == PlayerStat.player_id)
               .filter(Player.sport_slug == sport_slug,
                       PlayerStat.season == season,
                       PlayerStat.stat_type == 'season'))
    if conf_filter:
        stats_q = (stats_q
                   .join(Team, Player.team_id == Team.id)
                   .join(Conference, Team.conference_id == Conference.id)
                   .filter(Conference.name.ilike(f'%{conf_filter}%')))
    all_stats = stats_q.all()

    if sport_slug in ('nba', 'ncaam', 'ncaaw'):
        sort_map = {'points': lambda x: x[1].points_per_game,
                    'rebounds': lambda x: x[1].rebounds_per_game,
                    'assists': lambda x: x[1].assists_per_game,
                    'steals': lambda x: x[1].steals_per_game,
                    'blocks': lambda x: x[1].blocks_per_game}
    elif sport_slug in ('nfl',):
        sort_map = {'passing': lambda x: x[1].passing_yards,
                    'rushing': lambda x: x[1].rushing_yards,
                    'receiving': lambda x: x[1].receiving_yards}
    else:
        sort_map = {'points': lambda x: x[1].points_per_game}
    sort_fn = sort_map.get(stat, next(iter(sort_map.values())))
    all_stats.sort(key=sort_fn, reverse=True)
    leaders = all_stats[:25]
    return render_template('stat_leaders.html', sport=sport, leaders=leaders,
                           stat=stat, season=season, conf_filter=conf_filter)


# ─── R3 Routes: Betting / Odds ───────────────────────────────────────────────

SPORT_SLUG_NORM = {
    'college-football': 'ncaaf',
    'mens-college-basketball': 'ncaam',
    'womens-college-basketball': 'ncaaw',
    'ncaa': 'ncaam',
}


def _norm_sport(sport_slug: str) -> str:
    return SPORT_SLUG_NORM.get(sport_slug, sport_slug)


def _team_lookup(team_ids):
    """Return {id: Team} for the given iterable of team ids."""
    if not team_ids:
        return {}
    return {t.id: t for t in Team.query.filter(Team.id.in_(team_ids)).all()}


@app.route('/bet')
@app.route('/bet/')
@app.route('/espn-bet')
def espn_bet_hub():
    """ESPN BET hub — featured odds across the top sports."""
    sports_with_odds = ['nba', 'nfl', 'mlb', 'nhl', 'soccer']
    cards = []
    for sl in sports_with_odds:
        sport = Sport.query.filter_by(slug=sl).first()
        if not sport:
            continue
        odds = (BettingOdds.query.filter_by(sport_slug=sl, status='open')
                .order_by(BettingOdds.id).limit(4).all())
        if not odds:
            odds = (BettingOdds.query.filter_by(sport_slug=sl)
                    .order_by(BettingOdds.id.desc()).limit(4).all())
        # Attach game + teams
        attached = []
        game_ids = [o.game_id for o in odds]
        games = {g.id: g for g in Game.query.filter(Game.id.in_(game_ids)).all()}
        team_ids = set()
        for g in games.values():
            team_ids.add(g.home_team_id)
            team_ids.add(g.away_team_id)
        teams = _team_lookup(team_ids)
        for o in odds:
            g = games.get(o.game_id)
            if not g:
                continue
            attached.append({
                'odds': o, 'game': g,
                'home_team': teams.get(g.home_team_id),
                'away_team': teams.get(g.away_team_id),
            })
        cards.append({'sport': sport, 'lines': attached})
    return render_template('bet_hub.html', cards=cards)


@app.route('/<sport_slug>/odds')
@app.route('/<sport_slug>/betting')
def sport_odds(sport_slug):
    sport_slug = _norm_sport(sport_slug)
    sport = Sport.query.filter_by(slug=sport_slug).first_or_404()
    status_filter = request.args.get('status', '').strip()
    q = BettingOdds.query.filter_by(sport_slug=sport_slug)
    if status_filter in ('open', 'closed'):
        q = q.filter_by(status=status_filter)
    odds_rows = q.order_by(BettingOdds.id).all()
    games = {}
    if odds_rows:
        gids = [o.game_id for o in odds_rows]
        games = {g.id: g for g in Game.query.filter(Game.id.in_(gids)).all()}
    team_ids = set()
    for g in games.values():
        team_ids.add(g.home_team_id)
        team_ids.add(g.away_team_id)
    teams = _team_lookup(team_ids)
    rows = []
    for o in odds_rows:
        g = games.get(o.game_id)
        if not g:
            continue
        rows.append({
            'odds': o, 'game': g,
            'home_team': teams.get(g.home_team_id),
            'away_team': teams.get(g.away_team_id),
        })
    return render_template('odds.html', sport=sport, rows=rows,
                           status_filter=status_filter)


# ─── R3 Routes: Awards ───────────────────────────────────────────────────────

@app.route('/<sport_slug>/awards')
@app.route('/awards/<sport_slug>')  # R5 alias — accept either path order
def sport_awards(sport_slug):
    sport_slug = _norm_sport(sport_slug)
    sport = Sport.query.filter_by(slug=sport_slug).first_or_404()
    season = request.args.get('season', '').strip()
    q = Award.query.filter_by(sport_slug=sport_slug)
    if season:
        q = q.filter_by(season=season)
    awards = q.order_by(Award.season.desc(), Award.id).all()
    # Attach winner player and team
    pids = [a.winner_player_id for a in awards if a.winner_player_id]
    tids = [a.winner_team_id for a in awards if a.winner_team_id]
    players = {p.id: p for p in Player.query.filter(Player.id.in_(pids)).all()}
    teams = {t.id: t for t in Team.query.filter(Team.id.in_(tids)).all()}
    seasons = sorted({a.season for a in Award.query.filter_by(
        sport_slug=sport_slug).all()}, reverse=True)
    return render_template('awards.html', sport=sport, awards=awards,
                           players=players, teams=teams, seasons=seasons,
                           season=season)


@app.route('/awards')
def awards_hub():
    """All-sport awards index."""
    sports = (Sport.query.filter_by(is_active=True)
              .order_by(Sport.nav_order).all())
    sports = [s for s in sports if not (s.slug or '').startswith('_')]
    sport_awards_map = {}
    for sp in sports:
        latest = (Award.query.filter_by(sport_slug=sp.slug)
                  .order_by(Award.season.desc(), Award.id).limit(3).all())
        if latest:
            sport_awards_map[sp.slug] = (sp, latest)
    return render_template('awards_hub.html',
                           sport_awards_map=sport_awards_map)


# ─── R3 Routes: Draft ────────────────────────────────────────────────────────

@app.route('/<sport_slug>/draft')
@app.route('/draft/<sport_slug>')
def sport_draft(sport_slug):
    sport_slug = _norm_sport(sport_slug)
    sport = Sport.query.filter_by(slug=sport_slug).first_or_404()
    season = request.args.get('season', '2024').strip()
    round_n = request.args.get('round', type=int)
    q = DraftPick.query.filter_by(sport_slug=sport_slug, season=season)
    if round_n:
        q = q.filter_by(round=round_n)
    picks = q.order_by(DraftPick.overall_pick).all()
    tids = [p.team_id for p in picks if p.team_id]
    teams = {t.id: t for t in Team.query.filter(Team.id.in_(tids)).all()}
    seasons = sorted({p.season for p in DraftPick.query.filter_by(
        sport_slug=sport_slug).all()}, reverse=True)
    is_mock = any(p.is_mock for p in picks)
    return render_template('draft.html', sport=sport, picks=picks,
                           teams=teams, seasons=seasons, season=season,
                           round_n=round_n, is_mock=is_mock)


# ─── R3 Routes: Fantasy ──────────────────────────────────────────────────────

@app.route('/fantasy')
@app.route('/fantasy/')
def fantasy_hub():
    fan_articles = (Article.query.filter_by(sport_slug='fantasy')
                    .order_by(Article.created_at.desc()).limit(15).all())
    podcasts = Podcast.query.filter_by(sport_slug='fantasy').all()
    sport_links = [
        ('football', 'Fantasy Football', '/fantasy/football'),
        ('basketball', 'Fantasy Basketball', '/fantasy/basketball'),
        ('baseball', 'Fantasy Baseball', '/fantasy/baseball'),
        ('hockey', 'Fantasy Hockey', '/fantasy/hockey'),
    ]
    return render_template('fantasy_hub.html',
                           fan_articles=fan_articles,
                           podcasts=podcasts,
                           sport_links=sport_links)


FANTASY_SLUG_MAP = {
    'football': 'nfl', 'nfl': 'nfl',
    'basketball': 'nba', 'nba': 'nba',
    'baseball': 'mlb', 'mlb': 'mlb',
    'hockey': 'nhl', 'nhl': 'nhl',
}


@app.route('/fantasy/<sport_slug>')
def fantasy_sport(sport_slug):
    """Fantasy hub for a specific sport — top players + waiver list + tips."""
    canonical = FANTASY_SLUG_MAP.get(sport_slug)
    if not canonical:
        abort(404)
    sport = Sport.query.filter_by(slug=canonical).first_or_404()
    # Top fantasy players: sort by points_per_game / passing_yards / etc
    season = '2023-24' if canonical in ('nba', 'nhl') else '2023'
    stats_q = (db.session.query(Player, PlayerStat)
               .join(PlayerStat, Player.id == PlayerStat.player_id)
               .filter(Player.sport_slug == canonical,
                       PlayerStat.season == season,
                       PlayerStat.stat_type == 'season'))
    all_stats = stats_q.all()

    def fpts(item):
        _, st = item
        if canonical == 'nba':
            return (st.points_per_game * 1.0 +
                    st.rebounds_per_game * 1.2 +
                    st.assists_per_game * 1.5 +
                    st.steals_per_game * 3 +
                    st.blocks_per_game * 3)
        if canonical == 'nfl':
            return ((st.passing_yards or 0) * 0.04 +
                    (st.passing_tds or 0) * 4 +
                    (st.rushing_yards or 0) * 0.1 +
                    (st.receiving_yards or 0) * 0.1 +
                    (st.rushing_tds or 0) * 6 +
                    (st.receiving_tds or 0) * 6 +
                    (st.receptions or 0) * 0.5)
        if canonical == 'mlb':
            return ((st.home_runs or 0) * 4 + (st.rbi or 0) * 1 +
                    (st.batting_avg or 0) * 200 + (st.stolen_bases or 0) * 2)
        if canonical == 'nhl':
            return ((st.goals or 0) * 3 + (st.hockey_assists or 0) * 2 +
                    (st.plus_minus or 0) * 0.5)
        return 0

    all_stats.sort(key=fpts, reverse=True)
    top = all_stats[:30]
    waiver = all_stats[30:60]
    articles = (Article.query
                .filter((Article.sport_slug == canonical) |
                        (Article.sport_slug == 'fantasy'))
                .filter(Article.tags.like('%Fantasy%') |
                        (Article.sport_slug == 'fantasy'))
                .order_by(Article.created_at.desc()).limit(10).all())
    return render_template('fantasy_sport.html', sport=sport,
                           canonical=canonical, top=top, waiver=waiver,
                           articles=articles, season=season)


# ─── R3 Routes: Podcasts ─────────────────────────────────────────────────────

@app.route('/podcasts')
@app.route('/podcasts/')
def podcasts_index():
    sport_filter = request.args.get('sport', '').strip()
    q = Podcast.query
    if sport_filter:
        q = q.filter_by(sport_slug=sport_filter)
    podcasts = q.order_by(Podcast.id).all()
    return render_template('podcasts.html', podcasts=podcasts,
                           sport_filter=sport_filter)


@app.route('/podcast/<slug>')
def podcast_detail(slug):
    pod = Podcast.query.filter_by(slug=slug).first_or_404()
    related = (Podcast.query.filter_by(sport_slug=pod.sport_slug)
               .filter(Podcast.id != pod.id).limit(4).all())
    return render_template('podcast_detail.html', podcast=pod,
                           related=related)


# ─── R3 Routes: Conference-filtered standings ────────────────────────────────

@app.route('/<sport_slug>/standings/<conf_slug>')
def standings_by_conf(sport_slug, conf_slug):
    sport_slug = _norm_sport(sport_slug)
    sport = Sport.query.filter_by(slug=sport_slug).first_or_404()
    # Map nice URL slugs to conference name fragments
    conf_aliases = {
        'east': 'East', 'eastern': 'East',
        'west': 'West', 'western': 'West',
        'al': 'American', 'american': 'American',
        'nl': 'National', 'national': 'National',
        'afc': 'AFC', 'nfc': 'NFC',
        'epl': 'Premier', 'premier-league': 'Premier',
    }
    target = conf_aliases.get(conf_slug.lower(), conf_slug)
    conf = (Conference.query.filter_by(sport_slug=sport_slug)
            .filter(Conference.name.ilike(f'%{target}%')).first())
    if not conf:
        abort(404)
    divs = Division.query.filter_by(conference_id=conf.id).all()
    divisions_data = []
    if divs:
        for d in divs:
            teams = (Team.query.filter_by(division_id=d.id)
                     .order_by(Team.standing_rank).all())
            divisions_data.append({'division': d, 'teams': teams})
    else:
        teams = (Team.query.filter_by(conference_id=conf.id)
                 .order_by(Team.standing_rank).all())
        divisions_data.append({'division': None, 'teams': teams})
    all_teams = [t for d in divisions_data for t in d['teams']]
    return render_template('standings_conf.html', sport=sport, conf=conf,
                           divisions_data=divisions_data,
                           all_teams=all_teams, conf_slug=conf_slug)


# ─── R3 Routes: Live scores alias ────────────────────────────────────────────

@app.route('/<sport_slug>/live')
@app.route('/<sport_slug>/live-scores')
def sport_live(sport_slug):
    sport_slug = _norm_sport(sport_slug)
    sport = Sport.query.filter_by(slug=sport_slug).first_or_404()
    # 'Live' on a date-pinned mirror = games scheduled for today + the most
    # recent finals (so the page is never empty).
    today = mirror_today().strftime('%Y-%m-%d')
    today_games = (Game.query.filter_by(sport_slug=sport_slug)
                   .filter(Game.date == today).all())
    upcoming = get_upcoming_games(sport_slug, 8)
    recent = get_recent_scores(sport_slug, 8)
    return render_template('live_scores.html', sport=sport,
                           today_games=today_games,
                           upcoming=upcoming, recent=recent)


# ─── R4 Routes: Play-by-play ─────────────────────────────────────────────────

@app.route('/<sport_slug>/play-by-play/<int:game_id>')
@app.route('/playbyplay/<int:game_id>')
def play_by_play(sport_slug=None, game_id=None):
    game = Game.query.get_or_404(game_id)
    if sport_slug:
        sport_slug = _norm_sport(sport_slug)
    sport = Sport.query.filter_by(slug=sport_slug or game.sport_slug).first()
    home_team = Team.query.get(game.home_team_id) if game.home_team_id else None
    away_team = Team.query.get(game.away_team_id) if game.away_team_id else None
    events = (PlayByPlay.query.filter_by(game_id=game_id)
              .order_by(PlayByPlay.sequence).all())
    return render_template('play_by_play.html', game=game, sport=sport,
                           home_team=home_team, away_team=away_team,
                           events=events)


# ─── R4 Routes: Fantasy trade analyzer / waiver wire ─────────────────────────

@app.route('/fantasy/<sport_slug>/trade-analyzer')
def fantasy_trade_analyzer(sport_slug):
    sport_slug = _norm_sport(sport_slug)
    sport = Sport.query.filter_by(slug=sport_slug).first_or_404()
    candidates = (Player.query.filter_by(sport_slug=sport_slug)
                  .order_by(Player.id).limit(40).all())
    return render_template('trade_analyzer.html', sport=sport,
                           candidates=candidates)


@app.route('/fantasy/<sport_slug>/waiver-wire')
def fantasy_waiver_wire(sport_slug):
    sport_slug = _norm_sport(sport_slug)
    sport = Sport.query.filter_by(slug=sport_slug).first_or_404()
    # Lowest-ownership stat-bearing players
    stats = (PlayerStat.query.filter_by(stat_type='season')
             .order_by(PlayerStat.id.desc()).limit(80).all())
    rows = []
    for st in stats:
        p = Player.query.get(st.player_id)
        if p and p.sport_slug == sport_slug:
            rows.append((p, st))
        if len(rows) >= 40:
            break
    return render_template('waiver_wire.html', sport=sport, rows=rows)


# ─── R4 Routes: Bet parlay-builder ───────────────────────────────────────────

@app.route('/bet/parlay-builder')
@app.route('/bet/parlay-builder/')
def parlay_builder():
    featured = Parlay.query.filter_by(is_featured=1).order_by(Parlay.id).all()
    all_parlays = Parlay.query.order_by(Parlay.id).all()
    return render_template('parlay_builder.html',
                           featured=featured, all_parlays=all_parlays)


# ─── R4 Routes: Recruiting 247composite ──────────────────────────────────────

@app.route('/recruiting/<sport_slug>/247-composite')
@app.route('/<sport_slug>/recruiting/247-composite')
@app.route('/recruiting/<sport_slug>')  # R5 alias — redirect to 247-composite
@app.route('/<sport_slug>/recruiting')  # R5 alias for ncaaf/etc.
def recruiting_247(sport_slug):
    sport_slug = _norm_sport(sport_slug)
    sport = Sport.query.filter_by(slug=sport_slug).first_or_404()
    recruits = (Recruit.query.filter_by(sport_slug=sport_slug)
                .order_by(Recruit.rank).all())
    return render_template('composite_247.html', sport=sport, recruits=recruits)


# ─── R4 Routes: Awards by year + all-time ────────────────────────────────────

@app.route('/<sport_slug>/awards/<year>')
def awards_by_year(sport_slug, year):
    sport_slug = _norm_sport(sport_slug)
    sport = Sport.query.filter_by(slug=sport_slug).first_or_404()
    # Match either '2023' or '2023-24' season strings
    awards = (Award.query.filter_by(sport_slug=sport_slug)
              .filter(Award.season.like(f'%{year}%'))
              .order_by(Award.id).all())
    if not awards:
        abort(404)
    return render_template('awards_year.html', sport=sport,
                           awards=awards, year=year)


@app.route('/<sport_slug>/all-time')
def all_time_leaders(sport_slug):
    sport_slug = _norm_sport(sport_slug)
    sport = Sport.query.filter_by(slug=sport_slug).first_or_404()
    # Pull stat-bearing seasons; show top 30 by a sport-specific key.
    stats = (PlayerStat.query.filter_by(stat_type='season').all())
    enriched = []
    for st in stats:
        p = Player.query.get(st.player_id)
        if not p or p.sport_slug != sport_slug:
            continue
        if sport_slug == 'nba':
            key = st.points_per_game or 0
        elif sport_slug == 'nfl':
            key = (st.passing_yards or 0) + (st.rushing_yards or 0) * 1.5
        elif sport_slug == 'mlb':
            key = (st.home_runs or 0) * 4 + (st.rbi or 0)
        elif sport_slug == 'nhl':
            key = st.hockey_points or 0
        elif sport_slug == 'soccer':
            key = (st.soccer_goals or 0) * 2 + (st.soccer_assists or 0)
        else:
            key = 0
        enriched.append((key, p, st))
    enriched.sort(key=lambda r: r[0], reverse=True)
    enriched = enriched[:30]
    return render_template('all_time.html', sport=sport, leaders=enriched)


# ─── R4 Routes: Watch list (ESPN+) ───────────────────────────────────────────

@app.route('/watch/list')
@app.route('/watch/list/')
def watch_list():
    items = (Watchable.query.order_by(Watchable.is_live.desc(),
                                      Watchable.id).all())
    sport_filter = request.args.get('sport', '').strip()
    kind_filter = request.args.get('kind', '').strip()
    if sport_filter:
        items = [w for w in items if w.sport_slug == sport_filter]
    if kind_filter:
        items = [w for w in items if w.kind == kind_filter]
    return render_template('watch_list.html', items=items,
                           sport_filter=sport_filter, kind_filter=kind_filter)


@app.route('/watch/list/add', methods=['POST', 'GET'])
def watch_list_add():
    slug = (request.values.get('slug') or '').strip()
    show = Watchable.query.filter_by(slug=slug).first()
    if not show:
        flash('Show not found.', 'error')
        return redirect(url_for('watch_list'))
    # Store in session list (no DB write — keeps seed deterministic)
    saved = session.get('watch_list', [])
    if slug not in saved:
        saved.append(slug)
        session['watch_list'] = saved
        flash(f'Added "{show.title}" to your Watch List.', 'success')
    else:
        flash(f'"{show.title}" is already on your Watch List.', 'info')
    return redirect(url_for('watch_show', slug=slug))


@app.route('/watch/<slug>')
def watch_show(slug):
    show = Watchable.query.filter_by(slug=slug).first_or_404()
    related = (Watchable.query.filter_by(sport_slug=show.sport_slug)
               .filter(Watchable.id != show.id).limit(6).all())
    saved = session.get('watch_list', [])
    return render_template('watch_show.html', show=show, related=related,
                           on_watch_list=(slug in saved))


# ─── R4 Routes: Podcast transcript search ────────────────────────────────────

@app.route('/podcasts/search')
def podcasts_search():
    q = (request.args.get('q', '') or '').strip().lower()
    if not q:
        return render_template('podcasts.html',
                               podcasts=[], sport_filter='', search_q='')
    tokens = [t for t in q.split() if t]
    matches = []
    for pod in Podcast.query.order_by(Podcast.id).all():
        hay = ' '.join([
            (pod.title or '').lower(),
            (pod.host or '').lower(),
            (pod.description or '').lower(),
            (pod.latest_episode_title or '').lower(),
        ])
        if all(tok in hay for tok in tokens):
            matches.append(pod)
    return render_template('podcasts.html', podcasts=matches,
                           sport_filter='', search_q=q)


# ─── R7 Routes: SEO infrastructure (robots, sitemap, RSS) ────────────────────

@app.route('/robots.txt')
def robots_txt():
    body = (
        "User-agent: *\n"
        "Allow: /\n"
        "Disallow: /account\n"
        "Disallow: /account/\n"
        "Disallow: /api/\n"
        "Disallow: /login\n"
        "Disallow: /register\n"
        "Disallow: /logout\n"
        "Disallow: /webhook/\n"
        "Disallow: /api/telemetry\n"
        "Sitemap: /sitemap.xml\n"
    )
    return app.response_class(body, mimetype='text/plain')


@app.route('/sitemap.xml')
def sitemap_xml():
    """XML sitemap covering games, articles, podcasts, watch shows."""
    parts = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    # Home + key landing pages.
    for path in ['/', '/scores', '/bet', '/fantasy', '/podcasts',
                 '/watch', '/espnplus', '/awards', '/espn-deportes/',
                 '/stat-glossary', '/developer', '/help/keyboard',
                 '/healthz']:
        parts.append(f'  <url><loc>{path}</loc></url>')
    # Sport landing pages.
    for sp in Sport.query.filter(Sport.is_active == True).order_by(Sport.nav_order).all():  # noqa: E712
        parts.append(f'  <url><loc>{sp.url_prefix}</loc></url>')
        parts.append(f'  <url><loc>{sp.url_prefix}scoreboard</loc></url>')
        parts.append(f'  <url><loc>{sp.url_prefix}standings</loc></url>')
        parts.append(f'  <url><loc>{sp.url_prefix}news</loc></url>')
        parts.append(f'  <url><loc>/rss/{sp.slug}.xml</loc></url>')
    # Articles (cap at 2000 entries to keep XML lean).
    for a in Article.query.order_by(Article.id.desc()).limit(2000).all():
        last = (a.published_date or '').replace(' ', 'T') or '2025-01-01'
        parts.append(f'  <url><loc>/article/{a.slug}</loc>'
                     f'<lastmod>{last[:10]}</lastmod></url>')
    # Games (most recent 1500).
    for g in Game.query.order_by(Game.id.desc()).limit(1500).all():
        parts.append(f'  <url><loc>/game/{g.id}</loc>'
                     f'<lastmod>{g.date or "2025-01-01"}</lastmod></url>')
    # Podcasts.
    for p in Podcast.query.order_by(Podcast.id).all():
        parts.append(f'  <url><loc>/podcast/{p.slug}</loc></url>')
    parts.append('</urlset>')
    return app.response_class('\n'.join(parts),
                              mimetype='application/xml')


@app.route('/rss/<sport_slug>.xml')
def rss_feed(sport_slug):
    """Per-sport RSS feed of recent articles."""
    sport_slug = _norm_sport(sport_slug)
    sport = Sport.query.filter_by(slug=sport_slug).first_or_404()
    arts = (Article.query.filter_by(sport_slug=sport_slug)
            .order_by(Article.created_at.desc()).limit(40).all())
    title = f'ESPN {sport.display_name or sport.name} — Latest'
    items_xml = []
    for a in arts:
        pub = a.published_date or '2025-01-01'
        # crude HTML-strip via Jinja-safe escape on body excerpt
        excerpt = (a.body or '')[:280].replace('<', '&lt;').replace('>', '&gt;')
        items_xml.append(
            f'  <item>'
            f'<title>{(a.title or "").replace("&", "&amp;")}</title>'
            f'<link>/article/{a.slug}</link>'
            f'<guid>/article/{a.slug}</guid>'
            f'<pubDate>{pub}</pubDate>'
            f'<author>{a.author or "ESPN Staff"}</author>'
            f'<description>{excerpt}</description>'
            f'</item>')
    rss = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<rss version="2.0">\n'
        f'  <channel>\n    <title>{title}</title>\n'
        f'    <link>/{sport_slug}/news</link>\n'
        f'    <description>{title}</description>\n'
        + '\n'.join(items_xml) +
        '\n  </channel>\n</rss>'
    )
    return app.response_class(rss, mimetype='application/rss+xml')


# ─── R7 Routes: ESPN Deportes (Spanish locale) ───────────────────────────────

@app.route('/espn-deportes')
@app.route('/espn-deportes/')
@app.route('/deportes')
@app.route('/deportes/')
def espn_deportes():
    """Spanish-language landing page — articles tagged 'es'."""
    es_articles = (Article.query
                   .filter(Article.slug.like('es-%'))
                   .order_by(Article.created_at.desc()).limit(40).all())
    es_by_sport = {}
    for a in es_articles:
        es_by_sport.setdefault(a.sport_slug, []).append(a)
    return render_template('espn_deportes.html',
                           es_articles=es_articles,
                           es_by_sport=es_by_sport,
                           locale='es')


@app.route('/espn-deportes/<sport_slug>')
@app.route('/deportes/<sport_slug>')
def espn_deportes_sport(sport_slug):
    sport_slug = _norm_sport(sport_slug)
    sport = Sport.query.filter_by(slug=sport_slug).first_or_404()
    es_articles = (Article.query
                   .filter(Article.slug.like('es-%'))
                   .filter_by(sport_slug=sport_slug)
                   .order_by(Article.created_at.desc()).limit(40).all())
    return render_template('espn_deportes.html',
                           es_articles=es_articles,
                           es_by_sport={sport_slug: es_articles},
                           current_sport=sport,
                           locale='es')


# ─── R8: Observability + Developer surface ───────────────────────────────────
#
# These endpoints are intentionally simple, deterministic, and side-effect
# free so WebTau tasks can probe them without mutating real state. None of
# them read or write the seeded DB outside of read-only counts.

@app.route('/healthz')
def healthz():
    """Liveness probe — also accepts the legacy `/health` path."""
    payload = {
        'status': 'ok',
        'service': 'espn-mirror',
        'r8_marker_present': bool(Sport.query.filter_by(
            slug='_r8_marker').first()),
        'mirror_today': mirror_today().isoformat(),
    }
    return jsonify(payload)


@app.route('/health')
def health_alias():
    return redirect(url_for('healthz'), code=301)


@app.route('/api/uptime')
def api_uptime():
    """Mirror-clock-based uptime in seconds since R1 cutover."""
    delta = (mirror_now() - datetime(2024, 4, 1, 0, 0, 0))
    return jsonify({
        'mirror_today': mirror_today().isoformat(),
        'r1_cutover': '2024-04-01T00:00:00',
        'seconds_since_cutover': int(delta.total_seconds()),
        'human': f'{int(delta.total_seconds() // 86400)} days',
    })


@app.route('/api/events')
def api_events():
    """Recent observable events — read-only summary derived from the DB."""
    limit = max(1, min(int(request.args.get('limit', 25)), 100))
    arts = (Article.query.order_by(Article.id.desc()).limit(limit).all())
    out = []
    for a in arts:
        out.append({
            'type': 'article.published',
            'id': a.id,
            'slug': a.slug,
            'title': a.title,
            'sport_slug': a.sport_slug,
            'published_date': a.published_date,
        })
    return jsonify({'events': out, 'count': len(out)})


@app.route('/webhook/score-update', methods=['POST', 'GET'])
@csrf.exempt
def webhook_score_update():
    """Score-update webhook — accepts JSON, echoes a deterministic ack.
    Idempotent: same payload always produces the same ack id."""
    if request.method == 'GET':
        return jsonify({
            'endpoint': '/webhook/score-update',
            'methods': ['POST'],
            'expects': {
                'game_id': 'int',
                'home_score': 'int',
                'away_score': 'int',
                'period': 'string (optional)',
            },
            'returns': {'ack_id': 'sha1-derived', 'received': 'bool'},
        })
    payload = request.get_json(silent=True) or request.form.to_dict()
    seed = json.dumps(payload, sort_keys=True)
    import hashlib
    ack_id = hashlib.sha1(seed.encode()).hexdigest()[:16]
    return jsonify({
        'received': True,
        'ack_id': ack_id,
        'echo': payload,
        'note': 'Mirror webhook — payload is not persisted.',
    })


@app.route('/api/v3-graphql', methods=['GET', 'POST'])
@csrf.exempt
def api_v3_graphql():
    """Tiny GraphQL-ish endpoint — supports two introspection queries
    plus three named selections (game, article, team)."""
    if request.method == 'GET':
        return jsonify({
            'endpoint': '/api/v3-graphql',
            'version': 'v3',
            'protocol': 'graphql-min',
            'queries': ['__schema', 'game(id)', 'article(slug)',
                        'team(slug)'],
            'note': 'POST {"query": "..."} or use query string ?q=team(...)',
        })
    body = request.get_json(silent=True) or {}
    q = (body.get('query') or request.args.get('q') or '').strip()
    data, errors = {}, []
    if not q:
        errors.append('Missing query.')
    elif q.startswith('__schema'):
        data = {'__schema': {
            'queryType': {'name': 'Query'},
            'types': ['Game', 'Article', 'Team', 'Sport', 'Parlay']}}
    elif q.startswith('game('):
        try:
            gid = int(q.split('(', 1)[1].split(')')[0])
        except ValueError:
            errors.append('Bad game id.')
            gid = None
        if gid is not None:
            g = Game.query.get(gid)
            data = {'game': None if not g else {
                'id': g.id, 'sport_slug': g.sport_slug,
                'home_score': g.home_score, 'away_score': g.away_score,
                'status': g.status, 'venue': g.venue}}
    elif q.startswith('article('):
        slug = q.split('(', 1)[1].split(')')[0].strip('"\'')
        a = Article.query.filter_by(slug=slug).first()
        data = {'article': None if not a else {
            'id': a.id, 'slug': a.slug, 'title': a.title,
            'sport_slug': a.sport_slug, 'author': a.author}}
    elif q.startswith('team('):
        slug = q.split('(', 1)[1].split(')')[0].strip('"\'')
        t = Team.query.filter_by(slug=slug).first()
        data = {'team': None if not t else {
            'id': t.id, 'slug': t.slug, 'full_name': t.full_name,
            'sport_slug': t.sport_slug}}
    else:
        errors.append(f'Unknown query: {q[:40]}')
    return jsonify({'data': data, 'errors': errors})


@app.route('/api/telemetry', methods=['POST', 'GET'])
@csrf.exempt
def api_telemetry():
    """Telemetry beacon endpoint. Mirror does not persist; returns a
    deterministic ack so tasks can verify round-trip behaviour."""
    if request.method == 'GET':
        return jsonify({
            'endpoint': '/api/telemetry',
            'methods': ['POST'],
            'persisted': False,
            'fields': ['event', 'page', 'props'],
        })
    payload = request.get_json(silent=True) or request.form.to_dict()
    import hashlib
    bid = hashlib.sha1(json.dumps(payload, sort_keys=True).encode())\
        .hexdigest()[:12]
    return jsonify({'beacon_id': bid, 'ack': True, 'received': payload})


@app.route('/developer')
@app.route('/developer/')
def developer_index():
    return render_template('developer_index.html',
                           endpoints=[
                               '/api/v3-graphql',
                               '/api/events',
                               '/api/uptime',
                               '/api/telemetry',
                               '/webhook/score-update',
                               '/developer/fantasy-app',
                               '/healthz',
                           ])


@app.route('/developer/fantasy-app')
@app.route('/developer/fantasy-app/')
def developer_fantasy_app():
    """Landing for the fantasy-app integration guide."""
    teams = (Team.query.order_by(Team.id).limit(8).all())
    return render_template('developer_fantasy_app.html', teams=teams)


@app.route('/api/command-palette')
def api_command_palette():
    """JSON command list used by the Cmd+K palette in base.html."""
    items = [
        {'label': 'Home', 'href': '/'},
        {'label': 'Scores (all sports)', 'href': '/scores'},
        {'label': 'NBA', 'href': '/nba/'},
        {'label': 'NFL', 'href': '/nfl/'},
        {'label': 'MLB', 'href': '/mlb/'},
        {'label': 'NHL', 'href': '/nhl/'},
        {'label': 'Soccer', 'href': '/soccer/'},
        {'label': 'NBA Scoreboard', 'href': '/nba/scoreboard'},
        {'label': 'NBA Standings', 'href': '/nba/standings'},
        {'label': 'NFL Scoreboard', 'href': '/nfl/scoreboard'},
        {'label': 'NFL Standings', 'href': '/nfl/standings'},
        {'label': 'Fantasy', 'href': '/fantasy'},
        {'label': 'ESPN BET', 'href': '/bet'},
        {'label': 'Podcasts', 'href': '/podcasts'},
        {'label': 'Watch (ESPN+)', 'href': '/watch'},
        {'label': 'Awards Hub', 'href': '/awards'},
        {'label': 'Stat Glossary', 'href': '/stat-glossary'},
        {'label': 'Developer Hub', 'href': '/developer'},
        {'label': 'Help / Keyboard Shortcuts', 'href': '/help/keyboard'},
        {'label': 'ESPN Deportes', 'href': '/espn-deportes/'},
    ]
    return jsonify({'commands': items, 'count': len(items)})


# Stat glossary — backs the contextual-help-stat-glossary tooltip feature.
STAT_GLOSSARY = [
    ('PER', 'Player Efficiency Rating',
     "John Hollinger's per-minute rating, league-averaged to 15.0. "
     "Higher is better; anything above 25 is All-Star-tier."),
    ('eFG%', 'Effective Field Goal Percentage',
     'Adjusts shooting percentage to credit 3-pointers their proper '
     'weight: (FGM + 0.5 * 3PM) / FGA.'),
    ('TS%', 'True Shooting Percentage',
     'Single-number shooting efficiency that accounts for 3-pointers '
     'and free throws: PTS / (2 * (FGA + 0.44 * FTA)).'),
    ('USG%', 'Usage Rate',
     'An estimate of the percentage of team plays a player used while '
     'on the floor. Stars often run 28-34%.'),
    ('BPM', 'Box Plus-Minus',
     "Box-score estimate of a player's per-100-possession contribution "
     'above an average player.'),
    ('VORP', 'Value Over Replacement Player',
     'Cumulative per-team contribution above a replacement-level player, '
     'expressed in points per 100 team possessions.'),
    ('PFR', 'Pro Football Reference',
     'NFL data source. ESPN uses overlapping advanced metrics like EPA '
     'and DVOA from internal modeling.'),
    ('EPA', 'Expected Points Added',
     'Football: the change in expected next-score value from a single '
     'play. Sums over a drive or game.'),
    ('DVOA', 'Defense-adjusted Value Over Average',
     'A per-play efficiency measure adjusting for opponent quality.'),
    ('QBR', 'Total Quarterback Rating',
     "ESPN's proprietary 0-100 quarterback rating that accounts for "
     'pass, run, sack, and clutch context.'),
    ('OPS', 'On-base Plus Slugging',
     'Baseball: OBP + SLG. League average sits near .720; above .900 '
     'is All-Star territory.'),
    ('wRC+', 'Weighted Runs Created Plus',
     "Park- and league-adjusted offensive value. 100 is league average; "
     "150 is MVP-tier."),
    ('FIP', 'Fielding-Independent Pitching',
     'A pitching ERA estimator built from strikeouts, walks, and '
     'home runs allowed.'),
    ('Corsi', 'Corsi For Percentage',
     'Hockey: share of shot attempts taken while the player is on the '
     'ice. Anchors most modern NHL analytics.'),
    ('xG', 'Expected Goals',
     'The probability that a shot results in a goal, based on shot '
     'location and game state. Sums into a per-team xG total.'),
    ('PPG', 'Points Per Game',
     'A simple scoring average — total points divided by games played.'),
    ('RPG', 'Rebounds Per Game',
     'Average rebounds per game — total rebounds divided by games '
     'played.'),
    ('APG', 'Assists Per Game',
     'Average assists per game — total assists divided by games played.'),
    ('SPG', 'Steals Per Game',
     'Average steals per game — total steals divided by games played.'),
    ('BPG', 'Blocks Per Game',
     'Average blocks per game — total blocks divided by games played.'),
]


@app.route('/stat-glossary')
@app.route('/stat-glossary/')
def stat_glossary():
    return render_template('stat_glossary.html', entries=STAT_GLOSSARY)


@app.route('/api/stat/<key>')
def api_stat(key):
    key_norm = (key or '').strip().lower()
    for k, name, defn in STAT_GLOSSARY:
        if k.lower() == key_norm:
            return jsonify({'key': k, 'name': name, 'definition': defn})
    abort(404)


@app.route('/help/keyboard')
@app.route('/help/keyboard/')
def help_keyboard():
    shortcuts = [
        ('j', 'Move focus to the next game card on a scoreboard.'),
        ('k', 'Move focus to the previous game card on a scoreboard.'),
        ('g h', 'Jump to home page.'),
        ('g s', 'Jump to /scores.'),
        ('g n', 'Jump to /nba/.'),
        ('g f', 'Jump to /nfl/.'),
        ('/', 'Focus the search box.'),
        ('?', 'Open this keyboard help dialog.'),
        ('Cmd+K', 'Open the global command palette.'),
        ('Ctrl+K', 'Open the global command palette (Windows / Linux).'),
        ('Esc', 'Close any open dialog or palette.'),
    ]
    return render_template('help_keyboard.html', shortcuts=shortcuts)


# ─── R9 Routes: promo codes, DRM, fantasy commissioner, NIL, 247 board ───────

R9_PROMO_CODES = [
    ('SIGNUP100', 'New-user $100 bet credit',
     'Place your first $10 bet; receive $100 in bet credits.',
     'live', 'all', '2026-06-01', '2027-12-31', 100, 10),
    ('NBARESET', 'NBA 2026-27 reset boost',
     '20% odds boost on any NBA spread or moneyline.',
     'live', 'nba', '2026-10-01', '2027-04-15', 50, 5),
    ('MVP25', 'MVP futures boost',
     '+25% on any MVP futures wager up to $25.',
     'live', 'nba', '2026-11-01', '2027-04-15', 25, 5),
    ('NFLKICKOFF', 'NFL kickoff bet match',
     'Bet $50, get $250 in bet credits for week 1.',
     'live', 'nfl', '2026-09-01', '2026-09-15', 250, 50),
    ('CFB_PARLAY', 'CFB parlay insurance',
     '4-leg parlay loss refund up to $25.',
     'live', 'ncaaf', '2026-08-25', '2027-01-15', 25, 10),
    ('MLB_OPENER', 'MLB opener cash-back',
     '$50 back if your first opener bet loses.',
     'expired', 'mlb', '2026-03-25', '2026-04-05', 50, 10),
    ('NHL_PLAYOFF', 'NHL playoff boost',
     '15% odds boost on any conference final wager.',
     'live', 'nhl', '2027-04-20', '2027-06-20', 50, 5),
    ('SOCCER_UCL', 'UCL knockout boost',
     'Odds boost on any UEFA Champions League knockout-round wager.',
     'live', 'soccer', '2027-02-01', '2027-06-01', 50, 5),
    ('NIL_REPORT', 'NIL-disclosure promo',
     'Free $5 bet for users who view the NIL tracker.',
     'live', 'ncaaf', '2026-09-01', '2027-01-15', 5, 0),
    ('OLDLINK', 'Legacy promo (expired)',
     'Legacy R8 carry-over — no longer redeemable.',
     'expired', 'all', '2024-01-01', '2024-12-31', 0, 0),
]


@app.route('/espn-bet/promo')
@app.route('/espn-bet/promo/')
def espn_bet_promo_index():
    """ESPN BET promo-code registry — read-only landing page."""
    codes = []
    for code, title, terms, status, sport, opens, closes, payout, stake in \
            R9_PROMO_CODES:
        codes.append({
            'code': code, 'title': title, 'terms': terms,
            'status': status, 'sport': sport,
            'opens_on': opens, 'closes_on': closes,
            'max_payout': payout, 'min_stake': stake,
        })
    return render_template('espn_bet_promo.html', codes=codes)


@app.route('/espn-bet/promo/<code>')
def espn_bet_promo_detail(code):
    code_upper = code.upper()
    for row in R9_PROMO_CODES:
        if row[0] == code_upper:
            return render_template('espn_bet_promo_detail.html', promo={
                'code': row[0], 'title': row[1], 'terms': row[2],
                'status': row[3], 'sport': row[4],
                'opens_on': row[5], 'closes_on': row[6],
                'max_payout': row[7], 'min_stake': row[8],
            })
    abort(404)


@app.route('/watch/live/<event>/drm')
def watch_live_drm(event):
    """Live-stream DRM region notes for a given watchable event slug."""
    show = Watchable.query.filter_by(slug=event).first_or_404()
    digest = hashlib.sha1(event.encode()).hexdigest()
    # Deterministic region/DRM matrix from slug hash.
    all_regions = ['US-East', 'US-West', 'US-Central', 'Canada', 'UK', 'EU',
                   'LATAM', 'Asia-Pacific']
    region_count = 4 + int(digest[0], 16) % 5
    regions = [{
        'region': r,
        'allowed': (int(digest[i % len(digest)], 16) % 4) != 0,
        'drm': ['Widevine L1', 'PlayReady SL3000',
                'FairPlay'][(int(digest[(i + 1) % len(digest)], 16)) % 3],
    } for i, r in enumerate(all_regions[:region_count])]
    return render_template('watch_live_drm.html',
                           show=show, regions=regions,
                           entitlement='ESPN+',
                           manifest_url=f'/static/manifest/{event}.mpd',
                           drm_widevine_url='https://license.example.com/wv',
                           drm_playready_url='https://license.example.com/pr',
                           drm_fairplay_url='https://license.example.com/fp')


@app.route('/fantasy/league/<league_id>/commissioner')
def fantasy_league_commissioner(league_id):
    """Fantasy league commissioner tools — read-only stub page.

    The league id can be either an integer or a slug ('alice-and-bob-league').
    Output is deterministic from the id."""
    digest = hashlib.sha1(str(league_id).encode()).hexdigest()
    name = f'League #{league_id}'
    tools = [
        {'key': 'lineup-veto',
         'label': 'Lineup veto controls',
         'description': 'Override a manager lineup before lock time.'},
        {'key': 'scoring-overrides',
         'label': 'Custom scoring overrides',
         'description': 'Adjust season-long scoring weights.'},
        {'key': 'playoff-bracket',
         'label': 'Manual playoff bracket',
         'description': 'Force a playoff seeding outside the formula.'},
        {'key': 'trade-freeze',
         'label': 'Trade deadline freeze',
         'description': 'Lock all rosters at the deadline minute.'},
        {'key': 'transaction-log',
         'label': 'Transaction audit log',
         'description': 'Read-only history of every roster action.'},
    ]
    stats = {
        'members': 4 + int(digest[0], 16) % 9,
        'open_trades': int(digest[1], 16) % 4,
        'pending_vetoes': int(digest[2], 16) % 3,
        'commissioner_email': 'alice.j@test.com',
    }
    return render_template('fantasy_commissioner.html',
                           league_id=league_id, league_name=name,
                           tools=tools, stats=stats)


@app.route('/fantasy/trade/<trade_id>/veto-vote')
def fantasy_trade_veto_vote(trade_id):
    """Trade-veto vote screen — read-only summary of a pending vote."""
    digest = hashlib.sha1(str(trade_id).encode()).hexdigest()
    yes = 1 + int(digest[0], 16) % 8
    no = 1 + int(digest[1], 16) % 8
    abstain = int(digest[2], 16) % 4
    total = yes + no + abstain
    deadline_hours = 1 + int(digest[3], 16) % 24
    quorum_met = (yes + no) > total // 2
    return render_template('fantasy_veto_vote.html',
                           trade_id=trade_id,
                           yes=yes, no=no, abstain=abstain, total=total,
                           deadline_hours=deadline_hours,
                           quorum_met=quorum_met,
                           commissioner_override_available=True)


@app.route('/recruiting/247-board')
@app.route('/recruiting/247-board/')
def recruiting_247_board():
    """Cross-sport 247 composite board with flip-risk annotations."""
    sport_filter = request.args.get('sport', '').strip()
    q = Recruit.query
    if sport_filter:
        q = q.filter_by(sport_slug=sport_filter)
    recruits = q.order_by(Recruit.rank).all()
    annotated = []
    for r in recruits:
        digest = hashlib.sha1((r.name or '').encode()).hexdigest()
        flip_risk = ['low', 'medium', 'high'][int(digest[0], 16) % 3]
        oos_visits = int(digest[1], 16) % 4
        annotated.append({
            'recruit': r,
            'flip_risk': flip_risk,
            'oos_visits': oos_visits,
            'last_update_days_ago': int(digest[2], 16) % 14,
        })
    return render_template('recruiting_247_board.html',
                           board=annotated,
                           sport_filter=sport_filter)


@app.route('/nil/tracker')
@app.route('/nil/tracker/')
def nil_tracker():
    """NIL deals tracker — deterministic dollar amounts derived from recruits."""
    sport_filter = request.args.get('sport', '').strip()
    q = Recruit.query
    if sport_filter:
        q = q.filter_by(sport_slug=sport_filter)
    recruits = q.order_by(Recruit.rank).limit(120).all()
    deals = []
    collectives = ['One More Year Collective', 'Burnt Orange NIL',
                   'Yea Alabama', 'OSU NIL Fund', 'Bayou Traditions',
                   'Champions Circle', 'Crimson NIL Society',
                   'On3 NIL Collective', 'Dawgs of a Feather',
                   'Friends of the U']
    for r in recruits:
        digest = hashlib.sha1(('nil-' + (r.name or '')).encode()).hexdigest()
        amount = 25000 + int(digest[:6], 16) % 4_975_000  # $25k - $5M
        collective = collectives[int(digest[6], 16) % len(collectives)]
        disclosed = int(digest[7], 16) % 2 == 0
        deals.append({
            'recruit': r,
            'amount_usd': amount,
            'amount_label': f'${amount:,}',
            'collective': collective,
            'disclosed': disclosed,
            'school': r.committed_to,
            'season': r.season or '2026-27',
        })
    deals.sort(key=lambda d: -d['amount_usd'])
    totals = {
        'count': len(deals),
        'sum_usd': sum(d['amount_usd'] for d in deals),
        'disclosed_count': sum(1 for d in deals if d['disclosed']),
    }
    return render_template('nil_tracker.html', deals=deals,
                           totals=totals, sport_filter=sport_filter)


# ─── Seed Data ────────────────────────────────────────────────────────────────

def seed_database():
    if Sport.query.first():
        return  # Already seeded

    # ----- Sports -----
    sports_data = [
        ('NFL', 'nfl', 'National Football League', '/nfl/', 1),
        ('NBA', 'nba', 'National Basketball Association', '/nba/', 2),
        ('MLB', 'mlb', 'Major League Baseball', '/mlb/', 3),
        ('NHL', 'nhl', 'National Hockey League', '/nhl/', 4),
        ('Soccer', 'soccer', 'Soccer', '/soccer/', 5),
        ('College Football', 'ncaaf', 'College Football', '/college-football/', 6),
        ('Men\'s College Basketball', 'ncaam', "Men's College Basketball",
         '/mens-college-basketball/', 7),
        ('Women\'s College Basketball', 'ncaaw', "Women's College Basketball",
         '/womens-college-basketball/', 8),
        ('Tennis', 'tennis', 'Tennis', '/tennis/', 9),
        ('Golf', 'golf', 'Golf', '/golf/', 10),
        ('MMA', 'mma', 'MMA', '/mma/', 11),
        ('Fantasy', 'fantasy', 'Fantasy Sports', '/fantasy/', 12),
    ]
    for name, slug, display, prefix, order in sports_data:
        db.session.add(Sport(name=name, slug=slug, display_name=display,
                             url_prefix=prefix, nav_order=order))
    db.session.flush()

    from seed_data import seed_all
    seed_all(db, Conference, Division, Team, Player, PlayerStat, Game,
             GamePlayerStat, Article, Transaction, DepthChartEntry,
             PowerIndex, Recruit)
    db.session.commit()


def seed_benchmark_users():
    """Idempotent: creates 4 benchmark users with favorites seeded from DB."""
    if User.query.filter_by(email='alice.j@test.com').first():
        return  # already seeded

    # Helper to look up team/player by slug
    def _team(slug):
        return Team.query.filter_by(slug=slug).first()

    def _player(slug):
        return Player.query.filter_by(slug=slug).first()

    users_def = [
        {
            'email': 'alice.j@test.com',
            'name': 'Alice Johnson',
            'is_espn_plus': True,
            'team_slugs': ['boston-celtics', 'new-england-patriots', 'boston-red-sox'],
            'player_slugs': ['jayson-tatum', 'lebron-james'],
        },
        {
            'email': 'bob.c@test.com',
            'name': 'Bob Chen',
            'is_espn_plus': False,
            'team_slugs': ['los-angeles-lakers', 'golden-state-warriors', 'los-angeles-rams'],
            'player_slugs': ['lebron-james', 'stephen-curry', 'anthony-davis'],
        },
        {
            'email': 'carol.d@test.com',
            'name': 'Carol Davis',
            'is_espn_plus': True,
            'team_slugs': ['miami-heat', 'chicago-bulls'],
            'player_slugs': ['jimmy-butler', 'giannis-antetokounmpo'],
        },
        {
            'email': 'david.k@test.com',
            'name': 'David Kim',
            'is_espn_plus': False,
            'team_slugs': ['dallas-mavericks', 'oklahoma-city-thunder', 'denver-nuggets'],
            'player_slugs': ['luka-doncic', 'nikola-jokic', 'shai-gilgeous-alexander'],
        },
    ]

    for ud in users_def:
        user = User(email=ud['email'], name=ud['name'],
                    is_espn_plus=ud['is_espn_plus'])
        user.set_password('TestPass123!')
        db.session.add(user)
        db.session.flush()  # get user.id

        for tslug in ud['team_slugs']:
            t = _team(tslug)
            if t:
                db.session.add(UserFavorite(user_id=user.id,
                                            item_type='team', item_id=t.id))
        for pslug in ud['player_slugs']:
            p = _player(pslug)
            if p:
                db.session.add(UserFavorite(user_id=user.id,
                                            item_type='player', item_id=p.id))

    db.session.commit()


@app.before_request
def ensure_seeded():
    pass  # Seeding done at startup


# ─── Error Handlers ───────────────────────────────────────────────────────────

@app.errorhandler(404)
def not_found(e):
    return render_template('404.html'), 404


@app.errorhandler(500)
def server_error(e):
    return render_template('500.html'), 500


# ─── Main ─────────────────────────────────────────────────────────────────────


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
R2_SITE_NAME = "ESPN"
R2_DOMAIN = "espn.com"
R2_ACCESSIBILITY_BLURB = "ESPN provides captioned video, audio descriptions on key broadcasts, and a high-contrast scoreboard mode for fans with visual impairments."


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
R3_SITE_NAME = "ESPN"
R3_DOMAIN = "espn.com"


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


# === R4 GUI Fantasy + R5 GUI Brackets BEGIN ─────────────────────────────────
# Adds:
#   R4: lineup builder / waiver-wire window / trade analyzer / matchup detail
#       on top of new r4_fantasy_* tables (see _r4gui_extend.py).
#   R5: NCAA Men's + Women's March Madness, NBA Play-In, NHL Playoffs brackets
#       on top of new r5_* tables (see _r5gui_extend.py).
# Tables are queried via raw SQL (db.session.execute) since they have no
# SQLAlchemy model classes — the data is shipped through instance_seed/espn.db.
from sqlalchemy import text as _r45_text


def _r45_rows(sql, **params):
    """Execute SQL and return list of dict rows (RowMapping)."""
    return [dict(r) for r in db.session.execute(_r45_text(sql), params).mappings()]


def _r45_row(sql, **params):
    rs = _r45_rows(sql, **params)
    return rs[0] if rs else None


# ─── R4 Fantasy helpers ──────────────────────────────────────────────────────

def _r4_get_league_or_404(league_slug):
    lg = _r45_row(
        "SELECT * FROM r4_fantasy_leagues WHERE slug=:s", s=league_slug)
    if not lg:
        abort(404)
    return lg


def _r4_get_team_or_404(team_slug):
    tm = _r45_row(
        "SELECT * FROM r4_fantasy_teams WHERE slug=:s", s=team_slug)
    if not tm:
        abort(404)
    return tm


@app.route('/r4/fantasy')
@app.route('/r4/fantasy/')
def r4_fantasy_index():
    """Fantasy R4 hub: list public leagues across NFL / NBA / MLB."""
    leagues = _r45_rows(
        "SELECT * FROM r4_fantasy_leagues "
        "ORDER BY sport_slug, name")
    by_sport = {'nfl': [], 'nba': [], 'mlb': []}
    for lg in leagues:
        by_sport.setdefault(lg['sport_slug'], []).append(lg)
    return render_template('r4_fantasy_index.html',
                            leagues_by_sport=by_sport)


@app.route('/r4/fantasy/league/<league_slug>')
def r4_fantasy_league_home(league_slug):
    """League home: standings, matchup grid for current week, my team card."""
    lg = _r4_get_league_or_404(league_slug)
    teams = _r45_rows(
        "SELECT * FROM r4_fantasy_teams WHERE league_id=:lid "
        "ORDER BY wins DESC, points_for DESC", lid=lg['id'])
    matchups = _r45_rows(
        "SELECT m.*, ta.team_name AS a_name, ta.slug AS a_slug, "
        "tb.team_name AS b_name, tb.slug AS b_slug "
        "FROM r4_fantasy_matchups m "
        "JOIN r4_fantasy_teams ta ON ta.id=m.team_a_id "
        "JOIN r4_fantasy_teams tb ON tb.id=m.team_b_id "
        "WHERE m.league_id=:lid AND m.week=:wk ORDER BY m.id",
        lid=lg['id'], wk=lg['current_week'])
    return render_template('r4_fantasy_league.html',
                            league=lg, teams=teams, matchups=matchups)


@app.route('/r4/fantasy/lineup/<team_slug>')
def r4_lineup_builder(team_slug):
    """Lineup builder: starting lineup by position slot for a fantasy team."""
    tm = _r4_get_team_or_404(team_slug)
    lg = _r45_row(
        "SELECT * FROM r4_fantasy_leagues WHERE id=:lid", lid=tm['league_id'])
    lineup = _r45_rows(
        "SELECT * FROM r4_fantasy_lineups WHERE team_id=:tid "
        "AND week=:wk ORDER BY id", tid=tm['id'], wk=lg['current_week'])
    proj_total = round(sum((r['projected_points'] or 0.0) for r in lineup), 2)
    return render_template('r4_lineup_builder.html',
                            team=tm, league=lg, lineup=lineup,
                            proj_total=proj_total)


@app.route('/r4/fantasy/lineup/<team_slug>/slot/<slot>')
def r4_lineup_slot_detail(team_slug, slot):
    """Click a slot on the lineup builder to see eligible players + matchup."""
    tm = _r4_get_team_or_404(team_slug)
    lg = _r45_row(
        "SELECT * FROM r4_fantasy_leagues WHERE id=:lid", lid=tm['league_id'])
    row = _r45_row(
        "SELECT * FROM r4_fantasy_lineups WHERE team_id=:tid "
        "AND week=:wk AND slot=:sl", tid=tm['id'], wk=lg['current_week'],
        sl=slot.upper())
    if not row:
        abort(404)
    pos_map = {'QB': ['QB'], 'RB1': ['RB'], 'RB2': ['RB'],
               'WR1': ['WR'], 'WR2': ['WR'], 'TE': ['TE'],
               'FLEX': ['RB', 'WR', 'TE'], 'DST': ['DST'], 'K': ['K'],
               'PG': ['PG'], 'SG': ['SG'], 'SF': ['SF'], 'PF': ['PF'],
               'C': ['C'], 'G': ['PG', 'SG'], 'F': ['SF', 'PF'],
               'UTIL1': ['PG', 'SG', 'SF', 'PF', 'C'],
               'UTIL2': ['PG', 'SG', 'SF', 'PF', 'C']}
    positions = pos_map.get(slot.upper(), [slot.upper()])
    placeholders = ','.join([f':p{i}' for i in range(len(positions))])
    params = {f'p{i}': p for i, p in enumerate(positions)}
    params['sp'] = lg['sport_slug']
    alts = _r45_rows(
        f"SELECT name, position, slug FROM players WHERE sport_slug=:sp "
        f"AND position IN ({placeholders}) ORDER BY id LIMIT 8",
        **params)
    return render_template('r4_lineup_slot.html',
                            team=tm, league=lg, slot=slot.upper(),
                            row=row, alts=alts)


@app.route('/r4/fantasy/waiver-window/<league_slug>')
def r4_waiver_wire_window(league_slug):
    """Waiver wire transaction window for a league."""
    lg = _r4_get_league_or_404(league_slug)
    claims = _r45_rows(
        "SELECT c.*, t.team_name, t.manager_name, t.slug AS team_slug "
        "FROM r4_fantasy_waiver_claims c "
        "JOIN r4_fantasy_teams t ON t.id=c.team_id "
        "WHERE c.league_id=:lid ORDER BY c.priority, c.id",
        lid=lg['id'])
    return render_template('r4_waiver_window.html',
                            league=lg, claims=claims)


@app.route('/r4/fantasy/waiver-claim/<claim_slug>')
def r4_waiver_claim_detail(claim_slug):
    """Drill into a single waiver claim — needed for disambiguation tasks."""
    c = _r45_row(
        "SELECT c.*, t.team_name, t.manager_name, t.slug AS team_slug, "
        "l.slug AS league_slug, l.name AS league_name, l.sport_slug "
        "FROM r4_fantasy_waiver_claims c "
        "JOIN r4_fantasy_teams t ON t.id=c.team_id "
        "JOIN r4_fantasy_leagues l ON l.id=c.league_id "
        "WHERE c.slug=:s", s=claim_slug)
    if not c:
        abort(404)
    return render_template('r4_waiver_claim.html', claim=c)


@app.route('/r4/fantasy/trade-analyzer/<league_slug>')
def r4_trade_analyzer(league_slug):
    """List all current trade proposals in a league."""
    lg = _r4_get_league_or_404(league_slug)
    trades = _r45_rows(
        "SELECT tr.*, ta.team_name AS a_name, ta.slug AS a_slug, "
        "ta.manager_name AS a_mgr, "
        "tb.team_name AS b_name, tb.slug AS b_slug, tb.manager_name AS b_mgr "
        "FROM r4_fantasy_trades tr "
        "JOIN r4_fantasy_teams ta ON ta.id=tr.team_a_id "
        "JOIN r4_fantasy_teams tb ON tb.id=tr.team_b_id "
        "WHERE tr.league_id=:lid ORDER BY tr.id", lid=lg['id'])
    return render_template('r4_trade_analyzer.html',
                            league=lg, trades=trades)


@app.route('/r4/fantasy/trade/<trade_slug>')
def r4_trade_detail(trade_slug):
    """Single trade proposal — multi-player swap valuation."""
    tr = _r45_row(
        "SELECT tr.*, ta.team_name AS a_name, ta.slug AS a_slug, "
        "ta.manager_name AS a_mgr, "
        "tb.team_name AS b_name, tb.slug AS b_slug, tb.manager_name AS b_mgr, "
        "l.slug AS league_slug, l.name AS league_name, l.sport_slug "
        "FROM r4_fantasy_trades tr "
        "JOIN r4_fantasy_teams ta ON ta.id=tr.team_a_id "
        "JOIN r4_fantasy_teams tb ON tb.id=tr.team_b_id "
        "JOIN r4_fantasy_leagues l ON l.id=tr.league_id "
        "WHERE tr.slug=:s", s=trade_slug)
    if not tr:
        abort(404)
    players_a = json.loads(tr['players_a_json'] or '[]')
    players_b = json.loads(tr['players_b_json'] or '[]')
    return render_template('r4_trade_detail.html',
                            trade=tr, players_a=players_a,
                            players_b=players_b)


@app.route('/r4/fantasy/matchup/<int:matchup_id>')
def r4_fantasy_matchup(matchup_id):
    """Head-to-head matchup detail page."""
    m = _r45_row(
        "SELECT m.*, ta.team_name AS a_name, ta.slug AS a_slug, "
        "ta.manager_name AS a_mgr, "
        "tb.team_name AS b_name, tb.slug AS b_slug, tb.manager_name AS b_mgr, "
        "l.slug AS league_slug, l.name AS league_name, l.sport_slug "
        "FROM r4_fantasy_matchups m "
        "JOIN r4_fantasy_teams ta ON ta.id=m.team_a_id "
        "JOIN r4_fantasy_teams tb ON tb.id=m.team_b_id "
        "JOIN r4_fantasy_leagues l ON l.id=m.league_id "
        "WHERE m.id=:id", id=matchup_id)
    if not m:
        abort(404)
    lineup_a = _r45_rows(
        "SELECT * FROM r4_fantasy_lineups WHERE team_id=:t AND week=:w "
        "ORDER BY id", t=m['team_a_id'], w=m['week'])
    lineup_b = _r45_rows(
        "SELECT * FROM r4_fantasy_lineups WHERE team_id=:t AND week=:w "
        "ORDER BY id", t=m['team_b_id'], w=m['week'])
    return render_template('r4_fantasy_matchup.html',
                            matchup=m, lineup_a=lineup_a,
                            lineup_b=lineup_b)


# ─── R5 Brackets ─────────────────────────────────────────────────────────────

@app.route('/r5/bracket')
@app.route('/r5/bracket/')
def r5_bracket_index():
    """List all brackets (men's, women's, NBA play-in, NHL playoffs)."""
    brackets = _r45_rows(
        "SELECT * FROM r5_brackets ORDER BY sport_slug, year DESC")
    return render_template('r5_bracket_index.html', brackets=brackets)


@app.route('/r5/bracket/<slug>')
def r5_bracket_home(slug):
    """Full bracket view — all regions, all rounds."""
    b = _r45_row("SELECT * FROM r5_brackets WHERE slug=:s", s=slug)
    if not b:
        abort(404)
    seeds = _r45_rows(
        "SELECT * FROM r5_bracket_seeds WHERE bracket_id=:bid "
        "ORDER BY region, seed_num", bid=b['id'])
    matchups = _r45_rows(
        "SELECT * FROM r5_bracket_matchups WHERE bracket_id=:bid "
        "ORDER BY round_num, region, slot", bid=b['id'])
    regions_set = sorted({s['region'] for s in seeds})
    return render_template('r5_bracket_home.html',
                            bracket=b, seeds=seeds, matchups=matchups,
                            regions=regions_set)


@app.route('/r5/bracket/<slug>/region/<region>')
def r5_bracket_region(slug, region):
    """One region of a bracket — 16 seeds + 4 rounds of games."""
    b = _r45_row("SELECT * FROM r5_brackets WHERE slug=:s", s=slug)
    if not b:
        abort(404)
    seeds = _r45_rows(
        "SELECT * FROM r5_bracket_seeds WHERE bracket_id=:bid AND region=:r "
        "ORDER BY seed_num", bid=b['id'], r=region)
    matchups = _r45_rows(
        "SELECT * FROM r5_bracket_matchups WHERE bracket_id=:bid AND region=:r "
        "ORDER BY round_num, slot", bid=b['id'], r=region)
    return render_template('r5_bracket_region.html',
                            bracket=b, region=region, seeds=seeds,
                            matchups=matchups)


@app.route('/r5/bracket/<slug>/round/<int:round_num>')
def r5_bracket_round(slug, round_num):
    """All matchups in a single round across regions."""
    b = _r45_row("SELECT * FROM r5_brackets WHERE slug=:s", s=slug)
    if not b:
        abort(404)
    matchups = _r45_rows(
        "SELECT * FROM r5_bracket_matchups WHERE bracket_id=:bid "
        "AND round_num=:n ORDER BY region, slot", bid=b['id'], n=round_num)
    if not matchups:
        abort(404)
    return render_template('r5_bracket_round.html',
                            bracket=b, round_num=round_num,
                            round_name=matchups[0]['round_name'],
                            matchups=matchups)


@app.route('/r5/bracket/<slug>/matchup/<int:matchup_id>')
def r5_bracket_matchup_detail(slug, matchup_id):
    """Single bracket matchup — score, leading scorer, etc."""
    b = _r45_row("SELECT * FROM r5_brackets WHERE slug=:s", s=slug)
    if not b:
        abort(404)
    m = _r45_row(
        "SELECT * FROM r5_bracket_matchups WHERE id=:id AND bracket_id=:bid",
        id=matchup_id, bid=b['id'])
    if not m:
        abort(404)
    return render_template('r5_bracket_matchup.html',
                            bracket=b, matchup=m)


@app.route('/r5/seed/<slug>')
def r5_bracket_seed_detail(slug):
    """Drill into one seeded team — record, coach, region, results so far."""
    s = _r45_row("SELECT * FROM r5_bracket_seeds WHERE slug=:s", s=slug)
    if not s:
        abort(404)
    b = _r45_row("SELECT * FROM r5_brackets WHERE id=:i", i=s['bracket_id'])
    games = _r45_rows(
        "SELECT * FROM r5_bracket_matchups WHERE bracket_id=:bid "
        "AND (team_a_name=:n OR team_b_name=:n) ORDER BY round_num",
        bid=s['bracket_id'], n=s['team_name'])
    return render_template('r5_bracket_seed.html',
                            seed=s, bracket=b, games=games)


@app.route('/r5/play-in/nba')
@app.route('/r5/play-in/nba/')
def r5_play_in_home():
    """NBA Play-In Tournament home: East & West games."""
    games = _r45_rows(
        "SELECT * FROM r5_play_in_games ORDER BY conference, id")
    east = [g for g in games if g['conference'] == 'EAST']
    west = [g for g in games if g['conference'] == 'WEST']
    return render_template('r5_play_in_home.html', east=east, west=west)


@app.route('/r5/play-in/nba/game/<slug>')
def r5_play_in_game_detail(slug):
    g = _r45_row("SELECT * FROM r5_play_in_games WHERE slug=:s", s=slug)
    if not g:
        abort(404)
    return render_template('r5_play_in_game.html', game=g)


@app.route('/r5/playoffs/nhl')
@app.route('/r5/playoffs/nhl/')
def r5_nhl_playoffs_home():
    """NHL Stanley Cup Playoffs home: East & West conference brackets."""
    series = _r45_rows(
        "SELECT * FROM r5_nhl_series ORDER BY round_num, conference, id")
    east = [s for s in series if s['conference'] == 'EAST']
    west = [s for s in series if s['conference'] == 'WEST']
    return render_template('r5_nhl_playoffs.html', east=east, west=west)


@app.route('/r5/playoffs/nhl/series/<slug>')
def r5_nhl_series_detail(slug):
    s = _r45_row("SELECT * FROM r5_nhl_series WHERE slug=:s", s=slug)
    if not s:
        abort(404)
    return render_template('r5_nhl_series.html', series=s)


# === R4 GUI Fantasy + R5 GUI Brackets END ───────────────────────────────────


# === R6 GUI Fantasy/Bracket/Community POST surface BEGIN ════════════════════
# Adds ~30 POST endpoints (lineup save / waiver claim / trade lifecycle /
# league create+invite+join+draft+settings / team rename+avatar / bracket
# pick+champion+submit+tiebreaker / bracket pool create+join+invite /
# comment+reply+upvote / team+player follow / watchlist / alert / poll vote).
#
# Storage: writes land in instance/espn.db (the live, per-container DB).
# Tables are r6_* — created at build time by `_r6gui_extend.py`. The new
# routes never re-seed and never touch instance_seed/espn.db at runtime.
#
# CSRF: every form template renders {{ csrf_token() }}; the existing
# CSRFProtect() at module top will validate on submit. (Tasks that submit
# forms via the browser pick up the token automatically.)
#
# Auth: most write endpoints fall back to an anonymous "guest@espn.local"
# email when no user is logged in, so tasks that don't log in can still
# exercise the surface. Endpoints that require a logged-in identity
# (account-scoped settings, etc.) use @login_required.

R6_GUEST_EMAIL = 'guest@espn.local'
R6_GUEST_NAME = 'ESPN Guest'


def _r6_actor():
    """Return (email, display_name) for the current actor — logged in or guest."""
    if current_user.is_authenticated:
        return current_user.email, current_user.name
    # Form may supply name/email for unauthenticated submissions
    email = (request.form.get('author_email') or '').strip()
    name = (request.form.get('author_name') or '').strip()
    return (email or R6_GUEST_EMAIL, name or R6_GUEST_NAME)


def _r6_now():
    return mirror_now().strftime('%Y-%m-%d %H:%M:%S')


def _r6_exec(sql, **params):
    """Wrapper that runs an INSERT/UPDATE/DELETE and commits."""
    db.session.execute(_r45_text(sql), params)
    db.session.commit()


def _r6_lookup_team_full(team_slug):
    return _r45_row(
        "SELECT * FROM r4_fantasy_teams WHERE slug=:s", s=team_slug)


def _r6_render_success(title, message, back_url=None, back_label='Continue'):
    return render_template('r6_post_success.html',
                            title=title, message=message,
                            back_url=back_url, back_label=back_label)


# ─── Fantasy lineup ──────────────────────────────────────────────────────────

@app.route('/fantasy/lineup/save/<team_slug>', methods=['GET', 'POST'])
def r6_lineup_save(team_slug):
    tm = _r6_lookup_team_full(team_slug)
    if not tm:
        abort(404)
    lg = _r45_row("SELECT * FROM r4_fantasy_leagues WHERE id=:lid",
                  lid=tm['league_id'])
    lineup = _r45_rows(
        "SELECT * FROM r4_fantasy_lineups WHERE team_id=:tid "
        "AND week=:wk ORDER BY id", tid=tm['id'], wk=lg['current_week'])
    if request.method == 'POST':
        # Mark lineup saved (event log row + flip is_starter flags).
        starters = set(request.form.getlist('starter'))
        for r in lineup:
            new_val = 1 if str(r['id']) in starters else 0
            _r6_exec("UPDATE r4_fantasy_lineups SET is_starter=:v "
                     "WHERE id=:i", v=new_val, i=r['id'])
        email, _name = _r6_actor()
        _r6_exec(
            "INSERT INTO r6_lineup_events (team_slug, kind, slot, in_player, "
            "out_player, week, saved_at) "
            "VALUES (:t, 'save', NULL, NULL, NULL, :w, :ts)",
            t=team_slug, w=lg['current_week'], ts=_r6_now())
        flash(f'Lineup saved for week {lg["current_week"]}.', 'success')
        return redirect(url_for('r6_lineup_save', team_slug=team_slug))
    return render_template('r6_lineup_form.html',
                            team=tm, league=lg, lineup=lineup)


@app.route('/fantasy/lineup/swap/<team_slug>/<slot>', methods=['GET', 'POST'])
def r6_lineup_swap(team_slug, slot):
    tm = _r6_lookup_team_full(team_slug)
    if not tm:
        abort(404)
    lg = _r45_row("SELECT * FROM r4_fantasy_leagues WHERE id=:lid",
                  lid=tm['league_id'])
    current_slot = _r45_row(
        "SELECT * FROM r4_fantasy_lineups WHERE team_id=:tid "
        "AND week=:wk AND slot=:s",
        tid=tm['id'], wk=lg['current_week'], s=slot)
    if request.method == 'POST':
        new_player = request.form.get('new_player_name', '').strip()
        if not new_player:
            flash('Pick a replacement player.', 'danger')
            return redirect(request.url)
        out_player = current_slot['player_name'] if current_slot else ''
        _r6_exec(
            "UPDATE r4_fantasy_lineups SET player_name=:p "
            "WHERE team_id=:tid AND week=:wk AND slot=:s",
            p=new_player, tid=tm['id'], wk=lg['current_week'], s=slot)
        _r6_exec(
            "INSERT INTO r6_lineup_events (team_slug, kind, slot, in_player, "
            "out_player, week, saved_at) "
            "VALUES (:t, 'swap', :s, :ip, :op, :w, :ts)",
            t=team_slug, s=slot, ip=new_player, op=out_player,
            w=lg['current_week'], ts=_r6_now())
        return _r6_render_success(
            f'Swapped {slot}',
            f'{new_player} is now in the {slot} slot for {tm["team_name"]}.',
            back_url=f'/fantasy/lineup/save/{team_slug}',
            back_label='Back to lineup')
    return render_template('r6_lineup_swap.html',
                            team=tm, league=lg, slot=slot,
                            current_slot=current_slot)


# ─── Fantasy waiver wire ─────────────────────────────────────────────────────

@app.route('/fantasy/waiver/claim/<int:player_id>', methods=['GET', 'POST'])
def r6_waiver_claim(player_id):
    pl = _r45_row("SELECT * FROM players WHERE id=:i", i=player_id)
    if not pl:
        abort(404)
    leagues = _r45_rows(
        "SELECT * FROM r4_fantasy_leagues WHERE sport_slug=:s "
        "ORDER BY name", s=pl['sport_slug'])
    if request.method == 'POST':
        league_slug = request.form.get('league_slug', '').strip()
        team_slug = request.form.get('team_slug', '').strip()
        bid_amount = int(request.form.get('bid_amount', '5') or '5')
        drop_player = request.form.get('drop_player', '').strip()
        lg = _r45_row(
            "SELECT * FROM r4_fantasy_leagues WHERE slug=:s", s=league_slug)
        tm = _r45_row(
            "SELECT * FROM r4_fantasy_teams WHERE slug=:s", s=team_slug)
        if not (lg and tm):
            flash('League or team not found.', 'danger')
            return redirect(request.url)
        new_id = (_r45_row(
            "SELECT COALESCE(MAX(id),0)+1 AS n "
            "FROM r4_fantasy_waiver_claims") or {}).get('n', 1)
        slug = f'l{lg["id"]}-c{new_id}'
        _r6_exec(
            "INSERT INTO r4_fantasy_waiver_claims "
            "(id, league_id, team_id, slug, add_player_id, add_player_name, "
            "add_player_pos, drop_player_id, drop_player_name, drop_player_pos, "
            "bid_amount, priority, status, process_date) "
            "VALUES (:id, :lid, :tid, :slug, :apid, :apn, :apos, NULL, :dpn, "
            "'BENCH', :bid, 1, 'pending', :pd)",
            id=new_id, lid=lg['id'], tid=tm['id'], slug=slug, apid=pl['id'],
            apn=pl['name'], apos=pl['position'], dpn=drop_player,
            bid=bid_amount, pd=DEMO_DATE_R6())
        return _r6_render_success(
            'Waiver claim submitted',
            f'Claim filed for {pl["name"]} (${bid_amount} bid) — processes '
            'next waiver window.',
            back_url=f'/r4/fantasy/league/{league_slug}',
            back_label='Back to league')
    return render_template('r6_waiver_form.html',
                            player=pl, leagues=leagues, mode='claim')


@app.route('/fantasy/waiver/drop/<int:player_id>', methods=['GET', 'POST'])
def r6_waiver_drop(player_id):
    pl = _r45_row("SELECT * FROM players WHERE id=:i", i=player_id)
    if not pl:
        abort(404)
    leagues = _r45_rows(
        "SELECT * FROM r4_fantasy_leagues WHERE sport_slug=:s "
        "ORDER BY name", s=pl['sport_slug'])
    if request.method == 'POST':
        league_slug = request.form.get('league_slug', '').strip()
        team_slug = request.form.get('team_slug', '').strip()
        lg = _r45_row(
            "SELECT * FROM r4_fantasy_leagues WHERE slug=:s", s=league_slug)
        tm = _r45_row(
            "SELECT * FROM r4_fantasy_teams WHERE slug=:s", s=team_slug)
        if not (lg and tm):
            flash('League or team not found.', 'danger')
            return redirect(request.url)
        new_id = (_r45_row(
            "SELECT COALESCE(MAX(id),0)+1 AS n "
            "FROM r4_fantasy_waiver_claims") or {}).get('n', 1)
        slug = f'l{lg["id"]}-c{new_id}'
        _r6_exec(
            "INSERT INTO r4_fantasy_waiver_claims "
            "(id, league_id, team_id, slug, add_player_id, add_player_name, "
            "add_player_pos, drop_player_id, drop_player_name, drop_player_pos, "
            "bid_amount, priority, status, process_date) "
            "VALUES (:id, :lid, :tid, :slug, NULL, '', '', :dpid, :dpn, :dpos, "
            "0, 99, 'pending', :pd)",
            id=new_id, lid=lg['id'], tid=tm['id'], slug=slug,
            dpid=pl['id'], dpn=pl['name'], dpos=pl['position'],
            pd=DEMO_DATE_R6())
        return _r6_render_success(
            'Player dropped',
            f'Drop request filed for {pl["name"]}.',
            back_url=f'/r4/fantasy/league/{league_slug}',
            back_label='Back to league')
    return render_template('r6_waiver_form.html',
                            player=pl, leagues=leagues, mode='drop')


def DEMO_DATE_R6():
    return mirror_today().isoformat()


# ─── Fantasy trade lifecycle ─────────────────────────────────────────────────

@app.route('/fantasy/trade/propose/<league_slug>', methods=['GET', 'POST'])
def r6_trade_propose(league_slug):
    lg = _r45_row(
        "SELECT * FROM r4_fantasy_leagues WHERE slug=:s", s=league_slug)
    if not lg:
        abort(404)
    teams = _r45_rows(
        "SELECT * FROM r4_fantasy_teams WHERE league_id=:lid ORDER BY id",
        lid=lg['id'])
    if request.method == 'POST':
        team_a_slug = request.form.get('team_a', '').strip()
        team_b_slug = request.form.get('team_b', '').strip()
        players_a = request.form.get('players_a', '').strip()
        players_b = request.form.get('players_b', '').strip()
        note = request.form.get('note', '').strip()
        a = _r45_row("SELECT * FROM r4_fantasy_teams WHERE slug=:s",
                     s=team_a_slug)
        b = _r45_row("SELECT * FROM r4_fantasy_teams WHERE slug=:s",
                     s=team_b_slug)
        if not (a and b):
            flash('Pick both sides of the trade.', 'danger')
            return redirect(request.url)
        new_id = (_r45_row(
            "SELECT COALESCE(MAX(id),0)+1 AS n "
            "FROM r4_fantasy_trades") or {}).get('n', 1)
        slug = f'l{lg["id"]}-tr{new_id}'
        _r6_exec(
            "INSERT INTO r4_fantasy_trades "
            "(id, league_id, slug, team_a_id, team_b_id, players_a_json, "
            "players_b_json, value_a, value_b, status, proposed_date, note) "
            "VALUES (:id, :lid, :slug, :a, :b, :pa, :pb, 0, 0, 'pending', "
            ":pd, :nt)",
            id=new_id, lid=lg['id'], slug=slug, a=a['id'], b=b['id'],
            pa=players_a, pb=players_b, pd=DEMO_DATE_R6(), nt=note)
        return _r6_render_success(
            'Trade proposed',
            f'Trade proposal sent from {a["team_name"]} to {b["team_name"]}.',
            back_url=f'/r4/fantasy/league/{league_slug}',
            back_label='Back to league')
    return render_template('r6_trade_form.html',
                            league=lg, teams=teams, mode='propose')


def _trade_status_update(trade_slug, new_status):
    tr = _r45_row(
        "SELECT * FROM r4_fantasy_trades WHERE slug=:s", s=trade_slug)
    if not tr:
        abort(404)
    if request.method == 'POST':
        _r6_exec(
            "UPDATE r4_fantasy_trades SET status=:st WHERE slug=:s",
            st=new_status, s=trade_slug)
        lg = _r45_row(
            "SELECT slug FROM r4_fantasy_leagues WHERE id=:i",
            i=tr['league_id'])
        return _r6_render_success(
            f'Trade {new_status}',
            f'Trade {trade_slug} marked as {new_status}.',
            back_url=f'/r4/fantasy/league/{lg["slug"]}' if lg else '/r4/fantasy',
            back_label='Back to league')
    return render_template('r6_trade_review.html',
                            trade=tr, action=new_status)


@app.route('/fantasy/trade/<trade_slug>/accept', methods=['GET', 'POST'])
def r6_trade_accept(trade_slug):
    return _trade_status_update(trade_slug, 'accepted')


@app.route('/fantasy/trade/<trade_slug>/reject', methods=['GET', 'POST'])
def r6_trade_reject(trade_slug):
    return _trade_status_update(trade_slug, 'rejected')


@app.route('/fantasy/trade/<trade_slug>/counter', methods=['GET', 'POST'])
def r6_trade_counter(trade_slug):
    tr = _r45_row(
        "SELECT * FROM r4_fantasy_trades WHERE slug=:s", s=trade_slug)
    if not tr:
        abort(404)
    if request.method == 'POST':
        # Mark original countered + insert new pending trade
        _r6_exec(
            "UPDATE r4_fantasy_trades SET status='countered' WHERE slug=:s",
            s=trade_slug)
        new_id = (_r45_row(
            "SELECT COALESCE(MAX(id),0)+1 AS n "
            "FROM r4_fantasy_trades") or {}).get('n', 1)
        new_slug = f'{trade_slug}-counter{new_id}'
        players_a = request.form.get('players_a', '').strip()
        players_b = request.form.get('players_b', '').strip()
        note = request.form.get('note', '').strip()
        # In a counter, the previously-targeted team (team_b) becomes proposer
        _r6_exec(
            "INSERT INTO r4_fantasy_trades "
            "(id, league_id, slug, team_a_id, team_b_id, players_a_json, "
            "players_b_json, value_a, value_b, status, proposed_date, note) "
            "VALUES (:id, :lid, :slug, :a, :b, :pa, :pb, 0, 0, 'pending', "
            ":pd, :nt)",
            id=new_id, lid=tr['league_id'], slug=new_slug,
            a=tr['team_b_id'], b=tr['team_a_id'],
            pa=players_a, pb=players_b, pd=DEMO_DATE_R6(), nt=note)
        return _r6_render_success(
            'Counter offer sent',
            f'Counter offer recorded — original trade {trade_slug} marked '
            'countered.',
            back_url='/r4/fantasy',
            back_label='Fantasy hub')
    return render_template('r6_trade_form.html',
                            league=_r45_row(
                                "SELECT * FROM r4_fantasy_leagues "
                                "WHERE id=:i", i=tr['league_id']),
                            teams=_r45_rows(
                                "SELECT * FROM r4_fantasy_teams "
                                "WHERE league_id=:lid ORDER BY id",
                                lid=tr['league_id']),
                            mode='counter', original_trade=tr)


# ─── Fantasy league lifecycle ────────────────────────────────────────────────

@app.route('/fantasy/league/create', methods=['GET', 'POST'])
def r6_league_create():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        sport = request.form.get('sport_slug', 'nfl').strip()
        size = int(request.form.get('league_size', '10') or '10')
        scoring = request.form.get('scoring_type', 'PPR').strip()
        if not name:
            flash('Pick a league name.', 'danger')
            return redirect(request.url)
        slug = re.sub(r'[^a-z0-9-]+', '-', name.lower()).strip('-') + f'-{sport}'
        existing = _r45_row(
            "SELECT id FROM r4_fantasy_leagues WHERE slug=:s", s=slug)
        if existing:
            slug = f'{slug}-{hashlib.md5(name.encode()).hexdigest()[:6]}'
        new_id = (_r45_row(
            "SELECT COALESCE(MAX(id),0)+1 AS n "
            "FROM r4_fantasy_leagues") or {}).get('n', 1)
        _r6_exec(
            "INSERT INTO r4_fantasy_leagues "
            "(id, slug, name, sport_slug, season, league_size, scoring_type, "
            "roster_size, current_week, is_public) "
            "VALUES (:id, :slug, :name, :sport, '2024-25', :sz, :sc, 16, 1, 1)",
            id=new_id, slug=slug, name=name, sport=sport, sz=size, sc=scoring)
        return _r6_render_success(
            'League created',
            f'Your new league "{name}" is ready.',
            back_url=f'/r4/fantasy/league/{slug}',
            back_label='Open league')
    return render_template('r6_league_create.html')


@app.route('/fantasy/league/<league_slug>/invite', methods=['GET', 'POST'])
def r6_league_invite(league_slug):
    lg = _r45_row(
        "SELECT * FROM r4_fantasy_leagues WHERE slug=:s", s=league_slug)
    if not lg:
        abort(404)
    if request.method == 'POST':
        recipient = request.form.get('recipient_email', '').strip()
        message = request.form.get('message', '').strip()
        code = hashlib.md5(
            (league_slug + recipient + _r6_now()).encode()
        ).hexdigest()[:8].upper()
        new_id = (_r45_row(
            "SELECT COALESCE(MAX(id),0)+1 AS n "
            "FROM r6_league_invites") or {}).get('n', 1)
        _r6_exec(
            "INSERT INTO r6_league_invites "
            "(id, league_slug, invite_code, recipient_email, message, "
            "status, sent_at) "
            "VALUES (:id, :ls, :code, :r, :m, 'pending', :ts)",
            id=new_id, ls=league_slug, code=code, r=recipient, m=message,
            ts=_r6_now())
        return _r6_render_success(
            'Invite sent',
            f'Invite code {code} sent to {recipient}.',
            back_url=f'/r4/fantasy/league/{league_slug}',
            back_label='Back to league')
    return render_template('r6_league_invite.html', league=lg)


@app.route('/fantasy/league/<league_slug>/join', methods=['GET', 'POST'])
def r6_league_join(league_slug):
    lg = _r45_row(
        "SELECT * FROM r4_fantasy_leagues WHERE slug=:s", s=league_slug)
    if not lg:
        abort(404)
    if request.method == 'POST':
        team_name = request.form.get('team_name', 'My New Team').strip()
        manager = request.form.get('manager_name', _r6_actor()[1]).strip()
        invite_code = request.form.get('invite_code', '').strip()
        # Validate invite_code lazily: accept the empty/default for public
        # leagues (is_public=1) — otherwise require a known code.
        if not lg['is_public'] and invite_code:
            ok = _r45_row(
                "SELECT id FROM r6_league_invites WHERE league_slug=:ls "
                "AND invite_code=:c AND status='pending'",
                ls=league_slug, c=invite_code)
            if not ok:
                flash('Invite code not recognized.', 'danger')
                return redirect(request.url)
        new_id = (_r45_row(
            "SELECT COALESCE(MAX(id),0)+1 AS n "
            "FROM r4_fantasy_teams") or {}).get('n', 1)
        slug = re.sub(r'[^a-z0-9-]+', '-', team_name.lower()).strip('-')
        slug = f'{slug}-l{lg["id"]}-t{new_id}'
        _r6_exec(
            "INSERT INTO r4_fantasy_teams "
            "(id, league_id, slug, team_name, manager_name, wins, losses, "
            "ties, points_for, points_against, rank, waiver_priority, "
            "moves_used) "
            "VALUES (:id, :lid, :slug, :tn, :mg, 0, 0, 0, 0.0, 0.0, "
            ":rk, :wp, 0)",
            id=new_id, lid=lg['id'], slug=slug, tn=team_name, mg=manager,
            rk=lg['league_size'] + 1, wp=lg['league_size'] + 1)
        return _r6_render_success(
            'Welcome to the league',
            f'{team_name} joined {lg["name"]} (managed by {manager}).',
            back_url=f'/r4/fantasy/league/{league_slug}',
            back_label='Open league')
    return render_template('r6_league_join.html', league=lg)


@app.route('/fantasy/league/<league_slug>/draft/pick',
           methods=['GET', 'POST'])
def r6_league_draft_pick(league_slug):
    lg = _r45_row(
        "SELECT * FROM r4_fantasy_leagues WHERE slug=:s", s=league_slug)
    if not lg:
        abort(404)
    teams = _r45_rows(
        "SELECT * FROM r4_fantasy_teams WHERE league_id=:lid ORDER BY id",
        lid=lg['id'])
    picks_so_far = _r45_rows(
        "SELECT * FROM r6_draft_picks WHERE league_slug=:s "
        "ORDER BY pick_num DESC LIMIT 20", s=league_slug)
    if request.method == 'POST':
        team_slug = request.form.get('team_slug', '').strip()
        player_name = request.form.get('player_name', '').strip()
        player_pos = request.form.get('player_pos', '').strip()
        nfl_abbr = request.form.get('nfl_team_abbr', '').strip()
        if not (team_slug and player_name):
            flash('Pick a team and a player.', 'danger')
            return redirect(request.url)
        tm = _r45_row("SELECT * FROM r4_fantasy_teams WHERE slug=:s",
                      s=team_slug)
        if not tm:
            flash('Team not found.', 'danger')
            return redirect(request.url)
        next_pick = (_r45_row(
            "SELECT COALESCE(MAX(pick_num),0)+1 AS n "
            "FROM r6_draft_picks WHERE league_slug=:s",
            s=league_slug) or {}).get('n', 1)
        round_num = ((next_pick - 1) // lg['league_size']) + 1
        new_id = (_r45_row(
            "SELECT COALESCE(MAX(id),0)+1 AS n FROM r6_draft_picks"
        ) or {}).get('n', 1)
        _r6_exec(
            "INSERT INTO r6_draft_picks "
            "(id, league_slug, pick_num, round_num, team_slug, team_name, "
            "player_name, player_pos, nfl_team_abbr, picked_at) "
            "VALUES (:id, :ls, :pn, :rn, :ts, :tn, :pl, :pp, :ab, :ts2)",
            id=new_id, ls=league_slug, pn=next_pick, rn=round_num,
            ts=team_slug, tn=tm['team_name'], pl=player_name, pp=player_pos,
            ab=nfl_abbr, ts2=_r6_now())
        flash(f'Pick #{next_pick} ({player_name}) recorded.', 'success')
        return redirect(url_for('r6_league_draft_pick',
                                 league_slug=league_slug))
    return render_template('r6_league_draft_room.html',
                            league=lg, teams=teams, picks=picks_so_far)


@app.route('/fantasy/league/<league_slug>/settings/update',
           methods=['GET', 'POST'])
def r6_league_settings(league_slug):
    lg = _r45_row(
        "SELECT * FROM r4_fantasy_leagues WHERE slug=:s", s=league_slug)
    if not lg:
        abort(404)
    if request.method == 'POST':
        scoring = request.form.get('scoring_type', lg['scoring_type'])
        roster_size = int(request.form.get('roster_size',
                                            lg['roster_size']) or
                          lg['roster_size'])
        current_week = int(request.form.get('current_week',
                                              lg['current_week']) or
                           lg['current_week'])
        _r6_exec(
            "UPDATE r4_fantasy_leagues SET scoring_type=:sc, "
            "roster_size=:rs, current_week=:cw WHERE slug=:s",
            sc=scoring, rs=roster_size, cw=current_week, s=league_slug)
        return _r6_render_success(
            'Settings saved',
            f'League settings updated for {lg["name"]}.',
            back_url=f'/r4/fantasy/league/{league_slug}',
            back_label='Back to league')
    return render_template('r6_league_settings.html', league=lg)


@app.route('/fantasy/team/<team_slug>/rename', methods=['GET', 'POST'])
def r6_team_rename(team_slug):
    tm = _r6_lookup_team_full(team_slug)
    if not tm:
        abort(404)
    if request.method == 'POST':
        new_name = request.form.get('team_name', '').strip()
        if not new_name:
            flash('Pick a new team name.', 'danger')
            return redirect(request.url)
        old_name = tm['team_name']
        email, _name = _r6_actor()
        _r6_exec(
            "UPDATE r4_fantasy_teams SET team_name=:n WHERE slug=:s",
            n=new_name, s=team_slug)
        _r6_exec(
            "INSERT INTO r6_team_audit (team_slug, change_kind, old_value, "
            "new_value, actor_email, changed_at) "
            "VALUES (:t, 'rename', :o, :n, :a, :ts)",
            t=team_slug, o=old_name, n=new_name, a=email, ts=_r6_now())
        return _r6_render_success(
            'Team renamed',
            f'Renamed "{old_name}" → "{new_name}".',
            back_url=f'/r4/fantasy/lineup/{team_slug}',
            back_label='Back to team')
    return render_template('r6_team_rename.html', team=tm)


@app.route('/fantasy/team/<team_slug>/avatar/upload',
           methods=['GET', 'POST'])
def r6_team_avatar(team_slug):
    tm = _r6_lookup_team_full(team_slug)
    if not tm:
        abort(404)
    if request.method == 'POST':
        # We don't actually persist uploaded bytes (no static-asset writes in
        # the mirror) — we record the audit only.
        avatar_label = request.form.get('avatar_label', 'custom').strip()
        email, _name = _r6_actor()
        _r6_exec(
            "INSERT INTO r6_team_audit (team_slug, change_kind, old_value, "
            "new_value, actor_email, changed_at) "
            "VALUES (:t, 'avatar', 'default', :n, :a, :ts)",
            t=team_slug, n=avatar_label, a=email, ts=_r6_now())
        return _r6_render_success(
            'Avatar updated',
            f'New avatar "{avatar_label}" saved for {tm["team_name"]}.',
            back_url=f'/r4/fantasy/lineup/{team_slug}',
            back_label='Back to team')
    return render_template('r6_team_avatar.html', team=tm)


# ─── Bracket picks + pools ───────────────────────────────────────────────────

@app.route('/bracket/<bracket_slug>/pick/<int:matchup_id>',
           methods=['GET', 'POST'])
def r6_bracket_pick(bracket_slug, matchup_id):
    br = _r45_row(
        "SELECT * FROM r5_brackets WHERE slug=:s", s=bracket_slug)
    matchup = _r45_row(
        "SELECT * FROM r5_bracket_matchups WHERE id=:i", i=matchup_id)
    if not (br and matchup):
        abort(404)
    if request.method == 'POST':
        picked_team = request.form.get('picked_team', '').strip()
        pool_slug = request.form.get('pool_slug', '').strip() or None
        if not picked_team:
            flash('Pick a team.', 'danger')
            return redirect(request.url)
        email, _name = _r6_actor()
        # Idempotent: delete existing pick for (user, bracket, matchup) first
        _r6_exec(
            "DELETE FROM r6_bracket_picks WHERE user_email=:e "
            "AND bracket_slug=:b AND matchup_id=:m",
            e=email, b=bracket_slug, m=matchup_id)
        new_id = (_r45_row(
            "SELECT COALESCE(MAX(id),0)+1 AS n FROM r6_bracket_picks"
        ) or {}).get('n', 1)
        _r6_exec(
            "INSERT INTO r6_bracket_picks "
            "(id, user_email, bracket_slug, pool_slug, matchup_id, "
            "picked_team, round_num, is_champion_pick, tiebreaker_score, "
            "is_locked, picked_at) "
            "VALUES (:id, :e, :b, :p, :m, :pt, :rn, 0, NULL, 0, :ts)",
            id=new_id, e=email, b=bracket_slug, p=pool_slug, m=matchup_id,
            pt=picked_team, rn=matchup['round_num'], ts=_r6_now())
        return _r6_render_success(
            'Pick saved',
            f'{picked_team} is your pick for round {matchup["round_num"]} '
            f'matchup {matchup_id}.',
            back_url=f'/r5/bracket/{bracket_slug}',
            back_label='Back to bracket')
    return render_template('r6_bracket_pick.html',
                            bracket=br, matchup=matchup)


@app.route('/bracket/<bracket_slug>/champion-pick',
           methods=['GET', 'POST'])
def r6_bracket_champion(bracket_slug):
    br = _r45_row(
        "SELECT * FROM r5_brackets WHERE slug=:s", s=bracket_slug)
    if not br:
        abort(404)
    seeds = _r45_rows(
        "SELECT * FROM r5_bracket_seeds WHERE bracket_id=:b "
        "ORDER BY seed_num, region", b=br['id'])
    if request.method == 'POST':
        team = request.form.get('champion_team', '').strip()
        pool_slug = request.form.get('pool_slug', '').strip() or None
        if not team:
            flash('Pick a champion.', 'danger')
            return redirect(request.url)
        email, _name = _r6_actor()
        _r6_exec(
            "DELETE FROM r6_bracket_picks WHERE user_email=:e "
            "AND bracket_slug=:b AND is_champion_pick=1",
            e=email, b=bracket_slug)
        new_id = (_r45_row(
            "SELECT COALESCE(MAX(id),0)+1 AS n FROM r6_bracket_picks"
        ) or {}).get('n', 1)
        _r6_exec(
            "INSERT INTO r6_bracket_picks "
            "(id, user_email, bracket_slug, pool_slug, matchup_id, "
            "picked_team, round_num, is_champion_pick, tiebreaker_score, "
            "is_locked, picked_at) "
            "VALUES (:id, :e, :b, :p, NULL, :pt, 7, 1, NULL, 0, :ts)",
            id=new_id, e=email, b=bracket_slug, p=pool_slug, pt=team,
            ts=_r6_now())
        return _r6_render_success(
            'Champion pick saved',
            f'Your 2024 champion: {team}.',
            back_url=f'/r5/bracket/{bracket_slug}',
            back_label='Back to bracket')
    return render_template('r6_bracket_champion.html',
                            bracket=br, seeds=seeds)


@app.route('/bracket/<bracket_slug>/submit', methods=['GET', 'POST'])
def r6_bracket_submit(bracket_slug):
    br = _r45_row(
        "SELECT * FROM r5_brackets WHERE slug=:s", s=bracket_slug)
    if not br:
        abort(404)
    email, _name = _r6_actor()
    n_picks = (_r45_row(
        "SELECT COUNT(*) AS n FROM r6_bracket_picks "
        "WHERE user_email=:e AND bracket_slug=:b",
        e=email, b=bracket_slug) or {}).get('n', 0)
    if request.method == 'POST':
        _r6_exec(
            "UPDATE r6_bracket_picks SET is_locked=1 "
            "WHERE user_email=:e AND bracket_slug=:b",
            e=email, b=bracket_slug)
        return _r6_render_success(
            'Bracket locked',
            f'Your bracket for {br["name"]} is submitted and locked '
            f'({n_picks} picks).',
            back_url=f'/r5/bracket/{bracket_slug}',
            back_label='Back to bracket')
    return render_template('r6_bracket_submit.html',
                            bracket=br, n_picks=n_picks)


@app.route('/bracket/<bracket_slug>/lock-tiebreaker',
           methods=['GET', 'POST'])
def r6_bracket_tiebreaker(bracket_slug):
    br = _r45_row(
        "SELECT * FROM r5_brackets WHERE slug=:s", s=bracket_slug)
    if not br:
        abort(404)
    if request.method == 'POST':
        tb = int(request.form.get('tiebreaker_score', '120') or '120')
        email, _name = _r6_actor()
        _r6_exec(
            "UPDATE r6_bracket_picks SET tiebreaker_score=:tb "
            "WHERE user_email=:e AND bracket_slug=:b "
            "AND is_champion_pick=1",
            tb=tb, e=email, b=bracket_slug)
        return _r6_render_success(
            'Tiebreaker locked',
            f'Tiebreaker total set to {tb} for {br["name"]}.',
            back_url=f'/r5/bracket/{bracket_slug}',
            back_label='Back to bracket')
    return render_template('r6_bracket_tiebreaker.html', bracket=br)


@app.route('/bracket-pool/create', methods=['GET', 'POST'])
def r6_bracket_pool_create():
    brackets = _r45_rows(
        "SELECT * FROM r5_brackets ORDER BY id")
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        bracket_slug = request.form.get('bracket_slug', '').strip()
        scoring = request.form.get('scoring', 'standard').strip()
        if not (name and bracket_slug):
            flash('Pick a pool name and a bracket.', 'danger')
            return redirect(request.url)
        slug = re.sub(r'[^a-z0-9-]+', '-', name.lower()).strip('-')
        if not slug:
            slug = 'pool'
        slug = f'{slug}-{hashlib.md5((name+bracket_slug).encode()).hexdigest()[:6]}'
        invite_code = hashlib.md5(
            (slug + _r6_now()).encode()).hexdigest()[:8].upper()
        new_id = (_r45_row(
            "SELECT COALESCE(MAX(id),0)+1 AS n FROM r6_bracket_pools"
        ) or {}).get('n', 1)
        email, name_who = _r6_actor()
        _r6_exec(
            "INSERT INTO r6_bracket_pools "
            "(id, slug, bracket_slug, name, owner_email, scoring, is_locked, "
            "member_count, created_at, invite_code) "
            "VALUES (:id, :slug, :bs, :nm, :e, :sc, 0, 1, :ts, :ic)",
            id=new_id, slug=slug, bs=bracket_slug, nm=name, e=email,
            sc=scoring, ts=_r6_now(), ic=invite_code)
        # Auto-add owner as first member
        mem_id = (_r45_row(
            "SELECT COALESCE(MAX(id),0)+1 AS n "
            "FROM r6_bracket_pool_members") or {}).get('n', 1)
        _r6_exec(
            "INSERT INTO r6_bracket_pool_members "
            "(id, pool_id, user_email, display_name, joined_at, score) "
            "VALUES (:id, :pid, :e, :nm, :ts, 0)",
            id=mem_id, pid=new_id, e=email, nm=name_who, ts=_r6_now())
        return _r6_render_success(
            'Pool created',
            f'Pool "{name}" created. Invite code: {invite_code}.',
            back_url='/r5/bracket',
            back_label='Bracket hub')
    return render_template('r6_bracket_pool_create.html', brackets=brackets)


@app.route('/bracket-pool/<pool_slug>/join', methods=['GET', 'POST'])
def r6_bracket_pool_join(pool_slug):
    pool = _r45_row(
        "SELECT * FROM r6_bracket_pools WHERE slug=:s", s=pool_slug)
    if not pool:
        abort(404)
    if request.method == 'POST':
        display = request.form.get('display_name', _r6_actor()[1]).strip()
        email = (request.form.get('email', '').strip() or _r6_actor()[0])
        invite = request.form.get('invite_code', '').strip().upper()
        if pool['invite_code'] and invite and invite != pool['invite_code']:
            flash('Invite code does not match.', 'danger')
            return redirect(request.url)
        # Already a member?
        existing = _r45_row(
            "SELECT id FROM r6_bracket_pool_members "
            "WHERE pool_id=:p AND user_email=:e",
            p=pool['id'], e=email)
        if existing:
            return _r6_render_success(
                'Already in this pool',
                f'{email} is already a member of {pool["name"]}.',
                back_url=f'/bracket-pool/{pool_slug}/join',
                back_label='Back')
        new_id = (_r45_row(
            "SELECT COALESCE(MAX(id),0)+1 AS n "
            "FROM r6_bracket_pool_members") or {}).get('n', 1)
        _r6_exec(
            "INSERT INTO r6_bracket_pool_members "
            "(id, pool_id, user_email, display_name, joined_at, score) "
            "VALUES (:id, :pid, :e, :nm, :ts, 0)",
            id=new_id, pid=pool['id'], e=email, nm=display, ts=_r6_now())
        _r6_exec(
            "UPDATE r6_bracket_pools SET member_count=member_count+1 "
            "WHERE id=:p", p=pool['id'])
        return _r6_render_success(
            'Joined pool',
            f'{display} joined {pool["name"]}.',
            back_url=f'/r5/bracket/{pool["bracket_slug"]}',
            back_label='Open bracket')
    return render_template('r6_bracket_pool_join.html', pool=pool)


@app.route('/bracket-pool/<pool_slug>/invite', methods=['GET', 'POST'])
def r6_bracket_pool_invite(pool_slug):
    pool = _r45_row(
        "SELECT * FROM r6_bracket_pools WHERE slug=:s", s=pool_slug)
    if not pool:
        abort(404)
    if request.method == 'POST':
        recipient = request.form.get('recipient_email', '').strip()
        message = request.form.get('message', '').strip()
        new_id = (_r45_row(
            "SELECT COALESCE(MAX(id),0)+1 AS n FROM r6_league_invites"
        ) or {}).get('n', 1)
        _r6_exec(
            "INSERT INTO r6_league_invites "
            "(id, league_slug, invite_code, recipient_email, message, "
            "status, sent_at) "
            "VALUES (:id, :ls, :code, :r, :m, 'pending', :ts)",
            id=new_id, ls=f'pool:{pool_slug}',
            code=pool['invite_code'] or 'POOL', r=recipient, m=message,
            ts=_r6_now())
        return _r6_render_success(
            'Pool invite sent',
            f'Pool invite to {recipient} queued (code: '
            f'{pool["invite_code"]}).',
            back_url=f'/r5/bracket/{pool["bracket_slug"]}',
            back_label='Back to bracket')
    return render_template('r6_bracket_pool_invite.html', pool=pool)


# ─── Community: comments / follows / watchlist / alerts / polls ───────────────

@app.route('/article/<article_slug>/comment', methods=['GET', 'POST'])
def r6_article_comment(article_slug):
    art = _r45_row(
        "SELECT * FROM articles WHERE slug=:s", s=article_slug)
    if not art:
        abort(404)
    comments = _r45_rows(
        "SELECT * FROM r6_comments WHERE article_slug=:s "
        "AND parent_id IS NULL ORDER BY id DESC LIMIT 20", s=article_slug)
    if request.method == 'POST':
        body = request.form.get('body', '').strip()
        if not body or len(body) < 3:
            flash('Comment is too short.', 'danger')
            return redirect(request.url)
        email, name = _r6_actor()
        new_id = (_r45_row(
            "SELECT COALESCE(MAX(id),0)+1 AS n FROM r6_comments"
        ) or {}).get('n', 1)
        _r6_exec(
            "INSERT INTO r6_comments "
            "(id, article_slug, parent_id, author_name, author_email, body, "
            "upvotes, created_at, is_flagged) "
            "VALUES (:id, :a, NULL, :nm, :e, :b, 0, :ts, 0)",
            id=new_id, a=article_slug, nm=name, e=email, b=body,
            ts=_r6_now())
        flash('Comment posted.', 'success')
        return redirect(request.url)
    return render_template('r6_article_comment.html',
                            article=art, comments=comments)


@app.route('/comment/<int:comment_id>/upvote', methods=['GET', 'POST'])
def r6_comment_upvote(comment_id):
    c = _r45_row(
        "SELECT * FROM r6_comments WHERE id=:i", i=comment_id)
    if not c:
        abort(404)
    if request.method == 'POST':
        _r6_exec(
            "UPDATE r6_comments SET upvotes=upvotes+1 WHERE id=:i",
            i=comment_id)
        nxt = request.form.get('next') or url_for(
            'r6_article_comment', article_slug=c['article_slug'])
        return redirect(nxt)
    return render_template('r6_comment_upvote.html', comment=c)


@app.route('/comment/<int:comment_id>/reply', methods=['GET', 'POST'])
def r6_comment_reply(comment_id):
    parent = _r45_row(
        "SELECT * FROM r6_comments WHERE id=:i", i=comment_id)
    if not parent:
        abort(404)
    if request.method == 'POST':
        body = request.form.get('body', '').strip()
        if not body or len(body) < 3:
            flash('Reply is too short.', 'danger')
            return redirect(request.url)
        email, name = _r6_actor()
        new_id = (_r45_row(
            "SELECT COALESCE(MAX(id),0)+1 AS n FROM r6_comments"
        ) or {}).get('n', 1)
        _r6_exec(
            "INSERT INTO r6_comments "
            "(id, article_slug, parent_id, author_name, author_email, body, "
            "upvotes, created_at, is_flagged) "
            "VALUES (:id, :a, :p, :nm, :e, :b, 0, :ts, 0)",
            id=new_id, a=parent['article_slug'], p=comment_id, nm=name,
            e=email, b=body, ts=_r6_now())
        return _r6_render_success(
            'Reply posted',
            f'Reply added to comment #{comment_id}.',
            back_url=f'/article/{parent["article_slug"]}/comment',
            back_label='Back to article')
    return render_template('r6_comment_reply.html', parent=parent)


@app.route('/team/<sport_slug>/<team_slug>/follow', methods=['GET', 'POST'])
def r6_team_follow(sport_slug, team_slug):
    team = _r45_row(
        "SELECT * FROM teams WHERE sport_slug=:s AND slug=:t",
        s=sport_slug, t=team_slug)
    if not team:
        abort(404)
    if request.method == 'POST':
        email, _name = _r6_actor()
        existing = _r45_row(
            "SELECT id FROM r6_follows WHERE user_email=:e "
            "AND entity_kind='team' AND entity_slug=:s",
            e=email, s=team_slug)
        if not existing:
            new_id = (_r45_row(
                "SELECT COALESCE(MAX(id),0)+1 AS n FROM r6_follows"
            ) or {}).get('n', 1)
            _r6_exec(
                "INSERT INTO r6_follows "
                "(id, user_email, entity_kind, entity_sport, entity_slug, "
                "followed_at) "
                "VALUES (:id, :e, 'team', :sp, :sl, :ts)",
                id=new_id, e=email, sp=sport_slug, sl=team_slug,
                ts=_r6_now())
        return _r6_render_success(
            'Following team',
            f'You are now following {team["full_name"]}.',
            back_url=f'/team/{sport_slug}/{team_slug}',
            back_label='Back to team')
    return render_template('r6_follow_confirm.html',
                            entity_kind='team', entity=team)


@app.route('/player/<sport_slug>/<player_slug>/follow',
           methods=['GET', 'POST'])
def r6_player_follow(sport_slug, player_slug):
    player = _r45_row(
        "SELECT * FROM players WHERE sport_slug=:s AND slug=:p",
        s=sport_slug, p=player_slug)
    if not player:
        abort(404)
    if request.method == 'POST':
        email, _name = _r6_actor()
        existing = _r45_row(
            "SELECT id FROM r6_follows WHERE user_email=:e "
            "AND entity_kind='player' AND entity_slug=:s",
            e=email, s=player_slug)
        if not existing:
            new_id = (_r45_row(
                "SELECT COALESCE(MAX(id),0)+1 AS n FROM r6_follows"
            ) or {}).get('n', 1)
            _r6_exec(
                "INSERT INTO r6_follows "
                "(id, user_email, entity_kind, entity_sport, entity_slug, "
                "followed_at) "
                "VALUES (:id, :e, 'player', :sp, :sl, :ts)",
                id=new_id, e=email, sp=sport_slug, sl=player_slug,
                ts=_r6_now())
        return _r6_render_success(
            'Following player',
            f'You are now following {player["name"]}.',
            back_url=f'/player/{sport_slug}/{player_slug}',
            back_label='Back to player')
    return render_template('r6_follow_confirm.html',
                            entity_kind='player', entity=player)


@app.route('/watchlist/add', methods=['GET', 'POST'])
def r6_watchlist_add():
    if request.method == 'POST':
        kind = request.form.get('kind', 'team').strip()
        ref_slug = request.form.get('ref_slug', '').strip()
        label = request.form.get('label', '').strip()
        if not ref_slug:
            flash('Pick something to watch.', 'danger')
            return redirect(request.url)
        email, _name = _r6_actor()
        new_id = (_r45_row(
            "SELECT COALESCE(MAX(id),0)+1 AS n FROM r6_watchlist"
        ) or {}).get('n', 1)
        _r6_exec(
            "INSERT INTO r6_watchlist "
            "(id, user_email, kind, ref_slug, label, added_at) "
            "VALUES (:id, :e, :k, :r, :l, :ts)",
            id=new_id, e=email, k=kind, r=ref_slug, l=label, ts=_r6_now())
        return _r6_render_success(
            'Added to watchlist',
            f'{label or ref_slug} added to your watchlist.',
            back_url='/watch', back_label='Back to Watch')
    return render_template('r6_watchlist_form.html')


@app.route('/alert/subscribe', methods=['GET', 'POST'])
def r6_alert_subscribe():
    if request.method == 'POST':
        alert_kind = request.form.get('alert_kind', 'game-start').strip()
        ref_slug = request.form.get('ref_slug', '').strip()
        channel = request.form.get('channel', 'push').strip()
        if not ref_slug:
            flash('Pick something to be alerted about.', 'danger')
            return redirect(request.url)
        email, _name = _r6_actor()
        new_id = (_r45_row(
            "SELECT COALESCE(MAX(id),0)+1 AS n FROM r6_alerts"
        ) or {}).get('n', 1)
        _r6_exec(
            "INSERT INTO r6_alerts "
            "(id, user_email, alert_kind, ref_slug, channel, is_active, "
            "subscribed_at) "
            "VALUES (:id, :e, :k, :r, :c, 1, :ts)",
            id=new_id, e=email, k=alert_kind, r=ref_slug, c=channel,
            ts=_r6_now())
        return _r6_render_success(
            'Alert active',
            f'You will receive {alert_kind} alerts for {ref_slug} via '
            f'{channel}.',
            back_url='/account', back_label='Account')
    return render_template('r6_alert_subscribe.html')


@app.route('/poll/<int:poll_id>/vote', methods=['GET', 'POST'])
def r6_poll_vote(poll_id):
    poll = _r45_row("SELECT * FROM r6_polls WHERE id=:i", i=poll_id)
    if not poll:
        abort(404)
    options = _r45_rows(
        "SELECT * FROM r6_poll_options WHERE poll_id=:i ORDER BY position",
        i=poll_id)
    if request.method == 'POST':
        option_id = int(request.form.get('option_id', '0') or '0')
        if not option_id:
            flash('Pick an option.', 'danger')
            return redirect(request.url)
        opt = _r45_row(
            "SELECT * FROM r6_poll_options WHERE id=:i AND poll_id=:p",
            i=option_id, p=poll_id)
        if not opt:
            abort(400)
        email, _name = _r6_actor()
        existing = _r45_row(
            "SELECT id FROM r6_poll_votes WHERE poll_id=:p "
            "AND user_email=:e", p=poll_id, e=email)
        if existing:
            # Update vote (move count from old option to new)
            old = _r45_row(
                "SELECT option_id FROM r6_poll_votes WHERE id=:i",
                i=existing['id'])
            if old and old['option_id'] != option_id:
                _r6_exec(
                    "UPDATE r6_poll_options SET votes=votes-1 WHERE id=:i",
                    i=old['option_id'])
                _r6_exec(
                    "UPDATE r6_poll_options SET votes=votes+1 WHERE id=:i",
                    i=option_id)
                _r6_exec(
                    "UPDATE r6_poll_votes SET option_id=:o, voted_at=:ts "
                    "WHERE id=:i", o=option_id, ts=_r6_now(),
                    i=existing['id'])
        else:
            new_id = (_r45_row(
                "SELECT COALESCE(MAX(id),0)+1 AS n FROM r6_poll_votes"
            ) or {}).get('n', 1)
            _r6_exec(
                "INSERT INTO r6_poll_votes "
                "(id, poll_id, option_id, user_email, voted_at) "
                "VALUES (:id, :p, :o, :e, :ts)",
                id=new_id, p=poll_id, o=option_id, e=email, ts=_r6_now())
            _r6_exec(
                "UPDATE r6_poll_options SET votes=votes+1 WHERE id=:i",
                i=option_id)
        return _r6_render_success(
            'Vote recorded',
            f'Your vote for "{opt["label"]}" is in.',
            back_url=f'/poll/{poll_id}/vote', back_label='See results')
    return render_template('r6_poll_detail.html',
                            poll=poll, options=options)


# === R6 GUI POST surface END ════════════════════════════════════════════════


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        seed_database()
        seed_benchmark_users()
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
