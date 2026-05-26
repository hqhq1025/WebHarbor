#!/usr/bin/env python3
"""Amazon.com mirror - Flask application with full CRUD."""
import os
import json
import random
import re
from datetime import datetime, timedelta
from functools import wraps

from flask import (Flask, render_template, request, redirect, url_for,
                   flash, jsonify, session, abort, g, make_response)
from flask_sqlalchemy import SQLAlchemy
from flask_login import (LoginManager, UserMixin, login_user, logout_user,
                         login_required, current_user)
from flask_wtf import FlaskForm
from flask_wtf.csrf import CSRFProtect, generate_csrf
from flask_bcrypt import Bcrypt
from wtforms import StringField, PasswordField, TextAreaField, IntegerField, SelectField
from wtforms.validators import DataRequired, Email, Length, EqualTo, Optional, NumberRange
from sqlalchemy import or_, func

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Mirror reference date — pins datetime defaults so /reset rebuilds are
# byte-identical (see harden-env/gotchas.md). Live writes (new orders, reviews,
# returns) still use real datetime.utcnow() via the route handlers.
MIRROR_REFERENCE_DATE = datetime(2026, 4, 15)


def _seed_now():
    return MIRROR_REFERENCE_DATE


app = Flask(__name__)
app.config['SECRET_KEY'] = 'amazon-mirror-secret-key-change-in-prod'
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{os.path.join(BASE_DIR, 'instance', 'amazon_store.db')}"
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


# ----- Models -----

class User(db.Model, UserMixin):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    name = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(30), default='')
    address_line1 = db.Column(db.String(200), default='')
    address_line2 = db.Column(db.String(200), default='')
    city = db.Column(db.String(100), default='')
    state = db.Column(db.String(50), default='')
    zip_code = db.Column(db.String(20), default='')
    country = db.Column(db.String(50), default='United States')
    is_prime = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=_seed_now)

    cart_items = db.relationship('CartItem', backref='user', lazy=True, cascade='all, delete-orphan')
    orders = db.relationship('Order', backref='user', lazy=True, cascade='all, delete-orphan')
    wishlist_items = db.relationship('WishlistItem', backref='user', lazy=True, cascade='all, delete-orphan')
    reviews = db.relationship('Review', backref='user', lazy=True, cascade='all, delete-orphan')
    payment_methods = db.relationship('PaymentMethod', backref='user', lazy=True, cascade='all, delete-orphan')
    saved_addresses = db.relationship('SavedAddress', backref='user', lazy=True, cascade='all, delete-orphan')

    def set_password(self, pw):
        self.password_hash = bcrypt.generate_password_hash(pw).decode('utf-8')

    def check_password(self, pw):
        return bcrypt.check_password_hash(self.password_hash, pw)


class Category(db.Model):
    __tablename__ = 'categories'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    slug = db.Column(db.String(80), unique=True, nullable=False, index=True)
    icon = db.Column(db.String(20), default='')
    description = db.Column(db.Text, default='')


class Product(db.Model):
    __tablename__ = 'products'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    slug = db.Column(db.String(255), unique=True, nullable=False, index=True)
    brand = db.Column(db.String(100), default='')
    category_slug = db.Column(db.String(80), index=True)
    subcategory = db.Column(db.String(80), default='')
    description = db.Column(db.Text, default='')
    features = db.Column(db.Text, default='[]')  # JSON list
    specs = db.Column(db.Text, default='{}')  # JSON dict
    price = db.Column(db.Float, nullable=False)
    list_price = db.Column(db.Float, default=0.0)  # original price (strike-through)
    image = db.Column(db.String(500), default='')  # main thumbnail
    gallery_images = db.Column(db.Text, default='[]')  # JSON list of paths
    variant_options = db.Column(db.Text, default='{}')  # JSON dict: colors, sizes
    stock = db.Column(db.Integer, default=100)
    rating = db.Column(db.Float, default=4.5)
    review_count = db.Column(db.Integer, default=0)
    is_prime = db.Column(db.Boolean, default=True)
    is_featured = db.Column(db.Boolean, default=False)
    is_deal = db.Column(db.Boolean, default=False)
    is_bestseller = db.Column(db.Boolean, default=False)
    deal_discount = db.Column(db.Integer, default=0)  # percent off
    free_shipping = db.Column(db.Boolean, default=True)
    free_returns = db.Column(db.Boolean, default=True)
    condition = db.Column(db.String(30), default='New')  # New, Used - Like New, Used - Good, Used - Acceptable, Refurbished
    feature_tags = db.Column(db.Text, default='[]')  # JSON list — searchable feature keywords for filtering
    release_date = db.Column(db.String(20), default='')  # YYYY-MM-DD or "Pre-order: 2024-12-01"
    return_policy = db.Column(db.Text, default='30-day return policy. Eligible for free returns.')
    delivery_estimate = db.Column(db.String(100), default='FREE delivery in 2 days')
    created_at = db.Column(db.DateTime, default=_seed_now)

    cart_items = db.relationship('CartItem', backref='product', lazy=True, cascade='all, delete-orphan')
    order_items = db.relationship('OrderItem', backref='product', lazy=True)
    wishlist_items = db.relationship('WishlistItem', backref='product', lazy=True, cascade='all, delete-orphan')
    reviews = db.relationship('Review', backref='product', lazy=True, cascade='all, delete-orphan')

    def get_features(self):
        try:
            return json.loads(self.features or '[]')
        except Exception:
            return []

    def get_specs(self):
        try:
            return json.loads(self.specs or '{}')
        except Exception:
            return {}

    def get_gallery(self):
        try:
            return json.loads(self.gallery_images or '[]')
        except Exception:
            return []

    def get_variants(self):
        try:
            return json.loads(self.variant_options or '{}')
        except Exception:
            return {}

    def discount_percent(self):
        if self.list_price and self.list_price > self.price:
            return int(round((self.list_price - self.price) / self.list_price * 100))
        return 0

    def get_feature_tags(self):
        try:
            return json.loads(self.feature_tags or '[]')
        except Exception:
            return []

    def get_colors(self):
        return self.get_variants().get('color', []) or []

    def get_sizes(self):
        return self.get_variants().get('size', []) or []


class CartItem(db.Model):
    __tablename__ = 'cart_items'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    quantity = db.Column(db.Integer, default=1)
    variant = db.Column(db.String(100), default='')
    added_at = db.Column(db.DateTime, default=_seed_now)


class Order(db.Model):
    __tablename__ = 'orders'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    order_number = db.Column(db.String(40), unique=True, nullable=False)
    status = db.Column(db.String(30), default='processing')  # processing, shipped, delivered, cancelled
    subtotal = db.Column(db.Float, default=0)
    shipping = db.Column(db.Float, default=0)
    tax = db.Column(db.Float, default=0)
    total = db.Column(db.Float, default=0)
    ship_name = db.Column(db.String(120), default='')
    ship_address = db.Column(db.String(200), default='')
    ship_city = db.Column(db.String(100), default='')
    ship_state = db.Column(db.String(50), default='')
    ship_zip = db.Column(db.String(20), default='')
    payment_method = db.Column(db.String(30), default='Credit Card')
    payment_last4 = db.Column(db.String(10), default='1234')
    created_at = db.Column(db.DateTime, default=_seed_now)
    delivery_estimate = db.Column(db.String(50), default='')

    items = db.relationship('OrderItem', backref='order', lazy=True, cascade='all, delete-orphan')

    def item_count(self):
        return sum(i.quantity for i in self.items)


class OrderItem(db.Model):
    __tablename__ = 'order_items'
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    product_name = db.Column(db.String(255), default='')
    product_image = db.Column(db.String(500), default='')
    variant = db.Column(db.String(100), default='')
    quantity = db.Column(db.Integer, default=1)
    price = db.Column(db.Float, default=0)


class WishlistItem(db.Model):
    __tablename__ = 'wishlist_items'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    added_at = db.Column(db.DateTime, default=_seed_now)


class Review(db.Model):
    __tablename__ = 'reviews'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    rating = db.Column(db.Integer, default=5)
    title = db.Column(db.String(200), default='')
    body = db.Column(db.Text, default='')
    verified = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=_seed_now)


class PaymentMethod(db.Model):
    __tablename__ = 'payment_methods'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    card_type = db.Column(db.String(20), nullable=False)  # Visa, Mastercard, Amex, Discover
    last4 = db.Column(db.String(4), nullable=False)
    exp_month = db.Column(db.Integer, nullable=False)
    exp_year = db.Column(db.Integer, nullable=False)
    cardholder_name = db.Column(db.String(120), default='')
    is_default = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=_seed_now)


class SavedAddress(db.Model):
    __tablename__ = 'saved_addresses'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    label = db.Column(db.String(30), default='Home')  # Home, Work, Other
    full_name = db.Column(db.String(120), default='')
    phone = db.Column(db.String(30), default='')
    address_line1 = db.Column(db.String(200), nullable=False)
    address_line2 = db.Column(db.String(200), default='')
    city = db.Column(db.String(100), nullable=False)
    state = db.Column(db.String(50), nullable=False)
    zip_code = db.Column(db.String(20), nullable=False)
    country = db.Column(db.String(50), default='United States')
    is_default = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=_seed_now)


class Return(db.Model):
    __tablename__ = 'returns'
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    status = db.Column(db.String(30), default='requested')  # requested, approved, completed
    refund_method = db.Column(db.String(30), default='original_payment')  # original_payment, gift_card
    refund_amount = db.Column(db.Float, default=0)
    created_at = db.Column(db.DateTime, default=_seed_now)

    order = db.relationship('Order', backref='returns')
    items = db.relationship('ReturnItem', backref='return_request', lazy=True, cascade='all, delete-orphan')


class ReturnItem(db.Model):
    __tablename__ = 'return_items'
    id = db.Column(db.Integer, primary_key=True)
    return_id = db.Column(db.Integer, db.ForeignKey('returns.id'), nullable=False)
    order_item_id = db.Column(db.Integer, db.ForeignKey('order_items.id'), nullable=True)
    product_name = db.Column(db.String(255), default='')
    quantity = db.Column(db.Integer, default=1)
    reason = db.Column(db.String(60), default='')  # doesnt_fit, defective, changed_mind, wrong_item


# ----- Login -----

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# ----- Context processors -----

@app.context_processor
def inject_globals():
    cart_count = 0
    if current_user.is_authenticated:
        cart_count = db.session.query(func.sum(CartItem.quantity)).filter_by(user_id=current_user.id).scalar() or 0
    else:
        cart_count = sum(ci.get('quantity', 1) for ci in session.get('anon_cart', []))
    categories = Category.query.order_by(Category.id).all()
    return {
        'cart_count': cart_count,
        'nav_categories': categories,
        'csrf_token_value': generate_csrf(),
    }


# ----- Forms -----

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])


class RegisterForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired(), Length(min=2, max=120)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    confirm = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])


class ProfileForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired()])
    phone = StringField('Phone', validators=[Optional()])
    address_line1 = StringField('Address Line 1', validators=[Optional()])
    address_line2 = StringField('Address Line 2', validators=[Optional()])
    city = StringField('City', validators=[Optional()])
    state = StringField('State', validators=[Optional()])
    zip_code = StringField('ZIP Code', validators=[Optional()])
    country = StringField('Country', validators=[Optional()])


class PasswordForm(FlaskForm):
    current_password = PasswordField('Current Password', validators=[DataRequired()])
    new_password = PasswordField('New Password', validators=[DataRequired(), Length(min=6)])
    confirm = PasswordField('Confirm', validators=[DataRequired(), EqualTo('new_password')])


class CheckoutForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired()])
    address = StringField('Address', validators=[DataRequired()])
    city = StringField('City', validators=[DataRequired()])
    state = StringField('State', validators=[DataRequired()])
    zip_code = StringField('ZIP Code', validators=[DataRequired()])
    phone = StringField('Phone', validators=[Optional()])
    card_number = StringField('Card Number', validators=[DataRequired()])
    card_exp = StringField('Expiration', validators=[DataRequired()])
    card_cvv = StringField('CVV', validators=[DataRequired()])


class ReviewForm(FlaskForm):
    rating = IntegerField('Rating', validators=[DataRequired(), NumberRange(min=1, max=5)])
    title = StringField('Title', validators=[DataRequired(), Length(max=200)])
    body = TextAreaField('Review', validators=[DataRequired()])


class AddressForm(FlaskForm):
    label = SelectField('Address Label', choices=[('Home', 'Home'), ('Work', 'Work'), ('Other', 'Other')])
    full_name = StringField('Full Name', validators=[DataRequired()])
    phone = StringField('Phone', validators=[Optional()])
    address_line1 = StringField('Street Address', validators=[DataRequired()])
    address_line2 = StringField('Apt, Suite, Unit', validators=[Optional()])
    city = StringField('City', validators=[DataRequired()])
    state = StringField('State', validators=[DataRequired()])
    zip_code = StringField('ZIP Code', validators=[DataRequired()])
    country = StringField('Country', validators=[Optional()])


class PaymentForm(FlaskForm):
    card_type = SelectField('Card Type', choices=[('Visa', 'Visa'), ('Mastercard', 'Mastercard'), ('Amex', 'American Express'), ('Discover', 'Discover')])
    card_number = StringField('Card Number', validators=[DataRequired()])
    exp_month = SelectField('Exp Month', choices=[(str(i), f'{i:02d}') for i in range(1, 13)])
    exp_year = SelectField('Exp Year', choices=[(str(i), str(i)) for i in range(2024, 2035)])
    cardholder_name = StringField('Name on Card', validators=[DataRequired()])


