#!/usr/bin/env python3
"""NBA.com mirror - Flask app with teams, scores, news, tickets, shop, and account flows."""
import json
import os
import random as _rand
import re
from datetime import datetime, timedelta

from flask import Flask, abort, flash, redirect, render_template, request, url_for
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, UserMixin, current_user, login_required, login_user, logout_user
from flask_sqlalchemy import SQLAlchemy


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MIRROR_REFERENCE_DATE = datetime(2026, 5, 15, 12, 0, 0)
STOP_WORDS = {
    "the", "a", "an", "and", "or", "for", "of", "to", "in", "on", "at", "by",
    "with", "from", "find", "show", "me", "my", "nba",
}
DIVISION_ORDER = ["Atlantic", "Central", "Southeast", "Northwest", "Pacific", "Southwest"]
NEWS_CATEGORIES = [
    "Top Stories", "Draft", "Playoffs", "Awards", "Transactions", "History",
    "Around the NBA", "Preview", "Analysis", "Features", "Video", "Highlights",
]
PLAYER_STAT_FIELDS = {
    "ppg": "Points",
    "rpg": "Rebounds",
    "apg": "Assists",
    "bpg": "Blocks",
    "spg": "Steals",
    "topg": "Turnovers",
}

app = Flask(__name__, instance_path=os.path.join(BASE_DIR, "instance"))
app.config["SECRET_KEY"] = "webharbor-nba-dev-key"
app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{os.path.join(BASE_DIR, 'instance', 'nba.db')}"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
os.makedirs(os.path.join(BASE_DIR, "instance"), exist_ok=True)

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = "login"
login_manager.login_message = "Sign in to use your NBA ID."


def slugify(value):
    value = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return value or "item"


def tokens_for(query):
    return [t for t in re.split(r"\W+", query.lower()) if len(t) > 1 and t not in STOP_WORDS]


def scored_search(query, items, fields):
    tokens = tokens_for(query)
    if not tokens:
        return list(items)
    scored = []
    for item in items:
        text = " ".join(str(getattr(item, field, "") or "") for field in fields).lower()
        score = sum(1 for token in tokens if token in text)
        if score:
            scored.append((item, score))
    scored.sort(key=lambda row: (-row[1], getattr(row[0], "name", getattr(row[0], "title", ""))))
    return [item for item, _score in scored]


class User(db.Model, UserMixin):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    display_name = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(30), default="")
    address_line1 = db.Column(db.String(160), default="")
    city = db.Column(db.String(80), default="")
    state = db.Column(db.String(40), default="")
    zip_code = db.Column(db.String(20), default="")
    favorite_team_slug = db.Column(db.String(80), default="")
    payment_last4 = db.Column(db.String(4), default="4242")
    created_at = db.Column(db.DateTime, default=MIRROR_REFERENCE_DATE)

    cart_items = db.relationship("CartItem", backref="user", cascade="all, delete-orphan")
    orders = db.relationship("Order", backref="user", cascade="all, delete-orphan")
    favorites = db.relationship("Favorite", backref="user", cascade="all, delete-orphan")
    ticket_requests = db.relationship("TicketRequest", backref="user", cascade="all, delete-orphan")

    def set_password(self, password):
        self.password_hash = bcrypt.generate_password_hash(password).decode("utf-8")

    def check_password(self, password):
        return bcrypt.check_password_hash(self.password_hash, password)


class Team(db.Model):
    __tablename__ = "teams"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    city = db.Column(db.String(80), default="")
    slug = db.Column(db.String(80), unique=True, nullable=False, index=True)
    abbreviation = db.Column(db.String(4), default="")
    conference = db.Column(db.String(20), index=True)
    division = db.Column(db.String(40))
    wins = db.Column(db.Integer, default=0)
    losses = db.Column(db.Integer, default=0)
    home_record = db.Column(db.String(12), default="")
    road_record = db.Column(db.String(12), default="")
    streak = db.Column(db.String(12), default="")
    ppg = db.Column(db.Float, default=0)
    oppg = db.Column(db.Float, default=0)
    arena = db.Column(db.String(120), default="")
    coach = db.Column(db.String(120), default="")
    color = db.Column(db.String(20), default="#17408b")
    logo = db.Column(db.String(160), default="")

    players = db.relationship("Player", backref="team", cascade="all, delete-orphan")

    @property
    def full_name(self):
        return f"{self.city} {self.name}".strip()

    @property
    def win_pct(self):
        total = self.wins + self.losses
        return round(self.wins / total, 3) if total else 0


class Player(db.Model):
    __tablename__ = "players"
    id = db.Column(db.Integer, primary_key=True)
    team_id = db.Column(db.Integer, db.ForeignKey("teams.id"), nullable=False)
    name = db.Column(db.String(120), nullable=False)
    slug = db.Column(db.String(140), unique=True, nullable=False, index=True)
    position = db.Column(db.String(20), default="")
    jersey = db.Column(db.String(8), default="")
    height = db.Column(db.String(20), default="")
    weight = db.Column(db.Integer, default=0)
    age = db.Column(db.Integer, default=0)
    country = db.Column(db.String(60), default="USA")
    college = db.Column(db.String(80), default="")
    ppg = db.Column(db.Float, default=0)
    rpg = db.Column(db.Float, default=0)
    apg = db.Column(db.Float, default=0)
    spg = db.Column(db.Float, default=0)
    bpg = db.Column(db.Float, default=0)
    fg_pct = db.Column(db.Float, default=0)
    three_pct = db.Column(db.Float, default=0)
    bio = db.Column(db.Text, default="")
    image = db.Column(db.String(180), default="")


class Game(db.Model):
    __tablename__ = "games"
    id = db.Column(db.Integer, primary_key=True)
    game_date = db.Column(db.DateTime, nullable=False)
    home_team_id = db.Column(db.Integer, db.ForeignKey("teams.id"), nullable=False)
    away_team_id = db.Column(db.Integer, db.ForeignKey("teams.id"), nullable=False)
    home_score = db.Column(db.Integer, nullable=True)
    away_score = db.Column(db.Integer, nullable=True)
    status = db.Column(db.String(30), default="Scheduled")
    arena = db.Column(db.String(120), default="")
    broadcast = db.Column(db.String(80), default="")
    recap = db.Column(db.Text, default="")
    ticket_price = db.Column(db.Float, default=45)

    home_team = db.relationship("Team", foreign_keys=[home_team_id])
    away_team = db.relationship("Team", foreign_keys=[away_team_id])


class Article(db.Model):
    __tablename__ = "articles"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(220), nullable=False)
    slug = db.Column(db.String(240), unique=True, nullable=False, index=True)
    category = db.Column(db.String(50), default="News")
    dek = db.Column(db.String(260), default="")
    body = db.Column(db.Text, default="")
    author = db.Column(db.String(120), default="NBA.com Staff")
    published_at = db.Column(db.DateTime, default=MIRROR_REFERENCE_DATE)
    image = db.Column(db.String(180), default="")
    related_team_slug = db.Column(db.String(80), default="")
    related_player_slug = db.Column(db.String(140), default="")


class Product(db.Model):
    __tablename__ = "products"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(180), nullable=False)
    slug = db.Column(db.String(200), unique=True, nullable=False, index=True)
    category = db.Column(db.String(50), default="Jerseys")
    team_slug = db.Column(db.String(80), default="")
    price = db.Column(db.Float, default=0)
    list_price = db.Column(db.Float, default=0)
    rating = db.Column(db.Float, default=4.5)
    stock = db.Column(db.Integer, default=20)
    image = db.Column(db.String(180), default="")
    description = db.Column(db.Text, default="")
    features = db.Column(db.Text, default="[]")
    sizes = db.Column(db.String(120), default="S,M,L,XL")
    color = db.Column(db.String(40), default="")

    def feature_list(self):
        return json.loads(self.features or "[]")


class CartItem(db.Model):
    __tablename__ = "cart_items"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False)
    quantity = db.Column(db.Integer, default=1)
    size = db.Column(db.String(20), default="M")
    added_at = db.Column(db.DateTime, default=MIRROR_REFERENCE_DATE)
    product = db.relationship("Product")


class Order(db.Model):
    __tablename__ = "orders"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    order_number = db.Column(db.String(40), unique=True, nullable=False)
    status = db.Column(db.String(30), default="Processing")
    subtotal = db.Column(db.Float, default=0)
    shipping = db.Column(db.Float, default=0)
    tax = db.Column(db.Float, default=0)
    total = db.Column(db.Float, default=0)
    ship_address = db.Column(db.String(220), default="")
    payment_last4 = db.Column(db.String(4), default="4242")
    created_at = db.Column(db.DateTime, default=MIRROR_REFERENCE_DATE)
    items = db.relationship("OrderItem", backref="order", cascade="all, delete-orphan")


class OrderItem(db.Model):
    __tablename__ = "order_items"
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id"), nullable=False)
    product_name = db.Column(db.String(180), default="")
    quantity = db.Column(db.Integer, default=1)
    price = db.Column(db.Float, default=0)
    size = db.Column(db.String(20), default="")


class Favorite(db.Model):
    __tablename__ = "favorites"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    item_type = db.Column(db.String(20), nullable=False)
    item_id = db.Column(db.Integer, nullable=False)
    note = db.Column(db.String(160), default="")
    created_at = db.Column(db.DateTime, default=MIRROR_REFERENCE_DATE)


class TicketRequest(db.Model):
    __tablename__ = "ticket_requests"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    game_id = db.Column(db.Integer, db.ForeignKey("games.id"), nullable=False)
    seats = db.Column(db.Integer, default=2)
    section_preference = db.Column(db.String(80), default="Lower bowl")
    status = db.Column(db.String(30), default="Saved")
    game = db.relationship("Game")


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


@app.context_processor
def inject_globals():
    cart_count = 0
    if current_user.is_authenticated:
        cart_count = sum(item.quantity for item in current_user.cart_items)
    return {
        "cart_count": cart_count,
        "teams_nav": Team.query.order_by(Team.city).limit(10).all(),
        "mirror_date": MIRROR_REFERENCE_DATE,
        "division_order": DIVISION_ORDER,
        "news_categories": NEWS_CATEGORIES,
        "active_endpoint": request.endpoint or "",
        "team_seed": team_seed,
        "game_series_label": game_series_label,
        "game_round_label": game_round_label,
        "game_number_label": game_number_label,
        "game_time_label": game_time_label,
        "game_leaders": game_leaders,
        "game_date_slug": game_date_slug,
        "game_series_slug": game_series_slug,
    }


def get_or_404(model, slug):
    item = model.query.filter_by(slug=slug).first()
    if not item:
        abort(404)
    return item


def money(value):
    return f"${value:,.2f}"


app.jinja_env.filters["money"] = money


def signed_number(value):
    return f"+{value:.1f}" if value > 0 else f"{value:.1f}"


app.jinja_env.filters["signed"] = signed_number


def team_point_diff(team):
    return round((team.ppg or 0) - (team.oppg or 0), 1)


def team_last_ten(team):
    wins = max(0, min(10, round((team.win_pct or 0) * 10)))
    return f"{wins}-{10 - wins}"


def attach_standing_fields(teams):
    if not teams:
        return []
    leader_net = max(team.wins - team.losses for team in teams)
    for rank, team in enumerate(sorted(teams, key=lambda t: (-t.wins, t.losses, t.city)), 1):
        team.rank = rank
        team.games_back = round((leader_net - (team.wins - team.losses)) / 2, 1)
        team.last_ten = team_last_ten(team)
        team.point_diff = team_point_diff(team)
    return sorted(teams, key=lambda t: t.rank)


def grouped_teams_by_division():
    grouped = {}
    teams = Team.query.order_by(Team.conference, Team.division, Team.city).all()
    for division in DIVISION_ORDER:
        grouped[division] = [team for team in teams if team.division == division]
    return grouped


def grouped_games(games):
    groups = []
    for game in games:
        label = game.game_date.strftime("%A, %B %-d")
        if not groups or groups[-1][0] != label:
            groups.append((label, []))
        groups[-1][1].append(game)
    return groups


def game_date_slug(game):
    return game.game_date.strftime("%Y-%m-%d")


def game_calendar_days(selected_date=None):
    base = selected_date or MIRROR_REFERENCE_DATE.date()
    start = base - timedelta(days=(base.weekday() + 1) % 7)
    games = Game.query.all()
    days = []
    for offset in range(7):
        day = start + timedelta(days=offset)
        count = sum(1 for game in games if game.game_date.date() == day)
        days.append({
            "dow": day.strftime("%a"),
            "day": day.day,
            "date": day.strftime("%Y-%m-%d"),
            "count": count,
            "active": day == base,
        })
    return days


def game_series_slug(game):
    return "-vs-".join(sorted([game.home_team.slug, game.away_team.slug]))


def stat_value(player, stat):
    if stat == "topg":
        return round(1.1 + (player.apg * 0.18) + (player.ppg * 0.025), 1)
    return getattr(player, stat, 0)


def players_sorted_by_stat(stat):
    players = Player.query.all()
    return sorted(players, key=lambda p: (-stat_value(p, stat), p.name))


def stats_leaders():
    return [
        {"key": key, "label": label, "leader": players_sorted_by_stat(key)[0], "rows": players_sorted_by_stat(key)[:5]}
        for key, label in PLAYER_STAT_FIELDS.items()
    ]


def scoreboard_games():
    finals = Game.query.filter_by(status="Final").order_by(Game.game_date.desc()).limit(2).all()
    upcoming = Game.query.filter(Game.status != "Final").order_by(Game.game_date).limit(4).all()
    ordered_finals = sorted(finals, key=lambda game: game.game_date)
    seen = {game.id for game in ordered_finals + upcoming}
    fillers = []
    if len(seen) < 6:
        fillers = (
            Game.query.filter(~Game.id.in_(seen))
            .order_by(Game.game_date)
            .limit(6 - len(seen))
            .all()
        )
    return ordered_finals + upcoming + fillers


def team_seed(team):
    teams = Team.query.filter_by(conference=team.conference).all()
    ranked = sorted(teams, key=lambda item: (-item.wins, item.losses, item.city))
    for index, ranked_team in enumerate(ranked, 1):
        if ranked_team.id == team.id:
            return index
    return ""


def game_pair_key(game):
    return frozenset([game.home_team.slug, game.away_team.slug])


def game_series_label(game):
    labels = {
        frozenset(["cavaliers", "pistons"]): "CLE leads 3-2",
        frozenset(["timberwolves", "spurs"]): "SAS leads 3-2",
        frozenset(["thunder", "mavericks"]): "Series tied 0-0",
        frozenset(["clippers", "suns"]): "Series tied 0-0",
    }
    return labels.get(game_pair_key(game), "Series tied 0-0")


def game_round_label(game):
    labels = {
        frozenset(["cavaliers", "pistons"]): "East Conf. Semifinals",
        frozenset(["timberwolves", "spurs"]): "West Conf. Semifinals",
    }
    return labels.get(game_pair_key(game), "NBA Playoffs")


def game_number_label(game):
    if game.arena == "TBD":
        return "Game 1"
    if game_pair_key(game) in {frozenset(["cavaliers", "pistons"]), frozenset(["timberwolves", "spurs"])}:
        return "Game 6"
    return f"Game {max(1, min(game.id, 7))}"


def game_time_label(game):
    if game.arena == "TBD":
        return "TBD"
    return game.game_date.strftime("%-I:%M %p CT")


def game_leaders(game):
    players = list(game.away_team.players) + list(game.home_team.players)
    return sorted(players, key=lambda player: (-player.ppg, player.name))[:2]


def article_groups(articles):
    return {
        category: [article for article in articles if article.category == category]
        for category in NEWS_CATEGORIES
    }


def article_slug_match(articles, *needles):
    normalized_needles = [needle.lower() for needle in needles if needle]
    for article in articles:
        haystack = f"{article.title} {article.dek} {article.category}".lower()
        if all(needle in haystack for needle in normalized_needles):
            return article.slug
    return articles[0].slug if articles else ""


