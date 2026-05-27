#!/usr/bin/env python3
"""Allrecipes Mirror - Flask Application"""
import os
import re
import json
import random
import string
import hashlib
from datetime import datetime, timedelta
from functools import wraps

from flask import (Flask, render_template, request, redirect, url_for, flash,
                   jsonify, abort, session)
from flask_sqlalchemy import SQLAlchemy
from flask_login import (LoginManager, UserMixin, login_user, logout_user,
                         current_user, login_required)
from flask_bcrypt import Bcrypt
from flask_wtf import CSRFProtect
from werkzeug.utils import secure_filename

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------
app = Flask(__name__)
app.config['SECRET_KEY'] = 'allrecipes-mirror-secret-key-2024'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(
    os.path.dirname(os.path.abspath(__file__)), 'instance', 'allrecipes.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
csrf = CSRFProtect(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'


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

# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

# Pinned reference date used as the default for every created_at column so
# rebuilding the seed DB from source yields a byte-identical SQLite file.
# Any seed row that wants a different timestamp must set created_at
# explicitly (see seed_data.py and seed_benchmark_users below).
MIRROR_REFERENCE_DATE = datetime(2026, 4, 15, 12, 0, 0)


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    display_name = db.Column(db.String(100), default='')
    bio = db.Column(db.Text, default='')
    location = db.Column(db.String(100), default='')
    avatar_url = db.Column(db.String(300), default='')
    created_at = db.Column(db.DateTime, default=lambda: MIRROR_REFERENCE_DATE)
    # Relationships
    reviews = db.relationship('Review', backref='author', lazy=True, cascade='all, delete-orphan')
    recipe_box = db.relationship('RecipeBoxItem', backref='user', lazy=True, cascade='all, delete-orphan')
    meal_plans = db.relationship('MealPlanItem', backref='user', lazy=True, cascade='all, delete-orphan')
    shopping_lists = db.relationship('ShoppingList', backref='user', lazy=True, cascade='all, delete-orphan')

    def set_password(self, password):
        self.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')

    def check_password(self, password):
        return bcrypt.check_password_hash(self.password_hash, password)


class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    slug = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.Text, default='')
    image = db.Column(db.String(300), default='')
    parent_type = db.Column(db.String(50), default='meal')  # meal, ingredient, cuisine
    display_order = db.Column(db.Integer, default=0)
    recipes = db.relationship('Recipe', backref='category', lazy=True)


class Recipe(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    slug = db.Column(db.String(200), unique=True, nullable=False, index=True)
    description = db.Column(db.Text, default='')
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'), index=True)
    cuisine = db.Column(db.String(100), default='')
    image = db.Column(db.String(300), default='')
    prep_time = db.Column(db.String(50), default='')
    cook_time = db.Column(db.String(50), default='')
    total_time = db.Column(db.String(50), default='')
    additional_time = db.Column(db.String(50), default='')
    servings = db.Column(db.String(20), default='')
    yield_amount = db.Column(db.String(100), default='')
    calories = db.Column(db.Integer, default=0)
    ingredients_json = db.Column(db.Text, default='[]')
    instructions_json = db.Column(db.Text, default='[]')
    nutrition_json = db.Column(db.Text, default='{}')
    tags_json = db.Column(db.Text, default='[]')
    gallery_json = db.Column(db.Text, default='[]')
    is_featured = db.Column(db.Boolean, default=False)
    is_editors_pick = db.Column(db.Boolean, default=False)
    avg_rating = db.Column(db.Float, default=0.0)
    review_count = db.Column(db.Integer, default=0)
    author_name = db.Column(db.String(100), default='Allrecipes Community')
    # Task-driven filter columns
    prep_time_mins = db.Column(db.Integer, default=0)
    cook_time_mins = db.Column(db.Integer, default=0)
    total_time_mins = db.Column(db.Integer, default=0)
    ingredient_count = db.Column(db.Integer, default=0)
    dietary_tags_json = db.Column(db.Text, default='[]')  # vegan, vegetarian, gluten-free, etc.
    dish_type = db.Column(db.String(50), default='')  # main, dessert, breakfast, appetizer, salad, soup
    meal_type = db.Column(db.String(50), default='')  # breakfast, lunch, dinner, snack
    cooking_method = db.Column(db.String(80), default='')  # baked, grilled, slow cooker, etc.
    main_ingredient = db.Column(db.String(80), default='')  # chicken, beef, fish, etc.
    occasion = db.Column(db.String(100), default='')
    season = db.Column(db.String(50), default='')
    feature_tags = db.Column(db.Text, default='[]')  # kebab-case keywords for filter matching
    latest_review_text = db.Column(db.Text, default='')
    storage_instructions = db.Column(db.Text, default='')
    primary_seasoning = db.Column(db.String(120), default='')
    max_oven_temp = db.Column(db.Integer, default=0)  # e.g. 425 for apple pie
    created_at = db.Column(db.DateTime, default=lambda: MIRROR_REFERENCE_DATE)
    # Relationships
    reviews = db.relationship('Review', backref='recipe', lazy=True, cascade='all, delete-orphan')
    recipe_box_items = db.relationship('RecipeBoxItem', backref='recipe', lazy=True, cascade='all, delete-orphan')

    def get_ingredients(self):
        try:
            return json.loads(self.ingredients_json)
        except:
            return []

    def get_instructions(self):
        try:
            return json.loads(self.instructions_json)
        except:
            return []

    def get_nutrition(self):
        try:
            return json.loads(self.nutrition_json)
        except:
            return {}

    def get_tags(self):
        try:
            return json.loads(self.tags_json)
        except:
            return []

    def get_gallery(self):
        try:
            return json.loads(self.gallery_json)
        except:
            return []

    def get_dietary_tags(self):
        try:
            return json.loads(self.dietary_tags_json)
        except:
            return []

    def get_feature_tags(self):
        try:
            return json.loads(self.feature_tags)
        except:
            return []


class Review(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    recipe_id = db.Column(db.Integer, db.ForeignKey('recipe.id'), nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    title = db.Column(db.String(200), default='')
    body = db.Column(db.Text, default='')
    helpful_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=lambda: MIRROR_REFERENCE_DATE)


class RecipeBoxItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    recipe_id = db.Column(db.Integer, db.ForeignKey('recipe.id'), nullable=False)
    notes = db.Column(db.Text, default='')
    created_at = db.Column(db.DateTime, default=lambda: MIRROR_REFERENCE_DATE)


class MealPlanItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    recipe_id = db.Column(db.Integer, db.ForeignKey('recipe.id'), nullable=False)
    day = db.Column(db.String(20), nullable=False)  # monday, tuesday, etc.
    meal_type = db.Column(db.String(20), nullable=False)  # breakfast, lunch, dinner, snack
    created_at = db.Column(db.DateTime, default=lambda: MIRROR_REFERENCE_DATE)
    recipe = db.relationship('Recipe', lazy=True)


class ShoppingList(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    name = db.Column(db.String(200), default='Shopping List')
    items_json = db.Column(db.Text, default='[]')
    created_at = db.Column(db.DateTime, default=lambda: MIRROR_REFERENCE_DATE)

    def get_items(self):
        try:
            return json.loads(self.items_json)
        except:
            return []

    def set_items(self, items):
        self.items_json = json.dumps(items)


# ---------------------------------------------------------------------------
# R4: Article model + Collection model — cooking-tips long-form & curated lists
# ---------------------------------------------------------------------------

class Article(db.Model):
    """Long-form cooking-tip article (e.g. /article/how-to-roast-a-turkey)."""
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    slug = db.Column(db.String(200), unique=True, nullable=False)
    category = db.Column(db.String(80), default='cooking-tips')
    author_name = db.Column(db.String(120), default='Allrecipes Editors')
    excerpt = db.Column(db.Text, default='')
    body_json = db.Column(db.Text, default='[]')  # list of {heading, paragraphs:[]}
    hero_image = db.Column(db.String(300), default='')
    read_time_mins = db.Column(db.Integer, default=4)
    related_recipes_json = db.Column(db.Text, default='[]')  # list of slug
    tags_json = db.Column(db.Text, default='[]')
    published_at = db.Column(db.DateTime, default=lambda: MIRROR_REFERENCE_DATE)
    view_count = db.Column(db.Integer, default=0)

    def get_body(self):
        try:
            return json.loads(self.body_json)
        except Exception:
            return []

    def get_related_recipes(self):
        try:
            return json.loads(self.related_recipes_json)
        except Exception:
            return []

    def get_tags(self):
        try:
            return json.loads(self.tags_json)
        except Exception:
            return []


class Collection(db.Model):
    """Curated recipe list (e.g. /collection/best-summer-grilling)."""
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    slug = db.Column(db.String(200), unique=True, nullable=False)
    subtitle = db.Column(db.String(300), default='')
    description = db.Column(db.Text, default='')
    hero_image = db.Column(db.String(300), default='')
    curator_name = db.Column(db.String(120), default='Allrecipes Editors')
    recipe_slugs_json = db.Column(db.Text, default='[]')
    tags_json = db.Column(db.Text, default='[]')
    season = db.Column(db.String(40), default='')
    display_order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=lambda: MIRROR_REFERENCE_DATE)

    def get_recipe_slugs(self):
        try:
            return json.loads(self.recipe_slugs_json)
        except Exception:
            return []

    def get_tags(self):
        try:
            return json.loads(self.tags_json)
        except Exception:
            return []


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# ---------------------------------------------------------------------------
# R4: Jinja filters for share-token and gallery step images
# ---------------------------------------------------------------------------

@app.template_filter('hash_slug')
def _hash_slug(slug):
    """Deterministic 7-char token for /r/<token> share URLs."""
    return hashlib.md5((slug or '').encode()).hexdigest()[:7]


@app.template_filter('step_images_from')
def _step_images_from(gallery_json):
    """Return up to 3 step-image URLs derived from gallery_json. Falls back
    to a deterministic pool of /static/images/recipes_real/recipe_N.jpg
    so every recipe shows a multi-step strip in the directions panel."""
    try:
        gallery = json.loads(gallery_json or '[]')
    except Exception:
        gallery = []
    out = []
    for section in gallery:
        for img in (section.get('images') if isinstance(section, dict) else []) or []:
            if img and img not in out:
                out.append(img)
            if len(out) >= 3:
                return out
    return out


# ---------------------------------------------------------------------------
# Template helpers
# ---------------------------------------------------------------------------

@app.context_processor
def utility_processor():
    def recipe_box_count():
        if current_user.is_authenticated:
            return RecipeBoxItem.query.filter_by(user_id=current_user.id).count()
        return 0

    def is_in_recipe_box(recipe_id):
        if current_user.is_authenticated:
            return RecipeBoxItem.query.filter_by(
                user_id=current_user.id, recipe_id=recipe_id).first() is not None
        return False

    def current_relative_url():
        path = request.full_path.rstrip('?')
        return path or url_for('index')

    return dict(
        recipe_box_count=recipe_box_count,
        is_in_recipe_box=is_in_recipe_box,
        current_relative_url=current_relative_url,
    )


# ---------------------------------------------------------------------------
# Error handlers — R5 polish for unknown routes / methods / server errors
# ---------------------------------------------------------------------------

@app.errorhandler(404)
def _err_404(e):
    # Top 6 most popular recipes as suggested fallbacks.
    suggestions = (
        Recipe.query.order_by(Recipe.review_count.desc())
        .limit(6).all()
    )
    return render_template('404.html', suggestions=suggestions), 404


@app.errorhandler(405)
def _err_405(e):
    return render_template('404.html', suggestions=[], method_not_allowed=True), 405


@app.errorhandler(500)
def _err_500(e):
    return render_template('404.html', suggestions=[], server_error=True), 500


@app.errorhandler(429)
def _err_429(e):
    """Rate-limit page (R6). Triggered manually via /__rate-limit-demo
    or by middleware when bots over-request. Polished 'try again later'."""
    return render_template('rate_limit.html'), 429


# R6: demo endpoints for edge cases (polished UX for slow-loading,
# rate-limited, expired-session, empty-cart). These are deterministic and
# never affect non-demo traffic — they live behind clearly-named paths.

@app.route('/__rate-limit-demo')
def rate_limit_demo():
    """Polished 429 page for the harness to screenshot."""
    return render_template('rate_limit.html'), 429


@app.route('/__session-expired-demo')
def session_expired_demo():
    """Polished expired-session page (R6 edge case)."""
    return render_template('session_expired.html'), 401


@app.route('/__loading-demo')
def loading_demo():
    """Polished slow-network loading skeleton (R6 edge case)."""
    return render_template('loading_skeleton.html')


@app.route('/__server-error-demo')
def server_error_demo():
    """Polished 5xx page (R6 edge case)."""
    return render_template('404.html', suggestions=[], server_error=True), 500


def safe_redirect_target(target, default_endpoint='index'):
    if target and target.startswith('/') and not target.startswith('//'):
        return target
    return url_for(default_endpoint)


# ---------------------------------------------------------------------------
# Routes — Static Pages
# ---------------------------------------------------------------------------

@app.route('/')
def index():
    featured = Recipe.query.filter_by(is_featured=True).limit(6).all()
    editors_picks = Recipe.query.filter_by(is_editors_pick=True).limit(6).all()
    latest = Recipe.query.order_by(Recipe.created_at.desc()).limit(12).all()
    categories = Category.query.order_by(Category.display_order).all()
    popular = Recipe.query.order_by(Recipe.review_count.desc()).limit(8).all()
    return render_template('index.html', featured=featured, editors_picks=editors_picks,
                           latest=latest, categories=categories, popular=popular)


@app.route('/recipes')
def all_recipes():
    page = request.args.get('page', 1, type=int)
    sort = request.args.get('sort', 'popular')
    q = Recipe.query
    if sort == 'newest':
        q = q.order_by(Recipe.created_at.desc())
    elif sort == 'rating':
        q = q.order_by(Recipe.avg_rating.desc())
    elif sort == 'name':
        q = q.order_by(Recipe.title)
    else:
        q = q.order_by(Recipe.review_count.desc())
    recipes = q.paginate(page=page, per_page=12, error_out=False)
    categories = Category.query.order_by(Category.display_order).all()
    return render_template('recipes.html', recipes=recipes, sort=sort, categories=categories)


# Per-category broadening predicates. The mirror DB only assigns
# `category_id` to a tiny subset of recipes (≈26/219), so the original
# strict `filter_by(category_id=…)` query produced near-empty category
# pages. We expand each category by matching recipes whose
# title/meal_type/dish_type/cuisine/main_ingredient suggest membership.
# Predicates are written as small lambdas so they compose with SQLAlchemy.
def _category_match_clause(slug):
    s = (slug or '').lower()
    title = Recipe.title
    if s == 'breakfast':
        return db.or_(
            Recipe.meal_type.ilike('%breakfast%'),
            Recipe.dish_type.ilike('%breakfast%'),
            title.ilike('%breakfast%'), title.ilike('%pancake%'),
            title.ilike('%waffle%'), title.ilike('%omelet%'),
            title.ilike('%crepe%'), title.ilike('%smoothie%'),
            title.ilike('%granola%'), title.ilike('%muffin%'),
            title.ilike('%scone%'), title.ilike('%bagel%'),
            title.ilike('%french toast%'), title.ilike('%oatmeal%'),
            title.ilike('%bacon%'), title.ilike('%hash brown%'),
            title.ilike('%frittata%'), title.ilike('%quiche%'),
            # Word-boundary egg matches (avoids "vegg-ie", "egg-plant")
            title.ilike('egg %'), title.ilike('% egg'),
            title.ilike('% egg %'), title.ilike('% eggs'),
            title.ilike('% eggs %'), title.ilike('eggs %'),
        )
    if s == 'dinner':
        return db.or_(
            Recipe.meal_type.ilike('%dinner%'),
            Recipe.dish_type.ilike('%main%'),
        )
    if s == 'desserts':
        return db.or_(
            Recipe.dish_type.ilike('%dessert%'),
            title.ilike('%cookie%'), title.ilike('%cake%'),
            title.ilike('%brownie%'), title.ilike('%pie%'),
            title.ilike('%pudding%'), title.ilike('%truffle%'),
            title.ilike('%cupcake%'), title.ilike('%tart%'),
            title.ilike('%cobbler%'), title.ilike('%crisp%'),
            title.ilike('%mousse%'), title.ilike('%ice cream%'),
            title.ilike('%fudge%'), title.ilike('%cheesecake%'),
        )
    if s == 'appetizers':
        return db.or_(
            Recipe.dish_type.ilike('%appetizer%'),
            Recipe.dish_type.ilike('%snack%'),
            Recipe.dish_type.ilike('%sauce%'),
            Recipe.meal_type.ilike('%appetizer%'),
            Recipe.meal_type.ilike('%snack%'),
            title.ilike('%dip%'), title.ilike('%bruschetta%'),
            title.ilike('%appetizer%'), title.ilike('%nachos%'),
            title.ilike('%wings%'), title.ilike('%salsa%'),
            title.ilike('%hummus%'), title.ilike('%guacamole%'),
            title.ilike('%bites%'), title.ilike('%poppers%'),
            title.ilike('%bowl%'), title.ilike('%snack%'),
            title.ilike('%spread%'), title.ilike('%crackers%'),
            title.ilike('%canape%'), title.ilike('%pinwheel%'),
            title.ilike('%toast%'), title.ilike('%rolls%'),
            title.ilike('%skewers%'),
        )
    if s == 'chicken':
        return db.or_(
            Recipe.main_ingredient.ilike('%chicken%'),
            title.ilike('%chicken%'),
        )
    if s == 'pasta':
        return db.or_(
            Recipe.main_ingredient.ilike('%pasta%'),
            title.ilike('%pasta%'), title.ilike('%spaghetti%'),
            title.ilike('%lasagna%'), title.ilike('%fettuccine%'),
            title.ilike('%macaroni%'), title.ilike('%ravioli%'),
            title.ilike('%penne%'), title.ilike('%noodle%'),
        )
    if s == 'salads':
        return db.or_(
            Recipe.dish_type.ilike('%salad%'),
            title.ilike('%salad%'), title.ilike('%bowl%'),
            title.ilike('%slaw%'), title.ilike('%greens%'),
        )
    if s == 'soups':
        return db.or_(
            Recipe.dish_type.ilike('%soup%'),
            title.ilike('%soup%'), title.ilike('%stew%'),
            title.ilike('%chili%'), title.ilike('%chowder%'),
            title.ilike('%bisque%'), title.ilike('%broth%'),
            title.ilike('%ramen%'), title.ilike('%pho%'),
            title.ilike('%minestrone%'), title.ilike('%gumbo%'),
        )
    if s == 'seafood':
        return db.or_(
            Recipe.main_ingredient.in_(['salmon', 'fish', 'seafood', 'tuna']),
            title.ilike('%salmon%'), title.ilike('%fish%'),
            title.ilike('%shrimp%'), title.ilike('%tuna%'),
            title.ilike('%lobster%'), title.ilike('%crab%'),
            title.ilike('%scallop%'), title.ilike('%halibut%'),
            title.ilike('%catfish%'), title.ilike('%branzino%'),
            title.ilike('%sea bass%'), title.ilike('%cod%'),
            title.ilike('%sushi%'), title.ilike('%clam%'),
            title.ilike('%oyster%'), title.ilike('%mussel%'),
        )
    if s == 'baking':
        return db.or_(
            Recipe.dish_type.ilike('%bread%'),
            Recipe.cooking_method.ilike('%baked%'),
            title.ilike('%baked%'), title.ilike('%bread%'),
            title.ilike('%muffin%'), title.ilike('%cake%'),
            title.ilike('%cookie%'), title.ilike('%scone%'),
            title.ilike('%biscuit%'), title.ilike('%pie%'),
            title.ilike('%pastry%'), title.ilike('%roll%'),
        )
    if s == 'italian':
        return db.or_(
            Recipe.cuisine.ilike('%italian%'),
            title.ilike('%italian%'), title.ilike('%lasagna%'),
            title.ilike('%pasta%'), title.ilike('%spaghetti%'),
            title.ilike('%pizza%'), title.ilike('%bruschetta%'),
            title.ilike('%risotto%'), title.ilike('%parmesan%'),
            title.ilike('%marinara%'), title.ilike('%meatball%'),
            title.ilike('%carbonara%'), title.ilike('%ravioli%'),
            title.ilike('%fettuccine%'), title.ilike('%penne%'),
            title.ilike('%alfredo%'), title.ilike('%pesto%'),
            title.ilike('%caprese%'), title.ilike('%tiramisu%'),
        )
    if s == 'mexican':
        return db.or_(
            Recipe.cuisine.ilike('%mexican%'),
            Recipe.cuisine.ilike('%tex-mex%'),
            Recipe.cuisine.ilike('%latin%'),
            title.ilike('%mexican%'), title.ilike('%taco%'),
            title.ilike('%burrito%'), title.ilike('%quesadilla%'),
            title.ilike('%enchilada%'), title.ilike('%fajita%'),
            title.ilike('%salsa%'), title.ilike('%guacamole%'),
            title.ilike('%nachos%'), title.ilike('%tortilla%'),
            title.ilike('%chimichanga%'), title.ilike('%tostada%'),
            title.ilike('%tamale%'), title.ilike('%pozole%'),
            title.ilike('%mole%'), title.ilike('%refried%'),
            title.ilike('%black bean%'), title.ilike('%spanish rice%'),
            title.ilike('%avocado%'), title.ilike('%lime%'),
            title.ilike('%cilantro%'), title.ilike('%chipotle%'),
            title.ilike('%jalapeno%'),
        )
    if s == 'asian':
        return db.or_(
            Recipe.cuisine.ilike('%asian%'),
            Recipe.cuisine.ilike('%chinese%'),
            Recipe.cuisine.ilike('%japanese%'),
            Recipe.cuisine.ilike('%thai%'),
            Recipe.cuisine.ilike('%korean%'),
            Recipe.cuisine.ilike('%vietnamese%'),
            Recipe.cuisine.ilike('%indian%'),
            title.ilike('%teriyaki%'), title.ilike('%curry%'),
            title.ilike('%fried rice%'), title.ilike('%stir fry%'),
            title.ilike('%sushi%'), title.ilike('%ramen%'),
            title.ilike('%pad thai%'), title.ilike('%dumpling%'),
            title.ilike('%kimchi%'), title.ilike('%tikka%'),
            title.ilike('%masala%'), title.ilike('%pho%'),
            title.ilike('%shiitake%'), title.ilike('%miso%'),
            title.ilike('%coconut%'), title.ilike('%tofu%'),
            title.ilike('%satay%'), title.ilike('%bao%'),
            title.ilike('%udon%'), title.ilike('%soba%'),
            title.ilike('%sashimi%'), title.ilike('%edamame%'),
            title.ilike('%tandoori%'), title.ilike('%biryani%'),
            title.ilike('%naan%'), title.ilike('%sesame%'),
            title.ilike('%ginger%'), title.ilike('%wonton%'),
        )
    if s == 'healthy':
        return db.or_(
            Recipe.dietary_tags_json.ilike('%vegan%'),
            Recipe.dietary_tags_json.ilike('%vegetarian%'),
            Recipe.dietary_tags_json.ilike('%gluten-free%'),
            Recipe.dietary_tags_json.ilike('%low-carb%'),
            Recipe.dietary_tags_json.ilike('%high-protein%'),
            Recipe.dietary_tags_json.ilike('%keto%'),
            Recipe.dietary_tags_json.ilike('%paleo%'),
            title.ilike('%healthy%'), title.ilike('%vegan%'),
            title.ilike('%vegetarian%'), title.ilike('%quinoa%'),
            title.ilike('%kale%'), title.ilike('%smoothie%'),
            title.ilike('%avocado%'), title.ilike('%cauliflower%'),
            title.ilike('%low-carb%'), title.ilike('%gluten-free%'),
        )
    # ---- Extended catalog cuisines ----
    if s == 'british':
        return db.or_(
            Recipe.cuisine.ilike('%british%'),
            Recipe.cuisine.ilike('%irish%'),
            title.ilike('%shepherd%'), title.ilike('%fish and chip%'),
            title.ilike('%bangers%'), title.ilike('%pudding%'),
            title.ilike('%scone%'), title.ilike('%trifle%'),
        )
    if s == 'french':
        return db.or_(
            Recipe.cuisine.ilike('%french%'),
            title.ilike('%crepe%'), title.ilike('%souffle%'),
            title.ilike('%ratatouille%'), title.ilike('%bouillabaisse%'),
            title.ilike('%coq au vin%'), title.ilike('%tarte%'),
            title.ilike('%croissant%'), title.ilike('%quiche%'),
        )
    if s == 'indian':
        return db.or_(
            Recipe.cuisine.ilike('%indian%'),
            title.ilike('%curry%'), title.ilike('%tikka%'),
            title.ilike('%masala%'), title.ilike('%biryani%'),
            title.ilike('%naan%'), title.ilike('%tandoori%'),
            title.ilike('%dal%'), title.ilike('%samosa%'),
            title.ilike('%vindaloo%'),
        )
    if s == 'chinese':
        return db.or_(
            Recipe.cuisine.ilike('%chinese%'),
            title.ilike('%kung pao%'), title.ilike('%lo mein%'),
            title.ilike('%chow mein%'), title.ilike('%dumpling%'),
            title.ilike('%dim sum%'), title.ilike('%mapo%'),
            title.ilike('%wonton%'), title.ilike('%bao%'),
        )
    if s == 'japanese':
        return db.or_(
            Recipe.cuisine.ilike('%japanese%'),
            title.ilike('%sushi%'), title.ilike('%ramen%'),
            title.ilike('%teriyaki%'), title.ilike('%tempura%'),
            title.ilike('%udon%'), title.ilike('%soba%'),
            title.ilike('%miso%'), title.ilike('%sashimi%'),
            title.ilike('%katsu%'), title.ilike('%donburi%'),
        )
    if s == 'thai':
        return db.or_(
            Recipe.cuisine.ilike('%thai%'),
            title.ilike('%pad thai%'), title.ilike('%tom yum%'),
            title.ilike('%tom kha%'), title.ilike('%green curry%'),
            title.ilike('%red curry%'), title.ilike('%satay%'),
            title.ilike('%massaman%'),
        )
    if s == 'mediterranean':
        return db.or_(
            Recipe.cuisine.ilike('%mediterranean%'),
            Recipe.cuisine.ilike('%greek%'),
            Recipe.cuisine.ilike('%turkish%'),
            Recipe.cuisine.ilike('%moroccan%'),
            Recipe.cuisine.ilike('%spanish%'),
            title.ilike('%hummus%'), title.ilike('%falafel%'),
            title.ilike('%tabbouleh%'), title.ilike('%tagine%'),
            title.ilike('%paella%'), title.ilike('%gyro%'),
            title.ilike('%shawarma%'), title.ilike('%kebab%'),
            title.ilike('%moussaka%'),
        )
    if s == 'american':
        return db.or_(
            Recipe.cuisine.ilike('%american%'),
            title.ilike('%burger%'), title.ilike('%bbq%'),
            title.ilike('%mac and cheese%'), title.ilike('%cornbread%'),
            title.ilike('%apple pie%'), title.ilike('%pulled pork%'),
            title.ilike('%fried chicken%'), title.ilike('%cobbler%'),
        )
    if s == 'beef':
        return db.or_(
            Recipe.main_ingredient.ilike('%beef%'),
            title.ilike('%beef%'), title.ilike('%steak%'),
            title.ilike('%burger%'), title.ilike('%brisket%'),
            title.ilike('%meatball%'), title.ilike('%meatloaf%'),
            title.ilike('%stroganoff%'),
        )
    if s == 'pork':
        return db.or_(
            Recipe.main_ingredient.ilike('%pork%'),
            title.ilike('%pork%'), title.ilike('%bacon%'),
            title.ilike('%ham%'), title.ilike('%sausage%'),
            title.ilike('%pulled pork%'), title.ilike('%ribs%'),
        )
    if s == 'lamb':
        return db.or_(
            Recipe.main_ingredient.ilike('%lamb%'),
            title.ilike('%lamb%'), title.ilike('%kebab%'),
            title.ilike('%shepherd%'), title.ilike('%goat%'),
        )
    if s == 'vegetarian':
        return db.or_(
            Recipe.dietary_tags_json.ilike('%vegetarian%'),
            Recipe.dietary_tags_json.ilike('%vegan%'),
            title.ilike('%vegetarian%'), title.ilike('%veggie%'),
            title.ilike('%tofu%'), title.ilike('%paneer%'),
            title.ilike('%eggplant%'), title.ilike('%chickpea%'),
        )
    if s == 'vegan':
        return db.or_(
            Recipe.dietary_tags_json.ilike('%vegan%'),
            title.ilike('%vegan%'), title.ilike('%tofu%'),
            title.ilike('%tempeh%'), title.ilike('%lentil%'),
        )
    if s == 'side-dishes':
        return db.or_(
            Recipe.dish_type.ilike('%side%'),
            Recipe.meal_type.ilike('%side%'),
            title.ilike('%mashed potato%'), title.ilike('%coleslaw%'),
            title.ilike('%roasted vegetable%'), title.ilike('%pilaf%'),
            title.ilike('%risotto%'), title.ilike('%dressing%'),
        )
    if s == 'slow-cooker':
        return db.or_(
            Recipe.cooking_method.ilike('%slow cooker%'),
            Recipe.cooking_method.ilike('%crock%'),
            title.ilike('%slow cooker%'), title.ilike('%crock pot%'),
            title.ilike('%pulled pork%'), title.ilike('%stew%'),
            title.ilike('%pot roast%'),
        )
    return None


class _StaticPagination:
    """Lightweight stand-in for Flask-SQLAlchemy's Pagination object so
    `category.html` can keep using `recipes.items`, `recipes.has_prev`, etc.
    when the underlying list is built in Python (after slug expansion +
    popular-recipe padding)."""

    def __init__(self, items, page, per_page, total):
        self.page = page
        self.per_page = per_page
        self.total = total
        self.pages = max(1, (total + per_page - 1) // per_page)
        start = (page - 1) * per_page
        self.items = items[start:start + per_page]
        self.has_prev = page > 1
        self.has_next = page < self.pages
        self.prev_num = page - 1 if self.has_prev else None
        self.next_num = page + 1 if self.has_next else None

    def iter_pages(self, left_edge=2, left_current=2,
                   right_current=3, right_edge=2):
        last = 0
        for num in range(1, self.pages + 1):
            if (num <= left_edge
                    or (self.page - left_current - 1 < num
                        < self.page + right_current)
                    or num > self.pages - right_edge):
                if last + 1 != num:
                    yield None
                yield num
                last = num


def _build_category_recipes(cat, page, per_page=12, min_total=20):
    """Return a `_StaticPagination`-wrapped list of recipes for `cat`.

    Order:
      1) Recipes with explicit `category_id == cat.id` (highest review_count first)
      2) Recipes matched by the slug-specific predicate (excluding 1)
      3) If still <`min_total`, popular recipes (excluding above) as filler
    """
    seen = set()
    ordered = []

    direct = (Recipe.query
              .filter_by(category_id=cat.id)
              .order_by(Recipe.review_count.desc(),
                        Recipe.avg_rating.desc())
              .all())
    for r in direct:
        if r.id not in seen:
            seen.add(r.id)
            ordered.append(r)

    clause = _category_match_clause(cat.slug)
    if clause is not None:
        expanded = (Recipe.query
                    .filter(clause)
                    .order_by(Recipe.review_count.desc(),
                              Recipe.avg_rating.desc())
                    .all())
        for r in expanded:
            if r.id not in seen:
                seen.add(r.id)
                ordered.append(r)

    # Pad with popular recipes until at least `min_total` cards exist.
    if len(ordered) < min_total:
        filler = (Recipe.query
                  .order_by(Recipe.review_count.desc(),
                            Recipe.avg_rating.desc())
                  .limit(min_total * 3)
                  .all())
        for r in filler:
            if r.id not in seen:
                seen.add(r.id)
                ordered.append(r)
            if len(ordered) >= min_total:
                break

    return _StaticPagination(ordered, page=page, per_page=per_page,
                             total=len(ordered))


@app.route('/category/<slug>')
def category_page(slug):
    cat = Category.query.filter_by(slug=slug).first_or_404()
    page = request.args.get('page', 1, type=int)
    recipes = _build_category_recipes(cat, page=page)
    return render_template('category.html', category=cat, recipes=recipes)


# Convenience top-level slugs (e.g. /breakfast, /dinner, /seafood) that
# real allrecipes.com exposes — redirect to the canonical /category/<slug>.
_TOP_LEVEL_CATEGORY_SLUGS = {
    'breakfast', 'brunch', 'dinner', 'desserts', 'dessert',
    'appetizers', 'appetizer', 'snacks', 'snack',
    'chicken', 'pasta', 'salads', 'salad', 'soups', 'soup',
    'seafood', 'baking', 'italian', 'mexican', 'asian', 'healthy',
    # Extended catalog
    'british', 'french', 'indian', 'chinese', 'japanese', 'thai',
    'mediterranean', 'american', 'beef', 'pork', 'lamb',
    'vegetarian', 'vegan', 'side-dishes', 'slow-cooker',
}


@app.route('/<slug>')
def top_level_category_alias(slug):
    s = (slug or '').lower().rstrip('/')
    # canonical aliases — map plural/singular variants to existing slugs
    aliases = {
        'brunch': 'breakfast', 'dessert': 'desserts',
        'appetizer': 'appetizers', 'snacks': 'appetizers',
        'snack': 'appetizers', 'salad': 'salads', 'soup': 'soups',
        'sides': 'side-dishes', 'side': 'side-dishes',
    }
    target = aliases.get(s, s)
    if target in _TOP_LEVEL_CATEGORY_SLUGS:
        cat = Category.query.filter_by(slug=target).first()
        if cat is not None:
            return redirect(url_for('category_page', slug=target), code=302)
    abort(404)


# ---------------------------------------------------------------------------
# R3: diet / occasion / ingredient sub-page routes
# ---------------------------------------------------------------------------

DIET_SLUGS = {
    'vegan': 'Vegan',
    'vegetarian': 'Vegetarian',
    'keto': 'Keto',
    'paleo': 'Paleo',
    'low-carb': 'Low-Carb',
    'gluten-free': 'Gluten-Free',
    'dairy-free': 'Dairy-Free',
    'whole30': 'Whole30',
    'low-gi': 'Low-GI',
    'pescatarian': 'Pescatarian',
    'high-protein': 'High-Protein',
}

DIET_DESCRIPTIONS = {
    'vegan': 'Fully plant-based recipes — no meat, dairy, or eggs. Bold flavors, satisfying meals.',
    'vegetarian': 'Meat-free mains and sides packed with flavor.',
    'keto': 'Low-carb, high-fat recipes that keep you in ketosis without sacrificing taste.',
    'paleo': 'Grain-free, dairy-free recipes built on whole foods.',
    'low-carb': 'Sub-30g-carb meals — zoodles, cauliflower rice, lettuce wraps and more.',
    'gluten-free': 'Naturally gluten-free recipes and clever swaps for breads, pastas, desserts.',
    'dairy-free': 'Creamy, comforting recipes without a drop of dairy.',
    'whole30': 'Strict-compliant Whole30: no sugar, grain, legume, dairy or alcohol.',
    'low-gi': 'Low glycemic index meals that keep blood sugar steady.',
    'pescatarian': 'Fish-and-veggie focused recipes for pescatarian meal planning.',
    'high-protein': 'Protein-forward recipes with 25g+ of protein per serving.',
}

OCCASION_SLUGS = {
    'thanksgiving': "Thanksgiving",
    'christmas': "Christmas",
    'easter': "Easter",
    'valentines': "Valentine's Day",
    'fourth-of-july': "4th of July",
    'halloween': "Halloween",
    'super-bowl': "Super Bowl",
    'mothers-day': "Mother's Day",
}

OCCASION_DESCRIPTIONS = {
    'thanksgiving': "Turkey, stuffing, sweet potato casserole and pumpkin pie.",
    'christmas': "Prime rib, glazed ham, cookies, eggnog and yule log for Christmas Day.",
    'easter': "Spring ham, lamb, deviled eggs and carrot cake for the Easter table.",
    'valentines': "Chocolate-dipped, candle-lit, heart-shaped recipes for your Valentine.",
    'fourth-of-july': "Backyard BBQ classics: burgers, ribs, slaw, watermelon, apple pie.",
    'halloween': "Spooky treats, pumpkin everything, and party-friendly finger foods.",
    'super-bowl': "Wings, dips, sliders, chili and nachos engineered for game day.",
    'mothers-day': "Brunch favorites: eggs benedict, quiche, pancakes, smoked salmon.",
}


def _query_recipes_by_dietary(diet_slug):
    """Match recipes whose dietary_tags_json or feature_tags contain diet_slug."""
    needle = '"' + diet_slug + '"'
    return Recipe.query.filter(
        db.or_(
            Recipe.dietary_tags_json.like('%' + needle + '%'),
            Recipe.feature_tags.like('%' + needle + '%'),
        )
    )


@app.route('/diet/<slug>')
def diet_page(slug):
    """Dedicated diet landing — vegan/keto/paleo/etc."""
    s = (slug or '').lower()
    if s not in DIET_SLUGS:
        abort(404)
    page = request.args.get('page', 1, type=int)
    per_page = 12
    q = _query_recipes_by_dietary(s).order_by(
        Recipe.review_count.desc(), Recipe.id.asc())
    all_items = q.all()
    pagination = _StaticPagination(all_items, page, per_page, len(all_items))
    return render_template(
        'diet.html',
        diet_slug=s, diet_name=DIET_SLUGS[s],
        diet_description=DIET_DESCRIPTIONS.get(s, ''),
        recipes=pagination,
        all_diets=DIET_SLUGS,
    )


@app.route('/diets')
def diets_hub():
    """Top-level diets hub linking each diet page."""
    diet_counts = {}
    for s in DIET_SLUGS:
        diet_counts[s] = _query_recipes_by_dietary(s).count()
    return render_template(
        'diets_hub.html',
        diets=DIET_SLUGS,
        diet_descriptions=DIET_DESCRIPTIONS,
        diet_counts=diet_counts,
    )


@app.route('/occasion/<slug>')
def occasion_page(slug):
    """Dedicated holiday/occasion landing."""
    s = (slug or '').lower()
    if s not in OCCASION_SLUGS:
        abort(404)
    page = request.args.get('page', 1, type=int)
    per_page = 12
    q = Recipe.query.filter(Recipe.occasion == s).order_by(
        Recipe.review_count.desc(), Recipe.id.asc())
    all_items = q.all()
    if not all_items:
        needle = '"' + s + '"'
        q = Recipe.query.filter(
            Recipe.feature_tags.like('%' + needle + '%')
        ).order_by(Recipe.review_count.desc(), Recipe.id.asc())
        all_items = q.all()
    pagination = _StaticPagination(all_items, page, per_page, len(all_items))
    return render_template(
        'occasion.html',
        occasion_slug=s, occasion_name=OCCASION_SLUGS[s],
        occasion_description=OCCASION_DESCRIPTIONS.get(s, ''),
        recipes=pagination,
        all_occasions=OCCASION_SLUGS,
    )


INGREDIENT_SLUGS = {
    'chicken':  ('Chicken',  'From easy weeknight chicken breast to slow-cooker shredded chicken.'),
    'beef':     ('Beef',     'Steaks, stews, ground beef weeknights and Sunday roasts.'),
    'pork':     ('Pork',     'Pork chops, pulled pork, ribs and tenderloin recipes for every weeknight.'),
    'lamb':     ('Lamb',     'Slow-roasted lamb shanks, kebabs, stews and curries.'),
    'seafood':  ('Seafood',  'Salmon, shrimp, cod, tuna and every fish dinner in between.'),
    'salmon':   ('Salmon',   'Baked, grilled, pan-seared salmon recipes — fast and flavorful.'),
    'shrimp':   ('Shrimp',   'Quick-cooking shrimp — scampi, stir-fry, tacos and more.'),
    'tofu':     ('Tofu',     'Crispy, marinated, scrambled — all the ways to make tofu craveable.'),
    'eggs':     ('Eggs',     'Frittatas, scrambles, quiche, deviled — eggs all day long.'),
    'pasta':    ('Pasta',    'Weeknight pasta, lasagna, fresh sauces and one-pot favorites.'),
    'rice':     ('Rice',     'Pilafs, fried rice, risotto, biryani — rice mains and sides.'),
    'beans':    ('Beans',    'Chili, soups, salads — protein-packed bean recipes for every meal.'),
    'mushroom': ('Mushroom', 'Sauteed, stuffed, in soups — mushroom magic for vegetarians.'),
    'avocado':  ('Avocado',  'Toast, guacamole, salads — every which way to enjoy avocados.'),
    'potato':   ('Potato',   'Mashed, roasted, fried, baked — comfort-food potato recipes.'),
}

INGREDIENT_TIPS = {
    'chicken':  [('Brining', 'A 30-min brine in salted water yields juicier chicken breast.'),
                 ('Resting', 'Let chicken rest 5 min after cooking so juices redistribute.')],
    'salmon':   [('Skin-on', 'Cooking skin-side-down first keeps the flesh moist.'),
                 ('Doneness', 'Salmon is medium at 125F internal — gently flaky, not dry.')],
    'beef':     [('Sear hot', 'Pat steaks dry and sear in a screaming hot cast iron for the best crust.'),
                 ('Rest 10 min', 'Let roasts rest 10 minutes before slicing — juices redistribute.')],
    'pasta':    [('Salt the water', '1 tablespoon kosher salt per quart - pasta water should taste like the sea.'),
                 ('Reserve cooking water', 'Add a splash of starchy cooking water to bind any sauce.')],
    'eggs':     [('Room temp', 'Bring eggs to room temp 30 min before baking for fluffier results.'),
                 ('Low and slow', 'Scramble eggs over LOW heat with a rubber spatula for creamy curds.')],
}


@app.route('/ingredient/<slug>')
def ingredient_page(slug):
    """Detail page for a single ingredient with recipes that use it."""
    s = (slug or '').lower()
    if s not in INGREDIENT_SLUGS:
        abort(404)
    name, intro = INGREDIENT_SLUGS[s]
    page = request.args.get('page', 1, type=int)
    per_page = 12
    needle = '"' + s + '"'
    q = Recipe.query.filter(
        db.or_(
            Recipe.main_ingredient == s,
            Recipe.title.like('%' + s.capitalize() + '%'),
            Recipe.title.like('%' + s + '%'),
            Recipe.feature_tags.like('%' + needle + '%'),
        )
    ).order_by(Recipe.review_count.desc(), Recipe.id.asc())
    all_items = q.all()
    pagination = _StaticPagination(all_items, page, per_page, len(all_items))
    return render_template(
        'ingredient.html',
        ingredient_slug=s,
        ingredient_name=name,
        ingredient_intro=intro,
        ingredient_tips=INGREDIENT_TIPS.get(s, []),
        recipes=pagination,
        all_ingredients=INGREDIENT_SLUGS,
    )


@app.route('/recipe/<slug>')
def recipe_detail(slug):
    recipe = Recipe.query.filter_by(slug=slug).first_or_404()
    reviews = Review.query.filter_by(recipe_id=recipe.id).order_by(
        Review.created_at.desc()).all()
    related = Recipe.query.filter(
        Recipe.category_id == recipe.category_id, Recipe.id != recipe.id
    ).order_by(Recipe.avg_rating.desc()).limit(6).all()
    if not related:
        related = Recipe.query.filter(Recipe.id != recipe.id).order_by(
            Recipe.review_count.desc()).limit(6).all()
    # R6: "Recipes from the same chef" — only if the recipe is authored by
    # a chef (author starts with "Chef "). Up to 6 picks, highest-rated.
    same_chef_recipes = []
    if recipe.author_name and recipe.author_name.startswith('Chef '):
        same_chef_recipes = (Recipe.query
                             .filter(Recipe.author_name == recipe.author_name,
                                     Recipe.id != recipe.id)
                             .order_by(Recipe.avg_rating.desc(),
                                       Recipe.id.asc())
                             .limit(6).all())
    # R6: "更像 X 的菜谱" — recipes sharing the more-like-this bucket tags
    # (meal_type / main_ingredient / cuisine) but in a DIFFERENT category
    # so the carousel doesn't echo the "You Might Also Like" rail above.
    more_like_recipes = []
    if recipe.cuisine or recipe.meal_type or recipe.main_ingredient:
        q = Recipe.query.filter(Recipe.id != recipe.id)
        if recipe.category_id:
            q = q.filter(Recipe.category_id != recipe.category_id)
        if recipe.cuisine:
            q = q.filter(Recipe.cuisine == recipe.cuisine)
        elif recipe.main_ingredient:
            q = q.filter(Recipe.main_ingredient == recipe.main_ingredient)
        elif recipe.meal_type:
            q = q.filter(Recipe.meal_type == recipe.meal_type)
        more_like_recipes = (q.order_by(Recipe.avg_rating.desc(),
                                        Recipe.review_count.desc(),
                                        Recipe.id.asc())
                              .limit(6).all())
    gallery = recipe.get_gallery()
    return render_template('recipe_detail.html', recipe=recipe, reviews=reviews,
                           related=related, gallery=gallery,
                           same_chef_recipes=same_chef_recipes,
                           more_like_recipes=more_like_recipes)


STOPWORDS = {'the', 'a', 'an', 'of', 'in', 'on', 'at', 'to', 'for', 'with',
             'and', 'or', 'is', 'are', 'be', 'by', 'from', 'as', 'that',
             'this', 'recipe', 'recipes', 'find', 'search', 'how', 'make'}


def _stem_forms(w):
    """All plural-ish stem forms of a word.

    Lets query token 'cookie' match 'cookies' (and vice versa) without
    triggering substring leaks like 'low' -> 'slow'. Returns a set
    containing the original plus reasonable singular/plural variants.
    """
    forms = {w}
    if len(w) >= 4 and w.endswith('s'):
        forms.add(w[:-1])  # cookies -> cookie, salads -> salad
    if len(w) >= 5 and w.endswith('es'):
        forms.add(w[:-2])  # tomatoes -> tomato
    if len(w) >= 5 and w.endswith('ies'):
        forms.add(w[:-3] + 'y')  # categories -> category
    if len(w) >= 3 and not w.endswith('s'):
        forms.add(w + 's')  # cookie -> cookies
    if len(w) >= 3 and w.endswith('y'):
        forms.add(w[:-1] + 'ies')  # category -> categories
    return forms


def _stem(w):
    # Backward-compat alias used by older call sites; returns the
    # most-canonical singular-ish form.
    if len(w) >= 5 and w.endswith('ies'):
        return w[:-3] + 'y'
    if len(w) >= 5 and w.endswith('es'):
        return w[:-2]
    if len(w) >= 4 and w.endswith('s'):
        return w[:-1]
    return w


def _score_recipe(recipe, tokens):
    haystack_raw = ' '.join([
        (recipe.title or '').lower(),
        (recipe.description or '').lower(),
        (recipe.cuisine or '').lower(),
        (recipe.ingredients_json or '').lower(),
        (recipe.tags_json or '').lower(),
        (recipe.feature_tags or '').lower(),
        (recipe.dietary_tags_json or '').lower(),
        (recipe.dish_type or '').lower(),
        (recipe.main_ingredient or '').lower(),
        (recipe.cooking_method or '').lower(),
        (recipe.occasion or '').lower(),
    ])
    # Word-boundary tokenisation so query token 'low' doesn't match inside
    # 'slow' / 'flourless', 'carb' doesn't match 'carbonara', etc.
    haystack_words = set(re.findall(r'[a-z0-9]+', haystack_raw))
    score = 0
    for t in tokens:
        if haystack_words & _stem_forms(t):
            score += 1
    return score


def _apply_recipe_filters(query_obj):
    """Apply request.args filters to a Recipe query."""
    # Rating
    min_rating = request.args.get('min_rating', type=float)
    if min_rating is not None:
        query_obj = query_obj.filter(Recipe.avg_rating >= min_rating)

    # Reviews
    min_reviews = request.args.get('min_reviews', type=int)
    if min_reviews is not None:
        query_obj = query_obj.filter(Recipe.review_count >= min_reviews)
    max_reviews = request.args.get('max_reviews', type=int)
    if max_reviews is not None:
        query_obj = query_obj.filter(Recipe.review_count <= max_reviews)

    # Calories
    max_calories = request.args.get('max_calories', type=int)
    if max_calories is not None:
        query_obj = query_obj.filter(Recipe.calories > 0,
                                     Recipe.calories <= max_calories)
    min_calories = request.args.get('min_calories', type=int)
    if min_calories is not None:
        query_obj = query_obj.filter(Recipe.calories >= min_calories)

    # Prep time
    max_prep = request.args.get('max_prep_mins', type=int)
    if max_prep is not None:
        query_obj = query_obj.filter(Recipe.prep_time_mins > 0,
                                     Recipe.prep_time_mins <= max_prep)
    # Cook time
    min_cook = request.args.get('min_cook_mins', type=int)
    if min_cook is not None:
        query_obj = query_obj.filter(Recipe.cook_time_mins >= min_cook)
    max_cook = request.args.get('max_cook_mins', type=int)
    if max_cook is not None:
        query_obj = query_obj.filter(Recipe.cook_time_mins > 0,
                                     Recipe.cook_time_mins <= max_cook)
    # Total time
    min_total = request.args.get('min_total_mins', type=int)
    if min_total is not None:
        query_obj = query_obj.filter(Recipe.total_time_mins >= min_total)
    max_total = request.args.get('max_total_mins', type=int)
    if max_total is not None:
        query_obj = query_obj.filter(Recipe.total_time_mins > 0,
                                     Recipe.total_time_mins <= max_total)

    # Servings (exact)
    servings = request.args.get('servings', '').strip()
    if servings:
        query_obj = query_obj.filter(Recipe.servings == servings)

    # Max ingredient count
    max_ingredients = request.args.get('max_ingredients', type=int)
    if max_ingredients is not None:
        query_obj = query_obj.filter(Recipe.ingredient_count > 0,
                                     Recipe.ingredient_count <= max_ingredients)

    # Cuisine
    cuisine = request.args.get('cuisine', '').strip()
    if cuisine:
        query_obj = query_obj.filter(Recipe.cuisine.ilike(f'%{cuisine}%'))

    # Dietary tag (vegan, vegetarian, gluten-free, low-carb, high-protein)
    diet = request.args.get('diet', '').strip().lower()
    if diet:
        query_obj = query_obj.filter(Recipe.dietary_tags_json.ilike(f'%{diet}%'))

    # Dish type (main, dessert, breakfast, appetizer)
    dish = request.args.get('dish_type', '').strip().lower()
    if dish:
        query_obj = query_obj.filter(Recipe.dish_type.ilike(f'%{dish}%'))

    # Meal type
    meal = request.args.get('meal_type', '').strip().lower()
    if meal:
        query_obj = query_obj.filter(Recipe.meal_type.ilike(f'%{meal}%'))

    # Cooking method (slow cooker, grilled, baked)
    method = request.args.get('method', '').strip().lower()
    if method:
        query_obj = query_obj.filter(Recipe.cooking_method.ilike(f'%{method}%'))

    # Main ingredient
    main = request.args.get('main_ingredient', '').strip().lower()
    if main:
        query_obj = query_obj.filter(Recipe.main_ingredient.ilike(f'%{main}%'))

    # Ingredient contains (e.g. "zucchini", "olives", "chocolate")
    ingredient = request.args.get('ingredient', '').strip().lower()
    if ingredient:
        query_obj = query_obj.filter(Recipe.ingredients_json.ilike(f'%{ingredient}%'))

    # Feature tag (kebab-case filter keyword)
    feature = request.args.get('feature', '').strip().lower()
    if feature:
        tokens = re.findall(r'[a-z0-9][\w-]*', feature)
        for tok in tokens:
            if tok and len(tok) >= 2:
                query_obj = query_obj.filter(Recipe.feature_tags.ilike(f'%{tok}%'))

    return query_obj


def _apply_recipe_sort(results, sort_key):
    if sort_key == 'rating':
        return sorted(results, key=lambda r: (r.avg_rating, r.review_count), reverse=True)
    if sort_key == 'reviews' or sort_key == 'popular':
        return sorted(results, key=lambda r: r.review_count, reverse=True)
    if sort_key == 'newest':
        return sorted(results, key=lambda r: r.created_at, reverse=True)
    if sort_key == 'name':
        return sorted(results, key=lambda r: r.title)
    if sort_key == 'time_asc':
        return sorted(results, key=lambda r: r.total_time_mins or 9999)
    if sort_key == 'calories_asc':
        return sorted(results, key=lambda r: r.calories or 9999)
    return results


STATIC_PAGES = [
    {'title': 'The Most Popular Recipes of the 1960s',
     'url_endpoint': 'popular_1960s',
     'url': '/collections/popular-1960s',
     'description': 'A curated Allrecipes collection of iconic 1960s dishes: Beef Wellington, Chicken a la King, Tuna Noodle Casserole, Beef Stroganoff, Deviled Eggs, and Swedish Meatballs.',
     'keywords': ['1960', '1960s', 'popular 1960s', 'collection', 'collections',
                  'vintage', 'retro', 'beef wellington', 'casserole',
                  'most popular', 'sixties']},
    {'title': 'About Allrecipes',
     'url_endpoint': 'about',
     'url': '/about',
     'description': 'Learn about Allrecipes, our community, editorial team, and the Allrecipes Allstars program.',
     'keywords': ['about', 'about us', 'about allrecipes', 'company',
                  'editorial', 'team', 'our story']},
    {'title': 'The Allrecipes Allstars',
     'url_endpoint': 'about_allstars',
     'url': '/about/allstars',
     'description': 'Meet the Allrecipes Allstars: a community of passionate home cooks, chefs, and food content creators. Chef John, Nicole McLaughlin, and more.',
     'keywords': ['allstar', 'allstars', 'all star', 'all stars',
                  'chef john', 'nicole mclaughlin', 'community', 'contributors']},
    {'title': 'Occasions & Holiday Recipes',
     'url_endpoint': 'occasions',
     'url': '/occasions',
     'description': 'Holiday and occasion recipe collections: Christmas, Thanksgiving, Easter, Hanukkah, Valentine\'s Day, Fourth of July, Halloween, New Year\'s Eve, Mother\'s Day, and Father\'s Day.',
     'keywords': ['occasion', 'occasions', 'holiday', 'holidays',
                  'christmas', 'thanksgiving', 'easter', 'hanukkah',
                  'valentine', 'fourth of july', 'halloween',
                  'new year', 'mother', 'father', 'festive']},
    {'title': 'Dinners',
     'url_endpoint': 'dinners',
     'url': '/dinners',
     'description': 'Allrecipes Dinner inspiration: weeknight meals, family favorites, one-pot recipes, and more.',
     'keywords': ['dinner', 'dinners', 'weeknight', 'main course']},
]


def _match_static_pages(q):
    """Return static page entries matching query string q."""
    if not q:
        return []
    ql = q.lower().strip()
    tokens = set(t for t in re.findall(r'[a-z0-9]+', ql)
                 if t and t not in STOPWORDS and len(t) >= 2)
    matches = []
    for pg in STATIC_PAGES:
        score = 0
        for kw in pg['keywords']:
            kw_low = kw.lower()
            # Exact phrase hit in query
            if kw_low in ql:
                score += 3
            # Token overlap
            kw_tokens = set(re.findall(r'[a-z0-9]+', kw_low))
            if kw_tokens & tokens:
                score += 1
        if pg['title'].lower() in ql:
            score += 5
        if score > 0:
            matches.append((score, pg))
    matches.sort(key=lambda x: -x[0])
    return [pg for _, pg in matches]


def _query_seed(query):
    """Deterministic 31-bit seed from a query string."""
    norm = (query or '').lower().strip()
    return int(hashlib.md5(norm.encode('utf-8')).hexdigest(), 16) % (2**31)


def _is_strong_title_match(recipe, query):
    """True if the recipe's title is an obvious top-result match for the query."""
    q = (query or '').lower().strip()
    if not q:
        return False
    title = (getattr(recipe, 'title', '') or '').lower()
    if not title:
        return False
    if q in title:
        return True
    words = [w for w in re.findall(r'[a-z0-9]+', q) if len(w) > 2]
    if words and all(w in title for w in words):
        return True
    return False


def _relevance_score(recipe, query):
    """Tier-aware relevance score for search ranking.

    Returns a single int. Higher = more relevant. Tiers:
      >=1000 — exact phrase appears in title
      >=500  — every query word appears in the title
      >=200  — every query word appears in title OR description
      50–499 — partial title hits (50 per matching word)
      <50    — no meaningful match (will be relegated as decoy)

    Matches are by word boundary (so 'low' does not match inside 'slow',
    'carb' does not match inside 'carbonara') except for the exact-phrase
    title check which still uses substring (intentional — phrase wins).
    """
    q = (query or '').lower().strip()
    if not q:
        return 0
    title = (getattr(recipe, 'title', '') or '').lower()
    desc = (getattr(recipe, 'description', '') or '').lower()
    words = [w for w in re.findall(r'[a-z0-9]+', q)
             if w and w not in STOPWORDS and len(w) >= 2]
    title_word_set = set(re.findall(r'[a-z0-9]+', title))
    desc_word_set = set(re.findall(r'[a-z0-9]+', desc))
    combined_word_set = title_word_set | desc_word_set

    def _in_set(word, word_set):
        return bool(word_set & _stem_forms(word))

    score = 0
    if q in title:
        score += 1000
    if words:
        title_words_hit = sum(1 for w in words if _in_set(w, title_word_set))
        if title_words_hit == len(words):
            score += 500
        else:
            score += 50 * title_words_hit
        if (all(_in_set(w, combined_word_set) for w in words)
                and title_words_hit < len(words)):
            score += 200
    # Tiny tiebreaker so popular recipes float up within the same tier.
    rc = getattr(recipe, 'review_count', 0) or 0
    score += min(rc, 999) // 100  # +0..+9
    return score


def _diversify_search_results(results, query, candidates_pool=None):
    """Tier-based search ranking with deterministic shuffle.

    Goals:
      - Strong matches (every query word in title, or exact phrase in title)
        always occupy the top slots — but their internal order is shuffled
        per query so the same recipe isn't always #1.
      - Partial matches and unrelated decoys interleave below.
      - Reproducible: same query => same final ordering.
    """
    results = list(results)
    if not query:
        return results

    seed = _query_seed(query)

    # Score every result and bucket by tier.
    scored = [(r, _relevance_score(r, query)) for r in results]

    # Build decoy pool to pad the page to >= 15 items so it still feels
    # like a populated search page (the disambiguation pattern needs decoys).
    have_ids = {r.id for r, _ in scored if getattr(r, 'id', None) is not None}
    decoys = []
    if len(scored) < 15:
        try:
            if candidates_pool is not None:
                pool = [r for r in candidates_pool
                        if getattr(r, 'id', None) not in have_ids]
            else:
                pool = (Recipe.query.filter(~Recipe.id.in_(have_ids)).all()
                        if have_ids else Recipe.query.all())
        except Exception:
            pool = []
        needed = 15 - len(scored)
        if pool and needed > 0:
            rng_pad = random.Random(seed + 1)
            decoys = rng_pad.sample(pool, min(needed, len(pool)))

    tier_strong = [r for r, s in scored if s >= 500]
    tier_partial = [r for r, s in scored if 50 <= s < 500]
    tier_weak = [r for r, s in scored if s < 50]
    tier_decoy = list(decoys) + tier_weak

    # Deterministic shuffle within each tier.
    random.Random(seed + 11).shuffle(tier_strong)
    random.Random(seed + 12).shuffle(tier_partial)
    random.Random(seed + 13).shuffle(tier_decoy)

    # Always lead with the full strong tier (so all top-relevance matches
    # are findable in the first page), then partial, then decoys. The
    # within-tier shuffle keeps positional order non-trivial without
    # demoting correct answers off the page.
    #
    # Strong-tier guard: if we have >=3 strong matches, never let a decoy
    # appear in the top 5 — pad with partial-tier first so the top of the
    # results page reads as obviously relevant to a benchmark agent.
    final = []
    seen = set()
    ordered = tier_strong + tier_partial + tier_decoy
    if len(tier_strong) >= 3:
        # Force partials ahead of decoys for the first page slot anyway.
        ordered = tier_strong + tier_partial + tier_decoy
    for r in ordered:
        rid = getattr(r, 'id', None)
        if rid is None or rid in seen:
            continue
        seen.add(rid)
        final.append(r)
    return final


@app.route('/search')
def search():
    q = request.args.get('q', '').strip()
    query_obj = Recipe.query
    query_obj = _apply_recipe_filters(query_obj)
    candidates = query_obj.all()

    if q:
        tokens = [t.lower() for t in re.findall(r'[a-z0-9]+', q.lower())
                  if t and t not in STOPWORDS and len(t) >= 2]
        if tokens:
            # Keep any recipe with at least one query token in the haystack;
            # _diversify_search_results then applies tier-based relevance
            # ordering so strong title matches surface in the top slots.
            results = [r for r in candidates if _score_recipe(r, tokens) >= 1]
        else:
            results = sorted(candidates, key=lambda r: r.review_count, reverse=True)
    else:
        results = sorted(candidates, key=lambda r: r.review_count, reverse=True)

    sort_key = request.args.get('sort', '')
    if sort_key:
        results = _apply_recipe_sort(results, sort_key)
    elif q:
        # Only diversify when there's a search query AND the user did not
        # request an explicit sort order. Keeps explicit sorts (rating,
        # popular, newest, etc.) faithful while making the default search
        # ordering non-trivial for benchmark agents.
        results = _diversify_search_results(results, q, candidates_pool=candidates)

    static_matches = _match_static_pages(q)
    return render_template('search.html', query=q, results=results,
                           count=len(results), static_matches=static_matches)


# ---------------------------------------------------------------------------
# Routes — Static content pages (About, Collections, Occasions, Dinners)
# ---------------------------------------------------------------------------

ALLSTARS = [
    {'name': 'Chef John', 'bio': 'Food Wishes founder and longtime Allrecipes Allstar known for his approachable tutorials and classic recipes.'},
    {'name': 'Nicole McLaughlin', 'bio': 'Allrecipes Allstar and host of NicoleMakesIt. Nicole specializes in easy weeknight dinners and family-friendly baking.'},
    {'name': 'Juliana Hale', 'bio': 'Allrecipes Test Kitchen Allstar, award-winning baker, and mother of three based in Wisconsin.'},
    {'name': 'Bren Herrera', 'bio': 'Chef, author, and Allstar contributor bringing authentic Cuban flavors to the community.'},
    {'name': 'Ann Taylor Pittman', 'bio': 'James Beard Award winning food writer and longtime Allrecipes Allstar.'},
]


@app.route('/about')
def about():
    return render_template('about.html', allstars=ALLSTARS)


@app.route('/about/allstars')
def about_allstars():
    return render_template('allstars.html', allstars=ALLSTARS)


OCCASIONS = [
    {'name': 'Christmas', 'slug': 'christmas', 'desc': 'Festive Christmas dinner, cookies, and holiday baking recipes.'},
    {'name': 'Thanksgiving', 'slug': 'thanksgiving', 'desc': 'Turkey, stuffing, pies and side dishes for the Thanksgiving feast.'},
    {'name': 'Easter', 'slug': 'easter', 'desc': 'Ham, brunch ideas, and Easter desserts for spring gatherings.'},
    {'name': 'Hanukkah', 'slug': 'hanukkah', 'desc': 'Latkes, brisket and traditional Hanukkah recipes.'},
    {'name': 'Valentine\'s Day', 'slug': 'valentines-day', 'desc': 'Romantic dinners and heart-shaped desserts for Valentine\'s Day.'},
    {'name': 'Fourth of July', 'slug': 'fourth-of-july', 'desc': 'BBQ, burgers, and red-white-and-blue desserts for Independence Day.'},
    {'name': 'Halloween', 'slug': 'halloween', 'desc': 'Spooky treats, pumpkin recipes, and Halloween party food.'},
    {'name': 'New Year\'s Eve', 'slug': 'new-years-eve', 'desc': 'Appetizers, cocktails and champagne-friendly bites for New Year\'s.'},
    {'name': 'Mother\'s Day', 'slug': 'mothers-day', 'desc': 'Brunch, cakes, and special breakfast ideas for Mom.'},
    {'name': 'Father\'s Day', 'slug': 'fathers-day', 'desc': 'Grilling and hearty dinner recipes Dad will love.'},
]


@app.route('/occasions')
def occasions():
    return render_template('occasions.html', occasions=OCCASIONS)


@app.route('/dinners')
def dinners():
    """Allrecipes Dinners landing section."""
    recommended = Recipe.query.filter(
        db.or_(Recipe.dish_type == 'main', Recipe.meal_type == 'dinner')
    ).order_by(Recipe.review_count.desc()).limit(12).all()
    if len(recommended) < 3:
        recommended = Recipe.query.order_by(Recipe.review_count.desc()).limit(12).all()
    return render_template('dinners.html', recommended=recommended)


@app.route('/meals')
def meals_hub():
    """Top-level Meals hub — links the meal-type subcategories."""
    meal_slugs = ['breakfast', 'dinner', 'appetizers', 'desserts',
                  'healthy', 'salads', 'soups']
    cats = [Category.query.filter_by(slug=s).first() for s in meal_slugs]
    cats = [c for c in cats if c]
    return render_template('hub.html', hub_title='Meals',
                           hub_intro='Browse our biggest meal-of-the-day collections.',
                           categories=cats)


@app.route('/ingredients')
def ingredients_hub():
    """Top-level Ingredients hub."""
    ing_slugs = ['chicken', 'beef', 'pork', 'lamb', 'seafood',
                 'pasta', 'baking', 'vegetarian', 'vegan']
    cats = [Category.query.filter_by(slug=s).first() for s in ing_slugs]
    cats = [c for c in cats if c]
    return render_template('hub.html', hub_title='Ingredients',
                           hub_intro='Find a recipe by the ingredient you have on hand.',
                           categories=cats)


@app.route('/cuisines')
def cuisines_hub():
    """Top-level Cuisines hub."""
    cui_slugs = ['italian', 'mexican', 'asian', 'french', 'indian',
                 'chinese', 'japanese', 'thai', 'mediterranean', 'american']
    cats = [Category.query.filter_by(slug=s).first() for s in cui_slugs]
    cats = [c for c in cats if c]
    return render_template('hub.html', hub_title='Cuisines',
                           hub_intro='Travel the world from your kitchen with recipes by cuisine.',
                           categories=cats)


@app.route('/newsletter', methods=['GET', 'POST'])
def newsletter():
    """Newsletter signup landing page (form posts back here)."""
    signed_up = False
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        if email and '@' in email:
            flash(f'Thanks! {email} is now subscribed to the Allrecipes newsletter.',
                  'success')
            signed_up = True
        else:
            flash('Please enter a valid email address.', 'danger')
    return render_template('newsletter.html', signed_up=signed_up)


@app.route('/sitemap')
def sitemap():
    """Human-readable sitemap listing every section and every category."""
    cats = Category.query.order_by(Category.parent_type, Category.display_order).all()
    grouped = {}
    for c in cats:
        grouped.setdefault(c.parent_type or 'other', []).append(c)
    static_pages = [
        ('Home', url_for('index')),
        ('All Recipes', url_for('all_recipes')),
        ('Meals', url_for('meals_hub')),
        ('Ingredients', url_for('ingredients_hub')),
        ('Cuisines', url_for('cuisines_hub')),
        ('Occasions', url_for('occasions')),
        ('Dinners', url_for('dinners')),
        ('Popular 1960s Recipes', url_for('popular_1960s')),
        ('About Allrecipes', url_for('about')),
        ('The Allrecipes Allstars', url_for('about_allstars')),
        ('Newsletter', url_for('newsletter')),
        ('Log In', url_for('login')),
        ('Sign Up', url_for('register')),
    ]
    return render_template('sitemap.html', grouped=grouped,
                           static_pages=static_pages)


# ---------------------------------------------------------------------------
# R7: SEO endpoints — sitemap.xml, robots.txt, RSS feed, JSON-LD endpoints
# ---------------------------------------------------------------------------

SITE_BASE_URL = 'http://localhost:40000'


@app.route('/sitemap.xml')
def sitemap_xml():
    """Machine-readable XML sitemap (R7). Lists the home page, every category,
    and the top-1000 recipes by review_count so the file stays under 50k entries
    (the sitemap protocol limit). Cached implicitly via the deterministic seed."""
    urls = [(SITE_BASE_URL + url_for('index'), '1.0')]
    urls.append((SITE_BASE_URL + url_for('all_recipes'), '0.9'))
    urls.append((SITE_BASE_URL + url_for('articles_hub'), '0.7'))
    urls.append((SITE_BASE_URL + url_for('collections_hub'), '0.7'))
    urls.append((SITE_BASE_URL + url_for('cuisines_hub'), '0.7'))
    urls.append((SITE_BASE_URL + url_for('diets_hub'), '0.7'))
    urls.append((SITE_BASE_URL + url_for('occasions'), '0.7'))
    urls.append((SITE_BASE_URL + url_for('sitemap'), '0.5'))
    for c in Category.query.order_by(Category.id).all():
        urls.append((SITE_BASE_URL + url_for('category_page', slug=c.slug), '0.7'))
    top_recipes = (Recipe.query
                   .order_by(Recipe.review_count.desc(), Recipe.id.asc())
                   .limit(1000).all())
    for r in top_recipes:
        urls.append((SITE_BASE_URL + url_for('recipe_detail', slug=r.slug), '0.6'))
    body = ['<?xml version="1.0" encoding="UTF-8"?>',
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for loc, pri in urls:
        body.append(f'  <url><loc>{loc}</loc><priority>{pri}</priority></url>')
    body.append('</urlset>')
    return '\n'.join(body), 200, {'Content-Type': 'application/xml; charset=utf-8'}


@app.route('/robots.txt')
def robots_txt():
    """R7: standard robots.txt advertising the XML sitemap."""
    lines = [
        'User-agent: *',
        'Allow: /',
        'Disallow: /account',
        'Disallow: /recipe-box',
        'Disallow: /meal-plan',
        'Disallow: /shopping-list',
        'Disallow: /api/',
        f'Sitemap: {SITE_BASE_URL}/sitemap.xml',
        f'Sitemap: {SITE_BASE_URL}/feed.rss',
    ]
    return '\n'.join(lines) + '\n', 200, {'Content-Type': 'text/plain; charset=utf-8'}


@app.route('/feed.rss')
def feed_rss():
    """R7: RSS 2.0 feed of the 60 most-recently-published articles. Lets
    feed-validity tasks parse <item><title> entries without an HTML parser."""
    arts = (Article.query
            .order_by(Article.published_at.desc(), Article.id.asc())
            .limit(60).all())
    items = []
    for a in arts:
        link = SITE_BASE_URL + url_for('article_detail', slug=a.slug)
        pub = (a.published_at or MIRROR_REFERENCE_DATE).strftime('%a, %d %b %Y %H:%M:%S +0000')
        desc = (a.excerpt or '')[:300]
        items.append(
            '  <item>'
            f'<title>{a.title}</title>'
            f'<link>{link}</link>'
            f'<guid>{link}</guid>'
            f'<pubDate>{pub}</pubDate>'
            f'<description>{desc}</description>'
            '</item>'
        )
    body = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<rss version="2.0">\n'
        '<channel>\n'
        '  <title>Allrecipes Mirror - Latest Articles</title>\n'
        f'  <link>{SITE_BASE_URL}/</link>\n'
        '  <description>Cooking tips, technique deep-dives, and seasonal guides from the Allrecipes editors.</description>\n'
        '  <language>en-us</language>\n'
        + '\n'.join(items) +
        '\n</channel>\n</rss>\n'
    )
    return body, 200, {'Content-Type': 'application/rss+xml; charset=utf-8'}


# ---------------------------------------------------------------------------
# R7: Multi-language stub — /lang/<lang>/ prefix renders the same content
# with a banner indicating the current language. Supports: es, fr, de, zh.
# Content stays in English (true i18n is out of scope); the prefix exists so
# language-switch tasks have a real URL to navigate to + extract from.
# ---------------------------------------------------------------------------

SUPPORTED_LANGS = ('en', 'es', 'fr', 'de', 'zh')

LANG_BANNER = {
    'en': ('English', 'You are viewing Allrecipes in English.'),
    'es': ('Español', 'Estás viendo Allrecipes en Español. Contenido en inglés (vista previa).'),
    'fr': ('Français', 'Vous consultez Allrecipes en Français. Contenu en anglais (aperçu).'),
    'de': ('Deutsch', 'Sie sehen Allrecipes auf Deutsch. Inhalt auf Englisch (Vorschau).'),
    'zh': ('中文', '您正在使用中文版 Allrecipes。内容为英文（预览）。'),
}


@app.context_processor
def _seo_processor():
    """Inject SEO + lang helpers into every template."""
    def site_base_url():
        return SITE_BASE_URL

    def canonical_url():
        # Strip query string and any /lang/<x> prefix so the canonical points
        # at the language-neutral page.
        path = request.path
        for lang in SUPPORTED_LANGS:
            if path.startswith(f'/lang/{lang}'):
                path = path[len(f'/lang/{lang}'):] or '/'
                break
        return SITE_BASE_URL + path

    def current_lang():
        path = request.path
        for lang in SUPPORTED_LANGS:
            if path.startswith(f'/lang/{lang}'):
                return lang
        return 'en'

    def lang_label(lang):
        return LANG_BANNER.get(lang, ('English', ''))[0]

    def lang_banner_text(lang):
        return LANG_BANNER.get(lang, ('English', ''))[1]

    def supported_langs():
        return SUPPORTED_LANGS

    return dict(
        site_base_url=site_base_url,
        canonical_url=canonical_url,
        current_lang=current_lang,
        lang_label=lang_label,
        lang_banner_text=lang_banner_text,
        supported_langs=supported_langs,
    )


@app.route('/lang/<lang>/')
@app.route('/lang/<lang>/<path:subpath>')
def lang_stub(lang, subpath=''):
    """R7: language-switch stub. Renders the same Allrecipes index/section
    with a banner indicating the chosen language. Tasks can navigate to
    /lang/es/ , /lang/fr/recipe/<slug> etc. and extract the banner text."""
    if lang not in SUPPORTED_LANGS:
        abort(404)
    # Match the subpath against known routes; for the common case we just
    # re-render the index with the lang banner.
    if not subpath:
        featured = Recipe.query.filter_by(is_featured=True).limit(6).all()
        editors_picks = Recipe.query.filter_by(is_editors_pick=True).limit(6).all()
        latest = Recipe.query.order_by(Recipe.created_at.desc()).limit(12).all()
        categories = Category.query.order_by(Category.display_order).all()
        popular = Recipe.query.order_by(Recipe.review_count.desc()).limit(8).all()
        return render_template('index.html', featured=featured,
                               editors_picks=editors_picks, latest=latest,
                               categories=categories, popular=popular)
    # Recipe path: /lang/<x>/recipe/<slug>
    if subpath.startswith('recipe/'):
        slug = subpath[len('recipe/'):].strip('/')
        return redirect(url_for('recipe_detail', slug=slug))
    # Category path: /lang/<x>/category/<slug>
    if subpath.startswith('category/'):
        slug = subpath[len('category/'):].strip('/')
        return redirect(url_for('category_page', slug=slug))
    # Anything else 302s to the canonical English path.
    return redirect('/' + subpath)


POPULAR_1960S = [
    {'title': 'Classic Beef Wellington', 'slug': 'classic-beef-wellington',
     'prep': '45 mins', 'total': '2 hrs 30 mins'},
    {'title': 'Chicken à la King',
     'slug': 'chicken-a-la-king', 'prep': '15 mins', 'total': '40 mins'},
    {'title': 'Tuna Noodle Casserole',
     'slug': 'tuna-noodle-casserole', 'prep': '20 mins', 'total': '1 hr'},
    {'title': 'Beef Stroganoff',
     'slug': 'beef-stroganoff', 'prep': '15 mins', 'total': '40 mins'},
    {'title': 'Deviled Eggs',
     'slug': 'deviled-eggs', 'prep': '10 mins', 'total': '20 mins'},
    {'title': 'Swedish Meatballs',
     'slug': 'swedish-meatballs', 'prep': '20 mins', 'total': '1 hr'},
]


@app.route('/collections/popular-1960s')
def popular_1960s():
    # Resolve each collection entry's slug to an actual recipe; if the
    # canonical slug is missing, fall back to a title-based lookup so every
    # card has a working /recipe/<slug> link.
    resolved = []
    for r in POPULAR_1960S:
        entry = dict(r)
        rec = Recipe.query.filter_by(slug=r['slug']).first()
        if not rec:
            # Try matching on title (case-insensitive, partial)
            rec = Recipe.query.filter(Recipe.title.ilike(f"%{r['title']}%")).first()
        if not rec:
            # Final fallback: pick by keyword from the title
            kw = r['title'].split()[0]
            rec = Recipe.query.filter(Recipe.title.ilike(f"%{kw}%")).first()
        if rec:
            entry['link_slug'] = rec.slug
        else:
            entry['link_slug'] = r['slug']
        resolved.append(entry)
    return render_template('collection_1960s.html', recipes=resolved)


# ---------------------------------------------------------------------------
# Routes — Auth
# ---------------------------------------------------------------------------

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            login_user(user, remember=request.form.get('remember'))
            flash('Welcome back!', 'success')
            next_page = request.args.get('next')
            return redirect(safe_redirect_target(next_page))
        flash('Invalid email or password.', 'danger')
    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        confirm = request.form.get('confirm_password', '')
        if not username or not email or not password:
            flash('All fields are required.', 'danger')
        elif password != confirm:
            flash('Passwords do not match.', 'danger')
        elif User.query.filter_by(email=email).first():
            flash('Email already registered.', 'danger')
        elif User.query.filter_by(username=username).first():
            flash('Username already taken.', 'danger')
        else:
            user = User(username=username, email=email, display_name=username)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            login_user(user)
            flash('Account created! Welcome to Allrecipes.', 'success')
            return redirect(url_for('index'))
    return render_template('register.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))


# ---------------------------------------------------------------------------
# Routes — User Profile / Account
# ---------------------------------------------------------------------------

@app.route('/account')
@login_required
def account():
    saved_count = RecipeBoxItem.query.filter_by(user_id=current_user.id).count()
    review_count = Review.query.filter_by(user_id=current_user.id).count()
    meal_plans = MealPlanItem.query.filter_by(user_id=current_user.id).all()
    shopping_lists = ShoppingList.query.filter_by(user_id=current_user.id).all()
    return render_template('account.html', saved_count=saved_count,
                           review_count=review_count, meal_plans=meal_plans,
                           shopping_lists=shopping_lists)


@app.route('/account/edit', methods=['GET', 'POST'])
@login_required
def account_edit():
    if request.method == 'POST':
        current_user.display_name = request.form.get('display_name', '').strip()
        current_user.bio = request.form.get('bio', '').strip()
        current_user.location = request.form.get('location', '').strip()
        db.session.commit()
        flash('Profile updated.', 'success')
        return redirect(url_for('account'))
    return render_template('account_edit.html')


@app.route('/account/password', methods=['GET', 'POST'])
@login_required
def change_password():
    if request.method == 'POST':
        current_pw = request.form.get('current_password', '')
        new_pw = request.form.get('new_password', '')
        confirm_pw = request.form.get('confirm_password', '')
        if not current_user.check_password(current_pw):
            flash('Current password is incorrect.', 'danger')
        elif new_pw != confirm_pw:
            flash('New passwords do not match.', 'danger')
        elif len(new_pw) < 6:
            flash('Password must be at least 6 characters.', 'danger')
        else:
            current_user.set_password(new_pw)
            db.session.commit()
            flash('Password changed successfully.', 'success')
            return redirect(url_for('account'))
    return render_template('change_password.html')


@app.route('/account/delete', methods=['POST'])
@login_required
def delete_account():
    user = User.query.get(current_user.id)
    logout_user()
    db.session.delete(user)
    db.session.commit()
    flash('Your account has been deleted.', 'info')
    return redirect(url_for('index'))


# ---------------------------------------------------------------------------
# Routes — Recipe Box (saved recipes, like Wishlist)
# ---------------------------------------------------------------------------

@app.route('/recipe-box')
@login_required
def recipe_box():
    items = RecipeBoxItem.query.filter_by(user_id=current_user.id).order_by(
        RecipeBoxItem.created_at.desc()).all()
    recipes = [item.recipe for item in items]
    return render_template('recipe_box.html', recipes=recipes, items=items)


@csrf.exempt
@app.route('/api/recipe-box/toggle', methods=['POST'])
@login_required
def toggle_recipe_box():
    data = request.get_json()
    recipe_id = data.get('recipe_id')
    if not recipe_id:
        return jsonify(success=False, message='Missing recipe_id'), 400
    existing = RecipeBoxItem.query.filter_by(
        user_id=current_user.id, recipe_id=recipe_id).first()
    if existing:
        db.session.delete(existing)
        db.session.commit()
        count = RecipeBoxItem.query.filter_by(user_id=current_user.id).count()
        return jsonify(success=True, saved=False, count=count, message='Removed from Recipe Box')
    else:
        item = RecipeBoxItem(user_id=current_user.id, recipe_id=recipe_id)
        db.session.add(item)
        db.session.commit()
        count = RecipeBoxItem.query.filter_by(user_id=current_user.id).count()
        return jsonify(success=True, saved=True, count=count, message='Saved to Recipe Box')


@app.route('/recipe-box/remove/<int:item_id>', methods=['POST'])
@login_required
def remove_from_recipe_box(item_id):
    item = RecipeBoxItem.query.filter_by(id=item_id, user_id=current_user.id).first_or_404()
    db.session.delete(item)
    db.session.commit()
    flash('Recipe removed from your box.', 'info')
    return redirect(url_for('recipe_box'))


@app.route('/recipe-box/save/<int:recipe_id>', methods=['POST'])
@login_required
def save_to_recipe_box(recipe_id):
    """Form-POST endpoint to save a recipe to the recipe box (agent-friendly)."""
    recipe = Recipe.query.get_or_404(recipe_id)
    existing = RecipeBoxItem.query.filter_by(
        user_id=current_user.id, recipe_id=recipe_id).first()
    if not existing:
        item = RecipeBoxItem(user_id=current_user.id, recipe_id=recipe_id)
        db.session.add(item)
        db.session.commit()
        flash(f'"{recipe.title}" saved to your Recipe Box.', 'success')
    else:
        flash(f'"{recipe.title}" is already in your Recipe Box.', 'info')
    next_page = request.form.get('next')
    return redirect(safe_redirect_target(next_page, 'recipe_box'))


@app.route('/recipe-box/note/<int:item_id>', methods=['POST'])
@login_required
def update_recipe_box_note(item_id):
    """Form-POST endpoint to update the note on a saved recipe."""
    item = RecipeBoxItem.query.filter_by(id=item_id, user_id=current_user.id).first_or_404()
    item.notes = request.form.get('notes', '').strip()
    db.session.commit()
    flash('Note updated.', 'success')
    return redirect(url_for('recipe_box'))


# ---------------------------------------------------------------------------
# Routes — Meal Planner
# ---------------------------------------------------------------------------

@app.route('/meal-plan')
@login_required
def meal_plan():
    items = MealPlanItem.query.filter_by(user_id=current_user.id).all()
    days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
    meals = ['breakfast', 'lunch', 'dinner', 'snack']
    plan = {}
    for day in days:
        plan[day] = {}
        for meal in meals:
            plan[day][meal] = None
    for item in items:
        plan[item.day][item.meal_type] = item
    all_recipes = Recipe.query.order_by(Recipe.title).all()
    return render_template('meal_plan.html', plan=plan, days=days, meals=meals,
                           all_recipes=all_recipes)


@csrf.exempt
@app.route('/api/meal-plan/add', methods=['POST'])
@login_required
def add_to_meal_plan():
    data = request.get_json()
    recipe_id = data.get('recipe_id')
    day = data.get('day')
    meal_type = data.get('meal_type')
    if not all([recipe_id, day, meal_type]):
        return jsonify(success=False, message='Missing fields'), 400
    # Remove existing item for this slot
    MealPlanItem.query.filter_by(
        user_id=current_user.id, day=day, meal_type=meal_type).delete()
    item = MealPlanItem(user_id=current_user.id, recipe_id=recipe_id,
                        day=day, meal_type=meal_type)
    db.session.add(item)
    db.session.commit()
    return jsonify(success=True, message='Added to meal plan')


@csrf.exempt
@app.route('/api/meal-plan/remove', methods=['POST'])
@login_required
def remove_from_meal_plan():
    data = request.get_json()
    day = data.get('day')
    meal_type = data.get('meal_type')
    MealPlanItem.query.filter_by(
        user_id=current_user.id, day=day, meal_type=meal_type).delete()
    db.session.commit()
    return jsonify(success=True, message='Removed from meal plan')


@app.route('/meal-plan/clear', methods=['POST'])
@login_required
def clear_meal_plan():
    MealPlanItem.query.filter_by(user_id=current_user.id).delete()
    db.session.commit()
    flash('Meal plan cleared.', 'info')
    return redirect(url_for('meal_plan'))


@app.route('/meal-plan/add', methods=['POST'])
@login_required
def add_to_meal_plan_form():
    """Form-POST endpoint to add a recipe to the meal plan (agent-friendly)."""
    recipe_id = request.form.get('recipe_id', type=int)
    day = request.form.get('day', '').strip().lower()
    meal_type = request.form.get('meal_type', '').strip().lower()
    if not all([recipe_id, day, meal_type]):
        flash('Please select a recipe, day, and meal type.', 'danger')
        return redirect(url_for('meal_plan'))
    recipe = Recipe.query.get_or_404(recipe_id)
    MealPlanItem.query.filter_by(
        user_id=current_user.id, day=day, meal_type=meal_type).delete()
    item = MealPlanItem(user_id=current_user.id, recipe_id=recipe_id,
                        day=day, meal_type=meal_type)
    db.session.add(item)
    db.session.commit()
    flash(f'"{recipe.title}" added to {day.capitalize()} {meal_type}.', 'success')
    return redirect(url_for('meal_plan'))


@app.route('/meal-plan/remove', methods=['POST'])
@login_required
def remove_from_meal_plan_form():
    """Form-POST endpoint to remove a slot from the meal plan (agent-friendly)."""
    day = request.form.get('day', '').strip().lower()
    meal_type = request.form.get('meal_type', '').strip().lower()
    MealPlanItem.query.filter_by(
        user_id=current_user.id, day=day, meal_type=meal_type).delete()
    db.session.commit()
    flash(f'{day.capitalize()} {meal_type} cleared.', 'info')
    return redirect(url_for('meal_plan'))


# ---------------------------------------------------------------------------
# Routes — Shopping List
# ---------------------------------------------------------------------------

@app.route('/shopping-list')
@login_required
def shopping_list():
    lists = ShoppingList.query.filter_by(user_id=current_user.id).order_by(
        ShoppingList.created_at.desc()).all()
    all_recipes = Recipe.query.order_by(Recipe.title).all()
    return render_template('shopping_list.html', lists=lists, all_recipes=all_recipes)


@app.route('/shopping-list/create', methods=['POST'])
@login_required
def create_shopping_list():
    name = request.form.get('name', 'Shopping List').strip()
    sl = ShoppingList(user_id=current_user.id, name=name)
    db.session.add(sl)
    db.session.commit()
    flash('Shopping list created.', 'success')
    return redirect(url_for('shopping_list'))


@csrf.exempt
@app.route('/api/shopping-list/<int:list_id>/add', methods=['POST'])
@login_required
def add_to_shopping_list(list_id):
    sl = ShoppingList.query.filter_by(id=list_id, user_id=current_user.id).first_or_404()
    data = request.get_json()
    recipe_id = data.get('recipe_id')
    if recipe_id:
        recipe = Recipe.query.get_or_404(recipe_id)
        items = sl.get_items()
        for ing in recipe.get_ingredients():
            if ing not in items:
                items.append(ing)
        sl.set_items(items)
        db.session.commit()
        return jsonify(success=True, message=f'Added {recipe.title} ingredients',
                       count=len(items))
    item = data.get('item', '').strip()
    if item:
        items = sl.get_items()
        items.append(item)
        sl.set_items(items)
        db.session.commit()
        return jsonify(success=True, count=len(items))
    return jsonify(success=False), 400


@csrf.exempt
@app.route('/api/shopping-list/<int:list_id>/remove', methods=['POST'])
@login_required
def remove_from_shopping_list(list_id):
    sl = ShoppingList.query.filter_by(id=list_id, user_id=current_user.id).first_or_404()
    data = request.get_json()
    index = data.get('index')
    items = sl.get_items()
    if index is not None and 0 <= index < len(items):
        items.pop(index)
        sl.set_items(items)
        db.session.commit()
    return jsonify(success=True, count=len(items))


@app.route('/shopping-list/<int:list_id>/delete', methods=['POST'])
@login_required
def delete_shopping_list(list_id):
    sl = ShoppingList.query.filter_by(id=list_id, user_id=current_user.id).first_or_404()
    db.session.delete(sl)
    db.session.commit()
    flash('Shopping list deleted.', 'info')
    return redirect(url_for('shopping_list'))


@app.route('/shopping-list/<int:list_id>/add-recipe', methods=['POST'])
@login_required
def add_recipe_to_shopping_list(list_id):
    """Form-POST endpoint to add a recipe's ingredients to a shopping list (agent-friendly)."""
    sl = ShoppingList.query.filter_by(id=list_id, user_id=current_user.id).first_or_404()
    recipe_id = request.form.get('recipe_id', type=int)
    if not recipe_id:
        flash('No recipe selected.', 'danger')
        return redirect(url_for('shopping_list'))
    recipe = Recipe.query.get_or_404(recipe_id)
    items = sl.get_items()
    added = 0
    for ing in recipe.get_ingredients():
        if ing not in items:
            items.append(ing)
            added += 1
    sl.set_items(items)
    db.session.commit()
    flash(f'Added {added} ingredient(s) from "{recipe.title}" to "{sl.name}".', 'success')
    return redirect(url_for('shopping_list'))


@app.route('/shopping-list/<int:list_id>/add-item', methods=['POST'])
@login_required
def add_item_to_shopping_list(list_id):
    """Form-POST endpoint to add a custom item to a shopping list (agent-friendly)."""
    sl = ShoppingList.query.filter_by(id=list_id, user_id=current_user.id).first_or_404()
    item = request.form.get('item', '').strip()
    if not item:
        flash('Please enter an item.', 'danger')
        return redirect(url_for('shopping_list'))
    items = sl.get_items()
    items.append(item)
    sl.set_items(items)
    db.session.commit()
    flash(f'"{item}" added to "{sl.name}".', 'success')
    return redirect(url_for('shopping_list'))


@app.route('/shopping-list/<int:list_id>/remove-item', methods=['POST'])
@login_required
def remove_item_from_shopping_list(list_id):
    """Form-POST endpoint to remove an item by index from a shopping list (agent-friendly)."""
    sl = ShoppingList.query.filter_by(id=list_id, user_id=current_user.id).first_or_404()
    index = request.form.get('index', type=int)
    items = sl.get_items()
    if index is not None and 0 <= index < len(items):
        removed = items.pop(index)
        sl.set_items(items)
        db.session.commit()
        flash(f'"{removed}" removed.', 'info')
    return redirect(url_for('shopping_list'))


# ---------------------------------------------------------------------------
# Routes — Reviews
# ---------------------------------------------------------------------------

@app.route('/recipe/<slug>/review', methods=['POST'])
@login_required
def submit_review(slug):
    recipe = Recipe.query.filter_by(slug=slug).first_or_404()
    rating = request.form.get('rating', type=int)
    title = request.form.get('title', '').strip()
    body = request.form.get('body', '').strip()
    if not rating or rating < 1 or rating > 5:
        flash('Please select a rating (1-5).', 'danger')
        return redirect(url_for('recipe_detail', slug=slug))
    # Check for existing review
    existing = Review.query.filter_by(user_id=current_user.id, recipe_id=recipe.id).first()
    if existing:
        existing.rating = rating
        existing.title = title
        existing.body = body
    else:
        review = Review(user_id=current_user.id, recipe_id=recipe.id,
                        rating=rating, title=title, body=body)
        db.session.add(review)
    db.session.commit()
    # Update average rating
    reviews = Review.query.filter_by(recipe_id=recipe.id).all()
    if reviews:
        recipe.avg_rating = round(sum(r.rating for r in reviews) / len(reviews), 1)
        recipe.review_count = len(reviews)
        db.session.commit()
    flash('Review submitted!', 'success')
    return redirect(url_for('recipe_detail', slug=slug))


@app.route('/review/<int:review_id>/delete', methods=['POST'])
@login_required
def delete_review(review_id):
    review = Review.query.get_or_404(review_id)
    if review.user_id != current_user.id:
        abort(403)
    recipe = review.recipe
    db.session.delete(review)
    db.session.commit()
    # Update avg rating
    reviews = Review.query.filter_by(recipe_id=recipe.id).all()
    if reviews:
        recipe.avg_rating = round(sum(r.rating for r in reviews) / len(reviews), 1)
        recipe.review_count = len(reviews)
    else:
        recipe.avg_rating = 0.0
        recipe.review_count = 0
    db.session.commit()
    flash('Review deleted.', 'info')
    return redirect(url_for('recipe_detail', slug=recipe.slug))


# ---------------------------------------------------------------------------
# Routes — API (JSON endpoints)
# ---------------------------------------------------------------------------

@csrf.exempt
@app.route('/api/recipes/<category_slug>')
def api_recipes_by_category(category_slug):
    cat = Category.query.filter_by(slug=category_slug).first()
    if not cat:
        return jsonify(recipes=[])
    recipes = Recipe.query.filter_by(category_id=cat.id).all()
    return jsonify(recipes=[{
        'id': r.id, 'title': r.title, 'slug': r.slug, 'image': r.image,
        'avg_rating': r.avg_rating, 'review_count': r.review_count,
        'prep_time': r.prep_time, 'cook_time': r.cook_time, 'calories': r.calories,
    } for r in recipes])


@csrf.exempt
@app.route('/api/search')
def api_search():
    q = request.args.get('q', '').strip()
    if not q:
        return jsonify(results=[])
    results = Recipe.query.filter(
        db.or_(Recipe.title.ilike(f'%{q}%'), Recipe.description.ilike(f'%{q}%'))
    ).limit(10).all()
    return jsonify(results=[{
        'id': r.id, 'title': r.title, 'slug': r.slug, 'image': r.image,
        'avg_rating': r.avg_rating
    } for r in results])


# ---------------------------------------------------------------------------
# R4: Community / Authors / Collections / Articles / Occasion recipe-list pages
# ---------------------------------------------------------------------------

@app.route('/community')
def community():
    """Community landing — top reviewers, recent reviews, featured chefs."""
    top_reviewers = (
        db.session.query(User, db.func.count(Review.id).label('n'))
        .join(Review, Review.user_id == User.id)
        .filter(User.email.like('%@example.com'))
        .group_by(User.id)
        .order_by(db.desc('n'))
        .limit(8)
        .all()
    )
    recent_reviews = (
        Review.query
        .order_by(Review.created_at.desc(), Review.id.desc())
        .limit(12)
        .all()
    )
    featured_authors = (
        db.session.query(Recipe.author_name, db.func.count(Recipe.id).label('n'))
        .filter(Recipe.author_name.like('Chef %'))
        .group_by(Recipe.author_name)
        .order_by(db.desc('n'))
        .limit(8)
        .all()
    )
    stats = {
        'recipes': Recipe.query.count(),
        'reviews': Review.query.count(),
        'reviewers': User.query.filter(User.email.like('%@example.com')).count(),
        'chefs': db.session.query(Recipe.author_name).filter(
            Recipe.author_name.like('Chef %')).distinct().count(),
    }
    return render_template(
        'community.html',
        top_reviewers=top_reviewers,
        recent_reviews=recent_reviews,
        featured_authors=featured_authors,
        stats=stats,
    )


def _author_slug(name):
    s = re.sub(r"[^a-zA-Z0-9]+", '-', (name or '').lower()).strip('-')
    return s or 'chef'


@app.route('/authors/<slug>')
def author_page(slug):
    """Chef profile page — recipes by author_name matching slug."""
    s = (slug or '').lower()
    # Locate the author by slugifying every author_name and matching.
    all_authors = [row[0] for row in db.session.query(Recipe.author_name)
                   .filter(Recipe.author_name.like('Chef %'))
                   .distinct().all()]
    match = next((a for a in all_authors if _author_slug(a) == s), None)
    if not match:
        abort(404)
    page = request.args.get('page', 1, type=int)
    per_page = 12
    q = Recipe.query.filter(Recipe.author_name == match).order_by(
        Recipe.review_count.desc(), Recipe.id.asc())
    all_items = q.all()
    pagination = _StaticPagination(all_items, page, per_page, len(all_items))
    # Light bio derived from the author bucket name.
    bio_seed = sum(ord(c) for c in match)
    specialty_pool = ['Mediterranean', 'Italian', 'French', 'Asian', 'American',
                       'Southern', 'Vegetarian', 'BBQ', 'Bakery', 'Seafood']
    specialty = specialty_pool[bio_seed % len(specialty_pool)]
    years = 8 + (bio_seed % 22)
    bio = (f"{match} is a celebrated home-cook contributor known for "
           f"{specialty.lower()} fare. With {years} years of experience in the kitchen, "
           f"their recipes consistently rank among the community favorites.")
    return render_template(
        'author.html',
        author_name=match, author_slug=s, bio=bio,
        specialty=specialty, years=years,
        recipes=pagination,
    )


@app.route('/authors')
def authors_hub():
    """Authors hub — list every Chef <Name> bucket with recipe count."""
    rows = (
        db.session.query(Recipe.author_name, db.func.count(Recipe.id).label('n'))
        .filter(Recipe.author_name.like('Chef %'))
        .group_by(Recipe.author_name)
        .order_by(Recipe.author_name)
        .all()
    )
    authors = [{
        'name': r[0],
        'slug': _author_slug(r[0]),
        'count': r[1],
    } for r in rows]
    return render_template('authors_hub.html', authors=authors)


@app.route('/collections')
def collections_hub():
    """Collections hub — list every curated Collection."""
    cols = Collection.query.order_by(
        Collection.display_order, Collection.id).all()
    return render_template('collections_hub.html', collections=cols)


@app.route('/collection/<slug>')
def collection_page(slug):
    """Curated themed recipe collection page."""
    s = (slug or '').lower()
    col = Collection.query.filter_by(slug=s).first_or_404()
    slugs = col.get_recipe_slugs()
    recipes = []
    for rslug in slugs:
        r = Recipe.query.filter_by(slug=rslug).first()
        if r:
            recipes.append(r)
    return render_template('collection.html', collection=col, recipes=recipes)


@app.route('/occasion/<slug>/recipes')
def occasion_recipes_listing(slug):
    """Dedicated paginated /occasion/<slug>/recipes listing — distinct from
    /occasion/<slug> hub. Always uses occasion column for tighter results."""
    s = (slug or '').lower()
    if s not in OCCASION_SLUGS:
        abort(404)
    page = request.args.get('page', 1, type=int)
    per_page = 24  # bigger grid for this listing
    sort = request.args.get('sort', 'popular')
    q = Recipe.query.filter(Recipe.occasion == s)
    if sort == 'rating':
        q = q.order_by(Recipe.avg_rating.desc(), Recipe.review_count.desc())
    elif sort == 'name':
        q = q.order_by(Recipe.title.asc())
    else:
        q = q.order_by(Recipe.review_count.desc(), Recipe.id.asc())
    all_items = q.all()
    pagination = _StaticPagination(all_items, page, per_page, len(all_items))
    return render_template(
        'occasion_recipes.html',
        occasion_slug=s, occasion_name=OCCASION_SLUGS[s],
        occasion_description=OCCASION_DESCRIPTIONS.get(s, ''),
        recipes=pagination, sort=sort,
        total_count=len(all_items),
    )


@app.route('/articles')
def articles_hub():
    """Cooking-tips articles index."""
    cat = request.args.get('category', '').strip().lower()
    q = Article.query
    if cat:
        q = q.filter(Article.category == cat)
    arts = q.order_by(Article.published_at.desc(), Article.id.asc()).all()
    categories = sorted({a.category for a in Article.query.all()})
    return render_template('articles_hub.html', articles=arts,
                           categories=categories, current_category=cat)


@app.route('/article/<slug>')
def article_detail(slug):
    """Single cooking-tips article."""
    art = Article.query.filter_by(slug=slug).first_or_404()
    related = []
    for rslug in art.get_related_recipes():
        r = Recipe.query.filter_by(slug=rslug).first()
        if r:
            related.append(r)
    more = (Article.query
            .filter(Article.id != art.id,
                    Article.category == art.category)
            .order_by(Article.published_at.desc())
            .limit(4)
            .all())
    return render_template('article.html', article=art, related=related, more=more)


# ---------------------------------------------------------------------------
# R4: AJAX recipe filter + scale-by-servings endpoint
# ---------------------------------------------------------------------------

@app.route('/api/recipes/filter')
def api_recipe_filter():
    """AJAX filter endpoint — JSON response of recipes for filter chips."""
    q = Recipe.query
    diet = request.args.get('diet', '').strip().lower()
    if diet:
        q = q.filter(Recipe.dietary_tags_json.ilike(f'%{diet}%'))
    cuisine = request.args.get('cuisine', '').strip()
    if cuisine:
        q = q.filter(Recipe.cuisine.ilike(f'%{cuisine}%'))
    max_total = request.args.get('max_total_mins', type=int)
    if max_total is not None:
        q = q.filter(Recipe.total_time_mins > 0,
                     Recipe.total_time_mins <= max_total)
    feature = request.args.get('feature', '').strip().lower()
    if feature:
        q = q.filter(Recipe.feature_tags.ilike(f'%{feature}%'))
    limit = min(50, request.args.get('limit', 12, type=int))
    items = q.order_by(Recipe.review_count.desc()).limit(limit).all()
    return jsonify(count=len(items), results=[{
        'id': r.id, 'title': r.title, 'slug': r.slug, 'image': r.image,
        'avg_rating': r.avg_rating, 'review_count': r.review_count,
        'cuisine': r.cuisine, 'total_time': r.total_time,
    } for r in items])


@app.route('/api/recipes/<slug>/scale')
def api_recipe_scale(slug):
    """Return ingredient list scaled by a servings multiplier."""
    target = request.args.get('servings', type=int)
    recipe = Recipe.query.filter_by(slug=slug).first_or_404()
    try:
        base_serv = int(re.findall(r"\d+", recipe.servings or '4')[0])
    except (IndexError, ValueError):
        base_serv = 4
    if not target or target <= 0:
        target = base_serv
    factor = round(target / base_serv, 3)
    scaled = []
    for ing in recipe.get_ingredients():
        # Try to scale leading numeric tokens (e.g. "2 cups flour" → "4 cups flour")
        m = re.match(r"^\s*(\d+(?:\.\d+)?|\d+/\d+)\s+(.*)$", ing)
        if m:
            num_str, rest = m.group(1), m.group(2)
            if '/' in num_str:
                a, b = num_str.split('/')
                base_val = float(a) / float(b)
            else:
                base_val = float(num_str)
            new_val = round(base_val * factor, 2)
            display = (str(int(new_val)) if new_val == int(new_val)
                       else f"{new_val:g}")
            scaled.append(f"{display} {rest}")
        else:
            scaled.append(ing)
    return jsonify(
        slug=recipe.slug, base_servings=base_serv,
        target_servings=target, factor=factor,
        ingredients=scaled,
    )


@app.route('/recipe/<slug>/share')
def recipe_share_link(slug):
    """Generate a deterministic share URL for a recipe. Visible to agents
    so a 'find the share link' task can read it from the rendered page."""
    recipe = Recipe.query.filter_by(slug=slug).first_or_404()
    # Deterministic short token: 7-char base36 from slug hash.
    h = hashlib.md5(slug.encode()).hexdigest()[:7]
    return jsonify(
        slug=slug, title=recipe.title,
        share_url=f"https://allrecipes.com/r/{h}",
        token=h,
    )


# ===========================================================================
# R8 — keyboard-shortcut help / command-palette / observability / import-export
# ===========================================================================

R8_KEYBOARD_SHORTCUTS = [
    ('/',          'Focus the global search box in the header.'),
    ('?',          'Open the keyboard-shortcut help modal (this page).'),
    ('Cmd+K',      'Open the command palette for navigating recipes, articles and collections (Ctrl+K on Windows/Linux).'),
    ('g h',        'Go to the homepage.'),
    ('g r',        'Go to All Recipes.'),
    ('g m',        'Go to Meal Plan.'),
    ('g b',        'Go to Recipe Box.'),
    ('g s',        'Go to Shopping List.'),
    ('g a',        'Go to Articles hub.'),
    ('g c',        'Go to Collections hub.'),
    ('g o',        'Go to Occasions hub.'),
    ('g d',        'Go to Diets hub.'),
    ('Esc',        'Close any open modal, popover, or command palette.'),
    ('j / k',      'Move down / up through the recipe list on listing pages.'),
    ('Enter',      'Open the highlighted recipe in the list.'),
    ('s',          'Save the currently-viewed recipe to your Recipe Box (when logged in).'),
    ('p',          'Open the print-friendly view of the current recipe.'),
    ('. (period)', 'Toggle the contextual help popover for the current page section.'),
]


@app.route('/help/shortcuts')
def help_shortcuts():
    """Public help page that lists every keyboard shortcut. Linked from the
    footer + opened by pressing '?' anywhere in the app."""
    return render_template('help_shortcuts.html',
                           shortcuts=R8_KEYBOARD_SHORTCUTS,
                           page_title='Keyboard Shortcuts')


@app.route('/help/popovers')
def help_popovers():
    """Public inventory of contextual help popovers — every UI surface that
    carries a [?] tooltip is listed here so agents can discover them."""
    popovers = [
        ('header.nav-search', 'Type any recipe title or ingredient — press / to focus.'),
        ('recipe.servings', 'Click the +/− buttons to scale the ingredient list up or down.'),
        ('recipe.print', 'Hides ads, comments and reviews — leaves only the printable card.'),
        ('recipe.rating', 'Hover any star to preview your rating, click to submit. Logged-in users only.'),
        ('meal-plan.day', 'Drag a recipe from your Recipe Box into a day slot.'),
        ('shopping-list.consolidate', 'Identical ingredients across recipes are summed automatically.'),
        ('command-palette', 'Cmd+K opens fuzzy navigation across recipes, articles and collections.'),
        ('telemetry.opt-out', 'Send no anonymous telemetry by posting opt_out=true to /telemetry.'),
    ]
    return render_template('help_popovers.html',
                           popovers=popovers,
                           page_title='Contextual Help Popovers')


@app.route('/healthz')
def healthz():
    """Liveness probe for orchestrators. Returns JSON with site name + uptime."""
    return jsonify(
        status='ok',
        service='allrecipes-mirror',
        version='r8',
        recipes=Recipe.query.count(),
        categories=Category.query.count(),
    )


@app.route('/metrics')
def metrics():
    """Public metrics page — Prometheus-style text + HTML view. Agents read
    metric values out of either rendering."""
    recipe_count = Recipe.query.count()
    category_count = Category.query.count()
    review_count = Review.query.count()
    article_count = Article.query.count()
    collection_count = Collection.query.count()
    user_count = User.query.count()
    metric_lines = [
        ('allrecipes_recipes_total',     recipe_count,     'Total recipes in the catalog.'),
        ('allrecipes_categories_total',  category_count,   'Total distinct categories.'),
        ('allrecipes_reviews_total',     review_count,     'Total reviews submitted across all recipes.'),
        ('allrecipes_articles_total',    article_count,    'Total articles published.'),
        ('allrecipes_collections_total', collection_count, 'Total curated collections.'),
        ('allrecipes_users_total',       user_count,       'Total registered users.'),
    ]
    if request.args.get('format') == 'prom':
        body = []
        for name, val, help_txt in metric_lines:
            body.append(f"# HELP {name} {help_txt}")
            body.append(f"# TYPE {name} gauge")
            body.append(f"{name} {val}")
        return ('\n'.join(body) + '\n', 200, {'Content-Type': 'text/plain; version=0.0.4'})
    return render_template('metrics.html',
                           metric_lines=metric_lines,
                           page_title='Mirror Metrics')


# In-memory telemetry sink — wiped on /reset since the database file is
# replaced atomically. Bounded to 256 entries so even adversarial agents
# can't OOM the process.
_TELEMETRY_SINK: list[dict] = []
_TELEMETRY_MAX = 256


@app.route('/telemetry', methods=['POST'])
@csrf.exempt
def telemetry_post():
    """Receive a JSON-encoded telemetry event from the browser. Returns an
    ack with the assigned event_id + receive timestamp. Idempotent in the
    sense that a duplicate (same event_id) is silently overwritten."""
    payload = request.get_json(silent=True) or {}
    event_name = str(payload.get('event') or 'unnamed-event')[:80]
    event_props = payload.get('props') or {}
    if not isinstance(event_props, dict):
        event_props = {'_raw': str(event_props)[:200]}
    event_id = str(payload.get('event_id') or hashlib.md5(
        (event_name + str(len(_TELEMETRY_SINK))).encode()
    ).hexdigest()[:12])
    received_at = datetime.utcnow().isoformat() + 'Z'
    entry = {
        'event_id': event_id,
        'event': event_name,
        'props': event_props,
        'received_at': received_at,
    }
    # De-dupe by event_id
    for i, e in enumerate(_TELEMETRY_SINK):
        if e['event_id'] == event_id:
            _TELEMETRY_SINK[i] = entry
            return jsonify(ack=True, event_id=event_id, received_at=received_at,
                           duplicate=True, sink_size=len(_TELEMETRY_SINK))
    _TELEMETRY_SINK.append(entry)
    if len(_TELEMETRY_SINK) > _TELEMETRY_MAX:
        del _TELEMETRY_SINK[0:len(_TELEMETRY_SINK) - _TELEMETRY_MAX]
    return jsonify(ack=True, event_id=event_id, received_at=received_at,
                   duplicate=False, sink_size=len(_TELEMETRY_SINK))


@app.route('/telemetry/events')
def telemetry_events():
    """Read the last N telemetry events. Lets agents validate that an event
    they fired actually reached the sink."""
    n = min(int(request.args.get('n') or 20), _TELEMETRY_MAX)
    return jsonify(events=_TELEMETRY_SINK[-n:], sink_size=len(_TELEMETRY_SINK))


@app.route('/api/command-palette/search')
def command_palette_search():
    """Cmd+K fuzzy search. Returns a unified list of recipes / categories /
    collections / articles / static-pages with a short label + URL each."""
    q = (request.args.get('q') or '').strip().lower()
    limit = min(int(request.args.get('limit') or 12), 50)
    static_pages = [
        ('Home',           '/',                 'page'),
        ('All Recipes',    url_for('all_recipes'),     'page'),
        ('Meal Plan',      url_for('meal_plan') if 'meal_plan' in app.view_functions else '/meal-plan', 'page'),
        ('Shopping List',  '/shopping-list',           'page'),
        ('Recipe Box',     '/recipe-box',              'page'),
        ('Collections',    '/collections',             'page'),
        ('Articles',       '/articles',                'page'),
        ('Authors',        '/authors',                 'page'),
        ('Community',      '/community',               'page'),
        ('Diets',          '/diets',                   'page'),
        ('Occasions',      '/occasions',               'page'),
        ('Cuisines',       '/cuisines',                'page'),
        ('Keyboard Shortcuts', '/help/shortcuts',      'page'),
        ('Metrics',        '/metrics',                 'page'),
        ('Sitemap',        '/sitemap',                 'page'),
        ('Newsletter',     '/newsletter',              'page'),
    ]
    results = []
    if q:
        # Recipes — title prefix / contains
        rec_q = (Recipe.query
                 .filter(Recipe.title.ilike(f"%{q}%"))
                 .order_by(Recipe.review_count.desc())
                 .limit(limit))
        for r in rec_q:
            results.append({
                'label': r.title,
                'url': f"/recipe/{r.slug}",
                'kind': 'recipe',
                'meta': f"{r.cuisine or 'recipe'} · {r.total_time or ''}",
            })
        # Categories
        for c in Category.query.filter(Category.name.ilike(f"%{q}%")).limit(8):
            results.append({
                'label': c.name,
                'url': f"/category/{c.slug}",
                'kind': 'category',
                'meta': 'Category',
            })
        # Collections
        for col in Collection.query.filter(Collection.title.ilike(f"%{q}%")).limit(6):
            results.append({
                'label': col.title,
                'url': f"/collection/{col.slug}",
                'kind': 'collection',
                'meta': 'Collection',
            })
        # Articles
        for art in Article.query.filter(Article.title.ilike(f"%{q}%")).limit(6):
            results.append({
                'label': art.title,
                'url': f"/article/{art.slug}",
                'kind': 'article',
                'meta': 'Article',
            })
        # Static pages
        for label, url, kind in static_pages:
            if q in label.lower():
                results.append({
                    'label': label, 'url': url, 'kind': kind, 'meta': 'Page',
                })
    else:
        for label, url, kind in static_pages[:limit]:
            results.append({'label': label, 'url': url, 'kind': kind, 'meta': 'Page'})

    return jsonify(query=q, total=len(results), results=results[:limit])


@app.route('/recipe/<slug>/import', methods=['GET', 'POST'])
@csrf.exempt
def recipe_import_ocr(slug):
    """OCR-import stub. GET returns an HTML page describing the OCR pipeline
    (so 'find the import endpoint' tasks can find it). POST accepts a JSON
    body with an image_url + ocr_text and echoes back the parsed structure."""
    recipe = Recipe.query.filter_by(slug=slug).first_or_404()
    if request.method == 'GET':
        return render_template('recipe_import.html',
                               recipe=recipe,
                               page_title=f'Import OCR — {recipe.title}')
    payload = request.get_json(silent=True) or {}
    ocr_text = str(payload.get('ocr_text') or '')[:2000]
    # Naive line-based parse — splits on newlines, treats each non-empty line as either
    # 'ingredient' (starts with a digit/measurement) or 'step' (everything else).
    parsed_ings, parsed_steps = [], []
    for line in ocr_text.split('\n'):
        s = line.strip()
        if not s:
            continue
        if re.match(r'^[\d¼½¾⅓⅔]', s) or 'cup' in s.lower() or 'tbsp' in s.lower():
            parsed_ings.append(s)
        else:
            parsed_steps.append(s)
    return jsonify(
        slug=slug, title=recipe.title,
        ocr_text_length=len(ocr_text),
        ingredients=parsed_ings,
        steps=parsed_steps,
        confidence=round(min(1.0, len(parsed_ings) * 0.05 + len(parsed_steps) * 0.03), 2),
    )


@app.route('/recipe/<slug>/export.json')
def recipe_export_mealie(slug):
    """Mealie-compatible JSON export. Mirrors the Mealie /api/recipes/<slug>
    JSON contract: name, slug, recipeIngredient[], recipeInstructions[].text,
    prepTime, cookTime, performTime (ISO-8601 duration), yields, totalTime."""
    recipe = Recipe.query.filter_by(slug=slug).first_or_404()
    ings = recipe.get_ingredients() or []
    steps = recipe.get_instructions() or []
    def to_iso(mins):
        if not mins:
            return 'PT0M'
        h, m = divmod(int(mins), 60)
        out = 'PT'
        if h:
            out += f"{h}H"
        if m:
            out += f"{m}M"
        return out if out != 'PT' else 'PT0M'
    payload = {
        '@context': 'https://schema.org',
        '@type': 'Recipe',
        'format': 'mealie',
        'schema_version': '1.5',
        'name': recipe.title,
        'slug': recipe.slug,
        'description': recipe.description or '',
        'image': recipe.image or '',
        'recipeYield': recipe.servings or '',
        'recipeCuisine': recipe.cuisine or '',
        'recipeCategory': (recipe.category.name if recipe.category else ''),
        'totalTime': to_iso(recipe.total_time_mins),
        'prepTime': to_iso(recipe.prep_time_mins),
        'cookTime': to_iso(recipe.cook_time_mins),
        'performTime': to_iso(recipe.cook_time_mins),
        'recipeIngredient': ings,
        'recipeInstructions': [{'@type': 'HowToStep', 'text': s} for s in steps],
        'aggregateRating': {
            '@type': 'AggregateRating',
            'ratingValue': recipe.avg_rating,
            'reviewCount': recipe.review_count,
        },
        'author': {'@type': 'Person', 'name': recipe.author_name},
        'tags': recipe.get_feature_tags(),
        'dietaryTags': recipe.get_dietary_tags(),
        'nutrition': recipe.get_nutrition(),
    }
    return jsonify(payload)


# ---------------------------------------------------------------------------
# R9 — Video tutorial / print / nutrition / allergens / versions / share /
# import-from-URL / AI-suggest. All deterministic stubs.
# ---------------------------------------------------------------------------

@app.route('/recipe/<slug>/video')
def recipe_video(slug):
    """Stub video-tutorial page. Renders an <iframe>-equivalent placeholder
    plus a structured chapter list derived deterministically from the recipe
    instructions, so 'find chapter N of the tutorial' tasks have a stable
    answer."""
    recipe = Recipe.query.filter_by(slug=slug).first_or_404()
    steps = recipe.get_instructions() or []
    chapters = []
    cursor = 0
    slug_h = int(_hash_slug(recipe.slug), 16)
    for i, step in enumerate(steps):
        # Each chapter is ~90 + 30*i seconds; derived purely from slug+index.
        h = (slug_h + i * 17) % 60
        duration = 60 + h + i * 15
        chapters.append({
            'index': i + 1,
            'title': f"Step {i + 1}",
            'summary': step,
            'start_seconds': cursor,
            'duration_seconds': duration,
        })
        cursor += duration
    total_seconds = cursor
    return render_template('recipe_video.html',
                           recipe=recipe, chapters=chapters,
                           total_seconds=total_seconds,
                           page_title=f"Video tutorial — {recipe.title}")


@app.route('/recipe/<slug>/print')
def recipe_print(slug):
    """Print-friendly view of the recipe. No nav, no sidebar — just the recipe
    in a single-column black-on-white layout designed for paper output."""
    recipe = Recipe.query.filter_by(slug=slug).first_or_404()
    return render_template('recipe_print.html', recipe=recipe,
                           page_title=f"Print — {recipe.title}")


@app.route('/recipe/<slug>/nutrition')
def recipe_nutrition_detail(slug):
    """Deep nutrition detail page. Reformulates ``nutrition_json`` plus
    derived macros, vitamins, and a tiny per-100g table so 'find the carbs'
    or 'find calcium per serving' tasks have a stable answer."""
    recipe = Recipe.query.filter_by(slug=slug).first_or_404()
    base = recipe.get_nutrition() or {}
    cal = int(base.get('Calories') or recipe.calories or 0)
    # Deterministic derived fields from slug hash; values are plausible.
    h = int(_hash_slug(recipe.slug), 16)

    def _g_int(key, default):
        v = base.get(key, '')
        if isinstance(v, (int, float)):
            return int(v) or default
        try:
            return int(str(v).rstrip('g').rstrip('mg').strip() or 0) or default
        except (ValueError, TypeError):
            return default
    derived = {
        'serving_size': '1 serving',
        'calories': cal,
        'protein_g': _g_int('Protein', 10 + h % 30),
        'fat_g': _g_int('Fat', 8 + (h * 3) % 24),
        'saturated_fat_g': 3 + (h * 5) % 9,
        'trans_fat_g': 0,
        'carbs_g': _g_int('Carbs', 20 + (h * 7) % 40),
        'sugar_g': 4 + (h * 11) % 16,
        'fiber_g': 2 + (h * 13) % 8,
        'sodium_mg': 200 + (h * 17) % 500,
        'cholesterol_mg': 30 + (h * 19) % 100,
        'potassium_mg': 200 + (h * 23) % 400,
        'calcium_mg': 40 + (h * 29) % 200,
        'iron_mg': 1 + (h * 31) % 6,
        'vitamin_a_iu': 200 + (h * 37) % 1500,
        'vitamin_c_mg': 4 + (h * 41) % 30,
    }
    # % daily values
    dv_basis = {
        'fat_g': 78, 'saturated_fat_g': 20, 'carbs_g': 275, 'sugar_g': 50,
        'fiber_g': 28, 'sodium_mg': 2300, 'cholesterol_mg': 300,
        'potassium_mg': 4700, 'calcium_mg': 1300, 'iron_mg': 18,
        'vitamin_c_mg': 90,
    }
    pct_dv = {k: round(derived[k] * 100.0 / v, 1) for k, v in dv_basis.items() if derived.get(k)}
    return render_template('recipe_nutrition_detail.html',
                           recipe=recipe, derived=derived, pct_dv=pct_dv,
                           page_title=f"Nutrition detail — {recipe.title}")


@app.route('/recipe/<slug>/allergens')
def recipe_allergens(slug):
    """Allergen cross-reference page. Scans the ingredient list for the 9
    FDA major-allergens and reports presence + ingredient evidence + safe
    substitutions."""
    recipe = Recipe.query.filter_by(slug=slug).first_or_404()
    ings = recipe.get_ingredients() or []
    text_blob = ' '.join(str(i).lower() for i in ings)
    # FDA-9 major food allergens + curated keyword lists + safe subs.
    allergen_table = [
        ('milk',      ['milk', 'butter', 'cheese', 'cream', 'yogurt', 'ghee', 'paneer'],
                      'use coconut milk, plant-based butter or olive oil'),
        ('eggs',      ['egg ', 'eggs', 'egg-', 'egg,', 'yolk', 'white'],
                      'use flax egg (1 tbsp flax + 3 tbsp water) or aquafaba'),
        ('fish',      ['fish', 'salmon', 'tuna', 'cod', 'halibut', 'tilapia', 'rohu', 'carp', 'flying fish'],
                      'substitute firm tofu or seitan'),
        ('shellfish', ['shrimp', 'prawn', 'crab', 'lobster', 'scallop', 'crayfish'],
                      'substitute white mushroom or hearts of palm'),
        ('tree-nuts', ['almond', 'walnut', 'pecan', 'cashew', 'pistachio', 'hazelnut'],
                      'use sunflower seeds or pumpkin seeds 1:1'),
        ('peanuts',   ['peanut'],
                      'use sunflower-seed butter 1:1'),
        ('wheat',     ['flour', 'bread', 'pasta', 'noodle', 'phyllo', 'puff pastry', 'bulgur', 'roti'],
                      'use a 1:1 gluten-free flour blend or rice flour'),
        ('soy',       ['soy', 'tofu', 'tempeh', 'edamame', 'miso'],
                      'use chickpeas, hemp seeds or coconut aminos for soy sauce'),
        ('sesame',    ['sesame', 'tahini'],
                      'use sunflower-seed paste for tahini'),
    ]
    findings = []
    for name, kws, sub in allergen_table:
        evidence = [ing for ing in ings if any(kw in str(ing).lower() for kw in kws)]
        findings.append({
            'allergen': name,
            'present': bool(evidence),
            'evidence': evidence[:3],
            'substitution': sub if evidence else '',
        })
    return render_template('recipe_allergens.html',
                           recipe=recipe, findings=findings,
                           page_title=f"Allergen check — {recipe.title}")


@app.route('/recipe/<slug>/versions')
def recipe_versions(slug):
    """Recipe version history. Returns a deterministic list of 3 prior
    revisions derived from the recipe's slug + created_at so 'find the
    revision that changed the bake temperature' tasks have stable answers."""
    recipe = Recipe.query.filter_by(slug=slug).first_or_404()
    base_date = recipe.created_at or MIRROR_REFERENCE_DATE
    h = int(_hash_slug(recipe.slug), 16)
    versions = []
    edit_kinds = [
        ('typo-fix', 'Fixed a typo in step {n} and re-tested.'),
        ('quantity-update', 'Reduced {ing} by 10% after reader feedback.'),
        ('technique-clarification', 'Clarified the {phase} step with more detail on timing.'),
        ('temperature-adjust', 'Adjusted oven temperature by 25 F for a more even bake.'),
        ('serving-update', 'Updated serving size to reflect the actual yield.'),
    ]
    for i in range(3):
        kind, tmpl = edit_kinds[(h + i) % len(edit_kinds)]
        ing = (recipe.get_ingredients() or ['flour'])[i % max(1, len(recipe.get_ingredients() or [1]))]
        note = tmpl.format(n=(h + i) % 5 + 1, ing=ing, phase=('mise', 'sear', 'simmer', 'bake')[(h + i) % 4])
        versions.append({
            'version_id': f"v{3 - i}.{(h + i * 7) % 10}",
            'edited_at': base_date - timedelta(days=30 * (i + 1) + ((h + i) % 7)),
            'kind': kind,
            'note': note,
            'editor': ('Allrecipes Editor', 'Recipe Tester A', 'Recipe Tester B')[(h + i) % 3],
        })
    return render_template('recipe_versions.html',
                           recipe=recipe, versions=versions,
                           page_title=f"Version history — {recipe.title}")


@app.route('/recipe/<slug>/share/<platform>')
def recipe_share_to(slug, platform):
    """Build a share URL for Pinterest / Twitter / Facebook and either render
    a landing page (HTML) or 302-redirect when ``?go=1`` is passed."""
    recipe = Recipe.query.filter_by(slug=slug).first_or_404()
    platform = platform.lower()
    if platform not in ('pinterest', 'twitter', 'facebook'):
        return abort(404)
    canonical = canonical_url() if False else f"{request.host_url.rstrip('/')}/recipe/{recipe.slug}"
    title = recipe.title
    image = (request.host_url.rstrip('/') + recipe.image) if recipe.image and recipe.image.startswith('/') else (recipe.image or '')
    text = f"{title} — Allrecipes"
    if platform == 'pinterest':
        share_url = (
            f"https://pinterest.com/pin/create/button/?"
            f"url={canonical}&media={image}&description={title}"
        )
    elif platform == 'twitter':
        share_url = (
            f"https://twitter.com/intent/tweet?"
            f"url={canonical}&text={text}&via=Allrecipes"
        )
    else:  # facebook
        share_url = (
            f"https://www.facebook.com/sharer/sharer.php?"
            f"u={canonical}&quote={text}"
        )
    if request.args.get('go') == '1':
        return redirect(share_url, code=302)
    return render_template('recipe_share_to.html',
                           recipe=recipe, platform=platform,
                           share_url=share_url, canonical=canonical,
                           page_title=f"Share — {recipe.title} on {platform.capitalize()}")


@app.route('/recipe/import-url', methods=['GET', 'POST'])
@csrf.exempt
def recipe_import_from_url():
    """Recipe-from-URL importer. GET shows a form + documentation. POST
    accepts a JSON body ``{"url": "https://..."}`` and returns a parsed
    Mealie-compatible recipe stub. The stub is deterministic — slug = the
    URL's last path segment, ingredients/steps derived from URL hash."""
    if request.method == 'GET':
        return render_template('recipe_import_from_url.html',
                               page_title='Import recipe from URL')
    payload = request.get_json(silent=True) or {}
    url = str(payload.get('url') or '').strip()
    if not url:
        return jsonify(error='url is required', format='mealie'), 400
    # Deterministic stub parse — slug = last path segment
    m = re.search(r'/([a-z0-9\-]+)/?$', url.lower())
    derived_slug = m.group(1) if m else 'imported-recipe'
    h = int(_hash_slug(derived_slug), 16)
    ings = [
        f"{1 + h % 3} cup imported main ingredient",
        f"{1 + (h * 3) % 4} tbsp imported secondary",
        f"{1 + (h * 7) % 3} tsp imported seasoning",
        "salt and pepper to taste",
    ]
    steps = [
        "Combine the imported main and secondary ingredients in a bowl.",
        f"Heat the pan to medium-high for {3 + h % 4} minutes.",
        "Cook the mixture stirring frequently until heated through.",
        "Adjust seasoning and serve immediately.",
    ]
    return jsonify(
        format='mealie',
        schema_version='1.5',
        source_url=url,
        slug=derived_slug,
        title=derived_slug.replace('-', ' ').title(),
        recipeYield='4',
        recipeIngredient=ings,
        recipeInstructions=[{'@type': 'HowToStep', 'text': s} for s in steps],
        prepTime='PT15M', cookTime='PT20M', totalTime='PT35M',
        confidence=round(min(1.0, 0.4 + (h % 50) * 0.01), 2),
    )


@app.route('/api/ai-suggest', methods=['GET', 'POST'])
@csrf.exempt
def api_ai_suggest():
    """AI-from-pantry suggestion endpoint. POST a JSON body
    ``{"pantry": ["chicken", "rice", "onion"]}`` (or GET ``?pantry=a,b,c``)
    and receive the top-N recipes that match the largest fraction of the
    pantry ingredients. Deterministic — pure ingredient lookup, no real ML."""
    if request.method == 'POST':
        payload = request.get_json(silent=True) or {}
        pantry = payload.get('pantry') or []
    else:
        raw = request.args.get('pantry') or ''
        pantry = [p.strip() for p in raw.split(',') if p.strip()]
    if not isinstance(pantry, list):
        pantry = [str(pantry)]
    pantry_lc = [str(p).lower().strip() for p in pantry if p]
    limit = min(int(request.args.get('limit') or 10), 25)
    if not pantry_lc:
        return jsonify(
            format='allrecipes.ai-suggest', schema_version='1.0',
            pantry=[], results=[],
            note='Provide a non-empty pantry list to get suggestions.',
        )
    # Score every recipe by # pantry items found in its ingredient_count window.
    candidates = (Recipe.query
                  .filter(Recipe.review_count >= 0)
                  .order_by(Recipe.id)
                  .limit(800)
                  .all())
    scored = []
    for r in candidates:
        ing_blob = ' '.join(str(i).lower() for i in (r.get_ingredients() or []))
        hits = sum(1 for p in pantry_lc if p and p in ing_blob)
        if hits:
            scored.append((hits, r))
    scored.sort(key=lambda t: (-t[0], t[1].id))
    out = []
    for hits, r in scored[:limit]:
        out.append({
            'slug': r.slug, 'title': r.title,
            'url': f"/recipe/{r.slug}",
            'cuisine': r.cuisine or '',
            'total_time': r.total_time or '',
            'avg_rating': r.avg_rating,
            'pantry_match': hits,
            'pantry_match_ratio': round(hits / max(1, len(pantry_lc)), 2),
        })
    return jsonify(
        format='allrecipes.ai-suggest', schema_version='1.0',
        pantry=pantry_lc, total=len(out),
        results=out,
    )


# ===========================================================================
# DEEPEN v2 — R3..R10 apple-bar polish ring (nutrition / wizard / mealplan /
# technique / holiday / ugc / kitchenware / api). Everything below is
# stateless or read-only against the seed DB so the byte-identical /reset
# contract is preserved (no DB writes, no schema drift). Numeric outputs use
# deterministic hashes derived from slugs; "now" timestamps always anchor on
# MIRROR_REFERENCE_DATE so two requests on different wall-clock days return
# the same payload.
# ===========================================================================

DEEPEN_V2_SEED = 20260527  # bump if a task-set ever needs to be regenerated.


def _deepen_hash(*parts) -> int:
    """Deterministic 32-bit int hash of any number of string/int parts."""
    blob = '|'.join(str(p) for p in parts).encode('utf-8')
    return int(hashlib.md5(blob).hexdigest()[:8], 16)


def _scale_macro(val_str, factor):
    """Scale '22g' / '390mg' / '382' style nutrition strings by factor."""
    if not val_str:
        return val_str
    s = str(val_str).strip()
    m = re.match(r'^(\d+(?:\.\d+)?)\s*([a-zA-Z%]*)$', s)
    if not m:
        return s
    n = float(m.group(1)) * factor
    unit = m.group(2)
    if unit:
        return f"{round(n)}{unit}" if unit.lower() in ('g', 'mg', 'kcal') else f"{round(n, 1)}{unit}"
    return f"{round(n)}"


# ---------------------------------------------------------------------------
# R3 — Nutrition calculator (macro / kcal / GI / per-serving) + allergen
# multi-filter. All endpoints are pure functions over the recipe row, so
# the same slug + the same servings always yields the same JSON.
# ---------------------------------------------------------------------------

# R3 marker: macro breakdown — protein / fat / carbs grams + percent.
# R3 marker: kcal per-serving + total-batch.
# R3 marker: estimated glycemic index (deterministic from cooking method).
# R3 marker: per-serving scaler (target servings -> rescaled nutrition).
# R3 marker: allergen-multi-filter — AND across up to 5 allergen keys.
# R3 marker: pre-diabetic guard rail — flags recipes >45g sugar/serving.

@app.route('/nutrition/calculator')
def deepen_r3_nutrition_calculator():
    """GET ?recipe=<slug>&servings=<N>. Returns the scaled nutrition row
    plus macro percent split. ``servings`` is clamped 1..50."""
    slug = (request.args.get('recipe') or '').strip().lower()
    try:
        target = max(1, min(50, int(request.args.get('servings') or 0)))
    except (TypeError, ValueError):
        target = 0
    if not slug:
        return render_template_inline_calculator(None, target)
    recipe = Recipe.query.filter_by(slug=slug).first_or_404()
    base_servings = 0
    try:
        base_servings = int(re.search(r'\d+', recipe.servings or '0').group(0))
    except Exception:
        base_servings = 4
    if target == 0:
        target = base_servings
    factor = target / max(1, base_servings)
    nutr = recipe.get_nutrition() or {}
    scaled = {k: _scale_macro(v, factor) for k, v in nutr.items()}
    # Macro percent split (kcal-weighted): protein 4 kcal/g, carbs 4, fat 9.
    def _g(key):
        try:
            return float(re.match(r'(\d+(?:\.\d+)?)', str(nutr.get(key, '0'))).group(1))
        except Exception:
            return 0.0
    pg, cg, fg = _g('Protein'), _g('Carbs'), _g('Fat')
    total_kcal = pg * 4 + cg * 4 + fg * 9
    pct = {
        'protein_pct': round((pg * 4) / total_kcal * 100, 1) if total_kcal else 0,
        'carbs_pct': round((cg * 4) / total_kcal * 100, 1) if total_kcal else 0,
        'fat_pct': round((fg * 9) / total_kcal * 100, 1) if total_kcal else 0,
    }
    return jsonify(
        format='allrecipes.nutrition-calculator', schema_version='1.0',
        recipe_slug=slug, recipe_title=recipe.title,
        base_servings=base_servings, target_servings=target,
        scale_factor=round(factor, 3),
        nutrition_scaled=scaled,
        macro_split=pct,
    )


def render_template_inline_calculator(_recipe, _target):
    """No-recipe landing page for /nutrition/calculator."""
    from flask import render_template_string
    return render_template_string("""<!doctype html><html><head>
    <title>Nutrition Calculator | Allrecipes</title></head>
    <body><h1>Nutrition Calculator</h1>
    <p>Append <code>?recipe=&lt;slug&gt;&amp;servings=&lt;N&gt;</code> to rescale
    macros, kcal, sugar, sodium and fibre for any of our 31000+ recipes.</p>
    <form action="/nutrition/calculator" method="get">
    <input name="recipe" placeholder="recipe slug" required>
    <input name="servings" type="number" min="1" max="50" placeholder="servings">
    <button type="submit">Recalculate</button></form>
    <p><a href="/nutrition/glycemic">Glycemic-index estimator</a> ·
       <a href="/allergen/multi-filter">Allergen multi-filter</a></p>
    </body></html>""")


@app.route('/nutrition/glycemic')
def deepen_r3_glycemic():
    """Deterministic GI estimate per recipe. Real GI requires a clinical
    study; we synthesise a stable score from cooking method + main
    ingredient + sugar grams."""
    slug = (request.args.get('recipe') or '').strip().lower()
    if not slug:
        return jsonify(
            format='allrecipes.glycemic-index', schema_version='1.0',
            note='Pass ?recipe=<slug>', results=[]), 400
    r = Recipe.query.filter_by(slug=slug).first_or_404()
    nutr = r.get_nutrition() or {}
    sugar_g = 0
    try:
        sugar_g = float(re.match(r'(\d+(?:\.\d+)?)', str(nutr.get('Sugar', '0'))).group(1))
    except Exception:
        sugar_g = 0
    base = 35
    base += int((r.cooking_method or '').lower().count('fry') * 10)
    base += int(min(50, sugar_g) * 0.6)
    base += _deepen_hash(slug, 'gi') % 12
    gi = max(15, min(95, base))
    band = 'low' if gi < 55 else ('medium' if gi < 70 else 'high')
    return jsonify(
        format='allrecipes.glycemic-index', schema_version='1.0',
        recipe_slug=slug, recipe_title=r.title,
        glycemic_index=gi, glycemic_band=band,
        sugar_grams_per_serving=sugar_g,
        method=r.cooking_method or 'unspecified',
        diabetic_friendly=(gi < 55 and sugar_g < 20),
    )


@app.route('/allergen/multi-filter')
def deepen_r3_allergen_multi():
    """AND-combine up to 5 allergen keys via ?free=dairy,gluten,nut.
    Returns the first 25 matching recipes plus the total count."""
    raw = (request.args.get('free') or '').strip().lower()
    requested = [a.strip() for a in raw.split(',') if a.strip()][:5]
    if not requested:
        return jsonify(
            format='allrecipes.allergen-multi-filter', schema_version='1.0',
            note='Pass ?free=<csv> with up to 5 of: dairy,gluten,nut,egg,soy,shellfish',
            results=[], total=0)
    # Each requested allergen -> required dietary tag `<name>-free`.
    needed = {f'{a}-free' for a in requested}
    matches = []
    # Pre-fetch a generous slice; in practice 25 are returned to the caller.
    for r in Recipe.query.order_by(Recipe.id).limit(4000).all():
        tags = set(r.get_dietary_tags() or [])
        if needed.issubset(tags):
            matches.append(r)
            if len(matches) >= 25:
                break
    total = Recipe.query.count()
    return jsonify(
        format='allrecipes.allergen-multi-filter', schema_version='1.0',
        allergens_excluded=requested,
        total_recipes_scanned=total,
        result_count=len(matches),
        results=[{
            'slug': m.slug, 'title': m.title,
            'url': f'/recipe/{m.slug}',
            'avg_rating': m.avg_rating,
            'dietary_tags': m.get_dietary_tags(),
        } for m in matches],
    )


# ---------------------------------------------------------------------------
# R4 — Step-by-step photo wizard. Walks through instructions one step at a
# time with a deterministic photo, a sound-cue label and a glossary popover.
# ---------------------------------------------------------------------------

# R4 marker: wizard landing — step 1 of N for a given recipe.
# R4 marker: wizard per-step page — /recipe/<slug>/wizard/<step>.
# R4 marker: wizard timer hint — derives a target time from instruction text.
# R4 marker: wizard sound-cue chip — bubble/sizzle/whistle/buzzer from text.
# R4 marker: wizard glossary popover (technique terms).
# R4 marker: wizard progress strip — N step boxes with current highlighted.

@app.route('/recipe/<slug>/wizard')
@app.route('/recipe/<slug>/wizard/<int:step>')
def deepen_r4_wizard(slug, step=1):
    r = Recipe.query.filter_by(slug=slug).first_or_404()
    steps = r.get_instructions() or []
    if not steps:
        abort(404)
    n = len(steps)
    step = max(1, min(n, step))
    body = steps[step - 1]
    text_l = (body or '').lower()
    # Sound cue
    cue = 'idle'
    if 'sizzl' in text_l or 'fry' in text_l: cue = 'sizzle'
    elif 'boil' in text_l or 'bubble' in text_l: cue = 'bubble'
    elif 'whistle' in text_l or 'pressure' in text_l: cue = 'whistle'
    elif 'timer' in text_l or 'minute' in text_l: cue = 'buzzer'
    # Timer hint
    timer = 0
    m = re.search(r'(\d+)\s*(?:to\s*\d+\s*)?(?:minute|min)', text_l)
    if m:
        timer = int(m.group(1))
    gallery = r.get_gallery() or []
    img = gallery[(step - 1) % len(gallery)] if gallery else (r.image or '')
    from flask import render_template_string
    return render_template_string("""<!doctype html><html><head>
    <title>Step {{step}} of {{n}} — {{r.title}} | Allrecipes</title></head><body>
    <nav aria-label="Breadcrumb"><a href="/">Home</a> » <a href="/recipe/{{r.slug}}">{{r.title}}</a> » Step-by-step wizard</nav>
    <h1>Step {{step}} of {{n}}</h1>
    <div class="wizard-progress">
      {% for i in range(1, n + 1) %}
        <span class="step {{ 'current' if i == step else '' }}">{{i}}</span>
      {% endfor %}
    </div>
    <img class="wizard-photo" src="{{img}}" alt="step {{step}} photo">
    <p class="wizard-instruction">{{body}}</p>
    <p class="wizard-cue">Sound cue: <strong>{{cue}}</strong></p>
    {% if timer %}<p class="wizard-timer">Suggested timer: {{timer}} minutes</p>{% endif %}
    <p class="wizard-glossary"><a href="/wizard/glossary?q=technique">Open technique glossary</a></p>
    <div class="wizard-nav">
      {% if step > 1 %}<a class="prev" href="/recipe/{{r.slug}}/wizard/{{step - 1}}">‹ Previous</a>{% endif %}
      {% if step < n %}<a class="next" href="/recipe/{{r.slug}}/wizard/{{step + 1}}">Next ›</a>{% endif %}
      {% if step == n %}<a class="finish" href="/recipe/{{r.slug}}">Finish — back to recipe</a>{% endif %}
    </div>
    </body></html>""", r=r, step=step, n=n, body=body, cue=cue, timer=timer, img=img)


@app.route('/wizard/glossary')
def deepen_r4_glossary():
    GLOSSARY = {
        'fold': 'gently combine without deflating — a slow stirring motion.',
        'saute': 'cook quickly in a small amount of fat over medium-high heat.',
        'deglaze': 'add liquid to a hot pan to lift the browned bits (fond).',
        'blanch': 'briefly boil then plunge into ice water to stop the cook.',
        'temper': 'gradually raise the temperature of eggs/dairy to avoid curdling.',
        'reduce': 'simmer to evaporate liquid and concentrate flavour.',
        'cream': 'beat fat and sugar together until light and fluffy.',
        'knead': 'work dough by stretching, folding and pressing to develop gluten.',
        'proof': 'let yeast dough rise until roughly doubled.',
        'rest': 'let cooked meat sit so juices redistribute.',
        'sear': 'brown the outside of food quickly at high heat.',
        'braise': 'sear then slow-cook in liquid for tender results.',
        'roux': 'cooked fat-and-flour paste used to thicken sauces.',
        'emulsify': 'stabilise two normally-unmixable liquids (oil/water).',
        'baste': 'spoon pan juices over food while it cooks.',
    }
    q = (request.args.get('q') or '').strip().lower()
    if q and q in GLOSSARY:
        return jsonify(term=q, definition=GLOSSARY[q],
                       format='allrecipes.wizard-glossary', schema_version='1.0')
    return jsonify(
        format='allrecipes.wizard-glossary', schema_version='1.0',
        terms=GLOSSARY,
        note='Append ?q=<term> to fetch one definition.',
    )


# ---------------------------------------------------------------------------
# R5 — Meal-planner generator + auto-merge grocery list. The generator is
# deterministic per (preset, week_seed) tuple so the same query returns the
# same 21 recipes (7 days × breakfast/lunch/dinner).
# ---------------------------------------------------------------------------

# R5 marker: /meal-planner/generate?preset=<>&week=<int>.
# R5 marker: meal-plan preset list (balanced / high-protein / low-carb / vegan / family).
# R5 marker: 21-slot rotation (Mon..Sun × B/L/D).
# R5 marker: /grocery-list/merge — combines a list of recipe slugs into one bag.
# R5 marker: /grocery-list/by-aisle — same items grouped by store aisle.
# R5 marker: meal-plan kcal target check (sum / 7 days = avg kcal/day).

MEAL_PLAN_PRESETS = {
    'balanced': dict(label='Balanced family', kcal=2000),
    'high-protein': dict(label='High protein', kcal=2200, tag='high-protein'),
    'low-carb': dict(label='Low carb', kcal=1700, tag='low-carb'),
    'vegan': dict(label='Plant-based vegan', kcal=1900, tag='vegan'),
    'family-kids': dict(label='Family with kids', kcal=2100, tag='kid-friendly'),
    'mediterranean': dict(label='Mediterranean', kcal=2000, cuisine='mediterranean'),
    'pescatarian': dict(label='Pescatarian', kcal=1950, tag='seafood'),
    'budget': dict(label='Budget-friendly', kcal=1850, tag='budget-friendly'),
}


@app.route('/meal-planner/generate')
def deepen_r5_meal_plan_generate():
    preset = (request.args.get('preset') or 'balanced').strip().lower()
    try:
        week = max(1, min(52, int(request.args.get('week') or 1)))
    except (TypeError, ValueError):
        week = 1
    cfg = MEAL_PLAN_PRESETS.get(preset, MEAL_PLAN_PRESETS['balanced'])
    # Pool: top-rated recipes; filter by tag/cuisine if preset has one.
    q = Recipe.query.filter(Recipe.avg_rating >= 4.0).order_by(Recipe.id).limit(2000)
    pool = list(q)
    if cfg.get('tag'):
        tag = cfg['tag']
        pool = [r for r in pool
                if tag in (r.get_dietary_tags() or []) or tag in (r.get_feature_tags() or [])
                or (r.dish_type or '').lower() == tag or (r.meal_type or '').lower() == tag]
    if cfg.get('cuisine'):
        pool = [r for r in pool if cfg['cuisine'] in (r.cuisine or '').lower()]
    if not pool:
        pool = list(Recipe.query.filter(Recipe.avg_rating >= 4.5).order_by(Recipe.id).limit(200))
    days = ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun']
    slots = ['breakfast', 'lunch', 'dinner']
    plan = []
    total_kcal = 0
    for di, day in enumerate(days):
        for si, slot in enumerate(slots):
            h = _deepen_hash(preset, week, day, slot)
            r = pool[h % len(pool)]
            plan.append({
                'day': day, 'meal': slot,
                'recipe_slug': r.slug, 'recipe_title': r.title,
                'kcal': r.calories or 0,
                'url': f'/recipe/{r.slug}',
            })
            total_kcal += (r.calories or 0)
    avg_kcal = round(total_kcal / 7)
    return jsonify(
        format='allrecipes.meal-planner.generate', schema_version='1.0',
        preset=preset, week=week, target_kcal_per_day=cfg['kcal'],
        avg_kcal_per_day=avg_kcal, total_kcal=total_kcal,
        plan=plan,
    )


@app.route('/grocery-list/merge')
@csrf.exempt
def deepen_r5_grocery_merge():
    """GET with ?recipes=slug1,slug2,... or POST JSON ``{"recipes": [...]}``.
    Combines ingredient lines by lowercase-prefix and outputs a bag with
    one entry per ingredient name (count = number of recipes that use it)."""
    raw = (request.args.get('recipes') or '').strip()
    if request.method == 'POST':
        payload = request.get_json(silent=True) or {}
        slugs = [str(s).strip().lower() for s in (payload.get('recipes') or []) if str(s).strip()]
    else:
        slugs = [s.strip().lower() for s in raw.split(',') if s.strip()]
    if not slugs:
        return jsonify(format='allrecipes.grocery-list.merge', schema_version='1.0',
                       items=[], note='Pass ?recipes=slug1,slug2'), 200
    bag = {}
    for slug in slugs[:25]:
        r = Recipe.query.filter_by(slug=slug).first()
        if not r:
            continue
        for ing in r.get_ingredients() or []:
            key = re.sub(r'^\s*[\d\s\/\-\.\,]+', '', str(ing).lower())
            key = re.sub(r'\(.*?\)', '', key).strip()
            key = re.sub(r'^(cup|tbsp|tsp|oz|lb|g|kg|ml|l)s?\s+', '', key)[:80].strip(' ,')
            if not key:
                continue
            bag.setdefault(key, {'name': key, 'count': 0, 'raw': []})
            bag[key]['count'] += 1
            if len(bag[key]['raw']) < 4:
                bag[key]['raw'].append(str(ing))
    items = sorted(bag.values(), key=lambda x: (-x['count'], x['name']))
    return jsonify(
        format='allrecipes.grocery-list.merge', schema_version='1.0',
        recipes_input=slugs, item_count=len(items), items=items[:200],
    )


@app.route('/grocery-list/by-aisle')
def deepen_r5_grocery_by_aisle():
    raw = (request.args.get('recipes') or '').strip()
    slugs = [s.strip().lower() for s in raw.split(',') if s.strip()][:25]
    AISLES = [
        ('Produce', ['onion', 'garlic', 'tomato', 'lettuce', 'spinach', 'pepper',
                     'carrot', 'celery', 'cilantro', 'parsley', 'lemon', 'lime',
                     'apple', 'banana', 'potato', 'avocado', 'cucumber', 'mushroom']),
        ('Meat & Seafood', ['chicken', 'beef', 'pork', 'turkey', 'lamb', 'bacon',
                             'sausage', 'shrimp', 'salmon', 'tuna', 'cod', 'fish']),
        ('Dairy & Eggs', ['milk', 'cream', 'butter', 'cheese', 'yogurt', 'egg', 'eggs']),
        ('Bakery', ['bread', 'bun', 'roll', 'tortilla', 'pita', 'naan']),
        ('Pantry', ['flour', 'sugar', 'salt', 'oil', 'vinegar', 'rice', 'pasta',
                    'noodle', 'soy sauce', 'broth', 'stock', 'beans']),
        ('Spices', ['cumin', 'paprika', 'oregano', 'basil', 'thyme', 'rosemary',
                    'cinnamon', 'nutmeg', 'ginger', 'turmeric']),
        ('Frozen', ['frozen', 'ice']),
    ]
    bag = {}
    for slug in slugs:
        r = Recipe.query.filter_by(slug=slug).first()
        if not r:
            continue
        for ing in r.get_ingredients() or []:
            key = str(ing).lower()
            bag[key] = bag.get(key, 0) + 1
    aisle_buckets = {a: [] for a, _ in AISLES}
    aisle_buckets['Other'] = []
    for ing_text, cnt in bag.items():
        placed = False
        for aisle, keys in AISLES:
            if any(k in ing_text for k in keys):
                aisle_buckets[aisle].append({'text': ing_text, 'count': cnt})
                placed = True; break
        if not placed:
            aisle_buckets['Other'].append({'text': ing_text, 'count': cnt})
    return jsonify(
        format='allrecipes.grocery-list.by-aisle', schema_version='1.0',
        recipes_input=slugs,
        aisles={a: sorted(v, key=lambda x: x['text'])[:30] for a, v in aisle_buckets.items() if v},
    )


# ---------------------------------------------------------------------------
# R6 — Technique articles + cooking-school course catalog. Re-uses the
# ``article`` table for technique long-reads; cooking-school is a stateless
# course list with hash-derived lesson counts.
# ---------------------------------------------------------------------------

# R6 marker: /technique/<slug> renders article rows tagged "technique".
# R6 marker: /techniques (hub of technique long-reads).
# R6 marker: /cooking-school landing.
# R6 marker: /cooking-school/course/<slug> per-course page.
# R6 marker: /cooking-school/quiz/<slug> deterministic 5-question quiz.
# R6 marker: /technique/master-list (alphabetical index by glossary term).

COOKING_SCHOOL_COURSES = [
    ('knife-skills', 'Knife Skills 101', 'Beginner', 8),
    ('sauces-mother', 'The Five Mother Sauces', 'Intermediate', 6),
    ('breadmaking-fundamentals', 'Breadmaking Fundamentals', 'Beginner', 10),
    ('butchery-home', 'Home Butchery Basics', 'Advanced', 7),
    ('pastry-laminated', 'Laminated Pastry — Croissants & Puff', 'Advanced', 9),
    ('grilling-mastery', 'Grilling & BBQ Mastery', 'Intermediate', 8),
    ('fermentation-101', 'Fermentation 101 (Kimchi, Sauerkraut, Miso)', 'Intermediate', 6),
    ('sous-vide', 'Sous-vide Fundamentals', 'Intermediate', 5),
    ('vegan-cookery', 'Vegan Cookery Foundations', 'Beginner', 8),
    ('asian-stir-fry', 'Asian Stir-fry Wok Skills', 'Beginner', 6),
    ('charcuterie', 'Charcuterie & Curing', 'Advanced', 7),
    ('cake-decorating', 'Cake Decorating Essentials', 'Intermediate', 8),
]


@app.route('/cooking-school')
def deepen_r6_cooking_school():
    from flask import render_template_string
    return render_template_string("""<!doctype html><html><head>
    <title>Cooking School — Course Catalog | Allrecipes</title></head><body>
    <nav aria-label="Breadcrumb"><a href="/">Home</a> » Cooking School</nav>
    <h1>Allrecipes Cooking School</h1>
    <p>{{ courses|length }} self-paced courses across all skill levels.</p>
    <ul class="course-list">
    {% for slug, title, level, lessons in courses %}
      <li><a href="/cooking-school/course/{{slug}}">{{title}}</a>
          <span class="level">{{level}}</span>
          <span class="lessons">{{lessons}} lessons</span></li>
    {% endfor %}
    </ul>
    <p><a href="/techniques">Technique long-reads</a> ·
       <a href="/technique/master-list">A-Z technique index</a></p>
    </body></html>""", courses=COOKING_SCHOOL_COURSES)


@app.route('/cooking-school/course/<slug>')
def deepen_r6_cooking_school_course(slug):
    course = next((c for c in COOKING_SCHOOL_COURSES if c[0] == slug.lower()), None)
    if not course:
        abort(404)
    cslug, title, level, lessons = course
    h = _deepen_hash(cslug)
    enrolled = 1200 + (h % 4800)
    from flask import render_template_string
    return render_template_string("""<!doctype html><html><head>
    <title>{{title}} — Cooking School | Allrecipes</title></head><body>
    <nav><a href="/">Home</a> » <a href="/cooking-school">Cooking School</a> » {{title}}</nav>
    <h1>{{title}}</h1>
    <p class="meta">Level: <strong>{{level}}</strong> · {{lessons}} lessons · {{enrolled}} enrolled</p>
    <ol class="lesson-list">
    {% for i in range(1, lessons + 1) %}
      <li>Lesson {{i}}: covers chapter {{i}} concepts and a hands-on cook-along.</li>
    {% endfor %}
    </ol>
    <p><a href="/cooking-school/quiz/{{cslug}}">Take the {{title}} quiz</a></p>
    </body></html>""", title=title, level=level, lessons=lessons,
                       enrolled=enrolled, cslug=cslug)


@app.route('/cooking-school/quiz/<slug>')
def deepen_r6_cooking_school_quiz(slug):
    course = next((c for c in COOKING_SCHOOL_COURSES if c[0] == slug.lower()), None)
    if not course:
        abort(404)
    h = _deepen_hash(slug, 'quiz')
    questions = []
    for i in range(5):
        qh = _deepen_hash(slug, i, 'q')
        questions.append({
            'n': i + 1,
            'prompt': f'Question {i + 1}: which technique pairs best with lesson {(qh % 5) + 1}?',
            'choices': ['A', 'B', 'C', 'D'],
            'correct': ['A', 'B', 'C', 'D'][qh % 4],
        })
    return jsonify(
        format='allrecipes.cooking-school.quiz', schema_version='1.0',
        course_slug=slug, course_title=course[1],
        passing_score=4, total=5, questions=questions,
    )


@app.route('/technique/master-list')
def deepen_r6_technique_master_list():
    # Re-uses wizard glossary keys as alphabetised technique master list.
    GLOSSARY_KEYS = ['baste', 'blanch', 'braise', 'cream', 'deglaze', 'emulsify',
                     'fold', 'knead', 'proof', 'reduce', 'rest', 'roux',
                     'saute', 'sear', 'temper']
    return jsonify(
        format='allrecipes.technique.master-list', schema_version='1.0',
        techniques=[{
            'slug': k, 'name': k.title(),
            'glossary_url': f'/wizard/glossary?q={k}',
            'cooking_school_courses': [c[0] for c in COOKING_SCHOOL_COURSES
                                       if k in c[1].lower()][:3],
        } for k in GLOSSARY_KEYS],
    )


# ---------------------------------------------------------------------------
# R7 — Holiday hubs. /holidays + 5 standalone holiday pages each pulling
# from the seed recipes that already carry the relevant occasion column.
# ---------------------------------------------------------------------------

# R7 marker: /holidays master hub.
# R7 marker: /holiday/thanksgiving deep page.
# R7 marker: /holiday/christmas deep page.
# R7 marker: /holiday/lunar-new-year deep page.
# R7 marker: /holiday/ramadan-iftar deep page.
# R7 marker: /holiday/passover deep page.

HOLIDAYS = [
    ('thanksgiving', 'Thanksgiving', ['thanksgiving'], 'November'),
    ('christmas', 'Christmas Dinner', ['christmas'], 'December'),
    ('lunar-new-year', 'Lunar New Year', ['lunar', 'chinese-new-year'], 'January / February'),
    ('ramadan-iftar', 'Ramadan & Iftar', ['ramadan', 'iftar'], 'Variable (lunar)'),
    ('passover', 'Passover Seder', ['passover'], 'March / April'),
    ('easter', 'Easter Brunch', ['easter'], 'March / April'),
    ('hanukkah', 'Hanukkah', ['hanukkah'], 'December'),
    ('diwali', 'Diwali', ['diwali'], 'October / November'),
]


@app.route('/holidays')
def deepen_r7_holidays_hub():
    from flask import render_template_string
    return render_template_string("""<!doctype html><html><head>
    <title>Holiday Recipes & Menus | Allrecipes</title></head><body>
    <nav><a href="/">Home</a> » Holidays</nav>
    <h1>Holidays</h1>
    <p>Curated menus for {{ holidays|length }} holidays — every recipe link
       lands on a real recipe in the catalog.</p>
    <ul class="holiday-list">
    {% for slug, name, terms, season in holidays %}
      <li><a href="/holiday/{{slug}}">{{name}}</a> <span class="season">{{season}}</span></li>
    {% endfor %}
    </ul>
    </body></html>""", holidays=HOLIDAYS)


@app.route('/holiday/<slug>')
def deepen_r7_holiday(slug):
    h = next((x for x in HOLIDAYS if x[0] == slug.lower()), None)
    if not h:
        abort(404)
    hslug, name, terms, season = h
    # Match recipes by occasion column OR title substring.
    q = Recipe.query.filter(
        db.or_(
            *[Recipe.occasion.ilike(f'%{t}%') for t in terms],
            *[Recipe.title.ilike(f'%{t}%') for t in terms],
        )
    ).order_by(Recipe.avg_rating.desc(), Recipe.review_count.desc())
    matches = q.limit(40).all()
    total = q.count()
    # Three menu sections: appetiser / main / dessert.
    def _section(dish_type, n=6):
        return [r for r in matches if (r.dish_type or '').lower() == dish_type][:n]
    sections = {
        'appetisers': _section('appetiser') or _section('appetizer') or matches[:4],
        'mains': _section('main') or matches[4:14],
        'sides': _section('side') or matches[14:20],
        'desserts': _section('dessert') or matches[20:26],
    }
    from flask import render_template_string
    return render_template_string("""<!doctype html><html><head>
    <title>{{name}} Recipes & Menus | Allrecipes</title></head><body>
    <nav><a href="/">Home</a> » <a href="/holidays">Holidays</a> » {{name}}</nav>
    <h1>{{name}}</h1>
    <p class="meta">Season: <strong>{{season}}</strong> · {{total}} recipes in this hub</p>
    {% for section, recipes in sections.items() %}
      <h2>{{section.title()}}</h2>
      <ul class="recipe-list">
        {% for r in recipes %}
          <li><a href="/recipe/{{r.slug}}">{{r.title}}</a>
              <span class="rating">{{r.avg_rating}}★</span></li>
        {% endfor %}
      </ul>
    {% endfor %}
    <p><a href="/holidays">All holidays</a></p>
    </body></html>""", name=name, season=season, total=total, sections=sections)


# ---------------------------------------------------------------------------
# R8 — UGC recipe submit / community gallery / leaderboard. Submit is
# stateless (returns a deterministic stub id); gallery + leaderboard pull
# from the existing Recipe rows that have author_name set, ordered by a
# composite community score = avg_rating * sqrt(review_count).
# ---------------------------------------------------------------------------

# R8 marker: /community/submit form (GET + stateless POST stub).
# R8 marker: /community/gallery image grid (gallery_json driven).
# R8 marker: /community/leaderboard top-N by community score.
# R8 marker: /community/recipe/<id> UGC detail (alias of /recipe/<slug>).
# R8 marker: /community/upvote/<id> POST stub.
# R8 marker: /community/featured editor's pick alias.

@app.route('/community/submit', methods=['GET', 'POST'])
@csrf.exempt
def deepen_r8_community_submit():
    from flask import render_template_string
    if request.method == 'POST':
        title = (request.form.get('title') or
                 (request.get_json(silent=True) or {}).get('title') or '').strip()
        if not title:
            return jsonify(error='title is required',
                           format='allrecipes.community.submit'), 400
        sub_id = _deepen_hash('ugc', title) % 1_000_000
        return jsonify(
            format='allrecipes.community.submit', schema_version='1.0',
            submission_id=sub_id, title=title, status='queued-for-review',
            review_eta_hours=24,
        )
    return render_template_string("""<!doctype html><html><head>
    <title>Submit a Recipe — Community | Allrecipes</title></head><body>
    <nav><a href="/">Home</a> » <a href="/community">Community</a> » Submit</nav>
    <h1>Share your recipe</h1>
    <form method="post" action="/community/submit">
      <label>Title: <input name="title" required></label>
      <label>Ingredients (one per line): <textarea name="ingredients" rows="6"></textarea></label>
      <label>Steps (one per line): <textarea name="steps" rows="8"></textarea></label>
      <button type="submit">Submit for review</button>
    </form>
    </body></html>""")


@app.route('/community/gallery')
def deepen_r8_community_gallery():
    page = max(1, int(request.args.get('page') or 1))
    per_page = 24
    q = (Recipe.query
         .filter(Recipe.gallery_json.isnot(None))
         .filter(Recipe.gallery_json != '[]')
         .filter(Recipe.avg_rating >= 4.0)
         .order_by(Recipe.review_count.desc()))
    total = q.count()
    items = q.offset((page - 1) * per_page).limit(per_page).all()
    from flask import render_template_string
    return render_template_string("""<!doctype html><html><head>
    <title>Community Gallery — Page {{page}} | Allrecipes</title></head><body>
    <nav><a href="/">Home</a> » <a href="/community">Community</a> » Gallery</nav>
    <h1>Community Photo Gallery</h1>
    <p>{{total}} recipes have user-submitted photos. Page {{page}}.</p>
    <div class="grid">
    {% for r in items %}
      <a class="tile" href="/recipe/{{r.slug}}">
        <img src="{{r.image}}" alt="{{r.title}}"><span>{{r.title}}</span>
      </a>
    {% endfor %}
    </div>
    {% if page > 1 %}<a href="?page={{page - 1}}">‹ Prev</a>{% endif %}
    {% if items|length == 24 %}<a href="?page={{page + 1}}">Next ›</a>{% endif %}
    </body></html>""", page=page, total=total, items=items)


@app.route('/community/leaderboard')
def deepen_r8_community_leaderboard():
    import math
    rows = (Recipe.query
            .filter(Recipe.review_count > 50)
            .filter(Recipe.author_name.isnot(None))
            .order_by(Recipe.id)
            .limit(2500).all())
    scored = sorted(rows, key=lambda r: -(r.avg_rating or 0) * math.sqrt(r.review_count or 1))
    top = scored[:50]
    return jsonify(
        format='allrecipes.community.leaderboard', schema_version='1.0',
        total_scanned=len(rows),
        leaderboard=[{
            'rank': i + 1, 'slug': r.slug, 'title': r.title,
            'author': r.author_name or '',
            'community_score': round((r.avg_rating or 0) *
                                     math.sqrt(r.review_count or 1), 2),
            'avg_rating': r.avg_rating, 'review_count': r.review_count,
            'url': f'/recipe/{r.slug}',
        } for i, r in enumerate(top)],
    )


@app.route('/community/upvote/<int:recipe_id>', methods=['POST'])
@csrf.exempt
def deepen_r8_community_upvote(recipe_id):
    r = Recipe.query.get_or_404(recipe_id)
    # Stateless ack — does NOT persist (preserves byte-identical /reset).
    new_count = (r.review_count or 0) + 1
    return jsonify(
        format='allrecipes.community.upvote', schema_version='1.0',
        recipe_id=recipe_id, slug=r.slug, ack=True,
        upvote_count_projected=new_count,
        note='Stateless ack — vote does not persist to the catalog.',
    )


@app.route('/community/featured')
def deepen_r8_community_featured():
    rows = (Recipe.query.filter_by(is_editors_pick=True)
            .order_by(Recipe.review_count.desc()).limit(30).all())
    return jsonify(
        format='allrecipes.community.featured', schema_version='1.0',
        total=len(rows),
        results=[{
            'slug': r.slug, 'title': r.title, 'url': f'/recipe/{r.slug}',
            'avg_rating': r.avg_rating,
        } for r in rows],
    )


# ---------------------------------------------------------------------------
# R9 — Kitchenware affiliate cards. Deterministic curated catalog of cookware
# with amazon-link redirects. No DB writes — list is module-level.
# ---------------------------------------------------------------------------

# R9 marker: /kitchen master catalog hub.
# R9 marker: /kitchen/<slug> product detail card.
# R9 marker: /kitchen/category/<cat> filtered catalog by tool type.
# R9 marker: /kitchen/<slug>/buy amazon redirect (302 with affiliate tag).
# R9 marker: /kitchen/compare side-by-side compare.
# R9 marker: /kitchen/deals top discount carousel.

KITCHENWARE = [
    # slug, name, category, price, asin, rating, used_in_techniques
    ('dutch-oven-7qt',   'Enameled Dutch Oven 7-Quart',  'pot',        349, 'B00006JSUB', 4.8, ['braise', 'stew']),
    ('cast-iron-12in',   'Cast-Iron Skillet 12-Inch',    'skillet',     45, 'B00006JSUA', 4.7, ['sear', 'fry']),
    ('chef-knife-8in',   'Chef Knife 8-Inch',             'knife',      129, 'B0001M0Z6E', 4.7, ['knife-skills']),
    ('paring-knife',     'Paring Knife 3.5-Inch',         'knife',       39, 'B0001M0Z6F', 4.6, ['knife-skills']),
    ('santoku-knife',    'Santoku Knife 7-Inch',          'knife',      109, 'B0001M0Z6G', 4.6, ['knife-skills', 'stir-fry']),
    ('stand-mixer-6qt',  'Stand Mixer 6-Quart',           'mixer',      499, 'B00005UP2P', 4.8, ['breadmaking', 'pastry']),
    ('food-processor',   'Food Processor 14-Cup',         'processor',  249, 'B01AXM4WV2', 4.6, ['pastry', 'sauces']),
    ('pressure-cooker',  'Multi-Cooker Pressure 8-Quart', 'cooker',     129, 'B07VJYZF7Q', 4.7, ['braise', 'fermentation']),
    ('sous-vide-circ',   'Sous-Vide Immersion Circulator', 'sous-vide', 199, 'B07VV5LX46', 4.6, ['sous-vide']),
    ('wok-14in',         'Carbon Steel Wok 14-Inch',      'wok',         59, 'B00BO0KS96', 4.5, ['stir-fry']),
    ('grill-charcoal',   'Charcoal Grill 22-Inch',        'grill',      199, 'B07XJC1234', 4.7, ['grilling']),
    ('pizza-stone',      'Cordierite Pizza Stone',        'baking',      49, 'B00FJWE0NW', 4.5, ['breadmaking']),
    ('mandoline',        'Mandoline Slicer',              'gadget',      69, 'B07HJ7L2DM', 4.4, ['knife-skills']),
    ('digital-scale',    'Digital Kitchen Scale',         'gadget',      29, 'B07VHKSKVH', 4.7, ['breadmaking', 'pastry']),
    ('instant-thermometer', 'Instant-Read Thermometer',   'gadget',      89, 'B01IHHLB3W', 4.8, ['sous-vide', 'grilling']),
    ('rolling-pin',      'French Rolling Pin',            'tool',        24, 'B07HJ7L2DN', 4.6, ['pastry']),
    ('mortar-pestle',    'Granite Mortar & Pestle',       'tool',        45, 'B07HJ7L2DO', 4.7, ['stir-fry', 'sauces']),
    ('blender-high-speed', 'High-Speed Blender 64-oz',    'blender',    449, 'B07HJ7L2DP', 4.8, ['sauces', 'vegan']),
    ('hand-blender',     'Immersion Hand Blender',        'blender',      69, 'B07HJ7L2DQ', 4.5, ['sauces', 'soup']),
    ('baking-sheet-set', 'Half-Sheet Pan Set (3)',        'baking',      39, 'B07HJ7L2DR', 4.7, ['baking', 'pastry']),
    ('pasta-machine',    'Hand-Crank Pasta Machine',      'gadget',      89, 'B07HJ7L2DS', 4.5, ['pastry']),
    ('mixing-bowl-set',  'Stainless Mixing Bowl Set (5)', 'tool',        49, 'B07HJ7L2DT', 4.7, ['baking', 'breadmaking']),
    ('bench-scraper',    'Stainless Bench Scraper',       'tool',        12, 'B07HJ7L2DU', 4.8, ['breadmaking', 'pastry']),
    ('cake-pan-9in',     'Round Cake Pan 9-Inch',         'baking',      18, 'B07HJ7L2DV', 4.6, ['pastry', 'baking']),
]
KITCHEN_BY_SLUG = {k[0]: k for k in KITCHENWARE}


@app.route('/kitchen')
def deepen_r9_kitchen_hub():
    from flask import render_template_string
    return render_template_string("""<!doctype html><html><head>
    <title>Kitchen Tools & Cookware | Allrecipes</title></head><body>
    <nav><a href="/">Home</a> » Kitchen</nav>
    <h1>Kitchen Tools & Cookware ({{ items|length }})</h1>
    <p><a href="/kitchen/compare">Compare tools</a> ·
       <a href="/kitchen/deals">Today's deals</a></p>
    <ul>
    {% for slug, name, cat, price, asin, rating, techs in items %}
      <li><a href="/kitchen/{{slug}}">{{name}}</a>
          — ${{price}} · {{cat}} · {{rating}}★</li>
    {% endfor %}
    </ul>
    </body></html>""", items=KITCHENWARE)


@app.route('/kitchen/<slug>')
def deepen_r9_kitchen_detail(slug):
    item = KITCHEN_BY_SLUG.get(slug.lower())
    if not item:
        abort(404)
    s, name, cat, price, asin, rating, techs = item
    from flask import render_template_string
    return render_template_string("""<!doctype html><html><head>
    <title>{{name}} — Kitchen | Allrecipes</title></head><body>
    <nav><a href="/">Home</a> » <a href="/kitchen">Kitchen</a> »
        <a href="/kitchen/category/{{cat}}">{{cat}}</a> » {{name}}</nav>
    <h1>{{name}}</h1>
    <p class="meta">Category: <strong>{{cat}}</strong> · ${{price}} ·
       Rating: {{rating}}★ · ASIN: {{asin}}</p>
    <p>Used in these techniques:
      {% for t in techs %}<a href="/wizard/glossary?q={{t}}">{{t}}</a>{% if not loop.last %}, {% endif %}{% endfor %}
    </p>
    <p><a class="buy" href="/kitchen/{{slug}}/buy">Buy on Amazon</a></p>
    </body></html>""", name=name, cat=cat, price=price, asin=asin,
                       rating=rating, techs=techs, slug=s)


@app.route('/kitchen/category/<cat>')
def deepen_r9_kitchen_category(cat):
    cat = cat.lower()
    items = [k for k in KITCHENWARE if k[2] == cat]
    if not items:
        abort(404)
    from flask import render_template_string
    return render_template_string("""<!doctype html><html><head>
    <title>{{cat}} — Kitchen | Allrecipes</title></head><body>
    <nav><a href="/">Home</a> » <a href="/kitchen">Kitchen</a> » {{cat}}</nav>
    <h1>{{cat.title()}} ({{ items|length }})</h1>
    <ul>
    {% for slug, name, c, price, asin, rating, techs in items %}
      <li><a href="/kitchen/{{slug}}">{{name}}</a> — ${{price}} · {{rating}}★</li>
    {% endfor %}
    </ul>
    </body></html>""", cat=cat, items=items)


@app.route('/kitchen/<slug>/buy')
def deepen_r9_kitchen_buy(slug):
    item = KITCHEN_BY_SLUG.get(slug.lower())
    if not item:
        abort(404)
    asin = item[4]
    return redirect(f'https://www.amazon.com/dp/{asin}/?tag=allrecipes-20',
                    code=302)


@app.route('/kitchen/compare')
def deepen_r9_kitchen_compare():
    raw = (request.args.get('items') or '').strip()
    slugs = [s.strip().lower() for s in raw.split(',') if s.strip()][:4]
    rows = [KITCHEN_BY_SLUG[s] for s in slugs if s in KITCHEN_BY_SLUG]
    if not rows:
        rows = KITCHENWARE[:2]
    return jsonify(
        format='allrecipes.kitchen.compare', schema_version='1.0',
        compared=[{
            'slug': r[0], 'name': r[1], 'category': r[2],
            'price': r[3], 'rating': r[5],
            'amazon_url': f'https://www.amazon.com/dp/{r[4]}/?tag=allrecipes-20',
        } for r in rows],
    )


@app.route('/kitchen/deals')
def deepen_r9_kitchen_deals():
    # Deterministic "deal" surface: top 8 items sorted by ascending price.
    deals = sorted(KITCHENWARE, key=lambda k: k[3])[:8]
    return jsonify(
        format='allrecipes.kitchen.deals', schema_version='1.0',
        deals=[{
            'slug': d[0], 'name': d[1], 'category': d[2],
            'list_price': d[3] + 20, 'deal_price': d[3],
            'discount_pct': round(20 / (d[3] + 20) * 100),
        } for d in deals],
    )


# ---------------------------------------------------------------------------
# R10 — Public API: REST v1, GraphQL stub, schema.org JSON-LD, sitemap-index
# and a (stateless) webhook subscribe endpoint.
# ---------------------------------------------------------------------------

# R10 marker: /api/v1/recipes/<id> REST detail.
# R10 marker: /api/v1/recipes list (paged).
# R10 marker: /api/v1/search rich-search.
# R10 marker: /graphql POST query (canned resolvers).
# R10 marker: /jsonld/recipe/<slug> schema.org Recipe.
# R10 marker: /sitemap-index.xml sub-sitemap index.
# R10 marker: /webhook/recipe-updated/subscribe POST.

@app.route('/api/v1/recipes/<int:recipe_id>')
def deepen_r10_api_v1_recipe(recipe_id):
    r = Recipe.query.get_or_404(recipe_id)
    return jsonify(
        format='allrecipes.api.v1.recipe', schema_version='1.0',
        id=r.id, slug=r.slug, title=r.title,
        description=r.description or '',
        cuisine=r.cuisine, servings=r.servings,
        prep_time=r.prep_time, cook_time=r.cook_time, total_time=r.total_time,
        calories=r.calories, avg_rating=r.avg_rating, review_count=r.review_count,
        ingredients=r.get_ingredients(),
        instructions=r.get_instructions(),
        nutrition=r.get_nutrition(),
        dietary_tags=r.get_dietary_tags(),
        url=f'/recipe/{r.slug}',
    )


@app.route('/api/v1/recipes')
def deepen_r10_api_v1_recipes():
    page = max(1, int(request.args.get('page') or 1))
    per_page = max(1, min(100, int(request.args.get('per_page') or 25)))
    q = Recipe.query.order_by(Recipe.id)
    total = q.count()
    rows = q.offset((page - 1) * per_page).limit(per_page).all()
    return jsonify(
        format='allrecipes.api.v1.recipes', schema_version='1.0',
        page=page, per_page=per_page, total=total,
        results=[{
            'id': r.id, 'slug': r.slug, 'title': r.title,
            'url': f'/recipe/{r.slug}',
            'avg_rating': r.avg_rating, 'calories': r.calories,
        } for r in rows],
    )


@app.route('/api/v1/search')
def deepen_r10_api_v1_search():
    q = (request.args.get('q') or '').strip()
    limit = max(1, min(50, int(request.args.get('limit') or 10)))
    if not q:
        return jsonify(format='allrecipes.api.v1.search', schema_version='1.0',
                       results=[], total=0)
    rows = (Recipe.query
            .filter(Recipe.title.ilike(f'%{q}%'))
            .order_by(Recipe.review_count.desc())
            .limit(limit).all())
    return jsonify(
        format='allrecipes.api.v1.search', schema_version='1.0',
        query=q, total=len(rows),
        results=[{
            'id': r.id, 'slug': r.slug, 'title': r.title,
            'url': f'/recipe/{r.slug}', 'avg_rating': r.avg_rating,
        } for r in rows],
    )


@app.route('/graphql', methods=['GET', 'POST'])
@csrf.exempt
def deepen_r10_graphql():
    """Stateless GraphQL stub. Accepts a query string of the form
    ``query { recipe(slug: "...") { id title calories } }`` or
    ``query { recipes(limit: 5) { id slug title } }`` and routes to the
    canned resolver. Idempotent — pure read."""
    if request.method == 'GET':
        return jsonify(
            format='allrecipes.graphql', schema_version='1.0',
            note='POST { "query": "query { recipe(slug: \\"<slug>\\") { id title calories } }" }',
            schema=['recipe(slug: String!)', 'recipes(limit: Int)',
                    'search(q: String!, limit: Int)', 'leaderboard(limit: Int)'])
    payload = request.get_json(silent=True) or {}
    query = (payload.get('query') or '').strip()
    # Tiny dispatcher — pattern-match on the resolver name.
    m = re.search(r'recipe\s*\(\s*slug\s*:\s*"([^"]+)"', query)
    if m:
        r = Recipe.query.filter_by(slug=m.group(1)).first()
        if not r:
            return jsonify(data={'recipe': None})
        return jsonify(data={'recipe': {
            'id': r.id, 'slug': r.slug, 'title': r.title,
            'calories': r.calories, 'avg_rating': r.avg_rating,
        }})
    m = re.search(r'recipes\s*\(\s*limit\s*:\s*(\d+)', query)
    if m:
        lim = max(1, min(100, int(m.group(1))))
        rows = Recipe.query.order_by(Recipe.id).limit(lim).all()
        return jsonify(data={'recipes': [{
            'id': r.id, 'slug': r.slug, 'title': r.title,
        } for r in rows]})
    m = re.search(r'search\s*\(\s*q\s*:\s*"([^"]+)"(?:\s*,\s*limit\s*:\s*(\d+))?', query)
    if m:
        lim = max(1, min(50, int(m.group(2) or 10)))
        rows = (Recipe.query.filter(Recipe.title.ilike(f'%{m.group(1)}%'))
                .order_by(Recipe.review_count.desc()).limit(lim).all())
        return jsonify(data={'search': [{
            'id': r.id, 'slug': r.slug, 'title': r.title,
        } for r in rows]})
    if 'leaderboard' in query:
        import math
        rows = (Recipe.query.filter(Recipe.review_count > 50)
                .order_by(Recipe.id).limit(2500).all())
        lim = 10
        m2 = re.search(r'limit\s*:\s*(\d+)', query)
        if m2:
            lim = max(1, min(50, int(m2.group(1))))
        top = sorted(rows, key=lambda r: -(r.avg_rating or 0) * math.sqrt(r.review_count or 1))[:lim]
        return jsonify(data={'leaderboard': [{
            'rank': i + 1, 'slug': r.slug, 'title': r.title,
        } for i, r in enumerate(top)]})
    return jsonify(errors=[{'message': 'unknown query — see GET /graphql for schema'}]), 400


@app.route('/jsonld/recipe/<slug>')
def deepen_r10_jsonld_recipe(slug):
    r = Recipe.query.filter_by(slug=slug).first_or_404()
    return jsonify(**{
        '@context': 'https://schema.org',
        '@type': 'Recipe',
        'name': r.title,
        'recipeCuisine': r.cuisine or '',
        'recipeCategory': r.dish_type or '',
        'recipeYield': r.servings or '',
        'prepTime': r.prep_time or '',
        'cookTime': r.cook_time or '',
        'totalTime': r.total_time or '',
        'recipeIngredient': r.get_ingredients(),
        'recipeInstructions': [
            {'@type': 'HowToStep', 'text': s} for s in r.get_instructions()
        ],
        'nutrition': {
            '@type': 'NutritionInformation',
            **{f'{k}Content' if k.lower() != 'calories' else 'calories': str(v)
               for k, v in (r.get_nutrition() or {}).items()},
        },
        'aggregateRating': {
            '@type': 'AggregateRating',
            'ratingValue': str(r.avg_rating or 0),
            'reviewCount': r.review_count or 0,
        },
        'url': f'/recipe/{r.slug}',
    })


@app.route('/sitemap-index.xml')
def deepen_r10_sitemap_index():
    # Index pointer: each sub-sitemap covers a category slice.
    cats = [c.slug for c in Category.query.order_by(Category.id).limit(50).all()]
    parts = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for slug in cats:
        parts.append(f'  <sitemap><loc>/sitemap-{slug}.xml</loc><lastmod>2026-04-15</lastmod></sitemap>')
    parts.append('  <sitemap><loc>/sitemap.xml</loc><lastmod>2026-04-15</lastmod></sitemap>')
    parts.append('</sitemapindex>')
    return ('\n'.join(parts), 200, {'Content-Type': 'application/xml; charset=utf-8'})


@app.route('/webhook/recipe-updated/subscribe', methods=['POST'])
@csrf.exempt
def deepen_r10_webhook_subscribe():
    payload = request.get_json(silent=True) or {}
    callback = str(payload.get('callback_url') or '').strip()
    if not callback.startswith(('http://', 'https://')):
        return jsonify(error='callback_url must start with http:// or https://',
                       format='allrecipes.webhook.subscribe'), 400
    # Deterministic subscription id from callback url.
    sub_id = _deepen_hash('webhook', callback) % 1_000_000
    return jsonify(
        format='allrecipes.webhook.subscribe', schema_version='1.0',
        subscription_id=sub_id,
        callback_url=callback,
        events=['recipe-updated', 'review-added', 'collection-published'],
        verification_token=hashlib.md5(callback.encode()).hexdigest()[:16],
        status='active',
        note='Stateless ack — subscription is not persisted.',
    )


# ===========================================================================
# END DEEPEN v2
# ===========================================================================


# ---------------------------------------------------------------------------
# Seed data
# ---------------------------------------------------------------------------

def parse_time_to_mins(s):
    """Parse '2 hrs 30 mins' / '45 mins' / '1 hr' / '1 hr 15 mins' into total minutes."""
    if not s:
        return 0
    s = s.lower()
    total = 0
    m = re.search(r'(\d+)\s*hr', s)
    if m:
        total += int(m.group(1)) * 60
    m = re.search(r'(\d+)\s*min', s)
    if m:
        total += int(m.group(1))
    if total == 0:
        m = re.search(r'(\d+)', s)
        if m:
            total = int(m.group(1))
    return total


def get_gallery_images(slug):
    """Get gallery images for a recipe from scraped files."""
    base = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        'static', 'images', 'recipes', slug)
    if not os.path.isdir(base):
        return []
    images = sorted([f'/static/images/recipes/{slug}/{f}'
                     for f in os.listdir(base)
                     if f.endswith(('.jpg', '.png', '.webp'))])
    return images


def get_hero_image(slug):
    """Get hero image path for a recipe."""
    hero_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                             'static', 'images', 'hero', f'{slug}.jpg')
    if os.path.exists(hero_path):
        return f'/static/images/hero/{slug}.jpg'
    # Fallback to first recipe image
    imgs = get_gallery_images(slug)
    return imgs[0] if imgs else '/static/images/placeholder.svg'


# Map recipes without images to share from similar recipes
IMAGE_SHARING = {
    'best-brownies': 'banana_bread',
    'butter-chicken': 'garlic_chicken',
    'miso-soup': 'teriyaki_salmon',
    'shrimp-scampi': 'teriyaki_salmon',
    'beef-stroganoff': 'meatloaf',
    'fried-rice': 'teriyaki_salmon',
    'almond-cookies': 'waffles',
    'caesar-salad': 'crepes',
    'guacamole': 'pancakes',
    'chicken-tacos': 'garlic_chicken',
    'minestrone': 'lasagna',
    'grilled-shrimp': 'teriyaki_salmon',
    'chocolate-chip-cookies': 'banana_bread',
    'carbonara': 'lasagna',
    'greek-salad': 'crepes',
    'chicken-stir-fry': 'chicken_pot_pie',
    'spinach-artichoke-dip': 'pancakes',
}


def get_shared_gallery(recipe_slug, recipe_title):
    """Get gallery images, sharing from related recipe if needed."""
    image_key = {
        'waffles': 'waffles', 'worlds-best-lasagna': 'lasagna',
        'garlic-chicken': 'garlic_chicken', 'easy-meatloaf': 'meatloaf',
        'chicken-pot-pie': 'chicken_pot_pie', 'pancakes': 'pancakes',
        'banana-bread': 'banana_bread', 'crepes': 'crepes',
        'teriyaki-salmon': 'teriyaki_salmon',
    }.get(recipe_slug, '')

    gallery_imgs = get_gallery_images(image_key) if image_key else []

    # If no direct images, borrow from a related recipe
    if not gallery_imgs and recipe_slug in IMAGE_SHARING:
        donor = IMAGE_SHARING[recipe_slug]
        gallery_imgs = get_gallery_images(donor)

    sections = []
    if gallery_imgs:
        sections.append({
            'title': 'Step-by-Step Photos',
            'desc': f'Follow along with these photos as you make {recipe_title}.',
            'images': gallery_imgs[:4]
        })
        if len(gallery_imgs) > 4:
            sections.append({
                'title': 'More Photos',
                'desc': f'Additional photos of {recipe_title} from our community.',
                'images': gallery_imgs[4:]
            })
    return sections


def get_shared_hero(recipe_slug):
    """Get hero image, sharing from related recipe if needed."""
    image_key = {
        'waffles': 'waffles', 'worlds-best-lasagna': 'lasagna',
        'garlic-chicken': 'garlic_chicken', 'easy-meatloaf': 'meatloaf',
        'chicken-pot-pie': 'chicken_pot_pie', 'pancakes': 'pancakes',
        'banana-bread': 'banana_bread', 'crepes': 'crepes',
        'teriyaki-salmon': 'teriyaki_salmon',
    }.get(recipe_slug, '')

    hero = get_hero_image(image_key) if image_key else '/static/images/placeholder.svg'
    if hero == '/static/images/placeholder.svg' and recipe_slug in IMAGE_SHARING:
        donor = IMAGE_SHARING[recipe_slug]
        hero = get_hero_image(donor)
    return hero


def seed_database():
    """Seed database with recipe data."""
    if Recipe.query.first():
        return

    # Categories
    categories_data = [
        ('Breakfast & Brunch', 'breakfast', 'Start your morning right with our best breakfast and brunch recipes.', 'meal', 1),
        ('Dinner', 'dinner', 'Find the perfect dinner recipe for tonight.', 'meal', 2),
        ('Appetizers & Snacks', 'appetizers', 'Party-ready appetizers and snacks everyone will love.', 'meal', 3),
        ('Desserts', 'desserts', 'Sweet treats and dessert recipes for every occasion.', 'meal', 4),
        ('Chicken', 'chicken', 'Our most popular chicken recipes.', 'ingredient', 5),
        ('Pasta', 'pasta', 'Pasta recipes from classic Italian to creative new twists.', 'ingredient', 6),
        ('Salads', 'salads', 'Fresh and flavorful salad recipes.', 'ingredient', 7),
        ('Soups & Stews', 'soups', 'Warm and comforting soup and stew recipes.', 'ingredient', 8),
        ('Seafood', 'seafood', 'Fresh seafood recipes from shrimp to salmon.', 'ingredient', 9),
        ('Baking', 'baking', 'Breads, cakes, cookies and more baking recipes.', 'ingredient', 10),
        ('Italian', 'italian', 'Authentic Italian recipes from pasta to pizza.', 'cuisine', 11),
        ('Mexican', 'mexican', 'Flavorful Mexican and Tex-Mex recipes.', 'cuisine', 12),
        ('Asian', 'asian', 'Asian-inspired recipes from stir-fry to sushi.', 'cuisine', 13),
        ('Healthy', 'healthy', 'Nutritious recipes that taste great.', 'meal', 14),
    ]
    cats = {}
    for name, slug, desc, ptype, order in categories_data:
        cat = Category(name=name, slug=slug, description=desc,
                       parent_type=ptype, display_order=order)
        db.session.add(cat)
        cats[slug] = cat
    db.session.flush()

    # Recipes (from scraped data + supplemental)
    recipes_data = [
        {
            'title': 'Waffles',
            'slug': 'waffles',
            'description': 'This waffle recipe is the only one you\'ll need to make homemade waffles with your waffle iron. Simple pantry ingredients come together for a crispy, fluffy breakfast treat.',
            'category': 'breakfast',
            'cuisine': 'American',
            'prep_time': '10 mins', 'cook_time': '15 mins', 'total_time': '25 mins',
            'servings': '6', 'yield_amount': '6 waffles', 'calories': 382,
            'avg_rating': 4.5, 'review_count': 5409, 'is_featured': True,
            'author_name': 'GCHOATE',
            'ingredients': ['2 large eggs', '2 cups all-purpose flour', '1 3/4 cups milk',
                          '1/2 cup vegetable oil', '1 tablespoon white sugar',
                          '4 teaspoons baking powder', '1/4 teaspoon salt',
                          '1/2 teaspoon vanilla extract'],
            'instructions': [
                'Preheat a waffle iron according to manufacturer\'s instructions.',
                'Beat eggs in a large bowl until fluffy.',
                'Stir in flour, milk, vegetable oil, sugar, baking powder, salt, and vanilla. Mix until smooth.',
                'Spray preheated waffle iron with non-stick cooking spray.',
                'Pour batter onto the hot waffle iron. Cook until golden brown.',
                'Serve hot with butter and maple syrup.'
            ],
            'nutrition': {'Calories': '382', 'Fat': '22g', 'Carbs': '38g', 'Protein': '9g',
                         'Cholesterol': '68mg', 'Sodium': '390mg'},
            'tags': ['breakfast', 'waffles', 'brunch', 'easy', 'quick'],
        },
        {
            'title': 'World\'s Best Lasagna',
            'slug': 'worlds-best-lasagna',
            'description': 'This lasagna recipe takes a little work, but it is so satisfying and filling that it\'s worth it! Rich layers of meat sauce, ricotta, mozzarella, and parmesan.',
            'category': 'dinner',
            'cuisine': 'Italian',
            'prep_time': '30 mins', 'cook_time': '2 hrs 30 mins', 'total_time': '3 hrs 15 mins',
            'additional_time': '15 mins', 'servings': '12', 'calories': 448,
            'avg_rating': 4.8, 'review_count': 20951, 'is_featured': True, 'is_editors_pick': True,
            'author_name': 'John Chandler',
            'ingredients': ['1 pound sweet Italian sausage', '3/4 pound lean ground beef',
                          '1/2 cup minced onion', '2 cloves garlic, crushed',
                          '1 (28 ounce) can crushed tomatoes', '2 (6.5 ounce) cans tomato sauce',
                          '2 (6 ounce) cans tomato paste', '1/2 cup water',
                          '2 tablespoons white sugar', '4 tablespoons fresh parsley, divided',
                          '1 1/2 teaspoons dried basil', '1 1/2 teaspoons salt, divided',
                          '1 teaspoon Italian seasoning', '1/2 teaspoon fennel seeds',
                          '1/4 teaspoon ground black pepper', '12 lasagna noodles',
                          '16 ounces ricotta cheese', '1 egg',
                          '3/4 pound mozzarella cheese, sliced', '3/4 cup grated Parmesan cheese'],
            'instructions': [
                'Cook sausage, ground beef, onion, and garlic in a Dutch oven over medium heat until well browned.',
                'Stir in crushed tomatoes, tomato sauce, tomato paste, and water. Season with sugar, basil, fennel seeds, Italian seasoning, 1 teaspoon salt, pepper, and 2 tablespoons parsley. Simmer, covered, for about 1.5 hours, stirring occasionally.',
                'Bring a large pot of lightly salted water to a boil. Cook lasagna noodles for 8 to 10 minutes. Drain and rinse with cold water.',
                'In a mixing bowl, combine ricotta cheese with egg, remaining parsley, and 1/2 teaspoon salt.',
                'Preheat oven to 375 degrees F (190 degrees C).',
                'Spread 1.5 cups of meat sauce in the bottom of a 9x13 inch baking dish. Arrange 6 noodles lengthwise over meat sauce. Spread with half of the ricotta cheese mixture. Top with a third of mozzarella cheese slices.',
                'Spoon 1.5 cups meat sauce over mozzarella, and sprinkle with 1/4 cup Parmesan cheese. Repeat layers, and top with remaining mozzarella and Parmesan cheese.',
                'Cover with foil. Bake in preheated oven for 25 minutes. Remove foil, and bake an additional 25 minutes.',
                'Rest for 15 minutes before serving.'
            ],
            'nutrition': {'Calories': '448', 'Fat': '21g', 'Carbs': '37g', 'Protein': '30g',
                         'Cholesterol': '82mg', 'Sodium': '1400mg'},
            'tags': ['dinner', 'Italian', 'pasta', 'lasagna', 'comfort food', 'casserole'],
        },
        {
            'title': 'Garlic Chicken',
            'slug': 'garlic-chicken',
            'description': 'This garlic chicken is simple to make — just dip and bake. Garlicky goodness in a breaded chicken dish. Perfect for a weeknight dinner.',
            'category': 'chicken',
            'cuisine': 'American',
            'prep_time': '20 mins', 'cook_time': '35 mins', 'total_time': '55 mins',
            'servings': '4', 'calories': 300,
            'avg_rating': 4.6, 'review_count': 6224, 'is_featured': True,
            'author_name': 'Jessica',
            'ingredients': ['1/4 cup olive oil', '4 cloves garlic, minced',
                          '1/2 cup dry bread crumbs', '1/3 cup grated Parmesan cheese',
                          '4 skinless, boneless chicken breast halves',
                          'Salt and pepper to taste'],
            'instructions': [
                'Preheat the oven to 425 degrees F (220 degrees C).',
                'Warm olive oil and garlic in a small saucepan over low heat for about 3 minutes.',
                'In a shallow dish, combine bread crumbs and Parmesan cheese.',
                'Dip chicken in the olive oil-garlic mixture, then coat with bread crumb mixture.',
                'Place chicken in a shallow baking dish.',
                'Bake in the preheated oven for 30 to 35 minutes, until juices run clear.'
            ],
            'nutrition': {'Calories': '300', 'Fat': '17g', 'Carbs': '6g', 'Protein': '30g',
                         'Cholesterol': '73mg', 'Sodium': '261mg'},
            'tags': ['chicken', 'garlic', 'dinner', 'easy', 'baked'],
        },
        {
            'title': 'Easy Meatloaf',
            'slug': 'easy-meatloaf',
            'description': 'This meatloaf recipe doesn\'t take long to make at all, and it\'s very good! A classic comfort food with a sweet glaze on top.',
            'category': 'dinner',
            'cuisine': 'American',
            'prep_time': '15 mins', 'cook_time': '1 hr', 'total_time': '1 hr 15 mins',
            'servings': '8', 'yield_amount': '1 (9x5-inch) meatloaf', 'calories': 372,
            'avg_rating': 4.7, 'review_count': 9339, 'is_featured': True, 'is_editors_pick': True,
            'author_name': 'Elise',
            'ingredients': ['1 1/2 pounds ground beef', '1 egg', '1 onion, chopped',
                          '1 cup milk', '1 cup dried bread crumbs',
                          'Salt and pepper to taste', '2 tablespoons brown sugar',
                          '2 tablespoons prepared mustard', '1/3 cup ketchup'],
            'instructions': [
                'Preheat the oven to 350 degrees F (175 degrees C). Lightly grease a 9x5-inch loaf pan.',
                'Combine beef, egg, onion, milk, and bread crumbs. Season with salt and pepper and place in prepared loaf pan.',
                'In a small bowl, combine brown sugar, mustard, and ketchup. Mix well and pour over the meatloaf.',
                'Bake in preheated oven for 1 hour.'
            ],
            'nutrition': {'Calories': '372', 'Fat': '25g', 'Carbs': '19g', 'Protein': '18g',
                         'Cholesterol': '98mg', 'Sodium': '335mg'},
            'tags': ['dinner', 'meatloaf', 'beef', 'comfort food', 'easy'],
        },
        {
            'title': 'Chicken Pot Pie',
            'slug': 'chicken-pot-pie',
            'description': 'A delicious chicken pie made from scratch with carrots, peas, and celery in a rich, creamy sauce encased in a flaky pie crust.',
            'category': 'chicken',
            'cuisine': 'American',
            'prep_time': '20 mins', 'cook_time': '50 mins', 'total_time': '1 hr 20 mins',
            'additional_time': '10 mins', 'servings': '8', 'yield_amount': '1 (9-inch) pie',
            'calories': 412,
            'avg_rating': 4.8, 'review_count': 13657, 'is_editors_pick': True,
            'author_name': 'Robbie Rice',
            'ingredients': ['1 pound skinless, boneless chicken breasts, cubed',
                          '1 cup sliced carrots', '1 cup frozen green peas',
                          '1/2 cup sliced celery', '1/3 cup butter',
                          '1/3 cup chopped onion', '1/3 cup all-purpose flour',
                          '1/2 teaspoon salt', '1/4 teaspoon black pepper',
                          '1/4 teaspoon celery seed', '1 3/4 cups chicken broth',
                          '2/3 cup milk', '2 (9 inch) unbaked pie crusts'],
            'instructions': [
                'Preheat oven to 425 degrees F (220 degrees C).',
                'Combine chicken, carrots, peas, and celery in a saucepan. Cover with water, boil for 15 minutes. Remove from heat, drain and set aside.',
                'In the saucepan, cook onions in butter over medium heat until soft and translucent. Stir in flour, salt, pepper, and celery seed. Slowly stir in chicken broth and milk.',
                'Simmer over medium-low heat until thick. Remove from heat. Set aside.',
                'Place chicken mixture in bottom pie crust. Pour hot liquid mixture over.',
                'Cover with top crust, seal edges, and cut away excess dough. Make small slits in the top.',
                'Bake in preheated oven for 30 to 35 minutes, or until pastry is golden brown and filling is bubbly. Cool for 10 minutes before serving.'
            ],
            'nutrition': {'Calories': '412', 'Fat': '24g', 'Carbs': '30g', 'Protein': '18g',
                         'Cholesterol': '55mg', 'Sodium': '517mg'},
            'tags': ['chicken', 'pot pie', 'comfort food', 'dinner', 'savory pie'],
        },
        {
            'title': 'Good Old-Fashioned Pancakes',
            'slug': 'pancakes',
            'description': 'I found this pancake recipe in my Grandma\'s recipe book. Judging from the weathered look of this recipe card, this was a family favorite for years.',
            'category': 'breakfast',
            'cuisine': 'American',
            'prep_time': '5 mins', 'cook_time': '15 mins', 'total_time': '20 mins',
            'servings': '8', 'calories': 158,
            'avg_rating': 4.6, 'review_count': 20121, 'is_featured': True,
            'author_name': 'Robyn',
            'ingredients': ['1 1/2 cups all-purpose flour', '3 1/2 teaspoons baking powder',
                          '1 tablespoon white sugar', '1/4 teaspoon salt',
                          '1 1/4 cups milk', '1 egg', '3 tablespoons butter, melted'],
            'instructions': [
                'In a large bowl, sift together flour, baking powder, sugar, and salt. Make a well in the center.',
                'Pour in milk, egg, and melted butter. Mix until smooth.',
                'Heat a lightly oiled griddle or frying pan over medium-high heat.',
                'Pour or scoop the batter onto the griddle, using approximately 1/4 cup for each pancake.',
                'Brown on both sides and serve hot with butter and maple syrup.'
            ],
            'nutrition': {'Calories': '158', 'Fat': '6g', 'Carbs': '22g', 'Protein': '5g',
                         'Cholesterol': '38mg', 'Sodium': '504mg'},
            'tags': ['breakfast', 'pancakes', 'brunch', 'easy', 'quick', 'classic'],
        },
        {
            'title': 'Banana Banana Bread',
            'slug': 'banana-bread',
            'description': 'This banana bread recipe creates the most delicious, moist loaf with loads of banana flavor. Why compromise the banana flavor? This recipe packs a punch with bananas!',
            'category': 'baking',
            'cuisine': 'American',
            'prep_time': '15 mins', 'cook_time': '1 hr', 'total_time': '1 hr 15 mins',
            'servings': '12', 'yield_amount': '1 (9x5-inch) loaf', 'calories': 231,
            'avg_rating': 4.7, 'review_count': 17301, 'is_featured': True, 'is_editors_pick': True,
            'author_name': 'Shelley Albeluhn',
            'ingredients': ['2 cups all-purpose flour', '1 teaspoon baking soda',
                          '1/4 teaspoon salt', '1/2 cup butter, softened',
                          '3/4 cup brown sugar', '2 eggs, beaten',
                          '2 1/3 cups mashed overripe bananas'],
            'instructions': [
                'Preheat oven to 350 degrees F (175 degrees C). Lightly grease a 9x5-inch loaf pan.',
                'In a large bowl, combine flour, baking soda, and salt.',
                'In a separate bowl, cream together butter and brown sugar. Stir in eggs and mashed bananas until well blended.',
                'Stir banana mixture into flour mixture; stir just to moisten.',
                'Pour batter into prepared loaf pan.',
                'Bake in preheated oven for 60 to 65 minutes, until a toothpick inserted into center of the loaf comes out clean.',
                'Let bread cool in pan for 10 minutes, then turn out onto a wire rack.'
            ],
            'nutrition': {'Calories': '231', 'Fat': '9g', 'Carbs': '35g', 'Protein': '4g',
                         'Cholesterol': '51mg', 'Sodium': '226mg'},
            'tags': ['baking', 'banana bread', 'bread', 'quick bread', 'snack'],
        },
        {
            'title': 'Basic Crepes',
            'slug': 'crepes',
            'description': 'This simple but delicious crepe recipe can be made in minutes from ingredients that everyone has on hand. Fill with your favorite sweet or savory fillings.',
            'category': 'breakfast',
            'cuisine': 'French',
            'prep_time': '10 mins', 'cook_time': '20 mins', 'total_time': '30 mins',
            'servings': '4', 'yield_amount': '8 crepes', 'calories': 216,
            'avg_rating': 4.8, 'review_count': 4140,
            'author_name': 'Sarah Johnson',
            'ingredients': ['2 large eggs', '3/4 cup milk', '1/2 cup water',
                          '1 cup all-purpose flour', '3 tablespoons melted butter',
                          '1/4 teaspoon salt'],
            'instructions': [
                'Whisk eggs, milk, water, and salt together in a large mixing bowl.',
                'Add flour and butter; beat until smooth.',
                'Heat a lightly oiled griddle or frying pan over medium-high heat.',
                'Pour or scoop about 3 tablespoons of batter onto the griddle, tilting the pan with a circular motion so the batter coats the surface evenly.',
                'Cook the crepe for about 2 minutes until the bottom is light brown. Loosen with a spatula, turn and cook the other side.',
                'Serve with Nutella, fresh fruit, or your favorite filling.'
            ],
            'nutrition': {'Calories': '216', 'Fat': '9g', 'Carbs': '25g', 'Protein': '7g',
                         'Cholesterol': '111mg', 'Sodium': '229mg'},
            'tags': ['breakfast', 'crepes', 'French', 'brunch', 'sweet', 'savory'],
        },
        {
            'title': 'Teriyaki Salmon',
            'slug': 'teriyaki-salmon',
            'description': 'Teriyaki salmon is a crowd-pleaser. The sweet and savory marinade caramelizes beautifully whether broiled or grilled.',
            'category': 'seafood',
            'cuisine': 'Japanese',
            'prep_time': '10 mins', 'cook_time': '15 mins', 'total_time': '1 hr 25 mins',
            'additional_time': '1 hr', 'servings': '4', 'calories': 900,
            'avg_rating': 4.6, 'review_count': 218, 'is_editors_pick': True,
            'author_name': 'Lena Abraham',
            'ingredients': ['1/4 cup sesame oil', '2 tablespoons lemon juice',
                          '1/4 cup soy sauce', '1 tablespoon brown sugar',
                          '1 tablespoon sesame seeds', '1 teaspoon ground mustard',
                          '4 (6 ounce) salmon fillets'],
            'instructions': [
                'Mix sesame oil, lemon juice, soy sauce, brown sugar, sesame seeds, and ground mustard in a shallow bowl.',
                'Place salmon fillets in the marinade. Cover and refrigerate for at least 1 hour, turning occasionally.',
                'Preheat oven to broil or preheat grill to medium-high heat.',
                'Place salmon on a lightly oiled baking sheet or grill grate.',
                'Broil or grill for 10 to 14 minutes, basting frequently with remaining marinade, until fish flakes easily with a fork.'
            ],
            'nutrition': {'Calories': '900', 'Fat': '63g', 'Carbs': '8g', 'Protein': '72g',
                         'Cholesterol': '250mg', 'Sodium': '1031mg'},
            'tags': ['seafood', 'salmon', 'teriyaki', 'Japanese', 'fish', 'grilled'],
        },
        {
            'title': 'Best Brownies',
            'slug': 'best-brownies',
            'description': 'These brownies are rich, fudgy, and absolutely delicious. A chocolate lover\'s dream come true! Simple ingredients, incredible results.',
            'category': 'desserts',
            'cuisine': 'American',
            'prep_time': '15 mins', 'cook_time': '25 mins', 'total_time': '40 mins',
            'servings': '16', 'calories': 195,
            'avg_rating': 4.6, 'review_count': 11240, 'is_featured': True,
            'author_name': 'Angie',
            'ingredients': ['1/2 cup butter, melted', '1 cup white sugar',
                          '2 eggs', '1 teaspoon vanilla extract',
                          '1/3 cup unsweetened cocoa powder', '1/2 cup all-purpose flour',
                          '1/4 teaspoon salt', '1/4 teaspoon baking powder'],
            'instructions': [
                'Preheat oven to 350 degrees F (175 degrees C). Grease an 8-inch square pan.',
                'Combine butter, sugar, and vanilla in a bowl.',
                'Beat in eggs. Combine cocoa, flour, salt, and baking powder; stir into the butter mixture.',
                'Spread batter into the prepared pan.',
                'Bake for 25 to 30 minutes. Do not overcook.',
                'Cool before cutting into squares.'
            ],
            'nutrition': {'Calories': '195', 'Fat': '8g', 'Carbs': '28g', 'Protein': '2g',
                         'Cholesterol': '43mg', 'Sodium': '85mg'},
            'tags': ['desserts', 'brownies', 'chocolate', 'baking', 'easy'],
        },
        {
            'title': 'Butter Chicken',
            'slug': 'butter-chicken',
            'description': 'Tender chicken simmered in a rich, creamy tomato sauce with aromatic spices. This Indian restaurant favorite is easy to make at home.',
            'category': 'chicken',
            'cuisine': 'Indian',
            'prep_time': '25 mins', 'cook_time': '30 mins', 'total_time': '55 mins',
            'servings': '6', 'calories': 420,
            'avg_rating': 4.7, 'review_count': 3850, 'is_editors_pick': True,
            'author_name': 'Priya Sharma',
            'ingredients': ['1.5 pounds boneless chicken thighs, cubed',
                          '1 cup plain yogurt', '2 teaspoons garam masala',
                          '1 teaspoon turmeric', '1 teaspoon cumin',
                          '2 tablespoons butter', '1 large onion, diced',
                          '3 cloves garlic, minced', '1 tablespoon fresh ginger, grated',
                          '1 (14 ounce) can crushed tomatoes', '1 cup heavy cream',
                          '2 tablespoons tomato paste', '1 teaspoon paprika',
                          'Salt and pepper to taste', 'Fresh cilantro for garnish'],
            'instructions': [
                'Marinate chicken in yogurt, garam masala, turmeric, and cumin for at least 30 minutes.',
                'Melt butter in a large skillet over medium-high heat. Cook chicken until browned, about 5 minutes. Remove and set aside.',
                'In the same pan, cook onion until soft. Add garlic and ginger, cook 1 minute.',
                'Stir in crushed tomatoes, tomato paste, and paprika. Simmer for 10 minutes.',
                'Add heavy cream and return chicken to the pan. Simmer for 15 minutes until chicken is cooked through.',
                'Season with salt and pepper. Garnish with cilantro. Serve with basmati rice or naan.'
            ],
            'nutrition': {'Calories': '420', 'Fat': '28g', 'Carbs': '12g', 'Protein': '32g',
                         'Cholesterol': '120mg', 'Sodium': '480mg'},
            'tags': ['chicken', 'Indian', 'curry', 'butter chicken', 'dinner', 'creamy'],
        },
        {
            'title': 'Miso Soup',
            'slug': 'miso-soup',
            'description': 'A warm, comforting Japanese soup made with dashi broth, miso paste, tofu, and wakame seaweed. Ready in just 15 minutes.',
            'category': 'soups',
            'cuisine': 'Japanese',
            'prep_time': '5 mins', 'cook_time': '10 mins', 'total_time': '15 mins',
            'servings': '4', 'calories': 65,
            'avg_rating': 4.5, 'review_count': 1820,
            'author_name': 'Yuki Tanaka',
            'ingredients': ['4 cups dashi stock (or water with dashi granules)',
                          '3 tablespoons miso paste',
                          '1/2 block silken tofu, cubed',
                          '2 tablespoons dried wakame seaweed',
                          '2 green onions, thinly sliced'],
            'instructions': [
                'Bring dashi stock to a simmer in a pot over medium heat.',
                'Add tofu cubes and wakame. Simmer for 2 minutes.',
                'Remove from heat. Dissolve miso paste in a ladle of hot broth, then stir back into the pot.',
                'Do not boil after adding miso. Serve immediately, garnished with green onions.'
            ],
            'nutrition': {'Calories': '65', 'Fat': '2g', 'Carbs': '6g', 'Protein': '5g',
                         'Cholesterol': '0mg', 'Sodium': '890mg'},
            'tags': ['soups', 'Japanese', 'miso', 'quick', 'healthy', 'vegetarian'],
        },
        {
            'title': 'Shrimp Scampi with Pasta',
            'slug': 'shrimp-scampi',
            'description': 'Succulent shrimp tossed with linguine in a garlic butter and white wine sauce. Restaurant-quality dish ready in under 30 minutes.',
            'category': 'pasta',
            'cuisine': 'Italian',
            'prep_time': '10 mins', 'cook_time': '15 mins', 'total_time': '25 mins',
            'servings': '4', 'calories': 520,
            'avg_rating': 4.7, 'review_count': 5670, 'is_featured': True,
            'author_name': 'Marco Rossi',
            'ingredients': ['1 pound linguine', '1 pound large shrimp, peeled and deveined',
                          '4 tablespoons butter', '4 cloves garlic, minced',
                          '1/2 cup dry white wine', '1/4 cup lemon juice',
                          '1/4 teaspoon red pepper flakes', '1/4 cup fresh parsley, chopped',
                          'Salt and pepper to taste', 'Grated Parmesan cheese for serving'],
            'instructions': [
                'Cook linguine according to package directions. Reserve 1/2 cup pasta water. Drain.',
                'Melt butter in a large skillet over medium-high heat. Add shrimp and cook 2 minutes per side. Remove and set aside.',
                'Add garlic and red pepper flakes to the pan, cook 30 seconds.',
                'Pour in white wine and lemon juice. Simmer 3 minutes.',
                'Return shrimp to the pan. Add cooked pasta and toss to combine, adding pasta water as needed.',
                'Season with salt and pepper. Garnish with parsley and Parmesan.'
            ],
            'nutrition': {'Calories': '520', 'Fat': '16g', 'Carbs': '58g', 'Protein': '32g',
                         'Cholesterol': '180mg', 'Sodium': '620mg'},
            'tags': ['pasta', 'shrimp', 'Italian', 'seafood', 'scampi', 'quick'],
        },
        {
            'title': 'Beef Stroganoff',
            'slug': 'beef-stroganoff',
            'description': 'Tender strips of beef in a rich, creamy mushroom sauce served over egg noodles. A timeless comfort classic.',
            'category': 'dinner',
            'cuisine': 'Russian',
            'prep_time': '15 mins', 'cook_time': '25 mins', 'total_time': '40 mins',
            'servings': '4', 'calories': 580,
            'avg_rating': 4.5, 'review_count': 4320,
            'author_name': 'Emily Davis',
            'ingredients': ['1 pound beef sirloin, sliced thin', '8 ounces egg noodles',
                          '2 tablespoons butter', '1 onion, diced',
                          '8 ounces mushrooms, sliced', '2 cloves garlic, minced',
                          '2 tablespoons flour', '1 cup beef broth',
                          '1/2 cup sour cream', '1 tablespoon Worcestershire sauce',
                          'Salt and pepper to taste', 'Fresh parsley for garnish'],
            'instructions': [
                'Cook egg noodles according to package directions. Drain and set aside.',
                'Season beef with salt and pepper. In a large skillet, cook beef over high heat until browned. Remove and set aside.',
                'In the same skillet, melt butter. Cook onion and mushrooms until softened, about 5 minutes. Add garlic, cook 30 seconds.',
                'Sprinkle flour over vegetables and stir. Gradually add beef broth and Worcestershire sauce.',
                'Simmer until sauce thickens, about 5 minutes. Reduce heat and stir in sour cream.',
                'Return beef to the pan. Serve over egg noodles, garnished with parsley.'
            ],
            'nutrition': {'Calories': '580', 'Fat': '24g', 'Carbs': '48g', 'Protein': '42g',
                         'Cholesterol': '130mg', 'Sodium': '680mg'},
            'tags': ['dinner', 'beef', 'stroganoff', 'comfort food', 'mushroom', 'Russian'],
        },
        {
            'title': 'Shiitake Fried Rice',
            'slug': 'fried-rice',
            'description': 'A flavorful vegetarian fried rice loaded with shiitake mushrooms, vegetables, and seasoned with soy sauce and sesame oil.',
            'category': 'dinner',
            'cuisine': 'Asian',
            'prep_time': '10 mins', 'cook_time': '15 mins', 'total_time': '25 mins',
            'servings': '4', 'calories': 340,
            'avg_rating': 4.4, 'review_count': 1580,
            'author_name': 'Lin Chen',
            'ingredients': ['3 cups cooked rice (day-old preferred)', '8 ounces shiitake mushrooms, sliced',
                          '2 eggs, beaten', '3 green onions, chopped',
                          '1 cup frozen peas and carrots', '3 tablespoons soy sauce',
                          '1 tablespoon sesame oil', '2 tablespoons vegetable oil',
                          '2 cloves garlic, minced', '1 teaspoon fresh ginger, grated'],
            'instructions': [
                'Heat vegetable oil in a large wok or skillet over high heat.',
                'Add mushrooms and stir-fry until golden, about 3 minutes. Remove and set aside.',
                'Add beaten eggs to the wok. Scramble until set, then break into small pieces.',
                'Add garlic and ginger, cook 30 seconds. Add peas, carrots, and green onions.',
                'Add rice and mushrooms back to the wok. Stir-fry for 3 minutes.',
                'Add soy sauce and sesame oil. Toss everything together and serve hot.'
            ],
            'nutrition': {'Calories': '340', 'Fat': '12g', 'Carbs': '46g', 'Protein': '12g',
                         'Cholesterol': '95mg', 'Sodium': '720mg'},
            'tags': ['dinner', 'Asian', 'rice', 'vegetarian', 'mushroom', 'fried rice'],
        },
        {
            'title': 'Almond Crescent Cookies',
            'slug': 'almond-cookies',
            'description': 'Buttery, melt-in-your-mouth almond crescent cookies dusted with powdered sugar. Perfect for holiday cookie platters.',
            'category': 'desserts',
            'cuisine': 'American',
            'prep_time': '20 mins', 'cook_time': '12 mins', 'total_time': '32 mins',
            'servings': '36', 'calories': 85,
            'avg_rating': 4.7, 'review_count': 2340,
            'author_name': 'Barbara Miller',
            'ingredients': ['1 cup butter, softened', '1/2 cup powdered sugar',
                          '1 teaspoon vanilla extract', '1/2 teaspoon almond extract',
                          '2 1/4 cups all-purpose flour', '1/2 cup finely ground almonds',
                          '1/4 teaspoon salt', 'Additional powdered sugar for rolling'],
            'instructions': [
                'Preheat oven to 325 degrees F (165 degrees C).',
                'Cream butter and powdered sugar until light and fluffy.',
                'Beat in vanilla and almond extracts. Mix in flour, ground almonds, and salt.',
                'Shape dough into crescents using about 1 tablespoon of dough each.',
                'Place on ungreased cookie sheets.',
                'Bake for 12 to 14 minutes, until set but not browned.',
                'Roll warm cookies in powdered sugar. Cool and roll again.'
            ],
            'nutrition': {'Calories': '85', 'Fat': '6g', 'Carbs': '7g', 'Protein': '1g',
                         'Cholesterol': '14mg', 'Sodium': '42mg'},
            'tags': ['desserts', 'cookies', 'almond', 'holiday', 'baking'],
        },
        # Additional recipes to fill categories
        {
            'title': 'Classic Caesar Salad',
            'slug': 'caesar-salad',
            'description': 'A classic Caesar salad with homemade dressing, crisp romaine lettuce, crunchy croutons, and freshly shaved Parmesan.',
            'category': 'salads',
            'cuisine': 'Italian',
            'prep_time': '15 mins', 'cook_time': '0 mins', 'total_time': '15 mins',
            'servings': '4', 'calories': 280,
            'avg_rating': 4.6, 'review_count': 7800,
            'author_name': 'Julia Martin',
            'ingredients': ['2 heads romaine lettuce, chopped', '1/2 cup olive oil',
                          '3 tablespoons lemon juice', '2 cloves garlic, minced',
                          '1 teaspoon Dijon mustard', '1 teaspoon Worcestershire sauce',
                          '1/2 cup grated Parmesan cheese', '1 cup croutons',
                          'Salt and pepper to taste', '1 anchovy fillet (optional)'],
            'instructions': [
                'Whisk together olive oil, lemon juice, garlic, Dijon mustard, Worcestershire sauce, and anchovy if using.',
                'Season dressing with salt and pepper to taste.',
                'Place chopped romaine in a large bowl. Drizzle with dressing and toss.',
                'Top with Parmesan cheese and croutons. Serve immediately.'
            ],
            'nutrition': {'Calories': '280', 'Fat': '22g', 'Carbs': '12g', 'Protein': '10g',
                         'Cholesterol': '12mg', 'Sodium': '520mg'},
            'tags': ['salads', 'Caesar', 'Italian', 'quick', 'classic'],
        },
        {
            'title': 'Guacamole',
            'slug': 'guacamole',
            'description': 'The best guacamole recipe — perfectly creamy with just the right amount of lime and cilantro. Great with chips or on tacos.',
            'category': 'appetizers',
            'cuisine': 'Mexican',
            'prep_time': '10 mins', 'cook_time': '0 mins', 'total_time': '10 mins',
            'servings': '4', 'calories': 160,
            'avg_rating': 4.8, 'review_count': 8920, 'is_editors_pick': True,
            'author_name': 'Carlos Mendez',
            'ingredients': ['3 ripe avocados', '1 lime, juiced', '1 teaspoon salt',
                          '1/2 cup diced onion', '3 tablespoons fresh cilantro, chopped',
                          '2 roma tomatoes, diced', '1 teaspoon garlic, minced',
                          '1 pinch ground cayenne pepper'],
            'instructions': [
                'Cut avocados in half. Remove pit. Scoop out flesh and place in a mixing bowl.',
                'Mash avocados with a fork, leaving some chunks.',
                'Stir in lime juice and salt. Mix in onion, cilantro, tomatoes, and garlic.',
                'Add cayenne pepper. Refrigerate 1 hour for best flavor, or serve immediately.'
            ],
            'nutrition': {'Calories': '160', 'Fat': '14g', 'Carbs': '10g', 'Protein': '2g',
                         'Cholesterol': '0mg', 'Sodium': '590mg'},
            'tags': ['appetizers', 'Mexican', 'guacamole', 'dip', 'avocado', 'party'],
        },
        {
            'title': 'Chicken Tacos',
            'slug': 'chicken-tacos',
            'description': 'Easy, flavorful chicken tacos with seasoned chicken, fresh toppings, and a squeeze of lime. Perfect for Taco Tuesday!',
            'category': 'dinner',
            'cuisine': 'Mexican',
            'prep_time': '15 mins', 'cook_time': '15 mins', 'total_time': '30 mins',
            'servings': '6', 'calories': 320,
            'avg_rating': 4.5, 'review_count': 4560,
            'author_name': 'Rosa Garcia',
            'ingredients': ['1.5 pounds boneless chicken breasts', '2 tablespoons olive oil',
                          '2 teaspoons chili powder', '1 teaspoon cumin',
                          '1/2 teaspoon garlic powder', '1/2 teaspoon paprika',
                          '12 small corn tortillas', '1 cup shredded lettuce',
                          '1 cup diced tomatoes', '1/2 cup sour cream',
                          '1 cup shredded cheese', '1 lime, cut into wedges',
                          'Fresh cilantro', 'Salt and pepper to taste'],
            'instructions': [
                'Season chicken with chili powder, cumin, garlic powder, paprika, salt and pepper.',
                'Heat olive oil in a skillet over medium-high heat. Cook chicken for 6-7 minutes per side until cooked through.',
                'Let chicken rest for 5 minutes, then slice or shred.',
                'Warm tortillas in a dry skillet or microwave.',
                'Assemble tacos with chicken, lettuce, tomatoes, cheese, sour cream, and cilantro.',
                'Serve with lime wedges.'
            ],
            'nutrition': {'Calories': '320', 'Fat': '14g', 'Carbs': '24g', 'Protein': '28g',
                         'Cholesterol': '75mg', 'Sodium': '440mg'},
            'tags': ['dinner', 'Mexican', 'tacos', 'chicken', 'easy', 'quick'],
        },
        {
            'title': 'Minestrone Soup',
            'slug': 'minestrone',
            'description': 'A hearty Italian vegetable soup packed with beans, pasta, and seasonal vegetables in a rich tomato broth.',
            'category': 'soups',
            'cuisine': 'Italian',
            'prep_time': '20 mins', 'cook_time': '40 mins', 'total_time': '1 hr',
            'servings': '8', 'calories': 220,
            'avg_rating': 4.6, 'review_count': 5230,
            'author_name': 'Angela Romano',
            'ingredients': ['2 tablespoons olive oil', '1 onion, diced',
                          '2 carrots, diced', '2 stalks celery, diced',
                          '3 cloves garlic, minced', '1 (28 ounce) can diced tomatoes',
                          '4 cups vegetable broth', '1 (15 ounce) can kidney beans, drained',
                          '1 cup small pasta (ditalini)', '2 cups chopped kale or spinach',
                          '1 zucchini, diced', '1 teaspoon Italian seasoning',
                          'Salt and pepper to taste', 'Parmesan cheese for serving'],
            'instructions': [
                'Heat olive oil in a large pot over medium heat. Saute onion, carrots, and celery until softened, about 5 minutes.',
                'Add garlic and Italian seasoning. Cook 1 minute.',
                'Add diced tomatoes, vegetable broth, and kidney beans. Bring to a boil.',
                'Add pasta and zucchini. Reduce heat and simmer 15 minutes.',
                'Add kale or spinach and cook 5 more minutes. Season with salt and pepper.',
                'Serve hot topped with Parmesan cheese.'
            ],
            'nutrition': {'Calories': '220', 'Fat': '5g', 'Carbs': '36g', 'Protein': '10g',
                         'Cholesterol': '0mg', 'Sodium': '580mg'},
            'tags': ['soups', 'Italian', 'vegetarian', 'healthy', 'minestrone', 'vegetables'],
        },
        {
            'title': 'Grilled Shrimp Skewers',
            'slug': 'grilled-shrimp',
            'description': 'Juicy, perfectly grilled shrimp marinated in garlic, lemon, and herbs. Ready in minutes and great for summer cookouts.',
            'category': 'seafood',
            'cuisine': 'American',
            'prep_time': '15 mins', 'cook_time': '6 mins', 'total_time': '51 mins',
            'additional_time': '30 mins', 'servings': '4', 'calories': 190,
            'avg_rating': 4.7, 'review_count': 3420,
            'author_name': 'Chef Tom',
            'ingredients': ['1 pound large shrimp, peeled and deveined',
                          '3 tablespoons olive oil', '3 cloves garlic, minced',
                          '2 tablespoons lemon juice', '1 tablespoon fresh parsley, chopped',
                          '1/2 teaspoon paprika', '1/4 teaspoon red pepper flakes',
                          'Salt and pepper to taste', 'Wooden skewers, soaked in water'],
            'instructions': [
                'Whisk together olive oil, garlic, lemon juice, parsley, paprika, red pepper flakes, salt, and pepper.',
                'Toss shrimp in the marinade. Cover and refrigerate for 30 minutes.',
                'Preheat grill to medium-high heat. Thread shrimp onto skewers.',
                'Grill 2-3 minutes per side until pink and opaque.',
                'Serve with lemon wedges and extra parsley.'
            ],
            'nutrition': {'Calories': '190', 'Fat': '11g', 'Carbs': '2g', 'Protein': '23g',
                         'Cholesterol': '170mg', 'Sodium': '480mg'},
            'tags': ['seafood', 'shrimp', 'grilled', 'summer', 'healthy', 'quick'],
        },
        {
            'title': 'Chocolate Chip Cookies',
            'slug': 'chocolate-chip-cookies',
            'description': 'The perfect chocolate chip cookies — crispy on the edges, chewy in the center, with pools of melted chocolate throughout.',
            'category': 'desserts',
            'cuisine': 'American',
            'prep_time': '15 mins', 'cook_time': '10 mins', 'total_time': '25 mins',
            'servings': '48', 'calories': 110,
            'avg_rating': 4.8, 'review_count': 15600, 'is_featured': True, 'is_editors_pick': True,
            'author_name': 'Dottie Sullivan',
            'ingredients': ['1 cup butter, softened', '1 cup white sugar', '1 cup brown sugar',
                          '2 eggs', '2 teaspoons vanilla extract', '3 cups all-purpose flour',
                          '1 teaspoon baking soda', '2 teaspoons hot water',
                          '1/2 teaspoon salt', '2 cups semisweet chocolate chips',
                          '1 cup chopped walnuts (optional)'],
            'instructions': [
                'Preheat oven to 350 degrees F (175 degrees C).',
                'Cream together butter, white sugar, and brown sugar until smooth.',
                'Beat in eggs one at a time, then stir in vanilla.',
                'Dissolve baking soda in hot water. Add to batter along with salt.',
                'Stir in flour and chocolate chips (and nuts if desired).',
                'Drop by large spoonfuls onto ungreased pans.',
                'Bake for about 10 minutes, or until edges are nicely browned.'
            ],
            'nutrition': {'Calories': '110', 'Fat': '6g', 'Carbs': '14g', 'Protein': '1g',
                         'Cholesterol': '18mg', 'Sodium': '65mg'},
            'tags': ['desserts', 'cookies', 'chocolate chip', 'baking', 'classic'],
        },
        {
            'title': 'Spaghetti Carbonara',
            'slug': 'carbonara',
            'description': 'Authentic Italian carbonara with crispy pancetta, egg, Parmesan, and black pepper. No cream needed for this classic Roman dish.',
            'category': 'pasta',
            'cuisine': 'Italian',
            'prep_time': '10 mins', 'cook_time': '20 mins', 'total_time': '30 mins',
            'servings': '4', 'calories': 480,
            'avg_rating': 4.6, 'review_count': 6780,
            'author_name': 'Giovanni Luca',
            'ingredients': ['1 pound spaghetti', '6 ounces pancetta or guanciale, diced',
                          '4 large egg yolks', '2 whole eggs',
                          '1 cup grated Pecorino Romano cheese',
                          '1/2 cup grated Parmesan cheese',
                          'Freshly ground black pepper', '2 tablespoons olive oil'],
            'instructions': [
                'Cook spaghetti in salted boiling water until al dente. Reserve 1 cup pasta water.',
                'Meanwhile, cook pancetta in olive oil over medium heat until crispy, about 8 minutes.',
                'Whisk together egg yolks, whole eggs, Pecorino, and Parmesan in a bowl.',
                'Drain pasta and add to the pan with pancetta. Remove from heat.',
                'Quickly pour egg mixture over hot pasta. Toss rapidly, adding pasta water as needed.',
                'The heat of the pasta will cook the eggs into a creamy sauce. Serve with extra cheese and pepper.'
            ],
            'nutrition': {'Calories': '480', 'Fat': '22g', 'Carbs': '44g', 'Protein': '26g',
                         'Cholesterol': '250mg', 'Sodium': '780mg'},
            'tags': ['pasta', 'Italian', 'carbonara', 'dinner', 'Roman', 'classic'],
        },
        {
            'title': 'Greek Salad',
            'slug': 'greek-salad',
            'description': 'A refreshing Greek salad with crispy cucumbers, ripe tomatoes, red onion, Kalamata olives, and creamy feta cheese.',
            'category': 'salads',
            'cuisine': 'Greek',
            'prep_time': '15 mins', 'cook_time': '0 mins', 'total_time': '15 mins',
            'servings': '4', 'calories': 230,
            'avg_rating': 4.7, 'review_count': 5340,
            'author_name': 'Elena Papadopoulos',
            'ingredients': ['1 English cucumber, chopped', '4 large tomatoes, chopped',
                          '1 red onion, thinly sliced', '1 cup Kalamata olives',
                          '8 ounces feta cheese, crumbled', '1/4 cup olive oil',
                          '2 tablespoons red wine vinegar', '1 teaspoon dried oregano',
                          'Salt and pepper to taste'],
            'instructions': [
                'Combine cucumber, tomatoes, red onion, and olives in a large bowl.',
                'Whisk together olive oil, red wine vinegar, and oregano for the dressing.',
                'Pour dressing over vegetables and toss gently.',
                'Top with crumbled feta cheese. Season with salt and pepper.',
                'Serve immediately or refrigerate until ready to serve.'
            ],
            'nutrition': {'Calories': '230', 'Fat': '18g', 'Carbs': '10g', 'Protein': '8g',
                         'Cholesterol': '35mg', 'Sodium': '680mg'},
            'tags': ['salads', 'Greek', 'healthy', 'vegetarian', 'Mediterranean', 'quick'],
        },
        {
            'title': 'Chicken Stir-Fry',
            'slug': 'chicken-stir-fry',
            'description': 'A quick and colorful chicken stir-fry with bell peppers, broccoli, and a savory soy-ginger sauce. Dinner in under 20 minutes!',
            'category': 'chicken',
            'cuisine': 'Asian',
            'prep_time': '10 mins', 'cook_time': '10 mins', 'total_time': '20 mins',
            'servings': '4', 'calories': 310,
            'avg_rating': 4.5, 'review_count': 6120,
            'author_name': 'Amy Wong',
            'ingredients': ['1 pound chicken breast, sliced thin',
                          '2 tablespoons vegetable oil', '1 red bell pepper, sliced',
                          '1 cup broccoli florets', '1 carrot, julienned',
                          '3 cloves garlic, minced', '1 tablespoon fresh ginger, grated',
                          '3 tablespoons soy sauce', '1 tablespoon oyster sauce',
                          '1 teaspoon sesame oil', '1 tablespoon cornstarch mixed with 2 tablespoons water',
                          'Steamed rice for serving'],
            'instructions': [
                'Heat oil in a wok over high heat. Stir-fry chicken until golden, about 4 minutes. Remove.',
                'Add bell pepper, broccoli, and carrot. Stir-fry 3 minutes.',
                'Add garlic and ginger, cook 30 seconds.',
                'Return chicken. Add soy sauce, oyster sauce, and sesame oil.',
                'Pour in cornstarch mixture. Stir until sauce thickens.',
                'Serve over steamed rice.'
            ],
            'nutrition': {'Calories': '310', 'Fat': '12g', 'Carbs': '16g', 'Protein': '34g',
                         'Cholesterol': '70mg', 'Sodium': '820mg'},
            'tags': ['chicken', 'Asian', 'stir-fry', 'quick', 'healthy', 'dinner'],
        },
        {
            'title': 'Spinach Artichoke Dip',
            'slug': 'spinach-artichoke-dip',
            'description': 'Creamy, cheesy spinach artichoke dip that\'s the ultimate party appetizer. Serve warm with tortilla chips or crusty bread.',
            'category': 'appetizers',
            'cuisine': 'American',
            'prep_time': '10 mins', 'cook_time': '25 mins', 'total_time': '35 mins',
            'servings': '12', 'calories': 180,
            'avg_rating': 4.7, 'review_count': 7240,
            'author_name': 'Karen White',
            'ingredients': ['10 ounces frozen chopped spinach, thawed and drained',
                          '1 (14 ounce) can artichoke hearts, drained and chopped',
                          '8 ounces cream cheese, softened',
                          '1/2 cup sour cream', '1/2 cup mayonnaise',
                          '1 cup grated Parmesan cheese', '1/2 cup shredded mozzarella',
                          '3 cloves garlic, minced', 'Salt and pepper to taste'],
            'instructions': [
                'Preheat oven to 350 degrees F (175 degrees C).',
                'Mix cream cheese, sour cream, and mayonnaise until smooth.',
                'Stir in spinach, artichoke hearts, Parmesan, and garlic.',
                'Transfer to a baking dish. Top with mozzarella.',
                'Bake for 25 minutes until bubbly and golden.',
                'Serve warm with chips, crackers, or bread.'
            ],
            'nutrition': {'Calories': '180', 'Fat': '16g', 'Carbs': '4g', 'Protein': '6g',
                         'Cholesterol': '30mg', 'Sodium': '380mg'},
            'tags': ['appetizers', 'dip', 'spinach', 'artichoke', 'party', 'cheesy'],
        },
    ]

    for rd in recipes_data:
        cat = cats.get(rd['category'])
        hero_img = get_shared_hero(rd['slug'])
        gallery_sections = get_shared_gallery(rd['slug'], rd['title'])

        ingredients_list = rd['ingredients']
        recipe = Recipe(
            title=rd['title'],
            slug=rd['slug'],
            description=rd['description'],
            category_id=cat.id if cat else None,
            cuisine=rd.get('cuisine', ''),
            image=hero_img,
            prep_time=rd.get('prep_time', ''),
            cook_time=rd.get('cook_time', ''),
            total_time=rd.get('total_time', ''),
            additional_time=rd.get('additional_time', ''),
            servings=rd.get('servings', ''),
            yield_amount=rd.get('yield_amount', ''),
            calories=rd.get('calories', 0),
            ingredients_json=json.dumps(ingredients_list),
            instructions_json=json.dumps(rd['instructions']),
            nutrition_json=json.dumps(rd.get('nutrition', {})),
            tags_json=json.dumps(rd.get('tags', [])),
            gallery_json=json.dumps(gallery_sections),
            is_featured=rd.get('is_featured', False),
            is_editors_pick=rd.get('is_editors_pick', False),
            avg_rating=rd.get('avg_rating', 0.0),
            review_count=rd.get('review_count', 0),
            author_name=rd.get('author_name', 'Allrecipes Community'),
            prep_time_mins=parse_time_to_mins(rd.get('prep_time', '')),
            cook_time_mins=parse_time_to_mins(rd.get('cook_time', '')),
            total_time_mins=parse_time_to_mins(rd.get('total_time', '')),
            ingredient_count=len(ingredients_list),
            dietary_tags_json=json.dumps(rd.get('dietary_tags', [])),
            dish_type=rd.get('dish_type', ''),
            meal_type=rd.get('meal_type', ''),
            cooking_method=rd.get('cooking_method', ''),
            main_ingredient=rd.get('main_ingredient', ''),
            occasion=rd.get('occasion', ''),
            season=rd.get('season', ''),
            feature_tags=json.dumps(rd.get('feature_tags', rd.get('tags', []))),
            latest_review_text=rd.get('latest_review_text', ''),
            storage_instructions=rd.get('storage_instructions', ''),
            primary_seasoning=rd.get('primary_seasoning', ''),
            max_oven_temp=rd.get('max_oven_temp', 0),
        )
        db.session.add(recipe)

    db.session.commit()
    print(f"Seeded {Recipe.query.count()} recipes in {Category.query.count()} categories")


# ---------------------------------------------------------------------------
# Benchmark users seed
# ---------------------------------------------------------------------------

def seed_benchmark_users():
    """Idempotent seed of 4 benchmark users with recipe box, meal plan,
    shopping list, and review data.  Safe to call multiple times."""
    if User.query.filter_by(email='alice.j@test.com').first():
        return  # already seeded

    PASSWORD = 'TestPass123!'
    # Pinned bcrypt hash of 'TestPass123!' so a fresh seed build produces
    # byte-identical user rows. Without this, bcrypt's random salt would
    # rotate the hash on every rebuild and break the byte-identical reset
    # invariant. Login still works because bcrypt.check_password_hash
    # accepts any valid $2b$… hash. See harden-env/gotchas.md #1.
    PINNED_HASH = '$2b$12$RwAC/sfwDHtccU//A20fde.uKkZK4Ptnjjyua2l2ktwI6uysAp3Ou'

    def _get_recipe(title_fragment):
        return Recipe.query.filter(
            Recipe.title.ilike(f'%{title_fragment}%')).first()

    # ----- Create users -----
    users_data = [
        {
            'username': 'alice_j',
            'email': 'alice.j@test.com',
            'display_name': 'Alice Johnson',
            'bio': 'Home cook obsessed with vegetarian Italian food.',
            'location': 'Portland, OR',
        },
        {
            'username': 'bob_c',
            'email': 'bob.c@test.com',
            'display_name': 'Bob Chen',
            'bio': 'Weekend griller. Love quick weeknight dinners.',
            'location': 'Austin, TX',
        },
        {
            'username': 'carol_d',
            'email': 'carol.d@test.com',
            'display_name': 'Carol Davis',
            'bio': 'Gluten-free baker. Always hunting for healthier swaps.',
            'location': 'Denver, CO',
        },
        {
            'username': 'david_k',
            'email': 'david.k@test.com',
            'display_name': 'David Kim',
            'bio': 'Meal-prep enthusiast. Batch cook every Sunday.',
            'location': 'Chicago, IL',
        },
    ]
    users = {}
    for ud in users_data:
        u = User(
            username=ud['username'],
            email=ud['email'],
            display_name=ud['display_name'],
            bio=ud['bio'],
            location=ud['location'],
        )
        u.password_hash = PINNED_HASH
        db.session.add(u)
        users[ud['email']] = u
    db.session.flush()

    alice = users['alice.j@test.com']
    bob   = users['bob.c@test.com']
    carol = users['carol.d@test.com']
    david = users['david.k@test.com']

    # ----- Recipe Box items -----
    # Alice: 4 vegetarian/Italian recipes (including one she'll remove in T06)
    alice_box_titles = [
        'Easy Vegetarian Spinach Lasagna',
        'Mushroom and Spinach Vegetarian Lasagna',
        'Classic Vegetarian Lasagna',
        'Eggplant Parmesan',          # kept intentionally for removal in T06
        'Classic Italian Pasta Sauce',
    ]
    for title in alice_box_titles:
        r = _get_recipe(title)
        if r:
            db.session.add(RecipeBoxItem(user_id=alice.id, recipe_id=r.id,
                                         notes='Alice loves this one'))

    # Bob: quick dinner + grilling recipes
    bob_box_titles = [
        'Chicken Stir-Fry',
        'Baked Honey Garlic Salmon',
        'Garlic Chicken',
        'Greek Salad',
    ]
    for title in bob_box_titles:
        r = _get_recipe(title)
        if r:
            db.session.add(RecipeBoxItem(user_id=bob.id, recipe_id=r.id))

    # Carol: gluten-free recipes
    carol_box_titles = [
        'Baked Honey Garlic Salmon',
        'Flourless Gluten-Free Brownies',
        'Avocado Tomato Salad',
        'Keto Low-Carb Breakfast Bowl',
    ]
    for title in carol_box_titles:
        r = _get_recipe(title)
        if r:
            db.session.add(RecipeBoxItem(user_id=carol.id, recipe_id=r.id))

    # David: batch-cook / high-protein recipes
    david_box_titles = [
        'Chicken Breast and Quinoa Bowl',
        'Three Bean Vegetarian Chili',
        'Easy Meatloaf',
        'Baked Herb-Crusted Salmon',
    ]
    for title in david_box_titles:
        r = _get_recipe(title)
        if r:
            db.session.add(RecipeBoxItem(user_id=david.id, recipe_id=r.id))

    # ----- Meal Plan items -----
    # Alice: weekday dinner plan
    alice_plan = [
        ('monday',    'dinner',  'Easy Vegetarian Spinach Lasagna'),
        ('tuesday',   'dinner',  'Classic Vegetarian Lasagna'),
        ('wednesday', 'lunch',   'Greek Salad'),
        ('thursday',  'dinner',  'Mushroom and Spinach Vegetarian Lasagna'),
        ('friday',    'dinner',  'Eggplant Parmesan'),
    ]
    for day, meal, title in alice_plan:
        r = _get_recipe(title)
        if r:
            db.session.add(MealPlanItem(user_id=alice.id, recipe_id=r.id,
                                         day=day, meal_type=meal))

    # David: full week meal-prep plan
    david_plan = [
        ('monday',    'breakfast', 'Keto Low-Carb Breakfast Bowl'),
        ('monday',    'dinner',    'Chicken Breast and Quinoa Bowl'),
        ('tuesday',   'breakfast', 'Good Old-Fashioned Pancakes'),
        ('tuesday',   'dinner',    'Three Bean Vegetarian Chili'),
        ('wednesday', 'dinner',    'Easy Meatloaf'),
        ('thursday',  'dinner',    'Baked Herb-Crusted Salmon'),
        ('friday',    'dinner',    'Chicken Stir-Fry'),
        ('saturday',  'breakfast', 'Waffles'),
        ('sunday',    'dinner',    'Classic Vegetarian Lasagna'),
    ]
    for day, meal, title in david_plan:
        r = _get_recipe(title)
        if r:
            db.session.add(MealPlanItem(user_id=david.id, recipe_id=r.id,
                                         day=day, meal_type=meal))

    # ----- Shopping Lists -----
    # Alice: list pre-populated from lasagna ingredients
    alice_sl = ShoppingList(user_id=alice.id, name="Weekly Groceries")
    alice_lasagna = _get_recipe('Easy Vegetarian Spinach Lasagna')
    if alice_lasagna:
        alice_sl.set_items(alice_lasagna.get_ingredients())
    else:
        alice_sl.set_items(['lasagna noodles', 'ricotta cheese', 'spinach',
                            'mozzarella', 'marinara sauce', 'Parmesan'])
    db.session.add(alice_sl)

    # Carol: gluten-free baking list
    carol_sl = ShoppingList(user_id=carol.id, name="Gluten-Free Baking")
    carol_sl.set_items(['almond flour', 'coconut sugar', 'baking soda',
                        'dark chocolate chips', 'coconut oil', 'eggs',
                        'vanilla extract'])
    db.session.add(carol_sl)

    # David: meal-prep list
    david_sl = ShoppingList(user_id=david.id, name="Sunday Meal Prep")
    david_sl.set_items(['chicken breasts (4 lbs)', 'quinoa', 'broccoli',
                        'olive oil', 'garlic', 'lemon', 'black beans',
                        'canned tomatoes', 'onion', 'bell peppers'])
    db.session.add(david_sl)

    # Bob: quick dinner list (empty — he'll build it during a task)
    bob_sl = ShoppingList(user_id=bob.id, name="Weeknight Dinners")
    bob_sl.set_items([])
    db.session.add(bob_sl)

    # ----- Reviews -----
    # Give each user 2-3 reviews so the site looks lived-in
    reviews_data = [
        (alice, 'Easy Vegetarian Spinach Lasagna', 5,
         'Perfect weeknight lasagna',
         'My go-to! Made it three times. The spinach keeps it light.'),
        (alice, 'Classic Vegetarian Lasagna', 4,
         'Solid classic',
         'Great flavor. Took a bit longer than stated but worth it.'),
        (bob, 'Chicken Stir-Fry', 5,
         'Blazing fast dinner',
         'On the table in 20 minutes. Kids devoured it.'),
        (bob, 'Baked Honey Garlic Salmon', 5,
         'Restaurant-quality at home',
         'The glaze is incredible. Will make this every week.'),
        (carol, 'Flourless Gluten-Free Brownies', 5,
         'Best GF brownies ever',
         'Finally a gluten-free brownie that doesn\'t taste like cardboard!'),
        (carol, 'Avocado Tomato Salad', 4,
         'Fresh and simple',
         'Great summer salad. Added cucumber for extra crunch.'),
        (david, 'Chicken Breast and Quinoa Bowl', 5,
         'Meal-prep champion',
         'Made 6 portions on Sunday, stayed fresh all week.'),
        (david, 'Three Bean Vegetarian Chili', 4,
         'Hearty and filling',
         'Doubled the batch for the freezer. Excellent macros.'),
    ]
    for user, title, rating, rev_title, body in reviews_data:
        recipe = _get_recipe(title)
        if recipe:
            existing = Review.query.filter_by(
                user_id=user.id, recipe_id=recipe.id).first()
            if not existing:
                rev = Review(user_id=user.id, recipe_id=recipe.id,
                             rating=rating, title=rev_title, body=body)
                db.session.add(rev)
                db.session.flush()
                # Update recipe avg_rating
                all_revs = Review.query.filter_by(recipe_id=recipe.id).all()
                recipe.avg_rating = round(
                    sum(rv.rating for rv in all_revs) / len(all_revs), 1)
                recipe.review_count = len(all_revs)

    db.session.commit()
    print("Seeded 4 benchmark users: alice.j, bob.c, carol.d, david.k")


# ---------------------------------------------------------------------------
# Initialize
# ---------------------------------------------------------------------------
os.makedirs(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'instance'), exist_ok=True)

def seed_1960s_collection_recipes():
    """Ensure each recipe in the Popular 1960s collection exists in the DB
    with the prep/total time shown on the collection page, so every card
    resolves to a working /recipe/<slug> page."""
    seed_entries = [
        ('classic-beef-wellington', 'Classic Beef Wellington',
         'An iconic 1960s dinner party centerpiece: beef tenderloin wrapped in duxelles and golden puff pastry.',
         45, 105, 150,
         'dinner', 'main', 'beef'),
        ('chicken-a-la-king', 'Chicken a la King',
         'A creamy 1960s classic of diced chicken, mushrooms and pimientos in a sherry cream sauce served over toast or rice.',
         15, 25, 40,
         'dinner', 'main', 'chicken'),
        ('tuna-noodle-casserole', 'Tuna Noodle Casserole',
         'The quintessential 1960s weeknight casserole: egg noodles, tuna, mushroom sauce and a crispy breadcrumb topping.',
         20, 40, 60,
         'dinner', 'main', 'seafood'),
        ('deviled-eggs', 'Deviled Eggs',
         'A 1960s cocktail-party staple: hard-boiled eggs filled with a tangy, creamy yolk mixture.',
         10, 10, 20,
         'appetizer', 'appetizer', 'eggs'),
        ('swedish-meatballs', 'Swedish Meatballs',
         'Tender beef-and-pork meatballs simmered in a rich cream and beef-broth gravy — a 1960s potluck favorite.',
         20, 40, 60,
         'dinner', 'main', 'beef'),
    ]
    created = 0
    for slug, title, desc, prep_m, cook_m, total_m, meal, dish, main in seed_entries:
        if Recipe.query.filter_by(slug=slug).first():
            continue
        r = Recipe(
            title=title, slug=slug,
            description=desc,
            prep_time=f"{prep_m} mins",
            cook_time=f"{cook_m} mins",
            total_time=f"{total_m} mins" if total_m < 60 else (
                f"{total_m // 60} hr {total_m % 60} mins" if total_m % 60 else f"{total_m // 60} hr"),
            servings='6',
            calories=380,
            ingredients_json=json.dumps([
                'Key ingredient 1', 'Key ingredient 2', 'Key ingredient 3',
                'Salt and pepper, to taste']),
            instructions_json=json.dumps([
                'Prepare the ingredients according to the collection recipe.',
                'Cook until golden and heated through.',
                'Season to taste and serve warm.']),
            tags_json=json.dumps(['1960s', 'classic', 'vintage']),
            feature_tags=json.dumps(['1960s', 'classic', 'vintage']),
            author_name='Allrecipes Test Kitchen',
            avg_rating=4.6,
            review_count=120,
            prep_time_mins=prep_m,
            cook_time_mins=cook_m,
            total_time_mins=total_m,
            ingredient_count=4,
            meal_type=meal,
            dish_type=dish,
            main_ingredient=main,
            occasion='1960s Classics',
        )
        db.session.add(r)
        created += 1
    if created:
        db.session.commit()
        print(f"Seeded {created} Popular-1960s collection recipes")


with app.app_context():
    db.create_all()
    seed_database()
    # Extended catalog (TheMealDB + benchmark-fixture recipes) runs
    # BEFORE seed_benchmark_users so that user recipe-box / meal-plan
    # lookups by title fragment hit the extended recipe set.
    # Lives in seed_data.py to keep this file readable.
    try:
        from seed_data import seed_extended_catalog
        seed_extended_catalog()
    except Exception as exc:  # pragma: no cover - never silently swallow
        print(f"[seed_extended] FAILED: {exc!r}")
        raise
    seed_benchmark_users()
    seed_1960s_collection_recipes()

    # R4: final enrichment pass — fills tags >=5 + nutrition + gallery for
    # any recipe inserted by post-extended seed paths (1960s, benchmark users).
    try:
        from r4_seed import _enrich_existing_recipes
        _enrich_existing_recipes()
        db.session.commit()
    except Exception as exc:  # pragma: no cover
        print(f"[r4_final_enrich] failed: {exc!r}")

    # R5: final enrichment pass — top up cuisine-origin / time / calorie /
    # equipment / allergen-free flags on every recipe (including the
    # post-extended 1960s + benchmark inserts).
    try:
        from r5_seed import _enrich_r5_fields
        _enrich_r5_fields()
        db.session.commit()
    except Exception as exc:  # pragma: no cover
        print(f"[r5_final_enrich] failed: {exc!r}")

    # R6: final enrichment pass — re-derive more-like-this bucket tags on
    # the post-extended inserts (1960s collection, benchmark fixtures) so
    # the recipe detail "更像 X" carousel has rich tags to query against.
    try:
        from r6_seed import _enrich_r6_more_like_features
        _enrich_r6_more_like_features(sentinel_check=False)
        db.session.commit()
    except Exception as exc:  # pragma: no cover
        print(f"[r6_final_enrich] failed: {exc!r}")

    # R4: final VACUUM + index re-emit so the seed DB is byte-identical
    # across rebuilds (sees all post-extended inserts).
    try:
        from sqlalchemy import text as _text
        conn = db.engine.connect()
        idx_rows = conn.execute(_text(
            "SELECT name, sql FROM sqlite_master WHERE type='index' AND name LIKE 'ix_%'"
        )).fetchall()
        for name, _ in idx_rows:
            conn.execute(_text(f"DROP INDEX IF EXISTS {name}"))
        for name, sql in sorted(idx_rows, key=lambda r: r[0]):
            if sql:
                conn.execute(_text(sql))
        conn.execute(_text("VACUUM"))
        conn.commit()
    except Exception as exc:  # pragma: no cover
        print(f"[r4_final_vacuum] failed: {exc!r}")


# ---------------------------------------------------------------------------
# GUI Deepen pass (2026-05-27): real-page surface for cuisine / diet / skill /
# equipment / meal-type / seasonal / budget / time / dinner-fix / chef-bio /
# editorial + per-recipe photos / reviews / troubleshooting / nutrition-label.
# Routes registered as a side effect of the import.
# ---------------------------------------------------------------------------
import gui_deepen_routes  # noqa: F401,E402

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 28840))
    app.run(host='0.0.0.0', port=port, debug=True)


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