# ----- Routes: Static Pages -----

@app.route('/')
def index():
    from sqlalchemy.sql import func as _func
    # Randomize home-page product lists so each refresh shows different items.
    featured = Product.query.filter_by(is_featured=True).order_by(_func.random()).limit(12).all()
    deals = Product.query.filter_by(is_deal=True).order_by(_func.random()).limit(8).all()
    bestsellers = Product.query.filter_by(is_bestseller=True).order_by(_func.random()).limit(12).all()
    electronics = Product.query.filter_by(category_slug='electronics').order_by(_func.random()).limit(6).all()
    fashion = Product.query.filter_by(category_slug='fashion').order_by(_func.random()).limit(6).all()
    home_goods = Product.query.filter_by(category_slug='home').order_by(_func.random()).limit(6).all()
    books = Product.query.filter_by(category_slug='books').order_by(_func.random()).limit(6).all()
    computers = Product.query.filter_by(category_slug='computers').order_by(_func.random()).limit(6).all()
    # Explicit beauty list — the template previously post-filtered a generic
    # slice and often rendered nothing when no beauty product happened to be
    # in the first 4. Now we pass a dedicated random sample with fallback.
    beauty = (Product.query.filter_by(category_slug='beauty', is_bestseller=True)
              .order_by(_func.random()).limit(4).all())
    if len(beauty) < 4:
        seen = {p.id for p in beauty}
        q = Product.query.filter_by(category_slug='beauty')
        if seen:
            q = q.filter(~Product.id.in_(seen))
        extra = q.order_by(_func.random()).limit(4 - len(beauty)).all()
        beauty += extra

    resp = make_response(render_template('index.html',
        featured=featured, deals=deals, bestsellers=bestsellers,
        electronics=electronics, fashion=fashion, home_goods=home_goods,
        books=books, computers=computers, beauty=beauty))
    # Prevent browser from caching the home page so each refresh re-shuffles.
    resp.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    resp.headers['Pragma'] = 'no-cache'
    return resp


def _apply_filters(query_obj):
    """Apply request.args filters to a Product query. Used by /search and /c/<slug>."""
    from sqlalchemy import and_

    # Price range
    min_price = request.args.get('min_price', type=float)
    max_price = request.args.get('max_price', type=float)
    if min_price is not None:
        query_obj = query_obj.filter(Product.price >= min_price)
    if max_price is not None:
        query_obj = query_obj.filter(Product.price <= max_price)

    # Rating
    min_rating = request.args.get('min_rating', type=float)
    if min_rating is not None:
        query_obj = query_obj.filter(Product.rating >= min_rating)

    # Reviews
    min_reviews = request.args.get('min_reviews', type=int)
    if min_reviews is not None:
        query_obj = query_obj.filter(Product.review_count >= min_reviews)

    # Brand
    brand = request.args.get('brand', '').strip()
    if brand:
        query_obj = query_obj.filter(Product.brand.ilike(f'%{brand}%'))

    # Condition (New, Used - Good, etc.)
    condition = request.args.get('condition', '').strip()
    if condition:
        query_obj = query_obj.filter(Product.condition == condition)

    # Prime
    if request.args.get('prime') == '1':
        query_obj = query_obj.filter(Product.is_prime == True)

    # Deals
    if request.args.get('deal') == '1':
        query_obj = query_obj.filter(Product.is_deal == True)

    # Bestseller
    if request.args.get('bestseller') == '1':
        query_obj = query_obj.filter(Product.is_bestseller == True)

    # Free shipping
    if request.args.get('free_shipping') == '1':
        query_obj = query_obj.filter(Product.free_shipping == True)

    # Free returns
    if request.args.get('free_returns') == '1':
        query_obj = query_obj.filter(Product.free_returns == True)

    # Color (substring match in variant_options JSON)
    color = request.args.get('color', '').strip()
    if color:
        query_obj = query_obj.filter(Product.variant_options.ilike(f'%{color}%'))

    # Size (match any of: exact, normalized, common aliases)
    size = request.args.get('size', '').strip()
    if size:
        from sqlalchemy import or_ as _or
        # Build alias list so "XXL" also matches "XX-Large", "2XL", etc.
        alias_map = {
            'xs': ['xs', 'x-small', 'extra small'],
            's': ['s', 'small'],
            'm': ['m', 'medium'],
            'l': ['l', 'large'],
            'xl': ['xl', 'x-large', 'extra large'],
            'xxl': ['xxl', 'xx-large', '2xl', '2x-large'],
            'xxxl': ['xxxl', 'xxx-large', '3xl', '3x-large'],
        }
        key = size.lower().replace('-', '').replace(' ', '')
        aliases = alias_map.get(key, [size])
        if size not in aliases:
            aliases.append(size)
        conds = [Product.variant_options.ilike(f'%"{a}"%') for a in aliases]
        query_obj = query_obj.filter(_or(*conds))

    # Feature tag (substring match in feature_tags JSON) — split on comma OR space
    feature = request.args.get('feature', '').strip()
    if feature:
        # Split on commas first, then split each chunk on spaces for individual tokens
        import re as _re
        tokens = _re.findall(r'[a-z0-9][\w-]*', feature.lower())
        for tok in tokens:
            if tok and len(tok) >= 2:
                query_obj = query_obj.filter(Product.feature_tags.ilike(f'%{tok}%'))

    # Publication / release year (matches leading 4-digit year in release_date string)
    year = request.args.get('year', '').strip()
    if year and year.isdigit() and len(year) == 4:
        query_obj = query_obj.filter(Product.release_date.ilike(f'%{year}%'))

    # R5: One-Day shipping eligibility (encoded as `one-day-shipping-eligible`
    # feature_tag during seed). Accept multiple aliases for the agent.
    if request.args.get('one_day') == '1' or request.args.get('one_day_shipping') == '1':
        query_obj = query_obj.filter(
            Product.feature_tags.ilike('%one-day-shipping-eligible%'))

    # R5: Climate Pledge Friendly filter.
    if request.args.get('climate_pledge') == '1':
        query_obj = query_obj.filter(
            Product.feature_tags.ilike('%climate-pledge-friendly%'))

    # R5: Subscribe & Save filter.
    if request.args.get('sns') == '1' or request.args.get('subscribe_save') == '1':
        query_obj = query_obj.filter(
            Product.feature_tags.ilike('%subscribe-and-save%'))

    # R5: Small Business badge filter.
    if request.args.get('small_business') == '1':
        query_obj = query_obj.filter(
            Product.feature_tags.ilike('%small-business%'))

    # R5: In stock only (used by sold-out tasks).
    if request.args.get('in_stock') == '1':
        query_obj = query_obj.filter(Product.stock > 0)

    # R5: Made-in country filter — accepts country word or full tag.
    made_in_raw = (request.args.get('made_in') or '').strip().lower()
    if made_in_raw:
        # Allow either "USA" / "United States" / "Japan" or "made-in-usa"
        country_to_tag = {
            'usa': 'made-in-usa', 'united states': 'made-in-usa',
            'us': 'made-in-usa', 'america': 'made-in-usa',
            'germany': 'made-in-germany', 'deutsche': 'made-in-germany',
            'japan': 'made-in-japan',
            'italy': 'made-in-italy', 'italia': 'made-in-italy',
            'vietnam': 'made-in-vietnam',
            'china': 'made-in-china',
            'mexico': 'made-in-mexico',
        }
        tag = country_to_tag.get(made_in_raw, made_in_raw)
        if not tag.startswith('made-in-'):
            tag = f'made-in-{tag}'
        query_obj = query_obj.filter(Product.feature_tags.ilike(f'%{tag}%'))

    return query_obj


def _apply_sort(results, sort_key):
    # Accept multiple naming conventions (price_asc / price_low / low_to_high, etc.)
    key = (sort_key or '').strip().lower()
    if key in ('price_asc', 'price_low', 'price-low', 'low_to_high', 'price-low-to-high', 'lowtohigh', 'low', 'priceasc'):
        return sorted(results, key=lambda p: p.price)
    if key in ('price_desc', 'price_high', 'price-high', 'high_to_low', 'price-high-to-low', 'hightolow', 'high', 'pricedesc'):
        return sorted(results, key=lambda p: p.price, reverse=True)
    if key in ('rating', 'avg_rating', 'avg-rating', 'customer_review', 'review_rating'):
        return sorted(results, key=lambda p: (p.rating, p.review_count), reverse=True)
    if key in ('reviews', 'review_count', 'most_reviews'):
        return sorted(results, key=lambda p: p.review_count, reverse=True)
    if key in ('newest', 'new', 'newest_arrivals', 'release_date'):
        return sorted(results, key=lambda p: p.created_at, reverse=True)
    if key in ('bestseller', 'best_sellers', 'best-sellers', 'popular'):
        return sorted(results, key=lambda p: (p.is_bestseller, p.review_count), reverse=True)
    return results  # featured / default — keep DB order


def _normalize_sort_key(sort_key):
    """Map any alias to the canonical value used in the dropdown <option> tags."""
    key = (sort_key or '').strip().lower()
    if key in ('price_asc', 'price_low', 'price-low', 'low_to_high', 'price-low-to-high', 'lowtohigh', 'low', 'priceasc'):
        return 'price_asc'
    if key in ('price_desc', 'price_high', 'price-high', 'high_to_low', 'price-high-to-low', 'hightolow', 'high', 'pricedesc'):
        return 'price_desc'
    if key in ('rating', 'avg_rating', 'avg-rating', 'customer_review', 'review_rating'):
        return 'rating'
    if key in ('reviews', 'review_count', 'most_reviews'):
        return 'reviews'
    if key in ('newest', 'new', 'newest_arrivals', 'release_date'):
        return 'newest'
    if key in ('bestseller', 'best_sellers', 'best-sellers', 'popular'):
        return 'bestseller'
    return ''


@app.route('/c/<slug>')
def category(slug):
    cat = Category.query.filter_by(slug=slug).first_or_404()
    q = Product.query.filter_by(category_slug=slug)
    sub = request.args.get('sub', '')
    if sub:
        q = q.filter(Product.subcategory == sub)
    q = _apply_filters(q)
    products = q.all()
    sort_raw = request.args.get('sort', '')
    products = _apply_sort(products, sort_raw)
    current_sort = _normalize_sort_key(sort_raw)

    all_products = Product.query.filter_by(category_slug=slug).all()
    subcats = sorted({p.subcategory for p in all_products if p.subcategory})
    return render_template('category.html', category=cat, products=products,
                           subcategories=subcats, current_sub=sub, current_sort=current_sort)


@app.route('/product/<slug>')
def product_detail(slug):
    product = Product.query.filter_by(slug=slug).first_or_404()
    related = Product.query.filter(
        Product.category_slug == product.category_slug,
        Product.id != product.id
    ).limit(8).all()
    all_reviews = Review.query.filter_by(product_id=product.id).order_by(Review.created_at.desc()).all()
    # Top review = highest-rated, then most recent among those
    top_review = None
    if all_reviews:
        top_review = sorted(all_reviews, key=lambda r: (r.rating, r.created_at), reverse=True)[0]
    # Limit displayed reviews to the top 10 most-recent (DBs hold a sampled 12-30 per product)
    reviews = all_reviews[:10]
    in_wishlist = False
    if current_user.is_authenticated:
        in_wishlist = WishlistItem.query.filter_by(user_id=current_user.id, product_id=product.id).first() is not None
    # R4: derived facets used by /product/<slug>/{questions,reviews,customer-images,aplus-content}
    # and the in-page Q&A accordion / FBT carousel. All are deterministic from
    # the product slug so they survive byte-id reset without new DB columns.
    qna = _synth_qna(product)
    fbt = _frequently_bought_together(product)
    aplus = _synth_aplus_content(product)
    seller_id, seller_name = _synth_seller(product)
    # R5: Out-of-stock alternative recommendations. When stock<=0, surface
    # 6 in-stock items from the same subcategory (fallback to category).
    oos_alternatives = []
    if product.stock <= 0:
        oos_alternatives = (Product.query
                            .filter(Product.subcategory == product.subcategory,
                                    Product.id != product.id,
                                    Product.stock > 0)
                            .order_by(Product.review_count.desc())
                            .limit(6).all())
        if not oos_alternatives:
            oos_alternatives = (Product.query
                                .filter(Product.category_slug == product.category_slug,
                                        Product.id != product.id,
                                        Product.stock > 0)
                                .order_by(Product.review_count.desc())
                                .limit(6).all())
    # R5: Subscribe & Save eligibility — derived from feature_tags.
    sns_eligible = 'subscribe-and-save' in (product.get_feature_tags() or [])
    return render_template('product_detail.html',
        product=product, related=related, reviews=reviews, top_review=top_review,
        in_wishlist=in_wishlist, review_form=ReviewForm(),
        qna=qna, fbt=fbt, aplus=aplus,
        seller_id=seller_id, seller_name=seller_name,
        oos_alternatives=oos_alternatives, sns_eligible=sns_eligible)


# ----- R4: Deterministic synthesis helpers for sub-pages -----
import hashlib as _hashlib