def article_detail_profile(article):
    """Return NBA.com-style display content without requiring runtime network data."""
    if "cavaliers" in article.slug or "pistons" in article.slug:
        return {
            "series_label": "2026 Playoffs: East Semifinals | DET (1) vs. CLE (4)",
            "headline": "4 takeaways: Donovan Mitchell, Jarrett Allen power Cavaliers past Pistons in Game 7",
            "dek": "The Cavaliers go into Detroit and lean on their balanced attack to outplay the top seed and secure their spot in the East Finals.",
            "author": "Shaun Powell",
            "author_image": "/static/images/articles/Powell.jpg",
            "date_label": "May 18, 2026 6:05 AM",
            "image": "/static/images/articles/nba-official-cavs-game7.jpg",
            "caption": "Donovan Mitchell lifted off and brought the Cavs with him for a Game 7 win over the Pistons.",
            "sections": [
                {
                    "heading": "",
                    "paragraphs": [
                        "There is the belief that no greater challenge awaits a team than a Game 7, and this is only half true. It is trying to win a Game 7 on the road. Cleveland answered with poise, balance and its cleanest late-series effort.",
                        "The Cavaliers set the tone early, kept Cade Cunningham from controlling the game and turned a hostile road environment into a composed closeout performance.",
                        "For the first time since 2018, Cleveland is four wins away from the NBA Finals. Detroit exits with a young core that moved far beyond its recent rebuilding seasons.",
                    ],
                },
                {
                    "heading": "1. Donovan Mitchell sets tone, gets his milestone",
                    "paragraphs": [
                        "Mitchell attacked downhill, trusted his teammates and finished with the kind of efficient all-around line Cleveland needed from its lead guard.",
                        "His scoring pressure opened feeds for Jarrett Allen and Evan Mobley, and his ball security gave the Cavaliers control of the series' most important possessions.",
                    ],
                },
                {
                    "heading": "2. Jarrett Allen brings his A-game",
                    "paragraphs": [
                        "Allen imposed himself in the paint, shook off contact around the rim and protected the basket with the force of a center determined to reward Cleveland's guards.",
                        "His energy showed up in rolls, rebounds and second efforts, giving the Cavaliers the interior answer they needed in a road Game 7.",
                    ],
                },
                {
                    "heading": "3. Sam Merrill makes the big 3s",
                    "paragraphs": [
                        "The designated floor spacer chose the right time to fire. Merrill's early confidence punished Detroit's help and stretched the matchup beyond the Pistons' comfort zone.",
                    ],
                },
                {
                    "heading": "4. Pistons just getting started",
                    "paragraphs": [
                        "Detroit's season ended abruptly, but the broader timeline still points upward. Cunningham, Duren and the surrounding core gave the franchise its deepest run in years.",
                        "The urgency clock has not started yet. Next season will reveal how quickly this group converts the lesson into a longer playoff stay.",
                    ],
                },
            ],
        }
    category_profiles = {
        "Draft": {
            "series_label": "2026 NBA Draft",
            "author": "NBA.com Draft Staff",
            "author_image": "/static/images/articles/nba-official-draft-logo.png",
            "image": "/static/images/articles/nba-official-draft-combine-hero.jpg",
            "caption": "Draft hopefuls work through combine drills as teams gather measurements, interviews and on-court context.",
            "sections": [
                {
                    "heading": "What changed after the combine",
                    "paragraphs": [
                        "The draft board tightened after teams watched prospects move from interviews and measurements into live drills. Guards who handled pressure and wings who defended multiple spots helped themselves most.",
                        "Front offices are still sorting upside from readiness, but the week supplied the kind of side-by-side context that can move players into new tiers.",
                    ],
                },
                {
                    "heading": "Names to track",
                    "paragraphs": [
                        "A.J. Dybantsa, Darryn Peterson and the connector forwards near the top of the class remain central to the conversation, while several second-unit creators used the combine to show they can process quickly.",
                        "The most valuable prospects were not only the loudest athletes. Teams repeatedly came back to shooting versatility, defensive communication and how players responded during interviews.",
                    ],
                },
                {
                    "heading": "What comes next",
                    "paragraphs": [
                        "The lottery order and workout circuit will shape the next round of movement before the June 23-24 draft. The top of the class is still fluid enough for team fit to matter.",
                    ],
                },
            ],
        },
        "Top Stories": {
            "series_label": "Top Stories",
            "author": article.author,
            "author_image": "/static/images/articles/Powell.jpg",
            "image": article.image,
            "caption": article.dek,
            "sections": [
                {
                    "heading": "How the story developed",
                    "paragraphs": [
                        article.body,
                        "The headline matchup came down to discipline, communication and which team could keep its best lineups connected through the longest stretches of pressure.",
                    ],
                },
                {
                    "heading": "Details that mattered",
                    "paragraphs": [
                        "The most important swings were not isolated highlights. They came from second efforts, matchup recognition and how quickly players got back to the next possession after a mistake.",
                        "Coaches leaned on shorter rotations and more direct actions, placing a premium on the players who could defend without fouling and keep the ball moving.",
                    ],
                },
                {
                    "heading": "What is next",
                    "paragraphs": [
                        "The next step is about carrying the same execution into a new opponent. Scouting reports tighten this time of year, so every adjustment becomes more visible.",
                    ],
                },
            ],
        },
        "Analysis": {
            "series_label": "NBA Analysis",
            "author": article.author,
            "author_image": "/static/images/players/lebron_james.png",
            "image": article.image,
            "caption": article.dek,
            "sections": [
                {
                    "heading": "The matchup lens",
                    "paragraphs": [
                        f"{article.dek} The key is how quickly teams can identify the first defensive coverage and force the second decision.",
                        "The best possessions in this stretch have come from patience: drawing two to the ball, relocating shooters and making the weak-side defender choose between the corner and the rim.",
                    ],
                },
                {
                    "heading": "Numbers behind it",
                    "paragraphs": [
                        "The statistical story is not one column. Pace, turnover rate, rebounding margin and shot quality all tell part of the answer, especially when playoff rotations shrink.",
                        "This mirror keeps those details on the full article page rather than giving away task-critical answers in a card snippet.",
                    ],
                },
            ],
        },
        "Features": {
            "series_label": "NBA Features",
            "author": article.author,
            "author_image": "/static/images/articles/Powell.jpg",
            "image": article.image,
            "caption": article.dek,
            "sections": [
                {
                    "heading": "Inside the story",
                    "paragraphs": [
                        article.body,
                        "The feature angle follows the people and preparation behind the box score, connecting locker-room details with the decisions fans see late in games.",
                    ],
                },
                {
                    "heading": "Why it matters",
                    "paragraphs": [
                        "Small changes in role, trust and timing can swing a series. The teams that solve those details first tend to look deeper than their public scouting reports.",
                    ],
                },
            ],
        },
        "Video": {
            "series_label": "NBA Video",
            "author": "NBA.com Video Desk",
            "author_image": "/static/images/players/tyrese_haliburton.png",
            "image": article.image,
            "caption": article.dek,
            "sections": [
                {
                    "heading": "Clip breakdown",
                    "paragraphs": [
                        article.body,
                        "The sequence is built around early pace, first-side pressure and the quick pass that turns a good look into an open one.",
                    ],
                },
                {
                    "heading": "What to watch next",
                    "paragraphs": [
                        "Follow the same action on the next possession: if the defense sends an extra body, the counter usually appears on the weak side or in the dunker spot.",
                    ],
                },
            ],
        },
        "Preview": {
            "series_label": "NBA Preview",
            "author": article.author,
            "author_image": "/static/images/articles/Powell.jpg",
            "image": article.image,
            "caption": article.dek,
            "sections": [
                {
                    "heading": "Matchup setup",
                    "paragraphs": [
                        article.body,
                        "The preview centers on pace, ball pressure and how quickly each side can force its preferred matchup before the defense is organized.",
                    ],
                },
                {
                    "heading": "What decides it",
                    "paragraphs": [
                        "Rebounding, transition defense and the first six minutes after halftime are the areas that can tilt the game. Coaches will also watch which bench group can survive without losing the scoring margin.",
                    ],
                },
                {
                    "heading": "Players to watch",
                    "paragraphs": [
                        "The stars will draw the first layer of attention, but the swing players are the ones spacing the floor, tagging rollers and making the extra pass under pressure.",
                    ],
                },
            ],
        },
        "Playoffs": {
            "series_label": "2026 NBA Playoffs",
            "author": article.author,
            "author_image": "/static/images/articles/Powell.jpg",
            "image": article.image,
            "caption": article.dek,
            "sections": [
                {
                    "heading": "Series context",
                    "paragraphs": [
                        article.body,
                        "At this stage, every possession starts with the same question: can the offense get to its first option, and if not, how cleanly can it move to the counter?",
                    ],
                },
                {
                    "heading": "Rotation pressure",
                    "paragraphs": [
                        "Shorter rotations make the small decisions louder. Foul trouble, two-way lineups and the last shooting slot can all alter the shape of a series.",
                    ],
                },
                {
                    "heading": "What to watch next",
                    "paragraphs": [
                        "The next game will show whether the adjustment holds. If the same coverage works twice, the opponent will need a more aggressive counter.",
                    ],
                },
            ],
        },
        "Highlights": {
            "series_label": "NBA Highlights",
            "author": "NBA.com Video Desk",
            "author_image": "/static/images/players/tyrese_haliburton.png",
            "image": article.image,
            "caption": article.dek,
            "sections": [
                {
                    "heading": "Condensed game flow",
                    "paragraphs": [
                        article.body,
                        "The strongest runs were built on early stops, outlet passes and quick decisions before the defense could load up in the half court.",
                    ],
                },
                {
                    "heading": "Key sequence",
                    "paragraphs": [
                        "A late push turned on shot selection and floor balance. The offense found clean looks without giving up runouts the other way.",
                    ],
                },
            ],
        },
        "Awards": {
            "series_label": "NBA Awards",
            "author": article.author,
            "author_image": "/static/images/articles/Powell.jpg",
            "image": article.image,
            "caption": article.dek,
            "sections": [
                {
                    "heading": "The voting case",
                    "paragraphs": [
                        article.body,
                        "The strongest award cases combine production, availability and role difficulty. That is why two-way impact keeps showing up in the discussion.",
                    ],
                },
                {
                    "heading": "Separating the finalists",
                    "paragraphs": [
                        "The margins are narrow when candidates influence games in different ways. Voters often return to consistency, opponent attention and how much a team identity depends on the player.",
                    ],
                },
            ],
        },
        "Transactions": {
            "series_label": "NBA Transactions",
            "author": "NBA.com Staff",
            "author_image": "/static/images/articles/Powell.jpg",
            "image": article.image,
            "caption": article.dek,
            "sections": [
                {
                    "heading": "Roster impact",
                    "paragraphs": [
                        article.body,
                        "The move gives the rotation another specialist option while preserving the flexibility teams need during a long postseason push.",
                    ],
                },
                {
                    "heading": "Why it matters",
                    "paragraphs": [
                        "Depth transactions can become meaningful quickly when matchups change or injuries stack up. The best fits are usually players with one skill that translates immediately.",
                    ],
                },
            ],
        },
        "History": {
            "series_label": "NBA History",
            "author": "NBA.com History Desk",
            "author_image": "/static/images/articles/Powell.jpg",
            "image": article.image,
            "caption": article.dek,
            "sections": [
                {
                    "heading": "Historical context",
                    "paragraphs": [
                        article.body,
                        "The current postseason keeps echoing older playoff patterns: elite guards forcing help, bigs deciding the paint and role players changing a series with one clean stretch.",
                    ],
                },
                {
                    "heading": "Why fans still revisit it",
                    "paragraphs": [
                        "The best historical comparisons are not exact copies. They highlight the choices that repeat across eras and show how the league keeps evolving around them.",
                    ],
                },
            ],
        },
        "Around the NBA": {
            "series_label": "Around the NBA",
            "author": article.author,
            "author_image": "/static/images/articles/Powell.jpg",
            "image": article.image,
            "caption": article.dek,
            "sections": [
                {
                    "heading": "League view",
                    "paragraphs": [
                        article.body,
                        "Across the league, the detail is less about a single result and more about how travel, health, depth and late-game execution build over a long playoff run.",
                    ],
                },
                {
                    "heading": "The broader context",
                    "paragraphs": [
                        "Teams are balancing immediate matchup needs with bigger roster questions. That tension is why these daily notes matter beyond the final score.",
                    ],
                },
            ],
        },
    }
    profile = category_profiles.get(article.category, {})
    if profile:
        return {
            "series_label": profile["series_label"],
            "headline": article.title,
            "dek": article.dek,
            "author": profile["author"],
            "author_image": profile["author_image"],
            "date_label": article.published_at.strftime("%B %-d, %Y %-I:%M %p"),
            "image": profile["image"],
            "caption": profile["caption"],
            "sections": profile["sections"],
        }
    paragraphs = [
        article.body,
        f"{article.dek} The matchup details, statistical context and player notes are preserved inside this local NBA mirror so article cards lead to a complete reading page.",
        "The page keeps the same hierarchy used by NBA.com articles: series navigation, author metadata, a large lead image, related stories and a latest-news feed.",
    ]
    return {
        "series_label": f"{article.category} | NBA.com",
        "headline": article.title,
        "dek": article.dek,
        "author": article.author,
        "author_image": "/static/images/players/lebron_james.png",
        "date_label": article.published_at.strftime("%B %-d, %Y %-I:%M %p"),
        "image": article.image,
        "caption": article.dek,
        "sections": [{"heading": "", "paragraphs": paragraphs}],
    }


def player_news_items(players):
    titles = [
        "Closes with disappointing effort",
        "Passive end to season",
        "Catches fire in Game 7 blowout",
        "Unstoppable in blowout victory",
        "Dominates in Game 7 win",
        "Scores 26 in Game 7",
    ]
    return [
        {"player": player, "title": titles[index % len(titles)], "time": f"05/18/2026 {2 + index}:0{index % 6} AM"}
        for index, player in enumerate(players[:6])
    ]


def stats_home_context():
    players = Player.query.all()
    teams = Team.query.all()
    cavs = Team.query.filter_by(slug="cavaliers").first()
    pistons = Team.query.filter_by(slug="pistons").first()
    def top_players(key, count=5):
        return players_sorted_by_stat(key)[:count]
    return {
        "daily": {
            "Points": top_players("ppg"),
            "Rebounds": top_players("rpg"),
            "Assists": top_players("apg"),
            "Blocks": top_players("bpg"),
            "Steals": top_players("spg"),
            "Turnovers": top_players("topg"),
            "Three Pointers Made": top_players("ppg"),
            "Free Throws Made": top_players("fg_pct"),
            "Fantasy Points": top_players("ppg"),
        },
        "more_stats": [
            ("Total Points", top_players("ppg", 3)),
            ("Total Rebounds", top_players("rpg", 3)),
            ("Total Assists", top_players("apg", 3)),
            ("Total Blocks", top_players("bpg", 3)),
            ("Total Steals", top_players("spg", 3)),
            ("Catch and Shoot FGA", top_players("fg_pct", 3)),
        ],
        "team_daily": {
            "Points": [cavs, pistons],
            "Rebounds": [cavs, pistons],
            "Assists": [cavs, pistons],
            "Blocks": [pistons, cavs],
            "Steals": [cavs, pistons],
            "Field Goal Percentage": [cavs, pistons],
            "Three Pointers Made": [pistons, cavs],
            "Three Point Percentage": [cavs, pistons],
            "Free Throw Percentage": [pistons, cavs],
        },
        "player_news": player_news_items(sorted(players, key=lambda p: p.name)),
        "assist_player": Player.query.filter_by(slug="cade-cunningham").first() or top_players("apg", 1)[0],
        "spotlight_image": "/static/images/articles/nba-official-spurs-thunder.jpg",
        "shotchart_image": "/static/images/articles/nba-official-young-spurs.jpg",
    }


def official_schedule_context(teams_by_slug):
    def row(status, time_label, broadcast, round_label, away_slug, home_slug, series, arena, city, actions=None, away_score=None, home_score=None):
        away = teams_by_slug.get(away_slug)
        home = teams_by_slug.get(home_slug)
        return {
            "status": status,
            "time": time_label,
            "broadcast": broadcast,
            "round": round_label,
            "away_slug": away_slug,
            "home_slug": home_slug,
            "away_name": away.full_name if away else away_slug.title(),
            "home_name": home.full_name if home else home_slug.title(),
            "away_abbr": away.abbreviation if away else away_slug[:3].upper(),
            "home_abbr": home.abbreviation if home else home_slug[:3].upper(),
            "away_logo": away.logo if away else "",
            "home_logo": home.logo if home else "",
            "away_score": away_score,
            "home_score": home_score,
            "series": series,
            "arena": arena,
            "city": city,
            "actions": actions or ["Preview", "View Series"],
        }

    weeks = [
        {
            "label": "Week 30 (May 11 - May 17)",
            "days": [
                {
                    "label": "Sunday, May 17",
                    "count": "1 Game",
                    "rows": [
                        row(
                            "FINAL",
                            "",
                            "",
                            "East Conf. Semifinals",
                            "cavaliers",
                            "pistons",
                            "Game 7: CLE wins 4-3",
                            "Little Caesars Arena",
                            "Detroit, MI",
                            actions=["Watch", "Box Score", "View Series"],
                            away_score=125,
                            home_score=94,
                        )
                    ],
                }
            ],
        },
        {
            "label": "Week 31 (May 18 - May 24)",
            "days": [
                {"label": "Monday, May 18", "count": "1 Game", "rows": [row("8:30 AM CT (Tuesday)", "Now TV", "League Pass", "West Conf. Finals", "spurs", "thunder", "Game 1: Series tied 0-0", "Paycom Center", "Oklahoma City, OK")]},
                {"label": "Tuesday, May 19", "count": "1 Game", "rows": [row("8:00 AM CT (Wednesday)", "Now TV", "League Pass", "East Conf. Finals", "cavaliers", "knicks", "Game 1: Series tied 0-0", "Madison Square Garden", "New York, NY")]},
                {"label": "Wednesday, May 20", "count": "1 Game", "rows": [row("8:30 AM CT (Thursday)", "Now TV", "League Pass", "West Conf. Finals", "spurs", "thunder", "Game 2: Series tied 0-0", "Paycom Center", "Oklahoma City, OK")]},
                {"label": "Thursday, May 21", "count": "1 Game", "rows": [row("8:00 AM CT (Friday)", "Now TV", "League Pass", "East Conf. Finals", "cavaliers", "knicks", "Game 2: Series tied 0-0", "Madison Square Garden", "New York, NY")]},
                {"label": "Friday, May 22", "count": "1 Game", "rows": [row("8:30 AM CT (Saturday)", "Now TV", "Viu TV", "West Conf. Finals", "thunder", "spurs", "Game 3: Series tied 0-0", "Frost Bank Center", "San Antonio, TX")]},
                {"label": "Saturday, May 23", "count": "1 Game", "rows": [row("8:00 AM CT (Sunday)", "Now TV", "League Pass", "East Conf. Finals", "knicks", "cavaliers", "Game 3: Series tied 0-0", "Rocket Arena", "Cleveland, OH")]},
                {"label": "Sunday, May 24", "count": "1 Game", "rows": [row("8:30 AM CT (Monday)", "Now TV", "League Pass", "West Conf. Finals", "thunder", "spurs", "Game 4: Series tied 0-0", "Frost Bank Center", "San Antonio, TX")]},
            ],
        },
        {
            "label": "Week 32 (May 25 - May 31)",
            "days": [
                {"label": "Monday, May 25", "count": "1 Game", "rows": [row("8:00 AM CT (Tuesday)", "Now TV", "League Pass", "East Conf. Finals", "knicks", "cavaliers", "Game 4: Series tied 0-0", "Rocket Arena", "Cleveland, OH")]},
                {"label": "Tuesday, May 26", "count": "1 Game", "rows": [row("8:30 AM CT (Wednesday)", "Now TV", "League Pass", "West Conf. Finals", "spurs", "thunder", "Game 5: If necessary", "Paycom Center", "Oklahoma City, OK")]},
                {"label": "Wednesday, May 27", "count": "1 Game", "rows": [row("8:00 AM CT (Thursday)", "Now TV", "League Pass", "East Conf. Finals", "cavaliers", "knicks", "Game 5: If necessary", "Madison Square Garden", "New York, NY")]},
                {"label": "Thursday, May 28", "count": "1 Game", "rows": [row("8:30 AM CT (Friday)", "Now TV", "League Pass", "West Conf. Finals", "thunder", "spurs", "Game 6: If necessary", "Frost Bank Center", "San Antonio, TX")]},
                {"label": "Friday, May 29", "count": "1 Game", "rows": [row("8:00 AM CT (Saturday)", "Now TV", "League Pass", "East Conf. Finals", "knicks", "cavaliers", "Game 6: If necessary", "Rocket Arena", "Cleveland, OH")]},
                {"label": "Saturday, May 30", "count": "1 Game", "rows": [row("8:30 AM CT (Sunday)", "Now TV", "League Pass", "West Conf. Finals", "spurs", "thunder", "Game 7: If necessary", "Paycom Center", "Oklahoma City, OK")]},
                {"label": "Sunday, May 31", "count": "1 Game", "rows": [row("8:00 AM CT (Monday)", "Now TV", "League Pass", "East Conf. Finals", "cavaliers", "knicks", "Game 7: If necessary", "Madison Square Garden", "New York, NY")]},
            ],
        },
    ]
    return weeks


def draft_page_context(articles):
    all_articles = Article.query.order_by(Article.published_at.desc()).all()
    draft_slug = article_slug_match(all_articles, "draft")
    combine_slug = article_slug_match(all_articles, "combine")
    lottery_slug = article_slug_match(all_articles, "draft", "teams")
    return {
        "hero_slug": draft_slug,
        "headline_slugs": [draft_slug, combine_slug, article_slug_match(all_articles, "dybantsa"), article_slug_match(all_articles, "mock"), lottery_slug],
        "headlines": [
            "AWS NBA Draft Combine: Biggest takeaways",
            "Little-known facts about top 2026 Draft prospects",
            "The Athletic Mock Draft: Dybantsa, Peterson 1-2?",
            "Yahoo Sports Mock Draft: How each pick could play out",
            "AJ Dybantsa reflects on his NBA role models",
            "Peterson, Dybantsa among 4 who could be top pick",
            "Wizards win 2026 Draft Lottery, will pick No. 1",
            "2026 NBA Draft Order: Picks 1-60",
            "Dybantsa rises from mini hoop to NBA Draft Lottery",
            "Expectations already sky-high for 2026 Draft class",
        ],
        "videos": [
            ("All-Access: Draft Combine", "02:33", "nba-official-draft-video-1.jpg", draft_slug),
            ("AWS NBA Draft Combine: Biggest takeaways", "02:15", "draft-combine-2026.jpg", combine_slug),
            ("Jeremiah Fears joins AWS NBA Draft Combine", "06:07", "combine-knueppel.jpg", draft_slug),
            ("Yaxel Lendeborg discusses going through Draft process", "08:08", "nba-official-draft-video-2.jpg", draft_slug),
            ("2026 Draft Lottery: Watch the full drawing", "13:39", "nba-official-draft-lottery.jpg", lottery_slug),
        ],
        "combine": [
            ("AWS Draft Combine Data Hub", "The AWS NBA Draft Combine data hub turns measurements into insights, bringing context to every testing metric.", "nba-official-draft-logo.png", combine_slug),
            ("AWS NBA Draft Combine Data Hub: Everything to know", "Introducing the new 2026 AWS NBA Draft Combine Data Hub, which turns measurements and strength testing into context.", "draft-combine-2026.jpg", combine_slug),
            ("NBA Draft Combine: Closer look at each drill & more", "Take a closer look at the drills and activities at the 2026 AWS NBA Draft Combine in Chicago.", "combine-knueppel.jpg", combine_slug),
            ("Draft Combine Wingspans", "See which players recorded the 10 largest wingspans in the history of the AWS NBA Draft Combine.", "nba-official-draft-combine-hero.jpg", combine_slug),
            ("NBA Draft Combine: Highest max vertical leaps", "Tracking the combine history of players who recorded the highest vertical leaps.", "nba-official-draft-video-2.jpg", combine_slug),
            ("73 players invited to AWS NBA Draft Combine", "The annual AWS NBA Draft Combine will take place May 10-17 at Wintrust Arena and the Marriott Marquis in Chicago.", "nba-official-draft-logo.png", combine_slug),
        ],
        "mock": [
            ("Yahoo Sports Mock Draft: How each pick could play out", "Kevin O'Connor checks in with his latest mock draft now that the Wizards are on the clock.", "nba-official-draft-video-1.jpg", draft_slug),
            ("The Athletic Mock Draft: Dybantsa, Peterson 1-2?", "Washington won big at the Draft Lottery, but there are plenty of potential difference-makers in this class.", "peterson-dybantsa.jpg", draft_slug),
        ],
        "draft_info": [
            ("Everything to know about 2026 NBA Draft", "Get answers to all of your questions before the 2026 NBA Draft.", "nba-official-draft-logo.png", draft_slug),
            ("2026 NBA Draft Order: Picks 1-60", "Washington won the Draft Lottery and will have the first pick in the 2026 NBA Draft.", "nba-official-draft-banner.png", draft_slug),
            ("Two-night NBA Draft 2026 set for June", "The NBA Draft will be a 2-day event for the third straight year and will be broadcast on ESPN platforms.", "nba-official-draft-lottery.jpg", draft_slug),
            ("All-time NBA Draft History", "Recapping every NBA Draft from 1947 to the present.", "lebron-stern-draft-night.jpg", draft_slug),
        ],
        "classic": [
            ("Every No. 1 overall NBA Draft pick since 1980", "07:45", "nba-official-draft-lottery.jpg", draft_slug),
            ("NBA History: Draft-day suits", "04:02", "lebron-stern-draft-night.jpg", draft_slug),
            ("Class of 2003 - The Vault", "22:46", "nba-official-draft-video-2.jpg", draft_slug),
            ("NBAHistory: Luka Doncic in 2018 on Draft Night", "00:26", "nba-official-draft-banner.png", draft_slug),
            ("Craig Sager interviews Kevin Garnett at 1995 Draft", "00:52", "nba-official-draft-video-1.jpg", draft_slug),
        ],
    }