def _stable_hash(s):
    """Deterministic 32-bit unsigned hash. Used in place of Python's hash()
    which is salted per-process. Stable across builds and machines so synthesized
    Q&A / sellers / A+ content stay consistent.
    """
    return int.from_bytes(_hashlib.md5((s or '').encode('utf-8')).digest()[:4], 'big')


# Question / answer templates keyed by category slug. Picked deterministically
# from slug so each product gets the same five questions every render.
_QNA_BANK = {
    'electronics': [
        ('Does this work with iPhone 15 Pro Max?',
         'Yes — pairs over Bluetooth 5.x with any iOS 16+ device. Confirmed by the seller.',
         'Yes, works perfectly. I use mine with the 15 Pro daily.'),
        ('Is there a USB-C cable included in the box?',
         'A short USB-C to USB-C cable ships in the box. A wall adapter is sold separately.',
         'Mine came with a 1m cable, no adapter.'),
        ('Can I use this on a 220V outlet outside the US?',
         'The internal power supply is 100-240V auto-switching, so a simple plug adapter is enough.',
         'Used it in Germany with a 2-prong adapter, no transformer needed.'),
        ('How long is the warranty?',
         'Manufacturer warranty is 1 year limited. Amazon offers an optional 2-year protection plan at checkout.',
         'Mine had a 2-year warranty extension I bought for around $15.'),
        ('Will firmware updates be supported for older units?',
         'Yes — the manufacturer pushes firmware OTA for at least 3 years after launch.',
         'I got an update two months after I bought mine.'),
    ],
    'computers': [
        ('Can the RAM be upgraded after purchase?',
         'No. The RAM is soldered to the mainboard on this model; choose the configuration you want at purchase.',
         'I checked — it is soldered. Buy the 16GB if you think you might want it.'),
        ('Is the SSD user-replaceable?',
         'Yes, the M.2 NVMe slot is accessible after removing the bottom plate (Torx T5 screws).',
         'I swapped mine for a 2TB drive in about 10 minutes.'),
        ('Does it come with Microsoft Office?',
         'Office is not bundled; a 30-day Microsoft 365 trial is included and can be activated from the Start menu.',
         'Mine had the trial only — I use the free web apps instead.'),
        ('Can I use this for video editing in 4K?',
         'For light 4K editing on Premiere/DaVinci Resolve, yes; sustained color grading benefits from a dedicated GPU.',
         'I edit 4K footage on mine — proxy workflow makes it smooth.'),
        ('What ports does it have?',
         'Two USB-C (Thunderbolt 4), one USB-A 3.2, HDMI 2.1, SD card reader, and a 3.5mm combo jack.',
         'Plenty of ports for my docking setup.'),
    ],
    'home': [
        ('Is this dishwasher safe?',
         'The detachable parts are top-rack dishwasher safe. Hand-wash the motor base.',
         'Top rack only. Mine has held up over two years.'),
        ('What is the inner pot made of?',
         'Stainless steel, 18/8 grade, with an aluminum sandwich base for even heat distribution.',
         'Solid stainless, no nonstick coating to scratch.'),
        ('Does it fit under a standard kitchen cabinet?',
         'The total height is under 14 inches, fits standard 18-inch cabinet clearance.',
         'It fits under my cabinets with the lid open.'),
        ('What is the wattage / energy use?',
         'Rated at 1,200W peak; typical cook cycle averages under 0.4 kWh.',
         'Pulls about 1100W when actively cooking.'),
        ('Are replacement parts available?',
         'Yes. Seals, blades, and lid assemblies are sold directly by the manufacturer and via Amazon.',
         'I ordered a replacement gasket easily on Amazon.'),
    ],
    'fashion': [
        ('How does the sizing run?',
         'Sizing is true to standard US measurements. If you are between sizes, size up for a relaxed fit.',
         'I usually wear a Medium and Medium fits me well.'),
        ('Is the material stretchy?',
         'Yes — it includes 3% elastane for comfort movement without losing its shape after washing.',
         'Good 4-way stretch. Comfortable all day.'),
        ('Can I machine wash this?',
         'Machine wash cold, tumble dry low. Avoid bleach and fabric softeners.',
         'Holds up in the wash. No shrinking after several cycles.'),
        ('Is the color in the photo accurate?',
         'The product photos are taken in natural light and represent the color accurately within +/- 5% variance.',
         'Color is exactly what I expected.'),
        ('Does this run small in the chest or shoulders?',
         'The cut is slightly trim in the shoulders. Size up one if you have a broader build.',
         'I went up a size and it fits perfectly.'),
    ],
    'books': [
        ('Is this the most recent edition?',
         'Yes — this listing reflects the latest edition with updated references and an expanded index.',
         'I confirmed it matches the latest 4th-edition cover.'),
        ('Are there exercises or chapter summaries?',
         'Each chapter ends with a summary and 4-6 practice questions; an answer key is included in the appendix.',
         'Useful exercises at the end of each chapter.'),
        ('Is the Kindle version identical in content to the paperback?',
         'The text is identical. Some color illustrations are rendered in grayscale on non-color Kindles.',
         'Same content, easier to highlight on Kindle.'),
        ('Does it include access to online resources?',
         'A printed access code on the inside cover unlocks a companion website with practice tests for 12 months.',
         'Mine had a code I used for the practice site.'),
        ('What reading level is this targeted at?',
         'High school senior / early college. No prior background in the subject is required.',
         'Approachable even without prior knowledge.'),
    ],
    'beauty': [
        ('Is this product cruelty-free?',
         'Yes — Leaping Bunny certified. Not tested on animals at any stage of production.',
         'Confirmed cruelty-free on the brand site.'),
        ('Does this work for sensitive skin?',
         'Formulated without fragrance, alcohol, or sulfates; dermatologist-tested for sensitive skin.',
         'No irritation on my sensitive skin.'),
        ('How many uses per bottle?',
         'Approximately 40-50 applications per bottle when used as directed (twice daily).',
         'Lasts me about 6 weeks with daily use.'),
        ('Can I use this with retinol or vitamin C?',
         'Yes — layer this in the morning under SPF; use your retinol product at night to avoid sensitivity.',
         'I use it AM under sunscreen, no issues.'),
        ('Is the shade match accurate?',
         'The shade range matches Fenty/MAC reference shades. Each shade has a tooltip with undertone notes.',
         'I matched my MAC NC30 — accurate.'),
    ],
    'sports': [
        ('What is the size of the largest weight increment?',
         'Increments are 2.5 lb per dial click up to 25 lb, then 5 lb per click up to the max.',
         'Smooth dial action, easy to switch weights.'),
        ('Is assembly required?',
         'Minimal — the legs and handle attach with the included hex wrench in under 15 minutes.',
         'Assembly took me about 10 minutes.'),
        ('Is this safe for outdoor use?',
         'Yes. The frame and bearings are rated for outdoor temperature swings; store covered when not in use.',
         'I keep mine on a covered patio year-round.'),
        ('Does it include the subscription / app?',
         'A 30-day trial of the partner app is included. Full features require a paid subscription afterward.',
         'Trial worked fine; I subscribed monthly after.'),
        ('What weight capacity does it support?',
         'Rated for users up to 300 lb with a 5x safety factor on the frame.',
         'I am 220 lb and it feels rock solid.'),
    ],
    'toys': [
        ('What age range is this best for?',
         'Recommended for ages 6+. Some smaller pieces make it unsuitable for children under 3.',
         'My 7-year-old loved it. Too small for toddlers.'),
        ('Are the pieces compatible with other sets?',
         'Yes — all standard LEGO bricks and connectors interchange across themes.',
         'Mixes with my older Star Wars sets just fine.'),
        ('How long does assembly take?',
         'Typical first-time build is 2-3 hours; the included instruction booklet has 200+ steps.',
         'Took my daughter and me about 2.5 hours.'),
        ('Are batteries included?',
         'Three AA batteries are included for the electronic components.',
         'Came with batteries, started right away.'),
        ('Is the storage box included?',
         'A reusable storage box with internal dividers is included for sorting pieces between builds.',
         'Nice sturdy box, helpful for keeping pieces.'),
    ],
}


def _synth_qna(product):
    """Synthesize 5 deterministic Q&A entries for a product.

    Each Q&A is sourced from the category bank, picked deterministically by
    slug-hash. Helpful counts are also derived from the hash so they stay
    consistent across renders.
    """
    bank = _QNA_BANK.get(product.category_slug or '', _QNA_BANK['electronics'])
    h = _stable_hash(product.slug)
    out = []
    for i, (q, seller_a, customer_a) in enumerate(bank):
        helpful = (h >> (i * 3)) & 0xFF
        rolled = (h >> (i * 5)) & 0xFFF
        out.append({
            'id': f"{product.id}-{i+1}",
            'question': q,
            'asked_by': ['Mark T.', 'Janet S.', 'Christopher L.', 'Priya P.', 'Diego R.'][i],
            'asked_on': MIRROR_REFERENCE_DATE - timedelta(days=30 + (rolled % 320)),
            'answers': [
                {'name': f'Seller ({product.brand or "Manufacturer"})',
                 'is_seller': True, 'body': seller_a,
                 'helpful': 5 + (helpful % 80)},
                {'name': ['Robert P.', 'Lin H.', 'Ana C.', 'Tom W.', 'Mei L.'][i],
                 'is_seller': False, 'body': customer_a,
                 'helpful': 1 + ((helpful >> 4) % 40)},
            ],
        })
    return out


def _frequently_bought_together(product):
    """Pick 3 deterministic related products to render in the FBT carousel."""
    h = _stable_hash(product.slug)
    # Pull same-category siblings (excluding self), then pick 3 deterministically.
    siblings = (Product.query
                .filter(Product.category_slug == product.category_slug,
                        Product.id != product.id)
                .order_by(Product.id)
                .limit(80).all())
    if not siblings:
        return []
    picks = []
    used = set()
    for i in range(3):
        if not siblings:
            break
        idx = (h >> (i * 7)) % len(siblings)
        # Skip duplicates deterministically by walking forward.
        tries = 0
        while idx in used and tries < len(siblings):
            idx = (idx + 1) % len(siblings)
            tries += 1
        used.add(idx)
        picks.append(siblings[idx])
    return picks


def _synth_aplus_content(product):
    """Deterministic A+ marketing content blocks (Enhanced Brand Content)."""
    h = _stable_hash(product.slug + 'aplus')
    benefits_pool = [
        ('Designed by experts', 'Engineered with input from industry veterans for everyday reliability.'),
        ('Built to last', 'Premium materials and rigorous quality testing for years of use.'),
        ('Trusted by millions', f'{(h % 50000) + 50000:,}+ verified five-star reviews across our brand.'),
        ('Sustainable production', 'Recycled materials and energy-efficient manufacturing certified by SGS.'),
        ('Award-winning design', f'Recipient of the {2024 + (h % 3)} Red Dot Design Award.'),
        ('Best-in-class warranty', 'A full {0}-year warranty with 30-day no-questions-asked returns.'.format(2 + (h % 4))),
        ('Made with care', 'Each unit hand-inspected and assembled by a small team in our certified factory.'),
        ('Designed for accessibility', 'Voice control, large-print labels, and screen-reader compatibility built in.'),
    ]
    picks = []
    used = set()
    for i in range(4):
        idx = (h >> (i * 4)) % len(benefits_pool)
        tries = 0
        while idx in used and tries < len(benefits_pool):
            idx = (idx + 1) % len(benefits_pool)
            tries += 1
        used.add(idx)
        picks.append(benefits_pool[idx])
    gallery = product.get_gallery() or []
    return {
        'hero_title': f'The {product.brand or "premium"} difference',
        'hero_subtitle': product.description[:160] if product.description else
                          f'Discover what makes {product.name} stand out.',
        'benefits': picks,
        'hero_image': gallery[0] if gallery else product.image,
        'showcase_images': gallery[1:5] if len(gallery) > 1 else [],
        'video_url': '',  # No real video; left blank for now.
    }


def _synth_seller(product):
    """Map product to a synthetic seller (id + name) based on brand/category."""
    # Brand-anchored seller, with a small per-category disambiguator so the
    # same brand can have different sellers across categories (mirrors reality).
    key = (product.brand or 'Amazon.com') + '|' + (product.category_slug or '')
    sid = _stable_hash(key) % 9000 + 1000
    # Seller name: brand for branded products, generic third-party for unbranded.
    if product.brand:
        suffix = ['Direct', 'Official Store', 'Authorized Reseller',
                  'Authorized Dealer', 'Brand Outlet'][sid % 5]
        name = f'{product.brand} {suffix}'
    else:
        name = ['NorthBay Marketplace', 'Pacific Trade Co.', 'Atlas Goods',
                'Bluewave Retail', 'Cascade Supply Co.'][sid % 5]
    return sid, name


# ----- R4: Product sub-pages (Q&A, deep reviews, customer images, seller, A+, author) -----

@app.route('/product/<slug>/questions')
def product_questions(slug):
    product = Product.query.filter_by(slug=slug).first_or_404()
    qna = _synth_qna(product)
    # Sort by helpful count (descending) so the most-upvoted question floats up,
    # matching how Amazon orders /ask pages.
    sort_key = (request.args.get('sort') or '').lower()
    if sort_key in ('recent', 'newest'):
        qna = sorted(qna, key=lambda q: q['asked_on'], reverse=True)
    else:
        qna = sorted(qna, key=lambda q: q['answers'][0]['helpful'] +
                                         q['answers'][1]['helpful'], reverse=True)
    return render_template('product_questions.html', product=product, qna=qna,
                           current_sort=sort_key or 'helpful')


@app.route('/product/<slug>/reviews')
def product_reviews(slug):
    product = Product.query.filter_by(slug=slug).first_or_404()
    page = max(1, request.args.get('page', 1, type=int))
    per_page = 10
    star_filter = request.args.get('star', type=int)
    sort_key = (request.args.get('sort') or '').lower()
    base = Review.query.filter_by(product_id=product.id)
    if star_filter and 1 <= star_filter <= 5:
        base = base.filter_by(rating=star_filter)
    if sort_key in ('helpful', 'top'):
        base = base.order_by(Review.rating.desc(), Review.created_at.desc())
    elif sort_key in ('oldest',):
        base = base.order_by(Review.created_at.asc())
    else:
        base = base.order_by(Review.created_at.desc())
    total = base.count()
    pages = max(1, (total + per_page - 1) // per_page)
    page = min(page, pages)
    reviews = base.offset((page - 1) * per_page).limit(per_page).all()
    # Star histogram for filter sidebar
    star_counts = {i: Review.query.filter_by(product_id=product.id, rating=i).count()
                   for i in range(1, 6)}
    return render_template('product_reviews.html', product=product, reviews=reviews,
                           page=page, pages=pages, total=total,
                           star_filter=star_filter, current_sort=sort_key or 'recent',
                           star_counts=star_counts)


@app.route('/product/<slug>/customer-images')
def product_customer_images(slug):
    product = Product.query.filter_by(slug=slug).first_or_404()
    gallery = product.get_gallery()
    # Synthesize uploader names + dates so the page feels like a real customer
    # photo grid, not just the product's marketing shots.
    h = _stable_hash(product.slug + 'images')
    uploaders = ['Sarah K.', 'Marcus L.', 'Devon W.', 'Priya R.', 'Tatsu O.',
                 'Andrea N.', 'Carlos M.', 'Ben S.', 'Liang H.', 'Olivia P.',
                 'Hassan A.', 'Yuki M.']
    image_cards = []
    for i, path in enumerate([product.image] + gallery[:11]):
        days_ago = 7 + ((h >> (i * 4)) % 280)
        image_cards.append({
            'path': path,
            'uploader': uploaders[i % len(uploaders)],
            'uploaded_on': MIRROR_REFERENCE_DATE - timedelta(days=days_ago),
            'helpful': 2 + ((h >> (i * 3)) % 180),
        })
    return render_template('product_customer_images.html', product=product,
                           image_cards=image_cards)


@app.route('/product/<slug>/aplus-content')
@app.route('/aplus-content/<slug>')
def aplus_content(slug):
    product = Product.query.filter_by(slug=slug).first_or_404()
    aplus = _synth_aplus_content(product)
    return render_template('aplus_content.html', product=product, aplus=aplus)


@app.route('/seller/<int:seller_id>')
def seller_storefront(seller_id):
    # Find all products whose synthesized seller_id matches this id.
    # We scan products grouped by brand (small set ~150 brands) so this is
    # cheap; the heavy filter is the synth-id match.
    candidates = (db.session.query(Product.brand, Product.category_slug)
                  .distinct().all())
    matching_brands = []
    for brand, cat in candidates:
        sid, _ = _synth_seller(_StubProduct(brand, cat))
        if sid == seller_id:
            matching_brands.append((brand, cat))
    if not matching_brands:
        abort(404)
    # Build the product list across all matching (brand, category) pairs.
    seller_name = _synth_seller(_StubProduct(*matching_brands[0]))[1]
    from sqlalchemy import or_, and_
    conds = []
    for brand, cat in matching_brands:
        conds.append(and_(Product.brand == brand, Product.category_slug == cat))
    products = (Product.query.filter(or_(*conds))
                .order_by(Product.is_bestseller.desc(),
                          Product.review_count.desc()).limit(60).all())
    # Synthesized seller stats
    h = _stable_hash(seller_name)
    seller_stats = {
        'positive_rating': 90 + (h % 9),  # 90-98%
        'rating_count': 1000 + (h % 90000),
        'years_active': 3 + (h % 15),
        'ships_from': ['Seattle, WA', 'Phoenix, AZ', 'Newark, NJ', 'Atlanta, GA',
                       'Dallas, TX'][h % 5],
    }
    return render_template('seller_storefront.html',
                           seller_id=seller_id, seller_name=seller_name,
                           products=products, seller_stats=seller_stats,
                           brands=sorted({b for b, _ in matching_brands}))


class _StubProduct:
    """Lightweight shim for _synth_seller when we don't have a full Product row."""
    __slots__ = ('brand', 'category_slug')
    def __init__(self, brand, category_slug):
        self.brand = brand
        self.category_slug = category_slug


@app.route('/author/<path:name>')
def author_page(name):
    # Books store authors in the brand column. Match on ilike for permissive lookup.
    decoded = name.replace('-', ' ').strip()
    books = (Product.query
             .filter(Product.category_slug == 'books',
                     Product.brand.ilike(f'%{decoded}%'))
             .order_by(Product.review_count.desc())
             .limit(80).all())
    if not books:
        abort(404)
    # Pick a representative book for hero image
    headline = books[0]
    # Synthesize a brief author bio (deterministic) from the name.
    h = _stable_hash(decoded)
    eras = ['contemporary', 'modern', 'classic', 'best-selling', 'award-winning']
    countries = ['American', 'British', 'Canadian', 'Australian', 'Irish',
                 'Indian', 'Nigerian', 'Japanese', 'Spanish', 'Brazilian']
    bio_themes = ['fiction and non-fiction across multiple genres',
                  'novels exploring identity, memory, and place',
                  'thrillers, mysteries, and short-form fiction',
                  'literary fiction and essays',
                  'science fiction, fantasy, and speculative work',
                  'historical fiction and biography']
    bio = (
        f'{decoded.title()} is a {eras[h % len(eras)]} '
        f'{countries[(h >> 4) % len(countries)]} author who has written '
        f'{bio_themes[(h >> 8) % len(bio_themes)]}. With {len(books)} titles in our '
        f'catalog and over {sum(b.review_count for b in books):,} verified ratings, '
        f'their work has been translated into {3 + (h % 25)} languages.'
    )
    return render_template('author_page.html', author=decoded.title(),
                           books=books, headline=headline, bio=bio)


STOPWORDS = {'the', 'a', 'an', 'of', 'in', 'on', 'at', 'to', 'for', 'with',
             'and', 'or', 'is', 'are', 'be', 'by', 'from', 'as', 'that', 'this',
             'mens', 'womens', 'men', 'women', 'kids', 'boys', 'girls'}
# Note: gender words are in STOPWORDS so they can't slip between women's<->men's via
# substring tricks like "womens" containing "mens". Category/subcategory filters
# still pin the right gender bucket because of the category_slug/brand/description match.


def _score_product(product, tokens):
    """Score a product against a list of search tokens.

    Returns (distinct_matches, total_occurrences). Matching uses word-boundary
    semantics on a tokenised haystack so 'mens' does NOT match 'womens' etc.
    """
    raw = ' '.join([
        (product.name or ''),
        (product.brand or ''),
        (product.description or ''),
        (product.category_slug or ''),
        (product.subcategory or ''),
        (product.feature_tags or ''),
        (product.specs or ''),
    ]).lower()
    hay_tokens = set(re.findall(r'[a-z0-9]+', raw))
    hay_raw = raw  # for substring fallback ("phone" inside "iphone")

    def _match(t):
        if t in hay_tokens:
            return True
        # Light plural/singular tolerance so 'polos'<->'polo', 'shoes'<->'shoe',
        # 'boxes'<->'box' all match. Only applied for tokens longer than 3 chars
        # to avoid nonsense like 'ie'<->'i'.
        if len(t) > 3:
            if t.endswith('es') and t[:-2] in hay_tokens:
                return True
            if t.endswith('s') and t[:-1] in hay_tokens:
                return True
            if (t + 's') in hay_tokens:
                return True
            if (t + 'es') in hay_tokens:
                return True
        # Prefix match for partial queries ("watc" → "watch", "lapto" → "laptop",
        # "Xbo" → "xbox"). Requires ≥3 chars to avoid noise, and the matched
        # haystack token must be at most 2× the query length to avoid absurd
        # broadenings like "ca" matching "calculator".
        if len(t) >= 3:
            for hw in hay_tokens:
                if hw.startswith(t) and len(hw) <= len(t) * 2 + 3:
                    return True
        # Substring fallback for "phone" in "iphone" / "headphone",
        # "book" in "notebook", etc. Requires ≥4 chars to avoid noise.
        # Gender words (men/mens/women/womens) are already stopwords so the
        # classic "mens" inside "womens" trap doesn't trigger.
        if len(t) >= 4 and t in hay_raw:
            return True
        return False

    distinct = sum(1 for t in tokens if _match(t))
    return distinct


@app.route('/search')
@app.route('/s')
def search():
    q = (request.args.get('q') or request.args.get('k') or '').strip()
    query_obj = Product.query
    query_obj = _apply_filters(query_obj)  # apply structural filters first
    candidates = query_obj.all()

    if q:
        # Tokenize: lowercase, drop stopwords, drop very short tokens
        tokens = [t.lower() for t in re.findall(r'[a-z0-9]+', q.lower())
                  if t and t not in STOPWORDS and len(t) >= 2]
        if tokens:
            # Require a strong majority of query tokens. This kills the "pad with
            # anything that matches one token" bleed (e.g. kettles matching
            # 'stainless'/'steel'/'kitchen' for a kitchen-sink query).
            if len(tokens) >= 5:
                min_required = (len(tokens) // 2) + 1            # e.g. 5->3, 6->4, 7->4
            elif len(tokens) >= 3:
                min_required = max(2, (len(tokens) + 1) // 2)    # e.g. 3->2, 4->2
            elif len(tokens) == 2:
                min_required = 2
            else:
                min_required = 1
            scored = []
            for p in candidates:
                s = _score_product(p, tokens)
                if s >= min_required:
                    scored.append((s, p))
            # Within each score tier, do a deterministic shuffle seeded by the
            # query string so the single "best" match isn't pinned at position
            # #1. This forces callers to actually read specs instead of clicking
            # result #1 — which is otherwise often the exact task answer when
            # both the query text and all constraints happen to fully align on
            # the same top product.
            query_seed = abs(hash(q.lower())) % (2**31)
            rng = random.Random(query_seed)
            # Group by score, shuffle each group, then reassemble in score desc
            from itertools import groupby
            scored.sort(key=lambda x: -x[0])
            results = []
            for _, group in groupby(scored, key=lambda x: x[0]):
                bucket = [p for _, p in group]
                rng.shuffle(bucket)
                results.extend(bucket)
            # No random padding / popular fallback — if the query genuinely has no
            # more matches we show whatever we have (may be zero).
        else:
            results = candidates
    else:
        results = candidates

    sort_raw = request.args.get('sort', '')
    results = _apply_sort(results, sort_raw)
    current_sort = _normalize_sort_key(sort_raw)

    # R5: Sponsored vs organic toggle. By default the first 3 high-rating
    # products are flagged "Sponsored" — passing ?sponsored=hide strips them
    # so callers can compare organic-only output.
    sponsored_mode = (request.args.get('sponsored') or '').strip().lower()
    sponsored_ids = set()
    if results and sponsored_mode != 'hide':
        # Deterministic: top 3 by (rating, review_count). Skip if too few.
        top_for_ads = sorted(results, key=lambda p: (p.rating, p.review_count),
                              reverse=True)[:3]
        sponsored_ids = {p.id for p in top_for_ads}
    elif sponsored_mode == 'hide':
        # Drop the same 3 candidates so the answer set genuinely differs.
        top_for_ads = sorted(results, key=lambda p: (p.rating, p.review_count),
                              reverse=True)[:3]
        drop_ids = {p.id for p in top_for_ads}
        results = [p for p in results if p.id not in drop_ids]

    return render_template('search.html', query=q, results=results,
                           current_sort=current_sort,
                           sponsored_ids=sponsored_ids,
                           sponsored_mode=sponsored_mode)


@app.route('/deals')
def deals():
    products = Product.query.filter_by(is_deal=True).all()
    return render_template('deals.html', products=products)


@app.route('/bestsellers')
def bestsellers():
    products = Product.query.filter_by(is_bestseller=True).all()
    return render_template('bestsellers.html', products=products)


@app.route('/prime')
def prime():
    products = Product.query.filter_by(is_prime=True).limit(30).all()
    return render_template('prime.html', products=products)


# R3: Individual Prime benefit detail pages — let agents navigate to a specific
# benefit (Prime Video / Music / Gaming / Reading / Delivery / Photos / Try Before You Buy).
PRIME_BENEFITS = {
    'video': {
        'title': 'Prime Video',
        'tagline': 'Thousands of movies and TV shows included with Prime.',
        'icon': '📺',
        'features': [
            'Award-winning Amazon Originals',
            'Watch on TV, phone, tablet, or computer',
            'Download to watch offline',
            'Add channels like HBO, SHOWTIME, STARZ for an extra cost',
            '4K UHD and HDR titles available',
        ],
        'monthly': 'Included with Prime ($14.99/mo)',
        'standalone': '$8.99/mo standalone',
    },
    'music': {
        'title': 'Prime Music',
        'tagline': '100 million songs and podcasts, ad-free, shuffled.',
        'icon': '🎵',
        'features': [
            'Ad-free music streaming',
            'Unlimited shuffle play of 100 million songs',
            'Millions of podcast episodes',
            'Upgrade to Music Unlimited for on-demand listening',
            'Cast to Echo and Fire TV devices',
        ],
        'monthly': 'Included with Prime ($14.99/mo)',
        'standalone': 'Music Unlimited: $10.99/mo standalone',
    },
    'gaming': {
        'title': 'Prime Gaming',
        'tagline': 'Free games every month + in-game content.',
        'icon': '🎮',
        'features': [
            'Free PC games every month',
            'Free in-game loot for popular titles',
            'Free monthly Twitch channel subscription',
            'Linked to your Amazon Prime account',
        ],
        'monthly': 'Included with Prime ($14.99/mo)',
        'standalone': 'Not sold separately',
    },
    'reading': {
        'title': 'Prime Reading',
        'tagline': 'Rotating catalog of 1,000+ books, magazines, and comics.',
        'icon': '📚',
        'features': [
            'Read on any Kindle device or app',
            'Borrow up to 10 titles at a time',
            'Magazine subscriptions included',
            'Audible Channels available',
            'No additional cost over Prime',
        ],
        'monthly': 'Included with Prime ($14.99/mo)',
        'standalone': 'Kindle Unlimited: $11.99/mo standalone',
    },
    'delivery': {
        'title': 'Prime Delivery',
        'tagline': 'FREE One-Day, Two-Day, and Same-Day delivery on eligible items.',
        'icon': '🚚',
        'features': [
            'FREE Two-Day Delivery on millions of items',
            'FREE One-Day Delivery in eligible ZIP codes',
            'FREE Same-Day Delivery on $25+ orders in 5,000+ cities',
            'FREE No-Rush Shipping rewards',
            'FREE Prime Wardrobe Try Before You Buy on eligible apparel',
        ],
        'monthly': 'Included with Prime ($14.99/mo)',
        'standalone': 'Not sold separately',
    },
    'photos': {
        'title': 'Prime Photos',
        'tagline': 'Unlimited full-resolution photo storage + 5 GB video storage.',
        'icon': '🖼️',
        'features': [
            'Unlimited full-resolution photo storage',
            '5 GB free video storage',
            'Share albums with up to 5 family members',
            'Auto-save from phone or computer',
            'Print photos and photo books directly from app',
        ],
        'monthly': 'Included with Prime ($14.99/mo)',
        'standalone': 'Not sold separately',
    },
    'wardrobe': {
        'title': 'Prime Try Before You Buy',
        'tagline': 'Try eligible clothing, shoes, and accessories for 7 days before paying.',
        'icon': '👕',
        'features': [
            'Try up to 6 items for 7 days',
            'Pay only for what you keep',
            'FREE returns via prepaid label',
            'Includes thousands of brands across apparel and shoes',
            'No styling fee',
        ],
        'monthly': 'Included with Prime ($14.99/mo)',
        'standalone': 'Not sold separately',
    },
}


@app.route('/prime/<benefit>')
def prime_benefit(benefit):
    b = PRIME_BENEFITS.get(benefit.lower())
    if not b:
        abort(404)
    return render_template('prime_benefit.html', benefit=b, slug=benefit.lower(),
                           all_benefits=PRIME_BENEFITS)


@app.route('/customer-service')
def customer_service():
    return render_template('customer_service.html')


@app.route('/gift-cards')
def gift_cards():
    return render_template('gift_cards.html')


@app.route('/todays-deals')
def todays_deals():
    # R3: dedicated Today's Deals page with lightning deals, deal categories,
    # and a "ends in" countdown — distinct from /deals (which is the full deals list).
    from sqlalchemy.sql import func as _func
    lightning = (Product.query.filter(Product.is_deal == True, Product.deal_discount >= 20)
                 .order_by(_func.random()).limit(8).all())
    deals_under_25 = (Product.query.filter(Product.is_deal == True, Product.price < 25)
                      .order_by(_func.random()).limit(12).all())
    deals_electronics = (Product.query.filter_by(is_deal=True, category_slug='electronics')
                         .order_by(_func.random()).limit(8).all())
    deals_home = (Product.query.filter_by(is_deal=True, category_slug='home')
                  .order_by(_func.random()).limit(8).all())
    deals_fashion = (Product.query.filter_by(is_deal=True, category_slug='fashion')
                     .order_by(_func.random()).limit(8).all())
    # Top-discount deals overall
    biggest = (Product.query.filter(Product.is_deal == True)
               .order_by(Product.deal_discount.desc()).limit(12).all())
    return render_template('todays_deals.html',
                           lightning=lightning, deals_under_25=deals_under_25,
                           deals_electronics=deals_electronics,
                           deals_home=deals_home, deals_fashion=deals_fashion,
                           biggest=biggest)


@app.route('/alexa-skills')
def alexa_skills():
    # R3: simple Alexa Skills directory page.
    skills_list = [
        {'name': 'Spotify',              'category': 'Music & Audio',    'rating': 4.4, 'reviews': 18420, 'desc': 'Stream your playlists from Spotify on any Alexa device.'},
        {'name': 'Question of the Day',  'category': 'Education',        'rating': 4.6, 'reviews': 92350, 'desc': 'A new trivia question every day from Volley Inc.'},
        {'name': 'TuneIn Live',          'category': 'News',             'rating': 4.3, 'reviews': 7245,  'desc': 'Live news, sports, music, and radio from around the world.'},
        {'name': 'Jeopardy!',            'category': 'Games & Trivia',   'rating': 4.5, 'reviews': 36120, 'desc': 'Play the classic answer-and-question game with Alexa.'},
        {'name': 'Sleep Sounds',         'category': 'Lifestyle',        'rating': 4.7, 'reviews': 142800,'desc': 'White noise, rain, ocean and more for restful sleep.'},
        {'name': 'Headspace',            'category': 'Health & Fitness', 'rating': 4.6, 'reviews': 5340,  'desc': 'Guided meditation and mindfulness sessions.'},
        {'name': 'NYT Briefing',         'category': 'News',             'rating': 4.2, 'reviews': 2890,  'desc': 'Latest news briefing from The New York Times.'},
        {'name': 'My Chef',              'category': 'Food & Drink',     'rating': 4.4, 'reviews': 1820,  'desc': 'Step-by-step recipes you can cook hands-free.'},
        {'name': 'Big Sky',              'category': 'Weather',          'rating': 4.5, 'reviews': 14250, 'desc': 'Hyper-local weather forecasts down to the minute.'},
        {'name': 'Skyriver Pro',         'category': 'Smart Home',       'rating': 4.3, 'reviews': 980,   'desc': 'Control smart lighting, locks, and thermostats.'},
        {'name': 'Animal Sounds',        'category': 'Kids',             'rating': 4.4, 'reviews': 51380, 'desc': 'Hear sounds of 100+ animals — great for kids.'},
        {'name': 'Bedtime Story',        'category': 'Kids',             'rating': 4.7, 'reviews': 38240, 'desc': 'Original bedtime stories voiced by Alexa.'},
        {'name': 'Ambient Coffee Shop',  'category': 'Lifestyle',        'rating': 4.5, 'reviews': 11820, 'desc': 'Background coffee shop ambience for working from home.'},
        {'name': 'Daily Word',           'category': 'Education',        'rating': 4.6, 'reviews': 22480, 'desc': 'Learn a new vocabulary word every day.'},
        {'name': 'Pizza Hut',            'category': 'Food & Drink',     'rating': 3.9, 'reviews': 4250,  'desc': 'Reorder your favorite Pizza Hut delivery hands-free.'},
        {'name': 'Domino\'s',            'category': 'Food & Drink',     'rating': 4.0, 'reviews': 5800,  'desc': 'Place a Domino\'s order using your saved Easy Order.'},
        {'name': 'Uber',                 'category': 'Travel & Transport','rating': 4.2,'reviews': 7920,  'desc': 'Request an Uber ride from your home or office.'},
        {'name': 'Lyft',                 'category': 'Travel & Transport','rating': 4.1,'reviews': 6480,  'desc': 'Request a Lyft ride to any saved destination.'},
        {'name': 'Capital One',          'category': 'Finance',          'rating': 3.8, 'reviews': 3120,  'desc': 'Check your account balance, recent transactions, and pay your bill.'},
        {'name': 'Trivia Hero',          'category': 'Games & Trivia',   'rating': 4.5, 'reviews': 18920, 'desc': 'Quiz yourself on history, science, sports, and pop culture.'},
    ]
    category_filter = request.args.get('category', '').strip()
    if category_filter:
        skills_list = [s for s in skills_list if s['category'].lower() == category_filter.lower()]
    sort_key = request.args.get('sort', '').strip().lower()
    if sort_key in ('rating', 'top_rated'):
        skills_list = sorted(skills_list, key=lambda s: (s['rating'], s['reviews']), reverse=True)
    elif sort_key in ('reviews', 'most_reviewed'):
        skills_list = sorted(skills_list, key=lambda s: s['reviews'], reverse=True)
    elif sort_key in ('name', 'a_z'):
        skills_list = sorted(skills_list, key=lambda s: s['name'].lower())
    categories = sorted({s['category'] for s in [
        {'category': 'Music & Audio'}, {'category': 'Education'}, {'category': 'News'},
        {'category': 'Games & Trivia'}, {'category': 'Lifestyle'}, {'category': 'Health & Fitness'},
        {'category': 'Food & Drink'}, {'category': 'Weather'}, {'category': 'Smart Home'},
        {'category': 'Kids'}, {'category': 'Travel & Transport'}, {'category': 'Finance'},
    ]})
    return render_template('alexa_skills.html', skills=skills_list, categories=categories,
                           current_category=category_filter, current_sort=sort_key)


@app.route('/amazon-business')
def amazon_business():
    return render_template('amazon_business.html')


@app.route('/registry')
def registry():
    return render_template('registry.html')


# ----- R5: Registry creation flows (Wedding / Baby) -----
# Stored in `session` so tasks can verify post-conditions without
# needing a full Registry table. The form has explicit server-side
# validation so the "missing field" task variants exercise error UI.

_REGISTRY_VALID_EVENTS = {'wedding', 'baby', 'birthday', 'housewarming', 'graduation'}


def _normalize_event_slug(event):
    return (event or '').strip().lower()


@app.route('/registry/<event>/create', methods=['GET', 'POST'])
@csrf.exempt
def registry_create(event):
    event = _normalize_event_slug(event)
    if event not in _REGISTRY_VALID_EVENTS:
        abort(404)
    errors = {}
    saved = None
    if request.method == 'POST':
        partner1 = (request.form.get('partner1') or '').strip()
        partner2 = (request.form.get('partner2') or '').strip()  # optional for non-wedding
        event_date = (request.form.get('event_date') or '').strip()
        city = (request.form.get('city') or '').strip()
        state = (request.form.get('state') or '').strip()
        # Required fields per event type
        if not partner1:
            errors['partner1'] = 'Registrant name is required.'
        if event == 'wedding' and not partner2:
            errors['partner2'] = 'Co-registrant (partner) name is required for a wedding registry.'
        if not event_date:
            errors['event_date'] = 'Event date is required (YYYY-MM-DD).'
        elif not re.match(r'^\d{4}-\d{2}-\d{2}$', event_date):
            errors['event_date'] = 'Use YYYY-MM-DD format.'
        if not city:
            errors['city'] = 'City is required.'
        if not state:
            errors['state'] = 'State is required.'
        if not errors:
            saved = {
                'event': event, 'partner1': partner1, 'partner2': partner2,
                'event_date': event_date, 'city': city, 'state': state,
            }
            # Persist most-recent registry per session for downstream verification.
            session['registry'] = saved
            flash(f'Your {event.title()} Registry has been created.', 'success')
            return redirect(url_for('registry_view'))
    return render_template('registry_create.html', event=event, errors=errors,
                           form_data=request.form)


@app.route('/registry/view')
def registry_view():
    reg = session.get('registry')
    return render_template('registry_view.html', registry=reg)


# ----- R5: Departments browse + Gift Finder + Subscribe & Save -----

@app.route('/departments')
def departments():
    """Browse all departments (categories) with item counts + featured picks."""
    cats = Category.query.order_by(Category.name).all()
    by_cat = {}
    for c in cats:
        products = Product.query.filter_by(category_slug=c.slug).limit(6).all()
        count = Product.query.filter_by(category_slug=c.slug).count()
        by_cat[c.slug] = {'category': c, 'products': products, 'count': count}
    return render_template('departments.html', by_cat=by_cat, cats=cats)


@app.route('/gift-finder', methods=['GET', 'POST'])
def gift_finder():
    """Recipient + budget + occasion → curated product list."""
    recipient = (request.args.get('recipient') or '').strip().lower()
    occasion = (request.args.get('occasion') or '').strip().lower()
    try:
        budget = int(request.args.get('budget') or 0)
    except ValueError:
        budget = 0
    recipients = ['her', 'him', 'kids', 'baby', 'teens', 'parents', 'pet']
    occasions = ['birthday', 'wedding', 'baby-shower', 'graduation', 'holiday', 'anniversary']
    results = []
    if recipient or occasion or budget:
        q = Product.query
        if budget > 0:
            q = q.filter(Product.price <= budget)
        # Map recipient → category hints
        cat_hints = {
            'kids': ['toys'], 'baby': ['toys'], 'teens': ['electronics', 'fashion'],
            'her': ['beauty', 'fashion'], 'him': ['electronics', 'fashion'],
            'parents': ['home', 'books'], 'pet': ['home'],
        }
        hints = cat_hints.get(recipient, [])
        if hints:
            q = q.filter(Product.category_slug.in_(hints))
        results = q.order_by(Product.review_count.desc()).limit(24).all()
    return render_template('gift_finder.html',
                           recipients=recipients, occasions=occasions,
                           recipient=recipient, occasion=occasion, budget=budget,
                           results=results)


@app.route('/subscribe-save', methods=['GET', 'POST'])
def subscribe_save():
    """Landing page + frequency change form. Selections stored in session for
    deterministic post-condition checks."""
    valid_freq = {'1-month', '2-month', '3-month', '6-month'}
    if request.method == 'POST':
        slug = (request.form.get('slug') or '').strip()
        freq = (request.form.get('frequency') or '').strip()
        if not slug:
            flash('Choose a product to subscribe to.', 'error')
        elif freq not in valid_freq:
            flash('Pick a valid delivery frequency (1, 2, 3, or 6 months).', 'error')
        else:
            prod = Product.query.filter_by(slug=slug).first()
            if not prod:
                flash('That product was not found.', 'error')
            else:
                sns = session.get('subscribe_save', {})
                sns[slug] = freq
                session['subscribe_save'] = sns
                flash(f'Subscribe & Save: {prod.name} → {freq} delivery.', 'success')
                return redirect(url_for('subscribe_save'))
    # GET — list S&S-eligible products + current user subscriptions
    sns_products = Product.query.filter(
        Product.feature_tags.ilike('%subscribe-and-save%')
    ).order_by(Product.review_count.desc()).limit(40).all()
    active = session.get('subscribe_save', {})
    return render_template('subscribe_save.html',
                           products=sns_products, active=active,
                           frequencies=['1-month', '2-month', '3-month', '6-month'])


# ----- R5: AJAX search suggest -----

@app.route('/api/search/suggest')
def api_search_suggest():
    q = (request.args.get('q') or '').strip().lower()
    if len(q) < 2:
        return jsonify({'suggestions': []})
    # Match product name OR brand prefix; cap at 8. Also include category
    # auto-complete entries so 'ele…' suggests 'in Electronics'.
    name_matches = (Product.query
                    .filter(or_(Product.name.ilike(f'{q}%'),
                                Product.name.ilike(f'% {q}%'),
                                Product.brand.ilike(f'{q}%')))
                    .order_by(Product.review_count.desc())
                    .limit(8).all())
    cats = Category.query.filter(Category.name.ilike(f'{q}%')).limit(4).all()
    out = []
    seen = set()
    for c in cats:
        out.append({'text': c.name, 'kind': 'category',
                    'href': url_for('category', slug=c.slug)})
    for p in name_matches:
        if p.name.lower() in seen:
            continue
        seen.add(p.name.lower())
        out.append({'text': p.name, 'kind': 'product',
                    'href': url_for('product_detail', slug=p.slug)})
    return jsonify({'suggestions': out[:10]})


@app.route('/sell')
def sell():
    return render_template('sell.html')



# ----- Routes: Auth -----

@app.route('/login', methods=['GET', 'POST'])
@csrf.exempt
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.lower().strip()).first()
        if user and user.check_password(form.password.data):
            login_user(user)
            flash(f'Welcome back, {user.name}!', 'success')
            next_url = request.args.get('next')
            # Whitelist safe next targets: only internal GET-safe paths.
            # POST-only routes like /cart/add/<id> would return 405 on GET,
            # so fall back to /bag (cart) in that case.
            if next_url:
                # Only allow relative/internal paths (no scheme/host)
                if not next_url.startswith('/') or next_url.startswith('//'):
                    next_url = None
                elif '/cart/add' in next_url:
                    # POST-only route; redirect to the cart page instead
                    next_url = url_for('bag')
            return redirect(next_url or url_for('index'))
        flash('Invalid email or password.', 'error')
    return render_template('login.html', form=form)


@app.route('/register', methods=['GET', 'POST'])
@csrf.exempt
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = RegisterForm()
    if form.validate_on_submit():
        email = form.email.data.lower().strip()
        if User.query.filter_by(email=email).first():
            flash('That email is already registered.', 'error')
        else:
            user = User(email=email, name=form.name.data.strip())
            user.set_password(form.password.data)
            db.session.add(user)
            db.session.commit()
            login_user(user)
            flash('Welcome to Amazon!', 'success')
            return redirect(url_for('index'))
    return render_template('register.html', form=form)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been signed out.', 'info')
    return redirect(url_for('index'))


# ----- Routes: Account -----

@app.route('/account')
@login_required
def account():
    orders = Order.query.filter_by(user_id=current_user.id).order_by(Order.created_at.desc()).limit(5).all()
    wishlist_count = WishlistItem.query.filter_by(user_id=current_user.id).count()
    return render_template('account.html', orders=orders, wishlist_count=wishlist_count)


@app.route('/account/orders')
@login_required
def orders_list():
    orders = Order.query.filter_by(user_id=current_user.id).order_by(Order.created_at.desc()).all()
    return render_template('orders.html', orders=orders)


@app.route('/account/edit', methods=['GET', 'POST'])
@csrf.exempt
@login_required
def edit_profile():
    form = ProfileForm(obj=current_user)
    if form.validate_on_submit():
        current_user.name = form.name.data
        current_user.phone = form.phone.data or ''
        current_user.address_line1 = form.address_line1.data or ''
        current_user.address_line2 = form.address_line2.data or ''
        current_user.city = form.city.data or ''
        current_user.state = form.state.data or ''
        current_user.zip_code = form.zip_code.data or ''
        current_user.country = form.country.data or 'United States'
        db.session.commit()
        flash('Your profile has been updated.', 'success')
        return redirect(url_for('account'))
    return render_template('account_edit.html', form=form)


@app.route('/account/password', methods=['GET', 'POST'])
@csrf.exempt
@login_required
def change_password():
    form = PasswordForm()
    if form.validate_on_submit():
        if not current_user.check_password(form.current_password.data):
            flash('Current password is incorrect.', 'error')
        else:
            current_user.set_password(form.new_password.data)
            db.session.commit()
            flash('Your password has been changed.', 'success')
            return redirect(url_for('account'))
    return render_template('change_password.html', form=form)


@app.route('/account/delete', methods=['POST'])
@csrf.exempt
@login_required
def delete_account():
    user = current_user._get_current_object()
    logout_user()
    db.session.delete(user)
    db.session.commit()
    flash('Your account has been deleted.', 'info')
    return redirect(url_for('index'))


# ----- Routes: Saved Addresses -----

@app.route('/account/addresses')
@login_required
def addresses_list():
    addrs = SavedAddress.query.filter_by(user_id=current_user.id).order_by(SavedAddress.is_default.desc(), SavedAddress.created_at).all()
    return render_template('addresses.html', addresses=addrs)


@app.route('/account/addresses/add', methods=['GET', 'POST'])
@csrf.exempt
@login_required
def address_add():
    form = AddressForm()
    if form.validate_on_submit():
        addr = SavedAddress(
            user_id=current_user.id,
            label=form.label.data,
            full_name=form.full_name.data,
            phone=form.phone.data or '',
            address_line1=form.address_line1.data,
            address_line2=form.address_line2.data or '',
            city=form.city.data,
            state=form.state.data,
            zip_code=form.zip_code.data,
            country=form.country.data or 'United States',
            is_default=SavedAddress.query.filter_by(user_id=current_user.id).count() == 0,
        )
        db.session.add(addr)
        db.session.commit()
        flash('Address added.', 'success')
        return redirect(url_for('addresses_list'))
    return render_template('address_form.html', form=form, editing=False)


@app.route('/account/addresses/<int:addr_id>/edit', methods=['GET', 'POST'])
@csrf.exempt
@login_required
def address_edit(addr_id):
    addr = SavedAddress.query.filter_by(id=addr_id, user_id=current_user.id).first_or_404()
    form = AddressForm(obj=addr)
    if form.validate_on_submit():
        addr.label = form.label.data
        addr.full_name = form.full_name.data
        addr.phone = form.phone.data or ''
        addr.address_line1 = form.address_line1.data
        addr.address_line2 = form.address_line2.data or ''
        addr.city = form.city.data
        addr.state = form.state.data
        addr.zip_code = form.zip_code.data
        addr.country = form.country.data or 'United States'
        db.session.commit()
        flash('Address updated.', 'success')
        return redirect(url_for('addresses_list'))
    return render_template('address_form.html', form=form, editing=True, addr=addr)


@app.route('/account/addresses/<int:addr_id>/delete', methods=['POST'])
@csrf.exempt
@login_required
def address_delete(addr_id):
    addr = SavedAddress.query.filter_by(id=addr_id, user_id=current_user.id).first_or_404()
    was_default = addr.is_default
    db.session.delete(addr)
    if was_default:
        next_addr = SavedAddress.query.filter_by(user_id=current_user.id).first()
        if next_addr:
            next_addr.is_default = True
    db.session.commit()
    flash('Address removed.', 'success')
    return redirect(url_for('addresses_list'))


@app.route('/account/addresses/<int:addr_id>/set-default', methods=['POST'])
@csrf.exempt
@login_required
def address_set_default(addr_id):
    addr = SavedAddress.query.filter_by(id=addr_id, user_id=current_user.id).first_or_404()
    SavedAddress.query.filter_by(user_id=current_user.id).update({'is_default': False})
    addr.is_default = True
    db.session.commit()
    flash(f'{addr.label} address set as default.', 'success')
    return redirect(url_for('addresses_list'))


# ----- Routes: Payment Methods -----

@app.route('/account/payment')
@login_required
def payment_list():
    methods = PaymentMethod.query.filter_by(user_id=current_user.id).order_by(PaymentMethod.is_default.desc(), PaymentMethod.created_at).all()
    return render_template('payment.html', methods=methods)


@app.route('/account/payment/add', methods=['GET', 'POST'])
@csrf.exempt
@login_required
def payment_add():
    form = PaymentForm()
    if form.validate_on_submit():
        pm = PaymentMethod(
            user_id=current_user.id,
            card_type=form.card_type.data,
            last4=form.card_number.data[-4:],
            exp_month=int(form.exp_month.data),
            exp_year=int(form.exp_year.data),
            cardholder_name=form.cardholder_name.data,
            is_default=PaymentMethod.query.filter_by(user_id=current_user.id).count() == 0,
        )
        db.session.add(pm)
        db.session.commit()
        flash('Payment method added.', 'success')
        return redirect(url_for('payment_list'))
    return render_template('payment_form.html', form=form)


@app.route('/account/payment/<int:pm_id>/remove', methods=['POST'])
@csrf.exempt
@login_required
def payment_remove(pm_id):
    pm = PaymentMethod.query.filter_by(id=pm_id, user_id=current_user.id).first_or_404()
    was_default = pm.is_default
    db.session.delete(pm)
    if was_default:
        next_pm = PaymentMethod.query.filter_by(user_id=current_user.id).first()
        if next_pm:
            next_pm.is_default = True
    db.session.commit()
    flash('Payment method removed.', 'success')
    return redirect(url_for('payment_list'))


@app.route('/account/payment/<int:pm_id>/set-default', methods=['POST'])
@csrf.exempt
@login_required
def payment_set_default(pm_id):
    pm = PaymentMethod.query.filter_by(id=pm_id, user_id=current_user.id).first_or_404()
    PaymentMethod.query.filter_by(user_id=current_user.id).update({'is_default': False})
    pm.is_default = True
    db.session.commit()
    flash(f'{pm.card_type} ending in {pm.last4} set as default.', 'success')
    return redirect(url_for('payment_list'))


# ----- Routes: Cart / Bag -----

def _anon_cart_items():
    """Return list of dict-like items for session cart (anonymous users)."""
    items = []
    for ci in session.get('anon_cart', []):
        product = Product.query.get(ci.get('product_id'))
        if product:
            items.append({
                'id': ci.get('id', 0),
                'product': product,
                'quantity': ci.get('quantity', 1),
                'variant': ci.get('variant', ''),
            })
    return items


def _anon_cart_count():
    return sum(ci.get('quantity', 1) for ci in session.get('anon_cart', []))


class _AnonItem:
    """Duck-typed wrapper so bag.html loops can treat session items like CartItem objects."""
    def __init__(self, d):
        self.id = d['id']
        self.product = d['product']
        self.quantity = d['quantity']
        self.variant = d['variant']


@app.route('/bag')
def bag():
    if current_user.is_authenticated:
        items = CartItem.query.filter_by(user_id=current_user.id).all()
    else:
        items = [_AnonItem(d) for d in _anon_cart_items()]
    subtotal = sum(i.product.price * i.quantity for i in items)
    return render_template('bag.html', items=items, subtotal=subtotal)


@app.route('/cart')
def cart():
    """Alias for /bag - Amazon-style cart page."""
    return redirect(url_for('bag'))


@app.route('/cart/add/<int:product_id>', methods=['POST'])
@csrf.exempt
def cart_add_form(product_id):
    """Non-AJAX add-to-cart via form POST (works reliably with browser agents).

    Supports both logged-in users (DB-backed CartItem) and anonymous users
    (session-based cart), so agents don't hit a login wall mid-task.
    """
    product = Product.query.get_or_404(product_id)
    variant = request.form.get('variant', '')
    qty = int(request.form.get('quantity', 1))
    if current_user.is_authenticated:
        existing = CartItem.query.filter_by(
            user_id=current_user.id, product_id=product_id, variant=variant
        ).first()
        if existing:
            existing.quantity += qty
        else:
            db.session.add(CartItem(user_id=current_user.id, product_id=product_id, quantity=qty, variant=variant))
        db.session.commit()
    else:
        cart = session.get('anon_cart', [])
        found = False
        for ci in cart:
            if ci.get('product_id') == product_id and ci.get('variant', '') == variant:
                ci['quantity'] += qty
                found = True
                break
        if not found:
            next_id = max([ci.get('id', 0) for ci in cart] or [0]) + 1
            cart.append({'id': next_id, 'product_id': product_id, 'quantity': qty, 'variant': variant})
        session['anon_cart'] = cart
        session.modified = True
    flash(f'Added {product.name} to cart. Item added to your shopping cart.', 'success')
    next_url = request.form.get('next', '')
    if next_url == 'checkout':
        return redirect(url_for('checkout'))
    return redirect(url_for('bag'))


@app.route('/api/cart/add', methods=['POST'])
@csrf.exempt
def cart_add():
    if not current_user.is_authenticated:
        return jsonify({'success': False, 'error': 'Please sign in', 'redirect': url_for('login')}), 401
    data = request.get_json() or {}
    pid = data.get('product_id')
    qty = int(data.get('quantity', 1))
    variant = data.get('variant', '')
    product = Product.query.get(pid)
    if not product:
        return jsonify({'success': False, 'error': 'Product not found'}), 404

    existing = CartItem.query.filter_by(
        user_id=current_user.id, product_id=pid, variant=variant
    ).first()
    if existing:
        existing.quantity += qty
    else:
        db.session.add(CartItem(user_id=current_user.id, product_id=pid, quantity=qty, variant=variant))
    db.session.commit()

    cart_count = db.session.query(func.sum(CartItem.quantity)).filter_by(user_id=current_user.id).scalar() or 0
    return jsonify({'success': True, 'cart_count': int(cart_count), 'message': f'Added {product.name} to cart'})


@app.route('/api/cart/update', methods=['POST'])
@csrf.exempt
@login_required
def cart_update():
    data = request.get_json() or {}
    item_id = data.get('item_id')
    qty = int(data.get('quantity', 1))
    item = CartItem.query.filter_by(id=item_id, user_id=current_user.id).first()
    if not item:
        return jsonify({'success': False, 'error': 'Not found'}), 404
    if qty <= 0:
        db.session.delete(item)
    else:
        item.quantity = qty
    db.session.commit()

    items = CartItem.query.filter_by(user_id=current_user.id).all()
    subtotal = sum(i.product.price * i.quantity for i in items)
    cart_count = sum(i.quantity for i in items)
    return jsonify({'success': True, 'cart_count': cart_count, 'subtotal': round(subtotal, 2)})


@app.route('/api/cart/remove', methods=['POST'])
@csrf.exempt
@login_required
def cart_remove():
    data = request.get_json() or {}
    item_id = data.get('item_id')
    item = CartItem.query.filter_by(id=item_id, user_id=current_user.id).first()
    if not item:
        return jsonify({'success': False}), 404
    db.session.delete(item)
    db.session.commit()
    items = CartItem.query.filter_by(user_id=current_user.id).all()
    subtotal = sum(i.product.price * i.quantity for i in items)
    cart_count = sum(i.quantity for i in items)
    return jsonify({'success': True, 'cart_count': cart_count, 'subtotal': round(subtotal, 2)})


# ----- Routes: Checkout / Orders -----

@app.route('/checkout', methods=['GET', 'POST'])
@csrf.exempt
@login_required
def checkout():
    items = CartItem.query.filter_by(user_id=current_user.id).all()
    if not items:
        flash('Your cart is empty.', 'info')
        return redirect(url_for('bag'))

    subtotal = sum(i.product.price * i.quantity for i in items)
    shipping = 0 if current_user.is_prime or subtotal > 35 else 5.99
    tax = round(subtotal * 0.0825, 2)
    total = round(subtotal + shipping + tax, 2)

    saved_addrs = SavedAddress.query.filter_by(user_id=current_user.id).order_by(SavedAddress.is_default.desc()).all()
    saved_payments = PaymentMethod.query.filter_by(user_id=current_user.id).order_by(PaymentMethod.is_default.desc()).all()

    form = CheckoutForm()
    # Pre-fill from default saved address or user profile
    if request.method == 'GET':
        default_addr = next((a for a in saved_addrs if a.is_default), None)
        if default_addr:
            form.name.data = default_addr.full_name
            form.address.data = default_addr.address_line1
            form.city.data = default_addr.city
            form.state.data = default_addr.state
            form.zip_code.data = default_addr.zip_code
            form.phone.data = default_addr.phone
        else:
            form.name.data = current_user.name
            form.address.data = current_user.address_line1
            form.city.data = current_user.city
            form.state.data = current_user.state
            form.zip_code.data = current_user.zip_code
            form.phone.data = current_user.phone

    if form.validate_on_submit():
        # Determine payment info from saved method or form entry
        selected_pm_id = request.form.get('saved_payment_id')
        if selected_pm_id and selected_pm_id != 'new':
            pm = PaymentMethod.query.filter_by(id=int(selected_pm_id), user_id=current_user.id).first()
            pay_method = pm.card_type if pm else 'Visa'
            pay_last4 = pm.last4 if pm else '1234'
        else:
            pay_method = 'Visa'
            pay_last4 = form.card_number.data[-4:] if form.card_number.data else '1234'

        # Determine shipping address from saved address or form entry
        selected_addr_id = request.form.get('saved_address_id')
        if selected_addr_id and selected_addr_id != 'new':
            addr = SavedAddress.query.filter_by(id=int(selected_addr_id), user_id=current_user.id).first()
            if addr:
                ship_name = addr.full_name
                ship_address = addr.address_line1
                ship_city = addr.city
                ship_state = addr.state
                ship_zip = addr.zip_code
            else:
                ship_name, ship_address, ship_city, ship_state, ship_zip = (
                    form.name.data, form.address.data, form.city.data, form.state.data, form.zip_code.data)
        else:
            ship_name = form.name.data
            ship_address = form.address.data
            ship_city = form.city.data
            ship_state = form.state.data
            ship_zip = form.zip_code.data

        order_num = f"112-{random.randint(1000000, 9999999)}-{random.randint(1000000, 9999999)}"
        order = Order(
            user_id=current_user.id,
            order_number=order_num,
            status='processing',
            subtotal=round(subtotal, 2),
            shipping=shipping,
            tax=tax,
            total=total,
            ship_name=ship_name,
            ship_address=ship_address,
            ship_city=ship_city,
            ship_state=ship_state,
            ship_zip=ship_zip,
            payment_method=pay_method,
            payment_last4=pay_last4,
            delivery_estimate=(datetime.utcnow() + timedelta(days=random.randint(2, 5))).strftime('%A, %B %d')
        )
        db.session.add(order)
        db.session.flush()

        for item in items:
            db.session.add(OrderItem(
                order_id=order.id,
                product_id=item.product_id,
                product_name=item.product.name,
                product_image=item.product.image,
                variant=item.variant,
                quantity=item.quantity,
                price=item.product.price
            ))
            db.session.delete(item)

        db.session.commit()
        return redirect(url_for('order_confirmation', order_id=order.id))

    return render_template('checkout.html', form=form, items=items,
        subtotal=subtotal, shipping=shipping, tax=tax, total=total,
        saved_addrs=saved_addrs, saved_payments=saved_payments)


@app.route('/order/<int:order_id>/confirmation')
@login_required
def order_confirmation(order_id):
    order = Order.query.filter_by(id=order_id, user_id=current_user.id).first_or_404()
    return render_template('order_confirmation.html', order=order)


@app.route('/order/<int:order_id>')
@login_required
def order_detail(order_id):
    order = Order.query.filter_by(id=order_id, user_id=current_user.id).first_or_404()
    return render_template('order_detail.html', order=order)


@app.route('/order/<int:order_id>/cancel', methods=['POST'])
@csrf.exempt
@login_required
def order_cancel(order_id):
    order = Order.query.filter_by(id=order_id, user_id=current_user.id).first_or_404()
    # R5: explicit cancellation-window policy. Orders can be cancelled
    # while still 'processing' AND within 30 minutes of placement.
    # Beyond that they're locked even if not shipped — matches Amazon UX.
    CANCEL_WINDOW_MIN = 30
    if order.status != 'processing':
        flash(f'This order is "{order.status}" and can no longer be cancelled. '
              f'Cancellation is only available for orders in "processing" status.',
              'error')
    else:
        elapsed = (MIRROR_REFERENCE_DATE - order.created_at).total_seconds() / 60.0
        if elapsed > CANCEL_WINDOW_MIN:
            flash(f'The {CANCEL_WINDOW_MIN}-minute cancellation window has expired '
                  f'({int(elapsed)} min since order placement). Please request a '
                  f'return after delivery instead.', 'error')
        else:
            order.status = 'cancelled'
            db.session.commit()
            flash('Order cancelled. A refund will appear within 3–5 business days.',
                  'success')
    return redirect(url_for('order_detail', order_id=order.id))


@app.route('/order/<int:order_id>/reorder', methods=['POST'])
@csrf.exempt
@login_required
def order_reorder(order_id):
    order = Order.query.filter_by(id=order_id, user_id=current_user.id).first_or_404()
    count = 0
    for oi in order.items:
        existing = CartItem.query.filter_by(
            user_id=current_user.id, product_id=oi.product_id, variant=oi.variant
        ).first()
        if existing:
            existing.quantity += oi.quantity
        else:
            db.session.add(CartItem(
                user_id=current_user.id, product_id=oi.product_id,
                quantity=oi.quantity, variant=oi.variant
            ))
        count += 1
    db.session.commit()
    flash(f'{count} item(s) added back to your cart.', 'success')
    return redirect(url_for('bag'))


# ----- Routes: Returns -----

RETURN_REASONS = [
    ('doesnt_fit', "Doesn't fit"),
    ('defective', 'Item defective or doesn\'t work'),
    ('changed_mind', 'No longer needed'),
    ('wrong_item', 'Wrong item was sent'),
    ('better_price', 'Better price available'),
    ('damaged', 'Product damaged on arrival'),
]

@app.route('/order/<int:order_id>/return', methods=['GET', 'POST'])
@csrf.exempt
@login_required
def order_return(order_id):
    order = Order.query.filter_by(id=order_id, user_id=current_user.id).first_or_404()
    if order.status != 'delivered':
        flash('Only delivered orders can be returned.', 'error')
        return redirect(url_for('order_detail', order_id=order.id))
    # 30-day return window — measured against MIRROR_REFERENCE_DATE so that
    # seeded delivered orders remain returnable regardless of when an agent
    # exercises this route. Live orders placed via /checkout still anchor at
    # MIRROR_REFERENCE_DATE on insert (see _seed_now), so the math is uniform.
    if order.created_at and (MIRROR_REFERENCE_DATE - order.created_at).days > 30:
        flash('Return window (30 days) has expired for this order.', 'error')
        return redirect(url_for('order_detail', order_id=order.id))

    if request.method == 'POST':
        selected_item_ids = request.form.getlist('return_items')
        if not selected_item_ids:
            flash('Please select at least one item to return.', 'error')
            return render_template('return.html', order=order, reasons=RETURN_REASONS)

        refund_method = request.form.get('refund_method', 'original_payment')
        refund_amount = 0

        ret = Return(
            order_id=order.id,
            user_id=current_user.id,
            status='requested',
            refund_method=refund_method,
        )
        db.session.add(ret)
        db.session.flush()

        for oi_id in selected_item_ids:
            oi = OrderItem.query.get(int(oi_id))
            if oi and oi.order_id == order.id:
                reason = request.form.get(f'reason_{oi_id}', 'changed_mind')
                qty = int(request.form.get(f'qty_{oi_id}', oi.quantity))
                refund_amount += oi.price * qty
                db.session.add(ReturnItem(
                    return_id=ret.id,
                    order_item_id=oi.id,
                    product_name=oi.product_name,
                    quantity=qty,
                    reason=reason,
                ))

        ret.refund_amount = round(refund_amount, 2)
        db.session.commit()
        return redirect(url_for('return_confirmation', return_id=ret.id))

    return render_template('return.html', order=order, reasons=RETURN_REASONS)


@app.route('/return/<int:return_id>/confirmation')
@login_required
def return_confirmation(return_id):
    ret = Return.query.filter_by(id=return_id, user_id=current_user.id).first_or_404()
    return render_template('return_confirmation.html', ret=ret)


# ----- Routes: Wishlist -----

@app.route('/wishlist')
@login_required
def wishlist():
    items = WishlistItem.query.filter_by(user_id=current_user.id).order_by(WishlistItem.added_at.desc()).all()
    return render_template('wishlist.html', items=items)


@app.route('/api/wishlist/toggle', methods=['POST'])
@csrf.exempt
def wishlist_toggle():
    if not current_user.is_authenticated:
        return jsonify({'success': False, 'error': 'Please sign in', 'redirect': url_for('login')}), 401
    data = request.get_json() or {}
    pid = data.get('product_id')
    existing = WishlistItem.query.filter_by(user_id=current_user.id, product_id=pid).first()
    if existing:
        db.session.delete(existing)
        db.session.commit()
        return jsonify({'success': True, 'in_wishlist': False, 'message': 'Removed from wishlist'})
    else:
        db.session.add(WishlistItem(user_id=current_user.id, product_id=pid))
        db.session.commit()
        return jsonify({'success': True, 'in_wishlist': True, 'message': 'Added to wishlist'})


@app.route('/wishlist/remove/<int:item_id>', methods=['POST'])
@csrf.exempt
@login_required
def wishlist_remove(item_id):
    item = WishlistItem.query.filter_by(id=item_id, user_id=current_user.id).first_or_404()
    db.session.delete(item)
    db.session.commit()
    flash('Removed from wishlist.', 'info')
    return redirect(url_for('wishlist'))


# ----- Routes: Reviews -----

@app.route('/product/<slug>/review', methods=['POST'])
@csrf.exempt
@login_required
def add_review(slug):
    product = Product.query.filter_by(slug=slug).first_or_404()
    form = ReviewForm()
    if form.validate_on_submit():
        review = Review(
            user_id=current_user.id,
            product_id=product.id,
            rating=form.rating.data,
            title=form.title.data,
            body=form.body.data
        )
        db.session.add(review)
        # Update product avg rating
        reviews = Review.query.filter_by(product_id=product.id).all()
        if reviews:
            product.review_count = len(reviews) + 1
            total = sum(r.rating for r in reviews) + form.rating.data
            product.rating = round(total / product.review_count, 1)
        db.session.commit()
        flash('Thanks for your review!', 'success')
    else:
        flash('Please fill all fields.', 'error')
    return redirect(url_for('product_detail', slug=slug))


@app.route('/review/<int:review_id>/delete', methods=['POST'])
@csrf.exempt
@login_required
def delete_review(review_id):
    review = Review.query.filter_by(id=review_id, user_id=current_user.id).first_or_404()
    slug = review.product.slug
    db.session.delete(review)
    db.session.commit()
    flash('Review deleted.', 'info')
    return redirect(url_for('product_detail', slug=slug))


# ----- API -----

@app.route('/api/products/<category_slug>')
def api_products(category_slug):
    products = Product.query.filter_by(category_slug=category_slug).limit(50).all()
    return jsonify([{
        'id': p.id, 'name': p.name, 'slug': p.slug, 'price': p.price,
        'image': p.image, 'rating': p.rating, 'review_count': p.review_count
    } for p in products])


# ----- Error handlers -----

@app.errorhandler(404)
def not_found(e):
    return render_template('404.html'), 404


@app.errorhandler(500)
def server_error(e):
    db.session.rollback()
    return render_template('500.html'), 500


# ----- Seed Data -----

def seed_database():
    """Populate the database with categories, products, reviews."""
    from seed_data import run_seed
    run_seed(db, Category, Product, User, Review)


def seed_benchmark_users():
    """Seed multiple users with addresses, payment methods, and order history for WebTau tasks.
    Call this AFTER expand_catalog.py has run so all products exist."""
    if User.query.filter_by(email='alice.j@test.com').first():
        return  # already seeded

    users_data = [
        {'name': 'Alice Johnson', 'email': 'alice.j@test.com', 'password': 'TestPass123!', 'is_prime': True,
         'phone': '415-555-0101', 'city': 'San Francisco', 'state': 'CA', 'zip_code': '94102',
         'address_line1': '456 Oak Ave'},
        {'name': 'Bob Chen', 'email': 'bob.c@test.com', 'password': 'TestPass123!', 'is_prime': False,
         'phone': '512-555-0202', 'city': 'Austin', 'state': 'TX', 'zip_code': '78701',
         'address_line1': '789 Pine St'},
        {'name': 'Carol Davis', 'email': 'carol.d@test.com', 'password': 'TestPass123!', 'is_prime': True,
         'phone': '212-555-0303', 'city': 'New York', 'state': 'NY', 'zip_code': '10001',
         'address_line1': '321 Broadway'},
        {'name': 'David Kim', 'email': 'david.k@test.com', 'password': 'TestPass123!', 'is_prime': True,
         'phone': '312-555-0404', 'city': 'Chicago', 'state': 'IL', 'zip_code': '60601',
         'address_line1': '555 Michigan Ave'},
    ]

    created_users = []
    # Pinned bcrypt('TestPass123!') for byte-identical reset (see harden-env/gotchas.md).
    PINNED_TESTPASS_HASH = '$2b$12$PpubQvLvUkIksb10lxqIduzS2wfRkZ.ZAobDEtGEF7N9qelOp5ktK'
    for ud in users_data:
        u = User(email=ud['email'], name=ud['name'], phone=ud['phone'],
                 address_line1=ud['address_line1'], city=ud['city'], state=ud['state'],
                 zip_code=ud['zip_code'], is_prime=ud['is_prime'])
        u.password_hash = PINNED_TESTPASS_HASH
        db.session.add(u)
        db.session.flush()
        created_users.append(u)

    alice, bob, carol, david = created_users

    # --- Saved Addresses ---
    addresses_data = [
        # Alice: 2 addresses, Home (default) + Work
        (alice, 'Home', 'Alice Johnson', '415-555-0101', '456 Oak Ave', '', 'San Francisco', 'CA', '94102', True),
        (alice, 'Work', 'Alice Johnson', '415-555-0199', '100 Market St, Floor 5', '', 'San Francisco', 'CA', '94105', False),
        # Bob: 1 address
        (bob, 'Home', 'Bob Chen', '512-555-0202', '789 Pine St', 'Apt 4B', 'Austin', 'TX', '78701', True),
        # Carol: 3 addresses — for gift shopping tasks
        (carol, 'Home', 'Carol Davis', '212-555-0303', '321 Broadway', 'Apt 12A', 'New York', 'NY', '10001', True),
        (carol, 'Work', 'Carol Davis', '212-555-0388', '200 Park Ave', 'Suite 1500', 'New York', 'NY', '10166', False),
        (carol, 'Other', 'Sarah Johnson', '217-555-0777', '742 Evergreen Terrace', '', 'Springfield', 'IL', '62701', False),
        # David: 3 addresses
        (david, 'Home', 'David Kim', '312-555-0404', '555 Michigan Ave', '', 'Chicago', 'IL', '60601', True),
        (david, 'Work', 'David Kim', '312-555-0455', '233 S Wacker Dr', 'Floor 40', 'Chicago', 'IL', '60606', False),
        (david, 'Other', 'Lisa Kim', '847-555-0622', '1500 Sheridan Rd', 'Apt 3C', 'Evanston', 'IL', '60201', False),
    ]
    for user, label, name, phone, a1, a2, city, state, zc, default in addresses_data:
        db.session.add(SavedAddress(
            user_id=user.id, label=label, full_name=name, phone=phone,
            address_line1=a1, address_line2=a2, city=city, state=state,
            zip_code=zc, is_default=default))

    # --- Payment Methods ---
    # Alice gets 2 Visas (for ambiguity testing) + 1 Mastercard
    payments_data = [
        (alice, 'Visa', '4242', 12, 2027, 'Alice Johnson', True),
        (alice, 'Visa', '1177', 6, 2028, 'Alice Johnson', False),
        (alice, 'Mastercard', '8891', 3, 2026, 'Alice Johnson', False),
        (bob, 'Visa', '5678', 9, 2027, 'Bob Chen', True),
        (carol, 'Amex', '3456', 11, 2028, 'Carol Davis', True),
        (carol, 'Visa', '9012', 5, 2026, 'Carol Davis', False),
        (carol, 'Mastercard', '6677', 3, 2027, 'Carol Davis', False),
        (david, 'Mastercard', '7734', 8, 2027, 'David Kim', True),
        (david, 'Discover', '4455', 2, 2028, 'David Kim', False),
    ]
    for user, ctype, last4, em, ey, name, default in payments_data:
        db.session.add(PaymentMethod(
            user_id=user.id, card_type=ctype, last4=last4,
            exp_month=em, exp_year=ey, cardholder_name=name, is_default=default))

    # --- Pre-seeded Orders ---
    # We need products from DB for order items
    def _get_product(name_fragment):
        return Product.query.filter(Product.name.ilike(f'%{name_fragment}%')).first()

    def _make_order(user, status, items_spec, days_ago):
        order_num = f"112-{random.randint(1000000, 9999999)}-{random.randint(1000000, 9999999)}"
        subtotal = sum(p.price * qty for p, qty, _ in items_spec)
        ship_cost = 0 if user.is_prime or subtotal > 35 else 5.99
        tax = round(subtotal * 0.0825, 2)
        total = round(subtotal + ship_cost + tax, 2)
        default_addr = SavedAddress.query.filter_by(user_id=user.id, is_default=True).first()
        default_pm = PaymentMethod.query.filter_by(user_id=user.id, is_default=True).first()
        order = Order(
            user_id=user.id, order_number=order_num, status=status,
            subtotal=round(subtotal, 2), shipping=ship_cost, tax=tax, total=total,
            ship_name=default_addr.full_name if default_addr else user.name,
            ship_address=default_addr.address_line1 if default_addr else user.address_line1,
            ship_city=default_addr.city if default_addr else user.city,
            ship_state=default_addr.state if default_addr else user.state,
            ship_zip=default_addr.zip_code if default_addr else user.zip_code,
            payment_method=default_pm.card_type if default_pm else 'Visa',
            payment_last4=default_pm.last4 if default_pm else '1234',
            created_at=MIRROR_REFERENCE_DATE - timedelta(days=days_ago),
            delivery_estimate=(MIRROR_REFERENCE_DATE + timedelta(days=2 + (days_ago % 4))).strftime('%A, %B %d'),
        )
        db.session.add(order)
        db.session.flush()
        for prod, qty, variant in items_spec:
            db.session.add(OrderItem(
                order_id=order.id, product_id=prod.id,
                product_name=prod.name, product_image=prod.image,
                variant=variant, quantity=qty, price=prod.price))
        return order

    # Alice's orders
    p_sony = _get_product('Sony WH-1000XM5')
    p_echo = _get_product('Echo Dot')
    p_atomic = _get_product('Atomic Habits')
    p_irobot = _get_product('iRobot Roomba')
    p_instant = _get_product('Instant Pot')
    p_adidas = _get_product('Cloudfoam Pure Running')

    if p_sony:
        _make_order(alice, 'processing', [(p_sony, 1, 'Color: Black')], days_ago=1)
    if p_echo:
        _make_order(alice, 'shipped', [(p_echo, 1, 'Color: Charcoal')], days_ago=5)
    if p_atomic and p_adidas:
        _make_order(alice, 'delivered', [(p_atomic, 1, 'Format: Paperback'), (p_adidas, 1, 'Size: 8, Color: White/Black')], days_ago=10)
    if p_irobot:
        _make_order(alice, 'delivered', [(p_irobot, 1, '')], days_ago=20)

    # Bob's orders
    p_kindle = _get_product('Kindle Paperwhite')
    p_yoga = _get_product('Amazon Basics Yoga Mat')
    if p_kindle:
        _make_order(bob, 'delivered', [(p_kindle, 1, '')], days_ago=8)
    if p_yoga:
        _make_order(bob, 'processing', [(p_yoga, 1, 'Color: Blue')], days_ago=1)

    # Carol's orders
    p_macbook = _get_product('MacBook')
    p_logi = _get_product('Logitech MX')
    if p_macbook and p_logi:
        _make_order(carol, 'delivered', [(p_macbook, 1, ''), (p_logi, 1, '')], days_ago=7)

    # David's orders
    p_samsung_tv = _get_product('Samsung')
    p_hp = _get_product('HP OMEN')
    if p_samsung_tv:
        _make_order(david, 'delivered', [(p_samsung_tv, 1, '')], days_ago=12)
    if p_hp:
        _make_order(david, 'processing', [(p_hp, 1, '')], days_ago=2)
    if p_instant:
        _make_order(david, 'cancelled', [(p_instant, 1, '')], days_ago=15)

    # Pre-seed cart items for Alice (for cart modification tasks)
    p_jeans = _get_product("501 Original")
    p_shoe = _get_product('Cloudfoam Pure Running')
    if p_jeans:
        db.session.add(CartItem(user_id=alice.id, product_id=p_jeans.id, quantity=1, variant='Size: 32x30, Color: Medium Wash'))
    if p_shoe:
        db.session.add(CartItem(user_id=alice.id, product_id=p_shoe.id, quantity=1, variant='Size: 8, Color: White/Black'))
    if p_echo:
        db.session.add(CartItem(user_id=alice.id, product_id=p_echo.id, quantity=1, variant='Color: Charcoal'))

    db.session.commit()


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        if Product.query.count() == 0:
            seed_database()
        seed_benchmark_users()
        from seed_extras import run_extras
        run_extras(db, User, Product, Category, CartItem, Order, OrderItem,
                   WishlistItem, SavedAddress, PaymentMethod, Return, ReturnItem)
    port = int(os.environ.get('PORT', 28841))
    app.run(host='0.0.0.0', port=port, debug=False)