def fantasy_page_context(players, articles):
    all_articles = Article.query.order_by(Article.published_at.desc()).all()
    fantasy_slug = article_slug_match(all_articles, "guard") or article_slug_match(all_articles, "analysis")
    feature_slug = article_slug_match(all_articles, "playoff") or fantasy_slug
    stat_rows = []
    for index, player in enumerate(players, start=1):
        stat_rows.append({
            "rank": index,
            "player": player,
            "gp": max(22, min(82, 82 - index)),
            "min": round(36.5 - (index % 8) * 0.8, 1),
            "fgm": round(player.ppg * player.fg_pct / 10 + 4.2, 1),
            "fga": round(player.ppg / max(player.fg_pct / 100, .35) / 2.7, 1),
            "fgp": player.fg_pct,
            "three": round(player.three_pct / 10, 1),
            "ftm": round(player.ppg / 6, 1),
            "reb": player.rpg,
            "ast": player.apg,
            "stl": player.spg,
            "blk": player.bpg,
            "tov": round(max(1.0, (player.apg + player.ppg / 12) / 2), 1),
            "pts": player.ppg,
            "plus": round((player.ppg + player.rpg + player.apg) / 4 - 5, 1),
        })
    return {
        "feature_slug": feature_slug,
        "top_links": [
            ("NBA Fantasy: 2026-27 early first-round rankings", "Yahoo fantasy basketball analyst Dan Titus takes a peek at next season's potential first-round picks.", "nba-official-fantasy-spurs.jpg", fantasy_slug),
            ("NBA Fantasy: 2025-26 final week power rankings", "Rotowire highlights the top fantasy basketball performers from the final week of the season.", "nba-official-fantasy-power.jpg", fantasy_slug),
            ("NBA Fantasy: Best picks by round for 2025-26", "Yahoo fantasy basketball analyst Dan Titus gives his best picks by round from 2025-26 drafts.", "nba-official-fantasy-rookies.jpg", fantasy_slug),
        ],
        "watch": [
            ("Top pickups for your fantasy basketball playoff push", "nba-official-fantasy-playlist.jpg", feature_slug),
            ("Look to Memphis for fantasy basketball waiver help", "nba-official-fantasy-playlist.jpg", feature_slug),
            ("What can fantasy managers reasonably expect from rookies?", "nba-official-fantasy-playlist.jpg", feature_slug),
            ("Feel like a King with these fantasy basketball pickups", "nba-official-fantasy-playlist.jpg", feature_slug),
        ],
        "high_score": [
            ("NBA Fantasy: Final high score perfect lineup", "Check out the top performers from the previous week of Yahoo High Score.", "nba-official-fantasy-spurs.jpg", fantasy_slug),
            ("NBA Fantasy: Best picks by round for 2025-26", "Titus gives you his best picks by round from 2025-26 drafts.", "nba-official-fantasy-rookies.jpg", fantasy_slug),
            ("NBA Fantasy: Top 10 performances from 2025-26", "Check out the best Yahoo Fantasy High Score performances.", "nba-official-fantasy-power.jpg", fantasy_slug),
            ("NBA Fantasy: Sleeper centers for 2025-26", "RotoWire breaks down centers who could pop next season.", "nba-official-fantasy-playlist.jpg", fantasy_slug),
        ],
        "stat_rows": stat_rows,
        "draft_prep": [
            ("NBA Fantasy: 2026-27 early first-round rankings", "Titus takes a peek at next season's potential first-round picks.", "nba-official-fantasy-spurs.jpg", fantasy_slug),
            ("NBA Fantasy: Forward tiers for 2025-26", "RotoWire breaks down forwards to consider drafting.", "nba-official-fantasy-power.jpg", fantasy_slug),
            ("NBA Fantasy: Top 50 keepers for 25-26", "RotoWire breaks down the top keeper options.", "nba-official-fantasy-rookies.jpg", fantasy_slug),
            ("NBA Fantasy: Rookies preview for 2025-26", "RotoWire breaks down incoming rookies.", "nba-official-draft-combine-hero.jpg", fantasy_slug),
            ("NBA Fantasy: 10 risers & fallers for 2025-26", "RotoWire breaks down risers and fallers.", "nba-official-fantasy-playlist.jpg", fantasy_slug),
        ],
    }


def favorite_pairs(user):
    pairs = []
    for fav in user.favorites:
        model = {"team": Team, "player": Player, "article": Article, "product": Product}.get(fav.item_type)
        item = db.session.get(model, fav.item_id) if model else None
        if item:
            pairs.append((fav, item))
    return pairs


@app.route("/")
def index():
    articles = Article.query.order_by(Article.published_at.desc()).all()
    all_games = Game.query.order_by(Game.game_date).all()
    leaders = Player.query.order_by(Player.ppg.desc()).limit(6).all()
    products = Product.query.order_by(Product.rating.desc()).limit(4).all()
    recaps = [game for game in all_games if game.status == "Final"]
    groups = article_groups(articles)
    around_items = groups.get("Around the NBA", [])
    around_items = (around_items + [article for article in articles if article not in around_items])[:10]
    recap_images = {
        recaps[0].id: "/static/images/articles/cle-det-recap.jpg",
        recaps[1].id: "/static/images/articles/okc-lal-recap.jpg",
    } if len(recaps) >= 2 else {}
    return render_template(
        "index.html",
        hero=articles[0] if articles else None,
        stories=articles[1:9],
        headlines=articles[1:11],
        trending=articles[3:11],
        around=groups,
        around_items=around_items,
        games=scoreboard_games(),
        recaps=recaps,
        recap_images=recap_images,
        leaders=leaders,
        products=products,
    )


@app.route("/_health")
def health():
    return {"ok": True, "site": "nba", "teams": Team.query.count(), "players": Player.query.count()}


def render_section_landing(page_title, eyebrow, intro, articles, primary_label="Latest", include_games=False, include_leaders=False):
    all_articles = Article.query.order_by(Article.published_at.desc()).all()
    section_games = scoreboard_games()[:4] if include_games else []
    leaders = Player.query.order_by(Player.ppg.desc()).limit(6).all() if include_leaders else []
    return render_template(
        "section_landing.html",
        page_title=page_title,
        eyebrow=eyebrow,
        intro=intro,
        primary_label=primary_label,
        articles=articles,
        hero=articles[0] if articles else None,
        headlines=all_articles[1:9],
        games=scoreboard_games(),
        section_games=section_games,
        leaders=leaders,
    )


@app.route("/trending")
def trending():
    articles = Article.query.order_by(Article.published_at.desc()).offset(3).limit(8).all()
    return render_section_landing(
        "Trending Now",
        "Trending",
        "The latest playoff storylines, player features and league-wide developments.",
        articles,
        primary_label="Trending Stories",
        include_games=True,
    )


@app.route("/playoffs")
def playoffs():
    teams = {team.slug: team for team in Team.query.all()}
    article_pool = Article.query.filter(
        Article.category.in_(["Playoffs", "Preview", "Analysis", "Top Stories", "Highlights"])
    ).order_by(Article.published_at.desc()).all()
    fallback_articles = Article.query.order_by(Article.published_at.desc()).all()
    articles = article_pool or fallback_articles
    latest_specs = [
        ("Mitchell-led Cavs sprint into East Finals", "The Cavaliers go into Detroit and lean on their balanced attack to outplay the top seed and secure their spot in the East Finals.", "9 hours ago", "cle-det-recap.jpg"),
        ("Cavaliers win Game 7 wire-to-wire, advance to ECF", "Donovan Mitchell and the Cavaliers are headed to New York for the next round after a composed road performance.", "4 hours ago", "cavs-playoffs.jpg"),
        ("Depth, young talent headline West Finals", "The Thunder's depth and how they defend Victor Wembanyama loom large in a highly anticipated Western Conference Finals.", "3 hours ago", "edwards-game5-051426-scaled.jpg"),
        ("Brunson-Spida duel highlights East Finals", "The Knicks are rolling on offense, even as their stars find their defense targeted.", "2 hours ago", "brunson-iso-051426-scaled.jpg"),
        ("Facts to know about Game 7 history", "Dive deep into the stats and facts to know about Game 7 history in the NBA playoffs.", "May 17, 2026", "pistons-cavs-game6.jpg"),
        ("Wembanyama's rapid growth quickens Spurs' timeline", "The Spurs are preparing to play against the defending champion Thunder.", "May 17, 2026", "wembanyama-gm5.jpg"),
        ("Spurs define their timeline, head to WCF", "Stephen Castle steps up early, the whole squad swallows up the Wolves' rally and the Spurs move on.", "May 16, 2026", "min-sas-recap.jpg"),
        ("Castle leads Spurs with 32 points, 11 rebounds", "Stephen Castle leads the Spurs with 32 points, 11 rebounds in a Game 6 closeout victory.", "May 16, 2026", "edwards-spurs-gm5-051426-scaled.jpg"),
        ("Pistons pick up Cade, force Game 7 at home", "One play proves a microcosm of the Pistons' will to survive as a big-time bench effort boosts them back to Detroit.", "May 16, 2026", "det-cle-recap.jpg"),
        ("Cunningham, Duren lead Pistons to Game 6 victory", "Cade Cunningham and Jalen Duren lead the Pistons to a Game 6 victory to tie the series.", "May 16, 2026", "pistons-cavs-game6.jpg"),
        ("The Athletic: Pop mentoring Spurs in playoffs", "Gregg Popovich continues to mentor the Spurs players behind the scenes.", "May 15, 2026", "ian-eagle-noah-eagle.jpg"),
        ("Film Study: Knicks pivot around Towns", "With a familiar catalyst, the Knicks enter the East Finals re-energized on offense.", "May 15, 2026", "brunson-iso-051426-scaled.jpg"),
        ("Anunoby fully participates in practice", "OG Anunoby fully practiced with the Knicks for the second time as he works his way back.", "May 16, 2026", "og-anunoby.jpg"),
        ("NBA Mailbag: Jamal's X-factor for Knicks in East Finals", "Jamal Crawford answers your questions on the playoffs, OKC's 8-0 start, scoring off the bench, and more.", "May 14, 2026", "brandon-clarke.png"),
        ("The Athletic: Dylan Harper is a rising star", "Victor Wembanyama is the tip of the Spurs' spear, but Harper's early emergence is part of what makes San Antonio's future so exciting.", "May 14, 2026", "combine-knueppel.jpg"),
        ("The Athletic: Story behind Pistons won again song", "Gerald Allen, better known as Gmac Cash, celebrates Detroit's playoff run.", "May 14, 2026", "cavs-playoffs.jpg"),
    ]
    latest_news = []
    cavs_article = Article.query.filter(Article.slug.ilike("%cavaliers%")).order_by(Article.published_at.desc()).first()
    for index, (title, dek, date_label, image) in enumerate(latest_specs):
        article = articles[index % len(articles)]
        if index < 2 and cavs_article:
            article = cavs_article
        latest_news.append({"title": title, "dek": dek, "date": date_label, "image": f"/static/images/articles/{image}", "slug": article.slug})
    chasing_history = [
        ("Spurs Close it Out", "01:01", "wembanyama-gm5.jpg"),
        ("Chasing History: Cavs Storm Back", "02:29", "cle-det-recap.jpg"),
        ("Thunder Stay Perfect", "01:01", "okc-lal-recap.jpg"),
        ("A New York Sweep", "01:45", "brunson-iso-051426-scaled.jpg"),
        ("Chasing History: Home Sweet Home", "02:03", "harris-levert-051426-scaled.jpg"),
    ]
    return render_template(
        "playoffs.html",
        teams=teams,
        articles=articles,
        latest_news=latest_news,
        chasing_history=chasing_history,
    )


@app.route("/draft")
def draft():
    articles = Article.query.filter(Article.category == "Draft").order_by(Article.published_at.desc()).all()
    return render_template("draft.html", articles=articles, draft=draft_page_context(articles))


@app.route("/around-the-nba")
def around_the_nba():
    articles = Article.query.filter(Article.category.in_(["Around the NBA", "Transactions", "History", "Awards"])).order_by(Article.published_at.desc()).limit(10).all()
    return render_section_landing(
        "Around the NBA",
        "League News",
        "Daily league notes, transactions, historical context and team developments.",
        articles,
        primary_label="Around the NBA",
    )


@app.route("/nba-play")
def nba_play():
    articles = Article.query.filter(Article.category.in_(["Video", "Highlights", "Features", "Around the NBA"])).order_by(Article.published_at.desc()).limit(10).all()
    return render_section_landing(
        "NBA Play",
        "NBA Play",
        "Video-style stories, highlights and interactive fan-facing coverage.",
        articles,
        primary_label="Featured NBA Play",
        include_games=True,
    )


@app.route("/fantasy")
def fantasy():
    articles = Article.query.filter(Article.category.in_(["Analysis", "Preview", "Features"])).order_by(Article.published_at.desc()).limit(8).all()
    players = Player.query.order_by(Player.ppg.desc()).all()
    return render_template("fantasy.html", articles=articles, fantasy=fantasy_page_context(players, articles))


@app.route("/bal-2026")
def bal_2026():
    articles = Article.query.filter(Article.category.in_(["Draft", "Around the NBA", "History"])).order_by(Article.published_at.desc()).limit(8).all()
    return render_section_landing(
        "BAL 2026",
        "Basketball Africa League",
        "A local NBA-style landing page for BAL 2026 context, prospects and league notes.",
        articles,
        primary_label="BAL 2026 Coverage",
    )


@app.route("/league-pass")
def league_pass():
    scheduled = Game.query.filter(Game.status != "Final").order_by(Game.game_date).all()
    videos = Article.query.filter(Article.category.in_(["Video", "Highlights"])).order_by(Article.published_at.desc()).limit(4).all()
    return render_template(
        "league_pass.html",
        games=scheduled,
        videos=videos,
        headlines=Article.query.order_by(Article.published_at.desc()).limit(8).all(),
    )


@app.route("/affiliates")
@app.route("/apps")
def affiliates():
    return render_template(
        "affiliates.html",
        teams=Team.query.order_by(Team.conference, Team.division, Team.city).all(),
        articles=Article.query.filter(Article.category.in_(["Around the NBA", "History", "Awards"])).order_by(Article.published_at.desc()).limit(6).all(),
    )


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = User.query.filter_by(email=request.form.get("email", "").strip().lower()).first()
        if user and user.check_password(request.form.get("password", "")):
            login_user(user)
            flash("Signed in to NBA ID.", "success")
            return redirect(request.args.get("next") or url_for("account"))
        flash("Invalid email or password.", "error")
    return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        if User.query.filter_by(email=email).first():
            flash("That email is already registered.", "error")
        else:
            user = User(
                username=slugify(request.form.get("display_name", email.split("@")[0])).replace("-", "_"),
                email=email,
                display_name=request.form.get("display_name", "NBA Fan").strip() or "NBA Fan",
            )
            user.set_password(request.form.get("password", ""))
            db.session.add(user)
            db.session.commit()
            login_user(user)
            return redirect(url_for("account"))
    return render_template("register.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Signed out.", "info")
    return redirect(url_for("index"))


@app.route("/account")
@login_required
def account():
    favorite_team = Team.query.filter_by(slug=current_user.favorite_team_slug).first()
    return render_template("account.html", favorites=favorite_pairs(current_user), favorite_team=favorite_team)


@app.route("/account/edit", methods=["GET", "POST"])
@login_required
def account_edit():
    if request.method == "POST":
        current_user.display_name = request.form.get("display_name", current_user.display_name).strip()
        current_user.phone = request.form.get("phone", "").strip()
        current_user.address_line1 = request.form.get("address_line1", "").strip()
        current_user.city = request.form.get("city", "").strip()
        current_user.state = request.form.get("state", "").strip()
        current_user.zip_code = request.form.get("zip_code", "").strip()
        current_user.favorite_team_slug = request.form.get("favorite_team_slug", "")
        current_user.payment_last4 = request.form.get("payment_last4", current_user.payment_last4)[-4:]
        db.session.commit()
        flash("Account details updated.", "success")
        return redirect(url_for("account"))
    return render_template("account_edit.html", teams=Team.query.order_by(Team.city).all())


@app.route("/teams")
def teams():
    east = Team.query.filter_by(conference="East").order_by(Team.division, Team.city).all()
    west = Team.query.filter_by(conference="West").order_by(Team.division, Team.city).all()
    return render_template("teams.html", east=east, west=west, divisions=grouped_teams_by_division())


@app.route("/teams/<slug>")
def team_detail(slug):
    team = get_or_404(Team, slug)
    games = Game.query.filter((Game.home_team_id == team.id) | (Game.away_team_id == team.id)).order_by(Game.game_date).all()
    articles = Article.query.filter_by(related_team_slug=team.slug).order_by(Article.published_at.desc()).all()
    products = Product.query.filter_by(team_slug=team.slug).limit(4).all()
    return render_template(
        "team_detail.html",
        team=team,
        games=games,
        upcoming=[game for game in games if game.status == "Scheduled"],
        recent=[game for game in games if game.status == "Final"],
        articles=articles,
        products=products,
    )


@app.route("/teams/<slug>/roster")
def team_roster(slug):
    team = get_or_404(Team, slug)
    return render_template("team_roster.html", team=team, players=team.players)


@app.route("/teams/<slug>/schedule")
def team_schedule(slug):
    team = get_or_404(Team, slug)
    games = Game.query.filter((Game.home_team_id == team.id) | (Game.away_team_id == team.id)).order_by(Game.game_date).all()
    return render_template("team_schedule.html", team=team, grouped_games=grouped_games(games), games=games)


@app.route("/teams/<slug>/stats")
def team_stats_detail(slug):
    team = get_or_404(Team, slug)
    players = sorted(team.players, key=lambda player: (-player.ppg, player.name))
    games = Game.query.filter((Game.home_team_id == team.id) | (Game.away_team_id == team.id)).order_by(Game.game_date).all()
    team.point_diff = team_point_diff(team)
    team.last_ten = team_last_ten(team)
    return render_template("team_stats_detail.html", team=team, players=players, games=games, stat_value=stat_value)


@app.route("/players")
def players():
    name = request.args.get("name", "").strip()
    position = request.args.get("position", "")
    team_slug = request.args.get("team", "")
    page = max(1, int(request.args.get("page", 1)))
    per_page = 20
    query = Player.query
    if position:
        query = query.filter(Player.position.ilike(f"%{position}%"))
    if team_slug:
        team = Team.query.filter_by(slug=team_slug).first()
        if team:
            query = query.filter_by(team_id=team.id)
    if name:
        query = query.filter(Player.name.ilike(f"%{name}%"))
    all_players = query.order_by(Player.name).all()
    start = (page - 1) * per_page
    players_list = all_players[start:start + per_page]
    pagination = {
        "page": page,
        "pages": max(1, (len(all_players) + per_page - 1) // per_page),
        "total": len(all_players),
        "endpoint": "players",
        "args": {"name": name, "position": position, "team": team_slug},
    }
    return render_template(
        "players.html",
        players=players_list,
        teams=Team.query.order_by(Team.city).all(),
        position=position,
        team_slug=team_slug,
        name=name,
        pagination=pagination,
    )


@app.route("/players/<slug>")
def player_detail(slug):
    player = get_or_404(Player, slug)
    articles = Article.query.filter_by(related_player_slug=player.slug).order_by(Article.published_at.desc()).all()
    products = Product.query.filter(Product.name.ilike(f"%{player.team.name}%")).limit(4).all()
    return render_template("player_detail.html", player=player, articles=articles, products=products, stat_value=stat_value)


@app.route("/standings")
def standings():
    view = request.args.get("view", "conference")
    section = request.args.get("section", "overall")
    if view not in {"conference", "division"}:
        view = "conference"
    if section not in {"overall", "streaks", "ahead", "margins", "calendar"}:
        section = "overall"
    east = attach_standing_fields(Team.query.filter_by(conference="East").all())
    west = attach_standing_fields(Team.query.filter_by(conference="West").all())
    divisions = {division: attach_standing_fields(rows) for division, rows in grouped_teams_by_division().items()}
    all_teams = attach_standing_fields(Team.query.all())
    teams_by_slug = {team.slug: team for team in Team.query.all()}
    return render_template("standings.html", east=east, west=west, divisions=divisions, all_teams=all_teams, teams_by_slug=teams_by_slug, view=view, section=section)


@app.route("/stats")
def stats():
    stat = request.args.get("stat", "ppg")
    if stat not in PLAYER_STAT_FIELDS:
        stat = "ppg"
    players_list = players_sorted_by_stat(stat)
    teams_list = sorted(Team.query.all(), key=lambda team: (-team.ppg, team.city))
    stats_home = stats_home_context()
    return render_template(
        "stats.html",
        players=players_list,
        teams=teams_list,
        stat=stat,
        leaders=stats_leaders(),
        stat_labels=PLAYER_STAT_FIELDS,
        stat_value=stat_value,
        stats_home=stats_home,
        articles=Article.query.order_by(Article.published_at.desc()).limit(6).all(),
    )


@app.route("/stats/players")
def player_stats():
    stat = request.args.get("stat", "ppg")
    team_slug = request.args.get("team", "")
    if stat not in PLAYER_STAT_FIELDS:
        stat = "ppg"
    players_list = players_sorted_by_stat(stat)
    if team_slug:
        players_list = [player for player in players_list if player.team.slug == team_slug]
    return render_template(
        "player_stats.html",
        players=players_list,
        teams=Team.query.order_by(Team.city).all(),
        stat=stat,
        team_slug=team_slug,
        stat_labels=PLAYER_STAT_FIELDS,
        stat_value=stat_value,
    )


@app.route("/stats/teams")
def team_stats():
    sort = request.args.get("sort", "ppg")
    if sort not in {"ppg", "oppg", "point_diff", "wins"}:
        sort = "ppg"
    teams_list = Team.query.all()
    if sort == "point_diff":
        teams_list = sorted(teams_list, key=lambda team: (-team_point_diff(team), team.city))
    else:
        teams_list = sorted(teams_list, key=lambda team: (-getattr(team, sort), team.city))
    for team in teams_list:
        team.point_diff = team_point_diff(team)
    return render_template("team_stats.html", teams=teams_list, sort=sort)


@app.route("/games")
def games():
    status = request.args.get("status", "")
    date_param = request.args.get("date", "")
    hide_scores = request.args.get("hide_scores") == "1"
    selected_date = MIRROR_REFERENCE_DATE.date()
    if date_param:
        try:
            selected_date = datetime.strptime(date_param, "%Y-%m-%d").date()
        except ValueError:
            date_param = ""
    query = Game.query
    if status:
        query = query.filter_by(status=status)
    elif date_param:
        query = query.filter(
            Game.game_date >= datetime.combine(selected_date, datetime.min.time()),
            Game.game_date <= datetime.combine(selected_date, datetime.max.time()),
        )
    elif request.args.get("view") != "all":
        query = query.filter(Game.status != "Final")
    games_list = query.order_by(Game.game_date).all()
    if not status and not date_param and request.args.get("view") != "all":
        games_list = games_list[:2]
    headlines = Article.query.order_by(Article.published_at.desc()).limit(9).all()
    return render_template(
        "games.html",
        games=games_list,
        grouped_games=grouped_games(games_list),
        status=status,
        calendar_days=game_calendar_days(selected_date),
        selected_date=selected_date,
        prev_week_date=(selected_date - timedelta(days=7)).strftime("%Y-%m-%d"),
        next_week_date=(selected_date + timedelta(days=7)).strftime("%Y-%m-%d"),
        date_param=date_param,
        hide_scores=hide_scores,
        headlines=headlines,
    )


@app.route("/schedule")
def schedule():
    status = request.args.get("status", "")
    team_slug = request.args.get("team", "")
    season_type = request.args.get("season_type", "All Games")
    month = request.args.get("month", "")
    query = Game.query
    if status:
        query = query.filter_by(status=status)
    if team_slug:
        team = Team.query.filter_by(slug=team_slug).first()
        if team:
            query = query.filter((Game.home_team_id == team.id) | (Game.away_team_id == team.id))
    games_list = query.order_by(Game.game_date).all()
    if month:
        try:
            month_int = int(month)
            games_list = [game for game in games_list if game.game_date.month == month_int]
        except ValueError:
            month = ""
    if season_type == "Playoffs":
        games_list = [game for game in games_list if "semifinal" in game.recap.lower() or "playoff" in game_round_label(game).lower()]
    elif season_type == "Regular Season":
        games_list = []
    months = sorted({game.game_date.month for game in Game.query.all()})
    teams_by_slug = {team.slug: team for team in Team.query.all()}
    return render_template(
        "schedule.html",
        games=games_list,
        grouped_games=grouped_games(games_list),
        teams=Team.query.order_by(Team.city).all(),
        teams_by_slug=teams_by_slug,
        status=status,
        team_slug=team_slug,
        season_type=season_type,
        month=month,
        months=months,
        scoreboard_games_list=scoreboard_games(),
        official_schedule=official_schedule_context(teams_by_slug),
    )


@app.route("/games/<int:game_id>")
def game_detail(game_id):
    game = db.session.get(Game, game_id)
    if not game:
        abort(404)
    slugs = [game.home_team.slug, game.away_team.slug]
    related = Article.query.filter(Article.related_team_slug.in_(slugs)).order_by(Article.published_at.desc()).limit(6).all()
    return render_template("game_detail.html", game=game, related=related)


@app.route("/playoffs/series/<series_slug>")
def playoff_series(series_slug):
    slugs = series_slug.split("-vs-")
    if len(slugs) != 2:
        abort(404)
    team_a = Team.query.filter_by(slug=slugs[0]).first_or_404()
    team_b = Team.query.filter_by(slug=slugs[1]).first_or_404()
    games = Game.query.filter(
        ((Game.home_team_id == team_a.id) & (Game.away_team_id == team_b.id)) |
        ((Game.home_team_id == team_b.id) & (Game.away_team_id == team_a.id))
    ).order_by(Game.game_date).all()
    if not games:
        abort(404)
    articles = Article.query.filter(Article.related_team_slug.in_([team_a.slug, team_b.slug])).order_by(Article.published_at.desc()).limit(8).all()
    return render_template("series.html", team_a=team_a, team_b=team_b, games=games, articles=articles)


@app.route("/news")
def news():
    category = request.args.get("category", "")
    query = Article.query
    if category:
        query = query.filter_by(category=category)
    articles = query.order_by(Article.published_at.desc()).all()
    all_articles = Article.query.order_by(Article.published_at.desc()).all()
    return render_template(
        "news.html",
        articles=articles,
        all_articles=all_articles,
        hero=articles[0] if articles else None,
        category=category,
        groups=article_groups(all_articles),
    )


@app.route("/news/<slug>")
def article_detail(slug):
    article = get_or_404(Article, slug)
    related = Article.query.filter(Article.category == article.category, Article.id != article.id).limit(4).all()
    latest = Article.query.filter(Article.id != article.id).order_by(Article.published_at.desc()).limit(8).all()
    return render_template("article_detail.html", article=article, related=related, latest=latest, detail=article_detail_profile(article))


@app.route("/watch")
def watch():
    videos = Article.query.filter(Article.category.in_(["Video", "Highlights"])).order_by(Article.published_at.desc()).all()
    return render_template("watch.html", videos=videos, hero=videos[0] if videos else None)


@app.route("/tickets", methods=["GET", "POST"])
def tickets():
    team_slug = request.args.get("team", "")
    if request.method == "POST":
        if not current_user.is_authenticated:
            flash("Sign in to save ticket requests.", "info")
            return redirect(url_for("login", next=request.url))
        game = db.session.get(Game, int(request.form.get("game_id")))
        if not game:
            abort(404)
        db.session.add(TicketRequest(
            user_id=current_user.id,
            game_id=game.id,
            seats=max(1, int(request.form.get("seats", 2))),
            section_preference=request.form.get("section_preference", "Lower bowl"),
        ))
        db.session.commit()
        flash("Ticket request saved to your NBA ID.", "success")
        return redirect(url_for("account"))
    query = Game.query.filter(Game.status == "Scheduled")
    selected_team = None
    if team_slug:
        selected_team = Team.query.filter_by(slug=team_slug).first()
        if selected_team:
            query = query.filter((Game.home_team_id == selected_team.id) | (Game.away_team_id == selected_team.id))
    upcoming = query.order_by(Game.game_date).all()
    return render_template(
        "tickets.html",
        games=upcoming,
        teams=Team.query.order_by(Team.city).all(),
        team_slug=team_slug,
        selected_team=selected_team,
    )


@app.route("/shop")
@app.route("/store")
def shop():
    category = request.args.get("category", "")
    team = request.args.get("team", "")
    products = Product.query
    if category:
        products = products.filter_by(category=category)
    if team:
        products = products.filter_by(team_slug=team)
    return render_template("shop.html", products=products.order_by(Product.category, Product.name).all(), category=category, team=team)


@app.route("/shop/<slug>")
@app.route("/store/<slug>")
def product_detail(slug):
    product = get_or_404(Product, slug)
    related = Product.query.filter(Product.category == product.category, Product.id != product.id).limit(4).all()
    return render_template("product_detail.html", product=product, related=related)


@app.route("/cart")
@login_required
def cart():
    subtotal = sum(item.product.price * item.quantity for item in current_user.cart_items)
    return render_template("cart.html", subtotal=subtotal)


@app.route("/cart/add/<slug>", methods=["POST"])
@login_required
def cart_add(slug):
    product = get_or_404(Product, slug)
    size = request.form.get("size", "M")
    quantity = max(1, int(request.form.get("quantity", 1)))
    existing = CartItem.query.filter_by(user_id=current_user.id, product_id=product.id, size=size).first()
    if existing:
        existing.quantity += quantity
    else:
        db.session.add(CartItem(user_id=current_user.id, product_id=product.id, quantity=quantity, size=size))
    db.session.commit()
    flash("Added to bag.", "success")
    return redirect(url_for("cart"))


@app.route("/cart/update", methods=["POST"])
@login_required
def cart_update():
    for item in list(current_user.cart_items):
        qty = int(request.form.get(f"qty_{item.id}", item.quantity))
        if qty <= 0:
            db.session.delete(item)
        else:
            item.quantity = min(qty, 9)
    db.session.commit()
    return redirect(url_for("cart"))


@app.route("/checkout", methods=["GET", "POST"])
@login_required
def checkout():
    if not current_user.cart_items:
        flash("Your bag is empty.", "error")
        return redirect(url_for("shop"))
    subtotal = sum(item.product.price * item.quantity for item in current_user.cart_items)
    shipping = 8.95 if subtotal < 100 else 0
    tax = round(subtotal * 0.0825, 2)
    total = round(subtotal + shipping + tax, 2)
    if request.method == "POST":
        address = request.form.get("ship_address", current_user.address_line1).strip()
        if not address:
            flash("Shipping address is required.", "error")
        else:
            order = Order(
                user_id=current_user.id,
                order_number=f"NBA-{MIRROR_REFERENCE_DATE:%Y%m%d}-{current_user.id}{Order.query.count()+1:03d}",
                status="Processing",
                subtotal=subtotal,
                shipping=shipping,
                tax=tax,
                total=total,
                ship_address=address,
                payment_last4=request.form.get("payment_last4", current_user.payment_last4)[-4:],
                created_at=MIRROR_REFERENCE_DATE,
            )
            db.session.add(order)
            db.session.flush()
            for item in list(current_user.cart_items):
                db.session.add(OrderItem(order_id=order.id, product_name=item.product.name, quantity=item.quantity, price=item.product.price, size=item.size))
                db.session.delete(item)
            db.session.commit()
            flash("Order placed.", "success")
            return redirect(url_for("orders"))
    return render_template("checkout.html", subtotal=subtotal, shipping=shipping, tax=tax, total=total)


@app.route("/orders")
@login_required
def orders():
    return render_template("orders.html", orders=current_user.orders)


@app.route("/favorite/<item_type>/<int:item_id>", methods=["POST"])
@login_required
def favorite(item_type, item_id):
    if item_type not in {"team", "player", "article", "product"}:
        abort(404)
    existing = Favorite.query.filter_by(user_id=current_user.id, item_type=item_type, item_id=item_id).first()
    if existing:
        db.session.delete(existing)
        flash("Removed from favorites.", "info")
    else:
        db.session.add(Favorite(user_id=current_user.id, item_type=item_type, item_id=item_id, note=request.form.get("note", "")))
        flash("Saved to favorites.", "success")
    db.session.commit()
    return redirect(request.referrer or url_for("account"))


@app.route("/search")
def search():
    q = request.args.get("q", "").strip()
    teams_found = scored_search(q, Team.query.all(), ["city", "name", "abbreviation", "conference", "division", "arena", "coach"]) if q else []
    players_found = scored_search(q, Player.query.all(), ["name", "position", "country", "college", "bio"]) if q else []
    articles_found = scored_search(q, Article.query.all(), ["title", "category", "dek", "body", "author"]) if q else []
    products_found = scored_search(q, Product.query.all(), ["name", "category", "description", "color", "features"]) if q else []
    stats_found = []
    games_found = []
    if q:
        if any(token in q.lower() for token in ["points", "rebounds", "assists", "blocks", "steals", "turnovers", "stats"]):
            stats_found = Player.query.order_by(Player.ppg.desc()).limit(8).all()
        text_games = []
        for game in Game.query.all():
            game.search_text = f"{game.home_team.full_name} {game.away_team.full_name} {game.status} {game.arena} {game.broadcast} {game.recap}"
            text_games.append(game)
        games_found = scored_search(q, text_games, ["search_text"])
    return render_template(
        "search.html",
        q=q,
        teams=teams_found,
        players=players_found,
        articles=articles_found,
        products=products_found,
        games=games_found,
        stats=stats_found,
    )


TEAM_SEED = [
    ("Boston", "Celtics", "BOS", "East", "Atlantic", 64, 18, "37-4", "27-14", "W7", 120.6, 109.2, "TD Garden", "Joe Mazzulla", "#007A33", "celtics"),
    ("New York", "Knicks", "NYK", "East", "Atlantic", 50, 32, "27-14", "23-18", "W5", 112.8, 108.2, "Madison Square Garden", "Tom Thibodeau", "#006BB6", "knicks"),
    ("Philadelphia", "76ers", "PHI", "East", "Atlantic", 47, 35, "25-16", "22-19", "W8", 114.6, 111.5, "Wells Fargo Center", "Nick Nurse", "#006BB6", "seventysixers"),
    ("Milwaukee", "Bucks", "MIL", "East", "Central", 49, 33, "31-11", "18-22", "L2", 119.0, 116.4, "Fiserv Forum", "Doc Rivers", "#00471B", "bucks"),
    ("Cleveland", "Cavaliers", "CLE", "East", "Central", 48, 34, "26-15", "22-19", "L1", 112.6, 110.2, "Rocket Mortgage FieldHouse", "Kenny Atkinson", "#860038", "cavaliers"),
    ("Indiana", "Pacers", "IND", "East", "Central", 47, 35, "26-15", "21-20", "W1", 123.3, 120.2, "Gainbridge Fieldhouse", "Rick Carlisle", "#FDBB30", "pacers"),
    ("Orlando", "Magic", "ORL", "East", "Southeast", 47, 35, "29-12", "18-23", "W1", 110.5, 108.4, "Kia Center", "Jamahl Mosley", "#0077C0", "magic"),
    ("Miami", "Heat", "MIA", "East", "Southeast", 46, 36, "22-19", "24-17", "L1", 110.1, 108.4, "Kaseya Center", "Erik Spoelstra", "#98002E", "heat"),
    ("Atlanta", "Hawks", "ATL", "East", "Southeast", 36, 46, "21-20", "15-26", "L6", 118.3, 120.5, "State Farm Arena", "Quin Snyder", "#E03A3E", "hawks"),
    ("Chicago", "Bulls", "CHI", "East", "Central", 39, 43, "20-21", "19-22", "L2", 112.3, 113.7, "United Center", "Billy Donovan", "#CE1141", "bulls"),
    ("Dallas", "Mavericks", "DAL", "West", "Southwest", 50, 32, "25-16", "25-16", "W2", 117.9, 115.6, "American Airlines Center", "Jason Kidd", "#00538C", "mavericks"),
    ("Denver", "Nuggets", "DEN", "West", "Northwest", 57, 25, "33-8", "24-17", "W1", 114.9, 109.6, "Ball Arena", "Michael Malone", "#0E2240", "nuggets"),
    ("Minnesota", "Timberwolves", "MIN", "West", "Northwest", 56, 26, "30-11", "26-15", "W1", 113.0, 106.5, "Target Center", "Chris Finch", "#0C2340", "timberwolves"),
    ("Oklahoma City", "Thunder", "OKC", "West", "Northwest", 58, 24, "34-7", "24-17", "W5", 120.1, 112.7, "Paycom Center", "Mark Daigneault", "#007AC1", "thunder"),
    ("Phoenix", "Suns", "PHX", "West", "Pacific", 49, 33, "25-16", "24-17", "W3", 116.2, 113.2, "Footprint Center", "Mike Budenholzer", "#1D1160", "suns"),
    ("Los Angeles", "Lakers", "LAL", "West", "Pacific", 47, 35, "28-14", "19-21", "W2", 118.0, 117.4, "Crypto.com Arena", "JJ Redick", "#552583", "lakers"),
    ("LA", "Clippers", "LAC", "West", "Pacific", 51, 31, "25-16", "26-15", "L3", 115.6, 112.3, "Intuit Dome", "Tyronn Lue", "#C8102E", "clippers"),
    ("Golden State", "Warriors", "GSW", "West", "Pacific", 46, 36, "21-20", "25-16", "W1", 117.8, 115.2, "Chase Center", "Steve Kerr", "#1D428A", "warriors"),
    ("Sacramento", "Kings", "SAC", "West", "Pacific", 46, 36, "24-17", "22-19", "L1", 116.6, 114.8, "Golden 1 Center", "Doug Christie", "#5A2D81", "kings"),
    ("New Orleans", "Pelicans", "NOP", "West", "Southwest", 49, 33, "21-19", "28-14", "L1", 115.1, 110.7, "Smoothie King Center", "Willie Green", "#0C2340", "pelicans"),
    ("San Antonio", "Spurs", "SAS", "West", "Southwest", 22, 60, "12-29", "10-31", "W2", 112.1, 118.6, "Frost Bank Center", "Gregg Popovich", "#C4CED4", "spurs"),
    ("Memphis", "Grizzlies", "MEM", "West", "Southwest", 27, 55, "9-32", "18-23", "L5", 105.8, 112.8, "FedExForum", "Taylor Jenkins", "#5D76A9", "grizzlies"),
    ("Houston", "Rockets", "HOU", "West", "Southwest", 41, 41, "27-14", "14-27", "W2", 114.3, 113.2, "Toyota Center", "Ime Udoka", "#CE1141", "rockets"),
    ("Toronto", "Raptors", "TOR", "East", "Atlantic", 25, 57, "14-27", "11-30", "L4", 112.4, 118.8, "Scotiabank Arena", "Darko Rajakovic", "#CE1141", "raptors"),
    ("Brooklyn", "Nets", "BKN", "East", "Atlantic", 32, 50, "20-21", "12-29", "L2", 110.4, 113.3, "Barclays Center", "Jordi Fernandez", "#000000", "nets"),
    ("Charlotte", "Hornets", "CHA", "East", "Southeast", 21, 61, "11-30", "10-31", "W1", 106.6, 116.8, "Spectrum Center", "Charles Lee", "#1D1160", "hornets"),
    ("Detroit", "Pistons", "DET", "East", "Central", 14, 68, "7-33", "7-35", "L1", 109.9, 119.0, "Little Caesars Arena", "J.B. Bickerstaff", "#C8102E", "pistons"),
    ("Portland", "Trail Blazers", "POR", "West", "Northwest", 21, 61, "11-30", "10-31", "L5", 106.4, 115.4, "Moda Center", "Chauncey Billups", "#E03A3E", "trail_blazers"),
    ("Utah", "Jazz", "UTA", "West", "Northwest", 31, 51, "21-20", "10-31", "L1", 115.7, 120.5, "Delta Center", "Will Hardy", "#002B5C", "jazz"),
    ("Washington", "Wizards", "WAS", "East", "Southeast", 15, 67, "7-34", "8-33", "L6", 113.7, 123.0, "Capital One Arena", "Brian Keefe", "#002B5C", "wizards"),
]

PLAYER_SEED = [
    ("LeBron James", "lakers", "F", "23", "6-9", 250, 39, "USA", "St. Vincent-St. Mary HS", 25.7, 7.3, 8.3, 1.3, 0.5, 54.0, 41.0, "All-NBA forward directing the Lakers offense from the frontcourt.", "lebron_james"),
    ("Anthony Davis", "lakers", "C", "3", "6-10", 253, 31, "USA", "Kentucky", 24.7, 12.6, 3.5, 1.2, 2.3, 55.6, 27.1, "Elite rim protector and interior scorer.", "anthony_davis"),
    ("Luka Doncic", "mavericks", "G", "77", "6-7", 230, 25, "Slovenia", "Real Madrid", 33.9, 9.2, 9.8, 1.4, 0.5, 48.7, 38.2, "High-usage creator who bends defenses with passing and step-back scoring.", "luka_doncic"),
    ("Kyrie Irving", "mavericks", "G", "11", "6-2", 195, 32, "Australia", "Duke", 25.6, 5.0, 5.2, 1.3, 0.5, 49.7, 41.1, "Shot-making guard with elite handle and late-clock scoring.", "kyrie_irving"),
    ("Jayson Tatum", "celtics", "F", "0", "6-8", 210, 26, "USA", "Duke", 26.9, 8.1, 4.9, 1.0, 0.6, 47.1, 37.6, "Two-way wing and first option for Boston.", "jayson_tatum"),
    ("Jaylen Brown", "celtics", "G-F", "7", "6-6", 223, 27, "USA", "California", 23.0, 5.5, 3.6, 1.2, 0.5, 49.9, 35.4, "Physical wing scorer who attacks mismatches.", "jaylen_brown"),
    ("Nikola Jokic", "nuggets", "C", "15", "6-11", 284, 29, "Serbia", "Mega Basket", 26.4, 12.4, 9.0, 1.4, 0.9, 58.3, 35.9, "Offensive hub with historic passing from the center position.", "nikola_jokic"),
    ("Jamal Murray", "nuggets", "G", "27", "6-4", 215, 27, "Canada", "Kentucky", 21.2, 4.1, 6.5, 1.0, 0.7, 48.1, 42.5, "Pick-and-roll guard known for playoff shot creation.", "jamal_murray"),
    ("Giannis Antetokounmpo", "bucks", "F", "34", "6-11", 243, 29, "Greece", "Filathlitikos", 30.4, 11.5, 6.5, 1.2, 1.1, 61.1, 27.4, "Rim pressure superstar and transition force.", "giannis_antetokounmpo"),
    ("Damian Lillard", "bucks", "G", "0", "6-2", 195, 33, "USA", "Weber State", 24.3, 4.4, 7.0, 1.0, 0.2, 42.4, 35.4, "Deep-range guard who closes games from well beyond the arc.", "damian_lillard"),
    ("Stephen Curry", "warriors", "G", "30", "6-2", 185, 36, "USA", "Davidson", 26.4, 4.5, 5.1, 0.7, 0.4, 45.0, 40.8, "Movement shooter who warps defensive coverages.", "stephen_curry"),
    ("Draymond Green", "warriors", "F", "23", "6-6", 230, 34, "USA", "Michigan State", 8.6, 7.2, 6.0, 1.0, 0.9, 49.7, 39.5, "Defensive organizer and short-roll passer.", "draymond_green"),
    ("Shai Gilgeous-Alexander", "thunder", "G", "2", "6-6", 195, 25, "Canada", "Kentucky", 30.1, 5.5, 6.2, 2.0, 0.9, 53.5, 35.3, "Slashing guard with elite efficiency and foul pressure.", "shai_gilgeous_alexander"),
    ("Chet Holmgren", "thunder", "C-F", "7", "7-1", 208, 22, "USA", "Gonzaga", 16.5, 7.9, 2.4, 0.6, 2.3, 53.0, 37.0, "Floor-spacing rim protector with unusual length.", "chet_holmgren"),
    ("Kevin Durant", "suns", "F", "35", "6-11", 240, 35, "USA", "Texas", 27.1, 6.6, 5.0, 0.9, 1.2, 52.3, 41.3, "Efficient isolation scorer with unblockable release.", "kevin_durant"),
    ("Devin Booker", "suns", "G", "1", "6-5", 206, 27, "USA", "Kentucky", 27.1, 4.5, 6.9, 0.9, 0.4, 49.2, 36.4, "Three-level scorer and secondary playmaker.", "devin_booker"),
    ("Jalen Brunson", "knicks", "G", "11", "6-2", 190, 27, "USA", "Villanova", 28.7, 3.6, 6.7, 0.9, 0.2, 47.9, 40.1, "Crafty lead guard carrying New York's half-court offense.", "jalen_brunson"),
    ("Joel Embiid", "seventysixers", "C", "21", "7-0", 280, 30, "Cameroon", "Kansas", 34.7, 11.0, 5.6, 1.2, 1.7, 52.9, 38.8, "Post scorer and foul-drawing center with range.", "joel_embiid"),
    ("Tyrese Haliburton", "pacers", "G", "0", "6-5", 185, 24, "USA", "Iowa State", 20.1, 3.9, 10.9, 1.2, 0.7, 47.7, 36.4, "Transition passer and pick-and-roll organizer.", "tyrese_haliburton"),
    ("Anthony Edwards", "timberwolves", "G", "5", "6-4", 225, 22, "USA", "Georgia", 25.9, 5.4, 5.1, 1.3, 0.5, 46.1, 35.7, "Explosive two-way guard with downhill pressure.", "anthony_edwards"),
    ("Jimmy Butler", "heat", "F", "22", "6-7", 230, 34, "USA", "Marquette", 20.8, 5.3, 5.0, 1.3, 0.3, 49.9, 41.4, "Physical wing who controls playoff tempo.", "jimmy_butler"),
    ("Victor Wembanyama", "spurs", "C-F", "1", "7-4", 210, 20, "France", "Metropolitans 92", 21.4, 10.6, 3.9, 1.2, 3.6, 46.5, 32.5, "Generational rookie rim protector with perimeter skill.", "victor_wembanyama"),
    ("Paolo Banchero", "magic", "F", "5", "6-10", 250, 21, "USA", "Duke", 22.6, 6.9, 5.4, 0.9, 0.6, 45.5, 33.9, "Big wing creator powering Orlando's offense.", "paolo_banchero"),
    ("Donovan Mitchell", "cavaliers", "G", "45", "6-3", 215, 27, "USA", "Louisville", 26.6, 5.1, 6.1, 1.8, 0.5, 46.2, 36.8, "Explosive scoring guard leading Cleveland.", "donovan_mitchell"),
    ("Tyrese Maxey", "seventysixers", "G", "0", "6-2", 200, 23, "USA", "Kentucky", 25.9, 3.7, 6.2, 1.0, 0.5, 45.0, 37.3, "Speed guard who stretches defenses in transition.", "tyrese_maxey"),
    ("Ja Morant", "grizzlies", "G", "12", "6-2", 174, 24, "USA", "Murray State", 25.1, 5.6, 8.1, 0.8, 0.6, 47.1, 27.5, "Explosive point guard returning to lead Memphis.", "ja_morant"),
    ("Kawhi Leonard", "clippers", "F", "2", "6-7", 225, 32, "USA", "San Diego State", 23.7, 6.1, 3.6, 1.6, 0.9, 52.5, 41.7, "Efficient wing scorer and point-of-attack defender.", "kawhi_leonard"),
    ("Paul George", "clippers", "F", "13", "6-8", 220, 34, "USA", "Fresno State", 22.6, 5.2, 3.5, 1.5, 0.5, 47.1, 41.3, "Smooth wing shooter who guards multiple positions.", "paul_george"),
]


# EXTRA_ROSTERS — supplementary rosters per team. Stats are within plausible NBA
# ranges. Image left empty so the per-player render falls back to team logo.
EXTRA_ROSTERS = {
    "celtics": [
        ("Jrue Holiday", "G", "4", "6-4", 205, 34, "USA", "UCLA", 12.5, 5.4, 4.8, 0.9, 0.7, 48.2, 39.0, "Two-way guard who handles primary defensive assignments."),
        ("Kristaps Porzingis", "C", "8", "7-3", 240, 28, "Latvia", "International", 20.1, 7.2, 2.0, 0.7, 1.9, 51.6, 37.5, "Stretch big with rim protection and pick-and-pop range."),
        ("Derrick White", "G", "9", "6-4", 190, 30, "USA", "Colorado", 15.2, 4.2, 5.2, 1.0, 1.1, 46.1, 39.6, "Connector guard with elite off-ball shot-blocking."),
        ("Payton Pritchard", "G", "11", "6-1", 195, 26, "USA", "Oregon", 14.3, 3.8, 3.4, 0.9, 0.2, 47.2, 40.7, "Microwave bench scorer and movement shooter."),
        ("Al Horford", "C", "42", "6-9", 240, 38, "Dominican Rep.", "Florida", 9.0, 6.4, 2.6, 0.6, 1.0, 48.0, 41.9, "Veteran stretch five with elite team-defense IQ."),
        ("Sam Hauser", "F", "30", "6-7", 217, 26, "USA", "Virginia", 9.0, 3.5, 1.0, 0.5, 0.3, 45.5, 41.9, "Specialist wing who rains catch-and-shoot threes."),
    ],
    "knicks": [
        ("OG Anunoby", "F", "8", "6-7", 232, 27, "USA", "Indiana", 18.0, 4.8, 2.2, 1.6, 0.7, 48.6, 39.3, "Versatile two-way wing who switches across positions."),
        ("Mikal Bridges", "F", "25", "6-6", 209, 28, "USA", "Villanova", 17.2, 3.2, 3.6, 0.9, 0.5, 45.7, 37.2, "Iron-man wing scorer and point-of-attack defender."),
        ("Josh Hart", "G-F", "3", "6-4", 215, 29, "USA", "Villanova", 14.0, 9.4, 5.5, 1.0, 0.4, 49.9, 33.8, "Glass-cleaning guard who fills every line of the box score."),
        ("Donte DiVincenzo", "G", "0", "6-4", 203, 27, "USA", "Villanova", 12.7, 3.8, 2.7, 1.2, 0.4, 43.9, 39.5, "Sharpshooting combo guard with playoff experience."),
        ("Karl-Anthony Towns", "C", "32", "7-0", 248, 28, "Dominican Rep.", "Kentucky", 22.9, 11.6, 3.2, 0.7, 0.7, 53.0, 41.0, "Skilled center who pairs three-point range with post scoring."),
        ("Mitchell Robinson", "C", "23", "7-0", 240, 26, "USA", "International", 6.0, 8.4, 0.5, 0.5, 1.6, 61.2, 0.0, "Rim-protecting center who feasts on lob finishes."),
    ],
    "seventysixers": [
        ("Andre Drummond", "C", "5", "6-10", 279, 30, "USA", "Connecticut", 7.5, 9.0, 1.0, 0.9, 0.8, 56.2, 0.0, "Veteran rebounding center anchoring the second unit."),
        ("Kelly Oubre Jr.", "G-F", "9", "6-7", 203, 28, "USA", "Kansas", 15.4, 5.0, 1.5, 1.3, 0.5, 47.5, 32.3, "Slashing wing with multi-positional defensive tools."),
        ("Jared McCain", "G", "20", "6-3", 197, 20, "USA", "Duke", 15.3, 2.4, 2.6, 0.9, 0.2, 46.0, 38.6, "Rookie sharpshooter who quickly earned rotation minutes."),
        ("Caleb Martin", "F", "16", "6-5", 205, 28, "USA", "Nevada", 9.8, 4.5, 1.7, 0.7, 0.4, 45.0, 35.5, "Hard-playing wing who chases shooters and finishes in transition."),
        ("Eric Gordon", "G", "23", "6-3", 215, 35, "USA", "Indiana", 7.5, 1.7, 1.7, 0.4, 0.2, 39.9, 39.1, "Veteran spacer with playoff shot-making pedigree."),
        ("Guerschon Yabusele", "F-C", "28", "6-8", 260, 28, "France", "International", 11.0, 5.4, 2.1, 0.7, 0.3, 50.4, 38.0, "Skilled big who passes and shoots from the elbow."),
    ],
    "bucks": [
        ("Brook Lopez", "C", "11", "7-0", 282, 36, "USA", "Stanford", 12.5, 5.2, 1.6, 0.7, 2.4, 50.0, 36.5, "Rim-protecting stretch five who anchors the drop."),
        ("Khris Middleton", "F", "22", "6-7", 222, 32, "USA", "Texas A&M", 15.0, 4.7, 5.3, 0.9, 0.3, 49.5, 38.1, "Three-level scoring wing with late-clock pedigree."),
        ("Bobby Portis", "F-C", "9", "6-10", 250, 29, "USA", "Arkansas", 13.8, 7.4, 1.2, 0.7, 0.4, 47.5, 40.7, "Energy big who attacks the offensive glass."),
        ("Pat Connaughton", "G-F", "24", "6-5", 209, 31, "USA", "Notre Dame", 5.8, 3.6, 1.3, 0.6, 0.3, 43.2, 34.2, "Bench wing who plays both ends with maximum effort."),
        ("Andre Jackson Jr.", "G", "44", "6-6", 207, 22, "USA", "Connecticut", 4.4, 2.5, 1.5, 0.7, 0.3, 45.6, 33.3, "Athletic on-ball pest who pressures the ball-handler."),
        ("Taurean Prince", "F", "12", "6-7", 218, 30, "USA", "Baylor", 8.4, 3.0, 1.6, 0.7, 0.5, 44.5, 36.5, "Veteran 3-and-D wing who fills out the rotation."),
    ],
    "cavaliers": [
        ("Darius Garland", "G", "10", "6-1", 192, 24, "USA", "Vanderbilt", 20.7, 2.7, 6.5, 1.3, 0.1, 46.6, 39.8, "Quick guard who runs the pick-and-roll with finesse."),
        ("Jarrett Allen", "C", "31", "6-9", 243, 26, "USA", "Texas", 16.5, 10.5, 2.7, 0.7, 1.0, 63.4, 0.0, "Rim runner and lob threat with elite rebounding."),
        ("Evan Mobley", "C-F", "4", "7-0", 215, 23, "USA", "USC", 18.5, 9.3, 3.2, 0.9, 1.6, 55.0, 37.0, "Switchable big with developing perimeter game."),
        ("De'Andre Hunter", "F", "12", "6-8", 221, 27, "USA", "Virginia", 18.8, 3.5, 1.4, 0.6, 0.3, 46.5, 39.5, "Physical wing scorer added at the deadline for depth."),
        ("Sam Merrill", "G", "5", "6-5", 205, 28, "USA", "Utah State", 8.5, 2.2, 1.4, 0.6, 0.1, 41.5, 39.0, "Movement shooter who lifts second-unit spacing."),
        ("Caris LeVert", "G", "3", "6-6", 205, 29, "USA", "Michigan", 12.2, 3.7, 4.1, 0.9, 0.4, 43.2, 35.3, "Bench creator who keeps the offense flowing."),
    ],
    "pacers": [
        ("Pascal Siakam", "F", "43", "6-8", 245, 30, "Cameroon", "New Mexico State", 21.3, 6.9, 3.7, 0.9, 0.6, 51.4, 38.7, "Versatile forward who scores in the post and in transition."),
        ("Myles Turner", "C", "33", "6-11", 250, 28, "USA", "Texas", 17.4, 6.9, 1.4, 0.8, 1.9, 50.8, 39.6, "Stretch five and rim protector for the Pacers."),
        ("Bennedict Mathurin", "G-F", "00", "6-6", 210, 22, "Canada", "Arizona", 16.1, 4.4, 1.7, 0.6, 0.3, 45.7, 38.4, "Downhill scoring wing with three-level shot diet."),
        ("Andrew Nembhard", "G", "2", "6-4", 191, 24, "Canada", "Gonzaga", 9.7, 3.4, 4.3, 0.8, 0.1, 45.1, 38.0, "Steady combo guard who runs bench units."),
        ("Aaron Nesmith", "F", "23", "6-5", 215, 25, "USA", "Vanderbilt", 12.2, 3.8, 1.4, 0.8, 0.6, 50.2, 41.9, "Three-and-D wing with playoff-tested toughness."),
        ("T.J. McConnell", "G", "9", "6-1", 190, 32, "USA", "Arizona", 9.1, 2.5, 4.3, 1.1, 0.1, 50.5, 33.0, "Ball-pressure veteran who organizes the bench."),
    ],
    "magic": [
        ("Franz Wagner", "F", "22", "6-10", 220, 23, "Germany", "Michigan", 19.7, 5.3, 3.7, 1.1, 0.4, 48.0, 28.1, "Skilled wing creator who attacks closeouts."),
        ("Jalen Suggs", "G", "4", "6-4", 205, 23, "USA", "Gonzaga", 12.9, 3.1, 2.7, 1.5, 0.5, 47.0, 31.4, "Point-of-attack defender with growing offensive role."),
        ("Wendell Carter Jr.", "C", "34", "6-10", 270, 25, "USA", "Duke", 11.0, 6.9, 2.3, 0.7, 0.9, 50.5, 36.7, "Stretch center with passing chops."),
        ("Kentavious Caldwell-Pope", "G", "5", "6-5", 204, 31, "USA", "Georgia", 9.5, 2.5, 1.8, 1.1, 0.2, 43.5, 34.7, "Veteran wing shooter and on-ball defender."),
        ("Cole Anthony", "G", "50", "6-2", 185, 24, "USA", "North Carolina", 10.6, 3.4, 3.9, 0.7, 0.2, 43.8, 35.0, "Energy bench guard who creates downhill."),
        ("Goga Bitadze", "C", "35", "6-11", 250, 25, "Georgia", "International", 7.9, 5.2, 1.5, 0.5, 1.2, 56.6, 35.0, "Reliable rim-protecting backup center."),
    ],
    "heat": [
        ("Bam Adebayo", "C", "13", "6-9", 255, 27, "USA", "Kentucky", 19.3, 10.4, 4.1, 1.1, 0.9, 51.8, 35.7, "All-defense center who runs DHO offense."),
        ("Tyler Herro", "G", "14", "6-5", 195, 24, "USA", "Kentucky", 23.9, 5.3, 5.5, 0.8, 0.4, 47.2, 37.5, "Lead scoring guard with deep shot-making range."),
        ("Terry Rozier", "G", "2", "6-1", 190, 30, "USA", "Louisville", 15.5, 4.2, 4.4, 0.9, 0.4, 41.5, 35.0, "Ball-handling combo guard with pull-up range."),
        ("Duncan Robinson", "F", "55", "6-7", 215, 30, "USA", "Michigan", 12.6, 2.6, 3.0, 0.5, 0.2, 47.0, 39.5, "Movement shooter pulling defenders all over the floor."),
        ("Jaime Jaquez Jr.", "F", "11", "6-7", 226, 23, "USA", "UCLA", 12.5, 3.8, 2.4, 1.0, 0.4, 49.2, 32.6, "Crafty wing who finishes through contact."),
        ("Nikola Jovic", "F", "5", "6-10", 223, 21, "Serbia", "International", 7.7, 3.6, 1.8, 0.6, 0.3, 44.0, 33.8, "Skilled tall wing developing into a connective playmaker."),
    ],
    "hawks": [
        ("Trae Young", "G", "11", "6-1", 164, 26, "USA", "Oklahoma", 25.7, 2.8, 11.1, 1.4, 0.2, 43.0, 38.0, "Deep-range pick-and-roll guard who creates for teammates."),
        ("Jalen Johnson", "F", "1", "6-8", 219, 23, "USA", "Duke", 18.9, 10.0, 5.0, 1.1, 1.0, 51.0, 35.6, "Athletic point-forward with rebounding and transition tools."),
        ("Dyson Daniels", "G", "5", "6-7", 199, 21, "Australia", "G League Ignite", 14.1, 5.7, 4.5, 3.0, 0.6, 46.3, 34.0, "All-Defensive guard with elite hands and disruption rate."),
        ("Onyeka Okongwu", "C", "17", "6-8", 240, 24, "USA", "USC", 11.3, 8.0, 1.8, 0.7, 1.3, 56.0, 34.5, "Mobile rim protector who switches across screens."),
        ("Bogdan Bogdanovic", "G-F", "13", "6-5", 215, 32, "Serbia", "International", 14.0, 3.0, 3.0, 1.1, 0.2, 41.2, 37.2, "Veteran shot-maker with secondary creation chops."),
        ("Zaccharie Risacher", "F", "10", "6-9", 200, 19, "France", "International", 12.6, 3.6, 1.3, 0.7, 0.6, 45.6, 35.5, "No. 1 overall rookie wing with smooth shot mechanics."),
    ],
    "bulls": [
        ("Coby White", "G", "0", "6-5", 195, 24, "USA", "North Carolina", 20.4, 4.5, 5.1, 0.9, 0.3, 44.9, 37.0, "Pull-up shooting guard who creates for himself."),
        ("Nikola Vucevic", "C", "9", "6-11", 260, 34, "Montenegro", "USC", 18.4, 10.5, 3.0, 0.7, 0.7, 56.0, 39.0, "Skilled center with stretch range and post passing."),
        ("Patrick Williams", "F", "44", "6-7", 215, 23, "USA", "Florida State", 9.0, 3.5, 1.3, 0.6, 1.0, 43.0, 39.6, "Long forward with promising defensive tools."),
        ("Ayo Dosunmu", "G", "12", "6-5", 215, 25, "USA", "Illinois", 12.1, 3.0, 3.6, 1.0, 0.4, 49.5, 33.5, "Connective combo guard with sound shot diet."),
        ("Josh Giddey", "G", "3", "6-8", 215, 22, "Australia", "International", 14.6, 8.1, 7.5, 1.0, 0.6, 48.0, 33.7, "Jumbo playmaker with rebounding upside."),
        ("Matas Buzelis", "F", "14", "6-10", 209, 20, "USA", "G League Ignite", 8.6, 3.9, 1.3, 0.7, 1.0, 44.5, 35.8, "Rookie wing with shooting and shot-blocking flashes."),
    ],
    "mavericks": [
        ("PJ Washington", "F", "25", "6-7", 230, 26, "USA", "Kentucky", 12.5, 6.2, 1.8, 0.7, 1.0, 47.4, 37.0, "Versatile combo forward who switches on defense."),
        ("Daniel Gafford", "C", "21", "6-10", 234, 26, "USA", "Arkansas", 10.5, 6.8, 1.2, 0.6, 1.8, 70.0, 0.0, "Lob-finishing center who anchors the dunker spot."),
        ("Klay Thompson", "G", "31", "6-6", 215, 35, "USA", "Washington State", 14.3, 3.6, 2.0, 0.6, 0.5, 43.3, 38.0, "Iconic movement shooter still feasting off catch-and-shoot looks."),
        ("Naji Marshall", "F", "13", "6-7", 220, 26, "USA", "Xavier", 9.2, 4.0, 2.2, 0.8, 0.3, 46.6, 37.0, "Switchable wing with confident pull-up shooting."),
        ("Spencer Dinwiddie", "G", "26", "6-5", 215, 31, "USA", "Colorado", 9.0, 2.0, 4.0, 0.5, 0.3, 41.5, 32.8, "Veteran combo guard who runs second-unit offense."),
        ("Dereck Lively II", "C", "2", "7-1", 230, 21, "USA", "Duke", 8.4, 7.0, 1.1, 0.5, 1.4, 73.0, 0.0, "Long rim protector and athletic lob threat."),
    ],
    "nuggets": [
        ("Aaron Gordon", "F", "32", "6-8", 235, 29, "USA", "Arizona", 13.9, 6.5, 3.4, 0.8, 0.6, 56.7, 29.0, "Athletic forward who handles toughest defensive matchups."),
        ("Michael Porter Jr.", "F", "1", "6-10", 218, 26, "USA", "Missouri", 16.7, 7.0, 1.5, 0.7, 0.6, 48.4, 39.7, "Towering shooter with elite catch-and-shoot range."),
        ("Christian Braun", "G-F", "0", "6-6", 220, 23, "USA", "Kansas", 15.4, 5.1, 2.7, 0.9, 0.6, 57.7, 39.7, "Cutter and connector wing who plays in straight lines."),
        ("Russell Westbrook", "G", "4", "6-3", 200, 36, "USA", "UCLA", 13.0, 5.0, 6.0, 1.4, 0.4, 44.9, 32.0, "All-time triple-double leader running bench units."),
        ("Peyton Watson", "F", "8", "6-8", 200, 22, "USA", "UCLA", 8.8, 3.9, 1.4, 0.9, 1.7, 42.4, 32.7, "Long defensive wing with shot-blocking instincts."),
        ("Julian Strawther", "G-F", "3", "6-7", 205, 23, "USA", "Gonzaga", 7.0, 2.1, 1.0, 0.4, 0.2, 41.8, 37.5, "Spot-up shooter on a developing offensive role."),
    ],
    "timberwolves": [
        ("Julius Randle", "F", "30", "6-9", 250, 30, "USA", "Kentucky", 20.1, 9.0, 4.7, 0.7, 0.4, 47.0, 34.4, "Bullish forward with bruising post game and stepout range."),
        ("Rudy Gobert", "C", "27", "7-1", 258, 32, "France", "International", 13.0, 12.0, 2.0, 0.7, 2.1, 65.5, 0.0, "Four-time DPOY anchor of the Wolves defense."),
        ("Mike Conley", "G", "10", "6-1", 175, 37, "USA", "Ohio State", 11.4, 3.0, 5.6, 1.0, 0.2, 44.0, 41.0, "Veteran floor general who steadies late-game offense."),
        ("Naz Reid", "C-F", "11", "6-9", 264, 25, "USA", "LSU", 14.6, 5.4, 1.7, 0.9, 1.0, 49.7, 41.4, "Sixth Man stretch big who scores at all three levels."),
        ("Jaden McDaniels", "F", "3", "6-9", 200, 24, "USA", "Washington", 10.6, 5.3, 2.0, 1.4, 1.4, 49.0, 33.7, "Long perimeter defender with switchability across one through four."),
        ("Nickeil Alexander-Walker", "G", "9", "6-5", 205, 26, "Canada", "Virginia Tech", 8.2, 2.0, 2.0, 1.1, 0.5, 44.1, 39.0, "Plus on-ball defender and reliable corner shooter."),
    ],
    "thunder": [
        ("Jalen Williams", "F", "8", "6-6", 211, 23, "USA", "Santa Clara", 19.0, 4.0, 4.5, 1.4, 0.6, 53.5, 39.0, "All-around wing who creates and defends multiple positions."),
        ("Lu Dort", "G-F", "5", "6-4", 222, 25, "Canada", "Arizona State", 10.6, 4.5, 1.7, 0.9, 0.4, 41.6, 39.4, "Physical point-of-attack stopper with corner-three confidence."),
        ("Isaiah Hartenstein", "C", "55", "7-0", 250, 26, "USA", "International", 11.2, 10.5, 3.7, 1.1, 1.2, 58.0, 0.0, "Offensive-rebounding big who tightens the OKC interior."),
        ("Cason Wallace", "G", "22", "6-4", 195, 21, "USA", "Kentucky", 8.4, 2.7, 1.7, 1.8, 0.3, 47.0, 41.7, "Defensive-minded combo guard with growing offensive role."),
        ("Aaron Wiggins", "G-F", "21", "6-6", 200, 26, "USA", "Maryland", 12.0, 4.6, 1.9, 0.8, 0.4, 49.0, 38.0, "Two-way wing who scores in transition."),
        ("Alex Caruso", "G", "9", "6-5", 186, 30, "USA", "Texas A&M", 8.0, 3.4, 2.7, 1.7, 0.7, 45.5, 40.0, "All-Defense guard who lifts winning lineups."),
    ],
    "suns": [
        ("Bradley Beal", "G", "3", "6-4", 207, 31, "USA", "Florida", 17.6, 4.3, 4.7, 0.9, 0.3, 50.5, 43.0, "Three-level scoring guard sharing creation duties."),
        ("Tyus Jones", "G", "21", "6-0", 196, 28, "USA", "Duke", 12.5, 2.7, 7.3, 0.8, 0.1, 48.9, 41.4, "High-assist, low-turnover point guard."),
        ("Royce O'Neale", "F", "00", "6-4", 226, 31, "USA", "Baylor", 7.5, 3.9, 3.0, 1.0, 0.4, 41.0, 37.0, "Veteran 3-and-D wing with playmaking touch."),
        ("Grayson Allen", "G", "8", "6-4", 198, 29, "USA", "Duke", 13.5, 3.9, 3.0, 0.8, 0.2, 49.9, 46.1, "Spacer who connects pick-and-roll actions with the corners."),
        ("Mason Plumlee", "C", "22", "7-0", 254, 34, "USA", "Duke", 7.0, 6.7, 2.7, 0.6, 0.6, 65.0, 0.0, "Energy big who finishes and short-roll passes."),
        ("Jusuf Nurkic", "C", "20", "7-0", 290, 30, "Bosnia and Herzegovina", "International", 10.5, 9.0, 3.0, 0.8, 0.9, 52.0, 32.0, "Bruising center with elite passing for the position."),
    ],
    "lakers": [
        ("D'Angelo Russell", "G", "1", "6-4", 193, 28, "USA", "Ohio State", 17.0, 3.1, 6.4, 0.9, 0.4, 45.6, 41.5, "Shooting guard with deep pull-up range."),
        ("Austin Reaves", "G", "15", "6-5", 197, 26, "USA", "Oklahoma", 18.5, 4.4, 5.5, 0.8, 0.3, 48.6, 36.7, "Crafty combo guard who can lead an offense."),
        ("Rui Hachimura", "F", "28", "6-8", 230, 26, "Japan", "Gonzaga", 13.5, 5.0, 1.4, 0.5, 0.3, 53.0, 42.0, "Reliable mid-range forward and timely scorer."),
        ("Jaxson Hayes", "C", "11", "7-0", 220, 24, "USA", "Texas", 5.9, 4.4, 0.5, 0.5, 0.9, 73.0, 0.0, "Athletic backup center who finishes lobs."),
        ("Gabe Vincent", "G", "7", "6-2", 193, 28, "USA", "UC Santa Barbara", 5.5, 1.5, 1.7, 0.6, 0.1, 39.0, 31.8, "Veteran combo guard with playoff experience."),
        ("Max Christie", "G-F", "10", "6-6", 190, 21, "USA", "Michigan State", 6.0, 2.5, 1.0, 0.4, 0.3, 44.0, 41.0, "Long wing developing 3-and-D profile."),
    ],
    "clippers": [
        ("James Harden", "G", "1", "6-5", 220, 35, "USA", "Arizona State", 21.0, 5.0, 8.5, 1.0, 0.7, 42.8, 37.6, "Iso-and-stepback maestro running the Clippers offense."),
        ("Norman Powell", "G-F", "24", "6-3", 215, 31, "USA", "UCLA", 21.0, 3.0, 2.0, 1.1, 0.3, 49.0, 42.0, "Three-level scoring wing playing the best ball of his career."),
        ("Ivica Zubac", "C", "40", "7-0", 240, 27, "Croatia", "International", 16.7, 12.6, 2.5, 0.6, 1.1, 63.0, 0.0, "Drop-coverage center crashing the offensive glass."),
        ("Terance Mann", "G-F", "14", "6-5", 215, 28, "USA", "Florida State", 8.0, 3.7, 2.2, 0.7, 0.4, 49.0, 36.5, "Versatile connector wing who guards bigger forwards."),
        ("Nicolas Batum", "F", "33", "6-8", 230, 36, "France", "International", 4.6, 2.8, 1.9, 0.7, 0.6, 41.0, 39.0, "Veteran corner shooter with smart help defense."),
        ("Kris Dunn", "G", "8", "6-4", 205, 30, "USA", "Providence", 6.4, 2.7, 3.0, 1.3, 0.4, 44.0, 32.0, "On-ball defender who pressures lead guards."),
    ],
    "warriors": [
        ("Andrew Wiggins", "F", "22", "6-7", 197, 29, "Canada", "Kansas", 17.0, 4.5, 1.8, 0.7, 0.7, 45.2, 35.9, "Athletic wing with playoff-tested two-way game."),
        ("Jonathan Kuminga", "F", "00", "6-7", 225, 22, "DR Congo", "G League Ignite", 16.5, 4.8, 2.2, 0.7, 0.5, 52.9, 32.1, "Explosive young forward who attacks the rim."),
        ("Brandin Podziemski", "G", "2", "6-4", 205, 21, "USA", "Santa Clara", 11.7, 5.8, 3.7, 0.8, 0.3, 45.4, 38.5, "Rookie guard with mature offensive feel."),
        ("Buddy Hield", "G", "7", "6-4", 220, 32, "Bahamas", "Oklahoma", 12.0, 2.8, 2.1, 0.6, 0.2, 43.4, 38.5, "Career sharpshooter feasting on movement looks."),
        ("Gary Payton II", "G", "8", "6-2", 195, 32, "USA", "Oregon State", 5.5, 2.9, 1.7, 1.0, 0.5, 56.0, 36.0, "Defensive specialist guard who pressures the ball."),
        ("Trayce Jackson-Davis", "C", "32", "6-9", 240, 25, "USA", "Indiana", 7.0, 5.0, 2.4, 0.5, 1.1, 70.0, 0.0, "Lob threat and rim protector off the bench."),
    ],
    "kings": [
        ("De'Aaron Fox", "G", "5", "6-3", 185, 27, "USA", "Kentucky", 26.5, 4.6, 6.1, 2.0, 0.4, 46.5, 36.9, "Lightning quick lead guard who pressures the rim."),
        ("Domantas Sabonis", "C-F", "10", "6-11", 240, 28, "Lithuania", "Gonzaga", 19.2, 13.7, 8.1, 0.7, 0.4, 60.5, 41.7, "Triple-double machine and elbow-passing hub."),
        ("DeMar DeRozan", "F", "10", "6-6", 220, 35, "USA", "USC", 23.5, 4.0, 4.5, 1.1, 0.4, 47.7, 32.8, "Midrange master providing veteran shot creation."),
        ("Keegan Murray", "F", "13", "6-8", 225, 24, "USA", "Iowa", 13.4, 6.4, 1.8, 0.9, 0.7, 45.5, 36.3, "Stretch four with switchable defensive size."),
        ("Malik Monk", "G", "0", "6-3", 200, 27, "USA", "Kentucky", 15.0, 3.0, 5.6, 1.0, 0.5, 44.7, 35.0, "Sixth Man finalist who scores in bunches."),
        ("Trey Lyles", "F", "41", "6-9", 234, 29, "Canada", "Kentucky", 6.5, 4.4, 1.4, 0.5, 0.4, 47.5, 36.8, "Stretch big who switches across screens."),
    ],
    "pelicans": [
        ("Zion Williamson", "F", "1", "6-6", 284, 24, "USA", "Duke", 22.9, 5.8, 5.0, 1.1, 0.5, 56.8, 33.3, "Bullish forward who breaks paint with downhill drives."),
        ("Brandon Ingram", "F", "14", "6-8", 190, 27, "USA", "Duke", 21.0, 5.0, 5.0, 0.7, 0.6, 47.0, 36.0, "Long wing scorer who balances midrange and threes."),
        ("CJ McCollum", "G", "3", "6-3", 195, 33, "USA", "Lehigh", 18.0, 4.4, 4.8, 0.9, 0.3, 44.0, 39.6, "Pull-up shooting guard with playoff scoring chops."),
        ("Herbert Jones", "F", "5", "6-7", 206, 26, "USA", "Alabama", 11.0, 3.6, 2.6, 1.5, 0.7, 47.0, 38.0, "All-Defense wing who guards every position."),
        ("Trey Murphy III", "F", "25", "6-9", 206, 24, "USA", "Virginia", 14.8, 5.0, 1.7, 1.0, 0.6, 48.0, 38.3, "Long perimeter shooter with vertical pop."),
        ("Jose Alvarado", "G", "15", "6-0", 179, 26, "Puerto Rico", "Georgia Tech", 8.0, 1.9, 3.3, 1.5, 0.1, 41.0, 35.0, "Pesky on-ball defender who creates turnovers."),
    ],
    "spurs": [
        ("Devin Vassell", "G-F", "24", "6-5", 205, 24, "USA", "Florida State", 16.5, 3.7, 4.1, 1.1, 0.4, 41.5, 36.8, "Smooth wing scorer with three-level shot diet."),
        ("Keldon Johnson", "F", "3", "6-5", 220, 25, "USA", "Kentucky", 16.0, 5.8, 2.4, 0.7, 0.3, 47.0, 35.6, "Energy wing who attacks the offensive glass."),
        ("Chris Paul", "G", "3", "6-0", 175, 39, "USA", "Wake Forest", 9.4, 3.6, 7.5, 1.4, 0.1, 43.0, 36.8, "Hall-of-Fame floor general mentoring the young core."),
        ("Stephon Castle", "G", "5", "6-6", 215, 20, "USA", "Connecticut", 13.5, 3.4, 4.0, 0.9, 0.3, 42.0, 30.0, "Rookie combo guard with point-of-attack defensive tools."),
        ("Jeremy Sochan", "F", "10", "6-9", 230, 21, "Poland", "Baylor", 11.4, 6.4, 2.7, 0.7, 0.4, 47.0, 32.5, "Versatile defensive forward with developing offense."),
        ("Harrison Barnes", "F", "40", "6-8", 225, 32, "USA", "North Carolina", 12.0, 4.0, 1.6, 0.7, 0.3, 48.0, 39.0, "Veteran spacer playing winning corner-three basketball."),
    ],
    "grizzlies": [
        ("Desmond Bane", "G", "22", "6-5", 215, 26, "USA", "TCU", 23.0, 5.0, 5.5, 1.0, 0.4, 46.5, 39.0, "Three-level shot creator and tough closeout attacker."),
        ("Jaren Jackson Jr.", "F-C", "13", "7-0", 242, 25, "USA", "Michigan State", 22.5, 5.5, 2.3, 1.2, 1.7, 47.0, 32.8, "Defensive Player anchor with stretch range."),
        ("Marcus Smart", "G", "36", "6-4", 220, 30, "USA", "Oklahoma State", 14.5, 2.7, 4.4, 1.5, 0.3, 42.7, 33.0, "Hard-nosed point-of-attack defender."),
        ("Luke Kennard", "G", "10", "6-5", 206, 28, "USA", "Duke", 8.5, 2.0, 2.0, 0.4, 0.1, 45.0, 43.4, "Elite catch-and-shoot specialist."),
        ("Brandon Clarke", "F-C", "15", "6-8", 215, 28, "Canada", "Gonzaga", 9.5, 5.5, 1.1, 0.5, 1.1, 65.0, 33.0, "Bouncy forward with high finishing percentages."),
        ("Santi Aldama", "F", "7", "6-11", 224, 24, "Spain", "Loyola Maryland", 12.0, 6.2, 2.5, 0.7, 0.8, 47.0, 35.0, "Skilled big who shoots and passes."),
    ],
    "rockets": [
        ("Alperen Sengun", "C", "28", "6-11", 243, 22, "Turkey", "International", 21.0, 9.3, 5.0, 1.1, 0.8, 53.7, 30.5, "Elbow playmaking center with elite touch."),
        ("Jalen Green", "G", "4", "6-6", 186, 23, "USA", "G League Ignite", 19.6, 4.4, 3.2, 0.9, 0.3, 42.3, 35.0, "Athletic scoring guard with explosive transition."),
        ("Fred VanVleet", "G", "5", "6-1", 197, 30, "USA", "Wichita State", 14.0, 3.7, 8.3, 1.5, 0.5, 41.4, 34.5, "Defensive-minded floor general and pull-up shooter."),
        ("Jabari Smith Jr.", "F", "10", "6-11", 220, 21, "USA", "Auburn", 13.5, 8.0, 1.4, 0.7, 1.0, 45.0, 36.3, "Stretch forward with rim-protection upside."),
        ("Dillon Brooks", "F", "9", "6-7", 225, 28, "Canada", "Oregon", 14.0, 3.4, 1.5, 0.9, 0.4, 45.0, 39.5, "Combative wing who chases best opposing scorers."),
        ("Amen Thompson", "G-F", "1", "6-7", 199, 22, "USA", "Overtime Elite", 13.5, 8.0, 3.8, 1.4, 1.2, 55.6, 28.0, "Hyper-athletic point-forward with defensive playmaking."),
    ],
    "raptors": [
        ("Scottie Barnes", "F", "4", "6-7", 225, 23, "USA", "Florida State", 20.0, 8.0, 6.0, 1.4, 1.4, 47.0, 34.5, "All-around forward with growing shooting profile."),
        ("RJ Barrett", "G-F", "9", "6-6", 214, 24, "Canada", "Duke", 21.5, 6.0, 5.4, 0.8, 0.4, 44.5, 36.0, "Downhill scoring wing acclimated to Toronto."),
        ("Immanuel Quickley", "G", "5", "6-3", 190, 25, "USA", "Kentucky", 17.5, 4.0, 6.5, 0.8, 0.4, 43.6, 38.5, "Sixth Man finalist who runs pick-and-roll."),
        ("Jakob Poeltl", "C", "19", "7-1", 245, 29, "Austria", "Utah", 12.0, 9.5, 2.6, 0.7, 1.4, 64.0, 0.0, "Drop-coverage anchor with elite rim deterrence."),
        ("Gradey Dick", "G", "1", "6-7", 205, 21, "USA", "Kansas", 14.0, 4.0, 2.5, 0.8, 0.3, 45.5, 38.0, "Sharpshooting wing with off-ball relocation."),
        ("Ochai Agbaji", "G-F", "30", "6-5", 217, 24, "USA", "Kansas", 9.0, 2.6, 1.4, 0.7, 0.4, 44.0, 37.5, "Two-way wing with corner shooting."),
    ],
    "nets": [
        ("Cam Thomas", "G", "24", "6-3", 210, 23, "USA", "LSU", 22.5, 3.0, 3.5, 0.8, 0.2, 43.0, 36.0, "Shot-making guard who scores in volume."),
        ("Nic Claxton", "C", "33", "6-11", 215, 25, "USA", "Georgia", 11.0, 9.5, 2.0, 0.6, 2.0, 65.5, 0.0, "Rim-running center who switches across screens."),
        ("Cameron Johnson", "F", "2", "6-8", 210, 28, "USA", "North Carolina", 14.5, 4.0, 2.8, 0.9, 0.3, 45.5, 40.5, "Tall sharpshooting wing with closeout attack."),
        ("Dorian Finney-Smith", "F", "28", "6-7", 220, 31, "USA", "Florida", 8.0, 4.0, 1.3, 0.8, 0.5, 45.0, 39.0, "Three-and-D wing who guards multiple positions."),
        ("Dennis Schroder", "G", "17", "6-1", 172, 31, "Germany", "International", 13.0, 2.5, 6.0, 0.8, 0.2, 42.5, 34.0, "Veteran ball-handler running both units."),
        ("Day'Ron Sharpe", "C", "20", "6-9", 265, 23, "USA", "North Carolina", 8.5, 7.5, 1.5, 0.6, 0.7, 56.0, 0.0, "Rebounding big off the bench."),
    ],
    "hornets": [
        ("LaMelo Ball", "G", "1", "6-7", 180, 23, "USA", "Australia", 23.9, 5.1, 8.0, 1.8, 0.3, 43.0, 37.5, "Magnetic point guard with deep pull-up range."),
        ("Brandon Miller", "G-F", "24", "6-9", 200, 22, "USA", "Alabama", 21.0, 4.8, 3.5, 0.9, 0.7, 44.0, 37.3, "Skilled scoring wing with three-level shot diet."),
        ("Mark Williams", "C", "5", "7-0", 240, 23, "USA", "Duke", 12.7, 9.5, 1.4, 0.4, 1.2, 62.0, 0.0, "Long lob threat and rim protector."),
        ("Miles Bridges", "F", "0", "6-7", 225, 26, "USA", "Michigan State", 20.0, 7.0, 3.0, 1.0, 0.7, 46.5, 34.0, "Athletic wing scorer with rebounding chops."),
        ("Tre Mann", "G", "23", "6-4", 184, 23, "USA", "Florida", 11.5, 2.5, 4.0, 0.7, 0.2, 42.5, 35.5, "Combo guard with pull-up shooting range."),
        ("Tidjane Salaun", "F", "21", "6-9", 212, 19, "France", "International", 6.0, 3.5, 1.0, 0.7, 0.5, 39.0, 31.0, "Long wing rookie with shot-blocking flashes."),
    ],
    "pistons": [
        ("Cade Cunningham", "G", "2", "6-6", 220, 23, "USA", "Oklahoma State", 22.7, 4.3, 7.5, 0.9, 0.6, 45.5, 35.5, "Jumbo point guard who runs the Pistons offense."),
        ("Jaden Ivey", "G", "23", "6-4", 200, 23, "USA", "Purdue", 17.6, 4.0, 4.0, 0.8, 0.5, 45.5, 37.0, "Explosive guard with downhill driving force."),
        ("Jalen Duren", "C", "0", "6-10", 250, 21, "USA", "Memphis", 11.5, 11.5, 2.0, 0.8, 1.0, 64.0, 0.0, "Athletic rebounding center with screen-set craft."),
        ("Ausar Thompson", "F", "9", "6-7", 215, 22, "USA", "Overtime Elite", 11.5, 6.5, 2.5, 1.3, 1.2, 49.0, 28.0, "Defensive-minded two-way wing."),
        ("Tobias Harris", "F", "12", "6-8", 226, 32, "USA", "Tennessee", 13.0, 5.5, 2.4, 0.6, 0.6, 48.0, 35.0, "Veteran scoring forward providing wing depth."),
        ("Malik Beasley", "G", "5", "6-4", 187, 28, "USA", "Florida State", 15.5, 3.0, 1.6, 0.7, 0.2, 43.0, 41.0, "Catch-and-shoot specialist with off-ball gravity."),
    ],
    "trail_blazers": [
        ("Scoot Henderson", "G", "00", "6-2", 195, 21, "USA", "G League Ignite", 14.0, 3.0, 5.0, 0.8, 0.3, 41.0, 33.0, "Explosive young point guard with downhill burst."),
        ("Shaedon Sharpe", "G-F", "17", "6-6", 200, 21, "Canada", "Kentucky", 18.5, 5.0, 2.5, 0.7, 0.6, 45.0, 34.5, "Highlight-reel wing scorer with athletic upside."),
        ("Anfernee Simons", "G", "1", "6-3", 180, 25, "USA", "IMG Academy", 19.0, 3.0, 4.5, 0.7, 0.3, 42.5, 36.0, "Lead guard with deep pull-up range."),
        ("Deni Avdija", "F", "8", "6-9", 240, 24, "Israel", "International", 15.5, 7.0, 4.0, 0.9, 0.4, 47.0, 35.5, "Point-forward with rebounding and passing chops."),
        ("Donovan Clingan", "C", "23", "7-2", 280, 21, "USA", "Connecticut", 11.5, 9.5, 2.0, 0.5, 2.0, 56.0, 0.0, "Massive rookie rim protector and lob threat."),
        ("Toumani Camara", "F", "33", "6-7", 220, 25, "Belgium", "Dayton", 11.5, 5.5, 2.0, 1.0, 0.6, 45.0, 35.0, "Versatile defensive wing who plays multiple spots."),
    ],
    "jazz": [
        ("Lauri Markkanen", "F", "23", "7-0", 240, 27, "Finland", "Arizona", 21.0, 7.5, 1.7, 0.6, 0.5, 48.0, 38.0, "All-Star stretch four with three-level scoring."),
        ("Collin Sexton", "G", "2", "6-1", 190, 26, "USA", "Alabama", 19.5, 2.7, 4.0, 1.0, 0.1, 48.0, 39.0, "Downhill scoring guard with paint pressure."),
        ("Walker Kessler", "C", "24", "7-1", 245, 23, "USA", "Auburn", 10.0, 9.0, 1.0, 0.4, 2.4, 66.0, 0.0, "Elite shot-blocking center protecting the paint."),
        ("Keyonte George", "G", "3", "6-4", 206, 21, "USA", "Baylor", 16.5, 3.0, 5.0, 0.8, 0.2, 39.5, 34.0, "Young combo guard developing as primary creator."),
        ("John Collins", "F-C", "20", "6-9", 226, 27, "USA", "Wake Forest", 18.0, 8.5, 2.0, 0.5, 1.0, 53.0, 38.0, "Vertical spacer and lob threat."),
        ("Cody Williams", "F", "5", "6-7", 190, 19, "USA", "Colorado", 6.5, 2.5, 1.4, 0.5, 0.4, 41.0, 31.0, "Long rookie wing with two-way flashes."),
    ],
    "wizards": [
        ("Jordan Poole", "G", "13", "6-4", 194, 25, "USA", "Michigan", 19.0, 3.0, 4.5, 0.8, 0.3, 41.5, 35.0, "Shooting guard with pull-up range and bench scoring."),
        ("Kyle Kuzma", "F", "33", "6-9", 221, 29, "USA", "Utah", 18.0, 6.5, 4.5, 0.7, 0.5, 45.0, 31.0, "Veteran scoring forward providing leadership."),
        ("Bilal Coulibaly", "F", "0", "6-8", 230, 20, "France", "International", 12.0, 5.0, 3.0, 1.1, 0.8, 45.5, 35.0, "Long-armed wing with two-way defensive upside."),
        ("Alex Sarr", "C-F", "20", "7-1", 224, 19, "France", "International", 9.5, 5.0, 1.5, 0.7, 1.6, 41.0, 30.0, "No. 2 overall rookie big developing as rim protector."),
        ("Corey Kispert", "F", "24", "6-7", 224, 26, "USA", "Gonzaga", 13.5, 3.0, 2.0, 0.5, 0.2, 47.0, 39.0, "Catch-and-shoot wing punishing closeouts."),
        ("Bub Carrington", "G", "8", "6-5", 190, 19, "USA", "Pittsburgh", 9.0, 3.5, 4.5, 0.7, 0.3, 39.0, 34.0, "Rookie combo guard with passing feel."),
    ],
}


# EXTRA_ARTICLES — supplemental newsroom items rotated across categories.
EXTRA_ARTICLES = [
    ("Power Rankings: Contenders sort themselves after deadline", "Top Stories", "celtics", "jayson-tatum", "articles/harris-levert-051426-scaled.jpg"),
    ("Power Rankings: West playoff race heats up to the wire", "Top Stories", "thunder", "shai-gilgeous-alexander", "articles/edwards-spurs-gm5-051426-scaled.jpg"),
    ("Power Rankings: East middle tier reshuffles after All-Star", "Top Stories", "magic", "paolo-banchero", "articles/brunson-iso-051426-scaled.jpg"),
    ("Power Rankings: Spurs surge into national TV slots", "Top Stories", "spurs", "victor-wembanyama", "articles/wembanyama-gm5.jpg"),
    ("In-season tournament returns with revamped bracket", "Top Stories", "lakers", "lebron-james", "articles/okc-lal-recap.jpg"),
    ("All-Star reserves announced ahead of weekend in San Francisco", "Top Stories", "celtics", "jaylen-brown", "articles/harden-game5.jpg"),
    ("League announces new schedule format for 2026-27 season", "Top Stories", "warriors", "stephen-curry", "articles/nba-official-finals-logo.png"),
    ("Coach of the Year ladder shakes up with five games left", "Top Stories", "thunder", "shai-gilgeous-alexander", "articles/nba-official-chasing-thunder.jpeg"),
    ("Sixth Man race tightens between Naz Reid and Malik Monk", "Top Stories", "timberwolves", "naz-reid", "articles/nba-official-fantasy-spurs.jpg"),
    ("Trade deadline grades: best moves across both conferences", "Top Stories", "mavericks", "luka-doncic", "articles/morey.jpg"),

    ("Mock draft 4.0: post-combine board moves on prospects", "Draft", "wizards", "", "articles/peterson-dybantsa.jpg"),
    ("AJ Dybantsa breaks down film with NBA scouts", "Draft", "wizards", "", "articles/draft-combine-2026.jpg"),
    ("International watch: stash candidates rising up boards", "Draft", "spurs", "", "articles/combine-knueppel.jpg"),
    ("Combine measurements: full wingspan and standing reach data", "Draft", "raptors", "", "articles/nba-official-draft-combine-hero.jpg"),
    ("Draft history quiz: name every No. 1 overall pick since 2000", "Draft", "lakers", "", "articles/lebron-stern-draft-night.jpg"),
    ("Two-round mock: lottery scenarios across all 14 teams", "Draft", "hornets", "", "articles/nba-official-draft-banner.png"),
    ("Lottery odds explained: what each team is rooting for", "Draft", "pistons", "cade-cunningham", "articles/nba-official-draft-lottery.jpg"),
    ("Top 20 prospect rankings update after college season", "Draft", "wizards", "", "articles/nba-official-draft-logo.png"),

    ("Playoffs preview: Cavaliers-Knicks Eastern Conference Finals", "Playoffs", "cavaliers", "donovan-mitchell", "articles/nba-official-knicks-cavs.jpg"),
    ("Playoffs preview: Thunder-Spurs Western Conference Finals", "Playoffs", "thunder", "shai-gilgeous-alexander", "articles/nba-official-spurs-thunder.jpg"),
    ("Playoffs film: how the Knicks defend the pick-and-roll", "Playoffs", "knicks", "jalen-brunson", "articles/nba-official-cavs-game7.jpg"),
    ("Playoffs film: Cavaliers half-court actions break the paint", "Playoffs", "cavaliers", "evan-mobley", "articles/cle-det-recap.jpg"),
    ("Playoffs leaders: top scorers through the second round", "Playoffs", "thunder", "shai-gilgeous-alexander", "articles/nba-official-chasing-thunder.jpeg"),
    ("Conference Finals schedule: every game, every time slot", "Playoffs", "thunder", "", "articles/nba-official-playoffs-banner.png"),
    ("Playoff villains: which heel role players are stealing the show", "Playoffs", "heat", "jimmy-butler", "articles/harden-game5.jpg"),
    ("Game 7 history: every road team to win a winner-take-all", "Playoffs", "cavaliers", "donovan-mitchell", "articles/pistons-cavs-game6.jpg"),

    ("MVP ladder: Jokic, Gilgeous-Alexander remain at the top", "Awards", "nuggets", "nikola-jokic", "articles/wizards-no1.jpg"),
    ("DPOY race: Wembanyama vs. Bam Adebayo down the stretch", "Awards", "spurs", "victor-wembanyama", "articles/wembanyama-gm5.jpg"),
    ("Rookie of the Year shifts after late-season Risacher surge", "Awards", "hawks", "zaccharie-risacher", "articles/nba-official-castle.jpg"),
    ("Most Improved Player: five candidates with strong cases", "Awards", "magic", "franz-wagner", "articles/nba-official-chasing-spurs.png"),
    ("All-NBA First Team predictions and final tracking", "Awards", "celtics", "jayson-tatum", "articles/cavs-playoffs.jpg"),
    ("Clutch Player of the Year: regular season closing numbers", "Awards", "knicks", "jalen-brunson", "articles/brunson-iso-051426-scaled.jpg"),

    ("Transactions tracker: buyout market kicks off after deadline", "Transactions", "lakers", "lebron-james", "articles/morey.jpg"),
    ("Transactions tracker: ten-day contract signings across the league", "Transactions", "rockets", "", "articles/ian-eagle-noah-eagle.jpg"),
    ("Transactions tracker: hardship exceptions for injury-hit teams", "Transactions", "grizzlies", "ja-morant", "articles/morey.jpg"),
    ("Transactions tracker: two-way conversions before postseason", "Transactions", "warriors", "stephen-curry", "articles/nba-official-fantasy-rookies.jpg"),
    ("Transactions tracker: contender adds wing depth via trade", "Transactions", "celtics", "jrue-holiday", "articles/og-anunoby.jpg"),

    ("History: every team to come back from a 3-1 deficit", "History", "warriors", "stephen-curry", "articles/lebron-stern-draft-night.jpg"),
    ("History: best playoff buzzer-beaters of the last decade", "History", "lakers", "lebron-james", "articles/collins-obituary.png"),
    ("History: top 10 most legendary triple-doubles in playoff history", "History", "nuggets", "nikola-jokic", "articles/nba-official-finals-logo.png"),
    ("History: revisiting the 2016 Finals comeback game-by-game", "History", "cavaliers", "lebron-james", "articles/lebron-stern-draft-night.jpg"),
    ("History: how the three-point line transformed offense", "History", "warriors", "stephen-curry", "articles/nba-official-fantasy-power.jpg"),

    ("Around the NBA: bench mobs that are turning games around", "Around the NBA", "kings", "malik-monk", "articles/peterson-dybantsa.jpg"),
    ("Around the NBA: small-market storylines worth following", "Around the NBA", "thunder", "shai-gilgeous-alexander", "articles/nba-official-chasing-thunder.jpeg"),
    ("Around the NBA: rookie wall watch heading into spring", "Around the NBA", "spurs", "stephon-castle", "articles/nba-official-castle.jpg"),
    ("Around the NBA: load management decisions across contenders", "Around the NBA", "clippers", "kawhi-leonard", "articles/draft-combine-2026.jpg"),
    ("Around the NBA: international scouting trip from Belgrade", "Around the NBA", "magic", "franz-wagner", "articles/nba-official-draft-video-1.jpg"),

    ("Preview: Lakers vs. Warriors with playoff seeding on the line", "Preview", "lakers", "lebron-james", "articles/okc-lal-recap.jpg"),
    ("Preview: Celtics-Knicks rivalry game with East implications", "Preview", "celtics", "jayson-tatum", "articles/harris-levert-051426-scaled.jpg"),
    ("Preview: Thunder host Nuggets in possible playoff matchup", "Preview", "thunder", "shai-gilgeous-alexander", "articles/nba-official-spurs-thunder.jpg"),
    ("Preview: Heat-Bucks pace clash heading into national TV", "Preview", "heat", "bam-adebayo", "articles/harden-game5.jpg"),

    ("Analysis: how Wembanyama is bending offensive shot charts", "Analysis", "spurs", "victor-wembanyama", "articles/wembanyama-gm5.jpg"),
    ("Analysis: Jokic's elbow passing creates record-setting assists", "Analysis", "nuggets", "nikola-jokic", "articles/nba-official-chasing-cavs.png"),
    ("Analysis: how Cleveland's defense forces opponents off the line", "Analysis", "cavaliers", "evan-mobley", "articles/cle-det-recap.jpg"),
    ("Analysis: the Wolves switching scheme that powers their defense", "Analysis", "timberwolves", "jaden-mcdaniels", "articles/edwards-game5-051426-scaled.jpg"),

    ("Features: a day in the life of Anthony Edwards", "Features", "timberwolves", "anthony-edwards", "articles/edwards-game5-051426-scaled.jpg"),
    ("Features: the rebuild blueprint paying off in Oklahoma City", "Features", "thunder", "chet-holmgren", "articles/nba-official-chasing-thunder.jpeg"),
    ("Features: how Spurs are integrating Castle alongside Wembanyama", "Features", "spurs", "stephon-castle", "articles/nba-official-castle.jpg"),
    ("Features: Pistons' Cade Cunningham finally healthy and unleashed", "Features", "pistons", "cade-cunningham", "articles/nba-official-cade-duren.jpg"),

    ("Video: top 10 plays from the second round", "Video", "thunder", "shai-gilgeous-alexander", "articles/johnson-iso-051426-scaled.jpg"),
    ("Video: every Wembanyama block from the Game 5 win", "Video", "spurs", "victor-wembanyama", "articles/wembanyama-gm5.jpg"),
    ("Video: Cade Cunningham and Jalen Duren two-man game breakdown", "Video", "pistons", "cade-cunningham", "articles/nba-official-cade-duren.jpg"),
    ("Highlights: Knicks bounce back in pivotal Game 4", "Highlights", "knicks", "jalen-brunson", "articles/brunson-iso-051426-scaled.jpg"),
    ("Highlights: Indiana's transition offense torches Milwaukee", "Highlights", "pacers", "tyrese-haliburton", "articles/harden-game5.jpg"),
    ("Highlights: every made three from a 22-three barrage", "Highlights", "celtics", "payton-pritchard", "articles/nba-official-fantasy-power.jpg"),
]


# EXTRA_PRODUCTS — adds team-by-team merch and accessories.
EXTRA_PRODUCTS = [
    ("Atlanta Hawks Statement Edition Jersey", "Jerseys", "hawks", 109.99, 129.99, "Red", "hawks.svg", ["Nike Dri-FIT fabric", "Heat-applied name and number", "Statement Edition trim"]),
    ("Chicago Bulls Icon Edition Jersey", "Jerseys", "bulls", 109.99, 129.99, "Red", "bulls.svg", ["Nike Dri-FIT fabric", "Iconic team striping", "Tagless interior"]),
    ("Cleveland Cavaliers Association Jersey", "Jerseys", "cavaliers", 109.99, 129.99, "White", "cavaliers.svg", ["Lightweight mesh", "Heat transfer name", "Official sideline cut"]),
    ("Detroit Pistons Hardwood Classics Jersey", "Jerseys", "pistons", 119.99, 139.99, "Red", "pistons.svg", ["Throwback graphics", "Mesh body", "Official team detailing"]),
    ("Brooklyn Nets City Edition Jersey", "Jerseys", "nets", 119.99, 134.99, "Black", "nets.svg", ["Mesh build", "City Edition colorways", "Reflective trim"]),
    ("Toronto Raptors Statement Jersey", "Jerseys", "raptors", 109.99, 129.99, "Red", "raptors.svg", ["Lightweight knit", "Embroidered team mark", "Athletic fit"]),
    ("Charlotte Hornets Icon Edition Jersey", "Jerseys", "hornets", 99.99, 119.99, "Teal", "hornets.svg", ["Two-tone body", "Heat-applied numbers", "Sideline cut"]),
    ("Houston Rockets Statement Edition Jersey", "Jerseys", "rockets", 109.99, 129.99, "Red", "rockets.svg", ["Lightweight mesh", "Embroidered Houston wordmark", "Player-issued cut"]),
    ("Memphis Grizzlies Association Edition Jersey", "Jerseys", "grizzlies", 109.99, 129.99, "White", "grizzlies.svg", ["Lightweight knit", "Front and back number sets", "Tagless collar"]),
    ("New Orleans Pelicans Icon Edition Jersey", "Jerseys", "pelicans", 109.99, 129.99, "Navy", "pelicans.svg", ["Nike Dri-FIT", "Team color trim", "Official sideline cut"]),
    ("Portland Trail Blazers Statement Jersey", "Jerseys", "trail_blazers", 109.99, 129.99, "Red", "trail_blazers.svg", ["Lightweight mesh", "Heat transfer numbers", "Player-issued cut"]),
    ("Sacramento Kings Icon Edition Jersey", "Jerseys", "kings", 109.99, 129.99, "Purple", "kings.svg", ["Smooth knit body", "Embroidered crown", "Official sideline cut"]),
    ("Utah Jazz Association Edition Jersey", "Jerseys", "jazz", 109.99, 129.99, "White", "jazz.svg", ["Lightweight knit", "Heat transfer team mark", "Tagless interior"]),
    ("Washington Wizards Statement Edition Jersey", "Jerseys", "wizards", 109.99, 129.99, "Red", "wizards.svg", ["Lightweight mesh", "Embroidered team mark", "Authentic cut"]),

    ("Atlanta Hawks Performance Tee", "T-Shirts", "hawks", 34.99, 39.99, "Red", "hawks.svg", ["Cotton blend", "Screen print logo", "Athletic fit"]),
    ("Chicago Bulls Logo Hoodie", "Hoodies", "bulls", 79.99, 89.99, "Black", "bulls.svg", ["Midweight fleece", "Embroidered chest logo", "Drawstring hood"]),
    ("Detroit Pistons Snapback Cap", "Hats", "pistons", 31.99, 35.99, "Navy", "pistons.svg", ["Snapback closure", "Embroidered team mark", "Flat brim"]),
    ("Houston Rockets Cotton Tee", "T-Shirts", "rockets", 32.99, 37.99, "Red", "rockets.svg", ["Soft cotton", "Crew neck", "Screen print"]),
    ("Memphis Grizzlies Practice Shorts", "Shorts", "grizzlies", 49.99, 59.99, "Navy", "grizzlies.svg", ["Elastic waistband", "Side pockets", "Team color panels"]),
    ("Sacramento Kings Pullover Hoodie", "Hoodies", "kings", 74.99, 89.99, "Purple", "kings.svg", ["Heavyweight fleece", "Kangaroo pocket", "Embroidered crown"]),
    ("Toronto Raptors Track Jacket", "Outerwear", "raptors", 99.99, 119.99, "Red", "raptors.svg", ["Lightweight shell", "Full zip", "Ribbed cuffs"]),
    ("Utah Jazz City Edition Cap", "Hats", "jazz", 32.99, 36.99, "Black", "jazz.svg", ["Adjustable strap", "City Edition graphic", "Curved brim"]),
    ("Washington Wizards Long Sleeve Tee", "T-Shirts", "wizards", 39.99, 44.99, "Red", "wizards.svg", ["Soft jersey knit", "Ribbed cuffs", "Screen print"]),
    ("Portland Trail Blazers Crewneck Sweatshirt", "Hoodies", "trail_blazers", 64.99, 74.99, "Black", "trail_blazers.svg", ["French terry fabric", "Ribbed cuffs", "Front chest logo"]),

    ("NBA Authentic Spalding Game Basketball", "Accessories", "", 159.99, 179.99, "Brown", "league/nba-logo.svg", ["Indoor leather", "Official 29.5\" size", "Game-ready grip"]),
    ("NBA League Pass 12-Month Subscription", "Accessories", "", 99.99, 129.99, "Multi", "league/nba-logo.svg", ["All games live and on demand", "Multi-device access", "Includes condensed games"]),
    ("Brooklyn Nets Backpack", "Accessories", "nets", 54.99, 64.99, "Black", "nets.svg", ["Padded laptop sleeve", "Reinforced straps", "Embroidered team mark"]),
    ("Boston Celtics Replica Banner", "Accessories", "celtics", 39.99, 49.99, "Green", "celtics.svg", ["Two-sided print", "Hanging cord included", "Officially licensed"]),
    ("Denver Nuggets Throwback Hoodie", "Hoodies", "nuggets", 79.99, 94.99, "Navy", "nuggets.svg", ["Heavyweight fleece", "Throwback rainbow graphic", "Ribbed hem"]),
    ("New Orleans Pelicans Performance Tank", "T-Shirts", "pelicans", 32.99, 39.99, "Navy", "pelicans.svg", ["Moisture-wicking fabric", "Sleeveless cut", "Screen print team mark"]),
    ("Charlotte Hornets Travel Mug", "Accessories", "hornets", 22.99, 26.99, "Teal", "hornets.svg", ["Stainless steel", "Spill-resistant lid", "Wraparound team logo"]),
]


def _generate_regular_games(teams_by_slug, target_count=95):
    rng = _rand.Random(20260515)
    slugs = list(teams_by_slug.keys())
    out = []
    for i in range(target_count):
        home, away = rng.sample(slugs, 2)
        # Spread across the prior ~150 days (regular season window)
        offset_days = -1 * rng.randint(7, 175)
        hour = rng.choice([18, 19, 20, 21])
        home_score = rng.randint(95, 132)
        away_score = rng.randint(95, 132)
        if home_score == away_score:
            home_score += 1
        diff = home_score - away_score
        if diff > 0:
            recap = f"{teams_by_slug[home].full_name} held off {teams_by_slug[away].full_name} {home_score}-{away_score} at home."
        else:
            recap = f"{teams_by_slug[away].full_name} edged {teams_by_slug[home].full_name} {away_score}-{home_score} on the road."
        broadcast = rng.choice(["NBA TV", "ESPN", "TNT", "ABC", "League Pass", "Bally Sports"])
        out.append((home, away, offset_days, hour, 0, "Final", home_score, away_score,
                    teams_by_slug[home].arena, broadcast, recap, 0))
    return out


def seed_database():
    if Team.query.count() > 0:
        return

    teams_by_slug = {}
    for city, name, abbr, conf, div, wins, losses, home, road, streak, ppg, oppg, arena, coach, color, logo_slug in TEAM_SEED:
        team = Team(
            city=city, name=name, slug=slugify(name if name != "76ers" else "seventysixers"),
            abbreviation=abbr, conference=conf, division=div, wins=wins, losses=losses,
            home_record=home, road_record=road, streak=streak, ppg=ppg, oppg=oppg,
            arena=arena, coach=coach, color=color, logo=f"/static/images/teams/{logo_slug}.svg",
        )
        db.session.add(team)
        teams_by_slug[team.slug] = team
    db.session.flush()

    for name, team_slug, position, jersey, height, weight, age, country, college, ppg, rpg, apg, spg, bpg, fg, three, bio, image_slug in PLAYER_SEED:
        db.session.add(Player(
            team_id=teams_by_slug[team_slug].id, name=name, slug=slugify(name), position=position,
            jersey=jersey, height=height, weight=weight, age=age, country=country, college=college,
            ppg=ppg, rpg=rpg, apg=apg, spg=spg, bpg=bpg, fg_pct=fg, three_pct=three,
            bio=bio, image=f"/static/images/players/{image_slug}.png",
        ))

    # Append the broader roster — image falls back to team logo to avoid 404s.
    for team_slug, roster in EXTRA_ROSTERS.items():
        team = teams_by_slug.get(team_slug)
        if not team:
            continue
        for name, pos, jersey, h, w, age, country, college, ppg, rpg, apg, spg, bpg, fg, three, bio in roster:
            db.session.add(Player(
                team_id=team.id, name=name, slug=slugify(name), position=pos,
                jersey=jersey, height=h, weight=w, age=age, country=country, college=college,
                ppg=ppg, rpg=rpg, apg=apg, spg=spg, bpg=bpg, fg_pct=fg, three_pct=three,
                bio=bio, image=team.logo,
            ))

    games = [
        ("cavaliers", "pistons", 0, 7, 0, "Scheduled", None, None, "Rocket Arena", "Now TV", "East semifinal Game 6 with Cleveland leading 3-2."),
        ("timberwolves", "spurs", 0, 9, 30, "Scheduled", None, None, "Target Center", "Viu TV", "West semifinal Game 6 with San Antonio leading 3-2."),
        ("pistons", "cavaliers", 2, 0, 0, "Scheduled", None, None, "Little Caesars Arena", "League Pass", "Potential Game 7 in the Detroit-Cleveland series."),
        ("spurs", "timberwolves", 2, 0, 0, "Scheduled", None, None, "Frost Bank Center", "League Pass", "Potential Game 7 in the San Antonio-Minnesota series."),
        ("pacers", "bucks", 19, 8, 30, "Scheduled", None, None, "TBD", "League Pass", "Conference finals placeholder matchup."),
        ("clippers", "suns", 21, 8, 30, "Scheduled", None, None, "TBD", "League Pass", "Conference finals placeholder matchup."),
        ("cavaliers", "pistons", -2, 7, 0, "Final", 117, 113, "Rocket Arena", "TNT", "Cleveland made key plays late to take a 3-2 series lead."),
        ("timberwolves", "spurs", -1, 9, 30, "Final", 97, 126, "Target Center", "NBA TV", "San Antonio controlled the glass and pushed the series lead."),
        ("lakers", "warriors", -1, 8, 0, "Final", 112, 108, "Crypto.com Arena", "ABC", "Los Angeles leaned on late paint defense against Golden State."),
        ("mavericks", "thunder", 25, 8, 0, "Scheduled", None, None, "American Airlines Center", "TNT", "Two elite guard creators headline a West showdown."),
    ]
    for home_slug, away_slug, offset, hour, minute, status, home_score, away_score, arena, broadcast, recap in games:
        db.session.add(Game(
            home_team_id=teams_by_slug[home_slug].id, away_team_id=teams_by_slug[away_slug].id,
            game_date=MIRROR_REFERENCE_DATE.replace(hour=hour, minute=minute) + timedelta(days=offset),
            status=status, home_score=home_score, away_score=away_score, arena=arena,
            broadcast=broadcast, recap=recap, ticket_price=55 + offset * 4,
        ))

    # Generate ~95 regular-season Final games to make schedule, standings,
    # team_schedule and search pages feel populated.
    for home_slug, away_slug, offset, hour, minute, status, home_score, away_score, arena, broadcast, recap, ticket_price in _generate_regular_games(teams_by_slug):
        db.session.add(Game(
            home_team_id=teams_by_slug[home_slug].id, away_team_id=teams_by_slug[away_slug].id,
            game_date=MIRROR_REFERENCE_DATE.replace(hour=hour, minute=minute) + timedelta(days=offset),
            status=status, home_score=home_score, away_score=away_score, arena=arena,
            broadcast=broadcast, recap=recap, ticket_price=ticket_price,
        ))

    articles = [
        ("Celtics defense sets tone in latest home win", "Top Stories", "Boston's switching defense forced tough looks late.", "The Celtics leaned on perimeter pressure, balanced scoring and a deep bench to protect the lead at TD Garden.", "celtics", "jayson-tatum", "articles/harris-levert-051426-scaled.jpg"),
        ("Doncic and Thunder guards prepare for pace test", "Preview", "Dallas and Oklahoma City bring two of the league's most efficient creators.", "The matchup will hinge on transition defense, corner threes and late-clock shot quality.", "mavericks", "luka-doncic", "articles/edwards-spurs-gm5-051426-scaled.jpg"),
        ("Wembanyama's rim protection changes Spurs math", "Analysis", "San Antonio's rookie center is altering shot charts around the basket.", "Opponents are taking fewer attempts at the rim when the Spurs keep their young center near the paint.", "spurs", "victor-wembanyama", "articles/wembanyama-gm5.jpg"),
        ("Edwards headlines West guard watch list", "Features", "Minnesota's lead guard continues to pair downhill scoring with tougher defense.", "The Timberwolves have asked Edwards to defend stars while keeping his late-clock usage high.", "timberwolves", "anthony-edwards", "articles/edwards-game5-051426-scaled.jpg"),
        ("Haliburton fuels Indiana's early offense", "Video", "A breakdown of the Pacers' drag screens and hit-ahead passes.", "Indiana's best possessions start before the defense is matched, with Haliburton creating quick advantages.", "pacers", "tyrese-haliburton", "articles/johnson-iso-051426-scaled.jpg"),
        ("Lakers-Warriors condensed game", "Highlights", "Watch the decisive fourth-quarter possessions.", "Los Angeles found paint touches while Golden State hunted movement threes in a tight finish.", "lakers", "lebron-james", "articles/okc-lal-recap.jpg"),
        ("Brunson's footwork keeps Knicks offense steady", "Analysis", "New York relies on pivots, pace changes and patient pick-and-roll reads.", "Brunson creates separation without over-dribbling, giving New York a stable late-game plan.", "knicks", "jalen-brunson", "articles/brunson-iso-051426-scaled.jpg"),
        ("Bucks focus on half-court spacing", "Top Stories", "Milwaukee is balancing Antetokounmpo rim pressure with Lillard range.", "The Bucks' best lineups keep shooting on both wings and use early slips to clear the lane.", "bucks", "giannis-antetokounmpo", "articles/harden-game5.jpg"),
        ("Suns stars emphasize ball security", "Features", "Phoenix wants cleaner possessions before a Clippers matchup.", "Turnover margin has shaped recent Suns games, especially when opponents load up on Durant and Booker.", "suns", "kevin-durant", "articles/cavs-playoffs.jpg"),
        ("Magic-Cavaliers defensive matchup guide", "Preview", "Two East teams bring size, rim protection and physical point-of-attack defense.", "The game could come down to transition chances and which team wins the defensive glass.", "magic", "paolo-banchero", "articles/pistons-cavs-game6.jpg"),
        ("Mock draft board shifts after combine measurements", "Draft", "Front offices are weighing wing size, shooting indicators and defensive versatility.", "The latest draft board movement reflects how teams balance long-term upside with immediate rotation needs.", "hawks", "", "articles/draft-combine-2026.jpg"),
        ("Playoff rotation choices under the microscope", "Playoffs", "Coaches are trimming lineups and leaning into matchup-specific bench groups.", "The postseason field rewards teams that can survive non-star minutes and protect the glass.", "nuggets", "nikola-jokic", "articles/og-anunoby.jpg"),
        ("Awards voters debate two-way impact", "Awards", "Efficiency, availability and defensive role continue to shape the awards conversation.", "Several candidates combine box-score production with difficult nightly assignments.", "timberwolves", "anthony-edwards", "articles/wizards-no1.jpg"),
        ("Transaction tracker: contenders add shooting depth", "Transactions", "Several playoff hopefuls are using roster spots on movement shooting and switchable forwards.", "The latest transactions show teams prioritizing spacing around high-usage creators.", "seventysixers", "tyrese-maxey", "articles/morey.jpg"),
        ("History: classic guard duels that shaped the playoffs", "History", "From isolation battles to pick-and-roll counters, guard matchups have often defined series.", "Modern stars continue a long postseason tradition of late-clock shot creation.", "warriors", "stephen-curry", "articles/collins-obituary.png"),
        ("Around the NBA: road swings test West contenders", "Around the NBA", "Long trips are exposing depth, travel recovery and late-game execution.", "The next week features several back-to-backs that could shift seeding races.", "pelicans", "", "articles/peterson-dybantsa.jpg"),
        ("Draft notebook: teams look for connector forwards", "Draft", "Passing feel and defensive versatility are moving up evaluation boards.", "Teams with established stars are prioritizing players who can keep the ball moving.", "raptors", "", "articles/combine-knueppel.jpg"),
        ("Playoffs film room: corner help decisions", "Playoffs", "Small defensive choices are deciding whether offenses find the open corner.", "The best attacks are using skip passes and ghost screens to punish early help.", "clippers", "kawhi-leonard", "articles/brandon-clarke.png"),
        ("Awards watch: rookie rim protectors change schemes", "Awards", "Shot-blocking bigs are letting teams pressure higher at the point of attack.", "The rookie class has already influenced how opponents design their paint attacks.", "spurs", "victor-wembanyama", "articles/wembanyama-gm5.jpg"),
        ("Transaction tracker: hardship signings and 10-day deals", "Transactions", "Injuries are pushing teams to find short-term rotation insurance.", "Roster flexibility matters as teams protect practice depth during the closing stretch.", "heat", "jimmy-butler", "articles/ian-eagle-noah-eagle.jpg"),
        ("History: the evolution of five-out spacing", "History", "Modern offenses keep centers above the break and force rim protectors into space.", "The tactical shift has changed shot diets, rebounding lanes and help responsibilities.", "celtics", "jayson-tatum", "articles/peterson-dybantsa.jpg"),
        ("Around the NBA: young cores turn defense into identity", "Around the NBA", "Several rebuilding teams are finding a baseline through transition defense.", "Development staffs are emphasizing repeatable habits before expanding offensive roles.", "magic", "paolo-banchero", "articles/draft-combine-2026.jpg"),
    ]
    for i, (title, category, dek, body, team_slug, player_slug, image) in enumerate(articles):
        db.session.add(Article(
            title=title, slug=slugify(title), category=category, dek=dek, body=body,
            published_at=MIRROR_REFERENCE_DATE - timedelta(hours=i * 5),
            image=f"/static/images/{image}", related_team_slug=team_slug, related_player_slug=player_slug,
        ))

    # Append a deeper newsroom — generic dek/body keyed off the title so
    # category pages, search, and section landings have enough variety.
    base_articles = len(articles)
    for j, (title, category, team_slug, player_slug, image) in enumerate(EXTRA_ARTICLES):
        dek = f"{title} — featured coverage from the NBA.com newsroom."
        body = (
            f"{title}. Latest reporting includes context on the matchup, recent performance trends, "
            "key player availability and what to watch as the storyline develops."
        )
        db.session.add(Article(
            title=title, slug=slugify(title), category=category, dek=dek, body=body,
            published_at=MIRROR_REFERENCE_DATE - timedelta(hours=(base_articles + j) * 5),
            image=f"/static/images/{image}", related_team_slug=team_slug, related_player_slug=player_slug,
        ))

    product_defs = [
        ("Los Angeles Lakers Icon Swingman Jersey", "Jerseys", "lakers", 119.99, 139.99, "Gold", "lakers.svg", ["Nike Dri-FIT fabric", "Heat-applied name and number", "Classic Icon Edition colors"]),
        ("Boston Celtics Association Edition Jersey", "Jerseys", "celtics", 109.99, 129.99, "White", "celtics.svg", ["Lightweight double-knit mesh", "Woven jock tag", "Official team detailing"]),
        ("Dallas Mavericks Statement Hoodie", "Hoodies", "mavericks", 74.99, 89.99, "Royal", "mavericks.svg", ["Fleece lining", "Front pouch pocket", "Screen-printed team mark"]),
        ("Denver Nuggets 2024 Champions Tee", "T-Shirts", "nuggets", 34.99, 39.99, "Navy", "nuggets.svg", ["Cotton blend", "Rib-knit collar", "Commemorative graphic"]),
        ("Milwaukee Bucks City Edition Cap", "Hats", "bucks", 31.99, 35.99, "Cream", "bucks.svg", ["Adjustable strap", "Embroidered logo", "Curved bill"]),
        ("Golden State Warriors Hardwood Classics Jacket", "Outerwear", "warriors", 149.99, 179.99, "Royal", "warriors.svg", ["Full zip", "Satin finish", "Throwback trim"]),
        ("Oklahoma City Thunder Practice Shorts", "Shorts", "thunder", 54.99, 64.99, "Blue", "thunder.svg", ["Elastic waistband", "Side pockets", "Team color panels"]),
        ("Phoenix Suns Essential Pullover", "Hoodies", "suns", 69.99, 79.99, "Purple", "suns.svg", ["Midweight fleece", "Drawstring hood", "Screen print chest logo"]),
        ("New York Knicks Courtside Long Sleeve", "T-Shirts", "knicks", 44.99, 54.99, "Blue", "knicks.svg", ["Soft cotton feel", "Ribbed cuffs", "Courtside graphic"]),
        ("Minnesota Timberwolves Performance Tee", "T-Shirts", "timberwolves", 39.99, 44.99, "Green", "timberwolves.svg", ["Moisture-wicking fabric", "Athletic fit", "Reflective details"]),
        ("San Antonio Spurs Rookie Graphic Tee", "T-Shirts", "spurs", 37.99, 42.99, "Black", "spurs.svg", ["Rookie-year graphic", "Cotton jersey", "Screen print"]),
        ("Indiana Pacers Fastbreak Hoodie", "Hoodies", "pacers", 72.99, 84.99, "Navy", "pacers.svg", ["French terry fabric", "Team wordmark", "Kangaroo pocket"]),
        ("Miami Heat Vice Nights Cap", "Hats", "heat", 29.99, 34.99, "Black", "heat.svg", ["Snapback closure", "Raised embroidery", "Vice color undervisor"]),
        ("LA Clippers Intuit Dome Opening Tee", "T-Shirts", "clippers", 32.99, 39.99, "Red", "clippers.svg", ["Arena launch graphic", "Unisex fit", "Soft cotton"]),
        ("Philadelphia 76ers Maxey Name & Number Tee", "T-Shirts", "seventysixers", 39.99, 49.99, "Royal", "seventysixers.svg", ["Player name print", "Tagless collar", "Official team colors"]),
        ("Orlando Magic Defensive Identity Hoodie", "Hoodies", "magic", 68.99, 78.99, "Black", "magic.svg", ["Heavy fleece", "Raised team mark", "Ribbed hem"]),
    ]
    for name, category, team_slug, price, list_price, color, logo, features in product_defs:
        db.session.add(Product(
            name=name, slug=slugify(name), category=category, team_slug=team_slug, price=price,
            list_price=list_price, rating=4.2 + (price % 7) / 10, stock=18, color=color,
            image=f"/static/images/teams/{logo}", description=f"Official NBA Store gear for {teams_by_slug[team_slug].full_name} fans.",
            features=json.dumps(features), sizes="S,M,L,XL,2XL" if category != "Hats" else "One Size",
        ))

    for name, category, team_slug, price, list_price, color, logo, features in EXTRA_PRODUCTS:
        if team_slug and team_slug in teams_by_slug:
            description = f"Official NBA Store gear for {teams_by_slug[team_slug].full_name} fans."
            image_path = f"/static/images/teams/{logo}"
        else:
            description = "Officially licensed NBA fan gear available on NBA Store."
            image_path = f"/static/images/{logo}"
        if category == "Hats":
            sizes = "One Size"
        elif category == "Accessories":
            sizes = "One Size"
        else:
            sizes = "S,M,L,XL,2XL"
        db.session.add(Product(
            name=name, slug=slugify(name), category=category, team_slug=team_slug, price=price,
            list_price=list_price, rating=4.2 + (price % 7) / 10, stock=22, color=color,
            image=image_path, description=description,
            features=json.dumps(features), sizes=sizes,
        ))
    db.session.commit()


def seed_benchmark_users():
    if User.query.filter_by(email="alice.j@test.com").first():
        return

    users = [
        ("alice_j", "alice.j@test.com", "Alice Johnson", "213-555-0199", "742 Figueroa St", "Los Angeles", "CA", "90015", "lakers", "4242"),
        ("bob_c", "bob.c@test.com", "Bob Chen", "617-555-0182", "100 Legends Way", "Boston", "MA", "02114", "celtics", "1881"),
        ("carol_d", "carol.d@test.com", "Carol Davis", "214-555-0144", "2500 Victory Ave", "Dallas", "TX", "75219", "mavericks", "9090"),
        ("david_k", "david.k@test.com", "David Kim", "212-555-0117", "4 Pennsylvania Plaza", "New York", "NY", "10001", "knicks", "7777"),
    ]
    created = []
    # PINNED bcrypt hash for "TestPass123!" — bcrypt.generate_password_hash()
    # is non-deterministic (per-call salt), which breaks the byte-identical
    # reset invariant. Pinning the hash keeps seed runs reproducible.
    PINNED_HASH = "$2b$12$RwAC/sfwDHtccU//A20fde.uKkZK4Ptnjjyua2l2ktwI6uysAp3Ou"
    for username, email, name, phone, address, city, state, zip_code, fav_team, card in users:
        user = User(
            username=username, email=email, display_name=name, phone=phone,
            address_line1=address, city=city, state=state, zip_code=zip_code,
            favorite_team_slug=fav_team, payment_last4=card,
        )
        user.password_hash = PINNED_HASH
        db.session.add(user)
        created.append(user)
    db.session.flush()

    for user in created:
        products = Product.query.filter((Product.team_slug == user.favorite_team_slug) | (Product.category == "T-Shirts")).limit(3).all()
        for idx, product in enumerate(products[:2]):
            db.session.add(CartItem(user_id=user.id, product_id=product.id, quantity=idx + 1, size="L"))
        team = Team.query.filter_by(slug=user.favorite_team_slug).first()
        if team:
            db.session.add(Favorite(user_id=user.id, item_type="team", item_id=team.id, note="My default team"))
            player = Player.query.filter_by(team_id=team.id).first()
            if player:
                db.session.add(Favorite(user_id=user.id, item_type="player", item_id=player.id))
        article = Article.query.order_by(Article.published_at.desc()).offset(user.id - 1).first()
        if article:
            db.session.add(Favorite(user_id=user.id, item_type="article", item_id=article.id))
        order = Order(
            user_id=user.id,
            order_number=f"NBA-SEED-{user.id:04d}",
            status="Delivered" if user.id % 2 else "Shipped",
            subtotal=154.98,
            shipping=0,
            tax=12.79,
            total=167.77,
            ship_address=f"{user.address_line1}, {user.city}, {user.state} {user.zip_code}",
            payment_last4=user.payment_last4,
            created_at=MIRROR_REFERENCE_DATE - timedelta(days=18 + user.id),
        )
        db.session.add(order)
        db.session.flush()
        db.session.add(OrderItem(order_id=order.id, product_name="Official NBA team gear bundle", quantity=2, price=77.49, size="L"))
    # Seed a deterministic set of saved ticket requests so the /account page
    # and ticket_request tasks have realistic data without depending on
    # runtime POSTs.
    upcoming_games = (
        Game.query.filter(Game.status == "Scheduled")
        .order_by(Game.game_date, Game.id)
        .all()
    )
    if upcoming_games:
        ticket_plans = [
            ("alice_j", 0, 2, "Lower bowl - sideline"),
            ("alice_j", 2, 4, "Suite level"),
            ("alice_j", 4, 2, "Courtside upgrade"),
            ("bob_c", 1, 2, "Loge balcony"),
            ("bob_c", 3, 3, "Lower bowl - baseline"),
            ("carol_d", 0, 2, "Center court"),
            ("carol_d", 5, 4, "Mezzanine"),
            ("david_k", 1, 2, "Lower bowl - corner"),
            ("david_k", 2, 3, "Upper bowl"),
            ("david_k", 4, 2, "Floor seats"),
        ]
        users_by_username = {user.username: user for user in created}
        for username, game_idx, seats, preference in ticket_plans:
            user = users_by_username.get(username)
            if not user or game_idx >= len(upcoming_games):
                continue
            db.session.add(TicketRequest(
                user_id=user.id,
                game_id=upcoming_games[game_idx].id,
                seats=seats,
                section_preference=preference,
                status="Saved",
            ))
    db.session.commit()


with app.app_context():
    db.create_all()
    seed_database()
    seed_benchmark_users()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
